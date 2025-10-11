import os
from typing import Optional

# Port for local development
PORT = int(os.getenv("PORT", "8000"))

# CORS origins - allow all for development, restrict in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Environment check
ENV = os.getenv("ENV", "development")

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash-exp")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")


def get_env_var(key: str, required: bool = True) -> Optional[str]:
    """Helper to get environment variables with validation"""
    value = os.getenv(key)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {key}")
    return value
