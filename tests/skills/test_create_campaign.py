"""Tests for create-campaign skill."""

import json
import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "create-campaign"))

from create_campaign import (
    create_campaign,
    _research_topic,
    _define_strategy,
    _generate_calendar,
    _create_post_ideas,
)


class MockAgentState:
    """Mock agent state for testing."""

    def __init__(self, tmp_path: Path):
        self.memory_dir = tmp_path / "data" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def mock_agent_state(tmp_path):
    """Create mock agent state."""
    return MockAgentState(tmp_path)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    class MockLLM:
        async def generate(self, prompt: str) -> object:
            """Mock generate method."""
            class Response:
                text = json.dumps({
                    "goal": "Test goal",
                    "target_audience": "Test audience",
                    "key_messages": ["Message 1", "Message 2"],
                    "content_pillars": ["Pillar 1", "Pillar 2", "Pillar 3"],
                    "success_metrics": ["Metric 1", "Metric 2"]
                })
            return Response()
    return MockLLM()


@pytest.mark.asyncio
async def test_research_topic_placeholder(monkeypatch):
    """Test: Topic research returns mock data."""
    mock_state = type('obj', (object,), {'memory_dir': Path('.')})()
    
    # Mock search_web
    class MockSearchResult:
        success = True
        data = {
            "results": [
                {"title": "Result 1", "snippet": "Snippet 1"},
                {"title": "Result 2", "snippet": "Snippet 2"},
                {"title": "Result 3", "snippet": "Snippet 3"},
                {"title": "Result 4", "snippet": "Snippet 4"},
                {"title": "Result 5", "snippet": "Snippet 5"},
            ]
        }
    
    async def mock_search_web(agent_state, topic, limit, recency):
        return MockSearchResult()
    
    # Patch the import at the module level
    import sys
    mock_module = type(sys)('search_web')
    mock_module.search_web = mock_search_web
    sys.modules['search_web'] = mock_module
    
    result = await _research_topic(mock_state, "AI agents")
    
    assert "topic" in result
    assert result["topic"] == "AI agents"
    assert "search_results" in result
    assert "insights" in result
    assert len(result["insights"]) == 5


@pytest.mark.asyncio
async def test_define_strategy(mock_agent_state, mock_llm_client, monkeypatch):
    """Test: Strategy definition using LLM."""
    # Mock agent state to have llm_client
    mock_agent_state.llm_client = mock_llm_client
    
    research = {
        "topic": "AI agents",
        "insights": [{"title": "Insight 1"}]
    }
    
    strategy = await _define_strategy(mock_agent_state, "AI agents", 4, research)
    
    assert "goal" in strategy
    assert "target_audience" in strategy
    assert "key_messages" in strategy
    assert "content_pillars" in strategy
    assert len(strategy["content_pillars"]) >= 3


@pytest.mark.asyncio
async def test_generate_calendar():
    """Test: Calendar generation creates correct number of posts."""
    mock_state = type('obj', (object,), {'memory_dir': Path('.')})()
    
    calendar = await _generate_calendar(mock_state, 4, ["instagram", "x"])
    
    # 4 weeks * 2 platforms * 2 posts per platform per week = 16 posts
    assert len(calendar) == 16
    assert all(entry["platform"] in ["instagram", "x"] for entry in calendar)
    assert all("scheduled_at" in entry for entry in calendar)
    assert all("week" in entry for entry in calendar)


@pytest.mark.asyncio
async def test_create_post_ideas(mock_agent_state, mock_llm_client):
    """Test: Post ideas generation."""
    mock_agent_state.llm_client = mock_llm_client
    
    # Mock LLM to return post ideas array
    async def mock_generate(prompt):
        class Response:
            text = json.dumps([
                {"angle": "Test angle", "message": "Test message"},
                {"angle": "Test angle 2", "message": "Test message 2"}
            ])
        return Response()
    
    mock_agent_state.llm_client.generate = mock_generate
    
    strategy = {"content_pillars": ["Education", "Tips"]}
    calendar = [
        {"week": 1, "platform": "x", "scheduled_at": "2026-02-15T10:00:00"},
        {"week": 1, "platform": "x", "scheduled_at": "2026-02-18T10:00:00"}
    ]
    
    post_ideas = await _create_post_ideas(mock_agent_state, "AI", strategy, calendar)
    
    assert len(post_ideas) == len(calendar)
    assert all("idea" in post for post in post_ideas)
    assert all("status" in post for post in post_ideas)
    assert all(post["status"] == "planned" for post in post_ideas)


