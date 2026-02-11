# 12 - Session & Context Management (Goose Pattern)

**Source:** Goose (Block/Square) - Open Source AI Agent  
**Implementation:** SQLite-based session storage with auto-compaction  
**Key Feature:** Smart token management to stay under context limits

---

## Overview

Goose manages conversation sessions through:
1. **SQLite Storage:** Session metadata and messages stored in `~/.local/share/goose/sessions/sessions.db`
2. **Session IDs:** Format `YYYYMMDD_<COUNT>` (e.g., `20260211_001`)
3. **Auto-Compaction:** Triggered at ~80% of token limit (configurable)
4. **Context Strategies:** Summarization, truncation, or prompt user to choose

**Key Insight:** Long-running sessions would exceed context limits without intervention. Goose automatically summarizes old messages using a cheap model, preserving recent context while staying under limits.

---

## Core Pattern

### SQLite Schema

```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                  -- YYYYMMDD_<count>
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    total_tokens INTEGER,
    message_count INTEGER,
    metadata JSON                         -- Flexible storage
);

-- Messages table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT,                            -- system, user, assistant, function
    content TEXT,
    tool_calls JSON,                      -- For assistant messages
    tokens INTEGER,
    timestamp TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Indices for performance
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_sessions_created ON sessions(created_at);
```

### Python Implementation for emonk

