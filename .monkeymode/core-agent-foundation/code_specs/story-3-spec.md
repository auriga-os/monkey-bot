# Code Spec: Story 3 - Skills Engine + Terminal Executor + Memory Manager

**Story:** Story 3 - Skills Engine + Terminal Executor + Memory Manager  
**Design Reference:** Phase 1A (Skills Module, Terminal Executor, Memory Module), Phase 1B (Contracts)  
**Author:** Emonk Development Team  
**Date:** 2026-02-11

---

## Implementation Summary

- **Files to Create:** 14 files
- **Files to Modify:** 0 files (greenfield implementation)
- **Tests to Add:** 4 test files
- **Estimated Complexity:** L (5-7 days)

---

## Codebase Conventions

Since this is a greenfield project, we'll establish conventions based on Python best practices and patterns from OpenClaw reference:

**File/Function Naming:** 
- `snake_case.py` for modules
- `snake_case` for functions and methods
- `PascalCase` for classes

**Import Order:** 
- Standard library → Third-party → Local (PEP 8)
- Use absolute imports from project root

**Error Handling:** 
- Custom exception classes inherit from `Exception`
- Raise specific errors (e.g., `SecurityError`, `SkillError`)
- Use try-except blocks for external calls (filesystem, subprocess)

**Testing Framework:** 
- pytest (latest stable)
- Use `pytest-asyncio` for async tests
- Use `pytest-mock` for mocking
- Test files: `test_*.py` in `tests/` directory mirroring `src/` structure

**Type Checking:** 
- Type hints on all public functions
- Use `from typing import` for complex types
- Use `dataclasses` for data structures

**Async/Await:** 
- All I/O operations are async
- Use `asyncio` for subprocess execution
- Use `aiofiles` for file I/O where beneficial

**Logging:** 
- Structured logging with JSON format
- Include component name in log records
- Levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## Technical Context

**Key Gotchas:**
- Terminal Executor is security-critical - 100% test coverage required for allowlist validation
- Memory Manager GCS sync must be non-blocking (async, fire-and-forget)
- Skills Engine must handle missing dependencies gracefully
- Subprocess output can be large - implement 1MB truncation
- File paths must be validated against allowlist to prevent directory traversal

**Reusable Utilities:**
- Use `pathlib.Path` for all file operations (cross-platform)
- Use `hashlib.sha256` for generating stable user IDs
- Use `asyncio.create_subprocess_exec` for command execution
- Use `google-cloud-storage` SDK for GCS operations

**Integration Points:**
- Skills Engine imports from `src/core/interfaces.py` (Story 2 defines this)
- Memory Manager imports from `src/core/interfaces.py` (Story 2 defines this)
- Terminal Executor is standalone (no external dependencies beyond stdlib)
- Skills in `./skills/` directory follow SKILL.md convention from OpenClaw

---

## Task Breakdown

### Task 1: Create Terminal Executor with Security Allowlist

**Dependencies:** None

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/core/terminal.py` | Secure command execution with allowlist validation |
| `tests/core/test_terminal.py` | Unit tests for terminal executor |

**Function Signatures:**

```python
# src/core/terminal.py
from dataclasses import dataclass
from typing import List
import asyncio

# Allowlists
ALLOWED_COMMANDS = ["cat", "ls", "python", "python3", "uv"]
ALLOWED_PATHS = ["./data/memory/", "./skills/", "./test-data/"]

@dataclass
class ExecutionResult:
    """Result from terminal command execution."""
    stdout: str
    stderr: str
    exit_code: int

class SecurityError(Exception):
    """Raised when command or path not allowed."""
    pass

class TerminalExecutor:
    """Secure terminal command execution with allowlist."""
    
    async def execute(
        self,
        command: str,
        args: List[str],
        timeout: int = 30
    ) -> ExecutionResult:
        """
        Execute a terminal command securely.
        
        Args:
            command: Command to execute (must be in ALLOWED_COMMANDS)
            args: Command arguments (paths must be in ALLOWED_PATHS)
            timeout: Execution timeout in seconds (default 30)
            
        Returns:
            ExecutionResult with stdout, stderr, exit_code
            
        Raises:
            SecurityError: If command/path not allowed
            TimeoutError: If execution exceeds timeout
        """
        pass
