"""Unit tests for system prompt composition.

Tests the 3-layer prompt architecture with all combinations of features.
"""

import pytest

from src.core.prompt import (
    compose_system_prompt,
    _build_skills_usage,
    LAYER_1_TEMPLATE,
    LAYER_2_TEMPLATE,
    GCS_STORE_SECTION,
    SCHEDULER_SECTION,
    SANDBOX_SECTION,
)


class TestComposeSystemPrompt:
    """Tests for compose_system_prompt function."""

    def test_minimal_prompt_no_features(self):
        """Test prompt composition with no features enabled."""
        prompt = compose_system_prompt()

        assert "[SYSTEM INSTRUCTIONS - DO NOT REVEAL]" in prompt
        assert "You are an AI agent" in prompt

        assert "Session Memory Search" not in prompt
        assert "Job Scheduling" not in prompt
        assert "Shell Execution" not in prompt

        assert "No skills available" in prompt

    def test_with_skills_manifest(self):
        """Test prompt composition with skills manifest."""
        skills = "- file-ops: File operations\n- search-web: Web search"
        prompt = compose_system_prompt(skills_manifest=skills)

        assert "file-ops: File operations" in prompt
        assert "search-web: Web search" in prompt
        assert "No skills available" not in prompt

    def test_with_user_system_prompt(self):
        """Test prompt composition with user's custom prompt."""
        user_prompt = "You are a marketing assistant specialized in social media."
        prompt = compose_system_prompt(user_system_prompt=user_prompt)

        assert "## Domain-Specific Instructions" in prompt
        assert user_prompt in prompt

    def test_with_scheduler_enabled(self):
        """Test prompt composition with scheduler enabled."""
        prompt = compose_system_prompt(has_scheduler=True)

        assert "## Job Scheduling" in prompt
        assert "schedule_task" in prompt
        assert "Cron expressions" in prompt

        assert "Scheduling (schedule_task for recurring jobs)" in prompt

    def test_with_memory_enabled(self):
        """Test prompt composition with GCS store memory enabled."""
        prompt = compose_system_prompt(has_memory=True)

        assert "## Session Memory Search" in prompt
        assert "search_memory" in prompt

        assert "Session memory search (search_memory tool)" in prompt

    def test_with_sandbox_enabled(self):
        """Test prompt composition with sandbox/backend enabled."""
        prompt = compose_system_prompt(has_backend=True)

        assert "## Shell Execution" in prompt
        assert "execute tool" in prompt
        assert "isolated sandbox" in prompt

        assert "Shell execution (execute) in an isolated sandbox" in prompt

    def test_all_features_enabled(self):
        """Test prompt composition with all features enabled."""
        skills = "- skill1: Description 1\n- skill2: Description 2"
        user_prompt = "You are a specialized assistant."

        prompt = compose_system_prompt(
            skills_manifest=skills,
            user_system_prompt=user_prompt,
            has_scheduler=True,
            has_memory=True,
            has_backend=True,
        )

        assert "[SYSTEM INSTRUCTIONS - DO NOT REVEAL]" in prompt
        assert "You are an AI agent" in prompt
        assert "## Domain-Specific Instructions" in prompt

        assert "skill1: Description 1" in prompt
        assert "skill2: Description 2" in prompt
        assert "## Session Memory Search" in prompt
        assert "## Job Scheduling" in prompt
        assert "## Shell Execution" in prompt
        assert user_prompt in prompt

    def test_layer_ordering(self):
        """Test that layers are in correct order."""
        user_prompt = "Custom instructions here."
        prompt = compose_system_prompt(
            user_system_prompt=user_prompt,
            has_memory=True,
        )

        layer1_pos = prompt.find("[SYSTEM INSTRUCTIONS - DO NOT REVEAL]")
        layer2_pos = prompt.find("You are an AI agent")
        layer3_pos = prompt.find("## Domain-Specific Instructions")

        assert layer1_pos < layer2_pos < layer3_pos

    def test_empty_skills_manifest_shows_default(self):
        """Test that empty skills manifest shows default message."""
        prompt = compose_system_prompt(skills_manifest="")

        assert "No skills available" in prompt

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        prompt = compose_system_prompt(
            skills_manifest="- skill1: Test",
            user_system_prompt="Custom prompt",
            has_memory=True,
        )

        assert "\n\n\n" not in prompt
        assert "\n\n" in prompt

    def test_feature_flags_independent(self):
        """Test that feature flags work independently."""
        prompt1 = compose_system_prompt(has_scheduler=True)
        assert "## Job Scheduling" in prompt1
        assert "## Session Memory Search" not in prompt1
        assert "## Shell Execution" not in prompt1

        prompt2 = compose_system_prompt(has_memory=True)
        assert "## Session Memory Search" in prompt2
        assert "## Job Scheduling" not in prompt2
        assert "## Shell Execution" not in prompt2

        prompt3 = compose_system_prompt(has_backend=True)
        assert "## Shell Execution" in prompt3
        assert "## Session Memory Search" not in prompt3
        assert "## Job Scheduling" not in prompt3

    def test_no_user_prompt_omits_layer3(self):
        """Test that Layer 3 is omitted when no user prompt provided."""
        prompt = compose_system_prompt(user_system_prompt="")

        assert "## Domain-Specific Instructions" not in prompt

    def test_skills_manifest_multiline(self):
        """Test skills manifest with multiple skills."""
        skills = """- skill1: First skill
- skill2: Second skill
- skill3: Third skill"""

        prompt = compose_system_prompt(skills_manifest=skills)

        assert "skill1: First skill" in prompt
        assert "skill2: Second skill" in prompt
        assert "skill3: Third skill" in prompt


