# Phase 2: Marketing Campaign Manager (Full Workflow + MCP)

**Goal:** World-class social media campaign automation with research, planning, content generation, and posting

**Value Delivered:** Complete marketing workflow from topic research to scheduled multi-platform posting. Demonstrates framework's power for domain-specific agents.

**Prerequisites:** Phase 1 must be complete (core agent foundation working)

**Status:** Ready for monkeymode execution after Phase 1

---

## Strategic Context

This phase transforms the general assistant into a specialized marketing agent capable of:
1. **Research**: Web search + competitor analysis using MCP servers
2. **Planning**: Strategy development + content calendar creation
3. **Generation**: Brand voice-aware content creation
4. **Posting**: Multi-platform posting (X/Twitter, LinkedIn, Instagram)
5. **Scheduling**: Cron-based campaign execution

This demonstrates the framework's extensibility and validates the domain-specific agent pattern.

---

## Components to Build

### 1. MCP Integration Layer (CLI-Based)

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
