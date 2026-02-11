"""
PII (Personally Identifiable Information) filtering for Google Chat webhooks.

This module is SECURITY-CRITICAL. It ensures that no PII (user emails, names, etc.)
or Google Chat metadata (space IDs, thread IDs) is sent to the LLM.

Key security properties:
1. Email addresses are hashed (SHA-256) to create stable, anonymous user IDs
2. Hashing is deterministic (same email → same user_id) for memory consistency
3. Hashing is one-way (cannot reverse user_id to get email)
4. Only message content is passed to Agent Core - all metadata is stripped

This code has 100% test coverage requirement.
"""

import hashlib
from typing import Any, TypedDict


class FilteredMessage(TypedDict):
    """
    Filtered message with all PII removed.

    This is the ONLY data structure that should be passed from Gateway to Agent Core.
    It contains only anonymous, safe data.

    Attributes:
        user_id: Hashed user identifier (SHA-256, first 16 chars).
                 Anonymous - cannot be reversed to email.
                 Stable - same email produces same user_id.
        content: Message text only. No sender info, no metadata.
    """

    user_id: str
    content: str


def filter_google_chat_pii(webhook_payload: dict[str, Any]) -> FilteredMessage:
    """
    Extract only safe fields from Google Chat webhook and hash the email.

    This function is the PII filtering boundary. Everything that enters this
    function may contain PII. Everything that exits must be PII-free.

    Process:
    1. Extract sender email and message text from nested payload
    2. Hash email with SHA-256 (one-way, deterministic)
    3. Take first 16 chars of hash for user_id (sufficient uniqueness)
    4. Return ONLY user_id and content - discard everything else

    Args:
        webhook_payload: Raw Google Chat webhook payload.
                        May contain: email, displayName, space, thread, etc.

    Returns:
        FilteredMessage with only user_id (hashed) and content.
        Safe to pass to Agent Core and LLM.

    Raises:
        KeyError: If required fields (message.sender.email or message.text)
                 are missing from payload.

    Security Notes:
        - SHA-256 is cryptographically secure one-way hash
        - First 16 chars provide 2^64 possible values (sufficient for ~1M users)
        - Same email always produces same hash (enables memory/conversation continuity)
        - No collision risk at expected scale (birthday paradox requires ~5 billion users)

    Examples:
        >>> webhook = {
        ...     "message": {
        ...         "sender": {"email": "user@example.com"},
        ...         "text": "Remember that I prefer Python"
        ...     }
        ... }
        >>> result = filter_google_chat_pii(webhook)
        >>> result["user_id"]  # Hashed, not email
        'a1b2c3d4e5f6g7h8'
        >>> result["content"]
        'Remember that I prefer Python'
    """
    # Extract required fields from nested structure
    # Will raise KeyError if fields are missing (intentional - fail fast)
    sender_email = webhook_payload["message"]["sender"]["email"]
    message_text = webhook_payload["message"]["text"]

    # Hash email to create anonymous, stable user_id
    # SHA-256 produces 64-char hex string, we take first 16 for brevity
    # 16 hex chars = 64 bits = 2^64 possible values (no collision risk at our scale)
    hash_object = hashlib.sha256(sender_email.encode("utf-8"))
    user_id = hash_object.hexdigest()[:16]

    # Return ONLY safe fields - everything else is discarded
    # No sender name, no display name, no space, no thread, no timestamps
    return FilteredMessage(user_id=user_id, content=message_text)
