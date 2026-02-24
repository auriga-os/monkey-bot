"""Unit tests for FirestoreCheckpointSaver.

All Firestore I/O is mocked — no real GCP calls are made.
Tests verify serialization, Firestore document structure, and
the env-var wiring in build_deep_agent().
"""

import base64
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_checkpoint(checkpoint_id: str = "cp-001") -> dict:
    """Minimal valid LangGraph Checkpoint dict."""
    return {
        "v": 1,
        "id": checkpoint_id,
        "ts": "2026-02-24T19:00:00+00:00",
        "channel_values": {"messages": []},
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": None,
    }


def _make_config(
    thread_id: str = "john_at_ez-ai_dot_io",
    checkpoint_ns: str = "",
    checkpoint_id: str | None = None,
) -> dict:
    cfg: dict = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
        }
    }
    if checkpoint_id:
        cfg["configurable"]["checkpoint_id"] = checkpoint_id
    return cfg


def _make_saver(project_id: str = "aurigaos"):
    """Create a FirestoreCheckpointSaver with a mocked Firestore client."""
    from src.core.firestore_checkpointer import FirestoreCheckpointSaver
    saver = FirestoreCheckpointSaver(project_id=project_id)
    mock_db = MagicMock()
    saver._db = mock_db
    return saver, mock_db


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------

class TestSerialization:
    """Verify serde round-trips checkpoint data correctly."""

    def test_serde_round_trip(self):
        """Checkpoint survives dumps_typed → base64 → loads_typed."""
        from src.core.firestore_checkpointer import FirestoreCheckpointSaver
        saver = FirestoreCheckpointSaver.__new__(FirestoreCheckpointSaver)
        saver.__init__.__func__(saver, project_id="test") if False else None

        from src.core.firestore_checkpointer import FirestoreCheckpointSaver
        saver = FirestoreCheckpointSaver(project_id="test")
        saver._db = MagicMock()

        checkpoint = _make_checkpoint()
        type_, data = saver.serde.dumps_typed(checkpoint)
        encoded = base64.b64encode(data).decode()

        decoded = saver.serde.loads_typed((type_, base64.b64decode(encoded)))
        assert decoded["id"] == checkpoint["id"]
        assert decoded["v"] == checkpoint["v"]


# ---------------------------------------------------------------------------
# aput
# ---------------------------------------------------------------------------

class TestAPut:
    """Tests for aput() — storing checkpoints."""

    @pytest.mark.asyncio
    async def test_aput_calls_firestore_set(self):
        """aput stores a document under the checkpoints subcollection."""
        saver, mock_db = _make_saver()

        # Wire up the collection chain
        mock_col = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.set = AsyncMock()
        mock_col.document.return_value = mock_doc_ref

        mock_thread_doc = MagicMock()
        mock_thread_doc.collection.return_value = mock_col
        mock_db.collection.return_value.document.return_value = mock_thread_doc

        checkpoint = _make_checkpoint("cp-aput-01")
        config = _make_config(thread_id="john@ez-ai.io")
        metadata = {"step": 1, "source": "loop"}
        new_versions: dict = {}

        with patch("google.cloud.firestore_v1.SERVER_TIMESTAMP", "MOCK_TS"):
            result = await saver.aput(config, checkpoint, metadata, new_versions)

        mock_doc_ref.set.assert_awaited_once()
        stored = mock_doc_ref.set.call_args[0][0]
        assert stored["checkpoint_type"] is not None
        assert stored["checkpoint_data"] is not None
        assert stored["metadata"] == metadata
        assert "created_at" in stored

    @pytest.mark.asyncio
    async def test_aput_returns_runnable_config(self):
        """aput returns a RunnableConfig with thread_id and checkpoint_id."""
        saver, mock_db = _make_saver()

        mock_col = MagicMock()
        mock_doc_ref = MagicMock()
        mock_doc_ref.set = AsyncMock()
        mock_col.document.return_value = mock_doc_ref
        mock_thread_doc = MagicMock()
        mock_thread_doc.collection.return_value = mock_col
        mock_db.collection.return_value.document.return_value = mock_thread_doc

        checkpoint = _make_checkpoint("cp-return-01")
        config = _make_config(thread_id="alice@test.com")

        with patch("google.cloud.firestore_v1.SERVER_TIMESTAMP", "MOCK_TS"):
            result = await saver.aput(config, checkpoint, {}, {})

        assert result["configurable"]["thread_id"] == "alice@test.com"
        assert result["configurable"]["checkpoint_id"] == "cp-return-01"

    @pytest.mark.asyncio
    async def test_aput_sanitizes_thread_id_for_document_path(self):
        """Email addresses are sanitized to valid Firestore document IDs."""
        from src.core.firestore_checkpointer import _safe_thread_id

        safe = _safe_thread_id("john@ez-ai.io")
        assert "@" not in safe
        assert "." not in safe


# ---------------------------------------------------------------------------
# aget_tuple
# ---------------------------------------------------------------------------

