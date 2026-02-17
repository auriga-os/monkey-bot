"""Configuration and secrets management for monkey-bot framework.

Provides utilities for loading secrets and configuring models:
- load_secrets(): Load from GCP Secret Manager (prod) or .env (dev)
- get_model(): Get configured LangChain model
- get_system_prompt(): Load custom system prompt from file

This module handles environment detection and secret loading for deployments.
"""

import logging
import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


def load_secrets(required_secrets: list[str] | None = None) -> Dict[str, str]:
    """Load secrets from GCP Secret Manager in production, .env in development.

    In production (ENVIRONMENT=production):
        - Loads secrets from GCP Secret Manager
        - Converts secret names to env var format (e.g., x-api-key → X_API_KEY)
        - Sets environment variables automatically
        - Raises RuntimeError if required secrets are missing

    In development (ENVIRONMENT=development or not set):
        - Loads secrets from .env file using python-dotenv
        - No validation of required secrets (for easier local testing)

    Args:
        required_secrets: Optional list of secret names to validate in production.
            Secret names should use kebab-case (e.g., "vertex-ai-project-id").
            If not provided, loads all available secrets without validation.

    Returns:
        Dictionary of secret key-value pairs (env var name → value).
        In development mode, returns empty dict (secrets loaded into os.environ).

    Raises:
        RuntimeError: If required secrets are missing in production
        RuntimeError: If GCP Secret Manager is not available in production

    Environment Variables (inputs):
        ENVIRONMENT: "production" or "development" (default: "development")
        GCP_PROJECT_ID: GCP project ID for Secret Manager (default: "aurigaos")

    Environment Variables (outputs):
        Sets all loaded secrets as environment variables with env var naming.

    Example:
        >>> # Development mode - load from .env
        >>> load_secrets()
        {}  # Secrets loaded into os.environ

        >>> # Production mode - load from GCP Secret Manager
        >>> os.environ["ENVIRONMENT"] = "production"
        >>> load_secrets(required_secrets=["vertex-ai-project-id", "allowed-users"])
        {"VERTEX_AI_PROJECT_ID": "...", "ALLOWED_USERS": "..."}
    """
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        return _load_secrets_from_gcp(required_secrets)
    else:
        return _load_secrets_from_env()


def _load_secrets_from_gcp(required_secrets: list[str] | None = None) -> Dict[str, str]:
    """Load secrets from GCP Secret Manager.

    Args:
        required_secrets: Optional list of secret names to validate

    Returns:
        Dictionary of secret key-value pairs (env var name → value)

    Raises:
        RuntimeError: If Secret Manager client fails or required secrets are missing
    """
    try:
        from google.cloud import secretmanager
    except ImportError:
        raise RuntimeError(
            "google-cloud-secret-manager is required for production. "
            "Install with: pip install google-cloud-secret-manager"
        )

    project_id = os.getenv("GCP_PROJECT_ID", "aurigaos")
    client = secretmanager.SecretManagerServiceClient()

    # If no required secrets specified, just log warning and return empty dict
    if not required_secrets:
        logger.warning(
            "No required_secrets specified for GCP Secret Manager. "
            "Recommend passing required secrets list for validation."
        )
        return {}

    loaded_secrets: Dict[str, str] = {}
    missing_secrets = []

    for secret_name in required_secrets:
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")

            # Convert secret name to env var format (e.g., x-api-key → X_API_KEY)
            env_var_name = secret_name.upper().replace("-", "_")
            loaded_secrets[env_var_name] = secret_value

            # Set as environment variable for backward compatibility
            os.environ[env_var_name] = secret_value

            logger.info(f"✅ Loaded secret: {secret_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load secret {secret_name}: {e}")
            missing_secrets.append(secret_name)

    if missing_secrets:
        raise RuntimeError(
            f"Failed to load required secrets: {', '.join(missing_secrets)}\n"
            f"See docs/deployment.md for setup instructions."
        )

    logger.info(f"✅ Loaded {len(loaded_secrets)} secrets from GCP Secret Manager")
    return loaded_secrets


def _load_secrets_from_env() -> Dict[str, str]:
    """Load secrets from .env file for development.

    Returns:
        Empty dict (secrets loaded directly into os.environ by dotenv)
    """
    load_dotenv()
    logger.info("✅ Loaded secrets from .env file (development mode)")
    return {}


