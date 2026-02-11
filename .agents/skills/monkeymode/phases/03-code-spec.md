---
name: code-spec-skill
description: Guides the creation of detailed implementation plans from user stories. Used by the DEVELOPER-PROMPT during Phase 1 to create code specs before implementation.
---

# Code Spec Skill

## Purpose
Transform a user story into a detailed, task-by-task implementation plan that a developer (human or AI) can execute systematically.

## File Size Targets for AI Agent Efficiency

**CRITICAL: Code specs must be concise yet complete.**

| Story Size | Target Lines | Max Lines |
|------------|--------------|-----------|
| Small (S)  | 200-400      | 600       |
| Medium (M) | 400-800      | 1000      |
| Large (L)  | 800-1500     | 2000      |

**Why This Matters:**
- AI agents can infer implementation from patterns
- Excessive examples waste token budget
- Redundant checklists reduce clarity
- One complete example > many partial examples

**Optimization Strategies:**
1. **Show ONE complete code example**, reference it for similar tasks
2. **Use bullet lists** for test cases instead of full test code
3. **Simple tasks get simple specs** (3-5 lines) when pattern exists
4. **Complex tasks get detail** when pattern is new or tricky
5. **Consolidate checklists** - one at end, not per task

## Core Principles

### Read Before Writing
```
ALWAYS read existing files before planning modifications.
Understand:
- Code style and conventions
- Existing patterns and abstractions
- How similar features are implemented
- Testing approaches used
```

### Never Assume
```
If you don't know something, ASK.
Examples:
- "What testing framework do you use?"
- "How do you handle database migrations?"
- "What's the error handling pattern?"
- "Are there existing utilities I should use?"
```

### Atomic Tasks
```
Each task should be:
- Completable in one focused session
- Independently testable
- Committable as a logical unit

Bad: "Implement favorites feature"
Good: "Create favorites repository with CRUD methods"
```

### Follow Existing Patterns
```
Don't invent new patterns unless absolutely necessary.
If the codebase uses:
- Repository pattern → use Repository pattern
- Class-based → use classes
- Functional → use functions
- pytest → use pytest (don't switch to unittest)
```

## Code Spec Creation Process

### Step 1: Story Analysis & Discovery Questions (ALWAYS ASK FIRST!)

#### Parse the User Story
Extract:
- **Business value**: What problem are we solving?
- **Acceptance criteria**: What defines "done"?
- **Technical context**: Which files, patterns, design decisions?
- **Dependencies**: What must exist before we start?
- **Out of scope**: What should we NOT do?

#### Discovery Questions - Ask Before Planning

**CRITICAL: Before creating any code spec, ask clarifying questions.**

**Technical Context Questions:**
- "Which specific files should I modify?"
- "Are there similar implementations I should follow?"
- "What testing framework and version do you use?"
- "What's your error handling pattern?"
- "How do you handle database migrations?"
- "Are there existing utilities I should reuse?"

**Requirements Clarification:**
- "What's the expected data volume/scale?"
- "Are there specific performance requirements?"
- "What error cases should I handle?"
- "Should I handle edge cases like [specific scenario]?"
- "What's the expected behavior when [ambiguous situation]?"

**Pattern & Convention Questions:**
- "What's your file naming convention?"
- "How do you organize imports?"
- "What's your commit message format?"
- "Do you use feature flags for this?"
- "What's your branching strategy?"

### Step 2: Codebase Investigation

**CRITICAL: Read existing code BEFORE proposing any implementation plan.**

#### Read Existing Code
Before planning, read:
1. **Files mentioned in story** - Understand current state
2. **Pattern references** - See how similar features work
3. **Related tests** - Understand testing approach
4. **Shared utilities** - Identify reusable code

#### Ask About What You Find
As you investigate, ask:
- "I see you use [pattern] in [file]. Should I follow the same approach?"
- "I found [utility] that might help. Should I use it or create something new?"
- "The existing tests use [approach]. Should I match that style?"
- "I notice [inconsistency]. Which pattern should I follow?"

#### Document Conventions
Document what you discover:
- **File naming**: `snake_case.py` for modules
- **Import ordering**: Standard library → Third-party → Local (PEP 8)
- **Class structure**: `__init__` → Public methods → Private methods (`_method`)
- **Function naming**: `snake_case` for functions and methods
- **Error handling**: Custom exception classes, try-except blocks
- **Logging**: Structured logging (JSON), levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

