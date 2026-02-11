# Phase 4: Production Hardening + Jr Engineer Agent

**Goal:** Production-grade reliability features + demonstrate framework reusability with second agent type

**Value Delivered:** Battle-tested marketing agent in production. Second agent (jr software engineer) proves framework works for different domains. Both agents running reliably on GCP.

**Prerequisites:** Phase 1, 2, and 3 must be complete (marketing agent deployed to Cloud Run)

**Status:** Ready for monkeymode execution after Phase 3

---

## Strategic Context

This phase focuses on two critical objectives:
1. **Production Hardening** - Make the system reliable, observable, and cost-effective
2. **Framework Validation** - Build a second agent type (jr software engineer) to prove framework reusability

The production hardening features ensure the marketing agent can run reliably 24/7 with minimal manual intervention. The jr engineer agent validates that the framework is truly reusable across different domains.

---

## Components to Build

### 1. Error Recovery & Reliability

#### A. Error Classification System

**Key Insight:** Not all errors are equal. Some can be self-corrected by the LLM, others require infrastructure retry, and some are unrecoverable.

**Error Types:**

```python
# emonk/core/errors.py

class AgentError(Exception):
    """Errors the agent can self-correct (LLM retries)"""
    pass

class InfraError(Exception):
    """Infrastructure failures (network, API limits)"""
    pass

class ConfigError(Exception):
    """Configuration errors (unrecoverable without human intervention)"""
    pass
```

**Examples:**
- **AgentError**: Malformed JSON output, wrong skill arguments, incomplete reasoning
- **InfraError**: Network timeout, rate limit, API unavailable
- **ConfigError**: Missing credentials, invalid config, skill not found

#### B. Error Recovery Loop

**Implementation:**

```python
# emonk/core/error_recovery.py

import asyncio
from typing import Any, Dict

async def execute_with_recovery(
    agent,
    task: Dict[str, Any],
    max_retries: int = 3
) -> Any:
    """Execute task with automatic error recovery"""
    
    for attempt in range(max_retries):
        try:
            return await agent.execute(task)
        
        except AgentError as e:
            # LLM self-correction
            logger.warning(f"Agent error (attempt {attempt + 1}): {e}")
            
            # Add error context to help LLM fix it
            error_context = f"""Previous attempt failed with error:
            {str(e)}
            
            Please correct this error and try again."""
            
            task["context"].append({
                "role": "system",
                "content": error_context
            })
            
            # Retry with additional context
            continue
        
        except InfraError as e:
            # Exponential backoff for infrastructure issues
            backoff_seconds = 2 ** attempt
            logger.warning(
                f"Infrastructure error (attempt {attempt + 1}): {e}. "
                f"Retrying in {backoff_seconds}s..."
            )
            await asyncio.sleep(backoff_seconds)
            continue
        
        except ConfigError as e:
            # Unrecoverable - alert and fail fast
            logger.error(f"Configuration error: {e}")
            await alert_admin(
                level="critical",
                message=f"Agent configuration error: {e}"
            )
            raise
        
        except Exception as e:
            # Unknown error - log and alert
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await alert_admin(
                level="error",
                message=f"Unexpected agent error: {e}"
            )
            raise
    
    # All retries exhausted
    raise AgentError(
        f"Task failed after {max_retries} attempts. "
        f"Last error: {str(e)}"
    )
```

#### C. Retry Strategies

**Per-Component Strategies:**

| Component | Strategy | Retries | Backoff |
|-----------|----------|---------|---------|
| Cron Jobs | Exponential backoff | 3 | 1s, 2s, 4s |
| Skill Execution | Immediate retry once | 1 | None |
| LLM Calls | Exponential backoff | 5 | 1s, 2s, 4s, 8s, 16s |
| Web Search | Cache fallback | 2 | 2s, 4s |
| API Calls | Exponential backoff | 3 | 1s, 2s, 4s |

