# 14 - Observability & Tracing (Goose + Langfuse Pattern)

**Source:** Goose (Block/Square) + Langfuse Integration  
**Implementation:** Structured logging with LLM tracing and cost tracking  
**Key Feature:** Visual debugging of agent behavior and error recovery

---

## Overview

Goose implements comprehensive observability through:

1. **Structured Logging:** JSON-formatted logs with trace IDs, timestamps, metadata
2. **Langfuse Integration:** LLM tracing platform for visualizing agent sessions
3. **Cost Tracking:** Per-session token usage and cost attribution
4. **Error Tracing:** See exactly how LLM self-corrected errors in timeline view

**Key Insight from Goose Blog:**
> "Long agent sessions are hard to debug without observability. Langfuse's timeline view shows exactly where the agent got stuck, which tools failed, and how much each turn cost."

**What Langfuse Captures:**
- Full prompt/response pairs
- Tool call requests and results
- Token usage and costs per turn
- Parallel tool execution visualization
- Error recovery attempts
- Session-level aggregations

---

## Core Pattern

### Structured Logging

```python
import structlog
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import json

# Configure structured logging (JSON output)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()  # JSON output for parsing
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()

class TraceContext:
    """
    Trace context for distributed tracing.
    Tracks execution across tool calls and sub-tasks.
    """
    
    def __init__(self, trace_id: Optional[str] = None, parent_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.parent_id = parent_id
        self.start_time = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def child_span(self, name: str) -> "TraceContext":
        """Create child span for nested operations"""
        child = TraceContext(trace_id=self.trace_id, parent_id=self.span_id)
        child.metadata["span_name"] = name
        return child
    
    def log_event(self, event: str, **kwargs):
        """Log event with trace context"""
        log.info(
            event,
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_id=self.parent_id,
            duration_ms=(datetime.now() - self.start_time).total_seconds() * 1000,
            **kwargs
        )
    
    def log_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        latency_ms: float
    ):
        """Log LLM invocation with cost tracking"""
        self.log_event(
            "llm_call",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            latency_ms=latency_ms
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        parameters: Dict,
        result: Any,
        success: bool,
        latency_ms: float
    ):
        """Log tool execution"""
        self.log_event(
            "tool_call",
            tool_name=tool_name,
            parameters=parameters,
            success=success,
            result_size=len(str(result)) if result else 0,
            latency_ms=latency_ms
        )

class ObservabilityManager:
    """
    Goose-inspired observability for agent sessions.
    Tracks LLM calls, tool executions, costs, and errors.
    """
    
    def __init__(self):
        self.current_trace: Optional[TraceContext] = None
        self.session_stats: Dict[str, Any] = {
            "llm_calls": 0,
            "tool_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "errors": 0,
            "recoveries": 0,  # Errors that were self-corrected
            "start_time": None,
            "end_time": None
        }
        self.tool_stats: Dict[str, Dict[str, int]] = {}  # Per-tool statistics
    
    def start_trace(self, operation: str, metadata: Optional[Dict] = None) -> TraceContext:
        """Start new trace for an operation"""
        trace = TraceContext()
        trace.metadata["operation"] = operation
        if metadata:
            trace.metadata.update(metadata)
        
        if not self.session_stats["start_time"]:
            self.session_stats["start_time"] = datetime.now()
        
        trace.log_event("trace_start", operation=operation)
        self.current_trace = trace
        return trace
    
    def end_trace(self, trace: TraceContext):
        """End trace and log summary"""
        self.session_stats["end_time"] = datetime.now()
        
        duration = (datetime.now() - trace.start_time).total_seconds()
        trace.log_event(
            "trace_end",
            duration_seconds=duration,
            **self.session_stats
        )
    
    def log_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float
    ):
        """Track LLM call with cost calculation"""
        cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
        
        self.session_stats["llm_calls"] += 1
        self.session_stats["total_input_tokens"] += prompt_tokens
        self.session_stats["total_output_tokens"] += completion_tokens
        self.session_stats["total_cost"] += cost
        
        if self.current_trace:
            self.current_trace.log_llm_call(
                model, prompt_tokens, completion_tokens, cost, latency_ms
            )
    
    def log_tool_call(
        self,
        tool_name: str,
        parameters: Dict,
        result: Any,
        success: bool,
        latency_ms: float
    ):
        """Track tool execution"""
        self.session_stats["tool_calls"] += 1
        
        if not success:
            self.session_stats["errors"] += 1
        
        # Per-tool statistics
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = {
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "total_latency_ms": 0
            }
        
        self.tool_stats[tool_name]["calls"] += 1
        if success:
            self.tool_stats[tool_name]["successes"] += 1
        else:
            self.tool_stats[tool_name]["failures"] += 1
        self.tool_stats[tool_name]["total_latency_ms"] += latency_ms
        
        if self.current_trace:
            self.current_trace.log_tool_call(
                tool_name, parameters, result, success, latency_ms
            )
    
    def log_error_recovery(self, tool_name: str, error: str, recovered: bool):
        """Track error recovery attempts"""
        if recovered:
            self.session_stats["recoveries"] += 1
        
        log.info(
            "error_recovery",
            tool_name=tool_name,
            error=error,
            recovered=recovered,
            trace_id=self.current_trace.trace_id if self.current_trace else None
        )
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        if self.session_stats["start_time"] and self.session_stats["end_time"]:
            duration = (self.session_stats["end_time"] - self.session_stats["start_time"]).total_seconds()
        else:
            duration = 0
        
        total_tokens = (
            self.session_stats["total_input_tokens"] + 
            self.session_stats["total_output_tokens"]
        )
        
        return {
            **self.session_stats,
            "duration_seconds": duration,
            "total_tokens": total_tokens,
            "cost_per_call": self.session_stats["total_cost"] / max(1, self.session_stats["llm_calls"]),
            "tokens_per_call": total_tokens / max(1, self.session_stats["llm_calls"]),
            "error_rate": self.session_stats["errors"] / max(1, self.session_stats["tool_calls"]),
            "recovery_rate": self.session_stats["recoveries"] / max(1, self.session_stats["errors"]),
            "tool_stats": self.tool_stats
        }
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on model pricing"""
        # Vertex AI Gemini pricing (as of Feb 2026)
        pricing = {
            "gemini-2.0-flash-exp": {
                "input": 0.00004,   # $0.04 per 1M tokens
                "output": 0.00016   # $0.16 per 1M tokens
            },
            "gemini-2.0-pro-exp-0205": {
                "input": 0.00070,   # $0.70 per 1M tokens
                "output": 0.00210   # $2.10 per 1M tokens
            },
        }
        
        if model not in pricing:
            return 0.0
        
        return (
            prompt_tokens / 1000 * pricing[model]["input"] + 
            completion_tokens / 1000 * pricing[model]["output"]
        )
```