class TestAGetTuple:
    """Tests for aget_tuple() — retrieving checkpoints."""

    @pytest.mark.asyncio
    async def test_aget_tuple_returns_none_for_missing_thread(self):
        """When no checkpoint exists, aget_tuple returns None."""
        saver, mock_db = _make_saver()

        mock_col = MagicMock()
        mock_col.where.return_value = mock_col
        mock_col.order_by.return_value = mock_col
        mock_col.limit.return_value = mock_col

        # stream() yields nothing
        async def empty_stream():
            return
            yield  # pragma: no cover

        mock_col.stream = empty_stream

        mock_thread_doc = MagicMock()
        mock_thread_doc.collection.return_value = mock_col
        mock_db.collection.return_value.document.return_value = mock_thread_doc

        config = _make_config(thread_id="nobody@test.com")
        result = await saver.aget_tuple(config)
        assert result is None

    @pytest.mark.asyncio
    async def test_aget_tuple_deserializes_checkpoint(self):
        """aget_tuple fetches and deserializes a specific checkpoint by ID."""
        saver, mock_db = _make_saver()

        checkpoint = _make_checkpoint("cp-get-01")
        type_, data = saver.serde.dumps_typed(checkpoint)

        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "cp-get-01"
        mock_doc.to_dict.return_value = {
            "checkpoint_ns": "",
            "checkpoint_type": type_,
            "checkpoint_data": base64.b64encode(data).decode(),
            "metadata": {"step": 0, "source": "input"},
            "new_versions": {},
            "parent_checkpoint_id": None,
        }

        mock_col = MagicMock()
        mock_col.document.return_value = MagicMock(get=AsyncMock(return_value=mock_doc))

        # writes subcollection returns empty
        mock_writes_col = MagicMock()
        mock_writes_col.where.return_value = mock_writes_col

        async def empty_stream():
            return
            yield  # pragma: no cover

        mock_writes_col.stream = empty_stream

        call_count = 0

        def col_side_effect(name):
            nonlocal call_count
            call_count += 1
            if name == "checkpoints":
                return mock_col
            return mock_writes_col

        mock_thread_doc = MagicMock()
        mock_thread_doc.collection.side_effect = col_side_effect
        mock_db.collection.return_value.document.return_value = mock_thread_doc

        config = _make_config(thread_id="john@ez-ai.io", checkpoint_id="cp-get-01")
        result = await saver.aget_tuple(config)

        assert result is not None
        assert result.checkpoint["id"] == "cp-get-01"
        assert result.metadata == {"step": 0, "source": "input"}
        assert result.config["configurable"]["checkpoint_id"] == "cp-get-01"

    @pytest.mark.asyncio
    async def test_aget_tuple_returns_none_for_missing_doc(self):
        """Returns None when the specific checkpoint_id document doesn't exist."""
        saver, mock_db = _make_saver()

        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_col = MagicMock()
        mock_col.document.return_value = MagicMock(get=AsyncMock(return_value=mock_doc))

        mock_thread_doc = MagicMock()
        mock_thread_doc.collection.return_value = mock_col
        mock_db.collection.return_value.document.return_value = mock_thread_doc

        config = _make_config(thread_id="john@ez-ai.io", checkpoint_id="cp-missing")
        result = await saver.aget_tuple(config)

        assert result is None


# ---------------------------------------------------------------------------
# alist
# ---------------------------------------------------------------------------

class TestAList:
    """Tests for alist() — listing checkpoints."""

    @pytest.mark.asyncio
    async def test_alist_yields_checkpoints_in_order(self):
        """alist yields CheckpointTuples for all documents from the query."""
        saver, mock_db = _make_saver()

        checkpoints = [_make_checkpoint(f"cp-{i:03d}") for i in range(3)]

        async def fake_stream():
            for cp in checkpoints:
                type_, data = saver.serde.dumps_typed(cp)
                doc = MagicMock()
                doc.id = cp["id"]
                doc.to_dict.return_value = {
                    "checkpoint_ns": "",
                    "checkpoint_type": type_,
                    "checkpoint_data": base64.b64encode(data).decode(),
                    "metadata": {"step": 0, "source": "loop"},
                    "parent_checkpoint_id": None,
                }
                yield doc

        mock_col = MagicMock()
        mock_col.where.return_value = mock_col
        mock_col.order_by.return_value = mock_col
        mock_col.stream = fake_stream

        mock_thread_doc = MagicMock()
        mock_thread_doc.collection.return_value = mock_col
        mock_db.collection.return_value.document.return_value = mock_thread_doc

        config = _make_config(thread_id="john@ez-ai.io")
        results = [t async for t in saver.alist(config)]

        assert len(results) == 3
        assert results[0].checkpoint["id"] == "cp-000"
        assert results[2].checkpoint["id"] == "cp-002"

    @pytest.mark.asyncio
    async def test_alist_returns_immediately_for_none_config(self):
        """alist yields nothing when config is None."""
        saver, _ = _make_saver()
        results = [t async for t in saver.alist(None)]
        assert results == []


# ---------------------------------------------------------------------------
# aput_writes
# ---------------------------------------------------------------------------

