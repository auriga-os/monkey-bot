"""Tests for Instagram posting platform."""

import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "post-content"))

from platforms.instagram import post_to_instagram


class TestInstagramPosting:
    """Tests for Instagram posting."""

    def test_post_with_image_success(self):
        """Test: Posting with image returns mock result."""
        result = post_to_instagram(
            content="Amazing sunset! #photography",
            media_urls=["https://example.com/sunset.jpg"]
        )

        assert "post_id" in result
        assert "post_url" in result
        assert "instagram.com" in result["post_url"]

    def test_post_without_image_fails(self):
        """Test: Posting without media raises ValueError."""
        with pytest.raises(ValueError, match="At least 1 image required"):
            post_to_instagram(content="Test post", media_urls=[])

    def test_post_caption_too_long(self):
        """Test: Caption >2200 chars raises ValueError."""
        long_caption = "a" * 2250

        with pytest.raises(ValueError, match="Caption too long"):
            post_to_instagram(content=long_caption, media_urls=["https://example.com/img.jpg"])

    def test_post_too_many_hashtags(self):
        """Test: More than 30 hashtags raises ValueError."""
        hashtags = " ".join([f"#tag{i}" for i in range(35)])
        content = f"Great post! {hashtags}"

        with pytest.raises(ValueError, match="Too many hashtags"):
            post_to_instagram(content=content, media_urls=["https://example.com/img.jpg"])

    def test_post_multiple_images(self):
        """Test: Posting with multiple images works."""
        result = post_to_instagram(
            content="Photo carousel! #photography",
            media_urls=[
                "https://example.com/img1.jpg",
                "https://example.com/img2.jpg",
                "https://example.com/img3.jpg"
            ]
        )

        assert result["post_id"]
        assert result["post_url"]

    def test_post_with_valid_hashtags(self):
        """Test: Post with <=30 hashtags succeeds."""
        hashtags = " ".join([f"#tag{i}" for i in range(25)])
        content = f"Great post! {hashtags}"

        result = post_to_instagram(content=content, media_urls=["https://example.com/img.jpg"])

        assert result["post_id"]
        assert result["post_url"]

    def test_post_empty_caption(self):
        """Test: Posting with empty caption but with image succeeds."""
        result = post_to_instagram(content="", media_urls=["https://example.com/img.jpg"])

        assert result["post_id"]
        assert result["post_url"]

    def test_post_url_format(self):
        """Test: Post URL has correct Instagram format."""
        result = post_to_instagram(
            content="Test post",
            media_urls=["https://example.com/img.jpg"]
        )

        assert result["post_url"].startswith("https://instagram.com/p/")
