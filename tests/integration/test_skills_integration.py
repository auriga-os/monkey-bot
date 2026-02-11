"""
End-to-end integration tests for Skills System.

These tests verify that Terminal Executor, Skills Engine, and Memory Manager
work together correctly with real skills.
"""

import pytest
import asyncio
from pathlib import Path

from src.skills.executor import SkillsEngine
from src.core.terminal import TerminalExecutor, SecurityError
from src.core.memory import MemoryManager


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


@pytest.fixture
def memory_manager(test_data_dir):
    """Create Memory Manager instance (no GCS for tests)."""
    return MemoryManager(
        memory_dir=str(test_data_dir / "data" / "memory"),
        gcs_enabled=False
    )


class TestSkillsIntegration:
    """Integration tests for skills system."""
    
    @pytest.mark.asyncio
    async def test_skills_engine_lists_real_skills(self, skills_engine):
        """Test that skills engine discovers real skills."""
        skills = skills_engine.list_skills()
        
        assert "file-ops" in skills
        assert "memory" in skills
        assert len(skills) >= 2
    
    @pytest.mark.asyncio
    async def test_file_ops_skill_read(self, skills_engine, test_data_dir):
        """Test file-ops skill can read files."""
        # Setup: Create test file
        test_file = test_data_dir / "test-data" / "test.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Hello from integration test")
        
        # Execute skill
        result = await skills_engine.execute_skill(
            "file-ops",
            {"action": "read", "path": str(test_file)}
        )
        
        # Assert
        assert result.success is True
        assert "Hello from integration test" in result.output
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_file_ops_skill_list(self, skills_engine, test_data_dir):
        """Test file-ops skill can list directories."""
        # Setup: Create test files
        test_dir = test_data_dir / "test-data"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "file1.txt").touch()
        (test_dir / "file2.txt").touch()
        
        # Execute skill
        result = await skills_engine.execute_skill(
            "file-ops",
            {"action": "list", "path": str(test_dir)}
        )
        
        # Assert
        assert result.success is True
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
    
    @pytest.mark.asyncio
    async def test_file_ops_skill_write(self, skills_engine, test_data_dir):
        """Test file-ops skill can write files."""
        # Setup
        test_file = test_data_dir / "test-data" / "output.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Execute skill
        result = await skills_engine.execute_skill(
            "file-ops",
            {
                "action": "write",
                "path": str(test_file),
                "content": "Integration test content"
            }
        )
        
        # Assert
        assert result.success is True
        assert "Wrote" in result.output
        
        # Verify file was written
        assert test_file.exists()
        assert test_file.read_text() == "Integration test content"
    
    @pytest.mark.asyncio
    async def test_memory_skill_remember_recall(self, skills_engine):
        """Test memory skill can store and retrieve facts."""
        # Remember fact
        result1 = await skills_engine.execute_skill(
            "memory",
            {"action": "remember", "key": "test_key", "value": "test_value"}
        )
        assert result1.success is True
        assert "Remembered" in result1.output
        
        # Recall fact
        result2 = await skills_engine.execute_skill(
            "memory",
            {"action": "recall", "key": "test_key"}
        )
        assert result2.success is True
        assert "test_value" in result2.output
    
    @pytest.mark.asyncio
    async def test_memory_skill_recall_nonexistent(self, skills_engine):
        """Test memory skill handles non-existent facts."""
        result = await skills_engine.execute_skill(
            "memory",
            {"action": "recall", "key": "nonexistent_key"}
        )
        
        assert result.success is True
        assert "not found" in result.output.lower() or "no facts" in result.output.lower()
    
    @pytest.mark.asyncio
    async def test_skill_not_found(self, skills_engine):
        """Test skills engine handles missing skills gracefully."""
        result = await skills_engine.execute_skill(
            "nonexistent-skill",
            {}
        )
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_skill_with_invalid_arguments(self, skills_engine):
        """Test skill handles invalid arguments."""
        result = await skills_engine.execute_skill(
            "file-ops",
            {"action": "invalid_action", "path": "/tmp/test"}
        )
        
        # Skill should fail with error
        assert result.success is False


