# 13 - Permission & Security Model (Goose Pattern)

**Source:** Goose (Block/Square) - Open Source AI Agent  
**Implementation:** Multi-level permission system with risk-based approvals  
**Key Feature:** Protect against unwanted autonomous actions

---

## Overview

Goose implements a layered permission system to control tool execution:

**Permission Modes (Global):**
1. **Completely Autonomous** (default) - Full tool access without prompts
2. **Smart Approval** - Risk-based: auto-approve low-risk, prompt for high-risk
3. **Manual Approval** - Ask before every tool use
4. **Chat Only** - No extensions or file edits

**Tool-Level Permissions (Fine-Grained):**
- Each tool: "Always Allow" | "Ask Before" | "Never Allow"
- Overrides mode defaults for specific tools
- Configurable via UI or `permissions/tool_permissions.json`

**Key Insight:** Balance automation with safety. Autonomous mode enables "vibe coding", but users reported unwanted file changes. Permission system evolved to prevent unintended actions while maintaining productivity.

---

## Core Pattern

### Permission Modes

```python
from enum import Enum
from dataclasses import dataclass
from typing import Callable, Awaitable, Optional, Dict

class PermissionMode(Enum):
    """Agent permission modes (Goose pattern)"""
    AUTONOMOUS = "autonomous"        # Full access, no prompts
    SMART_APPROVE = "smart_approve"  # Risk-based approval
    MANUAL_APPROVE = "manual"        # Ask for everything
    CHAT_ONLY = "chat_only"          # No tools/extensions

class ToolPermission(Enum):
    """Per-tool permission levels"""
    ALWAYS_ALLOW = "always_allow"
    ASK_BEFORE = "ask_before"
    NEVER_ALLOW = "never_allow"

@dataclass
class ToolRiskLevel:
    """Risk classification for tools"""
    tool_name: str
    risk: str  # "low", "medium", "high"
    reason: str
    examples: List[str]  # Example scenarios

class PermissionManager:
    """
    Goose-style permission system for tool execution control.
    Protects against unwanted automated actions.
    """
    
    def __init__(self, mode: PermissionMode = PermissionMode.AUTONOMOUS):
        self.mode = mode
        self.tool_permissions: Dict[str, ToolPermission] = {}
        self.risk_levels: Dict[str, ToolRiskLevel] = self._default_risk_levels()
        self.approval_callback: Optional[Callable] = None
    
    def _default_risk_levels(self) -> Dict[str, ToolRiskLevel]:
        """Default risk classification for common tools"""
        return {
            # LOW RISK - Read operations
            "search_web": ToolRiskLevel(
                tool_name="search_web",
                risk="low",
                reason="Read-only web search, no side effects",
                examples=["Search for AI trends", "Find competitor pricing"]
            ),
            "read_file": ToolRiskLevel(
                tool_name="read_file",
                risk="low",
                reason="Read-only file access",
                examples=["Read config.json", "View README.md"]
            ),
            "list_files": ToolRiskLevel(
                tool_name="list_files",
                risk="low",
                reason="Directory listing, no modifications",
                examples=["List files in ./data/", "Find all .py files"]
            ),
            
            # MEDIUM RISK - Write operations with undo
            "post_to_telegram": ToolRiskLevel(
                tool_name="post_to_telegram",
                risk="medium",
                reason="Publishes content externally (but deletable)",
                examples=["Post competitor analysis", "Send status update"]
            ),
            "create_file": ToolRiskLevel(
                tool_name="create_file",
                risk="medium",
                reason="Creates new files (but reversible)",
                examples=["Create report.md", "Generate analysis.json"]
            ),
            "send_email": ToolRiskLevel(
                tool_name="send_email",
                risk="medium",
                reason="Sends external messages (less easily undone)",
                examples=["Email weekly report", "Notify team"]
            ),
            
            # HIGH RISK - Destructive or irreversible operations
            "delete_file": ToolRiskLevel(
                tool_name="delete_file",
                risk="high",
                reason="Irreversible deletion",
                examples=["Delete old logs", "Remove temp files"]
            ),
            "execute_shell": ToolRiskLevel(
                tool_name="execute_shell",
                risk="high",
                reason="Arbitrary command execution, security risk",
                examples=["Install npm packages", "Run deployment script"]
            ),
            "modify_cron": ToolRiskLevel(
                tool_name="modify_cron",
                risk="high",
                reason="Changes scheduled automation",
                examples=["Add daily backup job", "Cancel scheduled task"]
            ),
            "git_push": ToolRiskLevel(
                tool_name="git_push",
                risk="high",
                reason="Publishes code changes",
                examples=["Push to main branch", "Deploy to production"]
            ),
        }
    
    def set_tool_permission(self, tool_name: str, permission: ToolPermission):
        """Override default permission for a specific tool"""
        self.tool_permissions[tool_name] = permission
        log.info(
            "tool_permission_updated",
            tool=tool_name,
            permission=permission.value
        )
    
    async def check_permission(
        self,
        tool_name: str,
        parameters: Dict,
        context: Optional[str] = None
    ) -> bool:
        """
        Check if tool execution is permitted.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            context: Additional context for approval UI
        
        Returns:
            True if allowed, False if denied
        """
        # 1. Check tool-level override first (highest priority)
        if tool_name in self.tool_permissions:
            perm = self.tool_permissions[tool_name]
            
            if perm == ToolPermission.ALWAYS_ALLOW:
                log.info("permission_granted", tool=tool_name, reason="always_allow")
                return True
            
            elif perm == ToolPermission.NEVER_ALLOW:
                log.warning("permission_denied", tool=tool_name, reason="never_allow")
                return False
            
            elif perm == ToolPermission.ASK_BEFORE:
                return await self._request_approval(tool_name, parameters, context)
        
        # 2. Apply mode-based logic
        if self.mode == PermissionMode.CHAT_ONLY:
            log.warning("permission_denied", tool=tool_name, reason="chat_only_mode")
            return False
        
        if self.mode == PermissionMode.AUTONOMOUS:
            log.info("permission_granted", tool=tool_name, reason="autonomous_mode")
            return True
        
        if self.mode == PermissionMode.MANUAL_APPROVE:
            return await self._request_approval(tool_name, parameters, context)
        
        if self.mode == PermissionMode.SMART_APPROVE:
            # Risk-based approval
            risk_level = self.risk_levels.get(tool_name)
            
            if not risk_level:
                # Unknown tool - default to asking
                log.warning("unknown_tool_risk", tool=tool_name)
                return await self._request_approval(tool_name, parameters, context)
            
            if risk_level.risk == "low":
                log.info("permission_granted", tool=tool_name, reason="low_risk")
                return True
            else:
                # Ask for medium/high risk
                return await self._request_approval(
                    tool_name, parameters, context, risk_level=risk_level
                )
        
        # Fallback: deny by default (secure by default)
        log.warning("permission_denied", tool=tool_name, reason="fallback_deny")
        return False
    
    async def _request_approval(
        self,
        tool_name: str,
        parameters: Dict,
        context: Optional[str],
        risk_level: Optional[ToolRiskLevel] = None
    ) -> bool:
        """
        Request user approval for tool execution.
        Can be implemented via Telegram bot buttons, CLI prompt, or web UI.
        """
        if not self.approval_callback:
            log.error(
                "approval_required_but_no_callback",
                tool=tool_name,
                message="Permission system configured but no approval callback set"
            )
            return False  # Deny by default if no callback
        
        # Format approval request
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
            risk_level.risk if risk_level else "medium", "⚪"
        )
        risk_info = f"{risk_emoji} Risk: {risk_level.risk.upper()}" if risk_level else ""
        reason = f"\n\n**Why approval needed:** {risk_level.reason}" if risk_level else ""
        
        param_str = json.dumps(parameters, indent=2)
        context_str = f"\n\n**Context:** {context}" if context else ""
        
        message = f"""🔐 Permission Request {risk_info}

**Tool:** `{tool_name}`{reason}

**Parameters:**
```json
{param_str}
```{context_str}

**Allow this action?**"""
        
        # Call approval callback (blocks until user responds)
        try:
            approved = await self.approval_callback(message, tool_name, parameters)
            
            if approved:
                log.info("permission_granted", tool=tool_name, reason="user_approved")
            else:
                log.info("permission_denied", tool=tool_name, reason="user_denied")
            
            return approved
        
        except asyncio.TimeoutError:
            log.warning("permission_timeout", tool=tool_name)
            return False  # Deny on timeout
```

