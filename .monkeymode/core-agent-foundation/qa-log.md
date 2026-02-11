# Q&A Log: core-agent-foundation

## Branch Setup
**Date:** 2026-02-11T19:00:00Z

### Q: Would you like me to save a log of all our questions and answers during this process?
**A:** Yes - Save Q&A log

### Q: Which branch are you working on for this feature?
**A:** core

### Q: Which repositories will this feature touch?
**A:** monkey-bot (this repository - core agent, Google Chat integration, skills)

**Additional Context:**
- This repository will be open-sourced as a library/framework, so all code must be clean, well-documented, and follow best practices
- For now, all phases will be implemented in this single repository
- Repository: auriga-os/monkey-bot (GitHub)

### Q: Would you like me to pull latest from main first or create core branch from current main?
**A:** Create core branch from current main (use local main as-is)

**Actions Taken:**
- Created `core` branch from `main`
- Pushed `core` branch to remote (origin)
- Set up MonkeyMode workspace: `.monkeymode/core-agent-foundation/`

---

## Phase 1A: Discovery & Core Design
**Date:** 2026-02-11T19:15:00Z

### Q: Who will use this agent and what's the expected user impact?
**A:** This agent will be used by my startup team to quickly build agents that automate different processes or tasks (e.g., jr bug SWE, social media automation). Users should be able to easily add skills (starting with SKILL.md but can include Python and other files within those skills).

**Context:** 
- Building single agents (not multi-agent for now - see phase 2 for first use case)
- ~1 user initially (startup team)
- Focus on ease of skill creation

### Q: What's explicitly OUT of scope for Phase 1?
**A:** 
- Multi-agent orchestration (maybe later phases)
- Production-grade authentication (simple token-based is fine)
- Detailed audit logging (flow logging at most)

### Q: Timeline constraints or dependencies?
**A:** No timeline pressure. Plan this as one complete feature, thinking about major components and how everything works together for success.

---

## Phase 3: Code Spec - Story 4 (Integration & Deployment)
**Date:** 2026-02-11T23:45:00Z

### Q: What is your GCP project ID for Vertex AI?
**A:** Make all GCP configuration (project ID, region, bucket name) editable in .env file - user will fill it in themselves

### Q: What region should we use for Vertex AI and Cloud Run?
**A:** Make deployment configuration (region, min-instances, max-instances) editable in .env file

### Q: Should I add missing LangChain and Vertex AI dependencies to requirements.txt?
**A:** Test it! If you need it add it, if you don't need it, don't add it! (Add langgraph, langchain-google-vertexai, google-cloud-aiplatform, aiofiles as needed)

### Q: Should integration tests use real Vertex AI calls or mocks?
**A:** Most tests should use mocks (fast, free), but have at least 1 working integration test that uses real Vertex AI API calls

### Q: Should I create the code spec or implement Story 4?
**A:** Just create the spec for now - will review and provide feedback before implementation

**Code Spec Created:**
- File: `.monkeymode/core-agent-foundation/code_specs/story-4-spec.md`
- Tasks: 7 tasks (dependencies, config, main.py, Dockerfile, deployment, e2e tests, docs)
- Testing: Unit tests with mocked Vertex AI + 1 integration test with real API
- Configuration: All values in .env (user edits themselves)

---

### Q: Testing strategy and frameworks?
**A:** 
- Use pytest
- Unit tests with mocks
- Integration tests
- E2e tests
- Limited but definitely need functional tests to ensure it works

### Q: Tech stack and package management?
**A:** 
- Use `uv` package manager
- Use `.venv` for virtual environment
- Starting from scratch - establish patterns from ground up

### Q: Scale and load expectations?
**A:** 
- 1 user initially (startup team usage)
- Build smart but simple
- Don't overcomplicate for scale now
- Ensure scale can be added later very easily

