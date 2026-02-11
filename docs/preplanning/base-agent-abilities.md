# Base Agent Abilities

This document outlines the core capabilities and features that every Emonk agent should support. These abilities define the standard behavior, user interactions, and system architecture patterns.

---

## 1. On-Demand & Scheduled Tasks

Agents support both immediate on-demand execution and recurring scheduled tasks. Users can run any task directly or automate it for later.

### On-Demand Task Execution

Users can request tasks to execute immediately without scheduling.

- **Direct Execution:** User sends request → Agent executes immediately and returns results
  - Example: "Fetch competitor prices right now"
  - Example: "Generate a social media post about AI trends"
  - No scheduling or waiting required
  - Results streamed back to user in real-time

- **Synchronous Response:** Agent waits for task completion and returns full results
  - Useful for research, analysis, or information retrieval tasks
  - Timeout configurable per task (default 300 seconds)
  - Streaming support for long-running operations

- **Task Types:** Any skill-based operation can be executed on-demand
  - Web searches and data fetching
  - Content generation and formatting
  - Analysis and reporting
  - Social media operations

### Cron Job Management (Scheduled Tasks)

Users can also automate recurring tasks through a built-in cron job system with full visibility and control.

- **Setup Cron Jobs:** Users can define recurring tasks with standard cron syntax (e.g., `0 9 * * *` for daily at 9 AM)
  - Example: "Schedule a daily job to fetch competitor prices at 9 AM"
  - Agent parses natural language or accepts cron expressions
  - Jobs persist in the agent's memory layer (GCP Storage or local filesystem)

- **List Active Jobs:** Users can request a summary of all scheduled jobs with clear, scannable output
  - Quick status view showing: job ID, schedule, task description, last run, next run
  - Formatted for easy consumption (table or list format)
  - Includes execution history and pass/fail status

- **Cancel Jobs:** Users can remove or pause any scheduled job by ID or description
  - Example: "Cancel the daily competitor price job"
  - Agent confirms cancellation and updates memory

### Agent Responsibilities

- **Immediate Execution:** Route on-demand task requests to appropriate skills with minimal latency
- **Schedule Management:** Maintain a persistent cron registry in memory (JSON/YAML file in local storage or GCP Storage)
- **Scheduled Execution:** Trigger scheduled jobs at specified times using system cron daemon or equivalent scheduler
- **Logging:** Record every task execution (on-demand or scheduled) with timestamps, success/failure status, and output
- **Cleanup:** Remove expired or orphaned jobs automatically; archive old execution logs
- **Error Recovery:** Retry failed tasks with exponential backoff; alert user on repeated failures

---

## 2. Modular Skill Execution

Skills are the building blocks of agent capabilities. Each skill is a self-contained, reusable module that the agent can invoke to perform specific tasks.

### Skill Types

**Markdown Documentation Skills**
- Read-only instruction files that provide context or reference information
- Filename pattern: `*.md` within the skills directory
- Use case: Brand guidelines, API documentation, procedure checklists
- Loaded into context automatically when relevant task detected
- Example: `BRAND_VOICE.md` always loaded before content generation tasks

**Python Execution Skills**
- Executable scripts that perform logic or interact with external systems
- Filename pattern: `*.py` within the skills directory
- Invoked via the agent's built-in Shell execution capability
- Can accept arguments and return structured output (JSON, plain text)
- Example: `search-web.py`, `post-to-telegram.py`, `fetch-data.py`

### Skill Discovery & Loading

- Agent scans the skills directory on startup and indexes available skills
- Each skill YAML top (metadata) is included in the system prompt always
- Skill metadata includes: name, description, required arguments, output format
- Agent can dynamically request additional skills if not found in memory

### Skill Invocation Pattern

1. User requests a task → Agent determines required skills
2. Agent loads relevant skill documentation (.md files)
3. Agent executes skill script (.py file) via shell tool with appropriate arguments
4. Agent parses skill output and formats response for user
5. Skill result is logged for auditing and future context

**Example Flow:**
```
User: "Search for recent news on AI regulation"
  ↓
Agent detects web-search task
  ↓
Loads: skills/search-web.md (instructions)
  ↓
Executes: python skills/search-web.py --query "AI regulation" --limit 5
  ↓
Parses output → formats response
```

---

## 3. System Prompt Customization