**Implementation:**

```python
# emonk/core/retry.py

import asyncio
from typing import Callable, TypeVar

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential: bool = True,
    on_retry: Callable[[int, Exception], None] = None
) -> T:
    """Retry function with exponential backoff"""
    
    delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                # Last attempt failed
                raise
            
            # Call optional retry callback
            if on_retry:
                on_retry(attempt + 1, e)
            
            # Wait before retry
            await asyncio.sleep(delay)
            
            # Increase delay for next attempt
            if exponential:
                delay *= 2
```

#### D. Circuit Breaker Pattern

**Purpose:** Prevent cascading failures from external services

**Implementation:**

```python
# emonk/core/circuit_breaker.py

import time
from typing import Callable, TypeVar
from enum import Enum

T = TypeVar('T')

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit tripped, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    """Prevent cascading failures from external services"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        name: str = "unnamed"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call function with circuit breaker protection"""
        
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if time.time() - self.last_failure_time > self.timeout:
                logger.info(f"Circuit breaker '{self.name}': Attempting recovery")
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service unavailable."
                )
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset if in half-open state
            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit breaker '{self.name}': Recovered")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            # Failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.warning(
                f"Circuit breaker '{self.name}': Failure {self.failure_count}/{self.failure_threshold}"
            )
            
            # Trip circuit if threshold reached
            if self.failure_count >= self.failure_threshold:
                logger.error(f"Circuit breaker '{self.name}': OPEN (too many failures)")
                self.state = CircuitState.OPEN
            
            raise

# Usage
perplexity_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60,
    name="perplexity-api"
)

result = await perplexity_breaker.call(search_web, query="AI news")
```

---

### 2. Session Management & Context Compression

#### A. Persistent Sessions

**Storage:** Cloud Firestore or Cloud SQL

**Session Schema:**

```python
# emonk/core/session.py

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict

@dataclass
class Session:
    session_id: str
    user_id: str
    created_at: datetime
    last_active: datetime
    message_count: int
    token_count: int
    context_compressed: bool
    messages: List[Dict[str, str]]
    metadata: Dict[str, any]
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "message_count": self.message_count,
            "token_count": self.token_count,
            "context_compressed": self.context_compressed,
            "messages": self.messages,
            "metadata": self.metadata
        }
```

**Firestore Implementation:**

```python
# emonk/storage/firestore_sessions.py

from google.cloud import firestore
from emonk.core.session import Session

class FirestoreSessionStore:
    """Store sessions in Firestore"""
    
    def __init__(self, project_id: str):
        self.db = firestore.Client(project=project_id)
        self.collection = self.db.collection("sessions")
    
    async def save(self, session: Session):
        """Save session to Firestore"""
        doc_ref = self.collection.document(session.session_id)
        doc_ref.set(session.to_dict())
    
    async def load(self, session_id: str) -> Session:
        """Load session from Firestore"""
        doc_ref = self.collection.document(session_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise KeyError(f"Session {session_id} not found")
        
        return Session.from_dict(doc.to_dict())
    
    async def list_user_sessions(self, user_id: str) -> List[Session]:
        """List all sessions for user"""
        query = self.collection.where("user_id", "==", user_id)
        docs = query.stream()
        
        return [Session.from_dict(doc.to_dict()) for doc in docs]
```

#### B. Automatic Context Compression

**Trigger:** When conversation exceeds 50K tokens

**Strategy:** LLM summarization

**Implementation:**

