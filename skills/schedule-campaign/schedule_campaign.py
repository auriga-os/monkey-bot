"""Schedule all posts in a campaign for automatic posting.

This skill takes a campaign (from create-campaign) and schedules all
its posts using the cron scheduler. Each post becomes a background job
that will execute at its scheduled time.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SkillResponse:
    """Response from skill execution."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


async def schedule_campaign(
    agent_state: Any,
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
            return SkillResponse(
                success=False,
                message=f"Campaign {campaign_id} not found",
                error={"code": "CAMPAIGN_NOT_FOUND"}
            )

        plan_path = campaign_dir / "plan.json"
        plan = json.loads(plan_path.read_text())

        if plan.get("status") == "scheduled":
            return SkillResponse(
                success=False,
                message=f"Campaign {campaign_id} is already scheduled",
                error={"code": "ALREADY_SCHEDULED"}
            )

        # Get scheduler from agent state
        # Note: The agent core has a scheduler attribute
        scheduler = agent_state.scheduler

        # Schedule each post
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
        plan_path.write_text(json.dumps(plan, indent=2))

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
