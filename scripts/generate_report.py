"""Generate weekly engagement report and send to Google Chat."""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import httpx


class WeeklyReportGenerator:
    """Generate and send weekly engagement reports."""

    def __init__(self, data_dir: Path, webhook_url: str):
        """Initialize report generator.

        Args:
            data_dir: Path to data directory
            webhook_url: Google Chat webhook URL
        """
        self.data_dir = data_dir
        self.metrics_dir = data_dir / "metrics"
        self.webhook_url = webhook_url

    async def generate_and_send(self):
        """Generate weekly report and send to Google Chat."""
        # Load this week's metrics
        this_week_metrics = self._load_week_metrics(weeks_ago=0)
        last_week_metrics = self._load_week_metrics(weeks_ago=1)

        # Calculate growth
        growth = self._calculate_growth(this_week_metrics, last_week_metrics)

        # Format report
        report = self._format_report(this_week_metrics, growth)

        # Send to Google Chat
        await self._send_to_google_chat(report)

        print("✅ Weekly report sent to Google Chat")

    def _load_week_metrics(self, weeks_ago: int = 0) -> Dict:
        """Load aggregated metrics for a given week.

        Args:
            weeks_ago: How many weeks back to load (0 = current week)

        Returns:
            Aggregated metrics for the week
        """
        start_date = datetime.utcnow() - timedelta(weeks=weeks_ago + 1)
        end_date = datetime.utcnow() - timedelta(weeks=weeks_ago)

        aggregated = {
            "platforms": {
                "x": {"total_engagement": 0, "posts": 0},
                "instagram": {"total_engagement": 0, "posts": 0},
                "tiktok": {"total_engagement": 0, "posts": 0},
                "linkedin": {"total_engagement": 0, "posts": 0},
                "reddit": {"total_engagement": 0, "posts": 0},
            }
        }

        # Load all metrics files in date range
        for metrics_file in self.metrics_dir.glob("*.json"):
            try:
                file_date = datetime.strptime(metrics_file.stem, "%Y-%m-%d")

                if start_date <= file_date <= end_date:
                    metrics = json.loads(metrics_file.read_text())

                    for platform, data in metrics["platforms"].items():
                        aggregated["platforms"][platform]["total_engagement"] += data.get(
                            "total_engagement", 0
                        )
                        aggregated["platforms"][platform]["posts"] += len(data.get("posts", []))

            except Exception as e:
                print(f"Error loading metrics file {metrics_file}: {e}")

        return aggregated

    def _calculate_growth(self, this_week: Dict, last_week: Dict) -> Dict:
        """Calculate week-over-week growth.

        Args:
            this_week: This week's metrics
            last_week: Last week's metrics

        Returns:
            Growth percentages by platform
        """
        growth = {}

        for platform in this_week["platforms"]:
            this_engagement = this_week["platforms"][platform]["total_engagement"]
            last_engagement = last_week["platforms"][platform]["total_engagement"]

            if last_engagement > 0:
                pct_change = ((this_engagement - last_engagement) / last_engagement) * 100
            else:
                pct_change = 0 if this_engagement == 0 else 100

            growth[platform] = {
                "absolute": this_engagement - last_engagement,
                "percent": round(pct_change, 1),
            }

        return growth

    def _format_report(self, this_week: Dict, growth: Dict) -> Dict:
        """Format report as Google Chat card.

        Args:
            this_week: This week's metrics
            growth: Growth data

        Returns:
            Google Chat card payload
        """
        sections = []

        # Summary section
        total_engagement = sum(p["total_engagement"] for p in this_week["platforms"].values())
        total_posts = sum(p["posts"] for p in this_week["platforms"].values())

        sections.append(
            {
                "header": "📊 Weekly Social Media Report",
                "widgets": [
                    {
                        "keyValue": {
                            "topLabel": "Total Engagement",
                            "content": str(total_engagement),
                            "icon": "STAR",
                        }
                    },
                    {
                        "keyValue": {
                            "topLabel": "Total Posts",
                            "content": str(total_posts),
                            "icon": "DESCRIPTION",
                        }
                    },
                ],
            }
        )

        # Per-platform breakdown
        platform_widgets = []
        for platform, data in this_week["platforms"].items():
            if data["posts"] > 0:  # Only show active platforms
                growth_indicator = "🔺" if growth[platform]["percent"] > 0 else "🔻"

                platform_widgets.append(
                    {
                        "keyValue": {
                            "topLabel": platform.upper(),
                            "content": f"{data['total_engagement']} engagement ({data['posts']} posts)",
                            "bottomLabel": f"{growth_indicator} {growth[platform]['percent']}% vs last week",
                        }
                    }
                )

        if platform_widgets:
            sections.append({"header": "Platform Breakdown", "widgets": platform_widgets})

        return {"cards": [{"sections": sections}]}

    async def _send_to_google_chat(self, report: Dict):
        """Send report to Google Chat webhook.

        Args:
            report: Google Chat card payload

        Raises:
            Exception: If sending fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(self.webhook_url, json=report, timeout=10.0)

            if response.status_code != 200:
                raise Exception(f"Failed to send report: {response.text}")


async def main():
    """Generate and send weekly report."""
    # Get webhook URL from environment
    webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK")
    if not webhook_url:
        print("Error: GOOGLE_CHAT_WEBHOOK environment variable not set")
        return

    data_dir = Path("./data/memory")

    generator = WeeklyReportGenerator(data_dir, webhook_url)

    print("📧 Generating weekly report...")
    await generator.generate_and_send()


if __name__ == "__main__":
    asyncio.run(main())
