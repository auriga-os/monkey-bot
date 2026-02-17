"""
Pydantic models for Gateway module.

This module defines request/response models for:
- Google Chat webhook payload (incoming)
- Google Chat response (outgoing)
- Health check response

All models use Pydantic v2 for automatic validation.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class GoogleChatSender(BaseModel):
    """
    Google Chat message sender.

    Represents the user who sent the message. We only care about the email
    for authorization checking. Display name and other metadata are ignored
    for privacy (not sent to LLM).
    """

    email: str = Field(
        ...,
        description="Sender's email address (used for allowlist validation)",
        examples=["user@example.com"],
    )
    display_name: str | None = Field(
        None,
        alias="displayName",
        description="Sender's display name (optional, not used)",
    )

    model_config = {
        "populate_by_name": True,  # Allow both snake_case and camelCase
    }


class GoogleChatMessage(BaseModel):
    """
    Google Chat message structure.

    Represents the core message data from Google Chat webhook.
    """

    sender: GoogleChatSender = Field(
        ...,
        description="Message sender information",
    )
    text: str = Field(
        ...,
        description="Message text content",
        examples=["Remember that I prefer Python"],
    )

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Validate that message text is not empty."""
        if not v or not v.strip():
            raise ValueError("Message text cannot be empty")
        return v


class GoogleChatWebhook(BaseModel):
    """
    Google Chat webhook payload.

    This is the full payload received from Google Chat when a user sends a message.
    We only extract and validate the fields we need (message.sender.email and
    message.text). All other metadata (space, thread, etc.) is ignored for privacy.

    Example payload:
        {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Remember that I prefer Python",
                "space": {"name": "spaces/xxx"},  # ← Ignored
                "thread": {"name": "spaces/xxx/threads/yyy"}  # ← Ignored
            }
        }
    """

    message: GoogleChatMessage = Field(
        ...,
        description="Message content and sender",
    )

    # Note: We intentionally do NOT define space, thread, or other Google Chat
    # metadata fields. Pydantic will accept them in the payload but won't
    # include them in our model. This is a privacy feature - we never pass
    # Google Chat metadata to the LLM.


class GoogleChatResponse(BaseModel):
    """
    Google Chat response (Cards V2 format) - Legacy format.

    This is the legacy response format for Google Chat. The simplest Cards V2
    format is just {"text": "response"}. More complex cards (buttons, images)
    can be added in future phases.

    Google Chat has a 4096 character limit for Cards V2 text.
    Gateway truncates at 4000 to leave room for formatting.
    
    Note: For new deployments, use GoogleChatWorkspaceResponse instead.
    """

    text: str = Field(
        ...,
        description="Response text to display in Google Chat",
        examples=["✅ I'll remember that. Stored: code_language_preference = Python"],
    )

    @field_validator("text")
    @classmethod
    def text_not_too_long(cls, v: str) -> str:
        """
        Validate that response text is not too long for Google Chat.

        Note: Gateway will truncate at 4000 chars before creating this model,
        but we validate here as defense in depth.
        """
        if len(v) > 4000:
            raise ValueError("Response text exceeds 4000 character limit for Google Chat")
        return v


class GoogleChatWorkspaceResponse(BaseModel):
    """
    Google Chat Workspace Add-on response format (modern format).

    This is the modern format required for Google Workspace Add-ons.
    It uses a nested structure for better integration with Workspace apps.

    Example JSON:
        {
            "hostAppDataAction": {
                "chatDataAction": {
                    "createMessageAction": {
                        "message": {"text": "Response text"}
                    }
                }
            }
        }
    """

    class CreateMessageAction(BaseModel):
        """Message creation action."""
        message: dict[str, str] = Field(
            ...,
            description="Message to create",
            examples=[{"text": "Hello from bot"}]
        )

    class ChatDataAction(BaseModel):
        """Chat data action wrapper."""
        createMessageAction: "GoogleChatWorkspaceResponse.CreateMessageAction"

    class HostAppDataAction(BaseModel):
        """Host app data action wrapper."""
        chatDataAction: "GoogleChatWorkspaceResponse.ChatDataAction"

    hostAppDataAction: HostAppDataAction

    @classmethod
    def from_text(cls, text: str) -> "GoogleChatWorkspaceResponse":
        """Convenience constructor from plain text.

        Args:
            text: Response text to send (will be truncated to 4000 chars)

        Returns:
            GoogleChatWorkspaceResponse instance

        Example:
            >>> response = GoogleChatWorkspaceResponse.from_text("Hello!")
            >>> response.hostAppDataAction.chatDataAction.createMessageAction.message
            {"text": "Hello!"}
        """
        # Validate length
        if len(text) > 4000:
            raise ValueError("Response text exceeds 4000 character limit for Google Chat")
        
        return cls(
            hostAppDataAction=cls.HostAppDataAction(
                chatDataAction=cls.ChatDataAction(
                    createMessageAction=cls.CreateMessageAction(
                        message={"text": text}
                    )
                )
            )
        )


class HealthCheckResponse(BaseModel):
    """
    Health check response.

    Used by Cloud Run to determine if the service is healthy.
    Returns 200 OK if healthy, 503 Service Unavailable if unhealthy.
    """

    status: str = Field(
        ...,
        description="Overall health status: 'healthy' or 'unhealthy'",
        examples=["healthy", "unhealthy"],
    )
    timestamp: str = Field(
        ...,
        description="Current timestamp in ISO8601 format",
        examples=["2026-02-11T22:00:00Z"],
    )
    version: str = Field(
        default="1.0.0",
        description="Application version",
    )
    checks: dict[str, str] = Field(
        default_factory=dict,
        description="Component health checks (component_name -> status)",
        examples=[{"agent_core": "ok", "llm": "ok", "gcs": "ok"}],
    )

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        """Validate that status is either 'healthy' or 'unhealthy'."""
        if v not in ("healthy", "unhealthy"):
            raise ValueError("Status must be 'healthy' or 'unhealthy'")
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_valid(cls, v: str) -> str:
        """Validate that timestamp is in ISO8601 format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Timestamp must be in ISO8601 format: {e}") from e
        return v


class CronTickResponse(BaseModel):
    """
    Response from /cron/tick endpoint.
    
    Returns summary metrics about the scheduler tick execution.
    Used by Cloud Scheduler to verify successful execution.
    """
    
    status: str = Field(
        ...,
        description="Execution status: 'success' or 'error'",
        examples=["success", "error"],
    )
    timestamp: str = Field(
        ...,
        description="Tick execution timestamp in ISO8601 format",
        examples=["2026-02-11T22:00:00Z"],
    )
    trace_id: str = Field(
        ...,
        description="Trace ID for this tick execution",
        examples=["abc-123-def-456"],
    )
    metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metrics",
        examples=[{
            "jobs_checked": 10,
            "jobs_due": 2,
            "jobs_executed": 2,
            "jobs_succeeded": 1,
            "jobs_failed": 1,
            "execution_time_ms": 1234
        }],
    )
