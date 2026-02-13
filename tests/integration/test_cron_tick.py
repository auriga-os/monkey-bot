"""Integration tests for /cron/tick endpoint.

Tests the Cloud Scheduler integration including:
- Endpoint authentication
- Single tick execution
- Metrics reporting
- Idempotency and duplicate prevention

Note: These tests require updates for LangChain v1 architecture.
Currently skipped pending scheduler integration updates.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.agent import create_agent_with_mocks
from src.core.scheduler import create_storage
from src.gateway import server


@pytest.fixture
def test_storage(tmp_path):
    """Create test storage backend."""
    return create_storage("json", memory_dir=tmp_path)


@pytest.fixture
def test_agent(test_storage):
    """Create test agent with mock scheduler."""
    # Use MockAgentCore which has a scheduler attribute
    from src.gateway.mocks import MockAgentCore
    return MockAgentCore()


@pytest.fixture
def test_client(test_agent):
    """Create test client with mocked agent."""
    # Save original agent_core
    original_agent_core = server.agent_core
    
    # Inject test agent into server
    server.agent_core = test_agent
    
    client = TestClient(server.app)
    yield client
    
    # Cleanup - restore original
    server.agent_core = original_agent_core


class TestCronTick:
    """Tests for /cron/tick endpoint."""
    
    def test_tick_endpoint_exists(self, test_client, monkeypatch):
        """Test that /cron/tick endpoint exists."""
        # Clear any CRON_SECRET env var for this test
        monkeypatch.delenv("CRON_SECRET", raising=False)
        
        # Call endpoint without auth - should succeed (200) when no secret is set
        # or accept X-Cloudscheduler header
        response = test_client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        assert response.status_code == 200
        
        # Verify response structure
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "trace_id" in data
        assert "metrics" in data
    
    def test_tick_requires_authentication(self, test_client, monkeypatch):
        """Test that /cron/tick requires authentication when CRON_SECRET is set."""
        # Set CRON_SECRET to enable authentication
        monkeypatch.setenv("CRON_SECRET", "test-secret-123")
        
        # Call without auth - should fail with 401
        response = test_client.post("/cron/tick")
        assert response.status_code == 401
        
        # Call with wrong auth - should fail with 401
        response = test_client.post(
            "/cron/tick",
            headers={"Authorization": "Bearer wrong-secret"}
        )
        assert response.status_code == 401
        
        # Call with correct auth - should succeed
        response = test_client.post(
            "/cron/tick",
            headers={"Authorization": "Bearer test-secret-123"}
        )
        assert response.status_code == 200
        
        # Call with X-Cloudscheduler header - should also succeed
        response = test_client.post(
            "/cron/tick",
            headers={"X-Cloudscheduler": "true"}
        )
        assert response.status_code == 200
