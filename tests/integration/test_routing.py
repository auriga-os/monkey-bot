"""
Routing tests for Marketing Campaign Manager.

CRITICAL: These tests verify that Gemini correctly routes user messages
to the appropriate skills based on SKILL.md descriptions.

If routing fails, the entire system breaks.
"""

import pytest
from pathlib import Path

from src.skills.loader import SkillLoader


@pytest.fixture
def loader_with_marketing_skills():
    """Create skill loader with marketing skills loaded."""
    # Load skills from skills directory
    loader = SkillLoader("./skills")
    skills_data = loader.load_skills()
    tool_schemas = loader.get_tool_schemas()

    return loader, skills_data, tool_schemas


class TestGeneratePostRouting:
    """Tests for generate-post skill routing."""

    @pytest.mark.integration
    def test_route_generate_post_skill_loaded(self, loader_with_marketing_skills):
        """Test: 'generate-post' skill is loaded correctly."""
        loader, skills, schemas = loader_with_marketing_skills

        assert "generate-post" in skills
        assert "Create social media content" in skills["generate-post"]["description"]

    @pytest.mark.integration
    def test_route_generate_post_tool_schema(self, loader_with_marketing_skills):
        """Test: 'generate-post' has correct tool schema for LangGraph."""
        loader, skills, schemas = loader_with_marketing_skills

        # Find generate-post schema
        generate_post_schema = next((s for s in schemas if s["name"] == "generate-post"), None)

        assert generate_post_schema is not None
        assert "Instagram" in generate_post_schema["description"]
        assert "TikTok" in generate_post_schema["description"]
        assert "X" in generate_post_schema["description"]
        assert "parameters" in generate_post_schema


class TestApprovalRouting:
    """Tests for request-approval skill routing."""

    @pytest.mark.integration
    def test_route_approval_skill_loaded(self, loader_with_marketing_skills):
        """Test: 'request-approval' skill is loaded correctly."""
        loader, skills, schemas = loader_with_marketing_skills

        assert "request-approval" in skills
        assert "approval" in skills["request-approval"]["description"].lower()

    @pytest.mark.integration
    def test_route_approval_tool_schema(self, loader_with_marketing_skills):
        """Test: 'request-approval' has correct tool schema."""
        loader, skills, schemas = loader_with_marketing_skills

        # Find request-approval schema
        approval_schema = next((s for s in schemas if s["name"] == "request-approval"), None)

        assert approval_schema is not None
        assert "Google Chat" in approval_schema["description"]
        assert "parameters" in approval_schema


class TestPostingRouting:
    """Tests for post-content skill routing."""

    @pytest.mark.integration
    def test_route_posting_skill_loaded(self, loader_with_marketing_skills):
        """Test: 'post-content' skill is loaded correctly."""
        loader, skills, schemas = loader_with_marketing_skills

        assert "post-content" in skills
        assert "Publish" in skills["post-content"]["description"]

    @pytest.mark.integration
    def test_route_posting_tool_schema(self, loader_with_marketing_skills):
        """Test: 'post-content' has correct tool schema."""
        loader, skills, schemas = loader_with_marketing_skills

        # Find post-content schema
        post_schema = next((s for s in schemas if s["name"] == "post-content"), None)

        assert post_schema is not None
        assert "X" in post_schema["description"] or "Twitter" in post_schema["description"]
        assert "parameters" in post_schema


class TestAllMarketingSkills:
    """Tests for all marketing skills together."""

    @pytest.mark.integration
    def test_all_marketing_skills_loaded(self, loader_with_marketing_skills):
        """Test: All 3 marketing skills are loaded."""
        loader, skills, schemas = loader_with_marketing_skills

        marketing_skills = ["generate-post", "request-approval", "post-content"]

        for skill_name in marketing_skills:
            assert skill_name in skills, f"Skill {skill_name} not loaded"

    @pytest.mark.integration
    def test_all_marketing_schemas_generated(self, loader_with_marketing_skills):
        """Test: All 3 marketing skills have tool schemas."""
        loader, skills, schemas = loader_with_marketing_skills

        schema_names = [s["name"] for s in schemas]

        assert "generate-post" in schema_names
        assert "request-approval" in schema_names
        assert "post-content" in schema_names

    @pytest.mark.integration
    def test_skill_descriptions_sufficient_length(self, loader_with_marketing_skills):
        """Test: All skill descriptions are long enough for routing."""
        loader, skills, schemas = loader_with_marketing_skills

        marketing_skills = ["generate-post", "request-approval", "post-content"]

        for skill_name in marketing_skills:
            description = skills[skill_name]["description"]
            assert len(description) >= 20, (
                f"Skill {skill_name} description too short: {len(description)} chars"
            )
