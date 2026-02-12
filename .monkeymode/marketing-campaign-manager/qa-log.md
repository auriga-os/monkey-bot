# Q&A Log: Marketing Campaign Manager

## Branch Setup
**Date:** 2026-02-11T08:00:00Z

### Q: Would you like me to save a log of all our questions and answers during this process?
**A:** Yes (Option 1)

### Q: Which branch are you working on for this feature?
**A:** feature/marketing-campaign

### Q: Which repositories will this feature touch?
**A:** monkey-bot only (open source repo, will deploy as specialized marketing agent to GCP)

### Q: Would you like to sync your branch with main before starting?
**A:** Yes (Option 1)

**Branch Setup Result:**
- Created branch `feature/marketing-campaign` from `main`
- No open PRs found
- Branch synced successfully
- Pushed to origin

---

## Phase 1A: Discovery & Core Design
**Date:** 2026-02-11T08:00:00Z

### Q: Who will use this marketing agent?
**A:** Team at Auriga OS, maybe packaged for other users eventually

### Q: Which social media platforms to prioritize?
**A:** Instagram and TikTok (most important), Reddit, LinkedIn, X

### Q: Expected posting volume?
**A:** 2-5 posts per platform per week, ~5 campaigns running simultaneously

### Q: Success metrics?
**A:** Full automation, raising engagement metrics over time, increasing users and awareness

### Q: Do you have API keys for MCP servers (Perplexity, Playwright, Firecrawl)?
**A:** Can get API keys. Need to confirm monkey-bot supports env vars for skills

### Q: Do you have brand voice guidelines?
**A:** May need to research and define. Agent should ask and figure it out, then refer if available

### Q: Deployment model?
**A:** On-demand via Google Chat + autonomous cron jobs (monkey-bot should handle this)

### Q: Campaign approval workflow?
**A:** Google Chat approval - must see every post before it's made (scheduled or real-time)

### Q: Where should private marketing implementation live?
**A:** Option A - Separate private repo (auriga-marketing-bot) that uses public monkey-bot as dependency. Marketing skills, brand voice, and config must stay 100% private.

### Architecture Design Discussion

**Chosen Approach:** Two-Repo Extension Pattern
- **Public Repo (monkey-bot):** Framework enhancements (MCP layer, approval interface, cron scheduler, brand voice validator)
- **Private Repo (auriga-marketing-bot):** Marketing skills, brand voice, API keys, campaign data

**Key Benefits:**
1. Clean separation of public/private code
2. Can contribute framework improvements to open source
3. Marketing implementation stays 100% private
4. Easy to package for other users (copy private repo pattern)

**Framework Enhancements Needed:**
1. MCP Integration Layer (generic)
2. Approval Workflow System (abstract interface)
3. Cron Scheduler (job scheduling)
4. Enhanced Skill Loader (env var support)
5. Brand Voice Validator (generic, configurable)

**Private Implementation:**
1. Research skills (Perplexity, Firecrawl, Playwright wrappers)
2. Campaign skills (planning, generation, scheduling)
3. Posting skills (Instagram, TikTok, Reddit, LinkedIn, X)
4. Approval skills (Google Chat approval UI)
5. Brand voice document (Auriga-specific)

### Design Review Feedback

**Key Issues Identified:**
1. SKILL.md files were placeholders - need actual triggering descriptions NOW
2. Skill granularity problems:
   - Research skills too coarse (should split: search_web, analyze_competitor, identify_trends)
   - Posting skills too fine (should merge: one post_content skill with platform param)
3. Missing "menu" pattern for large skills
4. No success criteria in skill designs
5. Need to validate Gemini routing with SKILL.md descriptions
6. Framework enhancements over-scoped - should build vertical slice first

**Corrective Actions:**
- Redesign skill structure with proper granularity
- Write actual SKILL.md descriptions with triggering language
- Add inline success criteria to each skill
- Prioritize vertical slice (generate → approve → post) before framework abstractions
- Move framework changes to docs/phases/phase-2-marketing-campaign.md

### Design Updates Applied

