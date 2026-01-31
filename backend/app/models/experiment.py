"""
A/B Test Experiment model.

Defines experiments for testing different campaign variations,
hypotheses, and measuring statistical significance.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON, Integer, DateTime, Float, Text, Boolean
from sqlalchemy.orm import relationship

from .base import Base


class ExperimentType(str, Enum):
    """Types of experiments."""
    AB_TEST = "ab_test"           # Simple A/B test
    MULTIVARIATE = "multivariate"  # Multiple variables tested
    BANDIT = "bandit"             # Multi-armed bandit


class ExperimentStatus(str, Enum):
    """Experiment lifecycle status."""
    DRAFT = "draft"               # Being configured
    RUNNING = "running"           # Active and collecting data
    PAUSED = "paused"             # Temporarily stopped
    COMPLETED = "completed"       # Finished with winner selected
    ARCHIVED = "archived"         # Historical record


class Experiment(Base):
    """
    A/B test experiment model.
    
    Represents a controlled experiment to test hypotheses about
    campaign performance, creative effectiveness, or audience response.
    """
    
    organization_id = Column(
        String(12),
        ForeignKey("organizations.id"),
        nullable=False
    )
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Experiment configuration
    experiment_type = Column(SQLEnum(ExperimentType), default=ExperimentType.AB_TEST, nullable=False)
    status = Column(SQLEnum(ExperimentStatus), default=ExperimentStatus.DRAFT, nullable=False)
    
    # Hypothesis and metrics
    hypothesis = Column(Text, nullable=True)  # What we're testing
    primary_metric = Column(String(100), nullable=False)  # e.g., "conversion_rate", "ctr", "revenue"
    secondary_metrics = Column(JSON, default=list, nullable=False)  # List of additional metrics
    
    # Traffic allocation
    traffic_allocation = Column(Float, default=1.0, nullable=False)  # % of total traffic (0.0 to 1.0)
    
    # Timeline
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Sample size requirements
    min_sample_size = Column(Integer, default=100, nullable=False)
    target_sample_size = Column(Integer, nullable=True)  # Calculated based on MDE
    
    # Statistical parameters
    confidence_level = Column(Float, default=0.95, nullable=False)  # e.g., 0.95 for 95%
    statistical_power = Column(Float, default=0.8, nullable=False)  # Usually 0.8 (80%)
    minimum_detectable_effect = Column(Float, default=0.05, nullable=False)  # Minimum lift to detect
    
    # Campaign association (optional)
    campaign_id = Column(
        String(12),
        ForeignKey("campaigns.id"),
        nullable=True
    )
    
    # Winner
    winner_variant_id = Column(String(12), nullable=True)
    winner_declared_at = Column(DateTime, nullable=True)
    winner_reason = Column(Text, nullable=True)  # Why this variant won
    
    # Auto-optimization settings
    auto_winner_selection = Column(Boolean, default=False, nullable=False)
    auto_winner_min_confidence = Column(Float, default=0.95, nullable=False)
    auto_winner_min_lift = Column(Float, default=0.05, nullable=False)
    
    # Metadata
    created_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    stopped_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    stopped_reason = Column(Text, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="experiments")
    campaign = relationship("Campaign", back_populates="experiments")
    variants = relationship("ExperimentVariant", back_populates="experiment", cascade="all, delete-orphan")
    assignments = relationship("ExperimentAssignment", back_populates="experiment", cascade="all, delete-orphan")
    results = relationship("ExperimentResult", back_populates="experiment", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert experiment to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "experiment_type": self.experiment_type.value,
            "status": self.status.value,
            "hypothesis": self.hypothesis,
            "primary_metric": self.primary_metric,
            "secondary_metrics": self.secondary_metrics,
            "traffic_allocation": self.traffic_allocation,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "min_sample_size": self.min_sample_size,
            "target_sample_size": self.target_sample_size,
            "confidence_level": self.confidence_level,
            "statistical_power": self.statistical_power,
            "minimum_detectable_effect": self.minimum_detectable_effect,
            "campaign_id": self.campaign_id,
            "winner_variant_id": self.winner_variant_id,
            "winner_declared_at": self.winner_declared_at.isoformat() if self.winner_declared_at else None,
            "winner_reason": self.winner_reason,
            "auto_winner_selection": self.auto_winner_selection,
            "auto_winner_min_confidence": self.auto_winner_min_confidence,
            "auto_winner_min_lift": self.auto_winner_min_lift,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