```python
# emonk/core/context_compression.py

async def compress_context(session: Session, llm_client) -> Session:
    """Compress session context using LLM summarization"""
    
    logger.info(f"Compressing context for session {session.session_id}")
    
    # Extract key information using LLM
    summary_prompt = """Summarize this conversation, preserving:
    1. User preferences and requirements
    2. Important decisions made
    3. Action items and their current status
    4. Key facts and context mentioned
    5. Unresolved questions or issues
    
    Omit:
    - Casual chat and pleasantries
    - Redundant information
    - Detailed technical discussions that reached conclusion
    
    Format as a concise summary (max 500 words).
    """
    
    # Use only messages except last 10
    messages_to_compress = session.messages[:-10]
    
    summary = await llm_client.generate(
        prompt=summary_prompt,
        context=messages_to_compress,
        model="gemini-2.0-pro"  # Use better model for summarization
    )
    
    # Replace old messages with summary
    session.messages = [
        {
            "role": "system",
            "content": f"Previous conversation summary:\n\n{summary}"
        },
        *session.messages[-10:]  # Keep last 10 messages
    ]
    
    # Update session metadata
    session.context_compressed = True
    session.token_count = count_tokens(session.messages)
    
    logger.info(
        f"Context compressed for session {session.session_id}. "
        f"New token count: {session.token_count}"
    )
    
    return session

# Automatic compression
async def process_message(session: Session, message: str):
    """Process message with automatic context compression"""
    
    # Check if compression needed
    if session.token_count > 50000 and not session.context_compressed:
        session = await compress_context(session, llm_client)
        await session_store.save(session)
    
    # Process message normally
    response = await agent.process_message(message, session)
    
    return response
```

---

### 3. Multi-Model Routing (Cost Optimization)

#### A. Lead/Worker Pattern

**Models:**
- **Lead Model** (Gemini 2.0 Pro): Planning and complex reasoning
- **Worker Model** (Gemini 2.0 Flash): Simple execution tasks
- **Fallback Model** (Gemini 1.5 Pro): When Flash fails

**Routing Logic:**

```python
# emonk/core/multi_model_router.py

from typing import Dict, Any
from enum import Enum

class TaskComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"

class MultiModelRouter:
    """Route tasks to appropriate model based on complexity"""
    
    def __init__(self):
        self.flash = LLMClient(model="gemini-2.0-flash")
        self.pro = LLMClient(model="gemini-2.0-pro")
        self.fallback = LLMClient(model="gemini-1.5-pro")
    
    async def route(self, task: Dict[str, Any]) -> Any:
        """Route task to appropriate model"""
        
        # Assess complexity
        complexity = self.assess_complexity(task)
        
        if complexity == TaskComplexity.SIMPLE:
            # Use Flash (cheap and fast)
            try:
                return await self.flash.generate(task)
            except Exception as e:
                logger.warning(f"Flash failed, falling back to Pro: {e}")
                return await self.pro.generate(task)
        
        elif complexity == TaskComplexity.MODERATE:
            # Try Flash first with timeout, fallback to Pro
            try:
                return await asyncio.wait_for(
                    self.flash.generate(task),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                logger.info("Flash timeout, using Pro")
                return await self.pro.generate(task)
        
        else:
            # Use Pro (best quality)
            return await self.pro.generate(task)
    
    def assess_complexity(self, task: Dict[str, Any]) -> TaskComplexity:
        """Assess task complexity using heuristics"""
        
        # Heuristics:
        # 1. Explicit complexity flag
        if "complexity" in task:
            return TaskComplexity(task["complexity"])
        
        # 2. Task type
        task_type = task.get("type", "")
        if task_type in ["skill_call", "factual_qa", "format_response"]:
            return TaskComplexity.SIMPLE
        
        # 3. Context length
        context_length = task.get("context_length", 0)
        if context_length > 20000:
            return TaskComplexity.COMPLEX
        elif context_length > 10000:
            return TaskComplexity.MODERATE
        
        # 4. Reasoning required
        if task.get("requires_reasoning", False):
            return TaskComplexity.COMPLEX
        
        # 5. Multi-step task
        if task.get("steps", []):
            return TaskComplexity.MODERATE
        
        # Default to simple
        return TaskComplexity.SIMPLE
```

#### B. Cost Tracking

