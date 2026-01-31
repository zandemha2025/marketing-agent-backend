"""
Analytics API endpoints for the Marketing Agent Platform.

Provides comprehensive analytics and statistics for:
- Campaign performance
- Asset generation and usage
- Task completion rates
- Scheduled post metrics
- Recent activity tracking
- Attribution analysis
- Marketing Mix Modeling
- ROI reporting
- Conversion tracking
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from pydantic import BaseModel, Field

from ..core.database import get_session
from ..models.campaign import Campaign
from ..models.asset import Asset
from ..models.task import Task
from ..models.scheduled_post import ScheduledPost
from ..models.user import User
from ..models.deliverable import Deliverable
from ..models.attribution import AttributionModelType
from ..models.conversion_event import ConversionType, ConversionStatus
from ..models.marketing_mix_model import MMMModelStatus

from ..services.analytics.attribution_engine import AttributionEngine
from ..services.analytics.marketing_mix_modeling import MarketingMixModelingService
from ..services.analytics.analytics_dashboard import AnalyticsDashboardService
from ..services.analytics.conversion_tracker import ConversionTracker
from .auth import get_current_active_user
from ..models.user import User

router = APIRouter(tags=["Analytics"])


# ============== Response Models ==============

class CampaignStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    created_this_week: int
    created_this_month: int
    completion_rate: float


class AssetStats(BaseModel):
    total: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    created_this_week: int


class TaskStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    completion_rate: float
    overdue_count: int
    high_priority_count: int


class ScheduledPostStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_platform: Dict[str, int]
    published_this_week: int
    scheduled_this_week: int


class ActivityItem(BaseModel):
    id: str
    type: str  # campaign, asset, task, post
    action: str  # created, updated, completed, published
    title: str
    description: Optional[str] = None
    timestamp: datetime
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class OverviewStats(BaseModel):
    campaigns: CampaignStats
    assets: AssetStats
    tasks: TaskStats
    scheduled_posts: ScheduledPostStats
    recent_activity: List[ActivityItem]


class DateRangeFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# Attribution Models
class AttributionReportRequest(BaseModel):
    model_type: AttributionModelType = AttributionModelType.LAST_TOUCH
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    group_by: str = "channel"  # channel, campaign, touchpoint_type


class AttributionComparisonResponse(BaseModel):
    period: Dict[str, str]
    models: Dict[str, Dict[str, float]]


class AttributionReportResponse(BaseModel):
    model_type: str
    group_by: str
    period: Dict[str, str]
    summary: Dict[str, Any]
    data: List[Dict[str, Any]]


# ROI Models
class ROIReportResponse(BaseModel):
    period: Dict[str, str]
    summary: Dict[str, Any]
    data: List[Dict[str, Any]]


# Conversion Models
class ConversionTrackRequest(BaseModel):
    customer_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    conversion_type: ConversionType = ConversionType.CUSTOM
    conversion_name: Optional[str] = None
    conversion_value: float = 0.0
    currency: str = "USD"
    properties: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    lookback_window_days: int = 30


class ConversionResponse(BaseModel):
    id: str
    conversion_type: str
    conversion_name: str
    conversion_value: float
    currency: str
    status: str
    touchpoint_count: int
    created_at: str


# MMM Models
class MMMCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    target_variable: str = "revenue"
    target_unit: Optional[str] = "usd"
    training_start_date: Optional[date] = None
    training_end_date: Optional[date] = None
    mmm_config: Optional[Dict[str, Any]] = None


class MMMTrainResponse(BaseModel):
    model_id: str
    status: str
    r_squared: Optional[float] = None
    mape: Optional[float] = None
    message: str


class MMMBudgetOptimizeRequest(BaseModel):
    total_budget: float
    constraints: Optional[Dict[str, Any]] = None


class MMMBudgetOptimizeResponse(BaseModel):
    model_id: str
    total_budget: float
    improvement_pct: float
    improvement_absolute: float
    current_allocation: Dict[str, Any]
    optimized_allocation: Dict[str, Any]
    recommendations: List[Dict[str, Any]]


# Dashboard Models
class DashboardOverviewResponse(BaseModel):
    period: Dict[str, str]
    metrics: Dict[str, Any]
    top_channels: List[Dict[str, Any]]


class TimeSeriesRequest(BaseModel):
    metric: str  # revenue, conversions, attributed_revenue
    granularity: str = "day"  # hour, day, week, month
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TimeSeriesResponse(BaseModel):
    metric: str
    granularity: str
    data: List[Dict[str, Any]]


class FunnelResponse(BaseModel):
    period: Dict[str, str]
    stages: List[Dict[str, Any]]
    overall_conversion_rate: float


class CustomerJourneyResponse(BaseModel):
    customer_id: Optional[str]
    anonymous_id: Optional[str]
    period: Dict[str, str]
    touchpoint_count: int
    conversion_count: int
    journey: List[Dict[str, Any]]


# ============== Helper Functions ==============

def get_date_range(
    days: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> tuple:
    """Get date range for queries."""
    if start_date and end_date:
        return start_date, end_date

    end = end_date or datetime.utcnow()

    if days:
        start = end - timedelta(days=days)
    else:
        start = end - timedelta(days=30)

    return start, end


# ============== Existing Endpoints ==============

@router.get("/overview", response_model=OverviewStats)
async def get_overview_stats(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get overview statistics for the dashboard."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Campaign stats
    campaign_result = await session.execute(select(Campaign))
    campaigns = campaign_result.scalars().all()

    campaign_by_status = {}
    created_this_week = 0
    created_this_month = 0
    completed = 0

    for c in campaigns:
        campaign_by_status[c.status] = campaign_by_status.get(c.status, 0) + 1
        if c.created_at >= week_ago:
            created_this_week += 1
        if c.created_at >= month_ago:
            created_this_month += 1
        if c.status == "completed":
            completed += 1

    total_campaigns = len(campaigns)
    completion_rate = (completed / total_campaigns * 100) if total_campaigns > 0 else 0

    # Asset stats
    asset_result = await session.execute(select(Asset))
    assets = asset_result.scalars().all()

    asset_by_type = {}
    asset_by_status = {}
    assets_this_week = 0

    for a in assets:
        asset_by_type[a.asset_type] = asset_by_type.get(a.asset_type, 0) + 1
        asset_by_status[a.status] = asset_by_status.get(a.status, 0) + 1
        if a.created_at >= week_ago:
            assets_this_week += 1

    # Task stats
    task_result = await session.execute(select(Task))
    tasks = task_result.scalars().all()

    task_by_status = {}
    overdue = 0
    high_priority = 0
    completed_tasks = 0

    for t in tasks:
        task_by_status[t.status] = task_by_status.get(t.status, 0) + 1
        if t.due_date and t.due_date < now and t.status != "completed":
            overdue += 1
        if t.priority == "high":
            high_priority += 1
        if t.status == "completed":
            completed_tasks += 1

    total_tasks = len(tasks)
    task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Scheduled post stats
    post_result = await session.execute(select(ScheduledPost))
    posts = post_result.scalars().all()

    post_by_status = {}
    post_by_platform = {}
    published_this_week = 0
    scheduled_this_week = 0

    for p in posts:
        post_by_status[p.status] = post_by_status.get(p.status, 0) + 1
        post_by_platform[p.platform] = post_by_platform.get(p.platform, 0) + 1
        if p.published_at and p.published_at >= week_ago:
            published_this_week += 1
        if p.scheduled_at and p.scheduled_at >= week_ago:
            scheduled_this_week += 1

    # Recent activity
    recent_activity = []

    # Recent campaigns
    recent_campaigns = await session.execute(
        select(Campaign).order_by(desc(Campaign.created_at)).limit(5)
    )
    for c in recent_campaigns.scalars():
        recent_activity.append(ActivityItem(
            id=c.id,
            type="campaign",
            action="created",
            title=c.name,
            timestamp=c.created_at
        ))

    # Recent assets
    recent_assets = await session.execute(
        select(Asset).order_by(desc(Asset.created_at)).limit(5)
    )
    for a in recent_assets.scalars():
        recent_activity.append(ActivityItem(
            id=a.id,
            type="asset",
            action="created",
            title=a.name,
            timestamp=a.created_at
        ))

    # Sort by timestamp
    recent_activity.sort(key=lambda x: x.timestamp, reverse=True)
    recent_activity = recent_activity[:10]

    return OverviewStats(
        campaigns=CampaignStats(
            total=total_campaigns,
            by_status=campaign_by_status,
            created_this_week=created_this_week,
            created_this_month=created_this_month,
            completion_rate=completion_rate
        ),
        assets=AssetStats(
            total=len(assets),
            by_type=asset_by_type,
            by_status=asset_by_status,
            created_this_week=assets_this_week
        ),
        tasks=TaskStats(
            total=total_tasks,
            by_status=task_by_status,
            completion_rate=task_completion_rate,
            overdue_count=overdue,
            high_priority_count=high_priority
        ),
        scheduled_posts=ScheduledPostStats(
            total=len(posts),
            by_status=post_by_status,
            by_platform=post_by_platform,
            published_this_week=published_this_week,
            scheduled_this_week=scheduled_this_week
        ),
        recent_activity=recent_activity
    )


@router.get("/campaigns/{campaign_id}/performance")
async def get_campaign_performance(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed performance metrics for a campaign."""
    campaign = await session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get deliverables for this campaign
    deliverables_result = await session.execute(
        select(Deliverable).where(Deliverable.campaign_id == campaign_id)
    )
    deliverables = deliverables_result.scalars().all()

    # Calculate metrics
    total_deliverables = len(deliverables)
    completed_deliverables = sum(1 for d in deliverables if d.status == "completed")
    completion_rate = (completed_deliverables / total_deliverables * 100) if total_deliverables > 0 else 0

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "status": campaign.status,
        "deliverables": {
            "total": total_deliverables,
            "completed": completed_deliverables,
            "completion_rate": completion_rate
        },
        "timeline": {
            "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
            "end_date": campaign.end_date.isoformat() if campaign.end_date else None
        }
    }