**Phase 2 Doc (`docs/phases/phase-2-marketing-campaign.md`):**
- Added vertical slice first approach
- Added critical skill loader enhancement (expose descriptions to LLM)
- Added proper skill granularity rules
- Added SKILL.md format examples with triggering descriptions
- Added menu pattern for large skills
- Added testing strategy (routing tests!)
- Added implementation phases

**1A Discovery Doc (`.monkeymode/marketing-campaign-manager/design/1a-discovery.md`):**
- Corrected skill structure (merge posting, split research)
- Added 5 detailed SKILL.md designs with triggering descriptions
- Added success criteria to each skill
- Added vertical slice approach
- Added testing strategy focused on routing validation
- Moved framework details to phase-2 doc

---

## Phase 1B: Detailed Contracts
**Date:** 2026-02-11T14:00:00Z

### Q: Is any part of Phase 1B overkill for MVP?
**A:** Yes - identified 5 areas of overkill:
1. Internal event system (definitely overkill - moved to post-MVP)
2. Load testing specs (overkill - volume is ~1-2 interactions/hour)
3. Detailed social API contracts (overkill - simplified to reference official docs + key requirements)
4. Circuit breakers (probably overkill - documented but use simple retry for MVP)
5. Contract testing (probably overkill - integration tests sufficient)

**Actions Taken:**
1. Internal event system → Moved to post-MVP enhancements
2. Load testing → Removed (volume too low to justify)
3. Social API contracts → Simplified (use SDKs, link to official docs, note key requirements only)
4. Circuit breakers → Documented pattern but implement simple retry logic for MVP
5. Contract testing → Removed (integration tests will catch issues)

### Q: Phase 1B simplified and complete! Ready for Phase 1C (Production Readiness)?
**A:** Yes, proceed to Phase 1C

**Phase 1B Outputs:**
- ✅ Skill invocation contracts defined (standardized SkillResponse format)
- ✅ All 6 skills documented with parameters and response schemas
- ✅ Error handling strategy standardized (5 common error patterns)
- ✅ Integration contracts specified:
  - MCP servers: Perplexity, Firecrawl, Playwright (with timeouts, retries, circuit breakers)
  - Social APIs: Instagram, TikTok, X, LinkedIn, Reddit (with rate limits, error codes)
  - Google Chat: Approval card UI format defined
- ✅ Internal event system designed (6 event types for workflow orchestration)
- ✅ Testing strategy complete (routing tests prioritized!)
- ✅ Circuit breaker and retry policies specified
- ✅ Platform-specific requirements documented
- ✅ Security test cases defined

**Key Decisions:**
- Standardized SkillResponse format across all skills
- Google Chat card UI for approval workflow
- Circuit breaker thresholds: 5-10 failures trigger open circuit
- Retry policy: 3 attempts with exponential backoff + jitter
- Routing tests are CRITICAL - must validate Gemini skill selection

**Document Location:** `.monkeymode/marketing-campaign-manager/design/1b-contracts.md`

---

## Phase 1C: Production Readiness
**Date:** 2026-02-11T16:30:00Z

### Security & Authentication

#### Q: How will the agent authenticate with Google Chat? Who can invoke it?
**A:** 
- Service account credentials
- Only users with @ez-ai.io domain
- No admin-only commands for now

#### Q: Where will you store API keys for social media platforms? Rotation policy?
**A:** 
- GCP Secret Manager
- Manual rotation (no automated rotation for MVP)

#### Q: Should approval workflow have time limits, specific approvers, audit trail?
**A:** 
- Don't overkill it
- Anyone can approve for now
- Maybe add later if necessary

### Performance & Scale

#### Q: How many users will invoke the agent? Max posts per day during launch?
**A:** 
- Maybe 2-3 people invoking agent
- Won't be too much load

#### Q: How long should you wait for research/generation? Show progress?
**A:** 
- Shouldn't have to wait long
- Agent should work in background
- Answer quickly, start work, send completion message when finished

### Deployment

#### Q: Preferred deployment method? Separate staging/production environments?
**A:** 
- Manual deployment for now
- Don't overcomplicate it
- Give me an easy script