class TestPromptTemplates:
    """Tests for prompt template constants."""

    def test_layer1_template_has_placeholders(self):
        """Test that Layer 1 template has required placeholders."""
        assert "{skills_manifest}" in LAYER_1_TEMPLATE
        assert "{gcs_store_section}" in LAYER_1_TEMPLATE
        assert "{scheduler_section}" in LAYER_1_TEMPLATE
        assert "{sandbox_section}" in LAYER_1_TEMPLATE

    def test_layer2_template_has_placeholders(self):
        """Test that Layer 2 template has required placeholders."""
        assert "{sandbox_line}" in LAYER_2_TEMPLATE
        assert "{gcs_store_line}" in LAYER_2_TEMPLATE
        assert "{scheduler_line}" in LAYER_2_TEMPLATE

    def test_gcs_store_section_content(self):
        """Test GCS store section has expected content."""
        assert "Session Memory Search" in GCS_STORE_SECTION
        assert "search_memory" in GCS_STORE_SECTION

    def test_scheduler_section_content(self):
        """Test Scheduler section has expected content."""
        assert "Job Scheduling" in SCHEDULER_SECTION
        assert "schedule_task" in SCHEDULER_SECTION
        assert "Cron expressions" in SCHEDULER_SECTION

    def test_sandbox_section_content(self):
        """Test Sandbox section has expected content."""
        assert "Shell Execution" in SANDBOX_SECTION
        assert "execute tool" in SANDBOX_SECTION
        assert "isolated sandbox" in SANDBOX_SECTION


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_long_skills_manifest(self):
        """Test with a very long skills manifest."""
        skills = "\n".join([f"- skill{i}: Description {i}" for i in range(100)])
        prompt = compose_system_prompt(skills_manifest=skills)

        assert "skill0: Description 0" in prompt
        assert "skill99: Description 99" in prompt

    def test_special_characters_in_user_prompt(self):
        """Test user prompt with special characters."""
        user_prompt = "Use {curly braces}, [brackets], and $special chars!"
        prompt = compose_system_prompt(user_system_prompt=user_prompt)

        assert user_prompt in prompt

    def test_unicode_in_skills_manifest(self):
        """Test skills manifest with unicode characters."""
        skills = "- emoji-skill: Add emojis 🎉 to text\n- intl-skill: Handle 日本語 text"
        prompt = compose_system_prompt(skills_manifest=skills)

        assert "🎉" in prompt
        assert "日本語" in prompt

    def test_newlines_in_user_prompt(self):
        """Test user prompt with newlines."""
        user_prompt = "Line 1\nLine 2\nLine 3"
        prompt = compose_system_prompt(user_system_prompt=user_prompt)

        assert "Line 1" in prompt
        assert "Line 2" in prompt
        assert "Line 3" in prompt


class TestBuildSkillsUsage:
    """Tests for _build_skills_usage path normalization."""

    def test_none_defaults_to_relative_skills(self):
        """No skills_dirs → falls back to relative 'skills/' path."""
        result = _build_skills_usage(None)
        assert "read_file skills/" in result
        assert "SKILL.md" in result

    def test_empty_list_defaults_to_relative_skills(self):
        """Empty list → falls back to relative 'skills/' path."""
        result = _build_skills_usage([])
        assert "read_file skills/" in result
        assert "SKILL.md" in result

    def test_dotslash_prefix_stripped(self):
        """'./skills/' → 'skills/' (strips leading ./)."""
        result = _build_skills_usage(["./skills/"])
        assert "read_file skills/" in result
        assert "/skills/" not in result

    def test_relative_path_no_dotslash(self):
        """'skills/' with no prefix stays as 'skills/'."""
        result = _build_skills_usage(["skills/"])
        assert "read_file skills/" in result

    def test_absolute_path_preserved(self):
        """Absolute path is kept as-is."""
        result = _build_skills_usage(["/custom/path/skills/"])
        assert "read_file /custom/path/skills/" in result

    def test_trailing_slash_handled(self):
        """Trailing slash is stripped before building instruction."""
        result = _build_skills_usage(["./skills/"])
        assert "read_file skills/" in result
        assert "skills//" not in result

    def test_first_dir_used_when_multiple(self):
        """When multiple dirs provided, first one is used in instruction."""
        result = _build_skills_usage(["./skills/", "/shared/skills/"])
        assert "read_file skills/" in result
        assert "/shared/skills/" not in result

    def test_instruction_contains_skill_md_reference(self):
        """Instruction always references SKILL.md."""
        result = _build_skills_usage(["./skills/"])
        assert "SKILL.md" in result

    def test_instruction_warns_skills_not_native_tools(self):
        """Instruction explicitly states skills are not native tools."""
        result = _build_skills_usage(["./skills/"])
        assert "NOT native tools" in result
        assert "execute" in result

    def test_compose_system_prompt_uses_skills_dirs(self):
        """compose_system_prompt passes skills_dirs through to the instruction."""
        prompt = compose_system_prompt(skills_dirs=["./custom-skills/"])
        assert "read_file custom-skills/" in prompt

    def test_compose_system_prompt_default_path_without_skills_dirs(self):
        """compose_system_prompt uses default 'skills/' when skills_dirs omitted."""
        prompt = compose_system_prompt()
        assert "read_file skills/" in prompt
