"""GCS-backed LangGraph Store for long-term memory.

Provides GCSStore that persists JSON documents to Google Cloud Storage
with support for keyword search via embeddings.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from google.cloud import storage
from langgraph.store.base import BaseStore, Item

logger = logging.getLogger(__name__)


class GCSStore(BaseStore):
    """Google Cloud Storage-backed Store for LangGraph long-term memory.
    
    Stores JSON documents in GCS with namespace-based organization:
        gs://bucket/{namespace[0]}/{namespace[1]}/.../{key}.json
    
    Supports:
        - put/get/delete operations
        - search with keyword matching on content
        - list operations within namespaces
        - embeddings-based semantic search (future)
    
    Example:
        >>> from google.cloud import storage
        >>> store = GCSStore(bucket_name="my-agent-memory")
        >>> 
        >>> # Store a session summary
        >>> store.put(
        ...     namespace=("user123", "session_summaries"),
        ...     key="thread-456",
        ...     value={"summary": "Discussed AI trends", "key_topics": ["ai", "ml"]}
        ... )
        >>> 
        >>> # Search by keyword
        >>> results = store.search(
        ...     namespace=("user123", "session_summaries"),
        ...     query="ai trends"
        ... )
    """
    
    def __init__(
        self,
        bucket_name: str,
        project_id: Optional[str] = None,
        index: Optional[dict] = None,
    ):
        """Initialize GCSStore.
        
        Args:
            bucket_name: GCS bucket name for storing documents
            project_id: GCP project ID (optional, uses default credentials)
            index: Optional index config for semantic search (future)
                   Format: {"embed": callable, "dims": int}
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.index_config = index
        
        # Initialize GCS client
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)
        
        logger.info(
            f"GCSStore initialized: bucket={bucket_name}, project={project_id}",
            extra={"component": "gcs_store"}
        )
    
    def _namespace_to_prefix(self, namespace: tuple) -> str:
        """Convert namespace tuple to GCS prefix.
        
        Args:
            namespace: Tuple of namespace components
        
        Returns:
            GCS prefix path
        
        Example:
            ("user123", "session_summaries") -> "user123/session_summaries/"
        """
        return "/".join(namespace) + "/"
    
    def _blob_name(self, namespace: tuple, key: str) -> str:
        """Generate GCS blob name from namespace and key.
        
        Args:
            namespace: Namespace tuple
            key: Item key
        
        Returns:
            Full blob name
        """
        prefix = self._namespace_to_prefix(namespace)
        return f"{prefix}{key}.json"
    
    def put(
        self,
        namespace: tuple,
        key: str,
        value: dict[str, Any],
    ) -> None:
        """Store a document in GCS.
        
        Args:
            namespace: Namespace tuple (e.g., (user_id, "session_summaries"))
            key: Document key (e.g., thread_id)
            value: Document value (must be JSON-serializable)
        """
        blob_name = self._blob_name(namespace, key)
        blob = self.bucket.blob(blob_name)
        
        # Serialize to JSON
        content = json.dumps(value, indent=2)
        
        # Upload to GCS
        blob.upload_from_string(
            content,
            content_type="application/json"
        )
        
        logger.info(
            f"Stored document: {blob_name}",
            extra={
                "component": "gcs_store",
                "namespace": namespace,
                "key": key,
            }
        )
    
    def get(
        self,
        namespace: tuple,
        key: str,
    ) -> Optional[Item]:
        """Retrieve a document from GCS.
        
        Args:
            namespace: Namespace tuple
            key: Document key
        
        Returns:
            Item with value dict, or None if not found
        """
        blob_name = self._blob_name(namespace, key)
        blob = self.bucket.blob(blob_name)
        
        if not blob.exists():
            logger.debug(
                f"Document not found: {blob_name}",
                extra={"component": "gcs_store"}
            )
            return None
        
        # Download and parse JSON
        content = blob.download_as_text()
        value = json.loads(content)
        
        logger.debug(
            f"Retrieved document: {blob_name}",
            extra={
                "component": "gcs_store",
                "namespace": namespace,
                "key": key,
            }
        )
        
        return Item(
            value=value,
            key=key,
            namespace=namespace,
            created_at=blob.time_created.isoformat() if blob.time_created else None,
            updated_at=blob.updated.isoformat() if blob.updated else None,
        )
    
    def delete(
        self,
        namespace: tuple,
        key: str,
    ) -> None:
        """Delete a document from GCS.
        
        Args:
            namespace: Namespace tuple
            key: Document key
        """
        blob_name = self._blob_name(namespace, key)
        blob = self.bucket.blob(blob_name)
        
        if blob.exists():
            blob.delete()
            logger.info(
                f"Deleted document: {blob_name}",
                extra={
                    "component": "gcs_store",
                    "namespace": namespace,
                    "key": key,
                }
            )
        else:
            logger.warning(
                f"Document not found for deletion: {blob_name}",
                extra={"component": "gcs_store"}
            )
    
    def list(
        self,
        namespace: tuple,
        limit: Optional[int] = None,
    ) -> list[Item]:
        """List all documents in a namespace.
        
        Args:
            namespace: Namespace tuple
            limit: Maximum number of items to return
        
        Returns:
            List of Items
        """
        prefix = self._namespace_to_prefix(namespace)
        blobs = self.client.list_blobs(
            self.bucket_name,
            prefix=prefix,
            max_results=limit,
        )
        
        items = []
        for blob in blobs:
            # Skip if not a JSON file
            if not blob.name.endswith(".json"):
                continue
            
            # Extract key from blob name
            key = blob.name[len(prefix):].replace(".json", "")
            
            # Download and parse
            try:
                content = blob.download_as_text()
                value = json.loads(content)
                
                items.append(Item(
                    value=value,
                    key=key,
                    namespace=namespace,
                    created_at=blob.time_created.isoformat() if blob.time_created else None,
                    updated_at=blob.updated.isoformat() if blob.updated else None,
                ))
            except Exception as e:
                logger.error(
                    f"Failed to parse blob {blob.name}: {e}",
                    extra={"component": "gcs_store"}
                )
        
        logger.info(
            f"Listed {len(items)} documents in namespace {namespace}",
            extra={"component": "gcs_store"}
        )
        
        return items
    
    def search(
        self,
        namespace: tuple,
        query: Optional[str] = None,
        filter: Optional[dict] = None,
        limit: int = 10,
    ) -> list[Item]:
        """Search documents by keyword or filter.
        
        Current implementation: Simple keyword matching on JSON content.
        Future: Add embeddings-based semantic search.
        
        Args:
            namespace: Namespace tuple to search within
            query: Optional search query (keywords)
            filter: Optional dict filter (key-value matching)
            limit: Maximum number of results
        
        Returns:
            List of matching Items, ranked by relevance
        """
        # List all documents in namespace
        all_items = self.list(namespace, limit=None)
        
        if not all_items:
            return []
        
        # Apply filters
        filtered = all_items
        
        # Filter by dict match
        if filter:
            filtered = [
                item for item in filtered
                if all(
                    item.value.get(k) == v
                    for k, v in filter.items()
                )
            ]
        
        # Filter by keyword search
        if query:
            query_lower = query.lower()
            scored = []
            
            for item in filtered:
                # Search in all text fields
                text = json.dumps(item.value).lower()
                
                # Simple relevance scoring: count keyword occurrences
                score = text.count(query_lower)
                
                # Boost score for matches in key_topics if present
                if "key_topics" in item.value:
                    topics = item.value["key_topics"]
                    if isinstance(topics, list):
                        for topic in topics:
                            if query_lower in str(topic).lower():
                                score += 10  # Boost for topic match
                
                if score > 0:
                    scored.append((score, item))
            
            # Sort by score descending
            scored.sort(reverse=True, key=lambda x: x[0])
            filtered = [item for score, item in scored]
        
        # Apply limit
        results = filtered[:limit]
        
        logger.info(
            f"Search results: {len(results)} of {len(all_items)} documents matched",
            extra={
                "component": "gcs_store",
                "namespace": namespace,
                "query": query,
                "filter": filter,
            }
        )
        
        return results


