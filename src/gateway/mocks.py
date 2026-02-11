"""
Mock implementations for Gateway testing.

This module provides mock implementations that enable Sprint 1 parallel development:
- MockAgentCore: Simple echo implementation for Gateway testing

Real implementations will be wired in Story 4 (Integration).
"""

from __future__ import annotations

import src.gateway.interfaces as interfaces


class MockAgentCore(interfaces.AgentCoreInterface):  # type: ignore[misc]
    """
    Mock Agent Core for Gateway testing.

    This mock implementation enables Story 1 (Gateway) to be developed and tested
    independently in Sprint 1, without waiting for Story 2 (Agent Core) to complete.

    Behavior:
        - Returns simple echo response with trace_id
        - Never raises AgentError (always succeeds)
        - Useful for testing Gateway's request/response handling

    Real Agent Core (Story 2) will:
        - Load conversation history from Memory Manager
        - Call LLM with context
        - Execute skills via Skills Engine
        - Save conversation history
        - Return contextual responses

    Story 4 (Integration) will replace this mock with real Agent Core.

    Example:
        >>> mock = MockAgentCore()
        >>> response = await mock.process_message(
        ...     user_id="a1b2c3d4e5f6g7h8",
        ...     content="Hello",
        ...     trace_id="550e8400-e29b-41d4-a716-446655440000"
        ... )
        >>> print(response)
        'Echo: Hello (trace: 550e8400-e29b-41d4-a716-446655440000)'
    """

    async def process_message(self, user_id: str, content: str, trace_id: str) -> str:
        """
        Return simple echo response for testing.

        Args:
            user_id: Hashed user identifier (not used by mock)
            content: Message text (echoed back)
            trace_id: Request trace ID (included in response)

        Returns:
            Echo response with content and trace_id
        """
        return f"Echo: {content} (trace: {trace_id})"