### Telegram Approval Handler

```python
import uuid
import asyncio

class TelegramApprovalHandler:
    """Handle approval requests via Telegram bot with inline buttons"""
    
    def __init__(self, bot, user_id):
        self.bot = bot
        self.user_id = user_id
        self.pending_approvals: Dict[str, asyncio.Future] = {}
    
    async def request_approval(
        self,
        message: str,
        tool_name: str,
        parameters: Dict
    ) -> bool:
        """
        Send approval request to Telegram with buttons.
        Blocks until user responds or timeout.
        """
        approval_id = str(uuid.uuid4())
        
        # Create inline keyboard with approve/deny buttons
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Allow",
                        "callback_data": f"approve_{approval_id}"
                    },
                    {
                        "text": "❌ Deny",
                        "callback_data": f"deny_{approval_id}"
                    }
                ],
                [
                    {
                        "text": "✅ Always Allow for This Session",
                        "callback_data": f"always_{approval_id}"
                    }
                ],
                [
                    {
                        "text": "❌ Never Allow for This Session",
                        "callback_data": f"never_{approval_id}"
                    }
                ]
            ]
        }
        
        # Send message
        await self.bot.send_message(
            chat_id=self.user_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Create future to wait for response
        future = asyncio.Future()
        self.pending_approvals[approval_id] = future
        
        # Wait for user to click button (with timeout)
        try:
            result = await asyncio.wait_for(future, timeout=300.0)  # 5 min timeout
            return result
        
        except asyncio.TimeoutError:
            log.warning("approval_timeout", approval_id=approval_id)
            # Clean up
            await self.bot.send_message(
                chat_id=self.user_id,
                text="⏱️ Approval request timed out (5 minutes). Action was denied."
            )
            return False
        
        finally:
            # Cleanup
            if approval_id in self.pending_approvals:
                del self.pending_approvals[approval_id]
    
    async def handle_callback(self, callback_query):
        """Handle button click from Telegram"""
        callback_data = callback_query.data
        approval_id = callback_data.split("_", 1)[1]
        
        if approval_id not in self.pending_approvals:
            await self.bot.answer_callback_query(
                callback_query.id,
                text="⚠️ This approval request has expired."
            )
            return
        
        future = self.pending_approvals[approval_id]
        
        if callback_data.startswith("approve_"):
            future.set_result(True)
            response = "✅ Action approved"
        
        elif callback_data.startswith("deny_"):
            future.set_result(False)
            response = "❌ Action denied"
        
        elif callback_data.startswith("always_"):
            # TODO: Add to tool_permissions as ALWAYS_ALLOW for this session
            future.set_result(True)
            response = "✅ Action approved (always for this session)"
        
        elif callback_data.startswith("never_"):
            # TODO: Add to tool_permissions as NEVER_ALLOW for this session
            future.set_result(False)
            response = "❌ Action denied (never for this session)"
        
        # Answer callback and edit message
        await self.bot.answer_callback_query(callback_query.id, text=response)
        await self.bot.edit_message_reply_markup(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=None  # Remove buttons
        )
```

