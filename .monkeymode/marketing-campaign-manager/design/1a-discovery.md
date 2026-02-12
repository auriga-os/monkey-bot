# Design: Marketing Campaign Manager - Phase 1A

**Date:** 2026-02-11  
**Status:** Draft  
**Author:** MonkeyMode Agent

---

## Executive Summary

Build a specialized marketing automation agent by extending the open-source **monkey-bot** framework with domain-specific marketing capabilities. The solution uses a **two-repo architecture**: keep the general-purpose framework public (monkey-bot) while housing all marketing-specific skills and configuration in a separate private repo (auriga-marketing-bot). The agent will automate social media campaigns across Instagram, TikTok, Reddit, LinkedIn, and X through research, content generation, approval workflows, and scheduled posting.

**Key Innovation:** Extend monkey-bot as a **framework** rather than forking, enabling both public contribution and private deployment.

---

## Use Case & Business Value

### Problem Statement
Auriga OS team needs to maintain consistent, high-quality social media presence across 5 platforms (Instagram, TikTok, Reddit, LinkedIn, X) with 2-5 posts per platform per week. Manual posting is time-consuming and inconsistent.

### Target Users
- Primary: Auriga OS team (immediate)
- Secondary: Potential packaged product for other users (future)

### Success Metrics
1. **Automation Rate**: 100% of posts scheduled and posted automatically after approval
2. **Engagement Growth**: Track likes, shares, comments over time
3. **Brand Awareness**: Increase followers and user base
4. **Time Savings**: Reduce manual posting time from ~5 hours/week to ~1 hour (approval only)

### Expected Volume
- **Posting Frequency**: 2-5 posts per platform per week = 10-25 posts/week total
- **Concurrent Campaigns**: ~5 campaigns running simultaneously
- **Approval Requests**: 10-25 posts/week requiring Google Chat approval

### Out of Scope (Phase 2)
- Analytics dashboard (can add later)
- A/B testing (can add later)
- Paid advertising integration (organic only for now)
- Image generation (can use existing tools initially)

---

## Architecture Decision

### Chosen Approach: Two-Repo Extension Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PUBLIC: monkey-bot (Framework)                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Core Framework                           │   │
│  │  - Agent Core (LangGraph)                                    │   │
│  │  - LLM Client (Vertex AI)                                    │   │
│  │  - Skills Engine (extensible loader)                         │   │
│  │  - Memory Manager                                            │   │
│  │  - Terminal Executor                                         │   │
│  │  - Gateway (Google Chat)                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Phase 2 Enhancements (Public)                   │   │
│  │  - MCP Integration Layer (generic wrappers)                  │   │
│  │  - Approval Workflow System (abstract interface)            │   │
│  │  - Cron Scheduler (job scheduling engine)                   │   │
│  │  - Enhanced Skill Loader (env var injection)                │   │
│  │  - Brand Voice Validator (generic, configurable)            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ depends on (pip install)
                                    │
┌─────────────────────────────────────────────────────────────────────┐
│              PRIVATE: auriga-marketing-bot (Implementation)         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  Marketing Skills (Private)                  │   │
│  │  - skills/research/    (web search, competitor analysis)     │   │
│  │  - skills/campaign/    (planning, generation, scheduling)    │   │
│  │  - skills/posting/     (Instagram, TikTok, X, etc.)         │   │
│  │  - skills/approval/    (Google Chat approval UI)            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                Configuration & Data (Private)                │   │
│  │  - data/memory/BRAND_VOICE.md  (Auriga brand voice)         │   │
│  │  - data/memory/campaigns/      (campaign storage)            │   │
│  │  - .env                         (API keys, secrets)          │   │
│  │  - deploy.sh                    (custom deployment)          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Why This Approach?

**Advantages:**
1. ✅ **Clean Separation**: Public framework code never touches private marketing logic
2. ✅ **Open Source Contribution**: Can improve framework and share back to community
3. ✅ **Security**: API keys, brand voice, and custom skills stay 100% private
4. ✅ **Reusability**: Other teams can use same pattern (their own private repo + public framework)
5. ✅ **Maintenance**: Framework updates don't require forking/merging
6. ✅ **Deployment**: Private repo controls deployment independently

**Trade-offs:**
- Requires careful interface design (framework must be extensible)
- Two repos to manage (but clear ownership boundaries)
- Framework changes require versioning (but this is good practice anyway)

### Alternatives Considered

