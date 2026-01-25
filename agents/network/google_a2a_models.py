#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google A2A Protocol Data Models
Based on Agent2Agent (A2A) Protocol Specification v0.2.5
https://a2a-protocol.org/v0.2.5/specification/

This module defines all data structures required for Google A2A compliance.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4


# ============================================================================
# Enums
# ============================================================================

class TaskState(str, Enum):
    """Task lifecycle states as defined in Google A2A specification."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REJECTED = "rejected"


class MessageRole(str, Enum):
    """Message roles in A2A communication."""
    USER = "user"
    AGENT = "agent"


# ============================================================================
# Agent Card Structures
# ============================================================================

class AgentProvider(BaseModel):
    """Information about the organization or entity providing the agent."""
    organization: str = Field(..., description="Agent provider's organization name")
    url: str = Field(..., description="Agent provider's URL")


class AgentExtension(BaseModel):
    """A declaration of an extension supported by an Agent."""
    uri: str = Field(..., description="The URI of the extension")
    description: Optional[str] = Field(None, description="Description of how this agent uses this extension")
    required: Optional[bool] = Field(False, description="Whether the client must follow specific requirements of the extension")
    params: Optional[Dict[str, Any]] = Field(None, description="Optional configuration for the extension")


class AgentCapabilities(BaseModel):
    """Defines optional capabilities supported by an agent."""
    streaming: bool = Field(False, description="true if the agent supports SSE")
    push_notifications: bool = Field(False, description="true if the agent can notify updates to client")
    state_transition_history: bool = Field(False, description="true if the agent exposes status change history for tasks")
    extensions: List[AgentExtension] = Field(default_factory=list, description="extensions supported by this agent")


class SecurityScheme(BaseModel):
    """Base class for security schemes."""
    type: str = Field(..., description="Type of security scheme")


class APIKeySecurityScheme(SecurityScheme):
    """API Key authentication scheme."""
    type: Literal["apiKey"] = "apiKey"
    name: str = Field(..., description="Name of the header or query parameter")
    in_: Literal["header", "query"] = Field("header", alias="in", description="Location of the API key")


class HTTPAuthSecurityScheme(SecurityScheme):
    """HTTP authentication scheme."""
    type: Literal["http"] = "http"
    scheme: str = Field(..., description="The HTTP authentication scheme (e.g., 'bearer', 'basic')")


class OAuth2SecurityScheme(SecurityScheme):
    """OAuth2 authentication scheme."""
    type: Literal["oauth2"] = "oauth2"
    flows: Dict[str, Any] = Field(..., description="OAuth2 flows configuration")


class OpenIdConnectSecurityScheme(SecurityScheme):
    """OpenID Connect authentication scheme."""
    type: Literal["openIdConnect"] = "openIdConnect"
    open_id_connect_url: str = Field(..., description="OpenID Connect URL")


AgentSecurityScheme = Union[
    APIKeySecurityScheme,
    HTTPAuthSecurityScheme,
    OAuth2SecurityScheme,
    OpenIdConnectSecurityScheme
]


class AgentSkill(BaseModel):
    """Represents a unit of capability that an agent can perform."""
    id: str = Field(..., description="Unique identifier for the agent's skill")
    name: str = Field(..., description="Human readable name of the skill")
    description: str = Field(..., description="Description of the skill - supports CommonMark")
    tags: List[str] = Field(..., description="Set of tagwords describing classes of capabilities")
    examples: Optional[List[str]] = Field(None, description="Example scenarios that the skill can perform")
    input_modes: Optional[List[str]] = Field(None, description="Supported media types for input")
    output_modes: Optional[List[str]] = Field(None, description="Supported media types for output")


class AgentCard(BaseModel):
    """
    An AgentCard conveys key information about an A2A-compliant agent.
    Based on Google A2A Protocol Specification v0.2.5
    """
    protocol_version: str = Field("0.2.5", alias="protocolVersion", description="The version of the A2A protocol this agent supports")
    name: str = Field(..., description="Human readable name of the agent")
    description: str = Field(..., description="A human-readable description of the agent. Supports CommonMark")
    url: str = Field(..., description="Base URL for the agent's A2A service. Must be absolute. HTTPS for production")
    provider: Optional[AgentProvider] = Field(None, description="Information about the agent's provider")
    icon_url: Optional[str] = Field(None, alias="iconUrl", description="A URL to an icon for the agent")
    version: str = Field(..., description="The version of the agent - format is up to the provider")
    documentation_url: Optional[str] = Field(None, alias="documentationUrl", description="URL to documentation for the agent")
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities, description="Optional capabilities supported by the agent")
    security_schemes: Optional[Dict[str, Dict[str, Any]]] = Field(None, alias="securitySchemes", description="Security scheme details used for authenticating with this agent")
    security: Optional[List[Dict[str, List[str]]]] = Field(None, description="Security requirements for contacting the agent")
    default_input_modes: List[str] = Field(..., alias="defaultInputModes", description="Input Media Types accepted by the agent")
    default_output_modes: List[str] = Field(..., alias="defaultOutputModes", description="Output Media Types produced by the agent")
    skills: List[AgentSkill] = Field(..., description="Skills are a unit of capability that an agent can perform")
    supports_authenticated_extended_card: Optional[bool] = Field(False, alias="supportsAuthenticatedExtendedCard", description="true if the agent supports providing an extended agent card when the user is authenticated")

    class Config:
        populate_by_name = True


# ============================================================================
# Message and Content Structures
# ============================================================================

class TextPart(BaseModel):
    """Text content part."""
    text: str = Field(..., description="The text content")


class FileWithBytes(BaseModel):
    """File reference with embedded bytes."""
    data: str = Field(..., description="Base64-encoded file data")
    mime_type: str = Field(..., alias="mimeType", description="MIME type of the file")
    filename: Optional[str] = Field(None, description="Optional filename")

    class Config:
        populate_by_name = True


class FileWithUri(BaseModel):
    """File reference with URI."""
    uri: str = Field(..., description="URI where the file can be accessed")
    mime_type: str = Field(..., alias="mimeType", description="MIME type of the file")
    filename: Optional[str] = Field(None, description="Optional filename")

    class Config:
        populate_by_name = True


FilePart = Union[FileWithBytes, FileWithUri]


class DataPart(BaseModel):
    """Structured data part (JSON)."""
    data: Dict[str, Any] = Field(..., description="Structured data (JSON object)")


Part = Union[TextPart, FilePart, DataPart]


class Message(BaseModel):
    """A communication turn between a client and a remote agent."""
    role: MessageRole = Field(..., description="'user' or 'agent'")
    parts: List[Part] = Field(..., description="Content parts of the message")
    message_id: Optional[str] = Field(None, alias="messageId", description="Unique identifier for the message")

    class Config:
        populate_by_name = True


# ============================================================================
# Task Structures
# ============================================================================

class TaskStatus(BaseModel):
    """Current status of a task."""
    state: TaskState = Field(..., description="Current state of the task")
    message: Optional[Message] = Field(None, description="Optional message providing additional context about the status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of this status update")


class Task(BaseModel):
    """
    Represents the stateful unit of work being processed by the A2A Server.
    A task encapsulates the entire interaction related to a specific goal or request.
    """
    id: str = Field(..., description="Unique identifier for the task")
    context_id: str = Field(..., alias="contextId", description="Server-generated id for contextual alignment across interactions")
    status: TaskStatus = Field(..., description="Current status of the task")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Artifacts generated by the agent")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt", description="Timestamp when the task was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt", description="Timestamp when the task was last updated")

    class Config:
        populate_by_name = True


class Artifact(BaseModel):
    """An output generated by the agent as a result of a task."""
    parts: List[Part] = Field(..., description="Content parts of the artifact")
    display_name: Optional[str] = Field(None, alias="displayName", description="Human-readable name for the artifact")
    mime_type: Optional[str] = Field(None, alias="mimeType", description="MIME type of the artifact")

    class Config:
        populate_by_name = True


# ============================================================================
# JSON-RPC 2.0 Structures
# ============================================================================

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 Request."""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name to invoke")
    id: Optional[Union[str, int]] = Field(None, description="Request identifier")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 Response."""
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(None, description="Request identifier (must match request)")
    result: Optional[Any] = Field(None, description="Result of the method call")
    error: Optional[Dict[str, Any]] = Field(None, description="Error object if the call failed")


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 Error."""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")