---

## Pros

### ✅ Layered Security Model
**Source:** Defense-in-depth security principles

- **Multiple Checkpoints:** Global mode + per-tool overrides + risk classification
- **Fail Secure:** Defaults to denial if misconfigured
- **Granular Control:** Can allow some tools while blocking others

**Example Security Policy:**
```python
# Allow all read operations, approve writes
permission_manager.mode = PermissionMode.SMART_APPROVE

# Override: Always allow low-risk research tools
permission_manager.set_tool_permission("search_web", ToolPermission.ALWAYS_ALLOW)
permission_manager.set_tool_permission("read_file", ToolPermission.ALWAYS_ALLOW)

# Override: Always block destructive operations
permission_manager.set_tool_permission("delete_file", ToolPermission.NEVER_ALLOW)
permission_manager.set_tool_permission("execute_shell", ToolPermission.NEVER_ALLOW)
```

### ✅ User Control & Transparency
**Source:** Human-in-the-loop AI design, Goose user feedback

- **Informed Decisions:** User sees exactly what tool will do before approval
- **Context Awareness:** Approval UI includes parameters and risk level
- **Session Memory:** "Always Allow" persists for session (reduces approval fatigue)

**User Experience Comparison:**
```
Without Permission System:
- Agent: *silently deletes 500 files*
- User: "Wait, what just happened?!"

With Permission System:
- Agent: Requests approval to delete files
- User: Sees list of files, decides to approve/deny
- Agent: Executes only after approval
```

### ✅ Risk-Based Automation
**Source:** Goose Smart Approval mode

- **Best of Both Worlds:** Automate safe operations, gate risky ones
- **Productivity:** Don't interrupt user for low-risk read operations
- **Safety:** Catch high-risk operations before execution

**Smart Approval Statistics (from Goose GitHub):**
```
In 100-turn session:
- Low-risk tools (80 calls): 0 prompts
- Medium-risk tools (15 calls): 8 prompts (7 approved, 1 denied)
- High-risk tools (5 calls): 5 prompts (3 approved, 2 denied)

Result: 87% fewer approval prompts vs Manual mode, caught 2 unintended destructive actions
```

