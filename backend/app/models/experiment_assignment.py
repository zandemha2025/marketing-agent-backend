"""
Experiment Assignment model.

Tracks which users are assigned to which experiment variants,
ensuring consistent user experience across sessions.
"""
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from .base import Base


class ExperimentAssignment(Base):
    """
    Experiment assignment model.
    
    Records the assignment of a user (or anonymous visitor) to a specific
    experiment variant. Uses consistent hashing to ensure users always see
    the same variant across sessions.
    """
    
    __tablename__ = "experiment_assignments"
    
    experiment_id = Column(
        String(12),
        ForeignKey("experiments.id"),
        nullable=False
    )
    
    variant_id = Column(
        String(12),
        ForeignKey("experiment_variants.id"),
        nullable=False
    )
    
    # User identification (either user_id or anonymous_id)
    user_id = Column(String(12), ForeignKey("users.id"), nullable=True)
    anonymous_id = Column(String(64), nullable=True)  # For non-logged-in users
    
    # Assignment timestamp
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Context at time of assignment (for analysis)
    # {
    #     "device": "mobile",
    #     "browser": "chrome",
    #     "os": "ios",
    #     "country": "US",
    #     "referrer": "google",
    #     "utm_source": "newsletter"
    # }
    context = Column(JSON, default=dict, nullable=False)
    
    # First exposure tracking
    first_exposed_at = Column(DateTime, nullable=True)
    
    # Conversion tracking
    converted_at = Column(DateTime, nullable=True)
    conversion_value = Column(JSON, nullable=True)  # Store conversion details
    
    # Relationships
    experiment = relationship("Experiment", back_populates="assignments")
    variant = relationship("ExperimentVariant", back_populates="assignments")
    
    # Unique constraints
    __table_args__ = (
        # Ensure a user is only assigned once per experiment
        UniqueConstraint('experiment_id', 'user_id', name='uq_experiment_user'),
        UniqueConstraint('experiment_id', 'anonymous_id', name='uq_experiment_anonymous'),
        # Indexes for performance
        Index('idx_assignment_experiment', 'experiment_id'),
        Index('idx_assignment_variant', 'variant_id'),
        Index('idx_assignment_user', 'user_id'),
        Index('idx_assignment_anonymous', 'anonymous_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert assignment to dictionary."""
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "user_id": self.user_id,
            "anonymous_id": self.anonymous_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "context": self.context,
            "first_exposed_at": self.first_exposed_at.isoformat() if self.first_exposed_at else None,
            "converted_at": self.converted_at.isoformat() if self.converted_at else None,
            "conversion_value": self.conversion_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def mark_converted(self, conversion_value: Optional[Dict] = None):
        """Mark this assignment as converted."""
        self.converted_at = datetime.utcnow()
        if conversion_value:
            self.conversion_value = conversion_value