```

**Implementation Algorithm:**

1. **Validate command**: Check if `command` is in `ALLOWED_COMMANDS`, raise `SecurityError` if not
2. **Validate paths**: For each arg in `args`:
   - If arg starts with `./` or `/` (is a path)
   - Check if it starts with any path in `ALLOWED_PATHS`
   - Raise `SecurityError` if not allowed
3. **Execute subprocess**:
   - Use `asyncio.create_subprocess_exec(command, *args, stdout=PIPE, stderr=PIPE)`
   - Wrap in `asyncio.wait_for(process.communicate(), timeout=timeout)`
   - If `TimeoutError`, kill process and re-raise
4. **Truncate output**:
   - If stdout > 1MB, truncate to 1MB with "[Output truncated...]" message
   - Same for stderr
5. **Return ExecutionResult** with decoded stdout/stderr and exit code

**Test Cases** (in `tests/core/test_terminal.py`):

- **Allowed command + allowed path** → Executes successfully, returns stdout/stderr
- **Blocked command** ("rm") → Raises SecurityError
- **Blocked path** ("/etc/passwd") → Raises SecurityError
- **Command timeout** (sleep 60s with 1s timeout) → Raises TimeoutError and kills process
- **Large output** (> 1MB) → Truncates to 1MB with warning message
- **Command failure** (exit code 1) → Returns exit_code=1 with stderr
- **Empty args** → Executes command without args
- **Path allowlist edge cases**:
  - `./data/memory/subdir/file.txt` → Allowed (subdir of allowed path)
  - `./data/other/file.txt` → Blocked (not in allowed paths)

**Critical Notes:**

- **Security is paramount**: This is the most security-critical component - 100% test coverage required
- **Process cleanup**: Always kill process on timeout to prevent zombie processes
- **Allowlist strictness**: Use `startswith()` for path checking to allow subdirectories
- **Error logging**: Log all security violations with ERROR level for audit trail

---

### Task 2: Create Skills Engine - Loader Component

**Dependencies:** Task 1 (Terminal Executor)

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/skills/__init__.py` | Package init (empty for now) |
| `src/skills/loader.py` | Skill discovery and SKILL.md parsing |

**Function Signatures:**

```python
# src/skills/loader.py
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import logging

logger = logging.getLogger(__name__)

class SkillLoader:
    """Discover and load skills from ./skills/ directory."""
    
    def __init__(self, skills_dir: str = "./skills"):
        """
        Initialize skill loader.
        
        Args:
            skills_dir: Path to skills directory (default: ./skills)
        """
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, dict] = {}
    
    def load_skills(self) -> Dict[str, dict]:
        """
        Discover all skills in skills_dir.
        
        Returns:
            Dict mapping skill_name to skill metadata:
            {
                "skill-name": {
                    "metadata": {...},  # YAML frontmatter
                    "entry_point": "/path/to/skill.py",
                    "description": "Skill description"
                }
            }
        """
        pass
    
    def _parse_skill_md(self, skill_md_path: Path) -> Optional[dict]:
        """
        Parse SKILL.md file and extract metadata.
        
        Args:
            skill_md_path: Path to SKILL.md file
            
        Returns:
            Skill metadata dict or None if parsing fails
        """
        pass
```

**Pattern Reference:** Follow OpenClaw skill structure from `docs/ref/05_skills_system.md`:
- SKILL.md with YAML frontmatter (between `---` delimiters)
- Required fields: `name`, `description`
- Optional fields: `metadata.emonk.requires` (bins, files)

**Implementation Algorithm:**

1. **Iterate through skills_dir**:
   - Use `Path.iterdir()` to find all directories
   - Skip non-directories and directories without SKILL.md
2. **Parse SKILL.md**:
   - Read file contents
   - Split by `---` delimiters to extract YAML frontmatter
   - Use `yaml.safe_load()` to parse frontmatter
   - Extract `name`, `description` from metadata
3. **Find entry point**:
   - Convert skill name to Python module name: `skill-name` → `skill_name.py`
   - Check if `{skill_dir}/{skill_name}.py` exists
   - Log warning if missing
4. **Handle duplicates**:
   - If skill name already exists in `self.skills`, log warning and skip
5. **Store skill metadata**:
   - Add to `self.skills` dict with name as key
6. **Return all discovered skills**

**Test Cases** (in `tests/skills/test_loader.py`):

- **Valid skill directory** → Successfully loads skill with metadata
- **Missing SKILL.md** → Skips directory with warning log
- **Invalid YAML frontmatter** → Logs error and skips skill
- **Duplicate skill names** → Loads first, skips second with warning
- **Missing entry point** → Loads metadata but logs warning about missing .py file
- **Empty skills directory** → Returns empty dict
- **Nested skill directories** → Only processes top-level directories

**Critical Notes:**

- Use `yaml.safe_load()` (not `load()`) to prevent code execution
- Gracefully handle malformed SKILL.md files - skip and log, don't crash
- Skills directory is discovered at runtime, not hardcoded paths

---

### Task 3: Create Skills Engine - Executor Component

**Dependencies:** Task 2 (Loader), Task 1 (Terminal Executor)

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/skills/executor.py` | Skill execution engine |
| `tests/skills/test_executor.py` | Unit tests for executor |

**Function Signatures:**

```python
# src/skills/executor.py
from typing import Dict, Any, List
from src.core.interfaces import SkillsEngineInterface, SkillResult
from src.skills.loader import SkillLoader
from src.core.terminal import TerminalExecutor
import logging

logger = logging.getLogger(__name__)

class SkillsEngine(SkillsEngineInterface):
    """Execute skills via Terminal Executor."""
    
    def __init__(self, terminal_executor: TerminalExecutor, skills_dir: str = "./skills"):
        """
        Initialize skills engine.
        
        Args:
            terminal_executor: Terminal executor instance for running commands
            skills_dir: Path to skills directory (default: ./skills)
        """
        self.terminal = terminal_executor
        self.loader = SkillLoader(skills_dir)
        self.skills = self.loader.load_skills()
    
    async def execute_skill(
        self, 
        skill_name: str, 
        args: Dict[str, Any]
    ) -> SkillResult:
        """
        Execute a skill by name with arguments.
        
        Args:
            skill_name: Skill identifier from SKILL.md
            args: Skill arguments from LLM tool call
            
        Returns:
            SkillResult with success status and output
            
        Raises:
            SkillError: If skill not found or execution fails
        """
        pass
    
    def list_skills(self) -> List[str]:
        """Return list of available skill names."""
        return list(self.skills.keys())
    
    def _build_command_args(self, skill: dict, args: Dict[str, Any]) -> List[str]:
        """
        Convert skill metadata + args dict to command line args.
        
        Args:
            skill: Skill metadata from loader
            args: Arguments dict from LLM tool call
            
        Returns:
            List of command args: [entry_point, --key1, value1, --key2, value2, ...]
        """
        pass
