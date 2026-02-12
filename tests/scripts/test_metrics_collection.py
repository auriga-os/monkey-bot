"""Tests for metrics collection and reporting."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.collect_metrics import MetricsCollector
from scripts.generate_report import WeeklyReportGenerator


class TestMetricsCollector:
    """Test suite for MetricsCollector."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data directory with posts."""
        data_dir = tmp_path / "data" / "memory"
        data_dir.mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def collector(self, temp_data_dir):
        """Create MetricsCollector instance."""
        return MetricsCollector(temp_data_dir)

    @pytest.fixture
    def mock_x_posts(self, temp_data_dir):
        """Create mock X posts for testing."""
        posts_dir = temp_data_dir / "posts" / "x"
        posts_dir.mkdir(parents=True)

        # Create 3 recent posts
        for i in range(3):
            posted_at = datetime.utcnow() - timedelta(days=i)
            post_data = {
                "post_id": f"post_{i}",
                "post_url": f"https://x.com/user/status/123{i}",
                "content": f"Test post {i}",
                "posted_at": posted_at.isoformat(),
                "platform": "x"
            }
            post_file = posts_dir / f"{posted_at.strftime('%Y%m%d_%H%M%S')}_post_{i}.json"
            post_file.write_text(json.dumps(post_data))

        return posts_dir

    def test_load_recent_posts_success(self, collector, mock_x_posts):
        """Test loading recent posts from platform directory."""
        posts = collector._load_recent_posts("x", days=7)

        assert len(posts) == 3
        assert all(post["platform"] == "x" for post in posts)
        assert all("post_id" in post for post in posts)

    def test_load_recent_posts_empty_directory(self, collector):
        """Test loading posts from non-existent directory."""
        posts = collector._load_recent_posts("instagram", days=7)

        assert posts == []

    def test_load_recent_posts_filters_old_posts(self, collector, temp_data_dir):
        """Test that old posts are filtered out."""
        posts_dir = temp_data_dir / "posts" / "x"
        posts_dir.mkdir(parents=True)

        # Create one old post (10 days ago)
        old_post_date = datetime.utcnow() - timedelta(days=10)
        old_post = {
            "post_id": "old_post",
            "post_url": "https://x.com/user/status/old",
            "content": "Old post",
            "posted_at": old_post_date.isoformat(),
            "platform": "x"
        }
        old_post_file = posts_dir / f"{old_post_date.strftime('%Y%m%d_%H%M%S')}_old_post.json"
        old_post_file.write_text(json.dumps(old_post))

        # Create one recent post (2 days ago)
        recent_post_date = datetime.utcnow() - timedelta(days=2)
        recent_post = {
            "post_id": "recent_post",
            "post_url": "https://x.com/user/status/recent",
            "content": "Recent post",
            "posted_at": recent_post_date.isoformat(),
            "platform": "x"
        }
        recent_post_file = posts_dir / f"{recent_post_date.strftime('%Y%m%d_%H%M%S')}_recent_post.json"
        recent_post_file.write_text(json.dumps(recent_post))

        # Load posts from last 7 days
        posts = collector._load_recent_posts("x", days=7)

        assert len(posts) == 1
        assert posts[0]["post_id"] == "recent_post"

    @pytest.mark.asyncio
    async def test_collect_x_metrics_no_posts(self, collector):
        """Test X metrics collection when no posts exist."""
        metrics = await collector.collect_x_metrics()

        assert metrics == {"posts": [], "total_engagement": 0}

    @pytest.mark.asyncio
    async def test_collect_x_metrics_no_token(self, collector, mock_x_posts, monkeypatch):
        """Test X metrics collection when API token is not set."""
        # Unset X_ACCESS_TOKEN
        monkeypatch.delenv("X_ACCESS_TOKEN", raising=False)

        metrics = await collector.collect_x_metrics()

        assert metrics == {"posts": [], "total_engagement": 0}

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_collect_x_metrics_success(self, mock_client, collector, mock_x_posts, monkeypatch):
        """Test successful X metrics collection."""
        # Set up environment
        monkeypatch.setenv("X_ACCESS_TOKEN", "test_token")

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "public_metrics": {
                    "like_count": 10,
                    "retweet_count": 5,
                    "reply_count": 3,
                    "impression_count": 100
                }
            }
        }

        mock_client_instance = mock_client.return_value.__aenter__.return_value
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        # Collect metrics
        metrics = await collector.collect_x_metrics()

        # Verify results
        assert len(metrics["posts"]) == 3
        assert metrics["total_engagement"] > 0

    @pytest.mark.asyncio
    async def test_collect_all_saves_to_file(self, collector, mock_x_posts, monkeypatch):
        """Test that collect_all saves metrics to file."""
        monkeypatch.setenv("X_ACCESS_TOKEN", "test_token")

        with patch("httpx.AsyncClient"):
            await collector.collect_all()

        # Verify metrics file was created
        today = datetime.utcnow().strftime('%Y-%m-%d')
        metrics_file = collector.metrics_dir / f"{today}.json"

        assert metrics_file.exists()

        # Verify file contents
        metrics_data = json.loads(metrics_file.read_text())
        assert "collected_at" in metrics_data
        assert "platforms" in metrics_data
        assert "x" in metrics_data["platforms"]


