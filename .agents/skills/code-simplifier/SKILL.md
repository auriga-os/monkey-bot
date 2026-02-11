---
name: code-simplifier
description: Proactively refines code to maximize simplicity, readability, and maintainability. Eliminates unnecessary complexity and over-engineering based on Linus Torvalds' coding principles.
---

# Code Simplifier

## Purpose

Transform complex, over-engineered code into simple, maintainable solutions. This skill operates proactively to review and refine code, preventing the accumulation of technical debt through unnecessary abstractions and complexity.

## When to Activate

- After generating any code block (>20 lines)
- When implementing new features
- During refactoring sessions
- Before committing code
- When code exceeds 50 lines without clear structure
- When reviewing pull requests

## Core Philosophy

Based on Linus Torvalds' programming principles:

1. **Design-First Thinking** - Understand the complete problem before coding
2. **Minimal Abstraction** - Only add abstractions with 3+ concrete use cases
3. **Eliminate Special Cases** - Rewrite so special cases become normal cases
4. **Clarity Over Cleverness** - Explicit code beats compact, clever code

## Simplification Rules

### Rule 1: Minimal Abstraction

**AVOID**: Creating abstractions "just in case" for future needs

**PREFER**: Solve the immediate problem directly

**ONLY ADD**: Abstractions when you have 3+ concrete, existing use cases

**Example - Bad (Over-Abstracted):**
```python
class DataProcessorFactory:
    """Factory for creating data processors"""
    
    @staticmethod
    def create_processor(processor_type: str) -> BaseProcessor:
        if processor_type == "json":
            return JSONProcessor()
        elif processor_type == "xml":
            return XMLProcessor()
        # Only 1-2 types ever used in practice!
        
class BaseProcessor(ABC):
    @abstractmethod
    def process(self, data): pass
    
class JSONProcessor(BaseProcessor):
    def process(self, data):
        return json.loads(data)
```

**Example - Good (Direct):**
```python
def process_json(data: str) -> dict:
    """Process JSON data directly."""
    return json.loads(data)

# Add abstractions ONLY when you actually have multiple implementations
```

### Rule 2: Function Length & Complexity

**MAXIMUM**: 50 lines per function (ideally 20-30)

**ONE PURPOSE**: Each function does exactly one thing

**EARLY EXITS**: Return as soon as you know the answer

**NESTED COMPLEXITY**: Maximum 3 levels of indentation

**Example - Bad (Deep Nesting):**
```python
def process_user(user_data):
    if user_data:
        if user_data.get('email'):
            if '@' in user_data['email']:
                if validate_email(user_data['email']):
                    if user_data.get('age'):
                        if user_data['age'] >= 18:
                            return create_user(user_data)
    return None
```

**Example - Good (Early Returns):**
```python
def process_user(user_data):
    # Guard clauses at the top
    if not user_data:
        return None
    
    if not user_data.get('email'):
        return None
    
    if '@' not in user_data['email']:
        return None
        
    if not validate_email(user_data['email']):
        return None
    
    if not user_data.get('age') or user_data['age'] < 18:
        return None
    
    return create_user(user_data)
```

### Rule 3: Eliminate Special Cases

**GOAL**: Rewrite logic so special cases become normal cases

**TECHNIQUE**: Use data structures, pointers, or unified interfaces

**Example - Bad (Special Case for Head):**
```python
def remove_from_list(head, target):
    # Special case: removing the head
    if head and head.value == target:
        return head.next
    
    # General case: removing from middle/end
    current = head
    while current and current.next:
        if current.next.value == target:
            current.next = current.next.next
            break
        current = current.next
    
    return head
```

**Example - Good (No Special Case):**
```python
def remove_from_list(head, target):
    # Use indirect pointer - head is just another node
    indirect = head
    while indirect and indirect.value != target:
        indirect = indirect.next
    
    if indirect:
        indirect = indirect.next
    
    return head
```

### Rule 4: Avoid Clever Code

**AVOID**: Nested ternary operators, complex comprehensions, regex when unnecessary

**PREFER**: Explicit if/else, helper functions, string methods

**Example - Bad (Too Clever):**
```python
# Nested ternary
result = [x**2 if x%2==0 else x**3 if x%3==0 else x for x in range(100)]

# Complex regex when simple string methods work
import re
if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
    # Just need basic validation!
```