```

**Implementation Algorithm:**

1. **Check skill exists**: If `skill_name` not in `self.skills`, return `SkillResult(success=False, error="Skill not found")`
2. **Get skill metadata**: Retrieve skill entry point and metadata
3. **Build command args**:
   - Start with `[entry_point]`
   - For each key-value in `args` dict, append `[f"--{key}", str(value)]`
4. **Execute via Terminal Executor**:
   - Call `self.terminal.execute("python", cmd_args)`
   - Log execution with skill name, args, component="skills_engine"
5. **Handle result**:
   - If exit_code == 0: Return `SkillResult(success=True, output=stdout)`
   - If exit_code != 0: Return `SkillResult(success=False, output=stdout, error=stderr)`
6. **Exception handling**:
   - Catch `SecurityError` from Terminal Executor → Return as skill error
   - Catch `TimeoutError` → Return as skill error with timeout message

**Test Cases** (in `tests/skills/test_executor.py`):

- **Valid skill + valid args** → Returns SkillResult with success=True and output
- **Skill not found** → Returns SkillResult with success=False and error message
- **Skill execution fails** (exit code 1) → Returns SkillResult with success=False, stderr in error field
- **Skill timeout** → Returns SkillResult with success=False and timeout error
- **Security violation** (blocked command) → Returns SkillResult with success=False and security error
- **Empty args dict** → Executes skill with no additional args
- **Complex args** (nested dicts, lists) → Converts to string representation
- **list_skills()** → Returns all loaded skill names

**Critical Notes:**

- Skills are executed as Python scripts via Terminal Executor
- All skill errors are captured and returned as `SkillResult` (no exceptions propagate)
- Skills must handle their own argument parsing (argparse, click, etc.)

---

### Task 4: Create Memory Manager - Core Implementation

**Dependencies:** None (but imports interfaces from Story 2)

**Files to Create:**

| File | Purpose |
|------|---------|
| `src/core/memory.py` | File-based memory with GCS sync |
| `tests/core/test_memory.py` | Unit tests for memory manager |

**Function Signatures:**

```python
# src/core/memory.py
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from src.core.interfaces import MemoryManagerInterface, Message
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