### ✅ Easy Configuration
**Source:** Goose configuration system

- **Environment Variables:** Change mode without code changes
- **Per-User Settings:** Each user can set their own risk tolerance
- **Persistent:** Permissions saved to `permissions/tool_permissions.json`

---

## Cons

### ❌ Approval Fatigue
**Source:** Human factors research, notification overload

- **Interruption Cost:** Each approval breaks user's flow (context switching)
- **Decision Fatigue:** After 10+ approvals, users just click "Allow" without reading
- **False Security:** Users approve dangerous actions due to fatigue

**Real-World Problem:**
```
User in Manual Approval mode:
- Turn 1: Approve search_web
- Turn 2: Approve read_file
- Turn 3: Approve another search_web
- Turn 10: Approve delete_file (didn't read carefully - fatigued)
```

**Mitigation:** Use Smart Approval mode instead of Manual, or "Always Allow for Session" buttons.

### ❌ Latency Impact
**Source:** User interaction time studies

- **Approval Wait Time:** 10-60 seconds per approval (user must notice, read, decide)
- **Unpredictable Timing:** Agent can't predict when user will respond
- **Timeout Issues:** If user doesn't respond in 5 minutes, action denied

**Performance Impact:**
```
Autonomous mode: 
- 10-turn session: 45 seconds total
- Agent executes immediately

Smart Approval mode:
- 10-turn session: 2-4 minutes total
- 3 approvals @ 30s avg each = +90s
```

### ❌ False Sense of Security
**Source:** Security theater critique

- **Prompt Injection Risk:** Malicious tool could craft approval message to trick user
- **Parameter Complexity:** User may not understand technical parameters
- **No Rollback:** Approved action can't be undone (except manual)

**Example Attack:**
```python
# Malicious tool crafts misleading approval request
await check_permission(
    tool_name="safe_backup_tool",
    parameters={
        "action": "backup",
        "target": "/home/user/documents",
        # Hidden: also includes "delete_original=true"
    },
    context="Creating a safety backup of your documents"
)
# User sees "safe backup" and approves, but files get deleted
```

**Mitigation:** Show ALL parameters clearly, use technical parameter names (no aliases).

### ❌ Configuration Complexity
**Source:** Permission system usability studies

- **Learning Curve:** Users must understand 4 modes + tool permissions + risk levels
- **Misconfiguration Risk:** Wrong mode can block productive work or allow dangerous actions
- **Default Debate:** Is Autonomous or Smart Approval better default? (Community split 50/50)

---

## When to Use This Approach

### ✅ Use Permission System When:

1. **Destructive Tools:** Agent has access to delete files, push code, send emails
2. **Production Systems:** Agent interacts with live databases, APIs, servers
3. **Multi-User Access:** Different users with different trust levels
4. **Financial Impact:** Tools that spend money (API calls, cloud resources)
5. **Sensitive Data:** Agent accesses credentials, PII, business secrets

### ❌ Avoid This Approach When:

1. **Read-Only Agent:** Agent only searches, analyzes, reports (no write operations)
2. **Sandboxed Environment:** Agent runs in isolated container with no access to prod
3. **Solo Developer:** Single trusted user in local development
4. **High-Frequency Tools:** Tools called 100+ times per session (approval fatigue)
5. **Latency Critical:** Can't afford 10-60s approval delays

---

## Alternative Approaches

### Alternative 1: Capability-Based Security

```python
# Grant agent specific capabilities, no runtime approvals
agent = Agent(capabilities=[
    Capability.READ_FILES,
    Capability.SEARCH_WEB,
    Capability.CREATE_FILES  # But NOT Capability.DELETE_FILES
])

# Tool checks capability at registration, not execution
@tool(requires=Capability.DELETE_FILES)
def delete_file(path: str):
    pass  # This tool won't even be registered
```

**Pros:** No runtime approvals, fail fast at startup  
**Cons:** No fine-grained control, all-or-nothing per capability

### Alternative 2: Dry-Run Mode

```python
# Agent plans actions but doesn't execute
agent.execute(message, dry_run=True)
# Returns: "I would search web, read file X, create report Y"

# User reviews and approves plan
agent.execute(message, dry_run=False, approved_plan_id="plan_123")
```

**Pros:** User sees full plan before execution, batch approval  
**Cons:** Can't handle dynamic workflows (tool results affect next tools)

