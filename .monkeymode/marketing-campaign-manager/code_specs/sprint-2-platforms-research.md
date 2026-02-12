# Code Spec: Sprint 2 - Platform Expansion & Research Skills

**Author:** MonkeyMode Agent  
**Date:** 2026-02-12  
**Status:** Ready for Implementation  
**Sprint:** Sprint 2 - Platform Expansion  
**Stories:** 2.1-2.7 (Instagram, TikTok, LinkedIn, Reddit posting + Research skills)

---

## Table of Contents

1. [Implementation Summary](#implementation-summary)
2. [Technical Context](#technical-context)
3. [Story 2.1: Instagram Posting Support](#story-21-instagram-posting-support)
4. [Story 2.2: TikTok Posting Support](#story-22-tiktok-posting-support)
5. [Story 2.3: LinkedIn Posting Support](#story-23-linkedin-posting-support)
6. [Story 2.4: Reddit Posting Support](#story-24-reddit-posting-support)
7. [Story 2.5: Search Web Skill (Perplexity MCP)](#story-25-search-web-skill-perplexity-mcp)
8. [Story 2.6: Analyze Competitor Skill (Firecrawl MCP)](#story-26-analyze-competitor-skill-firecrawl-mcp)
9. [Story 2.7: Identify Trends Skill](#story-27-identify-trends-skill)
10. [Dependency Graph](#dependency-graph)
11. [Final Verification](#final-verification)

---

## Implementation Summary

**Files to Create:** 28 files  
**Files to Modify:** 4 files  
**Tests to Add:** 14 test files  
**Estimated Complexity:** L (5-7 days solo developer)

### File Breakdown by Story

| Story | Description | Files Created | Files Modified | Tests |
|-------|-------------|---------------|----------------|-------|
| 2.1 | Instagram posting | 1 | 2 | 1 |
| 2.2 | TikTok posting | 1 | 1 | 1 |
| 2.3 | LinkedIn posting | 1 | 1 | 1 |
| 2.4 | Reddit posting | 1 | 1 | 1 |
| 2.5 | Search web skill | 4 | 0 | 2 |
| 2.6 | Analyze competitor | 4 | 0 | 2 |
| 2.7 | Identify trends | 4 | 0 | 2 |
| **Total** | **7 stories** | **16** | **5** | **10** |

---

## Technical Context

### Key Integration Points

**Platform APIs:**
- **Instagram:** Facebook Graph API (2-step: create container → publish)
- **TikTok:** TikTok Content Posting API (requires video)
- **LinkedIn:** LinkedIn UGC Post API (supports text + images)
- **Reddit:** Reddit API (requires subreddit validation)

**MCP Servers:**
- **Perplexity MCP:** Web search with recency filters
- **Firecrawl MCP:** Web scraping for competitor analysis

### Dependencies

All stories depend on:
- Story 1.4 completed (post-content skill structure exists)
- X/Twitter posting working (reference implementation)

### Reusable Utilities

From Sprint 1:
- `skills/post-content/platforms/base.py` - Base platform interface
- `skills/post-content/platforms/x.py` - Reference X posting implementation
- `skills/post-content/post_content.py` - Main skill orchestrator
- `tests/skills/test_post_content.py` - Test patterns

---

## Story 2.1: Instagram Posting Support

**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** Story 1.4 (post-content skill exists)

### Task 2.1.1: Add Instagram Platform Module

**Files to Create:**
- `skills/post-content/platforms/instagram.py` (new)
- `tests/skills/post-content/test_instagram.py` (new)

**Files to Modify:**
- `skills/post-content/platforms/__init__.py` - Export Instagram platform
- `skills/post-content/post_content.py` - Add Instagram to platform enum

**Pattern Reference:** Follow `skills/post-content/platforms/x.py` structure

**Implementation Algorithm:**

Instagram requires a 2-step posting process:
1. **Step 1:** Create media container (upload image to Instagram)
2. **Step 2:** Publish the container

**Function Signatures:**

```python
# skills/post-content/platforms/instagram.py
from typing import List
from .base import BasePlatform, PostResult

class InstagramPlatform(BasePlatform):
    """Instagram posting implementation using Graph API."""
    
    async def post(
        self,
        content: str,
        media_urls: List[str],
        **kwargs
    ) -> PostResult:
        """Post to Instagram feed.
        
        Args:
            content: Caption text (max 2200 chars)
            media_urls: List of image URLs (at least 1 required)
            kwargs: Additional platform-specific params
            
        Returns:
            PostResult with post_id and post_url
            
        Raises:
            ValidationError: If no media provided or caption too long
            RateLimitError: If Instagram API rate limit hit
            PlatformError: If posting fails
        """
        await self._validate_content(content, media_urls)
        container_id = await self._create_media_container(media_urls[0], content)
        post_id = await self._publish_container(container_id)
        return PostResult(
            success=True,
            post_id=post_id,
            post_url=f"https://instagram.com/p/{post_id}"
        )
    
    async def _create_media_container(
        self,
        image_url: str,
        caption: str
    ) -> str:
        """Step 1: Create media container on Instagram.
        
        POST https://graph.facebook.com/v18.0/{ig-user-id}/media
        Params:
            - image_url: Public URL to image
            - caption: Post caption
            - access_token: Instagram access token
        """
        pass
    
    async def _publish_container(self, container_id: str) -> str:
        """Step 2: Publish the media container.
        
        POST https://graph.facebook.com/v18.0/{ig-user-id}/media_publish
        Params:
            - creation_id: Container ID from step 1
            - access_token: Instagram access token
        """
        pass
    
    def _validate_content(self, content: str, media_urls: List[str]) -> None:
        """Validate Instagram requirements.
        
        Rules:
            - At least 1 image required
            - Caption max 2200 characters
            - Max 30 hashtags
            - Image min 320x320px, recommended 1080x1080px
        """
        pass
```

**Instagram API Details:**

**Graph API Endpoints:**
```python
BASE_URL = "https://graph.facebook.com/v18.0"
IG_USER_ID = os.getenv("INSTAGRAM_USER_ID")  # From env
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")  # From env

# Step 1: Create container
POST f"{BASE_URL}/{IG_USER_ID}/media"
Body: {
    "image_url": "https://example.com/image.jpg",
    "caption": "Post caption #hashtag",
    "access_token": ACCESS_TOKEN
}
Response: {"id": "container_id_123"}

# Step 2: Publish
POST f"{BASE_URL}/{IG_USER_ID}/media_publish"
Body: {
    "creation_id": "container_id_123",
    "access_token": ACCESS_TOKEN
}
Response: {"id": "post_id_456"}
```

**Rate Limits:**
- 25 API calls per user per hour
- 200 API calls per app per hour (shared across users)

**Error Handling:**
```python
# Instagram API errors
error_map = {
    4: "API_RATE_LIMITED",  # Too many requests
    190: "ACCESS_TOKEN_INVALID",  # Token expired
    100: "INVALID_PARAMETER",  # Bad image URL or caption
    368: "TEMPORARILY_BLOCKED"  # Spam detected
}
```

**Test Cases** (follow pattern in `test_x.py`):
- `test_post_with_image_success()` - Valid image + caption → Returns post ID and URL
- `test_post_without_image_fails()` - No media → Raises ValidationError
- `test_post_caption_too_long()` - Caption > 2200 chars → Raises ValidationError
- `test_post_rate_limited()` - API returns 4 error → Raises RateLimitError with retry_after
- `test_post_invalid_token()` - API returns 190 error → Raises AuthenticationError
- `test_create_container_fails()` - Step 1 fails → Proper error propagation
- `test_publish_container_fails()` - Step 1 succeeds but Step 2 fails → Logs container ID for retry

**Configuration Required:**
```python
# .env (add these to deployment config)
INSTAGRAM_USER_ID=your_instagram_business_account_id
INSTAGRAM_ACCESS_TOKEN=your_long_lived_access_token
```

**Critical Notes:**
- Instagram requires a **Business or Creator account** (personal accounts don't have API access)
- Access tokens need to be **long-lived** (60 days) and refreshed before expiry
- Image URLs must be **publicly accessible** when creating container
- If Step 1 succeeds but Step 2 fails, save `container_id` in logs for manual retry
- Instagram has stricter spam detection than X - avoid duplicate content

---

## Story 2.2: TikTok Posting Support

**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** Story 1.4 (post-content skill exists)

### Task 2.2.1: Add TikTok Platform Module

**Files to Create:**
- `skills/post-content/platforms/tiktok.py` (new)
- `tests/skills/post-content/test_tiktok.py` (new)

**Files to Modify:**
- `skills/post-content/platforms/__init__.py` - Export TikTok platform

**Pattern Reference:** Follow Instagram 2-step pattern (TikTok uses similar flow)

**Implementation Algorithm:**

TikTok posting process:
1. **Step 1:** Initialize upload (get upload URL)
2. **Step 2:** Upload video to provided URL
3. **Step 3:** Publish video with metadata

**Function Signatures:**

```python
# skills/post-content/platforms/tiktok.py
from typing import List
from .base import BasePlatform, PostResult

class TikTokPlatform(BasePlatform):
    """TikTok posting implementation using Content Posting API."""
    
    async def post(
        self,
        content: str,
        media_urls: List[str],  # Must be video URLs
        **kwargs
    ) -> PostResult:
        """Post video to TikTok.
        
        Args:
            content: Video caption/description (max 2200 chars)
            media_urls: List of video URLs (exactly 1 required)
            kwargs: Additional params (privacy_level, allow_comments, etc.)
            
        Returns:
            PostResult with post_id and post_url
            
        Raises:
            ValidationError: If not video or caption invalid
            RateLimitError: If TikTok API rate limit hit
            PlatformError: If posting fails
        """
        await self._validate_content(content, media_urls)
        upload_url = await self._initialize_upload()
        await self._upload_video(upload_url, media_urls[0])
        post_id = await self._publish_video(content, upload_url)
        return PostResult(
            success=True,
            post_id=post_id,
            post_url=f"https://tiktok.com/@{self.username}/video/{post_id}"
        )
    
    async def _initialize_upload(self) -> str:
        """Step 1: Get upload URL from TikTok."""
        pass
    
    async def _upload_video(self, upload_url: str, video_url: str) -> None:
        """Step 2: Upload video file to TikTok."""
        pass
    
    async def _publish_video(self, caption: str, upload_url: str) -> str:
        """Step 3: Publish video with metadata."""
        pass
```

**TikTok API Details:**

```python
BASE_URL = "https://open.tiktokapis.com/v2"
ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN")

# Step 1: Initialize
POST f"{BASE_URL}/post/publish/inbox/video/init/"
Headers: {"Authorization": f"Bearer {ACCESS_TOKEN}"}
Body: {
    "source_info": {
        "source": "FILE_UPLOAD",
        "video_size": 12345678,  # bytes
        "chunk_size": 5242880,   # 5MB chunks
        "total_chunk_count": 3
    }
}
Response: {"data": {"upload_url": "https://...", "publish_id": "..."}}

# Step 2: Upload chunks
PUT upload_url
Body: video file chunks

# Step 3: Publish
POST f"{BASE_URL}/post/publish/video/init/"
Body: {
    "publish_id": "from_step_1",
    "post_info": {
        "title": "Video title",
        "description": "Caption text",
        "privacy_level": "PUBLIC_TO_EVERYONE",
        "disable_comment": false,
        "disable_duet": false,
        "disable_stitch": false
    }
}
```

**Test Cases** (follow Instagram pattern):
- `test_post_video_success()` - Valid video + caption → Returns post ID
- `test_post_without_video_fails()` - No video → ValidationError
- `test_post_with_image_fails()` - Image instead of video → ValidationError
- `test_video_too_large()` - Video > 4GB → ValidationError
- `test_upload_fails()` - Step 2 upload fails → Proper error handling
- `test_rate_limited()` - API rate limit → RateLimitError with retry_after

**Configuration:**
```python
# .env
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret
TIKTOK_ACCESS_TOKEN=user_access_token  # OAuth flow required
TIKTOK_USERNAME=your_tiktok_username
```

**Critical Notes:**
- TikTok requires **video content only** (no images, no text-only)
- Video requirements: MP4, max 4GB, 3-60 seconds recommended
- OAuth flow required for access token (more complex than Instagram)
- Rate limits: 100 posts per day per user
- For MVP, focus on **FILE_UPLOAD** source (not PULL_FROM_URL)

---

## Story 2.3: LinkedIn Posting Support

**Priority:** High  
**Size:** M (1-2 days)  
**Dependencies:** Story 1.4 (post-content skill exists)

### Task 2.3.1: Add LinkedIn Platform Module

**Files to Create:**
- `skills/post-content/platforms/linkedin.py` (new)
- `tests/skills/post-content/test_linkedin.py` (new)

**Files to Modify:**
- `skills/post-content/platforms/__init__.py` - Export LinkedIn platform

**Pattern Reference:** Follow X platform (simpler 1-step posting like X)

**Implementation Algorithm:**

LinkedIn uses UGC (User Generated Content) Post API:
1. Create post with text + optional images
2. Get post ID and URL immediately (1-step, unlike Instagram)

**Function Signatures:**

```python
# skills/post-content/platforms/linkedin.py
from typing import List
from .base import BasePlatform, PostResult

class LinkedInPlatform(BasePlatform):
    """LinkedIn posting using UGC Post API."""
    
    async def post(
        self,
        content: str,
        media_urls: List[str] = None,
        **kwargs
    ) -> PostResult:
        """Post to LinkedIn feed.
        
        Args:
            content: Post text (max 3000 chars, recommended 150-250)
            media_urls: Optional list of image URLs (max 9)
            kwargs: visibility ("PUBLIC" or "CONNECTIONS")
            
        Returns:
            PostResult with post_id and post_url
            
        Raises:
            ValidationError: If content exceeds limits
            RateLimitError: If LinkedIn throttles
            PlatformError: If posting fails
        """
        await self._validate_content(content, media_urls)
        post_data = self._build_ugc_post(content, media_urls, kwargs.get("visibility", "PUBLIC"))
        response = await self._create_ugc_post(post_data)
        return PostResult(
            success=True,
            post_id=response["id"],
            post_url=f"https://www.linkedin.com/feed/update/{response['id']}"
        )
    
    def _build_ugc_post(
        self,
        content: str,
        media_urls: List[str],
        visibility: str
    ) -> dict:
        """Build LinkedIn UGC post payload."""
        pass
    
    async def _create_ugc_post(self, post_data: dict) -> dict:
        """POST to LinkedIn UGC API."""
        pass
```

**LinkedIn API Details:**

```python
BASE_URL = "https://api.linkedin.com/v2"
ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
PERSON_URN = os.getenv("LINKEDIN_PERSON_URN")  # urn:li:person:xxxxx

POST f"{BASE_URL}/ugcPosts"
Headers: {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0"
}
Body: {
    "author": f"urn:li:person:{PERSON_URN}",
    "lifecycleState": "PUBLISHED",
    "specificContent": {
        "com.linkedin.ugc.ShareContent": {
            "shareCommentary": {
                "text": "Post content here"
            },
            "shareMediaCategory": "NONE"  # or "IMAGE" if media
        }
    },
    "visibility": {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
    }
}
```

**Test Cases**:
- `test_post_text_only()` - Text post → Success
- `test_post_with_image()` - Text + image → Success
- `test_content_too_long()` - > 3000 chars → ValidationError
- `test_invalid_visibility()` - Bad visibility param → ValidationError
- `test_rate_limited()` - Throttled → RateLimitError

**Configuration:**
```python
# .env
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_ACCESS_TOKEN=user_access_token  # OAuth flow
LINKEDIN_PERSON_URN=urn:li:person:your_person_id
```

**Critical Notes:**
- LinkedIn prefers **professional tone** - adjust brand voice accordingly
- Optimal post length: **150-250 characters** (longer posts get truncated in feed)
- OAuth 2.0 required for access token
- Rate limit: **100 posts per day per person**
- For images, LinkedIn API requires additional upload step (defer to post-MVP)

---

## Story 2.4: Reddit Posting Support

**Priority:** Medium  
**Size:** M (1-2 days)  
**Dependencies:** Story 1.4 (post-content skill exists)

### Task 2.4.1: Add Reddit Platform Module

**Files to Create:**
- `skills/post-content/platforms/reddit.py` (new)
- `tests/skills/post-content/test_reddit.py` (new)

**Files to Modify:**
- `skills/post-content/platforms/__init__.py` - Export Reddit platform

**Pattern Reference:** Similar to LinkedIn (1-step posting) but requires subreddit validation

**Implementation Algorithm:**

Reddit posting flow:
1. Validate subreddit exists and user has permission
2. Create post (text or link) in specified subreddit
3. Return post ID and URL

**Function Signatures:**

```python
# skills/post-content/platforms/reddit.py
from typing import List, Literal
from .base import BasePlatform, PostResult

class RedditPlatform(BasePlatform):
    """Reddit posting using Reddit API."""
    
    async def post(
        self,
        content: str,
        subreddit: str,  # Required for Reddit
        post_type: Literal["text", "link"] = "text",
        **kwargs
    ) -> PostResult:
        """Post to Reddit subreddit.
        
        Args:
            content: Post body (text) or URL (link post)
            subreddit: Target subreddit name (without r/)
            post_type: "text" for self-post or "link" for link post
            kwargs: title (required), flair_id (optional)
            
        Returns:
            PostResult with post_id and post_url
            
        Raises:
            ValidationError: Missing title or invalid subreddit
            PermissionError: User can't post in subreddit
            RateLimitError: Reddit rate limit hit
        """
        title = kwargs.get("title")
        if not title:
            raise ValidationError("Reddit posts require a 'title' parameter")
        
        await self._validate_subreddit(subreddit)
        response = await self._submit_post(subreddit, title, content, post_type)
        
        return PostResult(
            success=True,
            post_id=response["name"],  # Reddit uses t3_xxxxx format
            post_url=f"https://reddit.com{response['permalink']}"
        )
    
    async def _validate_subreddit(self, subreddit: str) -> None:
        """Validate subreddit exists and user can post."""
        pass
    
    async def _submit_post(
        self,
        subreddit: str,
        title: str,
        content: str,
        post_type: str
    ) -> dict:
        """Submit post to Reddit."""
        pass
```

**Reddit API Details:**

```python
BASE_URL = "https://oauth.reddit.com"
ACCESS_TOKEN = os.getenv("REDDIT_ACCESS_TOKEN")  # OAuth required

# Check subreddit
GET f"{BASE_URL}/r/{subreddit}/about"
Headers: {"Authorization": f"Bearer {ACCESS_TOKEN}"}

# Submit post
POST f"{BASE_URL}/api/submit"
Headers: {"Authorization": f"Bearer {ACCESS_TOKEN}"}
Body: {
    "sr": subreddit,
    "kind": "self",  # or "link"
    "title": "Post title",
    "text": "Post body",  # for self posts
    "url": "https://...",  # for link posts
    "sendreplies": true
}
Response: {
    "json": {
        "data": {
            "name": "t3_xyz123",
            "permalink": "/r/subreddit/comments/xyz123/post_title/"
        }
    }
}
```

**Test Cases**:
- `test_post_text_success()` - Text post with title → Success
- `test_post_link_success()` - Link post → Success
- `test_post_without_title()` - No title → ValidationError
- `test_invalid_subreddit()` - Subreddit doesn't exist → ValidationError
- `test_subreddit_no_permission()` - User can't post → PermissionError
- `test_rate_limited()` - Reddit throttle → RateLimitError

**Configuration:**
```python
# .env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_password  # or use OAuth refresh token
REDDIT_ACCESS_TOKEN=bearer_token
```

**Critical Notes:**
- Reddit has **strict subreddit rules** - validate against each subreddit's posting requirements
- New accounts have **karma requirements** to post in many subreddits
- Rate limit: **1 post per 10 minutes** for new accounts, improves with karma
- Consider **auto-generating titles** from post content if user doesn't provide one
- Each subreddit has unique culture - may need subreddit-specific prompts in generate-post

---

## Story 2.5: Search Web Skill (Perplexity MCP)

**Priority:** Medium  
**Size:** M (1-2 days)  
**Dependencies:** NONE

### Task 2.5.1: Create Search Web Skill

**Files to Create:**
- `skills/search-web/SKILL.md` (new)
- `skills/search-web/search_web.py` (new)
- `skills/search-web/__init__.py` (new)
- `tests/skills/test_search_web.py` (new)

**Files to Modify:** NONE

**Pattern Reference:** This is a simple MCP wrapper skill - minimal code

**Implementation Algorithm:**

1. Parse user's search query from message
2. Call Perplexity MCP server's `search` tool
3. Format results for agent consumption
4. Return structured search results

**Function Signatures:**

```python
# skills/search-web/search_web.py
from typing import Literal
from src.core.interfaces import AgentState, SkillResponse

async def search_web(
    agent_state: AgentState,
    query: str,
    limit: int = 10,
    recency: Literal["day", "week", "month", "year"] | None = None
) -> SkillResponse:
    """Search web using Perplexity MCP server.
    
    Args:
        agent_state: Current agent state
        query: Search query
        limit: Max results to return (default 10, max 20)
        recency: Optional recency filter
        
    Returns:
        SkillResponse with search results in data.results
    """
    try:
        # Call Perplexity MCP
        mcp_client = agent_state.mcp_client  # Assuming MCP client in state
        results = await mcp_client.call_tool(
            server="perplexity",
            tool="search",
            arguments={
                "query": query,
                "limit": min(limit, 20),
                "recency": recency
            }
        )
        
        return SkillResponse(
            success=True,
            message=f"Found {len(results)} results for '{query}'",
            data={
                "query": query,
                "results": results,
                "count": len(results)
            }
        )
    except Exception as e:
        return SkillResponse(
            success=False,
            message=f"Search failed: {str(e)}",
            error={"code": "SEARCH_FAILED", "details": str(e)}
        )
```

**SKILL.md Content:**

```markdown
---
name: search-web
description: Search the web for current information, articles, and trends using Perplexity AI. Use when researching topics, finding recent news, or gathering data for content creation.
---

# search-web

Search the web for real-time information.

## When to invoke

User says:
- "search for articles about AI agents"
- "what's trending in tech?"
- "find recent news about [topic]"
- "research [topic] for me"

## Parameters

- `query` (str, required): Search query
- `limit` (int, optional): Max results (default 10)
- `recency` (str, optional): Filter by time ("day", "week", "month", "year")
```

**Test Cases**:
- `test_search_basic()` - Simple query → Returns 10 results
- `test_search_with_recency()` - Query + recency filter → Only recent results
- `test_search_limit()` - Limit param respected → Correct count
- `test_search_empty_results()` - No results found → success=True, empty results
- `test_search_mcp_error()` - MCP server down → success=False, error details
- `test_routing()` - User says "search for AI agents" → search-web invoked

**MCP Server Setup:**

Add Perplexity MCP to agent config:
```yaml
# config/mcp_servers.yaml
mcp_servers:
  perplexity:
    type: perplexity
    api_key: ${PERPLEXITY_API_KEY}
    tools:
      - search
```

**Configuration:**
```python
# .env
PERPLEXITY_API_KEY=your_perplexity_api_key
```

**Critical Notes:**
- Perplexity returns **summarized results** with source citations
- Results include both title and snippet
- Rate limit: Check Perplexity MCP documentation
- Consider caching results to reduce API calls

---

## Story 2.6: Analyze Competitor Skill (Firecrawl MCP)

**Priority:** Medium  
**Size:** M (1-2 days)  
**Dependencies:** NONE

### Task 2.6.1: Create Analyze Competitor Skill

**Files to Create:**
- `skills/analyze-competitor/SKILL.md` (new)
- `skills/analyze-competitor/analyze_competitor.py` (new)
- `skills/analyze-competitor/__init__.py` (new)
- `tests/skills/test_analyze_competitor.py` (new)

**Pattern Reference:** Similar to search-web (MCP wrapper)

**Implementation Algorithm:**

1. Parse competitor URL from user message
2. Call Firecrawl MCP to scrape website
3. Extract key information (recent posts, topics, style)
4. Return structured analysis

**Function Signatures:**

```python
# skills/analyze-competitor/analyze_competitor.py
from src.core.interfaces import AgentState, SkillResponse

async def analyze_competitor(
    agent_state: AgentState,
    competitor_url: str,
    sections: list[str] = None  # ["blog", "social", "about"]
) -> SkillResponse:
    """Analyze competitor's content strategy.
    
    Args:
        agent_state: Current agent state
        competitor_url: URL to analyze
        sections: Specific sections to scrape (optional)
        
    Returns:
        SkillResponse with competitor analysis
    """
    try:
        # Scrape website using Firecrawl
        mcp_client = agent_state.mcp_client
        scraped_data = await mcp_client.call_tool(
            server="firecrawl",
            tool="scrape",
            arguments={
                "url": competitor_url,
                "wait_for": "networkidle"
            }
        )
        
        # Analyze content
        analysis = await _analyze_content(scraped_data, agent_state.llm_client)
        
        return SkillResponse(
            success=True,
            message=f"Analyzed competitor: {competitor_url}",
            data={
                "url": competitor_url,
                "analysis": analysis,
                "scraped_at": scraped_data.get("timestamp")
            }
        )
    except Exception as e:
        return SkillResponse(
            success=False,
            message=f"Analysis failed: {str(e)}",
            error={"code": "ANALYSIS_FAILED", "details": str(e)}
        )

async def _analyze_content(scraped_data: dict, llm_client) -> dict:
    """Use LLM to analyze scraped content."""
    prompt = f"""
    Analyze this competitor's content strategy:
    
    Content: {scraped_data['content'][:5000]}
    
    Provide:
    1. Main topics discussed
    2. Content tone/style
    3. Posting frequency
    4. Unique angles or approaches
    5. Opportunities for differentiation
    """
    
    response = await llm_client.generate(prompt)
    return {"insights": response.text}
```

**SKILL.md Content:**

```markdown
---
name: analyze-competitor
description: Analyze a competitor's website or blog to understand their content strategy, posting frequency, topics, and style. Use when researching competitors or finding content gaps.
---

# analyze-competitor

Scrape and analyze competitor content.

## When to invoke

User says:
- "analyze [competitor name]'s blog"
- "what is [company] posting about?"
- "check out [url] and tell me their content strategy"
```

**Test Cases**:
- `test_analyze_success()` - Valid URL → Returns analysis
- `test_analyze_invalid_url()` - Bad URL → ValidationError
- `test_firecrawl_timeout()` - Scrape times out → Proper error handling
- `test_llm_analysis()` - Analysis includes all 5 points → Complete insights

**MCP Server Setup:**

```yaml
# config/mcp_servers.yaml
mcp_servers:
  firecrawl:
    type: firecrawl
    api_key: ${FIRECRAWL_API_KEY}
    tools:
      - scrape
      - crawl
```

**Configuration:**
```python
# .env
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

**Critical Notes:**
- Respect **robots.txt** and rate limits when scraping
- Some sites block scrapers - handle 403/429 errors gracefully
- Consider adding **URL whitelist** for approved competitors only
- Cache analysis results (competitor content doesn't change that fast)

---

## Story 2.7: Identify Trends Skill

**Priority:** Medium  
**Size:** M (1-2 days)  
**Dependencies:** Story 2.5 (search-web skill)

### Task 2.7.1: Create Identify Trends Skill

**Files to Create:**
- `skills/identify-trends/SKILL.md` (new)
- `skills/identify-trends/identify_trends.py` (new)
- `skills/identify-trends/__init__.py` (new)
- `tests/skills/test_identify_trends.py` (new)

**Pattern Reference:** Combines search-web + LLM analysis

**Implementation Algorithm:**

1. Parse topic from user message
2. Call search-web skill multiple times with different queries
3. Aggregate results and use LLM to identify patterns/trends
4. Return structured trend analysis

**Function Signatures:**

```python
# skills/identify-trends/identify_trends.py
from src.core.interfaces import AgentState, SkillResponse
from skills.search_web import search_web

async def identify_trends(
    agent_state: AgentState,
    topic: str,
    time_range: str = "week"  # How far back to look
) -> SkillResponse:
    """Identify trending topics and patterns.
    
    Args:
        agent_state: Current agent state
        topic: Topic to research (e.g., "AI", "social media marketing")
        time_range: How far back to search ("day", "week", "month")
        
    Returns:
        SkillResponse with trend analysis
    """
    try:
        # Search multiple angles
        search_queries = _generate_search_queries(topic)
        
        # Aggregate search results
        all_results = []
        for query in search_queries:
            result = await search_web(agent_state, query, limit=10, recency=time_range)
            if result.success:
                all_results.extend(result.data["results"])
        
        # Analyze trends using LLM
        trends = await _analyze_trends(all_results, topic, agent_state.llm_client)
        
        return SkillResponse(
            success=True,
            message=f"Identified {len(trends['trending_topics'])} trends for '{topic}'",
            data={
                "topic": topic,
                "time_range": time_range,
                "trends": trends,
                "source_count": len(all_results)
            }
        )
    except Exception as e:
        return SkillResponse(
            success=False,
            message=f"Trend identification failed: {str(e)}",
            error={"code": "TREND_ANALYSIS_FAILED", "details": str(e)}
        )

def _generate_search_queries(topic: str) -> list[str]:
    """Generate diverse search queries for trend analysis."""
    return [
        f"{topic} trends 2026",
        f"latest {topic} news",
        f"what's new in {topic}",
        f"{topic} predictions",
        f"popular {topic} topics"
    ]

async def _analyze_trends(results: list[dict], topic: str, llm_client) -> dict:
    """Use LLM to identify patterns in search results."""
    results_text = "\n".join([
        f"- {r['title']}: {r['snippet']}"
        for r in results[:50]  # Limit to avoid token overflow
    ])
    
    prompt = f"""
    Based on these recent articles about {topic}, identify key trends:
    
    {results_text}
    
    Provide:
    1. Top 5 trending topics (with brief explanation)
    2. Emerging themes
    3. Popular keywords/hashtags
    4. Content opportunities (what's missing?)
    
    Format as JSON.
    """
    
    response = await llm_client.generate(prompt)
    return json.loads(response.text)
```

**SKILL.md Content:**

```markdown
---
name: identify-trends
description: Identify trending topics, keywords, and content opportunities in a given subject area by aggregating multiple web searches and analyzing patterns.
---

# identify-trends

Find what's trending in a topic area.

## When to invoke

User says:
- "what's trending in AI?"
- "identify trends in [topic]"
- "what should I write about for [topic]?"
- "find trending topics in [industry]"
```

**Test Cases**:
- `test_identify_trends_success()` - Valid topic → Returns trends
- `test_empty_search_results()` - No results → success=True, empty trends
- `test_llm_analysis_format()` - LLM returns valid JSON → Proper parsing
- `test_multiple_searches()` - Calls search-web 5 times → Aggregates correctly
- `test_trend_deduplication()` - Similar topics appear → Deduped in output

**Critical Notes:**
- This skill makes **multiple search-web calls** (5+) - watch API costs
- Consider caching trend analysis (trends don't change hourly)
- LLM prompt engineering is critical for quality trend identification
- May want to add **trend scoring** (how "hot" is each trend)

---

## Dependency Graph

```
Story 2.1 (Instagram) ─┐
Story 2.2 (TikTok)     ├─→ All depend on Story 1.4 (post-content structure)
Story 2.3 (LinkedIn)   │
Story 2.4 (Reddit)    ─┘

Story 2.5 (search-web) ──→ No dependencies
Story 2.6 (analyze-competitor) ──→ No dependencies
Story 2.7 (identify-trends) ──→ Depends on Story 2.5 (calls search-web)
```

**Recommended Implementation Order:**

1. **Week 1 (Days 1-3):** Stories 2.1-2.4 (All platform posting)
   - Can work on in parallel if desired (independent files)
   - Test each platform individually
   
2. **Week 1-2 (Days 4-5):** Story 2.5 (search-web)
   - Needed by story 2.7
   
3. **Week 2 (Days 6-7):** Stories 2.6-2.7 (Competitor analysis + Trends)
   - Can work in parallel

---

## Final Verification

**Functionality:**
- [ ] All 4 platforms (Instagram, TikTok, LinkedIn, Reddit) can post successfully
- [ ] Each platform respects character limits and media requirements
- [ ] Rate limiting handled gracefully with retry logic
- [ ] All 3 research skills (search-web, analyze-competitor, identify-trends) return valid results
- [ ] MCP integrations working (Perplexity, Firecrawl)

**Code Quality:**
- [ ] All platform modules follow BasePlatform interface
- [ ] Error handling consistent across all skills
- [ ] Proper logging for debugging
- [ ] Configuration properly externalized to .env
- [ ] No hardcoded credentials

**Testing:**
- [ ] Unit tests pass for all new modules
- [ ] Integration tests with real APIs (use sandbox accounts if available)
- [ ] Routing tests verify correct skill invocation
- [ ] Error scenarios properly tested

**Configuration:**
- [ ] All API keys added to .env template
- [ ] MCP servers configured in config/mcp_servers.yaml
- [ ] Documentation updated with setup instructions
- [ ] Platform account requirements documented

**Security:**
- [ ] No API keys in code
- [ ] OAuth tokens properly secured
- [ ] Rate limit respecting implemented
- [ ] Input validation for all user-provided URLs

---

## Post-Implementation Notes

After completing Sprint 2, you'll have:
- ✅ Full multi-platform posting (5 platforms)
- ✅ Web research capabilities (search + competitor analysis)
- ✅ Trend identification for content ideas

**Next Steps → Sprint 3:**
- Campaign planning (create-campaign skill)
- Scheduling system (schedule-campaign + cron)
- Batch approval workflows