| Approach | Pros | Cons | Why Not Chosen |
|----------|------|------|----------------|
| **Single Private Fork** | Simple single repo | Can't contribute framework improvements back, hard to sync upstream changes | Defeats open source goal |
| **Gitignored Directory** | Single repo checkout | Easy to accidentally commit secrets, messy .gitignore | Security risk too high |
| **Branch-Based Separation** | Easy to test both | Complicated branch management, risk of wrong merge | Too error-prone |
| **Two-Repo Extension** ✅ | Clean separation, open source friendly, secure | Two repos to manage | **Best balance of goals** |

---

## Architecture Diagram

### High-Level System Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            User (via Google Chat)                        │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 │ "Create a 4-week campaign about AI agents"
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     monkey-bot Gateway (Google Chat)                     │
│                     - Authentication (ALLOWED_USERS)                     │
│                     - PII Filtering                                      │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   Agent Core (LangGraph + Gemini 2.5)                    │
│                   - Load conversation history (last 10)                  │
│                   - Route to appropriate skill                           │
└────┬─────────────────────┬──────────────────────┬─────────────────┬──────┘
     │                     │                      │                 │
     ▼                     ▼                      ▼                 ▼
┌─────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌─────────────┐
│  Research   │   │  Campaign    │   │    Posting       │   │  Approval   │
│  Skills     │   │  Skills      │   │    Skills        │   │  Skills     │
│  (PRIVATE)  │   │  (PRIVATE)   │   │    (PRIVATE)     │   │  (PRIVATE)  │
└──────┬──────┘   └──────┬───────┘   └─────────┬────────┘   └──────┬──────┘
       │                 │                     │                    │
       │ MCP calls       │ Brand voice         │ Social APIs        │ GChat
       ▼                 ▼                     ▼                    ▼
┌─────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌─────────────┐
│ Perplexity  │   │ Brand Voice  │   │  Instagram API   │   │ Google Chat │
│ Firecrawl   │   │ Validator    │   │  TikTok API      │   │ Approval UI │
│ Playwright  │   │ (Framework)  │   │  Reddit API      │   │ (Framework) │
└─────────────┘   └──────────────┘   │  LinkedIn API    │   └─────────────┘
                                     │  X API           │
                                     └──────────────────┘
                                            │
                                            ▼ post_to_<platform>
                                     ┌──────────────────┐
                                     │ Cron Scheduler   │
                                     │ (Framework)      │
                                     │ - Schedule posts │
                                     │ - Execute jobs   │
                                     └──────────────────┘
