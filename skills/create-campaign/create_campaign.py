"""Create multi-week social media campaigns.

This skill orchestrates a multi-step workflow:
1. Research topic using search-web
2. Define campaign strategy (LLM-generated)
3. Generate content calendar (dates + platforms)
4. Create post ideas for each calendar entry
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class SkillResponse:
    """Response from skill execution."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    next_action: str | None = None


async def create_campaign(
    agent_state: Any,
    topic: str,
    duration_weeks: int,
    platforms: list[str]
) -> SkillResponse:
    """Create a multi-week social media campaign.

    Args:
        agent_state: Current agent state
        topic: Campaign theme (e.g., "AI agents")
        duration_weeks: Campaign duration (e.g., 4)
        platforms: Target platforms (e.g., ["instagram", "x"])

    Returns:
        SkillResponse with campaign plan saved to data/memory/campaigns/{id}/
    """
    try:
        campaign_id = str(uuid4())[:8]
        campaign_dir = agent_state.memory_dir / "campaigns" / campaign_id
        campaign_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Research topic
        research = await _research_topic(agent_state, topic)
        _save_json(campaign_dir / "research.json", research)

        # Step 2: Define strategy
        strategy = await _define_strategy(agent_state, topic, duration_weeks, research)
        _save_json(campaign_dir / "strategy.json", strategy)

        # Step 3: Generate content calendar
        calendar = await _generate_calendar(agent_state, duration_weeks, platforms)
        _save_json(campaign_dir / "calendar.json", calendar)

        # Step 4: Create post ideas
        post_ideas = await _create_post_ideas(agent_state, topic, strategy, calendar)
        _save_json(campaign_dir / "post_ideas.json", post_ideas)

        # Save complete plan
        plan = {
            "campaign_id": campaign_id,
            "topic": topic,
            "duration_weeks": duration_weeks,
            "platforms": platforms,
            "created_at": datetime.utcnow().isoformat(),
            "research": research,
            "strategy": strategy,
            "calendar": calendar,
            "post_ideas": post_ideas,
            "status": "planned"
        }
        _save_json(campaign_dir / "plan.json", plan)

        return SkillResponse(
            success=True,
            message=f"Created {duration_weeks}-week campaign '{topic}' with {len(post_ideas)} post ideas!",
            data={
                "campaign_id": campaign_id,
                "campaign_dir": str(campaign_dir),
                "post_count": len(post_ideas),
                "platforms": platforms
            },
            next_action="schedule-campaign"  # Suggest scheduling next
        )

    except Exception as e:
        return SkillResponse(
            success=False,
            message=f"Campaign creation failed: {str(e)}",
            error={"code": "CAMPAIGN_CREATION_FAILED", "details": str(e)}
        )


async def _research_topic(agent_state: Any, topic: str) -> dict[str, Any]:
    """Step 1: Research topic using search-web skill.

    Args:
        agent_state: Agent state
        topic: Topic to research

    Returns:
        Research results with topic, search results, and insights
    """
    # Try multiple import paths for search_web
    try:
        from skills.search_web import search_web
    except ModuleNotFoundError:
        import sys
        from pathlib import Path
        skills_path = Path(__file__).parent.parent / "search-web"
        if str(skills_path) not in sys.path:
            sys.path.insert(0, str(skills_path))
        from search_web import search_web

    search_result = await search_web(agent_state, topic, limit=10, recency="week")

    if not search_result.success:
        raise Exception(f"Research failed: {search_result.error}")

    return {
        "topic": topic,
        "search_results": search_result.data["results"],
        "insights": search_result.data["results"][:5]  # Top 5 for strategy
    }


async def _define_strategy(
    agent_state: Any,
    topic: str,
    duration_weeks: int,
    research: dict[str, Any]
) -> dict[str, Any]:
    """Step 2: Define campaign strategy using LLM.

    Uses define_strategy.md as prompt instructions.

    Args:
        agent_state: Agent state
        topic: Campaign topic
        duration_weeks: Campaign duration
        research: Research results from step 1

    Returns:
        Strategy dict with goal, target_audience, key_messages, content_pillars, success_metrics
    """
    instructions = _load_instructions("define_strategy.md")

    prompt = f"""
{instructions}

Campaign Details:
- Topic: {topic}
- Duration: {duration_weeks} weeks
- Research Insights: {json.dumps(research['insights'], indent=2)}

Generate campaign strategy.
"""

    response = await agent_state.llm_client.generate(prompt)
    strategy = json.loads(response.text)

    return strategy


async def _generate_calendar(
    agent_state: Any,
    duration_weeks: int,
    platforms: list[str]
) -> list[dict[str, Any]]:
    """Step 3: Generate content calendar.

    Creates posting schedule: 2 posts per platform per week.
    Uses generate_calendar.md for LLM instructions.

    Args:
        agent_state: Agent state
        duration_weeks: Campaign duration
        platforms: Target platforms

    Returns:
        Calendar list of dicts with week, platform, scheduled_at, post_number
    """
    # Calculate posting dates
    start_date = datetime.utcnow()
    posts_per_platform_per_week = 2  # Configurable

    calendar = []
    for week in range(duration_weeks):
        week_start = start_date + timedelta(weeks=week)

        for platform in platforms:
            for post_num in range(posts_per_platform_per_week):
                # Spread posts across the week
                day_offset = (post_num * 3) + 1  # Day 1, 4, etc.
                post_date = week_start + timedelta(days=day_offset, hours=10)  # 10am default

                calendar.append({
                    "week": week + 1,
                    "platform": platform,
                    "scheduled_at": post_date.isoformat(),
                    "post_number": len(calendar) + 1
                })

    return calendar


async def _create_post_ideas(
    agent_state: Any,
    topic: str,
    strategy: dict[str, Any],
    calendar: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Step 4: Generate post ideas for each calendar entry.

    Uses create_post_ideas.md for LLM instructions.

    Args:
        agent_state: Agent state
        topic: Campaign topic
        strategy: Strategy from step 2
        calendar: Calendar from step 3

    Returns:
        Post ideas list with calendar entries merged with LLM-generated ideas
    """
    instructions = _load_instructions("create_post_ideas.md")

    prompt = f"""
{instructions}

Campaign Topic: {topic}
Campaign Strategy: {json.dumps(strategy, indent=2)}
Number of posts needed: {len(calendar)}

For each calendar entry, generate a post idea including:
- Post angle/hook
- Key message
- Suggested format (text, image, video)
- Hashtag suggestions

Return as JSON array matching calendar length.
"""

    response = await agent_state.llm_client.generate(prompt)
    post_ideas_raw = json.loads(response.text)

    # Merge with calendar
    post_ideas = []
    for calendar_entry, idea in zip(calendar, post_ideas_raw, strict=True):
        post_ideas.append({
            **calendar_entry,
            "idea": idea,
            "status": "planned"
        })

    return post_ideas


def _load_instructions(filename: str) -> str:
    """Load instruction markdown file from same directory.

    Args:
        filename: Name of .md file to load

    Returns:
        File contents as string
    """
    instruction_path = Path(__file__).parent / filename
    return instruction_path.read_text()


def _save_json(filepath: Path, data: dict[str, Any]) -> None:
    """Save data as formatted JSON.

    Args:
        filepath: Path to save to
        data: Data to serialize
    """
    filepath.write_text(json.dumps(data, indent=2))
