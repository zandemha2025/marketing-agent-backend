"""
Application configuration.
"""
import logging
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import model_validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    app_name: str = "Marketing Agent"
    debug: bool = False
    environment: str = "development"

    # Database (SQLite for local dev, PostgreSQL for production)
    database_url: str = "sqlite:///local"  # Will auto-create data/local.db
    database_ssl: bool = True  # Enable SSL for PostgreSQL connections (disable for local dev)

    # API Keys
    openrouter_api_key: Optional[str] = None  # Primary LLM access (Claude, GPT-4, Gemini, etc.)
    openai_api_key: Optional[str] = None  # OpenAI API (Whisper transcription, etc.)
    firecrawl_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    segmind_api_key: Optional[str] = None  # Image generation
    elevenlabs_api_key: Optional[str] = None  # Voice generation
    xai_api_key: Optional[str] = None  # xAI/Grok vision for video analysis

    # AWS / S3 Storage
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    s3_endpoint_url: Optional[str] = None  # For S3-compatible services (MinIO, etc.)
    cdn_domain: Optional[str] = None  # CloudFront or other CDN domain

    # Convex (Real-time sync)
    convex_url: str = "https://steady-pig-234.convex.cloud"
    convex_deploy_key: Optional[str] = None  # For authenticated mutations

    # JWT / Auth
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # CORS - configurable via ALLOWED_ORIGINS env var (comma-separated)
    # In production, set ALLOWED_ORIGINS to specific domains only
    # Default includes localhost for development; wildcards removed for security
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3003",
        "http://localhost:5173",
        "http://localhost:4173",
    ]
    
    # Additional origins from environment (comma-separated, e.g., "https://app.example.com,https://staging.example.com")
    allowed_origins: Optional[str] = None

    # Additional CORS settings
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    cors_allow_headers: list[str] = ["*"]
    cors_expose_headers: list[str] = ["X-Request-ID", "X-Accel-Buffering"]  # Important for SSE
    cors_max_age: int = 600  # 10 minutes preflight cache

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Onboarding
    onboarding_max_pages: int = 50
    onboarding_timeout_seconds: int = 300  # 5 minutes
    
    # Email Templates
    email_placeholder_image_url: str = "https://placehold.co/600x300/e2e8f0/64748b?text=Hero+Image"  # Professional placeholder
    
    # Output Directory for generated content
    output_dir: str = "outputs"  # Base directory for generated emails, landing pages, etc.
    
    # === Enterprise Security & Compliance ===
    
    # SAML SSO Configuration
    saml_certificate: Optional[str] = None  # Path to SAML certificate file
    saml_private_key: Optional[str] = None  # Path to SAML private key file
    saml_strict_mode: bool = True  # Enforce strict SAML validation
    
    # Audit Logging
    audit_log_retention_days: int = 2555  # 7 years for SOC 2 compliance
    audit_log_batch_size: int = 100  # Batch size for async logging
    audit_log_flush_interval: int = 5  # Seconds between flushes
    
    # Compliance Flags
    gdpr_enabled: bool = True  # Enable GDPR compliance features
    ccpa_enabled: bool = True  # Enable CCPA compliance features
    soc2_enabled: bool = True  # Enable SOC 2 compliance features
    
    # Data Encryption
    encryption_key: Optional[str] = None  # Key for encrypting sensitive data
    
    # Application URL (for SAML metadata generation)
    app_url: Optional[str] = None  # e.g., https://app.example.com

    # === CDP Configuration ===
    cdp_enabled: bool = True
    cdp_event_retention_days: int = 365
    cdp_anonymous_retention_days: int = 30
    cdp_batch_size: int = 1000
    cdp_enrichment_enabled: bool = True

    # External enrichment APIs
    clearbit_api_key: Optional[str] = None
    zerobounce_api_key: Optional[str] = None

    # === Enterprise Integrations Configuration ===
    integrations_enabled: bool = True

    # OAuth credentials for CRM integrations
    salesforce_client_id: Optional[str] = None
    salesforce_client_secret: Optional[str] = None
    salesforce_redirect_uri: Optional[str] = None  # e.g., https://app.example.com/api/v1/integrations/salesforce/oauth/callback

    hubspot_client_id: Optional[str] = None
    hubspot_client_secret: Optional[str] = None
    hubspot_redirect_uri: Optional[str] = None  # e.g., https://app.example.com/api/v1/integrations/hubspot/oauth/callback

    # Webhook security
    webhook_secret: Optional[str] = None  # HMAC secret for webhook signature verification

    # Sync settings
    default_sync_batch_size: int = 1000
    max_sync_records_per_run: int = 100000
    default_sync_frequency: str = "hourly"  # Options: hourly, daily, weekly

    @model_validator(mode='after')
    def validate_integration_settings(self):
        """Validate integration settings."""
        # Valid sync frequencies
        valid_frequencies = ["hourly", "daily", "weekly", "monthly", "realtime"]
        if self.default_sync_frequency not in valid_frequencies:
            raise ValueError(f"default_sync_frequency must be one of {valid_frequencies}")
        return self

    # Event streaming
    kafka_enabled: bool = False
    kafka_bootstrap_servers: Optional[str] = None
    kafka_events_topic: str = "customer-events"

    # === Optimization Configuration ===
    optimization_enabled: bool = True
    auto_optimization_enabled: bool = False  # Enable with caution
    optimization_interval_minutes: int = 60
    experiment_min_sample_size: int = 100
    experiment_default_confidence: float = 0.95
    bandit_default_algorithm: str = "thompson_sampling"
    predictive_model_retrain_days: int = 7
    
    # === Additional Integration Configuration ===
    # Microsoft Dynamics OAuth credentials
    dynamics_client_id: Optional[str] = None
    dynamics_client_secret: Optional[str] = None
    
    # Additional sync settings
    sync_timeout_seconds: int = 3600
    
    # Data warehouse settings
    snowflake_account: Optional[str] = None
    snowflake_user: Optional[str] = None
    snowflake_password: Optional[str] = None
    snowflake_database: Optional[str] = None
    snowflake_schema: str = "PUBLIC"
    snowflake_warehouse: Optional[str] = None
    
    # BigQuery settings
    bigquery_project_id: Optional[str] = None
    bigquery_credentials_path: Optional[str] = None
    
    # CDP integration settings
    segment_write_key: Optional[str] = None
    mparticle_api_key: Optional[str] = None
    mparticle_api_secret: Optional[str] = None

    @model_validator(mode='after')
    def validate_production_settings(self) -> 'Settings':
        """Validate critical settings for production environment."""
        # Merge allowed_origins from environment into cors_origins
        if self.allowed_origins:
            additional_origins = [
                origin.strip() 
                for origin in self.allowed_origins.split(",") 
                if origin.strip()
            ]
            # Validate no wildcards in production origins
            for origin in additional_origins:
                if '*' in origin:
                    logger.warning(
                        f"Wildcard CORS origin '{origin}' detected. "
                        "Consider using specific domains for better security."
                    )
            self.cors_origins = list(set(self.cors_origins + additional_origins))
        
        if self.environment in ('production', 'prod', 'staging'):
            # Check for insecure default secret key
            insecure_defaults = [
                'your-secret-key-change-in-production',
                'secret',
                'changeme',
                'your-secret-key',
            ]
            if self.secret_key in insecure_defaults:
                raise ValueError(
                    f"SECURITY ERROR: Insecure SECRET_KEY detected in {self.environment} environment. "
                    "Set a strong, unique SECRET_KEY environment variable. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
            
            # Warn if secret key is too short
            if len(self.secret_key) < 32:
                logger.warning(
                    f"SECRET_KEY is shorter than recommended (32+ chars) in {self.environment}. "
                    "Consider using a longer key for better security."
                )
            
            # Warn if CORS origins include localhost in production
            localhost_origins = [o for o in self.cors_origins if 'localhost' in o]
            if localhost_origins:
                logger.warning(
                    f"Localhost CORS origins detected in {self.environment}: {localhost_origins}. "
                    "Consider removing localhost origins in production."
                )
        
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
