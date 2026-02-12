"""X (Twitter) posting implementation."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def post_to_x(content: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]:
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
        raise ValueError(f"Content too long for X: {len(content)} chars (max: 280)")

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
        extra={"content_length": len(content), "has_media": bool(media_urls)},
    )

    # Mock response for MVP testing
    mock_post_id = "1234567890123456789"
    return {
        "post_id": mock_post_id,
        "post_url": f"https://x.com/auriga_os/status/{mock_post_id}",
    }
