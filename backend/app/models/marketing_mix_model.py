"""
Marketing Mix Model for analyzing marketing channel effectiveness.

Implements Marketing Mix Modeling (MMM) with adstock and saturation effects
to measure the impact of marketing activities on business outcomes.
"""
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, Index, Enum as SQLEnum, Float, Integer, Date, Text, Boolean
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class MMMModelStatus(str, Enum):
    """Status of Marketing Mix Model."""
    DRAFT = "draft"
    TRAINING = "training"
    TRAINED = "trained"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"
    ERROR = "error"


class MMMChannelType(str, Enum):
    """Types of marketing channels for MMM."""
    # Paid Media
    TV = "tv"
    RADIO = "radio"
    PRINT = "print"
    OUT_OF_HOME = "out_of_home"
    PAID_SEARCH = "paid_search"
    PAID_SOCIAL = "paid_social"
    DISPLAY = "display"
    VIDEO_ADS = "video_ads"
    PROGRAMMATIC = "programmatic"

    # Digital
    ORGANIC_SEARCH = "organic_search"
    ORGANIC_SOCIAL = "organic_social"
    EMAIL = "email"
    CONTENT_MARKETING = "content_marketing"
    AFFILIATE = "affiliate"
    INFLUENCER = "influencer"

    # Other
    EVENTS = "events"
    PR = "pr"
    PARTNERSHIPS = "partnerships"
    DIRECT_MAIL = "direct_mail"
    SPONSORSHIP = "sponsorship"

    # Baseline
    BASELINE = "baseline"  # Non-marketing factors


