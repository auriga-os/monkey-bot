"""TikTok posting implementation."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def post_to_tiktok(content: str, media_urls: List[str]) -> Dict[str, Any]:
    """
    Post video to TikTok using Content Posting API.

    For MVP, this is a PLACEHOLDER that returns mock data.
    In production, use TikTok Content Posting API.

    TikTok requires a 3-step posting process:
    1. Initialize upload (get upload URL)
    2. Upload video to provided URL
    3. Publish video with metadata

    Args:
        content: Video caption/description (max 2200 chars)
        media_urls: List of video URLs (exactly 1 required)

    Returns:
        Dictionary with:
        - post_id: Platform post ID
        - post_url: URL to live post

    Raises:
        ValueError: If not video, multiple videos, or caption invalid
        RuntimeError: If TikTok API call fails

    Notes:
        - MVP: Returns mock data for testing
        - Production: Use TikTok Content Posting API
        - Requires OAuth authentication
        - Video requirements: MP4, max 4GB, 3-60 seconds recommended
        - API key: Load from environment (TIKTOK_ACCESS_TOKEN, TIKTOK_USERNAME)

    Example:
        >>> result = post_to_tiktok(
        ...     "Check out this cool video! #fyp",
        ...     ["https://example.com/video.mp4"]
        ... )
        >>> print(result["post_url"])
        'https://tiktok.com/@username/video/1234567890'
    """
    # Validate video requirement - exactly 1 video
    if not media_urls or len(media_urls) != 1:
        raise ValueError("TikTok requires exactly 1 video URL")

    video_url = media_urls[0]

    # Validate it's a video file (check extension)
    valid_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv']
    if not any(video_url.lower().endswith(ext) for ext in valid_extensions):
        raise ValueError(
            f"TikTok media must be a video file (mp4, mov, avi, webm, etc.). "
            f"Got: {video_url}"
        )

    # Validate caption length (max 2200 chars)
    if len(content) > 2200:
        raise ValueError(
            f"Description too long for TikTok: {len(content)} chars (max: 2200)"
        )

    # PLACEHOLDER: Mock TikTok API response
    # TODO: Replace with real TikTok Content Posting API call
    """
    Production implementation:

    import os
    import requests

    ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")
    USERNAME = os.getenv("TIKTOK_USERNAME", "auriga_os")
    BASE_URL = "https://open.tiktokapis.com/v2"

    if not ACCESS_TOKEN:
        raise RuntimeError("TIKTOK_ACCESS_TOKEN not found in environment")

    # Step 1: Initialize upload
    init_response = requests.post(
        f"{BASE_URL}/post/publish/inbox/video/init/",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        json={
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": 12345678,  # Get actual file size
                "chunk_size": 5242880,   # 5MB chunks
                "total_chunk_count": 3   # Calculate based on video size
            }
        }
    )
    init_response.raise_for_status()
    upload_url = init_response.json()["data"]["upload_url"]
    publish_id = init_response.json()["data"]["publish_id"]

    # Step 2: Upload video (simplified - actual implementation needs chunking)
    # Upload video file to upload_url

    # Step 3: Publish video
    publish_response = requests.post(
        f"{BASE_URL}/post/publish/video/init/",
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        json={
            "publish_id": publish_id,
            "post_info": {
                "title": content[:100],  # First 100 chars as title
                "description": content,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False
            }
        }
    )
    publish_response.raise_for_status()
    post_id = publish_response.json()["data"]["publish_id"]

    return {
        "post_id": post_id,
        "post_url": f"https://tiktok.com/@{USERNAME}/video/{post_id}"
    }
    """

    logger.info(
        "[PLACEHOLDER] Would post to TikTok",
        extra={
            "description_length": len(content),
            "video_url": video_url
        },
    )

    # Mock response for MVP testing
    mock_post_id = "7234567890123456789"
    mock_username = "auriga_os"

    return {
        "post_id": mock_post_id,
        "post_url": f"https://tiktok.com/@{mock_username}/video/{mock_post_id}",
    }
