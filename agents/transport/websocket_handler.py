#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket Server for Claude Agent
Provides web interface alongside Telegram bot.
"""

import json
import asyncio
import logging
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types."""
    # Client -> Server
    CHAT = "chat"
    LOGIN = "login"
    RESUME = "resume"
    SET_OPTIONS = "set_options"
    ABORT = "abort"
    
    # Server -> Client
    MESSAGE_ADDED = "message_added"
    MESSAGE_CHUNK = "message_chunk"
    MESSAGES_UPDATED = "messages_updated"
    SESSION_STATE_CHANGED = "session_state_changed"
    ERROR = "error"
    LOGIN_SUCCESS = "login_success"


@dataclass
class WebSocketClient:
    """Represents a connected WebSocket client."""
    websocket: Any
    session_id: Optional[str] = None
    telegram_id: Optional[str] = None
    bound_identity: Optional[str] = None  # Validated Email/User ID
    current_message_id: Optional[str] = None # For tracking stream context


class WebSocketHandler:
    """
    Handles WebSocket connections and message routing.
    
    Protocol:
    - Client sends: {"type": "chat", "content": "...", "attachments": [...]}
    - Server sends: {"type": "message_added", "message": {...}}
    - Server sends: {"type": "message_chunk", "content": "..."}
    """
    
    def __init__(self, agent_core):
        """
        Initialize WebSocket handler.
        
        Args:
            agent_core: Unified AgentCore instance
        """
        self.agent_core = agent_core
        self.clients: Dict[int, WebSocketClient] = {}
        self._client_counter = 0
    
    async def on_open(self, websocket) -> int:
        """
        Handle new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            Client ID
        """
        self._client_counter += 1
        client_id = self._client_counter
        self.clients[client_id] = WebSocketClient(websocket=websocket)
        logger.info(f"WebSocket client {client_id} connected")
        
        # Send initial state
        await self._send(websocket, {
            "type": MessageType.SESSION_STATE_CHANGED,
            "state": "connected",
            "clientId": client_id
        })
        
        return client_id
    
    async def on_close(self, client_id: int):
        """Handle WebSocket disconnection."""
        if client_id in self.clients:
            # Cancel any running tasks for this client
            if hasattr(self, 'running_tasks') and client_id in self.running_tasks:
                task = self.running_tasks[client_id]
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled running task for client {client_id}")
                del self.running_tasks[client_id]
                
            del self.clients[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def on_message(self, client_id: int, message: str):
        """
        Handle incoming WebSocket message.
        
        Args:
            client_id: Client identifier
            message: Raw message string (JSON)
        """
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
            elif msg_type == MessageType.RESUME:
                await self._handle_resume(client_id, client, data)
            elif msg_type == MessageType.SET_OPTIONS:
                await self._handle_set_options(client_id, client, data)
            elif msg_type == MessageType.ABORT:
                await self._handle_abort(client_id, client, data)
            else:
                await self._send_error(client.websocket, f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            await self._send_error(client.websocket, f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
            await self._send_error(client.websocket, str(e))
    
    async def _handle_login(self, client_id: int, client: WebSocketClient, data: dict):
        """Handle login request."""
        email = data.get("email", "").lower().strip()
        code = data.get("code", "")
        
        if not email or not code:
            await self._send_error(client.websocket, "Email and Code required", code="auth_error")
            return
            
        # Verify code
        if not self.agent_core.identity_manager.verify_access(code):
            await self._send_error(client.websocket, "Invalid access code", code="auth_failed")
            return
            
        # Bind identity to connection
        client.bound_identity = email
        logger.info(f"Client {client_id} authenticated as {email}")
        
        await self._send(client.websocket, {
            "type": MessageType.LOGIN_SUCCESS,
            "email": email
        })
        
        # Restore history for this email
        # TODO: Ideally push history here
    
    async def _handle_chat(self, client_id: int, client: WebSocketClient, data: dict):
        """Handle chat message using AgentCore streaming."""
        from agents.core.agent_core import Message, Platform
        
        content = data.get("content", "").strip()
        if not content:
            await self._send_error(client.websocket, "Empty message", code="empty_message")
            return
        
        user_id = client.bound_identity or client.telegram_id or f"web_{client_id}"
        
        async def run_process():
            try:
                message = Message(
                    user_id=user_id,
                    platform=Platform.WEB,
                    content=content
                )
                
                # Use stream processing
                async for event in self.agent_core.process_message_stream(
                    message,
                    platform_context=client
                ):
                    if client.websocket.closed:
                        break
                        
                    e_type = event.get("type")
                    
                    if e_type == "status":
                        status_str = event.get("text", "")
                        state = "tool_use" if ("tool" in status_str.lower() or "executing" in status_str.lower()) else "thinking"
                        await self._send(client.websocket, {
                            "type": MessageType.SESSION_STATE_CHANGED,
                            "state": state,
                            "status_text": status_str
                        })
                        
                    elif e_type == "tool_result":
                        await self._send(client.websocket, {
                            "type": MessageType.MESSAGE_ADDED,
                            "message": {
                                "role": "tool",
                                "content": event["content"],
                                "tool_name": event["tool_name"]
                            }
                        })
                        
                    elif e_type == "text_chunk":
                        # logger.debug(f"WS: Sending chunk to client {client_id}")
                        await self._send(client.websocket, {
                            "type": MessageType.MESSAGE_CHUNK,
                            "content": event["content"]
                        })
                        
                    elif e_type == "final_response":
                        # We don't necessarily need a whole new message if we used chunks,
                        # but we send 'idle' to signal completion.
                        await self._send(client.websocket, {
                            "type": MessageType.SESSION_STATE_CHANGED,
                            "state": "idle"
                        })
                        
                    elif e_type == "error":
                        await self._send_error(client.websocket, event["message"])

            except asyncio.CancelledError:
                logger.info(f"Task for client {client_id} was explicitly cancelled")
            except Exception as e:
                logger.error(f"Error processing chat: {e}", exc_info=True)
                if not client.websocket.closed:
                    await self._send_error(client.websocket, str(e))
            finally:
                if client_id in getattr(self, 'running_tasks', {}):
                    del self.running_tasks[client_id]

        if not hasattr(self, 'running_tasks'):
            self.running_tasks = {}
            
        if client_id in self.running_tasks:
            self.running_tasks[client_id].cancel()
            
        self.running_tasks[client_id] = asyncio.create_task(run_process())
    
    async def _handle_resume(self, client_id: int, client: WebSocketClient, data: dict):
        """Handle session resume request using AgentCore."""
        from agents.core.agent_core import Platform
        
        telegram_id = data.get("telegramId")
        if not telegram_id:
            await self._send_error(client.websocket, "telegramId required", code="missing_telegram_id")
            return
        
        # Store telegram ID for session merging
        client.telegram_id = str(telegram_id)
        # Check if this TG ID is bound to an email
        email = self.agent_core.identity_manager.get_email("telegram", str(telegram_id))
        if email:
            client.bound_identity = email
            logger.info(f"Client {client_id} auto-authenticated via TG ID -> {email}")
        
        client.session_id = f"telegram_{telegram_id}"
        
        # Load existing session via AgentCore
        try:
            # Note: get_session_history might need update to support generic user_id lookup
            # But currently we just confirm Resume
            
            await self._send(client.websocket, {
                "type": MessageType.MESSAGES_UPDATED,
                "messages": [], # TODO: Fetch actual history
                "sessionId": client.session_id,
                "telegramId": telegram_id
            })
            
            logger.info(f"Client {client_id} resumed session {telegram_id}")
            
        except Exception as e:
            logger.error(f"Error resuming session: {e}")
            await self._send_error(client.websocket, str(e))
    
    async def _handle_set_options(self, client_id: int, client: WebSocketClient, data: dict):
        """Handle options update."""
        # For future: model selection, temperature, etc.
        await self._send(client.websocket, {
            "type": MessageType.SESSION_STATE_CHANGED,
            "state": "options_updated"
        })
    
    async def _handle_abort(self, client_id: int, client: WebSocketClient, data: dict):
        """Handle abort request."""
        # TODO: Implement abort logic for streaming
        await self._send(client.websocket, {
            "type": MessageType.SESSION_STATE_CHANGED,
            "state": "aborted"
        })
    
    async def _send(self, websocket, data: dict):
        """Send message to websocket."""
        try:
            if websocket.closed:
                return
            await websocket.send_str(json.dumps(data))
        except Exception as e:
            # Silently handle closed connections
            if not websocket.closed:
                logger.error(f"Error sending to websocket: {e}")
    
    async def _send_error(self, websocket, message: str, code: str = "error"):
        """Send error message."""
        await self._send(websocket, {
            "type": MessageType.ERROR,
            "code": code,
            "message": message
        })
