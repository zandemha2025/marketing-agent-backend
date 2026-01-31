"""
Experiment Variant model.

Defines the different variants (A, B, C, etc.) for an experiment,
including traffic allocation and configuration.
"""
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import Column, String, ForeignKey, JSON, Float, Boolean, Text, Integer
from sqlalchemy.orm import relationship

from .base import Base


class ExperimentVariant(Base):
    """
    Experiment variant model.
    
    Represents a single variant in an A/B test or multivariate experiment.
    Each variant has a specific configuration that differs from others.
    """
    
    experiment_id = Column(
        String(12),
        ForeignKey("experiments.id"),
        nullable=False
    )
    
    # Variant identification
    name = Column(String(100), nullable=False)  # e.g., "control", "variant_a", "blue_cta"
    description = Column(Text, nullable=True)
    
    # Traffic allocation for this variant (must sum to 100% across all variants)
    traffic_percentage = Column(Float, nullable=False)  # 0.0 to 100.0
    
    # Variant configuration (what changes in this variant)
    # Examples:
    # {
    #     "creative_id": "asset_123",
    #     "headline": "New Headline Text",
    #     "cta_color": "#FF0000",
    #     "cta_text": "Get Started"
    # }
    configuration = Column(JSON, default=dict, nullable=False)
    
    # Control flag
    is_control = Column(Boolean, default=False, nullable=False)
    
    # Bandit-specific fields
    bandit_successes = Column(Integer, default=0, nullable=False)  # Alpha for Beta distribution
    bandit_failures = Column(Integer, default=0, nullable=False)   # Beta for Beta distribution
    bandit_pulls = Column(Integer, default=0, nullable=False)      # Total selections
    
    # Performance tracking (cached for quick access)
    total_assignments = Column(Integer, default=0, nullable=False)
    total_conversions = Column(Integer, default=0, nullable=False)
    conversion_rate = Column(Float, nullable=True)  # Calculated
    
    # Relationships
    experiment = relationship("Experiment", back_populates="variants")
    assignments = relationship("ExperimentAssignment", back_populates="variant", cascade="all, delete-orphan")
    results = relationship("ExperimentResult", back_populates="variant", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert variant to dictionary."""
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "traffic_percentage": self.traffic_percentage,
            "configuration": self.configuration,
            "is_control": self.is_control,
            "bandit_successes": self.bandit_successes,
            "bandit_failures": self.bandit_failures,
            "bandit_pulls": self.bandit_pulls,
            "total_assignments": self.total_assignments,
            "total_conversions": self.total_conversions,
            "conversion_rate": self.conversion_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def update_conversion_rate(self):
        """Recalculate conversion rate based on assignments and conversions."""
        if self.total_assignments > 0:
            self.conversion_rate = self.total_conversions / self.total_assignments
        else:
            self.conversion_rate = None
    
    def get_bandit_score(self) -> float:
        """
        Calculate bandit score (success rate) for this variant.
        Uses Laplace smoothing to handle zero pulls.
        """
        if self.bandit_pulls == 0:
            return 0.5  # Prior belief
        return self.bandit_successes / self.bandit_pulls
