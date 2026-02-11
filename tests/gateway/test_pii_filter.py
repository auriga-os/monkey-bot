"""
Tests for PII filtering.

This is SECURITY-CRITICAL code with 100% coverage requirement.
Tests verify that:
1. Emails are hashed (not stored in plain text)
2. Hashing is stable (same email → same user_id)
3. Hashing is unique (different emails → different user_ids)
4. All Google Chat metadata is stripped
5. Error handling for missing fields
"""

import hashlib

import pytest

from src.gateway.pii_filter import FilteredMessage, filter_google_chat_pii


class TestFilterGoogleChatPII:
    """Tests for filter_google_chat_pii function."""

    def test_filter_pii_success(self) -> None:
        """Test successful PII filtering with minimal payload."""
        webhook = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Remember that I prefer Python",
            }
        }

        result = filter_google_chat_pii(webhook)

        # Verify structure
        assert isinstance(result, dict)
        assert set(result.keys()) == {"user_id", "content"}

        # Verify user_id is hashed (not email)
        assert result["user_id"] != "user@example.com"
        assert "@" not in result["user_id"]
        assert len(result["user_id"]) == 16  # First 16 chars of SHA-256 hex

        # Verify content is preserved
        assert result["content"] == "Remember that I prefer Python"

    def test_filter_pii_strips_metadata(self) -> None:
        """Test that Google Chat metadata is stripped from output."""
        webhook = {
            "message": {
                "sender": {
                    "email": "user@example.com",
                    "displayName": "Test User",  # Should be stripped
                },
                "text": "Hello",
                "space": {"name": "spaces/xxx"},  # Should be stripped
                "thread": {"name": "spaces/xxx/threads/yyy"},  # Should be stripped
                "createTime": "2026-02-11T22:00:00Z",  # Should be stripped
            }
        }

        result = filter_google_chat_pii(webhook)

        # Only user_id and content should be in result
        assert set(result.keys()) == {"user_id", "content"}

        # Verify no metadata leaked into result values
        assert "space" not in str(result)
        assert "thread" not in str(result)
        assert "displayName" not in str(result)
        assert "Test User" not in str(result)
        assert "createTime" not in str(result)

    def test_filter_pii_stable_hashing(self) -> None:
        """Test that same email produces same user_id (deterministic hashing)."""
        webhook1 = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Message 1",
            }
        }
        webhook2 = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Message 2",
            }
        }

        result1 = filter_google_chat_pii(webhook1)
        result2 = filter_google_chat_pii(webhook2)

        # Same email should produce same user_id (enables conversation continuity)
        assert result1["user_id"] == result2["user_id"]

        # But content should be different
        assert result1["content"] != result2["content"]

    def test_filter_pii_different_emails(self) -> None:
        """Test that different emails produce different user_ids (uniqueness)."""
        webhook1 = {
            "message": {
                "sender": {"email": "user1@example.com"},
                "text": "Message",
            }
        }
        webhook2 = {
            "message": {
                "sender": {"email": "user2@example.com"},
                "text": "Message",
            }
        }

        result1 = filter_google_chat_pii(webhook1)
        result2 = filter_google_chat_pii(webhook2)

        # Different emails should produce different user_ids
        assert result1["user_id"] != result2["user_id"]

        # Content should be same (not email-dependent)
        assert result1["content"] == result2["content"]

    def test_filter_pii_hashing_algorithm(self) -> None:
        """Test that hashing uses SHA-256 and produces expected format."""
        email = "test@example.com"
        webhook = {
            "message": {
                "sender": {"email": email},
                "text": "Test",
            }
        }

        result = filter_google_chat_pii(webhook)

        # Manually compute expected hash
        expected_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()[:16]

        # Verify result matches expected hash
        assert result["user_id"] == expected_hash

        # Verify hash is hex string (0-9, a-f)
        assert all(c in "0123456789abcdef" for c in result["user_id"])

    def test_filter_pii_unicode_email(self) -> None:
        """Test that unicode characters in email are handled correctly."""
        webhook = {
            "message": {
                "sender": {"email": "user+tag@example.com"},
                "text": "Test with unicode: 🎉",
            }
        }

        result = filter_google_chat_pii(webhook)

        # Should not raise exception
        assert len(result["user_id"]) == 16
        assert result["content"] == "Test with unicode: 🎉"

    def test_filter_pii_missing_email(self) -> None:
        """Test error handling when email is missing."""
        webhook = {
            "message": {
                "sender": {},  # Missing email
                "text": "Hello",
            }
        }

        # Should raise KeyError (fail fast for security)
        with pytest.raises(KeyError) as exc_info:
            filter_google_chat_pii(webhook)

        assert "email" in str(exc_info.value)

    def test_filter_pii_missing_text(self) -> None:
        """Test error handling when text is missing."""
        webhook = {
            "message": {
                "sender": {"email": "user@example.com"},
                # Missing text
            }
        }

        # Should raise KeyError (fail fast for security)
        with pytest.raises(KeyError) as exc_info:
            filter_google_chat_pii(webhook)

        assert "text" in str(exc_info.value)

    def test_filter_pii_missing_sender(self) -> None:
        """Test error handling when sender is missing."""
        webhook = {
            "message": {
                # Missing sender
                "text": "Hello",
            }
        }

        # Should raise KeyError (fail fast for security)
        with pytest.raises(KeyError) as exc_info:
            filter_google_chat_pii(webhook)

        assert "sender" in str(exc_info.value)

    def test_filter_pii_missing_message(self) -> None:
        """Test error handling when message is missing."""
        webhook = {}  # Missing message

        # Should raise KeyError (fail fast for security)
        with pytest.raises(KeyError) as exc_info:
            filter_google_chat_pii(webhook)

        assert "message" in str(exc_info.value)

    def test_filter_pii_empty_email(self) -> None:
        """Test behavior with empty string email (should hash empty string)."""
        webhook = {
            "message": {
                "sender": {"email": ""},
                "text": "Hello",
            }
        }

        result = filter_google_chat_pii(webhook)

        # Empty string should still produce a hash
        expected_hash = hashlib.sha256("".encode("utf-8")).hexdigest()[:16]
        assert result["user_id"] == expected_hash
        assert len(result["user_id"]) == 16

    def test_filter_pii_empty_text(self) -> None:
        """Test behavior with empty string text (should preserve empty string)."""
        webhook = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "",
            }
        }

        result = filter_google_chat_pii(webhook)

        # Empty text should be preserved (validation happens in Pydantic models)
        assert result["content"] == ""
        assert len(result["user_id"]) == 16

    def test_filter_pii_case_sensitivity(self) -> None:
        """Test that email case affects hashing (SHA-256 is case-sensitive)."""
        webhook1 = {
            "message": {
                "sender": {"email": "User@Example.com"},
                "text": "Test",
            }
        }
        webhook2 = {
            "message": {
                "sender": {"email": "user@example.com"},
                "text": "Test",
            }
        }

        result1 = filter_google_chat_pii(webhook1)
        result2 = filter_google_chat_pii(webhook2)

        # Different case should produce different hashes
        # (This is expected SHA-256 behavior)
        assert result1["user_id"] != result2["user_id"]

    def test_filtered_message_type(self) -> None:
        """Test that FilteredMessage TypedDict has correct structure."""
        # This test ensures the TypedDict definition matches usage
        filtered: FilteredMessage = {
            "user_id": "a1b2c3d4e5f6g7h8",
            "content": "Test message",
        }

        assert filtered["user_id"] == "a1b2c3d4e5f6g7h8"
        assert filtered["content"] == "Test message"
