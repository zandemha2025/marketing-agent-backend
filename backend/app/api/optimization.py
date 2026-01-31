"""
Optimization API endpoints.

Provides REST API for:
- A/B testing experiments
- Campaign optimization
- Predictive modeling
- Bandit optimization
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from .auth import get_current_active_user
from ..models.user import User
from ..core.config import get_settings
from ..services.optimization.ab_testing import ABTestingEngine, VariantConfig, AssignmentResult
from ..services.optimization.bandit_engine import BanditEngine, BanditRecommendation
from ..services.optimization.campaign_optimizer import CampaignOptimizer, OptimizationStrategy
from ..services.optimization.predictive_modeling import PredictivePerformanceModel, PredictionResult, CampaignPrediction, TrainingExample
from ..models.experiment import Experiment, ExperimentStatus, ExperimentType
from ..models.experiment_variant import ExperimentVariant
from ..models.experiment_assignment import ExperimentAssignment
from ..models.experiment_result import ExperimentResult
from ..models.predictive_model import PredictiveModel, PredictiveModelType, PredictiveModelStatus

router = APIRouter(prefix="/optimization", tags=["optimization"])


# === Pydantic Models ===

class VariantConfigRequest(BaseModel):
    """Variant configuration for experiment creation."""
    name: str
    traffic_percentage: float = Field(..., ge=0, le=100)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    is_control: bool = False
    description: Optional[str] = None


class ExperimentCreateRequest(BaseModel):
    """Request to create an experiment."""
    organization_id: str
    name: str
    description: Optional[str] = None
    hypothesis: str
    primary_metric: str
    experiment_type: ExperimentType = ExperimentType.AB_TEST
    variants: List[VariantConfigRequest]
    traffic_allocation: float = Field(default=1.0, ge=0, le=1)
    min_sample_size: int = Field(default=100, ge=10)
    confidence_level: float = Field(default=0.95, ge=0.8, le=0.99)
    statistical_power: float = Field(default=0.8, ge=0.5, le=0.95)
    minimum_detectable_effect: float = Field(default=0.05, ge=0.01, le=0.5)
    campaign_id: Optional[str] = None
    secondary_metrics: Optional[List[str]] = None
    auto_winner_selection: bool = False


class ExperimentResponse(BaseModel):
    """Experiment response."""
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    experiment_type: str
    status: str
    hypothesis: str
    primary_metric: str
    traffic_allocation: float
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    winner_variant_id: Optional[str]
    created_at: datetime


class AssignmentRequest(BaseModel):
    """Request to assign user to experiment."""
    user_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AssignmentResponse(BaseModel):
    """Assignment response."""
    variant_id: str
    variant_name: str
    is_control: bool
    configuration: Dict[str, Any]
    assignment_id: str


class MetricTrackRequest(BaseModel):
    """Request to track experiment metric."""
    variant_id: str
    user_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    metric_name: str
    metric_value: float
    conversion_value: Optional[Dict[str, Any]] = None


class ExperimentResultsResponse(BaseModel):
    """Experiment results response."""
    experiment_id: str
    metric_name: str
    variants: List[Dict[str, Any]]
    has_winner: bool
    winner_variant_id: Optional[str]


class CampaignOptimizeRequest(BaseModel):
    """Request to optimize campaign."""
    optimization_type: str = Field(default="full", pattern="^(budget|creative|audience|full|bids)$")
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None


class OptimizationRecommendation(BaseModel):
    """Optimization recommendation."""
    type: str
    description: str
    expected_improvement: float
    confidence: float
    action_items: List[str]


class PredictiveModelCreateRequest(BaseModel):
    """Request to create predictive model."""
    organization_id: str
    name: str
    description: Optional[str] = None
    model_type: PredictiveModelType
    campaign_id: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None


class PredictiveModelResponse(BaseModel):
    """Predictive model response."""
    id: str
    name: str
    model_type: str
    status: str
    training_metrics: Dict[str, Any]
    validation_metrics: Dict[str, Any]
    feature_importance: Dict[str, float]
    is_active: bool
    created_at: datetime


class PredictionRequest(BaseModel):
    """Request for prediction."""
    creative: Dict[str, Any]
    audience: Dict[str, Any]
    context: Dict[str, Any] = Field(default_factory=dict)


class PredictionResponse(BaseModel):
    """Prediction response."""
    predicted_value: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    confidence_score: float
    feature_importance: Dict[str, float]


class BanditConfigRequest(BaseModel):
    """Request to create bandit experiment."""
    organization_id: str
    name: str
    description: Optional[str] = None
    variants: List[VariantConfigRequest]
    campaign_id: Optional[str] = None


class BanditRecommendationResponse(BaseModel):
    """Bandit recommendation response."""
    variant_id: str
    variant_name: str
    algorithm: str
    confidence: float
    estimated_conversion_rate: float


class BanditRewardRequest(BaseModel):
    """Request to report bandit reward."""
    variant_id: str
    reward: float = Field(..., ge=0, le=1)


class AutoOptimizationSettings(BaseModel):
    """Auto-optimization settings."""
    enabled: bool
    interval_minutes: int = Field(default=60, ge=15, le=1440)
    strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    max_budget_shift_percent: float = Field(default=0.2, ge=0.05, le=0.5)
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None


# === Dependency Injection ===

async def get_ab_testing_engine(db: AsyncSession = Depends(get_session)) -> ABTestingEngine:
    """Get A/B testing engine."""
    return ABTestingEngine(db)


async def get_bandit_engine(db: AsyncSession = Depends(get_session)) -> BanditEngine:
    """Get bandit engine."""
    return BanditEngine(db)


async def get_campaign_optimizer(
    db: AsyncSession = Depends(get_session)
) -> CampaignOptimizer:
    """Get campaign optimizer."""
    return CampaignOptimizer(db)


async def get_predictive_model(db: AsyncSession = Depends(get_session)) -> PredictivePerformanceModel:
    """Get predictive model service."""
    return PredictivePerformanceModel(db)


# === Experiment Endpoints ===

@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    request: ExperimentCreateRequest,
    engine: ABTestingEngine = Depends(get_ab_testing_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new A/B test experiment."""
    try:
        # Convert variant configs
        variants = [
            VariantConfig(
                name=v.name,
                traffic_percentage=v.traffic_percentage,
                configuration=v.configuration,
                is_control=v.is_control,
                description=v.description
            )
            for v in request.variants
        ]
        
        experiment = await engine.create_experiment(
            organization_id=request.organization_id,
            name=request.name,
            hypothesis=request.hypothesis,
            primary_metric=request.primary_metric,
            variants=variants,
            experiment_type=request.experiment_type,
            traffic_allocation=request.traffic_allocation,
            min_sample_size=request.min_sample_size,
            confidence_level=request.confidence_level,
            statistical_power=request.statistical_power,
            minimum_detectable_effect=request.minimum_detectable_effect,
            campaign_id=request.campaign_id,
            secondary_metrics=request.secondary_metrics,
            auto_winner_selection=request.auto_winner_selection
        )
        
        return ExperimentResponse(
            id=experiment.id,
            organization_id=experiment.organization_id,
            name=experiment.name,
            description=experiment.description,
            experiment_type=experiment.experiment_type.value,
            status=experiment.status.value,
            hypothesis=experiment.hypothesis,
            primary_metric=experiment.primary_metric,
            traffic_allocation=experiment.traffic_allocation,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            winner_variant_id=experiment.winner_variant_id,
            created_at=experiment.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    organization_id: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """List experiments for an organization."""
    from sqlalchemy import select, and_
    
    query = select(Experiment).where(Experiment.organization_id == organization_id)
    
    if status:
        query = query.where(Experiment.status == status)
    
    result = await db.execute(query.order_by(Experiment.created_at.desc()))
    experiments = result.scalars().all()
    
    return [
        ExperimentResponse(
            id=e.id,
            organization_id=e.organization_id,
            name=e.name,
            description=e.description,
            experiment_type=e.experiment_type.value,
            status=e.status.value,
            hypothesis=e.hypothesis,
            primary_metric=e.primary_metric,
            traffic_allocation=e.traffic_allocation,
            start_date=e.start_date,
            end_date=e.end_date,
            winner_variant_id=e.winner_variant_id,
            created_at=e.created_at
        )
        for e in experiments
    ]


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get experiment details."""
    experiment = await db.get(Experiment, experiment_id)
    
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return ExperimentResponse(
        id=experiment.id,
        organization_id=experiment.organization_id,
        name=experiment.name,
        description=experiment.description,
        experiment_type=experiment.experiment_type.value,
        status=experiment.status.value,
        hypothesis=experiment.hypothesis,
        primary_metric=experiment.primary_metric,
        traffic_allocation=experiment.traffic_allocation,
        start_date=experiment.start_date,
        end_date=experiment.end_date,
        winner_variant_id=experiment.winner_variant_id,
        created_at=experiment.created_at
    )


@router.post("/experiments/{experiment_id}/start", response_model=ExperimentResponse)
async def start_experiment(
    experiment_id: str,
    engine: ABTestingEngine = Depends(get_ab_testing_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Start a running experiment."""
    try:
        experiment = await engine.start_experiment(experiment_id)
        return ExperimentResponse(
            id=experiment.id,
            organization_id=experiment.organization_id,
            name=experiment.name,
            description=experiment.description,
            experiment_type=experiment.experiment_type.value,
            status=experiment.status.value,
            hypothesis=experiment.hypothesis,
            primary_metric=experiment.primary_metric,
            traffic_allocation=experiment.traffic_allocation,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            winner_variant_id=experiment.winner_variant_id,
            created_at=experiment.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/experiments/{experiment_id}/stop", response_model=ExperimentResponse)
async def stop_experiment(
    experiment_id: str,
    winner_variant_id: Optional[str] = None,
    reason: Optional[str] = None,
    engine: ABTestingEngine = Depends(get_ab_testing_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Stop an experiment and optionally declare winner."""
    try:
        experiment = await engine.stop_experiment(
            experiment_id=experiment_id,
            winner_variant_id=winner_variant_id,
            reason=reason
        )
        return ExperimentResponse(
            id=experiment.id,
            organization_id=experiment.organization_id,
            name=experiment.name,
            description=experiment.description,
            experiment_type=experiment.experiment_type.value,
            status=experiment.status.value,
            hypothesis=experiment.hypothesis,
            primary_metric=experiment.primary_metric,
            traffic_allocation=experiment.traffic_allocation,
            start_date=experiment.start_date,
            end_date=experiment.end_date,
            winner_variant_id=experiment.winner_variant_id,
            created_at=experiment.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/experiments/{experiment_id}/results", response_model=ExperimentResultsResponse)
async def get_experiment_results(
    experiment_id: str,
    metric_name: Optional[str] = None,
    engine: ABTestingEngine = Depends(get_ab_testing_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Get experiment results."""
    try:
        results = await engine.calculate_results(experiment_id, metric_name)
        
        # Get experiment for winner info
        from sqlalchemy import select
        result = await engine.db.execute(
            select(Experiment).where(Experiment.id == experiment_id)
        )
        experiment = result.scalar_one_or_none()
        
        variants_data = []
        for variant_id, result in results.items():
            variants_data.append(result.to_dict())
        
        return ExperimentResultsResponse(
            experiment_id=experiment_id,
            metric_name=metric_name or experiment.primary_metric if experiment else "unknown",
            variants=variants_data,
            has_winner=experiment.winner_variant_id is not None if experiment else False,
            winner_variant_id=experiment.winner_variant_id if experiment else None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/experiments/{experiment_id}/assign", response_model=AssignmentResponse)
async def assign_user_to_experiment(
    experiment_id: str,
    request: AssignmentRequest,
    engine: ABTestingEngine = Depends(get_ab_testing_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Assign user to experiment variant."""
    try:
        assignment = await engine.assign_user(
            experiment_id=experiment_id,
            user_id=request.user_id,
            anonymous_id=request.anonymous_id,
            context=request.context
        )
        
        return AssignmentResponse(
            variant_id=assignment.variant_id,
            variant_name=assignment.variant_name,
            is_control=assignment.is_control,
            configuration=assignment.configuration,
            assignment_id=assignment.assignment_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/experiments/{experiment_id}/track")
async def track_experiment_metric(
    experiment_id: str,
    request: MetricTrackRequest,
    engine: ABTestingEngine = Depends(get_ab_testing_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Track a conversion/metric for a user in an experiment."""
    try:
        success = await engine.track_conversion(
            experiment_id=experiment_id,
            user_id=request.user_id,
            anonymous_id=request.anonymous_id,
            conversion_value={
                'metric_name': request.metric_name,
                'metric_value': request.metric_value,
                **(request.conversion_value or {})
            }
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="No assignment found for user")
        
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Campaign Optimization Endpoints ===

@router.post("/campaigns/{campaign_id}/optimize")
async def optimize_campaign(
    campaign_id: str,
    request: CampaignOptimizeRequest,
    optimizer: CampaignOptimizer = Depends(get_campaign_optimizer),
    current_user: User = Depends(get_current_active_user)
):
    """Run optimization for a campaign."""
    # This would implement the actual optimization logic
    # For now, return a placeholder response
    return {
        "campaign_id": campaign_id,
        "optimization_type": request.optimization_type,
        "status": "completed",
        "recommendations": [
            {
                "type": "budget",
                "description": "Shift 20% budget from underperforming channels",
                "expected_improvement": 0.15
            }
        ]
    }


@router.get("/campaigns/{campaign_id}/recommendations")
async def get_optimization_recommendations(
    campaign_id: str,
    optimizer: CampaignOptimizer = Depends(get_campaign_optimizer),
    current_user: User = Depends(get_current_active_user)
):
    """Get optimization recommendations for a campaign."""
    # Placeholder - would fetch actual recommendations
    return {
        "campaign_id": campaign_id,
        "recommendations": [
            OptimizationRecommendation(
                type="budget",
                description="Reallocate budget to higher performing channels",
                expected_improvement=0.12,
                confidence=0.8,
                action_items=["Increase Facebook spend by 20%", "Decrease Display spend by 15%"]
            ),
            OptimizationRecommendation(
                type="creative",
                description="Rotate underperforming creatives",
                expected_improvement=0.08,
                confidence=0.75,
                action_items=["Pause Creative A", "Increase weight of Creative C"]
            )
        ]
    }


@router.post("/campaigns/{campaign_id}/auto-optimize")
async def enable_auto_optimization(
    campaign_id: str,
    settings: AutoOptimizationSettings,
    optimizer: CampaignOptimizer = Depends(get_campaign_optimizer),
    current_user: User = Depends(get_current_active_user)
):
    """Enable auto-optimization for a campaign."""
    try:
        campaign = await optimizer.enable_auto_optimization(
            campaign_id=campaign_id,
            settings=settings.dict()
        )
        return {
            "campaign_id": campaign_id,
            "auto_optimization_enabled": True,
            "settings": settings.dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/campaigns/{campaign_id}/auto-optimize")
async def disable_auto_optimization(
    campaign_id: str,
    reason: Optional[str] = None,
    optimizer: CampaignOptimizer = Depends(get_campaign_optimizer),
    current_user: User = Depends(get_current_active_user)
):
    """Disable auto-optimization for a campaign."""
    try:
        campaign = await optimizer.disable_auto_optimization(
            campaign_id=campaign_id,
            reason=reason
        )
        return {
            "campaign_id": campaign_id,
            "auto_optimization_enabled": False,
            "disabled_reason": reason
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# === Predictive Modeling Endpoints ===

@router.post("/predictive-models", response_model=PredictiveModelResponse)
async def create_predictive_model(
    request: PredictiveModelCreateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new predictive model configuration."""
    model = PredictiveModel(
        organization_id=request.organization_id,
        name=request.name,
        description=request.description,
        model_type=request.model_type,
        campaign_id=request.campaign_id,
        status=PredictiveModelStatus.TRAINING,
        hyperparameters=request.hyperparameters or {}
    )
    
    db.add(model)
    await db.commit()
    await db.refresh(model)
    
    return PredictiveModelResponse(
        id=model.id,
        name=model.name,
        model_type=model.model_type.value,
        status=model.status.value,
        training_metrics=model.training_metrics,
        validation_metrics=model.validation_metrics,
        feature_importance=model.feature_importance,
        is_active=model.is_active,
        created_at=model.created_at
    )


@router.get("/predictive-models", response_model=List[PredictiveModelResponse])
async def list_predictive_models(
    organization_id: str,
    model_type: Optional[PredictiveModelType] = None,
    active_only: bool = True,
    service: PredictivePerformanceModel = Depends(get_predictive_model),
    current_user: User = Depends(get_current_active_user)
):
    """List predictive models for an organization."""
    models = await service.list_models(organization_id, model_type, active_only)
    
    return [
        PredictiveModelResponse(
            id=m.id,
            name=m.name,
            model_type=m.model_type.value,
            status=m.status.value,
            training_metrics=m.training_metrics,
            validation_metrics=m.validation_metrics,
            feature_importance=m.feature_importance,
            is_active=m.is_active,
            created_at=m.created_at
        )
        for m in models
    ]


@router.post("/predictive-models/{model_id}/train")
async def train_predictive_model(
    model_id: str,
    training_data: List[Dict[str, Any]],
    service: PredictivePerformanceModel = Depends(get_predictive_model),
    current_user: User = Depends(get_current_active_user)
):
    """Train a predictive model with data."""
    try:
        # Convert training data
        examples = [
            TrainingExample(
                features=d.get('features', {}),
                target=d.get('target', 0),
                metadata=d.get('metadata')
            )
            for d in training_data
        ]
        
        # Get model to determine type
        model = await service.db.get(PredictiveModel, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Train based on type
        if model.model_type == PredictiveModelType.CTR_PREDICTION:
            trained_model = await service.train_ctr_model(
                organization_id=model.organization_id,
                training_data=examples,
                model_name=model.name
            )
        elif model.model_type == PredictiveModelType.CONVERSION_PREDICTION:
            trained_model = await service.train_conversion_model(
                organization_id=model.organization_id,
                training_data=examples,
                model_name=model.name
            )
        elif model.model_type == PredictiveModelType.REVENUE_PREDICTION:
            trained_model = await service.train_revenue_model(
                organization_id=model.organization_id,
                training_data=examples,
                model_name=model.name
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported model type: {model.model_type}")
        
        return PredictiveModelResponse(
            id=trained_model.id,
            name=trained_model.name,
            model_type=trained_model.model_type.value,
            status=trained_model.status.value,
            training_metrics=trained_model.training_metrics,
            validation_metrics=trained_model.validation_metrics,
            feature_importance=trained_model.feature_importance,
            is_active=trained_model.is_active,
            created_at=trained_model.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/predictive-models/{model_id}/predict", response_model=PredictionResponse)
async def predict_performance(
    model_id: str,
    request: PredictionRequest,
    service: PredictivePerformanceModel = Depends(get_predictive_model),
    current_user: User = Depends(get_current_active_user)
):
    """Get prediction from a model."""
    try:
        # Get model to determine type
        model = await service.db.get(PredictiveModel, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Predict based on type
        if model.model_type == PredictiveModelType.CTR_PREDICTION:
            result = await service.predict_ctr(
                model_id=model_id,
                creative=request.creative,
                audience=request.audience,
                context=request.context
            )
        elif model.model_type == PredictiveModelType.CONVERSION_PREDICTION:
            result = await service.predict_conversion_rate(
                model_id=model_id,
                landing_page=request.creative,  # Landing page passed as creative
                audience=request.audience
            )
        else:
            raise HTTPException(status_code=400, detail=f"Prediction not implemented for type: {model.model_type}")
        
        return PredictionResponse(
            predicted_value=result.predicted_value,
            confidence_interval_lower=result.confidence_interval[0],
            confidence_interval_upper=result.confidence_interval[1],
            confidence_score=result.confidence_score,
            feature_importance=result.feature_importance
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/predict")
async def predict_campaign_performance(
    campaign_id: str,
    campaign_config: Dict[str, Any],
    ctr_model_id: Optional[str] = None,
    conversion_model_id: Optional[str] = None,
    service: PredictivePerformanceModel = Depends(get_predictive_model),
    current_user: User = Depends(get_current_active_user)
):
    """Predict overall campaign performance."""
    try:
        prediction = await service.predict_campaign_performance(
            campaign_config=campaign_config,
            ctr_model_id=ctr_model_id,
            conversion_model_id=conversion_model_id
        )
        
        return {
            "campaign_id": campaign_id,
            "predicted_ctr": prediction.predicted_ctr,
            "predicted_conversion_rate": prediction.predicted_conversion_rate,
            "predicted_revenue": prediction.predicted_revenue,
            "confidence_score": prediction.confidence_score,
            "risk_level": prediction.risk_level,
            "recommendations": prediction.recommendations
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Bandit Optimization Endpoints ===

@router.post("/bandits")
async def create_bandit_experiment(
    request: BanditConfigRequest,
    engine: ABTestingEngine = Depends(get_ab_testing_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new bandit experiment."""
    try:
        variants = [
            VariantConfig(
                name=v.name,
                traffic_percentage=v.traffic_percentage,
                configuration=v.configuration,
                is_control=v.is_control,
                description=v.description
            )
            for v in request.variants
        ]
        
        experiment = await engine.create_experiment(
            organization_id=request.organization_id,
            name=request.name,
            hypothesis="Continuous optimization via multi-armed bandit",
            primary_metric="conversion_rate",
            variants=variants,
            experiment_type=ExperimentType.BANDIT,
            campaign_id=request.campaign_id
        )
        
        return {
            "experiment_id": experiment.id,
            "name": experiment.name,
            "status": experiment.status.value,
            "type": "bandit"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/bandits/{experiment_id}/recommend", response_model=BanditRecommendationResponse)
async def get_bandit_recommendation(
    experiment_id: str,
    algorithm: str = "thompson_sampling",
    engine: BanditEngine = Depends(get_bandit_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Get bandit recommendation for next user."""
    try:
        recommendation = await engine.get_recommendation(
            experiment_id=experiment_id,
            algorithm=algorithm
        )
        
        return BanditRecommendationResponse(
            variant_id=recommendation.variant_id,
            variant_name=recommendation.variant_name,
            algorithm=recommendation.algorithm,
            confidence=recommendation.confidence,
            estimated_conversion_rate=recommendation.estimated_conversion_rate
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bandits/{experiment_id}/reward")
async def report_bandit_reward(
    experiment_id: str,
    request: BanditRewardRequest,
    engine: BanditEngine = Depends(get_bandit_engine),
    current_user: User = Depends(get_current_active_user)
):
    """Report reward for a bandit variant."""
    try:
        variant = await engine.update_variant_performance(
            variant_id=request.variant_id,
            reward=request.reward
        )
        
        return {
            "variant_id": variant.id,
            "successes": variant.bandit_successes,
            "failures": variant.bandit_failures,
            "pulls": variant.bandit_pulls,
            "conversion_rate": variant.get_bandit_score()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))