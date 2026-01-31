"""
Unified customer profile model for the Customer Data Platform (CDP).

This model provides a 360-degree view of customers with identity resolution,
trait storage, and engagement metrics.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import Column, String, ForeignKey, JSON, Float, DateTime, Text, Index
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class Customer(Base):
    """
    Unified customer profile model.

    Stores comprehensive customer data including:
    - Identity information (external IDs, anonymous tracking)
    - Traits (demographic, firmographic, behavioral)
    - Computed metrics (engagement score, LTV, churn risk)
    - Merge history for identity resolution
    """

    # Organization/workspace scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    workspace_id = Column(String(12), ForeignKey("organizations.id"), nullable=True)

    # External identity mapping
    # Example: {"email": "user@example.com", "crm_id": "12345", "stripe_id": "cus_abc"}
    external_ids = Column(JSON, default=dict, nullable=False)

    # Anonymous tracking ID (for pre-identification tracking)
    anonymous_id = Column(String(64), nullable=True, index=True)

    # Core traits (demographic, firmographic data)
    # Example: {"first_name": "John", "company": "Acme Inc", "industry": "Technology"}
    traits = Column(JSON, default=dict, nullable=False)

    # Computed traits (calculated values)
    # Example: {"days_since_signup": 30, "total_orders": 5}
    computed_traits = Column(JSON, default=dict, nullable=False)

    # Engagement metrics
    engagement_score = Column(Float, default=0.0, nullable=False)
    lifetime_value = Column(Float, default=0.0, nullable=False)
    churn_risk = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0

    # RFM metrics (Recency, Frequency, Monetary)
    recency_days = Column(Float, nullable=True)  # Days since last activity
    frequency_score = Column(Float, nullable=True)  # Activity frequency score
    monetary_value = Column(Float, nullable=True)  # Total monetary value

    # Timestamps
    first_seen_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)

    # Merge history (array of merged profile IDs)
    merged_from = Column(JSON, default=list, nullable=False)

    # GDPR/privacy
    consent_status = Column(JSON, default=dict, nullable=False)
    # Example: {"email_marketing": true, "analytics": true, "advertising": false}

    # Soft delete for GDPR right to erasure
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(String(1), default="N", nullable=False)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id], back_populates="customers")
    identities = relationship("CustomerIdentity", back_populates="customer", cascade="all, delete-orphan")
    events = relationship("CustomerEvent", back_populates="customer", cascade="all, delete-orphan")
    segment_memberships = relationship("SegmentMembership", back_populates="customer", cascade="all, delete-orphan")
    conversions = relationship("ConversionEvent", back_populates="customer", cascade="all, delete-orphan")
    touchpoints = relationship("AttributionTouchpoint", back_populates="customer", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index("ix_customers_org_external_ids", "organization_id", "external_ids"),
        Index("ix_customers_org_anonymous", "organization_id", "anonymous_id"),
        Index("ix_customers_org_engagement", "organization_id", "engagement_score"),
        Index("ix_customers_org_ltv", "organization_id", "lifetime_value"),
        Index("ix_customers_org_last_seen", "organization_id", "last_seen_at"),
        Index("ix_customers_is_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<Customer {self.id} org={self.organization_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert customer to dictionary representation."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "external_ids": self.external_ids,
            "anonymous_id": self.anonymous_id,
            "traits": self.traits,
            "computed_traits": self.computed_traits,
            "engagement_score": self.engagement_score,
            "lifetime_value": self.lifetime_value,
            "churn_risk": self.churn_risk,
            "recency_days": self.recency_days,
            "frequency_score": self.frequency_score,
            "monetary_value": self.monetary_value,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "merged_from": self.merged_from,
            "consent_status": self.consent_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_primary_email(self) -> Optional[str]:
        """Get primary email from external_ids or traits."""
        if self.external_ids and "email" in self.external_ids:
            return self.external_ids["email"]
        if self.traits and "email" in self.traits:
            return self.traits["email"]
        return None

    def get_primary_phone(self) -> Optional[str]:
        """Get primary phone from external_ids or traits."""
        if self.external_ids and "phone" in self.external_ids:
            return self.external_ids["phone"]
        if self.traits and "phone" in self.traits:
            return self.traits["phone"]
        return None

    def update_last_seen(self, timestamp: Optional[datetime] = None):
        """Update last seen timestamp."""
        self.last_seen_at = timestamp or datetime.utcnow()
        if not self.first_seen_at:
            self.first_seen_at = self.last_seen_at

    def merge_profile(self, other_customer_id: str):
        """Record a merged profile ID."""
        if other_customer_id not in self.merged_from:
            self.merged_from.append(other_customer_id)

    def soft_delete(self):
        """Soft delete customer for GDPR compliance."""
        self.is_deleted = "Y"
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restore soft-deleted customer."""
        self.is_deleted = "N"
        self.deleted_at = None