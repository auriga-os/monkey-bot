# 10 - Multi-Model LLM Routing (Goose Lead/Worker Pattern)

**Source:** Goose (Block/Square) - Open Source AI Agent  
**Blog Post:** "Treating LLMs Like Tools in a Toolbox: A Multi-Model Approach"  
**Implementation:** Session-based model switching with failure detection

---

## Overview

Goose implements a "lead/worker" multi-model routing strategy to optimize cost and performance:

1. **Lead Model** (expensive, powerful): Used for initial planning and complex reasoning
2. **Worker Model** (cheap, fast): Used for routine execution after plan is established
3. **Automatic Fallback**: Detects task failures and switches back to lead model

**Key Result:** Goose reports **60-80% cost reduction** on routine tasks while maintaining reliability through intelligent fallback.

---

## Core Pattern

### Environment Configuration

```bash
# Goose lead/worker configuration
GOOSE_LEAD_MODEL=claude-4-opus              # Expensive reasoning model
GOOSE_MODEL=gpt-4o-mini                     # Cheap worker model
GOOSE_LEAD_TURNS=3                          # Use lead for first 3 turns
GOOSE_LEAD_FAILURE_THRESHOLD=2              # Fallback after 2 failures
GOOSE_LEAD_FALLBACK_TURNS=2                 # Stay on lead for 2 turns after fallback
```

### Python Implementation for emonk

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import os

class ModelTier(Enum):
    """Model capability tiers"""
    LEAD = "lead"      # Strong reasoning (Gemini Pro, Claude Opus)
    WORKER = "worker"  # Fast & cheap (Gemini Flash)

@dataclass
class ModelConfig:
    """Configuration for a model"""
    name: str
    provider: str
    tier: ModelTier
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    context_window: int
    