#### Q: How quickly do you need to rollback? Auto-rollback on failures?
**A:** 
- Don't worry about rollbacks

### Observability

#### Q: Where should logs go? What log level? Alert method?
**A:** 
- GCP Logging
- Only needed logs
- Don't want to sort through too much crap

#### Q: What metrics matter most? Want a dashboard?
**A:** 
- Engagement raising is most important
- (Dashboard not discussed, CSV export suggested)

#### Q: Should agent keep audit trail of posts created/approved/published? Retention period?
**A:** 
- Don't worry about this right now
- Will make it learn from past experiences later

### Q: Phase 1C complete! Ready for Phase 2 (User Stories)?
**A:** [Awaiting user response]

**Phase 1C Outputs:**
- ✅ Security design: Service account auth, Secret Manager, @ez-ai.io domain restriction
- ✅ Performance strategy: Async-first pattern (respond fast, work in background, notify on completion)
- ✅ Deployment strategy: Simple ./deploy.sh script for manual Cloud Run deployment
- ✅ Observability: GCP Cloud Logging (INFO level), engagement metrics tracking, weekly reports
- ✅ Risk assessment: 8 key risks identified with pragmatic mitigations
- ✅ Incident response runbook for common issues

**Key Decisions:**
- No complex rollback mechanism (manual redeploy sufficient)
- No audit trail for MVP (will add for learning system later)
- Engagement growth as primary KPI
- Manual metrics collection via Python script
- Simple Google Chat alerting for critical errors only

**Document Location:** `.monkeymode/marketing-campaign-manager/design/1c-operations.md`

---

## Phase 2: User Stories
**Date:** 2026-02-11T20:00:00Z

### Q: How many developers will work on this feature?
**A:** 1 developer (solo)

### Q: What's your target timeline for this feature?
**A:** Flexible, no hard deadline

### Q: Are you working solo on this, or do you want me to create stories assuming a team?
**A:** Working solo

**Story Decomposition Approach:**
- Since solo developer, stories optimized for sequential implementation
- Vertical slice prioritized (generate → approve → post for X/Twitter first)
- 4 sprints planned:
  1. Sprint 1: Core vertical slice (5 stories, 5-7 days)
  2. Sprint 2: Platform expansion + research skills (7 stories, 5-7 days)
  3. Sprint 3: Campaign planning & scheduling (4 stories, 5-7 days)
  4. Sprint 4: Production polish (3 stories, 3-5 days)
- Total estimated time: 18-26 days

**Phase 2 Outputs:**
- ✅ 19 user stories created across 4 sprints
- ✅ Each story has clear acceptance criteria and implementation details
- ✅ Stories follow vertical slice pattern (MVP first, then expand)
- ✅ Integration contracts defined for each skill
- ✅ Testing strategy included in each story
- ✅ Sprint 1 focuses on critical path: Skill loader → generate-post → request-approval → post-content (X)

**Document Location:** `.monkeymode/marketing-campaign-manager/user_stories.md`

---

## Phase 3: Code Spec
**Date:** 2026-02-12T02:30:00Z

### Q: Should I create separate code specs for each story, or one comprehensive spec for all Sprint 1 stories?
**A:** Create code specs for all of them in one md file please

**Code Spec Approach:**
- Created single comprehensive code spec covering all 5 Sprint 1 stories
- Includes detailed implementation guide for each task
- Follows monkey-bot codebase conventions (discovered through code analysis)
- Provides complete code examples where needed
- References existing patterns for similar tasks
- Total scope: 21 files (1 modified, 15 created, 10 test files)

**Phase 3 Outputs:**
- ✅ Story 1.1: Enhanced Skill Loader - Modify loader.py to expose descriptions, add get_tool_schemas() method
- ✅ Story 1.2: Generate Post Skill - Complete implementation with platform limits, validation, brand voice support
- ✅ Story 1.3: Request Approval Skill - Async approval workflow with Google Chat card (placeholder for MVP)
- ✅ Story 1.4: Post Content Skill - X (Twitter) posting with approval verification (placeholder API for MVP)
- ✅ Story 1.5: End-to-End Validation - Routing tests (CRITICAL!) and E2E workflow tests
- ✅ All code follows mypy strict mode (type hints everywhere)
- ✅ All tests use pytest + pytest-asyncio
- ✅ Structured logging with trace IDs throughout
- ✅ Detailed dependency graph showing implementation order
- ✅ Estimated timeline: 5-7 days solo developer

