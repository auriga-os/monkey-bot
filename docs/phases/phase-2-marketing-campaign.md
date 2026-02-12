# Phase 2: Marketing Campaign Manager (Framework Enhancements)

**Goal:** Add framework capabilities to support domain-specific marketing agents

**Value Delivered:** Generic, reusable framework components that enable marketing automation (and other domain-specific agents). Demonstrates framework's extensibility through a vertical slice approach.

**Prerequisites:** Phase 1 must be complete (core agent foundation working)

**Status:** In Design (MonkeyMode Phase 1A Complete)

**Updated:** 2026-02-11 - Revised based on Cursor skills blog best practices

---

## Strategic Context

This phase enhances the monkey-bot framework (PUBLIC repo) with generic capabilities needed for domain-specific agents. Implementation focuses on:

1. **Vertical Slice First**: Build one end-to-end flow (generate → approve → post) before abstracting
2. **Skills as LLM Contracts**: SKILL.md descriptions are triggering mechanisms, not documentation
3. **Validate Routing**: Test that Gemini (via LangGraph) correctly routes using SKILL.md descriptions
4. **Extract Abstractions**: Only after vertical slice works, extract generic framework components

**Note:** Actual marketing skills and private implementation live in separate private repo (auriga-marketing-bot). This document covers only PUBLIC framework enhancements in monkey-bot.

---

## Development Approach: Vertical Slice First

### Why Vertical Slice?

Rather than building 5 framework abstractions upfront, we'll:
1. **Build ONE working flow end-to-end** (in private repo): Generate post → Request approval → Post to X
2. **Validate routing works**: Test that Gemini selects the right skills based on SKILL.md descriptions
3. **Identify patterns**: See what's actually needed vs. speculative abstractions
4. **Extract to framework**: Move generic parts to public monkey-bot repo

### Vertical Slice: Social Post Flow

```
User: "Create a post about AI agents for X"
         │
         ▼
   [Agent Core Routes to generate_post skill]
         │
         ▼
   generate_post.py
   - Loads BRAND_VOICE.md (if exists)
   - Calls Gemini to generate content
   - Validates character limits
   - Returns formatted post
         │
         ▼
   [Agent Core Routes to request_approval skill]
         │
         ▼
   request_approval.py
   - Formats Google Chat card
   - Sends to user
   - Waits for approval (hardcoded timeout: 1 hour)
   - Returns approval status
         │
         ▼ (if approved)
   [Agent Core Routes to post_content skill]
         │
         ▼
   post_content.py
   - Takes platform="x" parameter
   - Calls X API
   - Returns post URL
         │
         ▼
   Success! Post live at https://x.com/...
```

**Success Criteria for Vertical Slice:**
- [ ] User can trigger flow via natural language
- [ ] Gemini routes correctly to each skill based on SKILL.md
- [ ] Approval workflow works end-to-end in Google Chat
- [ ] Post successfully published to X
- [ ] All code in PRIVATE repo initially (auriga-marketing-bot)

### After Vertical Slice Works

**Then and only then:**
1. Identify what's generic (approval interface, platform posting pattern)
2. Extract to public framework with proper abstractions
3. Update private repo to use framework components
4. Add other platforms (Instagram, TikTok, etc.)
5. Add research and campaign planning skills

---

## Framework Enhancements (After Vertical Slice)

These components will be added to monkey-bot PUBLIC repo ONLY after validating they're needed through the vertical slice.

### 1. Skill Loader Enhancement (CRITICAL - Do This First)

**Problem:** Current skill loader reads SKILL.md but doesn't expose descriptions to LLM routing.

**Current State** (`src/skills/loader.py`):
```python
class SkillLoader:
    def load_skills(self) -> Dict[str, dict]:
        """Discover skills by parsing SKILL.md frontmatter."""
        # Returns: {"skill-name": {"metadata": {...}, "entry_point": "..."}}
```

**Enhancement Needed:**
```python
class SkillLoader:
    def load_skills(self) -> Dict[str, dict]:
        """
        Load skills and expose to LLM routing.
        
        Returns skill metadata that LangGraph can use for tool selection:
        {
            "skill-name": {
                "metadata": {...},
                "entry_point": "/path/to/skill.py",
                "description": "Triggering description for LLM",  # NEW
                "requires_env": ["API_KEY"],  # NEW
                "available": True  # NEW - false if missing env vars
            }
        }
        """
    
    def get_skill_descriptions_for_llm(self) -> str:
        """
        Format skill descriptions for LLM system prompt.
        
        Returns markdown list of available skills:
        - generate_post: Create social media content for any platform...
        - request_approval: Send content to Google Chat for user approval...
        - post_content: Publish approved content to social media platforms...
        """
```