**Present findings and ask for confirmation:**
"I've analyzed the codebase and found these conventions: [list]. Should I follow these for the new code?"

### Step 3: Task Decomposition

**Before breaking down tasks, ask:**
- "Does this story require a database migration?"
- "Are there any existing components I should integrate with?"
- "Should I implement this in phases or all at once?"
- "What's the priority order if we need to ship incrementally?"

#### Break Down by Layer
Typical order for full-stack features:
```
1. Database Migration (if needed)
2. Data Access Layer (Repository/DAO)
3. Business Logic Layer (Service)
4. API Layer (Controller/Routes)
5. Integration Tests
```

**Present the breakdown and ask:**
"I'm planning to break this into [N] tasks: [list]. Does this order make sense for your workflow?"

#### Define Task Dependencies
```
Task 1: Database Migration
    │
    ├─→ Task 2: Repository Layer
    │       │
    │       └─→ Task 3: Service Layer
    │               │
    │               └─→ Task 4: API Layer
    │                       │
    │                       └─→ Task 5: Integration Tests
```

### Step 4: Define Contracts

#### Function Signatures
For each component, specify:
```python
from uuid import UUID

async def add_favorite(self, user_id: UUID, product_id: UUID) -> Favorite:
    """Add a product to user's favorites.
    
    Args:
        user_id: User ID (UUID format)
        product_id: Product ID (UUID format)
        
    Returns:
        Created favorite object
        
    Raises:
        NotFoundError: If product doesn't exist
        ConflictError: If already favorited
    """
```

#### Data Structures
```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class Favorite:
    """Favorite entity."""
    id: UUID
    user_id: UUID
    product_id: UUID
    created_at: datetime

@dataclass
class PaginationParams:
    """Pagination parameters."""
    offset: int
    limit: int
```

#### Abstract Base Classes (for contracts)
```python
from abc import ABC, abstractmethod

class FavoritesRepositoryInterface(ABC):
    """Repository contract for favorites."""
    
    @abstractmethod
    async def add(self, user_id: UUID, product_id: UUID) -> Favorite:
        """Add favorite to storage."""
        pass
```

#### Error Types
```python
class NotFoundError(Exception):
    """Raised when an entity is not found."""
    
    def __init__(self, entity: str, entity_id: str):
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} with id {entity_id} not found")
```

### Step 5: Specify Tests

**Philosophy**: Show ONE complete test file example, then reference it for all other tasks.

#### Test Specification Approach

**For the first complex task only**, provide complete test code showing:
- Test file structure and imports
- Setup/teardown patterns
- Mocking approach
- Assertion style
- 3-5 representative test cases (not exhaustive)

**For all subsequent tasks**, use concise bullet list:
```markdown
**Test Cases** (follow pattern in [reference test file]):
- Success case: [description]
- Error case 1: [description] → [expected error]
- Error case 2: [description] → [expected error]
- Edge case: [description]
```

#### Integration Test Scenarios
```markdown
| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Happy path | 1. POST /favorites<br>2. GET /favorites | Favorite appears in list |
| Duplicate handling | 1. POST /favorites<br>2. POST same favorite | Second call returns 409 |
| Pagination | 1. Create 100 favorites<br>2. GET /favorites?limit=50 | Returns 50 items with hasMore=true |
```

### Step 6: Create Implementation Plan

#### Task Template

**Choose template based on complexity:**

**For Simple/Repetitive Tasks** (utils, helpers, straightforward CRUD):
```markdown
### Task N: [Task Name]
**Dependencies:** [Task numbers or "None"]
**Files**: [path] (create), [path] (modify)
**Pattern**: Follow [reference file]
**Implementation**: [2-4 sentence algorithm description]
**Tests**: [Bullet list of 3-5 test scenarios]
```

