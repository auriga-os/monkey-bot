# Cron & Task Scheduling - OpenClaw Code Extraction

**Source**: OpenClaw Cron system implementation  
**Purpose**: Reference for building Emonk's scheduled task system  
**Extraction Date**: 2026-02-11

---

## Overview

OpenClaw's cron system enables scheduled task execution with:
- **Multiple schedule types**: Cron expressions, intervals, one-time
- **Persistent storage**: Jobs survive restarts
- **Execution history**: Track runs and failures
- **Flexible delivery**: Send results to channels or run silently

### Key Components

1. **Schedule Parser**: Handle cron expressions, intervals, timestamps
2. **Job Store**: Persist jobs to disk (JSON)
3. **Timer System**: Trigger jobs at correct times
4. **Execution Runner**: Execute jobs and handle errors
5. **Delivery System**: Route job results to channels

---

## Schedule Types

### Cron Expression

```typescript
{
  kind: "cron",
  expr: "0 9 * * *",     // Every day at 9 AM
  tz: "America/New_York" // Optional timezone
}
```

### Interval

```typescript
{
  kind: "every",
  everyMs: 3600000,      // Every hour (milliseconds)
  anchorMs: Date.now()   // Start time
}
```

### One-Time

```typescript
{
  kind: "at",
  at: "2026-02-15T09:00:00Z"  // ISO 8601 timestamp
}
```

---

## Next Run Calculation

```typescript
export function computeNextRunAtMs(
  schedule: CronSchedule,
  nowMs: number
): number | undefined {
  if (schedule.kind === "at") {
    const atMs = parseAbsoluteTimeMs(schedule.at);
    return atMs > nowMs ? atMs : undefined;
  }
  
  if (schedule.kind === "every") {
    const everyMs = Math.max(1, Math.floor(schedule.everyMs));
    const anchor = Math.max(0, Math.floor(schedule.anchorMs ?? nowMs));
    if (nowMs < anchor) {
      return anchor;
    }
    const elapsed = nowMs - anchor;
    const steps = Math.max(1, Math.floor((elapsed + everyMs - 1) / everyMs));
    return anchor + steps * everyMs;
  }
  
  // Cron expression
  const expr = schedule.expr.trim();
  const cron = new Cron(expr, {
    timezone: resolveCronTimezone(schedule.tz),
    catch: false,
  });
  const next = cron.nextRun(new Date(nowMs - 1));
  return next ? next.getTime() : undefined;
}
```

---

## Job Storage

### Job Structure

```typescript
type CronJob = {
  id: string;              // UUID
  name?: string;           // Human-readable name
  enabled: boolean;        // Can disable without deleting
  schedule: CronSchedule;  // When to run
  payload: CronPayload;    // What to execute
  delivery?: CronDelivery; // Where to send results
  createdAt: number;       // Unix timestamp
  updatedAt: number;
  nextRunAt?: number;      // Computed next run time
  lastRunAt?: number;
  lastRunStatus?: "success" | "error";
};

type CronPayload = {
  kind: "agentTurn" | "systemEvent";
  message?: string;        // For agentTurn
  text?: string;           // For systemEvent
  model?: string;          // Model override
  timeoutSeconds?: number;
};

type CronDelivery = {
  mode: "announce" | "none";
  channel?: string;        // "telegram", "discord", etc
  to?: string;             // Specific recipient
  bestEffort?: boolean;    // Don't fail if delivery fails
};
```

### Persistence

```typescript
// Store jobs in JSON file
const STORE_PATH = path.join(stateDir, "cron-jobs.json");

function saveJobs(jobs: Map<string, CronJob>): void {
  const data = JSON.stringify(
    Array.from(jobs.values()),
    null,
    2
  );
  fs.writeFileSync(STORE_PATH, data, "utf-8");
}

function loadJobs(): Map<string, CronJob> {
  if (!fs.existsSync(STORE_PATH)) {
    return new Map();
  }
  const data = fs.readFileSync(STORE_PATH, "utf-8");
  const array = JSON.parse(data);
  const map = new Map();
  for (const job of array) {
    map.set(job.id, job);
  }
  return map;
}
```

---

## Timer System

### Timer Manager

```typescript
class CronTimerManager {
  private timers = new Map<string, NodeJS.Timeout>();
  
  schedule(job: CronJob, onTrigger: (job: CronJob) => void): void {
    this.clear(job.id);
    
    if (!job.enabled) {
      return;
    }
    
    const nextRunAt = computeNextRunAtMs(job.schedule, Date.now());
    if (!nextRunAt) {
      return;  // No future runs
    }
    
    const delayMs = Math.max(0, nextRunAt - Date.now());
    
    const timer = setTimeout(() => {
      this.timers.delete(job.id);
      onTrigger(job);
    }, delayMs);
    
    this.timers.set(job.id, timer);
  }
  
  clear(jobId: string): void {
    const timer = this.timers.get(jobId);
    if (timer) {
      clearTimeout(timer);
      this.timers.delete(jobId);
    }
  }
  
  clearAll(): void {
    for (const timer of this.timers.values()) {
      clearTimeout(timer);
    }
    this.timers.clear();
  }
}
```

---

## Job Execution

### Execution Runner

