# 11 - Recipe/Workflow System (Goose Declarative Automation)

**Source:** Goose (Block/Square) - Open Source AI Agent  
**Implementation:** YAML-based workflow definitions with sub-recipe orchestration  
**Key Feature:** Shareable, reusable agent configurations

---

## Overview

Goose recipes are declarative workflow definitions that package:
- **Instructions & Prompts:** What the agent should do
- **Parameters:** Configurable inputs (substituted into prompts)
- **Extensions/Tools:** Required skills
- **Activities:** Example prompts for users (UI feature)
- **Sub-recipes:** Orchestration of other recipes (sequential/parallel)
- **Retry Logic:** Automatic retry with success validation
- **Response Schema:** Structured output (JSON schema)

**Key Insight:** Recipes turn complex multi-step workflows into shareable configuration files that can be version-controlled, tested, and reused across sessions.

---

## Core Pattern

### Recipe YAML Structure

```yaml
version: 1.0.0
title: "Daily Competitor Analysis"
description: "Automated competitor pricing research and reporting"

# At least one of instructions or prompt required
instructions: |
  Analyze competitor pricing daily. Use grounded web search for current data.
  Always cite sources. Format results as a markdown table showing:
  - Competitor name
  - Current price  
  - Change from yesterday (% and $)
  - URL source

prompt: "Analyze pricing for competitors: {competitors}. Today is {date}."

# Parameters with types and validation
parameters:
  - name: competitors
    type: array
    description: "List of competitor company names"
    required: true
  - name: date
    type: string
    description: "Date for analysis (YYYY-MM-DD)"
    required: false
    default: "today"
  - name: notification_channel
    type: string
    description: "Where to send results (telegram, email, slack)"
    default: "telegram"

# Required skills/extensions
extensions:
  - type: builtin
    name: developer
  - type: external
    command: "python skills/search-web-mcp.py"
    name: "web_search"

# Example prompts for UI (optional)
activities:
  - message: "Quick analysis"
    prompt: "Analyze {competitors} pricing right now"
  - message: "Weekly report"
    prompt: "Generate a weekly pricing trends report for {competitors}"

# Sub-recipe orchestration
sub_recipes:
  - path: "./recipes/fetch_competitor_urls.yaml"
    parallel: false
  - path: "./recipes/scrape_pricing_data.yaml"
    parallel: false
  - path: "./recipes/generate_report.yaml"
    parallel: false
  - path: "./recipes/post_to_telegram.yaml"
    parallel: false

# Retry logic
retry:
  max_attempts: 3
  success_check: "test -f ./output/competitor_report.md"  # Shell command
  on_failure: "python scripts/notify_failure.py"

# Expected response structure (for automation)
response:
  schema:
    type: object
    properties:
      competitors:
        type: array
        items:
          type: object
          properties:
            name: string
            price: number
            change_percent: number
            url: string
      analysis: string
      timestamp: string
    required: ["competitors", "timestamp"]
```

### Python Implementation for emonk

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import yaml
import asyncio

@dataclass
class Parameter:
    """Recipe parameter definition"""
    name: str
    type: str  # "string", "integer", "array", "object", "boolean"
    description: str
    required: bool = False
    default: Optional[Any] = None

@dataclass
class Extension:
    """Extension/skill requirement"""
    type: str  # "builtin" or "external"
    name: str
    command: Optional[str] = None  # For external MCP servers

@dataclass
class SubRecipe:
    """Reference to another recipe"""
    path: str
    parallel: bool = False  # Run in parallel with other parallel sub-recipes

@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    success_check: Optional[str] = None  # Shell command that returns 0 on success
    on_failure: Optional[str] = None  # Shell command to run on final failure

@dataclass
class ResponseSchema:
    """Expected response structure"""
    schema: Dict[str, Any]  # JSON schema