**Example - Good (Explicit):**
```python
# Clear transformation logic
def transform_number(x):
    if x % 2 == 0:
        return x ** 2
    if x % 3 == 0:
        return x ** 3
    return x

result = [transform_number(x) for x in range(100)]

# Simple string check
if '@' in email and '.' in email.split('@')[1]:
    # Basic validation is often sufficient
```

### Rule 5: Clear Naming

**VARIABLES**: Describe what they hold
**FUNCTIONS**: Describe what they do (verbs)
**CLASSES**: Describe what they are (nouns)
**BOOLEANS**: Use is_, has_, can_ prefixes

**Example - Bad:**
```python
def f(d):
    r = []
    for x in d:
        if x[1] > 100:
            r.append(x[0])
    return r
```

**Example - Good:**
```python
def get_high_value_users(user_records):
    high_value_users = []
    for username, purchase_amount in user_records:
        if purchase_amount > 100:
            high_value_users.append(username)
    return high_value_users

# Or more concisely:
def get_high_value_users(user_records):
    return [username for username, amount in user_records if amount > 100]
```

### Rule 6: Explicit Over Implicit

**AVOID**: Magic numbers, implicit behavior, hidden side effects

**PREFER**: Named constants, explicit parameters, pure functions

**Example - Bad (Magic Numbers & Side Effects):**
```python
def process(data):
    global last_result  # Hidden side effect!
    if len(data) > 100:  # Magic number
        data = data[:100]
    last_result = sum(data) / len(data)
    return last_result
```

**Example - Good (Explicit):**
```python
MAX_DATA_SIZE = 100

def calculate_average(data, max_size=MAX_DATA_SIZE):
    """Calculate average, truncating to max_size if needed."""
    truncated_data = data[:max_size]
    return sum(truncated_data) / len(truncated_data)
```

## Simplification Checklist

Run this checklist on every code block:

### Abstraction Check
- [ ] Is every class/interface actually needed?
- [ ] Do I have 3+ concrete use cases for this abstraction?
- [ ] Could I solve this with a simple function instead?
- [ ] Am I adding this "just in case"?

### Length Check
- [ ] Is any function > 50 lines?
- [ ] Can I split long functions into smaller, focused pieces?
- [ ] Does each function do exactly one thing?
- [ ] Are function names clear about their purpose?

### Complexity Check
- [ ] Are there > 3 levels of indentation anywhere?
- [ ] Can I use early returns to reduce nesting?
- [ ] Can special cases be eliminated through restructuring?
- [ ] Am I using nested ternary operators?

### Readability Check
- [ ] Can a junior developer understand this in < 2 minutes?
- [ ] Are variable/function names self-documenting?
- [ ] Is the "happy path" obvious?
- [ ] Am I using clever tricks that sacrifice clarity?

### Future-Proofing Check
- [ ] Am I solving today's problem or guessing at tomorrow's?
- [ ] Can I remove "just in case" code?
- [ ] Will this be easier or harder to change later?
- [ ] Have I optimized for simplicity over flexibility?

## Refactoring Process

When simplifying code:

1. **Understand Intent** - What is this code trying to do?
2. **Identify Complexity** - What makes it hard to understand?
3. **Propose Simplification** - Show before/after
4. **Explain Trade-offs** - What did we gain/lose?
5. **Get Approval** - Don't simplify without discussing

## Output Format

When suggesting simplifications:

```
### Simplification Opportunity: [Brief Title]

**Current Complexity:** [What makes it complex]
**Lines of Code:** [Before] → [After]
**Improvement:** [What gets better]

**Before:**
```[language]
[current code]
```

**After:**
```[language]
[simplified code]
```

**Why This Is Better:**
- [Reason 1]
- [Reason 2]
- [Reason 3]

**Trade-offs:**
- [Any downsides or considerations]
```

## What NOT to Simplify

Don't sacrifice these for simplicity:

- **Performance** in hot paths (profile first!)
- **Security** checks (explicit validations are good)
- **Error handling** (comprehensive is better than simple)
- **Domain logic** that's inherently complex
- **Team conventions** (follow existing patterns)

## Examples

### Example 1: Configuration Loading

