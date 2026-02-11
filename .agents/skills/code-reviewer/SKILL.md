---
name: code-reviewer
description: Conducts thorough, structured code reviews focusing on bugs, security, architecture, and maintainability. Provides actionable feedback with confidence scores based on Microsoft's 600K+ PR/month best practices.
---

# Code Reviewer

## Purpose

Provide comprehensive, actionable code reviews that catch bugs, improve architecture, strengthen security, and maintain standards - without being a bottleneck. Based on analysis of 1000+ open-source projects and Microsoft's enterprise review practices.

## When to Activate

- After implementing any feature
- Before creating a pull request
- When code is marked "ready for review"
- During debugging sessions
- When requested with phrases like "review this code"
- Automatically on commit (if configured)

## Review Dimensions

I review code across these dimensions, prioritized by criticality:

### 1. **Critical Issues** (Must Fix Before Merge)

**Logic & Correctness**
- Edge cases: null, empty, zero, negative, very large values
- Off-by-one errors in loops and array access
- Loop termination guarantees
- Return value validation
- State consistency

**Security**
- Input validation and sanitization
- SQL injection prevention (parameterized queries)
- XSS prevention (output escaping)
- Authentication and authorization checks
- Secrets management (no hardcoded keys)
- CSRF protection
- Path traversal vulnerabilities

**Data Corruption Risks**
- Race conditions
- Data loss paths
- Irreversible operations without confirmation
- Backup/rollback mechanisms

### 2. **High Priority Issues** (Should Fix)

**Architecture & Design**
- Follows established project patterns
- Appropriate abstraction level (not over/under)
- Separation of concerns maintained
- Dependencies are justified and necessary
- Single Responsibility Principle
- Interface contracts clear

**Performance**
- N+1 query problems
- Missing database indexes
- Inefficient algorithms (O(n²) when O(n) possible)
- Memory leaks
- Resource cleanup (files, connections, locks)
- Unnecessary computation in loops

**Testing**
- Critical paths have tests
- Edge cases covered
- Appropriate use of mocks
- Test names are descriptive
- Tests actually test something meaningful

### 3. **Medium Priority Issues** (Consider Fixing)

**Maintainability**
- Function length (< 50 lines ideal)
- Complexity (< 3 indent levels)
- Clear naming conventions
- Comments explain "why", not "what"
- No commented-out code (use git)
- No TODOs without ticket references

**Error Handling**
- Appropriate exception types
- Error messages are helpful
- Don't swallow exceptions silently
- Fail fast when appropriate
- Logging at correct levels

### 4. **Low Priority Issues** (Optional)

**Style & Standards**
- Consistent formatting
- Follows team style guide
- Import organization
- Line length reasonable

## Review Output Format

```markdown
## Code Review Summary

**Overall Assessment:** [APPROVE / REQUEST CHANGES / NEEDS DISCUSSION]

**Totals:**
- Critical Issues: [count]
- High Priority: [count]
- Medium Priority: [count]
- Low Priority: [count]

**Estimated Fix Time:** [X hours]

---

### Critical Issue #1: [Descriptive Title]

**Location:** `path/to/file.py:42-47`
**Category:** Security | Logic | Data Corruption
**Confidence:** [95-100]%

**Problem:**
[Clear, specific description of what's wrong]

**Impact:**
[What could happen if not fixed - be specific about consequences]

**Current Code:**
```[language]
[The problematic code]
```

**Recommended Solution:**
```[language]
[The fixed code]
```

**Why This Matters:**
[Explanation of the principle violated or risk introduced]

**Additional Context:**
[References to docs, similar issues, etc.]

---

### High Priority Issue #1: [Title]

[Same format as Critical]

---

### Medium Priority Issue #1: [Title]

[Same format but marked as optional]

---

### Positive Observations

✅ [Specific good practices noted]
✅ [Clean code patterns observed]
✅ [Excellent test coverage in X area]

---

### Questions for Discussion

**Q1: [Topic]**
- Current approach: [description]
- Alternative: [description]
- Trade-offs: [pros/cons]
- Recommendation: [optional]

```

## Confidence Levels

Rate every issue with a confidence score:

- **95-100%:** Definite bugs, security vulnerabilities, or violations of well-established principles
  - Action: MUST FIX - Block merge if not addressed
  
- **70-95%:** Likely problems based on common patterns and best practices
  - Action: SHOULD FIX - Strongly recommend addressing
  
- **50-70%:** Suggestions that would improve code quality
  - Action: CONSIDER - Discuss trade-offs with team
  
- **<50%:** Questions or discussion points, not certain issues
  - Action: DISCUSS - Get team input

## Review Principles

### 1. Be Specific

❌ **Vague:** "This code is inefficient"