### Langfuse Integration

```python
from langfuse import Langfuse
import os

# Initialize Langfuse client
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

class LangfuseObserver:
    """
    Wrap agent operations with Langfuse tracing.
    Provides visual timeline view of agent execution.
    """
    
    def __init__(self):
        self.current_trace = None
        self.current_generation = None
    
    def start_session(self, session_id: str, user_id: str, metadata: Dict = None):
        """Start Langfuse trace for session"""
        self.current_trace = langfuse.trace(
            name=f"agent_session_{session_id}",
            user_id=user_id,
            metadata=metadata or {},
            session_id=session_id
        )
        return self.current_trace
    
    def log_llm_generation(
        self,
        name: str,
        model: str,
        input_messages: List[Dict],
        output: str,
        usage: Dict,
        metadata: Dict = None
    ):
        """Log LLM generation to Langfuse"""
        if not self.current_trace:
            raise ValueError("Must start session before logging generation")
        
        generation = self.current_trace.generation(
            name=name,
            model=model,
            input=input_messages,
            output=output,
            usage=usage,  # {"input": N, "output": M, "total": N+M}
            metadata=metadata or {}
        )
        
        self.current_generation = generation
        return generation
    
    def log_tool_call(
        self,
        name: str,
        input_params: Dict,
        output: Any,
        status_message: Optional[str] = None,
        level: str = "DEFAULT"  # DEFAULT, WARNING, ERROR
    ):
        """Log tool execution as Langfuse span"""
        if not self.current_trace:
            raise ValueError("Must start session before logging tool call")
        
        span = self.current_trace.span(
            name=name,
            input=input_params,
            output=output,
            status_message=status_message,
            level=level
        )
        return span
    
    def log_event(self, name: str, metadata: Dict = None):
        """Log custom event"""
        if self.current_trace:
            self.current_trace.event(
                name=name,
                metadata=metadata or {}
            )
    
    def end_session(self):
        """Finalize trace"""
        if self.current_trace:
            # Langfuse automatically finalizes on flush
            langfuse.flush()
            self.current_trace = None

# Integration with agent loop
observability = ObservabilityManager()
langfuse_observer = LangfuseObserver()

async def agent_loop_with_observability(
    user_message: str,
    session_id: str,
    user_id: str
) -> str:
    """Agent loop with full observability"""
    
    # Start traces
    trace = observability.start_trace("agent_loop", {
        "session_id": session_id,
        "user_id": user_id
    })
    langfuse_observer.start_session(session_id, user_id, {
        "initial_message": user_message
    })
    
    try:
        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": user_message}
        ]
        
        for iteration in range(10):
            # Select model
            model = router.select_model()
            
            # Call LLM
            start_time = datetime.now()
            response = await llm_client.generate(messages, model=model.name)
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log to structured logs
            observability.log_llm_call(
                model=model.name,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                latency_ms=latency_ms
            )
            
            # Log to Langfuse
            langfuse_observer.log_llm_generation(
                name=f"turn_{iteration}",
                model=model.name,
                input_messages=messages,
                output=response.text,
                usage={
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total": response.usage.prompt_tokens + response.usage.completion_tokens
                },
                metadata={
                    "iteration": iteration,
                    "model_tier": model.tier.value
                }
            )
            
            # Process tool calls
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_trace = trace.child_span(f"tool_{tool_call.name}")
                    
                    start_time = datetime.now()
                    try:
                        result = await skill_registry.execute(
                            tool_call.name,
                            tool_call.parameters
                        )
                        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                        
                        # Log success
                        observability.log_tool_call(
                            tool_name=tool_call.name,
                            parameters=tool_call.parameters,
                            result=result,
                            success=True,
                            latency_ms=latency_ms
                        )
                        
                        langfuse_observer.log_tool_call(
                            name=tool_call.name,
                            input_params=tool_call.parameters,
                            output=result,
                            level="DEFAULT"
                        )
                        
                        messages.append({
                            "role": "function",
                            "name": tool_call.name,
                            "content": json.dumps(result)
                        })
                        
                    except AgentError as e:
                        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                        
                        # Log recoverable error
                        observability.log_tool_call(
                            tool_name=tool_call.name,
                            parameters=tool_call.parameters,
                            result=str(e),
                            success=False,
                            latency_ms=latency_ms
                        )
                        
                        langfuse_observer.log_tool_call(
                            name=tool_call.name,
                            input_params=tool_call.parameters,
                            output=e.to_tool_response(),
                            status_message=f"Recoverable error: {e.message}",
                            level="WARNING"
                        )
                        
                        # Track recovery
                        observability.log_error_recovery(
                            tool_name=tool_call.name,
                            error=e.message,
                            recovered=e.recoverable
                        )
                        
                        messages.append({
                            "role": "function",
                            "name": tool_call.name,
                            "content": json.dumps(e.to_tool_response())
                        })
                        
                    except InfraError as e:
                        # Fatal error
                        langfuse_observer.log_tool_call(
                            name=tool_call.name,
                            input_params=tool_call.parameters,
                            output=None,
                            status_message=f"Infrastructure failure: {e}",
                            level="ERROR"
                        )
                        raise
                
                continue
            
            # Final response
            summary = observability.get_session_summary()
            log.info("session_complete", **summary)
            
            langfuse_observer.log_event("session_complete", metadata=summary)
            langfuse_observer.end_session()
            
            observability.end_trace(trace)
            return response.text
        
    except Exception as e:
        log.error("session_failed", error=str(e), trace_id=trace.trace_id)
        langfuse_observer.log_event("session_failed", metadata={"error": str(e)})
        langfuse_observer.end_session()
        raise
    
    finally:
        # Ensure Langfuse flushes
        langfuse.flush()
```

