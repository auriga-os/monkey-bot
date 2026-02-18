"""Deep agent factory for monkey-bot.

Provides build_deep_agent() — the primary public API for constructing
agents with monkey-bot's opinionated defaults on top of LangChain Deep Agents.
"""

import logging
from collections.abc import Callable, Sequence
from pathlib import Path

import yaml
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.base import BaseStore

from .prompt import compose_system_prompt
from .store import create_search_memory_tool

logger = logging.getLogger(__name__)

# Try to import deep agents
try:
    from deepagents import create_deep_agent
    from deepagents.backends.protocol import BackendProtocol, SandboxBackendProtocol
    from deepagents.middleware.subagents import SubAgentMiddleware

    _DEEPAGENTS_AVAILABLE = True
except ImportError:
    _DEEPAGENTS_AVAILABLE = False
    BackendProtocol = object
    SandboxBackendProtocol = object


def build_deep_agent(
    model: str | BaseChatModel,
    *,
    tools: Sequence[BaseTool | Callable] | None = None,
    system_prompt: str = "",
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    backend: object | None = None,
    store: BaseStore | None = None,
    scheduler: object | None = None,
    subagents: list[dict] | None = None,
    checkpointer: object | None = None,
    summarization_trigger: tuple[str, float] = ("fraction", 0.85),
    summarization_keep: tuple[str, float] = ("fraction", 0.10),
):
    """Build a deep agent with monkey-bot's opinionated defaults.

    This is the primary public API for constructing agents with monkey-bot's
    opinionated defaults on top of LangChain Deep Agents. It handles:
    - 3-layer system prompt composition (internal + base + user)
    - Skills manifest generation from SKILL.md files
    - Auto-adding scheduler and memory tools
    - Middleware configuration (summarization, subagents)
    - Backend setup

    Args:
        model: LLM model name (e.g., "gemini-2.5-flash") or BaseChatModel instance
        tools: Optional list of LangChain tools or callables
        system_prompt: User's custom system prompt (Layer 3)
        skills: List of skill directory paths to load (e.g., ["./skills/", "/shared/skills/"])
        memory: List of memory directory paths (e.g., ["/memory/"])
        backend: Backend protocol implementation (BackendProtocol or SandboxBackendProtocol)
        store: LangGraph Store for long-term memory (enables search_memory tool)
        scheduler: Scheduler instance (enables schedule_task tool)
        subagents: List of subagent configs for SubAgentMiddleware
        checkpointer: LangGraph checkpointer for conversation persistence (defaults to InMemorySaver)
        summarization_trigger: When to trigger summarization (type, value)
        summarization_keep: How much context to keep after summarization (type, value)

    Returns:
        Compiled deep agent (LangGraph graph)

    Raises:
        ImportError: If deepagents package is not installed
        ValueError: If required dependencies are missing for enabled features

    Example:
        >>> from langchain_google_vertexai import ChatVertexAI
        >>> from langgraph.store.memory import InMemoryStore
        >>>
        >>> model = ChatVertexAI(model_name="gemini-2.5-flash")
        >>> store = InMemoryStore()
        >>>
        >>> agent = build_deep_agent(
        ...     model=model,
        ...     tools=[my_custom_tool],
        ...     system_prompt="You are a helpful marketing assistant.",
        ...     skills=["./skills/"],
        ...     store=store,
        ...     scheduler=my_scheduler,
        ... )
        >>>
        >>> # Invoke the agent
        >>> result = await agent.ainvoke(
        ...     {"messages": [{"role": "user", "content": "Hello"}]},
        ...     config={"configurable": {"thread_id": "thread-123"}}
        ... )
    """
    if not _DEEPAGENTS_AVAILABLE:
        raise ImportError(
            "deepagents package required: pip install deepagents\n"
            "See: https://github.com/langchain-ai/deepagents"
        )

    # Step 1: Collect all tools
    all_tools = list(tools) if tools else []

    # Auto-add schedule_task if scheduler provided
    if scheduler is not None:
        schedule_tool = _create_schedule_task_tool(scheduler)
        all_tools.append(schedule_tool)
        logger.info("Auto-added schedule_task tool")

    # Auto-add search_memory if store provided
    if store is not None:
        memory_tool = create_search_memory_tool(store)
        all_tools.append(memory_tool)
        logger.info("Auto-added search_memory tool")

    # Step 2: Generate skills manifest
    skills_manifest = ""
    if skills:
        skills_manifest = _generate_skills_manifest(skills)
        logger.info(f"Generated skills manifest from {len(skills)} directories")

    # Step 3: Compose 3-layer system prompt
    full_system_prompt = compose_system_prompt(
        skills_manifest=skills_manifest,
        user_system_prompt=system_prompt,
        has_scheduler=scheduler is not None,
        has_memory=store is not None,
        has_backend=backend is not None,
    )

    logger.info(
        "Composed system prompt",
        extra={
            "component": "deepagent",
            "has_scheduler": scheduler is not None,
            "has_memory": store is not None,
            "has_backend": backend is not None,
            "num_skills": len(skills) if skills else 0,
        }
    )

    # Step 4: Configure middleware
    middleware = []

    # Note: SummarizationMiddleware is added by default by create_deep_agent,
    # so we don't need to add it manually. The summarization_trigger and
    # summarization_keep parameters are not currently configurable via
    # create_deep_agent API, so we accept them but don't use them for now.

    # Add subagent middleware if subagents provided
    if subagents:
        subagent_mw = SubAgentMiddleware(subagents=subagents)
        middleware.append(subagent_mw)
        logger.info(f"Added SubAgentMiddleware with {len(subagents)} subagents")

    # TODO: Support persistent checkpointers for multi-instance deployments:
    #   - Firestore: custom BaseCheckpointSaver (best fit for GCP/Cloud Run)
    #   - Postgres: AsyncPostgresSaver from langgraph-checkpoint-postgres
    #   - Redis: RedisSaver from langgraph-checkpoint-redis
    if checkpointer is None:
        checkpointer = InMemorySaver()
        logger.info("Using InMemorySaver for conversation persistence (in-memory only)")

    # Step 5: Call create_deep_agent with all params
    agent = create_deep_agent(
        model=model,
        tools=all_tools,
        system_prompt=full_system_prompt,
        middleware=middleware,
        backend=backend,
        store=store,
        checkpointer=checkpointer,
    )

    logger.info(
        "Deep agent created",
        extra={
            "component": "deepagent",
            "num_tools": len(all_tools),
            "num_middleware": len(middleware),
        }
    )

    return agent