**Integration with Agent Core:**

Agent's system prompt should include skill descriptions from loader:
```python
system_prompt = f"""You are a helpful assistant with these skills:

{skill_loader.get_skill_descriptions_for_llm()}

When the user's request matches a skill description, invoke that skill.
"""
```

**Testing Strategy:**
1. Unit test: Verify loader parses SKILL.md correctly
2. Integration test: Verify LangGraph tool selection uses descriptions
3. Routing test: Give Gemini ambiguous requests, verify correct skill chosen

**Priority:** DO THIS FIRST - Without proper routing, nothing else matters.

---

### 2. MCP Integration Layer (CLI-Based)

#### Token Management System

**Key Files:**
- `src/integrations/token_manager.py` - Token storage and rotation
- `data/secrets/tokens.json` - Encrypted token storage (local)

**Features:**
- Store tokens securely (encrypted at rest)
- Easy token updates via skill
- Environment variable injection for MCP servers
- Token expiration tracking and warnings
- Test token validity on save

**Token Storage Format:**
```json
{
  "tokens": {
    "x_api": {
      "value": "encrypted_token_here",
      "created_at": "2026-02-11T10:00:00Z",
      "expires_at": "2026-05-11T10:00:00Z",
      "last_tested": "2026-02-11T10:00:00Z",
      "status": "valid"
    },
    "linkedin_api": {
      "value": "encrypted_token_here",
      "created_at": "2026-02-11T10:00:00Z",
      "expires_at": null,
      "last_tested": "2026-02-11T10:00:00Z",
      "status": "valid"
    }
  }
}
```

**Token Management Skill:**
```bash
# Update token
python skills/tokens/update_token.py --service x_api --token "new_token"

# List tokens
python skills/tokens/list_tokens.py

# Test token
python skills/tokens/test_token.py --service x_api
```

#### MCP Server Wrappers

**Approach:** CLI-based wrappers that invoke external MCP servers via subprocess

**Why CLI-based:**
- Simple to implement and debug
- Easy token management (env vars)
- Can test manually from command line
- No MCP protocol complexity in Phase 2

**MCP Servers to Integrate:**
1. **Perplexity MCP** - Web search with citations
2. **Playwright MCP** - Web scraping and automation
3. **Firecrawl MCP** - Competitor site analysis

**Wrapper Pattern:**
```python
# skills/research/perplexity_search.py
import subprocess
import json
import os

def search_web(query: str, limit: int = 10) -> dict:
    """Search web using Perplexity MCP server"""
    
    # Set environment variables for MCP auth
    env = os.environ.copy()
    env["PERPLEXITY_API_KEY"] = get_token("perplexity_api")
    
    # Call external MCP server
    result = subprocess.run(
        ["mcp", "call", "perplexity", "search", 
         "--query", query, "--limit", str(limit)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode != 0:
        raise Exception(f"MCP call failed: {result.stderr}")
    
    return json.loads(result.stdout)
```

---

### 3. Approval Workflow System (Extract After Vertical Slice)

**When to Extract:** After `request_approval` skill works in private repo.

**Purpose:** Generic approval pattern that works via Google Chat, email, CLI, etc.

**Interface** (`src/core/approval.py`):
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ApprovalRequest:
    item_type: str  # "social_post", "campaign", etc.
    item_data: dict
    approver: str
    timeout_seconds: int = 3600

@dataclass
class ApprovalResult:
    approved: bool
    feedback: str | None = None
    modified_data: dict | None = None

class ApprovalInterface(ABC):
    @abstractmethod
    async def request_approval(
        self, 
        request: ApprovalRequest
    ) -> ApprovalResult:
        """Request approval for an item."""

class GoogleChatApproval(ApprovalInterface):
    """Google Chat approval using interactive cards."""
    
    async def request_approval(
        self, 
        request: ApprovalRequest
    ) -> ApprovalResult:
        # Send card to Google Chat
        # Wait for user interaction
        # Return result