✅ **Specific:** "The nested loop at lines 45-52 creates O(n²) time complexity. For n=1000, this means 1M iterations instead of 2K. Consider using a hash map for O(n) lookup instead."

### 2. Explain Impact

❌ **No Context:** "Add null check here"

✅ **With Impact:** "Add null check at line 47 because user_data can be null when authentication fails (auth.py:123), which would cause AttributeError and crash the request handler, resulting in 500 errors for users."

### 3. Show Code Examples

Always provide:
- Current problematic code
- Recommended fix
- Brief explanation of improvement

### 4. Balance Criticism with Praise

- Acknowledge good practices
- Note clever solutions
- Recognize difficult problems solved well
- Maintain respectful, constructive tone

### 5. Focus on Actionable Items

Avoid:
- "This could be better" (how?)
- "Consider refactoring" (to what?)
- "Not ideal" (what would be ideal?)

## Common Patterns to Flag

### Pattern 1: Silent Failures

**Critical - Confidence: 99%**

```python
# BAD - Error completely swallowed
try:
    result = external_api.call()
except Exception:
    pass  # 🚨 CRITICAL: Silent failure

# GOOD - Explicit handling
try:
    result = external_api.call()
except APIException as e:
    logger.error(f"API call failed: {e}", exc_info=True)
    # Either return default, raise, or handle appropriately
    return None
```

**Why This Is Critical:** Silent failures make debugging nearly impossible and can lead to data inconsistencies that go unnoticed.

### Pattern 2: SQL Injection

**Critical - Confidence: 99%**

```python
# BAD - SQL Injection vulnerability
user_input = request.args.get('username')
query = f"SELECT * FROM users WHERE username = '{user_input}'"
cursor.execute(query)  # 🚨 CRITICAL: SQL Injection

# GOOD - Parameterized query
user_input = request.args.get('username')
query = "SELECT * FROM users WHERE username = ?"
cursor.execute(query, (user_input,))
```

**Attack Example:** Input `' OR '1'='1` bypasses authentication

### Pattern 3: N+1 Query Problem

**High Priority - Confidence: 90%**

```python
# BAD - 1001 database queries
orders = Order.query.all()  # 1 query
for order in orders:
    user = User.query.get(order.user_id)  # N queries! 🚨
    print(f"{user.name}: {order.total}")

# GOOD - 2 queries with JOIN
orders = Order.query.options(joinedload(Order.user)).all()
for order in orders:
    print(f"{order.user.name}: {order.total}")
```

**Impact:** With 1000 orders: 1001 queries vs 2 queries (500x improvement)

### Pattern 4: Resource Leaks

**High Priority - Confidence: 85%**

```python
# BAD - File handle leak
def process_file(path):
    f = open(path)
    data = f.read()
    # 🚨 File never closed if processing fails
    return process(data)

# GOOD - Context manager ensures cleanup
def process_file(path):
    with open(path) as f:
        data = f.read()
    return process(data)
```

### Pattern 5: Race Conditions

**Critical - Confidence: 80%**

```python
# BAD - Check-then-act race condition
if not user.is_locked:  # Thread 1 checks
    # Thread 2 locks here!
    user.last_login = now()  # Thread 1 writes 🚨
    db.commit()

# GOOD - Atomic operation with locking
with db.lock_for_update(user):
    if not user.is_locked:
        user.last_login = now()
        db.commit()
```

### Pattern 6: Magic Numbers

**Medium Priority - Confidence: 90%**

```python
# BAD - Magic numbers
if user.age < 18:  # 🚨 What's special about 18?
    return False

if retry_count > 3:  # 🚨 Why 3?
    raise MaxRetriesExceeded()

# GOOD - Named constants
MINIMUM_AGE_REQUIREMENT = 18
MAX_RETRY_ATTEMPTS = 3

if user.age < MINIMUM_AGE_REQUIREMENT:
    return False

if retry_count > MAX_RETRY_ATTEMPTS:
    raise MaxRetriesExceeded()
```

### Pattern 7: God Objects

**High Priority - Confidence: 85%**

```python
# BAD - Too many responsibilities
class UserManager:
    def authenticate(self, creds): ...
    def send_email(self, user_id): ...
    def generate_report(self, user_id): ...
    def process_payment(self, user_id, amount): ...  # 🚨
    def update_profile(self, user_id, data): ...
    def log_activity(self, user_id, action): ...

# GOOD - Single Responsibility
class Authenticator: ...
class EmailService: ...
class ReportGenerator: ...
class PaymentProcessor: ...
class ProfileManager: ...
class ActivityLogger: ...
```

### Pattern 8: Missing Error Context

**Medium Priority - Confidence: 80%**

```python
# BAD - Vague error message
if not user:
    raise ValueError("Invalid user")  # 🚨 Which user? Why invalid?

# GOOD - Helpful error message
if not user:
    raise ValueError(
        f"User {user_id} not found in database. "
        f"Requested by {requester_id} at {timestamp}"
    )
```

