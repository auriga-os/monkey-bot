---
name: review-phase
description: Review monkeymode phase documents (design, user stories, code spec) and produce concise review summaries. Use when the user asks to review a phase doc, check a phase output, or validate a monkeymode artifact.
---

# Review Phase Documents

## Purpose

Generate concise, actionable reviews of monkeymode phase outputs. Each review is capped at 100 lines with exactly 3 sections: Summary, Double Check These Sections, and Potential Issues.

## When to Use

- User asks to "review" a phase document
- User wants to validate a monkeymode output
- User requests "check this doc" or "review the design/stories/spec"
- Before advancing to next phase in monkeymode workflow

## Input

Path to any monkeymode phase MD file:
- `.monkeymode/{feature}/design/1a-discovery.md`
- `.monkeymode/{feature}/design/1b-contracts.md`
- `.monkeymode/{feature}/design/1c-operations.md`
- `.monkeymode/{feature}/user_stories.md`
- `.monkeymode/{feature}/code_specs/story-{N}-spec.md`

## Output

File: `review-{original-filename}.md` in the same directory as input
Length: Hard cap at 100 lines (prioritize by severity if needed)

## Review Structure

### Section 1: Summary (15-25 lines max)

**Format:**
```markdown
# Review: {Document Name}

**Phase:** [Design 1A / Design 1B / Design 1C / User Stories / Code Spec]
**Reviewed:** {timestamp}

## Overview
[2-3 sentence summary of what this doc covers]

## Key Artifacts Defined
- [Bullet list of key decisions/components/contracts in the doc]
- [...]

## Dependencies
[Note any dependencies on prior phase outputs or external systems]
```

**What to include:**
- Which phase this belongs to (1A, 1B, 1C, 2, or 3)
- High-level summary (2-3 sentences max)
- Key decisions or artifacts defined (bulleted list)
- Dependencies on prior phases or external systems

**What to skip:**
- Generic praise or commentary
- Detailed explanations
- Anything not essential to understanding scope

### Section 2: Double Check These Sections (30-40 lines max)

**Purpose:** Flag sections that need human review before moving forward.

**Flag these patterns:**

1. **Vague language:** "TBD", "TODO", "maybe", "probably", "we'll see", "later"
2. **Inconsistencies:** Naming mismatches, scope drift vs prior phases, conflicting requirements
3. **Missing criteria:** No acceptance criteria, success metrics, or validation approach defined
4. **Unjustified assumptions:** Assumptions stated without rationale or data
5. **Missing trade-offs:** Technical choices without pros/cons or alternatives discussion
6. **Cross-phase gaps:** Requirements from prior phases not addressed here

**Format (one bullet per item):**
```markdown
## Double Check These Sections

- **{Section Name}**: {One-line reason it needs review}
- **{Section Name}**: {One-line reason it needs review}
```

**Example bullets:**
- **API Endpoints > POST /favorites**: No error response codes defined
- **Data Model > User table**: Inconsistent with 1A design (1A uses "account" terminology)
- **Story 2 > Acceptance Criteria**: Contains "TBD" - needs specific success metrics
- **Performance section**: States "should be fast" without quantitative targets
- **Integration Points**: References "auth service" not mentioned in prior phases

**Rules:**
- One bullet = one issue
- Reference exact section headers
- One line per bullet
- Be specific, not generic
- If doc is clean, write: "No sections require additional review."

### Section 3: Potential Issues (20-30 lines max)

**Purpose:** Identify gaps, conflicts, risks, and scope creep.

**Categories:**

1. **Gaps:** Requirements or stories from prior phases not addressed
2. **Conflicts:** Contradictions within doc or against prior phase outputs
3. **Risks:** Blockers to implementation (unclear ownership, missing contracts, dependencies, scaling concerns)
4. **Scope Creep:** Features introduced without justification from prior phases

**Format (one bullet per issue):**
```markdown
## Potential Issues

### Gaps
- {One-line description of missing requirement}

### Conflicts
- {One-line description of contradiction}

### Risks
- {One-line description of risk/blocker}

### Scope Creep
- {One-line description of unjustified addition}
```

