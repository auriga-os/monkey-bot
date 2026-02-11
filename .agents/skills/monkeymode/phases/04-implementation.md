---
name: implementation-skill
description: Guides the implementation of code from a code spec. Used by the DEVELOPER-PROMPT during Phase 2 to write production-quality code with tests.
---

# Implementation Skill

## Purpose
Transform a code spec into working, tested, production-ready code.

## Core Principles

### Read Before Writing
```
ALWAYS read and understand relevant files before writing code.
Understand:
- Code style and formatting
- Naming conventions
- Existing abstractions
- How similar features work
```

### Write General Solutions
```
Write high-quality, general-purpose code.
Don't hard-code values or create solutions that only work for specific inputs.
Implement actual logic that solves the problem generally.

Bad: if (productId === "test-123") return mockData;
Good: return await this.repository.findById(productId);
```

### Avoid Over-Engineering
```
Only make changes that are directly requested.
Don't add features, refactor code, or make "improvements" beyond the spec.

Bad: "I'll also add caching and rate limiting while I'm here"
Good: "I'll implement exactly what the code spec requests"
```

### Test-Driven Development
```
Write tests first, then implement code to pass them.
Benefits:
- Ensures code is testable
- Clarifies requirements
- Prevents scope creep
- Provides immediate feedback
```

## Implementation Process

**⚠️ IMPORTANT: After completing all tasks, you MUST run Step 8 (Code Review Self-Check) before marking the story complete!**

### Step 1: Environment Setup

#### Pre-Implementation Checklist
- [ ] On a clean feature branch
- [ ] Latest changes pulled from main/develop
- [ ] All existing tests pass
- [ ] Dependencies installed
- [ ] Code spec reviewed and understood

#### Branch Naming
Follow repo convention:
- `feature/[story-id]-[brief-description]`
- `feat/add-favorites-api`
- `fix/favorites-duplicate-handling`

### Step 2: Implementation Loop

For each task in the code spec:

```
┌─────────────────────────────────────────┐
│ 1. Read existing related files          │
│              ▼                          │
│ 2. Write tests (TDD)                    │
│              ▼                          │
│ 3. Implement code to pass tests         │
│              ▼                          │
│ 4. Run all tests (not just new ones)    │
│              ▼                          │
│ 5. Run linter and type checker          │
│              ▼                          │
│ 6. Commit with clear message            │
│              ▼                          │
│ 7. Move to next task OR                 │
│    IF LAST TASK → Step 8                │
│              ▼                          │
│ 8. Run Code Review Checklist (MANDATORY)│
└─────────────────────────────────────────┘
```

### Step 3: Read Existing Code

#### What to Read
1. **Pattern reference files** - Understand the approach
2. **Related files in same module** - See conventions
3. **Test files** - Understand testing approach
4. **Shared utilities** - Identify reusable code

#### What to Extract
- **Import ordering**: How are imports organized?
- **Class structure**: Constructor → Public → Private?
- **Function organization**: Alphabetical? By importance?
- **Error handling**: Try-catch? Result types? Error classes?
- **Logging**: What gets logged? What format?
- **Comments**: When are comments used? What style?

### Step 4: Write Tests First (TDD)

#### Test File Creation
Follow repo naming convention:
- `test_[filename].py` (pytest) - Standard Python convention

#### Test Structure
```python
import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

class TestFavoritesService:
    """Test suite for FavoritesService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create mock repository for testing."""
        repo = Mock(spec=FavoritesRepository)
        repo.add = AsyncMock()
        repo.find_by_user = AsyncMock()
        return repo
    
    @pytest.fixture
    def service(self, mock_repository):
        """Create service with mocked dependencies."""
        return FavoritesService(repository=mock_repository)
    
    async def test_add_favorite_success(self, service, mock_repository):
        """Test adding favorite with valid input."""
        # Arrange
        user_id = uuid4()
        product_id = uuid4()
        expected = Favorite(id=uuid4(), user_id=user_id, product_id=product_id)
        mock_repository.add.return_value = expected
        
        # Act
        result = await service.add_favorite(user_id, product_id)
        
        # Assert
        assert result == expected
        mock_repository.add.assert_called_once_with(user_id, product_id)
    
    async def test_add_favorite_raises_conflict_error(self, service, mock_repository):
        """Test that ConflictError is raised when favorite already exists."""
        # Arrange
        mock_repository.add.side_effect = ConflictError("Already favorited")
        
        # Act & Assert
        with pytest.raises(ConflictError, match="Already favorited"):
            await service.add_favorite(uuid4(), uuid4())
```