**Before (Complex):**
```python
class ConfigurationManager:
    def __init__(self):
        self.loader = self._create_loader()
        self.validator = self._create_validator()
        self.cache = {}
        
    def _create_loader(self):
        return ConfigLoaderFactory.create_loader('json')
        
    def _create_validator(self):
        return ConfigValidatorFactory.create_validator('strict')
        
    def load_configuration(self, source: str) -> Configuration:
        if source in self.cache:
            return self.cache[source]
        
        raw_config = self.loader.load(source)
        validated_config = self.validator.validate(raw_config)
        config_object = Configuration.from_dict(validated_config)
        
        self.cache[source] = config_object
        return config_object
```

**After (Simple):**
```python
def load_config(file_path: str) -> dict:
    """Load and validate JSON configuration file."""
    with open(file_path) as f:
        config = json.load(f)
    
    required_keys = ['api_key', 'endpoint', 'timeout']
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"Config missing required keys: {missing}")
    
    return config
```

**Improvement:**
- 30 lines → 9 lines (70% reduction)
- No unnecessary classes or factories
- Clear validation logic
- Easy to test and modify

### Example 2: Data Processing

**Before (Clever but Unclear):**
```python
process = lambda data: {k: v if not callable(v) else v() 
                        for k, v in data.items() 
                        if k not in ['_private', '_internal'] 
                        and not k.startswith('_')}
```

**After (Explicit):**
```python
def process_data(data: dict) -> dict:
    """Process data: call functions, filter private keys."""
    result = {}
    
    for key, value in data.items():
        # Skip private keys
        if key.startswith('_'):
            continue
        
        # Call functions, keep other values
        result[key] = value() if callable(value) else value
    
    return result
```

**Improvement:**
- Lambda → named function (easier to test)
- One-liner → structured logic (easier to read)
- Complex condition → simple check with comment
- Can add logging, error handling easily

### Example 3: User Validation

**Before (Nested Complexity):**
```python
def create_user(data):
    if data:
        if 'username' in data:
            if len(data['username']) > 3:
                if 'email' in data:
                    if '@' in data['email']:
                        if 'password' in data:
                            if len(data['password']) >= 8:
                                return User(
                                    username=data['username'],
                                    email=data['email'],
                                    password=hash_password(data['password'])
                                )
    return None
```

**After (Early Returns):**
```python
def create_user(data):
    """Create user from validated data."""
    if not data:
        return None
    
    # Validate username
    username = data.get('username', '')
    if len(username) < 3:
        return None
    
    # Validate email
    email = data.get('email', '')
    if '@' not in email:
        return None
    
    # Validate password
    password = data.get('password', '')
    if len(password) < 8:
        return None
    
    return User(
        username=username,
        email=email,
        password=hash_password(password)
    )
```

**Improvement:**
- 6 indent levels → 2 indent levels
- Clear validation sequence
- Easy to add validation messages
- Each check is independent

## Integration

### Claude Code
Place this file at: `.claude/skills/code-simplifier/SKILL.md`

Create an agent at: `.claude/agents/simplifier.md`:
```markdown
---
name: code-simplifier-agent
description: Automatically simplifies code after generation
triggers: [completion]
---

After generating code, I automatically review for:
- Unnecessary abstractions
- Functions > 50 lines
- Nesting > 3 levels
- Clever code that sacrifices clarity
- Special cases that could be eliminated

I provide specific refactoring suggestions with before/after examples.
```

### Cursor
Add to `.cursorrules`:
```
# Code Simplicity Standards
- Functions under 50 lines
- Max 3 indentation levels  
- No abstractions without 3+ use cases
- Eliminate special cases through restructuring
- Prefer explicit code over clever one-liners
- Early returns to reduce nesting
```

### Kiro
Add to `docs/coding-standards.md` for Kiro to reference.

### Amazon Q / GitHub Copilot
Use as system prompt or project instructions.

## Success Metrics

Good simplification results in:

- ✅ 20-40% reduction in line count
- ✅ Fewer classes/files (consolidation)
- ✅ Faster code review (< 10 min vs > 30 min)
- ✅ Fewer bugs (less surface area)
- ✅ Easier testing (simpler logic)
- ✅ Team velocity improves over time

## Remember

> "Simplicity is the ultimate sophistication." - Leonardo da Vinci

> "I don't want you to understand why it doesn't have the if statement. But I want you to understand that sometimes you can see a problem in a different way and rewrite it so that a special case goes away and becomes the normal case, and that's good code." - Linus Torvalds

The best code is no code. The second best code is simple code.
