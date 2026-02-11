# Example Insights Report

This file shows what a well-structured insights report looks like after evaluation.

---

# Agent Evaluation Insights - SAT Prep Coach

**Date:** 2026-02-02 14:30:22
**Tests Run:** 15
**Pass Rate:** 86.7% (13/15)
**Overall Score:** 7.8/10

## Quick Verdict
**Needs targeted improvements** - Agent performs well on content delivery but struggles with tool reliability and efficiency.

## Key Takeaway
The SAT Prep Coach excels at providing accurate study guidance (9.2/10 correctness) and maintaining an encouraging tone, but critical tool failures in the practice quiz generator are blocking 2 test scenarios. The `generate_practice_questions` tool returns None in 13% of test cases, preventing students from accessing practice materials. This should be fixed before production deployment.

---

## 📊 Results Overview

### Dimension Performance

| Dimension | Score | Status | Trend |
|-----------|-------|--------|-------|
| Correctness | 9.2/10 | ✓ Excellent | Stable |
| Tone & Style | 9.0/10 | ✓ Excellent | Improving |
| Completeness | 8.5/10 | ✓ Good | Stable |
| Tool Usage | 6.8/10 | ⚠️ Needs Work | Declining |
| Efficiency | 5.4/10 | ⚠️ Needs Work | Declining |

### Performance by Category

| Category | Tests | Pass Rate | Avg Score | Notes |
|----------|-------|-----------|-----------|-------|
| Math Help | 5 | 100% | 8.2/10 | Strong |
| Reading Comprehension | 5 | 80% | 7.8/10 | Quiz tool failures |
| Writing Strategies | 5 | 80% | 7.5/10 | Efficiency issues |

### Performance by Persona

| Persona | Tests | Pass Rate | Avg Score | Observations |
|---------|-------|-----------|-----------|--------------|
| Motivated High Achiever | 5 | 100% | 8.4/10 | Responds well to detail |
| Struggling Student | 5 | 80% | 7.6/10 | Tool failures impact confidence |
| Time-Crunched Junior | 5 | 80% | 7.5/10 | Efficiency matters here |

---

## 🚨 Critical Issues

### Issue 1: Practice Quiz Generator Failure

**Severity:** High (Blocking functionality)
**Impact:** Students cannot access practice questions in 13% of scenarios
**Evidence:**
- Test `reading_comp_struggling_student_v2`: Tool returned `None`
- Test `writing_strategies_time_crunched_v1`: Tool returned `None`
- Error logs: `[SAT Coach] Tool generate_practice_questions failed: None is not a callable object`

**Root Cause:** Tool initialization in `skills/practice_materials/` returns None when difficulty parameter is missing

**Action Required:**
1. Fix tool initialization in `agents/sat_prep/backend/tools.py:145`
2. Add default difficulty parameter handling
3. Add error recovery: suggest manual practice resources when tool fails

**Expected Improvement:** Pass rate 87% → 93%+

### Issue 2: Excessive Tool Calls in Writing Section

**Severity:** Medium (Performance degradation)
**Impact:** 2.3x longer response times, higher costs
**Evidence:**
- Writing strategy tests average 6.4 tool calls (expected: 2-3)
- Test `writing_strategies_motivated_v2`: 9 tool calls for single answer
- Most calls are redundant `web_search` operations

**Root Cause:** Agent performs separate searches for each writing tip instead of batching

**Action Required:**
1. Modify `skills/writing_strategies/strategy.py` to batch related searches
2. Cache common writing rules in system prompt
3. Limit max tool calls to 4 in writing skill

**Expected Improvement:**
- Efficiency score: 5.4 → 7.5+
- Response time: 18s → 8s average
- Cost per query: $0.024 → $0.011

---

## ✅ Action Items

