"""
Application configuration.
"""
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    app_name: str = "Marketing Agent"
    debug: bool = False
    environment: str = "development"

    # Database (SQLite for local dev, PostgreSQL for production)
    database_url: str = "sqlite:///local"  # Will auto-create data/local.db

    # API Keys
    openrouter_api_key: Optional[str] = None  # Primary LLM access (Claude, GPT-4, Gemini, etc.)
    firecrawl_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    segmind_api_key: Optional[str] = None  # Image generation
    elevenlabs_api_key: Optional[str] = None  # Voice generation

    # Convex (Real-time sync)
    convex_url: str = "https://steady-pig-234.convex.cloud"
    convex_deploy_key: Optional[str] = None  # For authenticated mutations

    # JWT / Auth
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Onboarding
    onboarding_max_pages: int = 50
    onboarding_timeout_seconds: int = 300  # 5 minutes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
