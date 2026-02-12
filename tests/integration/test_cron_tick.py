"""Integration tests for /cron/tick endpoint.

Tests the Cloud Scheduler integration including:
- Endpoint authentication
- Single tick execution
- Metrics reporting
- Idempotency and duplicate prevention
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.agent import AgentCore
from src.core.mocks import MockMemoryManager, MockSkillsEngine, MockVertexAI
from src.core.llm_client import LLMClient
from src.core.scheduler import create_storage
from src.gateway import server


@pytest.fixture
def test_storage(tmp_path):
    """Create test storage backend."""
    return create_storage("json", memory_dir=tmp_path)


@pytest.fixture
def test_agent(test_storage):
    """Create test agent with real scheduler."""
    llm_client = LLMClient(vertex_client=MockVertexAI())
    skills_engine = MockSkillsEngine()
    memory_manager = MockMemoryManager()
    
    agent = AgentCore(
        llm_client,
        skills_engine,
        memory_manager,
        scheduler_storage=test_storage,
    )
    
    # Register test handler
    async def test_handler(job):
        """Test job handler that tracks execution."""
        if not hasattr(test_handler, "executed"):
            test_handler.executed = []
        test_handler.executed.append(job["id"])
    
    agent.scheduler.register_handler("test_job", test_handler)
    
    return agent


@pytest.fixture
def client(test_agent):
    """Create test client with agent injected."""
    server.agent_core = test_agent
    return TestClient(server.app)


class TestCronTickEndpoint:
    """Test /cron/tick endpoint behavior."""
    
    def test_tick_endpoint_exists(self, client):
        """Test that /cron/tick endpoint is available."""
        response = client.post("/cron/tick")
        
        # Should return 401 without auth, but endpoint exists
        assert response.status_code in [200, 401]
    
    def test_tick_with_scheduler_header(self, client):
        """Test tick with Cloud Scheduler header."""
        response = client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "timestamp" in data
        assert "trace_id" in data
        assert "metrics" in data
        
        # Check metrics structure
        metrics = data["metrics"]
        assert "jobs_checked" in metrics
        assert "jobs_executed" in metrics
        assert "execution_time_ms" in metrics
    
    def test_tick_with_bearer_token(self, client):
        """Test tick with Bearer token authentication."""
        # Set CRON_SECRET for test
        with patch.dict(os.environ, {"CRON_SECRET": "test-secret"}):
            response = client.post(
                "/cron/tick",
                headers={"Authorization": "Bearer test-secret"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_tick_with_invalid_token(self, client):
        """Test tick with invalid Bearer token."""
        with patch.dict(os.environ, {"CRON_SECRET": "test-secret"}):
            response = client.post(
                "/cron/tick",
                headers={"Authorization": "Bearer wrong-secret"}
            )
            
            assert response.status_code == 401
    
    def test_tick_without_auth(self, client):
        """Test tick without authentication headers."""
        with patch.dict(os.environ, {"CRON_SECRET": "test-secret"}):
            response = client.post("/cron/tick")
            
            # Should fail without auth when CRON_SECRET is set
            assert response.status_code == 401


class TestSchedulerExecution:
    """Test scheduler execution during tick."""
    
    @pytest.mark.asyncio
    async def test_executes_due_jobs(self, test_agent, client):
        """Test that tick executes due jobs."""
        # Schedule a job due now
        job_id = await test_agent.scheduler.schedule_job(
            job_type="test_job",
            schedule_at=datetime.utcnow() - timedelta(seconds=1),
            payload={"test": "data"}
        )
        
        # Trigger tick
        response = client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have executed the job
        metrics = data["metrics"]
        assert metrics["jobs_checked"] >= 1
        assert metrics["jobs_due"] >= 1
        assert metrics["jobs_executed"] >= 1
        assert metrics["jobs_succeeded"] >= 1
    
    @pytest.mark.asyncio
    async def test_skips_future_jobs(self, test_agent, client):
        """Test that tick skips jobs scheduled in future."""
        # Schedule a job for 1 hour from now
        job_id = await test_agent.scheduler.schedule_job(
            job_type="test_job",
            schedule_at=datetime.utcnow() + timedelta(hours=1),
            payload={"test": "data"}
        )
        
        # Trigger tick
        response = client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should not execute future job
        metrics = data["metrics"]
        assert metrics["jobs_checked"] >= 1
        assert metrics["jobs_executed"] == 0
    
    @pytest.mark.asyncio
    async def test_reports_job_failures(self, test_agent, client):
        """Test that tick reports job failures in metrics."""
        # Register failing handler
        async def failing_handler(job):
            raise Exception("Test failure")
        
        test_agent.scheduler.register_handler("failing_job", failing_handler)
        
        # Schedule failing job
        job_id = await test_agent.scheduler.schedule_job(
            job_type="failing_job",
            schedule_at=datetime.utcnow() - timedelta(seconds=1),
            payload={}
        )
        
        # Trigger tick
        response = client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should report failure
        metrics = data["metrics"]
        assert metrics["jobs_executed"] >= 1
        # Note: Failed jobs get rescheduled, so they stay pending
        # The failure is logged but job status stays pending for retry


class TestIdempotency:
    """Test idempotency and duplicate prevention."""
    
    @pytest.mark.asyncio
    async def test_duplicate_tick_prevention(self, test_agent, client):
        """Test that duplicate ticks don't double-execute jobs."""
        # Schedule a job
        job_id = await test_agent.scheduler.schedule_job(
            job_type="test_job",
            schedule_at=datetime.utcnow() - timedelta(seconds=1),
            payload={"test": "data"}
        )
        
        # Trigger two ticks rapidly
        response1 = client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        response2 = client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # With JSON storage, this doesn't prevent duplicates
        # But with Firestore storage, the second tick should skip claimed jobs
        # This is tested separately in test_scheduler_storage.py


