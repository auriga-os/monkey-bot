---
name: monkeymode
description: AI-Driven Development Life Cycle - Guides from feature idea to production through 4 structured phases (Design → User Stories → Code Spec → Implementation). Creates state-tracked artifacts in your workspace.
version: 1.0.0
author: Auriga OS
repository: https://github.com/auriga-os/monkeymode
---

# MonkeyMode - AI-Driven Development Life Cycle

## Intent

This skill orchestrates a complete feature development lifecycle through four distinct phases, with all artifacts saved in the user's workspace and state tracked for seamless continuation.

**User invokes:** `@monkeymode for [feature]`

**Agent guides through:**
1. **Phase 1: Design** - Create comprehensive technical design
2. **Phase 2: User Stories** - Decompose into parallelizable stories
3. **Phase 3: Code Spec** - Detailed implementation plan per story
4. **Phase 4: Implementation** - TDD-based code implementation

## Workspace Setup

### On First Invocation

When `@monkeymode` is invoked, **ALWAYS**:

1. **Extract feature name** from user's request (convert to kebab-case)
2. **Check for state file:** Read `{workspace}/.monkeymode/{feature-name}/state.json`
3. **If state file doesn't exist:**
   - **FIRST:** Run the [Branch Setup](#branch-setup) process
   - Create `.monkeymode/{feature-name}/` directory in workspace
   - Create initial `state.json` with feature name from user's request
   - Start Phase 1 (Design)
4. **If state file exists:**
   - Read current phase and resume from there
   - Load context (feature name, team size, selected story, branch, repos, etc.)
   - **If branch not set in state:** Run the [Branch Setup](#branch-setup) process

### Branch Setup

**Optional branch sync setup before starting design work.**

This step allows users to specify their working branch and optionally sync with the main development branch.

#### Step 1: Ask About Q&A Logging

**FIRST QUESTION - Before any other setup:**

Ask the user:
```
"Would you like me to save a log of all our questions and answers during this process?
This creates a qa-log.md file that tracks all decisions and context.

1. Yes - Save Q&A log (recommended for team projects)
2. No - Skip Q&A logging"
```

Store preference in state:
```json
{
  "context": {
    "save_qa_log": true  // or false
  }
}
```

If `save_qa_log` is `true`, create and maintain `qa-log.md` throughout the process.
If `save_qa_log` is `false`, skip all Q&A logging (do not create or update qa-log.md).

#### Step 2: Ask Which Branch

Ask the user:
```
"Which branch are you working on for this feature?
(e.g., dev-alpha, dev-beta, feature/my-feature, main)

Please enter your branch name:"
```

Wait for user response and store in state:
```json
{
  "context": {
    "save_qa_log": true,  // Set in Step 1
    "branch": "user-specified-branch-name"
  }
}
```

#### Step 3: Identify Repos

Ask the user:
```
"Which repositories will this feature touch? (Select all that apply)
1. auriga-web (frontend)
2. auriga-agents (AI agents)
3. auriga-connect (backend API)
4. infrastructure (terraform/db scripts)
5. Other (specify)"
```

Store selected repos in state:
```json
{
  "context": {
    "save_qa_log": true,
    "branch": "user-specified-branch-name",
    "repos": ["auriga-web", "auriga-agents", "auriga-connect", "infrastructure"]
  }
}
```

#### Step 4: Ask About Branch Syncing

Ask the user:
```
"Would you like to sync your branch with 'develop' (or main branch) before starting?
This ensures you have the latest code but will reset your branch.

1. Yes - Sync branch with develop (recommended for new features)
2. No - Skip sync (use if you have work in progress or open PRs)"
```

Store preference in state:
```json
{
  "context": {
    "save_qa_log": true,
    "branch": "user-specified-branch-name",
    "repos": ["auriga-web", "auriga-agents", "auriga-connect"],
    "sync_with_develop": true  // or false
  }
}
```

#### Step 5: Sync Repos (If Opted In)

**ONLY if `context.sync_with_develop` is `true`:**

For each selected repository, execute the sync process with PR-awareness:

```bash
# For each repo in context.repos:
cd {repo_path}
git fetch origin
git checkout {branch}  # user-specified branch

# CRITICAL: Check for open PRs BEFORE syncing
gh pr list --head {branch} --state open --json number,title

# If open PRs exist:
#   - Store PR info in state.json
#   - SKIP sync for this repo
#   - Inform user: "Found open PR #{number}: {title}. Skipping sync to preserve PR. Will work on top of current branch."
#   - Continue to next repo

# If NO open PRs:
#   - Proceed with sync using git reset --hard
git reset --hard origin/develop
git push origin {branch} --force-with-lease
```

**If `context.sync_with_develop` is `false`:**
- Skip all sync operations
- Just verify branch exists and is checked out
- Store `sync_with_develop: false` in state.json

**WHY reset instead of rebase (when syncing):**
- `git rebase` creates new commit SHAs, causing "commits ahead and behind" issues after PRs are merged
- `git reset --hard` makes your branch exactly match `develop`, avoiding commit history divergence
- After each PR merge, always reset to sync cleanly

**WHY check for open PRs (when syncing):**
- `git reset --hard origin/develop` will close any open PRs by removing their commits
- If a PR is open, it means the work is under review and should not be destroyed
- Users should continue working on top of the existing branch until the PR is merged
- After PR merge, the next sync will reset cleanly to the merged develop

**IMPORTANT (when syncing):** 
- If the user has uncommitted work, stash it first:
  ```bash
  git stash
  git reset --hard origin/develop
  git stash pop
  ```
- If there are unpushed commits the user wants to keep, warn them before resetting
- If the branch doesn't exist locally, create it from develop:
  ```bash
  git checkout develop
  git pull origin develop
  git checkout -b {branch}
  git push -u origin {branch}
  ```
- Always check for open PRs before any destructive operations

#### Step 6: Confirm Ready

After branch setup (with or without sync), report status:

**If user opted to sync AND all repos synced (no open PRs):**
```
"All repositories are now synced with develop!

Repos updated:
- auriga-web ({branch}) → Synced with develop ✓
- auriga-agents ({branch}) → Synced with develop ✓
- auriga-connect ({branch}) → Synced with develop ✓

Ready to start Phase 1: Design?"
```

**If user opted to sync BUT some repos have open PRs:**
```
"Branch setup complete!

Repos status:
- auriga-web ({branch}) → Open PR #113. Working on current branch (not synced)
- auriga-agents ({branch}) → Synced with develop ✓
- auriga-connect ({branch}) → Synced with develop ✓

Note: auriga-web has an open PR. After it merges, you can sync that repo.

Ready to start Phase 1: Design?"
```

**If user opted to skip sync:**
```
"Branch setup complete!

Working on branch: {branch}
Repos: auriga-web, auriga-agents, auriga-connect
Sync status: Skipped (working on current branch state)

Ready to start Phase 1: Design?"
```

#### Branch Setup State

Update state.json with branch setup info:
```json
{
  "context": {
    "save_qa_log": true,
    "branch": "user-specified-branch-name",
    "repos": ["auriga-web", "auriga-agents", "auriga-connect"],
    "sync_with_develop": true,  // User preference for syncing
    "branch_setup_completed": true,
    "last_sync": "ISO8601 timestamp",  // Only present if synced
    "open_prs": {  // Only present if sync was attempted and PRs found
      "auriga-web": {
        "pr_number": 113,
        "pr_title": "Add compliance features",
        "skipped_sync": true
      }
    }
  }
}
```

**Notes:**
- If user opted to skip sync, `sync_with_develop` is `false` and `last_sync` is not present
- If resuming work after a long period and sync was enabled, ask user if they want to re-sync to get latest changes
- Always check for open PRs before syncing (if sync is enabled)

### State File Schema

The agent MUST create and maintain this file at `{workspace}/.monkeymode/{feature-name}/state.json`:

```json
{
  "feature_name": "string (kebab-case)",
  "current_phase": "1a",
  "phase_status": {
    "branch_setup": "not_started|in_progress|completed",
    "design_1a": "not_started|in_progress|completed",
    "design_1b": "not_started|in_progress|completed",
    "design_1c": "not_started|in_progress|completed",
    "user_stories": "not_started|in_progress|completed", 
    "code_spec": "not_started|in_progress|completed",
    "implementation": "not_started|in_progress|completed"
  },
  "artifacts": {
    "design_docs": {
      "1a_discovery": ".monkeymode/{feature-name}/design/1a-discovery.md",
      "1b_contracts": ".monkeymode/{feature-name}/design/1b-contracts.md",
      "1c_operations": ".monkeymode/{feature-name}/design/1c-operations.md"
    },
    "user_stories_doc": ".monkeymode/{feature-name}/user_stories.md",
    "code_specs": [],
    "qa_log": ".monkeymode/{feature-name}/qa-log.md"  // Only present if save_qa_log is true
  },
  "context": {
    "save_qa_log": true,  // User preference for Q&A logging (set in Branch Setup Step 1)
    "branch": "user-specified-branch",  // User-specified branch name (set in Branch Setup Step 2)
    "repos": ["auriga-web", "auriga-agents", "auriga-connect", "infrastructure"],
    "sync_with_develop": true,  // User preference for branch syncing (set in Branch Setup Step 4)
    "branch_setup_completed": false,
    "last_sync": "ISO8601 timestamp",
    "open_prs": {},
    "team_size": null,
    "selected_story": null,
    "timeline": null
  },
  "last_updated": "ISO8601 timestamp"
}
```

### Workspace Artifact Structure

All generated files go in the **user's workspace** (NOT in the skills directory):

```
{workspace}/
├── .monkeymode/
│   └── {feature-name}/
│       ├── state.json              # State tracking (agent creates this)
│       ├── qa-log.md               # OPTIONAL: Q&A log (only if user opts in)
│       ├── design/
│       │   ├── 1a-discovery.md      # Phase 1A: Discovery & Core Design
│       │   ├── 1b-contracts.md      # Phase 1B: Detailed Contracts
│       │   └── 1c-operations.md     # Phase 1C: Production Readiness
│       ├── user_stories.md          # Phase 2 output
│       ├── code_specs/
│       │   ├── story-1-spec.md      # Phase 3 output (per story)
│       │   └── story-2-spec.md
│       └── implementation/
│           └── [implementation notes/tracking - optional]
└── src/
    └── [actual production code]    # Phase 4: Code written here
```

**Note:** Implementation code is written directly to your repository's `src/` (or appropriate) directory, not inside `.monkeymode/`. The `implementation/` folder can optionally be used for tracking/notes.

### Q&A Log (Optional)

**CONDITIONAL: Only maintain if user opted in during Branch Setup (Step 1).**

If `context.save_qa_log` is `true`, the agent MUST maintain a `qa-log.md` file at `{workspace}/.monkeymode/{feature-name}/qa-log.md` that captures every question asked and every answer received during the development lifecycle.

If `context.save_qa_log` is `false`, skip all Q&A logging activities (do not create or update qa-log.md).

#### Q&A Log Format

**Only applicable when `save_qa_log` is `true`:**

```markdown
# Q&A Log: {Feature Name}

## Branch Setup
**Date:** {timestamp}

### Q: Which development branch are you working on?
**A:** dev-alpha

### Q: Which repositories will this feature touch?
**A:** auriga-web, auriga-agents, auriga-connect

---

## Phase 1A: Discovery & Core Design
**Date:** {timestamp}

### Q: What problem are we solving?
**A:** Users need a way to save their favorite items for quick access later.

### Q: What's the expected user impact?
**A:** ~10,000 daily active users, accessed 2-3 times per day on average.

### Q: What's the tech stack?
**A:** Next.js frontend, Python FastAPI backend, PostgreSQL database.

[... more Q&As ...]

---

## Phase 1B: Detailed Contracts
**Date:** {timestamp}

### Q: What authentication method should the API use?
**A:** JWT tokens with Firebase Auth.

[... more Q&As ...]

---

## Phase 2: User Stories
**Date:** {timestamp}

### Q: How many developers will work on this?
**A:** 3 developers

### Q: What's your target timeline?
**A:** 2 weeks

[... more Q&As ...]
```

#### When to Update Q&A Log

**Only applicable when `save_qa_log` is `true`:**

Update the Q&A log **immediately after each Q&A exchange**:
1. When asking discovery questions in any phase
2. When asking for clarifications
3. When presenting options and receiving selections
4. When asking for confirmations or approvals

**When `save_qa_log` is `false`:**
- Skip all Q&A logging operations
- Do not create qa-log.md file
- Do not update any Q&A log entries

#### Why Track Q&A

**Benefits of enabling Q&A logging:**

- **Context Preservation:** All decisions and their rationale are recorded
- **Resumption:** Easy to understand context when resuming work
- **Audit Trail:** Complete history of what was discussed and decided
- **Knowledge Transfer:** New team members can understand the full context

**When to disable Q&A logging:**
- Solo projects where context is obvious
- Rapid prototyping where decisions are fluid
- Privacy concerns about recording conversations
- Preference for lightweight artifact generation

## Phase Flow & State Management

### Phase Detection Logic

```
1. Extract feature name from user's request (convert to kebab-case)
2. Read {workspace}/.monkeymode/{feature-name}/state.json
3. If file doesn't exist:
   → Create .monkeymode/{feature-name}/ directory
   → Create state.json with current_phase: "1a"
   → Start Phase 1A
4. If file exists:
   → Read current_phase field (e.g., "1a", "1b", "1c", "2", "3", "4")
   → Resume from that phase/sub-phase
   → Load context for continuity
```

### Phase Transitions

**CRITICAL: Never auto-advance phases. Always ask user for confirmation.**

After completing work in a phase:
1. Save the artifact to workspace
2. Update state.json with completed status
3. **Ask user:** "Phase [N] complete. Ready to move to Phase [N+1]?"
4. If yes → Update state.json current_phase, start next phase
5. If no → Keep in current phase for refinements

### State Update Pattern

After **every significant action**, update the state file:

```python
# Example: After completing design
state = read_json("{workspace}/.monkeymode/{feature-name}/state.json")
state["phase_status"]["design"] = "completed"
state["current_phase"] = 2
state["artifacts"]["design_doc"] = ".monkeymode/{feature-name}/design.md"
state["last_updated"] = datetime.utcnow().isoformat()
write_json("{workspace}/.monkeymode/{feature-name}/state.json", state)
```

## Phase 1A: Discovery & Core Design

### Entry Criteria
- state.json doesn't exist OR current_phase = "1a"
- Branch setup completed (context.branch_setup_completed = true)
- No design/1a-discovery.md exists

### Process
1. **Read phase guide:** Read the file at `phases/01a-design-discovery.md` for detailed methodology
2. **Extract feature name** from user's request (convert to kebab-case)
3. **Verify branch setup:** Ensure [Branch Setup](#branch-setup) has been completed
4. **Create state directory and file** if it doesn't exist:
   - Create directory: `{workspace}/.monkeymode/{feature-name}/design/`
   - Create file: `{workspace}/.monkeymode/{feature-name}/state.json`
   ```json
   {
     "feature_name": "extracted-feature-name",
     "current_phase": "1a",
     "phase_status": {"branch_setup": "completed", "design_1a": "in_progress", ...},
     "context": {"branch": "dev-alpha", "repos": [...], "branch_setup_completed": true, ...},
     ...
   }
   ```
4. **Follow design-skill Steps 1-3 from 01a-design-discovery.md:**
   - **Step 1: Discovery Questions** - Business & technical context
   - **Step 2: Architecture Design** - High-level approach, alternatives, decision
   - **Step 3: Data Model Design** - Core entities and relationships (basic)
5. **Log Q&A (if enabled):** If `context.save_qa_log` is `true`, append all questions and answers to `qa-log.md`
6. **Iterate with user** until they're satisfied with direction
7. **Generate artifact:** Write `{workspace}/.monkeymode/{feature-name}/design/1a-discovery.md`
   - Include: Discovery, Architecture Decision, Core Data Model
8. **Update state:**
   ```json
   {
     "phase_status": {"design_1a": "completed"},
     "artifacts": {
       "design_docs": {
         "1a_discovery": ".monkeymode/{feature-name}/design/1a-discovery.md"
       }
     },
     "last_updated": "..."
   }
   ```
9. **Ask user:** "Phase 1A complete! Ready for Phase 1B (Detailed Contracts)?"
   - If yes → Update current_phase to "1b"
   - If no → Stay in phase 1a for refinements

### Exit Criteria
- 1a-discovery.md created in workspace
- User confirms direction is good
- State updated with design_1a: "completed"

## Phase 1B: Detailed Contracts

### Entry Criteria
- current_phase = "1b"
- 1a-discovery.md exists

### Process
1. **Read phase guide:** Read `phases/01b-design-contracts.md` for detailed methodology
2. **Read previous work:** Load `1a-discovery.md` for context
3. **Follow design-skill Steps 4-6 from 01b-design-contracts.md:**
   - **Step 4: API Contract Design** - Endpoints, requests, responses, errors
   - **Step 5: Integration Points** - Events, external services, dependencies
   - **Step 6: Testing Strategy** - Unit, integration, contract, load tests
4. **Iterate with user** until contracts are clear
5. **Generate artifact:** Write `{workspace}/.monkeymode/{feature-name}/design/1b-contracts.md`
6. **Update state:**
   ```json
   {
     "phase_status": {"design_1b": "completed"},
     "artifacts": {
       "design_docs": {
         "1b_contracts": ".monkeymode/{feature-name}/design/1b-contracts.md"
       }
     },
     "current_phase": "1b",
     "last_updated": "..."
   }
   ```
7. **Ask user:** "Phase 1B complete! Ready for Phase 1C (Production Readiness)?"

### Exit Criteria
- 1b-contracts.md created
- User approves API contracts and integration
- State updated with design_1b: "completed"

## Phase 1C: Production Readiness

### Entry Criteria
- current_phase = "1c"
- 1a-discovery.md and 1b-contracts.md exist

### Process
1. **Read phase guide:** Read `phases/01c-design-operations.md` for detailed methodology
2. **Read previous work:** Load 1a-discovery.md and 1b-contracts.md
3. **Follow design-skill Steps 7-11 from 01c-design-operations.md:**
   - **Step 7: Security Design** - Auth, authorization, input validation
   - **Step 8: Performance & Scalability** - Load expectations, optimization
   - **Step 9: Deployment Strategy** - Rollout, rollback, health checks
   - **Step 10: Observability** - Logging, metrics, tracing, alerting
   - **Step 11: Risk Assessment** - Risks and mitigations
4. **Iterate with user** until production plan is solid
5. **Generate artifact:** Write `{workspace}/.monkeymode/{feature-name}/design/1c-operations.md`
6. **Update state:**
   ```json
   {
     "phase_status": {"design_1c": "completed"},
     "artifacts": {
       "design_docs": {
         "1c_operations": ".monkeymode/{feature-name}/design/1c-operations.md"
       }
     },
     "current_phase": "1c",
     "last_updated": "..."
   }
   ```
7. **Ask user:** "Design complete (all 3 phases)! Ready for Phase 2 (User Stories)?"
   - If yes → Update current_phase to "2"

### Exit Criteria
- 1c-operations.md created
- User confirms complete design
- State updated with design_1c: "completed"

## Phase 2: User Stories

### Entry Criteria
- current_phase = "2"
- All Phase 1 sub-phases completed (1a, 1b, 1c)
- Design files exist: 1a-discovery.md, 1b-contracts.md, 1c-operations.md

### Process
1. **Read phase guide:** Read `phases/02-user-stories.md` for methodology
2. **Read design docs:** Load all three design files (1a, 1b, 1c) for context
3. **CRITICAL - Ask discovery questions FIRST:**
   - "How many developers will work on this?"
   - "What's your target timeline?"
   - "Which components need to communicate?"
4. **Store context in state:**
   ```json
   {
     "context": {
       "team_size": 3,
       "timeline": "2 weeks"
     }
   }
   ```
5. **Follow user-stories-skill methodology:**
   - Decompose into N independent stories (N = team size)
   - ZERO dependencies between Sprint 1 stories
   - Define integration contracts upfront
   - Each story touches different files
6. **Iterate with user** until stories are clear
7. **Generate artifact:** Write `{workspace}/.monkeymode/{feature-name}/user_stories.md`
8. **Update state:**
   ```json
   {
     "phase_status": {"user_stories": "completed"},
     "artifacts": {"user_stories_doc": ".monkeymode/{feature-name}/user_stories.md"},
     "current_phase": 2,
     "last_updated": "..."
   }
   ```
9. **Ask user:** "Which story would you like to implement first?"
   - Wait for user to select a story number
   - Store selection: `state["context"]["selected_story"] = story_number`
   - Ask: "Ready to create code spec for Story {N}?"

### Exit Criteria
- user_stories.md created in workspace
- User selects a story to implement
- State updated with user_stories: "completed"

## Phase 3: Code Spec

### Entry Criteria
- current_phase = "3"
- user_stories.md exists
- User has selected a story number

### Process
1. **Read phase guide:** Read `phases/03-code-spec.md` for methodology
2. **Read context:**
   - Load design.md from workspace
   - Load user_stories.md from workspace
   - Get selected_story from state.json
3. **Follow code-spec-skill methodology:**
   - Analyze the specific user story
   - Ask discovery questions (testing framework, patterns, etc.)
   - Investigate codebase (Read files, Grep, SemanticSearch)
   - Break down into atomic tasks (2-4 hours each)
   - Define function signatures, data structures
   - Specify unit tests and integration tests
4. **Iterate with user** until spec is clear
5. **Generate artifact:** Write `{workspace}/.monkeymode/{feature-name}/code_specs/story-{N}-spec.md`
6. **Update state:**
   ```json
   {
     "phase_status": {"code_spec": "completed"},
     "artifacts": {
       "code_specs": [".monkeymode/{feature-name}/code_specs/story-1-spec.md"]
     },
     "last_updated": "..."
   }
   ```
7. **Ask user:** "Code spec complete! Ready to implement?"

### Exit Criteria
- code_spec.md created for selected story
- User confirms spec is ready
- State updated with code_spec: "completed"

## Phase 4: Implementation

### Entry Criteria
- current_phase = "4"
- code_spec.md exists for selected story

### Process
1. **Read phase guide:** Read `phases/04-implementation.md` for methodology
2. **Read code spec:** Load the code spec from workspace
3. **Follow implementation-skill methodology:**
   - Set up feature branch
   - For each task in code spec:
     - Read existing code
     - Write tests first (TDD)
     - Implement code to pass tests
     - Run linter and type checker
     - Commit with clear message
   - Run integration tests
   - Verify all acceptance criteria met
4. **Write code to workspace:** 
   - Write actual code to your repository's appropriate directories (e.g., `src/`, `tests/`)
   - Optionally track what was implemented in `{workspace}/.monkeymode/{feature-name}/implementation/` for reference
5. **Update state after completion:**
   ```json
   {
     "phase_status": {"implementation": "completed"},
     "last_updated": "..."
   }
   ```
6. **Ask user:** "Implementation complete! What's next?"
   - "Implement another story?" → Back to Phase 3 (select new story)
   - "Add more stories?" → Back to Phase 2
   - "Done!" → Mark project complete

### Exit Criteria
- All code implemented and tested
- All tests passing
- User satisfied with implementation

## Resuming Work

If user invokes `@monkeymode` in a workspace with existing state:

1. **Extract feature name** from user's request
2. **Read state file:** `{workspace}/.monkeymode/{feature-name}/state.json`
3. **Check branch setup:** If `context.branch_setup_completed` is false or missing, run [Branch Setup](#branch-setup) first
4. **Check for stale code or merged PRs (only if sync was enabled):** 
   - If `context.sync_with_develop` is `true` AND (`context.last_sync` is more than a day old OR there were open PRs), ask:
   ```
   "Your last sync was on {date}. Would you like to check for merged PRs and sync with develop to get the latest changes before continuing?"
   ```
   - If user agrees, re-run sync process (Steps 5-6 of Branch Setup)
   - If `context.sync_with_develop` is `false`, skip this check entirely
5. **Announce context:** "Resuming MonkeyMode for '{feature_name}'. Currently in Phase {N}: {phase_name}. Working on branch: {branch}."
6. **Load artifacts:** Read relevant files from workspace
7. **Continue from current phase**

Example:
```
User: "@monkeymode for favorites"
Agent: "Resuming MonkeyMode for 'favorites-feature'. Currently in Phase 3: Code Spec.
        Working on branch: my-feature-branch
        Repos: auriga-web, auriga-agents, auriga-connect
        You selected Story 2 (Vector Store Component). 
        Would you like to continue with the code spec, or change direction?"
```

**Note:** If user doesn't specify feature name, list available features:
```
User: "@monkeymode"
Agent: "Found existing MonkeyMode projects in this workspace:
        1. favorites-feature (Phase 3: Code Spec, branch: feature/favorites)
        2. notifications-system (Phase 2: User Stories, branch: dev-notifications)
        
        Which feature would you like to continue with?"
```

## Phase Reference Guides

The agent should read these files from the skills directory for detailed methodology:

- **Phase 1A:** Read `phases/01a-design-discovery.md` - Discovery, Architecture, Core Data Model
- **Phase 1B:** Read `phases/01b-design-contracts.md` - API Contracts, Integration, Testing
- **Phase 1C:** Read `phases/01c-design-operations.md` - Security, Performance, Deployment, Observability, Risk
- **Phase 2:** Read `phases/02-user-stories.md` - Story decomposition methodology  
- **Phase 3:** Read `phases/03-code-spec.md` - Code spec creation methodology
- **Phase 4:** Read `phases/04-implementation.md` - Implementation methodology

These files contain the detailed steps, patterns, checklists, and examples for each phase.

## Agent Instructions Summary

### On Every Invocation

1. **Extract feature name** from user's request (or list available if not specified)
2. **Read workspace state:** `{workspace}/.monkeymode/{feature-name}/state.json`
3. **Check branch setup:** If not completed, run [Branch Setup](#branch-setup) FIRST
4. **Check for stale code:** If last sync > 1 day, offer to sync with develop
5. **Determine phase:** Extract current_phase or start at 1a
6. **Load phase guide:** Read appropriate `phases/{N}-*.md` file
7. **Load workspace artifacts:** Read relevant design/stories/specs
8. **Execute phase:** Follow methodology from phase guide
9. **Save artifacts:** Write to `{workspace}/.monkeymode/{feature-name}/...` or `{workspace}/.monkeymode/{feature-name}/implementation/...`
10. **Update Q&A log (if enabled):** If `context.save_qa_log` is `true`, append Q&A to `qa-log.md`
11. **Update state:** Write updated `{workspace}/.monkeymode/{feature-name}/state.json`
12. **Ask for confirmation:** Before advancing to next phase

### State Updates

Update `{workspace}/.monkeymode/{feature-name}/state.json` after:
- Creating initial state
- Completing any phase
- Generating any artifact
- User making selections (story number, team size, etc.)
- Advancing to next phase

### Q&A Log Updates (Conditional)

**ONLY if `context.save_qa_log` is `true`:**

Update `{workspace}/.monkeymode/{feature-name}/qa-log.md` after:
- Every question asked and answered
- Every clarification received
- Every option presented and selection made
- Every confirmation or approval received

**If `context.save_qa_log` is `false`:**
- Skip all Q&A log updates
- Do not create or maintain qa-log.md file

### Never Do

- ❌ Auto-advance phases without user confirmation
- ❌ Save artifacts to skills directory
- ❌ Skip state updates
- ❌ Assume phase without reading state
- ❌ Create artifacts without proper workspace paths
- ❌ Forget to load context when resuming
- ❌ Skip branch setup on new features
- ❌ Start design work without syncing with develop
- ❌ Use `git rebase` to sync branches (causes commit history divergence)
- ❌ Use `git reset --hard` when there are open PRs (closes the PR)
- ❌ Assume which branch (dev-alpha/dev-beta) without asking
- ❌ **Skip logging Q&A exchanges to qa-log.md**

### Always Do

- ✅ Extract feature name first
- ✅ Run branch setup before starting any new feature
- ✅ Ask which branch (dev-alpha or dev-beta) the user is working on
- ✅ **Check for open PRs before syncing** - use `gh pr list --head {branch} --state open`
- ✅ Skip sync for repos with open PRs (work on top of current branch)
- ✅ Sync repos without open PRs using `git reset --hard origin/develop`
- ✅ Track open PRs in state.json so user knows to re-sync after merge
- ✅ Read state from `.monkeymode/{feature-name}/state.json`
- ✅ Save all artifacts to workspace
- ✅ Update state after significant actions
- ✅ **Log all Q&A exchanges to `qa-log.md` immediately**
- ✅ Ask user before phase transitions
- ✅ Load phase guides for detailed methodology
- ✅ Use workspace-relative paths for all artifacts
- ✅ Offer to re-sync if last sync was more than a day ago or if PRs may have merged

## Example: Complete Flow

```
# Session 1
User: "@monkeymode for favorites feature"
Agent: [Extracts feature_name: "favorites-feature"]
       [No state.json exists - starting fresh]
       
       "Starting MonkeyMode for 'favorites-feature'!
        
        First, would you like me to save a log of all our Q&A during this process?
        1. Yes - Save Q&A log (recommended for team projects)
        2. No - Skip Q&A logging"
User: "1"
Agent: "Great! I'll maintain a qa-log.md file.
        
        Which branch are you working on for this feature?
        (e.g., dev-alpha, feature/favorites, main)"
User: "feature/favorites"
Agent: "Which repositories will this feature touch?
        1. auriga-web (frontend)
        2. auriga-agents (AI agents)
        3. auriga-connect (backend API)
        4. infrastructure (terraform/db scripts)"
User: "1, 2, 3"
Agent: "Would you like to sync your branch with 'develop' before starting?
        1. Yes - Sync branch with develop (recommended for new features)
        2. No - Skip sync (use if you have work in progress)"
User: "1"
Agent: [Syncing repos with develop...]
       [Checking for open PRs in each repo first...]
       
       "Checking auriga-web (feature/favorites) for open PRs..."
       [gh pr list --head feature/favorites --state open]
       [No open PRs found]
       "Syncing auriga-web (feature/favorites) with develop..."
       [git fetch origin && git checkout feature/favorites && git reset --hard origin/develop && git push origin feature/favorites --force-with-lease]
       
       "Checking auriga-agents (feature/favorites) for open PRs..."
       [gh pr list --head feature/favorites --state open]
       [No open PRs found]
       "Syncing auriga-agents (feature/favorites) with develop..."
       [git fetch origin && git checkout feature/favorites && git reset --hard origin/develop && git push origin feature/favorites --force-with-lease]
       
       "Checking auriga-connect (feature/favorites) for open PRs..."
       [gh pr list --head feature/favorites --state open]
       [No open PRs found]
       "Syncing auriga-connect (feature/favorites) with develop..."
       [git fetch origin && git checkout feature/favorites && git reset --hard origin/develop && git push origin feature/favorites --force-with-lease]
       
       "All repositories are now synced with develop!
        
        Repos updated:
        - auriga-web (feature/favorites) → Synced with develop ✓
        - auriga-agents (feature/favorites) → Synced with develop ✓
        - auriga-connect (feature/favorites) → Synced with develop ✓
        
        Ready to start Phase 1A: Discovery & Core Design?"
User: "Yes"
Agent: [Creates .monkeymode/favorites-feature/state.json with branch info]
       [Reads phases/01a-design-discovery.md]
       "Starting Phase 1A: Discovery & Core Design for 'favorites-feature'
        Let me understand the business context..."
       [... discovery conversation ...]
       [Writes .monkeymode/favorites-feature/design/1a-discovery.md]
       [Updates state: design_1a completed, current_phase: "1a"]
       "Phase 1A complete! Ready for Phase 1B (Detailed Contracts)?"
User: "Yes"
Agent: [Updates state: current_phase = "1b"]
       [Reads phases/01b-design-contracts.md]
       "Phase 1B: Detailed Contracts
        Based on your design, let me specify the API contracts..."
       [... API design conversation ...]
       [Writes .monkeymode/favorites-feature/design/1b-contracts.md]
       "Phase 1B complete! Ready for Phase 1C (Production Readiness)?"
User: "Yes"
Agent:        [Writes .monkeymode/favorites-feature/design/1c-operations.md]
       "Design complete (all 3 phases)! Ready for Phase 2 (User Stories)?"
User: "Yes"
Agent: [Updates state: current_phase = "2"]
       [Reads phases/02-user-stories.md]
       "Phase 2: User Stories
        How many developers will work on this?"
       [... creates stories ...]
       [Writes .monkeymode/favorites-feature/user_stories.md]
       "Which story to implement first?"
User: "Story 1"
Agent: [Updates state: selected_story = 1]
       "Ready for Phase 3 (Code Spec)?"

# Session 2 (later, different conversation)
User: "@monkeymode for favorites"
Agent: [Reads .monkeymode/favorites-feature/state.json]
       [Sees current_phase = "3", selected_story = 1, branch = "feature/favorites"]
       [Sees sync_with_develop = true and last_sync was 3 days ago]
       [Checks open_prs - was empty after initial sync]
       
       "Resuming MonkeyMode for 'favorites-feature'
        Working on branch: feature/favorites
        Repos: auriga-web, auriga-agents, auriga-connect
        
        Note: Your last sync was 3 days ago. 
        Would you like to sync with develop to get the latest changes?"
User: "Yes, please sync"
Agent: [Logs Q&A if save_qa_log is true]
       [Checks for open PRs in each repo using gh pr list]
       [Syncs repos without open PRs using git reset --hard]
       [Updates state.json with new sync time]
       "All repos updated! Ready to create code spec for Story 1?"
       [Continues from where left off...]
```

**Q&A Log Example (qa-log.md after Session 1, if enabled):**
```markdown
# Q&A Log: favorites-feature

## Branch Setup
**Date:** 2026-01-27T10:00:00Z

### Q: Would you like me to save a log of all our Q&A during this process?
**A:** Yes - Save Q&A log

### Q: Which branch are you working on for this feature?
**A:** feature/favorites

### Q: Which repositories will this feature touch?
**A:** auriga-web, auriga-agents, auriga-connect

### Q: Would you like to sync your branch with 'develop' before starting?
**A:** Yes - Sync branch with develop

---

## Phase 1A: Discovery & Core Design
**Date:** 2026-01-27T10:05:00Z

### Q: What problem are we solving?
**A:** Users need a way to save their favorite items for quick access later.

### Q: What's the expected user impact?
**A:** ~10,000 daily active users, accessed 2-3 times per day.

### Q: What's the tech stack?
**A:** Next.js frontend, Python FastAPI backend, PostgreSQL database.

### Q: Phase 1A complete! Ready for Phase 1B?
**A:** Yes

---

## Phase 1B: Detailed Contracts
**Date:** 2026-01-27T11:00:00Z

### Q: What authentication method should the API use?
**A:** JWT tokens with Firebase Auth.

[... continues for all phases ...]
```

## Quality Standards

Every phase output must meet quality standards defined in phase guides:
- **Design:** Top 1% quality - performance, scalability, security
- **User Stories:** Zero dependencies in Sprint 1, fully parallelizable
- **Code Spec:** Atomic tasks, complete signatures, test specifications
- **Implementation:** Production-ready, tested, follows existing patterns

## Support

If user asks for help mid-process:
- Read state.json to understand current context
- Provide guidance relevant to current phase
- Offer to continue, restart, or skip to different phase
- Always maintain state consistency