### Q: Security, PII, and compliance requirements?
**A:** 
- **PII handling:** Ensure no PII goes to LLMs unless user explicitly puts it in the message
- **Google Chat metadata:** Gmail, Google Chat info (besides message content) should NEVER go to LLM
- **Audit logging:** Not needed right now - flow logging at most (nothing verbose or confusing)
- **Authentication:** Keep it simple - token-based deployment for Google Chat, can enhance later

### Architecture Design Decisions

**Q: What architecture approach should we use?**
**Decision:** Modular Monolith on Cloud Run

**Rationale:**
- Simple deployment (one service, one Docker image)
- No inter-service network latency
- Easy local development
- Cloud Run auto-scales (0 to N instances)
- Clear module boundaries enable future microservice split if needed

**Alternatives Considered:**
1. Microservices Architecture - Too complex for 1-user startup scale
2. Serverless Functions (Cloud Functions) - Cold start latency hurts UX

**Q: Data storage strategy?**
**Decision:** File-based memory with GCS sync

**Rationale:**
- Simple (no DB to manage)
- Human-readable (can inspect/edit memory files)
- Version-controllable (can commit to git for backups)
- Sufficient for single-user scale
- Easy to migrate to DB later if needed

**Q: How to handle Google Chat PII?**
**Decision:** Hash user email to user_id, filter all Google Chat metadata before sending to LLM

**Implementation:**
- Gateway filters webhook payload
- Only message content goes to LLM
- User email hashed to stable user_id (no PII exposure)

**Phase 1A Output:**
- ✅ Design document created: `.monkeymode/core-agent-foundation/design/1a-discovery.md`
- ✅ Architecture decision: Modular Monolith on Cloud Run
- ✅ Module breakdown: Gateway, Agent Core, Skills, Memory, Terminal, Cron
- ✅ Core data model: ConversationMessage, KnowledgeFact, CronJob, Skill
- ✅ Security: PII filtering, terminal allowlist
- ✅ Open source considerations documented

### Phase 1A Review & Fixes
**Date:** 2026-02-11T20:00:00Z

**Review Document:** `.monkeymode/core-agent-foundation/design/review-1a-discovery.md`

**Critical Issues Identified:**
1. Cron module conflict (described as "not suitable for Cloud Run")
2. Security gaps (webhook signature, skill validation, GCS conflicts)
3. Missing specifications (context window, retention, model selection criteria)

**User Responses & Fixes:**

### Q: Should cron be in Phase 1 or deferred to Phase 3?
**A:** Cron should be part of Phase 1. Reference: `docs/ref/04_cron_scheduler.md`

**Fix Applied:**
- Updated cron implementation to use GCS-backed storage (`gs://emonk-memory/cron-jobs.json`)
- Threading-based timers (Python `threading.Timer`)
- Loads jobs from GCS on startup and reschedules all timers
- Single Cloud Run instance for MVP (`--min-instances=1 --max-instances=1`) avoids duplicate execution
- Supports three schedule types: cron expressions, intervals, one-time

### Q: Should we add webhook signature verification?
**A:** Only add it if it is important

**Fix Applied:**
- Omitted webhook signature verification for Phase 1 (MVP simplicity)
- Rely on HTTPS + URL obscurity + user email allowlist
- Added note: "Can add in production if needed"

### Q: How to handle GCS write conflicts (multi-instance)?
**A:** Ensure you figure it out how to do it simply without over complicating it

**Fix Applied:**
- Single Cloud Run instance for MVP (`--min-instances=1 --max-instances=1`)
- Last-write-wins behavior documented
- Added note for future scaling: "Use GCS object versioning or distributed lock when scaling >1 instance"

### Q: How to validate Python scripts in skills (security risk)?
**A:** Add to README the danger, don't worry about validating python scripts, it's on dev to give them that info that is security risk, not the creator of the opensource tool

**Fix Applied:**
- Added security warning to Terminal Executor section: "No validation of skill script content - arbitrary code execution is possible"
- Added comprehensive security warning to Open Source Considerations section for README.md
- Documented that security is developer's responsibility, not framework's