Each agent instance can have a customized system prompt tailored to its domain, persona, and guidelines.

### Customization Points

- **Agent Persona:** Define how the agent introduces itself and communicates (e.g., formal, casual, technical)
- **Domain Knowledge:** Inject domain-specific instructions (e.g., "You are a college admissions advisor")
- **Safety Guidelines:** Specify what actions are permitted or prohibited
- **Response Constraints:** Define output format, tone, length preferences
- **Brand Voice:** Embed specific writing style, terminology, or compliance requirements

### Skill YAML Tops in System Prompt

All available skills' YAML metadata is **always included** in the system prompt. This ensures the agent has current knowledge of:
- Skill names and descriptions
- Required and optional parameters
- Expected output formats
- Preconditions and dependencies

**Example System Prompt Injection:**
```
You are a college recommendation advisor.
Domain: Higher education consulting

Available Skills:
- search-colleges.py (search college databases)
- fetch-rankings.py (retrieve rankings data)
- generate-essay-prompt.py (AI-powered prompt generation)

When generating recommendations, always:
1. Check current college rankings
2. Consider student profile (GPA, test scores, interests)
3. Use brand voice: friendly but authoritative
```

---

## 4. Multi-Channel Response & Communication

### Telegram Support

Agents can respond via Telegram Bot API for real-time user interaction.

- **Setup:** Agent registers webhook or polling endpoint
- **Message Types:** Text, markdown, buttons, inline queries
- **Flow:** User sends message → Agent processes → Response sent to Telegram
- **State Management:** Conversation history stored in memory for context
- **Media Support:** Can receive and send images, documents, audio (skill-dependent)

### Response Channels

- **Telegram Bot:** Primary user-facing channel for interactive conversations
- **Terminal Output:** For local development and debugging
- **GCP Storage Logs:** Structured logs synced to cloud for audit trails
- **Memory Files:** Persistent state (cron jobs, conversation history, memories)

---

## 5. Grounded Web Search with Vertex AI

Agents can perform intelligent web searches grounded in real-time information using Google's Vertex AI Search capabilities.

### Web Search Capabilities

- **Grounded Search:** Retrieves and cites sources automatically (reduces hallucinations)
- **Real-time Data:** Access to current web content, news, and trending information
- **Structured Results:** Returns formatted results suitable for further processing
- **Citation Tracking:** All search results include source URLs and confidence scores
- **Optional Integration:** Can be toggled on/off per task or globally

### Usage Pattern

- Agent identifies information need requiring current web data
- Calls `search-web.py` skill with grounded search enabled
- Vertex AI search returns results with citations
- Agent integrates results into response with proper attribution
- Example: "Based on a search dated [timestamp], [source]: [result]"

### Configuration

- Controlled via environment variable: `ENABLE_GROUNDED_SEARCH=true/false`
- Can be scoped per skill or globally in system prompt
- Requires GCP credentials (configured via `GOOGLE_APPLICATION_CREDENTIALS`)

---

## 6. Vertex AI LLM Integration

Agents natively integrate with any Vertex AI LLM model for flexible AI capabilities.

### Model Selection

- **Gemini 2.0 Flash:** Fast, cost-effective for simple tasks
- **Gemini 2.0 Pro:** Balance of speed and reasoning for most tasks
- **Gemini Experimental:** Cutting-edge models for complex reasoning
- **Custom Fine-tuned Models:** Support for enterprise-specific models

### Configuration

```env
VERTEX_AI_PROJECT_ID=your-gcp-project
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL_ID=gemini-2.0-flash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### LLM Capabilities

- **Cost Optimization:** Route simple tasks to Flash, complex tasks to Pro
- **Token Efficiency:** Context window up to 1M tokens for long conversations
- **Structured Output:** JSON schema validation for deterministic outputs
- **Function Calling:** Native tool/skill integration via Vertex AI function calling
- **Streaming:** Real-time token streaming for responsive user experience

### Response Quality

- Vertex AI models provide reasoning traces (via extended thinking where available)
- Agent can request explanations for transparency
- Multi-turn conversation support with full history context

---

## 7. Memory & Persistence Layer

### Storage Backends

**Local Development**
- Files stored in `./data/memory/` directory
- Formats: JSON, YAML, Markdown
- Includes: cron jobs, conversation history, skill cache

**GCP Storage (Production)**
- Syncs memory files to `gs://agent-memory/[agent-id]/`
- Automatic backup and versioning
- Survives container restarts
- Shared across agent replicas