# ============== Attribution Endpoints ==============

@router.post("/attribution/report", response_model=AttributionReportResponse)
async def get_attribution_report(
    request: AttributionReportRequest,
    organization_id: str = Query(..., description="Organization ID"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get attribution report by channel, campaign, or touchpoint type."""
    dashboard = AnalyticsDashboardService(session)

    report = await dashboard.get_attribution_report(
        organization_id=organization_id,
        model_type=request.model_type,
        start_date=request.start_date,
        end_date=request.end_date,
        group_by=request.group_by
    )

    return AttributionReportResponse(**report)


@router.get("/attribution/comparison", response_model=AttributionComparisonResponse)
async def compare_attribution_models(
    organization_id: str = Query(..., description="Organization ID"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Compare attribution across different models."""
    dashboard = AnalyticsDashboardService(session)

    comparison = await dashboard.get_attribution_comparison(
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date
    )

    return AttributionComparisonResponse(**comparison)


@router.post("/attribution/process")
async def process_attribution(
    background_tasks: BackgroundTasks,
    organization_id: str = Query(..., description="Organization ID"),
    batch_size: int = Query(100, description="Number of conversions to process"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Process pending conversions for attribution."""
    engine = AttributionEngine(session)

    processed = await engine.process_pending_conversions(organization_id, batch_size)

    return {
        "organization_id": organization_id,
        "processed_count": processed,
        "status": "completed"
    }


# ============== ROI Endpoints ==============

@router.get("/roi/report", response_model=ROIReportResponse)
async def get_roi_report(
    organization_id: str = Query(..., description="Organization ID"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    group_by: str = Query("channel", description="Group by: channel, campaign, touchpoint_type"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get ROI report by channel or campaign."""
    dashboard = AnalyticsDashboardService(session)

    report = await dashboard.get_roi_report(
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by
    )

    return ROIReportResponse(**report)


# ============== Conversion Tracking Endpoints ==============

@router.post("/conversions/track", response_model=ConversionResponse)
async def track_conversion(
    request: ConversionTrackRequest,
    organization_id: str = Query(..., description="Organization ID"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Track a new conversion."""
    tracker = ConversionTracker(session)

    conversion = await tracker.track_conversion(
        organization_id=organization_id,
        customer_id=request.customer_id,
        anonymous_id=request.anonymous_id,
        conversion_type=request.conversion_type,
        conversion_name=request.conversion_name,
        conversion_value=request.conversion_value,
        currency=request.currency,
        properties=request.properties,
        context=request.context,
        timestamp=request.timestamp,
        lookback_window_days=request.lookback_window_days
    )

    return ConversionResponse(
        id=conversion.id,
        conversion_type=conversion.conversion_type.value if conversion.conversion_type else "custom",
        conversion_name=conversion.conversion_name,
        conversion_value=conversion.conversion_value,
        currency=conversion.currency,
        status=conversion.status.value if conversion.status else "pending",
        touchpoint_count=conversion.attributed_touchpoint_count or 0,
        created_at=conversion.created_at.isoformat() if conversion.created_at else ""
    )


@router.get("/conversions/summary")
async def get_conversion_summary(
    organization_id: str = Query(..., description="Organization ID"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get conversion summary."""
    tracker = ConversionTracker(session)

    summary = await tracker.get_conversion_summary(
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date
    )

    return summary


@router.get("/conversions/{conversion_id}/journey", response_model=CustomerJourneyResponse)
async def get_conversion_journey(
    conversion_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get customer journey for a specific conversion."""
    from ..models.conversion_event import ConversionEvent

    conversion = await session.get(ConversionEvent, conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")

    tracker = ConversionTracker(session)

    journey = await tracker.get_customer_journey(
        organization_id=conversion.organization_id,
        customer_id=conversion.customer_id,
        anonymous_id=conversion.anonymous_id
    )

    return CustomerJourneyResponse(**journey)


# ============== Marketing Mix Modeling Endpoints ==============

@router.post("/mmm/models")
async def create_mmm_model(
    request: MMMCreateRequest,
    organization_id: str = Query(..., description="Organization ID"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new Marketing Mix Model."""
    from ..models.marketing_mix_model import MarketingMixModel

    model = MarketingMixModel(
        organization_id=organization_id,
        name=request.name,
        description=request.description,
        target_variable=request.target_variable,
        target_unit=request.target_unit,
        training_start_date=request.training_start_date,
        training_end_date=request.training_end_date,
        model_config=request.model_config or {},
        status=MMMModelStatus.DRAFT
    )

    session.add(model)
    await session.commit()

    return {
        "model_id": model.id,
        "name": model.name,
        "status": model.status.value,
        "message": "Model created successfully"
    }


@router.post("/mmm/models/{model_id}/train", response_model=MMMTrainResponse)
async def train_mmm_model(
    model_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Train a Marketing Mix Model."""
    mmm_service = MarketingMixModelingService(session)

    try:
        result = await mmm_service.train_model(model_id)

        return MMMTrainResponse(
            model_id=model_id,
            status="trained",
            r_squared=result.r_squared,
            mape=result.mape,
            message="Model trained successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/mmm/models/{model_id}/summary")
async def get_mmm_summary(
    model_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get Marketing Mix Model summary."""
    mmm_service = MarketingMixModelingService(session)

    summary = await mmm_service.get_model_summary(model_id)

    if not summary:
        raise HTTPException(status_code=404, detail="Model not found")

    return summary


@router.post("/mmm/models/{model_id}/optimize", response_model=MMMBudgetOptimizeResponse)
async def optimize_budget(
    model_id: str,
    request: MMMBudgetOptimizeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Optimize budget allocation for a Marketing Mix Model."""
    mmm_service = MarketingMixModelingService(session)

    try:
        result = await mmm_service.optimize_budget(
            model_id=model_id,
            total_budget=request.total_budget,
            constraints=request.constraints
        )

        recommendations = result.get_reallocation_recommendations()

        return MMMBudgetOptimizeResponse(
            model_id=model_id,
            total_budget=result.total_budget,
            improvement_pct=result.improvement_pct,
            improvement_absolute=result.improvement_absolute,
            current_allocation=result.current_allocation,
            optimized_allocation=result.optimized_allocation,
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


# ============== Dashboard Endpoints ==============

@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    organization_id: str = Query(..., description="Organization ID"),
    days: int = Query(30, description="Number of days to include"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get dashboard overview metrics."""
    dashboard = AnalyticsDashboardService(session)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    metrics = await dashboard.get_overview_metrics(
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date
    )

    top_channels = await dashboard._get_top_channels(
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date
    )

    return DashboardOverviewResponse(
        period={
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        metrics=metrics,
        top_channels=top_channels
    )


@router.post("/dashboard/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    request: TimeSeriesRequest,
    organization_id: str = Query(..., description="Organization ID"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get time-series data for a metric."""
    dashboard = AnalyticsDashboardService(session)

    series = await dashboard.get_time_series(
        organization_id=organization_id,
        metric=request.metric,
        granularity=request.granularity,
        start_date=request.start_date,
        end_date=request.end_date
    )

    return TimeSeriesResponse(
        metric=request.metric,
        granularity=request.granularity,
        data=[
            {
                "timestamp": point.timestamp.isoformat(),
                "value": point.value
            }
            for point in series
        ]
    )


@router.get("/dashboard/funnel", response_model=FunnelResponse)
async def get_conversion_funnel(
    organization_id: str = Query(..., description="Organization ID"),
    days: int = Query(30, description="Number of days to include"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get conversion funnel analysis."""
    dashboard = AnalyticsDashboardService(session)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    funnel = await dashboard.get_conversion_funnel(
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date
    )

    return FunnelResponse(**funnel)


@router.get("/dashboard/customer-journey", response_model=CustomerJourneyResponse)
async def get_customer_journey_analytics(
    organization_id: str = Query(..., description="Organization ID"),
    customer_id: Optional[str] = None,
    anonymous_id: Optional[str] = None,
    days: int = Query(90, description="Number of days to include"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get customer journey analytics."""
    if not customer_id and not anonymous_id:
        raise HTTPException(status_code=400, detail="Either customer_id or anonymous_id required")

    tracker = ConversionTracker(session)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    journey = await tracker.get_customer_journey(
        organization_id=organization_id,
        customer_id=customer_id,
        anonymous_id=anonymous_id,
        start_date=start_date,
        end_date=end_date
    )

    return CustomerJourneyResponse(**journey)


@router.get("/dashboard/export")
async def export_report(
    report_type: str = Query(..., description="Report type: attribution, roi, overview"),
    organization_id: str = Query(..., description="Organization ID"),
    format: str = Query("json", description="Export format: json, csv"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Export analytics report."""
    dashboard = AnalyticsDashboardService(session)

    export = await dashboard.export_report(
        organization_id=organization_id,
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        format=format
    )

    return export
