"""
Segment membership junction table for customer segmentation.

Links customers to segments with membership history tracking.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class SegmentMembership(Base):
    """
    Segment membership junction table.

    Tracks which customers belong to which segments,
    including when they joined and left.
    """

    # Relationships
    segment_id = Column(String(12), ForeignKey("customer_segments.id"), nullable=False)
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=False)

    # Membership timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    left_at = Column(DateTime, nullable=True)  # Null = currently a member

    # Reason for joining/leaving (for analytics)
    joined_reason = Column(String(50), nullable=True)  # e.g., "criteria_match", "manual_add"
    left_reason = Column(String(50), nullable=True)  # e.g., "criteria_no_longer_match", "manual_remove"

    # Computed at time of joining (snapshot of why they matched)
    matching_criteria_snapshot = Column(String(2000), nullable=True)  # JSON string

    # Relationships
    segment = relationship("CustomerSegment", back_populates="memberships")
    customer = relationship("Customer", back_populates="segment_memberships")

    # Indexes for efficient queries
    __table_args__ = (
        # Unique constraint on active memberships
        Index("ix_segment_memberships_segment_customer", "segment_id", "customer_id", unique=True),
        # Index for customer segment lookups
        Index("ix_segment_memberships_customer", "customer_id"),
        # Index for active memberships
        Index("ix_segment_memberships_active", "segment_id", "left_at"),
        # Index for membership history
        Index("ix_segment_memberships_joined", "segment_id", "joined_at"),
    )

    def __repr__(self):
        status = "active" if self.is_active() else "left"
        return f"<SegmentMembership segment={self.segment_id} customer={self.customer_id} {status}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert membership to dictionary representation."""
        return {
            "id": self.id,
            "segment_id": self.segment_id,
            "customer_id": self.customer_id,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "left_at": self.left_at.isoformat() if self.left_at else None,
            "joined_reason": self.joined_reason,
            "left_reason": self.left_reason,
            "matching_criteria_snapshot": self.matching_criteria_snapshot,
            "is_active": self.is_active(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_active(self) -> bool:
        """Check if membership is currently active."""
        return self.left_at is None

    def leave(self, reason: str = "criteria_no_longer_match"):
        """Mark membership as ended."""
        self.left_at = datetime.utcnow()
        self.left_reason = reason

    def rejoin(self, reason: str = "criteria_match"):
        """Reactivate membership (if previously left)."""
        self.left_at = None
        self.left_reason = None
        self.joined_at = datetime.utcnow()
        self.joined_reason = reason

    @property
    def membership_duration_days(self) -> Optional[float]:
        """Calculate membership duration in days."""
        end_time = self.left_at or datetime.utcnow()
        if self.joined_at:
            delta = end_time - self.joined_at
            return delta.total_seconds() / 86400
        return None