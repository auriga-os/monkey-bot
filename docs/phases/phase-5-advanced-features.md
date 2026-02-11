# Phase 5: Advanced Features & Polish (Optional)

**Goal:** Production polish, advanced workflows, and UX improvements

**Value Delivered:** Enterprise-grade features and nice-to-haves for power users

**Prerequisites:** Phase 1-4 must be complete (both agents in production with hardening features)

**Status:** Optional - Implement based on priority and business needs

---

## Strategic Context

Phase 5 is **optional** and focuses on enterprise-grade features that enhance the user experience and operational efficiency. These features are not critical for launch but provide significant value for power users and production scale.

**Key Decision:** Pick features based on:
1. User feedback from Phases 1-4
2. Business priorities
3. Resource availability

You **do not** need to implement all features in this phase. Choose 1-2 that provide the most value for your use case.

---

## Component Options (Pick 1-2)

### Option 1: Recipe/Workflow System

**Purpose:** Enable complex multi-step workflows without writing code

**Use Cases:**
- Weekly marketing reports
- Automated PR reviews
- Content pipeline (research → draft → review → post)
- Data collection and analysis workflows

#### A. Recipe Definition Format (YAML)

```yaml
# recipes/weekly-marketing-report.yaml
name: weekly-marketing-report
description: Generate weekly marketing performance report
version: 1.0

schedule: "0 9 * * 1"  # Monday 9 AM
enabled: true

inputs:
  - name: platforms
    type: list
    default: [twitter, linkedin, instagram]
  - name: period
    type: string
    default: last_week

steps:
  - name: fetch-metrics
    skill: fetch_metrics
    args:
      platforms: $inputs.platforms
      period: $inputs.period
    outputs:
      metrics: $result
    timeout: 60
    retry_on_failure: true
  
  - name: analyze-performance
    skill: analyze_engagement
    args:
      metrics: $steps.fetch-metrics.metrics
    outputs:
      analysis: $result
    depends_on:
      - fetch-metrics
  
  - name: generate-report
    skill: generate_weekly_report
    args:
      analysis: $steps.analyze-performance.analysis
      format: markdown
    outputs:
      report: $result
    depends_on:
      - analyze-performance
  
  - name: send-report
    skill: send_to_chat
    args:
      message: $steps.generate-report.report
      channel: marketing-team
    depends_on:
      - generate-report

on_failure:
  - skill: send_to_chat
    args:
      message: "❌ Weekly report failed: $error"
      channel: admin-alerts

on_success:
  - skill: save_to_memory
    args:
      path: reports/weekly-$timestamp.md
      content: $steps.generate-report.report
```

#### B. Recipe Execution Engine

```python
# emonk/core/recipe_engine.py

from typing import Dict, Any, List
import asyncio

class RecipeEngine:
    """Execute multi-step workflows defined in YAML"""
    
    def __init__(self, skill_executor):
        self.skill_executor = skill_executor
        self.context = {}
    
    async def execute(self, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recipe"""
        
        logger.info(f"Executing recipe: {recipe['name']}")
        
        # Initialize context with inputs
        self.context["inputs"] = recipe.get("inputs", {})
        self.context["steps"] = {}
        
        try:
            # Execute steps in dependency order
            execution_order = self._resolve_dependencies(recipe["steps"])
            
            for step_name in execution_order:
                step = self._get_step(recipe["steps"], step_name)
                result = await self._execute_step(step)
                self.context["steps"][step_name] = result
            
            # Run success handlers
            if "on_success" in recipe:
                await self._execute_handlers(recipe["on_success"])
            
            return {
                "success": True,
                "recipe": recipe["name"],
                "context": self.context
            }
        
        except Exception as e:
            logger.error(f"Recipe failed: {e}")
            
            # Run failure handlers
            if "on_failure" in recipe:
                self.context["error"] = str(e)
                await self._execute_handlers(recipe["on_failure"])
            
            return {
                "success": False,
                "recipe": recipe["name"],
                "error": str(e)
            }
    
    async def _execute_step(self, step: Dict[str, Any]) -> Any:
        """Execute single step"""
        
        step_name = step["name"]
        skill = step["skill"]
        
        # Resolve arguments (substitute variables)
        args = self._resolve_variables(step["args"])
        
        logger.info(f"Executing step: {step_name} (skill: {skill})")
        
        # Execute with timeout and retry
        timeout = step.get("timeout", 300)
        retry = step.get("retry_on_failure", False)
        
        try:
            result = await asyncio.wait_for(
                self.skill_executor.execute(skill, args),
                timeout=timeout
            )
            
            logger.info(f"Step completed: {step_name}")
            return result
        
        except asyncio.TimeoutError:
            if retry:
                logger.warning(f"Step timeout, retrying: {step_name}")
                result = await self.skill_executor.execute(skill, args)
                return result
            raise
        
        except Exception as e:
            if retry:
                logger.warning(f"Step failed, retrying: {step_name}")
                result = await self.skill_executor.execute(skill, args)
                return result
            raise
    
    def _resolve_dependencies(self, steps: List[Dict]) -> List[str]:
        """Resolve step execution order based on dependencies"""
        
        # Build dependency graph
        graph = {}
        for step in steps:
            name = step["name"]
            depends_on = step.get("depends_on", [])
            graph[name] = depends_on
        
        # Topological sort
        visited = set()
        order = []
        
        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for dep in graph.get(node, []):
                visit(dep)
            order.append(node)
        
        for node in graph:
            visit(node)
        
        return order
    
    def _resolve_variables(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve variable references in arguments"""
        
        resolved = {}
        
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("$"):
                # Variable reference
                path = value[1:].split(".")
                resolved[key] = self._get_from_context(path)
            else:
                resolved[key] = value
        
        return resolved
    
    def _get_from_context(self, path: List[str]) -> Any:
        """Get value from context by path"""
        
        current = self.context
        for key in path:
            current = current[key]
        return current
```