**Example bullets:**
- **Gap:** 1A design specified caching layer, not mentioned in 1B API contracts
- **Conflict:** User Stories splits "favorites" into 3 stories, but 1C operations treats as single deploy unit
- **Risk:** Story 2 depends on vector store setup with no owner or timeline defined
- **Scope Creep:** Code spec adds real-time sync feature not present in design or stories

**Rules:**
- One bullet = one issue
- One line per bullet
- Actionable and specific
- If no issues in a category, omit that subsection
- If doc is solid, write: "No significant issues identified."

## Behavioral Rules

1. **Never suggest fixes** - Only identify what needs review
2. **Be specific** - Reference exact sections, line content, or prior doc statements
3. **No fluff** - Engineering peer tone, direct, factual
4. **Prioritize by severity** - If exceeding 100 lines, cut lowest-priority items
5. **Don't invent issues** - If doc is clean, say so briefly
6. **Hard cap** - Never exceed 100 lines total

## Execution Steps

1. **Read the input doc** - Understand phase, content, structure
2. **Identify phase** - Determine if this is 1A, 1B, 1C, 2, or 3
3. **Read prior phases** - Load context from earlier phase docs if they exist
4. **Generate Section 1 (Summary)** - Keep to 15-25 lines
5. **Generate Section 2 (Double Check)** - Flag vague/inconsistent sections, 30-40 lines
6. **Generate Section 3 (Potential Issues)** - Gaps, conflicts, risks, scope creep, 20-30 lines
7. **Count total lines** - If > 100, prioritize by severity and cut
8. **Write output** - Save as `review-{original-filename}.md` in same directory

## Prior Phase Context

When reviewing a phase doc, load these prior phases for context:

**Reviewing 1B (Contracts):**
- Read: 1a-discovery.md

**Reviewing 1C (Operations):**
- Read: 1a-discovery.md, 1b-contracts.md

**Reviewing User Stories:**
- Read: 1a-discovery.md, 1b-contracts.md, 1c-operations.md

**Reviewing Code Spec:**
- Read: design/*.md, user_stories.md

## Line Counting

Include in line count:
- All section headers (# and ##)
- All body text lines
- All bullet points
- Empty lines between sections

Exclude from line count:
- Markdown frontmatter (if any)
- The review filename itself

## Example Output Structure

```markdown
# Review: 1a-discovery.md

**Phase:** Design 1A - Discovery & Core Design
**Reviewed:** 2026-02-11T14:30:00Z

## Overview
Defines a user favorites system with PostgreSQL storage and REST API. Covers core architecture, data model, and high-level tech stack decisions.

## Key Artifacts Defined
- Architecture: REST API + PostgreSQL with Next.js frontend
- Core entities: User, Favorite, Item
- High-level endpoints: POST /favorites, GET /favorites, DELETE /favorites/{id}

## Dependencies
- Existing auth system for user identity
- Existing item catalog for favoritable items

---

## Double Check These Sections

- **Data Model > Favorite entity**: No index strategy defined for user_id queries (could impact perf)
- **Architecture Decision**: States "may need caching later" - clarify if in scope
- **Core Entities > Item**: Inconsistent with frontend (frontend uses "resource" terminology)

---

## Potential Issues

### Gaps
- No mention of favorite limits per user (business requirement from kickoff)

### Conflicts
- Architecture section implies sync API, but user story 3 requires async processing

### Risks
- No error handling strategy defined (blocking for 1B contracts phase)
- Item catalog integration unclear - missing API contract

---

**Total lines: 45**
```

## Quality Checks

Before finalizing review:
- ✅ Exactly 3 sections present
- ✅ Line count ≤ 100 (prioritize by severity if needed)
- ✅ All bullets are one line each
- ✅ Specific section references (not generic)
- ✅ Engineering peer tone (direct, no fluff)
- ✅ Output filename: `review-{original-filename}.md`
- ✅ Output in same directory as input