**Implementation:**

```python
# emonk/core/cost_tracker.py

from google.cloud import firestore
from datetime import datetime

class CostTracker:
    """Track LLM costs per session/user"""
    
    def __init__(self, project_id: str):
        self.db = firestore.Client(project=project_id)
        self.collection = self.db.collection("usage_logs")
    
    # Model pricing (per 1M tokens)
    PRICING = {
        "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
        "gemini-2.0-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00}
    }
    
    async def log_usage(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ):
        """Log LLM usage and cost"""
        
        # Calculate cost
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        # Save to Firestore
        doc = {
            "session_id": session_id,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": total_cost,
            "timestamp": datetime.utcnow()
        }
        
        self.collection.add(doc)
        
        logger.info(
            f"Logged usage: {model}, "
            f"{input_tokens} in / {output_tokens} out, "
            f"${total_cost:.4f}"
        )
    
    async def get_user_costs(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, float]:
        """Get user's LLM costs for period"""
        
        query = (
            self.collection
            .where("user_id", "==", user_id)
            .where("timestamp", ">=", start_date)
            .where("timestamp", "<=", end_date)
        )
        
        docs = query.stream()
        
        total_cost = 0
        model_costs = {}
        
        for doc in docs:
            data = doc.to_dict()
            cost = data["total_cost_usd"]
            model = data["model"]
            
            total_cost += cost
            model_costs[model] = model_costs.get(model, 0) + cost
        
        return {
            "total_cost_usd": total_cost,
            "model_costs": model_costs,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }
```

---

### 4. Observability & Monitoring

#### A. Structured Logging

**Implementation:**

```python
# emonk/utils/logging.py

import structlog
import logging

def setup_logging(level: str = "INFO"):
    """Setup structured logging"""
    
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
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper())
    )

# Usage
logger = structlog.get_logger()

logger.info(
    "skill_executed",
    trace_id="abc-123",
    skill="post_to_x",
    duration_ms=234,
    success=True,
    tweet_id="1234567890"
)

# Output (JSON):
# {
#   "event": "skill_executed",
#   "level": "info",
#   "timestamp": "2026-02-11T14:30:00.123Z",
#   "trace_id": "abc-123",
#   "skill": "post_to_x",
#   "duration_ms": 234,
#   "success": true,
#   "tweet_id": "1234567890"
# }
```

#### B. Trace IDs

**Implementation:**

```python
# emonk/utils/tracing.py

import uuid
from contextlib import contextmanager

# Thread-local storage for trace ID
import threading
_trace_context = threading.local()

def generate_trace_id() -> str:
    """Generate unique trace ID"""
    return str(uuid.uuid4())

def set_trace_id(trace_id: str):
    """Set trace ID for current request"""
    _trace_context.trace_id = trace_id

def get_trace_id() -> str:
    """Get trace ID for current request"""
    return getattr(_trace_context, "trace_id", None)

@contextmanager
def trace_context(trace_id: str = None):
    """Context manager for trace ID"""
    if trace_id is None:
        trace_id = generate_trace_id()
    
    set_trace_id(trace_id)
    try:
        yield trace_id
    finally:
        set_trace_id(None)

# Usage
async def handle_request(request):
    trace_id = request.headers.get("X-Trace-ID", generate_trace_id())
    
    with trace_context(trace_id):
        logger.info("request_received", method=request.method, path=request.path)
        response = await process_request(request)
        logger.info("request_completed", status_code=response.status_code)
        return response
```

#### C. Metrics Dashboard

**Key Metrics:**

1. **Request Metrics**
   - Request count (requests/second)
   - Request latency (P50, P95, P99)
   - Error rate (%)

2. **Business Metrics**
   - LLM costs (per user, per model)
   - Skill execution time
   - Job success rate (cron jobs)
   - Campaign completion rate

3. **Infrastructure Metrics**
   - Container instance count
   - Memory utilization
   - CPU utilization
   - Network egress