#### C. Recipe Management

```python
# emonk/core/recipe_manager.py

class RecipeManager:
    """Manage and execute recipes"""
    
    def __init__(self, recipes_dir: str):
        self.recipes_dir = recipes_dir
        self.recipes = {}
        self.load_recipes()
    
    def load_recipes(self):
        """Load all recipes from directory"""
        
        import yaml
        from pathlib import Path
        
        recipes_path = Path(self.recipes_dir)
        
        for recipe_file in recipes_path.glob("*.yaml"):
            with open(recipe_file) as f:
                recipe = yaml.safe_load(f)
                self.recipes[recipe["name"]] = recipe
        
        logger.info(f"Loaded {len(self.recipes)} recipes")
    
    def get_recipe(self, name: str) -> Dict[str, Any]:
        """Get recipe by name"""
        return self.recipes.get(name)
    
    def list_recipes(self) -> List[str]:
        """List all recipe names"""
        return list(self.recipes.keys())
    
    async def execute_recipe(self, name: str, inputs: Dict = None):
        """Execute recipe by name"""
        
        recipe = self.get_recipe(name)
        if not recipe:
            raise ValueError(f"Recipe not found: {name}")
        
        # Override inputs if provided
        if inputs:
            recipe["inputs"] = inputs
        
        engine = RecipeEngine(skill_executor)
        return await engine.execute(recipe)
```

---

### Option 2: Full MCP Protocol Implementation

**Purpose:** Make skills interoperable with Claude Desktop, Cursor, Zed, and other MCP-compatible tools

**Benefits:**
- Skills work across multiple AI tools
- Leverage 100+ existing MCP servers
- Standardized protocol

#### A. Convert Skills to MCP Servers

```python
# skills/web-search-mcp.py (MCP server)
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("web-search")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search",
            description="Search the web with Perplexity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool"""
    
    if name == "search":
        results = await search_web(
            query=arguments["query"],
            limit=arguments.get("limit", 10)
        )
        
        return [TextContent(
            type="text",
            text=json.dumps(results, indent=2)
        )]
    
    raise ValueError(f"Unknown tool: {name}")

# Run server: uvx mcp install ./skills/web-search-mcp.py
```

#### B. MCP Client Integration

```python
# emonk/integrations/mcp_client.py

from mcp.client import Client
import subprocess

class MCPClient:
    """Client for connecting to MCP servers"""
    
    def __init__(self):
        self.servers = {}
    
    async def connect(self, server_name: str, command: list[str]):
        """Connect to MCP server"""
        
        # Start server process
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Create MCP client
        client = Client(
            read_stream=process.stdout,
            write_stream=process.stdin
        )
        
        # Initialize connection
        await client.initialize()
        
        self.servers[server_name] = {
            "client": client,
            "process": process
        }
        
        logger.info(f"Connected to MCP server: {server_name}")
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict
    ):
        """Call tool on MCP server"""
        
        server = self.servers.get(server_name)
        if not server:
            raise ValueError(f"Server not connected: {server_name}")
        
        client = server["client"]
        result = await client.call_tool(tool_name, arguments)
        
        return result
    
    async def list_tools(self, server_name: str) -> list:
        """List tools available on server"""
        
        server = self.servers.get(server_name)
        if not server:
            raise ValueError(f"Server not connected: {server_name}")
        
        client = server["client"]
        tools = await client.list_tools()
        
        return tools
```

