# Social Media Agent: Cursor-Ready Implementation Guide

**Project Goal:** Build a local-first, security-hardened AI agent for automated social media posting with GCP Storage memory, terminal execution capabilities, and efficient debugging.

**Strategy:** Selective extraction ("The Cursor Approach") - clone core capabilities, strip unnecessary complexity, develop custom CLI-based skills.

---

## Executive Summary

This guide outlines a **4-week implementation plan** to build a purpose-built social media automation agent optimized for local Docker development with production GCP deployment.

**What We're Building:**
- **Local-first development:** Docker container with hot-reload, full local testing
- **GCP Storage memory:** File-based persistent memory synced to Cloud Storage
- **Terminal execution skill:** Agent can run commands, cat markdown files, execute Python scripts
- **Custom CLI skills:** Social media posting via command-line tools (not direct API calls)
- **Vertex AI Grounded Search:** Web search optimized through Google's grounded search
- **Efficient logging:** Structured logs with log levels, easy debugging without noise
- **Cost-optimized LLM routing:** Gemini Flash for simple tasks, Opus for complex reasoning

**What We're NOT Building:**
- WhatsApp/Discord/Slack integrations (Telegram only)
- Browser automation (too fragile)
- Marketplace skill system (security risk)
- Direct API integrations (use CLI tools instead)

**Key Differentiators from Vanilla OpenClaw:**
1. **Local-first:** Full development cycle in Docker, deploy to GCP when ready
2. **File-system native:** Agent interacts via terminal commands (cat, ls, uv run)
3. **Observable:** Structured logging with trace IDs, easy to follow execution flow
4. **CLI-driven skills:** Each skill is a command-line tool with clear input/output
5. **Brand-aware:** BRAND_VOICE.md always loaded before content generation

**Timeline:** 4 weeks (40-60 hours total engineering time)  
**Infrastructure Cost:** $5-15/month local development, $30-50/month GCP production  
**Success Metric:** 20+ social posts/week generated with <5% brand voice deviation

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Social Media Agent                        │
│                    (Docker Container)                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────────┐             │
│  │   Telegram   │────────▶│  Gateway Daemon  │             │
│  │   Bot API    │         │  (Port 18789)    │             │
│  └──────────────┘         └────────┬─────────┘             │
│                                     │                        │
│                                     ▼                        │
│  ┌──────────────────────────────────────────────┐          │
│  │         Agent Core (LangGraph)                │          │
│  │  - Task routing                               │          │
│  │  - LLM calls (Gemini Flash / Opus)           │          │
│  │  - Skill orchestration                       │          │
│  └──────────────┬────────────────────────────┬──┘          │
│                 │                             │             │
│                 ▼                             ▼             │
│  ┌─────────────────────┐      ┌─────────────────────┐     │
│  │  Terminal Executor  │      │  Memory Manager     │     │
│  │  - Run shell cmds   │      │  - GCP Storage sync │     │
│  │  - cat .md files    │      │  - Local cache      │     │
│  │  - uv run scripts   │      │  - BRAND_VOICE.md   │     │
│  └─────────────────────┘      └─────────────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │         Custom CLI Skills                     │          │
│  │  ├─ ./skills/post-to-x.sh                    │          │
│  │  ├─ ./skills/post-to-linkedin.py             │          │
│  │  ├─ ./skills/search-web.py (Vertex grounded) │          │
│  │  └─ ./skills/generate-content.py             │          │
│  └──────────────────────────────────────────────┘          │
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │         Structured Logging                    │          │
│  │  - Log levels (DEBUG/INFO/WARN/ERROR)        │          │
│  │  - Trace IDs for request tracking            │          │
│  │  - JSON output for parsing                   │          │
│  │  - File rotation (logs/app.log)              │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌─────────────────┐      ┌─────────────────────┐
│  Local Storage  │      │   GCP Storage       │
│  (Development)  │      │   (Production)      │
│  ./data/memory/ │◀────▶│ gs://agent-memory/  │
└─────────────────┘      └─────────────────────┘
```

**Key Design Decisions:**
1. **Docker-first:** Entire agent runs in container, easy to test and deploy
2. **File-system as API:** Agent interacts with skills via terminal commands
3. **GCP Storage sync:** Memory files persist to cloud but cached locally
4. **CLI skills:** Each social media operation is a standalone script
5. **Structured logs:** JSON-formatted logs with trace IDs for debugging

---

## Components to Extract & Build

### 1. Gateway Daemon (Core Controller)
**What:** Background process that maintains persistent connection to Telegram and routes commands to the agent.

**Why We Need It:** 
- Enables "always-on" agent that can send proactive updates
- Handles message queuing and rate limiting
- Provides clean separation between UI (Telegram) and logic (agent core)

**What to Extract from OpenClaw:**
- Loopback-only binding pattern (`127.0.0.1:18789`)
- Message event queue architecture
- Graceful shutdown and restart logic

**Implementation Notes:**
```typescript
// Core pattern to replicate
class GatewayDaemon {
  private telegramClient: TelegramBot;
  private agentCore: AgentCore;
  private messageQueue: MessageQueue;
  private logger: Logger;
  
  async start() {
    // Bind to loopback only (Docker internal networking)
    this.server.listen(18789, '127.0.0.1');
    
    // Initialize structured logger
    this.logger = new Logger({ service: 'gateway', level: 'INFO' });
    
    // Initialize Telegram bot
    this.telegramClient = new TelegramBot(process.env.TELEGRAM_TOKEN);
    
    // Route incoming messages to agent
    this.telegramClient.on('message', async (msg) => {
      const traceId = generateTraceId();
      this.logger.info('Received message', { traceId, chatId: msg.chat.id });
      
      try {
        const response = await this.agentCore.processMessage(msg, traceId);
        await this.telegramClient.sendMessage(msg.chat.id, response);
        this.logger.info('Sent response', { traceId, length: response.length });
      } catch (error) {
        this.logger.error('Message processing failed', { traceId, error });
        await this.telegramClient.sendMessage(
          msg.chat.id, 
          '❌ Error processing request. Check logs for details.'
        );
      }
    });
  }
}
```

---

### 2. Terminal Executor Skill
**What:** Skill that allows the agent to execute shell commands, read files, and run Python scripts.

**Why We Need It:**
- Agent can inspect memory files: `cat ./data/memory/BRAND_VOICE.md`
- Agent can list available skills: `ls ./skills/`
- Agent can run content generation: `uv run ./skills/generate-content.py "topic"`
- Agent can execute social media CLI tools

**Security Implementation:**
```typescript
// Terminal executor with allowlist-based security
class TerminalExecutor {
  private allowedCommands = ['cat', 'ls', 'uv'];
  private allowedPaths = ['./data/memory/', './skills/', './content/'];
  private logger: Logger;
  
  async execute(command: string, traceId: string): Promise<string> {
    this.logger.debug('Execute request', { traceId, command });
    
    // Parse command
    const [cmd, ...args] = command.split(' ');
    
    // Validate command is allowed
    if (!this.allowedCommands.includes(cmd)) {
      throw new Error(`Command not allowed: ${cmd}`);
    }
    
    // Validate paths are within allowed directories
    for (const arg of args) {
      if (arg.startsWith('./') || arg.startsWith('/')) {
        const isAllowed = this.allowedPaths.some(p => arg.startsWith(p));
        if (!isAllowed) {
          throw new Error(`Path not allowed: ${arg}`);
        }
      }
    }
    
    // Execute in sandboxed environment
    const result = await execAsync(command, {
      cwd: '/app',
      timeout: 30000, // 30 second timeout
      env: {
        ...process.env,
        PATH: '/usr/local/bin:/usr/bin:/bin' // Restricted PATH
      }
    });
    
    this.logger.info('Command executed', { 
      traceId, 
      command, 
      exitCode: result.exitCode,
      outputLength: result.stdout.length 
    });
    
    return result.stdout;
  }
}

// Example usage in agent
const brandVoice = await terminalExecutor.execute(
  'cat ./data/memory/BRAND_VOICE.md',
  traceId
);

const contentDraft = await terminalExecutor.execute(
  'uv run ./skills/generate-content.py "AI agent evaluation frameworks"',
  traceId
);
```

**Command Allowlist:**
- `cat <file>` - Read markdown files (memory, brand voice, drafts)
- `ls <dir>` - List files in directory
- `uv run <script>` - Execute Python scripts with uv
- `bash ./skills/<script>.sh` - Execute shell scripts (if needed)

---

### 3. GCP Storage Memory System
**What:** File-based persistent memory with local cache and GCP Storage sync.

**Why This Approach:**
- **Simple:** Agent reads/writes markdown files (familiar format)
- **Observable:** Can manually inspect `./data/memory/BRAND_VOICE.md` anytime
- **Persistent:** GCP Storage ensures memory survives container restarts
- **Offline-capable:** Local cache allows development without internet

**File Structure:**
```
./data/memory/
├── BRAND_VOICE.md          # Core brand guidelines (always loaded)
├── CAMPAIGN_CONTEXT.md     # Active campaigns and themes
├── CONVERSATION_HISTORY/   # Recent conversations (rolling window)
│   ├── 2026-02-07.md
│   └── 2026-02-06.md
├── POSTS_ARCHIVE/          # Published posts for reference
│   ├── 2026-02-week1.md
│   └── 2026-01-week4.md
└── METRICS/                # Performance data
    └── weekly_stats.json
```

**Memory Manager Implementation:**
```typescript
class MemoryManager {
  private localStorage = './data/memory';
  private gcsBucket = 'gs://social-agent-memory';
  private logger: Logger;
  
  async loadBrandVoice(traceId: string): Promise<string> {
    this.logger.debug('Loading brand voice', { traceId });
    
    // Always read from local cache (fast)
    const localPath = `${this.localStorage}/BRAND_VOICE.md`;
    if (fs.existsSync(localPath)) {
      return fs.readFileSync(localPath, 'utf-8');
    }
    
    // If not in cache, sync from GCS
    await this.syncFromGCS('BRAND_VOICE.md');
    return fs.readFileSync(localPath, 'utf-8');
  }
  
  async saveConversation(date: string, content: string, traceId: string) {
    this.logger.info('Saving conversation', { traceId, date });
    
    // Write to local cache
    const localPath = `${this.localStorage}/CONVERSATION_HISTORY/${date}.md`;
    fs.writeFileSync(localPath, content);
    
    // Async sync to GCS (non-blocking)
    this.syncToGCS(`CONVERSATION_HISTORY/${date}.md`).catch(err => {
      this.logger.error('GCS sync failed', { traceId, error: err });
    });
  }
  
  private async syncToGCS(filePath: string) {
    if (process.env.NODE_ENV === 'development') {
      // Skip GCS sync in local development
      return;
    }
    
    await execAsync(
      `gsutil cp ${this.localStorage}/${filePath} ${this.gcsBucket}/${filePath}`
    );
  }
  
  private async syncFromGCS(filePath: string) {
    await execAsync(
      `gsutil cp ${this.gcsBucket}/${filePath} ${this.localStorage}/${filePath}`
    );
  }
}
```

**BRAND_VOICE.md Template:**
```markdown
# Brand Voice Guidelines

## Core Values
- Authentic, data-driven insights
- No hype or empty promises
- Technical but accessible
- Focus on building, not theorizing

## Tone Guidelines
- Use "we" not "I" (team voice)
- Lead with questions, not declarations
- Include concrete examples, avoid abstractions
- Be helpful without being condescending

## Writing Style
- Sentence length: 10-20 words average
- Paragraph length: 2-4 sentences
- Use active voice
- Minimize jargon unless explaining technical concepts

## Platform-Specific Adaptations

### X/Twitter (280 chars)
- Start with hook (question or bold statement)
- Include 1-2 hashtags maximum
- Emoji: Max 1 per tweet
- Tone: Conversational, slightly informal

### LinkedIn (1300 chars)
- Professional but approachable
- Data-driven claims with sources
- Structure: Hook → Context → Insight → CTA
- Hashtags: 3-5 relevant tags

### Instagram
- Visual-first (captions support image)
- Storytelling format
- Include call-to-action
- Emojis: 2-3 strategically placed

## Forbidden Phrases
- "Game-changer", "Revolutionary", "Disrupting"
- "Unlock", "Secrets", "Hack" (unless literal hacking)
- Excessive superlatives ("amazing", "incredible")
- Generic AI speak ("leverage synergies")

## Example Posts

### Good Example (X)
"Built an agent eval framework that caught 18 brand voice failures before they shipped.

The secret? Personas. Same query, different user types = different quality bars.

Write-up: [link]"

### Bad Example (X)
"🚀 Revolutionary AI framework unlocking game-changing insights! 

Leverage our cutting-edge synergies to disrupt the agent evaluation space! 

#AI #Innovation #GameChanger"

## Content Generation Checklist
- [ ] Passes forbidden phrase filter
- [ ] Includes concrete example or data point
- [ ] Appropriate length for platform
- [ ] Tone matches target audience
- [ ] CTA is clear and valuable
```

---

### 4. Custom CLI Skills (File-System Based)
**What:** Each skill is a standalone CLI tool that the agent executes via terminal.

**Why This Approach:**
- **Testable:** Can run `./skills/post-to-x.sh "Hello"` manually
- **Observable:** Agent's tool usage visible in terminal output
- **Debuggable:** Add `set -x` to shell scripts to see execution
- **Portable:** Skills work outside agent (can run standalone)

**Skill Template Structure:**
```bash
# ./skills/post-to-x.sh
#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars

# Skill: Post to X/Twitter
# Usage: ./skills/post-to-x.sh "Tweet content"
# Returns: JSON with tweet URL and ID

CONTENT="$1"
TRACE_ID="${2:-unknown}"

# Validate input
if [ -z "$CONTENT" ]; then
  echo '{"success": false, "error": "No content provided"}' >&2
  exit 1
fi

if [ ${#CONTENT} -gt 280 ]; then
  echo '{"success": false, "error": "Content exceeds 280 characters"}' >&2
  exit 1
fi

# Log execution (structured JSON)
echo "{\"level\": \"INFO\", \"traceId\": \"$TRACE_ID\", \"skill\": \"post-to-x\", \"action\": \"posting\"}" >&2

# Post to X using API (example with curl)
RESPONSE=$(curl -s -X POST "https://api.x.com/2/tweets" \
  -H "Authorization: Bearer $X_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$CONTENT\"}")

# Parse response
TWEET_ID=$(echo "$RESPONSE" | jq -r '.data.id')
TWEET_URL="https://x.com/user/status/$TWEET_ID"

# Return structured result (stdout)
echo "{\"success\": true, \"tweetId\": \"$TWEET_ID\", \"url\": \"$TWEET_URL\"}"

# Log success
echo "{\"level\": \"INFO\", \"traceId\": \"$TRACE_ID\", \"skill\": \"post-to-x\", \"action\": \"posted\", \"tweetId\": \"$TWEET_ID\"}" >&2
```

**Content Generator Skill (Python):**
```python
#!/usr/bin/env python3
"""
Skill: Generate platform-specific content
Usage: uv run ./skills/generate-content.py "topic" --platform x
Returns: JSON with generated content
"""

import sys
import json
import os
from pathlib import Path

def load_brand_voice():
    """Load brand voice guidelines from memory"""
    brand_voice_path = Path("./data/memory/BRAND_VOICE.md")
    if not brand_voice_path.exists():
        raise FileNotFoundError("BRAND_VOICE.md not found")
    
    return brand_voice_path.read_text()

def generate_content(topic: str, platform: str, trace_id: str) -> dict:
    """Generate content using LLM with brand voice context"""
    # Log execution
    log_event("INFO", "generate-content", "generating", trace_id, {"topic": topic, "platform": platform})
    
    # Load brand voice
    brand_voice = load_brand_voice()
    
    # Build prompt
    prompt = f"""Based on these brand guidelines:

{brand_voice}

Generate a {platform} post about: {topic}

Requirements:
- Follow brand voice exactly
- Match platform length constraints
- Include concrete examples
- No forbidden phrases

Output format: Just the post content, no preamble."""

    # Call LLM (Gemini Flash for content generation)
    # This would use actual Vertex AI client
    content = call_gemini_flash(prompt)
    
    # Validate against brand voice
    if any(phrase in content.lower() for phrase in ["game-changer", "revolutionary"]):
        log_event("WARN", "generate-content", "forbidden_phrase_detected", trace_id)
        raise ValueError("Content contains forbidden phrase")
    
    log_event("INFO", "generate-content", "generated", trace_id, {"length": len(content)})
    
    return {
        "success": True,
        "content": content,
        "platform": platform,
        "topic": topic
    }

def log_event(level: str, skill: str, action: str, trace_id: str, data: dict = None):
    """Write structured log to stderr"""
    log = {
        "level": level,
        "traceId": trace_id,
        "skill": skill,
        "action": action,
        **(data or {})
    }
    print(json.dumps(log), file=sys.stderr)

if __name__ == "__main__":
    topic = sys.argv[1]
    platform = sys.argv[2] if len(sys.argv) > 2 else "x"
    trace_id = os.getenv("TRACE_ID", "unknown")
    
    try:
        result = generate_content(topic, platform, trace_id)
        print(json.dumps(result))
    except Exception as e:
        log_event("ERROR", "generate-content", "failed", trace_id, {"error": str(e)})
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)
```

**Skills Directory Structure:**
```
./skills/
├── README.md                       # Skill documentation

# Core Infrastructure Skills
├── terminal-executor.py            # Execute whitelisted commands
├── memory-manager.py               # Load/save memory files

# Research & Intelligence Skills
├── search-web.py                   # Vertex AI Grounded Search
├── research-topic.py               # Deep research on topic (multi-source)
├── analyze-competitor.py           # Analyze competitor social presence
├── identify-trends.py              # Find trending topics in niche

# Campaign Planning Skills (World-Class Social Media Manager)
├── create-campaign.py              # Research → Strategy → Content Calendar
├── generate-campaign-posts.py      # Create all posts for campaign
├── analyze-post-performance.py     # Review metrics from past posts
├── suggest-posting-times.py        # Optimal times based on audience data

# Content Generation Skills
├── generate-content.py             # LLM content generation (platform-specific)
├── adapt-content.py                # Adapt single post to multiple platforms
├── generate-image-prompt.py        # Create DALL-E/Midjourney prompts
├── write-caption.py                # Write engaging captions

# Posting & Scheduling Skills
├── post-to-x.sh                    # Post to X/Twitter
├── post-to-linkedin.py             # Post to LinkedIn (Python with API)
├── post-to-instagram.py            # Post to Instagram (via Mixpost)
├── schedule-post.py                # Add post to cron job queue
├── list-scheduled-posts.py         # Show upcoming scheduled posts

# Approval & Review Skills
├── send-approval-email.py          # Email campaign for approval
├── parse-approval-response.py      # Parse "approve" from email reply
├── generate-preview.py             # Create visual preview of campaign

# Analytics & Optimization Skills
├── fetch-metrics.py                # Get posting metrics from APIs
├── analyze-engagement.py           # Analyze what performs best
├── generate-weekly-report.py       # Weekly performance summary
```

**New Campaign Workflow Skills:**

**1. Campaign Creator (`create-campaign.py`):**
```python
#!/usr/bin/env python3
"""
Skill: Research and create complete social media campaign

This skill mimics what a world-class social media manager would do:
1. Research topic thoroughly (trends, competitors, audience)
2. Develop content strategy
3. Create content calendar with optimal posting times
4. Generate post ideas for entire campaign

Usage: uv run ./skills/create-campaign.py "topic" --duration 4weeks
Returns: JSON with campaign plan, content calendar, post ideas
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

def research_topic(topic: str, trace_id: str) -> dict:
    """Deep research on topic using web search + competitor analysis"""
    log_event("INFO", "create-campaign", "researching", trace_id, {"topic": topic})
    
    # 1. Search for trending content on topic
    trends = call_skill("search-web.py", [topic, "--max-results", "10"])
    
    # 2. Analyze top competitors
    competitors = call_skill("analyze-competitor.py", [topic])
    
    # 3. Identify content gaps and opportunities
    analysis = analyze_research_data(trends, competitors)
    
    return {
        "trending_angles": analysis["angles"],
        "competitor_insights": analysis["gaps"],
        "audience_interests": analysis["interests"]
    }

def develop_content_strategy(research: dict, duration_weeks: int) -> dict:
    """Create content strategy based on research"""
    
    # Load brand voice for strategy alignment
    brand_voice = load_file("./data/memory/BRAND_VOICE.md")
    
    prompt = f"""Based on this research:
{json.dumps(research, indent=2)}

And these brand guidelines:
{brand_voice}

Create a {duration_weeks}-week social media campaign strategy with:
1. Campaign theme and key messages
2. Content pillars (3-5 main topics)
3. Posting cadence (how often per platform)
4. Engagement tactics
5. Success metrics

Output JSON format."""

    strategy = call_llm("claude-opus", prompt)
    
    return json.loads(strategy)

def create_content_calendar(strategy: dict, duration_weeks: int) -> list:
    """Generate content calendar with specific post slots"""
    
    # Get optimal posting times based on past performance
    optimal_times = call_skill("suggest-posting-times.py", [])
    
    calendar = []
    start_date = datetime.now()
    
    for week in range(duration_weeks):
        for day in range(7):
            post_date = start_date + timedelta(weeks=week, days=day)
            
            # Determine which platforms to post on this day
            # (e.g., X daily, LinkedIn 3x/week, Instagram 2x/week)
            platforms = get_platforms_for_day(day, strategy["posting_cadence"])
            
            for platform in platforms:
                # Get optimal time for this platform
                post_time = optimal_times[platform][day % len(optimal_times[platform])]
                
                # Assign content pillar for this post
                pillar = strategy["content_pillars"][len(calendar) % len(strategy["content_pillars"])]
                
                calendar.append({
                    "date": post_date.strftime("%Y-%m-%d"),
                    "time": post_time,
                    "platform": platform,
                    "content_pillar": pillar,
                    "post_id": f"post_{len(calendar) + 1}"
                })
    
    return calendar

def generate_post_ideas(calendar: list, strategy: dict) -> list:
    """Generate specific post ideas for each calendar slot"""
    
    brand_voice = load_file("./data/memory/BRAND_VOICE.md")
    
    post_ideas = []
    
    for slot in calendar:
        prompt = f"""Create a post idea for:
Platform: {slot['platform']}
Content Pillar: {slot['content_pillar']}
Campaign Theme: {strategy['theme']}
Date: {slot['date']}

Brand Voice: {brand_voice}

Provide:
1. Post topic/angle
2. Key message
3. Hook/opening line
4. Call-to-action

Output JSON."""

        idea = call_llm("gemini-flash", prompt)
        
        post_ideas.append({
            **slot,
            "idea": json.loads(idea)
        })
    
    return post_ideas

def create_campaign(topic: str, duration_weeks: int, trace_id: str) -> dict:
    """Full campaign creation workflow"""
    
    log_event("INFO", "create-campaign", "starting", trace_id, {
        "topic": topic,
        "duration": f"{duration_weeks} weeks"
    })
    
    # Step 1: Research
    research = research_topic(topic, trace_id)
    
    # Step 2: Strategy
    strategy = develop_content_strategy(research, duration_weeks)
    
    # Step 3: Content Calendar
    calendar = create_content_calendar(strategy, duration_weeks)
    
    # Step 4: Post Ideas
    post_ideas = generate_post_ideas(calendar, strategy)
    
    # Step 5: Save campaign to memory
    campaign = {
        "created": datetime.now().isoformat(),
        "topic": topic,
        "duration_weeks": duration_weeks,
        "research": research,
        "strategy": strategy,
        "calendar": calendar,
        "post_ideas": post_ideas,
        "status": "pending_approval"
    }
    
    save_campaign(campaign)
    
    log_event("INFO", "create-campaign", "completed", trace_id, {
        "posts_planned": len(post_ideas),
        "platforms": list(set(p["platform"] for p in calendar))
    })
    
    return campaign

if __name__ == "__main__":
    topic = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 4  # Default 4 weeks
    trace_id = os.getenv("TRACE_ID", "unknown")
    
    try:
        campaign = create_campaign(topic, duration, trace_id)
        print(json.dumps({"success": True, "campaign": campaign}))
    except Exception as e:
        log_event("ERROR", "create-campaign", "failed", trace_id, {"error": str(e)})
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)
```

**2. Campaign Post Generator (`generate-campaign-posts.py`):**
```python
#!/usr/bin/env python3
"""
Skill: Generate all posts for a campaign

Takes campaign plan and generates actual post content for each slot,
ensuring consistent messaging and brand voice across all posts.

Usage: uv run ./skills/generate-campaign-posts.py campaign_id
Returns: JSON with all generated posts
"""

import sys
import json
from pathlib import Path

def generate_campaign_posts(campaign_id: str, trace_id: str) -> list:
    """Generate all posts for campaign"""
    
    # Load campaign plan
    campaign = load_campaign(campaign_id)
    brand_voice = load_file("./data/memory/BRAND_VOICE.md")
    
    generated_posts = []
    
    for post_idea in campaign["post_ideas"]:
        log_event("INFO", "generate-campaign-posts", "generating", trace_id, {
            "post_id": post_idea["post_id"],
            "platform": post_idea["platform"]
        })
        
        # Generate actual post content
        content = call_skill("generate-content.py", [
            post_idea["idea"]["topic"],
            "--platform", post_idea["platform"],
            "--hook", post_idea["idea"]["hook"],
            "--cta", post_idea["idea"]["cta"]
        ])
        
        # Validate against brand voice
        if validate_brand_voice(content, brand_voice):
            generated_posts.append({
                **post_idea,
                "content": content,
                "status": "ready_for_approval"
            })
        else:
            log_event("WARN", "generate-campaign-posts", "brand_voice_violation", trace_id, {
                "post_id": post_idea["post_id"]
            })
            generated_posts.append({
                **post_idea,
                "content": content,
                "status": "needs_revision",
                "issue": "brand_voice_violation"
            })
    
    # Save generated posts to campaign
    campaign["generated_posts"] = generated_posts
    campaign["status"] = "ready_for_approval"
    save_campaign(campaign)
    
    return generated_posts

if __name__ == "__main__":
    campaign_id = sys.argv[1]
    trace_id = os.getenv("TRACE_ID", "unknown")
    
    try:
        posts = generate_campaign_posts(campaign_id, trace_id)
        print(json.dumps({"success": True, "posts": posts, "count": len(posts)}))
    except Exception as e:
        log_event("ERROR", "generate-campaign-posts", "failed", trace_id, {"error": str(e)})
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)
```

**3. Email Approval Sender (`send-approval-email.py`):**
```python
#!/usr/bin/env python3
"""
Skill: Send campaign approval email

Emails campaign preview to stakeholders for approval before scheduling.
Includes visual preview of posts and easy approve/reject links.

Usage: uv run ./skills/send-approval-email.py campaign_id --to user@example.com
Returns: JSON with email sent confirmation
"""

import sys
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def generate_email_preview(campaign: dict) -> str:
    """Generate HTML email with campaign preview"""
    
    html = f"""
    <html>
    <head>
        <style>
            .post {{ border: 1px solid #ccc; padding: 15px; margin: 10px 0; }}
            .platform {{ color: #666; font-size: 12px; }}
            .content {{ margin: 10px 0; }}
            .approve-btn {{ background: #28a745; color: white; padding: 10px 20px; text-decoration: none; }}
            .reject-btn {{ background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>Campaign Approval Request: {campaign['topic']}</h1>
        <p><strong>Duration:</strong> {campaign['duration_weeks']} weeks</p>
        <p><strong>Total Posts:</strong> {len(campaign['generated_posts'])}</p>
        
        <h2>Campaign Strategy</h2>
        <p>{campaign['strategy']['theme']}</p>
        
        <h2>Sample Posts (First 5)</h2>
    """
    
    # Show first 5 posts as preview
    for post in campaign['generated_posts'][:5]:
        html += f"""
        <div class="post">
            <div class="platform">{post['platform']} • {post['date']} at {post['time']}</div>
            <div class="content">{post['content']}</div>
        </div>
        """
    
    html += f"""
        <p><em>...and {len(campaign['generated_posts']) - 5} more posts</em></p>
        
        <h2>Approve or Reject</h2>
        <p>
            <a href="mailto:agent@yourcompany.com?subject=APPROVE-{campaign['id']}" class="approve-btn">
                ✅ Approve Campaign
            </a>
            <a href="mailto:agent@yourcompany.com?subject=REJECT-{campaign['id']}" class="reject-btn">
                ❌ Request Revisions
            </a>
        </p>
        
        <p><small>Or reply with "APPROVE" or "REJECT" in the subject line.</small></p>
    </body>
    </html>
    """
    
    return html

def send_approval_email(campaign_id: str, recipients: list, trace_id: str):
    """Send campaign approval email"""
    
    log_event("INFO", "send-approval-email", "sending", trace_id, {
        "campaign_id": campaign_id,
        "recipients": recipients
    })
    
    campaign = load_campaign(campaign_id)
    
    # Create email
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Campaign Approval: {campaign['topic']}"
    msg['From'] = os.getenv("SMTP_FROM_EMAIL")
    msg['To'] = ", ".join(recipients)
    
    # Generate HTML preview
    html_body = generate_email_preview(campaign)
    msg.attach(MIMEText(html_body, 'html'))
    
    # Send via SMTP
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(
            os.getenv("SMTP_USERNAME"),
            os.getenv("SMTP_PASSWORD")
        )
        server.send_message(msg)
    
    # Update campaign status
    campaign['status'] = 'awaiting_approval'
    campaign['approval_sent_at'] = datetime.now().isoformat()
    campaign['approval_recipients'] = recipients
    save_campaign(campaign)
    
    log_event("INFO", "send-approval-email", "sent", trace_id, {
        "campaign_id": campaign_id
    })
    
    return {"email_sent": True, "recipients": recipients}

if __name__ == "__main__":
    campaign_id = sys.argv[1]
    recipients = sys.argv[2].split(",") if len(sys.argv) > 2 else [os.getenv("DEFAULT_APPROVAL_EMAIL")]
    trace_id = os.getenv("TRACE_ID", "unknown")
    
    try:
        result = send_approval_email(campaign_id, recipients, trace_id)
        print(json.dumps({"success": True, **result}))
    except Exception as e:
        log_event("ERROR", "send-approval-email", "failed", trace_id, {"error": str(e)})
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)
```

**4. Cron Job Scheduler (`schedule-campaign.py`):**
```python
#!/usr/bin/env python3
"""
Skill: Schedule all campaign posts as cron jobs

After approval, creates cron jobs for all posts in campaign.
Each post gets its own cron entry at the specified date/time.

Usage: uv run ./skills/schedule-campaign.py campaign_id
Returns: JSON with scheduled post count
"""

import sys
import json
from datetime import datetime
from crontab import CronTab

def schedule_campaign(campaign_id: str, trace_id: str) -> dict:
    """Schedule all posts in campaign as cron jobs"""
    
    campaign = load_campaign(campaign_id)
    
    # Verify campaign is approved
    if campaign['status'] != 'approved':
        raise ValueError(f"Campaign not approved. Status: {campaign['status']}")
    
    log_event("INFO", "schedule-campaign", "scheduling", trace_id, {
        "campaign_id": campaign_id,
        "posts": len(campaign['generated_posts'])
    })
    
    # Get system crontab
    cron = CronTab(user='root')
    
    scheduled_count = 0
    
    for post in campaign['generated_posts']:
        # Parse post datetime
        post_datetime = datetime.strptime(
            f"{post['date']} {post['time']}", 
            "%Y-%m-%d %H:%M"
        )
        
        # Create cron job command
        # This will execute the appropriate posting skill at scheduled time
        command = f"cd /app && uv run ./skills/post-to-{post['platform']}.py '{post['content']}' --campaign-id {campaign_id} --post-id {post['post_id']}"
        
        # Create cron entry
        job = cron.new(command=command, comment=f"campaign_{campaign_id}_post_{post['post_id']}")
        
        # Set schedule (minute, hour, day, month, day_of_week)
        job.setall(
            post_datetime.minute,
            post_datetime.hour,
            post_datetime.day,
            post_datetime.month,
            None  # any day of week
        )
        
        scheduled_count += 1
        
        log_event("INFO", "schedule-campaign", "job_created", trace_id, {
            "post_id": post['post_id'],
            "datetime": post_datetime.isoformat()
        })
    
    # Write crontab
    cron.write()
    
    # Update campaign status
    campaign['status'] = 'scheduled'
    campaign['scheduled_at'] = datetime.now().isoformat()
    campaign['scheduled_posts'] = scheduled_count
    save_campaign(campaign)
    
    log_event("INFO", "schedule-campaign", "completed", trace_id, {
        "scheduled_posts": scheduled_count
    })
    
    return {
        "scheduled_posts": scheduled_count,
        "campaign_status": "scheduled"
    }

if __name__ == "__main__":
    campaign_id = sys.argv[1]
    trace_id = os.getenv("TRACE_ID", "unknown")
    
    try:
        result = schedule_campaign(campaign_id, trace_id)
        print(json.dumps({"success": True, **result}))
    except Exception as e:
        log_event("ERROR", "schedule-campaign", "failed", trace_id, {"error": str(e)})
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)
```

**5. Additional World-Class Social Media Manager Skills:**

```python
# ./skills/analyze-post-performance.py
"""
Analyzes metrics from past posts to inform future content:
- Engagement rates by platform, time, content type
- Best performing topics and formats
- Audience growth trends
- Optimal posting times based on actual data
"""

# ./skills/suggest-posting-times.py
"""
Uses historical performance data to suggest optimal posting times:
- Analyzes engagement by hour of day
- Considers platform-specific patterns (LinkedIn vs X vs Instagram)
- Accounts for audience timezone
- Returns recommended posting schedule
"""

# ./skills/analyze-competitor.py
"""
Researches competitor social media presence:
- What they post about (content themes)
- How often they post
- What gets most engagement
- Content gaps we can fill
"""

# ./skills/identify-trends.py
"""
Finds trending topics in your niche:
- Uses Vertex AI search for trend detection
- Analyzes social media trending topics
- Identifies relevant hashtags
- Suggests timely content opportunities
"""

# ./skills/generate-weekly-report.py
"""
Creates weekly performance report:
- Posts published this week
- Engagement metrics
- Best/worst performing content
- Recommendations for next week
"""

# ./skills/adapt-content.py
"""
Takes one piece of content and adapts it for multiple platforms:
- X: 280 chars, casual
- LinkedIn: Professional, data-driven
- Instagram: Visual-first, storytelling
- Ensures consistent core message
"""
```

---

### 5. Vertex AI Grounded Search Skill
**What:** Web search using Google's grounded search for factual accuracy.

**Why Grounded Search:**
- Reduces hallucinations (results tied to source documents)
- Better for research tasks (agent finding info on competitors, trends)
- Cost-effective for social media research (cheaper than browsing)

**Implementation:**
```python
#!/usr/bin/env python3
"""
Skill: Web search using Vertex AI Grounded Search
Usage: uv run ./skills/search-web.py "query"
Returns: JSON with search results and sources
"""

import sys
import json
import os
from google.cloud import aiplatform
from vertexai.preview import grounding

def search_web(query: str, trace_id: str, max_results: int = 5) -> dict:
    """Perform grounded web search"""
    log_event("INFO", "search-web", "searching", trace_id, {"query": query})
    
    # Initialize Vertex AI
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = "us-central1"
    
    aiplatform.init(project=project_id, location=location)
    
    # Perform grounded search
    tool = grounding.Tool.from_google_search_retrieval(
        grounding.GoogleSearchRetrieval()
    )
    
    response = tool.search(query, max_results=max_results)
    
    # Parse results
    results = []
    for item in response.search_results:
        results.append({
            "title": item.title,
            "snippet": item.snippet,
            "url": item.link,
            "source": item.source
        })
    
    log_event("INFO", "search-web", "found_results", trace_id, {"count": len(results)})
    
    return {
        "success": True,
        "query": query,
        "results": results,
        "count": len(results)
    }

def log_event(level: str, skill: str, action: str, trace_id: str, data: dict = None):
    log = {
        "level": level,
        "traceId": trace_id,
        "skill": skill,
        "action": action,
        **(data or {})
    }
    print(json.dumps(log), file=sys.stderr)

if __name__ == "__main__":
    query = sys.argv[1]
    trace_id = os.getenv("TRACE_ID", "unknown")
    
    try:
        result = search_web(query, trace_id)
        print(json.dumps(result))
    except Exception as e:
        log_event("ERROR", "search-web", "failed", trace_id, {"error": str(e)})
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)
```

---

### 6. Structured Logging System
**What:** Centralized logging with trace IDs, log levels, and JSON formatting.

**Why This Matters:**
- **Debuggable:** Trace a single request through entire system
- **Filterable:** `grep '"level":"ERROR"' logs/app.log` finds errors
- **Observable:** See exactly what agent did, in order
- **Production-ready:** Can pipe to log aggregation (Datadog, CloudWatch)

**Logger Implementation:**
```typescript
// logger.ts - Centralized logging system
import * as winston from 'winston';
import { v4 as uuidv4 } from 'uuid';

export class Logger {
  private logger: winston.Logger;
  private service: string;
  
  constructor(config: { service: string; level?: string }) {
    this.service = config.service;
    
    this.logger = winston.createLogger({
      level: config.level || process.env.LOG_LEVEL || 'INFO',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
      ),
      transports: [
        // Console output (for Docker logs)
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.colorize(),
            winston.format.printf(({ timestamp, level, message, traceId, ...meta }) => {
              const metaStr = Object.keys(meta).length > 0 ? JSON.stringify(meta) : '';
              return `${timestamp} [${traceId || 'no-trace'}] ${level}: ${message} ${metaStr}`;
            })
          )
        }),
        // File output (rotating logs)
        new winston.transports.File({
          filename: 'logs/error.log',
          level: 'error',
          maxsize: 10485760, // 10MB
          maxFiles: 5
        }),
        new winston.transports.File({
          filename: 'logs/app.log',
          maxsize: 10485760,
          maxFiles: 10
        })
      ]
    });
  }
  
  debug(message: string, meta?: Record<string, any>) {
    this.logger.debug(message, { service: this.service, ...meta });
  }
  
  info(message: string, meta?: Record<string, any>) {
    this.logger.info(message, { service: this.service, ...meta });
  }
  
  warn(message: string, meta?: Record<string, any>) {
    this.logger.warn(message, { service: this.service, ...meta });
  }
  
  error(message: string, meta?: Record<string, any>) {
    this.logger.error(message, { service: this.service, ...meta });
  }
}

export function generateTraceId(): string {
  return uuidv4().substring(0, 8); // Short trace IDs (8 chars)
}

// Example usage
const logger = new Logger({ service: 'agent-core', level: 'INFO' });
const traceId = generateTraceId();

logger.info('Processing message', { traceId, userId: 123 });
// Output: 2026-02-07T10:30:00.000Z [a4f3b2c1] INFO: Processing message {"service":"agent-core","userId":123}
```

**Log Level Configuration:**
```bash
# Development (verbose logging)
export LOG_LEVEL=DEBUG

# Production (only important events)
export LOG_LEVEL=INFO

# Debugging specific issue
export LOG_LEVEL=DEBUG
grep '"traceId":"a4f3b2c1"' logs/app.log
```

**Filtering Logs:**
```bash
# View only errors
docker logs social-agent 2>&1 | grep '"level":"ERROR"'

# Follow logs for specific trace ID
docker logs -f social-agent 2>&1 | grep 'a4f3b2c1'

# Export logs for analysis
docker logs social-agent 2>&1 | jq 'select(.level == "ERROR")' > errors.json

# Count log events by service
cat logs/app.log | jq '.service' | sort | uniq -c
```

---

### 7. Docker Development Environment
**What:** Complete Docker setup for local development and testing.

**Why Docker-First:**
- **Reproducible:** Same environment on Mac/Windows/Linux
- **Isolated:** Agent dependencies don't pollute host machine
- **Fast iteration:** Hot-reload on code changes
- **Production-like:** Local testing mimics GCP deployment

**Dockerfile:**
```dockerfile
# Dockerfile
FROM node:22-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Install gsutil for GCP Storage sync
RUN curl https://sdk.cloud.google.com | bash
ENV PATH="/root/google-cloud-sdk/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install Node dependencies
RUN npm install

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p /app/data/memory /app/logs /app/skills

# Build TypeScript
RUN npm run build

# Expose gateway port (internal only)
EXPOSE 18789

# Run agent
CMD ["node", "dist/index.js"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  agent:
    build: .
    container_name: social-agent
    environment:
      - NODE_ENV=development
      - LOG_LEVEL=INFO
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
      - X_API_TOKEN=${X_API_TOKEN}
      - LINKEDIN_API_TOKEN=${LINKEDIN_API_TOKEN}
    volumes:
      # Mount source code for hot-reload
      - ./src:/app/src
      - ./skills:/app/skills
      # Persist data locally
      - ./data:/app/data
      - ./logs:/app/logs
      # Mount GCP credentials
      - ~/.config/gcloud:/root/.config/gcloud:ro
    ports:
      - "18789:18789"  # Gateway (localhost only)
    restart: unless-stopped
    command: npm run dev  # Hot-reload mode
```

**.env.example:**
```bash
# Telegram Bot
TELEGRAM_TOKEN=your_bot_token_here

# GCP Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json

# Social Media APIs
X_API_TOKEN=your_x_token
LINKEDIN_API_TOKEN=your_linkedin_token

# Logging
LOG_LEVEL=INFO

# Development Mode
NODE_ENV=development
```

**Development Workflow:**
```bash
# 1. Clone repository
git clone https://github.com/yourorg/social-agent.git
cd social-agent

# 2. Copy environment template
cp .env.example .env
# Edit .env with your API keys

# 3. Authenticate with GCP
gcloud auth application-default login

# 4. Build and start container
docker-compose up --build

# 5. View logs (separate terminal)
docker logs -f social-agent

# 6. Test skills manually
docker exec social-agent ./skills/post-to-x.sh "Test tweet"
docker exec social-agent uv run ./skills/generate-content.py "AI agents"

# 7. Interact with agent via Telegram
# Send message to your bot

# 8. Stop container
docker-compose down

# 9. Clear data (reset memory)
rm -rf ./data/memory/*
docker-compose up
```

**Hot-Reload Setup:**
```json
// package.json
{
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "jest",
    "lint": "eslint src/",
    "logs:debug": "tail -f logs/app.log | jq 'select(.level == \"DEBUG\")'",
    "logs:errors": "tail -f logs/app.log | jq 'select(.level == \"ERROR\")'"
  },
  "devDependencies": {
    "tsx": "^4.7.0",
    "typescript": "^5.3.3",
    "eslint": "^8.56.0"
  }
}
```

---

## System Prompt Customization for Different Roles

**Vision:** This agent architecture is designed to be **role-agnostic**. By changing the system prompt and available skills, you can automate different employee functions without rewriting core code.

### Architecture for Multi-Role Support

**Current Focus: Social Media Manager**
- System Prompt: `./data/memory/SYSTEM_PROMPT_SOCIAL_MEDIA.md`
- Skills: Campaign creation, content generation, posting, analytics
- Memory: Brand voice, posting history, campaign archives

**Future Roles (Same Codebase):**

**1. Customer Support Agent**
- System Prompt: `./data/memory/SYSTEM_PROMPT_CUSTOMER_SUPPORT.md`
- Skills: Ticket triage, knowledge base search, response drafting, escalation
- Memory: FAQ database, customer history, support guidelines

**2. Sales Development Rep (SDR)**
- System Prompt: `./data/memory/SYSTEM_PROMPT_SDR.md`
- Skills: Lead research, outbound email drafting, meeting scheduling, CRM updates
- Memory: Ideal customer profile, outreach templates, objection handling

**3. Content Researcher**
- System Prompt: `./data/memory/SYSTEM_PROMPT_RESEARCHER.md`
- Skills: Deep research, source compilation, summary generation, citation management
- Memory: Research guidelines, trusted sources, output formats

**4. Email Marketing Manager**
- System Prompt: `./data/memory/SYSTEM_PROMPT_EMAIL_MARKETING.md`
- Skills: Email campaign creation, A/B test setup, list segmentation, performance analysis
- Memory: Brand voice, sending guidelines, segment definitions

### How to Switch Roles

**Option 1: Environment Variable**
```bash
# In docker-compose.yml or .env
AGENT_ROLE=social_media  # or customer_support, sdr, researcher, email_marketing

# In src/agent-core.ts
const systemPromptPath = `./data/memory/SYSTEM_PROMPT_${process.env.AGENT_ROLE.toUpperCase()}.md`;
const skillsFilter = ROLE_SKILLS[process.env.AGENT_ROLE];
```

**Option 2: Multiple Agent Instances**
```yaml
# docker-compose.yml
services:
  social-media-agent:
    build: .
    environment:
      - AGENT_ROLE=social_media
    volumes:
      - ./data/social-media:/app/data
  
  customer-support-agent:
    build: .
    environment:
      - AGENT_ROLE=customer_support
    volumes:
      - ./data/customer-support:/app/data
```

**Option 3: Runtime Role Switching** (Future Enhancement)
```typescript
// Agent can switch roles mid-conversation
User: "Switch to customer support mode"
Agent: Loads SYSTEM_PROMPT_CUSTOMER_SUPPORT.md, filters skills to support-only
```

### System Prompt Structure (Template)

**Template: `./data/memory/SYSTEM_PROMPT_{ROLE}.md`**

```markdown
# {Role} Agent System Prompt

## Role Definition
You are a world-class {role} working for {company name}.

Your responsibilities:
- [Primary responsibility 1]
- [Primary responsibility 2]
- [Primary responsibility 3]

## Skills Available
You have access to the following skills:
{dynamically inject available skills for this role}

## Communication Style
[Tone, formality, personality specific to role]

## Decision Authority
You CAN:
- [Actions you're authorized to take autonomously]

You CANNOT (require approval):
- [Actions that need human approval]

## Workflow Patterns

### [Primary Workflow 1]
1. [Step 1]
2. [Step 2]
3. [Step 3]

### [Primary Workflow 2]
...

## Quality Standards
All outputs must:
- [Quality criteria 1]
- [Quality criteria 2]
- [Quality criteria 3]

## Brand Guidelines
{Load from BRAND_VOICE.md or role-specific guidelines}

## Example Interactions

Good:
User: [example request]
You: [example response]

Bad:
User: [example request]
You: [what NOT to do]

## Error Handling
If you encounter:
- [Error type 1]: [How to handle]
- [Error type 2]: [How to handle]

## Success Metrics
Your performance is measured by:
- [Metric 1]
- [Metric 2]
- [Metric 3]
```

### Social Media Manager System Prompt (Current Implementation)

**File: `./data/memory/SYSTEM_PROMPT_SOCIAL_MEDIA.md`**

```markdown
# Social Media Manager Agent System Prompt

## Role Definition
You are a world-class social media manager working for a startup building AI agent infrastructure.

Your responsibilities:
- Research and create data-driven social media campaigns
- Generate platform-specific content that matches brand voice
- Schedule posts at optimal times for maximum engagement
- Analyze performance and optimize future content
- Stay on top of trends in AI, automation, and developer tools

## Skills Available
Campaign Planning:
- create-campaign.py - Research topic, develop strategy, create content calendar
- generate-campaign-posts.py - Generate all posts for a campaign
- suggest-posting-times.py - Recommend optimal posting times based on data

Content Creation:
- generate-content.py - Create platform-specific posts
- adapt-content.py - Adapt one message across multiple platforms
- search-web.py - Research trends and competitor content

Publishing & Scheduling:
- post-to-x.sh - Post to X/Twitter
- post-to-linkedin.py - Post to LinkedIn
- post-to-instagram.py - Post to Instagram
- schedule-campaign.py - Schedule posts as cron jobs

Approval & Review:
- send-approval-email.py - Request approval before scheduling
- parse-approval-response.py - Check for approvals

Analytics:
- analyze-post-performance.py - Review what's working
- generate-weekly-report.py - Weekly performance summary

## Communication Style
- Technical but accessible (explain complex topics simply)
- Data-driven (use metrics and examples)
- Authentic, no hype or empty promises
- Helpful and educational, not salesy

## Decision Authority

You CAN autonomously:
- Research topics and create campaign plans
- Generate draft posts (but NOT post them)
- Suggest posting schedules
- Analyze performance data
- Search for trends and competitor insights

You CANNOT (require approval):
- Actually post content to social media
- Schedule posts without email approval
- Spend money on ads or promotions
- Change brand voice guidelines

## Workflow Patterns

### Creating a Campaign
1. Research topic using search-web.py
2. Analyze competitors and trends
3. Develop content strategy aligned with brand voice
4. Create content calendar with optimal posting times
5. Generate all posts for campaign
6. Send approval email with preview
7. After approval: Schedule posts as cron jobs

### Responding to "Create a post about X"
1. Load BRAND_VOICE.md (ALWAYS)
2. Research topic if needed (search-web.py)
3. Generate content for specified platform
4. Validate against forbidden phrases
5. Return draft for review
6. Ask if user wants to post now or schedule

### Weekly Reporting
1. Run analyze-post-performance.py
2. Identify top performers and underperformers
3. Extract insights (what worked, what didn't)
4. Recommend adjustments for next week
5. Generate report and send via Telegram

## Quality Standards

All content must:
- Pass BRAND_VOICE.md validation (no forbidden phrases)
- Include concrete examples or data points
- Match platform length constraints (X: 280 chars, LinkedIn: 1300 chars)
- Have clear value proposition (why should reader care?)
- Include appropriate call-to-action

All campaigns must:
- Start with research (web search + competitor analysis)
- Align with brand guidelines
- Have measurable success metrics
- Get approval before scheduling

## Brand Guidelines
{Loaded from BRAND_VOICE.md}

Key rules:
- No "game-changer", "revolutionary", "disrupting"
- Lead with questions or data, not declarations
- Use "we" not "I"
- Max 1 emoji per X post, 2-3 per Instagram

## Example Interactions

Good:
User: "Create a 4-week campaign about agent evaluation"
You:
1. Call search-web.py to research agent evaluation trends
2. Call analyze-competitor.py to see what others are posting
3. Call create-campaign.py with research data
4. Generate campaign plan with 20+ post ideas
5. Call send-approval-email.py
6. Response: "Created campaign with 24 posts across X, LinkedIn, Instagram. Sent approval email. Key themes: automated testing, LLM-as-judge, brand voice consistency."

Bad (what NOT to do):
User: "Create a 4-week campaign about agent evaluation"
You: "Sure! Here's a campaign..." [generates text without research]
Why bad: No research, no approval process, no use of skills

Good:
User: "Post this to X: [content]"
You:
1. Check if content aligns with BRAND_VOICE.md
2. If yes: Ask "Should I post now or schedule for optimal time?"
3. If scheduling: Call suggest-posting-times.py, propose time
4. Wait for confirmation before calling post-to-x.sh

Bad:
User: "Post this to X: [content]"
You: [immediately calls post-to-x.sh]
Why bad: No brand validation, no approval

## Error Handling

If skill execution fails:
- Log error with trace ID
- Explain what went wrong to user
- Suggest alternative approach
- Never fail silently

If content violates brand voice:
- Explain which guideline was violated
- Suggest revision
- Don't post until fixed

If approval email bounces:
- Retry with different recipient
- Alert user via Telegram
- Don't schedule without approval

## Success Metrics

Your performance is measured by:
- Campaign completion rate (% of campaigns that get scheduled)
- Brand voice consistency (% passing BRAND_VOICE validation)
- Engagement rate on posted content
- User satisfaction with campaign quality
- Time from request to scheduled posts

Target benchmarks:
- >95% brand voice pass rate
- <24 hours from campaign request to approval email
- >85% campaign approval rate (not rejected)
```

### Adding New Roles (Future)

**To add a new role:**

1. **Create System Prompt:**
   ```bash
   cp ./data/memory/SYSTEM_PROMPT_SOCIAL_MEDIA.md \
      ./data/memory/SYSTEM_PROMPT_CUSTOMER_SUPPORT.md
   
   # Edit to define customer support responsibilities
   ```

2. **Create Role-Specific Skills:**
   ```bash
   mkdir ./skills/customer-support/
   # Add skills: triage-ticket.py, search-kb.py, draft-response.py, etc.
   ```

3. **Update Skill Registry:**
   ```typescript
   // src/skill-registry.ts
   const ROLE_SKILLS = {
     social_media: [
       'create-campaign', 'generate-content', 'post-to-x',
       'send-approval-email', 'schedule-campaign'
     ],
     customer_support: [
       'triage-ticket', 'search-kb', 'draft-response',
       'escalate-ticket', 'update-crm'
     ]
   };
   ```

4. **Configure Agent:**
   ```bash
   # Set role in .env
   echo "AGENT_ROLE=customer_support" >> .env
   
   # Restart agent
   docker-compose restart
   ```

5. **Test Role:**
   ```bash
   # Via Telegram
   User: "Triage this support ticket: [paste ticket]"
   Agent: [uses customer support skills and system prompt]
   ```

### Why This Architecture Scales

**Same Infrastructure, Different Behaviors:**
- Core code (Gateway, Terminal Executor, Memory Manager) doesn't change
- Only system prompt and skills change per role
- Docker container stays the same
- GCP deployment process identical

**Benefits:**
1. **No code duplication** - Write infrastructure once, use for all roles
2. **Easy role additions** - Just add new system prompt + skills
3. **Consistent quality** - Same evaluation framework for all roles
4. **Centralized improvements** - Fix logging bug once, all roles benefit

**Current Priority: Social Media Manager**
- Implement fully before adding other roles
- Use as template for future roles
- Validate architecture works at scale

**Future Enhancement Roadmap:**
1. **Month 1:** Social media manager (current focus)
2. **Month 2:** Add customer support agent (validate multi-role architecture)
3. **Month 3:** Add SDR agent (test sales workflows)
4. **Month 4:** Add researcher agent (test knowledge work automation)

Each new role validates that the architecture scales without major refactoring.

### ❌ Mem0 Integration (For Now)
**Why Skip Initially:** 
- Adds complexity during development
- GCP Storage + local cache sufficient for MVP
- Can add later if memory size becomes issue

**When to Add:** If BRAND_VOICE.md + conversation history exceeds 10,000 tokens per request

### ❌ Multi-Protocol Messaging Support
**Why Skip:** Telegram alone provides all needed functionality. No need for WhatsApp, Discord, Slack during initial build.

**Savings:** ~2 weeks of integration work

### ❌ Browser Automation
**Why Skip:** Extremely fragile (breaks on UI changes, CAPTCHA). Use direct APIs or CLI tools instead.

**Savings:** ~1 week of debugging + ongoing maintenance

### ❌ ClawHub Marketplace
**Why Skip:** 341 malicious skills identified by security researchers. Every community skill requires full audit.

**Alternative:** Write 3-5 custom CLI skills in-house.

**Savings:** Eliminates security audit burden

### ❌ Continuous Heartbeat
**Why Skip:** Burns $400-500/month in API costs even when idle.

**Alternative:** Use explicit cron jobs for scheduled tasks only.

**Savings:** $400-500/month in wasted API calls

---

## Getting Started with Cursor

### Initial Setup (First 30 Minutes)

**1. Create Repository:**
```bash
# Create project directory
mkdir social-agent
cd social-agent
git init

# Create initial structure
mkdir -p src/ skills/ data/memory logs/ tests/ evals/
touch README.md .gitignore .env.example

# Open in Cursor
cursor .
```

**2. Initialize Project with Cursor AI:**
Open Cursor and use Cmd+L (or Ctrl+L) to chat with Cursor. Provide this context:

```
I'm building a social media automation agent with these requirements:

Architecture:
- Docker-first development (Node.js 22 + Python 3)
- File-system based memory (./data/memory/)
- Terminal executor for running CLI skills
- GCP Storage for persistent memory
- Structured logging with trace IDs

Please help me:
1. Create package.json with dependencies (typescript, winston, node-telegram-bot-api)
2. Create tsconfig.json
3. Create Dockerfile with Node.js 22, Python 3, uv, gsutil
4. Create docker-compose.yml with hot-reload support
5. Create .gitignore for Node.js project
```

**3. Create Core Files:**

Use Cursor's Composer (Cmd+I or Ctrl+I) to generate files:

```
Create src/logger.ts implementing a structured logging system with:
- Winston logger
- Trace ID generation
- Log levels (DEBUG, INFO, WARN, ERROR)
- JSON output format
- File rotation (logs/app.log, logs/error.log)
```

```
Create src/terminal-executor.ts implementing:
- Command allowlist (cat, ls, uv)
- Path restrictions (./data/memory/, ./skills/)
- Security validation
- Structured logging for all executions
- Error handling
```

```
Create src/memory-manager.ts implementing:
- Local file storage (./data/memory/)
- GCP Storage sync (gsutil)
- loadBrandVoice() function
- saveConversation() function
- Development mode (skip GCS sync)
```

**4. Test Docker Build:**
```bash
# Build container
docker-compose build

# Start in detached mode
docker-compose up -d

# View logs
docker logs -f social-agent

# Test terminal executor
docker exec social-agent ls ./skills/

# Stop container
docker-compose down
```

**5. Create First Skill:**

Use Cursor to generate `./skills/test-skill.py`:

```
Create ./skills/test-skill.py that:
- Accepts one argument (topic)
- Prints structured JSON log to stderr
- Returns JSON result to stdout
- Uses uv for dependencies
- Includes error handling
```

Test it:
```bash
docker exec social-agent uv run ./skills/test-skill.py "test topic"
```

---

### Cursor Development Workflow

**Iterative Development Pattern:**

1. **Define what you're building (in Cursor chat):**
   ```
   I need to implement the Telegram Gateway that:
   - Listens for Telegram bot messages
   - Generates trace ID for each request
   - Routes to agent core
   - Logs all operations
   - Handles errors gracefully
   ```

2. **Let Cursor generate initial implementation:**
   Cursor will create `src/gateway.ts` with basic structure

3. **Review and refine:**
   - Read the generated code
   - Ask Cursor to add missing pieces: "Add rate limiting to prevent spam"
   - Ask Cursor to add tests: "Create jest tests for gateway.ts"

4. **Test in Docker:**
   ```bash
   # Rebuild with changes
   docker-compose up --build
   
   # Verify logs show new functionality
   docker logs social-agent | grep "gateway"
   ```

5. **Iterate on issues:**
   If something doesn't work, paste error into Cursor chat:
   ```
   Getting this error when starting gateway:
   [paste error]
   
   How do I fix it?
   ```

**Using Cursor Composer for Multi-File Changes:**

Press Cmd+I (Ctrl+I) to open Composer, then:

```
I need to add web search capability:

1. Create ./skills/search-web.py using Vertex AI Grounded Search
2. Update src/agent-core.ts to register the search skill
3. Add search_web to the list of available tools
4. Update tests/agent-core.test.ts to test search integration

Make sure search-web.py:
- Loads query from command line arg
- Uses Vertex AI client
- Returns JSON with results array
- Logs to stderr
```

Composer will create/modify all files simultaneously.

**Debugging with Cursor:**

When logs show an error:
```bash
docker logs social-agent 2>&1 | grep ERROR > error.log
```

Open error.log in Cursor, select the error, and ask:
```
This error is appearing in my logs. What's causing it and how do I fix it?
```

Cursor will analyze the error and suggest fixes.

---

### Cursor AI Prompting Best Practices

**Good Prompts:**

✅ "Create TerminalExecutor class that only allows commands: cat, ls, uv. Block everything else. Include tests."

✅ "The agent is calling uv run but getting 'command not found'. Check if uv is in PATH and fix the Dockerfile."

✅ "Add trace ID to all log statements in gateway.ts. Trace ID should be 8-character UUID."

**Bad Prompts:**

❌ "Make it work" (too vague)

❌ "Add AI" (unclear what AI should do)

❌ "Fix the bug" (which bug? in what file?)

**Template for Creating New Skills:**

```
Create a new skill at ./skills/[skill-name].py that:

Purpose: [What does this skill do?]

Input: [Command-line args or file inputs]

Processing: [What logic or API calls?]

Output: [JSON structure to stdout]

Logging: [What to log to stderr?]

Error Handling: [What errors to catch?]

Example usage:
uv run ./skills/[skill-name].py "arg1" "arg2"

Expected output:
{"success": true, "result": "..."}
```

---

### Daily Development Checklist

**Morning Standup (with yourself):**
- [ ] `docker-compose up` - Start agent
- [ ] `docker logs -f social-agent` - Verify no startup errors
- [ ] Review yesterday's work (git log)
- [ ] Identify today's task (from Week 1-4 plan)
- [ ] Ask Cursor to help plan implementation

**Development Loop:**
1. Define feature/task clearly (write it down or tell Cursor)
2. Use Cursor to generate initial implementation
3. Test in Docker
4. Review logs for errors
5. Iterate with Cursor's help
6. Commit when working (`git commit -m "Add X feature"`)

**End of Day:**
- [ ] `docker-compose down` - Stop agent
- [ ] `git status` - Check uncommitted changes
- [ ] `git commit` - Commit working changes
- [ ] Update progress in Week 1-4 plan
- [ ] Note any blockers for tomorrow

**Weekly Review (Sundays):**
- [ ] Run full test suite: `npm test`
- [ ] Check Week 1-4 deliverable status
- [ ] Review logs for warnings: `grep WARN logs/app.log`
- [ ] Update documentation if needed
- [ ] Plan next week's focus

---

## Debugging Guide

### Common Issues and Solutions

**Issue: Docker container won't start**
```bash
# Check build logs
docker-compose build

# Check for port conflicts
lsof -i :18789

# View full error
docker-compose up
```

**Fix with Cursor:**
```
Docker container is failing to start with this error:
[paste error from docker-compose up]

Check the Dockerfile and docker-compose.yml for issues.
```

**Issue: Terminal executor can't find uv**
```bash
# Exec into container
docker exec -it social-agent bash

# Check if uv exists
which uv
echo $PATH
```

**Fix with Cursor:**
```
uv command not found in Docker container. 
The Dockerfile installs uv but it's not in PATH.
How do I fix the PATH configuration?
```

**Issue: Skills return errors**
```bash
# Test skill directly
docker exec social-agent uv run ./skills/generate-content.py "test" --platform x

# Check skill logs
docker exec social-agent cat logs/app.log | grep "generate-content"
```

**Fix with Cursor:**
```
Skill ./skills/generate-content.py is failing with error:
[paste error]

Here's the skill code:
[paste generate-content.py]

What's wrong and how do I fix it?
```

**Issue: Logs are too verbose**
```bash
# Change log level
export LOG_LEVEL=INFO  # or WARN
docker-compose up

# Filter logs in real-time
docker logs -f social-agent 2>&1 | grep -v DEBUG
```

**Fix with Cursor:**
```
Logs have too many DEBUG messages making it hard to see important events.
How do I configure winston logger to:
1. Show INFO and above in console
2. Show DEBUG only in file
3. Make it configurable via LOG_LEVEL env var
```

**Issue: GCP Storage sync fails**
```bash
# Check credentials
docker exec social-agent gcloud auth list

# Test gsutil manually
docker exec social-agent gsutil ls gs://your-bucket/

# Check bucket permissions
gcloud storage buckets describe gs://your-bucket
```

**Fix with Cursor:**
```
GCP Storage sync is failing with permission denied.
The bucket exists and gcloud auth list shows correct account.
What's the issue with the service account permissions?
```

**Issue: Agent not responding to Telegram**
```bash
# Check if bot is receiving messages
docker logs social-agent | grep "Received message"

# Check Telegram token
docker exec social-agent printenv TELEGRAM_TOKEN

# Test Telegram connection
curl https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe
```

**Fix with Cursor:**
```
Telegram bot is not responding to messages.
Here's the gateway code:
[paste gateway.ts]

And the logs show:
[paste relevant logs]

What's preventing the bot from receiving messages?
```

---

### Trace ID Debugging

**Following a single request through the system:**

```bash
# 1. Send message to bot, note the trace ID in response or logs

# 2. Filter all logs for that trace ID
docker logs social-agent 2>&1 | grep "traceId\":\"a4f3b2c1"

# 3. Export to file for detailed analysis
docker logs social-agent 2>&1 | grep "traceId\":\"a4f3b2c1" > trace.log

# 4. View in order
cat trace.log | jq -r '[.timestamp, .level, .service, .message] | @tsv'
```

**Example trace output:**
```
2026-02-07T10:30:00 INFO  gateway      Received message
2026-02-07T10:30:01 INFO  agent-core   Processing request
2026-02-07T10:30:01 DEBUG agent-core   Loading brand voice
2026-02-07T10:30:02 INFO  terminal-exec Executing: cat ./data/memory/BRAND_VOICE.md
2026-02-07T10:30:02 INFO  agent-core   Calling Gemini Flash
2026-02-07T10:30:05 INFO  agent-core   Generated content (280 chars)
2026-02-07T10:30:05 INFO  gateway      Sent response
```

This shows exactly what happened, in order, with timing information.

---

## Next Steps: First Week Kickoff

**Day 1 (4 hours): Project Setup**
1. Create repository and open in Cursor
2. Use Cursor to generate package.json, Dockerfile, docker-compose.yml
3. Build Docker container and verify it starts
4. Create .env with Telegram token
5. Test Telegram bot connection

**Day 2 (4 hours): Terminal Executor**
1. Use Cursor to generate TerminalExecutor class
2. Add security allowlists
3. Create tests
4. Verify can execute: cat, ls, uv run

**Day 3 (4 hours): Structured Logging**
1. Use Cursor to generate Logger class with winston
2. Add trace ID generation
3. Test log levels and filtering
4. Verify logs are readable

**Day 4 (4 hours): Integration**
1. Connect Telegram gateway → Terminal executor
2. Test full flow: Telegram message → Execute command → Return result
3. Verify structured logs show complete trace
4. Document any blockers for Week 2

**Day 5 (4 hours): Testing & Documentation**
1. Write tests for all Week 1 components
2. Run full test suite
3. Update README with setup instructions
4. Verify Week 1 deliverable checklist

By end of Week 1, you should have a working foundation that you can build on for Weeks 2-4.

---

### Week 1: Docker Foundation & Terminal Executor
**Goal:** Get Docker environment running with agent that can execute terminal commands.

**Tasks:**

1. **Project Setup** (4 hours)
   ```bash
   # Initialize project
   mkdir social-agent && cd social-agent
   git init
   npm init -y
   
   # Create directory structure
   mkdir -p src/ skills/ data/memory logs/ tests/
   
   # Install core dependencies
   npm install typescript tsx @types/node
   npm install winston node-telegram-bot-api
   npm install --save-dev eslint prettier jest
   
   # Initialize TypeScript
   npx tsc --init
   ```

2. **Docker Environment** (6 hours)
   - Create `Dockerfile` with Node.js 22, Python 3, uv, gsutil
   - Create `docker-compose.yml` with volume mounts for hot-reload
   - Create `.env.example` with required environment variables
   - Test Docker build and container startup
   
   **Validation:**
   ```bash
   docker-compose up --build
   # Should start without errors
   docker exec social-agent node --version  # v22.x.x
   docker exec social-agent uv --version
   ```

3. **Terminal Executor Skill** (8 hours)
   - Implement `TerminalExecutor` class with command allowlist
   - Add security validation (command whitelist, path restrictions)
   - Test executing: `cat`, `ls`, `uv run`
   - Add structured logging for all command executions
   
   **Test Cases:**
   ```typescript
   // tests/terminal-executor.test.ts
   test('executes cat command', async () => {
     const result = await executor.execute('cat ./data/memory/test.md');
     expect(result).toContain('test content');
   });
   
   test('blocks dangerous commands', async () => {
     await expect(
       executor.execute('rm -rf /'))
     ).rejects.toThrow('Command not allowed');
   });
   
   test('restricts paths', async () => {
     await expect(
       executor.execute('cat /etc/passwd'))
     ).rejects.toThrow('Path not allowed');
   });
   ```

4. **Structured Logging** (4 hours)
   - Implement `Logger` class with winston
   - Add trace ID generation
   - Configure log levels (DEBUG/INFO/WARN/ERROR)
   - Test log output formatting and filtering
   
   **Validation:**
   ```bash
   # Start agent with DEBUG logging
   docker-compose down
   docker-compose up
   
   # Send test message via Telegram
   # Verify structured logs appear:
   docker logs social-agent 2>&1 | grep '"level":"INFO"'
   docker logs social-agent 2>&1 | grep '"traceId"'
   ```

**Deliverable:** Docker container running locally with terminal executor that can:
- Execute `cat ./data/memory/BRAND_VOICE.md`
- Execute `ls ./skills/`
- Execute `uv run ./skills/test.py`
- Log all operations with trace IDs

**Validation Checklist:**
- [ ] `docker-compose up` starts without errors
- [ ] Terminal executor can run whitelisted commands
- [ ] Dangerous commands are blocked (rm, curl, etc.)
- [ ] Logs show structured JSON with trace IDs
- [ ] Hot-reload works (edit src/, see restart)

---

### Week 2: GCP Storage Memory & Brand Voice
**Goal:** Implement file-based memory with GCP Storage sync and brand voice loading.

**Tasks:**

1. **Memory Manager** (8 hours)
   - Implement `MemoryManager` class with local cache
   - Add GCP Storage sync functions (upload/download)
   - Create memory file structure (BRAND_VOICE.md, CONVERSATION_HISTORY/, etc.)
   - Test sync behavior (local-first, async upload)
   
   **File Structure:**
   ```
   ./data/memory/
   ├── BRAND_VOICE.md          # Always loaded before content generation
   ├── CAMPAIGN_CONTEXT.md     # Current campaigns and themes
   ├── CONVERSATION_HISTORY/
   │   ├── 2026-02-07.md
   │   └── 2026-02-06.md
   └── POSTS_ARCHIVE/
       └── 2026-02-week1.md
   ```

2. **Brand Voice Integration** (6 hours)
   - Create comprehensive `BRAND_VOICE.md` template
   - Implement `loadBrandVoice()` function (always called before content generation)
   - Add brand voice validation (forbidden phrases filter)
   - Test brand voice consistency across multiple generations
   
   **BRAND_VOICE.md Template:** (see earlier section)

3. **GCP Storage Setup** (4 hours)
   - Create GCS bucket: `gs://social-agent-memory-{project-id}`
   - Configure bucket permissions (service account access)
   - Test gsutil commands from Docker container
   - Implement sync on agent startup (pull latest memory from GCS)
   
   **Setup Commands:**
   ```bash
   # Create GCS bucket
   gsutil mb -l us-central1 gs://social-agent-memory-$(gcloud config get-value project)
   
   # Test upload/download
   docker exec social-agent gsutil cp ./data/memory/BRAND_VOICE.md gs://social-agent-memory-$(gcloud config get-value project)/
   docker exec social-agent gsutil ls gs://social-agent-memory-$(gcloud config get-value project)/
   ```

4. **Agent Core Integration** (6 hours)
   - Implement `AgentCore` class with LangGraph
   - Integrate `MemoryManager` and `TerminalExecutor`
   - Add tool definitions for agent (execute_command, load_memory, save_memory)
   - Test end-to-end flow: Telegram message → Agent → Memory lookup → Response

**Deliverable:** Agent with persistent memory that:
- Loads BRAND_VOICE.md before every content generation
- Saves conversation history to GCP Storage
- Can retrieve memory via terminal commands

**Validation:**
```bash
# 1. Populate initial memory
cat > ./data/memory/BRAND_VOICE.md << EOF
# Brand Voice
- Technical but accessible
- No hype phrases
EOF

# 2. Start agent
docker-compose up

# 3. Test memory loading via Telegram
# Send: "Load brand voice"
# Agent should respond with BRAND_VOICE.md contents

# 4. Verify GCS sync
gsutil ls gs://social-agent-memory-$(gcloud config get-value project)/
# Should show BRAND_VOICE.md
```

---

### Week 3: CLI Skills & Campaign Workflow
**Goal:** Build campaign management system and all social media posting skills.

**Tasks:**

1. **Campaign Creator Skill** (10 hours)
   - Create `./skills/create-campaign.py` with full research workflow
   - Integrate web search, competitor analysis, trend identification
   - Implement content strategy development (pillars, cadence, themes)
   - Generate content calendar with optimal posting times
   - Create post ideas for each calendar slot
   
   **Workflow Test:**
   ```bash
   # Create 4-week campaign
   docker exec social-agent uv run ./skills/create-campaign.py \
     "AI agent frameworks" --duration 4
   
   # Output: Full campaign plan with 20-30 post ideas
   ```

2. **Content Generator Skill** (6 hours)
   - Create `./skills/generate-content.py` with Vertex AI Gemini
   - Add BRAND_VOICE.md loading before every generation
   - Implement platform-specific adaptations (X, LinkedIn, Instagram)
   - Add forbidden phrase validation
   - Create `./skills/generate-campaign-posts.py` for bulk generation
   
   **Test:**
   ```bash
   # Generate individual post
   docker exec social-agent uv run ./skills/generate-content.py \
     "AI agent evaluation" --platform x
   
   # Generate all posts for campaign
   docker exec social-agent uv run ./skills/generate-campaign-posts.py campaign_001
   ```

3. **Email Approval System** (8 hours)
   - Create `./skills/send-approval-email.py` with HTML preview
   - Configure SMTP settings (Gmail or Sendgrid)
   - Implement approval link handling (parse "APPROVE"/"REJECT" from email)
   - Create visual preview generator for campaigns
   - Test email sending and approval parsing
   
   **Test:**
   ```bash
   # Send approval email
   docker exec social-agent uv run ./skills/send-approval-email.py \
     campaign_001 --to your@email.com
   
   # Check email inbox for preview
   # Reply with "APPROVE" in subject
   
   # Parse approval
   docker exec social-agent uv run ./skills/parse-approval-response.py \
     --check-inbox
   ```

4. **Cron Scheduler** (6 hours)
   - Create `./skills/schedule-campaign.py` for cron job creation
   - Implement crontab management (add/list/remove jobs)
   - Add job validation (no duplicate scheduling)
   - Test scheduling multiple posts at different times
   
   **Test:**
   ```bash
   # Schedule approved campaign
   docker exec social-agent uv run ./skills/schedule-campaign.py campaign_001
   
   # Verify cron jobs created
   docker exec social-agent crontab -l
   
   # Output: Multiple entries for campaign posts
   ```

5. **Social Media Posting Skills** (6 hours)
   - Create `./skills/post-to-x.sh` (X/Twitter)
   - Create `./skills/post-to-linkedin.py` (LinkedIn)
   - Create `./skills/post-to-instagram.py` (Instagram via Mixpost)
   - Add posting confirmation and error handling
   - Test manual posting to each platform
   
   **Test:**
   ```bash
   # Test each posting skill
   docker exec social-agent ./skills/post-to-x.sh "Test tweet"
   docker exec social-agent uv run ./skills/post-to-linkedin.py "Test post"
   docker exec social-agent uv run ./skills/post-to-instagram.py \
     "Test caption" --image ./test.jpg
   ```

6. **Supporting Skills** (6 hours)
   - Create `./skills/analyze-post-performance.py` (metrics analysis)
   - Create `./skills/suggest-posting-times.py` (optimal timing)
   - Create `./skills/analyze-competitor.py` (competitive research)
   - Create `./skills/identify-trends.py` (trend detection)
   - Create `./skills/adapt-content.py` (cross-platform adaptation)

**Deliverable:** Complete campaign workflow from research to scheduled posting.

**Full Campaign Workflow Test:**
```bash
# 1. Agent creates campaign (via Telegram)
User: "Create a 4-week campaign about AI agent evaluation frameworks"
Agent executes: uv run ./skills/create-campaign.py "AI agent eval" --duration 4
Agent responds: "Campaign created with 24 posts. Generating content..."

# 2. Generate all posts
Agent executes: uv run ./skills/generate-campaign-posts.py campaign_001
Agent responds: "Generated 24 posts across X, LinkedIn, Instagram"

# 3. Send for approval
Agent executes: uv run ./skills/send-approval-email.py campaign_001 --to you@email.com
Agent responds: "Approval email sent. Awaiting response..."

# 4. User approves via email
User: Replies to email with "APPROVE" in subject

# 5. Agent detects approval
Agent executes: uv run ./skills/parse-approval-response.py --check-inbox
Agent finds: Approval for campaign_001

# 6. Schedule all posts
Agent executes: uv run ./skills/schedule-campaign.py campaign_001
Agent responds: "Scheduled 24 posts. First post goes live Monday at 9am."

# 7. Verify scheduled jobs
docker exec social-agent crontab -l | grep campaign_001
# Shows 24 cron entries with different dates/times
```

**Validation Checklist:**
- [ ] Campaign creator produces complete plan (research + strategy + calendar)
- [ ] Generated posts match brand voice (pass forbidden phrase check)
- [ ] Approval email sends with visual preview
- [ ] Email approval/rejection parsing works
- [ ] Cron jobs schedule correctly (verify with `crontab -l`)
- [ ] All posting skills work (X, LinkedIn, Instagram)
- [ ] Logs show complete execution trace with trace IDs
- [ ] Campaign persists to GCP Storage (survives restart)

---

### Week 4: Production Deployment & Monitoring
**Goal:** Deploy to GCP and add monitoring/alerting.

**Tasks:**

1. **GCP Compute Engine Setup** (4 hours)
   - Create e2-medium instance in us-central1
   - Install Docker and docker-compose
   - Configure VPC firewall (SSH only, no public ports)
   - Set up GCP Storage bucket permissions
   
   **Deployment Commands:**
   ```bash
   # Create VM
   gcloud compute instances create social-agent \
     --machine-type=e2-medium \
     --zone=us-central1-a \
     --image-family=ubuntu-2404-lts \
     --boot-disk-size=30GB
   
   # SSH and install Docker
   gcloud compute ssh social-agent
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   
   # Clone repo and start
   git clone https://github.com/yourorg/social-agent.git
   cd social-agent
   cp .env.example .env
   # Edit .env with production tokens
   docker-compose up -d
   ```

2. **Systemd Integration** (2 hours)
   - Create systemd service for docker-compose
   - Configure auto-restart on failure
   - Test VM reboot (agent should auto-start)
   
   **Service File:**
   ```ini
   # /etc/systemd/system/social-agent.service
   [Unit]
   Description=Social Media Agent
   Requires=docker.service
   After=docker.service
   
   [Service]
   Type=oneshot
   RemainAfterExit=yes
   WorkingDirectory=/home/user/social-agent
   ExecStart=/usr/bin/docker-compose up -d
   ExecStop=/usr/bin/docker-compose down
   
   [Install]
   WantedBy=multi-user.target
   ```

3. **Monitoring Setup** (8 hours)
   - Add cost tracking (LLM token usage per model)
   - Implement GCP billing alerts ($50, $150 thresholds)
   - Create health check endpoint (`GET /health`)
   - Add Telegram alerts for errors (critical errors → Telegram message)
   
   **Cost Tracker:**
   ```typescript
   class CostTracker {
     private costs = new Map<string, number>();
     
     trackLLMCall(model: string, tokens: number) {
       const costPerToken = model === 'gemini-flash' ? 0.0000001 : 0.000001;
       const cost = tokens * costPerToken;
       this.costs.set(model, (this.costs.get(model) || 0) + cost);
       
       logger.info('LLM call tracked', { model, tokens, cost });
     }
     
     async sendDailyReport() {
       const total = Array.from(this.costs.values()).reduce((a, b) => a + b, 0);
       await telegram.sendMessage(
         ADMIN_CHAT_ID,
         `💰 Daily LLM Cost Report\nTotal: $${total.toFixed(2)}\n` +
         `Gemini Flash: $${(this.costs.get('gemini-flash') || 0).toFixed(2)}\n` +
         `Claude Opus: $${(this.costs.get('claude-opus') || 0).toFixed(2)}`
       );
     }
   }
   ```

4. **AgentTrainings Integration** (10 hours)
   - Create evaluation test cases for brand voice
   - Set up weekly eval cron job (Sundays at 2 AM)
   - Configure Telegram alerts for eval failures
   - Build baseline tracking (save v1.0.0 baseline)
   
   **Evaluation Setup:**
   ```bash
   # Install AgentTrainings in Docker container
   pip install -e /path/to/agent-training
   
   # Create test cases
   mkdir -p /app/evals/test_cases
   cat > /app/evals/test_cases/brand_voice.json << EOF
   [
     {
       "test_id": "brand_001",
       "persona": {"name": "Technical Founder", "expertise_level": "expert"},
       "interaction": {"type": "single_turn", "user_message": "Create LinkedIn post about agent evals"},
       "expected_behavior": {
         "tone_and_style": {"required_tone": "data-driven and authentic"},
         "correctness": {"must_not_include": ["game-changer", "revolutionary"]}
       }
     }
   ]
   EOF
   
   # Run weekly evaluation
   0 2 * * 0 cd /app && python -m agent_trainings run --config evals/config.json
   ```

**Deliverable:** Production agent on GCP with:
- 24/7 uptime
- Automated monitoring and cost tracking
- Weekly quality evaluations
- Telegram alerts for errors and cost overruns

**Validation:**
```bash
# 1. Verify agent is running
gcloud compute ssh social-agent
docker ps  # Should show social-agent container

# 2. Check logs for last 24 hours
docker logs --since 24h social-agent | grep ERROR
# Should be minimal errors

# 3. Verify GCS sync
gsutil ls gs://social-agent-memory-$(gcloud config get-value project)/CONVERSATION_HISTORY/
# Should show recent conversation files

# 4. Test full workflow from Telegram
# Send: "Create and post a tweet about agent evaluation frameworks"
# Verify: Tweet appears on X, conversation logged, costs tracked

# 5. Run evaluation manually
docker exec social-agent python -m agent_trainings run --config /app/evals/config.json
# Check results: eval_results/report_*.json
```

---

## Week 4 Checkpoint: Production Readiness

By end of Week 4, verify:

- [x] Agent runs 72 hours unattended on GCP
- [x] Weekly evaluation passes at >85% overall score
- [x] Total monthly cost <$100 (infrastructure + API calls)
- [x] Telegram bot responds within 5 seconds
- [x] All skills execute successfully (search, generate, post)
- [x] Logs are readable and filterable by trace ID
- [x] GCP Storage sync works (memory persists across restarts)
- [x] Cost tracking reports accurate LLM spend
- [x] Alerts fire correctly (test by simulating error)

**If any checklist item fails:** Debug in local Docker environment before attempting GCP deployment fixes.

---

## Evaluation Framework Integration

### Why Evaluation Matters for Social Media Agents
Unlike general chatbots, social media agents have **concrete, measurable quality criteria:**
- **Brand voice consistency:** Posts should sound like your brand, not generic AI
- **Platform appropriateness:** X posts shouldn't read like LinkedIn articles
- **Factual accuracy:** No hallucinated metrics or false claims
- **Tool usage:** Agent should post to correct platforms with correct formatting

**The Risk:** Over time, agents "drift" due to:
- Memory compression (brand guidelines get summarized incorrectly)
- Model updates (new LLM versions behave differently)
- Edge case accumulation (unusual inputs cause unexpected outputs)

### AgentTrainings Integration Pattern

**Setup:**
```bash
# Install AgentTrainings in agent project
cd social-agent
pip install -e ../agent-training

# Create evaluation configuration
cat > evals/social_agent_config.json <<EOF
{
  "agent_under_test": {
    "type": "langgraph",
    "agent_id": "social_media_agent"
  },
  "test_dataset": {
    "path": "./evals/test_cases/brand_voice_tests.json"
  },
  "evaluation_dimensions": {
    "correctness": {"enabled": true, "weight": 0.25},
    "tool_usage": {"enabled": true, "weight": 0.25},
    "tone_and_style": {"enabled": true, "weight": 0.30},
    "completeness": {"enabled": true, "weight": 0.20}
  },
  "pass_fail_criteria": {
    "mode": "overall_score",
    "overall_threshold": 8.5
  }
}
EOF
```

**Test Case Examples:**
```json
{
  "test_id": "brand_voice_001",
  "category": "brand_consistency",
  "persona": {
    "name": "Technical Founder",
    "expertise_level": "expert"
  },
  "interaction": {
    "type": "single_turn",
    "user_message": "Create a LinkedIn post about our new agent evaluation framework"
  },
  "expected_behavior": {
    "correctness": {
      "must_include": ["AgentTrainings", "automated testing"],
      "must_not_include": ["game-changer", "revolutionary"]
    },
    "tone_and_style": {
      "required_tone": "data-driven and authentic",
      "formality_level": "professional but approachable"
    },
    "tool_usage": {
      "required_tools": ["linkedin_post"],
      "forbidden_tools": ["twitter_post"]
    }
  }
}
```

**Weekly Evaluation Cron:**
```typescript
// Add to scheduled tasks
const SCHEDULED_TASKS = {
  'weekly-evaluation': {
    schedule: '0 2 * * 0',  // 2 AM every Sunday
    action: async () => {
      // Run AgentTrainings evaluation
      const result = await runCommand(
        'python -m agent_trainings run --config evals/social_agent_config.json'
      );
      
      // Parse results
      const report = JSON.parse(fs.readFileSync('eval_results/report_latest.json'));
      
      // Alert if quality degraded
      if (report.summary_statistics.overall_scores.mean < 8.5) {
        await telegram.sendMessage(
          ADMIN_CHAT_ID,
          `🚨 QUALITY ALERT\n\n` +
          `Weekly evaluation score: ${report.summary_statistics.overall_scores.mean}\n` +
          `Pass rate: ${report.summary_statistics.pass_rate * 100}%\n\n` +
          `Top issues:\n${formatFailurePatterns(report.actionable_summary)}`
        );
      }
    }
  }
};
```

---

## Cost Breakdown & Optimization

### Monthly Operating Costs (Projected)

| Category | Service | Monthly Cost | Notes |
|----------|---------|--------------|-------|
| **Compute** | GCP e2-medium | $24 | 4GB RAM, 2 vCPUs, Ubuntu 24.04 |
| **Storage** | Boot disk (20GB) | $3 | Standard persistent disk |
| **LLM - Simple Tasks** | Gemini 2.5 Flash | $5-10 | ~500 simple tasks @ $0.001/task |
| **LLM - Complex Tasks** | Claude Opus 4.6 | $40-80 | ~50 complex tasks @ $0.02/task |
| **Social Media APIs** | X/LinkedIn/Mixpost | $0-15 | Depends on posting volume |
| **Evaluation** | AgentTrainings (weekly) | $2 | 20 test cases @ ~$0.10/eval |
| **TOTAL** | | **$74-132/month** | |

### Cost Optimization Strategies

**1. Intelligent LLM Routing**
Route 90% of tasks to Gemini Flash ($0.001 vs $0.02 = 20x cheaper):
- Scheduling posts → Flash
- Fetching metrics → Flash  
- Listing drafts → Flash
- Generating complex content → Opus
- Brand voice validation → Opus

**Savings:** $100-150/month

**2. Eliminate Heartbeat**
Use explicit cron jobs instead of continuous LLM polling:
- OpenClaw default: ~2,880 heartbeat calls/month @ $0.02 = $57.60
- Cron-based: 120 scheduled tasks/month @ $0.02 = $2.40

**Savings:** $55/month

**3. Batch Social Media Posts**
Generate 5 posts in single LLM call instead of 5 separate calls:
- Separate calls: 5 × $0.02 = $0.10
- Batched: 1 × $0.03 = $0.03

**Savings:** 70% reduction on content generation costs

**4. Use GCP Free Tier**
GCP provides $300 free credits for new accounts:
- Covers 4-6 months of infrastructure costs
- Use time to validate approach before committing budget

---

## Security Hardening Checklist

Before production deployment, implement these mandatory security controls:

### ✅ Network Security
- [ ] Gateway daemon bound to 127.0.0.1 ONLY (no public IP exposure)
- [ ] GCP firewall allows SSH only (port 22), no other inbound traffic
- [ ] No port forwarding to 18789 (control plane) or any other service ports
- [ ] VPN configured for remote admin access (not public SSH)

### ✅ Authentication & Authorization
- [ ] Telegram bot restricted to single admin user ID (hardcoded allow-list)
- [ ] All social media OAuth tokens stored in GCP Secret Manager
- [ ] Environment variables never committed to Git (.env in .gitignore)
- [ ] Vertex AI authentication uses Application Default Credentials (no hardcoded keys)

### ✅ Code Security
- [ ] All skills written in-house (zero marketplace dependencies)
- [ ] Skill execution happens in Docker sandbox (not host OS)
- [ ] No eval() or exec() in skill code (prevent code injection)
- [ ] Input validation on all Telegram commands (prevent prompt injection)

### ✅ Monitoring & Alerting
- [ ] GCP billing alerts at $50 and $150 thresholds
- [ ] Telegram alerts for evaluation failures (quality degradation)
- [ ] Systemd service restarts on crash (automatic recovery)
- [ ] Log rotation configured (prevent disk fill)

### ✅ Data Privacy
- [ ] No user data stored beyond current conversation (GDPR compliance)
- [ ] Memory files encrypted at rest
- [ ] Scheduled backup of BRAND_VOICE.md to GCS (versioned)

---

## Success Metrics

### Week 1 Success Criteria
- [ ] Agent responds to `/ping` in <1 second
- [ ] `/generate [topic]` produces valid tweet draft
- [ ] Local Telegram bot connects successfully

### Week 2 Success Criteria
- [ ] Brand voice consistency >90% (manual review of 10 posts)
- [ ] Memory system persists across agent restarts
- [ ] Multi-platform adaptation works (X vs LinkedIn tone difference visible)

### Week 3 Success Criteria
- [ ] Successfully post to X and LinkedIn via API
- [ ] Scheduling queue processes 5 posts without errors
- [ ] Telegram approval workflow functional (inline buttons work)

### Week 4 Success Criteria (Production Readiness)
- [ ] Agent runs on GCP for 72 hours unattended
- [ ] Weekly evaluation passes at >85% overall score
- [ ] Total monthly cost <$100
- [ ] Zero security audit findings

### 90-Day Success Criteria (Post-Launch)
- [ ] 60+ social posts published (20/month average)
- [ ] Zero brand voice incidents (no "AI-sounding" complaints)
- [ ] <2 hours/week maintenance time
- [ ] Evaluation baseline stable (no >10% score drops)

---

## Risk Mitigation

### Risk: Docker Environment Issues
**Probability:** Moderate  
**Impact:** Low (blocks development)

**Mitigations:**
1. Use official Node.js base image (well-tested)
2. Pin all versions (Node 22, Python 3.11, uv 0.1.x)
3. Test Docker build in CI before pushing
4. Keep Dockerfile simple (minimal layers)

**Recovery:**
```bash
# Clear Docker cache and rebuild
docker-compose down -v
docker system prune -a
docker-compose build --no-cache
```

---

### Risk: Terminal Executor Security Bypass
**Probability:** Low  
**Impact:** Critical (command injection)

**Mitigations:**
1. Strict command allowlist (only: cat, ls, uv)
2. Path validation (only ./data/memory/, ./skills/)
3. No shell interpolation (use exec arrays, not strings)
4. Comprehensive tests for bypass attempts
5. Run entire agent in Docker (container isolation)

**Test Cases:**
```typescript
// tests/security.test.ts
test('blocks command chaining', async () => {
  await expect(
    executor.execute('cat file.md && rm -rf /')
  ).rejects.toThrow();
});

test('blocks path traversal', async () => {
  await expect(
    executor.execute('cat ../../etc/passwd')
  ).rejects.toThrow();
});
```

---

### Risk: GCP Storage Sync Failures
**Probability:** Moderate  
**Impact:** Moderate (memory loss on container restart)

**Mitigations:**
1. Local cache always used first (fast reads)
2. GCS sync is async (doesn't block agent)
3. Retry logic for failed uploads (exponential backoff)
4. Development mode skips GCS (offline development)
5. Manual backup via: `gsutil -m cp -r ./data/memory gs://bucket/backup/`

**Monitoring:**
```typescript
// Alert if GCS sync fails >3 times in 1 hour
if (failedSyncs > 3) {
  await telegram.sendMessage(
    ADMIN_CHAT_ID,
    '🚨 GCS sync failing - check credentials and bucket permissions'
  );
}
```

---

### Risk: Brand Voice Drift
**Probability:** Moderate  
**Impact:** High (damages brand reputation)

**Mitigations:**
1. BRAND_VOICE.md always loaded before content generation
2. Forbidden phrase validation on all generated content
3. Weekly AgentTrainings evaluation with alerts
4. Monthly manual audit of 10 random posts
5. Version control for BRAND_VOICE.md (track changes)

**Automated Check:**
```python
# In generate-content.py
FORBIDDEN = ["game-changer", "revolutionary", "disrupt"]

for phrase in FORBIDDEN:
    if phrase.lower() in content.lower():
        raise ValueError(f"Forbidden phrase: {phrase}")
```

---

### Risk: API Cost Overrun
**Probability:** High  
**Impact:** Moderate ($200-500 surprise bills)

**Mitigations:**
1. Set hard GCP billing caps ($150 monthly limit)
2. LLM call rate limiting (max 100 Opus calls/day)
3. Cost tracker logs every LLM call
4. Daily cost report via Telegram
5. Weekly review of LLM usage patterns

**Cost Tracking:**
```typescript
// Track every LLM call
costTracker.trackLLMCall('gemini-flash', 1250 /* tokens */);
costTracker.trackLLMCall('claude-opus', 3400);

// Daily report (scheduled)
await costTracker.sendDailyReport(); // Sends to Telegram
```

---

### Risk: Skills Execution Failures
**Probability:** Moderate  
**Impact:** Moderate (posting stops)

**Mitigations:**
1. Each skill has comprehensive error handling
2. Skills return structured JSON (easy to parse errors)
3. Telegram alerts on skill failures
4. Retry logic with exponential backoff
5. Fallback mode (manual posting instructions)

**Skill Error Pattern:**
```python
# Every skill follows this pattern
try:
    result = do_work()
    print(json.dumps({"success": True, "data": result}))
except Exception as e:
    log_event("ERROR", "skill-name", "failed", trace_id, {"error": str(e)})
    print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
    sys.exit(1)
```

---

### Risk: Evaluation Overfitting
**Probability:** Low  
**Impact:** Moderate (agent optimizes for tests, not real performance)

**Mitigations:**
1. Use train/test split (80/20) in AgentTrainings
2. Regularly add new test cases from production failures
3. Combine automated + manual quality review
4. Test cases cover diverse personas and edge cases

---

### Risk: Logs Become Unreadable
**Probability:** Moderate  
**Impact:** Low (hard to debug)

**Mitigations:**
1. Structured JSON logging (easily parseable)
2. Log levels prevent DEBUG spam in production
3. Trace IDs connect related events
4. Log rotation prevents disk fill
5. Clear log filtering commands documented

**Log Filtering Quick Reference:**
```bash
# Only errors
docker logs social-agent 2>&1 | grep '"level":"ERROR"'

# Specific trace
docker logs social-agent 2>&1 | grep '"traceId":"abc123"'

# Specific skill
docker logs social-agent 2>&1 | grep '"skill":"post-to-x"'

# Today's logs
docker logs --since 24h social-agent

# Export for analysis
docker logs social-agent 2>&1 | jq '.' > logs-export.json
```

---

## Success Metrics

### Week 1 Success Criteria
- [ ] `docker-compose up` builds and starts successfully
- [ ] Agent responds to `/ping` in <1 second
- [ ] Terminal executor can execute: `cat`, `ls`, `uv run`
- [ ] Logs show structured JSON with trace IDs
- [ ] Hot-reload works (edit src/, container restarts)

### Week 2 Success Criteria
- [ ] BRAND_VOICE.md loads correctly
- [ ] Brand voice consistency >90% (manual review of 10 outputs)
- [ ] Memory persists across container restarts
- [ ] GCS sync uploads/downloads memory files
- [ ] Development mode works offline (no GCS required)

### Week 3 Success Criteria
- [ ] Content generator creates platform-specific posts
- [ ] Web search returns grounded results with sources
- [ ] Post-to-x skill successfully posts to X/Twitter
- [ ] Full workflow: search → generate → post (via Telegram)
- [ ] Logs show complete execution trace for workflow

### Week 4 Success Criteria (Production Readiness)
- [ ] Agent runs on GCP for 72 hours unattended
- [ ] Weekly evaluation passes at >85% overall score
- [ ] Total monthly cost <$100 (verified via cost tracker)
- [ ] Zero security audit findings
- [ ] Systemd service auto-restarts on failure
- [ ] Telegram alerts fire for errors and cost overruns
- [ ] All skills have tests with >80% coverage

### 90-Day Success Criteria (Post-Launch)
- [ ] 60+ social posts published (20/month average)
- [ ] Zero brand voice incidents (no "AI-sounding" complaints)
- [ ] <2 hours/week maintenance time
- [ ] Evaluation baseline stable (no >10% score drops)
- [ ] Monthly cost <$100 (tracked and verified)
- [ ] Agent uptime >99% (measured by health checks)

---

## Conclusion: Why This Approach Works

This implementation plan is optimized for **solo developer productivity** with **Cursor AI assistance**:

### Technical Strengths
1. **Docker-first:** Develop locally, deploy identically to GCP
2. **File-system native:** Agent interacts via terminal (observable, debuggable)
3. **CLI skills:** Testable outside agent, portable across projects
4. **Structured logs:** Trace requests end-to-end with trace IDs
5. **Local-first memory:** GCP Storage for persistence, local cache for speed

### Development Velocity
1. **Cursor integration:** AI assists with every component
2. **Hot-reload:** See changes immediately without rebuild
3. **Clear interfaces:** Each component has single responsibility
4. **Comprehensive tests:** Catch bugs before they reach production
5. **Incremental progress:** 4 weeks of concrete, testable milestones

### Production Readiness
1. **Security-hardened:** Terminal executor allowlist, no marketplace skills
2. **Cost-optimized:** LLM routing, rate limiting, billing alerts
3. **Quality-assured:** Weekly evaluations catch drift automatically
4. **Observable:** Structured logs, trace IDs, cost tracking
5. **Maintainable:** Clear code, good tests, documentation

### Why It Differs from OpenClaw
- **Simpler:** No browser automation, no multi-protocol messaging
- **Safer:** No malicious marketplace skills, strict command allowlist
- **Cheaper:** No heartbeat burn, intelligent LLM routing
- **More Observable:** Structured logs, trace IDs, GCP Storage
- **More Testable:** CLI skills, Docker isolation, comprehensive tests

**Expected outcome:** A production-ready social media agent that:
- Costs <$100/month (including infrastructure + API calls)
- Requires <2 hours/week maintenance
- Produces brand-consistent content at scale
- Can be developed solo in 4 weeks with Cursor assistance

**The 4-week timeline is achievable because:**
1. Docker eliminates environment issues
2. Cursor generates boilerplate code
3. CLI skills are simple and testable
4. GCP Storage is straightforward
5. AgentTrainings is already built

Start with Week 1, ship incremental progress, and you'll have a working agent by end of month.

---

## Appendix: Quick Reference

### Essential Commands

**Docker Operations:**
```bash
# Start agent
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker logs -f social-agent

# Rebuild after changes
docker-compose up --build

# Execute command in container
docker exec social-agent <command>

# Shell into container
docker exec -it social-agent bash

# Stop agent
docker-compose down

# Clear everything and rebuild
docker-compose down -v && docker-compose build --no-cache
```

**Testing Skills:**
```bash
# Test content generation
docker exec social-agent uv run ./skills/generate-content.py "AI agents" --platform x

# Test web search
docker exec social-agent uv run ./skills/search-web.py "latest AI trends"

# Test X posting (dry run)
docker exec social-agent ./skills/post-to-x.sh "Test tweet"

# Test terminal executor
docker exec social-agent cat ./data/memory/BRAND_VOICE.md
```

**Log Analysis:**
```bash
# Filter by level
docker logs social-agent 2>&1 | grep '"level":"ERROR"'

# Filter by trace ID
docker logs social-agent 2>&1 | grep '"traceId":"abc123"'

# Filter by skill
docker logs social-agent 2>&1 | grep '"skill":"post-to-x"'

# Export logs
docker logs social-agent > logs-$(date +%Y%m%d).log

# Parse JSON logs
docker logs social-agent 2>&1 | jq 'select(.level == "ERROR")'
```

**GCP Storage:**
```bash
# List memory files
gsutil ls gs://social-agent-memory-${PROJECT_ID}/

# Download memory backup
gsutil -m cp -r gs://social-agent-memory-${PROJECT_ID}/* ./backup/

# Upload new BRAND_VOICE.md
gsutil cp ./data/memory/BRAND_VOICE.md gs://social-agent-memory-${PROJECT_ID}/
```

**Development:**
```bash
# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Lint code
npm run lint

# Format code
npm run format

# Build TypeScript
npm run build
```

### File Locations

**Source Code:**
- `src/` - TypeScript source
- `dist/` - Compiled JavaScript
- `skills/` - CLI skill scripts

**Data:**
- `data/memory/` - Local memory cache
- `logs/` - Application logs
- `tests/` - Test files
- `evals/` - AgentTrainings eval configs

**Configuration:**
- `.env` - Environment variables (secrets)
- `docker-compose.yml` - Docker orchestration
- `Dockerfile` - Container definition
- `tsconfig.json` - TypeScript config
- `package.json` - Node.js dependencies

### OpenClaw Reference Files

When extracting patterns from OpenClaw, study these files:

**Gateway & Messaging:**
- `packages/gateway/src/daemon.ts` - Main server logic
- `packages/gateway/src/protocols/telegram.ts` - Telegram integration

**Memory:**
- `packages/core/src/memory/markdown-memory.ts` - File-based persistence

**Scheduling:**
- `packages/core/src/scheduler/cron.ts` - Cron job system

**LLM Integration:**
- `packages/llm/src/router.ts` - Model selection logic
- `packages/llm/src/vertex-ai.ts` - Vertex AI adapter

**⚠️ Important:** Read for architecture patterns, don't copy code directly (license risk).

---

## Next Steps (First 48 Hours)

### Immediate Actions
1. **Clone OpenClaw repository** for reference (do NOT run it):
   ```bash
   git clone https://github.com/openclaw/openclaw.git openclaw-reference
   ```

2. **Create new clean repository** for your agent:
   ```bash
   mkdir social-agent
   cd social-agent
   git init
   npm init -y
   ```

3. **Extract Gateway daemon code**:
   - Study `openclaw-reference/packages/gateway/src/daemon.ts`
   - Identify loopback binding, message queue, graceful shutdown patterns
   - Rewrite in your repository (do NOT copy/paste, avoid license issues)

4. **Set up Telegram bot**:
   - Message @BotFather on Telegram
   - Create new bot, get API token
   - Save to `.env` file (never commit)

5. **Install AgentTrainings**:
   ```bash
   cd ..
   git clone [agent-training-repo]
   pip install -e agent-training/
   ```

### Day 2 Focus
6. **Build minimal gateway**:
   - HTTP server on port 18789
   - Single route: POST /message
   - Responds with "Echo: {message}"

7. **Connect Telegram bot**:
   - Install `node-telegram-bot-api`
   - Forward Telegram messages to gateway
   - Return gateway response to user

8. **First integration test**:
   - Send `/ping` from Telegram
   - Verify response in <1 second
   - Confirm logs show request flow

### Week 1 Checkpoint
By end of Week 1, you should have:
- ✅ Local agent responding to Telegram
- ✅ Basic LLM integration (Gemini Flash)
- ✅ Simple command routing (`/help`, `/generate`)
- ✅ Dev environment configured (ESLint, VS Code)

**If blocked, revisit:**
- Gateway daemon implementation (reference OpenClaw code)
- Telegram bot API docs (https://core.telegram.org/bots/api)
- Vertex AI authentication guide (Application Default Credentials)

---

## Appendix: Key Files to Reference in OpenClaw

When extracting components, study these specific files:

### Gateway Daemon
- `packages/gateway/src/daemon.ts` - Main server logic
- `packages/gateway/src/message-queue.ts` - Request queuing
- `packages/gateway/src/protocols/telegram.ts` - Telegram integration

### Memory System
- `packages/core/src/memory/markdown-memory.ts` - File-based persistence
- `packages/core/src/memory/compaction.ts` - Memory summarization

### Task Scheduling
- `packages/core/src/scheduler/cron.ts` - Cron job system
- `packages/core/src/scheduler/task-queue.ts` - BullMQ integration

### Skills System
- `packages/skills/src/skill-loader.ts` - Skill registration
- `packages/skills/src/twitter-skill.ts` - Example X/Twitter skill

### LLM Integration
- `packages/llm/src/router.ts` - Model selection logic
- `packages/llm/src/vertex-ai.ts` - Vertex AI adapter

**Warning:** Do NOT copy code directly (license risk). Read for architecture patterns, then implement your own version.

---

## Conclusion: Why This Approach Works

This implementation plan balances **speed, security, and sustainability** by:

1. **Extracting proven patterns** (Gateway daemon, persistent memory) without inheriting technical debt
2. **Focusing on single use case** (social media) rather than building general assistant
3. **Adding evaluation from day 1** to prevent quality degradation
4. **Cost-optimizing aggressively** (LLM routing, no heartbeat) to stay under $100/month
5. **Security-hardening proactively** (no marketplace, sandboxed execution) to avoid CrowdStrike-reported vulnerabilities

**The 4-week timeline is aggressive but achievable** because we're not building from scratch - we're assembling proven components into a focused tool.

**This is the "Cursor Approach":** Use AI-assisted development (Cursor IDE) to accelerate implementation, but maintain human oversight of architecture decisions. The goal is a codebase you understand and control, not a black box.

**Expected outcome:** A production-ready social media agent that costs <$100/month, requires <2 hours/week maintenance, and produces brand-consistent content at scale.