**For Complex/Novel Tasks** (new patterns, integrations, security-critical):
```markdown
### Task N: [Task Name]
**Dependencies:** [Task numbers or "None"]

**Files to Create:**
| File | Purpose |
|------|---------|
| [path] | [description] |

**Files to Modify:**
| File | Change |
|------|--------|
| [path] | [description] |

**Function Signatures:**
```[language]
[Key interfaces only - not full implementation]
```

**Pattern Reference:**
Follow existing pattern in [path/to/similar/file]
[Explain any deviations from pattern and why]

**Implementation Algorithm:**
1. [Critical step with potential gotchas]
2. [Step with non-obvious logic]
3. [Integration point requiring care]

**Test Cases** (follow pattern in [reference test]):
- Success: [description]
- Error case 1: [description] → [expected error]
- Error case 2: [description] → [expected error]
- Edge case: [description]

**Critical Notes:**
- [Only include gotchas, security concerns, performance issues]
```

**Why**: Simple tasks don't need elaborate specs. AI agents waste tokens reading obvious details.

## Code Spec Output Format

**IMPORTANT: Optimize for AI Agent Efficiency**
- **Show complete code examples ONLY when pattern is new/complex**
- **Reference established patterns for repetitive tasks**
- **Use bullet lists over tables for test cases**
- **Consolidate redundant checklists**
- **Focus on "why" not "what" (AI knows syntax)**

```markdown
# Code Spec: [Story Title]

**Story:** [Reference to user story]
**Design Reference:** [Section from design.md]
**Author:** [Your name]
**Date:** [Date]

## Implementation Summary
- **Files to Create:** [count] files
- **Files to Modify:** [count] files
- **Tests to Add:** [count] test files
- **Estimated Complexity:** [S/M/L based on story size]

## Codebase Conventions
[Document discovered conventions - keep concise]

**File/Function Naming:** [convention]
**Import Order:** [convention]
**Error Handling:** [pattern with example file]
**Testing Framework:** [framework + version + config file]
**Type Checking:** [tool + strictness level]

## Technical Context
**Key Gotchas**: [Only critical/non-obvious items]
**Reusable Utilities**: [Existing code to leverage]
**Integration Points**: [What this touches]

## Task Breakdown

### Task 1: [Name]
[Use appropriate template - simple vs complex]

---

### Task 2: [Name]
[Use appropriate template - simple vs complex]

---

[Continue for all tasks]

## Dependency Graph
```
[Visual representation - ONLY if dependencies are non-linear]
```

## Reference Code Examples

**[Function Type] Pattern** (from [file]):
```[language]
[ONE complete example showing established pattern]
```

**Test Pattern** (from [file]):
```[language]
[ONE complete test file showing 3-5 test cases]
```

[ONLY include 1-2 reference examples total, not per task]

## Implementation Notes
[Consolidated section for]:
- Performance considerations
- Security notes
- Deployment requirements
- Post-deployment verification

## Final Verification
[SINGLE consolidated checklist, not per-task]

**Functionality:**
- [ ] All acceptance criteria met
- [ ] Edge cases handled

**Code Quality:**
- [ ] Follows existing patterns
- [ ] No security vulnerabilities

**Testing:**
- [ ] Tests pass
- [ ] Coverage meets standard

**Build:**
- [ ] Builds successfully
- [ ] Linter/type checker pass
```

**Target File Size**: 800-1200 lines for Large stories, 400-600 for Medium, 200-300 for Small

## Example: Task Specifications

**Example 1: Complex Task (New Pattern)**

```markdown
### Task 2: Create Favorites Repository

**Dependencies:** Task 1 (Database Migration)

**Files to Create:**
| File | Purpose |
|------|---------|
| `src/favorites/repository.py` | Data access layer for favorites |
| `tests/favorites/test_repository.py` | Unit tests for repository |

**Files to Modify:**
| File | Change |
|------|--------|
| `src/favorites/__init__.py` | Export repository class |

**Function Signatures:**
```python
from abc import ABC, abstractmethod
from uuid import UUID

class FavoritesRepositoryInterface(ABC):
    @abstractmethod
    async def add(self, user_id: UUID, product_id: UUID) -> Favorite:
        """Add favorite. Raises: ConflictError if duplicate."""
        pass
    
    @abstractmethod
    async def remove(self, user_id: UUID, product_id: UUID) -> None:
        """Remove favorite. Raises: NotFoundError if not found."""
        pass
    
    @abstractmethod
    async def find_by_user(self, user_id: UUID, pagination: PaginationParams) -> list[Favorite]:
        """Get paginated favorites for user."""
        pass
    
    @abstractmethod
    async def exists(self, user_id: UUID, product_id: UUID) -> bool:
        """Check if favorited."""
        pass
