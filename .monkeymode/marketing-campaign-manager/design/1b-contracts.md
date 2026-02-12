# Design: Marketing Campaign Manager - Phase 1B: Detailed Contracts

**Date:** 2026-02-11  
**Status:** Phase 1B - API Contracts & Integration Points  
**Author:** MonkeyMode Agent

---

## Executive Summary

This document defines the technical contracts for the Marketing Campaign Manager agent, focusing on **skill invocation contracts**, **integration points with external services**, and a **practical testing strategy for MVP**. Since this is a skill-based agent (not a REST API), our "API contracts" are primarily:

1. **Skill Contracts** - How Gemini invokes skills and what they return
2. **Integration Contracts** - How skills interact with MCP servers and social APIs (simplified, reference official docs)
3. **Error Handling** - Basic retry logic and error patterns
4. **Testing Strategy** - Routing validation (critical!) and integration tests

**Scope:** This is the **MVP contract specification**. Advanced patterns (events, circuit breakers, load testing) are documented in post-MVP phase.

---

## Table of Contents

1. [Skill Invocation Contracts](#skill-invocation-contracts)
2. [Integration Points (Simplified)](#integration-points-simplified)
3. [Error Handling Strategy](#error-handling-strategy)
4. [Testing Strategy (MVP Focus)](#testing-strategy-mvp-focus)
5. [Post-MVP Enhancements](#post-mvp-enhancements)
6. [Quality Checklist](#quality-checklist)

---

## Skill Invocation Contracts

### Base Pattern: LangGraph Function Calling

**How it Works:**
1. User sends message via Google Chat: `"Create an Instagram post about AI agents"`
2. LangGraph loads all SKILL.md files and exposes them to Gemini as function definitions
3. Gemini selects appropriate skill based on SKILL.md `description` field
4. LangGraph invokes Python function with extracted parameters
5. Skill returns standardized JSON response
6. Agent formats response and sends to Google Chat

### Skill Contract Schema

All skills follow this standardized contract:

#### Input Contract

```python
# Skill function signature
def skill_function(
    agent_state: AgentState,  # Current agent state (conversation history, memory)
    **params: dict             # Skill-specific parameters extracted by Gemini
) -> SkillResponse:
    pass
```

**AgentState Fields Available:**
```python
AgentState
├── user_id: str - Google Chat user ID
├── conversation_id: str - Thread ID
├── message_history: List[Message] - Last 10 messages
├── memory_dir: Path - ./data/memory/
├── skills_dir: Path - ./skills/
└── context: dict - Additional context (brand voice, campaigns, etc.)
```

#### Output Contract (Standardized)

All skills MUST return this format:

```python
class SkillResponse:
    success: bool                  # True if operation succeeded
    message: str                   # Human-readable summary for user
    data: dict | None              # Structured data (skill-specific)
    error: dict | None             # Error details if success=False
    next_action: str | None        # Suggested next skill ("request-approval", etc.)
    ui_card: dict | None           # Optional Google Chat card UI
```

**Success Response Example:**
```json
{
  "success": true,
  "message": "Created Instagram post about AI agents!",
  "data": {
    "post": {
      "platform": "instagram",
      "content": "Exploring how AI agents are revolutionizing software development...",
      "hashtags": ["#AI", "#TechInnovation", "#AurigaOS"],
      "character_count": 285,
      "validation": {
        "within_limit": true,
        "has_hook": true,
        "has_cta": true,
        "brand_voice_valid": true
      }
    }
  },
  "next_action": "request-approval",
  "ui_card": null
}
```

**Error Response Example:**
```json
{
  "success": false,
  "message": "Failed to generate post: Content exceeds platform limit",
  "data": null,
  "error": {
    "code": "CONTENT_TOO_LONG",
    "details": {
      "platform": "x",
      "character_count": 320,
      "limit": 280,
      "excess": 40
    },
    "recoverable": true,
    "suggestion": "Try shortening the content or split into multiple posts"
  },
  "next_action": null,
  "ui_card": null
}
```

---

## Individual Skill Contracts

### 1. generate-post

**Skill Name:** `generate-post`  
**Description:** Create social media content for any platform  
**File:** `skills/generate-post/generate_post.py`

#### Parameters

```python
@dataclass
class GeneratePostParams:
    topic: str                      # What the post is about (required)
    platform: Literal[              # Target platform (required)
        "instagram", "tiktok", "x", "linkedin", "reddit"
    ]
    tone: str = "professional"      # Desired tone (optional)
    include_hashtags: bool = True   # Whether to add hashtags (optional)
    length: Literal[                # Content length (optional)
        "short", "medium", "long"
    ] = "medium"
```

#### Response Data Schema

```json
{
  "success": true,
  "message": "Created Instagram post about AI agents!",
  "data": {
    "post": {
      "id": "uuid",
      "platform": "instagram",
      "content": "Post text...",
      "hashtags": ["#AI", "#TechInnovation"],
      "character_count": 285,
      "word_count": 45,
      "validation": {
        "within_limit": true,
        "has_hook": true,
        "has_cta": true,
        "brand_voice_valid": true,
        "readability_score": 75
      },
      "metadata": {
        "generated_at": "2026-02-11T10:00:00Z",
        "model_version": "gemini-2.5-pro",
        "brand_voice_version": "1.0"
      }
    }
  },
  "next_action": "request-approval"
}
```

#### Error Codes

| Code | Description | Recoverable | Next Action |
|------|-------------|-------------|-------------|
| `CONTENT_TOO_LONG` | Content exceeds platform limit | Yes | Regenerate with shorter constraint |
| `BRAND_VOICE_VIOLATION` | Content violates brand guidelines | Yes | Regenerate with stricter guidelines |
| `INVALID_PLATFORM` | Unknown platform specified | Yes | Ask user for valid platform |
| `GENERATION_FAILED` | LLM generation error | Yes | Retry with different prompt |
| `BRAND_VOICE_NOT_FOUND` | BRAND_VOICE.md missing | No | Create brand voice doc first |

#### Platform-Specific Limits

```python
PLATFORM_LIMITS = {
    "instagram": {"chars": 2200, "hashtags": 30},
    "tiktok": {"chars": 2200, "hashtags": 30},
    "x": {"chars": 280, "hashtags": 2},
    "linkedin": {"chars": 3000, "hashtags": 5},
    "reddit": {"chars": 40000, "hashtags": 0}
}
```

---

### 2. request-approval

**Skill Name:** `request-approval`  
**Description:** Send content to Google Chat for user approval  
**File:** `skills/request-approval/request_approval.py`

#### Parameters

```python
@dataclass
class RequestApprovalParams:
    content: str                        # Content to approve (required)
    content_type: Literal[              # Type of content (required)
        "social_post", "campaign", "image"
    ]
    platform: str | None = None         # Platform if social_post
    timeout_seconds: int = 3600         # Approval timeout (1 hour default)
    context: dict | None = None         # Additional context for decision
```

#### Response Data Schema

```json
{
  "success": true,
  "message": "Content approved!",
  "data": {
    "approval": {
      "id": "uuid",
      "status": "approved",
      "approved_by": "user@example.com",
      "approved_at": "2026-02-11T10:05:00Z",
      "feedback": "Looks great! Ship it.",
      "modified_content": null,
      "modifications": []
    }
  },
  "next_action": "post-content"
}
```

**Rejection Response:**
```json
{
  "success": false,
  "message": "Content rejected by user",
  "data": {
    "approval": {
      "id": "uuid",
      "status": "rejected",
      "approved_by": "user@example.com",
      "approved_at": "2026-02-11T10:05:00Z",
      "feedback": "Change the hashtags - too many technical ones",
      "modified_content": null,
      "modifications": []
    }
  },
  "error": {
    "code": "APPROVAL_REJECTED",
    "details": {"reason": "user_rejected"},
    "recoverable": true,
    "suggestion": "Modify content based on feedback and resubmit"
  },
  "next_action": "generate-post"
}
```

**Modification Response:**
```json
{
  "success": true,
  "message": "Content modified by user",
  "data": {
    "approval": {
      "id": "uuid",
      "status": "approved_with_modifications",
      "approved_by": "user@example.com",
      "approved_at": "2026-02-11T10:05:00Z",
      "feedback": "Tweaked the wording a bit",
      "modified_content": "Updated content here...",
      "modifications": [
        {"field": "content", "original": "...", "modified": "..."},
        {"field": "hashtags", "original": ["#A"], "modified": ["#B"]}
      ]
    }
  },
  "next_action": "post-content"
}
```

#### Error Codes

| Code | Description | Recoverable | Next Action |
|------|-------------|-------------|-------------|
| `APPROVAL_TIMEOUT` | No response within timeout | Yes | Ask user if still interested |
| `APPROVAL_REJECTED` | User explicitly rejected | Yes | Modify and resubmit |
| `GOOGLE_CHAT_ERROR` | Failed to send to Google Chat | Yes | Retry with backoff |
| `INVALID_CONTENT_TYPE` | Unknown content_type | Yes | Use valid content_type |

#### Google Chat Card UI Format

```json
{
  "cardsV2": [{
    "cardId": "approval-{uuid}",
    "card": {
      "header": {
        "title": "Approval Request: Instagram Post",
        "subtitle": "Topic: AI Agents",
        "imageUrl": "https://auriga.io/icons/instagram.png"
      },
      "sections": [{
        "header": "Content Preview",
        "widgets": [{
          "textParagraph": {
            "text": "Exploring how AI agents are revolutionizing software development...\n\n#AI #TechInnovation #AurigaOS"
          }
        }]
      }, {
        "header": "Validation",
        "widgets": [{
          "keyValue": {
            "topLabel": "Character Count",
            "content": "285 / 2200",
            "icon": "CHECK_CIRCLE"
          }
        }, {
          "keyValue": {
            "topLabel": "Brand Voice",
            "content": "Valid ✓",
            "icon": "CHECK_CIRCLE"
          }
        }]
      }],
      "cardActions": [{
        "actionLabel": "✅ Approve",
        "onClick": {
          "action": {
            "function": "approve_content",
            "parameters": [{"key": "approval_id", "value": "uuid"}]
          }
        }
      }, {
        "actionLabel": "❌ Reject",
        "onClick": {
          "action": {
            "function": "reject_content",
            "parameters": [{"key": "approval_id", "value": "uuid"}]
          }
        }
      }, {
        "actionLabel": "✏️ Modify",
        "onClick": {
          "action": {
            "function": "modify_content",
            "parameters": [{"key": "approval_id", "value": "uuid"}]
          }
        }
      }]
    }
  }]
}
```

---

### 3. post-content

**Skill Name:** `post-content`  
**Description:** Publish content to social media platforms  
**File:** `skills/post-content/post_content.py`

#### Parameters

```python
@dataclass
class PostContentParams:
    content: str                        # Post text (required)
    platform: Literal[                  # Target platform (required)
        "instagram", "tiktok", "x", "linkedin", "reddit"
    ]
    media_urls: List[str] = []          # Media attachments (optional)
    scheduled_time: str | None = None   # ISO8601 timestamp or None=now
    approval_id: str | None = None      # Reference to approval record
```

#### Response Data Schema

```json
{
  "success": true,
  "message": "Posted to X successfully!",
  "data": {
    "post": {
      "id": "uuid",
      "platform": "x",
      "platform_post_id": "1234567890",
      "platform_post_url": "https://x.com/auriga_os/status/1234567890",
      "content": "Posted content...",
      "media_urls": [],
      "posted_at": "2026-02-11T10:10:00Z",
      "scheduled_for": null,
      "status": "posted",
      "metrics": {
        "views": 0,
        "likes": 0,
        "shares": 0,
        "comments": 0
      }
    }
  },
  "next_action": null
}
```

#### Error Codes

| Code | Description | Recoverable | Next Action |
|------|-------------|-------------|-------------|
| `NOT_APPROVED` | Content not approved yet | Yes | Request approval first |
| `API_KEY_MISSING` | Platform API key not in env | No | Configure API keys |
| `API_RATE_LIMITED` | Platform rate limit hit | Yes | Retry with backoff |
| `API_AUTH_FAILED` | Invalid credentials | No | Check API keys |
| `CONTENT_REJECTED` | Platform rejected content | Yes | Review platform guidelines |
| `MEDIA_UPLOAD_FAILED` | Media upload error | Yes | Retry media upload |
| `PLATFORM_UNAVAILABLE` | Platform API down | Yes | Retry later |

#### Platform-Specific Requirements

```python
PLATFORM_REQUIREMENTS = {
    "instagram": {
        "media_required": True,
        "media_types": ["image"],
        "media_min_size": (1080, 1080),
        "media_max_size": (1080, 1350),
        "max_hashtags": 30
    },
    "tiktok": {
        "media_required": True,
        "media_types": ["video"],
        "video_min_duration": 3,
        "video_max_duration": 600,
        "max_hashtags": 30
    },
    "x": {
        "media_required": False,
        "media_types": ["image", "gif", "video"],
        "max_media": 4,
        "char_limit": 280
    },
    "linkedin": {
        "media_required": False,
        "media_types": ["image", "document"],
        "max_media": 1,
        "char_limit": 3000
    },
    "reddit": {
        "media_required": False,
        "media_types": ["image", "video", "link"],
        "subreddit_required": True,
        "char_limit": 40000
    }
}
```

---

### 4. search-web

**Skill Name:** `search-web`  
**Description:** Search web for current information  
**File:** `skills/search-web/search_web.py`

#### Parameters

```python
@dataclass
class SearchWebParams:
    query: str                      # Search query (required)
    limit: int = 10                 # Max results (optional, max: 20)
    recency: Literal[               # Filter by date (optional)
        "day", "week", "month", "year"
    ] | None = None
```

#### Response Data Schema

```json
{
  "success": true,
  "message": "Found 10 results for 'AI agent evaluation frameworks'",
  "data": {
    "search": {
      "query": "AI agent evaluation frameworks",
      "total_results": 10,
      "results": [
        {
          "title": "Building Trust in AI Agents",
          "url": "https://example.com/article",
          "snippet": "Recent approaches to evaluating AI agents focus on...",
          "source": "TechCrunch",
          "published_date": "2026-02-10",
          "relevance_score": 0.95
        }
      ],
      "citations": ["https://example.com/article"],
      "executed_at": "2026-02-11T10:00:00Z"
    }
  },
  "next_action": null
}
```

#### Error Codes

| Code | Description | Recoverable | Next Action |
|------|-------------|-------------|-------------|
| `MCP_SERVER_ERROR` | Perplexity MCP unavailable | Yes | Retry with backoff |
| `SEARCH_RATE_LIMITED` | API rate limit hit | Yes | Wait and retry |
| `INVALID_QUERY` | Empty or malformed query | Yes | Fix query format |
| `NO_RESULTS` | No results found | No | Try different query |

---

### 5. create-campaign

**Skill Name:** `create-campaign`  
**Description:** Plan complete social media campaign  
**File:** `skills/create-campaign/create_campaign.py`

#### Parameters

```python
@dataclass
class CreateCampaignParams:
    topic: str                          # Campaign topic (required)
    duration_weeks: int                 # Campaign duration (required, 1-12)
    platforms: List[str]                # Target platforms (required)
    posting_frequency: int = 3          # Posts per week per platform
```

#### Response Data Schema

```json
{
  "success": true,
  "message": "Created 4-week AI Agents campaign!",
  "data": {
    "campaign": {
      "id": "uuid",
      "topic": "AI agent evaluation frameworks",
      "duration_weeks": 4,
      "platforms": ["instagram", "tiktok", "x", "linkedin", "reddit"],
      "status": "draft",
      "created_at": "2026-02-11T10:00:00Z",
      "created_by": "user@example.com",
      "strategy": {
        "theme": "Building trust through rigorous evaluation",
        "content_pillars": [
          "Technical approaches",
          "Real-world case studies",
          "Best practices",
          "Tool comparisons"
        ],
        "posting_cadence": {
          "instagram": 3,
          "tiktok": 3,
          "x": 5,
          "linkedin": 2,
          "reddit": 2
        }
      },
      "calendar": [
        {
          "date": "2026-02-12",
          "platform": "instagram",
          "pillar": "Technical approaches",
          "post_idea": "Introducing evaluation metrics for AI agents"
        }
      ],
      "total_posts": 60,
      "saved_to": "./data/memory/campaigns/{uuid}/plan.json"
    }
  },
  "next_action": "generate_campaign_content"
}
```

#### Error Codes

| Code | Description | Recoverable | Next Action |
|------|-------------|-------------|-------------|
| `INVALID_DURATION` | Duration not 1-12 weeks | Yes | Fix duration |
| `INVALID_PLATFORMS` | Unknown platform | Yes | Use valid platforms |
| `RESEARCH_FAILED` | Web research failed | Yes | Retry or skip research |
| `CAMPAIGN_EXISTS` | Similar campaign exists | Yes | Ask to replace or modify |

---

### 6. schedule-campaign

**Skill Name:** `schedule-campaign`  
**Description:** Schedule campaign posts for future posting  
**File:** `skills/schedule-campaign/schedule_campaign.py`

#### Parameters

```python
@dataclass
class ScheduleCampaignParams:
    campaign_id: str                # Campaign UUID (required)
    start_date: str                 # ISO8601 date to start (optional)
```

#### Response Data Schema

```json
{
  "success": true,
  "message": "Scheduled 60 posts for campaign!",
  "data": {
    "scheduling": {
      "campaign_id": "uuid",
      "total_posts": 60,
      "scheduled_posts": 60,
      "failed_posts": 0,
      "jobs_created": [
        {
          "job_id": "uuid",
          "post_id": "uuid",
          "platform": "instagram",
          "scheduled_at": "2026-02-12T09:00:00Z"
        }
      ],
      "next_post_at": "2026-02-12T09:00:00Z"
    }
  },
  "next_action": null
}
```

#### Error Codes

| Code | Description | Recoverable | Next Action |
|------|-------------|-------------|-------------|
| `CAMPAIGN_NOT_FOUND` | Campaign doesn't exist | No | Create campaign first |
| `POSTS_NOT_APPROVED` | Some posts not approved | Yes | Approve posts first |
| `SCHEDULER_ERROR` | Cron scheduler unavailable | Yes | Retry later |

---

## Integration Points

### 1. MCP Server Integrations

#### Perplexity MCP (Web Search)

**Purpose:** Search web for current information  
**Used By:** `search-web` skill  
**Endpoint:** MCP Server: `perplexity`  
**Authentication:** API key in `PERPLEXITY_API_KEY` env var

**Contract:**
```python
# Request
mcp_client.call_tool(
    server="perplexity",
    tool="search",
    arguments={
        "query": "AI agent evaluation frameworks",
        "limit": 10,
        "recency": "week"
    }
)

# Response
{
    "results": [
        {
            "title": "Article title",
            "url": "https://...",
            "snippet": "...",
            "source": "TechCrunch",
            "published_date": "2026-02-10"
        }
    ],
    "citations": ["https://..."]
}
```

**Error Handling:**
- **Timeout:** 10 seconds
- **Retry:** 3 attempts with exponential backoff (1s, 2s, 4s)
- **Circuit Breaker:** 5 failures in 30 seconds → circuit open for 60s
- **Fallback:** Return error to user, suggest manual search

**Rate Limits:**
- 100 requests per minute per API key
- Mitigation: Implement token bucket rate limiter

---

#### Firecrawl MCP (Web Scraping)

**Purpose:** Analyze competitor websites and content  
**Used By:** `analyze-competitor` skill  
**Endpoint:** MCP Server: `firecrawl`  
**Authentication:** API key in `FIRECRAWL_API_KEY` env var

**Contract:**
```python
# Request
mcp_client.call_tool(
    server="firecrawl",
    tool="scrape",
    arguments={
        "url": "https://competitor.com/blog",
        "extract": ["title", "content", "meta"],
        "format": "markdown"
    }
)

# Response
{
    "url": "https://competitor.com/blog",
    "title": "Page title",
    "content": "Markdown content...",
    "meta": {
        "description": "...",
        "keywords": ["ai", "agents"]
    }
}
```

**Error Handling:**
- **Timeout:** 30 seconds (scraping can be slow)
- **Retry:** 2 attempts (scraping is expensive)
- **Circuit Breaker:** 3 failures in 60 seconds → circuit open for 120s
- **Fallback:** Return partial results or error

**Rate Limits:**
- 50 requests per minute per API key
- Mitigation: Queue requests, batch process

---

#### Playwright MCP (Browser Automation)

**Purpose:** Take screenshots, interact with web pages  
**Used By:** `analyze-competitor`, `verify-post` skills  
**Endpoint:** MCP Server: `playwright`  
**Authentication:** None (local server)

**Contract:**
```python
# Request (screenshot)
mcp_client.call_tool(
    server="playwright",
    tool="screenshot",
    arguments={
        "url": "https://example.com",
        "viewport": {"width": 1920, "height": 1080},
        "full_page": False
    }
)

# Response
{
    "screenshot_url": "file:///tmp/screenshot-{uuid}.png",
    "viewport": {"width": 1920, "height": 1080},
    "timestamp": "2026-02-11T10:00:00Z"
}
```

**Error Handling:**
- **Timeout:** 60 seconds (page load + rendering)
- **Retry:** 1 attempt (expensive operation)
- **Circuit Breaker:** None (local server)
- **Fallback:** Return error, continue without screenshot

---

### 2. Social Media API Integrations (Simplified)

**Approach:** Use official Python SDK libraries for each platform. Reference official docs for detailed API specs.

#### Platform Summary

| Platform | SDK/Library | Auth | Key Requirements | Rate Limits |
|----------|------------|------|------------------|-------------|
| **Instagram** | `facebook-sdk` or requests | Access token in `INSTAGRAM_API_KEY` | Requires image (1080x1080 min), 2-step post (create media → publish) | 25 posts/day, 200 calls/hour |
| **TikTok** | `TikTokApi` or requests | Access token in `TIKTOK_API_KEY` | Requires video (3s-10min), chunked upload | 10 posts/day |
| **X (Twitter)** | `tweepy` | Bearer token in `X_API_KEY` | 280 char limit, simple POST | 300 tweets/3hrs |
| **LinkedIn** | `linkedin-api` | OAuth token in `LINKEDIN_API_KEY` | UGC post format, 3000 char limit | 100 posts/day |
| **Reddit** | `praw` | OAuth token in `REDDIT_API_KEY` | Subreddit required, 40k char limit | 1 post/10min per subreddit |

#### Implementation Pattern

```python
# Example: post_content skill implementation pattern
def post_to_platform(platform: str, content: str, media_urls: list = None):
    """
    Use platform-specific SDK to post content.
    Each platform handler in skills/post-content/platforms/{platform}.py
    """
    if platform == "x":
        import tweepy
        client = tweepy.Client(bearer_token=os.getenv("X_API_KEY"))
        response = client.create_tweet(text=content)
        return response.data["id"]
    
    elif platform == "instagram":
        # Use Instagram Graph API via requests
        # See: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
        pass
    
    # ... other platforms
```

#### Error Handling (MVP)

**Simple Retry Logic:**
```python
@retry(tries=3, delay=1, backoff=2)  # 1s, 2s, 4s delays
def post_with_retry(platform, content):
    try:
        return post_to_platform(platform, content)
    except RateLimitError as e:
        # Don't retry rate limits, save as draft
        raise
    except APIError as e:
        # Retry network/transient errors
        raise
```

**Common Error Pattern:**
- Network errors: Retry 3 times with exponential backoff
- Rate limits: Don't retry, save post as draft and notify user
- Auth errors: Don't retry, notify user to re-authenticate
- Platform-specific errors: Log and return error to user

#### Documentation Links

- **Instagram:** https://developers.facebook.com/docs/instagram-api/guides/content-publishing
- **TikTok:** https://developers.tiktok.com/doc/content-posting-api-get-started
- **X:** https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets
- **LinkedIn:** https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-post-api
- **Reddit:** https://www.reddit.com/dev/api/#POST_api_submit

---

### 3. Google Chat Integration

#### Approval UI (Google Chat Cards)

**Purpose:** Send interactive cards for content approval  
**Used By:** `request-approval` skill  
**Endpoint:** Google Chat Webhook or REST API  
**Authentication:** Service account credentials

**Contract:** See [Google Chat Card UI Format](#google-chat-card-ui-format) above.

**Error Handling:**
- **Timeout:** 30 seconds
- **Retry:** 3 attempts with exponential backoff
- **Circuit Breaker:** 10 failures in 60 seconds → circuit open for 300s
- **Fallback:** Send plain text message with link

**Rate Limits:**
- 60 messages per minute per space
- Mitigation: Queue messages

---

### 4. Internal Event System

**Status:** Deferred to Post-MVP Phase

**Rationale:** For MVP, skills can communicate through direct function returns. An event system adds complexity without immediate value for a single-process agent handling synchronous chat messages.

**Future Use Cases:**
- Analytics dashboard (track post performance)
- Campaign metrics collector
- Async workflow orchestration
- Multi-agent coordination

See [Post-MVP Enhancements](#post-mvp-enhancements) section for event system design.

---

## Error Handling Strategy

### Common Error Patterns

All skills follow these standardized error handling patterns:

#### 1. Validation Errors

**When:** Invalid parameters or missing required fields  
**HTTP Equivalent:** 422 Unprocessable Entity  
**Recovery:** User can fix parameters and retry

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid platform specified",
    "details": {
      "field": "platform",
      "value": "facebook",
      "allowed": ["instagram", "tiktok", "x", "linkedin", "reddit"]
    },
    "recoverable": true,
    "suggestion": "Use one of: instagram, tiktok, x, linkedin, reddit"
  }
}
```

---

#### 2. External Service Errors

**When:** MCP server or social API fails  
**HTTP Equivalent:** 502 Bad Gateway / 503 Service Unavailable  
**Recovery:** Retry with exponential backoff, use circuit breaker

```json
{
  "success": false,
  "error": {
    "code": "EXTERNAL_SERVICE_ERROR",
    "message": "Perplexity MCP server unavailable",
    "details": {
      "service": "perplexity",
      "operation": "search",
      "underlying_error": "ConnectionTimeout"
    },
    "recoverable": true,
    "suggestion": "Service temporarily unavailable, please try again in a few minutes"
  }
}
```

---

#### 3. Rate Limit Errors

**When:** API rate limits exceeded  
**HTTP Equivalent:** 429 Too Many Requests  
**Recovery:** Wait specified time, retry with backoff

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "X API rate limit exceeded",
    "details": {
      "platform": "x",
      "limit": "300 tweets per 3 hours",
      "reset_at": "2026-02-11T13:00:00Z",
      "retry_after_seconds": 3600
    },
    "recoverable": true,
    "suggestion": "Rate limit will reset at 1:00 PM. Your post has been saved as draft."
  }
}
```

---

#### 4. Business Logic Errors

**When:** Operation violates business rules  
**HTTP Equivalent:** 409 Conflict  
**Recovery:** User must resolve conflict

```json
{
  "success": false,
  "error": {
    "code": "DUPLICATE_CONTENT",
    "message": "Similar post already exists",
    "details": {
      "existing_post_id": "uuid",
      "platform": "instagram",
      "similarity_score": 0.95
    },
    "recoverable": true,
    "suggestion": "Modify content to make it more unique or delete existing post"
  }
}
```

---

#### 5. Configuration Errors

**When:** Missing API keys or configuration  
**HTTP Equivalent:** 500 Internal Server Error  
**Recovery:** Administrator must fix configuration

```json
{
  "success": false,
  "error": {
    "code": "CONFIGURATION_ERROR",
    "message": "Missing Instagram API credentials",
    "details": {
      "missing_env_var": "INSTAGRAM_API_KEY",
      "documentation": "https://docs.auriga.io/setup/instagram"
    },
    "recoverable": false,
    "suggestion": "Contact administrator to configure Instagram API credentials"
  }
}
```

---

### Circuit Breaker (Post-MVP)

**MVP Approach:** Simple retry logic (see below)

**Future:** Implement circuit breakers to prevent cascading failures when external services are down. See [Post-MVP Enhancements](#post-mvp-enhancements) for circuit breaker pattern.

---

### Retry Policy

Exponential backoff with jitter:

```python
RETRY_POLICY = {
    "max_attempts": 3,
    "initial_delay_seconds": 1,
    "max_delay_seconds": 30,
    "multiplier": 2,
    "jitter": True,                  # Add randomness to prevent thundering herd
    "retry_on_codes": [
        "EXTERNAL_SERVICE_ERROR",
        "RATE_LIMIT_EXCEEDED",
        "TIMEOUT"
    ]
}
```

**Example Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 1s + random(0, 0.5s)
- Attempt 3: Wait 2s + random(0, 1s)
- Attempt 4: Wait 4s + random(0, 2s)

---

## Testing Strategy (MVP Focus)

### 1. Routing Tests (CRITICAL!)

**Purpose:** Validate that Gemini correctly routes to skills based on SKILL.md descriptions

**Why Critical:** If routing fails, users can't invoke skills, entire system breaks.

**Test Framework:** pytest + LangGraph test harness

#### Routing Test Cases

```python
def test_generate_post_routing():
    """Test: 'Create an Instagram post' → generate-post skill"""
    response = agent.process_message(
        user_id="test_user",
        content="Create an Instagram post about AI agents"
    )
    assert "generate-post" in response.skills_invoked
    assert response.skills_invoked["generate-post"]["parameters"]["platform"] == "instagram"
    assert "AI agents" in response.skills_invoked["generate-post"]["parameters"]["topic"]

def test_approval_routing():
    """Test: 'Send for approval' → request-approval skill"""
    response = agent.process_message(
        user_id="test_user",
        content="Send this for my approval"
    )
    assert "request-approval" in response.skills_invoked

def test_posting_routing():
    """Test: 'Post to X' → post-content skill"""
    response = agent.process_message(
        user_id="test_user",
        content="Post this to X"
    )
    assert "post-content" in response.skills_invoked
    assert response.skills_invoked["post-content"]["parameters"]["platform"] == "x"

def test_search_routing():
    """Test: 'Search for articles' → search-web skill"""
    response = agent.process_message(
        user_id="test_user",
        content="Search for recent articles about AI evaluation"
    )
    assert "search-web" in response.skills_invoked

def test_campaign_routing():
    """Test: 'Create a campaign' → create-campaign skill"""
    response = agent.process_message(
        user_id="test_user",
        content="Create a 4-week campaign about AI agents"
    )
    assert "create-campaign" in response.skills_invoked

def test_ambiguous_routing():
    """Test: Ambiguous request → clarification or best guess"""
    response = agent.process_message(
        user_id="test_user",
        content="Do something with social media"
    )
    # Should ask for clarification OR pick most likely skill
    assert response.needs_clarification or len(response.skills_invoked) > 0

def test_out_of_scope_routing():
    """Test: Out of scope → no skill invoked"""
    response = agent.process_message(
        user_id="test_user",
        content="Delete my account"
    )
    assert len(response.skills_invoked) == 0
    assert "can't help" in response.message.lower() or "out of scope" in response.message.lower()
```

**Coverage Target:** 100% of skill descriptions tested

**Failure Action:** If routing fails, adjust SKILL.md descriptions until Gemini routes correctly

---

### 2. Skill Quality Tests

**Purpose:** Validate each skill produces correct output

#### generate-post Tests

```python
def test_generate_post_instagram():
    """Test: Generate Instagram post within limits"""
    result = generate_post(
        agent_state=mock_state,
        topic="AI agents",
        platform="instagram"
    )
    assert result.success
    assert len(result.data["post"]["content"]) <= 2200
    assert len(result.data["post"]["hashtags"]) <= 30
    assert result.data["post"]["validation"]["brand_voice_valid"]

def test_generate_post_x_char_limit():
    """Test: Generate X post within 280 chars"""
    result = generate_post(
        agent_state=mock_state,
        topic="AI agents are revolutionizing software development",
        platform="x"
    )
    assert result.success
    assert len(result.data["post"]["content"]) <= 280

def test_generate_post_invalid_platform():
    """Test: Invalid platform returns error"""
    result = generate_post(
        agent_state=mock_state,
        topic="AI agents",
        platform="facebook"
    )
    assert not result.success
    assert result.error["code"] == "INVALID_PLATFORM"
```

---

#### request-approval Tests

```python
def test_request_approval_success():
    """Test: Approval request succeeds"""
    result = request_approval(
        agent_state=mock_state,
        content="Test post",
        content_type="social_post",
        platform="instagram"
    )
    # Mock user approval
    mock_user_approves(result.data["approval"]["id"])
    assert result.success
    assert result.data["approval"]["status"] == "approved"

def test_request_approval_timeout():
    """Test: Approval timeout returns error"""
    result = request_approval(
        agent_state=mock_state,
        content="Test post",
        content_type="social_post",
        timeout_seconds=1
    )
    # Wait for timeout
    time.sleep(2)
    assert not result.success
    assert result.error["code"] == "APPROVAL_TIMEOUT"
```

---

#### post-content Tests

```python
def test_post_to_x_success():
    """Test: Post to X succeeds"""
    with mock_x_api():
        result = post_content(
            agent_state=mock_state,
            content="Test tweet #AI",
            platform="x"
        )
        assert result.success
        assert result.data["post"]["platform_post_id"]
        assert result.data["post"]["platform_post_url"]

def test_post_without_approval():
    """Test: Posting without approval fails"""
    result = post_content(
        agent_state=mock_state,
        content="Unapproved content",
        platform="x",
        approval_id=None
    )
    assert not result.success
    assert result.error["code"] == "NOT_APPROVED"

def test_post_rate_limited():
    """Test: Rate limit returns recoverable error"""
    with mock_x_api_rate_limited():
        result = post_content(
            agent_state=mock_state,
            content="Test tweet",
            platform="x"
        )
        assert not result.success
        assert result.error["code"] == "API_RATE_LIMITED"
        assert result.error["recoverable"]
```

---

### 3. Integration Tests

**Purpose:** Test end-to-end workflows with real database and mocked external services

```python
def test_end_to_end_post_workflow():
    """Test: Generate → Approve → Post workflow"""
    
    # Step 1: Generate post
    gen_result = agent.process_message(
        user_id="test_user",
        content="Create an Instagram post about AI agents"
    )
    assert gen_result.success
    post_content = gen_result.data["post"]["content"]
    
    # Step 2: Approve post
    approval_result = agent.process_message(
        user_id="test_user",
        content="Send this for approval"
    )
    assert approval_result.success
    approval_id = approval_result.data["approval"]["id"]
    
    # Mock user approves
    mock_user_approves(approval_id)
    
    # Step 3: Post to Instagram
    with mock_instagram_api():
        post_result = agent.process_message(
            user_id="test_user",
            content="Post to Instagram"
        )
        assert post_result.success
        assert post_result.data["post"]["platform_post_url"]

def test_campaign_workflow():
    """Test: Create campaign → Generate posts → Schedule"""
    
    # Create campaign
    campaign_result = agent.process_message(
        user_id="test_user",
        content="Create a 4-week AI agents campaign for Instagram and X"
    )
    assert campaign_result.success
    campaign_id = campaign_result.data["campaign"]["id"]
    
    # Schedule campaign
    schedule_result = agent.process_message(
        user_id="test_user",
        content=f"Schedule campaign {campaign_id}"
    )
    assert schedule_result.success
    assert schedule_result.data["scheduling"]["scheduled_posts"] > 0
```

---

### 4. Security Tests (MVP Focus)

**Purpose:** Validate security controls

```python
def test_unauthorized_user():
    """Test: Unauthorized users can't access agent"""
    response = agent.process_message(
        user_id="unknown_user@example.com",
        content="Create a post"
    )
    assert not response.success
    assert response.error["code"] == "UNAUTHORIZED"

def test_api_key_not_exposed():
    """Test: API keys never in logs or responses"""
    response = agent.process_message(
        user_id="test_user",
        content="Post to X"
    )
    
    # Check response doesn't contain API keys
    response_str = json.dumps(response.dict())
    assert "INSTAGRAM_API_KEY" not in response_str
    assert "X_API_KEY" not in response_str
    
    # Check logs
    logs = get_recent_logs()
    for log in logs:
        assert not any(key in log for key in SENSITIVE_ENV_VARS)

def test_brand_voice_validation():
    """Test: Brand voice violations are caught"""
    result = generate_post(
        agent_state=mock_state,
        topic="Buy now! Limited time offer!",  # Salesy, violates brand voice
        platform="instagram"
    )
    assert not result.success or not result.data["post"]["validation"]["brand_voice_valid"]
```

---

## Post-MVP Enhancements

The following patterns are documented for future implementation but deferred from MVP to reduce complexity:

### 1. Internal Event System

**Purpose:** Workflow orchestration, analytics, observability

**Event Types to Implement:**
- `content.generated` - Track when posts are created
- `approval.requested` / `approval.completed` - Track approval workflow
- `content.posted` - Track successful posts
- `campaign.created` - Track campaign creation

**Implementation:**
- Start with in-memory event bus
- Upgrade to GCP Pub/Sub for durability
- Add event schema validation
- Implement event consumers (analytics, metrics)

**Benefits:**
- Decouple skills from analytics
- Enable dashboard and metrics collection
- Support async workflows
- Enable multi-agent coordination

---

### 2. Circuit Breaker Pattern

**Purpose:** Prevent cascading failures when external services are down

**Pattern:**
```python
CIRCUIT_BREAKER_CONFIG = {
    "perplexity": {
        "failure_threshold": 5,      # Open circuit after 5 failures
        "timeout_seconds": 30,       # Within 30 seconds
        "recovery_timeout": 60,      # Stay open for 60 seconds
        "half_open_max_calls": 3     # Test with 3 calls before fully closing
    },
    "instagram": {"failure_threshold": 10, "timeout_seconds": 60, ...},
    "x": {"failure_threshold": 10, "timeout_seconds": 60, ...}
}
```

**Implementation:**
- Use `pybreaker` library or implement custom
- Monitor failure rates per external service
- Automatically open circuit on threshold
- Half-open state to test recovery

**MVP Alternative:** Simple retry logic (see Error Handling section)

---

### 3. Contract Testing

**Purpose:** Validate all skills return standardized schemas

**Tests to Add:**
- Validate SkillResponse schema across all skills
- Validate Google Chat card format
- Validate event schemas (if events implemented)

**Tools:**
- JSON Schema validation
- Pydantic model validation
- Integration test assertions

**Why Deferred:** Integration tests catch this, adding contract tests is redundant for MVP

---

### 4. Load/Performance Testing

**Purpose:** Validate system handles expected load

**Expected Load:**
- Current: 1-2 interactions per hour (very low!)
- Peak: Maybe 10-20 interactions per hour during campaign creation

**Tests to Add (if needed):**
- Baseline: 10 msgs/min
- Peak: 100 msgs/min
- Campaign creation: 5 campaigns/min

**Tools:** k6, Locust, or JMeter

**Why Deferred:** Expected volume is too low to justify load testing MVP

---

### 5. Advanced Error Handling

**Patterns to Add:**
- Dead letter queue for failed posts
- Automatic retry with exponential backoff + jitter
- Error rate monitoring and alerting
- Graceful degradation (e.g., post without media if media upload fails)

**MVP Alternative:** Simple try/catch with basic retry

---

### 6. Analytics & Metrics

**Metrics to Track:**
- Post performance (likes, shares, comments)
- Skill invocation rates
- Error rates by skill
- Approval times
- Campaign effectiveness

**Implementation:**
- Integrate with GCP Cloud Monitoring
- Create dashboards in Grafana or Looker
- Set up alerts for error rates

**Why Deferred:** Focus on getting posts live first, measure later

---

## Quality Checklist

### Completeness (MVP Scope)
- ✅ All skill contracts defined with parameters and responses
- ✅ Common error patterns documented (5 standard patterns)
- ✅ Integration points simplified (reference official docs + key requirements)
- ✅ Testing strategy focused on MVP (routing tests + integration tests)
- ✅ Simple retry policy defined (exponential backoff)
- ✅ Platform requirements documented (limits, media specs)
- ✅ Google Chat card UI format defined
- ✅ Post-MVP enhancements documented for future

### Quality
- ✅ Error handling is standardized across skills
- ✅ Platform-specific requirements documented (character limits, rate limits)
- ✅ Security considerations addressed (API key handling)
- ✅ Test scenarios cover critical paths (routing is priority #1!)
- ✅ Routing validation prioritized (most critical test!)

### Clarity
- ✅ Skill contracts are unambiguous
- ✅ Integration approach is simple (use SDKs, reference official docs)
- ✅ Error codes are well-defined with recovery strategies
- ✅ Testing approach is practical and achievable for MVP
- ✅ Clear separation between MVP and post-MVP features

---

## Next Steps

### Phase 1C: Production Readiness

After user approves this Phase 1B document, proceed to Phase 1C to address:
- **Security:** API key storage, PII filtering, rate limiting enforcement
- **Performance:** Caching strategies, async operations, database optimization
- **Deployment:** Cloud Run configuration, environment variables, secrets management
- **Observability:** Logging, metrics, tracing, alerting
- **Risk Assessment:** Failure modes, mitigations, monitoring

---

## Definition of Done

Phase 1B is complete when:
- ✅ All skill contracts documented with schemas (standardized SkillResponse)
- ✅ Integration points simplified (reference official SDKs/docs)
- ✅ Testing strategy defined (routing tests + integration tests)
- ✅ Google Chat approval UI format specified
- ✅ Platform-specific API requirements documented (limits, media)
- ✅ Simple retry policy defined (exponential backoff)
- ✅ Post-MVP enhancements documented (events, circuit breakers, load tests)
- ⏳ **User approves:** "Simplified contracts look good for MVP"

**Ready for user review!**
