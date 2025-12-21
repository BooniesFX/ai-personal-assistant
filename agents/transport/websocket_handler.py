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


class WebSocketHandler:
    """
    Handles WebSocket connections and message routing.
    
    Protocol:
    - Client sends: {"type": "chat", "content": "...", "attachments": [...]}
    - Server sends: {"type": "message_added", "message": {...}}
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
        """Handle chat message using AgentCore."""
        from agents.core.agent_core import Message, Platform
        
        content = data.get("content", "").strip()
        if not content:
            await self._send_error(client.websocket, "Empty message", code="empty_message")
            return
        
        # Determine user_id
        # Use bound identity (Email) if logged in, else fallback to web_ID
        user_id = client.bound_identity or client.telegram_id or f"web_{client_id}"
        
        # Define status callback for real-time visibility
        async def status_callback(status: Any):
            """Push status update or tool result to client."""
            if isinstance(status, dict) and status.get("type") == "tool_result":
                # Send tool result as a message so UI can render it (like images)
                await self._send(client.websocket, {
                    "type": MessageType.MESSAGE_ADDED,
                    "message": {
                        "role": "tool",
                        "content": status["content"],
                        "tool_name": status["tool_name"]
                    }
                })
                return

            # fallback to state change for text status
            status_str = str(status)
            state = "thinking"
            if "tool" in status_str.lower() or "executing" in status_str.lower():
                state = "tool_use"
            
            await self._send(client.websocket, {
                "type": MessageType.SESSION_STATE_CHANGED,
                "state": state,
                "status_text": status_str
            })        
        try:
            # Create unified message
            message = Message(
                user_id=user_id,
                platform=Platform.WEB,
                content=content
            )
            
            # Process via AgentCore
            response = await self.agent_core.process_message(
                message,
                platform_context=client,
                status_callback=status_callback
            )
            
            # Send assistant response
            await self._send(client.websocket, {
                "type": MessageType.MESSAGE_ADDED,
                "message": {
                    "role": "assistant",
                    "content": response.content
                }
            })
            
            # Update state
            await self._send(client.websocket, {
                "type": MessageType.SESSION_STATE_CHANGED,
                "state": "idle"
            })
            
        except Exception as e:
            logger.error(f"Error processing chat: {e}")
            import traceback
            traceback.print_exc()
            await self._send_error(client.websocket, str(e))
            await self._send(client.websocket, {
                "type": MessageType.SESSION_STATE_CHANGED,
                "state": "error"
            })
    
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
            # aiohttp WebSocketResponse uses send_str() not send()
            await websocket.send_str(json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending to websocket: {e}")
    
    async def _send_error(self, websocket, message: str, code: str = "error"):
        """Send error message."""
        await self._send(websocket, {
            "type": MessageType.ERROR,
            "code": code,
            "message": message
        })
