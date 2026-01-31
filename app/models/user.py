"""
User and Organization models for multi-tenancy.
"""
from enum import Enum
from typing import Optional, List

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON, Boolean
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

    def __repr__(self):
        return f"<Organization {self.name} ({self.domain})>"


class User(Base):
    """
    User model.

    Users belong to an organization and have roles.
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
