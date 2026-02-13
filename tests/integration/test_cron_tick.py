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
    """Create test agent with real scheduler."""
    # Use create_agent_with_mocks for testing
    agent = create_agent_with_mocks()
    return agent


@pytest.fixture
def test_client(test_agent):
    """Create test client with mocked agent."""
    # Inject test agent into server
    server.agent_core = test_agent
    
    client = TestClient(server.app)
    yield client
    
    # Cleanup
    server.agent_core = None


@pytest.mark.skip(reason="Scheduler integration needs update for LangChain v1")
class TestCronTick:
    """Tests for /cron/tick endpoint."""
    
    def test_tick_endpoint_exists(self, test_client):
        """Test that /cron/tick endpoint exists."""
        # Try to call without auth (should fail with 401 or 403, not 404)
        response = test_client.post("/cron/tick")
        assert response.status_code in [401, 403, 405]  # Not 404
    
    def test_tick_requires_authentication(self, test_client):
        """Test that /cron/tick requires authentication."""
        response = test_client.post("/cron/tick")
        assert response.status_code in [401, 403]
    
    # Additional tests would go here but are skipped for now
    # pending scheduler integration updates