def _generate_skills_manifest(skills_dirs: list[str]) -> str:
    """Generate skills manifest by reading SKILL.md frontmatter.

    Walks each skills directory, finds SKILL.md files, parses YAML frontmatter,
    and extracts name and description to build a formatted manifest.

    Args:
        skills_dirs: List of directory paths to scan for skills

    Returns:
        Formatted skills manifest string (one skill per line)

    Example:
        >>> manifest = _generate_skills_manifest(["./skills/"])
        >>> print(manifest)
        - file-ops: File operations (read, write, list)
        - search-web: Search the web for information
    """
    skills = []

    for skills_dir in skills_dirs:
        dir_path = Path(skills_dir)

        if not dir_path.exists():
            logger.warning(f"Skills directory not found: {skills_dir}")
            continue

        if not dir_path.is_dir():
            logger.warning(f"Skills path is not a directory: {skills_dir}")
            continue

        # Walk the directory
        for skill_path in dir_path.iterdir():
            if not skill_path.is_dir():
                continue

            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                logger.debug(f"Skipping {skill_path.name} - no SKILL.md found")
                continue

            # Parse SKILL.md frontmatter
            metadata = _parse_skill_frontmatter(skill_md)
            if not metadata:
                continue

            name = metadata.get("name")
            description = metadata.get("description", "")

            if not name:
                logger.warning(f"Skill {skill_path.name} missing 'name' in frontmatter")
                continue

            skills.append(f"- {name}: {description}")
            logger.debug(f"Loaded skill: {name}")

    if not skills:
        return "No skills available."

    return "\n".join(skills)


def _parse_skill_frontmatter(skill_md_path: Path) -> dict | None:
    """Parse YAML frontmatter from SKILL.md file.

    SKILL.md format:
        ---
        name: skill-name
        description: "Description"
        ---

        # Skill Documentation
        ...

    Args:
        skill_md_path: Path to SKILL.md file

    Returns:
        Parsed metadata dict or None if parsing fails
    """
    try:
        with open(skill_md_path) as f:
            content = f.read()

        # Extract YAML frontmatter between --- delimiters
        if not content.startswith("---"):
            logger.error(f"SKILL.md missing frontmatter: {skill_md_path}")
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            logger.error(f"SKILL.md malformed frontmatter: {skill_md_path}")
            return None

        frontmatter = parts[1].strip()
        metadata = yaml.safe_load(frontmatter)

        return metadata

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML in {skill_md_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing {skill_md_path}: {e}")
        return None


def _create_schedule_task_tool(scheduler) -> BaseTool:
    """Create schedule_task tool for the scheduler.

    This tool allows the agent to schedule background jobs using cron expressions.

    Args:
        scheduler: CronScheduler instance

    Returns:
        LangChain tool function
    """
    from datetime import datetime, timezone

    from langchain_core.tools import tool

    @tool
    async def schedule_task(
        job_type: str,
        schedule_at_iso: str,
        payload: dict,
    ) -> str:
        """Schedule a background task to run at a specific time.

        Use this to schedule jobs for future execution (e.g., posting content,
        sending reminders, running reports).

        Args:
            job_type: Type of job (e.g., "post_content", "send_reminder")
            schedule_at_iso: When to run the job (ISO 8601 datetime string)
            payload: Job-specific data (dict)

        Returns:
            Success message with job ID

        Example:
            >>> # Schedule a post for tomorrow at 9am
            >>> await schedule_task(
            ...     job_type="post_content",
            ...     schedule_at_iso="2024-02-14T09:00:00Z",
            ...     payload={"platform": "x", "content": "Hello world"}
            ... )
        """
        try:
            schedule_at = datetime.fromisoformat(schedule_at_iso.replace("Z", "+00:00"))
            # Ensure timezone-aware datetime
            if schedule_at.tzinfo is None:
                schedule_at = schedule_at.replace(tzinfo=timezone.utc)
                logger.warning(
                    f"Received timezone-naive datetime '{schedule_at_iso}', "
                    f"assuming UTC: {schedule_at.isoformat()}"
                )
        except ValueError as e:
            return f"Error: Invalid ISO 8601 datetime format: {e}"

        job_id = await scheduler.schedule_job(
            job_type=job_type,
            schedule_at=schedule_at,
            payload=payload,
        )

        return f"Task scheduled successfully. Job ID: {job_id}"

    return schedule_task
