import os
import uuid
import logging
import asyncio
import json
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx
import uvicorn
import argparse
from datetime import datetime

# Import Google A2A models
import sys
from pathlib import Path

# Add parent directory to path so we can import agents.network
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.network.google_a2a_models import (
    AgentCard,
    AgentSkill,
    AgentProvider,
    AgentCapabilities,
    Message,
    MessageRole,
    TextPart,
    DataPart,
    Task,
    TaskState,
    TaskStatus,
    JSONRPCRequest,
    JSONRPCResponse,
    MessageSendParams,
    generate_agent_id,
    generate_task_id,
    generate_context_id,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sidecar")

app = FastAPI(title="Google A2A Compliant Agent Sidecar")

# Global State
AGENT_ID = None
ADAPTER = None
BUTLER_URL = None
AGENT_NAME = "Unknown Agent"
AGENT_PORT = 8000
GLOBAL_ANNOUNCED_URL = None

# Task storage (in-memory for simplicity, should use persistent storage in production)
_tasks: Dict[str, Task] = {}


# ============================================================================
# Legacy Models (Backward Compatibility)
# ============================================================================

class MessageRequest(BaseModel):
    """Legacy message request format."""
    from_agent_id: str
    conversation_id: str
    content: str
    context: Optional[dict] = None

class MessageResponse(BaseModel):
    """Legacy message response format."""
    agent_id: str
    content: str
    status: str = "success"
    error: Optional[str] = None


# ============================================================================
# Google A2A Endpoints
# ============================================================================

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Well-known endpoint for AgentCard discovery.
    This is the standard Google A2A discovery mechanism.
    """
    agent_card = AgentCard(
        protocol_version="0.2.5",
        name=AGENT_NAME,
        description=f"Sidecar agent: {AGENT_NAME}",
        url=GLOBAL_ANNOUNCED_URL or f"http://localhost:{AGENT_PORT}",
        provider=AgentProvider(
            organization="Sidecar",
            url="https://github.com"
        ),
        version="1.0.0",
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=True
        ),
        default_input_modes=["application/json", "text/plain"],
        default_output_modes=["application/json", "text/plain"],
        skills=[
            AgentSkill(
                id="generic",
                name="Generic Processing",
                description=f"Process requests using {ADAPTER.__class__.__name__} adapter",
                tags=["generic", "processing"],
                examples=["Process this request"]
            )
        ],
        supports_authenticated_extended_card=True
    )
    return agent_card


@app.post("/")
async def handle_jsonrpc(request: JSONRPCRequest):
    """
    Main Google A2A endpoint for JSON-RPC 2.0 requests.
    Handles message/send, message/stream, tasks/get, tasks/cancel methods.
    """
    try:
        logger.info(f"Received JSON-RPC request: {request.method}")
        
        if request.method == "message/send":
            return await handle_message_send(request)
        elif request.method == "message/stream":
            return await handle_message_stream(request)
        elif request.method == "tasks/get":
            return await handle_tasks_get(request)
        elif request.method == "tasks/cancel":
            return await handle_tasks_cancel(request)
        else:
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            )
    except Exception as e:
        logger.error(f"Error handling JSON-RPC request: {e}")
        return JSONRPCResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        )


async def handle_message_send(request: JSONRPCRequest) -> JSONRPCResponse:
    """Handle message/send method."""
    params = MessageSendParams(**request.params)
    
    # Create or get task
    if params.task_id and params.task_id in _tasks:
        task = _tasks[params.task_id]
    else:
        task = Task(
            id=generate_task_id(),
            context_id=generate_context_id(),
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                message=params.message
            )
        )
        _tasks[task.id] = task
    
    # Update task to working state
    task.status.state = TaskState.WORKING
    task.status.message = params.message
    
    # Process the message
    try:
        # Extract content from message parts
        content = ""
        context = {}
        for part in params.message.parts:
            if isinstance(part, TextPart):
                content += part.text
            elif isinstance(part, DataPart):
                context.update(part.data)
        
        # Call adapter
        response_text = await ADAPTER.process_message(content, context)
        
        # Update task to completed state
        task.status.state = TaskState.COMPLETED
        task.status.message = Message(
            role=MessageRole.AGENT,
            parts=[TextPart(text=response_text)]
        )
        
        return JSONRPCResponse(
            id=request.id,
            result=task.model_dump(mode='json', by_alias=True)
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        task.status.state = TaskState.FAILED
        task.status.message = Message(
            role=MessageRole.AGENT,
            parts=[TextPart(text=f"Error: {str(e)}")]
        )
        
        return JSONRPCResponse(
            id=request.id,
            result=task.model_dump(mode='json', by_alias=True)
        )


async def handle_message_stream(request: JSONRPCRequest) -> JSONRPCResponse:
    """Handle message/stream method (returns initial task, actual streaming via SSE)."""
    params = MessageSendParams(**request.params)
    
    # Create task
    task = Task(
        id=generate_task_id(),
        context_id=generate_context_id(),
        status=TaskStatus(
            state=TaskState.SUBMITTED,
            message=params.message
        )
    )
    _tasks[task.id] = task
    
    from agents.network.google_a2a_models import SendStreamingMessageResponse
    
    return JSONRPCResponse(
        id=request.id,
        result=SendStreamingMessageResponse(task=task).model_dump(mode='json', by_alias=True)
    )


async def handle_tasks_get(request: JSONRPCRequest) -> JSONRPCResponse:
    """Handle tasks/get method."""
    from agents.network.google_a2a_models import TaskQueryParams
    
    params = TaskQueryParams(**request.params)
    task = _tasks.get(params.task_id)
    
    if not task:
        return JSONRPCResponse(
            id=request.id,
            error={
                "code": -32602,
                "message": f"Task not found: {params.task_id}"
            }
        )
    
    return JSONRPCResponse(
        id=request.id,
        result=task.model_dump(mode='json', by_alias=True)
    )


async def handle_tasks_cancel(request: JSONRPCRequest) -> JSONRPCResponse:
    """Handle tasks/cancel method."""
    from agents.network.google_a2a_models import TaskQueryParams
    
    params = TaskQueryParams(**request.params)
    task = _tasks.get(params.task_id)
    
    if not task:
        return JSONRPCResponse(
            id=request.id,
            error={
                "code": -32602,
                "message": f"Task not found: {params.task_id}"
            }
        )
    
    task.status.state = TaskState.CANCELED
    
    return JSONRPCResponse(
        id=request.id,
        result=task.model_dump(mode='json', by_alias=True)
    )


# ============================================================================
# Legacy Endpoints (Backward Compatibility)
# ============================================================================

@app.post("/agent/message", response_model=MessageResponse)
async def handle_message_legacy(req: MessageRequest):
    """Legacy endpoint for backward compatibility."""
    if not ADAPTER:
        raise HTTPException(status_code=503, detail="Adapter not initialized")
    
    try:
        logger.info(f"Processing message from {req.from_agent_id}")
        response_text = await ADAPTER.process_message(req.content, req.context)
        return MessageResponse(
            agent_id=AGENT_ID,
            content=response_text,
            status="success"
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return MessageResponse(
            agent_id=AGENT_ID,
            content=str(e),
            status="error",
            error=str(e)
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "id": AGENT_ID,
        "adapter": str(ADAPTER.__class__.__name__) if ADAPTER else "None",
        "protocol": "google_a2a"
    }


# ============================================================================
# Lifecycle
# ============================================================================

@app.on_event("startup")
async def startup_event():
    global AGENT_ID
    
    # Load Persisted ID
    id_file = ".sidecar_id"
    if os.path.exists(id_file):
        with open(id_file, "r") as f:
            AGENT_ID = f.read().strip()
    else:
        AGENT_ID = generate_agent_id(AGENT_NAME.lower().replace(" ", "-"))
        with open(id_file, "w") as f:
            f.write(AGENT_ID)
            
    logger.info(f"Sidecar started with ID: {AGENT_ID}")
    logger.info(f"Google A2A compliant endpoint: http://0.0.0.0:{AGENT_PORT}")
    
    # Auto-Register
    if BUTLER_URL:
        logger.info(f"Auto-registration enabled for {BUTLER_URL}")
        asyncio.create_task(register_loop())


async def register_loop():
    """Periodically register with Butler."""
    url = f"{BUTLER_URL.rstrip('/')}/network/register"
    
    # Determine our URL
    my_url = GLOBAL_ANNOUNCED_URL or f"http://localhost:{AGENT_PORT}"
    
    payload = {
        "id": AGENT_ID,
        "name": AGENT_NAME,
        "url": my_url,
        "protocol": "google_a2a",
        "capabilities": [str(ADAPTER.__class__.__name__)] if ADAPTER else []
    }
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Registering with Butler at {url} as {my_url}...")
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("✅ Registration successful")
                else:
                    logger.warning(f"⚠️ Registration failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"❌ Connection to Butler failed: {e}")
            
        # Re-register every 60 seconds (heartbeat)
        await asyncio.sleep(60)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Add parent directory to path so we can import adapters
    sidecar_dir = Path(__file__).parent
    sys.path.insert(0, str(sidecar_dir))
    
    from adapters.cli import CLIAdapter
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", choices=["cli", "openai"], default="cli", help="Adapter type")
    parser.add_argument("--command", help="Command to run (for CLI adapter)")
    
    # OpenAI args
    parser.add_argument("--openai-url", help="Base URL for OpenAI adapter")
    parser.add_argument("--openai-key", help="API Key for OpenAI adapter")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="Model for OpenAI adapter")
    parser.add_argument("--system", help="System prompt")
    
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--name", default="Generic Agent")
    parser.add_argument("--butler-url", help="URL of the Butler AGENT")
    parser.add_argument("--announced-url", help="Public URL of this Sidecar (for NAT/Tunneling)")
    
    args = parser.parse_args()
    
    AGENT_NAME = args.name
    BUTLER_URL = args.butler_url
    AGENT_PORT = args.port
    GLOBAL_ANNOUNCED_URL = args.announced_url
    
    # Initialize Adapter
    if args.adapter == "cli":
        if not args.command:
            logger.error("--command is required for CLI adapter")
            exit(1)
        logger.info(f"Initializing CLI Adapter for: {args.command}")
        ADAPTER = CLIAdapter(args.command)
        
    elif args.adapter == "openai":
        from adapters.openai import OpenAIAdapter
        if not args.openai_key:
            args.openai_key = os.getenv("OPENAI_API_KEY")
            
        if not args.openai_url or not args.openai_key:
             logger.error("--openai-url and --openai-key are required for OpenAI adapter")
             exit(1)
             
        logger.info(f"Initializing OpenAI Adapter for: {args.model} at {args.openai_url}")
        ADAPTER = OpenAIAdapter(
            base_url=args.openai_url,
            api_key=args.openai_key,
            model=args.model,
            system_prompt=args.system
        )
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)