@dataclass
class Recipe:
    """Goose-style recipe for reusable workflows"""
    version: str
    title: str
    description: str
    instructions: Optional[str] = None
    prompt: Optional[str] = None
    parameters: List[Parameter] = field(default_factory=list)
    extensions: List[Extension] = field(default_factory=list)
    sub_recipes: List[SubRecipe] = field(default_factory=list)
    retry: Optional[RetryConfig] = None
    response: Optional[ResponseSchema] = None
    
    @classmethod
    def from_yaml(cls, path: str) -> "Recipe":
        """Load recipe from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        # Validate: must have instructions or prompt
        if not data.get("instructions") and not data.get("prompt"):
            raise ValueError("Recipe must have either 'instructions' or 'prompt'")
        
        # Parse nested structures
        parameters = [Parameter(**p) for p in data.get("parameters", [])]
        extensions = [Extension(**e) for e in data.get("extensions", [])]
        
        sub_recipes = []
        for sr in data.get("sub_recipes", []):
            if isinstance(sr, str):
                sub_recipes.append(SubRecipe(path=sr))
            else:
                sub_recipes.append(SubRecipe(**sr))
        
        retry = RetryConfig(**data["retry"]) if "retry" in data else None
        response = ResponseSchema(**data["response"]) if "response" in data else None
        
        return cls(
            version=data.get("version", "1.0.0"),
            title=data["title"],
            description=data["description"],
            instructions=data.get("instructions"),
            prompt=data.get("prompt"),
            parameters=parameters,
            extensions=extensions,
            sub_recipes=sub_recipes,
            retry=retry,
            response=response
        )
    
    def substitute_parameters(self, params: Dict[str, Any]) -> str:
        """Substitute {param} placeholders in prompt/instructions"""
        text = self.prompt or self.instructions or ""
        
        for param in self.parameters:
            if param.name in params:
                value = params[param.name]
                
                # Handle array formatting
                if param.type == "array" and isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                
                text = text.replace(f"{{{param.name}}}", str(value))
            elif param.default is not None:
                text = text.replace(f"{{{param.name}}}", str(param.default))
        
        return text
    
    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """Validate provided parameters against schema"""
        errors = []
        
        for param in self.parameters:
            # Check required parameters
            if param.required and param.name not in params:
                errors.append(f"Missing required parameter: {param.name}")
                continue
            
            # Type checking
            if param.name in params:
                value = params[param.name]
                expected_type = {
                    "string": str,
                    "integer": int,
                    "array": list,
                    "object": dict,
                    "boolean": bool
                }.get(param.type)
                
                if expected_type and not isinstance(value, expected_type):
                    errors.append(
                        f"Parameter '{param.name}' must be {param.type}, "
                        f"got {type(value).__name__}"
                    )
        
        return errors

class RecipeExecutor:
    """Execute recipes with retry logic and sub-recipe orchestration"""
    
    def __init__(self, agent_loop_func, skill_registry):
        self.agent_loop = agent_loop_func
        self.skill_registry = skill_registry
        self.recipe_cache: Dict[str, Recipe] = {}
    
    async def execute(self, recipe: Recipe, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a recipe with full retry/sub-recipe support.
        
        Returns:
            Dict with results and metadata
        """
        # Validate parameters
        errors = recipe.validate_parameters(params)
        if errors:
            raise ValueError(f"Parameter validation failed: {errors}")
        
        # Substitute parameters into prompt/instructions
        substituted_text = recipe.substitute_parameters(params)
        
        # Execute with retry logic
        max_attempts = recipe.retry.max_attempts if recipe.retry else 1
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                log.info(
                    "recipe_attempt",
                    recipe=recipe.title,
                    attempt=attempt,
                    max_attempts=max_attempts
                )
                
                # Execute sub-recipes first (if any)
                if recipe.sub_recipes:
                    await self._execute_sub_recipes(recipe.sub_recipes, params)
                
                # Execute main recipe
                result = await self.agent_loop(
                    user_message=substituted_text,
                    instructions=recipe.instructions,
                    required_extensions=[ext.name for ext in recipe.extensions]
                )
                
                # Validate response against schema (if provided)
                if recipe.response:
                    validated = self._validate_response(result, recipe.response.schema)
                    if not validated:
                        raise ValueError("Response validation failed")
                
                # Run success check (if configured)
                if recipe.retry and recipe.retry.success_check:
                    success = await self._run_success_check(recipe.retry.success_check)
                    if not success:
                        raise ValueError("Success check failed")
                
                # Success!
                log.info(
                    "recipe_success",
                    recipe=recipe.title,
                    attempt=attempt
                )
                return {
                    "status": "success",
                    "result": result,
                    "attempts": attempt,
                    "recipe": recipe.title
                }
                
            except Exception as e:
                last_error = e
                log.warning(
                    "recipe_attempt_failed",
                    recipe=recipe.title,
                    attempt=attempt,
                    error=str(e)
                )
                
                if attempt < max_attempts:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2 ** attempt)
                else:
                    # Final attempt failed
                    if recipe.retry and recipe.retry.on_failure:
                        await self._handle_failure(recipe.retry.on_failure, e)
        
        # All attempts exhausted
        raise RuntimeError(
            f"Recipe '{recipe.title}' failed after {max_attempts} attempts: {last_error}"
        )
    
    async def _execute_sub_recipes(self, sub_recipes: List[SubRecipe], params: Dict):
        """Execute sub-recipes (sequential or parallel)"""
        # Group by parallel flag
        sequential = [sr for sr in sub_recipes if not sr.parallel]
        parallel = [sr for sr in sub_recipes if sr.parallel]
        
        # Execute sequential sub-recipes
        for sub in sequential:
            recipe = self._load_recipe(sub.path)
            await self.execute(recipe, params)
        
        # Execute parallel sub-recipes concurrently
        if parallel:
            tasks = []
            for sub in parallel:
                recipe = self._load_recipe(sub.path)
                tasks.append(self.execute(recipe, params))
            await asyncio.gather(*tasks)
    
    def _load_recipe(self, path: str) -> Recipe:
        """Load recipe from file (with caching)"""
        if path not in self.recipe_cache:
            self.recipe_cache[path] = Recipe.from_yaml(path)
        return self.recipe_cache[path]
    
    async def _run_success_check(self, command: str) -> bool:
        """Run shell command to validate success"""
        try:
            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
        except Exception as e:
            log.error(f"Success check failed: {e}")
            return False
    
    async def _handle_failure(self, command: str, error: Exception):
        """Run failure callback"""
        try:
            result = await asyncio.create_subprocess_shell(
                f"{command} '{str(error)}'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
        except Exception as e:
            log.error(f"Failure handler error: {e}")
    
    def _validate_response(self, result: Any, schema: Dict) -> bool:
        """Validate response against JSON schema"""
        try:
            import jsonschema
            jsonschema.validate(instance=result, schema=schema)
            return True
        except Exception as e:
            log.error(f"Response validation failed: {e}")
            return False
```

---

## Pros

### ✅ Declarative Configuration
**Source:** Infrastructure-as-Code best practices, GitOps patterns

- **Version Control:** Recipes are YAML files that can be committed to Git
- **Code Review:** Changes to workflows go through standard PR process
- **Rollback:** Easy to revert to previous recipe version
- **Documentation:** Recipe IS the documentation (self-documenting workflows)

**Example Git Workflow:**
```bash
# recipes/competitor-analysis.yaml
git log recipes/competitor-analysis.yaml
# Shows who changed what, when, and why (commit messages)

git diff HEAD~1 recipes/competitor-analysis.yaml
# Compare current recipe with previous version
```

### ✅ Reusability & Sharing
**Source:** Goose Recipe Cookbook, community recipes

- **Templates:** Create base recipes that others customize
- **Marketplace:** Goose has community recipe repository (50+ recipes)
- **Cross-Project:** Same recipe works for different agents/teams
- **URL Sharing:** Goose Desktop can open recipes from URLs

**Real-World Example:** Goose community recipe "GitHub Issue to PR" has been reused 500+ times across different projects.

### ✅ Sub-Recipe Orchestration
**Source:** Goose sub-recipes documentation

- **Composition:** Break complex workflows into manageable pieces
- **Parallel Execution:** Run independent sub-recipes concurrently (faster)
- **Dependency Management:** Sequential sub-recipes ensure proper order
- **Isolation:** Each sub-recipe is testable independently

**Example: Multi-Step Social Media Campaign**
```yaml
# main_recipe.yaml
sub_recipes:
  # Sequential: must complete in order
  - path: "./01_research_trending_topics.yaml"
    parallel: false
  - path: "./02_generate_content_ideas.yaml"
    parallel: false
  
  # Parallel: can run simultaneously
  - path: "./03a_create_twitter_post.yaml"
    parallel: true
  - path: "./03b_create_linkedin_post.yaml"
    parallel: true
  - path: "./03c_create_instagram_caption.yaml"
    parallel: true
  
  # Sequential: wait for all parallel to finish
  - path: "./04_review_and_approve.yaml"
    parallel: false
```

### ✅ Integration with Cron/Automation
**Source:** Goose scheduled recipes feature

- **Headless Execution:** Recipes run without user interaction
- **Parameter Injection:** Pass runtime values (date, environment vars)
- **Success/Failure Hooks:** Automatic notifications on completion

**Integration with emonk Cron System:**
```python
# cron_job.py
cron_job = {
    "id": "daily-competitor-analysis",
    "schedule": "0 9 * * *",  # Daily at 9 AM
    "recipe_path": "recipes/competitor-analysis.yaml",
    "parameters": {
        "competitors": ["CompanyA", "CompanyB", "CompanyC"],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "notification_channel": "telegram"
    }
}

# When cron triggers
recipe = Recipe.from_yaml(cron_job["recipe_path"])
result = await recipe_executor.execute(recipe, cron_job["parameters"])
```

---

## Cons

### ❌ YAML Complexity
**Source:** Developer experience feedback, YAML pitfalls

- **Learning Curve:** Non-developers struggle with YAML syntax (indentation, types)
- **Limited Logic:** Can't express complex conditionals or loops in YAML
- **Debugging Pain:** YAML parsing errors are cryptic ("mapping values are not allowed here")
- **Type Safety:** YAML doesn't enforce types until runtime

**Common YAML Mistakes:**
```yaml
# BAD: Inconsistent indentation
parameters:
  - name: query
   type: string  # Wrong indent

# BAD: Type confusion
limit: "5"  # String, not integer

# BAD: Missing quotes
description: This is: a problem  # Colon breaks parsing
```

**Mitigation:** Use YAML linters (yamllint), schema validation, IDE plugins.

### ❌ Limited Expressiveness
**Source:** Declarative vs imperative programming trade-offs

- **No Control Flow:** Can't easily express "if X then Y else Z"
- **No Loops:** Can't iterate over dynamic lists
- **State Management:** Hard to maintain state across sub-recipes
- **Error Handling:** Limited to retry/fallback, no custom recovery logic

**What You CAN'T Do:**
```yaml
# IMPOSSIBLE in pure YAML
if competitor_count > 10:
    use_parallel_execution = true
else:
    use_sequential_execution = true

for competitor in competitors:
    if competitor.price_change > 20%:
        send_alert(competitor)
```

**Workaround:** Use Python scripts as sub-recipes for complex logic.

### ❌ Performance Overhead
**Source:** YAML parsing benchmarks

- **Parse Time:** Loading/validating YAML adds 50-200ms per recipe
- **Substitution Cost:** Parameter substitution requires string scanning
- **Schema Validation:** JSON schema validation adds 10-50ms
- **Sub-Recipe Loading:** Each sub-recipe requires separate file I/O

**Real-World Impact:** Complex recipe with 10 sub-recipes can add 1-2 seconds startup time.

### ❌ Versioning & Migration
**Source:** Schema evolution challenges

- **Breaking Changes:** Updating recipe schema breaks old recipes
- **Migration Burden:** Must manually update all existing recipes
- **Version Compatibility:** Hard to support multiple recipe versions
- **Default Value Changes:** Changing defaults affects existing workflows

**Example Migration Pain:**
```yaml
# v1.0.0 (old)
extensions:
  - name: web_search

# v2.0.0 (new - requires 'type' field)
extensions:
  - type: external
    name: web_search
    command: "python skills/search.py"

# Result: All v1.0.0 recipes break
```

---

## When to Use This Approach

### ✅ Use Recipe System When:

1. **Repetitive Workflows:** Running same automation 10+ times
2. **Team Collaboration:** Multiple people need to trigger same workflows
3. **Non-Technical Users:** Want to empower PMs/marketers to run automations
4. **Complex Orchestration:** Workflows with 5+ sequential/parallel steps
5. **Audit Trail:** Need version control and change tracking for workflows

### ❌ Avoid This Approach When:

1. **One-Off Tasks:** Workflow will only run once or twice
2. **Highly Dynamic:** Workflow logic changes based on runtime data
3. **Simple Use Case:** 1-2 step workflows (direct agent call is simpler)
4. **Performance Critical:** Sub-100ms latency required
5. **Complex State:** Workflow requires maintaining complex state across steps

---

## Alternative Approaches

### Alternative 1: Code-Based Workflows (Python Functions)

```python
async def competitor_analysis_workflow(competitors: List[str]):
    """Imperative workflow definition"""
    # Research
    urls = await fetch_competitor_urls(competitors)
    
    # Scrape (parallel)
    prices = await asyncio.gather(*[
        scrape_pricing(url) for url in urls
    ])
    
    # Analyze
    report = await generate_report(prices)
    
    # Notify
    if any(p.change_percent > 10 for p in prices):
        await send_alert(report)
    
    return report
```

**Pros:** Full Python power, easy debugging, type hints  
**Cons:** Not shareable, requires code changes, no version control for non-devs

### Alternative 2: Workflow Engines (Temporal, Airflow)

**Temporal Example:**
```python
@workflow.defn
class CompetitorAnalysisWorkflow:
    @workflow.run
    async def run(self, competitors: List[str]) -> Report:
        urls = await workflow.execute_activity(
            fetch_urls, competitors,
            start_to_close_timeout=timedelta(minutes=5)
        )
        # ... more activities
```

**Pros:** Enterprise-grade, observability, retry/recovery, durable execution  
**Cons:** Heavy infrastructure (requires Temporal server), steep learning curve

---

## Implementation Roadmap for emonk

### Week 1: Recipe Data Model
```python
# Day 1-2: Define Recipe, Parameter, Extension classes
# Day 3: YAML parsing (from_yaml method)
# Day 4: Parameter validation and substitution
# Day 5: Unit tests
```

### Week 2: Recipe Executor
```python
# Day 1-2: Basic executor (no sub-recipes)
# Day 3: Retry logic
# Day 4: Success checks and failure callbacks
# Day 5: Integration with agent loop
```

### Week 3: Sub-Recipe Orchestration
```python
# Day 1-2: Sequential sub-recipes
# Day 3-4: Parallel sub-recipes (asyncio.gather)
# Day 5: Dependency resolution
```

### Week 4: Cron Integration
```python
# Day 1-2: Cron job config with recipe paths
# Day 3: Runtime parameter injection
# Day 4-5: Testing and documentation
```

---

## Real-World Example: Goose Recipe

From Goose GitHub repository (`recipe.yaml`):

```yaml
version: 1.0.0
title: "404Portfolio"
description: "Create personalized, creative 404 pages using public profile data"

instructions: |
  Create an engaging 404 error page that tells a creative story using a user's 
  recent public content from GitHub, Dev.to, or Bluesky.
  
  The page should be fully built with HTML, CSS, and JavaScript, featuring:
  * Responsive design
  * Personal branding elements (name, handle, avatar)
  * Narrative-driven layout

  Wrap the user's activity into a story — for example:
  "This page may be lost, but @username is building something amazing..."

  Ask the user:
  1. Which platform to use: GitHub, Dev.to, or Bluesky
  2. Their username on that platform

  Then generate the complete code in a folder called 404-story.

activities:
  - "Build error page from GitHub repos"
  - "Generate error page from dev.to blog posts"
  - "Create a 404 page featuring Bluesky bio"

extensions:
  - type: builtin
    name: developer
  - type: builtin
    name: computercontroller
```

**Usage:**
```bash
goose run --recipe recipe.yaml
# Or via URL:
goose run --recipe https://raw.githubusercontent.com/block/goose/main/recipe.yaml
```

---

## Comparison Matrix

| Dimension | Recipe System | Python Functions | Workflow Engine |
|-----------|--------------|------------------|-----------------|
| **Ease of Creation** | ⭐⭐⭐⭐ YAML | ⭐⭐⭐⭐⭐ Code | ⭐⭐ Complex setup |
| **Shareability** | ⭐⭐⭐⭐⭐ URLs/Git | ⭐⭐ Code only | ⭐⭐⭐ DSL/Code |
| **Version Control** | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐⭐⭐ Native | ⭐⭐⭐⭐⭐ Native |
| **Non-Dev Friendly** | ⭐⭐⭐⭐ YAML editing | ❌ Requires coding | ❌ Complex |
| **Expressiveness** | ⭐⭐⭐ Limited | ⭐⭐⭐⭐⭐ Full Python | ⭐⭐⭐⭐ DSL |
| **Debugging** | ⭐⭐ YAML errors | ⭐⭐⭐⭐⭐ Python debugger | ⭐⭐⭐ UI tools |
| **Performance** | ⭐⭐⭐ Overhead | ⭐⭐⭐⭐⭐ Fast | ⭐⭐⭐ RPC overhead |
| **Observability** | ⭐⭐ Logs | ⭐⭐⭐ Custom | ⭐⭐⭐⭐⭐ Built-in |

---

## Resources

- **Goose Recipes Guide:** https://block.github.io/goose/docs/guides/recipes/
- **Recipe Reference:** https://block.github.io/goose/docs/guides/recipes/recipe-reference/
- **Recipe Generator:** https://block.github.io/goose/recipe-generator/
- **Recipe Cookbook:** https://block.github.io/goose/recipes/
- **Sub-recipes Blog:** https://block.github.io/goose/blog/2025/09/15/subrecipes-in-goose/
- **YAML Best Practices:** https://yaml.org/spec/1.2.2/
- **JSON Schema:** https://json-schema.org/
