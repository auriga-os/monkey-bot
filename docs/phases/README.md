# Emonk Project Phases

This directory contains the detailed phase breakdown for building the Emonk agent framework. Each phase is designed to be executed using the @monkeymode skill for structured development.

---

## Phase Overview

| Phase | Name | Duration | Value Delivered |
|-------|------|----------|-----------------|
| **1** | [Core Agent Foundation + Google Chat](phase-1-core-foundation.md) | 2-3 weeks | Working chat-based AI assistant |
| **2** | [Marketing Campaign Manager](phase-2-marketing-campaign.md) | 3-4 weeks | Complete marketing automation |
| **3** | [Cloud Run Deployment + Framework](phase-3-cloud-deployment.md) | 2-3 weeks | Production deployment + reusable library |
| **4** | [Production Hardening + Jr Engineer Agent](phase-4-production-hardening.md) | 2-3 weeks | Reliability + framework validation |
| **5** | [Advanced Features & Polish](phase-5-advanced-features.md) | 2-4 weeks | Enterprise-grade capabilities (Optional) |

**Total Timeline:** 11-17 weeks (3-4 months) for complete system

---

## Execution Strategy

### Using Monkeymode

Each phase is designed to work with the monkeymode skill:

```bash
# Start Phase 1
@monkeymode for Emonk Phase 1: Core Agent Foundation + Google Chat
```

The monkeymode skill will guide you through:
1. **Phase 1A: Design** - Discovery & Core Design
2. **Phase 1B: Design** - Detailed Contracts
3. **Phase 1C: Design** - Production Readiness
4. **Phase 2: User Stories** - Break into parallelizable tasks
5. **Phase 3: Code Spec** - Detailed implementation plan
6. **Phase 4: Implementation** - TDD-based development

### Sequential Execution

Execute phases in order:
1. Complete Phase 1 → Demo working agent
2. Complete Phase 2 → Demo marketing automation
3. Complete Phase 3 → Deploy to production
4. Complete Phase 4 → Validate framework with 2nd agent
5. (Optional) Complete Phase 5 → Add advanced features

**Important:** Only move to the next phase when the current phase delivers working, tested code.

---

## Phase Details

### Phase 1: Core Agent Foundation + Google Chat

**File:** [phase-1-core-foundation.md](phase-1-core-foundation.md)

**Goal:** Working general-purpose AI agent with chat interface

**Key Components:**
- LLM Integration (Vertex AI)
- Terminal Executor
- Memory System (File-based + GCS)
- Agent Core (LangGraph)
- Google Chat Integration
- Basic Skills (file ops, shell, memory)
- Cron Job System (basic)

**Success Criteria:**
- Agent responds to Google Chat within 2 seconds
- Memory persists across restarts
- Safe command execution
- Basic skills working end-to-end

**Demo:** Chat-based assistant that can execute commands, manage memory, and interact conversationally

---

### Phase 2: Marketing Campaign Manager

**File:** [phase-2-marketing-campaign.md](phase-2-marketing-campaign.md)

**Goal:** Complete marketing workflow automation

**Key Components:**
- MCP Integration Layer (CLI-based)
- Token Management System
- Research Skills (Perplexity, Firecrawl)
- Campaign Planning Skills
- Content Generation Skills
- Posting Skills (X/Twitter, LinkedIn, Instagram)
- Brand Voice System
- Grounded Web Search

**Success Criteria:**
- Complete campaign from single topic input
- Real-time web research working
- Brand voice validation automatic
- Multi-platform posting successful
- Token management easy

**Demo:** Create 4-week campaign from topic → research → strategy → generate posts → schedule

---

### Phase 3: Cloud Run Deployment + Framework

**File:** [phase-3-cloud-deployment.md](phase-3-cloud-deployment.md)

**Goal:** Production deployment + reusable framework library

**Key Components:**
- Framework Library (`emonk-framework`)
- Agent Configuration System (YAML)
- Storage Adapters (GCS, Local)
- Cloud Run Adapter (stateless)
- Cloud Scheduler Integration
- Secret Manager Integration
- Deployment Tooling (CLI, Terraform)
- Agent Templates

**Success Criteria:**
- Marketing agent deployed on Cloud Run
- Memory persists via GCS
- Cron jobs work via Cloud Scheduler
- Secrets in Secret Manager
- New agent created in <30 minutes

**Demo:** Deploy marketing agent to GCP, create new agent using framework library

---

### Phase 4: Production Hardening + Jr Engineer Agent

**File:** [phase-4-production-hardening.md](phase-4-production-hardening.md)

**Goal:** Reliability features + framework validation

**Key Components:**
- Error Recovery & Classification
- Retry Strategies
- Circuit Breaker Pattern
- Session Management
- Context Compression
- Multi-Model Routing (cost optimization)
- Observability & Monitoring
- Permission & Approval System
- Jr Software Engineer Agent

**Success Criteria:**
- Error recovery handles failures gracefully
- Session management prevents overflow
- Multi-model routing reduces costs 30%+
- Observability dashboard working
- Jr Engineer agent reviews PRs successfully
- Both agents running in production

**Demo:** Both agents running reliably 24/7, jr engineer reviews PR and suggests improvements

---

### Phase 5: Advanced Features & Polish (Optional)

