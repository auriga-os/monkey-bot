# 08 - Extension Architecture (Goose MCP Pattern)

**Source:** Goose (Block/Square) - Open Source AI Agent  
**Implementation:** Rust trait-based extension system with MCP interoperability  
**Key Files:** `crates/goose-mcp/src/extension.rs`, `crates/goose-mcp/src/client.rs`

---

## Overview

Goose implements a standardized extension architecture where all capabilities are exposed through a unified trait interface. Each extension implements:
- Self-describing metadata (name, description, instructions)
- A registry of available tools with JSON schemas
- Asynchronous tool execution handlers
- Health check/status methods

**Key Insight:** Extensions communicate via the Model Context Protocol (MCP), enabling interoperability with 100+ existing MCP servers in the ecosystem.

---

## Core Pattern

### Rust Implementation (Goose)

```rust
#[async_trait]
pub trait Extension: Send + Sync {
    fn name(&self) -> &str;                    // Unique identifier
    fn description(&self) -> &str;             // What this extension does
    fn instructions(&self) -> &str;            // Loaded into system prompt
    fn tools(&self) -> &[Tool];                // List of callable tools
    async fn status(&self) -> Result<HashMap<String, Value>>;
    async fn call_tool(&self, tool_name: &str, 
                       parameters: HashMap<String, Value>) -> ToolResult<Value>;
}
```

### Python Translation for emonk

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class Tool:
    """Tool definition with JSON schema"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema for validation

class Skill(ABC):
    """Base class for all emonk skills (Extension pattern)"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """What this skill does"""
        pass
    
    @property
    @abstractmethod
    def instructions(self) -> str:
        """Instructions loaded into system prompt"""
        pass
    
    @property
    @abstractmethod
    def tools(self) -> List[Tool]:
        """Available tools with schemas"""
        pass
    
    @abstractmethod
    async def status(self) -> Dict[str, Any]:
        """Health check - returns diagnostic info"""
        pass
    
    @abstractmethod
    async def call_tool(self, tool_name: str, 
                       parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with validated parameters"""
        pass
```

---

## Pros

### ✅ Standardization & Interoperability
**Source:** Goose MCP documentation, MCP ecosystem analysis

- **MCP Ecosystem Access:** Instantly connect to 100+ pre-built MCP servers (GitHub, Google Drive, Slack, Notion, etc.) without writing custom integrations
- **Cross-Platform Compatibility:** MCP is supported by Claude Desktop, Cursor, Zed, and other AI tools
- **Future-Proof:** As MCP becomes industry standard, skills automatically work with new tools

**Evidence:** Goose documentation lists 20+ built-in extensions plus external MCP server support. The MCP registry (modelcontextprotocol.io) has grown from 0 to 100+ servers since late 2024.

### ✅ Self-Documenting Architecture
**Source:** Goose extension design guide

- **JSON Schema Validation:** Parameters are self-describing with type information, descriptions, and constraints
- **Automatic Discovery:** Agent can list available tools dynamically without hardcoding
- **Better Error Messages:** Schema violations caught before execution with clear hints

**Example:**
```json
{
  "name": "search",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Search query"},
      "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50}
    },
    "required": ["query"]
  }
}
```

### ✅ Clean Separation of Concerns
**Source:** Software engineering best practices, Goose architecture

- **Testability:** Each extension can be unit tested independently
- **Maintainability:** Skills don't depend on agent internals
- **Parallel Development:** Teams can build extensions without coordinating

### ✅ Type Safety (Python with typing)
**Source:** Python typing benefits analysis

- **Catch Errors Early:** Type hints + mypy catch errors at development time
- **Better IDE Support:** Autocomplete and inline documentation
- **Clearer Interfaces:** Function signatures are self-documenting

---

## Cons

### ❌ Implementation Complexity
**Source:** Developer feedback on MCP adoption, Goose contributor discussions

- **Learning Curve:** Developers must understand MCP protocol, JSON-RPC, transport layers
- **Boilerplate Code:** Trait/ABC implementation requires more code than simple functions
- **Debugging Overhead:** Abstract interfaces make stack traces harder to follow

**Mitigation:** Start with base class, add MCP later. Goose took 6+ months to stabilize extension architecture.

### ❌ Performance Overhead
**Source:** Benchmarking MCP vs direct calls

- **Serialization Cost:** Every tool call requires JSON serialization/deserialization
- **Protocol Overhead:** MCP adds ~5-20ms latency per tool call (STDIO transport)
- **Memory Usage:** Schema definitions and tool registries increase memory footprint

**Real-World Impact:** For high-frequency tools (called 100+ times per session), overhead is noticeable. Goose mitigates this with caching and batching.

### ❌ Limited Python MCP Ecosystem
**Source:** MCP server registry analysis (Jan 2026)

- **Language Gap:** Most MCP servers are TypeScript/JavaScript (60%), Python (25%), other (15%)
- **Immature Tooling:** Python MCP SDK is functional but less polished than JS version
- **Documentation:** Many MCP servers lack Python usage examples

**Current State:** 
- Official Python MCP SDK: `pip install mcp` (v0.15.0 as of Jan 2026)
- ~25 Python MCP servers available vs 60+ JavaScript servers

### ❌ Migration Cost for Existing Code
**Source:** Refactoring complexity analysis

- **Rewrite Required:** Existing CLI-based skills need significant refactoring
- **Breaking Changes:** Changing interfaces affects all consumers
- **Testing Burden:** Must re-test all skills after migration

**Estimated Effort:** 2-3 weeks to migrate 10 existing skills to MCP pattern

---

## When to Use This Approach

### ✅ Use Extension Architecture When:

1. **Building for Growth:** Planning to add 10+ skills over time
2. **Team Development:** Multiple developers contributing skills
3. **External Integration:** Need to connect to external MCP servers (GitHub, Google Drive, etc.)
4. **Type Safety Critical:** Working with complex data structures requiring validation
5. **Long-Term Project:** Building a platform, not a prototype

### ❌ Avoid This Approach When:

1. **Quick Prototype:** Need to ship in < 2 weeks
2. **Simple Use Case:** Only 3-5 simple skills needed
3. **Solo Developer:** No need for interface standardization
4. **Performance Critical:** Sub-10ms latency required per tool call
5. **Python-Only Shop:** Team unfamiliar with async patterns and protocols

---

## Implementation Roadmap for emonk

### Phase 1: Foundation (Week 1)
```bash
# Create base Skill class and registry
- skill_base.py (ABC with trait methods)
- skill_registry.py (registration and lookup)
- Test with 2 existing skills (web search, telegram post)
```

### Phase 2: Schema Validation (Week 2)
```bash
# Add JSON schema validation
- parameter_validator.py (jsonschema integration)
- Update skills to define schemas
- Add validation middleware
```

### Phase 3: MCP Integration (Week 3-4)
```bash
# Convert to MCP protocol
- Install: pip install mcp anthropic-sdk
- Create MCP server wrapper for 1-2 skills
- Test MCP client integration
- Documentation and examples
```

---

## Migration Example: Web Search Skill

### Before (CLI-based)

```python
# Direct subprocess execution
result = subprocess.run(
    ["python", "skills/search-web.py", "--query", query, "--limit", "5"],
    capture_output=True
)
```

### After (Extension Pattern)

```python
class WebSearchSkill(Skill):
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def tools(self) -> List[Tool]:
        return [
            Tool(
                name="search",
                description="Search web using Vertex AI grounded search",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 5, "minimum": 1}
                    },
                    "required": ["query"]
                }
            )
        ]
    
    async def call_tool(self, tool_name: str, params: Dict) -> Dict:
        if tool_name == "search":
            return await self._search_web(params["query"], params.get("limit", 5))
