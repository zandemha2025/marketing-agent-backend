"""
Schemas for onboarding endpoints.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    """Request to start onboarding for a new organization."""
    domain: str = Field(..., description="Company website domain (e.g., acme.com)")
    company_name: Optional[str] = Field(None, description="Company name (auto-detected if not provided)")


class OnboardingProgress(BaseModel):
    """Current progress of onboarding."""
    stage: str = Field(..., description="Current stage of onboarding")
    progress: float = Field(..., ge=0, le=1, description="Progress percentage (0-1)")
    message: str = Field(..., description="Human-readable status message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class OnboardingStatus(BaseModel):
    """Status response for onboarding."""
    organization_id: str
    status: str  # pending, in_progress, complete, failed
    progress: OnboardingProgress
    can_resume: bool = Field(False, description="Whether onboarding can be resumed")


class VisualIdentity(BaseModel):
    """Brand visual identity."""
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_colors: List[str] = Field(default_factory=list)
    fonts: Dict[str, str] = Field(default_factory=dict)
    image_style: Optional[str] = None


class BrandVoice(BaseModel):
    """Brand voice characteristics."""
    tone: List[str] = Field(default_factory=list)
    personality: Optional[str] = None
    vocabulary: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)
    sample_phrases: List[str] = Field(default_factory=list)


class BrandProfile(BaseModel):
    """Complete brand profile from onboarding."""
    name: str
    domain: str
    tagline: Optional[str] = None
    description: Optional[str] = None
    visual_identity: VisualIdentity = Field(default_factory=VisualIdentity)
    voice: BrandVoice = Field(default_factory=BrandVoice)
    values: List[str] = Field(default_factory=list)
    mission: Optional[str] = None


class CompetitorProfile(BaseModel):
    """Competitor information."""
    name: str
    domain: Optional[str] = None
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    positioning: Optional[str] = None
    key_differentiators: List[str] = Field(default_factory=list)


class MarketTrend(BaseModel):
    """Market trend information."""
    trend: str
    relevance: str  # high, medium, low
    opportunity: Optional[str] = None


class MarketProfile(BaseModel):
    """Market intelligence from onboarding."""
    industry: Optional[str] = None
    competitors: List[CompetitorProfile] = Field(default_factory=list)
    trends: List[MarketTrend] = Field(default_factory=list)
    market_position: Optional[str] = None
    opportunities: List[str] = Field(default_factory=list)
    threats: List[str] = Field(default_factory=list)


class AudienceSegment(BaseModel):
    """Target audience segment."""
    name: str
    size: str  # primary, secondary
    demographics: Dict[str, Any] = Field(default_factory=dict)
    psychographics: Dict[str, Any] = Field(default_factory=dict)
    pain_points: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    preferred_channels: List[str] = Field(default_factory=list)
    content_preferences: List[str] = Field(default_factory=list)


class AudienceProfile(BaseModel):
    """Audience insights from onboarding."""
    segments: List[AudienceSegment] = Field(default_factory=list)


class OnboardingResult(BaseModel):
    """Complete onboarding result for presentation."""
    organization_id: str
    brand: BrandProfile
    market: MarketProfile
    audiences: AudienceProfile
    offerings: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    research_status: str
    pages_analyzed: int = 0
    duration_seconds: float = 0


class OnboardingUpdateRequest(BaseModel):
    """Request to update onboarding results."""
    section: str = Field(..., description="Section to update: brand, market, audiences, offerings")
    data: Dict[str, Any] = Field(..., description="Updated data for the section")