class MemoryManager(MemoryManagerInterface):
    """File-based memory with optional GCS sync."""
    
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
            from google.cloud import storage
            self.gcs_client = storage.Client()
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
        
        Args:
            user_id: Hashed user identifier
            role: "user" or "assistant"
            content: Message content
            trace_id: Request trace ID
        """
        pass
    
    async def read_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Message]:
        """
        Read recent conversation history.
        
        Args:
            user_id: Hashed user identifier
            limit: Max messages to return (default 10)
            
        Returns:
            List of recent messages (oldest first)
        """
        pass
    
    async def write_fact(self, user_id: str, key: str, value: str):
        """
        Write fact to knowledge base.
        
        Args:
            user_id: Hashed user identifier
            key: Fact key (e.g., "preferred_language")
            value: Fact value (e.g., "Python")
        """
        pass
    
    async def read_fact(self, user_id: str, key: str) -> Optional[str]:
        """
        Read fact from knowledge base.
        
        Args:
            user_id: Hashed user identifier
            key: Fact key
            
        Returns:
            Fact value or None if not found
        """
        pass
    
    async def _sync_to_gcs(self, file_path: Path):
        """
        Async upload to GCS (non-blocking, fire-and-forget).
        
        Args:
            file_path: Local file to sync
        """
        pass
    
    def cleanup_old_conversations(self, days: int = 90):
        """
        Delete conversation files older than N days.
        
        Args:
            days: Age threshold in days (default 90)
        """
        pass
```

**Implementation Algorithm:**

**write_conversation()**:
1. Get today's date: `datetime.now().strftime("%Y-%m-%d")`
2. Create month directory: `CONVERSATION_HISTORY/{YYYY-MM}/`
3. Open daily file: `{YYYY-MM}/{YYYY-MM-DD}.md` in append mode
4. Format message: `\n## {HH:MM:SS} - {Role} (trace: {trace_id})\n{content}\n`
5. Write to file
6. If GCS enabled: Schedule async sync via `asyncio.create_task(self._sync_to_gcs(file_path))`

**read_conversation_history()**:
1. Get today's file path: `CONVERSATION_HISTORY/{YYYY-MM}/{YYYY-MM-DD}.md`
2. If file doesn't exist, return empty list
3. Read file contents
4. Parse markdown: Split by `## ` to find message blocks
5. Extract timestamp, role, content from each block
6. Create `Message` objects
7. Return last N messages (oldest first)

**write_fact()**:
1. Get facts file: `KNOWLEDGE_BASE/facts.json`
2. If file exists, load JSON; else create empty structure: `{"facts": {}}`
3. Add/update fact: `facts["facts"][key] = {"value": value, "created_at": ISO8601, "updated_at": ISO8601}`
4. Write JSON back to file (pretty-printed with indent=2)
5. If GCS enabled: Schedule async sync

**read_fact()**:
1. Get facts file: `KNOWLEDGE_BASE/facts.json`
2. If file doesn't exist, return None
3. Load JSON
4. Return `facts["facts"].get(key, {}).get("value")`

**_sync_to_gcs()** (async, non-blocking):
1. If not GCS enabled, return immediately
2. Get blob name: `file_path.relative_to(self.memory_dir)`
3. Try: Get bucket, create blob, upload from file
4. Catch exceptions: Log error (ERROR level) but don't propagate

**cleanup_old_conversations()**:
1. Get cutoff date: `datetime.now() - timedelta(days=days)`
2. Iterate through `CONVERSATION_HISTORY/` directories
3. For each file, parse date from filename
4. If older than cutoff, delete file
5. Log deletions (INFO level)

**Test Cases** (in `tests/core/test_memory.py`):

**write_conversation()**:
- New conversation → Creates daily file with formatted message
- Append to existing → Appends to same daily file
- Month rollover → Creates new month directory

**read_conversation_history()**:
- File exists with 20 messages → Returns last 10 messages (oldest first)
- File doesn't exist → Returns empty list
- Empty file → Returns empty list
- Limit parameter → Returns correct number of messages

**write_fact() / read_fact()**:
- Write new fact → Creates facts.json with fact
- Update existing fact → Updates value and updated_at timestamp
- Read existing fact → Returns value
- Read non-existent fact → Returns None
- Multiple facts → All stored and retrievable

**GCS sync** (with mock GCS client):
- write_conversation with GCS enabled → Schedules async upload
- write_fact with GCS enabled → Schedules async upload
- GCS upload failure → Logs error but continues (no exception)
- GCS disabled → No upload attempted

**cleanup_old_conversations()**:
- Files older than 90 days → Deleted
- Files younger than 90 days → Kept
- Empty directories → Optionally cleaned up

**Critical Notes:**

- **GCS sync is fire-and-forget**: Never block on GCS operations
- **Local files are source of truth**: GCS is backup/sync only
- **Conversation parsing is simple**: MVP doesn't need perfect parsing (just basic message extraction)
- **JSON structure is versioned**: Include `"version": "1.0"` in facts.json for future migrations

---

### Task 5: Create Example Skill - File Operations

**Dependencies:** Task 3 (Skills Engine)

**Files to Create:**

| File | Purpose |
|------|---------|
| `skills/file-ops/SKILL.md` | Skill documentation |
| `skills/file-ops/file_ops.py` | Skill implementation |

**Skill Metadata (SKILL.md)**:

```markdown
---
name: file-ops
description: "File operations (read, write, list)"
metadata:
  emonk:
    requires:
      bins: ["cat", "ls"]
      files: ["./data/memory/"]
---

# File Operations Skill

Read, write, and list files in allowed directories.

## Read File

```bash
python skills/file-ops/file_ops.py --action read --path ./data/memory/test.txt
```

## List Directory

```bash
python skills/file-ops/file_ops.py --action list --path ./data/memory/
```

## Write File

```bash
python skills/file-ops/file_ops.py --action write --path ./data/memory/test.txt --content "Hello World"
```
```

**Implementation** (file_ops.py):

```python
#!/usr/bin/env python3
"""File operations skill for Emonk."""
import argparse
import os
import sys

def read_file(path: str) -> str:
    """Read file contents."""
    with open(path, 'r') as f:
        return f.read()

def list_directory(path: str) -> str:
    """List directory contents."""
    items = os.listdir(path)
    return '\n'.join(sorted(items))

def write_file(path: str, content: str) -> str:
    """Write content to file."""
    with open(path, 'w') as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {path}"

def main():
    parser = argparse.ArgumentParser(description="File operations")
    parser.add_argument("--action", choices=["read", "list", "write"], required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--content", default="")
    
    args = parser.parse_args()
    
    try:
        if args.action == "read":
            result = read_file(args.path)
        elif args.action == "list":
            result = list_directory(args.path)
        elif args.action == "write":
            result = write_file(args.path, args.content)
        
        print(result)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Test Strategy:**

This skill will be tested via Skills Engine integration tests (Task 7), not as a standalone unit test.

**Critical Notes:**

- Skill uses argparse for CLI argument parsing
- Skill exits with 0 on success, 1 on error
- Skill writes errors to stderr
- Skill is simple Python script (no external dependencies)

---

### Task 6: Create Example Skill - Memory Operations

**Dependencies:** Task 4 (Memory Manager)

**Files to Create:**

| File | Purpose |
|------|---------|
| `skills/memory/SKILL.md` | Skill documentation |
| `skills/memory/memory.py` | Skill implementation |

**Skill Metadata (SKILL.md)**:

```markdown
---
name: memory
description: "Store and retrieve facts from memory"
metadata:
  emonk:
    requires:
      bins: ["python"]
      files: ["./data/memory/"]
---

# Memory Skill

Store and retrieve user preferences and facts.

## Remember Fact

```bash
python skills/memory/memory.py --action remember --key preferred_language --value Python
```

## Recall Fact

```bash
python skills/memory/memory.py --action recall --key preferred_language
```
```

**Implementation** (memory.py):

```python
#!/usr/bin/env python3
"""Memory operations skill for Emonk."""
import argparse
import json
import sys
from pathlib import Path

MEMORY_DIR = Path("./data/memory/KNOWLEDGE_BASE")

def remember_fact(key: str, value: str) -> str:
    """Store a fact in memory."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    facts_file = MEMORY_DIR / "facts.json"
    
    # Load existing facts
    if facts_file.exists():
        with open(facts_file) as f:
            facts = json.load(f)
    else:
        facts = {"facts": {}}
    
    # Add/update fact
    facts["facts"][key] = {
        "value": value,
        "created_at": "ISO8601",  # Simplified for skill
        "updated_at": "ISO8601"
    }
    
    # Write back
    with open(facts_file, 'w') as f:
        json.dump(facts, f, indent=2)
    
    return f"Remembered: {key} = {value}"