# ============================================================================
# Method-Specific Structures
# ============================================================================

class MessageSendParams(BaseModel):
    """Parameters for message/send method."""
    task_id: Optional[str] = Field(None, alias="taskId", description="Optional task ID to continue an existing task")
    message: Message = Field(..., description="The message to send")
    push_notification_config: Optional[Dict[str, Any]] = Field(None, alias="pushNotificationConfig", description="Optional push notification configuration")

    class Config:
        populate_by_name = True


class SendStreamingMessageResponse(BaseModel):
    """Response for message/stream method."""
    task: Task = Field(..., description="The task object")


class TaskStatusUpdateEvent(BaseModel):
    """SSE event for task status update."""
    task: Task = Field(..., description="The task with updated status")


class TaskArtifactUpdateEvent(BaseModel):
    """SSE event for task artifact update."""
    task_id: str = Field(..., alias="taskId", description="The task ID")
    artifact: Artifact = Field(..., description="The artifact that was added/updated")

    class Config:
        populate_by_name = True


class TaskQueryParams(BaseModel):
    """Parameters for tasks/get method."""
    task_id: str = Field(..., alias="taskId", description="The task ID to query")

    class Config:
        populate_by_name = True


# ============================================================================
# Push Notification Structures
# ============================================================================

class PushNotificationAuthenticationInfo(BaseModel):
    """Authentication information for push notifications."""
    type: str = Field(..., description="Type of authentication required")
    description: Optional[str] = Field(None, description="Description of the authentication requirement")


class TaskPushNotificationConfig(BaseModel):
    """Push notification configuration for a task."""
    task_id: str = Field(..., alias="taskId", description="The task ID")
    webhook_url: str = Field(..., alias="webhookUrl", description="The webhook URL to send notifications to")
    authentication: Optional[Dict[str, Any]] = Field(None, description="Authentication configuration")

    class Config:
        populate_by_name = True


# ============================================================================
# Agent ID Generation
# ============================================================================

def generate_agent_id(prefix: str = "agent") -> str:
    """
    Generate a unique Agent ID following Google A2A conventions.
    
    Google A2A doesn't specify a strict format for agent IDs, but recommends:
    - Unique identifiers
    - Human-readable when possible
    - Stable across restarts
    
    Args:
        prefix: Optional prefix for the agent ID (default: "agent")
    
    Returns:
        A unique agent ID string
    """
    return f"{prefix}_{uuid4().hex[:16]}"


def generate_task_id() -> str:
    """
    Generate a unique Task ID following Google A2A conventions.
    
    Returns:
        A unique task ID string
    """
    return str(uuid4())


def generate_context_id() -> str:
    """
    Generate a context ID for grouping related tasks.
    
    Returns:
        A unique context ID string
    """
    return str(uuid4())