### Memory Types

- **Cron Jobs Registry:** All scheduled tasks and execution history
- **Conversation Memory:** Multi-turn chat history per user/session
- **Skill Cache:** Downloaded or generated skill definitions
- **Brand Voice & Guidelines:** Persistent agent personality/rules
- **Execution Logs:** Structured logs with trace IDs

---

## 8. Built-in Agent Execution Tools

### Shell Execution Tool

Agents have a built-in capability to execute shell commands and scripts safely.

- **Restrictions:** Allowlist-based command execution (no `rm -rf`, etc.)
- **Timeout:** Commands auto-terminate after 300 seconds (configurable)
- **Output Capture:** Full stdout/stderr captured and returned to agent
- **Environment:** Can access environment variables, but not modify system state
- **Use Cases:** Run Python scripts, call CLI tools, fetch files, execute background tasks

### File Operations

- Read files: `cat`, `head`, `tail` (via shell tool)
- Write files: Through skill scripts (not direct agent write)
- Directory listing: `ls` command

### Common Patterns

```bash
# Execute a skill script
python skills/search-web.py --query "topic" --limit 5

# Read a markdown file for context
cat skills/BRAND_VOICE.md

# List available skills
ls skills/

# Check cron job status
cat data/memory/cron_jobs.json
```

---

## 9. Error Handling & Reliability

### Graceful Degradation

- If web search fails, agent continues with cached data or general knowledge
- If a skill is unavailable, agent notifies user instead of failing silently
- If LLM response times out, agent uses shorter request or simpler model

### Retry Strategies

- **Cron Jobs:** Exponential backoff (retry after 1s, 2s, 4s, then alert)
- **Skill Execution:** Automatic retry once on timeout, fail after 2 attempts
- **LLM Calls:** Retry on rate limit with exponential backoff
- **Web Search:** Fall back to cached results if API unavailable

### Logging & Observability

- All operations logged with trace IDs for debugging
- Error levels: DEBUG, INFO, WARN, ERROR, CRITICAL
- Structured JSON logs for parsing and alerting
- Log files: `logs/app.log` with automatic rotation

---

## 10. Agent Lifecycle

### Initialization

1. Load system prompt with customizations
2. Index available skills (scan skills directory)
3. Inject skill YAML metadata into context
4. Load cron job registry from memory
5. Connect to configured LLM (Vertex AI)
6. Start Telegram bot listener (if enabled)

### Runtime

- Listen for incoming messages (Telegram, terminal)
- Route tasks to appropriate skills
- Execute cron jobs on schedule
- Log all operations to local and cloud storage
- Maintain conversation context in memory

### Shutdown

- Flush in-flight operations
- Save any unsaved state to memory
- Sync local storage to GCP Storage
- Close connections gracefully

---

## 11. Configuration & Deployment

### Environment Variables

```env
# LLM Configuration
VERTEX_AI_PROJECT_ID=your-project-id
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL_ID=gemini-2.0-flash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Telegram (Optional)
TELEGRAM_BOT_TOKEN=your-token-here
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# Features
ENABLE_GROUNDED_SEARCH=true
ENABLE_TELEGRAM=true

# Paths
SKILLS_DIR=./skills/
MEMORY_DIR=./data/memory/
LOGS_DIR=./logs/

# GCP Storage (Production)
GCP_STORAGE_BUCKET=gs://agent-memory/
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/qa-credentials.json

# Run agent
python -m emonk.agent --local --debug
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /agent
COPY . .
RUN pip install -r requirements.txt
ENV GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp_credentials
CMD ["python", "-m", "emonk.agent"]
```

---

## 12. Design Principles

1. **Modularity:** Each capability is pluggable and independently testable
2. **User-Centric:** Clear, scannable outputs for non-technical users
3. **Observability:** Full logging and debugging trails for troubleshooting
4. **Safety:** Allowlist-based execution, no destructive operations
5. **Persistence:** State survives restarts via cloud storage
6. **Extensibility:** New skills and LLMs can be added without core changes
7. **Performance:** Skill caching and lazy-loading to minimize context bloat
8. **Transparency:** Citations and reasoning traces for user trust

---

## Example: Complete Agent Interaction Flow

### On-Demand Task Execution