### Priority 1: Fix Practice Quiz Tool (Critical)
**What:** Debug and fix `generate_practice_questions` tool initialization
**Why:** Blocking core functionality for 2 test scenarios; prevents practice material access
**Where:** `agents/sat_prep/backend/tools.py` lines 145-167
**How:**
```python
# Add default parameter handling
def generate_practice_questions(topic: str, difficulty: str = "medium", count: int = 5):
    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"  # Safe default
    # ... rest of implementation
```
**Expected Improvement:** Pass rate +6%, tool usage score +1.5 points
**Time Estimate:** 30 minutes

### Priority 2: Optimize Writing Strategy Tool Calls
**What:** Batch related web searches in writing skills
**Why:** Reducing from 6.4 to 3 calls improves speed 2.3x and cuts costs 50%
**Where:** `agents/sat_prep/backend/skills/writing_strategies/strategy.py`
**How:**
- Combine "grammar rules" + "common mistakes" into single search
- Cache frequently requested writing tips in skill context
- Add `max_tool_calls=4` to skill config
**Expected Improvement:** Efficiency +2.1 points, cost -52%
**Time Estimate:** 1-2 hours

### Priority 3: Add Error Recovery for Tool Failures
**What:** Graceful fallback when tools fail
**Why:** Maintain user experience even when tools error
**Where:** Tool error handling in agent middleware
**How:**
```python
try:
    questions = generate_practice_questions(...)
except Exception as e:
    logger.warning(f"Quiz tool failed: {e}")
    return "I'm having trouble generating questions right now. " \
           "Try these resources: [Khan Academy SAT Practice](...)"
```
**Expected Improvement:** Better user experience, no test failures due to tool errors
**Time Estimate:** 45 minutes

### Priority 4: Expand Math Help Test Coverage
**What:** Add tests for advanced math topics (trig, complex numbers)
**Why:** Current tests only cover algebra and geometry basics
**Where:** Create new seeds in `agent-training/examples/seeds/sat_prep_seeds.json`
**Suggested Tests:**
- Trigonometry word problems
- Complex number operations
- Function transformations
- Probability and statistics
**Expected Improvement:** Better confidence in full math coverage
**Time Estimate:** 1 hour

---

## 📊 Coverage Analysis

### Well-Covered Scenarios ✅
- ✅ **Algebra basics**: 4 tests, 100% pass
- ✅ **Reading comprehension strategies**: 3 tests, 100% pass
- ✅ **Time management tips**: 2 tests, 100% pass
- ✅ **Motivational coaching**: All personas tested

### Missing/Weak Coverage ⚠️
- ⚠️ **Advanced math (trig, complex numbers)**: 0 tests
- ⚠️ **Essay writing**: Only 1 test
- ⚠️ **Test anxiety scenarios**: No dedicated tests
- ⚠️ **Calculator usage guidance**: Not tested
- ⚠️ **Pacing strategies under time pressure**: 1 superficial test

### Recommended Additional Tests 💡
1. **Trigonometry Problems** (high priority)
   - Sample: "How do I solve sin(x) = 1/2 on the SAT?"
   - Tests calculator vs. no-calculator strategies

2. **Essay Structure** (medium priority)
   - Sample: "Help me organize my SAT essay with thesis and evidence"
   - Tests 4-paragraph structure guidance

3. **Test Anxiety Management** (medium priority)
   - Sample: "I freeze up during practice tests, what should I do?"
   - Tests emotional support + practical strategies

4. **Multi-step Word Problems** (high priority)
   - Sample: "A train travels 240 miles in 4 hours. If it increases speed by 20%, how long to go 300 miles?"
   - Tests step-by-step problem solving

---

## ⚡ Performance Insights

### Execution Metrics
- **Average response time**: 18.2 seconds (target: <10s)
- **Slowest test**: `writing_strategies_motivated_v2` (42s)
- **Fastest test**: `math_help_time_crunched_v1` (6s)

### Cost Analysis
- **Total tokens**: 156,483 tokens
- **Estimated cost**: $0.31 for 15 tests ($0.021 per test)
- **Projected monthly cost** (1000 users, 5 queries/day): ~$3,150

### Tool Call Patterns
- **Average tool calls**: 4.2 per test
- **Most common tool**: `web_search` (68% of calls)
- **Least used tool**: `create_study_plan` (3% of calls)

