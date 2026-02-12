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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Literal, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

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
        raise ValueError("Cannot post without approval. Content must be approved before posting.")

    approval_file = APPROVALS_DIR / f"{approval_id}.json"

    if not approval_file.exists():
        raise FileNotFoundError(f"Approval record not found: {approval_id}")

    approval_data = json.loads(approval_file.read_text())
    status = approval_data.get("status")

    if status != "approved":
        raise RuntimeError(
            f"Content not approved (status: {status}). Cannot post unapproved content."
        )

    logger.info(
        f"Approval verified: {approval_id}",
        extra={"approval_id": approval_id, "status": status},
    )


def save_post_record(content: str, platform: str, result: PostResult) -> None:
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
        "posted_at": result.posted_at,
    }

    post_file = POSTS_DIR / f"{result.platform_post_id}.json"
    post_file.write_text(json.dumps(post_record, indent=2))

    logger.info(
        f"Saved post record: {result.platform_post_id}",
        extra={"post_id": result.platform_post_id},
    )


def post_content(
    content: str,
    platform: Literal["x"],
    media_urls: List[str] = [],
    approval_id: Optional[str] = None,
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
    # Import here to avoid circular dependency issues
    from platforms.x import post_to_x

    logger.info(
        f"Posting content to {platform}",
        extra={"platform": platform, "content_length": len(content)},
    )

    # Step 1: Verify approval
    verify_approval(approval_id)

    # Step 2: Post to platform
    if platform == "x":
        api_result = post_to_x(content, media_urls)
    else:
        raise ValueError(f"Platform '{platform}' not supported. Supported platforms: x")

    # Step 3: Build result
    result = PostResult(
        platform=platform,
        platform_post_id=api_result["post_id"],
        platform_post_url=api_result["post_url"],
        posted_at=str(time.time()),
    )

    # Step 4: Save post record
    save_post_record(content, platform, result)

    logger.info(
        f"Posted to {platform}: {result.platform_post_url}",
        extra={"url": result.platform_post_url},
    )

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Post content to social media platform")
    parser.add_argument("--content", required=True, help="Post content")
    parser.add_argument(
        "--platform",
        required=True,
        choices=["x"],
        help="Target platform (x only for MVP)",
    )
    parser.add_argument(
        "--media-urls",
        nargs="*",
        default=[],
        help="Media attachment URLs",
    )
    parser.add_argument(
        "--approval-id",
        required=True,
        help="Approval record ID",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        result = post_content(
            content=args.content,
            platform=args.platform,
            media_urls=args.media_urls,
            approval_id=args.approval_id,
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