---

### Option 3: Web UI for Campaign Management

**Purpose:** Self-service campaign management without chat interface

**Features:**
- Campaign creation wizard
- Content calendar view
- Post preview and editing
- Approval workflow UI
- Analytics dashboard

#### A. Technology Stack

- **Frontend:** React + Next.js
- **Backend:** FastAPI (already have)
- **Database:** Firestore (already have)
- **Auth:** Google OAuth

#### B. Key Pages

**1. Dashboard**
- Active campaigns overview
- Recent posts
- Performance metrics
- Quick actions

**2. Campaign Creation Wizard**
- Step 1: Topic and duration
- Step 2: Research results
- Step 3: Strategy review
- Step 4: Content calendar
- Step 5: Post previews
- Step 6: Approval and scheduling

**3. Content Calendar**
- Month/week/day view
- Drag-and-drop scheduling
- Status indicators (draft, scheduled, posted)
- Quick edit

**4. Post Editor**
- Live preview for each platform
- Character count
- Brand voice validation
- Image upload
- Emoji picker

**5. Analytics Dashboard**
- Engagement metrics
- Trend analysis
- Best performing posts
- Optimal posting times

#### C. Example Component

```typescript
// components/CampaignWizard.tsx
import React, { useState } from 'react';

export function CampaignWizard() {
  const [step, setStep] = useState(1);
  const [campaign, setCampaign] = useState({
    topic: '',
    duration: 4,
    platforms: []
  });
  
  const handleSubmit = async () => {
    // Call backend API
    const response = await fetch('/api/campaigns', {
      method: 'POST',
      body: JSON.stringify(campaign)
    });
    
    const result = await response.json();
    // Navigate to campaign page
  };
  
  return (
    <div className="campaign-wizard">
      {step === 1 && <TopicStep />}
      {step === 2 && <ResearchStep />}
      {step === 3 && <StrategyStep />}
      {/* ... more steps */}
    </div>
  );
}
```

---

### Option 4: Advanced Analytics & Reporting

**Purpose:** Data-driven insights for content optimization

**Features:**
- Engagement trend analysis
- Content performance correlation
- Optimal posting time recommendations
- Audience sentiment analysis
- Competitor benchmarking

#### A. Analytics Skills

```python
# skills/analytics/analyze_engagement.py

def analyze_engagement(posts: list[dict]) -> dict:
    """Analyze engagement patterns"""
    
    # Group by platform, time, content type
    by_platform = {}
    by_time = {}
    by_content_type = {}
    
    for post in posts:
        platform = post["platform"]
        timestamp = post["posted_at"]
        engagement = post["engagement"]
        
        # Aggregate metrics
        if platform not in by_platform:
            by_platform[platform] = []
        by_platform[platform].append(engagement)
        
        # ... more aggregations
    
    return {
        "by_platform": by_platform,
        "by_time": by_time,
        "by_content_type": by_content_type,
        "trends": detect_trends(posts),
        "recommendations": generate_recommendations(posts)
    }
```

#### B. Visualization

```python
# skills/analytics/visualize.py

import matplotlib.pyplot as plt
import seaborn as sns

def create_engagement_chart(data: dict) -> str:
    """Create engagement visualization"""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot engagement over time
    sns.lineplot(
        data=data,
        x="date",
        y="engagement",
        hue="platform",
        ax=ax
    )
    
    ax.set_title("Engagement Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Engagement Rate (%)")
    
    # Save to file
    output_path = "/tmp/engagement_chart.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    
    return output_path
```

---

### Option 5: Performance Optimization

**Purpose:** Reduce costs and improve response times

**Features:**
- Skill result caching (Redis)
- Parallel skill execution
- LLM response streaming
- Context window optimization
- Database query optimization

#### A. Redis Caching

```python
# emonk/core/cache.py

import redis
import json
from typing import Any
import hashlib

class SkillCache:
    """Cache skill results in Redis"""
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.ttl = 3600  # 1 hour default
    
    def _generate_key(self, skill: str, args: dict) -> str:
        """Generate cache key from skill and args"""
        key_data = f"{skill}:{json.dumps(args, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    async def get(self, skill: str, args: dict) -> Any:
        """Get cached result"""
        key = self._generate_key(skill, args)
        cached = self.redis.get(key)
        
        if cached:
            logger.info(f"Cache hit for {skill}")
            return json.loads(cached)
        
        return None
    
    async def set(self, skill: str, args: dict, result: Any, ttl: int = None):
        """Cache result"""
        key = self._generate_key(skill, args)
        ttl = ttl or self.ttl
        
        self.redis.setex(
            key,
            ttl,
            json.dumps(result)
        )
        
        logger.info(f"Cached result for {skill} (ttl: {ttl}s)")

# Usage
cache = SkillCache("redis://localhost:6379")

# Check cache before executing skill
cached_result = await cache.get("search_web", {"query": "AI news"})
if cached_result:
    return cached_result

# Execute skill
result = await skill_executor.execute("search_web", {"query": "AI news"})

# Cache result
await cache.set("search_web", {"query": "AI news"}, result, ttl=3600)
```