```

### Campaign Workflow Sequence

```
User: "Create 4-week AI campaign"
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ 1. Research Phase (skills/research/)                     │
│    - search_web.py (Perplexity MCP)                      │
│    - analyze_competitor.py (Firecrawl MCP)               │
│    - identify_trends.py (aggregation + LLM)              │
│    Output: Research summary + content gaps               │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 2. Campaign Planning (skills/campaign/)                  │
│    - create_campaign.py                                  │
│      * Define theme, content pillars                     │
│      * Create content calendar (dates, platforms)        │
│      * Generate post ideas                               │
│    Output: ./data/memory/campaigns/{id}/plan.json        │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 3. Content Generation (skills/content/)                  │
│    - generate_content.py                                 │
│      * Load BRAND_VOICE.md                               │
│      * Generate posts for each platform                  │
│      * Validate against brand voice                      │
│    Output: ./data/memory/campaigns/{id}/posts.json       │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│ 4. Approval Request (skills/approval/)                   │
│    - request_approval.py                                 │
│      * Format posts in Google Chat cards                 │
│      * Send to user with Approve/Reject buttons          │
│      * Wait for user response                            │
│    Output: Approval status (approved/rejected/modified)  │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼ (if approved)
┌──────────────────────────────────────────────────────────┐
│ 5. Scheduling (skills/campaign/)                         │
│    - schedule_campaign.py                                │
│      * Create cron job for each post                     │
│      * Store in ./data/memory/cron_jobs.json             │
│    Output: Scheduled jobs ready for execution            │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼ (at scheduled time)
┌──────────────────────────────────────────────────────────┐
│ 6. Posting (skills/posting/)                             │
│    - post_to_instagram.py                                │
│    - post_to_tiktok.py                                   │
│    - post_to_reddit.py                                   │
│    - post_to_linkedin.py                                 │
│    - post_to_x.py                                        │
│    Output: Posted content + URLs                         │
└──────────────────────────────────────────────────────────┘
```

---

## Repository Structure

### Public Repo: monkey-bot (Framework Enhancements)

**See `docs/phases/phase-2-marketing-campaign.md` for complete framework changes.**

Summary of enhancements (POST vertical slice):
- Enhanced SkillLoader (expose descriptions to LLM)
- ApprovalInterface (generic approval pattern)
- CronScheduler (generic job scheduling)
- MCP integration utilities (optional)

### Private Repo: auriga-marketing-bot (Implementation)

**Corrected Skill Structure** (based on Cursor skills blog best practices):

```
auriga-marketing-bot/
├── skills/                      # Marketing skills (PRIVATE)
│   │
│   ├── generate-post/           # Content generation (VERTICAL SLICE - Build First)
│   │   ├── SKILL.md             # name: generate-post
│   │   │                        # description: "Create social media content for any platform..."
│   │   └── generate_post.py
│   │
│   ├── request-approval/        # Approval workflow (VERTICAL SLICE)
│   │   ├── SKILL.md             # name: request-approval
│   │   │                        # description: "Send content to Google Chat for approval..."
│   │   └── request_approval.py
│   │
│   ├── post-content/            # Platform posting (VERTICAL SLICE)
│   │   ├── SKILL.md             # name: post-content
│   │   │                        # description: "Publish content to social platforms..."
│   │   ├── post_content.py      # Single file, platform parameter
│   │   └── platforms/           # Platform-specific helpers
│   │       ├── instagram.py
│   │       ├── tiktok.py
│   │       ├── x.py
│   │       ├── linkedin.py
│   │       └── reddit.py
│   │
│   ├── search-web/              # Web research (Add after vertical slice)
│   │   ├── SKILL.md             # name: search-web
│   │   │                        # description: "Search web for current information..."
│   │   └── search_web.py        # Perplexity MCP wrapper
│   │
│   ├── analyze-competitor/      # Competitor analysis (Separate from search!)
│   │   ├── SKILL.md             # name: analyze-competitor
│   │   │                        # description: "Analyze competitor websites..."
│   │   └── analyze_competitor.py # Firecrawl MCP wrapper
│   │
│   ├── identify-trends/         # Trend identification (Separate from search!)
│   │   ├── SKILL.md             # name: identify-trends
│   │   │                        # description: "Identify content trends and gaps..."
│   │   └── identify_trends.py
│   │
│   ├── create-campaign/         # Campaign planning (Uses menu pattern)
│   │   ├── SKILL.md             # name: create-campaign, references sub-files
│   │   ├── create_campaign.py   # Main orchestrator
│   │   ├── research_topic.md    # Step 1 instructions
│   │   ├── define_strategy.md   # Step 2 instructions
│   │   ├── generate_calendar.md # Step 3 instructions
│   │   └── create_post_ideas.md # Step 4 instructions
│   │
│   └── schedule-campaign/       # Campaign scheduling
│       ├── SKILL.md             # name: schedule-campaign
│       │                        # description: "Schedule campaign posts for future..."
│       └── schedule_campaign.py
│
├── data/
│   └── memory/
│       ├── BRAND_VOICE.md       # Auriga brand voice (PRIVATE)
│       ├── campaigns/           # Campaign data (PRIVATE)
│       │   └── {campaign_id}/
│       │       ├── plan.json
│       │       └── posts.json
│       └── cron_jobs.json       # Scheduled jobs
│
├── .env                         # PRIVATE: API keys, secrets
├── .gitignore                   # Ignore .env, data/, etc.
├── requirements.txt             # Includes: monkey-bot>=2.0.0
├── deploy.sh                    # Custom deployment (uses monkey-bot base)
└── README.md                    # Private documentation
```

**Key Corrections:**
1. ✅ **Posting skills merged**: One `post-content` skill with platform parameter (not 5 separate skills)
2. ✅ **Research skills split**: Separate skills for search-web, analyze-competitor, identify-trends
3. ✅ **Menu pattern**: `create-campaign` uses menu pattern with sub-files
4. ✅ **SKILL.md descriptions**: Each SKILL.md has triggering descriptions in frontmatter
5. ✅ **Vertical slice prioritized**: generate-post, request-approval, post-content built first

**Key Files in .env (Private):**
```bash
# Inherit from monkey-bot
SKILLS_DIR=./skills              # Point to private skills
MEMORY_DIR=./data/memory         # Private memory

# MCP API Keys (for research skills)
PERPLEXITY_API_KEY=xxx
FIRECRAWL_API_KEY=xxx