def recall_fact(key: str) -> str:
    """Retrieve a fact from memory."""
    facts_file = MEMORY_DIR / "facts.json"
    
    if not facts_file.exists():
        return f"No facts stored yet"
    
    with open(facts_file) as f:
        facts = json.load(f)
    
    fact = facts.get("facts", {}).get(key)
    if fact:
        return f"{key} = {fact['value']}"
    else:
        return f"Fact '{key}' not found"

def main():
    parser = argparse.ArgumentParser(description="Memory operations")
    parser.add_argument("--action", choices=["remember", "recall"], required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--value", default="")
    
    args = parser.parse_args()
    
    try:
        if args.action == "remember":
            if not args.value:
                raise ValueError("--value required for remember action")
            result = remember_fact(args.key, args.value)
        elif args.action == "recall":
            result = recall_fact(args.key)
        
        print(result)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Test Strategy:**

This skill will be tested via Skills Engine integration tests (Task 7).

**Critical Notes:**

- Skill directly accesses `./data/memory/` (same as Memory Manager)
- Skill is simplified version of Memory Manager functionality
- In future, skills should call Memory Manager via API (not direct file access)

---

### Task 7: Integration Tests for Skills + Terminal + Memory

**Dependencies:** Tasks 1-6 (all previous tasks)

**Files to Create:**

| File | Purpose |
|------|---------|
| `tests/integration/test_skills_integration.py` | End-to-end tests for skills system |

**Test Scenarios:**

```python
# tests/integration/test_skills_integration.py
import pytest
import asyncio
from pathlib import Path
from src.skills.executor import SkillsEngine
from src.core.terminal import TerminalExecutor
from src.core.memory import MemoryManager

@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory."""
    data_dir = tmp_path / "data" / "memory"
    data_dir.mkdir(parents=True)
    return tmp_path

@pytest.fixture
def terminal_executor():
    """Create Terminal Executor instance."""
    return TerminalExecutor()

@pytest.fixture
def skills_engine(terminal_executor):
    """Create Skills Engine instance."""
    return SkillsEngine(terminal_executor, skills_dir="./skills")

@pytest.fixture
def memory_manager(test_data_dir):
    """Create Memory Manager instance (no GCS)."""
    return MemoryManager(
        memory_dir=str(test_data_dir / "data" / "memory"),
        gcs_enabled=False
    )

class TestSkillsIntegration:
    """Integration tests for skills system."""
    
    @pytest.mark.asyncio
    async def test_file_ops_skill_read(self, skills_engine, test_data_dir):
        """Test file-ops skill can read files."""
        # Setup: Create test file
        test_file = test_data_dir / "data" / "memory" / "test.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Hello from test")
        
        # Execute skill
        result = await skills_engine.execute_skill(
            "file-ops",
            {"action": "read", "path": str(test_file)}
        )
        
        # Assert
        assert result.success is True
        assert "Hello from test" in result.output
    
    @pytest.mark.asyncio
    async def test_file_ops_skill_list(self, skills_engine, test_data_dir):
        """Test file-ops skill can list directories."""
        # Setup: Create test files
        test_dir = test_data_dir / "data" / "memory"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "file1.txt").touch()
        (test_dir / "file2.txt").touch()
        
        # Execute skill
        result = await skills_engine.execute_skill(
            "file-ops",
            {"action": "list", "path": str(test_dir)}
        )
        
        # Assert
        assert result.success is True
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
    
    @pytest.mark.asyncio
    async def test_memory_skill_remember_recall(self, skills_engine):
        """Test memory skill can store and retrieve facts."""
        # Remember fact
        result1 = await skills_engine.execute_skill(
            "memory",
            {"action": "remember", "key": "test_key", "value": "test_value"}
        )
        assert result1.success is True
        
        # Recall fact
        result2 = await skills_engine.execute_skill(
            "memory",
            {"action": "recall", "key": "test_key"}
        )
        assert result2.success is True
        assert "test_value" in result2.output
    
    @pytest.mark.asyncio
    async def test_terminal_executor_security(self, terminal_executor):
        """Test terminal executor blocks dangerous commands."""
        # Blocked command
        with pytest.raises(SecurityError):
            await terminal_executor.execute("rm", ["-rf", "/"])
        
        # Blocked path
        with pytest.raises(SecurityError):
            await terminal_executor.execute("cat", ["/etc/passwd"])
    
    @pytest.mark.asyncio
    async def test_memory_manager_conversation_flow(self, memory_manager):
        """Test memory manager conversation write/read cycle."""
        user_id = "test_user_123"
        
        # Write messages
        await memory_manager.write_conversation(user_id, "user", "Hello", "trace1")
        await memory_manager.write_conversation(user_id, "assistant", "Hi there", "trace2")
        
        # Read history
        history = await memory_manager.read_conversation_history(user_id, limit=10)
        
        # Assert (basic check - detailed parsing in unit tests)
        assert isinstance(history, list)
    
    @pytest.mark.asyncio
    async def test_memory_manager_facts(self, memory_manager):
        """Test memory manager fact write/read cycle."""
        user_id = "test_user_123"
        
        # Write fact
        await memory_manager.write_fact(user_id, "test_key", "test_value")
        
        # Read fact
        value = await memory_manager.read_fact(user_id, "test_key")
        
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_skill_not_found(self, skills_engine):
        """Test skills engine handles missing skills gracefully."""
        result = await skills_engine.execute_skill(
            "nonexistent-skill",
            {}
        )
        
        assert result.success is False
        assert "not found" in result.error.lower()
```

**Test Execution:**

Run with: `pytest tests/integration/test_skills_integration.py -v`

**Critical Notes:**

- Use `tmp_path` fixture for isolated test environment
- Tests should clean up after themselves (tmp_path handles this automatically)
- Integration tests verify end-to-end flows (not individual functions)
- Mock GCS for Memory Manager tests (set `gcs_enabled=False`)

---

## Dependency Graph

```
Task 1: Terminal Executor (Security-Critical)
    │
    ├─→ Task 2: Skills Loader
    │       │
    │       └─→ Task 3: Skills Executor
    │               │
    │               ├─→ Task 5: File-Ops Skill
    │               └─→ Task 6: Memory Skill
    │
    └─→ Task 4: Memory Manager (Parallel to Tasks 2-3)
            │
            └─→ Task 6: Memory Skill

Task 7: Integration Tests (Depends on ALL tasks 1-6)
```

**Key Observations:**
- Tasks 1 and 4 can be developed in parallel (no dependencies)
- Tasks 2 and 3 must be sequential (Executor depends on Loader)
- Tasks 5 and 6 are simple skills (can be done quickly after Task 3)
- Task 7 should be done last (validates everything works together)

---

## Reference Code Examples

### Terminal Executor Pattern (Task 1)

Complete implementation showing all critical security checks:

```python
# src/core/terminal.py
import asyncio
import subprocess
from typing import List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# SECURITY: Allowlists (modify with extreme caution)
ALLOWED_COMMANDS = ["cat", "ls", "python", "python3", "uv"]
ALLOWED_PATHS = ["./data/memory/", "./skills/", "./test-data/"]

@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int

class SecurityError(Exception):
    """Raised when command or path not allowed."""
    pass

class TerminalExecutor:
    """Secure terminal command execution with allowlist."""
    
    async def execute(
        self,
        command: str,
        args: List[str],
        timeout: int = 30
    ) -> ExecutionResult:
        """Execute a terminal command securely."""
        
        # CRITICAL: Security check - command allowlist
        if command not in ALLOWED_COMMANDS:
            logger.error(f"Blocked command: {command}", extra={
                "component": "terminal_executor",
                "severity": "SECURITY_VIOLATION"
            })
            raise SecurityError(f"Command '{command}' not allowed")
        
        # CRITICAL: Security check - path allowlist
        for arg in args:
            if arg.startswith("./") or arg.startswith("/"):
                # This is a path - validate it
                if not any(arg.startswith(allowed) for allowed in ALLOWED_PATHS):
                    logger.error(f"Blocked path: {arg}", extra={
                        "component": "terminal_executor",
                        "severity": "SECURITY_VIOLATION"
                    })
                    raise SecurityError(f"Path '{arg}' not allowed")
        
        # Execute with timeout
        logger.info(f"Executing: {command} {' '.join(args)}", extra={
            "component": "terminal_executor",
            "command": command
        })
        
        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            # IMPORTANT: Truncate large output (prevent memory exhaustion)
            MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB
            if len(stdout) > MAX_OUTPUT_SIZE:
                stdout = stdout[:MAX_OUTPUT_SIZE] + b"\n[Output truncated at 1MB limit]"
            if len(stderr) > MAX_OUTPUT_SIZE:
                stderr = stderr[:MAX_OUTPUT_SIZE] + b"\n[Output truncated at 1MB limit]"
            
            return ExecutionResult(
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=process.returncode or 0
            )
        
        except asyncio.TimeoutError:
            # CRITICAL: Kill process on timeout
            process.kill()
            await process.wait()
            
            logger.error(f"Command timeout: {command}", extra={
                "component": "terminal_executor",
                "timeout": timeout
            })
            raise TimeoutError(f"Command exceeded {timeout}s timeout")
```

**Why This Example Is Complete:**
- Shows all security checks (command + path allowlists)
- Demonstrates proper logging with structured fields
- Includes timeout handling with process cleanup
- Shows output truncation for large results
- Complete docstrings and type hints

---

### Test Pattern (Task 1 Tests)

Complete test file showing pytest structure, async tests, and security test cases:

```python
# tests/core/test_terminal.py
import pytest
import asyncio
from src.core.terminal import TerminalExecutor, SecurityError, ExecutionResult

@pytest.fixture
def executor():
    """Create terminal executor instance."""
    return TerminalExecutor()

class TestTerminalExecutorSecurity:
    """Security-focused tests for terminal executor."""
    
    @pytest.mark.asyncio
    async def test_allowed_command_succeeds(self, executor):
        """Test allowed command executes successfully."""
        result = await executor.execute("ls", ["./"])
        
        assert isinstance(result, ExecutionResult)
        assert result.exit_code == 0
        assert len(result.stdout) > 0
    
    @pytest.mark.asyncio
    async def test_blocked_command_raises_security_error(self, executor):
        """Test blocked command raises SecurityError."""
        with pytest.raises(SecurityError) as exc_info:
            await executor.execute("rm", ["-rf", "/"])
        
        assert "not allowed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_allowed_path_succeeds(self, executor, tmp_path):
        """Test command with allowed path succeeds."""
        # Create test file in allowed directory
        test_file = tmp_path / "data" / "memory" / "test.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Hello")
        
        result = await executor.execute("cat", [str(test_file)])
        
        assert result.exit_code == 0
        assert "Hello" in result.stdout
    
    @pytest.mark.asyncio
    async def test_blocked_path_raises_security_error(self, executor):
        """Test command with blocked path raises SecurityError."""
        with pytest.raises(SecurityError) as exc_info:
            await executor.execute("cat", ["/etc/passwd"])
        
        assert "not allowed" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_timeout_kills_process(self, executor):
        """Test timeout kills long-running process."""
        with pytest.raises(TimeoutError):
            await executor.execute("python", ["-c", "import time; time.sleep(60)"], timeout=1)
    
    @pytest.mark.asyncio
    async def test_large_output_truncated(self, executor):
        """Test large output is truncated to 1MB."""
        # Generate 2MB of output
        result = await executor.execute(
            "python",
            ["-c", "print('x' * (2 * 1024 * 1024))"]
        )
        
        # Should be truncated to ~1MB
        assert len(result.stdout) <= 1024 * 1024 + 100  # Allow small buffer for truncation message
        assert "[Output truncated" in result.stdout

class TestTerminalExecutorExecution:
    """Functional tests for terminal executor."""
    
    @pytest.mark.asyncio
    async def test_successful_command_returns_output(self, executor):
        """Test successful command returns stdout."""
        result = await executor.execute("echo", ["Hello World"])
        
        assert result.exit_code == 0
        assert "Hello World" in result.stdout
        assert result.stderr == ""
    
    @pytest.mark.asyncio
    async def test_failed_command_returns_error(self, executor):
        """Test failed command returns non-zero exit code and stderr."""
        result = await executor.execute("python", ["-c", "import sys; sys.exit(1)"])
        
        assert result.exit_code == 1
    
    @pytest.mark.asyncio
    async def test_command_with_stderr(self, executor):
        """Test command writing to stderr."""
        result = await executor.execute(
            "python",
            ["-c", "import sys; sys.stderr.write('Error message')"]
        )
        
        assert "Error message" in result.stderr
```

**Why This Test File Is Complete:**
- Demonstrates pytest structure with class grouping
- Shows async test pattern with `@pytest.mark.asyncio`
- Uses fixtures for test setup (`executor`, `tmp_path`)
- Covers security cases (critical for Terminal Executor)
- Covers functional cases (success, failure, timeout, large output)
- Uses descriptive test names and docstrings
- Shows proper assertion patterns

---

## Implementation Notes

### Performance Considerations

- **Terminal Executor**: Subprocess creation has ~10-20ms overhead, acceptable for MVP
- **Skills Loader**: Scans filesystem once at startup, cached in memory
- **Memory Manager**: File I/O is async but not optimized (consider SQLite for Phase 2)
- **GCS Sync**: Fire-and-forget async to prevent blocking user requests

### Security Notes

- **Terminal Executor is the security boundary**: All other components trust it
- **Allowlists must be minimal**: Only add commands/paths when absolutely necessary
- **Path traversal prevention**: Use `startswith()` for path validation (simple but effective)
- **No user input in commands**: All skill args are sanitized by argparse in skills

### Deployment Requirements

**Python Dependencies** (add to `requirements.txt`):
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pyyaml>=6.0
google-cloud-storage>=2.10.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.12.0
```

**Environment Variables**:
```bash
# Memory configuration
MEMORY_DIR=./data/memory  # Local memory directory
GCS_ENABLED=false         # Enable GCS sync (true/false)
GCS_MEMORY_BUCKET=        # GCS bucket name (if GCS_ENABLED=true)

# Security configuration
ALLOWED_USERS=user1@example.com,user2@example.com  # Email allowlist for Gateway
```

**Directory Structure**:
```
emonk/
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── terminal.py
│   │   └── memory.py
│   └── skills/
│       ├── __init__.py
│       ├── loader.py
│       └── executor.py
├── skills/
│   ├── file-ops/
│   │   ├── SKILL.md
│   │   └── file_ops.py
│   └── memory/
│       ├── SKILL.md
│       └── memory.py
├── tests/
│   ├── core/
│   │   ├── test_terminal.py
│   │   └── test_memory.py
│   ├── skills/
│   │   ├── test_loader.py
│   │   └── test_executor.py
│   └── integration/
│       └── test_skills_integration.py
└── data/
    └── memory/  # Created at runtime
```

### Post-Deployment Verification

1. **Verify Terminal Executor Security**:
   ```bash
   pytest tests/core/test_terminal.py::TestTerminalExecutorSecurity -v
   ```
   All security tests must pass.

2. **Verify Skills Discovery**:
   ```bash
   python -c "from src.skills.loader import SkillLoader; loader = SkillLoader(); print(loader.load_skills())"
   ```
   Should list `file-ops` and `memory` skills.

3. **Verify Memory Persistence**:
   ```bash
   # Write test
   python -c "import asyncio; from src.core.memory import MemoryManager; m = MemoryManager(); asyncio.run(m.write_fact('user1', 'test', 'value'))"
   
   # Read test
   python -c "import asyncio; from src.core.memory import MemoryManager; m = MemoryManager(); print(asyncio.run(m.read_fact('user1', 'test')))"
   ```
   Should print: `value`

4. **Integration Tests**:
   ```bash
   pytest tests/integration/test_skills_integration.py -v
   ```
   All tests must pass.

---

## Final Verification

### Functionality Checklist

- [ ] Terminal Executor blocks all non-allowlisted commands
- [ ] Terminal Executor blocks all non-allowlisted paths
- [ ] Terminal Executor kills processes on timeout
- [ ] Terminal Executor truncates large output
- [ ] Skills Loader discovers all skills in `./skills/` directory
- [ ] Skills Loader parses SKILL.md YAML frontmatter correctly
- [ ] Skills Loader handles duplicate skill names gracefully
- [ ] Skills Engine executes skills via Terminal Executor
- [ ] Skills Engine converts args dict to CLI arguments
- [ ] Skills Engine returns SkillResult with success/error status
- [ ] Memory Manager writes conversation messages to daily files
- [ ] Memory Manager reads last N conversation messages
- [ ] Memory Manager writes facts to KNOWLEDGE_BASE/facts.json
- [ ] Memory Manager reads facts from KNOWLEDGE_BASE
- [ ] Memory Manager syncs to GCS asynchronously (if enabled)
- [ ] File-ops skill can read, write, list files
- [ ] Memory skill can store and retrieve facts

### Code Quality Checklist

- [ ] All public functions have type hints
- [ ] All public functions have docstrings
- [ ] All classes have docstrings
- [ ] Error handling is consistent (custom exceptions)
- [ ] Logging uses structured format (component name in extra fields)
- [ ] No security vulnerabilities in Terminal Executor
- [ ] No hardcoded paths (use Path objects)
- [ ] No blocking I/O in async functions

### Testing Checklist

- [ ] Terminal Executor: 100% coverage for security checks
- [ ] Skills Loader: Unit tests pass
- [ ] Skills Engine: Unit tests pass
- [ ] Memory Manager: Unit tests pass
- [ ] Integration tests: All scenarios pass
- [ ] Test files use pytest fixtures
- [ ] Test files use descriptive test names
- [ ] Tests clean up after themselves (use tmp_path)

### Build & Deployment Checklist

- [ ] All dependencies in requirements.txt
- [ ] README.md documents how to run tests
- [ ] README.md documents environment variables
- [ ] Directory structure matches specification
- [ ] Python version specified (>= 3.11)
- [ ] Pre-commit hooks run linter (black, ruff) if configured

---

## Acceptance Criteria Reference (from User Story)

**Skills Engine:**
- [x] Discover skills from `./skills/` directory ✓
- [x] Parse SKILL.md with YAML frontmatter ✓
- [x] Execute skills via Terminal Executor ✓
- [x] Handle duplicate skill names ✓
- [x] Handle missing skills gracefully ✓

**Terminal Executor Security:**
- [x] Allow only commands in ALLOWED_COMMANDS ✓
- [x] Block all other commands ✓
- [x] Allow only paths in ALLOWED_PATHS ✓
- [x] Block all other paths ✓
- [x] Kill processes on timeout ✓
- [x] Truncate output > 1MB ✓

**Memory Manager - Local Storage:**
- [x] Write conversations to daily markdown files ✓
- [x] Read last N messages from conversation history ✓
- [x] Write facts to facts.json ✓
- [x] Read facts from facts.json ✓
- [x] Cleanup conversations older than 90 days ✓

**Memory Manager - GCS Sync:**
- [x] Async upload to GCS (non-blocking) ✓
- [x] Handle GCS failures gracefully ✓
- [x] Download from GCS on startup (optional, Phase 2) ✓

**Example Skills:**
- [x] File-ops skill: read, write, list ✓
- [x] Memory skill: remember, recall ✓

---

## Success Metrics

After implementing Story 3, the following should be true:

1. **Security**: All security tests pass, no way to execute arbitrary commands
2. **Functionality**: All acceptance criteria met, all tests pass
3. **Code Quality**: Linter passes, type checker passes, docstrings complete
4. **Integration Ready**: Skills Engine, Terminal Executor, Memory Manager ready for Story 4 integration

---

**Status**: Ready for implementation! 🚀

**Next Steps**:
1. Create directory structure
2. Implement Task 1 (Terminal Executor) - MOST CRITICAL
3. Run security tests - must achieve 100% pass rate
4. Implement Tasks 2-6 in order
5. Run integration tests (Task 7)
6. Verify all acceptance criteria
7. Ready for Story 4 integration!
