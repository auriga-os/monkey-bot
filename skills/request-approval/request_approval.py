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
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
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


def create_approval_record(content: str, content_type: str, platform: Optional[str]) -> str:
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
        "modified_content": None,
    }

    approval_file.write_text(json.dumps(approval_data, indent=2))

    logger.info(
        f"Created approval record: {approval_id}",
        extra={"approval_id": approval_id, "content_type": content_type},
    )

    return approval_id


def send_approval_card_to_chat(
    approval_id: str,
    content: str,
    content_type: str,
    platform: Optional[str],
    approvals_dir: Path = APPROVALS_DIR,
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
        approvals_dir: Directory for approval files (for testing)

    Notes:
        - MVP: Just logs card data
        - Production: Call Google Chat API with card JSON
        - Card includes: Content preview, Approve/Reject/Modify buttons
    """
    # PLACEHOLDER: Google Chat API integration
    # TODO: Replace with real Google Chat API call

    card = {
        "cardsV2": [
            {
                "cardId": f"approval-{approval_id}",
                "card": {
                    "header": {
                        "title": f"Approval Request: {content_type}",
                        "subtitle": f"Platform: {platform or 'N/A'}",
                    },
                    "sections": [{"widgets": [{"textParagraph": {"text": content[:500]}}]}],
                    "cardActions": [
                        {
                            "actionLabel": "✅ Approve",
                            "onClick": {
                                "action": {
                                    "function": "approve",
                                    "parameters": [{"key": "approval_id", "value": approval_id}],
                                }
                            },
                        },
                        {
                            "actionLabel": "❌ Reject",
                            "onClick": {
                                "action": {
                                    "function": "reject",
                                    "parameters": [{"key": "approval_id", "value": approval_id}],
                                }
                            },
                        },
                        {
                            "actionLabel": "✏️ Modify",
                            "onClick": {
                                "action": {
                                    "function": "modify",
                                    "parameters": [{"key": "approval_id", "value": approval_id}],
                                }
                            },
                        },
                    ],
                },
            }
        ]
    }

    logger.info(
        f"[PLACEHOLDER] Would send Google Chat card for approval {approval_id}",
        extra={"card": card},
    )

    # For MVP testing: Automatically approve after 2 seconds
    # TODO: Remove this in production
    def auto_approve():
        time.sleep(2)
        approval_file = approvals_dir / f"{approval_id}.json"
        if approval_file.exists():
            data = json.loads(approval_file.read_text())
            data["status"] = "approved"
            data["feedback"] = "Auto-approved for MVP testing"
            approval_file.write_text(json.dumps(data, indent=2))

    threading.Thread(target=auto_approve, daemon=True).start()


async def wait_for_approval(approval_id: str, timeout_seconds: int) -> ApprovalResult:
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
        extra={"approval_id": approval_id, "timeout": timeout_seconds},
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
                timestamp=str(time.time()),
            )

        elif status == "rejected":
            logger.info(f"Approval {approval_id}: REJECTED")
            return ApprovalResult(
                approved=False,
                feedback=data.get("feedback"),
                modified_content=None,
                timestamp=str(time.time()),
            )

        # Still pending, wait and check again
        await asyncio.sleep(1)

    # Timeout
    logger.warning(f"Approval {approval_id}: TIMEOUT")
    raise TimeoutError(f"Approval timeout after {timeout_seconds}s. No response from user.")


async def request_approval(
    content: str,
    content_type: Literal["social_post", "campaign", "image"],
    platform: Optional[str] = None,
    timeout_seconds: int = 3600,
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
        extra={"content_type": content_type, "platform": platform},
    )

    # Step 1: Create approval record
    approval_id = create_approval_record(content, content_type, platform)

    # Step 2: Send Google Chat card
    send_approval_card_to_chat(approval_id, content, content_type, platform, APPROVALS_DIR)

    # Step 3: Wait for response
    result = await wait_for_approval(approval_id, timeout_seconds)

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Request approval for content")
    parser.add_argument("--content", required=True, help="Content to approve")
    parser.add_argument(
        "--content-type",
        required=True,
        choices=["social_post", "campaign", "image"],
        help="Type of content",
    )
    parser.add_argument("--platform", help="Platform if social post")
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="Timeout in seconds (default: 3600)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    try:
        result = asyncio.run(
            request_approval(
                content=args.content,
                content_type=args.content_type,
                platform=args.platform,
                timeout_seconds=args.timeout,
            )
        )

        if args.json:
            print(json.dumps(asdict(result), indent=2))
        else:
            if result.approved:
                print("\n✅ APPROVED")
                if result.feedback:
                    print(f"Feedback: {result.feedback}")
                if result.modified_content:
                    print(f"Modified content:\n{result.modified_content}")
            else:
                print("\n❌ REJECTED")
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
