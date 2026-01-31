"""
Attribution model for storing attribution results.

Links touchpoints to conversions with attribution weights for different
attribution models, enabling multi-touch attribution analysis.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, Index, Enum as SQLEnum, Float, Integer, Text
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class AttributionModelType(str, Enum):
    """Types of attribution models."""
    # Single-touch models
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"

    # Multi-touch models
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    POSITION_BASED = "position_based"  # U-shaped
    W_SHAPED = "w_shaped"
    Z_SHAPED = "z_shaped"

    # Algorithmic models
    DATA_DRIVEN = "data_driven"
    MARKOV_CHAIN = "markov_chain"
    SHAPLEY_VALUE = "shapley_value"

    # Custom models
    CUSTOM = "custom"


class AttributionStatus(str, Enum):
    """Status of attribution calculation."""
    PENDING = "pending"
    CALCULATED = "calculated"
    VALIDATED = "validated"
    RECALCULATED = "recalculated"
    ERROR = "error"


class Attribution(Base):
    """
    Attribution model.

    Stores the attribution of a conversion value to a specific touchpoint
    using a specific attribution model. Multiple attribution records can
    exist for the same conversion-touchpoint pair with different models.
    """

    # Organization/workspace scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(String(12), ForeignKey("organizations.id"), nullable=True)

    # References
    conversion_event_id = Column(String(12), ForeignKey("conversion_events.id"), nullable=False, index=True)
    touchpoint_id = Column(String(12), ForeignKey("attribution_touchpoints.id"), nullable=False, index=True)

    # Attribution model
    model_type = Column(SQLEnum(AttributionModelType), nullable=False, index=True)
    model_version = Column(String(20), default="1.0", nullable=False)

    # Attribution weights and values
    weight = Column(Float, nullable=False)  # Attribution weight (0.0 to 1.0)
    attributed_value = Column(Float, nullable=False)  # Value attributed to this touchpoint
    attributed_revenue = Column(Float, nullable=True)  # Revenue attributed (if different from value)

    # Model-specific parameters
    model_parameters = Column(JSON, default=dict, nullable=False)
    # Example for time_decay:
    # {
    #     "half_life_days": 7,
    #     "decay_factor": 0.5
    # }
    # Example for position_based:
    # {
    #     "first_touch_weight": 0.4,
    #     "last_touch_weight": 0.4,
    #     "middle_touch_weight": 0.2
    # }

    # Touchpoint position in journey at time of attribution
    touchpoint_position = Column(Integer, nullable=True)
    total_touchpoints = Column(Integer, nullable=True)

    # Time calculations
    hours_to_conversion = Column(Float, nullable=True)

    # Confidence and quality metrics
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    data_quality_score = Column(Float, nullable=True)  # 0.0 to 1.0

    # Status
    status = Column(SQLEnum(AttributionStatus), default=AttributionStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)

    # Calculation metadata
    calculated_at = Column(DateTime, nullable=True)
    calculation_duration_ms = Column(Integer, nullable=True)

    # Validation
    validated_at = Column(DateTime, nullable=True)
    validated_by = Column(String(12), ForeignKey("users.id"), nullable=True)

    # Relationships
    conversion_event = relationship("ConversionEvent", back_populates="attributions")
    touchpoint = relationship("AttributionTouchpoint", back_populates="attributions")
    validator = relationship("User")

    # Indexes for analytics queries
    __table_args__ = (
        # Unique constraint: one attribution per conversion-touchpoint-model
        Index("ix_attributions_unique", "conversion_event_id", "touchpoint_id", "model_type", unique=True),
        # Composite index for conversion queries
        Index("ix_attributions_conversion", "conversion_event_id", "model_type"),
        # Composite index for touchpoint queries
        Index("ix_attributions_touchpoint", "touchpoint_id", "model_type"),
        # Composite index for model comparison
        Index("ix_attributions_org_model", "organization_id", "model_type", "calculated_at"),
        # Index for ROI calculations
        Index("ix_attributions_value", "attributed_value", "calculated_at"),
    )

    def __repr__(self):
        return f"<Attribution model={self.model_type} weight={self.weight:.2f} value={self.attributed_value:.2f}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert attribution to dictionary representation."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "conversion_event_id": self.conversion_event_id,
            "touchpoint_id": self.touchpoint_id,
            "model_type": self.model_type.value if self.model_type else None,
            "model_version": self.model_version,
            "weight": self.weight,
            "attributed_value": self.attributed_value,
            "attributed_revenue": self.attributed_revenue,
            "model_parameters": self.model_parameters,
            "touchpoint_position": self.touchpoint_position,
            "total_touchpoints": self.total_touchpoints,
            "hours_to_conversion": self.hours_to_conversion,
            "confidence_score": self.confidence_score,
            "data_quality_score": self.data_quality_score,
            "status": self.status.value if self.status else None,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
            "calculation_duration_ms": self.calculation_duration_ms,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "validated_by": self.validated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_roi(self, touchpoint_cost: float = None) -> Optional[float]:
        """
        Calculate ROI for this attribution.

        Args:
            touchpoint_cost: Cost of the touchpoint (if not stored in touchpoint)

        Returns:
            ROI as a ratio (e.g., 2.5 = 250% ROI) or None if cost is 0
        """
        cost = touchpoint_cost
        if cost is None and self.touchpoint:
            cost = self.touchpoint.cost or 0

        if cost and cost > 0:
            return (self.attributed_value - cost) / cost
        return None

    def get_roas(self, touchpoint_cost: float = None) -> Optional[float]:
        """
        Calculate ROAS (Return on Ad Spend) for this attribution.

        Args:
            touchpoint_cost: Cost of the touchpoint

        Returns:
            ROAS as a ratio (e.g., 3.5 = $3.50 return per $1 spent)
        """
        cost = touchpoint_cost
        if cost is None and self.touchpoint:
            cost = self.touchpoint.cost or 0

        if cost and cost > 0:
            return self.attributed_value / cost
        return None

    def is_single_touch(self) -> bool:
        """Check if this attribution uses a single-touch model."""
        single_touch_models = {
            AttributionModelType.FIRST_TOUCH,
            AttributionModelType.LAST_TOUCH,
        }
        return self.model_type in single_touch_models

    def is_multi_touch(self) -> bool:
        """Check if this attribution uses a multi-touch model."""
        multi_touch_models = {
            AttributionModelType.LINEAR,
            AttributionModelType.TIME_DECAY,
            AttributionModelType.POSITION_BASED,
            AttributionModelType.W_SHAPED,
            AttributionModelType.Z_SHAPED,
        }
        return self.model_type in multi_touch_models

    def is_algorithmic(self) -> bool:
        """Check if this attribution uses an algorithmic model."""
        algorithmic_models = {
            AttributionModelType.DATA_DRIVEN,
            AttributionModelType.MARKOV_CHAIN,
            AttributionModelType.SHAPLEY_VALUE,
        }
        return self.model_type in algorithmic_models


class AttributionModelConfig(Base):
    """
    Configuration for attribution models.

    Stores custom configurations for different attribution models
    per organization/workspace.
    """

    # Organization/workspace scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(String(12), ForeignKey("organizations.id"), nullable=True)

    # Model configuration
    model_type = Column(SQLEnum(AttributionModelType), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Model parameters
    parameters = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "lookback_window_days": 30,
    #     "time_decay_half_life_days": 7,
    #     "position_weights": {"first": 0.4, "last": 0.4, "middle": 0.2},
    #     "minimum_touchpoints": 1,
    #     "exclude_direct": False,
    #     "custom_rules": [...]
    # }

    # Model settings
    is_active = Column(String(1), default="Y", nullable=False)
    is_default = Column(String(1), default="N", nullable=False)

    # Lookback window
    lookback_window_days = Column(Integer, default=30, nullable=False)

    # Touchpoint filtering
    excluded_channels = Column(JSON, default=list, nullable=False)
    excluded_touchpoint_types = Column(JSON, default=list, nullable=False)

    # Validation settings
    min_confidence_threshold = Column(Float, default=0.5, nullable=False)
    require_validation = Column(String(1), default="N", nullable=False)

    # Metadata
    created_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    updated_by = Column(String(12), ForeignKey("users.id"), nullable=True)

    # Indexes
    __table_args__ = (
        # Unique constraint: one default config per model per organization
        Index("ix_attribution_configs_default", "organization_id", "model_type", "is_default", unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary representation."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "model_type": self.model_type.value if self.model_type else None,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "is_active": self.is_active == "Y",
            "is_default": self.is_default == "Y",
            "lookback_window_days": self.lookback_window_days,
            "excluded_channels": self.excluded_channels,
            "excluded_touchpoint_types": self.excluded_touchpoint_types,
            "min_confidence_threshold": self.min_confidence_threshold,
            "require_validation": self.require_validation == "Y",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_effective_parameters(self) -> Dict[str, Any]:
        """Get effective parameters with defaults applied."""
        defaults = {
            "lookback_window_days": self.lookback_window_days,
            "exclude_direct": False,
            "minimum_touchpoints": 1,
        }

        if self.model_type == AttributionModelType.TIME_DECAY:
            defaults["time_decay_half_life_days"] = 7
        elif self.model_type == AttributionModelType.POSITION_BASED:
            defaults["position_weights"] = {"first": 0.4, "last": 0.4, "middle": 0.2}
        elif self.model_type == AttributionModelType.W_SHAPED:
            defaults["position_weights"] = {"first": 0.3, "lead_conversion": 0.3, "last": 0.3, "middle": 0.1}

        # Override defaults with stored parameters
        effective = {**defaults, **self.parameters}
        return effective
