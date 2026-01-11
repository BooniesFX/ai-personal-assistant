#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket Handler for SDK-based Agent
"""

import json
import asyncio
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from claude_agent_sdk import AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    CHAT = "chat"
    LOGIN = "login"
    MESSAGE_ADDED = "message_added"
    SESSION_STATE_CHANGED = "session_state_changed"
    ERROR = "error"
    LOGIN_SUCCESS = "login_success"

@dataclass
class WebSocketClient:
    websocket: Any
    user_id: Optional[str] = None

class WebSocketHandlerSDK:
    """WebSocket handler using ButlerSDKAgent"""
    
    def __init__(self, agent):
        self.agent = agent
        self.clients: Dict[int, WebSocketClient] = {}
        self._client_counter = 0
        self.running_tasks: Dict[int, asyncio.Task] = {}
    
    async def on_open(self, websocket) -> int:
        self._client_counter += 1
        client_id = self._client_counter
        self.clients[client_id] = WebSocketClient(websocket=websocket)
        logger.info(f"WebSocket client {client_id} connected")
        
        await self._send(websocket, {
            "type": MessageType.SESSION_STATE_CHANGED,
            "state": "connected",
            "clientId": client_id
        })
        return client_id
    
    async def on_close(self, client_id: int):
        if client_id in self.running_tasks:
            self.running_tasks[client_id].cancel()
            del self.running_tasks[client_id]
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def on_message(self, client_id: int, message: str):
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == MessageType.CHAT:
                await self._handle_chat(client_id, client, data)
            elif msg_type == MessageType.LOGIN:
                await self._handle_login(client_id, client, data)
            else:
                await self._send_error(client.websocket, f"Unknown type: {msg_type}")
        except json.JSONDecodeError as e:
            await self._send_error(client.websocket, f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error(client.websocket, str(e))
    
    async def _handle_login(self, client_id: int, client: WebSocketClient, data: dict):
        email = data.get("email", "").lower().strip()
        code = data.get("code", "")
        
        if not email or not code:
            await self._send_error(client.websocket, "Email and code required")
            return
        
        # Use identity manager for verification
        from agents.sdk.hooks import get_identity_manager
        identity_manager = get_identity_manager()
        
        if identity_manager and not identity_manager.verify_access(code):
            await self._send_error(client.websocket, "Invalid access code")
            return
        
        client.user_id = email
        logger.info(f"Client {client_id} logged in as {email}")
        
        await self._send(client.websocket, {
            "type": MessageType.LOGIN_SUCCESS,
            "email": email
        })
    
    async def _handle_chat(self, client_id: int, client: WebSocketClient, data: dict):
        content = data.get("content", "").strip()
        if not content:
            await self._send_error(client.websocket, "Empty message")
            return
        
        user_id = client.user_id or f"web_{client_id}"
        
        async def run_process():
            try:
                await self._send(client.websocket, {
                    "type": MessageType.SESSION_STATE_CHANGED,
                    "state": "thinking",
                    "status_text": "💭 Thinking..."
                })
                
                full_response = ""
                async for msg in self.agent.process_message(user_id, content):
                    # Parse SDK message types
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                full_response += block.text
                                # Stream partial response
                                await self._send(client.websocket, {
                                    "type": MessageType.SESSION_STATE_CHANGED,
                                    "state": "streaming",
                                    "status_text": block.text[:100] + "..."
                                })
                            elif isinstance(block, ToolUseBlock):
                                await self._send(client.websocket, {
                                    "type": MessageType.SESSION_STATE_CHANGED,
                                    "state": "tool_use",
                                    "status_text": f"🔧 Using tool: {block.name}"
                                })
                
                if not client.websocket.closed:
                    await self._send(client.websocket, {
                        "type": MessageType.MESSAGE_ADDED,
                        "message": {
                            "role": "assistant",
                            "content": full_response or "No response."
                        }
                    })
                    await self._send(client.websocket, {
                        "type": MessageType.SESSION_STATE_CHANGED,
                        "state": "idle"
                    })
                    
            except asyncio.CancelledError:
                logger.info(f"Task for client {client_id} cancelled")
            except Exception as e:
                logger.error(f"Error processing chat: {e}")
                if not client.websocket.closed:
                    await self._send_error(client.websocket, str(e))
                    await self._send(client.websocket, {
                        "type": MessageType.SESSION_STATE_CHANGED,
                        "state": "error"
                    })
            finally:
                if client_id in self.running_tasks:
                    del self.running_tasks[client_id]
        
        # Cancel previous task if still running
        if client_id in self.running_tasks:
            self.running_tasks[client_id].cancel()
        
        self.running_tasks[client_id] = asyncio.create_task(run_process())
    
    async def _send(self, websocket, data: dict):
        try:
            if websocket.closed:
                return
            await websocket.send_str(json.dumps(data))
        except Exception as e:
            if not websocket.closed:
                logger.error(f"Error sending: {e}")
    
    async def _send_error(self, websocket, message: str):
        await self._send(websocket, {
            "type": MessageType.ERROR,
            "message": message
        })