```

**Why Generic:** Any agent might need approval workflows (expense reports, code reviews, etc.)

---

### 4. Cron Scheduler (Extract After Scheduling Works)

**When to Extract:** After manually scheduling a post works in private repo.

**Purpose:** Schedule and execute jobs at specified times.

**Interface** (`src/core/cron.py`):
```python
class CronScheduler:
    """Job scheduler for timed execution."""
    
    def schedule_job(
        self,
        job_id: str,
        schedule: dict,  # {"kind": "at", "at": "ISO8601"} or {"kind": "cron", "expr": "0 9 * * *"}
        skill_name: str,
        skill_params: dict
    ) -> None:
        """Schedule a job to run a skill."""
        
    def cancel_job(self, job_id: str) -> None:
        """Cancel a scheduled job."""
        
    def list_jobs(self, status: str = None) -> List[dict]:
        """List scheduled jobs."""
```

**Storage:** `./data/memory/cron_jobs.json`

**Why Generic:** Any agent might need scheduled tasks (backups, reports, data syncs)

---

## Skill Design Guidelines (Private Repo)

These guidelines apply to skills in auriga-marketing-bot (private repo).

### Skill Granularity Rules

**From Cursor Skills Blog:**
1. **Single-purpose skills**: One clear job per skill
2. **Platform as parameter**: Don't create 5 posting skills, create 1 with platform parameter
3. **Split research capabilities**: Don't bundle web search + competitor analysis

**Correct Granularity:**

❌ **TOO COARSE:**
```
skills/research/  (bundles 3 different capabilities)
├── SKILL.md
└── research.py  (does search AND competitor AND trends)
```

✅ **CORRECT:**
```
skills/search-web/
├── SKILL.md  (name: search-web, description: "Search the web...")
└── search_web.py

skills/analyze-competitor/
├── SKILL.md  (name: analyze-competitor, description: "Analyze competitor...")
└── analyze_competitor.py

skills/identify-trends/
├── SKILL.md  (name: identify-trends, description: "Identify content trends...")
└── identify_trends.py
```

❌ **TOO FINE:**
```
skills/post-to-instagram/
skills/post-to-tiktok/
skills/post-to-x/
skills/post-to-linkedin/
skills/post-to-reddit/
```

✅ **CORRECT:**
```
skills/post-content/
├── SKILL.md  (name: post-content, description: "Publish content to social platforms...")
└── post_content.py  (takes platform parameter)
```

### SKILL.md Format (LLM Triggering Contract)

**Critical:** The `name` and `description` in YAML frontmatter are what the LLM sees for routing.

**Example: generate-post skill**

```markdown
---
name: generate-post
description: Create social media content for any platform (Instagram, TikTok, X, LinkedIn, Reddit). Automatically validates character limits and brand voice. Use when user wants to create, write, draft, or generate a post.
metadata:
  emonk:
    requires:
      env: []  # No API keys needed
---

# Generate Social Media Post

Creates platform-specific social media content optimized for engagement.

## When to Use This Skill

The agent should invoke this skill when the user:
- Wants to create a new social media post
- Asks to "write a post about [topic]"
- Requests "draft Instagram caption for [topic]"
- Says "generate content for X about [topic]"

## Parameters

- `topic` (required): What the post is about
- `platform` (required): Target platform ("instagram", "tiktok", "x", "linkedin", "reddit")
- `tone` (optional): Desired tone ("professional", "casual", "humorous")
- `include_hashtags` (optional): Whether to add hashtags (default: true)

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

## Testing

Normal case: "Create an Instagram post about AI agents"
Edge case: "Create a 5000 character post for X" (should fail validation)
Out of scope: "Schedule this post for tomorrow" (use schedule-post skill instead)
```

### Menu Pattern for Large Skills

**Use when:** Skill has multiple sub-operations or large code files.

**Example: create-campaign skill**

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

Plans a comprehensive social media campaign with research and content calendar.

## Workflow

This skill follows a multi-step process. Each step can be found in separate files:

1. **Research Topic** → See `research_topic.md` for detailed instructions
   - Web search for trending content
   - Competitor analysis
   - Content gap identification

2. **Define Strategy** → See `define_strategy.md`
   - Choose theme and content pillars
   - Set posting cadence per platform
   - Define success metrics

3. **Generate Calendar** → See `generate_calendar.md`
   - Create posting schedule
   - Assign content pillars to dates
   - Balance platforms

4. **Create Post Ideas** → See `create_post_ideas.md`
   - Generate specific post topics
   - Assign to calendar dates

## Usage

If user wants a complete campaign, run all steps in order.
If user wants just research or just strategy, run that step only.

[Rest of skill details...]
```

