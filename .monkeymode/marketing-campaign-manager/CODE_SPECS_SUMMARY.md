# Code Specs Summary - Marketing Campaign Manager

**Generated:** 2026-02-12  
**Status:** All code specs complete and ready for implementation  
**Total Sprints:** 4  
**Total Stories:** 19 stories across 4 sprints

---

## Overview

This document provides a high-level summary of all code specifications created for the Marketing Campaign Manager. Each sprint has a detailed code spec document with implementation plans, test cases, and technical details.

---

## Sprint 1: Vertical Slice (MVP) ✅ COMPLETED

**Status:** Implementation complete  
**Code Spec:** `code_specs/sprint-1-complete.md`  
**Duration:** 5-7 days

### Stories Completed

| Story | Title | Size | Status |
|-------|-------|------|--------|
| 1.1 | Enhanced Skill Loader (Framework) | M | ✅ Done |
| 1.2 | Generate Post Skill | M | ✅ Done |
| 1.3 | Request Approval Skill | M | ✅ Done |
| 1.4 | Post Content Skill (X only) | M | ✅ Done |
| 1.5 | End-to-End Validation | S | ✅ Done |

### Key Deliverables

- ✅ Skill loader exposes SKILL.md descriptions to LLM for routing
- ✅ Generate social media content for any platform
- ✅ Request approval via Google Chat with interactive cards
- ✅ Post to X/Twitter successfully
- ✅ Complete end-to-end workflow: generate → approve → post

---

## Sprint 2: Platform Expansion & Research 📝 SPEC READY

**Status:** Code spec complete, ready for implementation  
**Code Spec:** `code_specs/sprint-2-platforms-research.md`  
**Duration:** 5-7 days

### Stories to Implement

| Story | Title | Size | Dependencies |
|-------|-------|------|--------------|
| 2.1 | Instagram Posting Support | M | Story 1.4 |
| 2.2 | TikTok Posting Support | M | Story 1.4 |
| 2.3 | LinkedIn Posting Support | M | Story 1.4 |
| 2.4 | Reddit Posting Support | M | Story 1.4 |
| 2.5 | Search Web Skill (Perplexity MCP) | M | None |
| 2.6 | Analyze Competitor Skill (Firecrawl MCP) | M | None |
| 2.7 | Identify Trends Skill | M | Story 2.5 |

### Key Deliverables

**Platform Expansion:**
- Instagram: 2-step posting (create container → publish)
- TikTok: Video-only posting with 3-step upload
- LinkedIn: Professional UGC posts
- Reddit: Subreddit-based posting with validation

**Research Skills:**
- Web search with Perplexity MCP (recency filters)
- Competitor analysis with Firecrawl MCP (web scraping)
- Trend identification (aggregates searches + LLM analysis)

### Technical Highlights

- All platforms follow `BasePlatform` interface pattern
- Rate limiting and retry logic for each platform
- MCP server integration for research capabilities
- OAuth configuration for each social platform

---

## Sprint 3: Campaign Planning & Scheduling 📝 SPEC READY

**Status:** Code spec complete, ready for implementation  
**Code Spec:** `code_specs/sprint-3-campaigns-scheduling.md`  
**Duration:** 5-7 days

### Stories to Implement

| Story | Title | Size | Dependencies |
|-------|-------|------|--------------|
| 3.1 | Create Campaign Skill | L | Story 2.5 |
| 3.2 | Schedule Campaign Skill | M | Stories 3.1, 3.3 |
| 3.3 | Cron Scheduler (Framework) | L | None |

### Key Deliverables

**Campaign Creation (Story 3.1):**
- Menu pattern implementation with 4 sub-steps
- Research topic → Define strategy → Generate calendar → Create post ideas
- Campaigns stored in `data/memory/campaigns/{id}/`
- LLM-powered strategy and content calendar generation

**Scheduling (Story 3.2):**
- Schedule all campaign posts for automatic posting
- Creates cron jobs for each post
- Updates campaign status to "scheduled"
- Tracks job IDs for future cancellation

**Cron Scheduler (Story 3.3):**
- Simple in-memory polling-based scheduler
- Check interval: 10 seconds (configurable)
- Automatic retry on failure (max 3 attempts)
- Job persistence across agent restarts
- Framework enhancement (lives in `core/scheduler/`)

### Technical Highlights

- Menu pattern with separate instruction files (`.md` files for LLM)
- Campaign structure: research → strategy → calendar → post ideas
- Scheduler executes `post_content` jobs by generating content + requesting approval
- Job types: `post_content`, `collect_metrics`, `send_weekly_report`

---

## Sprint 4: Production Polish & Deployment 📝 SPEC READY

**Status:** Code spec complete, ready for implementation  
**Code Spec:** `code_specs/sprint-4-production-polish.md`  
**Duration:** 3-5 days

### Stories to Implement

