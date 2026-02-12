"""Platform-specific limits and requirements."""

from typing import Any, Dict

PLATFORM_LIMITS: Dict[str, Dict[str, Any]] = {
    "instagram": {
        "char_limit": 2200,
        "min_hashtags": 3,
        "max_hashtags": 30,
        "hashtag_recommended": True,
    },
    "tiktok": {
        "char_limit": 2200,
        "min_hashtags": 3,
        "max_hashtags": 30,
        "hashtag_recommended": True,
    },
    "x": {
        "char_limit": 280,
        "min_hashtags": 1,
        "max_hashtags": 2,
        "hashtag_recommended": False,  # Optional for X
    },
    "linkedin": {
        "char_limit": 3000,
        "min_hashtags": 3,
        "max_hashtags": 5,
        "hashtag_recommended": True,
    },
    "reddit": {
        "char_limit": 40000,
        "min_hashtags": 0,
        "max_hashtags": 0,
        "hashtag_recommended": False,  # Reddit uses flair instead
    },
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
            f"Unknown platform: {platform}. Valid platforms: {', '.join(VALID_PLATFORMS)}"
        )

    return PLATFORM_LIMITS[platform]