```python
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import os

@dataclass
class Session:
    """Session metadata"""
    id: str  # Format: YYYYMMDD_<count>
    created_at: datetime
    updated_at: datetime
    total_tokens: int
    message_count: int
    metadata: Dict[str, Any]

class SessionStore:
    """SQLite-based session storage (Goose pattern)"""
    
    def __init__(self, db_path: str = "~/.emonk/sessions.db"):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                total_tokens INTEGER,
                message_count INTEGER,
                metadata JSON
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                tool_calls JSON,
                tokens INTEGER,
                timestamp TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at)")
        conn.commit()
        conn.close()
    
    def create_session(self, metadata: Optional[Dict] = None) -> Session:
        """Create new session with YYYYMMDD_<count> ID"""
        today = datetime.now().strftime("%Y%m%d")
        
        conn = sqlite3.connect(self.db_path)
        # Find count for today
        cursor = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE id LIKE ?",
            (f"{today}_%",)
        )
        count = cursor.fetchone()[0] + 1
        session_id = f"{today}_{count:03d}"
        
        now = datetime.now()
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, now, now, 0, 0, json.dumps(metadata or {}))
        )
        conn.commit()
        conn.close()
        
        log.info("session_created", session_id=session_id)
        return Session(
            id=session_id,
            created_at=now,
            updated_at=now,
            total_tokens=0,
            message_count=0,
            metadata=metadata or {}
        )
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List] = None,
        tokens: int = 0
    ):
        """Add message to session"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO messages (session_id, role, content, tool_calls, tokens, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, role, content, json.dumps(tool_calls or []), tokens, datetime.now())
        )
        # Update session stats
        conn.execute(
            "UPDATE sessions SET updated_at = ?, total_tokens = total_tokens + ?, "
            "message_count = message_count + 1 WHERE id = ?",
            (datetime.now(), tokens, session_id)
        )
        conn.commit()
        conn.close()
    
    def get_messages(self, session_id: str) -> List[Dict]:
        """Retrieve all messages for session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT role, content, tool_calls, tokens, timestamp "
            "FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,)
        )
        messages = []
        for row in cursor.fetchall():
            msg = {
                "role": row[0],
                "content": row[1],
                "tokens": row[3],
                "timestamp": row[4]
            }
            if row[2]:
                msg["tool_calls"] = json.loads(row[2])
            messages.append(msg)
        conn.close()
        return messages
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT created_at, updated_at, total_tokens, message_count, metadata "
            "FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Session(
            id=session_id,
            created_at=datetime.fromisoformat(row[0]),
            updated_at=datetime.fromisoformat(row[1]),
            total_tokens=row[2],
            message_count=row[3],
            metadata=json.loads(row[4])
        )
    
    def list_sessions(self, limit: int = 10) -> List[Session]:
        """List recent sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, created_at, updated_at, total_tokens, message_count, metadata "
            "FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        sessions = []
        for row in cursor.fetchall():
            sessions.append(Session(
                id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                total_tokens=row[3],
                message_count=row[4],
                metadata=json.loads(row[5])
            ))
        conn.close()
        return sessions

class ContextManager:
    """
    Goose-style context management with auto-compaction.
    Keeps conversations under token limits via summarization.
    """
    
    def __init__(
        self,
        model_context_limit: int = 128000,
        compaction_threshold: float = 0.8,
        keep_recent_messages: int = 5,
        summary_model: str = "gemini-2.0-flash"
    ):
        self.context_limit = model_context_limit
        self.compaction_threshold = compaction_threshold
        self.keep_recent_messages = keep_recent_messages
        self.summary_model = summary_model
    
    async def manage_context(
        self,
        session_id: str,
        session_store: SessionStore,
        llm_client
    ) -> List[Dict]:
        """
        Auto-compact context if approaching token limit.
        Returns managed message list ready for LLM.
        """
        # Get all messages
        messages = session_store.get_messages(session_id)
        
        # Count tokens
        total_tokens = sum(m.get("tokens", 0) for m in messages)
        threshold_tokens = self.context_limit * self.compaction_threshold
        
        if total_tokens < threshold_tokens:
            log.info(
                "context_ok",
                session_id=session_id,
                tokens=total_tokens,
                limit=self.context_limit,
                usage_percent=round(total_tokens / self.context_limit * 100, 1)
            )
            return messages  # No action needed
        
        log.warning(
            "context_compaction_triggered",
            session_id=session_id,
            tokens=total_tokens,
            threshold=threshold_tokens,
            usage_percent=round(total_tokens / self.context_limit * 100, 1)
        )
        
        # Strategy: Keep system prompt + recent N messages + summarize middle
        system_msg = messages[0]  # First message is always system prompt
        recent_msgs = messages[-self.keep_recent_messages:]
        old_msgs = messages[1:-self.keep_recent_messages]
        
        if not old_msgs:
            # Can't compact further - use truncation
            log.warning(
                "context_truncation",
                session_id=session_id,
                reason="no_old_messages_to_summarize"
            )
            return [system_msg] + recent_msgs
        
        # Summarize old messages using cheap model
        summary = await self._summarize_history(old_msgs, llm_client)
        
        # Construct compacted context
        compacted = [
            system_msg,
            {
                "role": "system",
                "content": f"[Previous conversation summary]: {summary}",
                "timestamp": datetime.now().isoformat(),
                "tokens": self._estimate_tokens(summary)
            },
            *recent_msgs
        ]
        
        new_total = sum(m.get("tokens", 0) for m in compacted)
        log.info(
            "context_compacted",
            session_id=session_id,
            old_tokens=total_tokens,
            new_tokens=new_total,
            old_messages=len(messages),
            new_messages=len(compacted),
            savings_percent=round((total_tokens - new_total) / total_tokens * 100, 1)
        )
        
        return compacted
    
    async def _summarize_history(
        self,
        messages: List[Dict],
        llm_client
    ) -> str:
        """Summarize conversation history using cheap model"""
        history_text = "\n\n".join([
            f"{m['role'].upper()}: {m['content']}"
            for m in messages
            if m.get("content")  # Skip empty messages
        ])
        
        prompt = f"""Summarize this conversation history in 3-4 concise sentences.
Focus on:
- Key decisions made
- Actions taken
- Important context for continuing the conversation

Conversation:
{history_text}

Summary:"""
        
        response = await llm_client.generate_simple(
            prompt,
            model=self.summary_model,
            max_tokens=200
        )
        
        return response.text
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Rule of thumb: 1 token ≈ 4 characters for English
        # More accurate: use tiktoken library
        return len(text) // 4
    
    def configure_threshold(self, threshold: float):
        """
        Update compaction threshold.
        
        Args:
            threshold: 0.0 to 1.0 (0.8 = compact at 80% full)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        self.compaction_threshold = threshold
        log.info("compaction_threshold_updated", threshold=threshold)
```

---

## Pros

### ✅ Automatic Token Management
**Source:** Goose auto-compaction documentation

- **No Manual Intervention:** Agent automatically stays under context limits
- **Transparent to User:** Compaction happens behind the scenes
- **Cost Optimization:** Uses cheap model for summarization (Gemini Flash costs ~5% of Pro)

**Example Savings:**
```
Without compaction: Hit 128K limit at turn 15, must start new session (lose context)
With compaction: Compact at turn 12 (102K tokens), continue to turn 30+ (maintain context)

Compaction cost: 100K tokens → 500 token summary using Gemini Flash
Cost: ~$0.004 (vs $0.00 but losing all context)
```

### ✅ SQLite Reliability
**Source:** SQLite vs file-based storage analysis

- **ACID Transactions:** No data loss from crashes
- **Concurrent Access:** Multiple processes can read simultaneously
- **Query Performance:** Fast lookups by session ID, date ranges
- **Battle-Tested:** SQLite used in production by billions of devices