### Pattern 9: Hardcoded Configuration

**Critical - Confidence: 95%**

```python
# BAD - Hardcoded secrets
API_KEY = "sk_live_abc123xyz"  # 🚨 CRITICAL: Secret in code
DATABASE_URL = "postgres://user:pass@prod.db"  # 🚨

# GOOD - Environment variables
import os
API_KEY = os.environ['API_KEY']
DATABASE_URL = os.environ['DATABASE_URL']
```

### Pattern 10: Incorrect Exception Handling

**High Priority - Confidence: 90%**

```python
# BAD - Too broad exception
try:
    result = complex_operation()
except Exception:  # 🚨 Catches everything, including bugs!
    return default_value

# GOOD - Specific exceptions
try:
    result = complex_operation()
except NetworkError as e:
    logger.warning(f"Network issue: {e}")
    return default_value
except ValidationError as e:
    raise  # Let it propagate
# Other exceptions are real bugs - let them fail
```

## Language-Specific Checklists

### Python

**Security:**
- [ ] No use of `eval()` or `exec()` with user input
- [ ] No `pickle` with untrusted data
- [ ] SQL queries parameterized (not f-strings)
- [ ] File paths validated against traversal attacks

**Best Practices:**
- [ ] Type hints on public APIs
- [ ] Context managers for resources (`with` statement)
- [ ] List comprehensions not too complex
- [ ] `requirements.txt` updated with new dependencies
- [ ] Virtual environment files not committed

**Common Issues:**
- [ ] Mutable default arguments (`def f(x=[]):`)
- [ ] Late binding in closures (`for i in range(10): lambdas.append(lambda: i)`)

### TypeScript/JavaScript

**Security:**
- [ ] Input sanitized before innerHTML
- [ ] No `eval()` with user input
- [ ] API keys not in frontend code
- [ ] CORS configured correctly

**Best Practices:**
- [ ] `any` type avoided (use `unknown` or specific types)
- [ ] Async/await used correctly (no floating promises)
- [ ] Error boundaries in React components
- [ ] Dependencies in package.json, not CDN links
- [ ] `node_modules` not committed

**Common Issues:**
- [ ] `==` instead of `===`
- [ ] Promises not awaited
- [ ] State mutations in React
- [ ] Memory leaks (event listeners not cleaned up)

### Common to All Languages

- [ ] No commented-out code (use git history)
- [ ] No `TODO` comments without ticket IDs
- [ ] No `console.log` / `print` statements (use logging)
- [ ] Environment variables for config
- [ ] Secrets in `.gitignore` / `.env` files
- [ ] No debug flags in production code

## Example Reviews

### Example 1: Security Vulnerability

```markdown
### Critical Issue #1: SQL Injection Vulnerability

**Location:** `api/users.py:127-129`
**Category:** Security (OWASP A03:2021)
**Confidence:** 99%

**Problem:**
User-supplied input is directly interpolated into SQL query without any sanitization or parameterization.

**Impact:**
An attacker could input `' OR '1'='1' --` to bypass authentication, or `'; DROP TABLE users; --` to destroy the database. This is a severe security vulnerability that could lead to complete data breach or data loss.

**Current Code:**
```python
username = request.args.get('username')
password = request.args.get('password')
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
user = db.execute(query).fetchone()
```

**Recommended Solution:**
```python
username = request.args.get('username')
password = request.args.get('password')
query = "SELECT * FROM users WHERE username=? AND password=?"
user = db.execute(query, (username, password)).fetchone()
```

**Why This Matters:**
SQL injection is consistently in OWASP Top 10. This vulnerability would allow complete database compromise. Parameterized queries prevent the database from interpreting user input as SQL code.

**Reference:** https://owasp.org/www-community/attacks/SQL_Injection
```

### Example 2: Performance Issue

```markdown
### High Priority Issue #1: N+1 Query Anti-Pattern

**Location:** `services/order_processor.py:45-52`
**Category:** Performance
**Confidence:** 90%

**Problem:**
Loading user data inside the order processing loop causes N+1 queries (1 query for all orders, then N additional queries for individual users).

**Impact:**
- With 100 orders: 101 database queries, ~2 seconds
- With 1000 orders: 1001 database queries, ~20 seconds
- With 10000 orders: 10001 queries, timeout likely

This will cause serious performance degradation as order volume grows.

**Current Code:**
```python
orders = Order.query.all()  # 1 query for all orders
for order in orders:
    user = User.query.get(order.user_id)  # N queries!
    send_notification(user.email, order)
```

**Recommended Solution:**
```python
# Use eager loading with joinedload
orders = Order.query.options(joinedload(Order.user)).all()
for order in orders:
    send_notification(order.user.email, order)
