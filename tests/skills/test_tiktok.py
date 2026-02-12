"""Tests for TikTok posting platform."""

import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "post-content"))

from platforms.tiktok import post_to_tiktok


class TestTikTokPosting:
    """Tests for TikTok posting."""

    def test_post_video_success(self):
        """Test: Posting video returns mock result."""
        result = post_to_tiktok(
            content="Check out this cool video! #fyp #viral",
            media_urls=["https://example.com/video.mp4"]
        )

        assert "post_id" in result
        assert "post_url" in result
        assert "tiktok.com" in result["post_url"]

    def test_post_without_video_fails(self):
        """Test: Posting without video raises ValueError."""
        with pytest.raises(ValueError, match="TikTok requires exactly 1 video"):
            post_to_tiktok(content="Test post", media_urls=[])

    def test_post_with_image_fails(self):
        """Test: TikTok only accepts videos."""
        with pytest.raises(ValueError, match="must be a video file"):
            post_to_tiktok(
                content="Test",
                media_urls=["https://example.com/image.jpg"]
            )

    def test_post_with_multiple_videos_fails(self):
        """Test: TikTok accepts only 1 video at a time."""
        with pytest.raises(ValueError, match="exactly 1 video"):
            post_to_tiktok(
                content="Test",
                media_urls=[
                    "https://example.com/video1.mp4",
                    "https://example.com/video2.mp4"
                ]
            )

    def test_post_caption_too_long(self):
        """Test: Caption >2200 chars raises ValueError."""
        long_caption = "a" * 2250

        with pytest.raises(ValueError, match="Description too long"):
            post_to_tiktok(
                content=long_caption,
                media_urls=["https://example.com/video.mp4"]
            )

    def test_post_with_valid_video_formats(self):
        """Test: Various video formats are accepted."""
        valid_formats = [
            "https://example.com/video.mp4",
            "https://example.com/video.mov",
            "https://example.com/video.avi",
            "https://example.com/video.webm"
        ]

        for video_url in valid_formats:
            result = post_to_tiktok(
                content="Test video",
                media_urls=[video_url]
            )
            assert result["post_id"]
            assert result["post_url"]

    def test_post_empty_caption(self):
        """Test: Posting with empty caption but video succeeds."""
        result = post_to_tiktok(
            content="",
            media_urls=["https://example.com/video.mp4"]
        )

        assert result["post_id"]
        assert result["post_url"]

    def test_post_url_format(self):
        """Test: Post URL has correct TikTok format."""
        result = post_to_tiktok(
            content="Test video #fyp",
            media_urls=["https://example.com/video.mp4"]
        )

        # URL should include username placeholder and video ID
        assert "/@" in result["post_url"]
        assert "/video/" in result["post_url"]