This keeps the main SKILL.md lean while providing detailed instructions in referenced files.

---

## Testing Strategy

### 1. Routing Tests (CRITICAL)

**Test that Gemini correctly selects skills based on descriptions.**

```python
# tests/test_skill_routing.py

def test_generate_post_routing():
    """Verify LLM routes 'create a post' to generate-post skill."""
    
    user_message = "Create an Instagram post about AI agents"
    
    # Invoke agent
    response = agent.process_message(user_id="test", content=user_message)
    
    # Verify generate-post skill was invoked
    assert "generate-post" in response.skills_invoked
    assert response.success

def test_approval_routing():
    """Verify LLM routes approval requests correctly."""
    
    user_message = "Send this post for approval"
    
    response = agent.process_message(user_id="test", content=user_message)
    
    assert "request-approval" in response.skills_invoked

def test_ambiguous_routing():
    """Verify LLM handles ambiguous requests gracefully."""
    
    # User says "post this" - could mean generate OR publish
    user_message = "post this to Instagram"
    
    response = agent.process_message(user_id="test", content=user_message)
    
    # Should ask for clarification or choose most likely skill
    assert response.success or "clarify" in response.content.lower()
```

### 2. Skill Quality Tests

```python
# tests/test_generate_post.py

def test_generate_post_instagram():
    """Verify Instagram posts meet platform requirements."""
    
    result = generate_post(topic="AI agents", platform="instagram")
    
    assert result["success"]
    assert len(result["post"]["content"]) <= 2200
    assert len(result["post"]["hashtags"]) <= 5
    assert result["post"]["validation"]["within_limit"]

def test_generate_post_x_character_limit():
    """Verify X posts respect 280 character limit."""
    
    result = generate_post(topic="AI agents", platform="x")
    
    assert result["post"]["character_count"] <= 280

def test_brand_voice_validation():
    """Verify posts are validated against brand voice if defined."""
    
    # Create test BRAND_VOICE.md with forbidden phrases
    write_brand_voice(forbidden_phrases=["game-changer", "revolutionary"])
    
    result = generate_post(topic="Our revolutionary AI is a game-changer", platform="x")
    
    # Should fail validation
    assert not result["post"]["validation"]["brand_voice_valid"]
```

### 3. Integration Tests

```python
# tests/test_social_post_flow.py

@pytest.mark.integration
async def test_end_to_end_post_flow():
    """Test complete flow: generate → approve → post."""
    
    # Step 1: Generate post
    generate_response = await agent.process_message(
        user_id="test@example.com",
        content="Create a post about AI agents for X"
    )
    assert "post generated" in generate_response.content.lower()
    
    # Step 2: Request approval (should send Google Chat card)
    approval_response = await agent.process_message(
        user_id="test@example.com",
        content="Send this for approval"
    )
    assert "approval requested" in approval_response.content.lower()
    
    # Step 3: Simulate approval (mock Google Chat interaction)
    mock_approval(user="test@example.com", approved=True)
    
    # Step 4: Post content
    post_response = await agent.process_message(
        user_id="test@example.com",
        content="Post it to X"
    )
    assert "posted successfully" in post_response.content.lower()
    assert "https://x.com/" in post_response.content  # Should return post URL
```

---

## Implementation Phases

### Phase 2A: Skill Loader Enhancement (1-2 days)
- [ ] Enhance SkillLoader to expose descriptions to LLM
- [ ] Update Agent Core to include skill descriptions in system prompt
- [ ] Write routing tests for Gemini
- [ ] Validate Gemini correctly selects skills

### Phase 2B: Vertical Slice (3-5 days)
- [ ] Build generate-post skill (private repo)
- [ ] Build request-approval skill (private repo)
- [ ] Build post-content skill (private repo)
- [ ] Test end-to-end: generate → approve → post to X
- [ ] Validate all routing works correctly

### Phase 2C: Extract Framework Components (2-3 days)
- [ ] Extract ApprovalInterface to public framework
- [ ] Move GoogleChatApproval to framework
- [ ] Update private repo to use framework components
- [ ] Add unit tests for framework components