class LLMRouter:
    """
    Goose-inspired multi-model routing.
    Optimizes cost while maintaining reliability.
    """
    
    def __init__(self):
        # Model configurations (example: Vertex AI Gemini)
        self.models = {
            "lead": ModelConfig(
                name="gemini-2.0-pro-exp-0205",
                provider="vertex-ai",
                tier=ModelTier.LEAD,
                cost_per_1k_input_tokens=0.00070,   # $0.70 per 1M tokens
                cost_per_1k_output_tokens=0.00210,  # $2.10 per 1M tokens
                context_window=1_000_000
            ),
            "worker": ModelConfig(
                name="gemini-2.0-flash-exp",
                provider="vertex-ai",
                tier=ModelTier.WORKER,
                cost_per_1k_input_tokens=0.00004,   # $0.04 per 1M tokens (95% cheaper)
                cost_per_1k_output_tokens=0.00016,  # $0.16 per 1M tokens
                context_window=1_000_000
            )
        }
        
        # Routing configuration (from env vars)
        self.lead_turns = int(os.getenv("EMONK_LEAD_TURNS", "3"))
        self.failure_threshold = int(os.getenv("EMONK_FAILURE_THRESHOLD", "2"))
        self.fallback_turns = int(os.getenv("EMONK_FALLBACK_TURNS", "2"))
        
        # Session state
        self.current_turn = 0
        self.failure_count = 0
        self.in_fallback = False
        self.fallback_turns_remaining = 0
        
        # Usage tracking
        self.usage_stats = {
            "lead_input_tokens": 0,
            "lead_output_tokens": 0,
            "worker_input_tokens": 0,
            "worker_output_tokens": 0
        }
    
    def select_model(self, 
                     task_complexity: Optional[str] = None,
                     force_lead: bool = False) -> ModelConfig:
        """
        Select appropriate model based on session state.
        
        Args:
            task_complexity: "simple"|"medium"|"complex" (optional override)
            force_lead: Force lead model usage
        
        Returns:
            ModelConfig for selected model
        """
        # Manual override: force lead
        if force_lead or task_complexity == "complex":
            log.info("Using lead model (forced)", extra={"reason": "manual_override"})
            return self.models["lead"]
        
        # Manual override: force worker
        if task_complexity == "simple":
            log.info("Using worker model (forced)", extra={"reason": "simple_task"})
            return self.models["worker"]
        
        # AUTO-ROUTING LOGIC (Goose pattern)
        
        # Rule 1: Initial turns use lead model
        if self.current_turn < self.lead_turns:
            log.info(
                "Using lead model (initial planning)",
                extra={
                    "turn": self.current_turn,
                    "lead_turns": self.lead_turns
                }
            )
            return self.models["lead"]
        
        # Rule 2: Fallback mode after failures
        if self.in_fallback and self.fallback_turns_remaining > 0:
            self.fallback_turns_remaining -= 1
            if self.fallback_turns_remaining == 0:
                self.in_fallback = False
                self.failure_count = 0
                log.info("Exiting fallback mode")
            
            log.info(
                "Using lead model (fallback mode)",
                extra={
                    "turns_remaining": self.fallback_turns_remaining + 1,
                    "reason": "failure_recovery"
                }
            )
            return self.models["lead"]
        
        # Rule 3: Enter fallback after repeated failures
        if self.failure_count >= self.failure_threshold:
            self.in_fallback = True
            self.fallback_turns_remaining = self.fallback_turns
            self.failure_count = 0
            
            log.warning(
                "Entering fallback mode",
                extra={
                    "failures": self.failure_count,
                    "threshold": self.failure_threshold,
                    "fallback_turns": self.fallback_turns
                }
            )
            return self.models["lead"]
        
        # Rule 4: Default to worker model
        log.info("Using worker model (routine execution)")
        return self.models["worker"]
    
    def record_turn(self, success: bool, input_tokens: int, output_tokens: int, model: ModelConfig):
        """
        Record turn result and update routing state.
        
        Args:
            success: Whether the turn succeeded
            input_tokens: Tokens in prompt
            output_tokens: Tokens in response
            model: Model that was used
        """
        self.current_turn += 1
        
        # Update usage stats
        if model.tier == ModelTier.LEAD:
            self.usage_stats["lead_input_tokens"] += input_tokens
            self.usage_stats["lead_output_tokens"] += output_tokens
        else:
            self.usage_stats["worker_input_tokens"] += input_tokens
            self.usage_stats["worker_output_tokens"] += output_tokens
        
        # Track failures
        if not success:
            self.failure_count += 1
            log.info(
                "Turn failed",
                extra={
                    "turn": self.current_turn,
                    "failure_count": self.failure_count,
                    "threshold": self.failure_threshold,
                    "will_fallback": self.failure_count >= self.failure_threshold
                }
            )
    
    def get_cost_analysis(self) -> Dict[str, Any]:
        """Calculate actual costs and savings"""
        lead = self.models["lead"]
        worker = self.models["worker"]
        
        # Calculate actual costs
        lead_input_cost = self.usage_stats["lead_input_tokens"] / 1000 * lead.cost_per_1k_input_tokens
        lead_output_cost = self.usage_stats["lead_output_tokens"] / 1000 * lead.cost_per_1k_output_tokens
        worker_input_cost = self.usage_stats["worker_input_tokens"] / 1000 * worker.cost_per_1k_input_tokens
        worker_output_cost = self.usage_stats["worker_output_tokens"] / 1000 * worker.cost_per_1k_output_tokens
        
        total_cost = lead_input_cost + lead_output_cost + worker_input_cost + worker_output_cost
        
        # Calculate what it would cost with lead-only
        total_tokens_input = self.usage_stats["lead_input_tokens"] + self.usage_stats["worker_input_tokens"]
        total_tokens_output = self.usage_stats["lead_output_tokens"] + self.usage_stats["worker_output_tokens"]
        
        all_lead_input_cost = total_tokens_input / 1000 * lead.cost_per_1k_input_tokens
        all_lead_output_cost = total_tokens_output / 1000 * lead.cost_per_1k_output_tokens
        all_lead_cost = all_lead_input_cost + all_lead_output_cost
        
        # Calculate savings
        savings = all_lead_cost - total_cost
        savings_percent = (savings / all_lead_cost * 100) if all_lead_cost > 0 else 0
        
        return {
            "total_cost": round(total_cost, 4),
            "all_lead_cost": round(all_lead_cost, 4),
            "savings": round(savings, 4),
            "savings_percent": round(savings_percent, 1),
            "lead_tokens": self.usage_stats["lead_input_tokens"] + self.usage_stats["lead_output_tokens"],
            "worker_tokens": self.usage_stats["worker_input_tokens"] + self.usage_stats["worker_output_tokens"],
            "turns": self.current_turn,
            "failures": self.failure_count,
            "fallback_count": 1 if self.in_fallback else 0
        }
