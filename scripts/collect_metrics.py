"""Collect engagement metrics from all social platforms."""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import httpx


class MetricsCollector:
    """Collect engagement metrics from all platforms."""

    def __init__(self, data_dir: Path):
        """Initialize metrics collector.

        Args:
            data_dir: Path to data directory (contains posts and metrics)
        """
        self.data_dir = data_dir
        self.metrics_dir = data_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all(self) -> Dict:
        """Collect metrics from all platforms.

        Returns:
            Dictionary with metrics for all platforms
        """
        metrics = {"collected_at": datetime.utcnow().isoformat(), "platforms": {}}

        # Collect from each platform
        metrics["platforms"]["x"] = await self.collect_x_metrics()
        metrics["platforms"]["instagram"] = await self.collect_instagram_metrics()
        metrics["platforms"]["tiktok"] = await self.collect_tiktok_metrics()
        metrics["platforms"]["linkedin"] = await self.collect_linkedin_metrics()
        metrics["platforms"]["reddit"] = await self.collect_reddit_metrics()

        # Save to file
        filename = f"{datetime.utcnow().strftime('%Y-%m-%d')}.json"
        (self.metrics_dir / filename).write_text(json.dumps(metrics, indent=2))

        return metrics

    async def collect_x_metrics(self) -> Dict:
        """Collect metrics from X/Twitter.

        Returns:
            Dictionary with X metrics
        """
        # Get recent posts from local storage
        posts = self._load_recent_posts("x")

        if not posts:
            return {"posts": [], "total_engagement": 0}

        # Get API credentials from environment
        access_token = os.getenv("X_ACCESS_TOKEN")
        if not access_token:
            print("Warning: X_ACCESS_TOKEN not set, skipping X metrics")
            return {"posts": [], "total_engagement": 0}

        # Fetch engagement for each post
        headers = {"Authorization": f"Bearer {access_token}"}

        engagement_data = []
        total_engagement = 0

        async with httpx.AsyncClient() as client:
            for post in posts:
                try:
                    # GET tweet metrics
                    response = await client.get(
                        f"https://api.twitter.com/2/tweets/{post['post_id']}",
                        headers=headers,
                        params={
                            "tweet.fields": "public_metrics",
                        },
                        timeout=10.0,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        metrics = data["data"]["public_metrics"]

                        engagement = {
                            "post_id": post["post_id"],
                            "posted_at": post["posted_at"],
                            "likes": metrics["like_count"],
                            "retweets": metrics["retweet_count"],
                            "replies": metrics["reply_count"],
                            "impressions": metrics.get("impression_count", 0),
                        }

                        engagement["total"] = (
                            engagement["likes"] + engagement["retweets"] + engagement["replies"]
                        )

                        engagement_data.append(engagement)
                        total_engagement += engagement["total"]

                except Exception as e:
                    print(f"Error fetching metrics for post {post['post_id']}: {e}")

        return {
            "posts": engagement_data,
            "total_engagement": total_engagement,
            "avg_engagement": total_engagement / len(posts) if posts else 0,
        }

    async def collect_instagram_metrics(self) -> Dict:
        """Collect metrics from Instagram.

        Returns:
            Dictionary with Instagram metrics
        """
        posts = self._load_recent_posts("instagram")
        if not posts:
            return {"posts": [], "total_engagement": 0}

        access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        if not access_token:
            print("Warning: INSTAGRAM_ACCESS_TOKEN not set, skipping Instagram metrics")
            return {"posts": [], "total_engagement": 0}

        # Instagram Graph API
        base_url = "https://graph.facebook.com/v18.0"

        engagement_data = []
        total_engagement = 0

        async with httpx.AsyncClient() as client:
            for post in posts:
                try:
                    response = await client.get(
                        f"{base_url}/{post['post_id']}",
                        params={
                            "fields": "like_count,comments_count,timestamp",
                            "access_token": access_token,
                        },
                        timeout=10.0,
                    )

                    if response.status_code == 200:
                        data = response.json()

                        engagement = {
                            "post_id": post["post_id"],
                            "posted_at": post["posted_at"],
                            "likes": data.get("like_count", 0),
                            "comments": data.get("comments_count", 0),
                        }

                        engagement["total"] = engagement["likes"] + engagement["comments"]
                        engagement_data.append(engagement)
                        total_engagement += engagement["total"]

                except Exception as e:
                    print(f"Error fetching Instagram metrics: {e}")

        return {
            "posts": engagement_data,
            "total_engagement": total_engagement,
            "avg_engagement": total_engagement / len(posts) if posts else 0,
        }

    async def collect_tiktok_metrics(self) -> Dict:
        """Collect metrics from TikTok.

        Returns:
            Dictionary with TikTok metrics
        """
        # TODO: Implement TikTok metrics collection
        # TikTok API endpoint: https://open.tiktokapis.com/v2/video/list/
        # Fields: like_count, comment_count, share_count, view_count
        posts = self._load_recent_posts("tiktok")
        return {"posts": [], "total_engagement": 0}

    async def collect_linkedin_metrics(self) -> Dict:
        """Collect metrics from LinkedIn.

        Returns:
            Dictionary with LinkedIn metrics
        """
        # TODO: Implement LinkedIn metrics collection
        # LinkedIn UGC Post Statistics API
        posts = self._load_recent_posts("linkedin")
        return {"posts": [], "total_engagement": 0}

    async def collect_reddit_metrics(self) -> Dict:
        """Collect metrics from Reddit.

        Returns:
            Dictionary with Reddit metrics
        """
        # TODO: Implement Reddit metrics collection
        # Reddit API: /api/info.json?id=post_id
        posts = self._load_recent_posts("reddit")
        return {"posts": [], "total_engagement": 0}

    def _load_recent_posts(self, platform: str, days: int = 7) -> List[Dict]:
        """Load posts from last N days for a platform.

        Args:
            platform: Platform name (x, instagram, tiktok, linkedin, reddit)
            days: Number of days to look back

        Returns:
            List of post dictionaries
        """
        # Posts should be stored by post-content skill after successful posting
        posts_dir = self.data_dir / "posts" / platform

        if not posts_dir.exists():
            return []

        # Load all post files from last N days
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_posts = []

        for post_file in posts_dir.glob("*.json"):
            try:
                post_data = json.loads(post_file.read_text())
                posted_at = datetime.fromisoformat(post_data["posted_at"])

                if posted_at >= cutoff:
                    recent_posts.append(post_data)
            except Exception as e:
                print(f"Error loading post file {post_file}: {e}")

        return recent_posts


async def main():
    """Run metrics collection."""
    data_dir = Path("./data/memory")
    collector = MetricsCollector(data_dir)

    print("📊 Collecting engagement metrics...")
    metrics = await collector.collect_all()

    print(f"✅ Metrics collected and saved to {collector.metrics_dir}")
    print(f"Total platforms: {len(metrics['platforms'])}")

    for platform, data in metrics["platforms"].items():
        print(f"  - {platform}: {data.get('total_engagement', 0)} total engagement")


if __name__ == "__main__":
    asyncio.run(main())
