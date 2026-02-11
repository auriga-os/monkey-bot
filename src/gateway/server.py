"""
FastAPI server for Gateway module.

This module implements the HTTP interface for Emonk:
- POST /webhook: Handle Google Chat messages
- GET /health: Health check for Cloud Run

Security layers:
1. Allowlist validation (ALLOWED_USERS env var)
2. PII filtering (hash emails, strip metadata)
3. Agent Core processing (LLM + skills)
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.gateway.interfaces import AgentCoreInterface, AgentError
from src.gateway.models import GoogleChatResponse, GoogleChatWebhook, HealthCheckResponse
from src.gateway.mocks import MockAgentCore
from src.gateway.pii_filter import filter_google_chat_pii

# Configure structured JSON logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(message)s")
logger = logging.getLogger(__name__)


def log_structured(level: str, message: str, **extra: str | int) -> None:
    """
    Log structured JSON for Cloud Logging.

    Args:
        level: Log level (INFO, WARNING, ERROR, etc.)
        message: Log message
        **extra: Additional fields to include in log entry
    """
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": level,
        "message": message,
        "component": "gateway",
        **extra,
    }
    getattr(logger, level.lower())(json.dumps(log_entry))


# Create FastAPI application
app = FastAPI(
    title="Emonk Gateway",
    version="1.0.0",
    description="HTTP interface for Emonk AI agent framework",
)

# For Sprint 1: Use mock Agent Core
# Story 4 (Integration) will wire real Agent Core implementation
agent_core: AgentCoreInterface = MockAgentCore()


def truncate_response(text: str, max_length: int = 4000) -> str:
    """
    Truncate response text for Google Chat.

    Google Chat has a 4096 character limit for Cards V2 text.
    We truncate at 4000 to leave room for formatting.

    Args:
        text: Response text from Agent Core
        max_length: Maximum length (default 4000)

    Returns:
        Truncated text if needed, original text otherwise
    """
    if len(text) <= max_length:
        return text

    # Truncation message length: "\n\n... (response truncated)" = 28 chars
    truncation_message = "\n\n... (response truncated)"
    truncate_at = max_length - len(truncation_message)

    return text[:truncate_at] + truncation_message


@app.post("/webhook", response_model=GoogleChatResponse, status_code=status.HTTP_200_OK)
async def webhook(payload: GoogleChatWebhook) -> GoogleChatResponse:
    """
    Handle Google Chat webhook.

    Process flow:
    1. Validate sender email against ALLOWED_USERS allowlist
    2. Filter PII (hash email to user_id, strip Google Chat metadata)
    3. Generate trace_id for request tracking
    4. Call Agent Core to process message
    5. Truncate response if needed (Google Chat limit: 4000 chars)
    6. Format response for Google Chat Cards V2

    Args:
        payload: Google Chat webhook payload (validated by Pydantic)

    Returns:
        GoogleChatResponse with agent's response text

    Raises:
        HTTPException(401): If sender email not in ALLOWED_USERS
        HTTPException(500): If Agent Core processing fails
    """
    trace_id = str(uuid.uuid4())

    # Log incoming webhook (before PII filtering, so we have email for debugging)
    log_structured(
        "INFO",
        "Webhook received",
        trace_id=trace_id,
        sender=payload.message.sender.email,
    )

    # Security Layer 1: Allowlist validation
    # Check sender email against ALLOWED_USERS env var
    allowed_users_str = os.getenv("ALLOWED_USERS", "")
    if not allowed_users_str:
        log_structured(
            "ERROR",
            "ALLOWED_USERS env var not set",
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: ALLOWED_USERS not set",
        )

    allowed_users = [email.strip() for email in allowed_users_str.split(",")]
    if payload.message.sender.email not in allowed_users:
        log_structured(
            "WARNING",
            "Unauthorized user attempted access",
            trace_id=trace_id,
            sender=payload.message.sender.email,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized user",
        )

    # Security Layer 2: PII filtering
    # Hash email to user_id, strip all Google Chat metadata
    filtered = filter_google_chat_pii(payload.model_dump())

    log_structured(
        "INFO",
        "PII filtered",
        trace_id=trace_id,
        user_id=filtered["user_id"],
        content_length=len(filtered["content"]),
    )

    # Call Agent Core to process message
    try:
        response_text = await agent_core.process_message(
            user_id=filtered["user_id"],
            content=filtered["content"],
            trace_id=trace_id,
        )
    except AgentError as e:
        log_structured(
            "ERROR",
            f"Agent Core processing failed: {e.message}",
            trace_id=trace_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent processing failed",
        ) from e
    except Exception as e:
        log_structured(
            "ERROR",
            f"Unexpected error during Agent Core processing: {str(e)}",
            trace_id=trace_id,
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e

    # Truncate response if needed (Google Chat limit: 4000 chars)
    response_text = truncate_response(response_text)

    log_structured(
        "INFO",
        "Webhook processed successfully",
        trace_id=trace_id,
        response_length=len(response_text),
    )

    # Return response in Google Chat Cards V2 format
    return GoogleChatResponse(text=response_text)


@app.get("/health", response_model=HealthCheckResponse)
async def health() -> HealthCheckResponse:
    """
    Health check endpoint for Cloud Run.

    Cloud Run pings this endpoint every 30 seconds to verify service health.
    Returns 200 OK if healthy, 503 Service Unavailable if unhealthy.

    For Sprint 1 (with MockAgentCore):
        - Always returns healthy (mock never fails)

    For Story 4+ (with real Agent Core):
        - Check Agent Core availability
        - Check LLM connectivity
        - Check GCS availability
        - Return unhealthy if any component down

    Returns:
        HealthCheckResponse with status and component checks
    """
    # For Sprint 1: MockAgentCore is always available
    # Story 4 will add real health checks for Agent Core, LLM, GCS
    checks = {"agent_core": "ok"}

    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=checks,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Logs the error with trace context and returns a generic error response
    to avoid leaking internal details to users.

    Args:
        request: FastAPI request object
        exc: Unhandled exception

    Returns:
        JSONResponse with error details
    """
    trace_id = str(uuid.uuid4())

    log_structured(
        "ERROR",
        f"Unhandled exception: {str(exc)}",
        trace_id=trace_id,
        error_type=type(exc).__name__,
        path=str(request.url),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "trace_id": trace_id,
        },
    )
