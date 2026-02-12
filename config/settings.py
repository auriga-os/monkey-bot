"""
Configuration and secrets management for Auriga Marketing Bot.

Loads secrets from:
- GCP Secret Manager (production)
- .env file (development)
"""

import logging
import os
from typing import Dict

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_secrets() -> Dict[str, str]:
    """Load secrets from GCP Secret Manager in production, .env in development.

    Returns:
        Dictionary of secret key-value pairs

    Raises:
        RuntimeError: If required secrets are missing in production
    """
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        return _load_secrets_from_gcp()
    else:
        return _load_secrets_from_env()


def _load_secrets_from_gcp() -> Dict[str, str]:
    """Load secrets from GCP Secret Manager.

    Returns:
        Dictionary of secret key-value pairs

    Raises:
        RuntimeError: If Secret Manager client fails or secrets are missing
    """
    try:
        from google.cloud import secretmanager
    except ImportError:
        raise RuntimeError(
            "google-cloud-secret-manager is required for production. "
            "Install with: pip install google-cloud-secret-manager"
        )

    project_id = os.getenv("GCP_PROJECT_ID", "auriga-prod")
    client = secretmanager.SecretManagerServiceClient()

    # List of all required secrets
    secret_names = [
        "google-chat-webhook",
        "x-api-key",
        "x-api-secret",
        "x-access-token",
        "x-access-token-secret",
        "instagram-user-id",
        "instagram-access-token",
        "tiktok-access-token",
        "linkedin-access-token",
        "linkedin-person-urn",
        "reddit-access-token",
        "perplexity-api-key",
        "firecrawl-api-key",
        "vertex-ai-project-id",
        "allowed-users",
    ]

    loaded_secrets: Dict[str, str] = {}
    missing_secrets = []

    for secret_name in secret_names:
        try:
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")

            # Convert secret name to env var format (e.g., x-api-key → X_API_KEY)
            env_var_name = secret_name.upper().replace("-", "_")
            loaded_secrets[env_var_name] = secret_value

            logger.info(f"✅ Loaded secret: {secret_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load secret {secret_name}: {e}")
            missing_secrets.append(secret_name)

    if missing_secrets:
        raise RuntimeError(
            f"Failed to load required secrets: {', '.join(missing_secrets)}\n"
            f"See SECRETS.md for setup instructions."
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


# Load secrets on module import
SECRETS = load_secrets()
