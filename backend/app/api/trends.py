from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from pydantic import BaseModel, Field

from ..core.database import get_session
from ..models.trend import Trend
from ..models.knowledge_base import KnowledgeBase
from ..services.trends.trend_scanner import trend_scanner
from .auth import get_current_active_user
from ..models.user import User
from ..services.trends.trend_analyzer import TrendAnalyzer, TrendAnalysisLegacy, TrendPrediction

router = APIRouter(prefix="/trends", tags=["Trends"])

# --- Schemas ---

class TrendSourceSchema(BaseModel):
    name: str
    url: Optional[str] = None
    engagement_score: int = 0

class TrendPredictionSchema(BaseModel):
    phase: str  # "emerging", "growth", "peak", "decline"
    confidence: float
    estimated_peak: Optional[datetime] = None
    longevity_days: int = 30
    growth_rate: float = 0.0

class TrendAnalysisResponse(BaseModel):
    title: str
    description: str
    category: str
    keywords: List[str] = []
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    sources: List[TrendSourceSchema] = []
    source_count: int = 0
    prediction: Optional[TrendPredictionSchema] = None
    relevance_score: int = 0
    audience_match: List[str] = []
    content_opportunities: List[str] = []
    related_trends: List[str] = []
    geographic_scope: str = "global"
    industry_impact: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TrendBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    score: int = 0
    source: str
    url: Optional[str] = None

class TrendResponse(TrendBase):
    id: str
    organization_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ContentFromTrendRequest(BaseModel):
    trend_title: str
    trend_description: str
    content_type: str  # "blog", "social", "email", "linkedin", "twitter"
    keywords: List[str] = []

class ContentFromTrendResponse(BaseModel):
    title: str
    content: str
    suggested_hashtags: List[str] = []
    tone: str
    cta: Optional[str] = None
    target_audience: Optional[str] = None

# --- Endpoints ---

