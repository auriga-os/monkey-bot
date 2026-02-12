"""Integration tests for generate-post skill."""

import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "generate-post"))

from generate_post import generate_post


@pytest.mark.integration
class TestGeneratePostIntegration:
    """Integration tests for generate-post skill."""

    def test_generate_all_platforms(self):
        """Test: Generate posts for all platforms successfully."""
        platforms = ["instagram", "tiktok", "x", "linkedin", "reddit"]

        for platform in platforms:
            post = generate_post("AI agents", platform)

            assert post.platform == platform
            assert post.content
            assert post.character_count > 0
            assert post.validation.within_limit

    def test_generate_with_different_topics(self):
        """Test: Generate posts with various topics."""
        topics = [
            "AI agent evaluation",
            "Machine learning best practices",
            "Software engineering tips",
            "Cloud infrastructure",
        ]

        for topic in topics:
            post = generate_post(topic, "instagram")
            # Check that topic is mentioned in content (case insensitive)
            assert topic.split()[0].lower() in post.content.lower()

    def test_generate_with_different_tones(self):
        """Test: Generate posts with different tones."""
        tones = ["professional", "casual", "humorous"]

        for tone in tones:
            post = generate_post("AI agents", "instagram", tone=tone)
            assert post.content
            assert post.validation.within_limit

    def test_consistent_character_count(self):
        """Test: Character count matches actual content length."""
        post = generate_post("AI agents", "instagram")
        assert post.character_count == len(post.content)