# Social Media API Keys (for posting skills)
INSTAGRAM_API_KEY=xxx
TIKTOK_API_KEY=xxx
REDDIT_API_KEY=xxx
LINKEDIN_API_KEY=xxx
X_API_KEY=xxx

# Deployment
AGENT_NAME=auriga-marketing-bot
CLOUD_RUN_SERVICE_NAME=auriga-marketing-bot
```

---

## Core Data Model

### Campaign Entity

```python
Campaign
├── id: str (UUID) - Unique campaign identifier
├── topic: str - Campaign topic (e.g., "AI agent evaluation frameworks")
├── duration_weeks: int - Campaign duration (e.g., 4)
├── platforms: List[str] - Target platforms (["instagram", "tiktok", "x", ...])
├── status: str - Status: "draft" | "approved" | "scheduled" | "active" | "completed"
├── created_at: str (ISO8601) - Campaign creation timestamp
├── created_by: str - User who created campaign (Google Chat email)
├── approved_at: str | None (ISO8601) - Approval timestamp
├── approved_by: str | None - User who approved
├── research_summary: dict | None - Research data from Phase 1
├── strategy: dict - Campaign strategy (theme, pillars, cadence)
├── calendar: List[dict] - Content calendar (posts with dates/platforms)
└── updated_at: str (ISO8601) - Last modification timestamp

Relationships:
- Campaign has many Posts (1:N)

Storage:
- File: ./data/memory/campaigns/{campaign_id}/plan.json
- GCS: gs://{bucket}/campaigns/{campaign_id}/plan.json (if GCS_ENABLED)

Indexes:
- PRIMARY KEY (id)
- INDEX on (created_by, status) - List campaigns by user and status
- INDEX on (status, created_at) - Active campaigns sorted by date
```

### Post Entity

```python
Post
├── id: str (UUID) - Unique post identifier
├── campaign_id: str - Parent campaign ID
├── platform: str - Target platform ("instagram" | "tiktok" | "reddit" | "linkedin" | "x")
├── content: str - Post text content
├── media_urls: List[str] | None - Media attachments (images, videos)
├── scheduled_at: str (ISO8601) - Scheduled posting time
├── status: str - Status: "draft" | "approved" | "scheduled" | "posted" | "failed"
├── posted_at: str | None (ISO8601) - Actual posting timestamp
├── platform_post_id: str | None - ID from platform (for tracking engagement)
├── platform_post_url: str | None - URL to live post
├── error: str | None - Error message if posting failed
├── approval_status: str - "pending" | "approved" | "rejected" | "modified"
├── approved_by: str | None - User who approved
├── approved_at: str | None (ISO8601) - Approval timestamp
└── created_at: str (ISO8601) - Post creation timestamp

Relationships:
- Post belongs to Campaign (N:1)

Storage:
- File: ./data/memory/campaigns/{campaign_id}/posts.json (array)
- GCS: gs://{bucket}/campaigns/{campaign_id}/posts.json (if GCS_ENABLED)

Indexes:
- PRIMARY KEY (id)
- INDEX on (campaign_id, scheduled_at) - Posts for campaign sorted by schedule
- INDEX on (status, scheduled_at) - Pending posts sorted by schedule
- INDEX on (platform, status) - Posts by platform and status
```

### Cron Job Entity

```python
CronJob
├── id: str (UUID) - Unique job identifier
├── job_type: str - Job type ("post_content" | "campaign_check" | "analytics_sync")
├── schedule: dict - Schedule definition
│   ├── kind: str - "at" (one-time) | "cron" (recurring) | "every" (interval)
│   ├── expr: str | None - Cron expression (if kind="cron")
│   ├── at: str | None - ISO8601 timestamp (if kind="at")
│   └── everyMs: int | None - Interval in milliseconds (if kind="every")
├── payload: dict - Job-specific data
│   ├── post_id: str | None - Post ID to publish (if job_type="post_content")
│   ├── campaign_id: str | None - Campaign ID to check (if job_type="campaign_check")
│   └── ... - Other job-specific fields
├── status: str - Status: "pending" | "running" | "completed" | "failed" | "cancelled"
├── next_run_at: str | None (ISO8601) - Next scheduled execution time
├── last_run_at: str | None (ISO8601) - Last execution time
├── last_run_result: dict | None - Last execution result
│   ├── success: bool - Execution success
│   ├── output: str | None - Output/logs
│   └── error: str | None - Error message
├── created_at: str (ISO8601) - Job creation timestamp
└── created_by: str - User who created job