```

### Integration with Agent Loop

```python
# Initialize router
router = LLMRouter()

async def agent_loop_with_routing(user_message: str) -> str:
    """Agent loop with Goose-style multi-model routing"""
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": user_message}
    ]
    
    for iteration in range(10):
        # SELECT MODEL BASED ON STATE
        model = router.select_model()
        
        try:
            # Generate response with selected model
            response = await llm_client.generate(
                messages,
                model=model.name,
                tools=skill_registry.get_all_tools()
            )
            
            # Process tool calls
            success = True
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    try:
                        result = await skill_registry.execute(
                            tool_call.name,
                            tool_call.parameters
                        )
                        messages.append({
                            "role": "function",
                            "name": tool_call.name,
                            "content": json.dumps(result)
                        })
                    except AgentError as e:
                        success = False  # Tool failure
                        messages.append({
                            "role": "function",
                            "name": tool_call.name,
                            "content": json.dumps(e.to_tool_response())
                        })
            
            # RECORD TURN FOR ROUTING
            router.record_turn(
                success=success,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                model=model
            )
            
            if not response.tool_calls:
                # Final response - log cost analysis
                analysis = router.get_cost_analysis()
                log.info(
                    "Session complete",
                    extra={
                        "cost_savings": f"{analysis['savings_percent']}%",
                        "total_cost": f"${analysis['total_cost']}",
                        **analysis
                    }
                )
                return response.text
            
        except InfraError as e:
            # Infrastructure failure - record as failure
            router.record_turn(success=False, input_tokens=0, output_tokens=0, model=model)
            log.error(f"Infrastructure failure: {e}")
            return f"❌ System error: {e}"
    
    return "⚠️ Max iterations reached"
```

---

## Pros

### ✅ Massive Cost Savings
**Source:** Goose blog post, Gemini pricing analysis

- **60-80% Reduction:** Real-world savings for routine tasks after initial planning
- **Predictable Costs:** Lead turns are fixed (first N turns), worker handles bulk
- **Scales Well:** More complex sessions see even higher savings (more worker turns)

**Real Numbers (Gemini Example):**
```
Scenario: 20-turn session (3 lead + 17 worker)
- Lead: 3 turns × 2,000 tokens avg = 6,000 tokens
- Worker: 17 turns × 2,000 tokens avg = 34,000 tokens

Cost breakdown:
- Lead only: 40,000 tokens × $0.00070 = $0.028
- Mixed routing: 
  - Lead: 6,000 × $0.00070 = $0.0042
  - Worker: 34,000 × $0.00004 = $0.00136
  - Total: $0.00556
- Savings: $0.028 - $0.00556 = $0.02244 (80% reduction)

At 100 sessions/day: $2.24/day saved ($67/month)
```

### ✅ Maintains Quality Through Fallback
**Source:** Goose failure detection logic

- **Automatic Recovery:** System detects when worker model struggles and switches to lead
- **No Manual Intervention:** Fallback is transparent to user
- **Graceful Degradation:** Quality never drops below lead model performance

**Failure Detection Signals:**
- Tool execution errors (invalid parameters, execution failures)
- User corrections/clarifications (indicate worker didn't understand)
- Retry loops (same tool called 3+ times with small variations)

### ✅ Simple Configuration
**Source:** Goose environment variables

- **No Code Changes:** Entire routing strategy controlled via env vars
- **Easy Tuning:** Adjust thresholds without redeploying
- **A/B Testing:** Test different routing strategies per environment

### ✅ Transparency & Observability
**Source:** Goose logging and cost tracking

- **Per-Session Metrics:** See exactly how much was saved per session
- **Model Distribution:** Track % of turns using lead vs worker
- **Failure Analysis:** Identify tasks that frequently trigger fallback

---

## Cons

### ❌ Complexity in Routing Logic
**Source:** Software engineering complexity analysis

- **State Management:** Must track turns, failures, fallback mode across async operations
- **Edge Cases:** Concurrent tool calls, partial failures, timeout handling
- **Testing Burden:** Need to test all routing paths (initial, fallback, recovery)

**Lines of Code:** ~200 lines for full router implementation vs 10 lines for single-model approach.

### ❌ Quality Variance
**Source:** LLM capability research, Goose user reports

- **Worker Model Limitations:** Cheap models struggle with complex reasoning
- **Context Sensitivity:** Worker may lose important details from earlier lead turns
- **Inconsistent Performance:** Same task might succeed or fail depending on turn number

**Example:** In Goose GitHub discussions, users report worker models (GPT-4o-mini, Gemini Flash) sometimes "forget" complex requirements established by lead model in initial turns.

**Mitigation:** Increase `LEAD_TURNS` for complex domains (e.g., 5 instead of 3).

### ❌ Latency Variability
**Source:** Model performance benchmarks

- **Model Switching Overhead:** 100-300ms to reinitialize model on fallback
- **Worker Speed Advantage:** Worker models are often 2-3x faster than lead
- **Unpredictable Timing:** User can't predict if response will take 2s (worker) or 8s (lead)

**Real-World Impact:**
```
Lead model (Gemini Pro): 3-8 seconds per turn
Worker model (Gemini Flash): 1-3 seconds per turn

