# Design: Marketing Campaign Manager - Phase 1C: Production Readiness

**Date:** 2026-02-11  
**Status:** Phase 1C - Production Readiness  
**Author:** MonkeyMode Agent

---

## Executive Summary

This document defines the operational requirements for deploying the Marketing Campaign Manager agent to production. The approach prioritizes **pragmatic MVP deployment** with:

- **Simple security** using GCP service accounts and Secret Manager
- **Async-first performance** for responsive user experience
- **Manual deployment** with an easy-to-use script
- **Essential logging** focused on actionable insights
- **Engagement-driven metrics** aligned with business goals

**Philosophy:** Launch fast, measure engagement, iterate based on real usage. Avoid over-engineering for problems we don't have yet.

---

## Table of Contents

1. [Security Design](#security-design)
2. [Performance & Scalability](#performance--scalability)
3. [Deployment Strategy](#deployment-strategy)
4. [Observability](#observability)
5. [Risk Assessment](#risk-assessment)
6. [Final Sign-Off](#final-sign-off)

---

## Security Design

### Authentication

#### Google Chat Authentication
```python
# Service Account Credentials
- Use GCP Service Account with Google Chat API permissions
- Credentials stored in GCP Secret Manager: `marketing-bot-service-account`
- Agent authenticates via service account JSON key
- No OAuth flow needed (bot-to-API communication only)
```

**Implementation:**
```python
# Load service account from Secret Manager
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
secret_name = "projects/PROJECT_ID/secrets/marketing-bot-service-account/versions/latest"
response = client.access_secret_version(request={"name": secret_name})
credentials = json.loads(response.payload.data.decode("UTF-8"))
```

#### Social Media API Authentication
All social media API keys stored in GCP Secret Manager:

| Platform | Secret Name | Rotation Policy |
|----------|-------------|-----------------|
| Instagram | `instagram-api-token` | Manual (on breach) |
| TikTok | `tiktok-api-token` | Manual (on breach) |
| Reddit | `reddit-api-credentials` | Manual (on breach) |
| LinkedIn | `linkedin-api-token` | Manual (on breach) |
| X (Twitter) | `x-api-credentials` | Manual (on breach) |

**Why manual rotation?** Low risk profile (organic posting only, no financial data), small team, no compliance requirements. If breached, manually rotate and redeploy.

### Authorization

#### User Access Control
```python
# Domain-based restriction
ALLOWED_DOMAIN = "@ez-ai.io"

def is_authorized_user(user_email: str) -> bool:
    """Only ez-ai.io domain users can invoke the agent"""
    return user_email.endswith(ALLOWED_DOMAIN)
```

**Access Levels:**
- **All @ez-ai.io users:** Can invoke agent, create campaigns, research, generate posts, approve/reject
- **No admin commands:** Everyone has equal permissions (MVP simplicity)
- **Future enhancement:** Role-based access control if team grows

#### Approval Workflow Security (MVP)
```python
# Simple approval pattern
- Anyone with @ez-ai.io email can approve/reject posts
- No time limits on approval requests (will add later if needed)
- No audit trail of who approved (will add later for learning system)
```

### Input Validation

#### User Input Validation
```python
# Campaign creation
- Campaign topic: Max 500 chars, alphanumeric + spaces
- Platform selection: Must be in ["instagram", "tiktok", "reddit", "linkedin", "x"]
- Target audience: Max 200 chars

# Research queries
- Query string: Max 1000 chars
- URL validation: Must be valid HTTP/HTTPS format

# Post content
- Validated by platform-specific limits (handled in 1b-contracts.md)
```

#### Rate Limiting (Lightweight)
```python
# Per-user limits (prevent accidental spam)
MAX_RESEARCH_REQUESTS_PER_HOUR = 20
MAX_POST_GENERATIONS_PER_DAY = 50

# Implementation: In-memory dict (sufficient for 2-3 users)
user_rate_limits = {}  # {user_id: {action: [(timestamp, count), ...]}}
```

### Data Protection

#### Secrets Management
```bash
# Store all secrets in GCP Secret Manager
gcloud secrets create marketing-bot-service-account \
  --replication-policy="automatic" \
  --data-file="service-account.json"

gcloud secrets create instagram-api-token \
  --replication-policy="automatic"
echo "YOUR_TOKEN" | gcloud secrets versions add instagram-api-token --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding marketing-bot-service-account \
  --member="serviceAccount:marketing-bot@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Data Storage Security
```python
# Memory storage (./data/memory/)
- Campaign configs: Plain JSON (no sensitive data)
- Research results: Plain text/JSON (public web data)
- Approved posts: Plain JSON (public content)
- No PII, no financial data, no auth tokens in memory

# Git security
- Add secrets/ to .gitignore
- Add data/memory/ to .gitignore (contains API responses)
- Never commit .env files
```

#### Environment Variables
```bash
# .env.production (never committed)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GCP_PROJECT_ID=auriga-prod
GOOGLE_CHAT_SPACE_ID=spaces/AAAA
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Security Headers (Cloud Run)

Cloud Run handles TLS automatically. No additional headers needed for bot-to-API communication.

---

## Performance & Scalability

### Expected Load (MVP)

```
Users: 2-3 team members
Requests per day: ~10-20 agent invocations
Research operations: ~5-10/day
Post generations: ~10-25/week
Approval requests: ~10-25/week
Peak load: None (async processing handles spikes)
```

**Conclusion:** Performance is not a bottleneck. Focus on **responsiveness** (fast initial reply) and **reliability** (complete background work).

### Performance Targets

| Metric | Target | Why |
|--------|--------|-----|
| Initial response time | < 2 seconds | User shouldn't wait for "thinking..." |
| Research completion | < 60 seconds | Acceptable for background work |
| Post generation | < 30 seconds | Acceptable for background work |
| Scheduling operation | < 5 seconds | Fast operation (just write to memory) |
| Approval notification | < 2 seconds | Send card and return |

### Async-First Architecture

**Pattern: Respond Fast, Work in Background, Notify on Completion**

```python
# Example: Research workflow
async def research_audience(agent_state, topic):
    # 1. Immediately respond to user
    await send_message(agent_state.space_id, 
        "🔍 Researching audience for '{topic}'... I'll update you when done!")
    
    # 2. Do expensive work in background
    research_results = await perform_research(topic)  # Takes 30-60s
    
    # 3. Notify user when complete
    await send_message(agent_state.space_id, 
        f"✅ Research complete! Found {len(research_results.insights)} insights.\n\n"
        f"Top insight: {research_results.insights[0]}")
    
    return SkillResponse(success=True, ...)
```

**Implementation Strategy:**
```python
# Use Python asyncio for concurrent operations
import asyncio

# Pattern 1: Fast acknowledgment + background work
@skill
async def create_post(agent_state, platform, topic):
    # Acknowledge immediately
    await quick_reply(agent_state, "Creating post...")
    
    # Background: Research + Generate + Format (30s total)
    results = await asyncio.gather(
        research_topic(topic),
        research_audience(platform),
        get_brand_voice()
    )
    post = await generate_post(results)
    
    # Notify completion
    await send_post_preview(agent_state, post)

# Pattern 2: Parallel operations
async def create_campaign(platforms):
    # Generate all posts concurrently
    posts = await asyncio.gather(*[
        create_post(platform, topic) for platform in platforms
    ])
```

### Optimization Strategy

#### Minimal Optimizations (MVP)
```python
# 1. Cache brand voice (loaded once per session)
_brand_voice_cache = None

def get_brand_voice():
    global _brand_voice_cache
    if _brand_voice_cache is None:
        _brand_voice_cache = load_brand_voice()
    return _brand_voice_cache

# 2. Reuse HTTP sessions (connection pooling)
import httpx
client = httpx.AsyncClient()  # Reuse across requests

# 3. Batch social media API calls when possible
# (e.g., schedule 5 posts in one API call if supported)
```

**What NOT to optimize yet:**
- ❌ Database caching (no database, just file storage)
- ❌ Redis/Memcache (overkill for 3 users)
- ❌ CDN (no static assets)
- ❌ Load balancing (single Cloud Run instance handles load easily)

### Scalability Plan

**Current Approach:** Single Cloud Run instance with 1 vCPU, 512MB RAM

```yaml
# Cloud Run config
resources:
  limits:
    cpu: "1"
    memory: 512Mi
autoscaling:
  minInstances: 0  # Scale to zero when idle (save costs)
  maxInstances: 1  # Only need one instance for MVP
  concurrency: 10  # Handle 10 concurrent requests (plenty for 3 users)
```

**When to scale:** If team grows to 10+ users or handling 100+ posts/week, then:
1. Increase max instances to 2-3
2. Increase memory to 1GB (for larger research results)
3. Add Redis for shared state (campaign memory)

**Bottleneck Analysis:**
- **Not CPU:** LLM calls are rate-limited by Gemini API, not local CPU
- **Not Memory:** Small JSON files, no large media processing
- **Not Network:** Social APIs are rate-limited, not bandwidth-constrained
- **Actual bottleneck:** Gemini API rate limits (500 requests/minute - way above our needs)

---

## Deployment Strategy

### Rollout Approach

**Chosen: Manual Deployment with Simple Script**

```bash
# deploy.sh - Simple deployment script
#!/bin/bash
set -e  # Exit on error

PROJECT_ID="auriga-prod"
REGION="us-central1"
SERVICE_NAME="marketing-campaign-manager"

echo "🚀 Deploying Marketing Campaign Manager to Cloud Run..."

# Step 1: Build container
echo "📦 Building container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Step 2: Deploy to Cloud Run
echo "☁️  Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --service-account marketing-bot@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production,LOG_LEVEL=INFO" \
  --set-secrets "GOOGLE_APPLICATION_CREDENTIALS=marketing-bot-service-account:latest" \
  --min-instances 0 \
  --max-instances 1 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300

# Step 3: Verify deployment
echo "✅ Deployment complete!"
echo "🔗 Service URL:"
gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'

echo ""
echo "🧪 Test the deployment:"
echo "1. Open Google Chat"
echo "2. Send message to bot: 'Hello!'"
echo "3. Verify bot responds within 2 seconds"
```

**Usage:**
```bash
cd /Users/johnpiscani/ez-ai/auriga/automation/monkey-bot
chmod +x deploy.sh
./deploy.sh
```

### Deployment Pipeline (Manual)

```
Code Changes → Git Commit → Run ./deploy.sh → Verify in Google Chat
```

**Pre-deployment Checklist:**
```bash
# Before running deploy.sh
- [ ] All tests passing locally: python -m pytest
- [ ] Secrets exist in Secret Manager: gcloud secrets list
- [ ] Service account has permissions
- [ ] .env.production file exists (not committed)
- [ ] No hardcoded credentials in code
```

### Health Checks (Built-in)

Cloud Run provides automatic health checks. No custom endpoint needed for MVP.

**Manual Health Check:**
```bash
# After deployment, test basic functionality
curl -X POST https://YOUR_CLOUD_RUN_URL/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"MESSAGE","message":{"text":"ping"}}'

# Expected: Bot responds with "pong" or similar
```

### Rollback Plan (Simple)

**If deployment breaks:**
```bash
# Option 1: Redeploy previous commit
git checkout HEAD~1  # Go back one commit
./deploy.sh

# Option 2: Quick fix
# Fix the bug, commit, redeploy
git commit -am "Fix critical bug"
./deploy.sh
```

**No complex rollback needed because:**
- No database migrations (just file storage)
- No traffic splitting
- Small user base (3 people can tolerate 5-min downtime)

### Post-Deployment Verification

```bash
# Checklist after running deploy.sh
- [ ] Bot responds to "Hello" in Google Chat
- [ ] Create a test campaign: "Create a campaign about AI"
- [ ] Generate test post: "Create an Instagram post about AI agents"
- [ ] Check logs: gcloud run logs read --service marketing-campaign-manager --limit 50
- [ ] No error messages in last 10 log entries
```

---

## Observability

### Logging Strategy

**Goal: Only log what you'll actually read. Avoid noise.**

#### Log Levels (Production)
```python
# Use INFO level in production (not DEBUG)
LOG_LEVEL = "INFO"

# Log only these events:
INFO:  Skill invocations, completions, social API posts
WARN:  Retries, degraded functionality, slow operations
ERROR: Failures requiring attention
```

#### What to Log

```python
# ✅ DO log these
logger.info("Skill invoked", extra={
    "skill": "research-audience",
    "user_id": user_id,
    "params": {"topic": "AI agents"}
})

logger.info("Post scheduled", extra={
    "platform": "instagram",
    "scheduled_time": "2024-02-15T10:00:00Z",
    "campaign_id": "campaign_123"
})

logger.error("Social API failed", extra={
    "platform": "instagram",
    "error": str(e),
    "retry_attempt": 2
})

# ❌ DON'T log these
# - Every function call (too noisy)
# - Full LLM responses (expensive, clutters logs)
# - User message content (privacy concern)
# - Successful API calls (too much noise)
```

#### Structured Logging (JSON)

```python
import structlog
import google.cloud.logging

# Configure structured logging for GCP
client = google.cloud.logging.Client()
client.setup_logging()

logger = structlog.get_logger()

# Usage
logger.info("research_completed", 
    user_id=user_id,
    topic=topic,
    insights_found=len(results),
    duration_seconds=elapsed_time
)
```

**GCP Cloud Logging Query Examples:**
```sql
-- View all errors in last hour
severity="ERROR"
timestamp >= timestamp_sub(timestamp_now(), interval 1 hour)

-- View posts scheduled today
jsonPayload.event="post_scheduled"
timestamp >= timestamp_trunc(timestamp_now(), DAY)

-- View slow operations (> 60s)
jsonPayload.duration_seconds > 60
```

### Metrics (Engagement-Focused)

**Primary KPI: Engagement Growth**

Track these metrics in `./data/metrics/engagement.json`:

```json
{
  "week": "2024-02-11",
  "platforms": {
    "instagram": {
      "posts_published": 5,
      "total_likes": 1250,
      "total_comments": 45,
      "total_shares": 12,
      "avg_engagement_rate": 3.2,
      "follower_count": 10500
    },
    "tiktok": { ... },
    "reddit": { ... },
    "linkedin": { ... },
    "x": { ... }
  },
  "overall": {
    "total_posts": 25,
    "total_engagement": 5000,
    "engagement_growth_pct": 15.2  // Compared to last week
  }
}
```

**How to Collect:**
```python
# Weekly cron job (manual for MVP, automate later)
# Run: python scripts/collect_metrics.py

async def collect_engagement_metrics():
    """Fetch engagement stats from each platform's API"""
    for platform in ["instagram", "tiktok", "reddit", "linkedin", "x"]:
        stats = await fetch_platform_stats(platform)
        save_to_metrics_file(platform, stats)
    
    calculate_growth_rate()
    send_weekly_report_to_chat()
```

**Weekly Report (Sent to Google Chat):**
```
📊 **Weekly Engagement Report** (Feb 5-11, 2024)

📈 Engagement Growth: +15.2% (vs last week)

Platform Breakdown:
• Instagram: 1,250 likes, 45 comments (↑ 12%)
• TikTok: 890 views, 67 likes (↑ 8%)
• Reddit: 234 upvotes, 28 comments (↑ 20%)
• LinkedIn: 150 reactions, 12 comments (↑ 5%)
• X: 567 impressions, 45 retweets (↑ 18%)

🏆 Top Post: "AI agents revolutionize workflow" (Instagram, 450 likes)

💡 Insight: Reddit posts perform 20% better - create more Reddit content!
```

### Alerting (Minimal)

**Google Chat Notifications (Simple Alerting)**

```python
# Alert on critical failures only
async def alert_if_critical(error, context):
    """Send Google Chat alert for critical errors"""
    if error.severity == "CRITICAL":
        await send_chat_message(
            space_id=ADMIN_SPACE_ID,
            message=f"🚨 CRITICAL: {error.message}\n\n"
                    f"Context: {context}\n"
                    f"Time: {datetime.now()}\n"
                    f"Fix: Check logs at https://console.cloud.google.com/logs"
        )

# Examples of critical errors:
# - Google Chat API unreachable (can't receive messages)
# - Secret Manager unavailable (can't load credentials)
# - All social APIs failing (systemic issue)
```

**Alert Conditions:**
| Condition | Severity | Action |
|-----------|----------|--------|
| Google Chat API down | CRITICAL | Send email to admin |
| Social API quota exceeded | WARN | Log warning, retry later |
| Post scheduling failed | ERROR | Notify in chat with retry button |
| Research timeout (> 2min) | WARN | Log warning, return partial results |

### Dashboards (Optional for MVP)

**Simple CSV Export (for analysis in Google Sheets):**

```python
# Export metrics to CSV for manual analysis
# Run: python scripts/export_metrics.py

def export_metrics_to_csv():
    """Export engagement metrics to CSV"""
    df = pd.DataFrame(load_all_metrics())
    df.to_csv("./data/metrics/engagement_history.csv")
    print("Exported to engagement_history.csv")
    print("Open in Google Sheets for visualization")
```

**Manual Dashboard (Google Sheets):**
1. Upload `engagement_history.csv` to Google Sheets
2. Create charts: Line chart (engagement over time), Bar chart (platform comparison)
3. Share with team

**Future Enhancement:** Auto-sync CSV to Google Sheets via API (if team wants live dashboard)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| **Social API rate limit exceeded** | Medium | Medium | Implement retry with exponential backoff (5s, 10s, 30s). Log warning and notify user. | Backend |
| **Gemini API quota exceeded** | Low | High | Use `safety_settings` to avoid blocked responses. Monitor quota in GCP console. Upgrade to paid tier if needed. | Backend |
| **Google Chat webhook fails** | Low | Critical | Implement health check endpoint. Alert via email if bot unreachable for > 5 min. | Backend |
| **Secrets accidentally committed to git** | Low | Critical | Use `.gitignore` for secrets/, data/memory/, .env*. Pre-commit hook to scan for secrets. | DevOps |
| **Post content violates platform guidelines** | Medium | Medium | Implement content validation (no hate speech, spam, etc.). Human approval required before posting. | Content |
| **Approved post fails to publish** | Medium | Medium | Retry 3 times with 10s delay. Log error. Notify user with "Failed to post, retry manually?" button. | Backend |
| **Memory storage fills disk** | Low | Low | Implement cleanup: Delete campaigns older than 90 days. Archive approved posts to GCS. | Backend |
| **User inputs malicious prompt** | Low | Low | All content is generated by Gemini (safe). No shell command execution. No SQL queries. Low risk. | Security |

### Risk Monitoring

```python
# Weekly risk review (manual checklist)
- [ ] Check GCP quota usage (Gemini API, Cloud Run, Secret Manager)
- [ ] Review error logs for recurring issues
- [ ] Check disk usage: du -sh ./data/memory/
- [ ] Verify social API credentials still valid (test API call)
- [ ] Review engagement metrics for anomalies (sudden drop = API issue?)
```

### Incident Response Runbook

```markdown
## If Bot Stops Responding

1. Check Cloud Run status: gcloud run services describe marketing-campaign-manager
2. Check recent logs: gcloud run logs read --service marketing-campaign-manager --limit 100
3. Check Google Chat API status: https://www.google.com/appsstatus
4. If Cloud Run crashed: Redeploy with ./deploy.sh
5. If API key expired: Rotate secret in Secret Manager, redeploy

## If Posts Fail to Publish

1. Check platform API status (Instagram, TikTok, Reddit, LinkedIn, X status pages)
2. Check API credentials: Test with curl (see 1b-contracts.md for examples)
3. Check rate limits: Review API response headers
4. Retry manually if transient failure

## If Costs Spike

1. Check GCP billing dashboard
2. Check Gemini API usage (likely culprit if high)
3. Check Cloud Run request count (should be < 100/day)
4. If Gemini usage high: Reduce context window size, optimize prompts
```

---

## Final Sign-Off

### Production Readiness Checklist

**Security:**
- [x] Service account credentials in Secret Manager
- [x] Domain restriction (@ez-ai.io only)
- [x] Social API keys in Secret Manager
- [x] No secrets in git repository
- [x] .gitignore configured

**Performance:**
- [x] Async-first pattern (respond fast, work in background)
- [x] Performance targets defined (< 2s response, < 60s research)
- [x] Brand voice caching implemented
- [x] HTTP session reuse (connection pooling)

**Deployment:**
- [x] Simple deployment script (./deploy.sh)
- [x] Cloud Run configuration defined
- [x] Pre-deployment checklist documented
- [x] Post-deployment verification steps

**Observability:**
- [x] GCP Cloud Logging configured
- [x] Structured logging (JSON format)
- [x] Engagement metrics tracking (engagement.json)
- [x] Weekly report automation (Python script)
- [x] Critical error alerting (Google Chat)

**Risk Management:**
- [x] Top 8 risks identified with mitigations
- [x] Incident response runbook documented
- [x] Weekly risk review checklist

### Approval

**Design Phase Complete:** All 3 sub-phases done (1a, 1b, 1c)

**Ready for Phase 2 (User Stories)?**
- Architecture: Skill-based agent with LangGraph + Gemini ✓
- Contracts: Skill invocation, integration points, testing ✓
- Operations: Security, performance, deployment, observability ✓

**Estimated Implementation Time:** 2-3 weeks (3 developers working in parallel on Sprint 1 stories)

---

## Appendix: Quick Reference

### Useful Commands

```bash
# Deploy
./deploy.sh

# View logs
gcloud run logs read --service marketing-campaign-manager --limit 50

# Check secrets
gcloud secrets list

# Test bot locally
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
python main.py

# Export metrics
python scripts/export_metrics.py

# Check disk usage
du -sh ./data/memory/

# Manual health check
curl -X POST https://YOUR_URL/webhook -d '{"type":"MESSAGE","message":{"text":"ping"}}'
```

### Environment Variables

```bash
# .env.production
GOOGLE_APPLICATION_CREDENTIALS=/secrets/service-account.json
GCP_PROJECT_ID=auriga-prod
GOOGLE_CHAT_SPACE_ID=spaces/AAAA
LOG_LEVEL=INFO
ENVIRONMENT=production
```

### Key File Locations

```
/monkey-bot/
├── deploy.sh                 # Deployment script
├── main.py                   # Bot entry point
├── skills/                   # Marketing skills (SKILL.md files)
├── data/
│   ├── memory/              # Campaign state, approved posts
│   └── metrics/             # engagement.json, engagement_history.csv
├── scripts/
│   ├── collect_metrics.py   # Weekly metrics collection
│   └── export_metrics.py    # Export to CSV
└── .env.production          # Environment variables (not committed)
```

---

**Phase 1C Complete!** 🎉

Ready to move to **Phase 2: User Stories**?
