"""Configuration and secrets management for monkey-bot framework.

Provides utilities for loading secrets and configuring models:
- load_bot_config(): Load bot.yaml config file with defaults
- load_secrets(): Load from GCP Secret Manager (prod) or .env (dev)
- get_model(): Get configured LangChain model
- get_system_prompt(): Load custom system prompt from file

This module handles environment detection and secret loading for deployments.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any

import yaml
from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


# Framework defaults (zero-config local dev)
DEFAULTS = {
    "AGENT_NAME": "monkey-bot",
    "SKILLS_DIR": "./skills",
    "MODEL_PROVIDER": "google_vertexai",
    "MODEL_NAME": "gemini-2.5-flash",
    "MODEL_TEMPERATURE": "0.7",
    "MODEL_MAX_TOKENS": "8192",
    "PORT": "8080",
    "LOG_LEVEL": "INFO",
    "ENVIRONMENT": "development",
    "MEMORY_DIR": "./data/memory",
    "MEMORY_BACKEND": "local",
    "GCS_ENABLED": "false",
    "SCHEDULER_STORAGE": "json",
    "SCHEDULER_TIMEZONE": "America/New_York",
    "SECRETS_PROVIDER": "env",
    "GOOGLE_CHAT_FORMAT": "workspace_addon",
}


# Mapping from YAML paths to environment variable names
CONFIG_MAPPING = {
    # Agent
    "agent.name": "AGENT_NAME",
    "agent.skills_dir": "SKILLS_DIR",
    # Model
    "model.provider": "MODEL_PROVIDER",
    "model.name": "MODEL_NAME",
    "model.temperature": "MODEL_TEMPERATURE",
    "model.max_tokens": "MODEL_MAX_TOKENS",
    # Server
    "server.port": "PORT",
    "server.log_level": "LOG_LEVEL",
    # Gateway
    "gateway.allowed_users": "ALLOWED_USERS",
    "gateway.chat_format": "GOOGLE_CHAT_FORMAT",
    # Memory
    "memory.dir": "MEMORY_DIR",
    "memory.backend": "MEMORY_BACKEND",
    "memory.bucket": "GCS_MEMORY_BUCKET",
    # Scheduler
    "scheduler.storage": "SCHEDULER_STORAGE",
    "scheduler.cadence": "SCHEDULER_CADENCE",
    "scheduler.timezone": "SCHEDULER_TIMEZONE",
    # Secrets
    "secrets.provider": "SECRETS_PROVIDER",
    # GCP-specific
    "gcp.project_id": "GCP_PROJECT_ID",
    "gcp.location": "VERTEX_AI_LOCATION",
    # AWS-specific (future)
    "aws.region": "AWS_REGION",
    "aws.account_id": "AWS_ACCOUNT_ID",
    # Azure-specific (future)
    "azure.subscription_id": "AZURE_SUBSCRIPTION_ID",
    "azure.resource_group": "AZURE_RESOURCE_GROUP",
}


class ConfigError(Exception):
    """Configuration error with actionable message."""
    pass


def _flatten_yaml_to_env(yaml_dict: Dict[str, Any]) -> Dict[str, str]:
    """Flatten nested YAML dict to flat env var dict using CONFIG_MAPPING.
    
    Args:
        yaml_dict: Nested dict from YAML parsing
        
    Returns:
        Flat dict with env var names as keys and string values
        
    Example:
        >>> yaml_dict = {"agent": {"name": "test"}, "gateway": {"allowed_users": ["a@b.com"]}}
        >>> _flatten_yaml_to_env(yaml_dict)
        {"AGENT_NAME": "test", "ALLOWED_USERS": "a@b.com"}
    """
    result = {}
    
    # Walk through CONFIG_MAPPING to extract values from nested yaml_dict
    for yaml_path, env_var in CONFIG_MAPPING.items():
        # Split path into parts (e.g., "agent.name" -> ["agent", "name"])
        parts = yaml_path.split(".")
        
        # Navigate nested dict
        value = yaml_dict
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = None
                break
        
        if value is not None:
            # Handle list values (join with commas)
            if isinstance(value, list):
                result[env_var] = ",".join(str(v) for v in value)
            else:
                # Convert all values to strings
                result[env_var] = str(value)
    
    return result


def _validate_provider_config(config: Dict[str, str]) -> None:
    """Validate cloud provider configuration and give actionable errors.
    
    Args:
        config: Flat env var dict from load_bot_config
        
    Raises:
        ConfigError: If unsupported provider is specified or required config is missing
    """
    # Supported providers for each backend type
    SUPPORTED_MEMORY_BACKENDS = {"local", "gcs"}
    SUPPORTED_SCHEDULER_STORAGE = {"json", "firestore"}
    SUPPORTED_SECRETS_PROVIDERS = {"env", "gcp_secret_manager"}
    SUPPORTED_MODEL_PROVIDERS = {"google_vertexai", "openai", "anthropic"}
    
    # Validate memory backend
    memory_backend = config.get("MEMORY_BACKEND", "local")
    if memory_backend not in SUPPORTED_MEMORY_BACKENDS:
        supported = ", ".join(SUPPORTED_MEMORY_BACKENDS)
        if memory_backend == "s3":
            raise ConfigError(
                f"memory.backend is set to 's3' but AWS S3 is not yet supported.\n\n"
                f"To add AWS S3 support, the following are needed:\n"
                f"  - Implement S3Store (subclass BaseStore) in emonk/core/store.py\n"
                f"  - Add aws.region and aws.account_id to bot.yaml\n"
                f"  - pip install boto3\n\n"
                f"Currently supported backends: {supported}"
            )
        elif memory_backend == "azure_blob":
            raise ConfigError(
                f"memory.backend is set to 'azure_blob' but Azure Blob Storage is not yet supported.\n\n"
                f"To add Azure Blob support, the following are needed:\n"
                f"  - Implement AzureBlobStore (subclass BaseStore) in emonk/core/store.py\n"
                f"  - Add azure.subscription_id and azure.resource_group to bot.yaml\n"
                f"  - pip install azure-storage-blob\n\n"
                f"Currently supported backends: {supported}"
            )
        else:
            raise ConfigError(
                f"memory.backend is set to '{memory_backend}' which is not supported.\n"
                f"Currently supported backends: {supported}"
            )
    
    # Validate scheduler storage
    scheduler_storage = config.get("SCHEDULER_STORAGE", "json")
    if scheduler_storage not in SUPPORTED_SCHEDULER_STORAGE:
        supported = ", ".join(SUPPORTED_SCHEDULER_STORAGE)
        if scheduler_storage == "dynamodb":
            raise ConfigError(
                f"scheduler.storage is set to 'dynamodb' but AWS DynamoDB is not yet supported.\n\n"
                f"To add DynamoDB support, the following are needed:\n"
                f"  - Implement DynamoDBStorage (subclass JobStorage) in emonk/core/scheduler/storage.py\n"
                f"  - Add aws.region and aws.account_id to bot.yaml\n"
                f"  - pip install boto3\n\n"
                f"Currently supported storage: {supported}"
            )
        elif scheduler_storage == "cosmosdb":
            raise ConfigError(
                f"scheduler.storage is set to 'cosmosdb' but Azure CosmosDB is not yet supported.\n\n"
                f"To add CosmosDB support, the following are needed:\n"
                f"  - Implement CosmosDBStorage (subclass JobStorage) in emonk/core/scheduler/storage.py\n"
                f"  - Add azure.subscription_id and azure.resource_group to bot.yaml\n"
                f"  - pip install azure-cosmos\n\n"
                f"Currently supported storage: {supported}"
            )
        else:
            raise ConfigError(
                f"scheduler.storage is set to '{scheduler_storage}' which is not supported.\n"
                f"Currently supported storage: {supported}"
            )
    
    # Validate secrets provider
    secrets_provider = config.get("SECRETS_PROVIDER", "env")
    if secrets_provider not in SUPPORTED_SECRETS_PROVIDERS:
        supported = ", ".join(SUPPORTED_SECRETS_PROVIDERS)
        if secrets_provider == "aws_secrets_manager":
            raise ConfigError(
                f"secrets.provider is set to 'aws_secrets_manager' but AWS Secrets Manager is not yet supported.\n\n"
                f"To add AWS Secrets Manager support, the following are needed:\n"
                f"  - Implement _load_secrets_from_aws() in emonk/core/config.py\n"
                f"  - Add aws.region and aws.account_id to bot.yaml\n"
                f"  - pip install boto3\n\n"
                f"Currently supported providers: {supported}"
            )
        elif secrets_provider == "azure_key_vault":
            raise ConfigError(
                f"secrets.provider is set to 'azure_key_vault' but Azure Key Vault is not yet supported.\n\n"
                f"To add Azure Key Vault support, the following are needed:\n"
                f"  - Implement _load_secrets_from_azure() in emonk/core/config.py\n"
                f"  - Add azure.subscription_id and azure.resource_group to bot.yaml\n"
                f"  - pip install azure-keyvault-secrets azure-identity\n\n"
                f"Currently supported providers: {supported}"
            )
        else:
            raise ConfigError(
                f"secrets.provider is set to '{secrets_provider}' which is not supported.\n"
                f"Currently supported providers: {supported}"
            )
    
    # Validate model provider
    model_provider = config.get("MODEL_PROVIDER", "google_vertexai")
    if model_provider not in SUPPORTED_MODEL_PROVIDERS:
        supported = ", ".join(SUPPORTED_MODEL_PROVIDERS)
        if model_provider == "aws_bedrock":
            raise ConfigError(
                f"model.provider is set to 'aws_bedrock' but AWS Bedrock is not yet supported.\n\n"
                f"To add AWS Bedrock support, the following are needed:\n"
                f"  - Add aws_bedrock case to get_model() in emonk/core/config.py\n"
                f"  - Add aws.region to bot.yaml\n"
                f"  - pip install langchain-aws\n\n"
                f"Currently supported providers: {supported}"
            )
        elif model_provider == "azure_openai":
            raise ConfigError(
                f"model.provider is set to 'azure_openai' but Azure OpenAI is not yet supported.\n\n"
                f"To add Azure OpenAI support, the following are needed:\n"
                f"  - Add azure_openai case to get_model() in emonk/core/config.py\n"
                f"  - Add azure.subscription_id to bot.yaml\n"
                f"  - pip install langchain-openai\n\n"
                f"Currently supported providers: {supported}"
            )
        else:
            raise ConfigError(
                f"model.provider is set to '{model_provider}' which is not supported.\n"
                f"Currently supported providers: {supported}"
            )
    
    # Validate GCP-specific dependencies
    if memory_backend == "gcs" and not config.get("GCP_PROJECT_ID"):
        raise ConfigError(
            "memory.backend is set to 'gcs' but gcp.project_id is not configured.\n"
            "Add 'gcp.project_id: your-project-id' to bot.yaml"
        )
    
    if scheduler_storage == "firestore" and not config.get("GCP_PROJECT_ID"):
        raise ConfigError(
            "scheduler.storage is set to 'firestore' but gcp.project_id is not configured.\n"
            "Add 'gcp.project_id: your-project-id' to bot.yaml"
        )
    
    if secrets_provider == "gcp_secret_manager" and not config.get("GCP_PROJECT_ID"):
        raise ConfigError(
            "secrets.provider is set to 'gcp_secret_manager' but gcp.project_id is not configured.\n"
            "Add 'gcp.project_id: your-project-id' to bot.yaml"
        )


# Track if config has been loaded to avoid duplicate work
_config_loaded = False


def load_bot_config(config_path: str | None = None) -> Dict[str, str]:
    """Load bot configuration from bot.yaml file with framework defaults.
    
    This is the main entry point for loading bot configuration. It:
    1. Applies framework DEFAULTS for any env var not already set
    2. Looks for bot.yaml in current directory (or explicit path)
    3. Parses YAML and flattens to env var format
    4. Derives computed values (e.g., GCS_ENABLED from memory.backend)
    5. Sets values as os.environ (only if not already set)
    6. Validates provider configuration
    7. Returns the loaded config dict
    
    Loading priority: framework DEFAULTS < bot.yaml < .env < secrets provider
    
    This function can be called multiple times safely - it will only load once.
    
    Args:
        config_path: Optional explicit path to bot.yaml file.
            If not provided, looks for bot.yaml in current directory.
            
    Returns:
        Dictionary of loaded config values (env var name -> value)
        
    Raises:
        ConfigError: If configuration validation fails
        
    Example:
        >>> # Load from default location (./bot.yaml)
        >>> config = load_bot_config()
        
        >>> # Load from explicit path
        >>> config = load_bot_config("/path/to/bot.yaml")
    """
    global _config_loaded
    
    # If already loaded, just return current env state
    if _config_loaded and not config_path:  # Allow explicit path to override
        return {k: os.environ.get(k, v) for k, v in DEFAULTS.items()}
    
    # Step 1: Apply framework defaults (only if not already set)
    for key, default_value in DEFAULTS.items():
        if key not in os.environ:
            os.environ[key] = default_value
            logger.debug(f"Applied default: {key}={default_value}")
    
    # Step 2: Look for bot.yaml
    if config_path:
        yaml_path = Path(config_path)
    else:
        yaml_path = Path("bot.yaml")
    
    if not yaml_path.exists():
        logger.info(f"No bot.yaml found at {yaml_path.absolute()}, using defaults and env vars only")
        # Mark as loaded even without yaml file
        _config_loaded = True
        # Return current env state (defaults already applied)
        return {k: os.environ.get(k, v) for k, v in DEFAULTS.items()}
    
    # Step 3: Parse YAML
    try:
        with open(yaml_path) as f:
            yaml_dict = yaml.safe_load(f)
        
        if not yaml_dict:
            logger.warning(f"bot.yaml at {yaml_path} is empty, using defaults only")
            return {k: os.environ.get(k, v) for k, v in DEFAULTS.items()}
        
        logger.info(f"Loaded bot.yaml from {yaml_path.absolute()}")
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse bot.yaml: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read bot.yaml: {e}")
    
    # Step 4: Flatten YAML to env var format
    config = _flatten_yaml_to_env(yaml_dict)
    
    # Step 5: Derive computed values
    # GCS_ENABLED is derived from memory.backend for backward compatibility
    if config.get("MEMORY_BACKEND") == "gcs":
        config["GCS_ENABLED"] = "true"
    
    # VERTEX_AI_PROJECT_ID can be set from gcp.project_id for backward compatibility
    if "GCP_PROJECT_ID" in config and "VERTEX_AI_PROJECT_ID" not in config:
        config["VERTEX_AI_PROJECT_ID"] = config["GCP_PROJECT_ID"]
    
    # Step 6: Set as environment variables (only if not already set)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value
            logger.debug(f"Set from bot.yaml: {key}={value}")
    
    # Step 7: Validate provider configuration
    # Use current environment state (includes defaults + yaml + any existing env vars)
    current_config = {k: os.environ.get(k, "") for k in config.keys()}
    _validate_provider_config(current_config)
    
    # Mark as loaded
    _config_loaded = True
    
    logger.info(f"✅ Bot config loaded from {yaml_path.absolute()}")
    return config


def load_secrets(required_secrets: list[str] | None = None) -> Dict[str, str]:
    """Load secrets using configured secrets provider.
    
    This function first loads bot.yaml config (which sets defaults and SECRETS_PROVIDER),
    then dispatches to the appropriate secrets backend based on configuration.

    Secrets providers:
        - env: Load from .env file using python-dotenv (development)
        - gcp_secret_manager: Load from GCP Secret Manager (production)
        - aws_secrets_manager: AWS Secrets Manager (future)
        - azure_key_vault: Azure Key Vault (future)

    The provider is determined by:
    1. bot.yaml `secrets.provider` field (if present)
    2. SECRETS_PROVIDER env var (if set)
    3. ENVIRONMENT env var: "production" -> gcp_secret_manager, else -> env (legacy)

    Args:
        required_secrets: Optional list of secret names to validate in production.
            Secret names should use kebab-case (e.g., "vertex-ai-project-id").
            If not provided, loads all available secrets without validation.

    Returns:
        Dictionary of secret key-value pairs (env var name → value).
        In development mode (env provider), returns empty dict (secrets loaded into os.environ).

    Raises:
        RuntimeError: If required secrets are missing in production
        RuntimeError: If secrets provider is not available
        ConfigError: If secrets provider is not supported

    Environment Variables (inputs):
        SECRETS_PROVIDER: Provider to use (env, gcp_secret_manager, etc.)
        ENVIRONMENT: "production" or "development" (legacy, for backward compat)
        GCP_PROJECT_ID: GCP project ID for Secret Manager (if using gcp_secret_manager)

    Environment Variables (outputs):
        Sets all loaded secrets as environment variables with env var naming.

    Example:
        >>> # Development mode - load from .env
        >>> load_secrets()
        {}  # Secrets loaded into os.environ

        >>> # Production mode with GCP - load from Secret Manager
        >>> os.environ["SECRETS_PROVIDER"] = "gcp_secret_manager"
        >>> load_secrets(required_secrets=["vertex-ai-project-id", "allowed-users"])
        {"VERTEX_AI_PROJECT_ID": "...", "ALLOWED_USERS": "..."}
    """
    # Load bot config first (sets SECRETS_PROVIDER and other config)
    load_bot_config()
    
    # Determine secrets provider
    # Priority: SECRETS_PROVIDER env var > ENVIRONMENT env var (legacy)
    secrets_provider = os.getenv("SECRETS_PROVIDER", "")
    
    # Legacy support: ENVIRONMENT=production -> gcp_secret_manager
    if not secrets_provider:
        environment = os.getenv("ENVIRONMENT", "development")
        if environment == "production":
            secrets_provider = "gcp_secret_manager"
            logger.info("Using gcp_secret_manager (inferred from ENVIRONMENT=production)")
        else:
            secrets_provider = "env"
    
    # Dispatch to appropriate secrets backend
    if secrets_provider == "env":
        return _load_secrets_from_env()
    elif secrets_provider == "gcp_secret_manager":
        return _load_secrets_from_gcp(required_secrets)
    else:
        # This should have been caught by _validate_provider_config, but check again
        raise ConfigError(
            f"Unsupported secrets provider: {secrets_provider}\n"
            f"Currently supported: env, gcp_secret_manager"
        )


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