#### B. Parallel Skill Execution

```python
# emonk/core/parallel_executor.py

import asyncio

async def execute_skills_parallel(skills: list[dict]) -> list:
    """Execute multiple skills in parallel"""
    
    tasks = []
    
    for skill_config in skills:
        task = skill_executor.execute(
            skill_config["skill"],
            skill_config["args"]
        )
        tasks.append(task)
    
    # Execute all skills concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle errors
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Skill {skills[i]['skill']} failed: {result}")
            processed_results.append(None)
        else:
            processed_results.append(result)
    
    return processed_results

# Usage: Execute research skills in parallel
results = await execute_skills_parallel([
    {"skill": "search_web", "args": {"query": "AI trends"}},
    {"skill": "analyze_competitor", "args": {"url": "competitor.com"}},
    {"skill": "identify_trends", "args": {"topic": "AI"}}
])

web_results, competitor_results, trends = results
```

---

## Feature Comparison

| Feature | Complexity | Value | Dependencies |
|---------|-----------|-------|--------------|
| Recipe System | Medium | High (automation) | None |
| Full MCP | High | High (interop) | MCP ecosystem |
| Web UI | High | Medium (UX) | Frontend skills |
| Analytics | Medium | Medium (insights) | Data |
| Performance | Medium | High (cost) | Redis |

---

## Recommended Priority Order

**For Marketing-Focused Use Case:**
1. Recipe System (automate reports)
2. Performance Optimization (reduce costs)
3. Web UI (if non-technical users)

**For Developer-Focused Use Case:**
1. Full MCP (tool interoperability)
2. Performance Optimization (response time)
3. Analytics (code metrics)

---

## Implementation Strategy

### Week 1: Choose Features
- Review user feedback from Phase 1-4
- Prioritize based on business value
- Create detailed spec for chosen features

### Week 2-3: Implementation
- Implement chosen features
- Write tests
- Update documentation

### Week 4: Testing & Polish
- Integration testing
- Performance testing
- User acceptance testing
- Documentation updates

---

## Success Criteria

**Recipe System:**
- [ ] 5+ production recipes deployed
- [ ] Recipes execute reliably (>95% success rate)
- [ ] Non-technical users can create recipes

**Full MCP:**
- [ ] Skills work in Claude Desktop
- [ ] Skills work in Cursor
- [ ] 10+ external MCP servers integrated

**Web UI:**
- [ ] Non-technical users can create campaigns
- [ ] Load time < 2 seconds
- [ ] Mobile-responsive design

**Analytics:**
- [ ] Insights lead to >20% engagement improvement
- [ ] Reports generated automatically
- [ ] Actionable recommendations

**Performance:**
- [ ] Cost reduced by >30%
- [ ] Response time <1 second (P95)
- [ ] Cache hit rate >50%

---

## Cost Implications

**Recipe System:** Minimal (execution costs same as manual)

**Full MCP:** None (protocol is free)

**Web UI:**
- Cloud Run frontend: ~$10/month
- CDN (Cloud Storage): ~$5/month

**Analytics:**
- Compute: ~$5/month
- Storage: ~$2/month

**Performance (Redis):**
- Memorystore: ~$30/month (basic tier)
- Savings from caching: ~$50/month
- Net savings: ~$20/month

---

## References

- [Goose Recipe Workflows](../ref/11_goose_recipe_workflows.md) - Recipe patterns
- [MCP Specification](https://modelcontextprotocol.io) - MCP protocol
- [Extension Architecture](../ref/08_goose_extension_architecture.md) - MCP pattern

---

## Conclusion

Phase 5 features are **optional** but provide significant value for production use. Choose features that align with your business priorities and user needs.

**Key Decision Points:**
- Recipe System: Choose if you need workflow automation
- Full MCP: Choose if you want tool interoperability
- Web UI: Choose if you have non-technical users
- Analytics: Choose if you need data-driven insights
- Performance: Choose if costs or latency are concerns

You can always add more features later based on user feedback and business needs.