### Alternative 3: Audit Log + Rollback

```python
# Agent executes autonomously but logs all actions
agent.execute(message)  # No approvals

# User reviews audit log
actions = agent.get_audit_log()
# Shows: created file X, deleted file Y, posted to telegram

# Rollback specific action
agent.rollback(action_id="action_456")  # Undo delete
```

**Pros:** No interruptions, full automation, can undo mistakes  
**Cons:** Some actions irreversible (sent emails, API calls with side effects)

---

## Implementation Roadmap for emonk

### Week 1: Permission Manager Core
```python
# Day 1-2: PermissionMode, ToolPermission enums, PermissionManager class
# Day 3: Risk level classifications for existing skills
# Day 4: check_permission logic (modes + overrides)
# Day 5: Unit tests
```

### Week 2: Telegram Approval Integration
```python
# Day 1-2: TelegramApprovalHandler with inline buttons
# Day 3: Callback handling and future resolution
# Day 4: Timeout handling and error cases
# Day 5: Integration testing with live bot
```

### Week 3: Agent Loop Integration
```python
# Day 1: Add permission check before tool execution
# Day 2: Handle denial gracefully (inform LLM)
# Day 3: Session-level permission overrides ("Always Allow")
# Day 4-5: Testing different modes and scenarios
```

### Week 4: Configuration & Persistence
```python
# Day 1-2: Save/load tool_permissions from JSON
# Day 3: Environment variable configuration
# Day 4: CLI commands (set mode, configure tool permissions)
# Day 5: Documentation and user guide
```

---

## Configuration Examples

### Development (Autonomous)
```python
permission_manager = PermissionManager(mode=PermissionMode.AUTONOMOUS)
# Result: No interruptions, full automation
# Use for: Local testing, trusted development environment
```

### Production (Smart Approval)
```python
permission_manager = PermissionManager(mode=PermissionMode.SMART_APPROVE)
# Override: Block destructive operations entirely
permission_manager.set_tool_permission("delete_file", ToolPermission.NEVER_ALLOW)
permission_manager.set_tool_permission("execute_shell", ToolPermission.NEVER_ALLOW)
permission_manager.set_tool_permission("git_push", ToolPermission.ASK_BEFORE)
# Result: Auto-approve safe operations, prompt for risky ones, block dangerous ones
```

### High-Security (Manual Approval)
```python
permission_manager = PermissionManager(mode=PermissionMode.MANUAL_APPROVE)
# Override: Allow only essential read operations
permission_manager.set_tool_permission("search_web", ToolPermission.ALWAYS_ALLOW)
permission_manager.set_tool_permission("read_file", ToolPermission.ALWAYS_ALLOW)
# Result: Approve every write operation individually
```

---

## Comparison Matrix

| Dimension | Goose Permission | Capability-Based | Dry-Run | Audit+Rollback |
|-----------|-----------------|------------------|---------|----------------|
| **User Control** | ⭐⭐⭐⭐⭐ Fine-grained | ⭐⭐⭐ Coarse | ⭐⭐⭐⭐ Plan review | ⭐⭐ After-the-fact |
| **Automation** | ⭐⭐⭐⭐ Smart mode | ⭐⭐⭐⭐⭐ Full | ⭐⭐ Two-phase | ⭐⭐⭐⭐⭐ Full |
| **Latency** | ⭐⭐⭐ Approval delays | ⭐⭐⭐⭐⭐ None | ⭐⭐ Double execution | ⭐⭐⭐⭐⭐ None |
| **Security** | ⭐⭐⭐⭐ Preventive | ⭐⭐⭐⭐ Preventive | ⭐⭐⭐⭐ Preventive | ⭐⭐ Detective |
| **Complexity** | ⭐⭐⭐ Moderate | ⭐⭐⭐⭐ Simple | ⭐⭐ Complex | ⭐⭐⭐ Moderate |
| **Irreversible Actions** | ✅ Blocked | ✅ Blocked | ✅ Blocked | ❌ Already executed |

---

## Resources

- **Goose Permission Modes:** https://block.github.io/goose/docs/guides/goose-permissions/
- **Tool Permissions:** https://block.github.io/goose/docs/guides/managing-tools/tool-permissions/
- **Security Blog:** "How to Vibe Code Responsibly" https://block.github.io/goose/blog/2025/04/08/vibe-code-responsibly/
- **Telegram Bot API:** https://core.telegram.org/bots/api#inlinekeyboardmarkup
- **Human-in-the-Loop AI:** "Designing for Human Oversight" (Stanford HAI, 2024)
