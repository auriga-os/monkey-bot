"""
End-to-end workflow tests for Marketing Campaign Manager.

Tests complete workflows by verifying data flow through filesystem artifacts.
"""

import asyncio
import json
import pytest
from pathlib import Path
import sys

# Add generate-post to path (it will be tested separately from post-content)
skills_path = Path(__file__).parent.parent.parent / "skills"
sys.path.insert(0, str(skills_path / "generate-post"))
from generate_post import generate_post

sys.path.pop(0)

# Add request-approval to path
sys.path.insert(0, str(skills_path / "request-approval"))
from request_approval import request_approval

sys.path.pop(0)


@pytest.fixture
def setup_workflow_dirs(tmp_path, monkeypatch):
    """Set up temporary directories for workflow."""
    approvals_dir = tmp_path / "approvals"
    approvals_dir.mkdir()

    # Patch approval skill to use temp dir
    monkeypatch.setattr("request_approval.APPROVALS_DIR", approvals_dir)

    return approvals_dir


@pytest.mark.integration
class TestCompletePostWorkflow:
    """Tests for Generate → Approve workflow (without posting)."""

    @pytest.mark.asyncio
    async def test_generate_and_approve_instagram(self, setup_workflow_dirs):
        """Test: Generate and approve Instagram post."""
        approvals_dir = setup_workflow_dirs

        # Step 1: Generate post
        post = generate_post("AI agents", "instagram")
        assert post.content
        assert len(post.content) <= 2200

        # Step 2: Request approval
        approval = await request_approval(
            content=post.content,
            content_type="social_post",
            platform="instagram",
            timeout_seconds=5,
        )
        assert approval.approved

        # Verify approval record exists
        approval_files = list(approvals_dir.glob("*.json"))
        assert len(approval_files) == 1

    @pytest.mark.asyncio
    async def test_generate_and_approve_x(self, setup_workflow_dirs):
        """Test: Generate and approve X post."""
        approvals_dir = setup_workflow_dirs

        # Step 1: Generate post
        post = generate_post("AI agents", "x")
        assert post.content
        assert len(post.content) <= 280

        # Step 2: Request approval
        approval = await request_approval(
            content=post.content,
            content_type="social_post",
            platform="x",
            timeout_seconds=5,
        )
        assert approval.approved

        # Verify approval record
        approval_files = list(approvals_dir.glob("*.json"))
        assert len(approval_files) == 1

    @pytest.mark.asyncio
    async def test_rejection_workflow(self, setup_workflow_dirs):
        """Test: Rejection workflow (generate → reject)."""
        approvals_dir = setup_workflow_dirs

        # Generate post
        post = generate_post("AI agents", "instagram")

        # Request approval but manually reject
        async def reject_approval():
            await asyncio.sleep(1)
            approval_files = list(approvals_dir.glob("*.json"))
            if approval_files:
                data = json.loads(approval_files[0].read_text())
                data["status"] = "rejected"
                data["feedback"] = "Change the hashtags"
                approval_files[0].write_text(json.dumps(data))

        asyncio.create_task(reject_approval())

        approval = await request_approval(
            content=post.content,
            content_type="social_post",
            platform="instagram",
            timeout_seconds=5,
        )

        assert not approval.approved
        assert approval.feedback == "Change the hashtags"


class TestErrorHandling:
    """Tests for error handling in workflows."""

    def test_invalid_platform_fails(self):
        """Test: Invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Invalid platform"):
            generate_post("AI agents", "facebook")  # type: ignore

    @pytest.mark.asyncio
    async def test_approval_timeout(self, setup_workflow_dirs):
        """Test: Approval timeout raises TimeoutError."""
        approvals_dir = setup_workflow_dirs

        post = generate_post("Test", "x")

        with pytest.raises(TimeoutError, match="Approval timeout"):
            await request_approval(
                content=post.content,
                content_type="social_post",
                platform="x",
                timeout_seconds=2,  # Will timeout since no auto-approve
            )


@pytest.mark.integration
class TestDataFlow:
    """Tests for data flow between skills."""

    @pytest.mark.asyncio
    async def test_content_passes_through_approval(self, setup_workflow_dirs):
        """Test: Content flows correctly through generation and approval."""
        approvals_dir = setup_workflow_dirs

        # Generate with specific topic
        topic = "Machine Learning"
        post = generate_post(topic, "x")

        # Verify topic is in content
        assert topic.lower() in post.content.lower()

        # Approve
        approval = await request_approval(
            content=post.content,
            content_type="social_post",
            platform="x",
            timeout_seconds=5,
        )

        # Verify content is in approval record
        approval_files = list(approvals_dir.glob("*.json"))
        approval_data = json.loads(approval_files[0].read_text())
        assert topic.lower() in approval_data["content"].lower()
        assert approval_data["status"] == "approved"

    @pytest.mark.asyncio
    async def test_approval_record_structure(self, setup_workflow_dirs):
        """Test: Approval records have correct structure for downstream use."""
        approvals_dir = setup_workflow_dirs

        # Generate and approve
        post = generate_post("Test topic", "x")
        approval = await request_approval(
            content=post.content,
            content_type="social_post",
            platform="x",
            timeout_seconds=5,
        )

        # Verify approval record structure
        approval_files = list(approvals_dir.glob("*.json"))
        approval_data = json.loads(approval_files[0].read_text())

        # Check all required fields for post-content skill
        assert "id" in approval_data
        assert "status" in approval_data
        assert "content" in approval_data
        assert approval_data["status"] == "approved"
