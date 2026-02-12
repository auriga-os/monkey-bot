"""Tests for post-content skill."""

import json
import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "skills" / "post-content"))

from post_content import (
    post_content,
    verify_approval,
    save_post_record,
    PostResult,
    APPROVALS_DIR,
    POSTS_DIR,
)
from platforms.x import post_to_x


@pytest.fixture
def setup_dirs(tmp_path, monkeypatch):
    """Set up temporary directories."""
    approvals = tmp_path / "approvals"
    posts = tmp_path / "posts"
    approvals.mkdir()
    posts.mkdir()

    monkeypatch.setattr("post_content.APPROVALS_DIR", approvals)
    monkeypatch.setattr("post_content.POSTS_DIR", posts)

    return approvals, posts


class TestApprovalVerification:
    """Tests for approval verification."""

    def test_verify_approval_missing_id(self):
        """Test: Missing approval_id raises ValueError."""
        with pytest.raises(ValueError, match="Cannot post without approval"):
            verify_approval(None)

    def test_verify_approval_not_found(self, setup_dirs):
        """Test: Non-existent approval raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Approval record not found"):
            verify_approval("nonexistent-id")

    def test_verify_approval_not_approved(self, setup_dirs):
        """Test: Non-approved content raises RuntimeError."""
        approvals_dir, _ = setup_dirs

        # Create pending approval
        approval_file = approvals_dir / "test-id.json"
        approval_file.write_text(json.dumps({"status": "pending"}))

        with pytest.raises(RuntimeError, match="Content not approved"):
            verify_approval("test-id")

    def test_verify_approval_success(self, setup_dirs):
        """Test: Approved content passes verification."""
        approvals_dir, _ = setup_dirs

        # Create approved record
        approval_file = approvals_dir / "test-id.json"
        approval_file.write_text(json.dumps({"status": "approved"}))

        # Should not raise
        verify_approval("test-id")


class TestXPlatformPosting:
    """Tests for X (Twitter) posting."""

    def test_post_to_x_success(self):
        """Test: Posting to X returns mock result."""
        result = post_to_x("Hello world! #AI")

        assert "post_id" in result
        assert "post_url" in result
        assert "x.com" in result["post_url"]

    def test_post_to_x_too_long(self):
        """Test: Content >280 chars raises ValueError."""
        long_content = "a" * 300

        with pytest.raises(ValueError, match="Content too long"):
            post_to_x(long_content)

    def test_post_to_x_with_media(self):
        """Test: Posting with media URLs works."""
        result = post_to_x("Check out this image!", ["https://example.com/img.jpg"])

        assert result["post_id"]
        assert result["post_url"]


class TestPostRecordSaving:
    """Tests for post record saving."""

    def test_save_post_record(self, setup_dirs):
        """Test: Post record is saved correctly."""
        _, posts_dir = setup_dirs

        result = PostResult(
            platform="x",
            platform_post_id="123456789",
            platform_post_url="https://x.com/test/status/123456789",
            posted_at="1234567890",
        )

        save_post_record("Test content", "x", result)

        post_file = posts_dir / "123456789.json"
        assert post_file.exists()

        data = json.loads(post_file.read_text())
        assert data["post_id"] == "123456789"
        assert data["platform"] == "x"
        assert data["content"] == "Test content"


class TestPostContentIntegration:
    """Integration tests for complete posting flow."""

    def test_post_content_success(self, setup_dirs):
        """Test: Complete posting flow succeeds."""
        approvals_dir, posts_dir = setup_dirs

        # Create approved record
        approval_id = "test-approval"
        approval_file = approvals_dir / f"{approval_id}.json"
        approval_file.write_text(json.dumps({"status": "approved"}))

        # Post content
        result = post_content(
            content="Hello world! #AI",
            platform="x",
            approval_id=approval_id,
        )

        assert result.platform == "x"
        assert result.platform_post_url
        assert result.platform_post_id

        # Verify post record saved
        post_files = list(posts_dir.glob("*.json"))
        assert len(post_files) == 1

    def test_post_content_without_approval(self, setup_dirs):
        """Test: Posting without approval fails."""
        with pytest.raises(ValueError, match="Cannot post without approval"):
            post_content(
                content="Hello world!",
                platform="x",
                approval_id=None,
            )

    def test_post_content_with_media(self, setup_dirs):
        """Test: Posting with media URLs works."""
        approvals_dir, _ = setup_dirs

        # Create approved record
        approval_id = "test-approval-media"
        approval_file = approvals_dir / f"{approval_id}.json"
        approval_file.write_text(json.dumps({"status": "approved"}))

        # Post with media
        result = post_content(
            content="Check this out!",
            platform="x",
            media_urls=["https://example.com/img.jpg"],
            approval_id=approval_id,
        )

        assert result.platform_post_url

    def test_post_content_invalid_platform(self, setup_dirs):
        """Test: Invalid platform raises ValueError."""
        approvals_dir, _ = setup_dirs

        # Create approved record
        approval_id = "test-approval-invalid"
        approval_file = approvals_dir / f"{approval_id}.json"
        approval_file.write_text(json.dumps({"status": "approved"}))

        with pytest.raises(ValueError, match="not supported"):
            post_content(
                content="Test",
                platform="facebook",  # type: ignore
                approval_id=approval_id,
            )

    def test_post_result_structure(self, setup_dirs):
        """Test: PostResult has correct structure."""
        approvals_dir, _ = setup_dirs

        # Create approved record
        approval_id = "test-approval-structure"
        approval_file = approvals_dir / f"{approval_id}.json"
        approval_file.write_text(json.dumps({"status": "approved"}))

        result = post_content(
            content="Test post",
            platform="x",
            approval_id=approval_id,
        )

        assert hasattr(result, "platform")
        assert hasattr(result, "platform_post_id")
        assert hasattr(result, "platform_post_url")
        assert hasattr(result, "posted_at")
        assert isinstance(result.platform, str)