Storage:
- File: ./data/memory/cron_jobs.json (array)
- GCS: gs://{bucket}/cron_jobs.json (if GCS_ENABLED)

Indexes:
- PRIMARY KEY (id)
- INDEX on (status, next_run_at) - Pending jobs sorted by next run
- INDEX on (job_type, status) - Jobs by type and status
```

### Brand Voice Entity

```markdown
BrandVoice (stored as Markdown document)
├── core_values: List[str] - Core brand values
├── tone_guidelines: List[str] - Tone rules
├── writing_style: dict - Style rules (sentence length, voice, etc.)
├── platform_adaptations: dict - Platform-specific rules
│   ├── instagram: dict
│   ├── tiktok: dict
│   ├── reddit: dict
│   ├── linkedin: dict
│   └── x: dict
├── forbidden_phrases: List[str] - Phrases to avoid
├── example_posts: dict - Good and bad examples by platform
└── validation_checklist: List[str] - Pre-post validation items

Storage:
- File: ./data/memory/BRAND_VOICE.md
- GCS: gs://{bucket}/BRAND_VOICE.md (if GCS_ENABLED)

Usage:
- Loaded by generate_content.py before creating posts
- Used by brand_voice.py validator to check content
- Referenced by LLM in system prompt for content generation
```

---

## Framework Enhancements Needed (Public Repo)

**See `docs/phases/phase-2-marketing-campaign.md` for complete framework enhancements.**

Summary:
1. **Enhanced Skill Loader** (CRITICAL - Do First): Expose SKILL.md descriptions to LLM routing
2. **Approval Interface** (After vertical slice): Generic approval pattern
3. **Cron Scheduler** (After scheduling works): Job scheduling system
4. **MCP Utilities** (Optional): Generic MCP server wrappers

**Approach:** Build vertical slice in PRIVATE repo first, then extract generic components to PUBLIC framework.

---

## Detailed Skill Designs (Private Repo)

### Skill 1: generate-post (VERTICAL SLICE - Build First)

**File:** `skills/generate-post/SKILL.md`

```markdown
---
name: generate-post
description: Create social media content for any platform (Instagram, TikTok, X, LinkedIn, Reddit). Automatically validates character limits and brand voice. Use when user wants to create, write, draft, or generate a post.
metadata:
  emonk:
    requires:
      env: []
---

# Generate Social Media Post

Creates platform-specific social media content optimized for engagement.

## When to Use This Skill

Invoke this skill when the user:
- Wants to create a new social media post
- Says "write a post about [topic]"
- Requests "draft Instagram caption for [topic]"
- Says "generate content for X about [topic]"

## Parameters

- `topic` (required): What the post is about
- `platform` (required): Target platform ("instagram", "tiktok", "x", "linkedin", "reddit")
- `tone` (optional): Desired tone ("professional", "casual", "humorous")
- `include_hashtags` (optional): Whether to add hashtags (default: true for Instagram/TikTok)

## Success Criteria

A good post has:
- ✅ Appropriate length for platform (see limits below)
- ✅ Engaging hook in first line
- ✅ Clear call-to-action
- ✅ Platform-appropriate hashtags (if applicable)
- ✅ No forbidden brand voice phrases (if BRAND_VOICE.md exists)

## Platform Limits

| Platform | Character Limit | Hashtag Recommendation |
|----------|----------------|------------------------|
| Instagram | 2200 | 3-5 hashtags |
| TikTok | 2200 | 3-5 hashtags |
| X | 280 | 1-2 hashtags |
| LinkedIn | 3000 | 3-5 hashtags |
| Reddit | 40000 | No hashtags (use flair) |

## Output Format

```json
{
  "success": true,
  "post": {
    "platform": "instagram",
    "content": "Post text here...",
    "hashtags": ["#AI", "#TechInnovation"],
    "character_count": 285,
    "validation": {
      "within_limit": true,
      "has_hook": true,
      "has_cta": true,
      "brand_voice_valid": true
    }
  }
}
```

## Error Handling

- If BRAND_VOICE.md exists but post violates it, return error with specifics
- If platform is unknown, return error with valid platforms
- If content generation fails, return error with reason
```

---

### Skill 2: request-approval (VERTICAL SLICE)

**File:** `skills/request-approval/SKILL.md`

```markdown
---
name: request-approval
description: Send content to Google Chat for user approval before posting. Returns approved/rejected status with optional feedback. Use when user wants to review content before it goes live.
metadata:
  emonk:
    requires:
      env: []
