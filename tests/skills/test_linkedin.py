"""Tests for LinkedIn posting platform."""

import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "post-content"))

from platforms.linkedin import post_to_linkedin


class TestLinkedInPosting:
    """Tests for LinkedIn posting."""

    def test_post_text_only(self):
        """Test: Posting text-only content succeeds."""
        result = post_to_linkedin(
            content="Exciting news about our product launch! #innovation #tech"
        )

        assert "post_id" in result
        assert "post_url" in result
        assert "linkedin.com" in result["post_url"]

    def test_post_with_image(self):
        """Test: Posting with image succeeds."""
        result = post_to_linkedin(
            content="Check out our new feature!",
            media_urls=["https://example.com/feature.jpg"]
        )

        assert result["post_id"]
        assert result["post_url"]

    def test_post_with_multiple_images(self):
        """Test: Posting with multiple images (up to 9) succeeds."""
        result = post_to_linkedin(
            content="Photo gallery from our event!",
            media_urls=[
                f"https://example.com/img{i}.jpg" for i in range(5)
            ]
        )

        assert result["post_id"]
        assert result["post_url"]

    def test_post_content_too_long(self):
        """Test: Content >3000 chars raises ValueError."""
        long_content = "a" * 3050

        with pytest.raises(ValueError, match="Content too long"):
            post_to_linkedin(content=long_content)

    def test_post_empty_content(self):
        """Test: Empty content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            post_to_linkedin(content="")

    def test_post_whitespace_only_content(self):
        """Test: Whitespace-only content raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            post_to_linkedin(content="   \n\t  ")

    def test_post_optimal_length(self):
        """Test: Post with optimal length (150-250 chars) succeeds."""
        optimal_content = "A" * 200  # Within optimal range

        result = post_to_linkedin(content=optimal_content)

        assert result["post_id"]
        assert result["post_url"]

    def test_post_url_format(self):
        """Test: Post URL has correct LinkedIn format."""
        result = post_to_linkedin(content="Test post for our network")

        assert result["post_url"].startswith("https://www.linkedin.com/feed/update/")

    def test_post_with_visibility_public(self):
        """Test: Posting with PUBLIC visibility succeeds."""
        result = post_to_linkedin(
            content="Public announcement!",
            visibility="PUBLIC"
        )

        assert result["post_id"]
        assert result["post_url"]

    def test_post_with_visibility_connections(self):
        """Test: Posting with CONNECTIONS visibility succeeds."""
        result = post_to_linkedin(
            content="Just for my network",
            visibility="CONNECTIONS"
        )

        assert result["post_id"]
        assert result["post_url"]