**Implementation (Cloud Monitoring):**

```python
# emonk/utils/metrics.py

from google.cloud import monitoring_v3
import time

class MetricsClient:
    """Report custom metrics to Cloud Monitoring"""
    
    def __init__(self, project_id: str):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"
    
    def record_metric(
        self,
        metric_type: str,
        value: float,
        labels: dict = None
    ):
        """Record custom metric"""
        
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/{metric_type}"
        
        if labels:
            series.metric.labels.update(labels)
        
        series.resource.type = "cloud_run_revision"
        
        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10**9)
        
        interval = monitoring_v3.TimeInterval(
            {"end_time": {"seconds": seconds, "nanos": nanos}}
        )
        
        point = monitoring_v3.Point({
            "interval": interval,
            "value": {"double_value": value}
        })
        
        series.points = [point]
        
        self.client.create_time_series(
            name=self.project_name,
            time_series=[series]
        )

# Usage
metrics = MetricsClient(project_id="my-project")

metrics.record_metric(
    metric_type="agent/skill_duration",
    value=234.5,
    labels={"skill": "post_to_x", "success": "true"}
)
```

---

### 5. Permission & Approval System

#### A. Risk-Based Approvals

**Implementation:**

```python
# emonk/core/permission.py

from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class PermissionSystem:
    """Request approval for high-risk operations"""
    
    # Risk assessment rules
    RISK_RULES = {
        # High risk: Public posting, data deletion
        "high": [
            "post_to_x",
            "post_to_linkedin",
            "post_to_instagram",
            "delete_file",
            "delete_campaign"
        ],
        # Medium risk: Scheduling, token updates
        "medium": [
            "schedule_job",
            "update_token",
            "create_campaign"
        ]
        # Low risk: Read operations (default)
    }
    
    async def check_permission(
        self,
        user_id: str,
        skill: str,
        parameters: dict
    ) -> bool:
        """Check if user has permission for skill"""
        
        risk = self.assess_risk(skill, parameters)
        
        if risk == RiskLevel.LOW:
            # Auto-approve low-risk operations
            return True
        
        elif risk == RiskLevel.MEDIUM:
            # Ask for confirmation
            approved = await self.request_approval(
                user_id=user_id,
                message=f"Approve {skill} with parameters {parameters}?",
                buttons=["Approve", "Reject"]
            )
            return approved
        
        else:
            # High risk: Require explicit approval with preview
            approved = await self.request_detailed_approval(
                user_id=user_id,
                skill=skill,
                parameters=parameters
            )
            return approved
    
    def assess_risk(self, skill: str, parameters: dict) -> RiskLevel:
        """Assess risk level of operation"""
        
        # Check against risk rules
        for risk_level, skills in self.RISK_RULES.items():
            if skill in skills:
                return RiskLevel(risk_level)
        
        # Default to low risk
        return RiskLevel.LOW
```

#### B. Approval UI (Google Chat Cards)

**Implementation:**

```python
# emonk/integrations/google_chat.py (enhanced)

async def request_approval(
    self,
    user_id: str,
    message: str,
    buttons: list[str]
) -> bool:
    """Send approval request via Google Chat"""
    
    # Create interactive card
    card = {
        "cardsV2": [{
            "cardId": "approval-card",
            "card": {
                "header": {
                    "title": "Approval Required",
                    "subtitle": "Please review and approve"
                },
                "sections": [{
                    "widgets": [
                        {
                            "textParagraph": {
                                "text": message
                            }
                        },
                        {
                            "buttonList": {
                                "buttons": [
                                    {
                                        "text": "Approve",
                                        "onClick": {
                                            "action": {
                                                "actionMethodName": "approve",
                                                "parameters": [{
                                                    "key": "approved",
                                                    "value": "true"
                                                }]
                                            }
                                        }
                                    },
                                    {
                                        "text": "Reject",
                                        "onClick": {
                                            "action": {
                                                "actionMethodName": "reject",
                                                "parameters": [{
                                                    "key": "approved",
                                                    "value": "false"
                                                }]
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }]
            }
        }]
    }
    
    # Send card
    response = await self.chat_api.send_message(
        space=user_id,
        message=card
    )
    
    # Wait for user response (with timeout)
    approval = await self.wait_for_response(
        message_id=response["name"],
        timeout=300  # 5 minutes
    )
    
    return approval
```