| Story | Title | Size | Dependencies |
|-------|-------|------|--------------|
| 4.1 | Deployment & Documentation | M | All sprints |
| 4.2 | Engagement Metrics Collection | M | Sprint 2 |

### Key Deliverables

**Deployment (Story 4.1):**
- `deploy.sh` - One-command deployment to GCP Cloud Run
- `Dockerfile` - Containerized application
- `SECRETS.md` - Complete secrets setup guide
- Health check endpoint (`/health`)
- GCP Secret Manager integration (no .env in production)
- Auto-scaling configuration (scale to zero)

**Metrics & Reporting (Story 4.2):**
- Daily metrics collection from all 5 platforms
- Engagement data: likes, comments, shares, impressions
- Weekly report generation (Monday 9am)
- Google Chat card-formatted reports
- Week-over-week growth calculations
- Scheduled via cron (automated)

### Technical Highlights

- Secrets via GCP Secret Manager (never in code)
- Structured JSON logging for Cloud Logging
- Graceful shutdown for scheduler
- Platform-specific metric collection (API-based)
- Post data storage for metrics (saved during posting)

---

## Implementation Roadmap

### Recommended Order

**Phase 1: Sprint 2 (Platform Expansion)**
- Days 1-3: Stories 2.1-2.4 (All platform posting)
- Days 4-5: Story 2.5 (search-web)
- Days 6-7: Stories 2.6-2.7 (Competitor analysis + Trends)

**Phase 2: Sprint 3 (Campaigns)**
- Days 1-2: Story 3.3 (Cron Scheduler - Framework)
- Days 3-5: Story 3.1 (Create Campaign)
- Days 6-7: Story 3.2 (Schedule Campaign)

**Phase 3: Sprint 4 (Production)**
- Days 1-2: Story 4.1 (Deployment)
- Days 3-4: Story 4.2 (Metrics)

**Total Estimated Time:** 18-26 days (solo developer)

---

## File Organization

```
monkey-bot/
├── .monkeymode/
│   └── marketing-campaign-manager/
│       ├── state.json                              # State tracking
│       ├── qa-log.md                               # Q&A log (if enabled)
│       ├── CODE_SPECS_SUMMARY.md                   # This file
│       ├── design/
│       │   ├── 1a-discovery.md                     # Design Phase 1A
│       │   ├── 1b-contracts.md                     # Design Phase 1B
│       │   └── 1c-operations.md                    # Design Phase 1C
│       ├── user_stories.md                         # All user stories
│       └── code_specs/
│           ├── sprint-1-complete.md                # Sprint 1 (DONE)
│           ├── sprint-2-platforms-research.md      # Sprint 2 (NEW)
│           ├── sprint-3-campaigns-scheduling.md    # Sprint 3 (NEW)
│           └── sprint-4-production-polish.md       # Sprint 4 (NEW)
```

---

## Key Decisions & Patterns

### Established Patterns (Sprint 1)

1. **Skill Structure:** SKILL.md + Python function, standardized SkillResponse
2. **Error Handling:** Custom exceptions, retry logic, structured error objects
3. **Testing:** Unit tests + integration tests + routing tests
4. **State Storage:** File-based in `data/memory/` directory
5. **Approval Workflow:** Google Chat cards with interactive buttons

### New Patterns (Sprints 2-4)

6. **Platform Interface:** `BasePlatform` abstract class, platform-specific implementations
7. **Menu Pattern:** Complex skills broken into sub-files (LLM instruction files)
8. **MCP Integration:** Wrapper skills calling MCP servers (Perplexity, Firecrawl)
9. **Job Scheduling:** Cron-based background jobs with persistence
10. **Metrics Collection:** Daily collection + weekly aggregation/reporting

---

## Testing Strategy

### Test Coverage Requirements

**Unit Tests:**
- Each skill function
- Each platform module
- Scheduler job execution
- Metrics collection scripts

**Integration Tests:**
- End-to-end workflows (generate → approve → post)
- Campaign creation → scheduling → execution
- Multi-platform posting
- Metrics collection → report generation

**Routing Tests:**
- LLM correctly routes to skills based on SKILL.md descriptions
- Parameter extraction accuracy
- Error handling in routing

### Test Commands

```bash
# Run all tests
pytest tests/

# Run specific sprint tests
pytest tests/skills/test_generate_post.py
pytest tests/skills/test_create_campaign.py
pytest tests/core/test_cron_scheduler.py

# Run with coverage
pytest --cov=skills --cov=core --cov-report=html
```

---

## Configuration Requirements

### Environment Variables (Development)

```bash
# .env (local development only)
GOOGLE_CHAT_WEBHOOK=...
X_API_KEY=...
X_API_SECRET=...
INSTAGRAM_USER_ID=...
INSTAGRAM_ACCESS_TOKEN=...
TIKTOK_ACCESS_TOKEN=...
LINKEDIN_ACCESS_TOKEN=...
REDDIT_ACCESS_TOKEN=...
PERPLEXITY_API_KEY=...
FIRECRAWL_API_KEY=...
```

