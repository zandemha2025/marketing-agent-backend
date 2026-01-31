"""
Predictive Performance Modeling.

Provides ML-based performance prediction for campaigns before launch,
including CTR prediction, conversion rate prediction, and overall
campaign performance forecasting.
"""
import logging
import pickle
import base64
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, mean_squared_error, r2_score
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...models.predictive_model import PredictiveModel, PredictiveModelType, PredictiveModelStatus
from ...models.campaign import Campaign
from ...models.asset import Asset

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Result of a prediction."""
    predicted_value: float
    confidence_interval: Tuple[float, float]
    confidence_score: float
    feature_importance: Dict[str, float]
    model_version: str


@dataclass
class CampaignPrediction:
    """Complete campaign performance prediction."""
    predicted_ctr: float
    predicted_conversion_rate: float
    predicted_revenue: float
    confidence_score: float
    risk_level: str  # low, medium, high
    recommendations: List[str]


@dataclass
class ModelEvaluation:
    """Model evaluation metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: Optional[float]
    rmse: Optional[float]
    r2_score: Optional[float]
    test_size: int


@dataclass
class TrainingExample:
    """Training example for model."""
    features: Dict[str, float]
    target: float
    metadata: Optional[Dict[str, Any]] = None


class PredictivePerformanceModel:
    """
    Predictive performance modeling service.
    
    Uses machine learning to predict campaign performance before launch,
    enabling data-driven decisions about creative selection, audience
targeting, and budget allocation.
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize with database session."""
        self.db = db_session
    
    # === Feature Engineering ===
    
    def extract_creative_features(
        self,
        creative: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Extract features from a creative asset.
        
        Args:
            creative: Creative asset data
            
        Returns:
            Dict of feature names to values
        """
        features = {}
        
        # Text features
        headline = creative.get('headline', '')
        description = creative.get('description', '')
        
        features['headline_length'] = len(headline)
        features['description_length'] = len(description)
        features['headline_word_count'] = len(headline.split())
        features['has_number_in_headline'] = 1.0 if any(c.isdigit() for c in headline) else 0.0
        features['has_question_in_headline'] = 1.0 if '?' in headline else 0.0
        features['has_exclamation'] = 1.0 if '!' in headline else 0.0
        
        # Visual features (if available)
        visual = creative.get('visual', {})
        features['has_image'] = 1.0 if visual.get('type') == 'image' else 0.0
        features['has_video'] = 1.0 if visual.get('type') == 'video' else 0.0
        features['color_count'] = visual.get('color_count', 0)
        features['brightness'] = visual.get('brightness', 0.5)
        
        # CTA features
        cta = creative.get('cta', '')
        features['cta_length'] = len(cta)
        features['cta_urgency_words'] = sum(1 for word in ['now', 'today', 'limited', 'hurry'] 
                                           if word in cta.lower())
        
        return features
    
    def extract_audience_features(
        self,
        audience: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Extract features from audience data.
        
        Args:
            audience: Audience targeting data
            
        Returns:
            Dict of feature names to values
        """
        features = {}
        
        # Size features
        features['audience_size'] = audience.get('estimated_size', 0)
        features['audience_size_log'] = np.log1p(features['audience_size'])
        
        # Demographic features
        demographics = audience.get('demographics', {})
        features['age_range_width'] = demographics.get('age_max', 65) - demographics.get('age_min', 18)
        features['gender_targeting'] = 1.0 if demographics.get('gender') else 0.0
        
        # Interest features
        interests = audience.get('interests', [])
        features['interest_count'] = len(interests)
        features['interest_diversity'] = len(set(interests)) / len(interests) if interests else 0.0
        
        # Behavioral features
        behaviors = audience.get('behaviors', [])
        features['behavior_count'] = len(behaviors)
        
        return features
    
    def extract_context_features(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Extract features from context (time, device, etc.).
        
        Args:
            context: Context data
            
        Returns:
            Dict of feature names to values
        """
        features = {}
        
        # Time features
        hour = context.get('hour', 12)
        features['hour'] = hour
        features['is_business_hours'] = 1.0 if 9 <= hour <= 17 else 0.0
        features['is_evening'] = 1.0 if 18 <= hour <= 22 else 0.0
        features['is_weekend'] = 1.0 if context.get('day_of_week', 0) >= 5 else 0.0
        
        # Device features
        device = context.get('device', 'desktop')
        features['is_mobile'] = 1.0 if device == 'mobile' else 0.0
        features['is_tablet'] = 1.0 if device == 'tablet' else 0.0
        features['is_desktop'] = 1.0 if device == 'desktop' else 0.0
        
        # Channel features
        channel = context.get('channel', '')
        features['is_social'] = 1.0 if channel in ['facebook', 'instagram', 'twitter', 'linkedin'] else 0.0
        features['is_search'] = 1.0 if channel in ['google', 'bing'] else 0.0
        features['is_display'] = 1.0 if channel in ['display', 'programmatic'] else 0.0
        
        return features
    
    def extract_historical_features(
        self,
        organization_id: str,
        creative_type: str
    ) -> Dict[str, float]:
        """
        Extract historical performance features.
        
        Args:
            organization_id: Organization ID
            creative_type: Type of creative
            
        Returns:
            Dict of feature names to values
        """
        # These would be fetched from historical data in production
        # For now, return default values
        return {
            'historical_ctr': 0.02,
            'historical_cvr': 0.05,
            'historical_roas': 2.5,
            'campaigns_count': 10,
            'avg_campaign_performance': 0.5
        }
    
    def extract_features(
        self,
        creative: Dict[str, Any],
        audience: Dict[str, Any],
        context: Dict[str, Any],
        organization_id: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Extract all features for prediction.
        
        Combines creative, audience, context, and historical features.
        
        Args:
            creative: Creative asset data
            audience: Audience targeting data
            context: Context data
            organization_id: Optional org ID for historical features
            
        Returns:
            Combined feature dictionary
        """
        features = {}
        
        features.update(self.extract_creative_features(creative))
        features.update(self.extract_audience_features(audience))
        features.update(self.extract_context_features(context))
        
        if organization_id:
            creative_type = creative.get('type', 'unknown')
            features.update(self.extract_historical_features(organization_id, creative_type))
        
        return features
    
    # === Model Training ===
    
    async def train_ctr_model(
        self,
        organization_id: str,
        training_data: List[TrainingExample],
        model_name: Optional[str] = None
    ) -> PredictiveModel:
        """
        Train CTR prediction model.
        
        Uses gradient boosting for binary classification (click/no-click).
        
        Args:
            organization_id: Organization ID
            training_data: List of training examples
            model_name: Optional model name
            
        Returns:
            Trained PredictiveModel
        """
        return await self._train_model(
            organization_id=organization_id,
            model_type=PredictiveModelType.CTR_PREDICTION,
            training_data=training_data,
            model_algorithm="gradient_boosting_classifier",
            model_name=model_name or f"CTR Model {datetime.utcnow().strftime('%Y-%m-%d')}"
        )
    
    async def train_conversion_model(
        self,
        organization_id: str,
        training_data: List[TrainingExample],
        model_name: Optional[str] = None
    ) -> PredictiveModel:
        """
        Train conversion rate prediction model.
        
        Args:
            organization_id: Organization ID
            training_data: List of training examples
            model_name: Optional model name
            
        Returns:
            Trained PredictiveModel
        """
        return await self._train_model(
            organization_id=organization_id,
            model_type=PredictiveModelType.CONVERSION_PREDICTION,
            training_data=training_data,
            model_algorithm="gradient_boosting_classifier",
            model_name=model_name or f"Conversion Model {datetime.utcnow().strftime('%Y-%m-%d')}"
        )
    
    async def train_revenue_model(
        self,
        organization_id: str,
        training_data: List[TrainingExample],
        model_name: Optional[str] = None
    ) -> PredictiveModel:
        """
        Train revenue prediction model.
        
        Uses gradient boosting regressor for continuous revenue prediction.
        
        Args:
            organization_id: Organization ID
            training_data: List of training examples
            model_name: Optional model name
            
        Returns:
            Trained PredictiveModel
        """
        return await self._train_model(
            organization_id=organization_id,
            model_type=PredictiveModelType.REVENUE_PREDICTION,
            training_data=training_data,
            model_algorithm="gradient_boosting_regressor",
            model_name=model_name or f"Revenue Model {datetime.utcnow().strftime('%Y-%m-%d')}"
        )
    
    async def _train_model(
        self,
        organization_id: str,
        model_type: PredictiveModelType,
        training_data: List[TrainingExample],
        model_algorithm: str,
        model_name: str,
        hyperparameters: Optional[Dict[str, Any]] = None
    ) -> PredictiveModel:
        """
        Internal method to train a predictive model.
        
        Args:
            organization_id: Organization ID
            model_type: Type of model
            training_data: Training examples
            model_algorithm: Algorithm to use
            model_name: Name for the model
            hyperparameters: Optional hyperparameters
            
        Returns:
            Trained PredictiveModel
        """
        if len(training_data) < 100:
            raise ValueError(f"Insufficient training data: {len(training_data)} samples (min 100)")
        
        # Prepare data
        feature_keys = list(training_data[0].features.keys())
        X = np.array([[example.features.get(k, 0) for k in feature_keys] 
                      for example in training_data])
        y = np.array([example.target for example in training_data])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Create model
        default_params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': 42
        }
        params = {**default_params, **(hyperparameters or {})}
        
        if model_algorithm == "gradient_boosting_classifier":
            model = GradientBoostingClassifier(**params)
        elif model_algorithm == "gradient_boosting_regressor":
            model = GradientBoostingRegressor(**params)
        elif model_algorithm == "random_forest":
            model = RandomForestClassifier(**params)
        else:
            raise ValueError(f"Unknown algorithm: {model_algorithm}")
        
        # Train
        model.fit(X_train, y_train)
        
        # Evaluate
        evaluation = self._evaluate_model(model, X_test, y_test, model_algorithm)
        
        # Get feature importance
        importance = dict(zip(feature_keys, model.feature_importances_))
        
        # Serialize model
        model_bytes = pickle.dumps(model)
        model_b64 = base64.b64encode(model_bytes).decode('utf-8')
        
        # Create model record
        predictive_model = PredictiveModel(
            organization_id=organization_id,
            name=model_name,
            model_type=model_type,
            status=PredictiveModelStatus.ACTIVE,
            feature_columns=feature_keys,
            target_column="ctr" if model_type == PredictiveModelType.CTR_PREDICTION else "conversion",
            model_parameters={'serialized_model': model_b64},
            model_algorithm=model_algorithm,
            training_metrics={
                'accuracy': evaluation.accuracy,
                'precision': evaluation.precision,
                'recall': evaluation.recall,
                'f1_score': evaluation.f1_score
            },
            validation_metrics={
                'auc_roc': evaluation.auc_roc,
                'rmse': evaluation.rmse,
                'r2_score': evaluation.r2_score
            },
            feature_importance=importance,
            training_data_count=len(training_data),
            last_trained_at=datetime.utcnow(),
            hyperparameters=params,
            is_active=True
        )
        
        self.db.add(predictive_model)
        await self.db.commit()
        await self.db.refresh(predictive_model)
        
        logger.info(f"Trained {model_type.value} model: {model_name} (ID: {predictive_model.id})")
        
        return predictive_model
    
    def _evaluate_model(
        self,
        model,
        X_test: np.ndarray,
        y_test: np.ndarray,
        algorithm: str
    ) -> ModelEvaluation:
        """Evaluate model performance."""
        predictions = model.predict(X_test)
        
        if "classifier" in algorithm:
            # Classification metrics
            pred_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
            
            return ModelEvaluation(
                accuracy=accuracy_score(y_test, predictions),
                precision=precision_score(y_test, predictions, zero_division=0),
                recall=recall_score(y_test, predictions, zero_division=0),
                f1_score=f1_score(y_test, predictions, zero_division=0),
                auc_roc=roc_auc_score(y_test, pred_proba) if pred_proba is not None else None,
                rmse=None,
                r2_score=None,
                test_size=len(y_test)
            )
        else:
            # Regression metrics
            return ModelEvaluation(
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                auc_roc=None,
                rmse=np.sqrt(mean_squared_error(y_test, predictions)),
                r2_score=r2_score(y_test, predictions),
                test_size=len(y_test)
            )
    
    # === Prediction ===
    
    async def predict_ctr(
        self,
        model_id: str,
        creative: Dict[str, Any],
        audience: Dict[str, Any],
        context: Dict[str, Any]
    ) -> PredictionResult:
        """
        Predict CTR for a creative before launch.
        
        Args:
            model_id: PredictiveModel ID
            creative: Creative asset data
            audience: Audience targeting data
            context: Context data
            
        Returns:
            PredictionResult with predicted CTR
        """
        # Get model
        model_record = await self.db.get(PredictiveModel, model_id)
        if not model_record:
            raise ValueError(f"Model {model_id} not found")
        
        # Deserialize model
        model = self._deserialize_model(model_record.model_parameters)
        
        # Extract features
        features = self.extract_features(creative, audience, context)
        feature_vector = np.array([features.get(k, 0) for k in model_record.feature_columns])
        
        # Predict
        if hasattr(model, 'predict_proba'):
            prediction = model.predict_proba([feature_vector])[0][1]
        else:
            prediction = model.predict([feature_vector])[0]
        
        # Calculate confidence interval (simplified)
        confidence = 0.8  # Could be calculated from model uncertainty
        ci_width = 0.05
        ci_lower = max(0, prediction - ci_width)
        ci_upper = min(1, prediction + ci_width)
        
        # Update prediction stats
        model_record.total_predictions += 1
        model_record.last_prediction_at = datetime.utcnow()
        await self.db.commit()
        
        return PredictionResult(
            predicted_value=float(prediction),
            confidence_interval=(ci_lower, ci_upper),
            confidence_score=confidence,
            feature_importance=model_record.feature_importance,
            model_version=model_record.model_version
        )
    
    async def predict_conversion_rate(
        self,
        model_id: str,
        landing_page: Dict[str, Any],
        audience: Dict[str, Any]
    ) -> PredictionResult:
        """
        Predict conversion rate for a landing page.
        
        Args:
            model_id: PredictiveModel ID
            landing_page: Landing page data
            audience: Audience data
            
        Returns:
            PredictionResult with predicted conversion rate
        """
        # Similar to predict_ctr but for conversion
        model_record = await self.db.get(PredictiveModel, model_id)
        if not model_record:
            raise ValueError(f"Model {model_id} not found")
        
        model = self._deserialize_model(model_record.model_parameters)
        
        # Extract features (simplified)
        features = {
            **self.extract_creative_features(landing_page),
            **self.extract_audience_features(audience)
        }
        feature_vector = np.array([features.get(k, 0) for k in model_record.feature_columns])
        
        if hasattr(model, 'predict_proba'):
            prediction = model.predict_proba([feature_vector])[0][1]
        else:
            prediction = model.predict([feature_vector])[0]
        
        confidence = 0.75
        ci_width = 0.03
        
        model_record.total_predictions += 1
        model_record.last_prediction_at = datetime.utcnow()
        await self.db.commit()
        
        return PredictionResult(
            predicted_value=float(prediction),
            confidence_interval=(max(0, prediction - ci_width), min(1, prediction + ci_width)),
            confidence_score=confidence,
            feature_importance=model_record.feature_importance,
            model_version=model_record.model_version
        )
    
    async def predict_campaign_performance(
        self,
        campaign_config: Dict[str, Any],
        ctr_model_id: Optional[str] = None,
        conversion_model_id: Optional[str] = None
    ) -> CampaignPrediction:
        """
        Predict overall campaign performance.
        
        Combines multiple models for comprehensive prediction.
        
        Args:
            campaign_config: Campaign configuration
            ctr_model_id: Optional CTR model ID
            conversion_model_id: Optional conversion model ID
            
        Returns:
            CampaignPrediction with full performance forecast
        """
        creatives = campaign_config.get('creatives', [])
        audience = campaign_config.get('audience', {})
        budget = campaign_config.get('budget', 1000)
        
        if not creatives:
            raise ValueError("No creatives provided for prediction")
        
        # Predict CTR for each creative
        ctr_predictions = []
        for creative in creatives:
            if ctr_model_id:
                try:
                    result = await self.predict_ctr(
                        ctr_model_id,
                        creative,
                        audience,
                        campaign_config.get('context', {})
                    )
                    ctr_predictions.append(result.predicted_value)
                except Exception as e:
                    logger.warning(f"CTR prediction failed: {e}")
                    ctr_predictions.append(0.02)  # Default
            else:
                ctr_predictions.append(0.02)  # Default industry average
        
        avg_ctr = np.mean(ctr_predictions)
        
        # Predict conversion rate
        if conversion_model_id:
            try:
                conv_result = await self.predict_conversion_rate(
                    conversion_model_id,
                    campaign_config.get('landing_page', {}),
                    audience
                )
                conversion_rate = conv_result.predicted_value
            except Exception as e:
                logger.warning(f"Conversion prediction failed: {e}")
                conversion_rate = 0.05
        else:
            conversion_rate = 0.05  # Default
        
        # Estimate revenue
        cpc = campaign_config.get('avg_cpc', 1.0)
        estimated_clicks = (budget / cpc) if cpc > 0 else 0
        estimated_conversions = estimated_clicks * conversion_rate
        avg_order_value = campaign_config.get('avg_order_value', 50)
        estimated_revenue = estimated_conversions * avg_order_value
        
        # Calculate confidence and risk
        confidence = 0.7 if (ctr_model_id and conversion_model_id) else 0.5
        
        if confidence > 0.8:
            risk_level = "low"
        elif confidence > 0.6:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_ctr, conversion_rate, campaign_config
        )
        
        return CampaignPrediction(
            predicted_ctr=avg_ctr,
            predicted_conversion_rate=conversion_rate,
            predicted_revenue=estimated_revenue,
            confidence_score=confidence,
            risk_level=risk_level,
            recommendations=recommendations
        )
    
    def _generate_recommendations(
        self,
        ctr: float,
        conversion_rate: float,
        config: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on predictions."""
        recommendations = []
        
        if ctr < 0.01:
            recommendations.append("Predicted CTR is low. Consider testing different headlines or visuals.")
        
        if conversion_rate < 0.02:
            recommendations.append("Predicted conversion rate is low. Review landing page and offer.")
        
        if ctr > 0.05:
            recommendations.append("High predicted CTR! This creative should perform well.")
        
        audience_size = config.get('audience', {}).get('estimated_size', 0)
        if audience_size < 10000:
            recommendations.append("Audience size is small. Consider expanding targeting.")
        
        return recommendations
    
    def _deserialize_model(self, model_parameters: Dict[str, Any]):
        """Deserialize model from storage."""
        if 'serialized_model' not in model_parameters:
            raise ValueError("Model parameters missing serialized model")
        
        model_b64 = model_parameters['serialized_model']
        model_bytes = base64.b64decode(model_b64)
        return pickle.loads(model_bytes)
    
    # === Model Management ===
    
    async def evaluate_model(
        self,
        model_id: str,
        test_data: List[TrainingExample]
    ) -> ModelEvaluation:
        """
        Evaluate model performance on test data.
        
        Args:
            model_id: Model ID
            test_data: Test examples
            
        Returns:
            ModelEvaluation metrics
        """
        model_record = await self.db.get(PredictiveModel, model_id)
        if not model_record:
            raise ValueError(f"Model {model_id} not found")
        
        model = self._deserialize_model(model_record.model_parameters)
        
        # Prepare test data
        X = np.array([[example.features.get(k, 0) for k in model_record.feature_columns] 
                      for example in test_data])
        y = np.array([example.target for example in test_data])
        
        return self._evaluate_model(model, X, y, model_record.model_algorithm)
    
    async def retrain_if_needed(
        self,
        model_id: str,
        new_training_data: Optional[List[TrainingExample]] = None,
        accuracy_threshold: float = 0.7
    ) -> Optional[PredictiveModel]:
        """
        Retrain model if accuracy drops below threshold.
        
        Args:
            model_id: Model ID
            new_training_data: Optional new data to include
            accuracy_threshold: Minimum accuracy before retraining
            
        Returns:
            New model if retrained, None otherwise
        """
        model_record = await self.db.get(PredictiveModel, model_id)
        if not model_record:
            raise ValueError(f"Model {model_id} not found")
        
        # Check if retraining needed
        primary_metric = model_record.get_primary_metric()
        if primary_metric and primary_metric >= accuracy_threshold:
            logger.info(f"Model {model_id} performance ({primary_metric:.3f}) above threshold, no retraining needed")
            return None
        
        logger.info(f"Model {model_id} performance ({primary_metric:.3f}) below threshold, retraining...")
        
        # In production, would fetch historical data and combine with new data
        # For now, just mark as needing retraining
        model_record.status = PredictiveModelStatus.DEPRECATED
        await self.db.commit()
        
        # Return None - actual retraining would be done separately
        return None
    
    async def list_models(
        self,
        organization_id: str,
        model_type: Optional[PredictiveModelType] = None,
        active_only: bool = True
    ) -> List[PredictiveModel]:
        """
        List predictive models for an organization.
        
        Args:
            organization_id: Organization ID
            model_type: Optional filter by type
            active_only: Only return active models
            
        Returns:
            List of PredictiveModel records
        """
        query = select(PredictiveModel).where(
            PredictiveModel.organization_id == organization_id
        )
        
        if model_type:
            query = query.where(PredictiveModel.model_type == model_type)
        
        if active_only:
            query = query.where(PredictiveModel.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def deactivate_model(self, model_id: str) -> PredictiveModel:
        """Deactivate a model."""
        model = await self.db.get(PredictiveModel, model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        model.is_active = False
        model.status = PredictiveModelStatus.DEPRECATED
        
        await self.db.commit()
        await self.db.refresh(model)
        
        return model