---

### 6. Jr Software Engineer Agent (Second Agent Type)

**Goal:** Demonstrate framework reusability by building a different agent type

**Agent Configuration:**

```yaml
# jr-engineer-agent.yaml
agent:
  name: jr-engineer-agent
  type: software-engineer
  llm:
    model: gemini-2.0-pro  # More reasoning needed for code
    fallback: gemini-1.5-pro
  memory:
    backend: gcs
    bucket: emonk-jr-engineer-memory
  integrations:
    - google_chat
    - github
  skills_dir: ./skills/
  system_prompt: |
    You are a junior software engineer assistant.
    Focus on code quality, testing, and documentation.
    Always suggest improvements, not just fixes.
    Follow best practices and established patterns.
```

#### A. Code Analysis Skills (`skills/code/`)

**1. Read Codebase**
```python
# skills/code/read_codebase.py
def analyze_codebase(path: str) -> dict:
    """Analyze codebase structure"""
    # Use tree, cloc, or similar tools
    # Return file counts, LOC, languages, etc.
```

**2. Find Bugs**
```python
# skills/code/find_bugs.py
def find_bugs(file_path: str) -> list:
    """Static analysis for bug detection"""
    # Use pylint, mypy, or similar
    # Return list of potential issues
```

**3. Suggest Refactoring**
```python
# skills/code/suggest_refactoring.py
def suggest_refactoring(file_path: str) -> list:
    """Suggest code quality improvements"""
    # Analyze complexity, duplication
    # Return refactoring suggestions
```

**4. Explain Code**
```python
# skills/code/explain_code.py
def explain_code(code: str) -> str:
    """Generate natural language explanation"""
    # Use LLM to explain code
    # Return plain English description
```

#### B. Development Skills (`skills/dev/`)

**1. Write Tests**
```python
# skills/dev/write_tests.py
def generate_tests(function_code: str) -> str:
    """Generate unit tests for function"""
    # Analyze function signature
    # Generate pytest tests
    # Return test code
```

**2. Write Code**
```python
# skills/dev/write_code.py
def generate_code(spec: str) -> str:
    """Generate code from specification"""
    # Use LLM to generate code
    # Follow project conventions
    # Return code
```

**3. Debug Code**
```python
# skills/dev/debug_code.py
def debug_code(code: str, error: str) -> str:
    """Debug failing code"""
    # Analyze error message
    # Suggest fixes
    # Return corrected code
```

**4. Review PR**
```python
# skills/dev/review_pr.py
def review_pr(pr_number: int) -> dict:
    """Pull request code review"""
    # Fetch PR diff
    # Analyze changes
    # Generate review comments
    # Return review
```

#### C. Git & GitHub Skills (`skills/git/`)

**1. Create Branch**
```bash
# skills/git/create_branch.sh
gh api repos/owner/repo/git/refs -f ref="refs/heads/feature-branch" -f sha="$BASE_SHA"
```

**2. Commit Changes**
```bash
# skills/git/commit_changes.sh
git add .
git commit -m "feat: add new feature"
git push origin feature-branch
```

**3. Create PR**
```bash
# skills/git/create_pr.sh
gh pr create --title "Feature: New feature" --body "Description"
```

**4. Merge PR**
```bash
# skills/git/merge_pr.sh
gh pr merge $PR_NUMBER --squash
```

