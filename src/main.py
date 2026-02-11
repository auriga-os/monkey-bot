"""
Main application entry point for Emonk.

Wires all components together with real implementations:
- Gateway → Agent Core → Skills Engine → Memory Manager
- LLM Client → Vertex AI (Gemini 2.0 Flash)

Run locally:
    python -m src.main

Run with uvicorn:
    uvicorn src.main:app --reload --port 8080
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env FIRST (before any imports that read env vars)
load_dotenv()

from google.cloud import aiplatform  # noqa: E402
from langchain_google_vertexai import ChatVertexAI  # noqa: E402

from src.core.agent import AgentCore  # noqa: E402
from src.core.llm_client import LLMClient  # noqa: E402
from src.core.memory import MemoryManager  # noqa: E402
from src.core.terminal import TerminalExecutor  # noqa: E402
from src.gateway import server  # noqa: E402
from src.skills.executor import SkillsEngine  # noqa: E402

logger = logging.getLogger(__name__)


def validate_env_vars() -> None:
    """Validate required environment variables.
    
    Raises:
        RuntimeError: If any required env var is missing
    """
    required_vars = [
        "GOOGLE_APPLICATION_CREDENTIALS",
        "VERTEX_AI_PROJECT_ID",
        "ALLOWED_USERS",
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill in your values."
        )
    
    # Validate GOOGLE_APPLICATION_CREDENTIALS file exists
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not Path(creds_path).exists():
        raise RuntimeError(
            f"GOOGLE_APPLICATION_CREDENTIALS file not found: {creds_path}\n"
            f"Download from: https://console.cloud.google.com/iam-admin/serviceaccounts"
        )
    
    logger.info("✅ Environment variables validated")


def create_app():
    """Create FastAPI app with real implementations wired.
    
    Returns:
        FastAPI app ready to run
        
    Raises:
        RuntimeError: If configuration is invalid
    """
    # Validate configuration
    validate_env_vars()
    
    # Initialize Vertex AI (must happen before creating ChatVertexAI)
    project_id = os.getenv("VERTEX_AI_PROJECT_ID")
    location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    
    logger.info(f"Initializing Vertex AI: project={project_id}, location={location}")
    aiplatform.init(project=project_id, location=location)
    
    # Create real Vertex AI LLM client (Gemini 2.0 Flash)
    vertex_llm = ChatVertexAI(
        model_name="gemini-2.0-flash-exp",
        temperature=0.7,
        max_output_tokens=8192,
    )
    llm_client = LLMClient(vertex_llm)
    logger.info("✅ LLM Client created (Gemini 2.0 Flash)")
    
    # Create Terminal Executor
    terminal_executor = TerminalExecutor()
    logger.info("✅ Terminal Executor created")
    
    # Create Skills Engine (depends on Terminal Executor)
    skills_dir = os.getenv("SKILLS_DIR", "./skills")
    skills_engine = SkillsEngine(terminal_executor, skills_dir=skills_dir)
    logger.info(f"✅ Skills Engine created (skills_dir={skills_dir})")
    
    # Create Memory Manager
    memory_dir = os.getenv("MEMORY_DIR", "./data/memory")
    gcs_enabled = os.getenv("GCS_ENABLED", "false").lower() == "true"
    gcs_bucket = os.getenv("GCS_MEMORY_BUCKET") if gcs_enabled else None
    
    memory_manager = MemoryManager(
        memory_dir=memory_dir,
        gcs_enabled=gcs_enabled,
        gcs_bucket=gcs_bucket,
    )
    logger.info(
        f"✅ Memory Manager created (dir={memory_dir}, gcs_enabled={gcs_enabled})"
    )
    
    # Create Agent Core (depends on all above)
    agent_core = AgentCore(llm_client, skills_engine, memory_manager)
    logger.info("✅ Agent Core created")
    
    # Inject Agent Core into Gateway (replace MockAgentCore)
    server.agent_core = agent_core
    logger.info("✅ Agent Core injected into Gateway")
    
    # Return FastAPI app
    return server.app


# Create app instance (for uvicorn to import)
# Only create if not in test environment
if os.getenv("PYTEST_CURRENT_TEST"):
    # In test environment - tests will call create_app() manually
    app = None
else:
    # In production/development - create app immediately
    app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    log_level = os.getenv("LOG_LEVEL", "INFO").lower()
    
    print("=" * 60)
    print("🚀 Starting Emonk Agent")
    print("=" * 60)
    print(f"Port: {port}")
    print(f"Log level: {log_level}")
    print(f"Allowed users: {os.getenv('ALLOWED_USERS', 'NOT SET')}")
    print(f"Vertex AI Project: {os.getenv('VERTEX_AI_PROJECT_ID', 'NOT SET')}")
    print(f"GCS Enabled: {os.getenv('GCS_ENABLED', 'false')}")
    print("=" * 60)
    print()
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        log_level=log_level,
        reload=False,  # Disable reload for production
    )
