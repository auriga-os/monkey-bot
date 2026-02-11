#!/bin/bash

################################################################################
# [AGENT_NAME] - Automated Evaluation Script
# Generated: [TIMESTAMP]
################################################################################
#
# This script demonstrates the standard structure for agent evaluation scripts.
# Replace [PLACEHOLDERS] with actual values when generating for a specific agent.
#
# Usage:
#   cd [agent-repo]
#   ./run_[agent_name]_eval.sh
#
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration
AGENT_NAME="[agent_name]"
AGENT_TYPE="[langgraph|lcel_chain|callable]"
AGENT_PATH="[path/to/agent/file.py]"
AGENT_IMPORT="[agents.my_agent.backend.agent]"
AGENT_OBJECT="[my_agent_graph]"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/eval_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# File paths
SEED_TESTS="[path/to/seed_tests.json]"
GENERATED_TESTS="$OUTPUT_DIR/generated_tests.json"
EVAL_CONFIG="$OUTPUT_DIR/eval_config.json"
INSIGHTS_FILE="$SCRIPT_DIR/EVAL_INSIGHTS_$TIMESTAMP.md"

################################################################################
# Helper Functions
################################################################################

print_banner() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}${BOLD}$AGENT_NAME - EVALUATION${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

print_step() {
    local step=$1
    local total=$2
    local message=$3
    echo ""
    echo -e "${BLUE}${BOLD}[$step/$total] $message${NC}"
    echo "----------------------------------------"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

################################################################################
# Step 1: Environment Validation
################################################################################

validate_environment() {
    print_step 1 5 "Validating environment"
    
    # Check virtual environment
    if [ ! -d "$SCRIPT_DIR/.venv" ]; then
        print_error "Virtual environment not found at $SCRIPT_DIR/.venv"
        echo ""
        echo "Create a virtual environment with:"
        echo "  python -m venv .venv"
        echo "  source .venv/bin/activate"
        echo "  pip install -e ../agent-training"
        exit 1
    fi
    print_success "Virtual environment found"
    
    # Check GCP credentials
    if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        print_warning "GOOGLE_APPLICATION_CREDENTIALS not set"
        # Try to auto-detect
        if [ -f "$PROJECT_ROOT/gcp_service_auth_qa.json" ]; then
            export GOOGLE_APPLICATION_CREDENTIALS="$PROJECT_ROOT/gcp_service_auth_qa.json"
            print_success "Auto-detected GCP credentials"
        else
            print_error "GCP credentials not found"
            echo ""
            echo "Set GCP credentials:"
            echo "  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json"
            exit 1
        fi
    else
        print_success "GCP credentials configured"
    fi
    
    # Check GCP project
    if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        print_warning "GOOGLE_CLOUD_PROJECT not set, attempting auto-detection..."
        GOOGLE_CLOUD_PROJECT=$(python3 -c "import json; print(json.load(open('$GOOGLE_APPLICATION_CREDENTIALS'))['project_id'])" 2>/dev/null || echo "")
        if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
            export GOOGLE_CLOUD_PROJECT
            print_success "Auto-detected project: $GOOGLE_CLOUD_PROJECT"
        else
            print_error "Could not determine GCP project ID"
            exit 1
        fi
    else
        print_success "GCP project: $GOOGLE_CLOUD_PROJECT"
    fi
    
    # Check agent file exists
    if [ ! -f "$SCRIPT_DIR/$AGENT_PATH" ]; then
        print_error "Agent file not found: $AGENT_PATH"
        exit 1
    fi
    print_success "Agent file found"
    
    # Check seed tests (if using synthetic generation)
    if [ -n "$SEED_TESTS" ] && [ ! -f "$SEED_TESTS" ]; then
        print_warning "Seed tests not found: $SEED_TESTS"
        print_info "Will need to create seed tests or use manual test dataset"
    fi
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    print_success "Output directory ready: $(basename $OUTPUT_DIR)"
}

################################################################################
# Step 2: Activate Virtual Environment
################################################################################

activate_venv() {
    print_step 2 5 "Activating virtual environment"
    
    source "$SCRIPT_DIR/.venv/bin/activate"
    
    # Verify agent-training is installed
    if ! python3 -c "import agent_trainings" 2>/dev/null; then
        print_error "agent-training module not found"
        echo ""
        echo "Install agent-training:"
        echo "  pip install -e ../agent-training"
        exit 1
    fi
    print_success "agent-training module available"
    
    # Add current directory to PYTHONPATH for agent imports
    export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
    print_success "PYTHONPATH configured for agent imports"
}

################################################################################
# Step 3: Generate or Prepare Tests
################################################################################

prepare_tests() {
    print_step 3 5 "Preparing test cases"
    
    # Option A: Generate synthetic tests from seeds
    if [ -f "$SEED_TESTS" ]; then
        print_info "Generating synthetic tests from seeds"
        
        cd "$PROJECT_ROOT/agent-training"
        python3 -m agent_trainings generate \
            --seed-tests "$SEED_TESTS" \
            --output "$GENERATED_TESTS" \
            --num-personas 3 \
            --variations 2 \
            --validate
        
        cd "$SCRIPT_DIR"
        
        TEST_COUNT=$(python3 -c "import json; print(len(json.load(open('$GENERATED_TESTS'))))")
        print_success "Generated $TEST_COUNT test cases"
    
    # Option B: Use existing test dataset
    else
        print_warning "No seed tests found, will need manual test dataset"
        # Prompt user or use default location
        GENERATED_TESTS="[path/to/manual/tests.json]"
        
        if [ ! -f "$GENERATED_TESTS" ]; then
            print_error "No test dataset available"
            exit 1
        fi
        
        TEST_COUNT=$(python3 -c "import json; print(len(json.load(open('$GENERATED_TESTS'))))")
        print_success "Using $TEST_COUNT existing test cases"
    fi
}

################################################################################
# Step 4: Create Evaluation Configuration
################################################################################

create_config() {
    print_step 4 5 "Creating evaluation configuration"
    
    cat > "$EVAL_CONFIG" <<EOF
{
  "config_name": "${AGENT_NAME}_evaluation",
  "version": "1.0",
  "agent_under_test": {
    "type": "$AGENT_TYPE",
    "import_path": "$AGENT_IMPORT",
    "object_name": "$AGENT_OBJECT",
    "timeout_seconds": 60
  },
  "test_dataset": {
    "path": "$GENERATED_TESTS",
    "limit": 10
  },
  "evaluation_dimensions": {
    "correctness": {
      "enabled": true,
      "weight": 0.3,
      "description": "Factual accuracy and appropriateness of response"
    },
    "tool_usage": {
      "enabled": true,
      "weight": 0.2,
      "description": "Correct and efficient use of available tools"
    },
    "tone_and_style": {
      "enabled": true,
      "weight": 0.2,
      "description": "Communication style matches persona and context"
    },
    "completeness": {
      "enabled": true,
      "weight": 0.2,
      "description": "All required elements addressed"
    },
    "efficiency": {
      "enabled": true,
      "weight": 0.1,
      "description": "Minimal redundancy and optimal tool usage"
    }
  },
  "pass_fail_criteria": {
    "mode": "overall_score",
    "overall_threshold": 7.0
  },
  "evaluator_config": {
    "model": "gemini-2.5-flash",
    "temperature": 0.0,
    "max_tokens": 10000
  },
  "execution_settings": {
    "parallel_workers": 1,
    "timeout_per_test_seconds": 60,
    "retry_on_failure": true,
    "max_retries": 2,
    "continue_on_error": true
  },
  "output_settings": {
    "output_directory": "$OUTPUT_DIR",
    "save_individual_results": true,
    "save_aggregate_report": true,
    "save_conversation_logs": true,
    "report_format": ["json", "markdown"],
    "include_passed_tests_in_report": false
  }
}
EOF
    
    print_success "Configuration created: $(basename $EVAL_CONFIG)"
}

################################################################################
# Step 5: Run Evaluation
################################################################################

run_evaluation() {
    print_step 5 5 "Running evaluation"
    
    print_info "This will execute tests against your agent and score responses"
    print_warning "Expected duration: 2-5 minutes depending on test count..."
    echo ""
    
    cd "$PROJECT_ROOT/agent-training"
    
    python3 -m agent_trainings run \
        --config "$EVAL_CONFIG" \
        --output-dir "$OUTPUT_DIR"
    
    cd "$SCRIPT_DIR"
}

################################################################################
# Step 6: Generate Insights Report
################################################################################

generate_insights() {
    print_step 6 6 "Generating insights report"
    
    # Find the most recent report
    REPORT_JSON=$(ls -t "$OUTPUT_DIR"/report_*.json 2>/dev/null | head -1)
    REPORT_MD=$(ls -t "$OUTPUT_DIR"/report_*.md 2>/dev/null | head -1)
    
    if [ -z "$REPORT_JSON" ]; then
        print_error "No evaluation report found"
        exit 1
    fi
    
    print_info "Analyzing results..."
    
    # Generate insights using Python
    python3 << 'PYTHON_SCRIPT'
import json
import sys
from pathlib import Path
from datetime import datetime

# Load results
report_path = Path(sys.argv[1])
with open(report_path, 'r') as f:
    results = json.load(f)

# Extract key metrics
summary = results['summary_statistics']
total_tests = summary['total_tests']
pass_rate = summary['pass_rate'] * 100
overall_score = summary['overall_scores']['mean']
dimensions = summary['dimension_averages']

# Determine verdict
if pass_rate >= 95 and overall_score >= 8.5:
    verdict = "Production ready"
elif pass_rate >= 85 and overall_score >= 7.5:
    verdict = "Needs targeted improvements"
else:
    verdict = "Not ready - requires significant fixes"

# Find weakest dimensions
sorted_dims = sorted(dimensions.items(), key=lambda x: x[1])
weakest = sorted_dims[0]
second_weakest = sorted_dims[1]

# Generate insights markdown
insights = f"""# Agent Evaluation Insights - {sys.argv[2]}

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Tests Run:** {total_tests}
**Pass Rate:** {pass_rate:.1f}% ({summary['passed']}/{total_tests})
**Overall Score:** {overall_score:.1f}/10

## Quick Verdict
**{verdict}**

## Key Takeaway
The agent scored {overall_score:.1f}/10 across {total_tests} tests. Primary areas for improvement:
- **{weakest[0].replace('_', ' ').title()}**: {weakest[1]:.1f}/10 - Needs significant attention
- **{second_weakest[0].replace('_', ' ').title()}**: {second_weakest[1]:.1f}/10 - Requires optimization

---

## 📊 Results Overview

### Dimension Performance

| Dimension | Score | Status |
|-----------|-------|--------|
"""

# Add dimension rows
for dim_name, score in sorted(dimensions.items(), key=lambda x: x[1], reverse=True):
    status = "✓ Excellent" if score >= 9 else "✓ Good" if score >= 7.5 else "⚠️ Needs Work" if score >= 6 else "✗ Poor"
    dim_display = dim_name.replace('_', ' ').title()
    insights += f"| {dim_display} | {score:.1f}/10 | {status} |\n"

# Add performance by category
insights += "\n### Performance by Category\n\n"
insights += "| Category | Pass Rate | Avg Score |\n"
insights += "|----------|-----------|----------|\n"

for category, stats in results['performance_by_category'].items():
    insights += f"| {category} | {stats['pass_rate']*100:.1f}% | {stats['avg_score']:.1f}/10 |\n"

# Add critical issues section
insights += "\n---\n\n## 🚨 Critical Issues\n\n"

# Check for failures
if summary['failed'] > 0:
    insights += f"**{summary['failed']} tests failed.** Review detailed results for specifics.\n\n"
    insights += "To view failed tests:\n"
    insights += "```bash\n"
    insights += f"cat {report_path}\n"
    insights += "```\n\n"
else:
    insights += "No critical failures detected. All tests passed!\n\n"

# Action items
insights += "## ✅ Action Items\n\n"
insights += "### Priority 1: Improve " + weakest[0].replace('_', ' ').title() + "\n"
insights += f"**Current Score:** {weakest[1]:.1f}/10\n"
insights += "**Target Score:** 7.5+/10\n"
insights += f"**Impact:** Primary weakness affecting overall score\n\n"

insights += "### Priority 2: Optimize " + second_weakest[0].replace('_', ' ').title() + "\n"
insights += f"**Current Score:** {second_weakest[1]:.1f}/10\n"
insights += "**Target Score:** 7.5+/10\n\n"

# Next steps
insights += "---\n\n## 🎯 Next Steps\n\n"
insights += "1. **Review detailed results:**\n"
insights += f"   ```bash\n   cat {str(report_path).replace('.json', '.md')}\n   ```\n\n"
insights += "2. **Check individual test failures:**\n"
insights += f"   ```bash\n   ls {report_path.parent}/individual_results/\n   ```\n\n"
insights += "3. **Fix priority issues** and re-run evaluation\n\n"
insights += "4. **Save baseline** for future comparison:\n"
insights += "   ```bash\n"
insights += f"   python -m agent_trainings run --config {sys.argv[3]} --save-baseline v1.0.0\n"
insights += "   ```\n\n"

insights += "---\n\n"
insights += "**For detailed analysis, see:** " + str(report_path.name) + "\n"
insights += "**Generated by:** agent-training evaluation framework\n"

# Write insights file
insights_path = Path(sys.argv[4])
with open(insights_path, 'w') as f:
    f.write(insights)

print(f"✓ Insights saved to: {insights_path.name}")

PYTHON_SCRIPT

    python3 - "$REPORT_JSON" "$AGENT_NAME" "$EVAL_CONFIG" "$INSIGHTS_FILE" <<< "$PYTHON_SCRIPT"
    
    print_success "Insights report generated!"
}

################################################################################
# Main Execution
################################################################################

main() {
    print_banner
    
    validate_environment
    activate_venv
    prepare_tests
    create_config
    run_evaluation
    generate_insights
    
    echo ""
    echo -e "${GREEN}${BOLD}✓ Evaluation Complete!${NC}"
    echo ""
    echo -e "${CYAN}📄 View insights:${NC}"
    echo "   cat $INSIGHTS_FILE"
    echo ""
    echo -e "${CYAN}📊 View detailed report:${NC}"
    echo "   cat $OUTPUT_DIR/report_*.md"
    echo ""
}

# Run main function
main "$@"