---

# Request Approval for Content

Sends content to Google Chat with Approve/Reject/Modify buttons and waits for user response.

## When to Use This Skill

Invoke when user:
- Says "send this for approval"
- Wants to "review before posting"
- Says "let me see it first"
- Says "get my approval"

## Parameters

- `content` (required): The content to approve (post text, campaign plan, etc.)
- `content_type` (required): Type of content ("social_post", "campaign", "image")
- `platform` (optional): Target platform if social post
- `timeout_seconds` (optional): How long to wait for approval (default: 3600 = 1 hour)

## Approval Flow

1. Format content as Google Chat interactive card
2. Add buttons: "✅ Approve", "❌ Reject", "✏️ Modify"
3. Send to user via Google Chat
4. Wait for user interaction (up to timeout)
5. Return approval result

## Output Format

```json
{
  "success": true,
  "approved": true,
  "feedback": "Looks great! Ship it.",
  "modified_content": null,
  "timestamp": "2026-02-11T09:00:00Z"
}
```

If user clicked "Modify":
```json
{
  "success": true,
  "approved": false,
  "feedback": "Change the hashtags",
  "modified_content": "Updated content here...",
  "timestamp": "2026-02-11T09:05:00Z"
}
```

## Error Handling

- If timeout expires, return error: "Approval timeout - no response in {timeout} seconds"
- If Google Chat API fails, return error with details
- If content is empty, return error: "Cannot request approval for empty content"
```

---

### Skill 3: post-content (VERTICAL SLICE)

**File:** `skills/post-content/SKILL.md`

```markdown
---
name: post-content
description: Publish approved content to social media platforms (Instagram, TikTok, X, LinkedIn, Reddit). Requires content to be pre-approved. Returns live post URL.
metadata:
  emonk:
    requires:
      env: ["INSTAGRAM_API_KEY", "TIKTOK_API_KEY", "X_API_KEY", "LINKEDIN_API_KEY", "REDDIT_API_KEY"]
---

# Post Content to Social Media

Publishes content to specified platform using platform API.

## When to Use This Skill

Invoke when user:
- Says "post this to [platform]"
- Says "publish to Instagram"
- Says "go live on X"
- Has already approved content (check approval status first!)

## Parameters

- `content` (required): Post content (text)
- `platform` (required): Target platform ("instagram", "tiktok", "x", "linkedin", "reddit")
- `media_urls` (optional): List of image/video URLs to attach
- `scheduled_time` (optional): ISO8601 timestamp for scheduled post (if not now)

## Pre-Posting Validation

Before posting, verify:
1. Content was approved (check approval_status)
2. Platform API key exists in environment
3. Content meets platform requirements (length, media format)

## Output Format

```json
{
  "success": true,
  "platform": "x",
  "post_id": "1234567890",
  "post_url": "https://x.com/auriga_os/status/1234567890",
  "posted_at": "2026-02-11T09:10:00Z"
}
```

## Error Handling

- If content not approved, return error: "Content must be approved before posting"
- If API key missing, return error: "Missing API key for {platform}"
- If platform API fails, return error with platform-specific details
- If media upload fails, return error with media URL

## Platform-Specific Notes

### Instagram
- Requires at least 1 image (1080x1080 minimum)
- Captions support newlines and emojis
- Max 30 hashtags

### TikTok
- Requires video (min 3 seconds, max 10 minutes)
- Caption max 2200 characters
- Hashtags count toward character limit

### X
- Text-only posts supported
- Max 280 characters (strict)
- Media optional (images/GIFs/videos)

### LinkedIn
- Text-only or with single image/document
- Professional tone expected
- Max 3000 characters

### Reddit
- Subreddit must be specified (add `subreddit` parameter)
- Follows subreddit rules (bot must check)
- Can be text or link post
```

---

### Skill 4: search-web (Build After Vertical Slice)

**File:** `skills/search-web/SKILL.md`

```markdown
---
name: search-web
description: Search the web for current information, trending topics, or recent articles. Returns titles, URLs, snippets, and citations. Use when user needs recent data or wants to research a topic.
metadata:
  emonk:
    requires:
      env: ["PERPLEXITY_API_KEY"]
---

# Search Web for Current Information

Uses Perplexity MCP server to search web with citations.

## When to Use This Skill