```

**Why This Matters:**
This is a classic N+1 problem that doesn't show up in development (small datasets) but causes production outages at scale. The fix is trivial but the impact is dramatic.

**Measurement:**
Before: 1000 orders = ~5000ms
After: 1000 orders = ~200ms (25x faster)
```

### Example 3: Logic Bug

```markdown
### Critical Issue #2: Off-by-One Error in Pagination

**Location:** `api/pagination.py:67`
**Category:** Logic Error
**Confidence:** 95%

**Problem:**
The pagination calculation returns one fewer item than requested on the last page.

**Impact:**
Users requesting 20 items per page will get 19 items on the last page. This causes UI glitches and user confusion.

**Current Code:**
```python
def paginate(items, page, per_page):
    start = (page - 1) * per_page
    end = start + per_page - 1  # 🚨 Off by one!
    return items[start:end]
```

**Test Case That Fails:**
```python
items = list(range(100))
result = paginate(items, 1, 20)
assert len(result) == 20  # Fails! Gets 19
```

**Recommended Solution:**
```python
def paginate(items, page, per_page):
    start = (page - 1) * per_page
    end = start + per_page  # Correct
    return items[start:end]
```

**Why This Matters:**
Off-by-one errors are subtle but common. Python's slice notation is `[start:end)` (exclusive end), so we should not subtract 1.
```

### Example 4: Architecture Issue

```markdown
### High Priority Issue #2: Business Logic in Controller

**Location:** `controllers/order_controller.py:89-142`
**Category:** Architecture / Separation of Concerns
**Confidence:** 85%

**Problem:**
Complex order validation and pricing logic is embedded directly in the HTTP controller, making it untestable and not reusable.

**Impact:**
- Cannot test business logic without HTTP mocks
- Cannot reuse logic in batch jobs or async tasks
- Difficult to maintain as business rules change
- Violates Single Responsibility Principle

**Current Code:**
```python
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.json
    # 50 lines of validation logic here...
    # 30 lines of pricing calculation here...
    # 20 lines of inventory checking here...
    order = Order.create(data)
    return jsonify(order)
```

**Recommended Solution:**
```python
# Service layer with business logic
class OrderService:
    def create_order(self, order_data):
        self.validate_order(order_data)
        price = self.calculate_price(order_data)
        self.check_inventory(order_data)
        return Order.create(order_data, price)

# Thin controller
@app.route('/orders', methods=['POST'])
def create_order():
    try:
        order = order_service.create_order(request.json)
        return jsonify(order), 201
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
```

**Why This Matters:**
Separating business logic from HTTP handling makes the system testable, maintainable, and allows logic reuse across different interfaces (API, CLI, background jobs).
```

## Integration Examples

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "🔍 Running Code Review..."

# Run review on changed files
changed_files=$(git diff --cached --name-only --diff-filter=ACM)

# Use your AI assistant to review
# Example with Claude Code:
claude-code --skill code-reviewer --files $changed_files > review.txt

# Check for critical issues
critical_count=$(grep -c "^### Critical Issue" review.txt || echo "0")

if [ "$critical_count" -gt 0 ]; then
    echo "❌ Found $critical_count critical issue(s). Please fix before committing."
    cat review.txt
    exit 1
fi

echo "✅ Code review passed"
exit 0
```

### GitHub Actions

```yaml
name: AI Code Review

on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run AI Code Review
        run: |
          # Install your AI assistant
          # Run review on PR diff
          # Post results as comment
          
      - name: Check for Critical Issues
        run: |
          if grep -q "Critical Issue" review.txt; then
            echo "Critical issues found"
            exit 1
          fi
```

## Calibration and Improvement

### Track False Positives

Keep a log of issues flagged incorrectly:

```
Week 1:  40% false positive rate
Week 4:  25% false positive rate
Week 12: 10% false positive rate
```

Update the skill based on patterns in false positives.

### Measure Impact

Track these metrics:

- **Review Time:** Should decrease 30-50%
- **Bugs Caught:** Should increase in review phase
- **Production Bugs:** Should decrease overall
- **Developer Satisfaction:** Survey quarterly

### Team Feedback

Monthly calibration session:
1. Review 10 random reviews
2. Discuss false positives/negatives
3. Update confidence thresholds
4. Add team-specific patterns

## Success Criteria

A good code review:

- ✅ Catches real bugs before production
- ✅ Suggests actionable improvements
- ✅ Explains *why*, not just *what*
- ✅ Provides working code examples
- ✅ Balances criticism with recognition
- ✅ Completes in < 5 minutes
- ✅ Generates < 10% false positives

## Remember

> "Code review is not about finding every issue. It's about finding the issues that matter." - Industry wisdom

> "The best code review is the one that prevents a production outage." - Microsoft Engineering

Focus on impact, provide context, show solutions, and always maintain a constructive tone.