class TestAPutWrites:
    """Tests for aput_writes() — storing pending task writes."""

    @pytest.mark.asyncio
    async def test_aput_writes_stores_each_write(self):
        """aput_writes stores one Firestore doc per (channel, value) pair."""
        saver, mock_db = _make_saver()

        stored_docs: dict[str, dict] = {}

        async def mock_set(data):
            stored_docs[doc_id_holder[0]] = data

        doc_id_holder = [None]

        def mock_document(doc_id):
            doc_id_holder[0] = doc_id
            mock_ref = MagicMock()
            mock_ref.set = AsyncMock(side_effect=mock_set)
            return mock_ref

        mock_writes_col = MagicMock()
        mock_writes_col.document.side_effect = mock_document

        mock_thread_doc = MagicMock()
        mock_thread_doc.collection.return_value = mock_writes_col
        mock_db.collection.return_value.document.return_value = mock_thread_doc

        config = _make_config(thread_id="john@ez-ai.io", checkpoint_id="cp-writes-01")
        writes = [("messages", ["hello"]), ("output", {"text": "world"})]

        with patch("google.cloud.firestore_v1.SERVER_TIMESTAMP", "MOCK_TS"):
            await saver.aput_writes(config, writes, task_id="task-abc")

        assert mock_writes_col.document.call_count == 2
        # Verify doc IDs follow the {checkpoint_id}_{task_id}_{idx} pattern
        call_args = [c[0][0] for c in mock_writes_col.document.call_args_list]
        assert "cp-writes-01_task-abc_0" in call_args
        assert "cp-writes-01_task-abc_1" in call_args


# ---------------------------------------------------------------------------
# Sync stubs
# ---------------------------------------------------------------------------

class TestSyncStubs:
    """Sync methods raise NotImplementedError (async-only saver)."""

    def test_get_tuple_raises(self):
        saver, _ = _make_saver()
        with pytest.raises(NotImplementedError):
            saver.get_tuple(_make_config())

    def test_list_raises(self):
        saver, _ = _make_saver()
        with pytest.raises(NotImplementedError):
            list(saver.list(_make_config()))

    def test_put_raises(self):
        saver, _ = _make_saver()
        with pytest.raises(NotImplementedError):
            saver.put(_make_config(), _make_checkpoint(), {}, {})

    def test_put_writes_raises(self):
        saver, _ = _make_saver()
        with pytest.raises(NotImplementedError):
            saver.put_writes(_make_config(), [], "task-1")


# ---------------------------------------------------------------------------
# build_deep_agent integration
# ---------------------------------------------------------------------------

class TestBuildDeepAgentCheckpointerWiring:
    """Tests that build_deep_agent picks the right checkpointer from env vars."""

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    def test_uses_in_memory_saver_by_default(self, mock_create, monkeypatch):
        """No CHECKPOINT_BACKEND env var → InMemorySaver."""
        from langgraph.checkpoint.memory import InMemorySaver
        from src.core.deepagent import build_deep_agent

        monkeypatch.delenv("CHECKPOINT_BACKEND", raising=False)
        mock_create.return_value = Mock()

        build_deep_agent(model="gemini-2.5-flash")

        call_kwargs = mock_create.call_args.kwargs
        assert isinstance(call_kwargs["checkpointer"], InMemorySaver)

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    def test_uses_firestore_saver_when_env_set(self, mock_create, monkeypatch):
        """CHECKPOINT_BACKEND=firestore → FirestoreCheckpointSaver."""
        from src.core.firestore_checkpointer import FirestoreCheckpointSaver
        from src.core.deepagent import build_deep_agent

        monkeypatch.setenv("CHECKPOINT_BACKEND", "firestore")
        monkeypatch.setenv("GCP_PROJECT_ID", "aurigaos")

        mock_create.return_value = Mock()

        # Patch Firestore client init so no real GCP call is made
        with patch("google.cloud.firestore.AsyncClient"):
            build_deep_agent(model="gemini-2.5-flash")

        call_kwargs = mock_create.call_args.kwargs
        assert isinstance(call_kwargs["checkpointer"], FirestoreCheckpointSaver)

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    def test_raises_when_firestore_and_no_project_id(self, mock_create, monkeypatch):
        """CHECKPOINT_BACKEND=firestore without project_id raises ValueError."""
        from src.core.deepagent import build_deep_agent

        monkeypatch.setenv("CHECKPOINT_BACKEND", "firestore")
        monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
        monkeypatch.delenv("VERTEX_AI_PROJECT_ID", raising=False)

        mock_create.return_value = Mock()

        with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
            build_deep_agent(model="gemini-2.5-flash")

    @patch("src.core.deepagent._DEEPAGENTS_AVAILABLE", True)
    @patch("src.core.deepagent.create_deep_agent")
    def test_falls_back_to_memory_for_unknown_backend(self, mock_create, monkeypatch):
        """Unknown CHECKPOINT_BACKEND value falls through to InMemorySaver."""
        from langgraph.checkpoint.memory import InMemorySaver
        from src.core.deepagent import build_deep_agent

        monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")  # not implemented
        mock_create.return_value = Mock()

        build_deep_agent(model="gemini-2.5-flash")

        call_kwargs = mock_create.call_args.kwargs
        assert isinstance(call_kwargs["checkpointer"], InMemorySaver)