**Additional Fixes:**
- Added conversation context window: Last 10 messages (configurable)
- Added retention policy: 90-day conversation history, persistent facts/jobs
- Clarified LLM model selection: Flash by default, Pro only on explicit request (no auto-fallback)
- Clarified streaming threshold: 200 tokens (~1-2 paragraphs)
- Added skill conflict resolution: Use first discovered (alphabetical), log warning
- Added metrics implementation: Cloud Logging queries, manual analysis
- Added skill runtime changes: Requires restart (future: hot-reload endpoint)
- Added ALLOWED_USERS env var for email allowlist

---

## Phase 1B: Detailed Contracts
**Date:** 2026-02-11T20:15:00Z

### API Contracts Defined
- **Public Endpoints**: POST /webhook (Google Chat), GET /health
- **Internal APIs**: Gateway → Agent Core, Agent Core → LLM/Skills/Memory, Skills → Terminal
- **Error Format**: Standardized JSON with code, message, trace_id

### Integration Points Documented
- **Vertex AI**: Gemini 2.0 API with timeout (60s), retry (3x exponential backoff)
- **Google Cloud Storage**: Memory persistence with async sync, graceful failure handling
- **Google Chat API**: Response delivery with retry logic

### Testing Strategy
- **Unit Tests**: 80% coverage target, mock external dependencies
  - Gateway: PII filtering, allowlist validation
  - Agent Core: Message routing, context management
  - Skills Engine: Skill discovery, execution
  - Memory Manager: Read/write operations, GCS sync
  - Terminal Executor: Command/path allowlist, timeout
  - LLM Client: Chat, streaming, error handling
  - Cron Manager: Job scheduling, persistence
- **Integration Tests**: E2E flows with real filesystem
  - Remember + recall fact, file operations, skill execution, cron job execution
- **Contract Tests**: JSON Schema validation for Google Chat webhook
- **Load Tests**: Optional for Phase 1 (1 user), add when scaling
- **E2E Tests**: Manual testing of critical user journeys

**Phase 1B Output:**
- ✅ Design document created: `.monkeymode/core-agent-foundation/design/1b-contracts.md`
- ✅ API contracts defined (public + internal)
- ✅ Integration points documented (Vertex AI, GCS, Google Chat)
- ✅ Testing strategy specified (unit, integration, contract, E2E)
- ✅ Concise format (descriptions only, no full test code per user request)
- ✅ Load testing removed per user request (defer until multi-user scale)

---

## Phase 1C: Production Readiness
**Date:** 2026-02-11T20:30:00Z

**User Requirement:** "Do not make it too complicated!"

**Simplified Approach:**
- Focused on MVP scale (1 user, single instance)
- Practical security (email allowlist, PII filter, env var secrets)
- Relaxed performance targets (appropriate for startup usage)
- Simple deployment (Cloud Run with built-in features)
- Basic observability (Cloud Logging, simple metrics)

### Security Design
- **Authentication**: Email allowlist via ALLOWED_USERS env var
- **PII Protection**: Hash email to user_id, strip Google Chat metadata
- **Secrets**: Env vars for dev, GCP Secret Manager for production
- **Security Warning**: Added to README for skill execution risk

### Performance & Scalability
- **Expected Load**: 1 user, ~100 messages/day
- **Performance Targets**: < 5s response, < 2s LLM, < 1% error rate
- **Optimization**: Local cache, async GCS sync, context window limit
- **Scalability Path**: Documented future scaling (Redis, multi-instance, connection pooling)

### Deployment Strategy
- **Approach**: Single Cloud Run instance (`--min-instances=1 --max-instances=1`)
- **Pipeline**: Simple (Local → Docker → GCR → Cloud Run)
- **Health Checks**: GET /health (checks LLM, GCS, skills)
- **Rollback**: Cloud Run automatic revision rollback (< 2 min)

