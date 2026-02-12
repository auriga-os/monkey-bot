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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Import platform limits
try:
    from platform_config import VALID_PLATFORMS, get_platform_limit
except ImportError:
    from .platform_config import VALID_PLATFORMS, get_platform_limit

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
            extra={"path": str(BRAND_VOICE_PATH)},
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
    brand_voice: Optional[str],
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
        content = content[: char_limit - 3] + "..."

    # Generate hashtags
    hashtags = []
    if include_hashtags and limits["hashtag_recommended"]:
        hashtags = ["#AI", "#Tech", "#Innovation"][: limits["max_hashtags"]]

    return {"content": content, "hashtags": hashtags}


def validate_post(
    content: str, platform: str, hashtags: List[str], brand_voice: Optional[str]
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
    first_line = content.split("\n")[0]
    attention_words = [
        "explore",
        "discover",
        "learn",
        "check",
        "dive",
        "unveil",
        "reveal",
    ]
    has_hook = len(first_line) < 80 and any(word in first_line.lower() for word in attention_words)

    # Check 3: Has call-to-action
    cta_phrases = [
        "check out",
        "learn more",
        "share",
        "comment",
        "double-tap",
        "link in bio",
        "?",
    ]
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
        brand_voice_valid=brand_voice_valid,
    )


def generate_post(
    topic: str,
    platform: Literal["instagram", "tiktok", "x", "linkedin", "reddit"],
    tone: str = "professional",
    include_hashtags: bool = True,
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
        extra={"platform": platform, "topic": topic, "tone": tone},
    )

    # Validate platform
    if platform not in VALID_PLATFORMS:
        raise ValueError(
            f"Invalid platform: {platform}. Valid platforms: {', '.join(VALID_PLATFORMS)}"
        )

    # Load brand voice (optional)
    brand_voice = load_brand_voice()

    # Generate content
    generated = generate_content_with_llm(
        topic=topic,
        platform=platform,
        tone=tone,
        include_hashtags=include_hashtags,
        brand_voice=brand_voice,
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
        validation=validation,
    )

    logger.info(
        f"Generated post: {len(content)} chars, "
        f"{len(hashtags)} hashtags, "
        f"valid={validation.within_limit}",
        extra={"validation": asdict(validation)},
    )

    return post


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate social media post for platform")
    parser.add_argument("--topic", required=True, help="What the post is about")
    parser.add_argument(
        "--platform",
        required=True,
        choices=VALID_PLATFORMS,
        help="Target platform",
    )
    parser.add_argument(
        "--tone",
        default="professional",
        help="Desired tone (default: professional)",
    )
    parser.add_argument(
        "--include-hashtags",
        action="store_true",
        default=True,
        help="Include hashtags (default: True)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        post = generate_post(
            topic=args.topic,
            platform=args.platform,
            tone=args.tone,
            include_hashtags=args.include_hashtags,
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