### Phase 2D: Additional Platforms (3-5 days)
- [ ] Add Instagram support to post-content
- [ ] Add TikTok support
- [ ] Add LinkedIn, Reddit support
- [ ] Platform-specific validation

### Phase 2E: Campaign Planning (5-7 days)
- [ ] Build search-web skill (Perplexity MCP)
- [ ] Build analyze-competitor skill (Firecrawl MCP)
- [ ] Build create-campaign skill (menu pattern)
- [ ] Build schedule-campaign skill
- [ ] Extract CronScheduler to framework

---

## Success Criteria

Phase 2 is complete when:
- [ ] Skill routing works reliably with Gemini
- [ ] Vertical slice (generate → approve → post) works end-to-end
- [ ] At least 2 platforms supported (X + Instagram minimum)
- [ ] ApprovalInterface extracted to framework
- [ ] All routing tests passing
- [ ] All skill quality tests passing
- [ ] End-to-end integration test passing
- [ ] Documentation updated with skill design guidelines

---

## References

- [Cursor Skills Blog Post](https://www.cursor.com/blog/skills) - Skill design best practices
- [Phase 1 Complete](./phase-1-core-foundation.md) - Current framework state
- [Skills System Reference](../ref/05_skills_system.md) - Current skill loader
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) - Agent orchestration

---

## Next Phase

After Phase 2 is complete and working:
- **Phase 3:** Production deployment, monitoring, and framework packaging
- Focus: Cloud Run deployment, observability, error handling, framework versioning

---

## IMPORTANT: Skills Live in Private Repo

**Reminder:** All marketing skills (generate-post, post-content, etc.) are built in **auriga-marketing-bot** (private repo), NOT in monkey-bot. Only generic framework components (ApprovalInterface, CronScheduler, enhanced SkillLoader) go in monkey-bot (public repo).

This document describes framework changes needed in PUBLIC repo to support private marketing skills.

---

## OLD CONTENT BELOW (For Reference - Will Be Removed)

### 2. Campaign Workflow Skills

#### A. Research Skills (`skills/research/`)

**1. Web Search Skill**
- **File:** `search_web.py`
- **Function:** `search_web(topic, limit=10)`
- **MCP Server:** Perplexity
- **Returns:** titles, URLs, snippets, citations
- **Use Case:** Find trending content on topic

**2. Competitor Analysis Skill**
- **File:** `analyze_competitor.py`
- **Function:** `analyze_competitor(url)`
- **MCP Server:** Firecrawl
- **Returns:** pricing, features, content themes
- **Use Case:** Scrape competitor sites for insights

**3. Trend Identification Skill**
- **File:** `identify_trends.py`
- **Function:** `identify_trends(topic)`
- **Returns:** trending angles, content gaps, opportunities
- **Use Case:** Aggregate research and identify opportunities

**SKILL.md Example (search_web):**
```markdown
---
name: search-web
description: "Search web using Perplexity with citations"
metadata:
  emonk:
    requires:
      env: ["PERPLEXITY_API_KEY"]
      bins: ["mcp"]
---

# Web Search Skill

Search for current information with citations.

## Usage

```bash
python skills/research/search_web.py "AI agent evaluation" --limit 10
```

## Output Format

```json
{
  "results": [
    {
      "title": "Building Trust in AI Agents",
      "url": "https://example.com/article",
      "snippet": "...",
      "source": "TechCrunch",
      "date": "2026-02-10"
    }
  ],
  "citations": ["https://example.com/article"]
}
```
```

#### B. Campaign Planning Skills (`skills/campaign/`)

**1. Create Campaign Skill**
- **File:** `create_campaign.py`
- **Function:** `create_campaign(topic, duration_weeks, platforms)`
- **Workflow:**
  1. Research topic (web search + competitors)
  2. Develop content strategy (theme, pillars, cadence)
  3. Create content calendar (dates, times, platforms)
  4. Generate post ideas (topics, hooks, CTAs)
- **Output:** Complete campaign plan (JSON)
- **Storage:** `./data/memory/campaigns/{campaign_id}/plan.json`

