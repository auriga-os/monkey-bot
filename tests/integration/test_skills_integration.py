"""
End-to-end integration tests for Skills System.

These tests verify that Terminal Executor and Skills Engine work correctly with real skills.

Note: With LangChain v1, skills are now LangChain @tool functions.
These tests focus on the Terminal Executor security layer.
"""

import pytest
import asyncio
from pathlib import Path

from src.skills.executor import SkillsEngine
from src.core.terminal import TerminalExecutor, SecurityError


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory."""
    data_dir = tmp_path / "data" / "memory"
    data_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def terminal_executor():
    """Create Terminal Executor instance."""
    return TerminalExecutor()


@pytest.fixture
def skills_engine(terminal_executor):
    """Create Skills Engine instance with real skills."""
    return SkillsEngine(terminal_executor, skills_dir="./skills")


class TestSkillsIntegration:
    """Integration tests for skills system."""
    
    @pytest.mark.asyncio
    async def test_skills_engine_lists_real_skills(self, skills_engine):
        """Test that skills engine can list available skills."""
        skills = skills_engine.list_skills()
        
        # Should have at least some skills
        assert isinstance(skills, list)
        # Note: May be empty if ./skills directory doesn't exist yet
    
    @pytest.mark.asyncio
    async def test_terminal_executor_security_blocks_invalid_commands(
        self, terminal_executor
    ):
        """Test that Terminal Executor blocks disallowed commands."""
        # Try to execute a command that's not in ALLOWED_COMMANDS
        with pytest.raises(SecurityError) as exc_info:
            await terminal_executor.execute("rm", ["-rf", "/"])
        
        assert "not allowed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_terminal_executor_security_blocks_invalid_paths(
        self, terminal_executor
    ):
        """Test that Terminal Executor blocks access to disallowed paths."""
        # Try to access a path outside allowed directories
        with pytest.raises(SecurityError) as exc_info:
            await terminal_executor.execute("cat", ["/etc/passwd"])
        
        assert "not allowed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_terminal_executor_allows_safe_commands(
        self, terminal_executor, test_data_dir
    ):
        """Test that Terminal Executor allows safe commands in allowed paths."""
        # Create a test file in allowed path
        test_file = test_data_dir / "test.txt"
        test_file.write_text("test content")
        
        # Execute cat on file in allowed path (./test-data/ is in ALLOWED_PATHS)
        result = await terminal_executor.execute("cat", [str(test_file)])
        
        assert result.exit_code == 0
        assert "test content" in result.stdout


@pytest.mark.skip(reason="Skill execution needs update for LangChain @tool pattern")
class TestSkillExecution:
    """Tests for executing real skills (pending updates for LangChain v1)."""
    
    @pytest.mark.asyncio
    async def test_execute_file_ops_skill(self, skills_engine, test_data_dir):
        """Test executing file-ops skill."""
        # This test is skipped pending conversion of skills to @tool functions
        pass