@router.get("/", response_model=List[TrendResponse])
async def list_trends(
    organization_id: str,
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """List trends for an organization."""
    query = select(Trend).where(Trend.organization_id == organization_id)
    
    if category and category != "All":
        query = query.where(Trend.category == category)
        
    query = query.order_by(desc(Trend.score))
    
    result = await session.execute(query)
    trends = result.scalars().all()
    
    # If no trends found, trigger a refresh automatically
    if not trends:
        trends = await _refresh_trends_internal(organization_id, session)
        
    return trends


class TrendCreate(BaseModel):
    """Schema for creating a trend manually."""
    title: str
    description: Optional[str] = None
    category: str
    score: int = 0
    source: str = "manual"
    url: Optional[str] = None


class TrendUpdate(BaseModel):
    """Schema for updating a trend."""
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    score: Optional[int] = None
    source: Optional[str] = None
    url: Optional[str] = None


@router.post("/", response_model=TrendResponse)
async def create_trend(
    trend_data: TrendCreate,
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new trend manually."""
    trend = Trend(
        organization_id=organization_id,
        title=trend_data.title,
        description=trend_data.description,
        category=trend_data.category,
        score=trend_data.score,
        source=trend_data.source,
        url=trend_data.url
    )
    session.add(trend)
    await session.commit()
    await session.refresh(trend)
    return trend


@router.get("/analyzed", response_model=List[TrendAnalysisResponse])
async def list_analyzed_trends(
    organization_id: str,
    category: Optional[str] = None,
    min_relevance: int = Query(0, ge=0, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get AI-analyzed trends with predictions and insights.
    
    This endpoint provides comprehensive trend analysis including:
    - Sentiment analysis
    - Lifecycle predictions (emerging/growth/peak/decline)
    - Content opportunities
    - Relevance scoring
    """
    # Get industry and brand context from knowledge base
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()
    
    industry = "General Business"
    organization_context = {}
    
    if kb:
        if kb.market_data:
            industry = kb.market_data.get("industry", "General Business")
        if kb.brand_data:
            organization_context = {
                "name": kb.brand_data.get("name", ""),
                "description": kb.brand_data.get("description", ""),
                "voice": kb.brand_data.get("voice", {})
            }
    
    # Use the new trend analyzer
    analyzer = TrendAnalyzer()
    try:
        analyzed_trends = await analyzer.analyze_trends(
            industry=industry,
            organization_context=organization_context
        )
    finally:
        await analyzer.close()
    
    # Filter by relevance if specified
    if min_relevance > 0:
        analyzed_trends = [t for t in analyzed_trends if t.relevance_score >= min_relevance]
    
    # Filter by category if specified
    if category and category != "All":
        analyzed_trends = [t for t in analyzed_trends if t.category.lower() == category.lower()]
    
    # Convert to response schema
    response = []
    for trend in analyzed_trends:
        response.append(TrendAnalysisResponse(
            title=trend.title,
            description=trend.description,
            category=trend.category,
            keywords=trend.keywords,
            sentiment=trend.sentiment,
            sentiment_score=trend.sentiment_score,
            sources=[TrendSourceSchema(**s.__dict__) for s in trend.sources],
            source_count=trend.source_count,
            prediction=TrendPredictionSchema(**trend.prediction.__dict__) if trend.prediction else None,
            relevance_score=trend.relevance_score,
            audience_match=trend.audience_match,
            content_opportunities=trend.content_opportunities,
            related_trends=trend.related_trends,
            geographic_scope=trend.geographic_scope,
            industry_impact=trend.industry_impact,
            created_at=trend.created_at
        ))
    
    return response

@router.post("/refresh", response_model=List[TrendResponse])
async def refresh_trends(
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Refresh trends from external sources."""
    return await _refresh_trends_internal(organization_id, session)

async def _refresh_trends_internal(
    organization_id: str,
    session: AsyncSession
) -> List[Trend]:
    """Internal function to refresh trends."""
    # Get industry from knowledge base
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()
    
    industry = "General Business"
    if kb and kb.market_data:
        industry = kb.market_data.get("industry", "General Business")
        
    # Scan for new trends
    new_trends_data = await trend_scanner.scan_trends(industry)
    
    # Clear old trends (optional: could keep history)
    delete_stmt = delete(Trend).where(Trend.organization_id == organization_id)
    await session.execute(delete_stmt)
    
    # Save new trends
    saved_trends = []
    for t_data in new_trends_data:
        trend = Trend(
            organization_id=organization_id,
            title=t_data["title"],
            description=t_data["description"],
            category=t_data["category"],
            score=t_data["score"],
            source=t_data["source"],
            url=t_data.get("url")
        )
        session.add(trend)
        saved_trends.append(trend)
        
    await session.commit()
    
    # Refresh objects to get IDs
    for t in saved_trends:
        await session.refresh(t)
        
    return saved_trends

@router.post("/create-content", response_model=ContentFromTrendResponse)
async def create_content_from_trend(
    request: ContentFromTrendRequest,
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate content from a trend.
    
    Creates blog posts, social media content, emails, etc.
    based on trending topics with brand voice integration.
    """
    # Get brand voice from knowledge base
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()
    
    brand_voice = None
    if kb and kb.brand_data:
        brand_voice = kb.brand_data.get("voice")
    
    # Create a trend analysis object from request
    from ..services.trends.trend_analyzer import TrendAnalysisLegacy
    
    trend = TrendAnalysisLegacy(
        title=request.trend_title,
        description=request.trend_description,
        category="User Selected",
        keywords=request.keywords,
        sentiment="neutral",
        prediction=TrendPrediction(phase="growth", confidence=0.8, growth_rate=10.0)
    )
    
    # Generate content
    analyzer = TrendAnalyzer()
    try:
        content = await analyzer.generate_content_from_trend(
            trend=trend,
            content_type=request.content_type,
            brand_voice=brand_voice
        )
    finally:
        await analyzer.close()
    
    return ContentFromTrendResponse(**content)

@router.get("/categories")
async def list_trend_categories() -> List[str]:
    """Get available trend categories."""
    return [
        "All",
        "Technology",
        "Business",
        "Marketing",
        "Finance",
        "Product",
        "Leadership",
        "Content Strategy",
        "Social Media",
        "Search Trends",
        "Discussion"
    ]

@router.get("/{trend_id}", response_model=TrendResponse)
async def get_trend(
    trend_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific trend by ID."""
    query = select(Trend).where(Trend.id == trend_id)
    result = await session.execute(query)
    trend = result.scalars().first()
    
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    
    return trend


@router.put("/{trend_id}", response_model=TrendResponse)
async def update_trend(
    trend_id: str,
    trend_data: TrendUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Update a trend."""
    query = select(Trend).where(Trend.id == trend_id)
    result = await session.execute(query)
    trend = result.scalars().first()
    
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    
    # Update only provided fields
    update_data = trend_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(trend, field, value)
    
    await session.commit()
    await session.refresh(trend)
    
    return trend


@router.delete("/{trend_id}")
async def delete_trend(
    trend_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a trend."""
    query = select(Trend).where(Trend.id == trend_id)
    result = await session.execute(query)
    trend = result.scalars().first()
    
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    
    await session.delete(trend)
    await session.commit()
    
    return {"message": "Trend deleted successfully"}