### Observability
- **Logging**: Cloud Logging (structured JSON, trace IDs)
- **Metrics**: Cloud Logging metrics (error rate, response time, LLM failures)
- **Tracing**: Cloud Trace (optional for MVP)
- **Alerting**: Email alerts for service down, high errors

### Risk Assessment
- 6 risks identified with mitigations
- Focus on LLM limits, GCS sync, skill security, PII leakage
- Weekly error log review for first 2 weeks

### Infrastructure
- **GCP Resources**: Cloud Run, GCS bucket, Service Account, Secret Manager
- **Estimated Cost**: $10-15/month for MVP

**Phase 1C Output:**
- ✅ Design document created: `.monkeymode/core-agent-foundation/design/1c-operations.md`
- ✅ Simplified for MVP (no over-engineering)
- ✅ Security design (practical for single user)
- ✅ Performance targets (appropriate for startup)
- ✅ Simple deployment (Cloud Run with rollback)
- ✅ Basic observability (Cloud Logging, email alerts)
- ✅ Risk assessment (6 risks identified and mitigated)

---

## Design Phase Complete (1A + 1B + 1C)

**All 3 design phases finished:**
- Phase 1A: Architecture & Core Design ✓
- Phase 1B: API Contracts & Integration ✓
- Phase 1C: Production Readiness ✓

**Total Design Artifacts:**
- 1a-discovery.md (850+ lines)
- 1b-contracts.md (330 lines)
- 1c-operations.md (350 lines)
- review-1a-discovery.md (78 lines review)

**Design Philosophy:**
- Simple but smart (MVP-appropriate)
- Scalability path defined (no refactor needed)
- Security by transparency (warnings, not enforcement)
- Cloud-native (leverage GCP built-in features)
- Open source ready (clean, documented, tested)

---

## Phase 2: User Stories
**Date:** 2026-02-11T21:00:00Z

### Q: How many developers will work on this?
**A:** 3 developers

### Q: What's your target timeline for completing Sprint 1?
**A:** Don't worry about a timeline!

### Q: Should I define integration contracts upfront for parallel development?
**A:** Make 3 stories to do in parallel, then do 1 story to integrate them all at the end

**User Stories Created:**
- **Story 1**: Gateway Module - HTTP Interface & Google Chat Integration (Dev 1, 3-5 days)
- **Story 2**: Agent Core + LLM Client - Orchestration & Intelligence (Dev 2, 3-5 days)
- **Story 3**: Skills Engine + Terminal Executor + Memory Manager (Dev 3, 5-7 days)
- **Story 4**: Integration & Deployment (1 developer, 2-3 days) - Sprint 2

**Parallelization Strategy:**
- Sprint 1: All 3 stories are completely independent (ZERO dependencies)
- Each story defines interfaces that others will consume
- All stories use mocks for dependencies (enables parallel development)
- Sprint 2: Integration story wires real implementations together

**Phase 2 Output:**
- ✅ User stories document created: `.monkeymode/core-agent-foundation/user_stories.md`
- ✅ 3 parallel stories for Sprint 1 (no dependencies between them)
- ✅ 1 integration story for Sprint 2
- ✅ All interfaces defined upfront for clean integration
- ✅ Each story has complete acceptance criteria, implementation details, and mocks
- ✅ Estimated timeline: 7-10 days from start to production deployment

### Phase 2 Review & Fixes
**Date:** 2026-02-11T21:30:00Z

**Review Document:** `.monkeymode/core-agent-foundation/review-user_stories.md`

**Critical Issues Identified:**
1. File ownership conflict: Stories 2 and 3 both tried to create `src/core/interfaces.py`
2. Interface duplication: AgentCoreInterface defined in multiple places
3. Mixed mock/real imports in Story 2 code snippets
4. Story 3 size concern (5-7 days for 3 components)

**User Responses & Fixes:**