---

## Pros

### ✅ Visual Timeline View
**Source:** Goose + Langfuse blog post, LangSmith comparison

- **See What Happened:** Timeline shows exact sequence of LLM calls and tool executions
- **Parallel Execution:** Visualize concurrent tool calls
- **Error Recovery:** See LLM retry attempts and self-corrections
- **Cost Attribution:** See which turns consumed most tokens/cost

**Example Langfuse Timeline:**
```
Turn 1: [3.2s] LLM Generation (Gemini Pro) - 2,340 tokens - $0.0048
  ├─ Tool Call: search_web (1.8s) - SUCCESS
  └─ Tool Call: read_file (0.3s) - SUCCESS

Turn 2: [2.1s] LLM Generation (Gemini Flash) - 1,120 tokens - $0.0005
  └─ Tool Call: create_file (0.5s) - FAILED: Missing parameter
  
Turn 3: [2.4s] LLM Generation (Gemini Flash) - 1,280 tokens - $0.0006
  └─ Tool Call: create_file (0.6s) - SUCCESS (recovered from error)

Total: 4,740 tokens, $0.0059, 3 turns, 1 error (recovered)
```

### ✅ Structured Logs for Automation
**Source:** JSON logging best practices

- **Machine Readable:** JSON logs can be parsed by log aggregators (DataDog, Splunk)
- **Queryable:** Filter by trace_id, session_id, tool_name, etc.
- **Alerting:** Set up alerts on error_rate, cost thresholds, latency spikes

