"""Unit tests for Agent (LangChain v1).

This test suite verifies the modernized agent using create_agent:
- Agent wrapper compatibility with Gateway interface
- Agent invocation with LangChain tools
- Mock agent creation for testing
- Error handling
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.core.agent import build_agent, create_agent_with_mocks, AgentWrapper
from src.core.interfaces import AgentError


# ============================================================================
# Tests for create_agent_with_mocks (compatibility function)
# ============================================================================


@pytest.mark.asyncio
async def test_create_agent_with_mocks():
    """Test that create_agent_with_mocks creates a functional agent."""
    agent = create_agent_with_mocks()
    
    assert isinstance(agent, AgentWrapper)
    assert agent.graph is not None
    assert agent.scheduler is not None


@pytest.mark.asyncio
async def test_process_message_compatibility():
    """Test process_message method (legacy interface for Gateway compatibility)."""
    agent = create_agent_with_mocks()
    
    response = await agent.process_message(
        user_id="test_user",
        content="Hello, how are you?",
        trace_id="test_trace_123",
    )
    
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_process_message_with_different_content():
    """Test that process_message handles different content."""
    agent = create_agent_with_mocks()
    
    # Test with a different message
    response = await agent.process_message(
        user_id="user456",
        content="What can you help me with?",
        trace_id="trace_456",
    )
    
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_invoke_method():
    """Test the native invoke method."""
    agent = create_agent_with_mocks()
    
    result = await agent.invoke(
        inputs={"messages": [{"role": "user", "content": "Hello"}]},
        config={"configurable": {"thread_id": "test_thread"}},
    )
    
    assert "messages" in result
    assert len(result["messages"]) > 0


# ============================================================================
# Scheduler Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scheduler_start_stop():
    """Test scheduler start and stop methods."""
    agent = create_agent_with_mocks()
    
    # Start scheduler
    await agent.start_scheduler()
    assert agent._scheduler_task is not None
    
    # Stop scheduler
    await agent.stop_scheduler()
    assert agent._scheduler_task is None


@pytest.mark.asyncio
async def test_scheduler_already_running():
    """Test that starting scheduler twice doesn't create multiple tasks."""
    agent = create_agent_with_mocks()
    
    await agent.start_scheduler()
    first_task = agent._scheduler_task
    
    # Try to start again
    await agent.start_scheduler()
    second_task = agent._scheduler_task
    
    # Should be the same task
    assert first_task == second_task
    
    # Cleanup
    await agent.stop_scheduler()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_message_error_handling():
    """Test that errors are properly wrapped in AgentError."""
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import tool
    
    # Create a model that raises an exception
    class FailingModel(BaseChatModel):
        def _generate(self, messages, stop=None, **kwargs):
            raise Exception("Test error")
        
        async def _agenerate(self, messages, stop=None, **kwargs):
            raise Exception("Test error")
        
        @property
        def _llm_type(self) -> str:
            return "failing"
    
    @tool
    def mock_tool(query: str) -> str:
        """Mock tool."""
        return "mock"
    
    agent = build_agent(
        model=FailingModel(),
        tools=[mock_tool],
        user_system_prompt="",
    )
    
    with pytest.raises(AgentError) as exc_info:
        await agent.process_message(
            user_id="test",
            content="Test",
            trace_id="test",
        )
    
    assert "Message processing failed" in str(exc_info.value)


# ============================================================================
# Integration Tests with Real Components
# ============================================================================


@pytest.mark.asyncio
async def test_build_agent_with_custom_prompt():
    """Test building agent with custom system prompt."""
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import tool
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    
    class TestModel(BaseChatModel):
        def _generate(self, messages, stop=None, **kwargs):
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Test response"))])
        
        async def _agenerate(self, messages, stop=None, **kwargs):
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Test response"))])
        
        @property
        def _llm_type(self) -> str:
            return "test"
    
    @tool
    def search_tool(query: str) -> str:
        """Search for information."""
        return f"Results for: {query}"
    
    agent = build_agent(
        model=TestModel(),
        tools=[search_tool],
        user_system_prompt="You are a helpful marketing assistant.",
    )
    
    assert isinstance(agent, AgentWrapper)
    assert agent.graph is not None


@pytest.mark.asyncio
async def test_stream_method():
    """Test that stream method works."""
    agent = create_agent_with_mocks()
    
    chunks = []
    async for chunk in agent.stream(
        inputs={"messages": [{"role": "user", "content": "Hello"}]},
        config={"configurable": {"thread_id": "test_thread"}},
    ):
        chunks.append(chunk)
    
    # Should have received at least one chunk
    assert len(chunks) > 0


# ============================================================================
# Legacy Interface Tests
# ============================================================================


@pytest.mark.asyncio
async def test_multiple_messages_same_thread():
    """Test multiple messages in the same conversation thread."""
    agent = create_agent_with_mocks()
    
    # First message
    response1 = await agent.process_message(
        user_id="user123",
        content="Hello",
        trace_id="trace1",
    )
    
    # Second message in same thread
    response2 = await agent.process_message(
        user_id="user123",
        content="How are you?",
        trace_id="trace2",
    )
    
    assert isinstance(response1, str)
    assert isinstance(response2, str)
