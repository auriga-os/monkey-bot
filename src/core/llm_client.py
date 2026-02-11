"""LLM client wrapper for Vertex AI integration.

This module provides a clean abstraction over the Vertex AI LLM API,
handling error cases, logging, and configuration.
"""

import logging
from typing import Any

from .interfaces import LLMError

logger = logging.getLogger(__name__)

# Configuration constants
# These can be overridden via environment variables in production
DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TIMEOUT_SECONDS = 60


class LLMClient:
    """Vertex AI Gemini client wrapper.

    Provides a clean interface to the LLM with proper error handling,
    logging, and configuration management.

    For Sprint 1: Uses MockVertexAI (passed via constructor).
    For Story 4: Uses real ChatVertexAI from langchain-google-vertexai.

    Key responsibilities:
        - Call LLM with conversation context
        - Handle errors gracefully (timeouts, rate limits, etc.)
        - Log all LLM interactions for debugging
        - Support multiple models (Flash, Pro, Haiku)

    Example:
        >>> from src.core.mocks import MockVertexAI
        >>> vertex_client = MockVertexAI()
        >>> llm = LLMClient(vertex_client)
        >>> response = await llm.chat(
        ...     messages=[{"role": "user", "content": "Hello"}],
        ...     model="gemini-2.5-flash-002"
        ... )
        >>> print(response)
        "Hello! I'm Emonk, your AI assistant..."
    """

    def __init__(self, vertex_client: Any) -> None:
        """Initialize LLM client.

        Args:
            vertex_client: MockVertexAI for Sprint 1 testing
                          (Real ChatVertexAI added in Story 4)
        """
        self.client = vertex_client
        self.model = DEFAULT_MODEL

    async def chat(
        self, messages: list[dict[str, str]], model: str = DEFAULT_MODEL, stream: bool = False
    ) -> str:
        """Call LLM with conversation context.

        This is the main entry point for all LLM interactions. It handles
        error cases, logging, and response formatting.

        Args:
            messages: Conversation history [{"role": "user", "content": "..."}]
                     Messages should be in chronological order (oldest first).
            model: Model identifier (default: "gemini-2.5-flash-002")
                  Supported models:
                  - "gemini-2.5-flash-002" (fast, cheap, default)
                  - "gemini-2.0-pro" (slower, more capable)
                  - "claude-haiku-4.5" (future support)
            stream: Enable streaming for long responses (Story 4 - defer implementation)
                   When True, responses > 200 tokens are streamed for better UX.
                   Currently accepted but not implemented (Story 4).

        Returns:
            LLM response text

        Raises:
            LLMError: If API call fails after retries
                     Possible causes:
                     - Timeout (60s)
                     - Rate limit (429)
                     - Service unavailable (503)
                     - Invalid credentials

        Note:
            Streaming is deferred to Story 4. Set stream=True but don't implement yet.
            Story 4 will add real streaming support for responses > 200 tokens using
            astream() instead of ainvoke().

        Story 4 Integration:
            - Add retry logic (3x exponential backoff) for 429 and 503 errors
            - Add timeout handling (60s default)
            - Implement streaming with astream() for responses > 200 tokens
            - Add token counting and cost tracking
        """
        logger.info(
            "Calling LLM",
            extra={
                "component": "llm_client",
                "model": model,
                "message_count": len(messages),
                "stream": stream,
                "last_role": messages[-1]["role"] if messages else None,
            },
        )

        try:
            # For Sprint 1: Use MockVertexAI (simple mock that returns string)
            # Story 4: Replace with real ChatVertexAI with retry logic (3x exponential backoff)
            #
            # Example Story 4 implementation:
            # from tenacity import retry, stop_after_attempt, wait_exponential
            # @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
            # async def call_with_retry():
            #     return await self.client.ainvoke(messages)
            # response = await call_with_retry()

            response_obj = await self.client.ainvoke(messages)
            
            # Extract text from response (ChatVertexAI returns AIMessage with .content)
            if hasattr(response_obj, "content"):
                response: str = response_obj.content
            else:
                # Fallback for simple string responses (mocks)
                response: str = str(response_obj)

            logger.info(
                "LLM response received",
                extra={
                    "component": "llm_client",
                    "model": model,
                    "response_length": len(response),
                },
            )

            return response

        except TimeoutError as e:
            error_msg = f"LLM call timeout after {DEFAULT_TIMEOUT_SECONDS}s: {e}"
            logger.error(
                error_msg,
                extra={"component": "llm_client", "model": model, "error_type": "timeout"},
            )
            raise LLMError(error_msg) from e

        except Exception as e:
            # Catch all other errors (API errors, network errors, etc.)
            error_msg = f"LLM call failed: {e}"
            logger.error(
                error_msg,
                extra={
                    "component": "llm_client",
                    "model": model,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            raise LLMError(error_msg) from e