**Example Log Query (DataDog):**
```
# Find all sessions with > 5 errors
service:emonk event:session_complete @session_stats.errors:>5

# Find expensive sessions (> $0.10)
service:emonk event:session_complete @session_stats.total_cost:>0.10

# Find slow tool calls (> 5s)
service:emonk event:tool_call @latency_ms:>5000
```

### ✅ Cost Tracking & Optimization
**Source:** FinOps for LLMs

- **Per-Session Costs:** See exactly how much each user session cost
- **Model Distribution:** Track % of spend on lead vs worker model
- **Tool Cost Attribution:** Identify which tools trigger expensive LLM calls

**Real-World Impact:**
```
Before cost tracking:
- Monthly LLM spend: $450
- No visibility into drivers

After observability:
- Discovered: 80% of cost from 10 "research" sessions
- Optimization: Use worker model for research, save 60%
- New monthly spend: $180 (60% reduction)
```

### ✅ Error Analysis
**Source:** Goose error handling + Langfuse

- **Recovery Rate Metrics:** See % of errors that self-correct
- **Failure Patterns:** Identify tools with high error rates
- **Root Cause Analysis:** Trace errors back to specific LLM turns

---

## Cons

### ❌ Additional Latency
**Source:** Observability overhead benchmarks

- **Langfuse API Calls:** 20-50ms per trace/generation/span
- **JSON Serialization:** 5-15ms per log event
- **Network Overhead:** Langfuse runs remotely (unless self-hosted)

**Real-World Impact:**
```
Without observability: 10-turn session = 45 seconds
With observability: 10-turn session = 48 seconds (+6%)

Breakdown:
- Structured logging: +1s total (100ms per turn)
- Langfuse tracing: +2s total (200ms per turn)
```

**Mitigation:** Async logging, batch Langfuse uploads (flush() after session).

### ❌ Privacy & Security Concerns
**Source:** Data governance requirements

- **Prompt Logging:** Full prompts/responses sent to Langfuse (may contain PII)
- **Parameter Logging:** Tool parameters might include sensitive data
- **Third-Party Risk:** Langfuse cloud = data leaves your infrastructure

**Regulations:**
- GDPR: Must anonymize PII before logging
- HIPAA: Can't log PHI to third-party without BAA
- SOC 2: Requires audit trail of who accessed logs