class MarketingMixModel(Base):
    """
    Marketing Mix Model.

    Stores trained marketing mix models that analyze the relationship
    between marketing spend and business outcomes.
    """

    # Organization/workspace scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(String(12), ForeignKey("organizations.id"), nullable=True)

    # Model identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Model status
    status = Column(SQLEnum(MMMModelStatus), default=MMMModelStatus.DRAFT, nullable=False, index=True)

    # Target variable (what we're predicting)
    target_variable = Column(String(50), nullable=False)  # e.g., "revenue", "conversions", "signups"
    target_unit = Column(String(20), nullable=True)  # e.g., "usd", "count"

    # Time period
    training_start_date = Column(Date, nullable=True)
    training_end_date = Column(Date, nullable=True)
    prediction_horizon_days = Column(Integer, default=30, nullable=False)

    # Model configuration
    model_config = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "model_type": "ridge_regression",
    #     "adstock_decay": 0.5,
    #     "saturation_shape": "hill",
    #     "saturation_k": 2.0,
    #     "include_seasonality": True,
    #     "include_trend": True,
    #     "include_holidays": True,
    #     "granularity": "daily"  # or "weekly", "monthly"
    # }

    # Model performance metrics
    performance_metrics = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "r_squared": 0.85,
    #     "adjusted_r_squared": 0.82,
    #     "mape": 0.08,
    #     "rmse": 15000,
    #     "mae": 12000,
    #     "cross_validation_score": 0.83
    # }

    # Model coefficients
    model_coefficients = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "channels": {
    #         "paid_search": {"coefficient": 0.45, "roi": 3.2, "mroi": 2.8},
    #         "paid_social": {"coefficient": 0.32, "roi": 2.5, "mroi": 2.1}
    #     },
    #     "baseline": {"coefficient": 0.23, "contribution_pct": 0.35},
    #     "control_variables": {
    #         "seasonality": {"coefficient": 0.15},
    #         "trend": {"coefficient": 0.02}
    #     }
    # }

    # Adstock parameters
    adstock_params = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "paid_search": {"decay": 0.3, "peak_delay_days": 2},
    #     "tv": {"decay": 0.7, "peak_delay_days": 7}
    # }

    # Saturation parameters
    saturation_params = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "paid_search": {"shape": "hill", "k": 2.0, "half_saturation": 50000},
    #     "tv": {"shape": "hill", "k": 1.5, "half_saturation": 100000}
    # }

    # Feature importance
    feature_importance = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "paid_search": 0.35,
    #     "paid_social": 0.28,
    #     "organic_search": 0.15,
    #     "baseline": 0.22
    # }

    # Model diagnostics
    diagnostics = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "residual_analysis": {"mean": 0.02, "std": 0.15},
    #     "heteroscedasticity_test": {"p_value": 0.23},
    #     "multicollinearity": {"max_vif": 3.2},
    #     "normality_test": {"shapiro_wilk": 0.87}
    # }

    # Training metadata
    trained_at = Column(DateTime, nullable=True)
    trained_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    training_duration_seconds = Column(Integer, nullable=True)

    # Validation metadata
    validated_at = Column(DateTime, nullable=True)
    validated_by = Column(String(12), ForeignKey("users.id"), nullable=True)

    # Model version
    version = Column(String(20), default="1.0.0", nullable=False)
    parent_model_id = Column(String(12), ForeignKey("marketing_mix_models.id"), nullable=True)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    channels = relationship(
        "MMMChannel",
        back_populates="model",
        cascade="all, delete-orphan"
    )
    predictions = relationship(
        "MMMPrediction",
        back_populates="model",
        cascade="all, delete-orphan"
    )
    optimizer_results = relationship(
        "MMMBudgetOptimizer",
        back_populates="model",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_mmm_models_org_status", "organization_id", "status"),
        Index("ix_mmm_models_trained_at", "trained_at"),
        Index("ix_mmm_models_target", "organization_id", "target_variable"),
    )

    def __repr__(self):
        return f"<MarketingMixModel {self.name} status={self.status} version={self.version}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "target_variable": self.target_variable,
            "target_unit": self.target_unit,
            "training_start_date": self.training_start_date.isoformat() if self.training_start_date else None,
            "training_end_date": self.training_end_date.isoformat() if self.training_end_date else None,
            "prediction_horizon_days": self.prediction_horizon_days,
            "model_config": self.model_config,
            "performance_metrics": self.performance_metrics,
            "model_coefficients": self.model_coefficients,
            "adstock_params": self.adstock_params,
            "saturation_params": self.saturation_params,
            "feature_importance": self.feature_importance,
            "diagnostics": self.diagnostics,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            "training_duration_seconds": self.training_duration_seconds,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "version": self.version,
            "parent_model_id": self.parent_model_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_channel_roi(self, channel: str) -> Optional[float]:
        """Get ROI for a specific channel."""
        if self.model_coefficients and "channels" in self.model_coefficients:
            channel_data = self.model_coefficients["channels"].get(channel, {})
            return channel_data.get("roi")
        return None

    def get_total_contribution_pct(self) -> Dict[str, float]:
        """Get contribution percentage by channel."""
        contributions = {}
        if self.model_coefficients:
            channels = self.model_coefficients.get("channels", {})
            baseline = self.model_coefficients.get("baseline", {})

            for channel, data in channels.items():
                contributions[channel] = data.get("contribution_pct", 0)

            if baseline:
                contributions["baseline"] = baseline.get("contribution_pct", 0)

        return contributions

    def is_ready_for_prediction(self) -> bool:
        """Check if model is ready for prediction."""
        return self.status in {MMMModelStatus.TRAINED, MMMModelStatus.VALIDATED, MMMModelStatus.DEPLOYED}


class MMMChannel(Base):
    """
    Marketing Mix Model Channel.

    Represents a marketing channel included in a Marketing Mix Model
    with its configuration and historical data.
    """
    __tablename__ = "mmm_channels"

    # Model reference
    model_id = Column(String(12), ForeignKey("marketing_mix_models.id"), nullable=False, index=True)

    # Channel identification
    channel_type = Column(SQLEnum(MMMChannelType), nullable=False, index=True)
    channel_name = Column(String(100), nullable=False)
    display_name = Column(String(255), nullable=True)

    # Channel configuration
    config = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "spend_aggregation": "daily",
    #     "currency": "USD",
    #     "impression_metric": "impressions",
    #     "include_in_model": True,
    #     "is_control_variable": False
    # }

    # Adstock configuration
    adstock_decay = Column(Float, nullable=True)  # Decay rate (0-1)
    adstock_peak_delay = Column(Integer, nullable=True)  # Days to peak effect

    # Saturation configuration
    saturation_shape = Column(String(20), default="hill", nullable=True)  # hill, logistic, linear
    saturation_k = Column(Float, nullable=True)  # Shape parameter
    saturation_half_spend = Column(Float, nullable=True)  # Spend at 50% saturation

    # Historical aggregates
    total_spend = Column(Float, nullable=True)
    total_impressions = Column(Float, nullable=True)
    avg_daily_spend = Column(Float, nullable=True)
    spend_currency = Column(String(3), default="USD", nullable=True)

    # Model results
    coefficient = Column(Float, nullable=True)
    standard_error = Column(Float, nullable=True)
    p_value = Column(Float, nullable=True)
    roi = Column(Float, nullable=True)
    marginal_roi = Column(Float, nullable=True)
    contribution_pct = Column(Float, nullable=True)

    # Elasticity
    elasticity = Column(Float, nullable=True)  # % change in target / % change in spend

    # Relationships
    model = relationship("MarketingMixModel", back_populates="channels")
    daily_data = relationship(
        "MMMChannelDaily",
        back_populates="channel",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_mmm_channels_model_type", "model_id", "channel_type"),
        Index("ix_mmm_channels_roi", "roi"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert channel to dictionary representation."""
        return {
            "id": self.id,
            "model_id": self.model_id,
            "channel_type": self.channel_type.value if self.channel_type else None,
            "channel_name": self.channel_name,
            "display_name": self.display_name,
            "config": self.config,
            "adstock_decay": self.adstock_decay,
            "adstock_peak_delay": self.adstock_peak_delay,
            "saturation_shape": self.saturation_shape,
            "saturation_k": self.saturation_k,
            "saturation_half_spend": self.saturation_half_spend,
            "total_spend": self.total_spend,
            "total_impressions": self.total_impressions,
            "avg_daily_spend": self.avg_daily_spend,
            "spend_currency": self.spend_currency,
            "coefficient": self.coefficient,
            "standard_error": self.standard_error,
            "p_value": self.p_value,
            "roi": self.roi,
            "marginal_roi": self.marginal_roi,
            "contribution_pct": self.contribution_pct,
            "elasticity": self.elasticity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MMMChannelDaily(Base):
    """
    Daily data for MMM channels.

    Stores time-series data for marketing channels used in MMM training.
    """

    # Channel reference
    channel_id = Column(String(12), ForeignKey("mmm_channels.id"), nullable=False, index=True)
    model_id = Column(String(12), ForeignKey("marketing_mix_models.id"), nullable=False, index=True)

    # Date
    date = Column(Date, nullable=False, index=True)

    # Spend data
    spend = Column(Float, nullable=True)
    spend_currency = Column(String(3), default="USD", nullable=True)

    # Media metrics
    impressions = Column(Float, nullable=True)
    clicks = Column(Float, nullable=True)
    conversions = Column(Float, nullable=True)

    # Transformed values (adstock, saturation)
    adstocked_spend = Column(Float, nullable=True)
    saturated_spend = Column(Float, nullable=True)

    # Target variable (for reference)
    target_value = Column(Float, nullable=True)

    # Relationships
    channel = relationship("MMMChannel", back_populates="daily_data")

    # Indexes
    __table_args__ = (
        Index("ix_mmm_daily_channel_date", "channel_id", "date"),
        Index("ix_mmm_daily_model_date", "model_id", "date"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert daily data to dictionary representation."""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "model_id": self.model_id,
            "date": self.date.isoformat() if self.date else None,
            "spend": self.spend,
            "spend_currency": self.spend_currency,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "adstocked_spend": self.adstocked_spend,
            "saturated_spend": self.saturated_spend,
            "target_value": self.target_value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MMMPrediction(Base):
    """
    Marketing Mix Model Prediction.

    Stores predictions made by a Marketing Mix Model for future periods.
    """

    # Model reference
    model_id = Column(String(12), ForeignKey("marketing_mix_models.id"), nullable=False, index=True)

    # Organization
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)

    # Prediction period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Prediction type
    prediction_type = Column(String(50), default="forecast", nullable=False)  # forecast, scenario, optimization

    # Scenario configuration (for scenario predictions)
    scenario_config = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "budget_changes": {"paid_search": 1.2, "paid_social": 0.9},
    #     "description": "20% increase in paid search"
    # }

    # Predicted values
    predicted_total = Column(Float, nullable=False)
    prediction_interval_lower = Column(Float, nullable=True)  # 95% CI lower
    prediction_interval_upper = Column(Float, nullable=True)  # 95% CI upper

    # Channel breakdown
    channel_predictions = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "paid_search": {"predicted": 50000, "contribution_pct": 0.35},
    #     "paid_social": {"predicted": 35000, "contribution_pct": 0.25}
    # }

    # Model metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(12), ForeignKey("users.id"), nullable=True)

    # Relationships
    model = relationship("MarketingMixModel", back_populates="predictions")

    # Indexes
    __table_args__ = (
        Index("ix_mmm_predictions_model_date", "model_id", "start_date"),
        Index("ix_mmm_predictions_org", "organization_id", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction to dictionary representation."""
        return {
            "id": self.id,
            "model_id": self.model_id,
            "organization_id": self.organization_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "prediction_type": self.prediction_type,
            "scenario_config": self.scenario_config,
            "predicted_total": self.predicted_total,
            "prediction_interval_lower": self.prediction_interval_lower,
            "prediction_interval_upper": self.prediction_interval_upper,
            "channel_predictions": self.channel_predictions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MMMBudgetOptimizer(Base):
    """
    Marketing Mix Model Budget Optimizer Results.

    Stores results from budget optimization runs that recommend
    optimal budget allocation across channels.
    """

    # Model reference
    model_id = Column(String(12), ForeignKey("marketing_mix_models.id"), nullable=False, index=True)

    # Organization
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)

    # Optimization parameters
    total_budget = Column(Float, nullable=False)
    budget_currency = Column(String(3), default="USD", nullable=False)
    optimization_period_days = Column(Integer, default=30, nullable=False)

    # Constraints
    constraints = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "min_spend_per_channel": {"paid_search": 10000, "paid_social": 5000},
    #     "max_spend_per_channel": {"paid_search": 100000, "tv": 200000},
    #     "min_total_spend": 50000,
    #     "maintain_current_mix_pct": 0.2  # Can change by max 20%
    # }

    # Current allocation (baseline)
    current_allocation = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "paid_search": {"spend": 50000, "predicted_return": 150000},
    #     "paid_social": {"spend": 40000, "predicted_return": 100000}
    # }

    # Optimized allocation
    optimized_allocation = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "paid_search": {"spend": 60000, "predicted_return": 180000, "marginal_roi": 2.8},
    #     "paid_social": {"spend": 30000, "predicted_return": 85000, "marginal_roi": 2.5}
    # }

    # Optimization results
    current_predicted_total = Column(Float, nullable=False)
    optimized_predicted_total = Column(Float, nullable=False)
    improvement_pct = Column(Float, nullable=False)
    improvement_absolute = Column(Float, nullable=False)

    # Optimization metadata
    optimization_algorithm = Column(String(50), default="gradient_descent", nullable=False)
    iterations = Column(Integer, nullable=True)
    convergence_tolerance = Column(Float, default=0.001, nullable=True)

    # Status
    status = Column(String(20), default="completed", nullable=False)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(12), ForeignKey("users.id"), nullable=True)

    # Relationships
    model = relationship("MarketingMixModel", back_populates="optimizer_results")

    # Indexes
    __table_args__ = (
        Index("ix_mmm_optimizer_model", "model_id", "created_at"),
        Index("ix_mmm_optimizer_org", "organization_id", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert optimizer result to dictionary representation."""
        return {
            "id": self.id,
            "model_id": self.model_id,
            "organization_id": self.organization_id,
            "total_budget": self.total_budget,
            "budget_currency": self.budget_currency,
            "optimization_period_days": self.optimization_period_days,
            "constraints": self.constraints,
            "current_allocation": self.current_allocation,
            "optimized_allocation": self.optimized_allocation,
            "current_predicted_total": self.current_predicted_total,
            "optimized_predicted_total": self.optimized_predicted_total,
            "improvement_pct": self.improvement_pct,
            "improvement_absolute": self.improvement_absolute,
            "optimization_algorithm": self.optimization_algorithm,
            "iterations": self.iterations,
            "convergence_tolerance": self.convergence_tolerance,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def get_reallocation_recommendations(self) -> List[Dict[str, Any]]:
        """Get budget reallocation recommendations."""
        recommendations = []

        for channel in set(self.current_allocation.keys()) | set(self.optimized_allocation.keys()):
            current = self.current_allocation.get(channel, {}).get("spend", 0)
            optimized = self.optimized_allocation.get(channel, {}).get("spend", 0)
            change_pct = ((optimized - current) / current * 100) if current > 0 else 0

            recommendations.append({
                "channel": channel,
                "current_spend": current,
                "recommended_spend": optimized,
                "change_amount": optimized - current,
                "change_pct": change_pct,
                "priority": "high" if abs(change_pct) > 20 else "medium" if abs(change_pct) > 10 else "low"
            })

        return sorted(recommendations, key=lambda x: abs(x["change_pct"]), reverse=True)
