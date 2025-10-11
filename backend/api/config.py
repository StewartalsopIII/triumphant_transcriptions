import os
from typing import Optional

# Port for local development
PORT = int(os.getenv("PORT", "8000"))

# CORS origins - allow all for development, restrict in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Environment check
ENV = os.getenv("ENV", "development")

def get_env_var(key: str, required: bool = True) -> Optional[str]:
    """Helper to get environment variables with validation"""
    value = os.getenv(key)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value