**Key Implementation Notes:**
- MVP uses placeholders for: Gemini API (content generation), Google Chat API (approval cards), X API (posting)
- Replace placeholders with real APIs in production
- Auto-approve logic in approval skill (for testing) should be removed in production
- Focus on routing tests first - if routing fails, entire system breaks
- All code follows existing monkey-bot patterns (analyzed codebase first)

**Document Location:** `.monkeymode/marketing-campaign-manager/code_specs/sprint-1-complete.md`

---

## Code Specs for Sprints 2-4
**Date:** 2026-02-12T03:00:00Z

### Q: Please create code specs for the rest of the user stories in Sprints 2-4
**A:** Created comprehensive code specs for all remaining stories (Sprints 2, 3, and 4)

**Deliverables Created:**

1. **Sprint 2 Code Spec** (`code_specs/sprint-2-platforms-research.md`)
   - 7 stories: Instagram, TikTok, LinkedIn, Reddit posting + 3 research skills
   - Platform-specific API patterns (2-step Instagram, 3-step TikTok, etc.)
   - MCP integration (Perplexity, Firecrawl)
   - Estimated duration: 5-7 days

2. **Sprint 3 Code Spec** (`code_specs/sprint-3-campaigns-scheduling.md`)
   - 3 stories: Campaign creation, scheduling, cron framework
   - Menu pattern with LLM instruction files
   - Background job scheduling with persistence
   - Estimated duration: 5-7 days

3. **Sprint 4 Code Spec** (`code_specs/sprint-4-production-polish.md`)
   - 2 stories: Deployment automation + metrics collection
   - GCP Cloud Run deployment (Docker, secrets, health checks)
   - Daily metrics + weekly reports
   - Estimated duration: 3-5 days

4. **Summary Document** (`CODE_SPECS_SUMMARY.md`)
   - Overview of all 4 sprints (19 total stories)
   - Implementation roadmap (18-26 days)
   - Testing strategy, configuration requirements
   - Success metrics and risk mitigation

**Key Technical Specifications:**

**Sprint 2 Highlights:**
- Instagram: 2-step posting (create container → publish) via Graph API
- TikTok: 3-step video upload (initialize → upload chunks → publish)
- LinkedIn: UGC posts with professional tone
- Reddit: Subreddit validation before posting
- Perplexity MCP: Web search with recency filters
- Firecrawl MCP: Competitor website scraping
- Trend identification: Aggregates searches + LLM pattern analysis

**Sprint 3 Highlights:**
- Campaign creation: 4-step workflow (research → strategy → calendar → post ideas)
- Menu pattern: Separate .md files with LLM instructions for each step
- Cron scheduler: Polling-based (10s intervals), job persistence, automatic retry (3 attempts)
- Campaign storage: `data/memory/campaigns/{id}/plan.json`
- Job types: `post_content`, `collect_metrics`, `send_weekly_report`

**Sprint 4 Highlights:**
- Deployment: One-command deploy script (`./deploy.sh`)
- Secrets: GCP Secret Manager integration (no .env in production)
- Health checks: `/health` endpoint for Cloud Run
- Metrics: Daily collection from all 5 platforms (likes, comments, shares, impressions)
- Reports: Weekly Google Chat cards with week-over-week growth analysis

**Total Scope:**
- 55+ files to create
- 7 files to modify
- 21 test files
- All following established patterns from Sprint 1

**Recommended Implementation Order:**
1. Sprint 2 first (builds on X posting pattern, validates multi-platform approach)
2. Sprint 3 second (adds campaign planning and scheduling on stable foundation)
3. Sprint 4 last (production polish when all features complete)

**Next Steps:**
- User should select which story to implement first
- All code specs are complete and ready for implementation
- Each spec includes: function signatures, API details, test cases, critical notes

---

