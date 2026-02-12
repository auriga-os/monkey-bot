"""Tests for request-approval skill."""

import asyncio
import json
import pytest
from pathlib import Path
import sys

# Add skills directory to path
sys.path.insert(
    0,
    str(Path(__file__).parent.parent.parent / "skills" / "request-approval"),
)

from request_approval import (
    request_approval,
    create_approval_record,
    wait_for_approval,
    ApprovalResult,
    APPROVALS_DIR,
)


@pytest.fixture
def approvals_dir(tmp_path, monkeypatch):
    """Create temporary approvals directory."""
    approvals = tmp_path / "approvals"
    approvals.mkdir()
    monkeypatch.setattr(
        "request_approval.APPROVALS_DIR",
        approvals,
    )
    return approvals


class TestApprovalRecordCreation:
    """Tests for approval record creation."""

    def test_create_approval_record(self, approvals_dir):
        """Test: Approval record is created with correct structure."""
        approval_id = create_approval_record(
            content="Test post", content_type="social_post", platform="instagram"
        )

        assert approval_id
        approval_file = approvals_dir / f"{approval_id}.json"
        assert approval_file.exists()

        data = json.loads(approval_file.read_text())
        assert data["id"] == approval_id
        assert data["content"] == "Test post"
        assert data["status"] == "pending"
        assert data["content_type"] == "social_post"
        assert data["platform"] == "instagram"

    def test_create_approval_record_without_platform(self, approvals_dir):
        """Test: Approval record can be created without platform."""
        approval_id = create_approval_record(
            content="Test campaign", content_type="campaign", platform=None
        )

        approval_file = approvals_dir / f"{approval_id}.json"
        data = json.loads(approval_file.read_text())
        assert data["platform"] is None


class TestApprovalWaiting:
    """Tests for approval waiting logic."""

    @pytest.mark.asyncio
    async def test_wait_for_approval_approved(self, approvals_dir):
        """Test: Waiting for approval returns when approved."""
        approval_id = create_approval_record("Test", "social_post", "x")

        # Simulate user approving after 1 second
        async def approve_later():
            await asyncio.sleep(1)
            approval_file = approvals_dir / f"{approval_id}.json"
            data = json.loads(approval_file.read_text())
            data["status"] = "approved"
            data["feedback"] = "Looks good!"
            approval_file.write_text(json.dumps(data))

        asyncio.create_task(approve_later())

        result = await wait_for_approval(approval_id, timeout_seconds=5)
        assert result.approved is True
        assert result.feedback == "Looks good!"

    @pytest.mark.asyncio
    async def test_wait_for_approval_rejected(self, approvals_dir):
        """Test: Waiting for approval returns when rejected."""
        approval_id = create_approval_record("Test", "social_post", "x")

        # Simulate user rejecting
        async def reject_later():
            await asyncio.sleep(1)
            approval_file = approvals_dir / f"{approval_id}.json"
            data = json.loads(approval_file.read_text())
            data["status"] = "rejected"
            data["feedback"] = "Change hashtags"
            approval_file.write_text(json.dumps(data))

        asyncio.create_task(reject_later())

        result = await wait_for_approval(approval_id, timeout_seconds=5)
        assert result.approved is False
        assert result.feedback == "Change hashtags"

    @pytest.mark.asyncio
    async def test_wait_for_approval_timeout(self, approvals_dir):
        """Test: Timeout raises TimeoutError."""
        approval_id = create_approval_record("Test", "social_post", "x")

        with pytest.raises(TimeoutError, match="Approval timeout"):
            await wait_for_approval(approval_id, timeout_seconds=2)

    @pytest.mark.asyncio
    async def test_wait_for_approval_missing_file(self, approvals_dir):
        """Test: Missing approval file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Approval record not found"):
            await wait_for_approval("nonexistent-id", timeout_seconds=2)


class TestRequestApprovalIntegration:
    """Integration tests for complete approval flow."""

    @pytest.mark.asyncio
    async def test_request_approval_success(self, approvals_dir):
        """Test: Complete approval flow succeeds."""
        # Use short timeout for test
        result = await request_approval(
            content="Test post",
            content_type="social_post",
            platform="instagram",
            timeout_seconds=5,
        )

        # Auto-approve logic should approve after 2 seconds
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_request_approval_campaign(self, approvals_dir):
        """Test: Approval works for campaign content type."""
        result = await request_approval(
            content="Campaign plan",
            content_type="campaign",
            platform=None,
            timeout_seconds=5,
        )

        assert result.approved is True

    @pytest.mark.asyncio
    async def test_approval_result_structure(self, approvals_dir):
        """Test: ApprovalResult has correct structure."""
        result = await request_approval(
            content="Test", content_type="social_post", platform="x", timeout_seconds=5
        )

        assert hasattr(result, "approved")
        assert hasattr(result, "feedback")
        assert hasattr(result, "modified_content")
        assert hasattr(result, "timestamp")
        assert isinstance(result.approved, bool)