### Q: Should we fix the file ownership conflict (Story 2 vs Story 3)?
**A:** Please make this fix!

**Fix Applied:**
- Story 2 designated as owner of `src/core/interfaces.py` with ALL shared interfaces
- Added ExecutionResult dataclass to Story 2's interfaces
- Story 3 now imports from Story 2's interfaces (does not redefine)
- Clear file ownership documented in File Ownership Summary table

### Q: Should we fix the interface duplication issue?
**A:** Yes please fix this

**Fix Applied:**
- Story 1 keeps local AgentCoreInterface copy for Sprint 1 independence
- Story 2 owns master copy in `src/core/interfaces.py`
- Story 4 will consolidate (remove Gateway's local copy during integration)

### Q: Should we adjust time estimates?
**A:** Don't worry about time estimate

**Fix Applied:**
- Removed specific day estimates from Sprint 2
- Changed to "Variable (integration complexity)"

### Q: Should we specify which developer owns Story 4 tasks?
**A:** Don't worry about which developer owns it

**Fix Applied:**
- Left Story 4 ownership flexible
- No specific developer assignments

**Additional Fixes:**
- Removed `./content/` from ALLOWED_PATHS (not in design)
- Fixed Story 2 LLM Client to use only MockVertexAI for Sprint 1
- Clarified Story 4 uses real Vertex AI via LangChain wrapper
- Added env var validation to Story 4's create_app()
- Enhanced Story 2 Notes for Developer with file ownership clarity

---

## Phase 3: Code Spec - Story 1
**Date:** 2026-02-11T22:00:00Z

### Q: Ready to create code spec for Story 1?
**A:** "I am story 1 please make the code spec"

**Action Taken:**
Created comprehensive code spec at `.monkeymode/core-agent-foundation/code_specs/story-1-spec.md`

**Code Spec Details:**
- **Story:** Gateway Module - HTTP Interface & Google Chat Integration
- **Size:** Medium (M) - 3-5 days
- **Tasks:** 8 atomic tasks
- **Files to Create:** 8 new files
- **Tests:** 3 test files with 100% coverage for security-critical PII filter
- **Target File Size:** ~750 lines (within M story target of 400-800 lines)

**Key Features:**
- FastAPI server with async/await throughout
- Google Chat webhook handling (POST /webhook)
- Health check endpoint for Cloud Run (GET /health)
- PII filtering with email hashing (SHA-256)
- Allowlist-based user authorization
- MockAgentCore for Sprint 1 parallel development
- Structured JSON logging with trace_id
- Response truncation for Google Chat (4000 char limit)
- Complete test specifications following pytest async patterns

**Task Breakdown:**
1. Project Setup & Dependencies (requirements.txt, pyproject.toml, .env.example)
2. Create Core Interfaces & Data Models (Pydantic models, ABC interfaces)
3. Implement PII Filter (hash emails, strip Google Chat metadata)
4. Create Mock Agent Core (MockAgentCore for testing)
5. Implement FastAPI Server (POST /webhook, GET /health endpoints)
6. Add Structured Logging (JSON logs for Cloud Logging)
7. Add Response Truncation (4000 char limit for Google Chat)
8. Create Main Entry Point (uvicorn runner for local dev)

**Conventions Established:**
- Python 3.11+ with async/await
- Type hints on all functions (mypy strict mode)
- Pydantic for validation
- pytest 8.x with async support
- Structured JSON logging
- PEP 8 style guide
- 80%+ test coverage (100% for security-critical paths)

**Integration Contract:**
Defined `AgentCoreInterface` that Story 2 will implement:
```python
async def process_message(user_id: str, content: str, trace_id: str) -> str
```

**Next Step:** Ready for Phase 4 (Implementation) when user confirms

---

## Phase 3: Code Spec - Story 3
**Date:** 2026-02-11T22:45:00Z

### Q: Which story would you like to create a code spec for?
**A:** Story 3 - Skills Engine + Terminal Executor + Memory Manager

### Q: Ready to create code spec for Story 3?
**A:** Yes (implicit - user said "I am story 3 please make the code spec")

**Code Spec Created:** `.monkeymode/core-agent-foundation/code_specs/story-3-spec.md`

**Code Spec Details:**
- **Story:** Skills Engine + Terminal Executor + Memory Manager
- **Size:** Large (L) - 5-7 days
- **Tasks:** 7 atomic tasks
- **Files to Create:** 14 new files
- **Tests:** 4 test files with 100% coverage for security-critical Terminal Executor
- **Target File Size:** ~1,450 lines (within L story target of 800-1500 lines)

**Key Features:**
- Terminal Executor with security allowlists (ALLOWED_COMMANDS, ALLOWED_PATHS)
- Skills Engine with SKILL.md discovery and parsing (YAML frontmatter)
- Skills Executor with Terminal Executor integration
- Memory Manager with file-based storage (conversation history + facts)
- Async GCS sync (fire-and-forget, non-blocking)
- Two example skills: file-ops and memory
- Complete integration tests for end-to-end validation

**Task Breakdown:**
1. Create Terminal Executor with Security Allowlist (CRITICAL - security boundary)
2. Create Skills Engine - Loader Component (discover skills, parse SKILL.md)
3. Create Skills Engine - Executor Component (execute skills via Terminal)
4. Create Memory Manager - Core Implementation (file-based with GCS sync)
5. Create Example Skill - File Operations (read, write, list files)
6. Create Example Skill - Memory Operations (remember, recall facts)
7. Integration Tests for Skills + Terminal + Memory (end-to-end validation)

**Conventions Established:**
- Python 3.11+ with async/await throughout
- Type hints on all public functions
- pytest with pytest-asyncio for async tests
- Structured logging with JSON format
- Custom exception classes (SecurityError, SkillError, etc.)
- Dataclasses for data structures
- Pathlib for all file operations
- Security-first design (100% test coverage for Terminal Executor security)

**Integration Contracts:**
Story 3 imports interfaces from Story 2's `src/core/interfaces.py`:
- `SkillsEngineInterface` (implemented by SkillsEngine)
- `MemoryManagerInterface` (implemented by MemoryManager)
- `SkillResult`, `ExecutionResult`, `Message` (data structures)

**Security Notes:**
- Terminal Executor is most security-critical component
- Allowlist-based command/path validation (deny by default)
- Process timeout with cleanup (prevent zombie processes)
- Output truncation (1MB limit to prevent memory exhaustion)
- No user input in commands (skills parse args themselves)

**Next Step:** Ready for Phase 4 (Implementation) when user confirms

---


## Phase 3: Code Spec - Story 2 (Agent Core + LLM Client)
**Date:** 2026-02-11T22:00:00Z

### Q: Python version & tooling - Do you have a preference for Python version (3.11+, 3.12)? Should I include pyproject.toml or requirements.txt?
**A:** Use whatever is best for most people

**Decision:** Python 3.11+ (modern async, type hints), pyproject.toml with requirements.txt generation

### Q: Testing framework - I see the design mentions pytest. Any specific pytest plugins?
**A:** Pytest or whatever the standard is

**Decision:** pytest + pytest-asyncio + pytest-cov (standard for async Python projects)

### Q: Type checking - Should I include type hints with mypy checking? Any specific strictness level?
**A:** Whatever you think is necessary, consider being quick but providing a lot of value still

**Decision:** mypy with strict mode (catches more bugs, good for maintainability)

### Q: Code formatter - Preference for black, ruff, or another formatter?
**A:** ruff

**Decision:** ruff for linting + formatting (fast, modern)

### Q: Vertex AI setup - For Sprint 1 with mocks, should I create a MockVertexAI that mimics the LangChain ChatVertexAI interface?
**A:** Vertex AI models. Use gemini2.5 flash, or haiku 4.5

**Decision:** Use Gemini 2.5 Flash (gemini-2.5-flash-002) as primary model, MockVertexAI for Sprint 1 testing

### Q: Streaming implementation - The design mentions streaming for responses > 200 tokens. Should I implement streaming logic in Sprint 1?
**A:** Defer to story 4, make a note there please

**Decision:** Document streaming in Story 4 integration notes, don't implement in Sprint 1

### Q: Exception hierarchy - Should I create custom exception classes (AgentError, LLMError, SkillError) with specific error codes?
**A:** Make it easy to fix and maintain and make it work that's all I care about

**Decision:** Simple exception hierarchy (EmonkError base, specific subclasses), clear error messages

### Q: Retry logic - Design mentions 3x exponential backoff for LLM. Should I implement retry logic in Sprint 1 mocks?
**A:** Doc for story 4

**Decision:** Document retry logic for Story 4, mocks don't need retry

### Q: Interfaces file - Story 2 owns src/core/interfaces.py with ALL shared interfaces. Should I also include type aliases and data classes?
**A:** Do what you think is best, I strive for maintainable and quality code!

**Decision:** Single interfaces.py file with dataclasses, exceptions, and all ABC interfaces (single source of truth)

### Q: Logging setup - Should I configure structured JSON logging in Story 2?
**A:** Maintainable and quality/accuracy is the most important thing I care about now, do what you think is best

**Decision:** Use Python logging module with structured format (trace_id, component), JSON format documented for production use

**Code Spec Created:** `.monkeymode/core-agent-foundation/code_specs/story-2-spec.md`

**Summary:**
- **Files to Create:** 8 files (5 source, 3 test)
- **Files to Modify:** 0 (greenfield)
- **Tests:** 2 test files with 80%+ coverage
- **Target File Size:** ~750 lines (within M story target of 400-800 lines)

**Key Features:**
- Shared interfaces file (src/core/interfaces.py) - owned by Story 2
- LLM Client wrapper for Vertex AI (MockVertexAI for Sprint 1)
- Agent Core with simple single-step orchestration
- Mock dependencies for parallel development
- Complete unit tests with pytest-asyncio
- Type checking with mypy (strict mode)
- Structured logging with trace IDs

**Task Breakdown:**
1. Project Structure + Dependencies (pyproject.toml, pytest.ini, mypy.ini)
2. Create Shared Interfaces (src/core/interfaces.py) - ALL project interfaces
3. Create Mock Dependencies (MockVertexAI, MockSkillsEngine, MockMemoryManager)
4. Create LLM Client (Vertex AI wrapper with error handling)
5. Create Agent Core with LangGraph (simple single-step agent)
6. Unit Tests for Agent Core (8 test cases)
7. Unit Tests for LLM Client (5 test cases)
8. Integration Test (end-to-end with mocks)

**Conventions Established:**
- Python 3.11+ with async/await
- Type hints on all functions (mypy strict mode)
- Google-style docstrings
- ruff for formatting/linting
- Structured logging (timestamp, level, component, trace_id)
- Custom exceptions (EmonkError base class)

**Integration Contracts:**
Story 2 owns `src/core/interfaces.py` - defines ALL shared interfaces:
- `AgentCoreInterface` (implemented by AgentCore)
- `SkillsEngineInterface` (Story 3 implements)
- `MemoryManagerInterface` (Story 3 implements)
- Data classes: `Message`, `SkillResult`, `ExecutionResult`
- Exceptions: `AgentError`, `LLMError`, `SkillError`, `SecurityError`

**Story 4 Integration Notes:**
- Replace MockVertexAI with real ChatVertexAI from langchain-google-vertexai
- Add retry logic (3x exponential backoff) for LLM calls
- Add streaming support for responses > 200 tokens
- Wire real SkillsEngine and MemoryManager from Story 3
- Add Vertex AI initialization (aiplatform.init())

**Next Step:** Ready for implementation or create specs for remaining stories

---
