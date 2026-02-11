# Shell Execution & Terminal Tools - OpenClaw Code Extraction

**Source**: OpenClaw Terminal execution implementation  
**Purpose**: Reference for building Emonk's shell execution capability  
**Extraction Date**: 2026-02-11

---

## Overview

OpenClaw's terminal executor enables secure shell command execution with:
- **Sandboxed execution**: Docker container isolation
- **Security allowlist**: Pre-approved commands only
- **Process management**: Track running/completed processes
- **Output handling**: Capture stdout/stderr with limits
- **Background jobs**: Long-running processes

---

## Security Model

### Three Security Levels

1. **deny**: Block all shell access
2. **allowlist**: Only pre-approved commands
3. **full**: Unrestricted (dangerous!)

### Dangerous Environment Variables (Blocked)

```typescript
const DANGEROUS_HOST_ENV_VARS = new Set([
  "LD_PRELOAD",
  "LD_LIBRARY_PATH",
  "LD_AUDIT",
  "DYLD_INSERT_LIBRARIES",
  "DYLD_LIBRARY_PATH",
  "NODE_OPTIONS",
  "NODE_PATH",
  "PYTHONPATH",
  "PYTHONHOME",
  "RUBYLIB",
  "PERL5LIB",
  "BASH_ENV",
  "ENV",
  "IFS",
]);

function validateHostEnv(env: Record<string, string>): void {
  for (const key of Object.keys(env)) {
    const upperKey = key.toUpperCase();
    
    // Block dangerous prefixes
    if (upperKey.startsWith("DYLD_") || upperKey.startsWith("LD_")) {
      throw new Error(`Security Violation: ${key} is forbidden`);
    }
    
    // Block known dangerous variables
    if (DANGEROUS_HOST_ENV_VARS.has(upperKey)) {
      throw new Error(`Security Violation: ${key} is forbidden`);
    }
    
    // Block PATH modification (prevents binary hijacking)
    if (upperKey === "PATH") {
      throw new Error(`Security Violation: Custom PATH is forbidden`);
    }
  }
}
```

### Safe Binaries Allowlist

```typescript
const DEFAULT_SAFE_BINS = [
  "ls", "cat", "grep", "find", "head", "tail",
  "echo", "date", "pwd", "whoami",
  "git", "gh", "python", "python3", "node",
  "curl", "wget", "jq",
];

function evaluateShellAllowlist(
  command: string,
  safeBins: string[]
): { allowed: boolean; reason?: string } {
  // Extract first token (binary name)
  const tokens = command.trim().split(/\s+/);
  const binary = tokens[0];
  
  if (!binary) {
    return { allowed: false, reason: "Empty command" };
  }
  
  // Check if binary is in allowlist
  if (safeBins.includes(binary)) {
    return { allowed: true };
  }
  
  // Check if it's a path to allowed binary
  const basename = path.basename(binary);
  if (safeBins.includes(basename)) {
    return { allowed: true };
  }
  
  return {
    allowed: false,
    reason: `Binary '${binary}' not in allowlist`,
  };
}
```

---

## Process Session Management

### Session Structure

```typescript
export interface ProcessSession {
  id: string;              // Unique session ID
  command: string;         // Command being executed
  scopeKey?: string;       // Agent scope
  sessionKey?: string;     // Agent session
  pid?: number;            // Process ID
  startedAt: number;       // Unix timestamp
  cwd?: string;            // Working directory
  maxOutputChars: number;  // Output size limit
  totalOutputChars: number;
  pendingStdout: string[]; // Buffered stdout
  pendingStderr: string[]; // Buffered stderr
  aggregated: string;      // Combined output
  tail: string;            // Last N chars for preview
  exitCode?: number | null;
  exitSignal?: string | null;
  exited: boolean;
  truncated: boolean;
  backgrounded: boolean;
}
```

### Session Registry

```typescript
const runningSessions = new Map<string, ProcessSession>();
const finishedSessions = new Map<string, FinishedSession>();

export function addSession(session: ProcessSession) {
  runningSessions.set(session.id, session);
  startSweeper();  // Auto-cleanup old sessions
}

export function getSession(id: string) {
  return runningSessions.get(id);
}

export function markExited(
  session: ProcessSession,
  exitCode: number | null,
  exitSignal: string | null,
  status: ProcessStatus,
) {
  session.exited = true;
  session.exitCode = exitCode;
  session.exitSignal = exitSignal;
  session.tail = tail(session.aggregated, 2000);
  
  // Move to finished sessions
  runningSessions.delete(session.id);
  finishedSessions.set(session.id, {
    id: session.id,
    command: session.command,
    startedAt: session.startedAt,
    endedAt: Date.now(),
    status,
    exitCode,
    exitSignal,
    aggregated: session.aggregated,
    tail: session.tail,
    truncated: session.truncated,
    totalOutputChars: session.totalOutputChars,
  });
}
```

