"""
Integration configuration model for enterprise integrations.

This model manages connections to external systems including CRMs,
data warehouses, and CDPs. It stores authentication configuration,
sync settings, and operational status.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, Text, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class IntegrationType(str, Enum):
    """Types of integrations supported."""
    CRM = "crm"
    DATA_WAREHOUSE = "data_warehouse"
    CDP = "cdp"
    EMAIL = "email"
    ADS = "ads"
    ANALYTICS = "analytics"
    CUSTOM = "custom"


class IntegrationProvider(str, Enum):
    """Supported integration providers."""
    # CRM
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    DYNAMICS = "dynamics"
    PIPEDRIVE = "pipedrive"
    ZOHO = "zoho"
    
    # Data Warehouse
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    DATABRICKS = "databricks"
    REDSHIFT = "redshift"
    
    # CDP
    SEGMENT = "segment"
    MPARTICLE = "mparticle"
    TEALIUM = "tealium"
    
    # Email
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    MAILCHIMP = "mailchimp"
    
    # Ads
    GOOGLE_ADS = "google_ads"
    FACEBOOK_ADS = "facebook_ads"
    LINKEDIN_ADS = "linkedin_ads"
    
    # Analytics
    GOOGLE_ANALYTICS = "google_analytics"
    MIXPANEL = "mixpanel"
    AMPLITUDE = "amplitude"


class IntegrationStatus(str, Enum):
    """Integration operational status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"
    PENDING = "pending"
    AUTH_REQUIRED = "auth_required"


class Integration(Base):
    """
    Integration configuration model.
    
    Manages connections to external enterprise systems with:
    - OAuth and API key authentication
    - Configurable sync schedules and rules
    - Status tracking and error handling
    - Organization-scoped access
    """
    
    # Organization scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    
    # Integration identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Integration type and provider
    integration_type = Column(
        SQLEnum(IntegrationType),
        nullable=False,
        index=True
    )
    provider = Column(
        SQLEnum(IntegrationProvider),
        nullable=False,
        index=True
    )
    
    # Operational status
    status = Column(
        SQLEnum(IntegrationStatus),
        default=IntegrationStatus.PENDING,
        nullable=False
    )
    
    # Authentication configuration (encrypted at rest)
    # Stores OAuth tokens, API keys, connection strings
    # Example: {
    #     "access_token": "encrypted_token",
    #     "refresh_token": "encrypted_refresh",
    #     "expires_at": "2024-01-30T18:00:00Z",
    #     "instance_url": "https://instance.salesforce.com"
    # }
    auth_config = Column(JSON, default=dict, nullable=False)
    
    # Sync configuration
    # Example: {
    #     "sync_mode": "bidirectional",  # inbound, outbound, bidirectional
    #     "sync_frequency": "hourly",    # realtime, hourly, daily, weekly
    #     "sync_schedule": "0 * * * *",  # Cron expression
    #     "entities": ["contacts", "leads", "opportunities"],
    #     "filters": {"created_after": "2024-01-01"},
    #     "batch_size": 1000,
    #     "conflict_resolution": "timestamp_wins"  # cdp_wins, source_wins, merge
    # }
    sync_config = Column(JSON, default=dict, nullable=False)
    
    # Webhook configuration
    # Example: {
    #     "webhook_url": "https://api.example.com/webhooks/salesforce",
    #     "webhook_secret": "encrypted_secret",
    #     "events": ["contact.created", "contact.updated"]
    # }
    webhook_config = Column(JSON, default=dict, nullable=False)
    
    # Sync tracking
    last_sync_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(50), nullable=True)
    last_sync_records = Column(JSON, default=dict, nullable=False)
    
    # Error tracking
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)
    error_count = Column(JSON, default=dict, nullable=False)
    
    # Connection metadata
    connected_at = Column(DateTime, nullable=True)
    connected_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    
    # Provider-specific metadata
    # Example: {
    #     "salesforce_org_id": "00D...",
    #     "hubspot_portal_id": "12345",
    #     "api_version": "v58.0"
    # }
    provider_metadata = Column(JSON, default=dict, nullable=False)
    
    # Rate limiting
    rate_limit_remaining = Column(JSON, default=dict, nullable=False)
    rate_limit_reset_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    user = relationship("User", foreign_keys=[connected_by])
    sync_logs = relationship("IntegrationSyncLog", back_populates="integration", cascade="all, delete-orphan")
    mappings = relationship("IntegrationMapping", back_populates="integration", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_integration_org_type', 'organization_id', 'integration_type'),
        Index('idx_integration_org_provider', 'organization_id', 'provider'),
        Index('idx_integration_status', 'status'),
    )
    
    def is_active(self) -> bool:
        """Check if integration is active and ready for operations."""
        return self.status == IntegrationStatus.ACTIVE
    
    def is_syncing(self) -> bool:
        """Check if integration is currently syncing."""
        return self.status == IntegrationStatus.SYNCING
    
    def get_auth_token(self) -> Optional[str]:
        """Get decrypted access token from auth config."""
        return self.auth_config.get("access_token")
    
    def get_sync_entities(self) -> List[str]:
        """Get list of entities configured for sync."""
        return self.sync_config.get("entities", [])
    
    def get_sync_frequency(self) -> str:
        """Get configured sync frequency."""
        return self.sync_config.get("sync_frequency", "hourly")
    
    def update_last_sync(self, status: str, records: Dict[str, int]) -> None:
        """Update last sync timestamp and status."""
        self.last_sync_at = datetime.utcnow()
        self.last_sync_status = status
        self.last_sync_records = records
    
    def record_error(self, error_message: str) -> None:
        """Record an integration error."""
        self.last_error_at = datetime.utcnow()
        self.last_error_message = error_message
        self.status = IntegrationStatus.ERROR
        
        # Update error count
        provider = self.provider.value if self.provider else "unknown"
        self.error_count[provider] = self.error_count.get(provider, 0) + 1
    
    def clear_error(self) -> None:
        """Clear error state and mark as active."""
        self.last_error_message = None
        self.status = IntegrationStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive auth data)."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "integration_type": self.integration_type.value if self.integration_type else None,
            "provider": self.provider.value if self.provider else None,
            "status": self.status.value if self.status else None,
            "sync_config": self.sync_config,
            "webhook_config": {k: v for k, v in self.webhook_config.items() if k != "webhook_secret"},
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "last_sync_records": self.last_sync_records,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "last_error_message": self.last_error_message,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "connected_by": self.connected_by,
            "provider_metadata": self.provider_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