#### What to Test
**Always test:**
- Happy path (normal operation)
- Error cases from code spec
- Edge cases (empty inputs, boundary values, null/undefined)
- Input validation

**Don't test:**
- Framework code (trust the framework)
- Simple getters/setters without logic
- Third-party library internals

#### Test Data Factories
```python
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

def create_test_user(**overrides) -> User:
    """Factory function for creating test users.
    
    Args:
        **overrides: Fields to override in the default user
        
    Returns:
        User instance with test data
    """
    defaults = {
        'id': uuid4(),
        'email': 'test@example.com',
        'name': 'Test User',
        'created_at': datetime(2024, 1, 1),
    }
    return User(**{**defaults, **overrides})

# Usage
user = create_test_user(email='custom@example.com')
```

#### Mocking Strategy
```python
from unittest.mock import Mock, AsyncMock

# Mock external dependencies
mock_repository = Mock(spec=FavoritesRepository)
mock_repository.find_by_id = AsyncMock()
mock_repository.save = AsyncMock()
mock_repository.delete = AsyncMock()

# Don't mock the unit under test
service = FavoritesService(repository=mock_repository)

# Mock return values
mock_repository.find_by_id.return_value = test_favorite

# Verify calls
mock_repository.find_by_id.assert_called_once_with(user_id)
assert mock_repository.find_by_id.call_count == 1
```

### Step 5: Implement Code

#### Follow Code Spec Signatures
```python
# Code spec says:
async def add_favorite(self, user_id: UUID, product_id: UUID) -> Favorite:

# Implement exactly as specified:
async def add_favorite(self, user_id: UUID, product_id: UUID) -> Favorite:
    # Implementation
    pass

# Don't change the signature:
# ❌ async def add_favorite(self, data: AddFavoriteDto) -> Favorite:
```

#### Implement Incrementally
1. **Start with happy path** - Get basic functionality working
2. **Add error handling** - Handle specified error cases
3. **Add edge cases** - Handle boundary conditions
4. **Refactor if needed** - Clean up while tests still pass

#### Error Handling Patterns

**Pattern A: Custom Error Classes**
```python
class NotFoundError(Exception):
    """Raised when an entity is not found."""
    
    def __init__(self, entity: str, entity_id: str):
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} with id {entity_id} not found")

# Usage
if not product:
    raise NotFoundError('Product', str(product_id))
```

**Pattern B: Try-Except at Boundary**
```python
# Service raises
async def add_favorite(self, user_id: UUID, product_id: UUID) -> Favorite:
    """Add favorite with validation."""
    product = await self.products_service.find_by_id(product_id)
    if not product:
        raise NotFoundError('Product', str(product_id))
    return await self.repository.add(user_id, product_id)

# Controller/Route catches
@router.post("/favorites")
async def create_favorite(dto: CreateFavoriteDto, user: User = Depends(get_current_user)):
    """Create a new favorite."""
    try:
        return await service.add_favorite(user.id, dto.product_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

#### Logging Best Practices
```python
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Good: Structured logging with context
logger.info(
    json.dumps({
        "message": "Adding favorite",
        "user_id": str(user_id),
        "product_id": str(product_id),
        "request_id": context.request_id,
        "timestamp": datetime.utcnow().isoformat(),
    })
)

# Good: Log errors with stack traces
logger.error(
    json.dumps({
        "message": "Failed to add favorite",
        "user_id": str(user_id),
        "product_id": str(product_id),
        "error": str(error),
        "timestamp": datetime.utcnow().isoformat(),
    }),
    exc_info=True
)

# Bad: Unstructured logging
print('adding favorite')