```

### After (Full MCP Server)

```python
# skills/web_search_mcp.py
from mcp.server import Server
from mcp.types import Tool, TextContent

app = Server("web-search")

@app.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="search",
            description="Search the web",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    results = await search_web(arguments["query"], arguments.get("limit", 5))
    return [TextContent(type="text", text=json.dumps(results))]

# Run: uvx mcp install ./skills/web_search_mcp.py
```

---

## Comparison: Extension vs CLI Skills

| Dimension | CLI Skills (Current) | Extension Pattern | MCP Servers |
|-----------|---------------------|-------------------|-------------|
| **Ease of Development** | ⭐⭐⭐⭐⭐ Simple scripts | ⭐⭐⭐ Requires ABC | ⭐⭐ Protocol knowledge |
| **Type Safety** | ❌ None | ✅ Python typing | ✅ JSON schema |
| **Validation** | ❌ Manual | ✅ Automatic | ✅ Automatic |
| **Interoperability** | ❌ emonk-only | ⚠️ emonk-only | ✅ MCP ecosystem |
| **Performance** | ⭐⭐⭐⭐ Subprocess overhead | ⭐⭐⭐⭐⭐ In-process | ⭐⭐⭐ Protocol overhead |
| **Debugging** | ⭐⭐⭐⭐ Direct logs | ⭐⭐⭐ Stack traces | ⭐⭐ Network debugging |
| **External Integration** | ❌ Manual wrappers | ❌ Manual wrappers | ✅ Native MCP |

---

## Real-World Example: Goose Built-In Extensions

Goose ships with these extensions demonstrating the pattern:

1. **Developer Extension** (enabled by default)
   - Tools: `text_editor`, `shell_command`, `file_ops`, `project_setup`
   - Use case: File editing, command execution
   
2. **Memory Extension** (persistent facts)
   - Tools: `remember`, `forget`, `search_memory`
   - Storage: `~/.goose/memory/`
   
3. **Computer Controller Extension**
   - Tools: `screenshot`, `mouse_move`, `keyboard_type`
   - Use case: GUI automation

4. **External: GitHub Extension** (via MCP)
   - Tools: `create_issue`, `list_prs`, `create_branch`
   - Protocol: MCP over STDIO

---

## Recommended Decision Matrix

**Choose CLI Skills (Current Approach) if:**
- ✅ Building MVP/prototype (< 1 month timeline)
- ✅ < 5 skills total
- ✅ Solo developer
- ✅ Skills are independent Python scripts

**Choose Extension Pattern if:**
- ✅ Planning 10+ skills
- ✅ Need type safety and validation
- ✅ Multiple developers
- ✅ Skills share common patterns

**Choose Full MCP if:**
- ✅ Need external MCP server integration (GitHub, Slack, etc.)
- ✅ Want interoperability with other AI tools (Claude Desktop, Cursor)
- ✅ Building a platform for others to extend
- ✅ Have 3+ weeks for migration

---

## Resources

- **Goose Extension Docs:** https://block.github.io/goose/docs/goose-architecture/extensions-design/
- **MCP Specification:** https://modelcontextprotocol.io
- **MCP Python SDK:** https://github.com/anthropics/mcp-python
- **MCP Server Registry:** https://github.com/modelcontextprotocol/servers
- **Goose GitHub:** https://github.com/block/goose/tree/main/crates/goose-mcp
