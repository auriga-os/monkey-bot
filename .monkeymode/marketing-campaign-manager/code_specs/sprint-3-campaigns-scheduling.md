# Code Spec: Sprint 3 - Campaign Planning & Scheduling

**Author:** MonkeyMode Agent  
**Date:** 2026-02-12  
**Status:** Ready for Implementation  
**Sprint:** Sprint 3 - Campaign Features  
**Stories:** 3.1-3.3 (Campaign creation, scheduling, cron system)

---

## Table of Contents

1. [Implementation Summary](#implementation-summary)
2. [Technical Context](#technical-context)
3. [Story 3.1: Create Campaign Skill](#story-31-create-campaign-skill)
4. [Story 3.2: Schedule Campaign Skill](#story-32-schedule-campaign-skill)
5. [Story 3.3: Cron Scheduler (Framework)](#story-33-cron-scheduler-framework)
6. [Dependency Graph](#dependency-graph)
7. [Final Verification](#final-verification)

---

## Implementation Summary

**Files to Create:** 18 files  
**Files to Modify:** 2 files  
**Tests to Add:** 8 test files  
**Estimated Complexity:** L (5-7 days solo developer)

### File Breakdown by Story

| Story | Description | Files Created | Files Modified | Tests |
|-------|-------------|---------------|----------------|-------|
| 3.1 | Create campaign | 10 | 0 | 3 |
| 3.2 | Schedule campaign | 4 | 0 | 2 |
| 3.3 | Cron scheduler | 3 | 2 | 3 |
| **Total** | **3 stories** | **17** | **2** | **8** |

---

## Technical Context

### Key Concepts

**Campaign Structure:**
A campaign is a planned series of posts across multiple platforms over a defined time period. Each campaign includes:
- Topic/theme
- Duration (e.g., 4 weeks)
- Target platforms
- Content calendar (specific dates + platforms)
- Post ideas for each calendar entry

**Scheduling System:**
The scheduler takes campaign posts and creates cron jobs that automatically post at specified times.

**Menu Pattern:**
The create-campaign skill uses the "menu pattern" - breaking complex workflows into sub-tasks with separate instruction files.

### Dependencies

**Story 3.1 (create-campaign) depends on:**
- Story 2.5 (search-web) - For topic research
- Stories 1.2, 2.1-2.4 (all platform posting) - To validate platforms

**Story 3.2 (schedule-campaign) depends on:**
- Story 3.1 (campaigns must exist to schedule)
- Story 3.3 (cron scheduler must exist)

**Story 3.3 (cron scheduler) depends on:**
- NONE (framework enhancement, standalone)

### Reusable Patterns

From previous sprints:
- Skill structure and SkillResponse format (Sprint 1)
- LLM generation patterns (Story 1.2 generate-post)
- File-based state storage (Sprint 1 approval workflow)

---

## Story 3.1: Create Campaign Skill

**Priority:** High  
**Size:** L (2-3 days)  
**Dependencies:** Story 2.5 (search-web)

### Overview

The create-campaign skill orchestrates a multi-step workflow:
1. Research topic using search-web
2. Define campaign strategy (LLM-generated)
3. Generate content calendar (dates + platforms)
4. Create post ideas for each calendar entry

Uses the **menu pattern** with separate instruction files for each step.

### Task 3.1.1: Create Campaign Skill Structure

**Files to Create:**
- `skills/create-campaign/SKILL.md` (new)
- `skills/create-campaign/create_campaign.py` (new - orchestrator)
- `skills/create-campaign/__init__.py` (new)
- `skills/create-campaign/research_topic.md` (new - Step 1 instructions)
- `skills/create-campaign/define_strategy.md` (new - Step 2 instructions)
- `skills/create-campaign/generate_calendar.md` (new - Step 3 instructions)
- `skills/create-campaign/create_post_ideas.md` (new - Step 4 instructions)
- `tests/skills/test_create_campaign.py` (new)
- `tests/skills/test_campaign_integration.py` (new)

**Files to Modify:** NONE

**Pattern Reference:** This is a NEW pattern (menu pattern with sub-files)

### Implementation Details

**Directory Structure:**
```
skills/create-campaign/
├── SKILL.md                 # Skill description for routing
├── __init__.py              
├── create_campaign.py       # Main orchestrator
├── research_topic.md        # LLM instructions for Step 1
├── define_strategy.md       # LLM instructions for Step 2
├── generate_calendar.md     # LLM instructions for Step 3
└── create_post_ideas.md     # LLM instructions for Step 4
```

**SKILL.md Content:**

```markdown
---
name: create-campaign
description: Create a multi-week social media campaign with a content calendar, strategy, and post ideas. Use when planning comprehensive marketing campaigns across multiple platforms.
---

# create-campaign

Plan and structure social media campaigns.

## When to invoke

User says:
- "create a 4-week campaign about [topic]"
- "plan a campaign for [product launch]"
- "I need a content calendar for [topic]"
- "generate a marketing campaign about [theme]"

## Parameters

- `topic` (str, required): Campaign theme/topic
- `duration_weeks` (int, required): Campaign length in weeks
- `platforms` (list[str], required): Target platforms (instagram, x, tiktok, linkedin, reddit)
```

**Main Orchestrator (create_campaign.py):**

```python
# skills/create-campaign/create_campaign.py
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta
from typing import List

from src.core.interfaces import AgentState, SkillResponse
from skills.search_web import search_web

async def create_campaign(
    agent_state: AgentState,
    topic: str,
    duration_weeks: int,
    platforms: List[str]
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


async def _research_topic(agent_state: AgentState, topic: str) -> dict:
    """Step 1: Research topic using search-web skill."""
    search_result = await search_web(agent_state, topic, limit=10, recency="week")
    
    if not search_result.success:
        raise Exception(f"Research failed: {search_result.error}")
    
    return {
        "topic": topic,
        "search_results": search_result.data["results"],
        "insights": search_result.data["results"][:5]  # Top 5 for strategy
    }


async def _define_strategy(
    agent_state: AgentState,
    topic: str,
    duration_weeks: int,
    research: dict
) -> dict:
    """Step 2: Define campaign strategy using LLM.
    
    Uses define_strategy.md as prompt instructions.
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
    agent_state: AgentState,
    duration_weeks: int,
    platforms: List[str]
) -> List[dict]:
    """Step 3: Generate content calendar.
    
    Creates posting schedule: 2-3 posts per platform per week.
    Uses generate_calendar.md for LLM instructions.
    """
    instructions = _load_instructions("generate_calendar.md")
    
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
    agent_state: AgentState,
    topic: str,
    strategy: dict,
    calendar: List[dict]
) -> List[dict]:
    """Step 4: Generate post ideas for each calendar entry.
    
    Uses create_post_ideas.md for LLM instructions.
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
    for calendar_entry, idea in zip(calendar, post_ideas_raw):
        post_ideas.append({
            **calendar_entry,
            "idea": idea,
            "status": "planned"
        })
    
    return post_ideas


def _load_instructions(filename: str) -> str:
    """Load instruction markdown file from same directory."""
    instruction_path = Path(__file__).parent / filename
    return instruction_path.read_text()


def _save_json(filepath: Path, data: dict) -> None:
    """Save data as formatted JSON."""
    filepath.write_text(json.dumps(data, indent=2))
```

**LLM Instruction Files:**

```markdown
<!-- research_topic.md -->
# Step 1: Research Topic

You are researching a topic for a social media campaign.

Your goal:
1. Identify key themes and subtopics
2. Find trending angles and discussions
3. Identify content gaps and opportunities
4. Note popular keywords/hashtags

Output format: List of insights with supporting evidence from search results.
```

```markdown
<!-- define_strategy.md -->
# Step 2: Define Campaign Strategy

Based on research, create a campaign strategy.

Required elements:
1. **Campaign Goal**: What are we trying to achieve?
2. **Target Audience**: Who are we speaking to?
3. **Key Messages**: 3-5 core messages to communicate
4. **Content Pillars**: 3-4 themes to rotate through
5. **Success Metrics**: How will we measure effectiveness?

Output as JSON:
{
  "goal": "...",
  "target_audience": "...",
  "key_messages": ["...", "...", "..."],
  "content_pillars": ["...", "...", "..."],
  "success_metrics": ["...", "..."]
}
```

```markdown
<!-- generate_calendar.md -->
# Step 3: Generate Content Calendar

Create a posting schedule balancing:
- Consistent frequency (2-3 posts per platform per week)
- Optimal posting times for each platform
- Variety across platforms
- Content pillar rotation

For each post entry, include:
- Week number
- Platform
- Scheduled date/time
- Suggested content pillar
```

```markdown
<!-- create_post_ideas.md -->
# Step 4: Create Post Ideas

For each calendar entry, generate a specific post idea.

Each idea should include:
1. **Angle/Hook**: What makes this post interesting?
2. **Key Message**: Core takeaway for audience
3. **Format**: Text-only, image, video, carousel, etc.
4. **Hashtags**: 3-5 relevant hashtags
5. **Call-to-Action**: What should audience do?

Ensure variety:
- Mix educational, entertaining, and promotional content
- Rotate through content pillars
- Adapt tone for each platform
- Build on previous posts (storyline)

Output as JSON array matching calendar length.
```

**Test Cases:**

```python
# tests/skills/test_create_campaign.py

async def test_create_campaign_success():
    """Full campaign creation flow."""
    result = await create_campaign(
        agent_state,
        topic="AI agents",
        duration_weeks=4,
        platforms=["instagram", "x"]
    )
    
    assert result.success is True
    assert "campaign_id" in result.data
    assert result.data["post_count"] == 16  # 4 weeks * 2 platforms * 2 posts/week
    
    # Verify files created
    campaign_dir = Path(result.data["campaign_dir"])
    assert (campaign_dir / "plan.json").exists()
    assert (campaign_dir / "research.json").exists()
    assert (campaign_dir / "strategy.json").exists()
    assert (campaign_dir / "calendar.json").exists()
    assert (campaign_dir / "post_ideas.json").exists()


async def test_research_step():
    """Step 1: Topic research."""
    research = await _research_topic(agent_state, "AI agents")
    
    assert "topic" in research
    assert "search_results" in research
    assert len(research["search_results"]) > 0


async def test_strategy_step():
    """Step 2: Strategy definition."""
    research = {"insights": [...]}
    strategy = await _define_strategy(agent_state, "AI agents", 4, research)
    
    assert "goal" in strategy
    assert "target_audience" in strategy
    assert "key_messages" in strategy
    assert len(strategy["content_pillars"]) >= 3


async def test_calendar_generation():
    """Step 3: Calendar creation."""
    calendar = await _generate_calendar(agent_state, 4, ["instagram", "x"])
    
    assert len(calendar) == 16  # 4 weeks * 2 platforms * 2 posts/week
    assert all(entry["platform"] in ["instagram", "x"] for entry in calendar)
    assert all("scheduled_at" in entry for entry in calendar)


async def test_post_ideas_generation():
    """Step 4: Post idea creation."""
    strategy = {"content_pillars": ["Education", "Case Studies", "Tips"]}
    calendar = [{"week": 1, "platform": "x", "scheduled_at": "..."}]
    
    post_ideas = await _create_post_ideas(agent_state, "AI agents", strategy, calendar)
    
    assert len(post_ideas) == len(calendar)
    assert all("idea" in post for post in post_ideas)
    assert all("status" in post for post in post_ideas)
```

**Integration Test:**

```python
# tests/skills/test_campaign_integration.py

async def test_full_campaign_workflow():
    """End-to-end campaign creation → scheduling."""
    
    # Step 1: Create campaign
    campaign = await create_campaign(
        agent_state,
        topic="AI automation",
        duration_weeks=2,
        platforms=["x"]
    )
    
    assert campaign.success is True
    campaign_id = campaign.data["campaign_id"]
    
    # Step 2: Load campaign plan
    campaign_dir = agent_state.memory_dir / "campaigns" / campaign_id
    plan = json.loads((campaign_dir / "plan.json").read_text())
    
    assert plan["status"] == "planned"
    assert len(plan["post_ideas"]) == 4  # 2 weeks * 1 platform * 2 posts/week
    
    # Step 3: Verify all posts have ideas
    for post in plan["post_ideas"]:
        assert "idea" in post
        assert "scheduled_at" in post
        assert post["status"] == "planned"
```

**Critical Notes:**
- Campaign creation is **LLM-heavy** (4 LLM calls per campaign) - watch costs
- Consider adding **campaign templates** for common use cases to reduce LLM calls
- Store campaigns in `data/memory/campaigns/{id}/` for easy access
- Each campaign gets a unique ID (first 8 chars of UUID)
- Scheduling logic is simplified (Day 1, 4, 7 pattern) - can make smarter in future

---

## Story 3.2: Schedule Campaign Skill

**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** Story 3.1 (campaigns exist), Story 3.3 (cron scheduler)

### Task 3.2.1: Create Schedule Campaign Skill

**Files to Create:**
- `skills/schedule-campaign/SKILL.md` (new)
- `skills/schedule-campaign/schedule_campaign.py` (new)
- `skills/schedule-campaign/__init__.py` (new)
- `tests/skills/test_schedule_campaign.py` (new)

**Files to Modify:** NONE

**Pattern Reference:** Simple skill, loads campaign and creates cron jobs

**Implementation Details:**

**SKILL.md Content:**

```markdown
---
name: schedule-campaign
description: Schedule all posts in a campaign to be automatically posted at their scheduled times. Use after creating a campaign to automate posting.
---

# schedule-campaign

Schedule campaign posts for automatic posting.

## When to invoke

User says:
- "schedule campaign [id]"
- "activate the campaign"
- "start posting the campaign"
- "schedule all posts for [campaign]"

## Parameters

- `campaign_id` (str, required): Campaign ID from create-campaign
```

**Main Implementation:**

```python
# skills/schedule-campaign/schedule_campaign.py
import json
from pathlib import Path
from datetime import datetime

from src.core.interfaces import AgentState, SkillResponse
from src.core.scheduler import CronScheduler

async def schedule_campaign(
    agent_state: AgentState,
    campaign_id: str
) -> SkillResponse:
    """Schedule all posts in a campaign for automatic posting.
    
    Args:
        agent_state: Current agent state
        campaign_id: Campaign ID (from create-campaign)
        
    Returns:
        SkillResponse with scheduling confirmation
    """
    try:
        # Load campaign plan
        campaign_dir = agent_state.memory_dir / "campaigns" / campaign_id
        if not campaign_dir.exists():
            raise ValueError(f"Campaign {campaign_id} not found")
        
        plan = json.loads((campaign_dir / "plan.json").read_text())
        
        if plan.get("status") == "scheduled":
            return SkillResponse(
                success=False,
                message=f"Campaign {campaign_id} is already scheduled",
                error={"code": "ALREADY_SCHEDULED"}
            )
        
        # Schedule each post
        scheduler = CronScheduler(agent_state)
        scheduled_jobs = []
        
        for post_idea in plan["post_ideas"]:
            job_id = await scheduler.schedule_job(
                job_type="post_content",
                schedule_at=datetime.fromisoformat(post_idea["scheduled_at"]),
                payload={
                    "campaign_id": campaign_id,
                    "post_number": post_idea["post_number"],
                    "platform": post_idea["platform"],
                    "idea": post_idea["idea"],
                    "topic": plan["topic"]
                }
            )
            
            scheduled_jobs.append({
                "job_id": job_id,
                "post_number": post_idea["post_number"],
                "platform": post_idea["platform"],
                "scheduled_at": post_idea["scheduled_at"]
            })
        
        # Update campaign status
        plan["status"] = "scheduled"
        plan["scheduled_at"] = datetime.utcnow().isoformat()
        plan["scheduled_jobs"] = scheduled_jobs
        _save_json(campaign_dir / "plan.json", plan)
        
        return SkillResponse(
            success=True,
            message=f"Scheduled {len(scheduled_jobs)} posts for campaign '{plan['topic']}'!",
            data={
                "campaign_id": campaign_id,
                "scheduled_count": len(scheduled_jobs),
                "first_post_at": scheduled_jobs[0]["scheduled_at"],
                "last_post_at": scheduled_jobs[-1]["scheduled_at"]
            }
        )
        
    except Exception as e:
        return SkillResponse(
            success=False,
            message=f"Scheduling failed: {str(e)}",
            error={"code": "SCHEDULING_FAILED", "details": str(e)}
        )


def _save_json(filepath: Path, data: dict) -> None:
    """Save data as formatted JSON."""
    filepath.write_text(json.dumps(data, indent=2))
```

**Test Cases:**

```python
# tests/skills/test_schedule_campaign.py

async def test_schedule_campaign_success():
    """Schedule all posts in a campaign."""
    # Setup: Create campaign first
    campaign = await create_campaign(agent_state, "AI", 2, ["x"])
    campaign_id = campaign.data["campaign_id"]
    
    # Schedule it
    result = await schedule_campaign(agent_state, campaign_id)
    
    assert result.success is True
    assert result.data["scheduled_count"] == 4  # 2 weeks * 1 platform * 2 posts
    
    # Verify campaign status updated
    plan = json.loads((agent_state.memory_dir / "campaigns" / campaign_id / "plan.json").read_text())
    assert plan["status"] == "scheduled"
    assert "scheduled_jobs" in plan


async def test_schedule_nonexistent_campaign():
    """Scheduling non-existent campaign fails."""
    result = await schedule_campaign(agent_state, "invalid-id")
    
    assert result.success is False
    assert result.error["code"] == "CAMPAIGN_NOT_FOUND" or "not found" in result.message.lower()


async def test_schedule_already_scheduled():
    """Scheduling already-scheduled campaign."""
    campaign = await create_campaign(agent_state, "AI", 1, ["x"])
    campaign_id = campaign.data["campaign_id"]
    
    # Schedule twice
    result1 = await schedule_campaign(agent_state, campaign_id)
    result2 = await schedule_campaign(agent_state, campaign_id)
    
    assert result1.success is True
    assert result2.success is False
    assert "already scheduled" in result2.message.lower()
```

**Critical Notes:**
- Each scheduled job stores the **post idea** so the cron job knows what to generate
- Campaign status changes from "planned" → "scheduled"
- Store job IDs so campaigns can be **cancelled** later (future feature)
- If scheduling fails partway through, need **rollback logic** (future enhancement)

---

## Story 3.3: Cron Scheduler (Framework Enhancement)

**Priority:** High  
**Size:** L (2-3 days)  
**Dependencies:** NONE

### Overview

Add a simple in-memory cron scheduler to the monkey-bot framework. This is a **framework enhancement** (goes in `core/` not `skills/`).

### Task 3.3.1: Implement Cron Scheduler

**Files to Create:**
- `core/scheduler/cron.py` (new)
- `core/scheduler/__init__.py` (new)
- `tests/core/test_cron_scheduler.py` (new)

**Files to Modify:**
- `core/agent.py` - Start scheduler on agent init
- `config/settings.py` - Add scheduler config

**Pattern Reference:** This is a NEW framework component

**Implementation Details:**

**Scheduler Implementation:**

```python
# core/scheduler/cron.py
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List
from uuid import uuid4

logger = logging.getLogger(__name__)


class CronScheduler:
    """Simple in-memory cron scheduler for background jobs.
    
    For MVP, this is a simple polling-based scheduler.
    Future: Use APScheduler or similar for production.
    """
    
    def __init__(self, agent_state, check_interval_seconds: int = 10):
        """Initialize scheduler.
        
        Args:
            agent_state: Agent state for accessing skills
            check_interval_seconds: How often to check for due jobs
        """
        self.agent_state = agent_state
        self.check_interval = check_interval_seconds
        self.jobs: List[Dict] = []
        self.running = False
        self._load_jobs()
    
    async def schedule_job(
        self,
        job_type: str,
        schedule_at: datetime,
        payload: dict
    ) -> str:
        """Schedule a job to run at specified time.
        
        Args:
            job_type: Type of job (e.g., "post_content")
            schedule_at: When to run the job (datetime)
            payload: Job-specific data
            
        Returns:
            Job ID (UUID)
        """
        job_id = str(uuid4())
        
        job = {
            "id": job_id,
            "job_type": job_type,
            "schedule_at": schedule_at.isoformat(),
            "payload": payload,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0,
            "max_attempts": 3
        }
        
        self.jobs.append(job)
        self._save_jobs()
        
        logger.info(
            "Job scheduled",
            extra={
                "job_id": job_id,
                "job_type": job_type,
                "schedule_at": schedule_at.isoformat()
            }
        )
        
        return job_id
    
    async def start(self):
        """Start the scheduler background task."""
        self.running = True
        logger.info("Cron scheduler started")
        
        while self.running:
            await self._check_and_execute_jobs()
            await asyncio.sleep(self.check_interval)
    
    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        logger.info("Cron scheduler stopped")
    
    async def _check_and_execute_jobs(self):
        """Check for due jobs and execute them."""
        now = datetime.utcnow()
        
        for job in self.jobs:
            if job["status"] != "pending":
                continue
            
            schedule_at = datetime.fromisoformat(job["schedule_at"])
            
            if schedule_at <= now:
                await self._execute_job(job)
    
    async def _execute_job(self, job: Dict):
        """Execute a single job."""
        job_id = job["id"]
        job_type = job["job_type"]
        
        logger.info(f"Executing job {job_id} (type: {job_type})")
        
        try:
            job["status"] = "running"
            job["started_at"] = datetime.utcnow().isoformat()
            self._save_jobs()
            
            # Execute based on job type
            if job_type == "post_content":
                await self._execute_post_content(job)
            else:
                raise ValueError(f"Unknown job type: {job_type}")
            
            # Mark as completed
            job["status"] = "completed"
            job["completed_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            job["attempts"] += 1
            logger.error(f"Job {job_id} failed: {e}", extra={"job": job})
            
            if job["attempts"] >= job["max_attempts"]:
                job["status"] = "failed"
                job["error"] = str(e)
            else:
                # Retry later (reschedule for 5 minutes from now)
                retry_at = datetime.utcnow() + timedelta(minutes=5)
                job["schedule_at"] = retry_at.isoformat()
                job["status"] = "pending"
                logger.info(f"Job {job_id} will retry at {retry_at}")
        
        finally:
            self._save_jobs()
    
    async def _execute_post_content(self, job: Dict):
        """Execute post_content job.
        
        Job payload includes:
            - campaign_id
            - post_number
            - platform
            - idea (post idea from campaign)
            - topic
        """
        payload = job["payload"]
        
        # Step 1: Generate post content
        from skills.generate_post import generate_post
        generated = await generate_post(
            self.agent_state,
            topic=payload["topic"],
            platform=payload["platform"],
            additional_context=payload["idea"]
        )
        
        if not generated.success:
            raise Exception(f"Post generation failed: {generated.error}")
        
        # Step 2: Request approval (creates approval request)
        from skills.request_approval import request_approval
        approval_requested = await request_approval(
            self.agent_state,
            post_data=generated.data["post"]
        )
        
        if not approval_requested.success:
            raise Exception(f"Approval request failed: {approval_requested.error}")
        
        # Note: Actual posting happens when user approves via Google Chat
        # This job just generates content and requests approval
        
        logger.info(
            "Scheduled post generated and sent for approval",
            extra={
                "campaign_id": payload["campaign_id"],
                "post_number": payload["post_number"],
                "platform": payload["platform"]
            }
        )
    
    def _load_jobs(self):
        """Load jobs from disk (persistence)."""
        jobs_file = self.agent_state.memory_dir / "scheduler" / "jobs.json"
        
        if jobs_file.exists():
            self.jobs = json.loads(jobs_file.read_text())
            logger.info(f"Loaded {len(self.jobs)} jobs from disk")
    
    def _save_jobs(self):
        """Save jobs to disk (persistence)."""
        jobs_file = self.agent_state.memory_dir / "scheduler" / "jobs.json"
        jobs_file.parent.mkdir(parents=True, exist_ok=True)
        jobs_file.write_text(json.dumps(self.jobs, indent=2))
    
    def get_pending_jobs(self) -> List[Dict]:
        """Get all pending jobs."""
        return [job for job in self.jobs if job["status"] == "pending"]
    
    def get_job(self, job_id: str) -> Dict | None:
        """Get job by ID."""
        for job in self.jobs:
            if job["id"] == job_id:
                return job
        return None
```

**Integration with Agent:**

```python
# core/agent.py (modify)

from core.scheduler import CronScheduler

class AgentCore:
    def __init__(self, config):
        # ... existing init ...
        
        # Initialize scheduler
        self.scheduler = CronScheduler(
            agent_state=self.agent_state,
            check_interval_seconds=config.get("scheduler_check_interval", 10)
        )
    
    async def start(self):
        """Start agent and scheduler."""
        # ... existing start logic ...
        
        # Start scheduler in background
        asyncio.create_task(self.scheduler.start())
        
        logger.info("Agent started with scheduler")
    
    async def stop(self):
        """Stop agent and scheduler."""
        await self.scheduler.stop()
        # ... existing stop logic ...
```

**Configuration:**

```python
# config/settings.py (add)

SCHEDULER_CONFIG = {
    "check_interval_seconds": 10,  # How often to check for due jobs
    "max_attempts": 3,              # Max retries per job
    "retry_delay_minutes": 5        # Delay between retries
}
```

**Test Cases:**

```python
# tests/core/test_cron_scheduler.py

async def test_schedule_job():
    """Schedule a job for future execution."""
    scheduler = CronScheduler(agent_state)
    
    schedule_at = datetime.utcnow() + timedelta(seconds=5)
    job_id = await scheduler.schedule_job(
        job_type="post_content",
        schedule_at=schedule_at,
        payload={"platform": "x", "content": "Test"}
    )
    
    assert job_id is not None
    assert len(scheduler.jobs) == 1
    assert scheduler.jobs[0]["status"] == "pending"


async def test_execute_due_job():
    """Scheduler executes jobs when time arrives."""
    scheduler = CronScheduler(agent_state, check_interval_seconds=1)
    
    # Schedule job for 2 seconds from now
    schedule_at = datetime.utcnow() + timedelta(seconds=2)
    job_id = await scheduler.schedule_job(
        job_type="post_content",
        schedule_at=schedule_at,
        payload={"platform": "x"}
    )
    
    # Start scheduler
    asyncio.create_task(scheduler.start())
    
    # Wait for job to execute
    await asyncio.sleep(4)
    
    # Check job status
    job = scheduler.get_job(job_id)
    assert job["status"] in ["completed", "running"]  # Should have executed


async def test_job_retry_on_failure():
    """Failed jobs are retried."""
    scheduler = CronScheduler(agent_state)
    
    # Schedule job that will fail
    job_id = await scheduler.schedule_job(
        job_type="post_content",
        schedule_at=datetime.utcnow(),
        payload={"platform": "invalid"}  # Will cause error
    )
    
    # Execute
    job = scheduler.get_job(job_id)
    await scheduler._execute_job(job)
    
    # Check retry scheduled
    assert job["attempts"] == 1
    assert job["status"] == "pending"  # Rescheduled for retry
    
    new_schedule = datetime.fromisoformat(job["schedule_at"])
    assert new_schedule > datetime.utcnow()


async def test_job_fails_after_max_attempts():
    """Jobs fail permanently after max attempts."""
    scheduler = CronScheduler(agent_state)
    
    job_id = await scheduler.schedule_job(
        job_type="post_content",
        schedule_at=datetime.utcnow(),
        payload={"platform": "invalid"}
    )
    
    job = scheduler.get_job(job_id)
    job["max_attempts"] = 2
    
    # Execute twice
    await scheduler._execute_job(job)
    await scheduler._execute_job(job)
    
    # Should be marked as failed
    assert job["status"] == "failed"
    assert job["attempts"] == 2


async def test_job_persistence():
    """Jobs are saved to disk and reloaded."""
    scheduler1 = CronScheduler(agent_state)
    
    job_id = await scheduler1.schedule_job(
        job_type="post_content",
        schedule_at=datetime.utcnow() + timedelta(hours=1),
        payload={"platform": "x"}
    )
    
    # Create new scheduler (simulates restart)
    scheduler2 = CronScheduler(agent_state)
    
    # Should have loaded job from disk
    assert len(scheduler2.jobs) == 1
    assert scheduler2.jobs[0]["id"] == job_id
```

**Critical Notes:**
- This is a **simple MVP scheduler** - not production-grade
- For production, consider using **APScheduler** or similar library
- Jobs are stored in `data/memory/scheduler/jobs.json` for persistence
- Scheduler checks every 10 seconds by default (configurable)
- Failed jobs **retry automatically** (max 3 attempts)
- Scheduler starts automatically when agent starts
- Jobs survive agent restarts (loaded from disk)

---

## Dependency Graph

```
Story 3.3 (Cron Scheduler - Framework)
    ↓
Story 3.1 (Create Campaign) ──→ Story 3.2 (Schedule Campaign)
    ↓                                  ↓
Story 2.5 (search-web)               Story 3.3 (Cron)
```

**Recommended Implementation Order:**

1. **Day 1-2:** Story 3.3 (Cron Scheduler)
   - Framework enhancement, needed by Story 3.2
   - Test thoroughly before moving on

2. **Day 3-5:** Story 3.1 (Create Campaign)
   - Complex skill with 4 sub-steps
   - Test each step independently

3. **Day 6-7:** Story 3.2 (Schedule Campaign)
   - Ties together 3.1 and 3.3
   - End-to-end integration testing

---

## Final Verification

**Functionality:**
- [ ] Campaigns can be created with full workflow (research → strategy → calendar → ideas)
- [ ] Campaign files properly saved to data/memory/campaigns/{id}/
- [ ] Scheduler can schedule jobs for future execution
- [ ] Scheduled jobs execute at correct times
- [ ] Failed jobs retry automatically
- [ ] Campaign posts generate approval requests when scheduled time arrives
- [ ] All LLM instruction files produce valid outputs

**Code Quality:**
- [ ] Menu pattern properly implemented (separate .md files for sub-steps)
- [ ] Scheduler is framework enhancement (in core/, not skills/)
- [ ] Proper error handling in all async operations
- [ ] Jobs persist across agent restarts
- [ ] Clean separation between campaign creation and scheduling

**Testing:**
- [ ] Unit tests pass for all components
- [ ] Integration tests cover full campaign → schedule → execute flow
- [ ] Scheduler tests cover retry logic and failure scenarios
- [ ] End-to-end test: Create campaign → Schedule → Wait → Verify approval requests sent

**Configuration:**
- [ ] Scheduler config in config/settings.py
- [ ] Jobs directory created automatically
- [ ] Campaign directory structure documented

**Documentation:**
- [ ] Campaign creation workflow documented
- [ ] Scheduler architecture documented
- [ ] Job types and payload formats documented

---

## Post-Implementation Notes

After completing Sprint 3, you'll have:
- ✅ Full campaign planning and strategy generation
- ✅ Automated content calendars
- ✅ Scheduling system for automated posting
- ✅ Background job execution with retry logic

**Next Steps → Sprint 4:**
- Deployment automation (deploy.sh script)
- Engagement metrics collection
- Weekly reporting
- Production polish
