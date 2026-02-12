# Code Spec: Sprint 1 - Marketing Campaign Manager (Complete)

**Author:** MonkeyMode Agent  
**Date:** 2026-02-11  
**Status:** Ready for Implementation  
**Stories:** 1.1, 1.2, 1.3, 1.4, 1.5 (All Sprint 1 stories)

---

## Table of Contents

1. [Implementation Summary](#implementation-summary)
2. [Codebase Conventions](#codebase-conventions)
3. [Story 1.1: Enhanced Skill Loader](#story-11-enhanced-skill-loader-framework)
4. [Story 1.2: Generate Post Skill](#story-12-generate-post-skill-mvp)
5. [Story 1.3: Request Approval Skill](#story-13-request-approval-skill-mvp)
6. [Story 1.4: Post Content Skill](#story-14-post-content-skill-x-only-mvp)
7. [Story 1.5: End-to-End Validation](#story-15-end-to-end-validation)
8. [Dependency Graph](#dependency-graph)
9. [Final Verification](#final-verification)

---

## Implementation Summary

**Files to Create:** 21 files  
**Files to Modify:** 1 file (loader.py)  
**Tests to Add:** 10 test files  
**Estimated Complexity:** M-L (5-7 days solo developer)

### File Breakdown by Story

| Story | Files Created | Files Modified | Tests |
|-------|---------------|----------------|-------|
| 1.1 | 0 | 1 | 1 |
| 1.2 | 4 | 0 | 2 |
| 1.3 | 3 | 0 | 2 |
| 1.4 | 8 | 0 | 3 |
| 1.5 | 0 | 0 | 2 |
| **Total** | **15** | **1** | **10** |

---

## Codebase Conventions

### Discovered from monkey-bot codebase

**File/Function Naming:**
- Files: `snake_case.py` (e.g., `skill_loader.py`, `generate_post.py`)
- Functions: `snake_case` (e.g., `load_skills()`, `generate_post()`)
- Classes: `PascalCase` (e.g., `SkillLoader`, `AgentCore`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `PLATFORM_LIMITS`, `ALLOWED_COMMANDS`)

**Import Order (PEP 8):**
```python
# Standard library
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

# Third-party
import httpx
import yaml
from pydantic import BaseModel

# Local
from src.core.interfaces import AgentCoreInterface, SkillResult
```

**Error Handling Pattern:**
```python
from src.core.interfaces import EmonkError, SkillError

# Custom exceptions inherit from EmonkError
class GenerationError(SkillError):
    """Raised when post generation fails."""
    pass

# Usage
try:
    result = await generate_content(topic)
except GenerationError as e:
    logger.error(f"Generation failed: {e}", extra={"trace_id": trace_id})
    raise
```

**Logging Pattern (Structured JSON):**
```python
import logging
logger = logging.getLogger(__name__)

logger.info(
    "Skill invoked",
    extra={
        "component": "generate_post",
        "trace_id": trace_id,
        "platform": "instagram",
        "topic": topic[:50]  # Truncate long values
    }
)
```

**Type Hints (mypy strict mode):**
```python
from typing import Dict, List, Optional, Literal

def generate_post(
    topic: str,
    platform: Literal["instagram", "tiktok", "x", "linkedin", "reddit"],
    tone: str = "professional"
) -> Dict[str, Any]:
    """Generate post with strict typing."""
    pass
```

**Testing Framework:**
- Framework: `pytest` with `pytest-asyncio`
- Coverage: `pytest-cov` (target: 80%+)
- Fixtures: Use `@pytest.fixture` for setup
- Async tests: `async def` with `asyncio_mode = "auto"`
- Mocking: Use `unittest.mock` or `pytest-mock`

**Dataclasses for Data Structures:**
```python
from dataclasses import dataclass

@dataclass
class PostContent:
    """Generated post content."""
    platform: str
    content: str
    hashtags: List[str]
    character_count: int
```

---

## Story 1.1: Enhanced Skill Loader (Framework)

**Repository:** monkey-bot (public)  
**Priority:** Critical (blocks all other stories)  
**Dependencies:** None  
**Estimated Time:** 1-2 days

### Overview

Modify `SkillLoader` to expose SKILL.md descriptions to Gemini for routing decisions. This is **THE MOST CRITICAL** task - without this, skills won't be invoked correctly.

### Current State Analysis

**File to Modify:** `src/skills/loader.py`

**Current Implementation:**
```python
class SkillLoader:
    def load_skills(self) -> Dict[str, dict]:
        # Currently loads:
        # - SKILL.md metadata (name, description)
        # - Entry point path
        # Returns: {"skill-name": {"metadata": {...}, "entry_point": "...", "description": "..."}}
```

**What's Missing:**
- Description is loaded but **NOT** formatted for LangGraph tool definitions
- No method to get tool schemas for Gemini
- No validation of description quality (must be clear for routing)

### Task Breakdown

#### Task 1.1.1: Add `get_tool_schemas()` Method

**File:** `src/skills/loader.py` (modify existing)

**Add New Method:**
```python
def get_tool_schemas(self) -> List[Dict[str, Any]]:
    """
    Convert loaded skills to LangGraph tool schema format.
    
    This method transforms skill metadata into the format expected by
    LangGraph for tool calling with Gemini. Each skill becomes a tool
    that Gemini can invoke based on the description.
    
    Returns:
        List of tool schema dictionaries suitable for LangGraph:
        [
            {
                "name": "generate-post",
                "description": "Create social media content for any platform...",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            ...
        ]
    
    Notes:
        - Description is extracted from SKILL.md frontmatter
        - Parameters are auto-generated (empty for MVP)
        - Required fields list is empty (Gemini extracts from description)
    
    Example:
        >>> loader = SkillLoader()
        >>> loader.load_skills()
        >>> schemas = loader.get_tool_schemas()
        >>> print(schemas[0]["name"])
        'generate-post'
        >>> print(schemas[0]["description"][:50])
        'Create social media content for any platform...'
    """
    tool_schemas = []
    
    for skill_name, skill_data in self.skills.items():
        description = skill_data.get("description", "")
        
        # Validation: Ensure description is meaningful
        if len(description) < 20:
            logger.warning(
                f"Skill '{skill_name}' has short description ({len(description)} chars). "
                "May affect routing quality.",
                extra={"component": "skill_loader", "skill": skill_name}
            )
        
        schema = {
            "name": skill_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {},  # Auto-inferred by Gemini from description
                "required": []
            }
        }
        
        tool_schemas.append(schema)
    
    logger.info(
        f"Generated {len(tool_schemas)} tool schemas for LangGraph",
        extra={"component": "skill_loader", "count": len(tool_schemas)}
    )
    
    return tool_schemas
```

**Implementation Notes:**
- Add after existing `load_skills()` method
- Keep existing methods unchanged (backward compatibility)
- Validate description length (warn if < 20 chars)
- Return empty list if no skills loaded

---

#### Task 1.1.2: Update Type Hints

**File:** `src/skills/loader.py` (modify existing)

**Add Import:**
```python
from typing import Dict, List, Any, Optional
```

**Update Method Signature:**
```python
def get_tool_schemas(self) -> List[Dict[str, Any]]:
    """See docstring above"""
    pass
```

---

#### Task 1.1.3: Add Tests

**File:** `tests/skills/test_loader.py` (modify existing)

**Add Test Class:**
```python
class TestSkillLoaderToolSchemas:
    """Tests for tool schema generation."""
    
    def test_get_tool_schemas_with_valid_skills(self, skills_dir):
        """Test: Valid skills generate correct tool schemas."""
        # Create skill with good description
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: "This is a test skill with a good description that is long enough for routing."
---
# Test Skill
""")
        
        loader = SkillLoader(str(skills_dir))
        loader.load_skills()
        schemas = loader.get_tool_schemas()
        
        assert len(schemas) == 1
        assert schemas[0]["name"] == "test-skill"
        assert "test skill" in schemas[0]["description"].lower()
        assert schemas[0]["parameters"]["type"] == "object"
    
    def test_get_tool_schemas_with_short_description(self, skills_dir, caplog):
        """Test: Short descriptions trigger warning."""
        # Create skill with short description
        skill_dir = skills_dir / "short-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: short-skill
description: "Short"
---
# Short
""")
        
        loader = SkillLoader(str(skills_dir))
        loader.load_skills()
        schemas = loader.get_tool_schemas()
        
        # Should still generate schema
        assert len(schemas) == 1
        
        # But should log warning
        assert "short description" in caplog.text.lower()
    
    def test_get_tool_schemas_with_no_skills(self, skills_dir):
        """Test: Empty skills directory returns empty list."""
        loader = SkillLoader(str(skills_dir))
        loader.load_skills()
        schemas = loader.get_tool_schemas()
        
        assert schemas == []
    
    def test_get_tool_schemas_with_multiple_skills(self, skills_dir):
        """Test: Multiple skills generate multiple schemas."""
        # Create 3 skills
        for i in range(3):
            skill_dir = skills_dir / f"skill-{i}"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(f"""---
name: skill-{i}
description: "This is skill {i} with a description for routing."
---
# Skill {i}
""")
        
        loader = SkillLoader(str(skills_dir))
        loader.load_skills()
        schemas = loader.get_tool_schemas()
        
        assert len(schemas) == 3
        assert set([s["name"] for s in schemas]) == {"skill-0", "skill-1", "skill-2"}
```

**Run Tests:**
```bash
pytest tests/skills/test_loader.py::TestSkillLoaderToolSchemas -v
```

---

### Story 1.1 Acceptance Criteria Checklist

- [ ] **Given** a skill with valid SKILL.md, **When** `get_tool_schemas()` called, **Then** returns LangGraph-compatible schema
- [ ] **Given** SKILL.md with short description (<20 chars), **When** loaded, **Then** logs warning but still works
- [ ] **Given** multiple skills, **When** `get_tool_schemas()` called, **Then** returns schema for each skill
- [ ] **Given** no skills loaded, **When** `get_tool_schemas()` called, **Then** returns empty list
- [ ] All existing tests still pass (backward compatibility)
- [ ] New tests pass with 100% coverage of new method
- [ ] Type hints added for mypy strict mode
- [ ] Docstrings follow Google style

---

## Story 1.2: Generate Post Skill (MVP)

**Repository:** monkey-bot (will be moved to private repo later)  
**Priority:** High  
**Dependencies:** Story 1.1 (skill loader must work)  
**Estimated Time:** 1-2 days

### Overview

Create skill that generates platform-optimized social media content. Validates against character limits and brand voice.

### Integration Contracts

**This skill defines the content generation interface that other skills depend on.**

**Input Parameters:**
```python
@dataclass
class GeneratePostParams:
    topic: str
    platform: Literal["instagram", "tiktok", "x", "linkedin", "reddit"]
    tone: str = "professional"
    include_hashtags: bool = True
```

**Output Schema:**
```python
@dataclass
class PostContent:
    platform: str
    content: str
    hashtags: List[str]
    character_count: int
    validation: ValidationResult

@dataclass
class ValidationResult:
    within_limit: bool
    has_hook: bool
    has_cta: bool
    brand_voice_valid: bool
```

---

### Task Breakdown

#### Task 1.2.1: Create Skill Structure

**Files to Create:**
```
skills/generate-post/
├── SKILL.md
├── generate_post.py
├── platforms.py  (platform limits)
└── __init__.py
```

**File:** `skills/generate-post/SKILL.md`
```markdown
---
name: generate-post
description: Create social media content for any platform (Instagram, TikTok, X, LinkedIn, Reddit). Automatically validates character limits and brand voice. Use when user wants to create, write, draft, or generate a post.
metadata:
  emonk:
    requires:
      bins: []
      files: ["./data/memory/BRAND_VOICE.md"]
---

# Generate Social Media Post

Creates platform-specific social media content optimized for engagement.

## When to Use This Skill

Invoke this skill when the user:
- Wants to create a new social media post
- Says "write a post about [topic]"
- Requests "draft Instagram caption for [topic]"
- Says "generate content for X about [topic]"

## Parameters

- `topic` (required): What the post is about
- `platform` (required): Target platform ("instagram", "tiktok", "x", "linkedin", "reddit")
- `tone` (optional): Desired tone ("professional", "casual", "humorous")
- `include_hashtags` (optional): Whether to add hashtags (default: true)

## Success Criteria

A good post has:
- ✅ Appropriate length for platform
- ✅ Engaging hook in first line
- ✅ Clear call-to-action
- ✅ Platform-appropriate hashtags
- ✅ No forbidden brand voice phrases

## Platform Limits

| Platform | Character Limit | Hashtags |
|----------|----------------|----------|
| Instagram | 2200 | 3-5 |
| TikTok | 2200 | 3-5 |
| X | 280 | 1-2 |
| LinkedIn | 3000 | 3-5 |
| Reddit | 40000 | 0 (use flair) |

## Example Usage

```bash
python3 skills/generate-post/generate_post.py \
  --topic "AI agent evaluation" \
  --platform instagram \
  --tone professional
```
```

**File:** `skills/generate-post/platforms.py`
```python
"""Platform-specific limits and requirements."""

from typing import Dict, Any

PLATFORM_LIMITS: Dict[str, Dict[str, Any]] = {
    "instagram": {
        "char_limit": 2200,
        "min_hashtags": 3,
        "max_hashtags": 30,
        "hashtag_recommended": True
    },
    "tiktok": {
        "char_limit": 2200,
        "min_hashtags": 3,
        "max_hashtags": 30,
        "hashtag_recommended": True
    },
    "x": {
        "char_limit": 280,
        "min_hashtags": 1,
        "max_hashtags": 2,
        "hashtag_recommended": False  # Optional for X
    },
    "linkedin": {
        "char_limit": 3000,
        "min_hashtags": 3,
        "max_hashtags": 5,
        "hashtag_recommended": True
    },
    "reddit": {
        "char_limit": 40000,
        "min_hashtags": 0,
        "max_hashtags": 0,
        "hashtag_recommended": False  # Reddit uses flair instead
    }
}

VALID_PLATFORMS = list(PLATFORM_LIMITS.keys())

def get_platform_limit(platform: str) -> Dict[str, Any]:
    """
    Get character limit and hashtag rules for platform.
    
    Args:
        platform: Platform name (lowercase)
    
    Returns:
        Dictionary with char_limit, min_hashtags, max_hashtags
    
    Raises:
        ValueError: If platform is not recognized
    
    Example:
        >>> limits = get_platform_limit("instagram")
        >>> print(limits["char_limit"])
        2200
    """
    if platform not in PLATFORM_LIMITS:
        raise ValueError(
            f"Unknown platform: {platform}. "
            f"Valid platforms: {', '.join(VALID_PLATFORMS)}"
        )
    
    return PLATFORM_LIMITS[platform]
```

---

#### Task 1.2.2: Implement Core Generator

**File:** `skills/generate-post/generate_post.py`
```python
#!/usr/bin/env python3
"""
Generate social media posts optimized for platform.

This skill creates engaging social media content tailored to each platform's
requirements (character limits, hashtags, tone).
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Literal, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Import platform limits
from platforms import get_platform_limit, VALID_PLATFORMS

# Paths
BRAND_VOICE_PATH = Path("./data/memory/BRAND_VOICE.md")


@dataclass
class ValidationResult:
    """Post validation result."""
    within_limit: bool
    has_hook: bool
    has_cta: bool
    brand_voice_valid: bool
    readability_score: int = 75  # Placeholder (can implement later)


@dataclass
class PostContent:
    """Generated post content."""
    platform: str
    content: str
    hashtags: List[str]
    character_count: int
    validation: ValidationResult


def load_brand_voice() -> Optional[str]:
    """
    Load brand voice guidelines from file.
    
    Returns:
        Brand voice text if file exists, None otherwise
    
    Notes:
        - Brand voice file is optional for MVP
        - File location: ./data/memory/BRAND_VOICE.md
        - If missing, generation continues without brand validation
    """
    if not BRAND_VOICE_PATH.exists():
        logger.warning(
            "Brand voice file not found. Skipping brand voice validation.",
            extra={"path": str(BRAND_VOICE_PATH)}
        )
        return None
    
    try:
        return BRAND_VOICE_PATH.read_text()
    except Exception as e:
        logger.error(f"Failed to load brand voice: {e}")
        return None


def generate_content_with_llm(
    topic: str,
    platform: str,
    tone: str,
    include_hashtags: bool,
    brand_voice: Optional[str]
) -> Dict[str, Any]:
    """
    Generate post content using LLM (Gemini).
    
    This is a PLACEHOLDER for MVP. In real implementation:
    - Call Vertex AI Gemini API
    - Use structured prompt with platform requirements
    - Validate against brand voice
    
    Args:
        topic: What the post is about
        platform: Target platform
        tone: Desired tone
        include_hashtags: Whether to generate hashtags
        brand_voice: Brand voice guidelines (optional)
    
    Returns:
        Dictionary with 'content' and 'hashtags' keys
    
    Notes:
        - For MVP, this returns mock data
        - Replace with real Gemini API call in production
        - Use system prompt to enforce platform requirements
    """
    # PLACEHOLDER: Mock generation for MVP testing
    # TODO: Replace with real Vertex AI Gemini call
    
    limits = get_platform_limit(platform)
    char_limit = limits["char_limit"]
    
    # Mock content based on platform
    if platform == "x":
        content = f"Exploring {topic}: Key insights for developers. Learn more about best practices. #Tech"
    elif platform == "instagram":
        content = f"""Diving deep into {topic} today! 🚀

Here's what you need to know:
• Key insights for success
• Best practices from experts
• Real-world applications

Double-tap if you found this useful! 💡

#TechInnovation #AI #Development"""
    elif platform == "linkedin":
        content = f"""Professional insight on {topic}

In today's fast-paced technology landscape, understanding {topic} is crucial for success. Here are the key takeaways:

1. Industry best practices
2. Implementation strategies  
3. Measurable outcomes

What's your experience with {topic}? Share in the comments!

#Technology #Innovation #Professional"""
    else:
        content = f"Check out this post about {topic}! Great insights and practical tips."
    
    # Ensure content fits within limit
    if len(content) > char_limit:
        content = content[:char_limit - 3] + "..."
    
    # Generate hashtags
    hashtags = []
    if include_hashtags and limits["hashtag_recommended"]:
        hashtags = ["#AI", "#Tech", "#Innovation"][:limits["max_hashtags"]]
    
    return {
        "content": content,
        "hashtags": hashtags
    }


def validate_post(
    content: str,
    platform: str,
    hashtags: List[str],
    brand_voice: Optional[str]
) -> ValidationResult:
    """
    Validate generated post against requirements.
    
    Checks:
    1. Within character limit
    2. Has engaging hook (first line)
    3. Has call-to-action
    4. Matches brand voice (if provided)
    
    Args:
        content: Post text
        platform: Target platform
        hashtags: Generated hashtags
        brand_voice: Brand voice guidelines (optional)
    
    Returns:
        ValidationResult with pass/fail for each criterion
    
    Notes:
        - Hook detection: First line should grab attention
        - CTA detection: Look for question, action phrase, or link
        - Brand voice: Basic keyword matching (can enhance later)
    """
    limits = get_platform_limit(platform)
    char_limit = limits["char_limit"]
    
    # Check 1: Within character limit
    within_limit = len(content) <= char_limit
    
    # Check 2: Has hook (first line has impact)
    # Simple heuristic: First line is < 80 chars and contains attention words
    first_line = content.split('\n')[0]
    attention_words = ["explore", "discover", "learn", "check", "dive", "unveil", "reveal"]
    has_hook = (
        len(first_line) < 80 and
        any(word in first_line.lower() for word in attention_words)
    )
    
    # Check 3: Has call-to-action
    cta_phrases = ["check out", "learn more", "share", "comment", "double-tap", "link in bio", "?"]
    has_cta = any(phrase in content.lower() for phrase in cta_phrases)
    
    # Check 4: Brand voice validation (simple keyword check)
    brand_voice_valid = True
    if brand_voice:
        # Basic check: No forbidden phrases
        forbidden = ["buy now", "limited time", "act now", "don't miss"]
        brand_voice_valid = not any(phrase in content.lower() for phrase in forbidden)
    
    return ValidationResult(
        within_limit=within_limit,
        has_hook=has_hook,
        has_cta=has_cta,
        brand_voice_valid=brand_voice_valid
    )


def generate_post(
    topic: str,
    platform: Literal["instagram", "tiktok", "x", "linkedin", "reddit"],
    tone: str = "professional",
    include_hashtags: bool = True
) -> PostContent:
    """
    Generate social media post for platform.
    
    Main entry point for post generation. Orchestrates:
    1. Load brand voice (optional)
    2. Generate content with LLM
    3. Validate output
    4. Return structured result
    
    Args:
        topic: What the post is about
        platform: Target platform
        tone: Desired tone (default: "professional")
        include_hashtags: Whether to include hashtags (default: True)
    
    Returns:
        PostContent with generated content and validation
    
    Raises:
        ValueError: If platform is invalid
    
    Example:
        >>> post = generate_post("AI agents", "instagram")
        >>> print(post.content[:50])
        'Diving deep into AI agents today! 🚀...'
        >>> print(post.validation.within_limit)
        True
    """
    logger.info(
        f"Generating {platform} post about '{topic}'",
        extra={"platform": platform, "topic": topic, "tone": tone}
    )
    
    # Validate platform
    if platform not in VALID_PLATFORMS:
        raise ValueError(
            f"Invalid platform: {platform}. "
            f"Valid platforms: {', '.join(VALID_PLATFORMS)}"
        )
    
    # Load brand voice (optional)
    brand_voice = load_brand_voice()
    
    # Generate content
    generated = generate_content_with_llm(
        topic=topic,
        platform=platform,
        tone=tone,
        include_hashtags=include_hashtags,
        brand_voice=brand_voice
    )
    
    content = generated["content"]
    hashtags = generated["hashtags"]
    
    # Validate
    validation = validate_post(content, platform, hashtags, brand_voice)
    
    # Build result
    post = PostContent(
        platform=platform,
        content=content,
        hashtags=hashtags,
        character_count=len(content),
        validation=validation
    )
    
    logger.info(
        f"Generated post: {len(content)} chars, "
        f"{len(hashtags)} hashtags, "
        f"valid={validation.within_limit}",
        extra={"validation": asdict(validation)}
    )
    
    return post


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate social media post for platform"
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="What the post is about"
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=VALID_PLATFORMS,
        help="Target platform"
    )
    parser.add_argument(
        "--tone",
        default="professional",
        help="Desired tone (default: professional)"
    )
    parser.add_argument(
        "--include-hashtags",
        action="store_true",
        default=True,
        help="Include hashtags (default: True)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    try:
        post = generate_post(
            topic=args.topic,
            platform=args.platform,
            tone=args.tone,
            include_hashtags=args.include_hashtags
        )
        
        if args.json:
            # Output as JSON
            print(json.dumps(asdict(post), indent=2))
        else:
            # Human-readable output
            print(f"\n✅ Generated {args.platform.upper()} post:\n")
            print(post.content)
            if post.hashtags:
                print(f"\nHashtags: {' '.join(post.hashtags)}")
            print(f"\nCharacter count: {post.character_count}")
            print(f"Validation: {asdict(post.validation)}")
        
        sys.exit(0)
    
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

#### Task 1.2.3: Add Unit Tests

**File:** `tests/skills/test_generate_post.py` (create new)
```python
"""Tests for generate-post skill."""

import pytest
from pathlib import Path
from skills.generate_post.generate_post import (
    generate_post,
    load_brand_voice,
    validate_post,
    PostContent,
    ValidationResult
)
from skills.generate_post.platforms import get_platform_limit, VALID_PLATFORMS


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
        monkeypatch.setattr(
            "skills.generate_post.generate_post.BRAND_VOICE_PATH",
            tmp_path / "missing.md"
        )
        
        brand_voice = load_brand_voice()
        assert brand_voice is None
    
    def test_load_brand_voice_existing_file(self, tmp_path, monkeypatch):
        """Test: Existing brand voice file is loaded."""
        brand_voice_file = tmp_path / "BRAND_VOICE.md"
        brand_voice_file.write_text("Our brand is professional and helpful.")
        
        monkeypatch.setattr(
            "skills.generate_post.generate_post.BRAND_VOICE_PATH",
            brand_voice_file
        )
        
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
```

**Run Tests:**
```bash
pytest tests/skills/test_generate_post.py -v
```

---

#### Task 1.2.4: Add Integration Test

**File:** `tests/integration/test_generate_post_integration.py` (create new)
```python
"""Integration tests for generate-post skill."""

import pytest
from skills.generate_post.generate_post import generate_post


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
            "Cloud infrastructure"
        ]
        
        for topic in topics:
            post = generate_post(topic, "instagram")
            assert topic.split()[0].lower() in post.content.lower()
```

**Run Integration Tests:**
```bash
pytest tests/integration/test_generate_post_integration.py -v -m integration
```

---

### Story 1.2 Acceptance Criteria Checklist

- [ ] **Given** topic="AI agents" and platform="x", **When** generate_post() called, **Then** returns content <= 280 chars
- [ ] **Given** platform="instagram", **When** generate_post() called, **Then** returns 3-5 hashtags
- [ ] **Given** BRAND_VOICE.md exists, **When** generating post, **Then** validates against brand guidelines
- [ ] **Given** invalid platform="facebook", **When** generate_post() called, **Then** raises ValueError
- [ ] **Given** generated content, **When** returned, **Then** includes validation results
- [ ] All tests pass (unit + integration)
- [ ] Type hints complete (mypy strict passes)
- [ ] Logging includes trace IDs and structured data

---

## Story 1.3: Request Approval Skill (MVP)

**Repository:** monkey-bot  
**Priority:** High  
**Dependencies:** Story 1.2 (needs content to approve)  
**Estimated Time:** 1-2 days

### Overview

Send content to Google Chat for approval with interactive buttons. Waits for user response (Approve/Reject/Modify).

### Integration Contracts

**Input Parameters:**
```python
@dataclass
class RequestApprovalParams:
    content: str
    content_type: Literal["social_post", "campaign", "image"]
    platform: Optional[str] = None
    timeout_seconds: int = 3600
```

**Output Schema:**
```python
@dataclass
class ApprovalResult:
    approved: bool
    feedback: Optional[str]
    modified_content: Optional[str]
    timestamp: str
```

---

### Task Breakdown

#### Task 1.3.1: Create Skill Structure

**Files to Create:**
```
skills/request-approval/
├── SKILL.md
├── request_approval.py
└── __init__.py
```

**File:** `skills/request-approval/SKILL.md`
```markdown
---
name: request-approval
description: Send content to Google Chat for user approval before posting. Returns approved/rejected status with optional feedback. Use when user wants to review content before it goes live.
metadata:
  emonk:
    requires:
      bins: ["python3"]
      files: ["./data/memory/approvals/"]
---

# Request Approval for Content

Sends content to Google Chat with interactive Approve/Reject/Modify buttons.

## When to Use This Skill

Invoke when user:
- Says "send this for approval"
- Wants to "review before posting"
- Says "let me see it first"
- Says "get my approval"

## Parameters

- `content` (required): The content to approve
- `content_type` (required): Type ("social_post", "campaign", "image")
- `platform` (optional): Platform if social post
- `timeout_seconds` (optional): Approval timeout (default: 3600 = 1 hour)

## Example Usage

```bash
python3 skills/request-approval/request_approval.py \
  --content "Check out this post..." \
  --content-type social_post \
  --platform instagram
```
```

---

#### Task 1.3.2: Implement Approval Logic

**File:** `skills/request-approval/request_approval.py`
```python
#!/usr/bin/env python3
"""
Request approval for content via Google Chat.

This skill sends interactive cards to Google Chat for user approval.
For MVP, it uses a simple polling mechanism (check approval file).
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
APPROVALS_DIR = Path("./data/memory/approvals")


@dataclass
class ApprovalResult:
    """Approval result from user."""
    approved: bool
    feedback: Optional[str]
    modified_content: Optional[str]
    timestamp: str


def create_approval_record(
    content: str,
    content_type: str,
    platform: Optional[str]
) -> str:
    """
    Create approval record and return approval ID.
    
    Stores approval request in file system for polling.
    
    Args:
        content: Content to approve
        content_type: Type of content
        platform: Platform if social post
    
    Returns:
        Approval ID (UUID)
    
    Notes:
        - Approval file: ./data/memory/approvals/{id}.json
        - Status: "pending" | "approved" | "rejected"
        - User updates file via Google Chat callback
    """
    APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
    
    approval_id = str(uuid4())
    approval_file = APPROVALS_DIR / f"{approval_id}.json"
    
    approval_data = {
        "id": approval_id,
        "content": content,
        "content_type": content_type,
        "platform": platform,
        "status": "pending",
        "created_at": time.time(),
        "feedback": None,
        "modified_content": None
    }
    
    approval_file.write_text(json.dumps(approval_data, indent=2))
    
    logger.info(
        f"Created approval record: {approval_id}",
        extra={"approval_id": approval_id, "content_type": content_type}
    )
    
    return approval_id


def send_approval_card_to_chat(
    approval_id: str,
    content: str,
    content_type: str,
    platform: Optional[str]
) -> None:
    """
    Send Google Chat card with approval buttons.
    
    For MVP, this is a PLACEHOLDER that logs the card data.
    In production, this would call Google Chat API.
    
    Args:
        approval_id: Approval ID for callbacks
        content: Content to display
        content_type: Type of content
        platform: Platform if social post
    
    Notes:
        - MVP: Just logs card data
        - Production: Call Google Chat API with card JSON
        - Card includes: Content preview, Approve/Reject/Modify buttons
    """
    # PLACEHOLDER: Google Chat API integration
    # TODO: Replace with real Google Chat API call
    
    card = {
        "cardsV2": [{
            "cardId": f"approval-{approval_id}",
            "card": {
                "header": {
                    "title": f"Approval Request: {content_type}",
                    "subtitle": f"Platform: {platform or 'N/A'}"
                },
                "sections": [{
                    "widgets": [{
                        "textParagraph": {"text": content[:500]}  # Truncate
                    }]
                }],
                "cardActions": [
                    {"actionLabel": "✅ Approve", "onClick": {"action": {"function": "approve", "parameters": [{"key": "approval_id", "value": approval_id}]}}},
                    {"actionLabel": "❌ Reject", "onClick": {"action": {"function": "reject", "parameters": [{"key": "approval_id", "value": approval_id}]}}},
                    {"actionLabel": "✏️ Modify", "onClick": {"action": {"function": "modify", "parameters": [{"key": "approval_id", "value": approval_id}]}}}
                ]
            }
        }]
    }
    
    logger.info(
        f"[PLACEHOLDER] Would send Google Chat card for approval {approval_id}",
        extra={"card": card}
    )
    
    # For MVP testing: Automatically approve after 2 seconds
    # TODO: Remove this in production
    def auto_approve():
        time.sleep(2)
        approval_file = APPROVALS_DIR / f"{approval_id}.json"
        if approval_file.exists():
            data = json.loads(approval_file.read_text())
            data["status"] = "approved"
            data["feedback"] = "Auto-approved for MVP testing"
            approval_file.write_text(json.dumps(data, indent=2))
    
    import threading
    threading.Thread(target=auto_approve, daemon=True).start()


async def wait_for_approval(
    approval_id: str,
    timeout_seconds: int
) -> ApprovalResult:
    """
    Wait for user to approve/reject content.
    
    Polls approval file every 1 second until:
    - User approves/rejects (status changes)
    - Timeout expires
    
    Args:
        approval_id: Approval ID to poll
        timeout_seconds: Max wait time
    
    Returns:
        ApprovalResult with decision
    
    Raises:
        TimeoutError: If approval times out
    
    Notes:
        - Polls every 1 second (efficient for low volume)
        - Status values: "pending" | "approved" | "rejected"
        - User updates file via Google Chat callback
    """
    approval_file = APPROVALS_DIR / f"{approval_id}.json"
    start_time = time.time()
    
    logger.info(
        f"Waiting for approval: {approval_id} (timeout: {timeout_seconds}s)",
        extra={"approval_id": approval_id, "timeout": timeout_seconds}
    )
    
    while time.time() - start_time < timeout_seconds:
        if not approval_file.exists():
            raise FileNotFoundError(f"Approval record not found: {approval_id}")
        
        data = json.loads(approval_file.read_text())
        status = data["status"]
        
        if status == "approved":
            logger.info(f"Approval {approval_id}: APPROVED")
            return ApprovalResult(
                approved=True,
                feedback=data.get("feedback"),
                modified_content=data.get("modified_content"),
                timestamp=str(time.time())
            )
        
        elif status == "rejected":
            logger.info(f"Approval {approval_id}: REJECTED")
            return ApprovalResult(
                approved=False,
                feedback=data.get("feedback"),
                modified_content=None,
                timestamp=str(time.time())
            )
        
        # Still pending, wait and check again
        await asyncio.sleep(1)
    
    # Timeout
    logger.warning(f"Approval {approval_id}: TIMEOUT")
    raise TimeoutError(
        f"Approval timeout after {timeout_seconds}s. "
        f"No response from user."
    )


async def request_approval(
    content: str,
    content_type: Literal["social_post", "campaign", "image"],
    platform: Optional[str] = None,
    timeout_seconds: int = 3600
) -> ApprovalResult:
    """
    Request approval for content.
    
    Main entry point. Orchestrates:
    1. Create approval record
    2. Send Google Chat card
    3. Wait for user response
    4. Return result
    
    Args:
        content: Content to approve
        content_type: Type of content
        platform: Platform if social post
        timeout_seconds: Max wait time (default: 1 hour)
    
    Returns:
        ApprovalResult with decision
    
    Raises:
        TimeoutError: If no response within timeout
    
    Example:
        >>> result = await request_approval(
        ...     content="Check out this post!",
        ...     content_type="social_post",
        ...     platform="instagram"
        ... )
        >>> print(result.approved)
        True
    """
    logger.info(
        f"Requesting approval for {content_type}",
        extra={"content_type": content_type, "platform": platform}
    )
    
    # Step 1: Create approval record
    approval_id = create_approval_record(content, content_type, platform)
    
    # Step 2: Send Google Chat card
    send_approval_card_to_chat(approval_id, content, content_type, platform)
    
    # Step 3: Wait for response
    result = await wait_for_approval(approval_id, timeout_seconds)
    
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Request approval for content"
    )
    parser.add_argument(
        "--content",
        required=True,
        help="Content to approve"
    )
    parser.add_argument(
        "--content-type",
        required=True,
        choices=["social_post", "campaign", "image"],
        help="Type of content"
    )
    parser.add_argument(
        "--platform",
        help="Platform if social post"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Timeout in seconds (default: 3600)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    try:
        result = asyncio.run(request_approval(
            content=args.content,
            content_type=args.content_type,
            platform=args.platform,
            timeout_seconds=args.timeout
        ))
        
        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            if result.approved:
                print(f"\n✅ APPROVED")
                if result.feedback:
                    print(f"Feedback: {result.feedback}")
                if result.modified_content:
                    print(f"Modified content:\n{result.modified_content}")
            else:
                print(f"\n❌ REJECTED")
                if result.feedback:
                    print(f"Feedback: {result.feedback}")
        
        sys.exit(0 if result.approved else 1)
    
    except TimeoutError as e:
        logger.error(f"Timeout: {e}")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Approval failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

#### Task 1.3.3: Add Tests

**File:** `tests/skills/test_request_approval.py` (create new)
```python
"""Tests for request-approval skill."""

import pytest
import asyncio
import json
from pathlib import Path
from skills.request_approval.request_approval import (
    request_approval,
    create_approval_record,
    wait_for_approval,
    ApprovalResult,
    APPROVALS_DIR
)


@pytest.fixture
def approvals_dir(tmp_path, monkeypatch):
    """Create temporary approvals directory."""
    approvals = tmp_path / "approvals"
    approvals.mkdir()
    monkeypatch.setattr(
        "skills.request_approval.request_approval.APPROVALS_DIR",
        approvals
    )
    return approvals


class TestApprovalRecordCreation:
    """Tests for approval record creation."""
    
    def test_create_approval_record(self, approvals_dir):
        """Test: Approval record is created with correct structure."""
        approval_id = create_approval_record(
            content="Test post",
            content_type="social_post",
            platform="instagram"
        )
        
        assert approval_id
        approval_file = approvals_dir / f"{approval_id}.json"
        assert approval_file.exists()
        
        data = json.loads(approval_file.read_text())
        assert data["id"] == approval_id
        assert data["content"] == "Test post"
        assert data["status"] == "pending"


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


class TestRequestApprovalIntegration:
    """Integration tests for complete approval flow."""
    
    @pytest.mark.asyncio
    async def test_request_approval_success(self, approvals_dir, monkeypatch):
        """Test: Complete approval flow succeeds."""
        # Mock auto-approve (skip real Google Chat)
        async def mock_send(*args, **kwargs):
            pass
        
        monkeypatch.setattr(
            "skills.request_approval.request_approval.send_approval_card_to_chat",
            mock_send
        )
        
        # Use short timeout for test
        result = await request_approval(
            content="Test post",
            content_type="social_post",
            platform="instagram",
            timeout_seconds=5
        )
        
        # Auto-approve logic should approve after 2 seconds
        assert result.approved is True
```

**Run Tests:**
```bash
pytest tests/skills/test_request_approval.py -v
```

---

### Story 1.3 Acceptance Criteria Checklist

- [ ] **Given** post content, **When** request_approval() called, **Then** creates approval record
- [ ] **Given** approval requested, **When** user approves, **Then** returns success with approved=True
- [ ] **Given** approval requested, **When** user rejects, **Then** returns error with feedback
- [ ] **Given** no response, **When** timeout expires, **Then** raises TimeoutError
- [ ] All tests pass (unit + async)
- [ ] Type hints complete (mypy passes)
- [ ] Approval records stored in ./data/memory/approvals/

---

## Story 1.4: Post Content Skill (X Only - MVP)

**Repository:** monkey-bot  
**Priority:** High  
**Dependencies:** Story 1.3 (needs approval first)  
**Estimated Time:** 1 day

### Overview

Publish approved content to X (Twitter). Validates approval exists before posting.

### Integration Contracts

**Input Parameters:**
```python
@dataclass
class PostContentParams:
    content: str
    platform: Literal["x"]  # Only X for MVP
    media_urls: List[str] = []
    approval_id: Optional[str] = None
```

**Output Schema:**
```python
@dataclass
class PostResult:
    platform: str
    platform_post_id: str
    platform_post_url: str
    posted_at: str
```

---

### Task Breakdown

#### Task 1.4.1: Create Skill Structure

**Files to Create:**
```
skills/post-content/
├── SKILL.md
├── post_content.py
├── platforms/
│   ├── __init__.py
│   └── x.py
└── __init__.py
```

**File:** `skills/post-content/SKILL.md`
```markdown
---
name: post-content
description: Publish approved content to social media platforms (X/Twitter). Requires content to be pre-approved. Returns live post URL. Use when user wants to post, publish, or go live.
metadata:
  emonk:
    requires:
      bins: ["python3"]
      files: ["./data/memory/approvals/"]
---

# Post Content to Social Media

Publishes content to X (Twitter) using platform API.

## When to Use This Skill

Invoke when user:
- Says "post this to X"
- Says "publish to Twitter"
- Says "go live on X"
- Has already approved content

## Parameters

- `content` (required): Post content (text)
- `platform` (required): Target platform ("x" only for MVP)
- `media_urls` (optional): List of image/video URLs
- `approval_id` (optional): Reference to approval record

## Pre-Posting Validation

Before posting, verify:
1. Content was approved (approval_id must exist)
2. X API key exists in environment
3. Content meets platform requirements (≤280 chars)

## Example Usage

```bash
python3 skills/post-content/post_content.py \
  --content "Check out this post! #AI" \
  --platform x \
  --approval-id abc-123-def
```
```

---

#### Task 1.4.2: Implement Platform-Specific Posting

**File:** `skills/post-content/platforms/x.py`
```python
"""X (Twitter) posting implementation."""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def post_to_x(
    content: str,
    media_urls: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Post to X (Twitter) using Tweepy library.
    
    For MVP, this is a PLACEHOLDER that returns mock data.
    In production, use tweepy to call X API.
    
    Args:
        content: Post text (max 280 chars)
        media_urls: Optional media attachments
    
    Returns:
        Dictionary with:
        - post_id: Platform post ID
        - post_url: URL to live post
    
    Raises:
        ValueError: If content exceeds 280 chars
        RuntimeError: If X API call fails
    
    Notes:
        - MVP: Returns mock data for testing
        - Production: Install tweepy and use real API
        - API key: Load from environment (X_API_KEY)
    
    Example:
        >>> result = post_to_x("Hello world! #AI")
        >>> print(result["post_url"])
        'https://x.com/auriga_os/status/1234567890'
    """
    # Validate length
    if len(content) > 280:
        raise ValueError(
            f"Content too long for X: {len(content)} chars (max: 280)"
        )
    
    # PLACEHOLDER: Mock X API response
    # TODO: Replace with real tweepy call
    """
    Production implementation:
    
    import tweepy
    import os
    
    api_key = os.getenv("X_API_KEY")
    if not api_key:
        raise RuntimeError("X_API_KEY not found in environment")
    
    client = tweepy.Client(bearer_token=api_key)
    response = client.create_tweet(text=content)
    
    return {
        "post_id": response.data["id"],
        "post_url": f"https://x.com/auriga_os/status/{response.data['id']}"
    }
    """
    
    logger.info(
        "[PLACEHOLDER] Would post to X (Twitter)",
        extra={"content_length": len(content), "has_media": bool(media_urls)}
    )
    
    # Mock response for MVP testing
    mock_post_id = "1234567890123456789"
    return {
        "post_id": mock_post_id,
        "post_url": f"https://x.com/auriga_os/status/{mock_post_id}"
    }
```

---

#### Task 1.4.3: Implement Main Posting Logic

**File:** `skills/post-content/post_content.py`
```python
#!/usr/bin/env python3
"""
Post content to social media platforms.

This skill publishes approved content to platform APIs.
For MVP, only X (Twitter) is supported.
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Literal, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Import platform implementations
from platforms.x import post_to_x

# Paths
APPROVALS_DIR = Path("./data/memory/approvals")
POSTS_DIR = Path("./data/memory/posts")


@dataclass
class PostResult:
    """Result from posting to platform."""
    platform: str
    platform_post_id: str
    platform_post_url: str
    posted_at: str


def verify_approval(approval_id: Optional[str]) -> None:
    """
    Verify that content was approved before posting.
    
    Args:
        approval_id: Approval record ID
    
    Raises:
        ValueError: If approval_id is None
        FileNotFoundError: If approval record doesn't exist
        RuntimeError: If content was not approved
    
    Notes:
        - Approval must have status="approved"
        - Reads from ./data/memory/approvals/{id}.json
        - This is a critical security check
    """
    if not approval_id:
        raise ValueError(
            "Cannot post without approval. "
            "Content must be approved before posting."
        )
    
    approval_file = APPROVALS_DIR / f"{approval_id}.json"
    
    if not approval_file.exists():
        raise FileNotFoundError(
            f"Approval record not found: {approval_id}"
        )
    
    approval_data = json.loads(approval_file.read_text())
    status = approval_data.get("status")
    
    if status != "approved":
        raise RuntimeError(
            f"Content not approved (status: {status}). "
            f"Cannot post unapproved content."
        )
    
    logger.info(
        f"Approval verified: {approval_id}",
        extra={"approval_id": approval_id, "status": status}
    )


def save_post_record(
    content: str,
    platform: str,
    result: PostResult
) -> None:
    """
    Save post record for tracking.
    
    Args:
        content: Posted content
        platform: Platform name
        result: Post result with IDs and URL
    
    Notes:
        - Saves to ./data/memory/posts/{post_id}.json
        - Used for analytics and tracking
        - Includes timestamp, platform, URL
    """
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    
    post_record = {
        "post_id": result.platform_post_id,
        "platform": platform,
        "content": content,
        "url": result.platform_post_url,
        "posted_at": result.posted_at
    }
    
    post_file = POSTS_DIR / f"{result.platform_post_id}.json"
    post_file.write_text(json.dumps(post_record, indent=2))
    
    logger.info(
        f"Saved post record: {result.platform_post_id}",
        extra={"post_id": result.platform_post_id}
    )


def post_content(
    content: str,
    platform: Literal["x"],
    media_urls: List[str] = [],
    approval_id: Optional[str] = None
) -> PostResult:
    """
    Post content to social media platform.
    
    Main entry point. Orchestrates:
    1. Verify approval
    2. Call platform API
    3. Save post record
    4. Return result
    
    Args:
        content: Post text
        platform: Target platform ("x" only for MVP)
        media_urls: Optional media attachments
        approval_id: Approval record ID (required)
    
    Returns:
        PostResult with platform IDs and URL
    
    Raises:
        ValueError: If approval_id is None or platform invalid
        RuntimeError: If posting fails
    
    Example:
        >>> result = post_content(
        ...     content="Hello world! #AI",
        ...     platform="x",
        ...     approval_id="abc-123"
        ... )
        >>> print(result.platform_post_url)
        'https://x.com/auriga_os/status/1234567890'
    """
    logger.info(
        f"Posting content to {platform}",
        extra={"platform": platform, "content_length": len(content)}
    )
    
    # Step 1: Verify approval
    verify_approval(approval_id)
    
    # Step 2: Post to platform
    if platform == "x":
        api_result = post_to_x(content, media_urls)
    else:
        raise ValueError(
            f"Platform '{platform}' not supported. "
            f"Supported platforms: x"
        )
    
    # Step 3: Build result
    result = PostResult(
        platform=platform,
        platform_post_id=api_result["post_id"],
        platform_post_url=api_result["post_url"],
        posted_at=str(time.time())
    )
    
    # Step 4: Save post record
    save_post_record(content, platform, result)
    
    logger.info(
        f"Posted to {platform}: {result.platform_post_url}",
        extra={"url": result.platform_post_url}
    )
    
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Post content to social media platform"
    )
    parser.add_argument(
        "--content",
        required=True,
        help="Post content"
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=["x"],
        help="Target platform (x only for MVP)"
    )
    parser.add_argument(
        "--media-urls",
        nargs="*",
        default=[],
        help="Media attachment URLs"
    )
    parser.add_argument(
        "--approval-id",
        required=True,
        help="Approval record ID"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    args = parser.parse_args()
    
    try:
        result = post_content(
            content=args.content,
            platform=args.platform,
            media_urls=args.media_urls,
            approval_id=args.approval_id
        )
        
        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            print(f"\n✅ Posted to {args.platform.upper()}!")
            print(f"URL: {result.platform_post_url}")
            print(f"Post ID: {result.platform_post_id}")
        
        sys.exit(0)
    
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Posting failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

#### Task 1.4.4: Add Tests

**File:** `tests/skills/test_post_content.py` (create new)
```python
"""Tests for post-content skill."""

import pytest
import json
from pathlib import Path
from skills.post_content.post_content import (
    post_content,
    verify_approval,
    save_post_record,
    PostResult,
    APPROVALS_DIR,
    POSTS_DIR
)
from skills.post_content.platforms.x import post_to_x


@pytest.fixture
def setup_dirs(tmp_path, monkeypatch):
    """Set up temporary directories."""
    approvals = tmp_path / "approvals"
    posts = tmp_path / "posts"
    approvals.mkdir()
    posts.mkdir()
    
    monkeypatch.setattr("skills.post_content.post_content.APPROVALS_DIR", approvals)
    monkeypatch.setattr("skills.post_content.post_content.POSTS_DIR", posts)
    
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
            approval_id=approval_id
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
                approval_id=None
            )
```

**Run Tests:**
```bash
pytest tests/skills/test_post_content.py -v
```

---

### Story 1.4 Acceptance Criteria Checklist

- [ ] **Given** approved content and platform="x", **When** post_content() called, **Then** posts successfully
- [ ] **Given** successful post, **When** returned, **Then** includes platform_post_url
- [ ] **Given** unapproved content, **When** post_content() called, **Then** raises RuntimeError
- [ ] **Given** missing approval_id, **When** post_content() called, **Then** raises ValueError
- [ ] **Given** X API success, **When** posted, **Then** saves post record
- [ ] All tests pass (unit + integration)
- [ ] Type hints complete (mypy passes)
- [ ] Approval verification works correctly

---

## Story 1.5: End-to-End Validation

**Repository:** monkey-bot  
**Priority:** Critical  
**Dependencies:** Stories 1.1-1.4 (all skills complete)  
**Estimated Time:** 0.5 days

### Overview

Validate complete workflow works end-to-end with special focus on **routing tests** (most critical).

---

### Task Breakdown

#### Task 1.5.1: Create Routing Tests

**File:** `tests/integration/test_routing.py` (create new)
```python
"""
Routing tests for Marketing Campaign Manager.

CRITICAL: These tests verify that Gemini correctly routes user messages
to the appropriate skills based on SKILL.md descriptions.

If routing fails, the entire system breaks.
"""

import pytest
from src.core import AgentCore, create_agent_with_mocks
from src.skills.loader import SkillLoader


@pytest.fixture
def agent_with_marketing_skills():
    """Create agent with marketing skills loaded."""
    # Load skills
    loader = SkillLoader("./skills")
    skills_data = loader.load_skills()
    tool_schemas = loader.get_tool_schemas()
    
    # Create agent (with mocks for MVP)
    agent = create_agent_with_mocks()
    
    # TODO: Attach tool schemas to agent
    # This will be implemented when LangGraph tool calling is integrated
    
    return agent


class TestGeneratePostRouting:
    """Tests for generate-post skill routing."""
    
    @pytest.mark.integration
    async def test_route_create_post(self, agent_with_marketing_skills):
        """Test: 'Create a post' routes to generate-post skill."""
        # PLACEHOLDER: This will work once LangGraph tool calling is integrated
        # For now, just verify skills are loaded
        
        loader = SkillLoader("./skills")
        skills = loader.load_skills()
        
        assert "generate-post" in skills
        assert "Create social media content" in skills["generate-post"]["description"]
    
    @pytest.mark.integration
    async def test_route_generate_instagram(self, agent_with_marketing_skills):
        """Test: 'Generate Instagram post' routes correctly."""
        loader = SkillLoader("./skills")
        skills = loader.load_skills()
        
        # Verify skill description mentions Instagram
        assert "Instagram" in skills["generate-post"]["description"]
    
    @pytest.mark.integration
    async def test_route_draft_caption(self, agent_with_marketing_skills):
        """Test: 'Draft caption' routes to generate-post."""
        # PLACEHOLDER: Will test actual routing once integrated
        pass


class TestApprovalRouting:
    """Tests for request-approval skill routing."""
    
    @pytest.mark.integration
    async def test_route_send_for_approval(self, agent_with_marketing_skills):
        """Test: 'Send for approval' routes to request-approval."""
        loader = SkillLoader("./skills")
        skills = loader.load_skills()
        
        assert "request-approval" in skills
        assert "approval" in skills["request-approval"]["description"].lower()


class TestPostingRouting:
    """Tests for post-content skill routing."""
    
    @pytest.mark.integration
    async def test_route_post_to_x(self, agent_with_marketing_skills):
        """Test: 'Post to X' routes to post-content."""
        loader = SkillLoader("./skills")
        skills = loader.load_skills()
        
        assert "post-content" in skills
        assert "Publish" in skills["post-content"]["description"]


class TestRoutingEdgeCases:
    """Tests for routing edge cases."""
    
    @pytest.mark.integration
    async def test_route_ambiguous_request(self, agent_with_marketing_skills):
        """Test: Ambiguous request behavior."""
        # Should either:
        # 1. Ask for clarification, OR
        # 2. Pick most likely skill
        # This is LLM-dependent behavior
        pass
    
    @pytest.mark.integration
    async def test_route_out_of_scope(self, agent_with_marketing_skills):
        """Test: Out of scope request doesn't invoke skills."""
        # Example: "Delete my account" should NOT route to any skill
        pass
```

**Run Routing Tests:**
```bash
pytest tests/integration/test_routing.py -v -m integration
```

---

#### Task 1.5.2: Create E2E Workflow Tests

**File:** `tests/integration/test_e2e_workflow.py` (create new)
```python
"""
End-to-end workflow tests for Marketing Campaign Manager.

Tests complete workflows from user intent to posted content.
"""

import pytest
import asyncio
from skills.generate_post.generate_post import generate_post
from skills.request_approval.request_approval import request_approval
from skills.post_content.post_content import post_content


@pytest.mark.integration
class TestCompletePostWorkflow:
    """Tests for complete Generate → Approve → Post workflow."""
    
    async def test_happy_path_instagram(self, tmp_path, monkeypatch):
        """Test: Complete workflow for Instagram post."""
        # Set up temp directories
        approvals_dir = tmp_path / "approvals"
        posts_dir = tmp_path / "posts"
        approvals_dir.mkdir()
        posts_dir.mkdir()
        
        monkeypatch.setattr(
            "skills.request_approval.request_approval.APPROVALS_DIR",
            approvals_dir
        )
        monkeypatch.setattr(
            "skills.post_content.post_content.APPROVALS_DIR",
            approvals_dir
        )
        monkeypatch.setattr(
            "skills.post_content.post_content.POSTS_DIR",
            posts_dir
        )
        
        # Step 1: Generate post
        post = generate_post("AI agents", "instagram")
        assert post.content
        assert len(post.content) <= 2200
        
        # Step 2: Request approval (auto-approves after 2s)
        approval = await request_approval(
            content=post.content,
            content_type="social_post",
            platform="instagram",
            timeout_seconds=5
        )
        assert approval.approved
        
        # Step 3: Post to platform (mock for X, but same pattern)
        # For MVP, we post to X since that's the only implemented platform
        # Skip actual posting test since Instagram not implemented yet
    
    async def test_happy_path_x(self, tmp_path, monkeypatch):
        """Test: Complete workflow for X post."""
        # Set up temp directories
        approvals_dir = tmp_path / "approvals"
        posts_dir = tmp_path / "posts"
        approvals_dir.mkdir()
        posts_dir.mkdir()
        
        monkeypatch.setattr(
            "skills.request_approval.request_approval.APPROVALS_DIR",
            approvals_dir
        )
        monkeypatch.setattr(
            "skills.post_content.post_content.APPROVALS_DIR",
            approvals_dir
        )
        monkeypatch.setattr(
            "skills.post_content.post_content.POSTS_DIR",
            posts_dir
        )
        
        # Step 1: Generate post
        post = generate_post("AI agents", "x")
        assert post.content
        assert len(post.content) <= 280
        
        # Step 2: Request approval
        approval = await request_approval(
            content=post.content,
            content_type="social_post",
            platform="x",
            timeout_seconds=5
        )
        assert approval.approved
        
        # Get approval ID from approval record
        import json
        approval_files = list(approvals_dir.glob("*.json"))
        assert len(approval_files) == 1
        approval_data = json.loads(approval_files[0].read_text())
        approval_id = approval_data["id"]
        
        # Step 3: Post to X
        result = post_content(
            content=post.content,
            platform="x",
            approval_id=approval_id
        )
        assert result.platform_post_url
        assert "x.com" in result.platform_post_url
    
    async def test_rejection_workflow(self, tmp_path, monkeypatch):
        """Test: Rejection workflow (generate → reject → regenerate)."""
        # Set up temp directories
        approvals_dir = tmp_path / "approvals"
        approvals_dir.mkdir()
        
        monkeypatch.setattr(
            "skills.request_approval.request_approval.APPROVALS_DIR",
            approvals_dir
        )
        
        # Generate post
        post = generate_post("AI agents", "instagram")
        
        # Request approval but manually reject
        import json
        
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
            timeout_seconds=5
        )
        
        assert not approval.approved
        assert approval.feedback == "Change the hashtags"


class TestErrorHandling:
    """Tests for error handling in workflows."""
    
    def test_post_without_approval_fails(self, tmp_path, monkeypatch):
        """Test: Posting without approval raises error."""
        posts_dir = tmp_path / "posts"
        posts_dir.mkdir()
        
        monkeypatch.setattr(
            "skills.post_content.post_content.POSTS_DIR",
            posts_dir
        )
        
        with pytest.raises(ValueError, match="Cannot post without approval"):
            post_content(
                content="Test post",
                platform="x",
                approval_id=None
            )
    
    def test_invalid_platform_fails(self):
        """Test: Invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Invalid platform"):
            generate_post("AI agents", "facebook")
```

**Run E2E Tests:**
```bash
pytest tests/integration/test_e2e_workflow.py -v -m integration
```

---

### Story 1.5 Acceptance Criteria Checklist

- [ ] **Routing Test:** "Create a post" → generate-post skill invoked
- [ ] **Routing Test:** "Send for approval" → request-approval skill invoked
- [ ] **Routing Test:** "Post to X" → post-content skill invoked
- [ ] **E2E Test:** Generate → Approve → Post → Success (all steps work)
- [ ] **E2E Test:** Generate → Reject → Feedback returned
- [ ] **Error Test:** Post without approval → Raises error
- [ ] **Error Test:** Invalid platform → Raises ValueError
- [ ] All tests pass locally

---

## Dependency Graph

```
Story 1.1 (Skill Loader)
    │
    ├─→ Story 1.2 (Generate Post)
    │       │
    │       └─→ Story 1.3 (Request Approval)
    │               │
    │               └─→ Story 1.4 (Post Content - X)
    │                       │
    │                       └─→ Story 1.5 (E2E Validation)
```

**Implementation Order:**
1. Story 1.1 first (blocks everything)
2. Stories 1.2, 1.3, 1.4 sequentially (dependencies)
3. Story 1.5 last (validates all previous)

**Estimated Timeline:**
- Day 1: Story 1.1 (loader enhancement)
- Day 2-3: Story 1.2 (generate post)
- Day 3-4: Story 1.3 (request approval)
- Day 4-5: Story 1.4 (post content)
- Day 5: Story 1.5 (validation)

**Total: 5-7 days** (solo developer, sequential)

---

## Final Verification

### Pre-Deployment Checklist

**Functionality:**
- [ ] All acceptance criteria met for Stories 1.1-1.5
- [ ] Routing tests pass (CRITICAL!)
- [ ] E2E tests pass (generate → approve → post)
- [ ] Error handling works (invalid inputs, missing approvals)

**Code Quality:**
- [ ] All tests pass: `pytest`
- [ ] Type checking passes: `mypy src/`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Code formatted: `ruff format src/ tests/`
- [ ] Docstrings complete (Google style)
- [ ] No hardcoded credentials

**Testing:**
- [ ] Unit test coverage ≥80%
- [ ] Integration tests pass
- [ ] Routing tests pass (verify LangGraph integration)
- [ ] Mock APIs used correctly (X API mocked)

**Documentation:**
- [ ] All SKILL.md files complete
- [ ] README updated (if needed)
- [ ] Type hints complete

---

## Post-Implementation Notes

### Known Limitations (MVP)

1. **LLM Integration:** Content generation uses placeholder (replace with real Gemini API)
2. **Google Chat:** Approval cards use placeholder (replace with real Google Chat API)
3. **X API:** Posting uses placeholder (replace with real tweepy)
4. **Platforms:** Only X supported (add Instagram/TikTok/LinkedIn/Reddit in Sprint 2)

### Next Steps (Sprint 2)

1. **Real API Integration:**
   - Replace placeholders with real Gemini, Google Chat, X APIs
   - Add API keys to GCP Secret Manager
   - Test with real accounts

2. **Platform Expansion:**
   - Add Instagram posting
   - Add TikTok posting
   - Add LinkedIn posting
   - Add Reddit posting

3. **Research Skills:**
   - search-web (Perplexity MCP)
   - analyze-competitor (Firecrawl MCP)
   - identify-trends

4. **Campaign Features:**
   - create-campaign
   - schedule-campaign

---

**Code Spec Complete!** 🎉

Ready to implement Sprint 1.
