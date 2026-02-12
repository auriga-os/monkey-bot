"""Tests for generate-post skill."""

import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "generate-post"))

from generate_post import (
    generate_post,
    load_brand_voice,
    validate_post,
    PostContent,
    ValidationResult,
)
from platform_config import VALID_PLATFORMS, get_platform_limit


class TestPlatformLimits:
    """Tests for platform limits."""

    def test_get_platform_limit_valid(self):
        """Test: Valid platforms return limits."""
        limits = get_platform_limit("instagram")
        assert limits["char_limit"] == 2200
        assert limits["max_hashtags"] == 30

    def test_get_platform_limit_invalid(self):
        """Test: Invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_platform_limit("facebook")

    def test_all_valid_platforms_have_limits(self):
        """Test: All valid platforms have complete limit data."""
        for platform in VALID_PLATFORMS:
            limits = get_platform_limit(platform)
            assert "char_limit" in limits
            assert "max_hashtags" in limits
            assert "hashtag_recommended" in limits


class TestBrandVoiceLoading:
    """Tests for brand voice loading."""

    def test_load_brand_voice_missing_file(self, tmp_path, monkeypatch):
        """Test: Missing brand voice file returns None with warning."""
        monkeypatch.setattr("generate_post.BRAND_VOICE_PATH", tmp_path / "missing.md")

        brand_voice = load_brand_voice()
        assert brand_voice is None

    def test_load_brand_voice_existing_file(self, tmp_path, monkeypatch):
        """Test: Existing brand voice file is loaded."""
        brand_voice_file = tmp_path / "BRAND_VOICE.md"
        brand_voice_file.write_text("Our brand is professional and helpful.")

        monkeypatch.setattr("generate_post.BRAND_VOICE_PATH", brand_voice_file)

        brand_voice = load_brand_voice()
        assert "professional" in brand_voice


class TestPostValidation:
    """Tests for post validation."""

    def test_validate_post_within_limit(self):
        """Test: Content within limit passes validation."""
        content = "Short post about AI"
        validation = validate_post(content, "x", [], None)
        assert validation.within_limit is True

    def test_validate_post_exceeds_limit(self):
        """Test: Content exceeding limit fails validation."""
        content = "a" * 300  # X limit is 280
        validation = validate_post(content, "x", [], None)
        assert validation.within_limit is False

    def test_validate_post_has_hook(self):
        """Test: Content with hook passes validation."""
        content = "Discover how AI agents work\n\nDetails here..."
        validation = validate_post(content, "instagram", [], None)
        assert validation.has_hook is True

    def test_validate_post_has_cta(self):
        """Test: Content with CTA passes validation."""
        content = "AI agents are powerful. Learn more about them!"
        validation = validate_post(content, "instagram", [], None)
        assert validation.has_cta is True

    def test_validate_post_brand_voice_forbidden_phrase(self):
        """Test: Forbidden phrase fails brand voice validation."""
        content = "Buy now! Limited time offer on AI agents!"
        brand_voice = "We never use salesy language."
        validation = validate_post(content, "instagram", [], brand_voice)
        assert validation.brand_voice_valid is False


class TestPostGeneration:
    """Tests for complete post generation."""

    def test_generate_post_instagram(self):
        """Test: Generate Instagram post within limits."""
        post = generate_post("AI agents", "instagram")

        assert isinstance(post, PostContent)
        assert post.platform == "instagram"
        assert len(post.content) <= 2200
        assert len(post.hashtags) >= 3
        assert post.validation.within_limit is True

    def test_generate_post_x(self):
        """Test: Generate X post within 280 chars."""
        post = generate_post("AI agents", "x")

        assert post.platform == "x"
        assert len(post.content) <= 280
        assert post.character_count == len(post.content)

    def test_generate_post_linkedin(self):
        """Test: Generate LinkedIn post with professional tone."""
        post = generate_post("AI agents", "linkedin", tone="professional")

        assert post.platform == "linkedin"
        assert len(post.content) <= 3000

    def test_generate_post_invalid_platform(self):
        """Test: Invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Invalid platform"):
            generate_post("AI agents", "facebook")

    def test_generate_post_without_hashtags(self):
        """Test: Can generate post without hashtags."""
        post = generate_post("AI agents", "reddit", include_hashtags=False)

        assert post.platform == "reddit"
        assert len(post.hashtags) == 0

    def test_generate_post_tiktok(self):
        """Test: Generate TikTok post."""
        post = generate_post("AI agents", "tiktok")

        assert post.platform == "tiktok"
        assert len(post.content) <= 2200
        assert post.validation.within_limit is True

    def test_post_content_structure(self):
        """Test: PostContent has correct structure."""
        post = generate_post("Test topic", "instagram")

        assert hasattr(post, "platform")
        assert hasattr(post, "content")
        assert hasattr(post, "hashtags")
        assert hasattr(post, "character_count")
        assert hasattr(post, "validation")
        assert isinstance(post.validation, ValidationResult)

    def test_validation_result_structure(self):
        """Test: ValidationResult has correct structure."""
        post = generate_post("Test topic", "instagram")
        validation = post.validation

        assert hasattr(validation, "within_limit")
        assert hasattr(validation, "has_hook")
        assert hasattr(validation, "has_cta")
        assert hasattr(validation, "brand_voice_valid")
        assert hasattr(validation, "readability_score")