**Campaign Plan Structure:**
```json
{
  "id": "ai-eval-campaign-001",
  "topic": "AI agent evaluation frameworks",
  "duration_weeks": 4,
  "created_at": "2026-02-11T10:00:00Z",
  "research": {
    "trending_articles": [...],
    "competitor_insights": [...],
    "content_gaps": [...]
  },
  "strategy": {
    "theme": "Building trust in AI agents",
    "content_pillars": [
      "Testing patterns",
      "Persona-based evaluation",
      "LLM-as-judge",
      "CI/CD integration"
    ],
    "posting_cadence": {
      "x": "daily",
      "linkedin": "3x/week",
      "instagram": "2x/week"
    }
  },
  "calendar": [
    {
      "date": "2026-02-12",
      "time": "09:00",
      "platform": "x",
      "content_pillar": "Testing patterns",
      "post_id": "post_001"
    }
  ],
  "post_ideas": [...]
}
```

**2. Generate Campaign Posts Skill**
- **File:** `generate_campaign_posts.py`
- **Function:** `generate_campaign_posts(campaign_id)`
- **Input:** Campaign plan
- **Process:**
  - Load campaign plan
  - Load BRAND_VOICE.md
  - Generate content for each post
  - Validate against brand voice
- **Output:** Posts ready for approval
- **Storage:** `./data/memory/campaigns/{campaign_id}/posts.json`

#### C. Content Generation Skills (`skills/content/`)

**1. Generate Content Skill**
- **File:** `generate_content.py`
- **Function:** `generate_content(topic, platform, hook=None, cta=None)`
- **Always loads:** `./data/memory/BRAND_VOICE.md`
- **Platforms:** X/Twitter (280 chars), LinkedIn (1300 chars), Instagram
- **Validation:** Brand voice validation (forbidden phrases filter)
- **Output:** Validated post content

**Platform-Specific Constraints:**
- **X/Twitter:** 280 characters max, 1-2 hashtags, 1 emoji max
- **LinkedIn:** 1300 characters, 3-5 hashtags, professional tone
- **Instagram:** 2200 characters, 2-3 emojis, visual-first

**2. Adapt Content Skill**
- **File:** `adapt_content.py`
- **Function:** `adapt_content(content, from_platform, to_platforms)`
- **Input:** Single post content
- **Output:** Adapted versions for all target platforms

#### D. Posting Skills (`skills/posting/`)

**1. Post to X/Twitter**
- **File:** `post_to_x.py`
- **Function:** `post_to_x(content)`
- **API:** X API v2 (bearer token auth)
- **Validation:** Character limit, token validity
- **Returns:** tweet URL and ID

**Example:**
```python
import requests
import os

def post_to_x(content: str) -> dict:
    """Post to X/Twitter"""
    
    if len(content) > 280:
        raise ValueError("Content exceeds 280 characters")
    
    token = get_token("x_api")
    
    response = requests.post(
        "https://api.x.com/2/tweets",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"text": content}
    )
    
    if response.status_code != 201:
        raise Exception(f"X API error: {response.text}")
    
    data = response.json()
    tweet_id = data["data"]["id"]
    
    return {
        "success": True,
        "tweet_id": tweet_id,
        "url": f"https://x.com/user/status/{tweet_id}"
    }
```

**2. Post to LinkedIn**
- **File:** `post_to_linkedin.py`
- **Function:** `post_to_linkedin(content)`
- **API:** LinkedIn API (OAuth)
- **Features:** Rich text formatting support
- **Returns:** post URL

**3. Post to Instagram**
- **File:** `post_to_instagram.py`
- **Function:** `post_to_instagram(content, image_path=None)`
- **API:** Instagram Basic Display API or Mixpost
- **Features:** Image handling, caption generation
- **Returns:** post URL

#### E. Campaign Management Skills (`skills/campaign/`)

**1. Schedule Campaign Skill**
- **File:** `schedule_campaign.py`
- **Function:** `schedule_campaign(campaign_id)`
- **Process:**
  - Load campaign posts
  - Create cron job for each post
  - Store in cron registry
- **Storage:** `./data/memory/cron_jobs.json`

**2. Send Approval Email Skill**
- **File:** `send_approval_email.py`
- **Function:** `send_approval_email(campaign_id, recipients)`
- **Process:**
  - Generate HTML preview of all posts
  - Include approve/reject links
  - Send via SMTP (Gmail)
- **Returns:** email sent confirmation

**Email Template:**
```html
<h1>Campaign Approval Request: {topic}</h1>
<p>Duration: {duration} weeks | Total Posts: {count}</p>

<h2>Campaign Strategy</h2>
<p>{theme}</p>

<h2>Sample Posts (First 5)</h2>
<!-- Post previews -->

<h2>Approve or Reject</h2>
<a href="mailto:agent@company.com?subject=APPROVE-{campaign_id}">
  Approve Campaign
</a>
<a href="mailto:agent@company.com?subject=REJECT-{campaign_id}">
  Request Revisions
</a>
```