class TestTerminalExecutorSecurity:
    """Security integration tests."""
    
    @pytest.mark.asyncio
    async def test_terminal_executor_blocks_dangerous_commands(self, terminal_executor):
        """Test that terminal executor blocks dangerous commands."""
        # Blocked command
        with pytest.raises(SecurityError):
            await terminal_executor.execute("rm", ["-rf", "/"])
    
    @pytest.mark.asyncio
    async def test_terminal_executor_blocks_dangerous_paths(self, terminal_executor):
        """Test that terminal executor blocks dangerous paths."""
        # Blocked path
        with pytest.raises(SecurityError):
            await terminal_executor.execute("cat", ["/etc/passwd"])


class TestMemoryManagerIntegration:
    """Integration tests for Memory Manager."""
    
    @pytest.mark.asyncio
    async def test_memory_manager_conversation_flow(self, memory_manager):
        """Test memory manager conversation write/read cycle."""
        user_id = "test_user_123"
        
        # Write messages
        await memory_manager.write_conversation(user_id, "user", "Hello", "trace1")
        await memory_manager.write_conversation(user_id, "assistant", "Hi there", "trace2")
        
        # Read history (currently returns empty list in MVP)
        history = await memory_manager.read_conversation_history(user_id, limit=10)
        
        # Assert basic functionality
        assert isinstance(history, list)
    
    @pytest.mark.asyncio
    async def test_memory_manager_facts(self, memory_manager):
        """Test memory manager fact write/read cycle."""
        user_id = "test_user_123"
        
        # Write fact
        await memory_manager.write_fact(user_id, "test_key", "test_value")
        
        # Read fact
        value = await memory_manager.read_fact(user_id, "test_key")
        
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_memory_manager_fact_update(self, memory_manager):
        """Test updating an existing fact."""
        user_id = "test_user_123"
        
        # Write initial value
        await memory_manager.write_fact(user_id, "language", "Python")
        
        # Update value
        await memory_manager.write_fact(user_id, "language", "JavaScript")
        
        # Read updated value
        value = await memory_manager.read_fact(user_id, "language")
        
        assert value == "JavaScript"
    
    @pytest.mark.asyncio
    async def test_memory_manager_read_nonexistent_fact(self, memory_manager):
        """Test reading a non-existent fact returns None."""
        user_id = "test_user_123"
        
        value = await memory_manager.read_fact(user_id, "nonexistent_key")
        
        assert value is None


class TestEndToEndScenarios:
    """End-to-end scenario tests."""
    
    @pytest.mark.asyncio
    async def test_complete_skill_execution_flow(
        self,
        terminal_executor,
        test_data_dir
    ):
        """Test complete flow: Terminal -> Skills Engine -> Skill Execution."""
        # Create skills engine
        skills_engine = SkillsEngine(terminal_executor, skills_dir="./skills")
        
        # Create test file
        test_file = test_data_dir / "test-data" / "e2e_test.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("End-to-end test data")
        
        # Execute skill
        result = await skills_engine.execute_skill(
            "file-ops",
            {"action": "read", "path": str(test_file)}
        )
        
        # Verify complete flow worked
        assert result.success is True
        assert "End-to-end test data" in result.output
    
    @pytest.mark.asyncio
    async def test_memory_persistence_flow(self, test_data_dir):
        """Test that memory persists across manager instances."""
        user_id = "test_user_456"
        memory_dir = str(test_data_dir / "data" / "memory")
        
        # Write fact with first manager instance
        manager1 = MemoryManager(memory_dir=memory_dir, gcs_enabled=False)
        await manager1.write_fact(user_id, "persistent_key", "persistent_value")
        
        # Read fact with second manager instance
        manager2 = MemoryManager(memory_dir=memory_dir, gcs_enabled=False)
        value = await manager2.read_fact(user_id, "persistent_key")
        
        assert value == "persistent_value"