### API Reliability
- **Vertex AI uptime**: 100% (no failures)
- **Anthropic Claude retries**: 6 connection errors (auto-recovered)
- **Tool initialization errors**: 2 failures (generate_practice_questions)

---

## 💡 Recommendations

### Quick Wins (< 1 hour each) 🎯
1. **Fix quiz tool initialization** (30 min)
   - Immediate +6% pass rate improvement
   - High impact, low effort

2. **Add error recovery messages** (45 min)
   - Better user experience during failures
   - Prevents blank responses

3. **Cache common writing rules** (20 min)
   - Reduce 40% of web_search calls in writing skill
   - Faster responses, lower costs

### Medium Effort (1-4 hours) 🔧
1. **Batch writing strategy searches** (2 hours)
   - 2.3x faster responses
   - 50% cost reduction
   - Efficiency score improvement

2. **Expand test coverage** (3 hours)
   - Add 8-10 new tests for missing scenarios
   - Covers advanced math, essays, test anxiety
   - Higher confidence in production readiness

3. **Add response time monitoring** (2 hours)
   - Track slow queries in production
   - Alert when >95th percentile exceeds 30s
   - Helps catch performance regressions

### Long-term Improvements 🚀
1. **Implement request caching** (1 day)
   - Cache answers to common SAT questions
   - Could reduce 30-40% of LLM calls
   - Significant cost savings at scale

2. **Progressive skill loading** (2 days)
   - Only load skills relevant to query type
   - Reduces context size, improves latency
   - Better for complex multi-skill agents

3. **A/B test persona-specific prompts** (1 week)
   - Different strategies for struggling vs high-achiever students
   - Could boost pass rate to 95%+
   - Requires infrastructure for variant testing

---

## 🎯 Next Steps

### Immediate (Today)
1. **Fix the quiz tool bug** - Critical blocker, 30 min fix
2. **Re-run evaluation** - Verify fix: `./run_sat_prep_eval.sh`
3. **Review individual test failures** - Check `eval_results/individual_results/`

### This Week
1. **Optimize tool calls** - Batch searches, reduce redundancy
2. **Add error recovery** - Graceful handling of tool failures
3. **Expand test scenarios** - Add 5 new tests for weak coverage areas
4. **Create baseline** - Save results for future comparison:
   ```bash
   python -m agent_trainings run --config sat_prep_config.json --save-baseline v1.0.0
   ```

### Next Sprint
1. **Implement caching** - For common questions and writing rules
2. **Performance optimization** - Target <10s average response time
3. **Add monitoring** - Production metrics dashboard

---

## 📈 Expected Trajectory

After implementing Priority 1-3 fixes:

| Metric | Current | After Fixes | Target |
|--------|---------|-------------|--------|
| Pass Rate | 86.7% | 93%+ | 95% |
| Overall Score | 7.8/10 | 8.4/10 | 8.5+ |
| Tool Usage | 6.8/10 | 8.2/10 | 8.0+ |
| Efficiency | 5.4/10 | 7.5/10 | 7.5+ |
| Avg Response Time | 18.2s | 8.5s | <10s |
| Cost per Query | $0.021 | $0.011 | <$0.015 |

---

## 🔄 Re-run After Fixes

```bash
./run_sat_prep_eval.sh
```

Then compare results:
```bash
python -m agent_trainings compare \
  --baseline eval_results/baselines/baseline_v1.0.0.json \
  --current eval_results/baselines/baseline_v1.0.1.json
```

---

## 📚 Additional Resources

- **Detailed test results**: `eval_results/report_*.json`
- **Individual test logs**: `eval_results/individual_results/`
- **Agent code**: `agents/sat_prep/backend/`
- **Test seeds**: `agent-training/examples/seeds/sat_prep_seeds.json`
- **Evaluation docs**: `agent-training/README.md`

---

**Generated by agent-training evaluation framework**
*For questions or issues, see `agent-training/docs/NEW_AGENT_QUICKSTART.md`*
