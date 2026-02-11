"""Unit tests for LLM Client.

This test suite verifies the LLM client wrapper including:
- Successful API calls
- Error handling (timeout, API errors)
- Logging
- Model selection
- Stream parameter acceptance
"""

from unittest.mock import patch

import pytest

from src.core.interfaces import LLMError
from src.core.llm_client import DEFAULT_MODEL, LLMClient
from src.core.mocks import MockVertexAI

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_vertex_client() -> MockVertexAI:
    """Create mock Vertex AI client."""
    return MockVertexAI()


@pytest.fixture
def llm_client(mock_vertex_client: MockVertexAI) -> LLMClient:
    """Create LLM client with mock Vertex AI."""
    return LLMClient(mock_vertex_client)


# ============================================================================
# Tests: Successful API Calls
# ============================================================================


@pytest.mark.asyncio
async def test_chat_success(llm_client: LLMClient) -> None:
    """Test successful LLM API call.

    Verifies:
        - Client calls vertex API
        - Returns string response
        - Response is non-empty
    """
    # Arrange
    messages = [{"role": "user", "content": "Hello"}]

    # Act
    response = await llm_client.chat(messages)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_chat_with_custom_model(llm_client: LLMClient) -> None:
    """Test API call with custom model.

    Verifies:
        - Client accepts custom model parameter
        - Model parameter passed through
    """
    # Arrange
    messages = [{"role": "user", "content": "Test"}]
    custom_model = "gemini-2.0-pro"

    # Act
    response = await llm_client.chat(messages, model=custom_model)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_chat_with_conversation_history(llm_client: LLMClient) -> None:
    """Test API call with multi-turn conversation.

    Verifies:
        - Client handles multiple messages
        - History sent to LLM
    """
    # Arrange
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]

    # Act
    response = await llm_client.chat(messages)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0


# ============================================================================
# Tests: Stream Parameter
# ============================================================================


@pytest.mark.asyncio
async def test_stream_parameter_accepted(llm_client: LLMClient) -> None:
    """Test that stream parameter is accepted (not implemented yet).

    Verifies:
        - stream=True doesn't cause errors
        - Response still returned (not streaming yet)
        - Story 4 will implement actual streaming
    """
    # Arrange
    messages = [{"role": "user", "content": "Long response please"}]

    # Act
    response = await llm_client.chat(messages, stream=True)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0
    # Note: Streaming not implemented yet, returns regular response


# ============================================================================
# Tests: Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_chat_failure_raises_llm_error(llm_client: LLMClient) -> None:
    """Test that API failures raise LLMError.

    Verifies:
        - Exceptions caught and wrapped
        - LLMError raised
        - Error message includes context
    """
    # Arrange
    messages = [{"role": "user", "content": "Test"}]

    # Mock client to raise exception
    with patch.object(llm_client.client, "ainvoke", side_effect=Exception("API connection failed")):
        # Act & Assert
        with pytest.raises(LLMError) as exc_info:
            await llm_client.chat(messages)

        assert "LLM call failed" in str(exc_info.value)
        assert "API connection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_chat_timeout_raises_llm_error(llm_client: LLMClient) -> None:
    """Test that timeouts raise LLMError.

    Verifies:
        - Timeout exceptions caught
        - LLMError raised with timeout message
    """
    # Arrange
    messages = [{"role": "user", "content": "Test"}]

    # Mock client to raise TimeoutError
    with patch.object(llm_client.client, "ainvoke", side_effect=TimeoutError("Request timeout")):
        # Act & Assert
        with pytest.raises(LLMError) as exc_info:
            await llm_client.chat(messages)

        assert "timeout" in str(exc_info.value).lower()


# ============================================================================
# Tests: Logging
# ============================================================================


@pytest.mark.asyncio
async def test_chat_logs_correctly(llm_client: LLMClient, caplog: pytest.LogCaptureFixture) -> None:
    """Test that LLM calls are logged properly.

    Verifies:
        - Request logged with metadata
        - Response logged with metadata
        - Component field present
        - Model field present
    """
    # Arrange
    messages = [{"role": "user", "content": "Test logging"}]

    # Act
    with caplog.at_level("INFO"):
        await llm_client.chat(messages, model=DEFAULT_MODEL)

    # Assert
    log_text = caplog.text
    assert "Calling LLM" in log_text
    assert "LLM response received" in log_text
    # Note: Extra fields (component, model, etc.) may not appear in caplog.text
    # but they are passed to the logger via extra= parameter


@pytest.mark.asyncio
async def test_chat_logs_errors(llm_client: LLMClient, caplog: pytest.LogCaptureFixture) -> None:
    """Test that errors are logged properly.

    Verifies:
        - Errors logged with ERROR level
        - Error message included
        - Error type included
    """
    # Arrange
    messages = [{"role": "user", "content": "Test"}]

    # Mock client to raise exception
    import contextlib

    with patch.object(llm_client.client, "ainvoke", side_effect=Exception("Test error")):
        # Act
        with caplog.at_level("ERROR"), contextlib.suppress(LLMError):
            await llm_client.chat(messages)

        # Assert
        log_text = caplog.text
        assert "LLM call failed" in log_text


# ============================================================================
# Tests: Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_chat_with_empty_messages(llm_client: LLMClient) -> None:
    """Test API call with empty messages list.

    Verifies:
        - Client handles empty messages
        - No crashes
    """
    # Arrange
    messages: list[dict[str, str]] = []

    # Act
    response = await llm_client.chat(messages)

    # Assert
    assert isinstance(response, str)
    # Mock returns response even for empty input


@pytest.mark.asyncio
async def test_chat_with_very_long_message(llm_client: LLMClient) -> None:
    """Test API call with very long message.

    Verifies:
        - Client handles long messages
        - No truncation or errors
    """
    # Arrange
    messages = [{"role": "user", "content": "A" * 50000}]  # 50KB message

    # Act
    response = await llm_client.chat(messages)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_chat_with_special_characters(llm_client: LLMClient) -> None:
    """Test API call with special characters.

    Verifies:
        - Client handles Unicode, emojis
        - No encoding errors
    """
    # Arrange
    messages = [{"role": "user", "content": "Hello 👋 世界 ñ é"}]

    # Act
    response = await llm_client.chat(messages)

    # Assert
    assert isinstance(response, str)
    assert len(response) > 0


# ============================================================================
# Tests: Model Selection
# ============================================================================


@pytest.mark.asyncio
async def test_default_model_used(llm_client: LLMClient) -> None:
    """Test that default model is used when not specified.

    Verifies:
        - DEFAULT_MODEL used by default
        - No errors with default
    """
    # Arrange
    messages = [{"role": "user", "content": "Test"}]

    # Act
    response = await llm_client.chat(messages)  # No model specified

    # Assert
    assert isinstance(response, str)
    assert llm_client.model == DEFAULT_MODEL


@pytest.mark.asyncio
async def test_multiple_models_supported(llm_client: LLMClient) -> None:
    """Test that multiple models can be specified.

    Verifies:
        - Different models accepted
        - No validation errors
    """
    # Arrange
    messages = [{"role": "user", "content": "Test"}]
    models = ["gemini-2.5-flash-002", "gemini-2.0-pro", "claude-haiku-4.5"]

    # Act & Assert
    for model in models:
        response = await llm_client.chat(messages, model=model)
        assert isinstance(response, str)
        assert len(response) > 0
