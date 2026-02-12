# User Stories: Marketing Campaign Manager

**Date:** 2026-02-11  
**Status:** Phase 2 - User Stories  
**Team Size:** 1 developer (solo)  
**Timeline:** Flexible (no hard deadline)

---

## Executive Summary

This document breaks down the Marketing Campaign Manager into implementable user stories optimized for **solo developer sequential implementation**. The approach follows the **vertical slice pattern**: build end-to-end functionality first (generate → approve → post), then expand to more platforms and features.

**Implementation Strategy:**
1. **Sprint 1:** Core vertical slice (generate-post, request-approval, post-content for X/Twitter)
2. **Sprint 2:** Expand to all platforms + research skills
3. **Sprint 3:** Campaign planning and scheduling

---

## Table of Contents

1. [Sprint 1: Vertical Slice](#sprint-1-vertical-slice-mvp)
2. [Sprint 2: Platform Expansion](#sprint-2-platform-expansion)
3. [Sprint 3: Campaign Features](#sprint-3-campaign-features)
4. [Sprint 4: Polish & Production](#sprint-4-polish--production)

---

## Sprint 1: Vertical Slice (MVP)

**Goal:** End-to-end post workflow working for X (Twitter)

**Stories in this sprint:**
1. Enhance Skill Loader (monkey-bot framework)
2. Create generate-post skill
3. Create request-approval skill
4. Create post-content skill (X only)
5. Validate routing and integration

**Expected Duration:** 5-7 days

---

### Story 1.1: Enhanced Skill Loader (Framework)

**Repository:** monkey-bot (public)  
**Type:** Enhancement  
**Priority:** Critical (blocks all other stories)  
**Size:** M (1-2 days)  
**Dependencies:** NONE

#### Description
As a **skill developer**,  
I want the skill loader to expose SKILL.md descriptions to Gemini,  
So that the LLM can correctly route user messages to the appropriate skill.

#### Technical Context
- **Affected modules:** `monkey-bot/core/skills/loader.py` (existing)
- **Design reference:** Phase 1A "Framework Enhancements Needed"
- **Key changes:**
  - Modify `SkillLoader` to parse SKILL.md frontmatter
  - Extract `name` and `description` fields
  - Expose as function definitions to LangGraph
  - Pass to Gemini for routing decisions

#### Implementation Details

**Current State:**
```python
# monkey-bot/core/skills/loader.py
class SkillLoader:
    def load_skills(self, skills_dir: Path) -> List[Skill]:
        """Load Python skill functions only"""
        # Currently only imports .py files
        # Doesn't read SKILL.md descriptions
```

**Target State:**
```python
# monkey-bot/core/skills/loader.py
class SkillLoader:
    def load_skills(self, skills_dir: Path) -> List[Skill]:
        """Load skills with SKILL.md metadata"""
        for skill_dir in skills_dir.iterdir():
            skill_md = skill_dir / "SKILL.md"
            skill_py = skill_dir / f"{skill_dir.name}.py"
            
            # Parse SKILL.md frontmatter
            metadata = parse_frontmatter(skill_md)
            
            # Load Python function
            skill_func = import_skill_function(skill_py)
            
            # Create skill with routing info
            skill = Skill(
                name=metadata["name"],
                description=metadata["description"],  # Used by Gemini for routing
                function=skill_func,
                metadata=metadata.get("metadata", {})
            )
            yield skill
```

**Function to Implement:**
```python
def parse_frontmatter(skill_md: Path) -> dict:
    """Parse YAML frontmatter from SKILL.md
    
    Example SKILL.md:
    ---
    name: generate-post
    description: Create social media content for any platform...
    metadata:
      emonk:
        requires:
          env: []
    ---
    
    Returns:
        {"name": "generate-post", "description": "...", "metadata": {...}}
    """
    import yaml
    content = skill_md.read_text()
    # Extract YAML between --- markers
    # Parse and return dict
```

#### Acceptance Criteria
- [ ] **Given** a skill directory with SKILL.md, **When** SkillLoader loads it, **Then** `skill.name` and `skill.description` are populated from frontmatter
- [ ] **Given** SKILL.md with missing `name` field, **When** loader runs, **Then** it raises clear error message
- [ ] **Given** a skill with valid SKILL.md, **When** exposed to LangGraph, **Then** Gemini receives the description for routing
- [ ] Unit tests cover: valid SKILL.md, missing fields, invalid YAML, missing file
- [ ] Integration test: Load sample skill and verify Gemini can route to it

#### Files to Create/Modify
- `monkey-bot/core/skills/loader.py` (modify existing)
- `monkey-bot/core/skills/schema.py` (add `Skill` dataclass if missing)
- `monkey-bot/tests/test_skill_loader.py` (create new)
- `monkey-bot/docs/skills.md` (update documentation)

#### Out of Scope
- MCP integration (later)
- Approval system abstraction (later)
- Cron scheduler (later)

#### Notes for Developer
- Use `pyyaml` library for frontmatter parsing
- Follow existing monkey-bot code style
- This is a PUBLIC repo change - keep it generic
- Test with multiple skills to ensure routing works

---

### Story 1.2: Generate Post Skill (MVP)

**Repository:** auriga-marketing-bot (private)  
**Type:** Feature  
**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** Story 1.1 (skill loader must work)

#### Description
As a **marketing team member**,  
I want to generate social media posts for any platform,  
So that I can create engaging content quickly without manual writing.

#### Technical Context
- **Affected modules:** `skills/generate-post/` (new)
- **Design reference:** Phase 1A "Skill 1: generate-post"
- **Key files to create:**
  - `skills/generate-post/SKILL.md`
  - `skills/generate-post/generate_post.py`
  - `tests/skills/test_generate_post.py`

#### Integration Contracts

**Interface Defined by This Story:**
```python
# skills/generate-post/generate_post.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class GeneratePostParams:
    topic: str
    platform: Literal["instagram", "tiktok", "x", "linkedin", "reddit"]
    tone: str = "professional"
    include_hashtags: bool = True

async def generate_post(
    agent_state: AgentState,
    **params: GeneratePostParams
) -> SkillResponse:
    """Generate social media post optimized for platform.
    
    Returns:
        SkillResponse with post content, validation, next_action="request-approval"
    """
    # 1. Load brand voice (if exists)
    # 2. Generate content via Gemini
    # 3. Validate character limits
    # 4. Return standardized response
```

**Dependencies:**
- Uses `BRAND_VOICE.md` if exists (create sample file)
- Uses Gemini API (already in monkey-bot)
- No external dependencies

#### Acceptance Criteria
- [ ] **Given** topic="AI agents" and platform="x", **When** generate_post() called, **Then** returns content <= 280 chars
- [ ] **Given** platform="instagram", **When** generate_post() called, **Then** returns 3-5 hashtags
- [ ] **Given** BRAND_VOICE.md exists, **When** generating post, **Then** validates against brand guidelines
- [ ] **Given** invalid platform="facebook", **When** generate_post() called, **Then** returns error with valid platforms
- [ ] **Given** generated content, **When** returned, **Then** includes validation: within_limit, has_hook, has_cta
- [ ] Integration test: User says "Create a post about AI for X" → skill invoked correctly
- [ ] Routing test: Gemini routes "write a post" → generate-post skill

#### Implementation Details

**SKILL.md Frontmatter:**
```yaml
---
name: generate-post
description: Create social media content for any platform (Instagram, TikTok, X, LinkedIn, Reddit). Automatically validates character limits and brand voice. Use when user wants to create, write, draft, or generate a post.
metadata:
  emonk:
    requires:
      env: []
---
```

**Platform Limits to Enforce:**
```python
PLATFORM_LIMITS = {
    "instagram": {"chars": 2200, "hashtags": 30},
    "tiktok": {"chars": 2200, "hashtags": 30},
    "x": {"chars": 280, "hashtags": 2},
    "linkedin": {"chars": 3000, "hashtags": 5},
    "reddit": {"chars": 40000, "hashtags": 0}
}
```

**Brand Voice Loading (Optional):**
```python
def load_brand_voice() -> str | None:
    """Load BRAND_VOICE.md if exists"""
    brand_voice_path = Path("./data/memory/BRAND_VOICE.md")
    if brand_voice_path.exists():
        return brand_voice_path.read_text()
    return None
```

#### Out of Scope
- Image generation (use existing tools)
- Multi-language support (English only for MVP)
- A/B testing variants

#### Notes for Developer
- Start with X (Twitter) as simplest platform (280 char limit)
- Test routing heavily - this is CRITICAL for skill invocation
- Create sample BRAND_VOICE.md for testing
- Use async/await for Gemini API calls

---

### Story 1.3: Request Approval Skill (MVP)

**Repository:** auriga-marketing-bot (private)  
**Type:** Feature  
**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** Story 1.2 (needs post content to approve)

#### Description
As a **marketing team member**,  
I want to review and approve content before it goes live,  
So that I maintain quality control over our social media presence.

#### Technical Context
- **Affected modules:** `skills/request-approval/` (new)
- **Design reference:** Phase 1B "Skill 2: request-approval"
- **Key files to create:**
  - `skills/request-approval/SKILL.md`
  - `skills/request-approval/request_approval.py`
  - `tests/skills/test_request_approval.py`

#### Integration Contracts

**Interface Defined by This Story:**
```python
# skills/request-approval/request_approval.py
@dataclass
class RequestApprovalParams:
    content: str
    content_type: Literal["social_post", "campaign", "image"]
    platform: str | None = None
    timeout_seconds: int = 3600  # 1 hour default

async def request_approval(
    agent_state: AgentState,
    **params: RequestApprovalParams
) -> SkillResponse:
    """Send content to Google Chat for approval.
    
    Returns:
        SkillResponse with approval status and optional modified content
    """
    # 1. Format content as Google Chat card
    # 2. Add Approve/Reject/Modify buttons
    # 3. Send to user
    # 4. Wait for response (async)
    # 5. Return approval result
```

#### Acceptance Criteria
- [ ] **Given** post content, **When** request_approval() called, **Then** sends Google Chat card with preview
- [ ] **Given** approval card sent, **When** user clicks "Approve", **Then** returns success with approved=True
- [ ] **Given** approval card sent, **When** user clicks "Reject", **Then** returns error with feedback
- [ ] **Given** approval card sent, **When** user clicks "Modify" and changes content, **Then** returns modified_content
- [ ] **Given** no response within timeout, **When** timeout expires, **Then** returns APPROVAL_TIMEOUT error
- [ ] **Given** approval card, **When** displayed, **Then** shows character count, validation status, platform
- [ ] Integration test: Generate post → Request approval → Approve → Returns success

#### Implementation Details

**Google Chat Card Format:**
```python
def create_approval_card(content: str, platform: str, validation: dict) -> dict:
    """Create Google Chat interactive card for approval"""
    return {
        "cardsV2": [{
            "cardId": f"approval-{uuid4()}",
            "card": {
                "header": {
                    "title": f"Approval Request: {platform.title()} Post",
                    "subtitle": f"Character count: {len(content)}"
                },
                "sections": [{
                    "widgets": [{
                        "textParagraph": {"text": content}
                    }]
                }],
                "cardActions": [
                    {"actionLabel": "✅ Approve", "onClick": {...}},
                    {"actionLabel": "❌ Reject", "onClick": {...}},
                    {"actionLabel": "✏️ Modify", "onClick": {...}}
                ]
            }
        }]
    }
```

**Async Approval Wait Pattern:**
```python
async def wait_for_approval(approval_id: str, timeout_seconds: int) -> dict:
    """Wait for user to approve/reject"""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        # Check if approval record updated
        approval = load_approval_record(approval_id)
        if approval["status"] != "pending":
            return approval
        await asyncio.sleep(1)  # Poll every second
    
    raise TimeoutError("Approval timeout")
```

#### Out of Scope
- Multiple approvers (single approver for MVP)
- Approval history/audit log (add later)
- Email notifications (Google Chat only)

#### Notes for Developer
- Test timeout logic thoroughly (use 5s timeout in tests, not 1 hour)
- Mock Google Chat API responses in tests
- Store approval state in `./data/memory/approvals/{id}.json`
- Ensure button callbacks work correctly

---

### Story 1.4: Post Content Skill (X Only - MVP)

**Repository:** auriga-marketing-bot (private)  
**Type:** Feature  
**Priority:** High  
**Size:** S (1 day)  
**Dependencies:** Story 1.3 (needs approval first)

#### Description
As a **marketing team member**,  
I want to publish approved content to X (Twitter),  
So that our posts go live automatically after approval.

#### Technical Context
- **Affected modules:** `skills/post-content/` (new)
- **Design reference:** Phase 1B "Skill 3: post-content"
- **Key files to create:**
  - `skills/post-content/SKILL.md`
  - `skills/post-content/post_content.py`
  - `skills/post-content/platforms/x.py` (X/Twitter implementation)
  - `tests/skills/test_post_content.py`

#### Integration Contracts

**Interface Defined by This Story:**
```python
# skills/post-content/post_content.py
@dataclass
class PostContentParams:
    content: str
    platform: Literal["x"]  # Only X for MVP
    media_urls: List[str] = []
    approval_id: str | None = None

async def post_content(
    agent_state: AgentState,
    **params: PostContentParams
) -> SkillResponse:
    """Publish content to social media platform.
    
    Pre-conditions:
        - Content must be approved (approval_id must exist)
        - X_API_KEY must be in environment
    
    Returns:
        SkillResponse with platform_post_id and platform_post_url
    """
    # 1. Validate approval exists
    # 2. Get platform credentials from env
    # 3. Call platform API (X only for MVP)
    # 4. Return post URL
```

**Platform Implementation:**
```python
# skills/post-content/platforms/x.py
import tweepy

async def post_to_x(content: str, media_urls: List[str] = None) -> dict:
    """Post to X (Twitter) using Tweepy library.
    
    Returns:
        {"post_id": "1234567890", "post_url": "https://x.com/..."}
    """
    api_key = os.getenv("X_API_KEY")
    client = tweepy.Client(bearer_token=api_key)
    response = client.create_tweet(text=content)
    return {
        "post_id": response.data["id"],
        "post_url": f"https://x.com/auriga_os/status/{response.data['id']}"
    }
```

#### Acceptance Criteria
- [ ] **Given** approved content and platform="x", **When** post_content() called, **Then** posts to X successfully
- [ ] **Given** successful post, **When** returned, **Then** includes platform_post_id and platform_post_url
- [ ] **Given** unapproved content, **When** post_content() called, **Then** returns NOT_APPROVED error
- [ ] **Given** missing X_API_KEY, **When** post_content() called, **Then** returns CONFIGURATION_ERROR
- [ ] **Given** X API rate limited, **When** post_content() called, **Then** returns API_RATE_LIMITED with retry_after
- [ ] **Given** X API fails, **When** post_content() called, **Then** retries 3 times with exponential backoff
- [ ] Integration test: Generate → Approve → Post → Verify live on X

#### Implementation Details

**API Key Setup:**
```bash
# Store in GCP Secret Manager (production)
gcloud secrets create x-api-credentials \
  --replication-policy="automatic"

# Load in code
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
secret_name = "projects/PROJECT_ID/secrets/x-api-credentials/versions/latest"
response = client.access_secret_version(request={"name": secret_name})
x_api_key = response.payload.data.decode("UTF-8")
```

**Retry Logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def post_with_retry(platform: str, content: str):
    """Retry posting 3 times: 1s, 2s, 4s delays"""
    return await post_to_platform(platform, content)
```

#### Out of Scope
- Other platforms (Instagram, TikTok, etc.) - Sprint 2
- Scheduled posting (post now only) - Sprint 3
- Media upload (text only) - Sprint 2

#### Notes for Developer
- Test with X Developer API sandbox first
- Use `tweepy` library (official Python SDK)
- Mock X API in tests (don't post to real account)
- Store post records in `./data/memory/posts/{id}.json`

---

### Story 1.5: End-to-End Validation

**Repository:** auriga-marketing-bot (private)  
**Type:** Testing  
**Priority:** Critical  
**Size:** S (0.5 days)  
**Dependencies:** Stories 1.1-1.4 (all skills complete)

#### Description
As a **developer**,  
I want to validate the complete workflow works end-to-end,  
So that I'm confident the vertical slice is production-ready.

#### Technical Context
- **Affected modules:** `tests/integration/` (new)
- **Design reference:** Phase 1B "Testing Strategy"
- **Key tests to write:**
  - Routing validation (CRITICAL!)
  - End-to-end workflow
  - Error handling

#### Acceptance Criteria
- [ ] **Routing Test:** User says "Create an X post about AI" → generate-post skill invoked
- [ ] **Routing Test:** User says "Send for approval" → request-approval skill invoked
- [ ] **Routing Test:** User says "Post to X" → post-content skill invoked
- [ ] **E2E Test:** Generate → Approve → Post → Live on X (all steps work)
- [ ] **E2E Test:** Generate → Reject → Regenerate → Approve → Post
- [ ] **Error Test:** Post without approval → Returns NOT_APPROVED error
- [ ] **Error Test:** Invalid platform → Returns INVALID_PLATFORM error
- [ ] All tests pass in CI/CD (if set up) or locally

#### Implementation Details

**Routing Tests:**
```python
# tests/integration/test_routing.py
import pytest

def test_generate_post_routing(agent):
    """Test: 'Create a post' routes to generate-post skill"""
    response = agent.process_message(
        user_id="test@ez-ai.io",
        content="Create an Instagram post about AI agents"
    )
    assert "generate-post" in response.skills_invoked
    assert response.skills_invoked["generate-post"]["params"]["platform"] == "instagram"

def test_approval_routing(agent):
    """Test: 'Send for approval' routes to request-approval"""
    response = agent.process_message(
        user_id="test@ez-ai.io",
        content="Send this for my approval"
    )
    assert "request-approval" in response.skills_invoked

def test_posting_routing(agent):
    """Test: 'Post to X' routes to post-content"""
    response = agent.process_message(
        user_id="test@ez-ai.io",
        content="Post this to X"
    )
    assert "post-content" in response.skills_invoked
```

**End-to-End Tests:**
```python
# tests/integration/test_e2e_workflow.py
@pytest.mark.e2e
async def test_complete_post_workflow(agent, mock_x_api):
    """Test: Generate → Approve → Post workflow"""
    
    # Step 1: Generate post
    gen_response = await agent.process_message(
        user_id="test@ez-ai.io",
        content="Create a post about AI agents for X"
    )
    assert gen_response.success
    post_content = gen_response.data["post"]["content"]
    
    # Step 2: Request approval
    approval_response = await agent.process_message(
        user_id="test@ez-ai.io",
        content="Send for approval"
    )
    approval_id = approval_response.data["approval"]["id"]
    
    # Mock user approval
    approve_content(approval_id)
    
    # Step 3: Post to X
    post_response = await agent.process_message(
        user_id="test@ez-ai.io",
        content="Post to X"
    )
    assert post_response.success
    assert post_response.data["post"]["platform_post_url"]
```

#### Out of Scope
- Load testing (volume too low)
- Performance benchmarks (not critical yet)
- Security testing (basic validation sufficient)

#### Notes for Developer
- Run tests locally before deploying
- If routing tests fail, adjust SKILL.md descriptions
- Use `pytest -m e2e` to run only E2E tests
- Mock all external APIs (X, Google Chat) in tests

---

## Sprint 2: Platform Expansion

**Goal:** Support all 5 platforms + research skills

**Stories in this sprint:**
1. Add Instagram support to post-content
2. Add TikTok support to post-content
3. Add LinkedIn support to post-content
4. Add Reddit support to post-content
5. Create search-web skill (Perplexity MCP)
6. Create analyze-competitor skill (Firecrawl MCP)
7. Create identify-trends skill

**Expected Duration:** 5-7 days

---

### Story 2.1: Instagram Posting Support

**Repository:** auriga-marketing-bot (private)  
**Type:** Enhancement  
**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** Story 1.4 (post-content skill exists)

#### Description
As a **marketing team member**,  
I want to post approved content to Instagram,  
So that we maintain presence on Instagram.

#### Technical Context
- **Affected modules:** `skills/post-content/platforms/instagram.py` (new)
- **Key changes:**
  - Add Instagram to `platform` enum in `PostContentParams`
  - Implement `post_to_instagram()` function
  - Handle Instagram's 2-step posting (create media → publish)

#### Implementation Details

**Instagram API Pattern:**
```python
# skills/post-content/platforms/instagram.py
import requests

async def post_to_instagram(content: str, media_urls: List[str]) -> dict:
    """Post to Instagram using Graph API.
    
    Instagram requires 2-step process:
    1. Create media container (upload image)
    2. Publish container
    
    Args:
        content: Caption text (max 2200 chars)
        media_urls: List of image URLs (min 1 required)
    
    Returns:
        {"post_id": "...", "post_url": "https://instagram.com/p/..."}
    """
    # Step 1: Create media container
    container_id = await create_media_container(media_urls[0], content)
    
    # Step 2: Publish container
    post_id = await publish_media_container(container_id)
    
    return {
        "post_id": post_id,
        "post_url": f"https://instagram.com/p/{post_id}"
    }
```

**Instagram Requirements:**
- Must include at least 1 image (1080x1080 min)
- Caption max 2200 characters
- Max 30 hashtags
- Requires Facebook Graph API credentials

#### Acceptance Criteria
- [ ] **Given** approved content with image, **When** posting to Instagram, **Then** creates media container and publishes successfully
- [ ] **Given** content without image, **When** posting to Instagram, **Then** returns error "Image required for Instagram"
- [ ] **Given** Instagram API rate limit, **When** posting, **Then** returns API_RATE_LIMITED with retry_after
- [ ] Integration test: Post to Instagram → Verify live on Instagram

#### Out of Scope
- Instagram Reels/Stories (feed posts only)
- Multi-image carousels (single image only)

---

### Story 2.2-2.4: TikTok, LinkedIn, Reddit Support

**Similar structure to Story 2.1, but for each platform:**
- TikTok: Requires video, uses TikTok API
- LinkedIn: Professional tone, UGC post format
- Reddit: Requires subreddit, follows subreddit rules

**Implementation Details:** See Phase 1B "Platform-Specific Requirements" for each platform's API docs and requirements.

---

### Story 2.5: Search Web Skill (Perplexity MCP)

**Repository:** auriga-marketing-bot (private)  
**Type:** Feature  
**Priority:** Medium  
**Size:** M (1-2 days)  
**Dependencies:** NONE

#### Description
As a **marketing team member**,  
I want to search the web for current information,  
So that I can research trending topics and create relevant content.

#### Technical Context
- **Affected modules:** `skills/search-web/` (new)
- **Design reference:** Phase 1A "Skill 4: search-web"
- **Key integrations:** Perplexity MCP server

#### Implementation Details

**Perplexity MCP Integration:**
```python
# skills/search-web/search_web.py
from mcp import Client

async def search_web(
    agent_state: AgentState,
    query: str,
    limit: int = 10,
    recency: str | None = None
) -> SkillResponse:
    """Search web using Perplexity MCP server"""
    mcp_client = Client()
    results = await mcp_client.call_tool(
        server="perplexity",
        tool="search",
        arguments={"query": query, "limit": limit, "recency": recency}
    )
    
    return SkillResponse(
        success=True,
        message=f"Found {len(results)} results for '{query}'",
        data={"search": results}
    )
```

#### Acceptance Criteria
- [ ] **Given** query="AI agents", **When** search_web() called, **Then** returns 10 relevant results
- [ ] **Given** recency="week", **When** search_web() called, **Then** returns only results from past week
- [ ] **Given** Perplexity API down, **When** search_web() called, **Then** retries 3 times and returns error
- [ ] Routing test: User says "search for articles about AI" → search-web skill invoked

---

### Story 2.6-2.7: Competitor Analysis & Trend Identification

Similar structure to Story 2.5:
- **analyze-competitor:** Uses Firecrawl MCP to scrape competitor content
- **identify-trends:** Aggregates search results and identifies patterns

---

## Sprint 3: Campaign Features

**Goal:** Campaign planning, scheduling, and automation

**Stories in this sprint:**
1. Create create-campaign skill
2. Create schedule-campaign skill
3. Implement cron scheduler (framework)
4. Batch approval workflow

**Expected Duration:** 5-7 days

---

### Story 3.1: Create Campaign Skill

**Repository:** auriga-marketing-bot (private)  
**Type:** Feature  
**Priority:** Medium  
**Size:** L (2-3 days)  
**Dependencies:** Stories 2.5-2.7 (research skills)

#### Description
As a **marketing team member**,  
I want to create a multi-week campaign,  
So that I can plan and schedule content strategically.

#### Technical Context
- **Affected modules:** `skills/create-campaign/` (new)
- **Design reference:** Phase 1A "Skill 5: create-campaign"
- **Pattern:** Menu pattern with sub-files

#### Implementation Details

**Campaign Creation Workflow:**
1. Research topic (calls search-web skill)
2. Define strategy (LLM-generated)
3. Generate content calendar (dates + platforms)
4. Create post ideas (one per calendar entry)

**Menu Pattern:**
```
skills/create-campaign/
├── SKILL.md                 # Main skill description
├── create_campaign.py       # Orchestrator
├── research_topic.md        # Step 1 instructions
├── define_strategy.md       # Step 2 instructions
├── generate_calendar.md     # Step 3 instructions
└── create_post_ideas.md     # Step 4 instructions
```

#### Acceptance Criteria
- [ ] **Given** topic="AI agents" and duration=4 weeks, **When** create_campaign() called, **Then** generates 4-week content calendar
- [ ] **Given** platforms=["instagram", "x"], **When** campaign created, **Then** calendar includes posts for both platforms
- [ ] **Given** campaign created, **When** saved, **Then** stored at `./data/memory/campaigns/{id}/plan.json`
- [ ] Integration test: Create campaign → Verify calendar has correct number of posts

---

### Story 3.2: Schedule Campaign Skill

**Repository:** auriga-marketing-bot (private)  
**Type:** Feature  
**Priority:** Medium  
**Size:** M (1-2 days)  
**Dependencies:** Story 3.1 (campaign exists), Story 3.3 (cron scheduler)

#### Description
As a **marketing team member**,  
I want to schedule campaign posts for future posting,  
So that posts go live automatically at optimal times.

#### Acceptance Criteria
- [ ] **Given** campaign with 20 posts, **When** schedule_campaign() called, **Then** creates 20 cron jobs
- [ ] **Given** scheduled job, **When** time arrives, **Then** posts automatically to platform
- [ ] **Given** post fails, **When** scheduled job runs, **Then** retries 3 times and notifies user

---

### Story 3.3: Cron Scheduler (Framework)

**Repository:** monkey-bot (public)  
**Type:** Enhancement  
**Priority:** Medium  
**Size:** L (2-3 days)  
**Dependencies:** NONE

#### Description
As a **framework developer**,  
I want a generic cron scheduling system,  
So that skills can schedule background jobs.

#### Implementation Details

**Simple In-Memory Scheduler (MVP):**
```python
# monkey-bot/core/scheduler/cron.py
import asyncio
from datetime import datetime

class CronScheduler:
    """Simple in-memory cron scheduler"""
    
    def __init__(self):
        self.jobs = []  # List of scheduled jobs
    
    async def schedule_job(
        self,
        job_type: str,
        schedule_at: datetime,
        payload: dict
    ) -> str:
        """Schedule a job to run at specified time"""
        job = {
            "id": str(uuid4()),
            "job_type": job_type,
            "schedule_at": schedule_at,
            "payload": payload,
            "status": "pending"
        }
        self.jobs.append(job)
        return job["id"]
    
    async def run_scheduler(self):
        """Background task that checks and executes due jobs"""
        while True:
            now = datetime.utcnow()
            for job in self.jobs:
                if job["status"] == "pending" and job["schedule_at"] <= now:
                    await self.execute_job(job)
            await asyncio.sleep(10)  # Check every 10 seconds
```

#### Acceptance Criteria
- [ ] **Given** job scheduled for 5 minutes from now, **When** time arrives, **Then** job executes
- [ ] **Given** job fails, **When** executed, **Then** marks as failed and logs error
- [ ] **Given** 100 scheduled jobs, **When** scheduler running, **Then** all execute at correct times

---

## Sprint 4: Polish & Production

**Goal:** Production readiness, deployment, monitoring

**Stories:**
1. Deployment script and documentation
2. Engagement metrics collection
3. Weekly reporting automation
4. Error handling and logging improvements

**Expected Duration:** 3-5 days

---

### Story 4.1: Deployment & Documentation

**Repository:** auriga-marketing-bot (private)  
**Type:** DevOps  
**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** All features complete

#### Description
As a **developer**,  
I want a simple deployment script,  
So that I can deploy to Cloud Run with one command.

#### Deliverables
- `deploy.sh` script (see Phase 1C)
- `README.md` with setup instructions
- `SECRETS.md` with credential setup steps
- Pre-deployment checklist

#### Acceptance Criteria
- [ ] Run `./deploy.sh` → Deploys to Cloud Run successfully
- [ ] New developer can follow README and deploy in < 30 minutes
- [ ] All secrets properly configured in GCP Secret Manager

---

### Story 4.2: Engagement Metrics Collection

**Repository:** auriga-marketing-bot (private)  
**Type:** Feature  
**Priority:** Medium  
**Size:** M (1-2 days)  
**Dependencies:** All platform posting works

#### Description
As a **marketing team member**,  
I want to track post engagement metrics,  
So that I can measure campaign effectiveness.

#### Implementation Details

**Metrics Collection:**
```python
# scripts/collect_metrics.py
async def collect_engagement_metrics():
    """Fetch engagement stats from each platform"""
    metrics = {}
    for platform in PLATFORMS:
        stats = await fetch_platform_stats(platform)
        metrics[platform] = stats
    
    save_metrics(metrics, f"./data/metrics/{date}.json")
```

**Weekly Report:**
```python
async def generate_weekly_report():
    """Generate and send weekly engagement report to Google Chat"""
    this_week = load_metrics(current_week)
    last_week = load_metrics(previous_week)
    growth = calculate_growth(this_week, last_week)
    
    report = format_report(this_week, growth)
    await send_to_google_chat(report)
```

#### Acceptance Criteria
- [ ] Run `python scripts/collect_metrics.py` → Fetches stats from all platforms
- [ ] Metrics saved to `./data/metrics/{date}.json`
- [ ] Weekly report sent to Google Chat every Monday at 9am

---

## Summary & Next Steps

### Sprint Overview

| Sprint | Goal | Stories | Duration |
|--------|------|---------|----------|
| Sprint 1 | Vertical slice (X posting) | 5 stories | 5-7 days |
| Sprint 2 | Platform expansion + research | 7 stories | 5-7 days |
| Sprint 3 | Campaign planning & scheduling | 4 stories | 5-7 days |
| Sprint 4 | Production polish | 3 stories | 3-5 days |

**Total Estimated Time:** 18-26 days (solo developer)

### Implementation Order (Recommended)

**Week 1-2: Sprint 1 (MVP)**
- Day 1-2: Story 1.1 (Skill loader enhancement)
- Day 3-4: Story 1.2 (Generate post skill)
- Day 5-6: Story 1.3 (Request approval skill)
- Day 7: Story 1.4 (Post to X skill)
- Day 8: Story 1.5 (E2E validation)

**Week 3-4: Sprint 2 (Expansion)**
- Days 9-12: Stories 2.1-2.4 (All platforms)
- Days 13-16: Stories 2.5-2.7 (Research skills)

**Week 5-6: Sprint 3 (Campaigns)**
- Days 17-19: Story 3.1 (Create campaign)
- Day 20-21: Story 3.3 (Cron scheduler framework)
- Day 22-23: Story 3.2 (Schedule campaign)

**Week 7: Sprint 4 (Production)**
- Days 24-25: Story 4.1 (Deployment)
- Days 26-27: Story 4.2 (Metrics)

### Definition of Done (Per Story)
- [ ] Code written and tested locally
- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Routing tests pass (for skills)
- [ ] Documentation updated (SKILL.md or README)
- [ ] No linter errors
- [ ] Committed to git with clear message

### Ready for Phase 3?

Once you select which story to implement first (recommend Story 1.1: Skill Loader Enhancement), we'll move to **Phase 3: Code Spec** to create a detailed implementation plan for that story.

**Which story would you like to implement first?**
