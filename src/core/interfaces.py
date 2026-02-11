"""
Shared interfaces for Emonk components.

This module defines all shared interfaces used across the Emonk agent framework.
Story 2 owns this file, but Story 3 uses these interfaces for implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class Message:
    """Conversation message."""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str
    trace_id: str


@dataclass
class SkillResult:
    """Result from skill execution."""
    success: bool
    output: str
    error: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result from terminal command execution."""
    stdout: str
    stderr: str
    exit_code: int


class SkillsEngineInterface(ABC):
    """Contract for Skills Engine."""
    
    @abstractmethod
    async def execute_skill(
        self, 
        skill_name: str, 
        args: Dict[str, Any]
    ) -> SkillResult:
        """
        Execute a skill by name with arguments.
        
        Args:
            skill_name: Skill identifier from SKILL.md
            args: Skill arguments from LLM tool call
            
        Returns:
            SkillResult with success status and output
            
        Raises:
            SkillError: If skill not found or execution fails
        """
        pass
    
    @abstractmethod
    def list_skills(self) -> List[str]:
        """Return list of available skill names."""
        pass


class MemoryManagerInterface(ABC):
    """Contract for Memory Manager."""
    
    @abstractmethod
    async def read_conversation_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Message]:
        """
        Read recent conversation history.
        
        Args:
            user_id: Hashed user identifier
            limit: Max messages to return (default 10)
            
        Returns:
            List of recent messages (oldest first)
        """
        pass
    
    @abstractmethod
    async def write_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
        trace_id: str
    ):
        """
        Write a conversation message.
        
        Args:
            user_id: Hashed user identifier
            role: "user" or "assistant"
            content: Message content
            trace_id: Request trace ID
        """
        pass
    
    @abstractmethod
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        """Read a fact from knowledge base."""
        pass
    
    @abstractmethod
    async def write_fact(self, user_id: str, key: str, value: str):
        """Write a fact to knowledge base."""
        pass


class AgentCoreInterface(ABC):
    """Contract that Gateway will call."""
    
    @abstractmethod
    async def process_message(
        self, 
        user_id: str, 
        content: str, 
        trace_id: str
    ) -> str:
        """Process user message and return response."""
        pass
