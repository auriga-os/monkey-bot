"""Instagram posting implementation."""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def post_to_instagram(content: str, media_urls: List[str]) -> Dict[str, Any]:
    """
    Post to Instagram using Graph API.

    For MVP, this is a PLACEHOLDER that returns mock data.
    In production, use Facebook Graph API to post to Instagram.

    Instagram requires a 2-step posting process:
    1. Create media container (upload image to Instagram)
    2. Publish the container

    Args:
        content: Caption text (max 2200 chars)
        media_urls: List of image URLs (at least 1 required)

    Returns:
        Dictionary with:
        - post_id: Platform post ID
        - post_url: URL to live post

    Raises:
        ValueError: If no media provided, caption too long, or too many hashtags
        RuntimeError: If Instagram API call fails

    Notes:
        - MVP: Returns mock data for testing
        - Production: Use Facebook Graph API
        - Requires Instagram Business account
        - API key: Load from environment (INSTAGRAM_USER_ID, INSTAGRAM_ACCESS_TOKEN)

    Example:
        >>> result = post_to_instagram(
        ...     "Amazing sunset! #photography",
        ...     ["https://example.com/sunset.jpg"]
        ... )
        >>> print(result["post_url"])
        'https://instagram.com/p/ABC123def'
    """
    # Validate media requirement
    if not media_urls or len(media_urls) == 0:
        raise ValueError("At least 1 image required for Instagram posts")

    # Validate caption length (max 2200 chars)
    if len(content) > 2200:
        raise ValueError(f"Caption too long for Instagram: {len(content)} chars (max: 2200)")

    # Validate hashtag count (max 30)
    hashtag_count = len(re.findall(r'#\w+', content))
    if hashtag_count > 30:
        raise ValueError(
            f"Too many hashtags for Instagram: {hashtag_count} (max: 30)"
        )

    # PLACEHOLDER: Mock Instagram API response
    # TODO: Replace with real Graph API call
    """
    Production implementation:

    import os
    import requests

    IG_USER_ID = os.getenv("INSTAGRAM_USER_ID")
    ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    BASE_URL = "https://graph.facebook.com/v18.0"

    if not IG_USER_ID or not ACCESS_TOKEN:
        raise RuntimeError("INSTAGRAM_USER_ID or INSTAGRAM_ACCESS_TOKEN not found")

    # Step 1: Create media container
    container_response = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media",
        data={
            "image_url": media_urls[0],  # Use first image (carousel for multiple)
            "caption": content,
            "access_token": ACCESS_TOKEN
        }
    )
    container_response.raise_for_status()
    container_id = container_response.json()["id"]

    # Step 2: Publish container
    publish_response = requests.post(
        f"{BASE_URL}/{IG_USER_ID}/media_publish",
        data={
            "creation_id": container_id,
            "access_token": ACCESS_TOKEN
        }
    )
    publish_response.raise_for_status()
    post_id = publish_response.json()["id"]

    return {
        "post_id": post_id,
        "post_url": f"https://instagram.com/p/{post_id}"
    }
    """

    logger.info(
        "[PLACEHOLDER] Would post to Instagram",
        extra={
            "caption_length": len(content),
            "media_count": len(media_urls),
            "hashtag_count": hashtag_count
        },
    )

    # Mock response for MVP testing
    mock_post_id = "ABC123def456GHI"
    return {
        "post_id": mock_post_id,
        "post_url": f"https://instagram.com/p/{mock_post_id}",
    }