```typescript
async function executeJob(job: CronJob): Promise<void> {
  const startMs = Date.now();
  
  try {
    // Execute payload
    let result: string;
    if (job.payload.kind === "agentTurn") {
      result = await executeAgentTurn(job.payload);
    } else {
      result = await executeSystemEvent(job.payload);
    }
    
    // Update job status
    job.lastRunAt = startMs;
    job.lastRunStatus = "success";
    
    // Deliver result
    if (job.delivery && job.delivery.mode === "announce") {
      await deliverResult(job.delivery, result);
    }
    
    // Log execution
    logExecution({
      jobId: job.id,
      status: "success",
      durationMs: Date.now() - startMs,
    });
  } catch (err) {
    job.lastRunAt = startMs;
    job.lastRunStatus = "error";
    
    logExecution({
      jobId: job.id,
      status: "error",
      error: String(err),
      durationMs: Date.now() - startMs,
    });
    
    throw err;
  }
}

async function executeAgentTurn(payload: CronPayload): Promise<string> {
  // Call agent with message
  const response = await callGateway({
    method: "agent.chat",
    params: {
      message: payload.message,
      model: payload.model,
      timeoutMs: (payload.timeoutSeconds ?? 300) * 1000,
    },
  });
  return response.text || "";
}
```

---

## Emonk Adaptation (Python)

### Simple Cron Manager

```python
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Callable
from croniter import croniter

class CronManager:
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.jobs: Dict[str, dict] = {}
        self.timers: Dict[str, threading.Timer] = {}
        self.load_jobs()
    
    def load_jobs(self):
        """Load jobs from storage"""
        if self.storage_path.exists():
            with open(self.storage_path) as f:
                jobs_list = json.load(f)
                for job in jobs_list:
                    self.jobs[job["id"]] = job
    
    def save_jobs(self):
        """Save jobs to storage"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(list(self.jobs.values()), f, indent=2)
    
    def add_job(
        self,
        job_id: str,
        schedule: dict,
        payload: dict,
        name: str = None,
        enabled: bool = True
    ):
        """Add a new job"""
        job = {
            "id": job_id,
            "name": name,
            "enabled": enabled,
            "schedule": schedule,
            "payload": payload,
            "createdAt": int(time.time()),
            "updatedAt": int(time.time()),
        }
        self.jobs[job_id] = job
        self.save_jobs()
        self.schedule_job(job)
    
    def remove_job(self, job_id: str):
        """Remove a job"""
        if job_id in self.jobs:
            self.cancel_timer(job_id)
            del self.jobs[job_id]
            self.save_jobs()
    
    def schedule_job(self, job: dict):
        """Schedule a job to run"""
        self.cancel_timer(job["id"])
        
        if not job.get("enabled"):
            return
        
        next_run = self.compute_next_run(job["schedule"])
        if not next_run:
            return
        
        delay = max(0, next_run - time.time())
        
        def run():
            self.execute_job(job)
            # Reschedule if recurring
            if job["schedule"]["kind"] in ["cron", "every"]:
                self.schedule_job(job)
        
        timer = threading.Timer(delay, run)
        timer.start()
        self.timers[job["id"]] = timer
    
    def compute_next_run(self, schedule: dict) -> float:
        """Compute next run time"""
        now = time.time()
        
        if schedule["kind"] == "at":
            # One-time execution
            at_time = datetime.fromisoformat(schedule["at"]).timestamp()
            return at_time if at_time > now else None
        
        elif schedule["kind"] == "every":
            # Interval execution
            every_ms = schedule["everyMs"]
            anchor = schedule.get("anchorMs", now * 1000)
            elapsed = (now * 1000) - anchor
            steps = max(1, int((elapsed + every_ms - 1) / every_ms))
            return (anchor + steps * every_ms) / 1000
        
        elif schedule["kind"] == "cron":
            # Cron expression
            expr = schedule["expr"]
            tz = schedule.get("tz")
            cron = croniter(expr, datetime.now())
            return cron.get_next()
        
        return None
    
    def execute_job(self, job: dict):
        """Execute a job"""
        start_time = time.time()
        
        try:
            # Execute payload
            payload = job["payload"]
            if payload["kind"] == "agentTurn":
                result = self.execute_agent_turn(payload)
            else:
                result = self.execute_system_event(payload)
            
            # Update job
            job["lastRunAt"] = int(start_time)
            job["lastRunStatus"] = "success"
            self.save_jobs()
            
            # Log
            print(f"Job {job['id']} executed successfully")
            
        except Exception as e:
            job["lastRunAt"] = int(start_time)
            job["lastRunStatus"] = "error"
            job["lastError"] = str(e)
            self.save_jobs()
            print(f"Job {job['id']} failed: {e}")
    
    def execute_agent_turn(self, payload: dict) -> str:
        """Execute agent turn"""
        # Call agent via gateway
        # This would integrate with your gateway client
        message = payload.get("message", "")
        # return agent_response
        return ""
    
    def cancel_timer(self, job_id: str):
        """Cancel a job's timer"""
        if job_id in self.timers:
            self.timers[job_id].cancel()
            del self.timers[job_id]
    
    def stop(self):
        """Stop all timers"""
        for timer in self.timers.values():
            timer.cancel()
        self.timers.clear()

# Usage
cron = CronManager("./data/cron-jobs.json")

# Add daily job at 9 AM
cron.add_job(
    job_id="daily-report",
    name="Daily Report",
    schedule={
        "kind": "cron",
        "expr": "0 9 * * *",
        "tz": "America/New_York"
    },
    payload={
        "kind": "agentTurn",
        "message": "Generate daily social media report"
    }
)

# Add hourly job
cron.add_job(
    job_id="hourly-check",
    name="Hourly Check",
    schedule={
        "kind": "every",
        "everyMs": 3600000  # 1 hour
    },
    payload={
        "kind": "agentTurn",
        "message": "Check for trending topics"
    }
)
```

---

## Key Takeaways

1. **Three schedule types**: Cron, interval, one-time
2. **Persistent storage**: JSON file survives restarts
3. **Timer management**: setTimeout for scheduling
4. **Execution history**: Track success/failure
5. **Error handling**: Don't crash on job failures

---

**Next Document**: [05_skills_system.md](05_skills_system.md)