Session with fallback:
- Turns 1-3 (lead): 15 seconds total
- Turns 4-8 (worker): 10 seconds total
- Turn 9 (fallback to lead after 2 failures): 6 seconds
- Turns 10-15 (lead): 36 seconds total
Total: 67 seconds

Same session with lead-only: 90 seconds
Savings: 23 seconds, but with variance spikes
```

### ❌ Provider Lock-In Risk
**Source:** Multi-cloud architecture considerations

- **Cross-Provider Routing Complexity:** Routing between Vertex AI (lead) and OpenAI (worker) requires different SDKs
- **Authentication Overhead:** Managing API keys for multiple providers
- **Rate Limits:** Each provider has separate rate limit buckets

**Goose Approach:** Supports cross-provider routing but adds significant complexity. Most users stick to single provider (e.g., all Gemini or all Claude).

### ❌ Cost Tracking Complexity
**Source:** FinOps for AI systems

- **Token Attribution:** Must track which model consumed which tokens
- **Billing Reconciliation:** Provider bills don't show routing breakdown
- **Budget Alerts:** Setting thresholds requires estimating worker/lead ratio

---

## When to Use This Approach

### ✅ Use Multi-Model Routing When:

1. **High Volume:** Running 50+ sessions per day (cost savings justify complexity)
2. **Cost Sensitive:** Budget constraints require optimization
3. **Clear Task Phases:** Tasks have distinct "planning" vs "execution" phases
4. **Quality Tolerance:** Can accept occasional worker model mistakes (with fallback)
5. **Same Provider:** Both models from same provider (Vertex AI, OpenAI) for simplicity

### ❌ Avoid This Approach When:

1. **Low Volume:** < 10 sessions per day (savings don't justify engineering cost)
2. **Critical Quality:** Every response must be highest quality (medical, legal, financial)
3. **Simple Tasks:** Tasks complete in 2-3 turns (no worker turns to save on)
4. **Tight Latency SLA:** Must guarantee < 5 second responses
5. **Complex Multi-Provider:** Would require routing across 3+ different LLM providers

---

## Alternative Routing Strategies

### Strategy 1: Task-Based Routing (Simpler)

```python
def select_model_by_task(task_type: str) -> str:
    """Route by explicit task classification"""
    routing = {
        "research": "gemini-2.0-pro",      # Complex analysis
        "summarize": "gemini-2.0-flash",   # Simple extraction
        "translate": "gemini-2.0-flash",   # Straightforward
        "code_review": "gemini-2.0-pro",   # Requires reasoning
        "format": "gemini-2.0-flash"       # Templating
    }
    return routing.get(task_type, "gemini-2.0-flash")

# Usage
task_type = detect_task_type(user_message)
model = select_model_by_task(task_type)
```

**Pros:** Simple, deterministic, no state management  
**Cons:** Requires task classification, less adaptive

### Strategy 2: Tool-Based Routing

```python
def select_model_by_tools(tools_called: List[str]) -> str:
    """Route based on which tools are being used"""
    complex_tools = {"code_generation", "architecture_design", "security_audit"}
    
    if any(tool in complex_tools for tool in tools_called):
        return "gemini-2.0-pro"
    return "gemini-2.0-flash"
