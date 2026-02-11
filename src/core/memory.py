"""
File-based memory manager with optional GCS sync.

This module provides persistent memory storage using local files with
optional asynchronous backup to Google Cloud Storage.
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

from src.core.interfaces import MemoryManagerInterface, Message

logger = logging.getLogger(__name__)


class MemoryManager(MemoryManagerInterface):
    """
    File-based memory manager with optional GCS sync.
    
    Stores conversation history as daily markdown files and facts as JSON.
    Optionally syncs to GCS asynchronously (fire-and-forget, non-blocking).
    
    Directory structure:
        {memory_dir}/
            CONVERSATION_HISTORY/
                2026-02/
                    2026-02-11.md
                    2026-02-12.md
            KNOWLEDGE_BASE/
                facts.json
    
    Attributes:
        memory_dir: Local memory directory path
        gcs_enabled: Whether GCS sync is enabled
        gcs_bucket: GCS bucket name (if sync enabled)
        gcs_client: GCS client instance (if sync enabled)
    
    Example:
        >>> manager = MemoryManager(gcs_enabled=False)
        >>> await manager.write_conversation("user123", "user", "Hello", "trace1")
        >>> await manager.write_fact("user123", "name", "John")
        >>> fact = await manager.read_fact("user123", "name")
        >>> print(fact)  # "John"
    """
    
    def __init__(
        self,
        memory_dir: str = "./data/memory",
        gcs_enabled: bool = False,
        gcs_bucket: Optional[str] = None
    ):
        """
        Initialize memory manager.
        
        Args:
            memory_dir: Local memory directory (default: ./data/memory)
            gcs_enabled: Enable GCS sync (default: False)
            gcs_bucket: GCS bucket name (required if gcs_enabled=True)
        """
        self.memory_dir = Path(memory_dir)
        self.gcs_enabled = gcs_enabled
        self.gcs_bucket = gcs_bucket
        
        # Create directory structure
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "CONVERSATION_HISTORY").mkdir(exist_ok=True)
        (self.memory_dir / "KNOWLEDGE_BASE").mkdir(exist_ok=True)
        
        # Initialize GCS client if enabled
        if self.gcs_enabled:
            try:
                from google.cloud import storage
                self.gcs_client = storage.Client()
                logger.info("GCS sync enabled", extra={"component": "memory_manager"})
            except Exception as e:
                logger.warning(
                    f"Failed to initialize GCS client: {e}. Continuing with local only.",
                    extra={"component": "memory_manager"}
                )
                self.gcs_enabled = False
                self.gcs_client = None
        else:
            self.gcs_client = None
    
    async def write_conversation(
        self,
        user_id: str,
        role: str,
        content: str,
        trace_id: str
    ):
        """
        Write conversation message to daily file.
        
        Creates a markdown file for each day with timestamped messages.
        Optionally syncs to GCS asynchronously.
        
        Args:
            user_id: Hashed user identifier
            role: "user" or "assistant"
            content: Message content
            trace_id: Request trace ID
        """
        today = datetime.now().strftime("%Y-%m-%d")
        month_dir = self.memory_dir / "CONVERSATION_HISTORY" / today[:7]
        month_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = month_dir / f"{today}.md"
        
        # Format message
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"\n## {timestamp} - {role.capitalize()} (trace: {trace_id})\n{content}\n"
        
        # Append to file
        with open(file_path, "a") as f:
            f.write(message)
        
        logger.debug(
            f"Wrote conversation message",
            extra={
                "component": "memory_manager",
                "role": role,
                "trace_id": trace_id
            }
        )
        
        # Async GCS sync (fire-and-forget)
        if self.gcs_enabled:
            asyncio.create_task(self._sync_to_gcs(file_path))
    
    async def read_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Message]:
        """
        Read recent conversation history.
        
        For MVP: Returns empty list (basic implementation).
        Full parsing can be added later when needed.
        
        Args:
            user_id: Hashed user identifier
            limit: Max messages to return (default 10)
            
        Returns:
            List of recent messages (oldest first)
        """
        # MVP: Simple implementation - return empty list
        # Full implementation would parse markdown and return Message objects
        return []
    
    async def write_fact(self, user_id: str, key: str, value: str):
        """
        Write fact to knowledge base.
        
        Stores facts in a JSON file with timestamps.
        
        Args:
            user_id: Hashed user identifier
            key: Fact key (e.g., "preferred_language")
            value: Fact value (e.g., "Python")
        """
        facts_file = self.memory_dir / "KNOWLEDGE_BASE" / "facts.json"
        
        # Load existing facts
        if facts_file.exists():
            with open(facts_file) as f:
                facts = json.load(f)
        else:
            facts = {"version": "1.0", "facts": {}}
        
        # Add/update fact
        now = datetime.now().isoformat()
        if key in facts["facts"]:
            facts["facts"][key]["value"] = value
            facts["facts"][key]["updated_at"] = now
        else:
            facts["facts"][key] = {
                "value": value,
                "created_at": now,
                "updated_at": now
            }
        
        # Write back
        with open(facts_file, "w") as f:
            json.dump(facts, f, indent=2)
        
        logger.debug(
            f"Wrote fact: {key}",
            extra={"component": "memory_manager", "key": key}
        )
        
        # Async GCS sync
        if self.gcs_enabled:
            asyncio.create_task(self._sync_to_gcs(facts_file))
    
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        """
        Read fact from knowledge base.
        
        Args:
            user_id: Hashed user identifier
            key: Fact key
            
        Returns:
            Fact value or None if not found
        """
        facts_file = self.memory_dir / "KNOWLEDGE_BASE" / "facts.json"
        
        if not facts_file.exists():
            return None
        
        with open(facts_file) as f:
            facts = json.load(f)
        
        fact = facts.get("facts", {}).get(key)
        return fact["value"] if fact else None
    
    async def _sync_to_gcs(self, file_path: Path):
        """
        Async upload to GCS (fire-and-forget, non-blocking).
        
        Args:
            file_path: Local file to sync
        """
        if not self.gcs_enabled or not self.gcs_client:
            return
        
        try:
            blob_name = str(file_path.relative_to(self.memory_dir))
            bucket = self.gcs_client.bucket(self.gcs_bucket)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(file_path))
            
            logger.debug(
                f"Synced to GCS: {blob_name}",
                extra={"component": "memory_manager", "blob": blob_name}
            )
        except Exception as e:
            logger.error(
                f"GCS sync failed: {e}",
                extra={"component": "memory_manager", "file": str(file_path), "error": str(e)}
            )
    
    def cleanup_old_conversations(self, days: int = 90):
        """
        Delete conversation files older than N days.
        
        Args:
            days: Age threshold in days (default 90)
        """
        cutoff = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        conv_dir = self.memory_dir / "CONVERSATION_HISTORY"
        if not conv_dir.exists():
            return
        
        for month_dir in conv_dir.iterdir():
            if not month_dir.is_dir():
                continue
            
            for file_path in month_dir.iterdir():
                if not file_path.is_file():
                    continue
                
                try:
                    # Parse date from filename (YYYY-MM-DD.md)
                    date_str = file_path.stem  # Remove .md extension
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if file_date < cutoff:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(
                            f"Deleted old conversation file: {file_path.name}",
                            extra={"component": "memory_manager"}
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to process file {file_path}: {e}",
                        extra={"component": "memory_manager"}
                    )
        
        logger.info(
            f"Cleanup complete: deleted {deleted_count} files",
            extra={"component": "memory_manager", "deleted": deleted_count}
        )