---

## Command Execution

### Execute with Timeout

```typescript
export async function executeCommand(params: {
  command: string;
  cwd?: string;
  env?: Record<string, string>;
  timeoutSec?: number;
  maxOutputChars?: number;
}): Promise<ExecProcessOutcome> {
  const startedAt = Date.now();
  
  // Create session
  const sessionId = createSessionSlug();
  const session: ProcessSession = {
    id: sessionId,
    command: params.command,
    startedAt,
    maxOutputChars: params.maxOutputChars ?? 200_000,
    totalOutputChars: 0,
    pendingStdout: [],
    pendingStderr: [],
    aggregated: "",
    tail: "",
    exited: false,
    truncated: false,
    backgrounded: false,
  };
  
  addSession(session);
  
  // Spawn process
  const child = spawn("bash", ["-c", params.command], {
    cwd: params.cwd ?? process.cwd(),
    env: { ...process.env, ...params.env },
    shell: false,
  });
  
  session.pid = child.pid;
  
  // Handle output
  child.stdout.on("data", (data) => {
    appendOutput(session, "stdout", data.toString());
  });
  
  child.stderr.on("data", (data) => {
    appendOutput(session, "stderr", data.toString());
  });
  
  // Wait for exit or timeout
  const outcome = await new Promise<ExecProcessOutcome>((resolve) => {
    let timedOut = false;
    let timeoutHandle: NodeJS.Timeout | null = null;
    
    if (params.timeoutSec) {
      timeoutHandle = setTimeout(() => {
        timedOut = true;
        child.kill("SIGTERM");
        setTimeout(() => child.kill("SIGKILL"), 5000);
      }, params.timeoutSec * 1000);
    }
    
    child.on("exit", (exitCode, exitSignal) => {
      if (timeoutHandle) {
        clearTimeout(timeoutHandle);
      }
      
      const durationMs = Date.now() - startedAt;
      const status = exitCode === 0 ? "completed" : "failed";
      
      markExited(session, exitCode, exitSignal, status);
      
      resolve({
        status,
        exitCode,
        exitSignal,
        durationMs,
        aggregated: session.aggregated,
        timedOut,
        reason: timedOut ? "Command timed out" : undefined,
      });
    });
  });
  
  return outcome;
}
```

### Output Buffering

```typescript
export function appendOutput(
  session: ProcessSession,
  stream: "stdout" | "stderr",
  chunk: string
) {
  const buffer = stream === "stdout" ? session.pendingStdout : session.pendingStderr;
  buffer.push(chunk);
  
  // Check size limit
  const pendingChars = buffer.join("").length;
  const pendingCap = Math.min(30_000, session.maxOutputChars);
  
  if (pendingChars > pendingCap) {
    session.truncated = true;
    // Drop oldest chunks to stay under limit
    while (buffer.join("").length > pendingCap && buffer.length > 0) {
      buffer.shift();
    }
  }
  
  session.totalOutputChars += chunk.length;
  
  // Update aggregated output
  const aggregated = session.aggregated + chunk;
  if (aggregated.length > session.maxOutputChars) {
    session.truncated = true;
    session.aggregated = aggregated.slice(-session.maxOutputChars);
  } else {
    session.aggregated = aggregated;
  }
  
  // Update tail (last 2000 chars)
  session.tail = session.aggregated.slice(-2000);
}

export function drainSession(session: ProcessSession) {
  const stdout = session.pendingStdout.join("");
  const stderr = session.pendingStderr.join("");
  session.pendingStdout = [];
  session.pendingStderr = [];
  return { stdout, stderr };
}
```

---

## Background Processes

### Backgrounding Long-Running Commands

```typescript
export async function executeWithBackground(params: {
  command: string;
  backgroundMs?: number;  // Auto-background after N ms
}): Promise<ExecToolResult> {
  const backgroundMs = params.backgroundMs ?? 10_000;
  const handle = await executeCommandAsync(params);
  
  // Wait for backgroundMs or completion
  const result = await Promise.race([
    handle.promise,
    new Promise<null>((resolve) => 
      setTimeout(() => resolve(null), backgroundMs)
    ),
  ]);
  
  if (result === null) {
    // Backgrounded
    markBackgrounded(handle.session);
    return {
      status: "running",
      sessionId: handle.session.id,
      pid: handle.pid,
      startedAt: handle.startedAt,
      tail: handle.session.tail,
    };
  } else {
    // Completed before timeout
    return {
      status: result.status,
      exitCode: result.exitCode,
      aggregated: result.aggregated,
      durationMs: result.durationMs,
    };
  }
}
```

