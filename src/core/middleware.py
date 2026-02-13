"""Custom middleware for monkey-bot agents.

Provides SessionSummaryMiddleware for per-session GCS audit trail.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model
from langgraph.store.base import BaseStore

# Try to import from deepagents first, fall back to langchain
try:
    from deepagents.middleware import AgentMiddleware
except ImportError:
    from langchain.agents.middleware import AgentMiddleware

logger = logging.getLogger(__name__)


class SessionSummaryMiddleware(AgentMiddleware):
    """Writes ONE summary per session to GCS Store for long-term recall.
    
    This middleware:
        - Fires on after_agent hook (once per agent invocation)
        - Accumulates context across invocations within a session
        - Writes a single summary document to the Store when session ends or threshold is reached
        - Does NOT write per-message or per-invocation (avoids GCS spam)
    
    The summary includes:
        - summary: Text summary of the conversation
        - key_topics: List of topics for keyword search
        - message_count: Number of messages in session
        - timestamp: ISO 8601 timestamp
    
    Example:
        >>> from langgraph.store.memory import InMemoryStore
        >>> store = InMemoryStore()
        >>> middleware = SessionSummaryMiddleware(store=store)
        >>> agent = build_agent(model, tools, middleware=[middleware], store=store)
    """
    
    def __init__(
        self,
        store: BaseStore,
        summary_model: Optional[BaseChatModel] = None,
        min_messages_to_summarize: int = 5,
    ):
        """Initialize SessionSummaryMiddleware.
        
        Args:
            store: LangGraph Store for persisting summaries
            summary_model: Model for generating summaries (default: gemini-2.5-flash)
            min_messages_to_summarize: Minimum messages before summarizing
        """
        super().__init__()
        self.store = store
        self.summary_model = summary_model or init_chat_model("gemini-2.5-flash")
        self.min_messages = min_messages_to_summarize
    
    def after_agent(self, state, runtime) -> dict[str, Any] | None:
        """Generate and store session summary after agent completes.
        
        This hook fires once per agent invocation (not per LLM call or tool call).
        We check if the session has enough messages to warrant a summary.
        
        Args:
            state: Agent state with messages
            runtime: Runtime context with config, store access
        
        Returns:
            None (no state updates)
        """
        messages = state.get("messages", [])
        
        # Only summarize if we have enough messages
        if len(messages) < self.min_messages:
            logger.debug(
                f"Skipping summary: only {len(messages)} messages (min: {self.min_messages})",
                extra={"component": "session_summary_middleware"}
            )
            return None
        
        # Extract context from runtime
        config = runtime.config
        thread_id = config.get("configurable", {}).get("thread_id")
        user_id = config.get("configurable", {}).get("user_id", thread_id)
        
        if not thread_id:
            logger.warning(
                "No thread_id in config, skipping session summary",
                extra={"component": "session_summary_middleware"}
            )
            return None
        
        try:
            # Generate session summary
            summary = self._summarize_session(messages)
            key_topics = self._extract_topics(summary)
            
            # Store ONE summary doc per session in the Store
            self.store.put(
                namespace=(user_id, "session_summaries"),
                key=thread_id,
                value={
                    "summary": summary,
                    "key_topics": key_topics,
                    "message_count": len(messages),
                    "timestamp": datetime.utcnow().isoformat(),
                    "last_updated": datetime.utcnow().isoformat(),
                },
            )
            
            logger.info(
                f"Session summary written to Store",
                extra={
                    "component": "session_summary_middleware",
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "message_count": len(messages),
                    "topics": key_topics,
                }
            )
            
        except Exception as e:
            # Don't fail the agent if summary fails
            logger.error(
                f"Failed to generate session summary: {e}",
                extra={
                    "component": "session_summary_middleware",
                    "error": str(e),
                }
            )
        
        return None
    
    def _summarize_session(self, messages: list) -> str:
        """Generate a concise summary of the conversation.
        
        Args:
            messages: List of conversation messages
        
        Returns:
            Summary text
        """
        # Format messages for summarization
        formatted = []
        for msg in messages:
            role = getattr(msg, "role", getattr(msg, "type", "unknown"))
            content = getattr(msg, "content", str(msg))
            formatted.append(f"{role}: {content}")
        
        conversation_text = "\n\n".join(formatted)
        
        # Generate summary using cheap model
        prompt = f"""Summarize the following conversation in 2-3 sentences. Focus on:
- Main topics discussed
- Key decisions or outcomes
- User preferences or facts learned

Conversation:
{conversation_text}

Summary:"""
        
        try:
            response = self.summary_model.invoke([{"role": "user", "content": prompt}])
            summary = response.content if hasattr(response, "content") else str(response)
            return summary.strip()
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            # Fallback: simple truncation
            return f"Conversation with {len(messages)} messages about: " + conversation_text[:200]
    
    def _extract_topics(self, summary: str, max_topics: int = 5) -> list[str]:
        """Extract key topics from summary for keyword search.
        
        Args:
            summary: Summary text
            max_topics: Maximum number of topics to extract
        
        Returns:
            List of topic keywords
        """
        # Simple keyword extraction using LLM
        prompt = f"""Extract up to {max_topics} key topics/keywords from this summary.
Return them as a comma-separated list, lowercase, no extra text.

Summary: {summary}

Keywords:"""
        
        try:
            response = self.summary_model.invoke([{"role": "user", "content": prompt}])
            keywords_text = response.content if hasattr(response, "content") else str(response)
            topics = [t.strip().lower() for t in keywords_text.split(",")]
            return topics[:max_topics]
        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            # Fallback: extract common words
            words = summary.lower().split()
            return list(set([w for w in words if len(w) > 4]))[:max_topics]


# Example of how to use with SummarizationMiddleware
def create_default_middleware_stack(store: Optional[BaseStore] = None) -> list:
    """Create the default middleware stack for monkey-bot agents.
    
    Includes:
        1. SummarizationMiddleware - In-context window management (ephemeral)
        2. SessionSummaryMiddleware - Per-session GCS audit trail (persistent)
    
    Args:
        store: LangGraph Store for long-term memory
    
    Returns:
        List of middleware instances
    """
    from langchain.agents.middleware import SummarizationMiddleware
    
    middleware = [
        # In-context summarization (ephemeral, keeps LLM context small)
        SummarizationMiddleware(
            model="gemini-2.5-flash",
            trigger=("tokens", 4000),
            keep=("messages", 20),
        ),
    ]
    
    # Per-session summarization (persistent to GCS via Store)
    if store is not None:
        middleware.append(
            SessionSummaryMiddleware(
                store=store,
                min_messages_to_summarize=5,
            )
        )
    
    return middleware