Invoke when user:
- Asks "what's trending about [topic]?"
- Says "search for recent articles on [topic]"
- Wants to "research [topic]"
- Needs current information (not in LLM training data)

## Parameters

- `query` (required): Search query
- `limit` (optional): Max results to return (default: 10, max: 20)
- `recency` (optional): Filter by date ("day", "week", "month", "year")

## Output Format

```json
{
  "success": true,
  "query": "AI agent evaluation frameworks",
  "results": [
    {
      "title": "Building Trust in AI Agents",
      "url": "https://example.com/article",
      "snippet": "Recent approaches to evaluating...",
      "source": "TechCrunch",
      "published_date": "2026-02-10"
    }
  ],
  "citations": ["https://example.com/article"]
}
```

## Success Criteria

Good search results have:
- ✅ Relevant to query
- ✅ Recent (within recency filter if specified)
- ✅ Diverse sources (not all from one site)
- ✅ High-quality sites (no spam/low-quality)
```

---

### Skill 5: create-campaign (Menu Pattern Example)

**File:** `skills/create-campaign/SKILL.md`

```markdown
---
name: create-campaign
description: Plan a complete social media campaign including research, strategy, and content calendar. Use when user wants to create a multi-week campaign or plan content strategy.
metadata:
  emonk:
    requires:
      env: ["PERPLEXITY_API_KEY"]
---

# Create Marketing Campaign

Plans comprehensive social media campaign with research and content calendar.

## When to Use This Skill

Invoke when user:
- Says "create a campaign about [topic]"
- Wants to "plan 4 weeks of content"
- Asks for "content strategy for [topic]"

## Workflow (Menu Pattern)

This skill follows a multi-step process. Each step has detailed instructions in separate files:

### Step 1: Research Topic → See `research_topic.md`

- Web search for trending content
- Competitor analysis
- Content gap identification
- Output: Research summary

### Step 2: Define Strategy → See `define_strategy.md`

- Choose theme and content pillars
- Set posting cadence per platform
- Define success metrics
- Output: Campaign strategy

### Step 3: Generate Calendar → See `generate_calendar.md`

- Create posting schedule
- Assign content pillars to dates
- Balance platforms
- Output: Content calendar

### Step 4: Create Post Ideas → See `create_post_ideas.md`

- Generate specific post topics
- Assign to calendar dates
- Output: Post ideas

## Parameters

- `topic` (required): Campaign topic
- `duration_weeks` (required): Campaign duration (1-12 weeks)
- `platforms` (required): List of platforms (["instagram", "tiktok", "x", "linkedin", "reddit"])
- `posting_frequency` (optional): Posts per week per platform (default: 3)

## Output Format

Saves complete campaign plan to:
`./data/memory/campaigns/{campaign_id}/plan.json`

Returns campaign ID for reference.
```

**Menu Files:**

- `research_topic.md`: Detailed instructions for Step 1
- `define_strategy.md`: Detailed instructions for Step 2
- `generate_calendar.md`: Detailed instructions for Step 3
- `create_post_ideas.md`: Detailed instructions for Step 4

This keeps main SKILL.md concise while providing rich guidance.

---

## Development Approach: Vertical Slice First

### Priority 1: Skill Loader Enhancement (Monkey-Bot Framework)

**Before building ANY skills**, enhance the skill loader to expose descriptions to LLM routing.

See `docs/phases/phase-2-marketing-campaign.md` Section 1 for details.

**Critical:** Without proper routing, skills won't be invoked correctly by Gemini.

### Priority 2: Build Vertical Slice (Private Repo)

Build these 3 skills in order in **auriga-marketing-bot** (private repo):

1. **generate-post** - Create content for any platform
2. **request-approval** - Get user approval via Google Chat
3. **post-content** - Publish to X (Twitter) first

**Test End-to-End:** User says "Create a post about AI agents for X" → generates → gets approval → posts live.

### Priority 3: Validate Routing (CRITICAL)

Write routing tests to verify Gemini correctly selects skills:

```python
def test_generate_routing():
    response = agent.process_message(
        user_id="test",
        content="Create an Instagram post about AI agents"
    )
    assert "generate-post" in response.skills_invoked

def test_approval_routing():
    response = agent.process_message(
        user_id="test",
        content="Send this for my approval"
    )
    assert "request-approval" in response.skills_invoked
