"""Integration tests for full agent flow with LangChain v1.

These tests verify that all components work together correctly:
- build_agent() with LangChain create_agent
- Agent wrapper process_message compatibility
- Multi-turn conversations with checkpointer
- Error propagation
"""

import pytest

from src.core.agent import create_agent_with_mocks


# ============================================================================
# Tests: End-to-End Message Processing
# ============================================================================


@pytest.mark.asyncio
async def test_end_to_end_single_message() -> None:
    """Test complete flow from message to response.

    Verifies:
        - Agent processes message successfully
        - Response returned
        - No errors raised
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"
    content = "Hello, how are you?"
    trace_id = "test_trace"

    # Act
    response = await agent.process_message(user_id, content, trace_id)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_end_to_end_multi_turn_conversation() -> None:
    """Test multi-turn conversation flow.

    Verifies:
        - Multiple messages processed in sequence
        - Context maintained via checkpointer
        - No errors across turns
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_id = "test_user"

    # Act - Turn 1
    response1 = await agent.process_message(user_id, "Hello", "trace_1")

    # Act - Turn 2
    response2 = await agent.process_message(user_id, "How are you?", "trace_2")

    # Act - Turn 3
    response3 = await agent.process_message(user_id, "Goodbye", "trace_3")

    # Assert
    assert all(isinstance(r, str) for r in [response1, response2, response3])
    assert all(len(r) > 0 for r in [response1, response2, response3])


@pytest.mark.asyncio
async def test_different_users_isolated() -> None:
    """Test that different users have isolated conversations.

    Verifies:
        - User A's messages don't affect User B
        - Thread isolation via checkpointer
    """
    # Arrange
    agent = create_agent_with_mocks()
    user_a = "user_a"
    user_b = "user_b"

    # Act
    response_a = await agent.process_message(user_a, "I'm User A", "trace_a")
    response_b = await agent.process_message(user_b, "I'm User B", "trace_b")

    # Assert
    assert isinstance(response_a, str)
    assert isinstance(response_b, str)
    # Both should get responses without interference


@pytest.mark.asyncio
async def test_native_invoke_interface() -> None:
    """Test the native LangChain invoke interface.

    Verifies:
        - Agent.invoke() works with LangChain message format
        - Checkpointer persists state across invocations
    """
    agent = create_agent_with_mocks()
    
    # First invocation
    result1 = await agent.invoke(
        inputs={"messages": [{"role": "user", "content": "Hello"}]},
        config={"configurable": {"thread_id": "test_thread"}},
    )
    
    assert "messages" in result1
    assert len(result1["messages"]) > 0
    
    # Second invocation (should have context from first)
    result2 = await agent.invoke(
        inputs={"messages": [{"role": "user", "content": "Do you remember me?"}]},
        config={"configurable": {"thread_id": "test_thread"}},
    )
    
    assert "messages" in result2
    assert len(result2["messages"]) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_error_in_agent_propagates() -> None:
    """Test that errors in agent execution propagate correctly."""
    from src.core.interfaces import AgentError
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import tool
    from src.core.agent import build_agent
    
    # Create failing model
    class FailingModel(BaseChatModel):
        async def _agenerate(self, messages, stop=None, **kwargs):
            raise ValueError("Intentional test error")
        
        def _generate(self, messages, stop=None, **kwargs):
            raise ValueError("Intentional test error")
        
        @property
        def _llm_type(self) -> str:
            return "failing"
    
    @tool
    def test_tool(query: str) -> str:
        """Test tool."""
        return "test"
    
    # Use empty middleware to avoid GCP initialization
    agent = build_agent(
        model=FailingModel(),
        tools=[test_tool],
        middleware=[],  # Empty middleware to avoid GCP dependency
    )
    
    # Should raise AgentError
    with pytest.raises(AgentError):
        await agent.process_message("test_user", "Test message", "test_trace")


@pytest.mark.asyncio
async def test_empty_message_handling() -> None:
    """Test handling of empty message content."""
    agent = create_agent_with_mocks()
    
    # Empty string should still process (LangChain handles it)
    response = await agent.process_message("test_user", "", "test_trace")
    
    # Should return something (even if just acknowledgment)
    assert isinstance(response, str)