@pytest.mark.asyncio
async def test_create_campaign_full_flow(mock_agent_state, mock_llm_client, monkeypatch):
    """Test: Full campaign creation flow."""
    mock_agent_state.llm_client = mock_llm_client
    
    # Mock search_web
    class MockSearchResult:
        success = True
        data = {
            "results": [
                {"title": "Result 1", "snippet": "Snippet 1"},
                {"title": "Result 2", "snippet": "Snippet 2"}
            ]
        }
    
    async def mock_search_web(agent_state, topic, limit, recency):
        return MockSearchResult()
    
    # Monkeypatch the import
    import sys
    mock_module = type(sys)('skills.search_web')
    mock_module.search_web = mock_search_web
    sys.modules['skills.search_web'] = mock_module
    
    # Mock LLM for post ideas (array response)
    call_count = [0]
    
    async def mock_generate_conditional(prompt):
        call_count[0] += 1
        class Response:
            if call_count[0] == 2:  # Second call is for post ideas
                text = json.dumps([
                    {"angle": "Test", "message": "Test"} for _ in range(8)
                ])
            else:
                text = json.dumps({
                    "goal": "Test goal",
                    "target_audience": "Test audience",
                    "key_messages": ["Message 1"],
                    "content_pillars": ["Pillar 1", "Pillar 2"],
                    "success_metrics": ["Metric 1"]
                })
        return Response()
    
    mock_agent_state.llm_client.generate = mock_generate_conditional
    
    result = await create_campaign(
        mock_agent_state,
        topic="AI agents",
        duration_weeks=2,
        platforms=["instagram", "x"]
    )
    
    assert result.success is True
    assert "campaign_id" in result.data
    assert result.data["post_count"] == 8  # 2 weeks * 2 platforms * 2 posts/week
    
    # Verify files created
    campaign_dir = Path(result.data["campaign_dir"])
    assert (campaign_dir / "plan.json").exists()
    assert (campaign_dir / "research.json").exists()
    assert (campaign_dir / "strategy.json").exists()
    assert (campaign_dir / "calendar.json").exists()
    assert (campaign_dir / "post_ideas.json").exists()
    
    # Verify plan structure
    plan = json.loads((campaign_dir / "plan.json").read_text())
    assert plan["status"] == "planned"
    assert len(plan["post_ideas"]) == 8


class TestCampaignStructure:
    """Tests for campaign file structure."""

    @pytest.mark.asyncio
    async def test_campaign_plan_structure(self, mock_agent_state, mock_llm_client, monkeypatch):
        """Test: Campaign plan has correct structure."""
        mock_agent_state.llm_client = mock_llm_client
        
        # Setup mocks (same as above)
        class MockSearchResult:
            success = True
            data = {"results": [{"title": "Test"}]}
        
        async def mock_search_web(agent_state, topic, limit, recency):
            return MockSearchResult()
        
        import sys
        mock_module = type(sys)('skills.search_web')
        mock_module.search_web = mock_search_web
        sys.modules['skills.search_web'] = mock_module
        
        async def mock_generate(prompt):
            class Response:
                text = json.dumps([
                    {"angle": "Test", "message": "Test"} for _ in range(2)
                ])
            return Response()
        
        async def mock_generate_strategy(prompt):
            class Response:
                text = json.dumps({
                    "goal": "Test",
                    "target_audience": "Test",
                    "key_messages": ["Test"],
                    "content_pillars": ["Test"],
                    "success_metrics": ["Test"]
                })
            return Response()
        
        call_count = [0]
        async def mock_generate_conditional(prompt):
            call_count[0] += 1
            if "post idea" in prompt.lower() or call_count[0] > 1:
                return await mock_generate(prompt)
            else:
                return await mock_generate_strategy(prompt)
        
        mock_agent_state.llm_client.generate = mock_generate_conditional
        
        result = await create_campaign(
            mock_agent_state,
            topic="Test topic",
            duration_weeks=1,
            platforms=["x"]
        )
        
        campaign_dir = Path(result.data["campaign_dir"])
        plan = json.loads((campaign_dir / "plan.json").read_text())
        
        # Verify structure
        assert "campaign_id" in plan
        assert "topic" in plan
        assert "duration_weeks" in plan
        assert "platforms" in plan
        assert "created_at" in plan
        assert "research" in plan
        assert "strategy" in plan
        assert "calendar" in plan
        assert "post_ideas" in plan
        assert "status" in plan
        assert plan["status"] == "planned"
