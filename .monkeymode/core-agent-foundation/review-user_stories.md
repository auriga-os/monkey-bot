# Review: user_stories.md

**Phase:** Phase 2 - User Stories
**Reviewed:** 2026-02-11T21:15:00Z

## Overview
Decomposes core agent foundation into 3 parallel stories (Gateway, Agent Core, Skills Engine) plus 1 integration story. Each story defines interfaces for others to consume, uses mocks for dependencies, and targets different file paths to enable true parallel development.

## Key Artifacts Defined
- Story 1 (Dev 1): Gateway Module (FastAPI, Google Chat, PII filter) defines AgentCoreInterface
- Story 2 (Dev 2): Agent Core + LLM Client (LangGraph, Vertex AI) defines SkillsEngineInterface, MemoryManagerInterface
- Story 3 (Dev 3): Skills Engine + Terminal Executor + Memory Manager implements interfaces, provides example skills
- Story 4 (Integration): Wire real implementations, end-to-end tests, Cloud Run deployment
- Sprint 1 target: 5-7 days parallel work, Sprint 2: 2-3 days integration

## Dependencies
- All stories depend on clear interface definitions (defined upfront in each story)
- Story 4 requires Stories 1-3 complete before starting
- External deps: LangGraph, LangChain, FastAPI, Vertex AI, GCS, Google Chat API

---

## Double Check These Sections

- **Story 2 > Integration Contracts > MemoryManagerInterface**: Uses `Message` dataclass not defined in snippet - verify it's in imports or defined elsewhere
- **Story 2 > Implementation Details > AgentCore**: Comment says "For Sprint 1: Use mocks" but constructor takes real deps - clarify init pattern for testing
- **Story 3 > Implementation Details > SkillLoader**: YAML parsing assumes `---` delimiters - no error handling shown for malformed SKILL.md files
- **Story 3 > Integration Contracts**: Defines same interfaces as Story 2 - potential file conflict if both devs create `src/core/interfaces.py`
- **Story 1 > Acceptance Criteria > Google Chat Response**: "Cards V2 format" mentioned but no schema validation criterion - should add explicit format check
- **Story 3 > Terminal Executor > ALLOWED_PATHS**: Includes `./test-data/` which isn't in design docs - verify this is intentional for testing
- **Story 2 > Out of Scope**: States "Real Vertex AI integration (use MockVertexAI)" but LLM Client imports `aiplatform.gapic.PredictionServiceClient` - clarify Sprint 1 vs Sprint 2 boundary
- **Story 4 > Implementation Details > create_app()**: Imports `from google.cloud import aiplatform` - conflicts with Story 2's "use MockVertexAI" guidance
- **All Stories > Integration Timeline**: Each says "Sprint 2: Integration story wires real implementations" but doesn't specify which dev owns what in Story 4
- **Story 1 > Acceptance Criteria > Health Check**: Says "check Agent Core unavailable → 503" but Story 1 uses mock which always returns ok - criterion impossible to test

---

## Potential Issues

### Gaps
- No story explicitly owns `src/core/interfaces.py` - both Story 2 and Story 3 reference it (file ownership conflict)
- Story 4 doesn't specify test data cleanup strategy across all 3 components
- No acceptance criteria for Story 4 define "integration successful" beyond "tests pass"
- Sprint 1 completion definition unclear - who validates each story is "done" before Story 4 starts?

### Conflicts
- **Story 2 vs Story 3 file ownership**: Both create `src/core/interfaces.py` - will cause merge conflict
- **Story 2 imports**: Mixes MockVertexAI (Sprint 1) with real aiplatform imports (Sprint 2) in same code snippet
- **Story 1 mock behavior vs acceptance criteria**: Health check test requires checking "Agent Core unavailable" but MockAgentCore never fails

### Risks
- **Parallel merge conflicts**: Story 1 creates `src/gateway/interfaces.py` with `AgentCoreInterface`, Story 2 creates `src/core/interfaces.py` with same class - risk of duplicating interface definitions
- **Story 3 size**: 5-7 days for 3 major components (Skills + Terminal + Memory) is largest story - could block integration if delayed
- **Integration complexity underestimated**: Story 4 says 2-3 days but must wire 5+ components (Gateway, Agent, LLM, Skills, Terminal, Memory, GCS) plus write e2e tests - may need 4-5 days
- **Mock quality unverified**: No acceptance criteria require mocks to match real implementation signatures - could discover interface mismatches in Story 4

### Scope Creep
- **Story 3 > ALLOWED_PATHS**: Adds `./content/` directory not mentioned in any design doc
- **Story 4 > Dockerfile**: Includes health check with curl but curl not in requirements.txt or design
- **Story 2 > LLM Client**: Streaming logic mentioned but design 1A says "streaming for responses > 200 tokens" without implementation details - needs clarification or deferral

---

**Total lines: 75**