**File:** [phase-5-advanced-features.md](phase-5-advanced-features.md)

**Goal:** Enterprise-grade features (pick 1-2 based on priorities)

**Feature Options:**
1. **Recipe/Workflow System** - Complex multi-step workflows without code
2. **Full MCP Protocol** - Skills work in Claude Desktop, Cursor, Zed
3. **Web UI** - Self-service campaign management dashboard
4. **Advanced Analytics** - Data-driven insights and reporting
5. **Performance Optimization** - Caching, parallel execution, streaming

**Implementation Strategy:** Choose features based on user feedback and business priorities

**Demo:** Depends on chosen features (e.g., weekly report recipe, web UI campaign creation)

---

## Architecture Evolution

### Phase 1: Monolithic Agent
```
┌─────────────────┐
│   Agent Core    │
├─────────────────┤
│ Google Chat     │
│ Skills          │
│ Memory (Local)  │
│ Cron (Local)    │
└─────────────────┘
```

### Phase 2: Domain-Specific Agent
```
┌─────────────────────────┐
│   Marketing Agent       │
├─────────────────────────┤
│ Campaign Skills         │
│ MCP Integration         │
│ Brand Voice System      │
│ Social Media Posting    │
└─────────────────────────┘
```

### Phase 3: Framework + Cloud Deployment
```
┌─────────────────────────┐
│   emonk-framework       │ ← Reusable Library
├─────────────────────────┤
│ Marketing Agent         │ ← Deployed to Cloud Run
│ (Template Instance)     │
└─────────────────────────┘
         ↓
┌─────────────────────────┐
│   GCP Services          │
├─────────────────────────┤
│ Cloud Run               │
│ Cloud Storage           │
│ Cloud Scheduler         │
│ Secret Manager          │
└─────────────────────────┘
```

### Phase 4: Multi-Agent Framework
```
┌─────────────────────────┐
│   emonk-framework       │
├─────────────────────────┤
│ ┌─────────────────────┐ │
│ │ Marketing Agent     │ │ ← Agent 1
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │ Jr Engineer Agent   │ │ ← Agent 2
│ └─────────────────────┘ │
└─────────────────────────┘
```

---

## Critical Success Factors

### For Each Phase:

1. **Working Code** - Every phase ends with functional, testable code
2. **Clear Demo** - Can demo value to stakeholders (even non-technical)
3. **Documentation** - README with setup and usage instructions
4. **Tests** - Unit tests for critical components
5. **Deployment** - Can deploy to environment (local Docker or GCP)

### Startup Prioritization Principles:

- ✅ **Phase 1**: Smallest viable product (chat assistant)
- ✅ **Phase 2**: Killer feature (full marketing automation)
- ✅ **Phase 3**: Scale and reuse (framework + deployment)
- ✅ **Phase 4**: Production quality (reliability + 2nd use case)
- ✅ **Phase 5**: Nice-to-haves (optional enhancements)

---

## Quick Start

### Begin Phase 1

1. Read [phase-1-core-foundation.md](phase-1-core-foundation.md)
2. Set up development environment:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   export VERTEX_AI_PROJECT_ID=your-gcp-project
   ```
3. Run monkeymode:
   ```bash
   @monkeymode for Emonk Phase 1: Core Agent Foundation + Google Chat
   ```
4. Follow the monkeymode workflow through design → user stories → code spec → implementation

### After Completing a Phase

1. Demo the working functionality
2. Document any learnings or deviations from plan
3. Update phase document if needed
4. Move to next phase

---

## References

### Planning Documents
- [Base Agent Abilities](../preplanning/base-agent-abilities.md)
- [OpenClaw Implementation Guide](../preplanning/OpenClaw_Implementation_Guide.md)
- [MCP Integration Research](../preplanning/mcp-research.md)
- [Skills MCP Integration](../preplanning/integrate-skills-mcp.md)

### Reference Architecture
- [Gateway Daemon](../ref/01_gateway_daemon.md)
- [Telegram Integration](../ref/02_telegram_integration.md)
- [Memory System](../ref/03_memory_system.md)
- [Cron Scheduler](../ref/04_cron_scheduler.md)
- [Skills System](../ref/05_skills_system.md)
- [LLM Integration](../ref/06_llm_integration.md)
- [Terminal Executor](../ref/07_terminal_executor.md)
- [Extension Architecture](../ref/08_goose_extension_architecture.md)
- [Error Recovery](../ref/09_goose_error_recovery.md)
- [Multi-Model Routing](../ref/10_goose_multi_model_routing.md)
- [Recipe Workflows](../ref/11_goose_recipe_workflows.md)
- [Session Management](../ref/12_goose_session_management.md)
- [Permission Security](../ref/13_goose_permission_security.md)
- [Observability](../ref/14_goose_observability.md)

---

## Support

For questions or issues during implementation:
1. Review the relevant phase document
2. Check reference architecture documents
3. Consult monkeymode output and logs
4. Create GitHub issue if blocked

---

## Contributing

If you discover improvements or corrections needed in the phase documents:
1. Document the issue or improvement
2. Update the relevant phase document
3. Create a pull request with explanation
4. Update this README if needed

---

**Good luck building Emonk!** 🚀

Remember: Each phase should deliver working, valuable functionality. Don't move to the next phase until the current one is complete and tested.
