---
name: user-stories-skill
description: Guides the decomposition of designs into parallelizable user stories with detailed technical context. Used by the LEAD-PROMPT during Phase 2.
---

# User Stories Skill

## Purpose
Transform a technical design into actionable user stories that developers can implement independently and in parallel.

## Discovery Questions (ALWAYS ASK FIRST!)

Before creating any stories, you MUST ask:

1. **"How many developers will work on this?"**
   - Create up to N stories for Sprint 1 (1 per developer)
   - If fewer independent components than developers, create fewer stories
   - Each story must be 100% independent (ZERO dependencies)

2. **"What's your target timeline?"**
   - Helps size stories appropriately (S: 1-2 days, M: 3-5 days)

3. **"Which components need to communicate?"**
   - Define API contracts upfront for parallel development

## Core Principles

### N Developers = N Independent Stories (NO Dependencies)

```
✅ GOOD (3 devs, truly parallel):
Story 1: Embeddings Component (defines EmbeddingsInterface)
Story 2: Storage Component (defines StorageInterface)
Story 3: Config Component (defines ConfigInterface)
→ All use mocks for dependencies, integration happens Sprint 2

❌ BAD (has dependencies, NOT parallel):
Story 1: Database schema
Story 2: API endpoints (depends on Story 1) ← BLOCKS developer 2!
Story 3: UI components (depends on Story 2) ← BLOCKS developer 3!
```

### Never Assume - Always Ask
- Don't assume story size - ask about team velocity and complexity
- Don't assume priority - ask about business value
- If design is unclear, ask before creating stories

## Story Creation Process

### Step 1: Decompose by Independent Components

**For N developers, create N completely independent stories:**

```
Each Sprint 1 story must:
✅ Touch completely different files/modules
✅ Have ZERO dependencies on other stories
✅ Define clear interfaces/contracts for integration
✅ Use mocks for any external dependencies
✅ Be fully testable in isolation

❌ NEVER create stories with dependencies in Sprint 1
❌ NEVER create layered stories (DB → API → UI)
❌ NEVER make one developer wait for another
```

**Example: 3 developers on ACE Memory System**

```
Story 1: Embeddings Component
- Files: ace/embeddings/
- Defines: EmbeddingsInterface
- Implements: BedrockEmbeddings (real)
- Tests: With real Bedrock API

Story 2: Vector Store Component
- Files: ace/vector_store/
- Defines: VectorStoreInterface
- Implements: DatabricksVectorStore (real)
- Tests: With MockEmbeddings

Story 3: Storage Component
- Files: ace/storage/
- Defines: StorageInterface
- Implements: S3Storage (real)
- Tests: With mocked S3

Story 4 (Sprint 2): Integration
- Wire real components together
- End-to-end tests
```

### Step 2: Define Integration Contracts

**CRITICAL: Define all interfaces upfront so developers can work in parallel**

**Note on Mocking Strategy:** The mock/interface pattern is recommended for maximum parallelization, but not mandatory. If the lead engineer prefers a different integration approach, that's acceptable. However, if components must be integrated sequentially after stories complete, clearly document this in the story and inform the lead engineer of the integration dependencies.

```python
# Story 1 defines this interface
class EmbeddingsInterface(ABC):
    """Contract for embedding generation."""
    
    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding vector.
        
        Args:
            text: Input text (max 8000 tokens)
            
        Returns:
            1024-dimensional float vector
            
        Raises:
            ValueError: If text empty or too long
            EmbeddingError: If generation fails
        """
        pass

# Story 2 uses mock for testing
class MockEmbeddings(EmbeddingsInterface):
    async def embed_query(self, text: str) -> List[float]:
        return [0.1] * 1024  # Mock enables parallel development
```

### Step 3: Write Complete Story Details

Use this template for each story:

```markdown
## Story [N]: [Action] [Component]

**Repository:** [repo-name]
**Type:** Feature
**Priority:** High
**Size:** M (3-5 days)
**Dependencies:** NONE (Sprint 1 - fully parallel)

### Description
As a [user type],
I want [capability],
So that [business value].

### Technical Context
- **Affected modules:** [module] (new)
- **Design reference:** design.md "[Section]" section
- **Key files to create:**
  - `src/[module]/__init__.py`
  - `src/[module]/[component].py` (main implementation)
  - `src/[module]/interfaces.py` (contracts for other stories)
  - `src/[module]/mocks.py` (mocks for testing)
  - `tests/[module]/test_[component].py`
- **Patterns to follow:** [similar component pattern]
- **Dependencies:** NONE (no dependencies on other Sprint 1 stories)
  - Note: Stories CAN depend on existing codebase, libraries, and infrastructure

### Integration Contracts

**Interfaces Defined by This Story:**
```python
# src/[module]/interfaces.py
class [Component]Interface(ABC):
    @abstractmethod
    async def method_name(self, param: Type) -> ReturnType:
        """Contract description with full type info."""
        pass
```

**Interfaces Used by This Story:**
```python
# Uses mocks for parallel development
from other_module.interfaces import OtherInterface
from other_module.mocks import MockOther

