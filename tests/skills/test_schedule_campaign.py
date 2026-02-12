"""Tests for schedule-campaign skill."""

import json
import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "schedule-campaign"))

from schedule_campaign import schedule_campaign


class MockAgentState:
    """Mock agent state for testing."""

    def __init__(self, tmp_path: Path):
        self.memory_dir = tmp_path / "data" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)


class MockScheduler:
    """Mock scheduler for testing."""

    def __init__(self):
        self.scheduled_jobs = []

    async def schedule_job(self, job_type: str, schedule_at: datetime, payload: dict):
        """Mock schedule_job method."""
        job_id = f"job-{len(self.scheduled_jobs) + 1}"
        self.scheduled_jobs.append({
            "id": job_id,
            "job_type": job_type,
            "schedule_at": schedule_at.isoformat(),
            "payload": payload
        })
        return job_id


@pytest.fixture
def mock_agent_state(tmp_path):
    """Create mock agent state."""
    state = MockAgentState(tmp_path)
    state.scheduler = MockScheduler()
    return state


def create_test_campaign(mock_agent_state, campaign_id: str, post_count: int = 4):
    """Create a test campaign for testing."""
    campaign_dir = mock_agent_state.memory_dir / "campaigns" / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)

    post_ideas = [
        {
            "week": 1,
            "platform": "x",
            "scheduled_at": datetime.utcnow().isoformat(),
            "post_number": i + 1,
            "idea": {"angle": f"Test angle {i+1}"},
            "status": "planned"
        }
        for i in range(post_count)
    ]

    plan = {
        "campaign_id": campaign_id,
        "topic": "AI agents",
        "duration_weeks": 2,
        "platforms": ["x"],
        "status": "planned",
        "post_ideas": post_ideas
    }

    (campaign_dir / "plan.json").write_text(json.dumps(plan, indent=2))
    return plan


@pytest.mark.asyncio
async def test_schedule_campaign_success(mock_agent_state):
    """Test: Schedule all posts in a campaign."""
    campaign_id = "test-campaign"
    create_test_campaign(mock_agent_state, campaign_id, post_count=4)

    result = await schedule_campaign(mock_agent_state, campaign_id)

    assert result.success is True
    assert result.data["scheduled_count"] == 4
    assert "first_post_at" in result.data
    assert "last_post_at" in result.data

    # Verify campaign status updated
    plan_path = mock_agent_state.memory_dir / "campaigns" / campaign_id / "plan.json"
    plan = json.loads(plan_path.read_text())
    assert plan["status"] == "scheduled"
    assert "scheduled_jobs" in plan
    assert len(plan["scheduled_jobs"]) == 4


@pytest.mark.asyncio
async def test_schedule_nonexistent_campaign(mock_agent_state):
    """Test: Scheduling non-existent campaign fails."""
    result = await schedule_campaign(mock_agent_state, "invalid-id")

    assert result.success is False
    assert "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_schedule_already_scheduled(mock_agent_state):
    """Test: Scheduling already-scheduled campaign fails."""
    campaign_id = "test-campaign"
    plan = create_test_campaign(mock_agent_state, campaign_id, post_count=2)

    # Schedule once
    result1 = await schedule_campaign(mock_agent_state, campaign_id)
    assert result1.success is True

    # Try to schedule again
    result2 = await schedule_campaign(mock_agent_state, campaign_id)
    assert result2.success is False
    assert "already scheduled" in result2.message.lower()


@pytest.mark.asyncio
async def test_schedule_creates_correct_job_payloads(mock_agent_state):
    """Test: Scheduled jobs have correct payloads."""
    campaign_id = "test-campaign"
    create_test_campaign(mock_agent_state, campaign_id, post_count=3)

    result = await schedule_campaign(mock_agent_state, campaign_id)
    assert result.success is True

    # Check scheduler received correct jobs
    assert len(mock_agent_state.scheduler.scheduled_jobs) == 3

    for job in mock_agent_state.scheduler.scheduled_jobs:
        assert job["job_type"] == "post_content"
        assert "campaign_id" in job["payload"]
        assert "post_number" in job["payload"]
        assert "platform" in job["payload"]
        assert "idea" in job["payload"]
        assert "topic" in job["payload"]


@pytest.mark.asyncio
async def test_schedule_preserves_post_order(mock_agent_state):
    """Test: Posts are scheduled in correct order."""
    campaign_id = "test-campaign"
    create_test_campaign(mock_agent_state, campaign_id, post_count=5)

    result = await schedule_campaign(mock_agent_state, campaign_id)
    assert result.success is True

    # Verify plan has jobs in order
    plan_path = mock_agent_state.memory_dir / "campaigns" / campaign_id / "plan.json"
    plan = json.loads(plan_path.read_text())

    for i, job in enumerate(plan["scheduled_jobs"]):
        assert job["post_number"] == i + 1