```

**Pattern Reference:** Follow `src/users/repository.py`:
- SQLAlchemy AsyncSession injection
- Custom error classes (NotFoundError, ConflictError)
- IntegrityError → ConflictError for duplicates

**Implementation Algorithm:**
1. Inject AsyncSession via constructor
2. For add(): Use try-except to catch IntegrityError, raise ConflictError
3. For remove(): Check exists first, raise NotFoundError if missing
4. For find_by_user(): Apply offset/limit, order by created_at DESC
5. For exists(): Use COUNT query, return bool

**Test Cases** (follow pattern in `tests/users/test_repository.py`):
- add() with valid input → Returns Favorite with all fields
- add() duplicate → Raises ConflictError
- remove() existing → Success
- remove() non-existent → Raises NotFoundError
- find_by_user() with pagination → Correct page returned
- exists() true/false cases

**Critical Notes:**
- Use parameterized queries to prevent SQL injection
- Ensure AsyncSession is properly managed (no resource leaks)
```

**Example 2: Simple Task (Established Pattern)**

```markdown
### Task 5: Add GET /favorites Endpoint

**Dependencies:** Task 3 (Service Layer)
**Files**: `src/api/favorites.py` (modify), `tests/api/test_favorites.py` (create)
**Pattern**: Follow GET /users endpoint in `src/api/users.py`
**Implementation**: Extract user_id from JWT, call service.get_favorites(), apply pagination params from query string, return JSON
**Tests**:
- Authenticated request → Returns 200 with favorites array
- Unauthenticated → Returns 401
- Invalid pagination params → Returns 400
- User has no favorites → Returns empty array
```

**Why These Examples Work:**
- Example 1: Complex/new pattern → Full details with gotchas
- Example 2: Simple/repetitive → Minimal spec, references establish pattern
- AI agent can infer implementation details from patterns
- Saves ~60% file size without losing critical information

## Quality Checklist

Before finalizing code spec, verify:

### Completeness
- [ ] Every acceptance criterion has corresponding tasks
- [ ] Critical function signatures are defined (not ALL signatures)
- [ ] Test approach is clear (pattern + cases, not full code)
- [ ] Dependencies between tasks are explicit

### Efficiency
- [ ] File size is appropriate for story complexity (S: 200-400, M: 400-800, L: 800-1500 lines)
- [ ] Redundant examples eliminated (one pattern reference, not per-task)
- [ ] Simple tasks use concise template
- [ ] Complex tasks get detailed treatment

### Actionability
- [ ] Each task is independently implementable
- [ ] Pattern references are specific (file + line/function)
- [ ] Critical gotchas are highlighted
- [ ] AI agent has enough context without over-specification

## Anti-Patterns to Avoid

❌ **Over-Specification**
```
Showing complete implementation code for every function
→ Wastes tokens, AI can write code from good specs
```

✅ **Right-Sized Specification**
```
Show ONE complete example, then reference pattern
→ AI pattern-matches efficiently
```

---

❌ **Redundant Test Code**
```
Full test file for every task (80+ lines each)
→ Bloats file size by 40%+
```

✅ **Test Case Lists**
```
- Success case: [description]
- Error case: [description] → [expected error]
(Follow pattern in test_repository.py)
→ AI writes tests from bullet points
```

---

❌ **Vague References**
```
"Follow existing pattern"
→ AI doesn't know which pattern
```

✅ **Specific References**
```
"Follow repository pattern in src/users/repository.py lines 45-67"
→ AI can read and replicate exact pattern
```

---

❌ **Large Monolithic Tasks**
```
Task 1: Implement entire favorites feature
→ Too large, hard to track progress
```

✅ **Atomic Tasks**
```
Task 1: Database migration
Task 2: Repository layer
Task 3: Service layer
→ Each completable in one session
```

---

❌ **Assuming Knowledge**
```
"Use standard error handling"
→ What is "standard"?
```

✅ **Explicit References**
```
"Use error handling from src/common/errors/
- NotFoundError for missing entities
- ConflictError for duplicates"
```

---

❌ **Checklist Duplication**
```
Verification checklist after EVERY task
→ Same items repeated 8+ times
```

✅ **Consolidated Checklist**
```
Single "Final Verification" section at end
→ Lists each check once
```