# Bad: Logging sensitive data
logger.info(f"User login: {user.password}")  # NEVER DO THIS
```

### Step 6: Run Verification

#### Test Execution
```bash
# Run all tests (not just new ones)
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/favorites/test_repository.py

# Run specific test
pytest tests/favorites/test_repository.py::TestFavoritesRepository::test_add_success

# Run in watch mode during development (requires pytest-watch)
ptw
```

#### Linting
```bash
# Run linter
ruff check .

# Auto-fix issues
ruff check . --fix
```

#### Type Checking
```bash
# mypy (strict mode)
mypy src/

# pyright (alternative)
pyright src/
```

### Step 7: Commit Changes

#### Commit Message Format
```
type(scope): brief description

- Detail 1
- Detail 2

Refs: STORY-123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code change that neither fixes nor adds
- `test`: Adding or updating tests
- `docs`: Documentation only
- `chore`: Maintenance tasks

**Examples:**
```
feat(favorites): add favorites repository

- Implement CRUD operations for favorites table
- Add composite index for user+product queries
- Include pagination support

Refs: STORY-456

---

test(favorites): add repository unit tests

- Test happy path for all CRUD operations
- Test error cases (not found, duplicate)
- Test pagination edge cases

Refs: STORY-456

---

feat(favorites): add favorites API endpoints

- POST /favorites - add favorite
- DELETE /favorites/:id - remove favorite
- GET /favorites - list user favorites
- Include request/response DTOs
- Add input validation

Refs: STORY-456
```

#### Commit Frequency
- Commit after each completed task
- Commit when all tests pass
- Don't commit broken code
- Don't commit commented-out code
- Don't commit debug statements

### Step 8: Final Code Review Self-Check (MANDATORY)

**⚠️ STOP: Before marking the story complete, run through the code review checklist!**

This step is MANDATORY after completing all tasks but BEFORE marking story complete.

#### Locate and Review Checklist

1. **Find the checklist** in your code spec (search for "Code Review Checklist")
2. **Go through EVERY item** - don't skip any categories:
   - [ ] Functionality (all acceptance criteria met)
   - [ ] Code Quality (patterns, types, no hardcoded values)
   - [ ] UI/UX (responsive, accessible, animations)
   - [ ] Testing (tests pass, edge cases handled)
   - [ ] Documentation (JSDoc, props documented)
3. **Fix missing items immediately** - do not defer or skip
4. **Re-run linter** after making fixes
5. **Commit fixes** with clear message: "fix: add missing accessibility/docs from code review"

#### Common Missing Items (Check These First)

**Accessibility (Often Missed):**
```typescript
// ❌ BAD - No accessibility
<div onClick={handleClick}>Click me</div>

// ✅ GOOD - Fully accessible
<div 
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
  tabIndex={0}
  role="button"
  aria-label="Descriptive action label"
>
  Click me
</div>
```

**Documentation (Often Missed):**
```typescript
// ❌ BAD - No JSDoc
interface ComponentProps {
  userId: string;
  onSubmit: () => void;
}

export function MyComponent({ userId, onSubmit }: ComponentProps) {
  // implementation
}

// ✅ GOOD - Fully documented
/**
 * Props for MyComponent
 */
interface ComponentProps {
  /** User ID to fetch data for */
  userId: string;
  /** Callback when form is submitted */
  onSubmit: () => void;
}

/**
 * MyComponent - Brief description of what it does
 * 
 * Longer description if needed, including:
 * - Key features
 * - Important behavior
 * - Usage notes
 * 
 * @param props - Component props
 */
export function MyComponent({ userId, onSubmit }: ComponentProps) {
  // implementation
}
```

**Responsive Design:**
- Test on mobile (375px width)
- Test on tablet (768px width)
- Test on desktop (1920px width)
- No horizontal scrolling
- Touch targets at least 44x44px

**Edge Cases:**
- Empty states (no data)
- Loading states (fetching data)
- Error states (failed request)
- Validation errors (form inputs)

#### Verification Commands

```bash
# Run linter one final time
npm run lint
# or
ruff check .

# Check for any TODO comments you left behind
rg "TODO|FIXME" src/

# Verify all required files were created
ls -la src/components/[feature]/
ls -la src/lib/api/
ls -la src/hooks/

# Check for console.log statements you forgot to remove
rg "console\.(log|debug)" src/
```

