import os
import uuid
import logging
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx
import uvicorn
import argparse

# Import shared models from core (or redefine if standalone)
# For the sidecar to be standalone, we redefine minimal models here or import if in same repo path.
# We will assume we can import from agents.network.models if running from root, 
# but essentially the sidecar should be independent. 
# For now, let's keep it simple and independent.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sidecar")

app = FastAPI(title="Agent Sidecar")

# Global State
AGENT_ID = None
ADAPTER = None
BUTLER_URL = None
AGENT_NAME = "Unknown Agent"
AGENT_PORT = 8000

class MessageRequest(BaseModel):
    from_agent_id: str
    conversation_id: str
    content: str
    context: Optional[dict] = None

class MessageResponse(BaseModel):
    agent_id: str
    content: str
    status: str = "success"
    error: Optional[str] = None

# --- Lifecycle ---

@app.on_event("startup")
async def startup_event():
    global AGENT_ID
    
    # Load Persisted ID
    id_file = ".sidecar_id"
    if os.path.exists(id_file):
        with open(id_file, "r") as f:
            AGENT_ID = f.read().strip()
    else:
        AGENT_ID = f"agent_{uuid.uuid4().hex[:8]}"
        with open(id_file, "w") as f:
            f.write(AGENT_ID)
            
    logger.info(f"Sidecar started with ID: {AGENT_ID}")
    
    # Auto-Register
    if BUTLER_URL:
        logger.info(f"Auto-registration enabled for {BUTLER_URL}")
        asyncio.create_task(register_loop())

async def register_loop():
    """Periodically register with Butler."""
    url = f"{BUTLER_URL.rstrip('/')}/network/register"
    
    # Determine our URL
    # If GLOBAL_ANNOUNCED_URL is set, use it. Otherwise assume http://localhost:{port}
    # We need access to AGENT_PORT which is global
    my_url = GLOBAL_ANNOUNCED_URL if 'GLOBAL_ANNOUNCED_URL' in globals() and globals()['GLOBAL_ANNOUNCED_URL'] else f"http://localhost:{AGENT_PORT}"
    
    payload = {
        "id": AGENT_ID,
        "name": AGENT_NAME,
        "url": my_url,
        "protocol": "a2a_rest",
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


# --- Endpoints ---

@app.post("/agent/message", response_model=MessageResponse)
async def handle_message(req: MessageRequest):
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
    return {"status": "ok", "id": AGENT_ID, "adapter": str(ADAPTER.__class__.__name__) if ADAPTER else "None"}

if __name__ == "__main__":
    import sys
    from pathlib import Path
    
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
    
    # Use announced URL if provided, else guess localhost
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