---

### 3. Brand Voice System

#### BRAND_VOICE.md Template

**Location:** `./data/memory/BRAND_VOICE.md`

**Structure:**
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

#### Brand Voice Validator

**File:** `src/core/brand_voice_validator.py`

**Functions:**
- `validate(content, platform)` - Check against brand voice rules
- `check_forbidden_phrases(content)` - Detect forbidden phrases
- `check_length(content, platform)` - Verify length constraints
- `analyze_tone(content)` - Assess formality and sentiment

**Validation Rules:**
```python
class BrandVoiceValidator:
    FORBIDDEN_PHRASES = [
        "game-changer", "revolutionary", "disrupting",
        "unlock", "secrets", "hack", "leverage synergies"
    ]
    
    PLATFORM_LIMITS = {
        "x": 280,
        "linkedin": 1300,
        "instagram": 2200
    }
    
    def validate(self, content: str, platform: str) -> dict:
        """Validate content against brand voice"""
        
        issues = []
        
        # Check forbidden phrases
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase.lower() in content.lower():
                issues.append(f"Contains forbidden phrase: '{phrase}'")
        
        # Check length
        max_length = self.PLATFORM_LIMITS.get(platform)
        if max_length and len(content) > max_length:
            issues.append(f"Exceeds {platform} limit: {len(content)} > {max_length}")
        
        # Check tone (placeholder - use LLM in real implementation)
        if content.isupper():
            issues.append("All caps detected - too aggressive")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
```

---

### 4. Grounded Web Search (Vertex AI)

**Feature:** Enable grounded search in LLM calls for real-time information

**Implementation:** `src/core/llm_client.py`

**Configuration:**
```python
# Add to LLM client
def generate_with_search(self, prompt: str, grounding_enabled: bool = True):
    """Generate with optional web search grounding"""
    
    if grounding_enabled:
        # Use Vertex AI Search
        tools = [
            {
                "google_search_retrieval": {
                    "disable_attribution": False
                }
            }
        ]
    else:
        tools = None
    
    response = self.model.generate_content(
        prompt,
        tools=tools
    )
    
    # Extract citations if present
    citations = self._extract_citations(response)
    
    return {
        "content": response.text,
        "citations": citations
    }
```

**When to Use:**
- Research skills (always enable)
- Content generation (enable for trend-based content)
- General queries (enable by default, disable for creative tasks)

---

## Campaign Workflow Example

```
User: "Create a 4-week campaign about AI agent evaluation frameworks"

Agent:
1. 🔍 Researching "AI agent evaluation frameworks"...
   - Searching web (Perplexity)... Found 12 trending articles
   - Analyzing competitors (Firecrawl)... Scraped 3 sites (LangSmith, Braintrust, Langfuse)
   - Identifying trends... Found 5 content gaps

2. 📋 Creating campaign strategy...
   - Theme: "Building trust in AI agents through systematic evaluation"
   - Content pillars: Testing patterns, Persona-based evaluation, LLM-as-judge, CI/CD integration
   - Posting cadence: X daily, LinkedIn 3x/week, Instagram 2x/week
   - Total posts: 28 posts across 4 weeks

3. ✍️ Generating content calendar...
   - Week 1: 7 posts (testing patterns focus)
   - Week 2: 7 posts (persona techniques)
   - Week 3: 7 posts (LLM-as-judge deep dive)
   - Week 4: 7 posts (CI/CD integration)

4. 📝 Generating all 28 posts...
   - Loading BRAND_VOICE.md...
   - Generating X/Twitter posts (20)... ✓
   - Generating LinkedIn posts (6)... ✓
   - Generating Instagram posts (2)... ✓
   - Validating against brand voice... ✓ All passed

5. ✅ Campaign ready!
   Saved to: ./data/memory/campaigns/ai-eval-campaign-001/
   
   Would you like to:
   - Review posts before scheduling
   - Email campaign preview for approval
   - Schedule immediately
```

---

## Token Management Example