**Mitigation:** 
- Self-host Langfuse (open source)
- Redact sensitive fields before logging
- Use structured logging only (skip Langfuse for sensitive data)

### ❌ Storage Costs
**Source:** Langfuse pricing, log retention analysis

- **Langfuse Cloud:** $49/month for 50K events (traces + generations + spans)
- **Self-Hosted:** Infrastructure costs (Docker/Kubernetes + PostgreSQL)
- **Log Retention:** Structured logs can grow to GB/day at high volume

**Real-World Costs:**
```
100 sessions/day × 10 turns each = 1,000 generations/day
Each generation = 1 trace + 1 generation + 3 spans avg = 5 events
Total: 5,000 events/day = 150K events/month

Langfuse Cloud: $49/month (barely fits in 50K tier)
Self-Hosted: $20-50/month (DigitalOcean + PostgreSQL)
```

### ❌ Debugging Complexity
**Source:** Distributed tracing learning curve

- **Trace ID Management:** Must thread trace IDs through all function calls
- **Async Challenges:** Parent-child spans in asyncio are tricky
- **Multiple Sources:** Logs in CloudWatch + traces in Langfuse = context switching

---

## When to Use This Approach

### ✅ Use Full Observability When:

1. **Production System:** Deployed agent with real users
2. **Complex Workflows:** Multi-step orchestration, parallel tools
3. **Cost Management:** Need to track and optimize LLM spend
4. **SLA Requirements:** Must meet latency/reliability targets
5. **Team Debugging:** Multiple developers need to investigate issues

### ❌ Avoid Full Observability When:

1. **Prototype/MVP:** Simple single-user testing
2. **Sensitive Data:** Can't log prompts/parameters due to compliance
3. **Ultra-Low Latency:** Every millisecond matters (HFT, gaming)
4. **Cost Sensitive:** Can't afford $50/month observability platform
5. **Privacy First:** Agent processes highly confidential data

---

## Alternative Approaches

### Alternative 1: Print Debugging

```python
# Simple print statements
print(f"[{datetime.now()}] Calling tool: {tool_name}")
result = await execute_tool(tool_name, params)
print(f"[{datetime.now()}] Tool result: {result}")
```

**Pros:** Zero cost, no dependencies, instant feedback  
**Cons:** Not machine-readable, no persistence, clutters output

### Alternative 2: File-Based Logging

```python
# Log to file with rotation
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler("agent.log", maxBytes=10*1024*1024, backupCount=5)
logger.addHandler(handler)
logger.info(f"Tool call: {tool_name}, result: {result}")
```

**Pros:** Free, persistent, simple  
**Cons:** No visual timeline, manual analysis, no cost tracking

### Alternative 3: Cloud Logging (Google Cloud Logging, AWS CloudWatch)

```python
# GCP Cloud Logging
from google.cloud import logging as gcp_logging

client = gcp_logging.Client()
logger = client.logger("agent")

logger.log_struct({
    "event": "tool_call",
    "tool_name": tool_name,
    "success": True
}, severity="INFO")
```

**Pros:** Managed, integrated with cloud infra, queryable  
**Cons:** Cloud vendor lock-in, no LLM-specific features, complex pricing

---

## Implementation Roadmap for emonk

### Week 1: Structured Logging
```python
# Day 1-2: Configure structlog with JSON output
# Day 3: TraceContext class with span management
# Day 4: ObservabilityManager with session stats
# Day 5: Integration with agent loop
```

### Week 2: Cost Tracking
```python
# Day 1: Model pricing configuration
# Day 2: Cost calculation per LLM call
# Day 3: Per-tool statistics
# Day 4-5: Session summary and analytics
```

### Week 3: Langfuse Integration
```python
# Day 1: Langfuse account setup (cloud or self-hosted)
# Day 2: LangfuseObserver class
# Day 3: Trace/generation/span logging
# Day 4: Error level mapping
# Day 5: Testing and validation
```

### Week 4: Dashboards & Alerts
```python
# Day 1-2: Build cost dashboard (Langfuse UI or custom)
# Day 3: Set up alerts (high cost, high errors)
# Day 4: Documentation and runbook
# Day 5: Team training
```