```

**Pros:** Tool-specific optimization, no turn tracking  
**Cons:** Requires tool execution before routing (too late)

### Strategy 3: Hybrid (Task + Goose Pattern)

```python
def select_model_hybrid(task_type: str, current_turn: int, failures: int) -> str:
    """Combine task classification with Goose's session-based routing"""
    # Override: Always use lead for complex tasks
    if task_type in ["code_review", "architecture", "security"]:
        return "gemini-2.0-pro"
    
    # Use Goose pattern for general tasks
    if current_turn < 3 or failures >= 2:
        return "gemini-2.0-pro"
    return "gemini-2.0-flash"
```

**Pros:** Best of both worlds, domain-specific optimization  
**Cons:** Most complex to implement and tune

---

## Implementation Roadmap for emonk

### Week 1: Basic Router
```python
# Day 1-2: Model configs and router class
# Day 3-4: Integration with agent loop
# Day 5: Testing with 2 models (Gemini Flash + Pro)
```

### Week 2: Failure Detection
```python
# Day 1-2: Define failure signals
# Day 3-4: Implement fallback logic
# Day 5: Test fallback scenarios
```

### Week 3: Cost Tracking
```python
# Day 1-2: Usage statistics
# Day 3: Cost analysis methods
# Day 4-5: Reporting dashboard/logs
```

### Week 4: Tuning & Optimization
```python
# Day 1-3: A/B test different thresholds
# Day 4-5: Document optimal configs for different use cases
```

---

## Configuration Examples

### Conservative (Quality First)
```bash
EMONK_LEAD_TURNS=5                # More lead model usage
EMONK_FAILURE_THRESHOLD=1         # Quick fallback on first failure
EMONK_FALLBACK_TURNS=5            # Stay on lead longer after fallback
# Result: ~40% cost savings, highest quality
```

### Balanced (Goose Default)
```bash
EMONK_LEAD_TURNS=3
EMONK_FAILURE_THRESHOLD=2
EMONK_FALLBACK_TURNS=2
# Result: ~60% cost savings, good quality
```

### Aggressive (Cost First)
```bash
EMONK_LEAD_TURNS=1                # Minimal lead usage
EMONK_FAILURE_THRESHOLD=3         # Tolerate more failures
EMONK_FALLBACK_TURNS=1            # Quick return to worker
# Result: ~80% cost savings, acceptable quality for simple tasks
```

---

## Comparison Matrix

| Dimension | Single Model | Goose Routing | Task-Based | Tool-Based |
|-----------|-------------|---------------|------------|-----------|
| **Cost Savings** | ❌ 0% | ✅ 60-80% | ⚠️ 40-60% | ⚠️ 50-70% |
| **Implementation** | ⭐⭐⭐⭐⭐ Simple | ⭐⭐⭐ Complex | ⭐⭐⭐⭐ Medium | ⭐⭐⭐⭐ Medium |
| **Quality Consistency** | ⭐⭐⭐⭐⭐ Perfect | ⭐⭐⭐⭐ High | ⭐⭐⭐ Variable | ⭐⭐⭐ Variable |
| **Latency Predictability** | ⭐⭐⭐⭐⭐ Perfect | ⭐⭐⭐ Variable | ⭐⭐⭐⭐ Good | ⭐⭐⭐ Variable |
| **Adaptability** | ❌ None | ✅ High | ⚠️ Medium | ⚠️ Medium |
| **Debugging** | ⭐⭐⭐⭐⭐ Trivial | ⭐⭐⭐ Complex | ⭐⭐⭐⭐ Simple | ⭐⭐⭐⭐ Simple |

---

## Resources

- **Goose Multi-Model Blog:** https://block.github.io/goose/blog/2025/06/16/multi-model-in-goose
- **Goose Lead/Worker Setup:** https://block.github.io/goose/docs/tutorials/lead-worker/
- **Gemini Pricing:** https://ai.google.dev/pricing
- **Claude Pricing:** https://www.anthropic.com/pricing
- **Cost Optimization Research:** "Efficient LLM Inference" (Hugging Face, 2025)