### GCP Secrets (Production)

All secrets stored in GCP Secret Manager:
- `google-chat-webhook`
- `x-api-key`, `x-api-secret`, `x-access-token`, `x-access-token-secret`
- `instagram-user-id`, `instagram-access-token`
- `tiktok-access-token`
- `linkedin-access-token`, `linkedin-person-urn`
- `reddit-access-token`
- `perplexity-api-key`
- `firecrawl-api-key`

Setup instructions in `SECRETS.md` (created in Sprint 4).

---

## Dependencies

### Python Packages

```
# Core framework
langgraph>=0.2.0
langchain>=0.3.0
google-cloud-aiplatform>=1.70.0
pydantic>=2.0.0

# HTTP & APIs
httpx>=0.27.0
requests>=2.32.0

# Google Cloud
google-cloud-pubsub>=2.20.0
google-cloud-secretmanager>=2.20.0
google-cloud-logging>=3.10.0

# Social platforms (official SDKs where available)
tweepy>=4.14.0  # X/Twitter
facebook-sdk>=3.1.0  # Instagram via Graph API

# MCP integration
mcp>=1.0.0  # Model Context Protocol client

# Utilities
python-dotenv>=1.0.0
PyYAML>=6.0.0
```

### External Services

- **GCP Project:** Cloud Run, Secret Manager, Cloud Logging
- **Social Platform Accounts:** X, Instagram (Business), TikTok, LinkedIn, Reddit
- **MCP Servers:** Perplexity API, Firecrawl API
- **Google Chat:** Webhook for bot communication

---

## Success Metrics

### MVP Success Criteria (After Sprint 1)

- ✅ Agent successfully generates posts for X
- ✅ Approval workflow functional
- ✅ Posts successfully to X/Twitter
- ✅ End-to-end workflow takes < 5 minutes (including approval)

### Full System Success Criteria (After Sprint 4)

- [ ] Posts successfully to all 5 platforms (X, Instagram, TikTok, LinkedIn, Reddit)
- [ ] Multi-week campaigns can be planned and scheduled
- [ ] Scheduled posts execute automatically at correct times
- [ ] Engagement metrics collected daily from all platforms
- [ ] Weekly reports sent to Google Chat every Monday
- [ ] System deployed to GCP Cloud Run and running stably
- [ ] Zero manual posting required (100% automation after approval)

### Business Metrics

- **Automation Rate:** 100% (all posts scheduled and posted automatically)
- **Time Savings:** 80% reduction (from ~5 hours/week to ~1 hour for approvals)
- **Post Volume:** 10-25 posts/week across 5 platforms
- **Engagement Growth:** Track week-over-week (baseline TBD after Sprint 4)

---

## Risk Mitigation

### Known Risks

1. **API Rate Limits:** Each platform has different limits
   - Mitigation: Retry logic, exponential backoff, respect rate limits
   
2. **OAuth Token Expiry:** Tokens need periodic refresh
   - Mitigation: Document refresh process, monitor expiry dates
   
3. **Scheduler Failures:** Jobs might fail to execute
   - Mitigation: Automatic retry (3 attempts), error notifications
   
4. **Content Quality:** LLM might generate off-brand content
   - Mitigation: Approval workflow (human review), brand voice validation
   
5. **Platform Policy Changes:** Social platforms update APIs frequently
   - Mitigation: Version pinning, monitoring for breaking changes

---

## Next Steps

### Immediate Actions (Choose One Story to Start)

**Option 1: Continue Sprint 2 (Platform Expansion)**
- Start with Story 2.1 (Instagram) - Most similar to X (reference implementation)
- Then 2.2-2.4 (other platforms)
- Then 2.5-2.7 (research skills)

**Option 2: Jump to Sprint 3 (Campaigns)**
- Start with Story 3.3 (Cron Scheduler - Framework)
- Critical foundation for scheduling features
- Can test independently before campaign integration

**Option 3: Jump to Sprint 4 (Deployment)**
- Start with Story 4.1 (Deployment)
- Get production environment set up early
- Can deploy Sprint 1 features while building Sprint 2-3

### Recommended: Option 1 (Sequential Implementation)

Reason: Builds on existing X posting pattern, validates multi-platform approach before adding complexity of campaigns and scheduling.

---

## Questions or Clarifications?

If you need any clarification on a specific story or technical detail:

1. **Read the detailed code spec** for that sprint (in `code_specs/` folder)
2. **Check the design docs** for architectural context (in `design/` folder)
3. **Review user stories** for acceptance criteria (in `user_stories.md`)

Each code spec includes:
- Complete function signatures
- Implementation algorithms
- API integration details
- Test cases and examples
- Critical gotchas and notes

Ready to implement! 🚀