def create_search_memory_tool(store: GCSStore):
    """Create a LangChain tool for searching memory.
    
    This tool allows the agent to search past session summaries.
    
    Args:
        store: GCSStore instance
    
    Returns:
        LangChain tool function
    """
    from langchain_core.tools import tool
    
    @tool
    def search_memory(query: str, user_id: str = None) -> str:
        """Search past conversation summaries by keyword.
        
        Use this to recall information from previous conversations.
        
        Args:
            query: Keywords to search for
            user_id: Optional user ID to scope search
        
        Returns:
            Formatted search results
        """
        if not user_id:
            return "Error: user_id required for memory search"
        
        # Search in session_summaries namespace
        results = store.search(
            namespace=(user_id, "session_summaries"),
            query=query,
            limit=5,
        )
        
        if not results:
            return f"No relevant memories found for query: {query}"
        
        # Format results
        output = f"Found {len(results)} relevant memories:\n\n"
        for i, item in enumerate(results, 1):
            summary = item.value.get("summary", "No summary")
            topics = item.value.get("key_topics", [])
            timestamp = item.value.get("timestamp", "Unknown time")
            
            output += f"{i}. {summary}\n"
            output += f"   Topics: {', '.join(topics)}\n"
            output += f"   Time: {timestamp}\n\n"
        
        return output
    
    return search_memory
