"""
User and Organization models for multi-tenancy.
"""
from enum import Enum
from typing import Optional, List

from datetime import datetime, timedelta
from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON, Boolean, DateTime, Text, Integer
from sqlalchemy.orm import relationship

from .base import Base


class UserRole(str, Enum):
    """User roles within an organization."""
    ADMIN = "admin"       # Full access, can manage users
    EDITOR = "editor"     # Can create/edit campaigns and assets
    VIEWER = "viewer"     # Read-only access


class SubscriptionTier(str, Enum):
    """Organization subscription tiers."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Organization(Base):
    """
    Organization (tenant) model.

    Each organization has its own:
    - Knowledge base
    - Campaigns
    - Assets
    - Users
    """

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)  # URL-friendly identifier
    domain = Column(String(255), unique=True, nullable=True)  # Primary domain (optional)
    logo_url = Column(String(500), nullable=True)

    # Subscription
    subscription_tier = Column(
        SQLEnum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False
    )

    # Settings stored as JSON for flexibility
    settings = Column(JSON, default=dict, nullable=False)
    # Example settings:
    # {
    #     "brand_guidelines_url": "...",
    #     "default_channels": ["twitter", "linkedin"],
    #     "approval_required": true,
    #     "notifications": {...}
    # }

    # Relationships
    users = relationship("User", back_populates="organization")
    knowledge_base = relationship(
        "KnowledgeBase",
        back_populates="organization",
        uselist=False  # One-to-one
    )
    campaigns = relationship("Campaign", back_populates="organization")
    image_edit_sessions = relationship("ImageEditSession", back_populates="organization")
    customers = relationship("Customer", back_populates="organization", foreign_keys="Customer.organization_id")
    customer_segments = relationship("CustomerSegment", back_populates="organization")
    experiments = relationship("Experiment", back_populates="organization")
    predictive_models = relationship("PredictiveModel", back_populates="organization")

    def __repr__(self):
        return f"<Organization {self.name} ({self.domain})>"


class IdentityProvider(str, Enum):
    """Supported identity providers for SSO."""
    LOCAL = "local"  # Email/password authentication
    OKTA = "okta"
    AUTH0 = "auth0"
    AZURE_AD = "azure_ad"
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    """
    User model.

    Users belong to an organization and have roles.
    Supports both local (email/password) and SSO (SAML/OAuth) authentication.
    """

    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500), nullable=True)

    # Password hash (for email/password auth)
    password_hash = Column(String(255), nullable=True)

    # Organization membership
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.EDITOR, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    
    # === SSO/SAML Fields ===
    
    # Identity provider
    identity_provider = Column(
        SQLEnum(IdentityProvider),
        default=IdentityProvider.LOCAL,
        nullable=False
    )
    
    # SAML-specific fields
    saml_subject_id = Column(String(255), nullable=True, index=True)
    """SAML NameID/Subject ID from the Identity Provider."""
    
    saml_metadata_xml = Column(Text, nullable=True)
    """SAML metadata XML from the IdP (stored encrypted in production)."""
    
    # SSO tracking
    last_sso_login = Column(DateTime, nullable=True)
    """Timestamp of last successful SSO login."""
    
    sso_session_index = Column(String(255), nullable=True)
    """SAML session index for logout tracking."""
    
    # MFA fields
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    """Whether MFA is enabled for this user."""
    
    mfa_verified_at = Column(DateTime, nullable=True)
    """When MFA was last verified."""
    
    mfa_secret = Column(String(255), nullable=True)
    """Encrypted MFA secret (TOTP)."""
    
    # Backup codes for MFA recovery
    mfa_backup_codes = Column(JSON, nullable=True)
    """Hashed backup codes for MFA recovery."""
    
    # OAuth fields (for non-SAML providers)
    oauth_provider_id = Column(String(255), nullable=True)
    """User ID from OAuth provider (Google, GitHub, etc.)."""
    
    oauth_access_token = Column(Text, nullable=True)
    """Encrypted OAuth access token."""
    
    oauth_refresh_token = Column(Text, nullable=True)
    """Encrypted OAuth refresh token."""
    
    oauth_token_expires_at = Column(DateTime, nullable=True)
    """When the OAuth token expires."""
    
    # Security tracking
    last_password_change = Column(DateTime, nullable=True)
    """When password was last changed."""
    
    password_reset_token = Column(String(255), nullable=True)
    """Temporary password reset token hash."""
    
    password_reset_expires = Column(DateTime, nullable=True)
    """When password reset token expires."""
    
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    """Count of consecutive failed login attempts."""
    
    locked_until = Column(DateTime, nullable=True)
    """Account lockout expiration."""
    
    last_login_ip = Column(String(45), nullable=True)
    """IP address of last successful login."""
    
    last_login_at = Column(DateTime, nullable=True)
    """Timestamp of last successful login."""

    # Preferences
    preferences = Column(JSON, default=dict, nullable=False)
    # Example preferences:
    # {
    #     "theme": "dark",
    #     "notifications_email": true,
    #     "notifications_in_app": true,
    # }

    # Relationships
    organization = relationship("Organization", back_populates="users")
    created_campaigns = relationship(
        "Campaign",
        back_populates="created_by_user",
        foreign_keys="Campaign.created_by"
    )
    created_assets = relationship(
        "Asset",
        back_populates="created_by_user",
        foreign_keys="Asset.created_by"
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    consents = relationship("Consent", back_populates="user")
    data_subject_requests = relationship(
        "DataSubjectRequest", 
        back_populates="user",
        foreign_keys="DataSubjectRequest.user_id"
    )

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"

    def has_permission(self, action: str) -> bool:
        """Check if user has permission for an action."""
        permissions = {
            UserRole.ADMIN: [
                "manage_users", "manage_org", "create_campaign",
                "edit_campaign", "delete_campaign", "create_asset",
                "edit_asset", "delete_asset", "approve_asset", "view"
            ],
            UserRole.EDITOR: [
                "create_campaign", "edit_campaign", "create_asset",
                "edit_asset", "approve_asset", "view"
            ],
            UserRole.VIEWER: ["view"],
        }
        return action in permissions.get(self.role, [])
    
    def is_sso_user(self) -> bool:
        """Check if user authenticates via SSO."""
        return self.identity_provider != IdentityProvider.LOCAL
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def record_failed_login(self):
        """Record a failed login attempt."""
        self.failed_login_attempts += 1
        # Lock account after 5 failed attempts for 30 minutes
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def record_successful_login(self, ip_address: str = None):
        """Record a successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip_address
    
    def requires_mfa(self) -> bool:
        """Check if MFA is required for this user."""
        # MFA required for SSO users if enabled at org level
        # or if user has explicitly enabled MFA
        return self.mfa_enabled
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert user to dictionary."""
        data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "organization_id": self.organization_id,
            "role": self.role.value,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "identity_provider": self.identity_provider.value,
            "mfa_enabled": self.mfa_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_sso_login": self.last_sso_login.isoformat() if self.last_sso_login else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
        
        if include_sensitive:
            data.update({
                "saml_subject_id": self.saml_subject_id,
                "failed_login_attempts": self.failed_login_attempts,
                "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            })
        
        return data