class TestWeeklyReportGenerator:
    """Test suite for WeeklyReportGenerator."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data directory."""
        data_dir = tmp_path / "data" / "memory"
        data_dir.mkdir(parents=True)
        return data_dir

    @pytest.fixture
    def generator(self, temp_data_dir):
        """Create WeeklyReportGenerator instance."""
        return WeeklyReportGenerator(temp_data_dir, "https://chat.googleapis.com/test")

    @pytest.fixture
    def mock_metrics_files(self, temp_data_dir):
        """Create mock metrics files."""
        metrics_dir = temp_data_dir / "metrics"
        metrics_dir.mkdir(parents=True)

        # Create metrics for this week (3 days)
        for i in range(3):
            date = datetime.utcnow() - timedelta(days=i)
            metrics_data = {
                "collected_at": date.isoformat(),
                "platforms": {
                    "x": {
                        "total_engagement": 50 + i * 10,
                        "posts": [{"post_id": f"post_{i}", "total": 50 + i * 10}]
                    },
                    "instagram": {
                        "total_engagement": 30,
                        "posts": [{"post_id": f"ig_{i}", "total": 30}]
                    },
                    "tiktok": {"total_engagement": 0, "posts": []},
                    "linkedin": {"total_engagement": 0, "posts": []},
                    "reddit": {"total_engagement": 0, "posts": []}
                }
            }
            metrics_file = metrics_dir / f"{date.strftime('%Y-%m-%d')}.json"
            metrics_file.write_text(json.dumps(metrics_data))

        return metrics_dir

    def test_load_week_metrics(self, generator, mock_metrics_files):
        """Test loading metrics for a specific week."""
        metrics = generator._load_week_metrics(weeks_ago=0)

        assert "platforms" in metrics
        assert metrics["platforms"]["x"]["total_engagement"] > 0
        assert metrics["platforms"]["x"]["posts"] > 0

    def test_calculate_growth(self, generator):
        """Test growth calculation."""
        this_week = {
            "platforms": {
                "x": {"total_engagement": 150, "posts": 5},
                "instagram": {"total_engagement": 100, "posts": 3}
            }
        }
        last_week = {
            "platforms": {
                "x": {"total_engagement": 100, "posts": 5},
                "instagram": {"total_engagement": 100, "posts": 3}
            }
        }

        growth = generator._calculate_growth(this_week, last_week)

        assert growth["x"]["absolute"] == 50
        assert growth["x"]["percent"] == 50.0
        assert growth["instagram"]["absolute"] == 0
        assert growth["instagram"]["percent"] == 0.0

    def test_calculate_growth_from_zero(self, generator):
        """Test growth calculation when starting from zero."""
        this_week = {
            "platforms": {
                "x": {"total_engagement": 50, "posts": 2}
            }
        }
        last_week = {
            "platforms": {
                "x": {"total_engagement": 0, "posts": 0}
            }
        }

        growth = generator._calculate_growth(this_week, last_week)

        assert growth["x"]["percent"] == 100.0

    def test_format_report(self, generator):
        """Test report formatting."""
        this_week = {
            "platforms": {
                "x": {"total_engagement": 150, "posts": 5},
                "instagram": {"total_engagement": 100, "posts": 3},
                "tiktok": {"total_engagement": 0, "posts": 0}
            }
        }
        growth = {
            "x": {"absolute": 50, "percent": 50.0},
            "instagram": {"absolute": 0, "percent": 0.0},
            "tiktok": {"absolute": 0, "percent": 0.0}
        }

        report = generator._format_report(this_week, growth)

        assert "cards" in report
        assert len(report["cards"]) > 0
        assert "sections" in report["cards"][0]

        # Verify summary section exists
        sections = report["cards"][0]["sections"]
        assert len(sections) > 0
        assert "header" in sections[0]

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_to_google_chat_success(self, mock_client, generator):
        """Test successful Google Chat webhook."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client_instance = mock_client.return_value.__aenter__.return_value
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        report = {"cards": [{"sections": []}]}

        # Should not raise exception
        await generator._send_to_google_chat(report)

        mock_client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_send_to_google_chat_failure(self, mock_client, generator):
        """Test failed Google Chat webhook."""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        mock_client_instance = mock_client.return_value.__aenter__.return_value
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        report = {"cards": [{"sections": []}]}

        # Should raise exception
        with pytest.raises(Exception, match="Failed to send report"):
            await generator._send_to_google_chat(report)