**Performance:**
- Insert message: ~0.5ms
- Get session messages: ~2-10ms (depends on message count)
- List recent sessions: ~5ms

### ✅ Structured Querying
**Source:** SQL vs JSON file advantages

```python
# Easy analytics queries
conn.execute("""
    SELECT DATE(created_at) as date, COUNT(*) as count
    FROM sessions
    WHERE created_at >= datetime('now', '-7 days')
    GROUP BY DATE(created_at)
""")
# Result: Daily session counts for last week

conn.execute("""
    SELECT session_id, SUM(tokens) as total
    FROM messages
    GROUP BY session_id
    ORDER BY total DESC
    LIMIT 10
""")
# Result: Top 10 sessions by token usage
```

### ✅ Flexible Metadata Storage
**Source:** JSON column advantages

- **Schema Evolution:** Add new fields without migrations
- **Custom Attributes:** Store session-specific data (user_id, tags, etc.)
- **Queryable:** SQLite JSON functions allow filtering

```python
# Store custom metadata
session_store.create_session(metadata={
    "user_id": "user_123",
    "channel": "telegram",
    "tags": ["competitor-analysis", "automated"],
    "cost_limit": 0.50
})

# Query by metadata (SQLite 3.38+)
conn.execute("""
    SELECT * FROM sessions
    WHERE json_extract(metadata, '$.user_id') = 'user_123'
""")
```

---

## Cons

### ❌ Summary Quality Loss
**Source:** Information compression research, Goose user feedback

- **Detail Loss:** Summaries drop specifics (names, numbers, URLs)
- **Context Drift:** Important nuances lost after multiple compressions
- **Hallucination Risk:** Summary model might invent details
- **Irreversible:** Can't recover original messages after compaction

**Example Problem:**
```
Original context (3 messages):
- User asks about competitor pricing for CompanyA, CompanyB, CompanyC
- Agent searches and finds: A=$99, B=$129, C=$89
- User asks: "What was CompanyB's price again?"

After compaction summary:
- "User researched competitor pricing and found various price points"

Result: Agent can't answer "What was CompanyB's price?" because detail was lost
```

**Mitigation:** Store full conversation in database, only summarize for LLM context.

### ❌ Summarization Latency
**Source:** LLM API benchmarks

- **Added Delay:** 2-5 seconds to generate summary (blocks agent loop)
- **Compaction Spike:** User sees longer wait time during compaction
- **Unpredictable:** Can't predict when compaction will trigger

**User Experience:**
```
Normal turn: 2-3 seconds
Turn with compaction: 6-8 seconds (includes 3-5s for summarization)

User perspective: "Why did this response take so long?"
```

**Mitigation:** Show compaction indicator ("Organizing conversation history...")

### ❌ SQLite Limitations
**Source:** Database scaling best practices

