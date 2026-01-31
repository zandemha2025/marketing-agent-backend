"""
Customer identity model for identity resolution and linking.

This model maintains an identity graph linking multiple identifiers
(email, phone, device_id, etc.) to a unified customer profile.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, Float, Boolean, DateTime, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class IdentityType(str, Enum):
    """Supported identity types for customer identification."""
    EMAIL = "email"
    PHONE = "phone"
    DEVICE_ID = "device_id"
    BROWSER_ID = "browser_id"
    CRM_ID = "crm_id"
    STRIPE_ID = "stripe_id"
    SHOPIFY_ID = "shopify_id"
    HUBSPOT_ID = "hubspot_id"
    SALESFORCE_ID = "salesforce_id"
    FACEBOOK_ID = "facebook_id"
    GOOGLE_ID = "google_id"
    APPLE_ID = "apple_id"
    LINKEDIN_ID = "linkedin_id"
    CUSTOM = "custom"


class IdentitySource(str, Enum):
    """Source of the identity data."""
    WEB = "web"
    MOBILE = "mobile"
    CRM = "crm"
    PAYMENT = "payment"
    SSO = "sso"
    IMPORT = "import"
    API = "api"
    WEBHOOK = "webhook"


class CustomerIdentity(Base):
    """
    Identity graph model for linking profiles.

    Each record represents a single identity (e.g., email address, phone number)
    linked to a customer profile. Multiple identities can be linked to one customer
    for unified profile management.
    """

    # Customer relationship
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=False)

    # Identity type and value
    identity_type = Column(SQLEnum(IdentityType), nullable=False)
    identity_value = Column(String(500), nullable=False)

    # Identity confidence (0.0 to 1.0)
    # Higher for verified identities (email confirmation, phone verification)
    confidence_score = Column(Float, default=1.0, nullable=False)

    # Source of the identity
    source = Column(SQLEnum(IdentitySource), default=IdentitySource.WEB, nullable=False)

    # Verification status
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)

    # Primary flag (main identity for this type)
    is_primary = Column(Boolean, default=False, nullable=False)

    # Additional data (using 'extra_data' to avoid reserved word conflict)
    extra_data = Column(String(1000), nullable=True)  # JSON string for additional data

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(String(1), default="N", nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="identities")

    # Indexes for identity resolution
    __table_args__ = (
        # Unique constraint on type + value (excluding soft-deleted)
        Index("ix_customer_identities_type_value", "identity_type", "identity_value", unique=True),
        # Index for customer lookups
        Index("ix_customer_identities_customer", "customer_id"),
        # Index for verification status
        Index("ix_customer_identities_verified", "is_verified"),
        # Index for source filtering
        Index("ix_customer_identities_source", "source"),
        # Index for soft delete filtering
        Index("ix_customer_identities_is_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<CustomerIdentity {self.identity_type}={self.identity_value} customer={self.customer_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert identity to dictionary representation."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "identity_type": self.identity_type.value if self.identity_type else None,
            "identity_value": self.identity_value,
            "confidence_score": self.confidence_score,
            "source": self.source.value if self.source else None,
            "is_verified": self.is_verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "is_primary": self.is_primary,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def verify(self):
        """Mark identity as verified."""
        self.is_verified = True
        self.verified_at = datetime.utcnow()
        self.confidence_score = max(self.confidence_score, 0.9)

    def set_primary(self):
        """Mark as primary identity for this type."""
        self.is_primary = True

    def soft_delete(self):
        """Soft delete identity."""
        self.is_deleted = "Y"
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restore soft-deleted identity."""
        self.is_deleted = "N"
        self.deleted_at = None