#### Final Checklist Before Marking Complete

- [ ] All acceptance criteria from code spec verified
- [ ] All code review checklist items checked and fixed
- [ ] No linter errors
- [ ] No console.log or debug statements
- [ ] No commented-out code (except Sprint 2 integration notes if specified)
- [ ] All components have JSDoc comments
- [ ] All props interfaces documented
- [ ] Accessibility verified (ARIA labels, keyboard nav, focus states)
- [ ] Responsive design verified on multiple screen sizes
- [ ] All tests pass
- [ ] Manual testing complete (if applicable)

**Only after ALL items above are checked can you mark the story complete.**

### Step 9: Integration Testing

#### When to Write Integration Tests
- After all unit-tested components are complete
- To verify end-to-end flow
- To test actual database/API interactions

#### Integration Test Structure
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

class TestFavoritesAPIIntegration:
    """Integration tests for Favorites API."""
    
    @pytest.fixture
    async def client(self, app):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    async def auth_token(self, client):
        """Get authentication token for tests."""
        response = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture(autouse=True)
    async def clean_database(self, db_session: AsyncSession):
        """Clean database before each test."""
        # Clean up before test
        await db_session.execute("DELETE FROM favorites")
        await db_session.commit()
        yield
        # Clean up after test
        await db_session.execute("DELETE FROM favorites")
        await db_session.commit()
    
    async def test_add_favorite_and_retrieve(self, client, auth_token):
        """Test adding favorite and retrieving it."""
        # Add favorite
        add_response = await client.post(
            "/favorites",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"product_id": "550e8400-e29b-41d4-a716-446655440000"}
        )
        assert add_response.status_code == 201
        assert "id" in add_response.json()
        
        # Retrieve favorites
        get_response = await client.get(
            "/favorites",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 200
        favorites = get_response.json()["items"]
        assert len(favorites) == 1
        assert favorites[0]["product_id"] == "550e8400-e29b-41d4-a716-446655440000"
```

## Code Quality Checklist

**⚠️ CRITICAL: This checklist MUST be completed before marking story as done!**

Before requesting review, verify:

### Functionality
- [ ] All acceptance criteria from story are met
- [ ] All code spec tasks are complete
- [ ] Manual testing performed (if applicable)
- [ ] Edge cases are handled (empty, loading, error states)

### Code Quality
- [ ] Follows existing patterns in codebase
- [ ] No unnecessary code or abstractions
- [ ] No commented-out code (except Sprint 2 integration notes if specified)
- [ ] No TODO comments (create tickets instead)
- [ ] No print() or debug statements
- [ ] No console.log() statements
- [ ] Functions are focused and single-purpose
- [ ] No magic numbers or hardcoded values
- [ ] Meaningful variable and function names

### Tests
- [ ] All new code has unit tests
- [ ] Tests cover happy path and error cases
- [ ] All tests pass locally
- [ ] Test names are descriptive
- [ ] Tests are independent (no shared state)
- [ ] Integration tests verify end-to-end flow
- [ ] Test coverage meets project standards

### Performance
- [ ] No N+1 query issues
- [ ] Appropriate use of indexes
- [ ] No blocking operations in hot paths
- [ ] Efficient algorithms used

### Security
- [ ] Input validation on all endpoints
- [ ] Authorization checks in place
- [ ] No sensitive data in logs
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (input sanitization)

### Documentation
- [ ] All components have JSDoc comments
- [ ] All props/parameters have JSDoc descriptions
- [ ] Function signatures have docstrings
- [ ] Complex logic has explanatory comments
- [ ] README updated (if applicable)
- [ ] API docs updated (if applicable)

### Accessibility (Frontend Only)
- [ ] All interactive elements have aria-label or aria-labelledby
- [ ] Keyboard navigation works (Tab, Enter, Space, Escape)
- [ ] Focus states are visible
- [ ] role attributes on custom interactive elements
- [ ] tabIndex set appropriately for keyboard access
- [ ] Screen reader friendly (semantic HTML)

### Responsive Design (Frontend Only)
- [ ] Works on mobile (375px width minimum)
- [ ] Works on tablet (768px width)
- [ ] Works on desktop (1920px+ width)
- [ ] No horizontal scrolling
- [ ] Touch targets at least 44x44px
- [ ] Text is readable (not too small)

### Git Hygiene
- [ ] Commits are logical and atomic
- [ ] Commit messages follow convention
- [ ] No merge commits (rebase if needed)
- [ ] Branch is up to date with target

### Linting & Type Checking
- [ ] Linter passes with no warnings
- [ ] Type checker passes (if applicable)
- [ ] No unused imports or variables
- [ ] Consistent code formatting

**If ANY item above is unchecked, FIX IT before marking complete!**

## Common Patterns

### Repository Pattern
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from uuid import UUID

class FavoritesRepository:
    """Repository for favorites data access."""
    
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def add(self, user_id: UUID, product_id: UUID) -> Favorite:
        """Add favorite to database.
        
        Args:
            user_id: User UUID
            product_id: Product UUID
            
        Returns:
            Created favorite
            
        Raises:
            ConflictError: If favorite already exists
        """
        favorite = FavoriteModel(user_id=user_id, product_id=product_id)
        self.session.add(favorite)
        
        try:
            await self.session.commit()
            await self.session.refresh(favorite)
            return Favorite.from_orm(favorite)
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("Favorite already exists")
    
    async def find_by_user(
        self,
        user_id: UUID,
        pagination: PaginationParams
    ) -> list[Favorite]:
        """Get favorites for user with pagination.
        
        Args:
            user_id: User UUID
            pagination: Offset and limit
            
        Returns:
            List of favorites
        """
        result = await self.session.execute(
            select(FavoriteModel)
            .where(FavoriteModel.user_id == user_id)
            .offset(pagination.offset)
            .limit(pagination.limit)
            .order_by(FavoriteModel.created_at.desc())
        )
        return [Favorite.from_orm(f) for f in result.scalars().all()]
```

### Service Pattern
```python
from uuid import UUID

class FavoritesService:
    """Service for favorites business logic."""
    
    def __init__(
        self,
        repository: FavoritesRepository,
        products_service: ProductsService,
        event_emitter: EventEmitter,
    ) -> None:
        self.repository = repository
        self.products_service = products_service
        self.event_emitter = event_emitter
    
    async def add_favorite(self, user_id: UUID, product_id: UUID) -> FavoriteDto:
        """Add favorite with validation.
        
        Args:
            user_id: User UUID
            product_id: Product UUID
            
        Returns:
            Created favorite DTO
            
        Raises:
            NotFoundError: If product doesn't exist
            ConflictError: If already favorited
        """
        # Validate product exists
        product = await self.products_service.find_by_id(product_id)
        if not product:
            raise NotFoundError('Product', str(product_id))
        
        # Add favorite
        favorite = await self.repository.add(user_id, product_id)
        
        # Emit event
        await self.event_emitter.emit('favorite.added', {
            'user_id': str(user_id),
            'product_id': str(product_id),
            'timestamp': datetime.utcnow().isoformat(),
        })
        
        return self._to_dto(favorite)
    
    def _to_dto(self, favorite: Favorite) -> FavoriteDto:
        """Convert entity to DTO."""
        return FavoriteDto(
            id=favorite.id,
            user_id=favorite.user_id,
            product_id=favorite.product_id,
            created_at=favorite.created_at.isoformat(),
        )
```

### Controller/Router Pattern (FastAPI)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

router = APIRouter(prefix="/favorites", tags=["favorites"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=FavoriteResponse)
async def add_favorite(
    dto: AddFavoriteDto,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> FavoriteResponse:
    """Add a product to user's favorites.
    
    Args:
        dto: Request body with product_id
        user: Current authenticated user
        service: Favorites service instance
        
    Returns:
        Created favorite
        
    Raises:
        HTTPException: 404 if product not found, 409 if already favorited
    """
    try:
        return await service.add_favorite(user.id, dto.product_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    product_id: UUID,
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> None:
    """Remove a product from user's favorites."""
    await service.remove_favorite(user.id, product_id)

@router.get("/", response_model=PaginatedResponse[FavoriteResponse])
async def get_favorites(
    pagination: PaginationParams = Depends(),
    user: User = Depends(get_current_user),
    service: FavoritesService = Depends(get_favorites_service),
) -> PaginatedResponse[FavoriteResponse]:
    """Get user's favorites with pagination."""
    items = await service.get_user_favorites(user.id, pagination)
    total = await service.count_user_favorites(user.id)
    
    return PaginatedResponse(
        items=items,
        total=total,
        offset=pagination.offset,
        limit=pagination.limit,
        has_more=pagination.offset + len(items) < total,
    )
```

### DTO Validation (Pydantic)
```python
from pydantic import BaseModel, Field
from uuid import UUID

class AddFavoriteDto(BaseModel):
    """Request body for adding a favorite."""
    product_id: UUID = Field(..., description="Product UUID to favorite")

class FavoriteResponse(BaseModel):
    """Response model for favorite."""
    id: UUID
    user_id: UUID
    product_id: UUID
    created_at: str
    
    class Config:
        from_attributes = True  # Allows creation from ORM models

# FastAPI validates automatically
@router.post("/")
async def create(dto: AddFavoriteDto):  # Pydantic validates dto
    # dto.product_id is guaranteed to be a valid UUID
    pass
```

## Troubleshooting

### Tests Failing Unexpectedly

**Issue:** Tests pass individually but fail when run together
**Solution:** Tests are not isolated - check for shared state
```python
# Bad: Shared state
test_user: User = None

@pytest.fixture(scope="module")
def user():
    return create_user()

# Good: Fresh state per test
@pytest.fixture
def user():
    return create_user()
```

**Issue:** Async tests timing out
**Solution:** Missing await
```python
# Bad
async def test_save_user():
    service.save(user)  # Missing await

# Good
async def test_save_user():
    await service.save(user)
```

### Type Errors

**Issue:** "Incompatible types" or "Missing type annotation"
**Solution:** Check imports and type definitions
```python
# Ensure correct import
from app.models import User

# Ensure type hint is correct
user: User = await repository.find_by_id(user_id)

# Use Optional for nullable values
from typing import Optional
user: Optional[User] = await repository.find_by_id(user_id)
```

### Integration Issues

**Issue:** Dependency injection not working
**Solution:** Verify dependencies are properly configured
```python
# FastAPI example - use Depends()
from fastapi import Depends

def get_repository(session: AsyncSession = Depends(get_session)):
    return FavoritesRepository(session)

@router.post("/")
async def create(
    repo: FavoritesRepository = Depends(get_repository)
):
    # repo is injected automatically
    pass
```

## Anti-Patterns to Avoid

❌ **Hard-coding test data**
```python
if user_id == "test-123":
    return mock_data
```

✅ **General implementation**
```python
return await self.repository.find_by_user(user_id)
```

❌ **Over-engineering**
```python
# Adding features not in spec
class FavoritesCache:
    # Complex caching logic not requested
    pass
```

✅ **Implement what's requested**
```python
# Simple, direct implementation
async def add_favorite(self, user_id: UUID, product_id: UUID) -> Favorite:
    return await self.repository.add(user_id, product_id)
```

❌ **Ignoring existing patterns**
```python
# Using different error handling than rest of codebase
return {"error": "Not found"}
```

✅ **Follow existing patterns**
```python
# Using same error classes as rest of codebase
raise NotFoundError('Product', str(product_id))
```

❌ **No error handling**
```python
async def add_favorite(self, user_id: UUID, product_id: UUID) -> Favorite:
    return await self.repository.add(user_id, product_id)
    # What if repository raises?
```

✅ **Proper error handling**
```python
async def add_favorite(self, user_id: UUID, product_id: UUID) -> Favorite:
    try:
        return await self.repository.add(user_id, product_id)
    except ConflictError:
        # Handle duplicate
        raise
    except Exception as e:
        # Log and re-raise
        logger.error(f"Failed to add favorite: {e}")
        raise
```