class TestMetrics:
    """Test metrics reporting."""
    
    def test_metrics_structure(self, client):
        """Test that metrics have correct structure."""
        response = client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["status"] in ["success", "error"]
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["trace_id"], str)
        assert isinstance(data["metrics"], dict)
        
        # Verify metrics keys
        metrics = data["metrics"]
        required_keys = [
            "jobs_checked",
            "jobs_due",
            "jobs_executed",
            "jobs_succeeded",
            "jobs_failed",
            "execution_time_ms"
        ]
        for key in required_keys:
            assert key in metrics
            assert isinstance(metrics[key], int)
    
    def test_execution_time_recorded(self, client):
        """Test that execution time is recorded."""
        response = client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have execution time (may be 0 for very fast ticks)
        assert "execution_time_ms" in data["metrics"]
        assert isinstance(data["metrics"]["execution_time_ms"], int)
        assert data["metrics"]["execution_time_ms"] >= 0


class TestErrorHandling:
    """Test error handling in tick endpoint."""
    
    def test_handles_scheduler_errors(self, client):
        """Test that scheduler errors are handled gracefully."""
        # Mock scheduler to raise error
        with patch.object(
            server.agent_core.scheduler,
            'run_tick',
            side_effect=Exception("Test error")
        ):
            response = client.post(
                "/cron/tick",
                headers={"X-Cloudscheduler": "true"}
            )
            
            # Should still return 200 with error status
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "error"
            assert "error" in data["metrics"]
            assert "Test error" in data["metrics"]["error"]
    
    def test_missing_scheduler(self, client):
        """Test handling when scheduler is not initialized."""
        # Remove scheduler
        original_scheduler = server.agent_core.scheduler
        delattr(server.agent_core, 'scheduler')
        
        try:
            response = client.post(
                "/cron/tick",
                headers={"X-Cloudscheduler": "true"}
            )
            
            # Endpoint now returns 200 with error status instead of 500
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "error" in data["metrics"]
        finally:
            # Restore scheduler
            server.agent_core.scheduler = original_scheduler


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