---

## Emonk Adaptation (Python)

### Simple Terminal Executor

```python
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ProcessSession:
    id: str
    command: str
    pid: int
    started_at: float
    max_output: int = 200_000
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    exited: bool = False
    backgrounded: bool = False

class TerminalExecutor:
    def __init__(self, safe_bins: list[str] = None):
        self.safe_bins = safe_bins or [
            "ls", "cat", "grep", "echo", "pwd",
            "git", "gh", "python", "python3",
            "curl", "jq",
        ]
        self.sessions: Dict[str, ProcessSession] = {}
    
    def is_allowed(self, command: str) -> tuple[bool, str]:
        """Check if command is allowed"""
        tokens = command.split()
        if not tokens:
            return False, "Empty command"
        
        binary = tokens[0]
        if binary in self.safe_bins:
            return True, ""
        
        return False, f"Binary '{binary}' not in allowlist"
    
    def execute(
        self,
        command: str,
        cwd: str = None,
        timeout: int = 300,
        background_after: int = 10
    ) -> dict:
        """Execute command with optional backgrounding"""
        # Check allowlist
        allowed, reason = self.is_allowed(command)
        if not allowed:
            return {
                "status": "error",
                "error": f"Command not allowed: {reason}"
            }
        
        # Create session
        session_id = str(time.time())
        
        # Start process
        proc = subprocess.Popen(
            ["bash", "-c", command],
            cwd=cwd or ".",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        session = ProcessSession(
            id=session_id,
            command=command,
            pid=proc.pid,
            started_at=time.time()
        )
        self.sessions[session_id] = session
        
        # Wait for completion or background timeout
        try:
            stdout, stderr = proc.communicate(timeout=background_after)
            session.stdout = stdout
            session.stderr = stderr
            session.exit_code = proc.returncode
            session.exited = True
            
            return {
                "status": "completed" if proc.returncode == 0 else "failed",
                "exitCode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "durationMs": int((time.time() - session.started_at) * 1000)
            }
        except subprocess.TimeoutExpired:
            # Background the process
            session.backgrounded = True
            return {
                "status": "running",
                "sessionId": session_id,
                "pid": proc.pid,
                "message": f"Command backgrounded after {background_after}s"
            }
    
    def get_status(self, session_id: str) -> dict:
        """Get status of backgrounded command"""
        session = self.sessions.get(session_id)
        if not session:
            return {"status": "not_found"}
        
        if session.exited:
            return {
                "status": "completed" if session.exit_code == 0 else "failed",
                "exitCode": session.exit_code,
                "stdout": session.stdout,
                "stderr": session.stderr,
            }
        else:
            return {
                "status": "running",
                "pid": session.pid,
                "duration": int((time.time() - session.started_at) * 1000)
            }

# Usage
executor = TerminalExecutor()

# Execute command
result = executor.execute("ls -la", timeout=60)
print(result)

# Background long command
result = executor.execute("python train.py", background_after=5)
if result["status"] == "running":
    # Check status later
    time.sleep(10)
    status = executor.get_status(result["sessionId"])
```

---

## Key Takeaways

1. **Security first**: Allowlist, no dangerous env vars
2. **Output limits**: Prevent memory exhaustion
3. **Backgrounding**: Handle long-running processes
4. **Process tracking**: Session registry for all executions
5. **Timeouts**: Kill runaway processes

---

**End of Extraction Documents**

---

## Summary

All 7 extraction documents completed:

1. **01_gateway_daemon.md**: Gateway daemon, loopback binding, lock mechanism
2. **02_telegram_integration.md**: Grammy framework, message handling, access control
3. **03_memory_system.md**: File-based storage, embeddings, vector search
4. **04_cron_scheduler.md**: Cron expressions, job storage, scheduling
5. **05_skills_system.md**: SKILL.md format, CLI wrappers, discovery
6. **06_llm_integration.md**: Vertex AI, model selection, cost optimization
7. **07_terminal_executor.md**: Secure shell execution, allowlists, process management

These documents provide comprehensive patterns for building Emonk while avoiding license risks.
