"""Tests for Reddit posting platform."""

import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "post-content"))

from platforms.reddit import post_to_reddit


class TestRedditPosting:
    """Tests for Reddit posting."""

    def test_post_text_success(self):
        """Test: Posting text post with title succeeds."""
        result = post_to_reddit(
            content="This is an exciting announcement about our new product!",
            subreddit="technology",
            title="Announcing our new AI tool"
        )

        assert "post_id" in result
        assert "post_url" in result
        assert "reddit.com" in result["post_url"]
        assert "/r/technology/" in result["post_url"]

    def test_post_link_success(self):
        """Test: Posting link post succeeds."""
        result = post_to_reddit(
            content="https://example.com/article",
            subreddit="programming",
            title="Interesting article about AI",
            post_type="link"
        )

        assert result["post_id"]
        assert result["post_url"]

    def test_post_without_title(self):
        """Test: Posting without title raises ValueError."""
        with pytest.raises(ValueError, match="Reddit posts require a 'title'"):
            post_to_reddit(
                content="Test content",
                subreddit="test"
            )

    def test_post_without_subreddit(self):
        """Test: Posting without subreddit raises ValueError."""
        with pytest.raises(ValueError, match="subreddit is required"):
            post_to_reddit(
                content="Test content",
                subreddit="",
                title="Test title"
            )

    def test_post_title_too_long(self):
        """Test: Title >300 chars raises ValueError."""
        long_title = "a" * 350

        with pytest.raises(ValueError, match="Title too long"):
            post_to_reddit(
                content="Test content",
                subreddit="test",
                title=long_title
            )

    def test_post_empty_content(self):
        """Test: Empty content for text post raises ValueError."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            post_to_reddit(
                content="",
                subreddit="test",
                title="Test title"
            )

    def test_post_link_with_valid_url(self):
        """Test: Link post with valid URL succeeds."""
        result = post_to_reddit(
            content="https://example.com/page",
            subreddit="test",
            title="Check this out",
            post_type="link"
        )

        assert result["post_id"]
        assert result["post_url"]

    def test_post_link_with_invalid_url(self):
        """Test: Link post with invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Link posts must have a valid URL"):
            post_to_reddit(
                content="not a url",
                subreddit="test",
                title="Test title",
                post_type="link"
            )

    def test_post_url_format(self):
        """Test: Post URL has correct Reddit format."""
        result = post_to_reddit(
            content="Test content",
            subreddit="python",
            title="Python programming tips"
        )

        assert "/r/python/comments/" in result["post_url"]

    def test_post_with_flair(self):
        """Test: Posting with flair succeeds."""
        result = post_to_reddit(
            content="Test content",
            subreddit="test",
            title="Test title",
            flair_id="abc123"
        )

        assert result["post_id"]
        assert result["post_url"]

    def test_post_id_format(self):
        """Test: Post ID has Reddit format (t3_xxxxx)."""
        result = post_to_reddit(
            content="Test content",
            subreddit="test",
            title="Test title"
        )

        assert result["post_id"].startswith("t3_")
