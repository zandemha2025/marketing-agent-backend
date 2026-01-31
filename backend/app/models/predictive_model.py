"""
Predictive Performance Model storage.

Stores trained machine learning models for predicting campaign performance,
including feature columns, model parameters, and training metrics.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON, Float, DateTime, Text, Integer, Boolean
from sqlalchemy.orm import relationship

from .base import Base


class PredictiveModelType(str, Enum):
    """Types of predictive models."""
    CTR_PREDICTION = "ctr_prediction"           # Click-through rate prediction
    CONVERSION_PREDICTION = "conversion_prediction"  # Conversion rate prediction
    REVENUE_PREDICTION = "revenue_prediction"   # Revenue prediction
    ENGAGEMENT_PREDICTION = "engagement_prediction"  # Engagement prediction
    LTV_PREDICTION = "ltv_prediction"          # Lifetime value prediction
    CHURN_PREDICTION = "churn_prediction"      # Churn prediction
    MULTI_TARGET = "multi_target"              # Multiple target predictions


class PredictiveModelStatus(str, Enum):
    """Status of predictive model."""
    TRAINING = "training"           # Currently being trained
    ACTIVE = "active"               # Ready for predictions
    DEPRECATED = "deprecated"       # Old version, not recommended
    FAILED = "failed"               # Training failed
    ARCHIVED = "archived"           # Historical record


class PredictiveModel(Base):
    """
    Predictive performance model storage.
    
    Stores serialized ML models for predicting various campaign metrics
    before launch. Includes feature engineering info and training metrics.
    """
    
    __tablename__ = "predictive_models"
    
    organization_id = Column(
        String(12),
        ForeignKey("organizations.id"),
        nullable=False
    )
    
    # Model identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    model_type = Column(SQLEnum(PredictiveModelType), nullable=False)
    status = Column(SQLEnum(PredictiveModelStatus), default=PredictiveModelStatus.TRAINING, nullable=False)
    
    # Optional campaign association (for campaign-specific models)
    campaign_id = Column(
        String(12),
        ForeignKey("campaigns.id"),
        nullable=True
    )
    
    # Feature configuration
    # List of feature column names used for training
    feature_columns = Column(JSON, default=list, nullable=False)
    
    # Target variable
    target_column = Column(String(100), nullable=False)  # e.g., "ctr", "conversion_rate"
    
    # Model parameters (serialized model)
    # Stores the actual trained model (e.g., XGBoost, LightGBM, sklearn model)
    # Serialized using pickle or joblib, stored as base64
    model_parameters = Column(JSON, nullable=True)
    
    # Model metadata
    model_algorithm = Column(String(50), nullable=True)  # e.g., "xgboost", "lightgbm", "random_forest"
    model_version = Column(String(20), default="1.0.0", nullable=False)
    
    # Training metrics
    training_metrics = Column(JSON, default=dict, nullable=False)
    # {
    #     "accuracy": 0.85,
    #     "precision": 0.82,
    #     "recall": 0.78,
    #     "f1_score": 0.80,
    #     "auc_roc": 0.91,
    #     "rmse": 0.05,
    #     "mae": 0.03,
    #     "r2_score": 0.87
    # }
    
    # Validation metrics (on holdout set)
    validation_metrics = Column(JSON, default=dict, nullable=False)
    
    # Feature importance (top features and their importance scores)
    feature_importance = Column(JSON, default=dict, nullable=False)
    # {
    #     "creative_color_count": 0.25,
    #     "headline_length": 0.18,
    #     "audience_size": 0.15,
    #     "time_of_day": 0.12,
    #     ...
    # }
    
    # Training data info
    training_data_count = Column(Integer, default=0, nullable=False)
    last_trained_at = Column(DateTime, nullable=True)
    
    # Hyperparameters used
    hyperparameters = Column(JSON, default=dict, nullable=False)
    # {
    #     "n_estimators": 100,
    #     "max_depth": 6,
    #     "learning_rate": 0.1
    # }
    
    # Thresholds for retraining
    accuracy_threshold = Column(Float, default=0.7, nullable=False)
    
    # Is this the active model for this type?
    is_active = Column(Boolean, default=False, nullable=False)
    
    # Prediction statistics
    total_predictions = Column(Integer, default=0, nullable=False)
    last_prediction_at = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="predictive_models")
    campaign = relationship("Campaign", back_populates="predictive_models")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "description": self.description,
            "model_type": self.model_type.value,
            "status": self.status.value,
            "campaign_id": self.campaign_id,
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
            "model_algorithm": self.model_algorithm,
            "model_version": self.model_version,
            "training_metrics": self.training_metrics,
            "validation_metrics": self.validation_metrics,
            "feature_importance": self.feature_importance,
            "training_data_count": self.training_data_count,
            "last_trained_at": self.last_trained_at.isoformat() if self.last_trained_at else None,
            "hyperparameters": self.hyperparameters,
            "accuracy_threshold": self.accuracy_threshold,
            "is_active": self.is_active,
            "total_predictions": self.total_predictions,
            "last_prediction_at": self.last_prediction_at.isoformat() if self.last_prediction_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_primary_metric(self) -> Optional[float]:
        """Get the primary performance metric for this model type."""
        if self.model_type in [PredictiveModelType.CTR_PREDICTION, 
                               PredictiveModelType.CONVERSION_PREDICTION]:
            return self.validation_metrics.get("auc_roc") or self.training_metrics.get("auc_roc")
        elif self.model_type in [PredictiveModelType.REVENUE_PREDICTION]:
            return self.validation_metrics.get("r2_score") or self.training_metrics.get("r2_score")
        return self.validation_metrics.get("accuracy") or self.training_metrics.get("accuracy")
    
    def needs_retraining(self) -> bool:
        """Check if model needs retraining based on accuracy threshold."""
        primary_metric = self.get_primary_metric()
        if primary_metric is None:
            return True
        return primary_metric < self.accuracy_threshold