```

**If routing fails:** Adjust SKILL.md descriptions until Gemini routes correctly.

### Priority 4: Extract Framework Components

**After vertical slice works**, extract generic parts to monkey-bot (public repo):
- ApprovalInterface
- GoogleChatApproval implementation

### Priority 5: Add More Skills

Once vertical slice + routing validated:
- Add more platforms (Instagram, TikTok, LinkedIn, Reddit)
- Add research skills (search-web, analyze-competitor, identify-trends)
- Add campaign planning (create-campaign, schedule-campaign)

---

## Testing Strategy

### 1. Routing Tests (Most Important!)

Test that Gemini selects correct skills based on user input:
- Normal operations: "Create a post" → generate-post
- Edge cases: Ambiguous requests → clarification or best guess
- Out of scope: "Delete my account" → should NOT invoke any skill

### 2. Skill Quality Tests

Test that each skill produces good output:
- generate-post: Character limits, brand voice, hashtags
- request-approval: Google Chat card format, timeout handling
- post-content: API success, error handling, post URLs

### 3. End-to-End Integration Tests

Test complete flows:
- Generate → Approve → Post
- Generate → Reject → Modify → Approve → Post
- Campaign planning → Generate posts → Schedule → Auto-post

See `docs/phases/phase-2-marketing-campaign.md` for complete testing details.

---

## Next Steps

### Phase 1B: Detailed Contracts
- ✅ SKILL.md designs complete (above)
- Define error handling patterns
- Define Google Chat approval UI card format
- Specify social media API contracts (platform-specific)
- Define testing strategy details (routing tests!)

### Phase 1C: Production Readiness
- Security: API key storage, rate limiting, error handling
- Performance: Caching strategy, async operations
- Deployment: Cloud Run configuration, monitoring
- Observability: Logging, metrics, alerting
- Risk assessment: API failures, approval timeout, rate limits

---

## Quality Checklist

### Completeness
- ✅ All discovery questions answered
- ✅ Visual diagrams included (architecture + sequence)
- ✅ Architecture decision is clear with alternatives
- ✅ Core entities defined with relationships
- ✅ Two-repo separation clearly explained

### Quality
- ✅ Architecture decision is justified (clean separation, security, reusability)
- ✅ Alternatives documented with trade-offs
- ✅ Diagrams are clear and comprehensive
- ✅ No ambiguous requirements (all questions answered in Q&A log)
- ✅ Security requirement addressed (private repo approach)

### Clarity
- ✅ Developers can understand the two-repo pattern
- ✅ Core entities and their purpose are clear
- ✅ Campaign workflow is step-by-step clear
- ✅ Framework vs. implementation boundaries are obvious

---

## Critical Design Corrections Applied

Based on Cursor Skills Blog best practices:

### Corrections Made

1. ✅ **SKILL.md designs complete** - Not placeholders, actual triggering descriptions
2. ✅ **Skill granularity fixed**:
   - Posting: Merged 5 separate skills into 1 (`post-content` with platform param)
   - Research: Split coarse skill into 3 separate (`search-web`, `analyze-competitor`, `identify-trends`)
3. ✅ **Menu pattern added** - `create-campaign` uses menu pattern with sub-files
4. ✅ **Success criteria in skills** - Each SKILL.md defines what good output looks like
5. ✅ **Vertical slice prioritized** - Build generate → approve → post FIRST
6. ✅ **Testing strategy** - Routing tests to validate Gemini behavior
7. ✅ **Framework scope reduced** - Build vertical slice first, extract abstractions after

### Skill Routing Validation

**CRITICAL RISK:** Must validate that Gemini (via LangGraph) correctly routes to skills based on SKILL.md descriptions.

**Mitigation:** Write routing tests EARLY. If Gemini doesn't route correctly, adjust SKILL.md descriptions until it does.

### Framework Changes Moved

All monkey-bot (public repo) framework enhancements documented in:
**`docs/phases/phase-2-marketing-campaign.md`**

This design (1a-discovery.md) now focuses on PRIVATE repo implementation (auriga-marketing-bot).

---

## Definition of Done

- [x] All discovery questions answered (see Q&A log)
- [x] Visual diagrams created (architecture + sequence)
- [x] Architecture decision made (two-repo extension pattern)
- [x] Core data model defined (Campaign, Post, CronJob, BrandVoice)
- [x] Skill designs complete with triggering descriptions
- [x] Skill granularity corrected per blog best practices
- [x] Vertical slice approach defined
- [x] Testing strategy (routing tests!) defined
- [x] Framework enhancements moved to phase-2 doc
- [ ] User approves direction: **Awaiting user approval**

**Ready for user review!**