```
User: "Update my X API token"
Agent: "Please provide your new X API bearer token (it will be encrypted)"

User: "xoxb-1234567890-abcdef..."
Agent: 
  "Testing token... ✓ Valid
   Encrypting token... ✓
   Saving to secure storage... ✓
   
   ✅ Updated X API token
   - Expires: 2026-05-12 (90 days)
   - Last tested: Just now
   - Status: Valid"

User: "List my tokens"
Agent: "Active tokens:
┌───────────────────┬──────────┬──────────────┬──────────────┐
│ Service           │ Status   │ Expires      │ Last Tested  │
├───────────────────┼──────────┼──────────────┼──────────────┤
│ X/Twitter API     │ ✅ Valid │ 2026-05-12   │ 2026-02-11   │
│ LinkedIn API      │ ✅ Valid │ 2026-08-01   │ 2026-02-10   │
│ Perplexity API    │ ⚠️ Soon  │ 2026-02-20   │ 2026-02-11   │
│ Instagram (Mixpost)│ ✅ Valid │ No expiration│ 2026-02-09   │
└───────────────────┴──────────┴──────────────┴──────────────┘"
```

---

## Success Criteria

- [ ] Complete campaign created from single topic input
- [ ] Research pulls from real-time web sources (Perplexity MCP)
- [ ] Content validates against brand voice automatically
- [ ] Posts successfully to X/Twitter and LinkedIn
- [ ] Tokens easy to update without code changes
- [ ] Campaign approval workflow functional (email preview)
- [ ] Brand voice validator catches forbidden phrases
- [ ] All campaign data persists in GCS
- [ ] MCP wrappers handle errors gracefully
- [ ] Unit tests for all new skills

---

## Testing Strategy

### Unit Tests
- `test_token_manager.py` - Token encryption, storage, validation
- `test_brand_voice.py` - Validator logic
- `test_campaign_skills.py` - Campaign creation, post generation

### Integration Tests
- End-to-end campaign creation
- MCP server integration (mock responses)
- Post validation and scheduling

### Manual Testing
1. Create campaign via chat
2. Verify research results
3. Review generated posts
4. Update token and test posting
5. Schedule campaign and verify cron jobs

---

## MCP Server Setup

### Install MCP Servers

```bash
# Install MCP CLI (if not already installed)
npm install -g @modelcontextprotocol/cli

# Install Perplexity MCP server
mcp install perplexity

# Install Playwright MCP server
mcp install playwright

# Install Firecrawl MCP server
mcp install firecrawl
```

### Configure MCP Servers

**~/.mcp/config.json:**
```json
{
  "servers": {
    "perplexity": {
      "command": "mcp-server-perplexity",
      "env": {
        "PERPLEXITY_API_KEY": "your-key-here"
      }
    },
    "playwright": {
      "command": "mcp-server-playwright"
    },
    "firecrawl": {
      "command": "mcp-server-firecrawl",
      "env": {
        "FIRECRAWL_API_KEY": "your-key-here"
      }
    }
  }
}
```

---

## Environment Variables (Add to .env)

```bash
# MCP Configuration
MCP_ENABLED=true

# API Tokens (for MCP servers)
PERPLEXITY_API_KEY=your-perplexity-key
FIRECRAWL_API_KEY=your-firecrawl-key

# Social Media API Tokens (stored in token manager)
# These are managed via the token management skill

# SMTP Configuration (for approval emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=agent@yourcompany.com
DEFAULT_APPROVAL_EMAIL=approver@yourcompany.com
```

---

## Dependencies (Add to requirements.txt)

```txt
# MCP Integration
mcp==0.15.0

# Social Media APIs
tweepy==4.14.0  # X/Twitter
linkedin-api==2.2.0  # LinkedIn

# Web & Email
requests==2.31.0
beautifulsoup4==4.12.0
python-smtp==0.1.0

# Encryption (for token storage)
cryptography==41.0.7

# Existing dependencies from Phase 1...
```

---

## References

- [OpenClaw Implementation Guide](../preplanning/OpenClaw_Implementation_Guide.md) - Campaign skills section
- [Integrate Skills MCP](../preplanning/integrate-skills-mcp.md) - MCP wrapper pattern
- [MCP Research](../preplanning/mcp-research.md) - Perplexity, Firecrawl efficiency
- [Skills System](../ref/05_skills_system.md) - Skill structure and patterns

---

## Next Phase

After Phase 2 is complete and working:
- **Phase 3:** Refactor into reusable framework library and deploy to Cloud Run
- Focus: Production deployment, framework extraction, Cloud Scheduler integration
