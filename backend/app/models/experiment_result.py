"""
Experiment Result model.

Stores statistical results and metrics for experiment variants,
including significance testing and confidence intervals.
"""
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import Column, String, ForeignKey, JSON, Float, Integer, DateTime, Text, Boolean, Index
from sqlalchemy.orm import relationship

from .base import Base


class ExperimentResult(Base):
    """
    Experiment result model.
    
    Stores calculated metrics and statistical significance for each
    variant in an experiment. Updated periodically as data is collected.
    """
    
    __tablename__ = "experiment_results"
    
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
    
    # Metric being measured
    metric_name = Column(String(100), nullable=False)  # e.g., "conversion_rate", "revenue", "ctr"
    
    # Sample statistics
    sample_size = Column(Integer, nullable=False)
    conversions = Column(Integer, default=0, nullable=False)  # For binary metrics
    
    # Metric value
    metric_value = Column(Float, nullable=False)  # e.g., 0.15 for 15% conversion rate
    metric_sum = Column(Float, nullable=True)  # For continuous metrics (total value)
    metric_sum_squares = Column(Float, nullable=True)  # For variance calculation
    
    # Comparison to control
    lift_percentage = Column(Float, nullable=True)  # Relative lift vs control (e.g., 0.15 for 15%)
    lift_absolute = Column(Float, nullable=True)  # Absolute difference
    
    # Statistical significance
    p_value = Column(Float, nullable=True)  # P-value from statistical test
    is_statistically_significant = Column(Boolean, default=False, nullable=False)
    
    # Confidence interval
    confidence_level = Column(Float, default=0.95, nullable=False)
    confidence_interval_lower = Column(Float, nullable=True)
    confidence_interval_upper = Column(Float, nullable=True)
    
    # Effect size
    cohens_d = Column(Float, nullable=True)  # Standardized effect size
    
    # Statistical test used
    statistical_test = Column(String(50), nullable=True)  # e.g., "chi_square", "t_test", "mann_whitney"
    
    # Additional metrics (JSON)
    # {
    #     "revenue_per_visitor": 12.50,
    #     "average_order_value": 85.00,
    #     "bounce_rate": 0.35
    # }
    additional_metrics = Column(JSON, default=dict, nullable=False)
    
    # Calculation metadata
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    calculation_method = Column(Text, nullable=True)  # Description of calculation method
    
    # Relationships
    experiment = relationship("Experiment", back_populates="results")
    variant = relationship("ExperimentVariant", back_populates="results")
    
    # Indexes
    __table_args__ = (
        Index('idx_result_experiment', 'experiment_id'),
        Index('idx_result_variant', 'variant_id'),
        Index('idx_result_metric', 'experiment_id', 'metric_name'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "id": self.id,
            "experiment_id": self.experiment_id,
            "variant_id": self.variant_id,
            "metric_name": self.metric_name,
            "sample_size": self.sample_size,
            "conversions": self.conversions,
            "metric_value": self.metric_value,
            "metric_sum": self.metric_sum,
            "lift_percentage": self.lift_percentage,
            "lift_absolute": self.lift_absolute,
            "p_value": self.p_value,
            "is_statistically_significant": self.is_statistically_significant,
            "confidence_level": self.confidence_level,
            "confidence_interval_lower": self.confidence_interval_lower,
            "confidence_interval_upper": self.confidence_interval_upper,
            "cohens_d": self.cohens_d,
            "statistical_test": self.statistical_test,
            "additional_metrics": self.additional_metrics,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "calculation_method": self.calculation_method,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def get_confidence_interval_range(self) -> Optional[tuple]:
        """Get confidence interval as a tuple (lower, upper)."""
        if self.confidence_interval_lower is not None and self.confidence_interval_upper is not None:
            return (self.confidence_interval_lower, self.confidence_interval_upper)
        return None
    
    def get_formatted_lift(self) -> str:
        """Get formatted lift percentage string."""
        if self.lift_percentage is None:
            return "N/A"
        sign = "+" if self.lift_percentage > 0 else ""
        return f"{sign}{self.lift_percentage * 100:.2f}%"
    
    def get_significance_stars(self) -> str:
        """Get significance stars (like in academic papers)."""
        if self.p_value is None:
            return ""
        if self.p_value < 0.001:
            return "***"
        elif self.p_value < 0.01:
            return "**"
        elif self.p_value < 0.05:
            return "*"
        return ""