- **Single-Write Bottleneck:** Only one writer at a time (not an issue for single-agent systems)
- **File Locking:** Can't scale across multiple servers without shared filesystem
- **Backup Complexity:** Must backup entire .db file (can't backup individual sessions)
- **Cloud Storage Issues:** Google Cloud Storage, S3 don't support SQLite locking

**Goose's Approach:** SQLite works great for local agent. For cloud deployment, Goose recommends PostgreSQL.

### ❌ Token Estimation Accuracy
**Source:** Tokenization research

- **Model-Specific:** Different models tokenize differently (GPT-4 vs Gemini)
- **Estimation Errors:** Simple character count can be off by 20-30%
- **Language Variance:** Non-English text has different token ratios
- **Special Tokens:** Tool calls, JSON structures tokenize unpredictably

**Better Approach:** Use model-specific tokenizer library (tiktoken for OpenAI, sentencepiece for Gemini).

---

## When to Use This Approach

### ✅ Use Session + Context Management When:

1. **Long Conversations:** Sessions exceed 10+ turns regularly
2. **Large Context Windows:** Using models with 100K+ token limits
3. **Multi-Day Sessions:** User returns to same conversation over days
4. **Analytics Needed:** Want to query session history, track token usage
5. **Local Deployment:** Agent runs on single server/laptop

### ❌ Avoid This Approach When:

1. **Short Sessions:** All conversations < 10 turns (never hit context limit)
2. **Stateless Preferred:** Want each request independent (API-style)
3. **Multi-Server Deployment:** Need distributed session storage
4. **Critical Details:** Can't afford any information loss from summarization
5. **Ultra-Low Latency:** Can't tolerate compaction delays

---

## Alternative Approaches

### Alternative 1: File-Based Storage

```python
# sessions/20260211_001.jsonl
{"role": "system", "content": "...", "timestamp": "2026-02-11T10:00:00Z"}
{"role": "user", "content": "...", "timestamp": "2026-02-11T10:00:15Z"}
{"role": "assistant", "content": "...", "timestamp": "2026-02-11T10:00:22Z"}
```

**Pros:** Simple, human-readable, easy to version control  
**Cons:** No querying, slow at scale, race conditions

### Alternative 2: Redis/Cloud Storage

```python
# Redis
redis.lpush(f"session:{session_id}:messages", json.dumps(message))
redis.expire(f"session:{session_id}:messages", 86400 * 7)  # 7 day TTL
```

**Pros:** Fast, distributed, built-in TTL  
**Cons:** Higher cost, network latency, persistence complexity

### Alternative 3: Vector Database (Pinecone, Weaviate)

```python
# Store messages as vectors for semantic search
vectordb.upsert(
    id=message_id,
    values=embedding(message.content),
    metadata={"session_id": session_id, "role": message.role}
)

# Retrieve relevant past messages semantically
results = vectordb.query(current_message_embedding, top_k=5)
```

**Pros:** Semantic retrieval, relevant context only  
**Cons:** Complex, expensive, requires embedding model

---

## Implementation Roadmap for emonk

### Week 1: SQLite Session Store
```python
# Day 1-2: Schema design and SessionStore class
# Day 3: CRUD operations (create, add, get, list)
# Day 4-5: Unit tests and error handling
```

### Week 2: Context Manager
```python
# Day 1-2: Token counting and threshold detection
# Day 3: Summarization logic
# Day 4: Integration with agent loop
# Day 5: Testing compaction scenarios
```

### Week 3: Observability
```python
# Day 1-2: Logging for compaction events
# Day 3: Session analytics queries
# Day 4-5: Dashboard/CLI for session inspection
```

### Week 4: Optimization
```python
# Day 1-2: Use proper tokenizer (tiktoken)
# Day 3: Tune compaction thresholds
# Day 4-5: Performance benchmarking
```

---

## Configuration Examples

### Conservative (Preserve More Context)
```python
context_manager = ContextManager(
    model_context_limit=128000,
    compaction_threshold=0.9,        # Compact at 90% full
    keep_recent_messages=10,         # Keep last 10 messages
    summary_model="gemini-2.0-pro"   # Use better model for summaries
)
# Result: Less frequent compaction, higher quality summaries, higher cost
```

### Balanced (Goose Default)
```python
context_manager = ContextManager(
    model_context_limit=128000,
    compaction_threshold=0.8,        # Compact at 80% full
    keep_recent_messages=5,          # Keep last 5 messages
    summary_model="gemini-2.0-flash" # Use cheap model
)
# Result: Good balance of context preservation and cost
```

### Aggressive (Minimize Tokens)
```python
context_manager = ContextManager(
    model_context_limit=128000,
    compaction_threshold=0.7,        # Compact at 70% full
    keep_recent_messages=3,          # Keep last 3 messages
    summary_model="gemini-2.0-flash"
)
# Result: More frequent compaction, minimal context, lowest cost
```

---

## Comparison Matrix

| Dimension | SQLite + Auto-Compact | File-Based | Redis | Vector DB |
|-----------|----------------------|-----------|--------|-----------|
| **Querying** | ⭐⭐⭐⭐⭐ SQL | ❌ None | ⭐⭐ Limited | ⭐⭐⭐⭐ Semantic |
| **Performance** | ⭐⭐⭐⭐ Fast | ⭐⭐⭐ OK | ⭐⭐⭐⭐⭐ Very fast | ⭐⭐⭐ Network |
| **Scalability** | ⭐⭐⭐ Single server | ⭐⭐ Single server | ⭐⭐⭐⭐⭐ Distributed | ⭐⭐⭐⭐ Distributed |
| **Cost** | ⭐⭐⭐⭐⭐ Free | ⭐⭐⭐⭐⭐ Free | ⭐⭐ Hosting | ⭐ Expensive |
| **Complexity** | ⭐⭐⭐ Medium | ⭐⭐⭐⭐⭐ Simple | ⭐⭐⭐ Medium | ⭐⭐ Complex |
| **Context Management** | ✅ Auto-compact | ❌ Manual | ⚠️ TTL | ✅ Semantic |

---

## Resources

- **Goose Session Management:** https://block.github.io/goose/docs/guides/sessions/session-management/
- **Auto-Compaction:** https://block.github.io/goose/docs/guides/sessions/smart-context-management/
- **SQLite Documentation:** https://www.sqlite.org/docs.html
- **Token Counting (tiktoken):** https://github.com/openai/tiktoken
- **Context Window Research:** https://block.github.io/goose/blog/2025/08/18/understanding-context-windows/