# Tests use MockOther() instead of real implementation
```

**Integration Timeline:**
- Sprint 1: Fully functional with mocks, all tests pass
- Sprint 2: Integration story wires real implementations

### Acceptance Criteria
- [ ] **Given** [valid input], **When** [method called], **Then** [expected output]
- [ ] **Given** [invalid input], **When** [method called], **Then** [appropriate error]
- [ ] **Given** [edge case], **When** [method called], **Then** [handled correctly]
- [ ] Interface defined in interfaces.py with complete docstrings
- [ ] Mock implementation provided in mocks.py
- [ ] Unit tests cover: happy path, errors, edge cases (using mocks)
- [ ] All tests pass independently (no external dependencies)

### Implementation Details
[Paste relevant sections from design.md - function signatures, data models, error handling]

### Out of Scope
- Integration with other components (Sprint 2)
- [Other exclusions to prevent scope creep]

### Notes for Developer
- Other stories will use your interface - make it clear!
- Provide good mocks - other devs depend on them
- [Helpful context, gotchas, recommendations]
```

### Step 4: Create Parallelization Plan

```markdown
## Parallelization Plan

**Sprint 1: Core Components (N developers, ZERO dependencies)**
- Story 1: [Component A] (Dev 1)
- Story 2: [Component B] (Dev 2)
- Story 3: [Component C] (Dev 3)

All stories start Day 1. No waiting.

**Sprint 2: Integration**
- Story N+1: Wire components together
- Story N+2: End-to-end tests

**Sprint 3: Advanced Features** (if needed)
- Story X: [Feature A] (Dev 1)
- Story Y: [Feature B] (Dev 2)
```

**Key Rule:** If you see arrows (→) between Sprint 1 stories, YOU'RE DOING IT WRONG!

### Step 5: Validate Quality

**True Parallelization Check:**
```
✅ Up to N stories for N developers (fewer if fewer independent components)
✅ ZERO dependencies between Sprint 1 stories (can depend on existing codebase)
✅ Each story touches completely different files
✅ All integration contracts defined upfront
✅ Each story testable with mocks
✅ Integration story planned for Sprint 2+

Test: Can all N developers start Day 1 at 9am without waiting?
If NO → redesign stories!
```

**Completeness Check:**
```
✅ Exact files to create/modify listed
✅ Patterns to follow referenced
✅ Design decisions linked
✅ Acceptance criteria testable
✅ Dependencies explicit (NONE for Sprint 1)
✅ Interfaces have complete type signatures
✅ Mock implementations provided
```

## Story Template Variations

### For API/Backend Components
```markdown
**Key files to create:**
- `src/[module]/[component].py` (implementation)
- `src/[module]/interfaces.py` (contracts)
- `src/[module]/mocks.py` (mocks)
- `tests/[module]/test_[component].py`
```

### For UI Components
```markdown
**Key files to create:**
- `src/components/[Component]/[Component].tsx`
- `src/components/[Component]/[Component].test.tsx`
- `src/hooks/use[Feature].ts`
- `src/api/[feature].api.ts` (with mock API responses)
```

### For Database/Infrastructure
```markdown
**Key files to create:**
- `scripts/setup_[resource].py` (idempotent setup)
- `scripts/[resource]_schema.sql` (if applicable)
- `tests/test_[resource]_setup.py`

**Note:** Make setup scripts idempotent and testable
```

## Output Quality Checklist

Before finalizing, verify:

### Discovery
- [ ] Asked: "How many developers?"
- [ ] Asked: "What's your timeline?"
- [ ] Asked: "Which components communicate?"
- [ ] Created up to N stories (fewer if fewer independent components exist)

### Parallelization
- [ ] Sprint 1 stories have ZERO dependencies
- [ ] Each story touches different files/modules
- [ ] All contracts defined upfront
- [ ] Mocks provided for testing
- [ ] Test: All N devs can start Day 1

### Story Quality
- [ ] All required sections present
- [ ] Given/When/Then acceptance criteria
- [ ] Exact files listed
- [ ] Patterns referenced
- [ ] Out of scope defined
- [ ] Interfaces with complete types
- [ ] Integration timeline specified

## Anti-Patterns to Avoid

❌ **Stories with dependencies**
```
Story 1: Database Schema
Story 2: API (depends on Story 1) ← BLOCKS Dev 2!
```

✅ **Independent components**
```
Story 1: Embeddings (defines interface)
Story 2: VectorStore (uses MockEmbeddings)
→ Both start Day 1!
```

---

❌ **Vague acceptance criteria**
```
- [ ] API works correctly
```

✅ **Specific acceptance criteria**
```
- [ ] **Given** valid ID, **When** POST /api, **Then** 201 with object
- [ ] **Given** invalid ID, **When** POST /api, **Then** 404 with error
```

---

❌ **Missing technical context**
```
"Implement favorites API"
```

✅ **Complete technical context**
```
"Implement favorites API"
- Files: src/favorites/controller.ts (create)
- Pattern: Follow src/users/controller.ts
- Design: See design.md "API Contracts"
```

---

❌ **Vague contracts**
```python
def save(self, data): pass
```

✅ **Clear contracts**
```python
@abstractmethod
async def save(self, data: Dict[str, Any]) -> bool:
    """Save data to store.
    
    Args:
        data: Dict with required keys: id, content
        
    Returns:
        True if saved, False if failed
        
    Raises:
        ValueError: If data missing required keys
    """
    pass
```

## Final Reminder

**The goal:** N developers working in parallel from Day 1, with clear contracts enabling seamless integration in Sprint 2.

**Success criteria:** 
- No developer waits for another
- No merge conflicts
- All stories fully testable with mocks
- Integration is straightforward (just wire real implementations)
