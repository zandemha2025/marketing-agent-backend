"""
Customer segment model for audience segmentation.

Defines dynamic and static segments for targeted marketing,
personalization, and analytics.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, Integer, Boolean, DateTime, Index, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class SegmentType(str, Enum):
    """Type of customer segment."""
    DYNAMIC = "dynamic"  # Auto-updates based on criteria
    STATIC = "static"    # Manual membership
    BEHAVIORAL = "behavioral"  # Based on event patterns
    PREDICTIVE = "predictive"  # ML-based predictions


class SegmentStatus(str, Enum):
    """Status of the segment."""
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    COMPUTING = "computing"  # Currently being recalculated


class CustomerSegment(Base):
    """
    Customer segment model.

    Segments group customers based on criteria for targeted
campaigns, personalization, and analytics.
    """

    # Organization scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)

    # Segment details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Segment type
    segment_type = Column(SQLEnum(SegmentType), default=SegmentType.DYNAMIC, nullable=False)
    status = Column(SQLEnum(SegmentStatus), default=SegmentStatus.ACTIVE, nullable=False)

    # Segment criteria (JSON filter conditions)
    # Example for dynamic segment:
    # {
    #     "conditions": [
    #         {"field": "traits.plan", "operator": "eq", "value": "premium"},
    #         {"field": "engagement_score", "operator": "gt", "value": 50}
    #     ],
    #     "operator": "and"
    # }
    criteria = Column(JSON, default=dict, nullable=False)

    # Event-based criteria (for behavioral segments)
    # Example:
    # {
    #     "event_name": "purchase",
    #     "count": {"min": 3, "max": null},
    #     "time_window_days": 30
    # }
    event_criteria = Column(JSON, nullable=True)

    # Statistics
    customer_count = Column(Integer, default=0, nullable=False)
    computed_at = Column(DateTime, nullable=True)

    # Auto-refresh settings (for dynamic segments)
    is_dynamic = Column(Boolean, default=True, nullable=False)
    refresh_interval_minutes = Column(Integer, default=60, nullable=False)  # 0 = manual only
    last_refreshed_at = Column(DateTime, nullable=True)
    next_refresh_at = Column(DateTime, nullable=True)

    # Metadata
    tags = Column(JSON, default=list, nullable=False)
    color = Column(String(7), nullable=True)  # Hex color for UI

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(String(1), default="N", nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="customer_segments")
    memberships = relationship("SegmentMembership", back_populates="segment", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_customer_segments_org", "organization_id"),
        Index("ix_customer_segments_org_type", "organization_id", "segment_type"),
        Index("ix_customer_segments_org_status", "organization_id", "status"),
        Index("ix_customer_segments_dynamic", "is_dynamic"),
        Index("ix_customer_segments_next_refresh", "next_refresh_at"),
        Index("ix_customer_segments_is_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<CustomerSegment {self.name} ({self.customer_count} members) org={self.organization_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert segment to dictionary representation."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "segment_type": self.segment_type.value if self.segment_type else None,
            "status": self.status.value if self.status else None,
            "criteria": self.criteria,
            "event_criteria": self.event_criteria,
            "customer_count": self.customer_count,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
            "is_dynamic": self.is_dynamic,
            "refresh_interval_minutes": self.refresh_interval_minutes,
            "last_refreshed_at": self.last_refreshed_at.isoformat() if self.last_refreshed_at else None,
            "next_refresh_at": self.next_refresh_at.isoformat() if self.next_refresh_at else None,
            "tags": self.tags,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def mark_computing(self):
        """Mark segment as currently computing."""
        self.status = SegmentStatus.COMPUTING

    def mark_computed(self, count: int):
        """Mark segment as computed with new count."""
        self.status = SegmentStatus.ACTIVE
        self.customer_count = count
        self.computed_at = datetime.utcnow()
        self.last_refreshed_at = datetime.utcnow()

        # Schedule next refresh
        if self.is_dynamic and self.refresh_interval_minutes > 0:
            from datetime import timedelta
            self.next_refresh_at = datetime.utcnow() + timedelta(minutes=self.refresh_interval_minutes)

    def should_refresh(self) -> bool:
        """Check if segment should be refreshed."""
        if not self.is_dynamic:
            return False
        if self.refresh_interval_minutes <= 0:
            return False
        if not self.next_refresh_at:
            return True
        return datetime.utcnow() >= self.next_refresh_at

    def soft_delete(self):
        """Soft delete segment."""
        self.is_deleted = "Y"
        self.deleted_at = datetime.utcnow()
        self.status = SegmentStatus.ARCHIVED

    def restore(self):
        """Restore soft-deleted segment."""
        self.is_deleted = "N"
        self.deleted_at = None
        self.status = SegmentStatus.ACTIVE

    def add_tag(self, tag: str):
        """Add a tag to the segment."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str):
        """Remove a tag from the segment."""
        if tag in self.tags:
            self.tags.remove(tag)