#### D. Documentation Skills (`skills/docs/`)

**1. Write README**
```python
# skills/docs/write_readme.py
def generate_readme(project_path: str) -> str:
    """Generate README from code"""
    # Analyze project structure
    # Generate README sections
    # Return markdown
```

**2. Write Docstrings**
```python
# skills/docs/write_docstrings.py
def add_docstrings(code: str) -> str:
    """Add docstrings to functions"""
    # Parse code
    # Generate docstrings
    # Return updated code
```

**3. Generate API Docs**
```python
# skills/docs/generate_api_docs.py
def generate_api_docs(api_spec: str) -> str:
    """Generate API documentation"""
    # Parse OpenAPI spec
    # Generate docs
    # Return markdown
```

#### Example Workflow

```
User: "Review PR #42 and suggest improvements"

Agent:
1. 📖 Reading PR #42 from GitHub...
   - Files changed: 3 (app.py, test_app.py, README.md)
   - Lines: +89, -12
   - Author: john-doe
   
2. 🔍 Analyzing code changes...
   - Running static analysis...
   - Checking test coverage...
   - Reviewing documentation...
   
3. ⚠️ Found 2 potential bugs:
   - Line 45 in app.py: Potential null pointer exception
   - Line 78 in app.py: SQL injection risk (user input not sanitized)
   
4. 📝 Found missing tests:
   - No test for new API endpoint /api/users
   - Edge case not covered: empty request body
   
5. 📚 Documentation needs update:
   - CHANGELOG.md not updated
   - New API endpoint not documented in README.md
   
6. ✍️ Posting review to PR #42...
   
✅ Review posted! Found 2 bugs, 2 missing tests, 2 docs updates needed.

Would you like me to:
- Fix the bugs and push a commit?
- Write the missing tests?
- Update the documentation?
```

---

## Success Criteria

- [ ] Error recovery handles LLM failures gracefully
- [ ] Session management prevents context overflow
- [ ] Multi-model routing reduces costs by 30%+
- [ ] Observability dashboard shows real-time metrics
- [ ] Permission system prevents accidental public posts
- [ ] Jr Engineer agent successfully reviews PRs and writes tests
- [ ] Both agents (marketing + engineer) running in production
- [ ] Circuit breakers prevent cascading failures
- [ ] Cost tracking accurate within 5%
- [ ] All metrics visible in Cloud Monitoring

---

## Testing Strategy

### Unit Tests
- `test_error_recovery.py` - Error classification and retry logic
- `test_session_management.py` - Session compression
- `test_multi_model_router.py` - Model routing logic
- `test_permission.py` - Risk assessment
- `test_jr_engineer_skills.py` - All jr engineer skills

### Integration Tests
- End-to-end error recovery flow
- Session compression with real LLM
- Cost tracking accuracy
- Permission approval workflow

### Load Tests
- 100 concurrent requests
- Measure latency under load
- Verify auto-scaling works
- Check circuit breaker behavior

---

## Deployment Checklist

- [ ] Update emonk-framework with new components
- [ ] Deploy updated marketing agent
- [ ] Deploy new jr engineer agent
- [ ] Set up Firestore for sessions
- [ ] Configure Cloud Monitoring dashboards
- [ ] Set up alerting rules
- [ ] Document new features
- [ ] Train team on new capabilities

---

## References

- [Goose Error Recovery](../ref/09_goose_error_recovery.md) - Error classification
- [Goose Multi-Model Routing](../ref/10_goose_multi_model_routing.md) - Lead/worker pattern
- [Goose Session Management](../ref/12_goose_session_management.md) - Context compression
- [Goose Observability](../ref/14_goose_observability.md) - Logging and tracing

---

## Next Phase

After Phase 4 is complete:
- **Phase 5 (Optional):** Advanced features like recipe system, web UI, and performance optimizations
- Focus: Enterprise-grade features and nice-to-haves for power users