---

## Configuration Examples

### Development (Minimal)
```python
# Just structured logs, no Langfuse
observability = ObservabilityManager()
# Logs to stdout in JSON format
# Cost: $0
```

### Production (Full Stack)
```python
# Structured logs + Langfuse + cost tracking
observability = ObservabilityManager()
langfuse_observer = LangfuseObserver()

# Configure Langfuse
LANGFUSE_PUBLIC_KEY=xxx
LANGFUSE_SECRET_KEY=xxx
LANGFUSE_HOST=https://cloud.langfuse.com

# Cost: $49/month (Langfuse) + $20/month (log storage)
```

### High-Compliance (Self-Hosted)
```python
# Self-hosted Langfuse + on-prem logs
observability = ObservabilityManager()
langfuse_observer = LangfuseObserver()

# Self-hosted Langfuse
LANGFUSE_HOST=https://langfuse.internal.company.com

# Redact sensitive fields
def redact_pii(data):
    # Remove emails, phone numbers, etc.
    pass

# Cost: $30/month (infrastructure)
```

---

## Comparison Matrix

| Dimension | Structured Logs + Langfuse | Print Debugging | File Logging | Cloud Logging |
|-----------|---------------------------|----------------|--------------|---------------|
| **Cost Tracking** | ✅ Built-in | ❌ None | ❌ Manual | ⚠️ Custom |
| **Visual Timeline** | ✅ Langfuse UI | ❌ None | ❌ None | ⚠️ Limited |
| **Queryability** | ⭐⭐⭐⭐⭐ Rich | ❌ None | ⭐⭐ grep | ⭐⭐⭐⭐ SQL |
| **Latency Overhead** | ⭐⭐⭐ 6% | ⭐⭐⭐⭐⭐ 0% | ⭐⭐⭐⭐ 2% | ⭐⭐⭐ 5% |
| **Setup Complexity** | ⭐⭐⭐ Medium | ⭐⭐⭐⭐⭐ None | ⭐⭐⭐⭐ Simple | ⭐⭐ Complex |
| **Monthly Cost** | ⭐⭐ $50-100 | ⭐⭐⭐⭐⭐ Free | ⭐⭐⭐⭐⭐ Free | ⭐⭐⭐ $10-50 |
| **Privacy** | ⚠️ Third-party | ✅ Local | ✅ Local | ⚠️ Cloud |

---

## Real-World Example: Goose Error Recovery

From Goose blog "How goose Catches AI Errors with Langfuse":

**Scenario:** User asks "Create a Python script that fetches weather data"

**Without Observability:**
```
User: "Why did it fail?"
Developer: *looks at terminal output*
Developer: "I don't know, the logs are confusing"
```

**With Langfuse:**
```
Developer opens Langfuse → sees timeline:

Turn 1: LLM generates code
  └─ Tool: create_file("weather.py", content="...")
  
Turn 2: LLM tries to test code
  └─ Tool: execute_shell("python weather.py") → ERROR: Missing API key
  
Turn 3: LLM self-corrects
  └─ Tool: read_file("weather.py")
  └─ Tool: update_file("weather.py", content="... with env var ...")
  
Turn 4: LLM retests
  └─ Tool: execute_shell("python weather.py") → SUCCESS

Developer: "Ah, it recovered automatically after detecting missing API key"
```

**Analysis from Timeline:**
- Total time: 12.4 seconds
- Total cost: $0.0089
- Errors: 1 (recovered automatically)
- Recovery time: 6.2 seconds (turns 2-4)

---

## Resources

- **Goose + Langfuse Blog:** https://block.github.io/goose/blog/2025/03/18/goose-langfuse
- **Langfuse Documentation:** https://langfuse.com/docs
- **Langfuse Python SDK:** https://github.com/langfuse/langfuse-python
- **Structlog Documentation:** https://www.structlog.org/
- **OpenTelemetry:** https://opentelemetry.io/ (alternative tracing standard)
- **LangSmith:** https://www.langchain.com/langsmith (alternative to Langfuse)