```
User (Telegram): "Fetch competitor prices right now"

Agent Processing:
  1. Parse intent → identify web-search + data-fetch task
  2. Load: skills/search-web.md
  3. Execute immediately: python skills/fetch-competitor-prices.py
  4. Wait for completion (timeout: 300s)
  5. Parse results → format for user consumption
  6. Return results to user via Telegram
  7. Log execution to: logs/app.log + GCP Storage
  
Agent Response (within seconds):
  📊 Current Competitor Prices
  
  Competitor A: $99.99 (↓ 5% from yesterday)
  Competitor B: $129.99 (→ no change)
  Competitor C: $89.99 (↑ 2% from yesterday)
  
  Last updated: 2025-02-07 10:30 AM
  (No scheduling required - executed immediately on your request)
```

### Scheduled Task Setup

```
User (Telegram): "Schedule a daily job to fetch competitor prices at 9 AM"

Agent Processing:
  1. Parse intent → cron job setup
  2. Create cron registry entry:
     {
       "id": "competitor-prices-001",
       "schedule": "0 9 * * *",
       "task": "fetch-competitor-prices",
       "created_at": "2025-02-07T10:00:00Z"
     }
  3. Confirm to user: "✅ Job scheduled. Will fetch competitor prices daily at 9 AM EST."
  4. Store cron entry in: data/memory/cron_jobs.json + gs://agent-memory/agent-id/cron_jobs.json
  5. When 9 AM arrives:
     - Execute: python skills/fetch-competitor-prices.py
     - Parse results → format for user
     - Send results via Telegram
     - Log execution to: logs/app.log + GCP Storage
     - Update memory: "last_run": "2025-02-08T09:00:00Z", "status": "success"

Agent Response:
  ✅ Daily job scheduled! I'll fetch competitor prices every day at 9 AM EST and send you the results.
```

### Managing Scheduled Jobs

```
User (Telegram): "Show me my scheduled jobs"

Agent Response:
  ✅ Your Scheduled Jobs
  
  1. competitor-prices-001
     Schedule: Daily at 9:00 AM EST
     Task: Fetch competitor prices
     Last Run: 2025-02-08 09:02 AM (SUCCESS)
     Next Run: 2025-02-09 09:00 AM
  
  2. morning-briefing-002
     Schedule: Mon-Fri at 9:00 AM EST
     Task: Generate daily briefing
     Last Run: 2025-02-07 09:05 AM (SUCCESS)
     Next Run: 2025-02-10 09:00 AM

User (Telegram): "Cancel competitor-prices-001"

Agent Response:
  ✅ Cancelled job 'competitor-prices-001'. No more daily price updates.
  (Updates memory and removes cron entry)
```

### Complex Multi-Step Workflow

```
User (Telegram): "Schedule a daily job to search for AI news at 8 AM, then post the top 3 results to my feed"

Agent Processing:
  1. Parse intent → cron job setup + skill chaining
  2. Load: skills/search-web.md, skills/post-content.md
  3. Create cron registry entry:
     {
       "id": "news-scheduler-001",
       "schedule": "0 8 * * *",
       "task": "search_and_post",
       "created_at": "2025-02-07T10:00:00Z"
     }
  4. Confirm to user: "✅ Job scheduled. Will search for AI news daily at 8 AM EST and post to your feed."
  5. Store cron entry in: data/memory/cron_jobs.json + gs://agent-memory/agent-id/cron_jobs.json
  6. When 8 AM arrives:
     - Execute: python skills/search-web.py --query "AI news" --limit 3
     - Parse results → format with brand voice
     - Execute: python skills/post-to-telegram.py --content "[formatted results]"
     - Log execution to: logs/app.log + GCP Storage
     - Update memory: "last_run": "2025-02-08T08:00:00Z", "status": "success"
```

---

## Next Steps for Implementation

1. **Cron Daemon:** Integrate with system cron or use APScheduler for Python
2. **Skill Registry:** Build indexing and caching system for skills
3. **Memory Layer:** Implement GCP Storage sync with local cache
4. **Vertex AI Client:** Wrap Vertex AI SDK with custom routing logic
5. **Telegram Integration:** Set up bot polling or webhook listener
6. **Logging:** Implement structured JSON logging with trace IDs
7. **Error Handling:** Build retry logic and graceful degradation
8. **Testing:** Unit tests for each ability, integration tests for flows

