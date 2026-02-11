---
name: generate-agent-eval
description: Generate evaluation scripts for LangGraph, LCEL, and callable agents with automated test execution and insights reporting. Use when the user wants to create eval scripts, test an agent, run evaluations, or generate agent performance reports. Validates agent compatibility before creating test scripts.
---

# Generate Agent Evaluation Script

Generate comprehensive evaluation scripts that test AI agents end-to-end with the agent-training framework, then produce actionable insights reports.

## When to Use This Skill

Use when the user:
- Wants to create an eval script for an agent
- Needs to test/evaluate an agent's performance
- Asks to "run evals" or "test my agent"
- Wants insights on agent behavior or quality
- Mentions testing, evaluation, or quality assessment

## Prerequisites Check

Before generating a script, verify:

1. **Agent file exists** - Locate the agent file/module
2. **Agent type is supported** - LangGraph, LCEL chains, or callables
3. **agent-training is available** - Check if installed in project
4. **Seed tests exist** (optional) - For synthetic test generation

## Core Workflow

### Step 1: Validate Agent Compatibility

Read the agent file and determine:

**✅ CAN TEST:**
- LangGraph compiled graphs (`CompiledGraph`, `StateGraph`)
- LCEL chains with `.invoke()` or `.ainvoke()` methods
- Callable functions accepting message dictionaries
- Agents with clear entry points

**❌ CANNOT TEST (explain why):**
- Agents without clear invoke interface
- Streaming-only agents (requires special handling)
- Agents with complex external dependencies not documented
- Incomplete agent implementations

**If cannot test:** Explain specifically what's missing and what needs to be added.

### Step 2: Locate or Create Seed Tests

**Option A: Use existing seeds**
- Look for `agent-training/examples/seeds/[agent-name]_seeds.json`
- If found, reference this file in the script

**Option B: Offer to create seeds**
- If no seeds exist, ask: "Should I create seed tests for this agent?"
- Generate 3-5 seed examples based on the agent's purpose
- Use the agent's system prompt or README to understand capabilities

### Step 3: Generate Evaluation Script

Create a bash script named `run_[agent-name]_eval.sh` with:

**Required sections:**
1. **Environment validation**
   - Check venv exists (or prompt to create)
   - Validate GCP credentials
   - Verify agent-training module
   - Check seed tests location

2. **Virtual environment activation**
   ```bash
   source .venv/bin/activate
   ```

3. **Test generation** (if using synthetic)
   ```bash
   python -m agent_trainings generate \
     --seed-tests <path-to-seeds> \
     --output <output-path> \
     --num-personas 3 \
     --variations 2
   ```

4. **Configuration creation**
   - Generate config.json with agent details
   - Set appropriate thresholds based on agent complexity
   - Configure output directories

5. **Evaluation execution**
   ```bash
   python -m agent_trainings run \
     --config <config-path> \
     --output-dir <output-dir>
   ```

6. **Results processing**
   - Find latest report files
   - Generate insights markdown (see Step 4)

### Step 4: Generate Insights Report

After evaluation completes, create `EVAL_INSIGHTS_[timestamp].md` with:

#### Section 1: Executive Summary (Top of file)
```markdown
# Agent Evaluation Insights - [Agent Name]

**Date:** [timestamp]
**Tests Run:** X
**Pass Rate:** X%
**Overall Score:** X.X/10

## Quick Verdict
[One sentence: "Production ready" / "Needs improvement" / "Not ready"]

## Key Takeaway
[One paragraph highlighting the most critical finding]
```

#### Section 2: Results Overview
- Pass/fail breakdown
- Dimension scores with status indicators
- Performance by category/difficulty/persona
- Top strengths and weaknesses

#### Section 3: Critical Issues (If any)
```markdown
## 🚨 Critical Issues

### Issue 1: [Tool Failure]
**Severity:** High
**Impact:** Blocks [specific functionality]
**Evidence:** Test X, Y failed due to [specific error]
**Action:** Fix [specific component]
```

#### Section 4: Actionable Items
Prioritized list of specific actions:
```markdown
## ✅ Action Items

### Priority 1: Fix [Specific Issue]
- **What:** [Concrete description]
- **Why:** [Impact on users/tests]
- **Where:** [File/function to modify]
- **Expected improvement:** [Metric change]

### Priority 2: [Next item]
...
```

#### Section 5: Test Coverage Analysis
```markdown
## 📊 Coverage Analysis

### Well-Covered Scenarios
- ✅ [Scenario type]: X tests
- ✅ [Scenario type]: Y tests

### Missing/Weak Coverage
- ⚠️ [Scenario type]: Only 1 test
- ❌ [Scenario type]: No tests
- 💡 **Recommendation:** Add tests for [specific scenarios]
```

#### Section 6: Performance Insights (If available)
- Execution time patterns
- Token usage and costs
- API retry patterns
- Tool call efficiency

#### Section 7: Recommendations
```markdown
## 💡 Recommendations

### Quick Wins (< 1 hour)
1. [Specific change with high ROI]
2. [Specific change with high ROI]

### Medium Effort (1-4 hours)
1. [Improvement with details]

### Long-term Improvements
1. [Strategic enhancement]
```

#### Section 8: Next Steps
```markdown
## 🎯 Next Steps

1. **Immediate:** [Most urgent action]
2. **This week:** [Important improvements]
3. **Future:** [Long-term enhancements]

### Re-run After Fixes
\`\`\`bash
./run_[agent-name]_eval.sh
\`\`\`

Expected improvements:
- [Metric]: [Current] → [Target]
- [Metric]: [Current] → [Target]
```