def get_model(
    provider: str | None = None,
    model_name: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """Get configured chat model from environment or explicit parameters.

    Supports any LangChain-compatible model via provider parameter or
    MODEL_PROVIDER env var. Parameters override environment variables.

    Supported providers:
    - google_vertexai: Google Vertex AI (Gemini models)
    - openai: OpenAI (GPT models)
    - anthropic: Anthropic (Claude models)

    Args:
        provider: Model provider override (default: from MODEL_PROVIDER env var)
        model_name: Model name override (default: from MODEL_NAME env var)
        temperature: Temperature override (default: from MODEL_TEMPERATURE env var)
        max_tokens: Max tokens override (default: from MODEL_MAX_TOKENS env var)

    Returns:
        Configured BaseChatModel instance

    Raises:
        ValueError: If unsupported model provider is specified
        ImportError: If required model provider package is not installed

    Environment Variables:
        MODEL_PROVIDER: Provider name (google_vertexai, openai, anthropic)
        MODEL_NAME: Model name/identifier
        MODEL_TEMPERATURE: Temperature for generation (0.0-1.0)
        MODEL_MAX_TOKENS: Maximum output tokens

    Example:
        >>> # Use environment variables
        >>> os.environ["MODEL_PROVIDER"] = "google_vertexai"
        >>> os.environ["MODEL_NAME"] = "gemini-2.5-flash"
        >>> model = get_model()

        >>> # Override with explicit parameters
        >>> model = get_model(
        ...     provider="openai",
        ...     model_name="gpt-4",
        ...     temperature=0.3
        ... )
    """
    # Use parameters if provided, else fall back to env vars with defaults
    provider = provider or os.getenv("MODEL_PROVIDER", "google_vertexai")
    model_name = model_name or os.getenv("MODEL_NAME", "gemini-2.5-flash")
    temperature = temperature if temperature is not None else float(
        os.getenv("MODEL_TEMPERATURE", "0.7")
    )
    max_tokens = max_tokens if max_tokens is not None else int(
        os.getenv("MODEL_MAX_TOKENS", "8192")
    )

    logger.info(
        f"Initializing model: provider={provider}, "
        f"model={model_name}, temp={temperature}, max_tokens={max_tokens}"
    )

    if provider == "google_vertexai":
        try:
            from langchain_google_vertexai import ChatVertexAI
        except ImportError:
            raise ImportError(
                "langchain-google-vertexai is required for google_vertexai provider. "
                "Install with: pip install langchain-google-vertexai"
            )
        return ChatVertexAI(
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    elif provider == "openai":
        try:
            from langchain.chat_models import init_chat_model
        except ImportError:
            raise ImportError(
                "langchain package is required for model initialization. "
                "Install with: pip install langchain"
            )
        return init_chat_model(
            f"openai:{model_name}",
            temperature=temperature,
            max_tokens=max_tokens,
        )

    elif provider == "anthropic":
        try:
            from langchain.chat_models import init_chat_model
        except ImportError:
            raise ImportError(
                "langchain package is required for model initialization. "
                "Install with: pip install langchain"
            )
        return init_chat_model(
            f"anthropic:{model_name}",
            temperature=temperature,
            max_tokens=max_tokens,
        )

    else:
        raise ValueError(
            f"Unsupported model provider: {provider}. "
            f"Supported providers: google_vertexai, openai, anthropic"
        )


def get_system_prompt(prompt_file_path: str | None = None) -> str:
    """Load system prompt from file.

    Args:
        prompt_file_path: Path to system prompt file.
            If not provided, uses SYSTEM_PROMPT_FILE env var.
            If neither provided, returns empty string.

    Returns:
        System prompt string from file, or empty string if file not found

    Environment Variables:
        SYSTEM_PROMPT_FILE: Optional path to system prompt file

    Example:
        >>> # Load from env var
        >>> os.environ["SYSTEM_PROMPT_FILE"] = "/app/prompts/bot-prompt.txt"
        >>> prompt = get_system_prompt()

        >>> # Load from explicit path
        >>> prompt = get_system_prompt("/app/prompts/custom-prompt.txt")
    """
    prompt_file = prompt_file_path or os.getenv("SYSTEM_PROMPT_FILE")

    if not prompt_file:
        logger.debug("No system prompt file specified (SYSTEM_PROMPT_FILE not set)")
        return ""

    prompt_path = Path(prompt_file)
    if not prompt_path.exists():
        logger.warning(f"System prompt file not found: {prompt_file}")
        return ""

    try:
        with open(prompt_path) as f:
            content = f.read()
        logger.info(f"✅ Loaded system prompt from {prompt_file}")
        return content
    except Exception as e:
        logger.error(f"❌ Failed to load system prompt from {prompt_file}: {e}")
        return ""