## Insights Generation Guidelines

### Be Specific, Not Generic
- ❌ "Improve tool usage"
- ✅ "Fix find_scholarships tool - currently returns None instead of callable function"

### Include Evidence
Always cite specific tests or error messages:
- "Test seed_002_v1 failed due to..."
- "Logs show 'APIConnectionError' in tests 3, 5, 7"

### Provide Context
Explain WHY something matters:
- Not just "Efficiency score is low"
- But "Efficiency score is 5.2/10 because agent makes 7 tool calls when 2 expected, increasing latency and costs"

### Make Actions Concrete
- ❌ "Optimize the agent"
- ✅ "Reduce tool calls by combining web_search queries in scholarship_discovery skill"

### Highlight Patterns
Look for:
- Multiple tests failing the same way
- Specific personas struggling more
- Certain categories underperforming
- Tool failures clustering in scenarios

### Compare to Expectations
- "Expected single-turn responses, but averaging 2.8 turns"
- "Target was 95% pass rate, achieved 73%"

## Agent Type Handling

### LangGraph Agents
```json
{
  "agent_under_test": {
    "type": "langgraph",
    "import_path": "agents.my_agent.backend.agent",
    "object_name": "my_agent_graph"
  }
}
```

### LCEL Chains
```json
{
  "agent_under_test": {
    "type": "lcel_chain",
    "import_path": "chains.my_chain",
    "object_name": "chain"
  }
}
```

### Callable Functions
```json
{
  "agent_under_test": {
    "type": "callable",
    "import_path": "agents.simple_agent",
    "object_name": "process_message"
  }
}
```

## Error Handling in Script

The generated script should handle:

1. **Missing venv**
   ```bash
   if [ ! -d ".venv" ]; then
       echo "Virtual environment not found. Create one with:"
       echo "  python -m venv .venv"
       exit 1
   fi
   ```

2. **Missing GCP credentials**
   ```bash
   if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
       # Try to auto-detect from common locations
       # If not found, provide clear instructions
   fi
   ```

3. **Agent import failures**
   - Catch Python import errors
   - Suggest adding parent directory to PYTHONPATH

4. **No seed tests**
   - Offer to create basic seeds
   - Or point to manual test dataset creation

## Script Template Structure

Use this structure for generated scripts:

```bash
#!/bin/bash
# [Agent Name] - Automated Evaluation Script
# Generated: [timestamp]

set -e  # Exit on error

# [Configuration section]
AGENT_NAME="[name]"
AGENT_PATH="[path]"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# [Step 1: Environment validation]
echo "[1/5] Validating environment..."

# [Step 2: Activate venv]
echo "[2/5] Activating virtual environment..."
source .venv/bin/activate

# [Step 3: Generate/prepare tests]
echo "[3/5] Preparing test cases..."

# [Step 4: Run evaluation]
echo "[4/5] Running evaluation..."

# [Step 5: Generate insights]
echo "[5/5] Generating insights report..."

# [Insights generation logic]
python3 << 'PYTHON_SCRIPT'
import json
from pathlib import Path
from datetime import datetime

# Load results
report_path = Path("eval_results/report_*.json").resolve()
# ... generate insights markdown ...
PYTHON_SCRIPT

echo "✓ Complete! See EVAL_INSIGHTS_*.md for detailed analysis"
```

## Common Pitfalls to Avoid

1. **Don't generate generic insights**
   - Read the actual test results
   - Parse failure patterns
   - Cite specific evidence

2. **Don't ignore tool failures**
   - If logs show tool errors, call them out explicitly
   - Explain the impact on functionality

3. **Don't skip coverage analysis**
   - Look at category distribution
   - Identify missing test scenarios
   - Suggest specific tests to add

4. **Don't make assumptions**
   - If agent structure is unclear, ask
   - If seed tests don't exist, offer to create
   - If venv location is non-standard, detect it

## Validation Checklist

Before delivering the script to the user:

- [ ] Script is executable (`chmod +x`)
- [ ] All paths are relative or properly resolved
- [ ] Venv activation is correct for the project
- [ ] Agent import path is valid
- [ ] Seed tests exist or will be created
- [ ] Output directories are created if missing
- [ ] Error messages are helpful and actionable
- [ ] Insights generation reads actual results
- [ ] Script includes clear usage instructions

## Example Usage Flow

**User:** "Create an eval script for my SAT prep agent"

**Agent response:**
1. ✅ "Found agent at `agents/sat_prep/backend/agent.py`"
2. ✅ "Agent type: LangGraph (compatible)"
3. ⚠️ "No seed tests found. Should I create basic seeds for SAT prep scenarios?"
4. [User confirms]
5. ✅ "Generated `run_sat_prep_eval.sh` with:"
   - 5 seed tests covering math, reading, writing
   - 10 test variations across student personas
   - Full evaluation and insights pipeline
6. 📄 "Run with: `./run_sat_prep_eval.sh`"

## Post-Generation Support

After generating the script, offer:

1. **Test the script**: "Would you like me to do a dry-run check?"
2. **Explain usage**: "Here's how to run and interpret results..."
3. **Customize**: "Need different test scenarios or thresholds?"

## Summary

This skill helps AI engineers:
- ✅ Quickly set up eval pipelines for any agent
- ✅ Get actionable insights, not just numbers
- ✅ Identify specific bugs and improvements
- ✅ Track quality over time with baselines
- ✅ Ensure comprehensive test coverage

The key is making evals **easy to run** and **insights actionable**.
