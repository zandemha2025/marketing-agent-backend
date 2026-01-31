"""
Content generation API endpoints.

Includes:
- Press release generation
- Email/newsletter generation
- Article generation
- Landing page generation
- Interview processing
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, validator

from ..core.database import get_session
from .auth import get_current_active_user
from ..models.user import User
from ..models.knowledge_base import KnowledgeBase
from ..services.content.press_release import PressReleaseGenerator, PressRelease
from ..services.content.interview_processor import InterviewProcessor, ProcessedInterview
from ..services.content.article_generator import ArticleGenerator, GeneratedContent
from ..services.content.email_generator import EmailGenerator, GeneratedEmail, SubjectLineVariant
from ..services.content.mjml_templates import MJMLTemplateSystem
from ..services.content.landing_page_generator import LandingPageGenerator, LandingPageContent, LandingPageType
from ..services.content.nextjs_scaffolder import scaffold_nextjs_project

router = APIRouter(prefix="/content", tags=["Content Generation"])

# --- Press Release Schemas ---

class PressReleaseRequest(BaseModel):
    topic: str = Field(..., description="Main topic/news of the press release")
    key_points: List[str] = Field(default_factory=list, description="Key points to cover")
    executive_name: Optional[str] = Field(None, description="Executive name for quotes")
    executive_title: Optional[str] = Field(None, description="Executive title")
    target_audience: Optional[str] = Field(None, description="Target audience")
    tone: str = Field("professional", description="Tone: professional, excited, serious")
    
class QuoteRequest(BaseModel):
    topic: str
    angle: str
    executive_name: str
    executive_title: str

class HeadlineVariantsRequest(BaseModel):
    topic: str
    key_point: str
    count: int = Field(5, ge=1, le=10)

class PressReleaseResponse(BaseModel):
    headline: str
    subheadline: Optional[str]
    dateline: str
    lead: str
    body: List[str]
    quotes: List[Dict[str, str]]
    boilerplate: str
    contact_info: Dict[str, str]
    word_count: int
    html: str
    plaintext: str

# --- Interview Schemas ---

class ProcessInterviewRequest(BaseModel):
    text: str = Field(..., description="Interview text to process")
    title: str = Field(..., description="Interview title")
    speaker_names: Optional[List[str]] = Field(None, description="Optional speaker names")

class InterviewInsightSchema(BaseModel):
    category: str
    content: str
    context: str
    importance: int

class InterviewSegmentSchema(BaseModel):
    speaker: str
    text: str
    timestamp: Optional[float]

class ProcessedInterviewResponse(BaseModel):
    title: str
    segments: List[InterviewSegmentSchema]
    insights: List[InterviewInsightSchema]
    key_quotes: List[str]
    topics: List[str]
    summary: str
    word_count: int
    duration_minutes: Optional[float]

# --- Article Generation Schemas ---

class GenerateFromInterviewRequest(BaseModel):
    interview_text: str = Field(..., description="Raw interview text")
    interview_title: str = Field(..., description="Interview title")
    formats: List[str] = Field(default_factory=lambda: ["blog", "linkedin", "twitter", "email"], 
                               description="Formats to generate: blog, linkedin, twitter, press_release, email")
    target_audience: Optional[str] = None

class GeneratedContentResponse(BaseModel):
    format: str
    title: str
    content: str
    word_count: int
    estimated_read_time: int
    suggested_hashtags: List[str]
    key_takeaways: List[str]

class MultiFormatContentResponse(BaseModel):
    contents: Dict[str, GeneratedContentResponse]

# --- Endpoints ---

@router.post("/press-release", response_model=PressReleaseResponse)
async def generate_press_release(
    request: PressReleaseRequest,
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a professional press release.
    
    Creates a press release in standard AP format with:
    - Compelling headline and subheadline
    - Proper dateline
    - Strong lead paragraph
    - Informative body sections
    - AI-generated executive quotes
    - Company boilerplate
    """
    # Get company info from knowledge base
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Organization knowledge base not found")
    
    # Build company info
    company_info = {
        "name": kb.brand_data.get("name", "Company"),
        "description": kb.brand_data.get("description", ""),
        "website": kb.brand_data.get("website", ""),
        "location": kb.brand_data.get("location", "City, State"),
        "contact": kb.brand_data.get("contact", {})
    }
    
    # Get brand voice
    brand_voice = kb.brand_data.get("voice")
    
    # Generate press release
    generator = PressReleaseGenerator()
    try:
        pr = await generator.generate(
            topic=request.topic,
            key_points=request.key_points,
            company_info=company_info,
            brand_voice=brand_voice,
            executive_name=request.executive_name,
            executive_title=request.executive_title,
            target_audience=request.target_audience,
            tone=request.tone
        )
        
        return PressReleaseResponse(
            headline=pr.headline,
            subheadline=pr.subheadline,
            dateline=pr.dateline,
            lead=pr.lead,
            body=pr.body,
            quotes=pr.quotes,
            boilerplate=pr.boilerplate,
            contact_info=pr.contact_info,
            word_count=pr.word_count,
            html=pr.to_html(),
            plaintext=pr.to_plaintext()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate press release: {str(e)}")

@router.post("/press-release/headlines")
async def generate_headline_variants(
    request: HeadlineVariantsRequest,
    organization_id: str
):
    """
    Generate multiple headline options for A/B testing.
    """
    generator = PressReleaseGenerator()
    try:
        headlines = await generator.generate_headline_variants(
            topic=request.topic,
            key_point=request.key_point,
            count=request.count
        )
        return {"headlines": headlines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate headlines: {str(e)}")

@router.post("/press-release/quote")
async def generate_quote(
    request: QuoteRequest,
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a natural-sounding executive quote.
    """
    # Get brand voice
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()
    brand_voice = kb.brand_data.get("voice") if kb else None
    
    generator = PressReleaseGenerator()
    try:
        quote = await generator.generate_quote(
            topic=request.topic,
            angle=request.angle,
            executive_name=request.executive_name,
            executive_title=request.executive_title,
            brand_voice=brand_voice
        )
        return quote
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quote: {str(e)}")

# --- Interview Processing Endpoints ---

@router.post("/interview/process", response_model=ProcessedInterviewResponse)
async def process_interview(
    request: ProcessInterviewRequest,
    organization_id: str
):
    """
    Process an interview transcript into structured content.
    
    Extracts:
    - Speaker segments
    - Key insights
    - Notable quotes
    - Topics discussed
    - Summary
    """
    processor = InterviewProcessor()
    try:
        result = await processor.process_text_interview(
            text=request.text,
            title=request.title,
            speaker_names=request.speaker_names
        )
        
        return ProcessedInterviewResponse(
            title=result.title,
            segments=[
                InterviewSegmentSchema(
                    speaker=s.speaker,
                    text=s.text,
                    timestamp=s.timestamp
                ) for s in result.segments
            ],
            insights=[
                InterviewInsightSchema(
                    category=i.category,
                    content=i.content,
                    context=i.context,
                    importance=i.importance
                ) for i in result.insights
            ],
            key_quotes=result.key_quotes,
            topics=result.topics,
            summary=result.summary,
            word_count=result.word_count,
            duration_minutes=result.duration_minutes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process interview: {str(e)}")

@router.post("/interview/generate-content", response_model=MultiFormatContentResponse)
async def generate_content_from_interview(
    request: GenerateFromInterviewRequest,
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate multiple content formats from an interview.
    
    Creates:
    - Blog articles
    - LinkedIn posts
    - Twitter threads
    - Press releases
    - Email newsletters
    
    All from a single interview input.
    """
    # First process the interview
    processor = InterviewProcessor()
    try:
        interview = await processor.process_text_interview(
            text=request.interview_text,
            title=request.interview_title
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process interview: {str(e)}")
    
    # Get brand voice from knowledge base
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()
    brand_voice = kb.brand_data.get("voice") if kb else None
    
    # Generate content in requested formats
    generator = ArticleGenerator()
    try:
        contents = await generator.generate_all_formats(
            interview=interview,
            brand_voice=brand_voice,
            target_audience=request.target_audience
        )
        
        # Filter to requested formats
        filtered_contents = {
            fmt: GeneratedContentResponse(
                format=c.format,
                title=c.title,
                content=c.content,
                word_count=c.word_count,
                estimated_read_time=c.estimated_read_time,
                suggested_hashtags=c.suggested_hashtags,
                key_takeaways=c.key_takeaways
            )
            for fmt, c in contents.items()
            if fmt in request.formats
        }
        
        return MultiFormatContentResponse(contents=filtered_contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate content: {str(e)}")

# --- Email Generation Endpoints ---

VALID_EMAIL_TYPES = {"welcome", "newsletter", "promotional", "announcement", "nurture", "transactional"}
VALID_SEQUENCE_TYPES = {"welcome", "nurture", "onboarding", "re_engagement"}

# --- New API Spec Request/Response Models ---

class EmailGenerateRequestV2(BaseModel):
    """Request model matching the API spec for POST /api/content/email/generate"""
    campaign_id: Optional[str] = Field(None, description="Campaign ID")
    type: str = Field(..., description="Email type: promotional, welcome, nurture, newsletter, transactional")
    subject: str = Field(..., description="Email subject line")
    headline: str = Field(..., description="Main headline")
    body_content: str = Field(..., description="Main message content")
    cta_text: str = Field(..., description="Call-to-action button text")
    cta_url: str = Field(..., description="Call-to-action URL")
    brand_colors: Optional[Dict[str, str]] = Field(None, description="Brand colors, e.g., {'primary': '#007bff'}")

    @validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_EMAIL_TYPES:
            raise ValueError(f"type must be one of: {', '.join(sorted(VALID_EMAIL_TYPES))}")
        return v


class EmailGenerateResponseV2(BaseModel):
    """Response model matching the API spec"""
    success: bool
    email_id: str
    html_content: str
    text_content: str
    subject_lines: List[str]
    preview_text: str
    preview_url: Optional[str] = None


class EmailSequenceRequestV2(BaseModel):
    """Request model matching the API spec for POST /api/content/email/sequence"""
    campaign_id: Optional[str] = Field(None, description="Campaign ID")
    sequence_type: str = Field(..., description="Sequence type: welcome, nurture, onboarding, re_engagement")
    num_emails: int = Field(5, ge=1, le=10, description="Number of emails in the sequence")
    brand_data: Optional[Dict[str, Any]] = Field(None, description="Brand data for styling")

    @validator("sequence_type")
    @classmethod
    def validate_sequence_type(cls, v: str) -> str:
        if v not in VALID_SEQUENCE_TYPES:
            raise ValueError(f"sequence_type must be one of: {', '.join(sorted(VALID_SEQUENCE_TYPES))}")
        return v


class EmailSequenceEmailV2(BaseModel):
    """Individual email in a sequence"""
    day: int
    subject: str
    html_content: str
    text_content: str


class EmailSequenceResponseV2(BaseModel):
    """Response model matching the API spec"""
    success: bool
    sequence_id: str
    emails: List[EmailSequenceEmailV2]
    timing_schedule: List[int]


# --- Legacy Request/Response Models (kept for backward compatibility) ---

class EmailGenerateRequest(BaseModel):
    email_type: str = Field(..., description="Type: welcome, newsletter, promotional, announcement, nurture, transactional")
    topic: str = Field(..., description="Main topic of the email")
    key_points: List[str] = Field(default_factory=list, description="Key points to include")
    target_audience: Optional[str] = None
    tone: str = Field("professional", description="professional, casual, enthusiastic")

    @validator("email_type")
    @classmethod
    def validate_email_type(cls, v: str) -> str:
        if v not in VALID_EMAIL_TYPES:
            raise ValueError(f"email_type must be one of: {', '.join(sorted(VALID_EMAIL_TYPES))}")
        return v

class SubjectVariantRequest(BaseModel):
    topic: str
    count: int = Field(5, ge=1, le=10)

class GeneratedEmailResponse(BaseModel):
    subject: str
    mjml: str
    html: str
    plaintext: str
    metadata: Dict[str, Any]

class SubjectVariantResponse(BaseModel):
    text: str
    predicted_open_rate: float
    emoji: bool
    urgency_level: str


# --- New API Endpoints (matching spec) ---

@router.post("/email/generate", response_model=EmailGenerateResponseV2)
async def generate_email_v2(
    request: EmailGenerateRequestV2,
    organization_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a complete email with HTML and plain text versions.
    
    Creates:
    - Responsive HTML email (works in all email clients)
    - Plain text fallback
    - Multiple subject line variations for A/B testing
    - Preview text for inbox display
    - Saves email to outputs/emails/
    
    Request:
    ```json
    {
      "campaign_id": "uuid",
      "type": "promotional",
      "subject": "Your Amazing Offer",
      "headline": "Don't Miss Out!",
      "body_content": "Main message content...",
      "cta_text": "Shop Now",
      "cta_url": "https://example.com/shop",
      "brand_colors": {"primary": "#007bff"}
    }
    ```
    """
    # Get brand data from knowledge base if organization_id provided
    brand_colors = request.brand_colors
    if organization_id and not brand_colors:
        query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
        result = await session.execute(query)
        kb = result.scalars().first()
        if kb:
            brand_colors = {
                "primary": kb.brand_data.get("visual_identity", {}).get("primary_color", "#3b82f6")
            }
    
    generator = EmailGenerator()
    try:
        result = await generator.generate_complete_email(
            email_type=request.type,
            subject=request.subject,
            headline=request.headline,
            body_content=request.body_content,
            cta_text=request.cta_text,
            cta_url=request.cta_url,
            brand_colors=brand_colors,
            campaign_id=request.campaign_id,
            save_to_file=True,
        )
        
        return EmailGenerateResponseV2(
            success=True,
            email_id=result["email_id"],
            html_content=result["html_content"],
            text_content=result["text_content"],
            subject_lines=result["subject_lines"],
            preview_text=result["preview_text"],
            preview_url=result["preview_url"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email: {str(e)}")


@router.post("/email/sequence", response_model=EmailSequenceResponseV2)
async def generate_email_sequence_v2(
    request: EmailSequenceRequestV2,
    organization_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate an email sequence (drip campaign).
    
    Creates a multi-email sequence with:
    - Unique content for each email
    - Timing schedule (Day 1, Day 3, Day 7, etc.)
    - HTML and plain text versions
    - Saves sequence to outputs/emails/sequences/
    
    Request:
    ```json
    {
      "campaign_id": "uuid",
      "sequence_type": "welcome",
      "num_emails": 5,
      "brand_data": {...}
    }
    ```
    """
    from ..services.content.email_sequence import EmailSequenceGenerator, SequenceType
    
    # Get brand data from knowledge base if organization_id provided
    brand_data = request.brand_data
    brand_voice = None
    if organization_id:
        query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
        result = await session.execute(query)
        kb = result.scalars().first()
        if kb:
            brand_voice = kb.brand_data.get("voice")
            if not brand_data:
                brand_data = {
                    "primary_color": kb.brand_data.get("visual_identity", {}).get("primary_color", "#3b82f6"),
                    "font_family": kb.brand_data.get("visual_identity", {}).get("fonts", {}).get("body", "Arial")
                }
    
    generator = EmailSequenceGenerator()
    try:
        sequence_type = SequenceType(request.sequence_type)
        result = await generator.generate_sequence(
            sequence_type=sequence_type,
            num_emails=request.num_emails,
            brand_data=brand_data,
            brand_voice=brand_voice,
            campaign_id=request.campaign_id,
            save_to_file=True,
        )
        
        return EmailSequenceResponseV2(
            success=True,
            sequence_id=result.sequence_id,
            emails=[
                EmailSequenceEmailV2(
                    day=e.day,
                    subject=e.subject,
                    html_content=e.html_content,
                    text_content=e.text_content,
                )
                for e in result.emails
            ],
            timing_schedule=result.timing_schedule,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email sequence: {str(e)}")


# --- Legacy Endpoints (kept for backward compatibility) ---

@router.post("/email/generate-legacy", response_model=GeneratedEmailResponse)
async def generate_email_legacy(
    request: EmailGenerateRequest,
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a complete email with MJML template (legacy endpoint).
    
    Creates:
    - AI-generated content matching brand voice
    - MJML source code
    - HTML for sending
    - Plaintext fallback
    """
    # Get brand data from knowledge base
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()
    
    brand_voice = kb.brand_data.get("voice") if kb else None
    brand_data = {
        "primary_color": kb.brand_data.get("visual_identity", {}).get("primary_color", "#3b82f6"),
        "font_family": kb.brand_data.get("visual_identity", {}).get("fonts", {}).get("body", "Arial")
    } if kb else None
    
    generator = EmailGenerator()
    try:
        email = await generator.generate(
            email_type=request.email_type,
            topic=request.topic,
            key_points=request.key_points,
            brand_voice=brand_voice,
            brand_data=brand_data,
            target_audience=request.target_audience,
            tone=request.tone
        )
        
        return GeneratedEmailResponse(
            subject=email.subject,
            mjml=email.mjml,
            html=email.html,
            plaintext=email.plaintext,
            metadata=email.metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email: {str(e)}")

@router.post("/email/subject-variants", response_model=List[SubjectVariantResponse])
async def generate_subject_variants(
    request: SubjectVariantRequest,
    organization_id: str
):
    """
    Generate subject line variants for A/B testing.
    """
    generator = EmailGenerator()
    try:
        variants = await generator.generate_subject_variants(
            topic=request.topic,
            count=request.count
        )
        
        return [
            SubjectVariantResponse(
                text=v.text,
                predicted_open_rate=v.predicted_open_rate,
                emoji=v.emoji,
                urgency_level=v.urgency_level
            )
            for v in variants
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate subject variants: {str(e)}")


# --- Legacy Sequence Models and Endpoint ---

class EmailSequenceRequest(BaseModel):
    campaign_id: str = Field(..., description="Campaign ID")
    sequence_type: str = Field(..., description="Sequence type: welcome, nurture, onboarding, re_engagement")
    num_emails: int = Field(3, ge=1, le=10, description="Number of emails in the sequence")
    organization_id: str = Field(..., description="Organization ID")

class EmailSequenceItem(BaseModel):
    subject: str
    html: str
    plaintext: str
    send_day: int

class EmailSequenceResponse(BaseModel):
    campaign_id: str
    sequence_type: str
    emails: List[EmailSequenceItem]

SEQUENCE_SCHEDULES = {
    "welcome": [1, 3, 7, 14, 21],
    "nurture": [1, 4, 8, 12, 18, 25],
    "onboarding": [1, 2, 5, 10, 15],
    "re_engagement": [1, 3, 7, 14, 30],
}

@router.post("/email/sequence", response_model=EmailSequenceResponse)
async def generate_email_sequence(
    request: EmailSequenceRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a sequence of emails for a campaign.

    Creates a multi-email sequence (e.g., welcome series) where each email
    has a subject, HTML body, plaintext fallback, and scheduled send day.
    Uses the email generator service and OpenRouter LLM.
    """
    # Get brand data from knowledge base
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == request.organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()

    brand_voice = kb.brand_data.get("voice") if kb else None
    brand_data = {
        "primary_color": kb.brand_data.get("visual_identity", {}).get("primary_color", "#3b82f6"),
        "font_family": kb.brand_data.get("visual_identity", {}).get("fonts", {}).get("body", "Arial")
    } if kb else None

    # Determine send day schedule
    schedule = SEQUENCE_SCHEDULES.get(request.sequence_type, SEQUENCE_SCHEDULES["nurture"])
    send_days = schedule[:request.num_emails]
    # Extend if more emails requested than schedule has entries
    while len(send_days) < request.num_emails:
        send_days.append(send_days[-1] + 7)

    # Map sequence type to email type
    email_type_map = {
        "welcome": "welcome",
        "nurture": "nurture",
        "onboarding": "welcome",
        "re_engagement": "promotional",
    }
    email_type = email_type_map.get(request.sequence_type, "nurture")

    generator = EmailGenerator()
    emails = []
    try:
        for i, day in enumerate(send_days):
            topic = f"{request.sequence_type.replace('_', ' ').title()} - Email {i + 1} of {request.num_emails} (Day {day})"
            key_points = [
                f"This is email {i + 1} in a {request.sequence_type.replace('_', ' ')} sequence",
                f"Scheduled to send on day {day}",
            ]

            email = await generator.generate(
                email_type=email_type,
                topic=topic,
                key_points=key_points,
                brand_voice=brand_voice,
                brand_data=brand_data,
                target_audience=None,
                tone="professional"
            )

            emails.append(EmailSequenceItem(
                subject=email.subject,
                html=email.html,
                plaintext=email.plaintext,
                send_day=day,
            ))

        return EmailSequenceResponse(
            campaign_id=request.campaign_id,
            sequence_type=request.sequence_type,
            emails=emails,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate email sequence: {str(e)}")

@router.get("/email/templates")
async def list_email_templates():
    """List available email templates."""
    system = MJMLTemplateSystem()
    return system.get_available_templates()

# --- Landing Page Generation Endpoints ---

class LandingPageGenerateRequest(BaseModel):
    goal: str = Field(..., description="Campaign goal: lead generation, product launch, etc.")
    target_audience: str = Field(..., description="Target audience description")
    key_benefits: List[str] = Field(default_factory=list, description="Key benefits to highlight")
    sections: Optional[List[str]] = Field(None, description="Specific sections to include")
    output_format: str = Field("all", description="html, react, nextjs, or all")

class LandingPageSectionResponse(BaseModel):
    type: str
    title: str
    content: Dict[str, Any]

class LandingPageResponse(BaseModel):
    title: str
    description: str
    sections: List[LandingPageSectionResponse]
    html_tailwind: Optional[str] = None
    react_component: Optional[str] = None
    nextjs_project: Optional[Dict[str, str]] = None
    seo_title: str
    seo_description: str
    keywords: List[str]

@router.post("/landing-page/generate", response_model=LandingPageResponse)
async def generate_landing_page(
    request: LandingPageGenerateRequest,
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a complete landing page in multiple formats.
    
    Output formats:
    - html: HTML + Tailwind CSS
    - react: React component
    - nextjs: Full Next.js project
    - all: All formats
    """
    # Get brand data from knowledge base
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()
    
    brand_voice = kb.brand_data.get("voice") if kb else None
    brand_data = {
        "primary_color": kb.brand_data.get("visual_identity", {}).get("primary_color", "#3b82f6"),
        "font_family": kb.brand_data.get("visual_identity", {}).get("fonts", {}).get("body", "Inter")
    } if kb else {
        "primary_color": "#3b82f6",
        "font_family": "Inter"
    }
    
    generator = LandingPageGenerator()
    try:
        # Infer page type from goal
        goal_lower = request.goal.lower()
        if "lead" in goal_lower or "capture" in goal_lower:
            page_type = LandingPageType.LEAD_CAPTURE
        elif "event" in goal_lower:
            page_type = LandingPageType.EVENT
        elif "webinar" in goal_lower:
            page_type = LandingPageType.WEBINAR
        elif "coming soon" in goal_lower or "launch" in goal_lower:
            page_type = LandingPageType.COMING_SOON
        elif "compar" in goal_lower:
            page_type = LandingPageType.COMPARISON
        else:
            page_type = LandingPageType.PRODUCT

        # Build brand_context from brand_data and brand_voice
        brand_context = {**brand_data}
        if brand_voice:
            brand_context["voice"] = brand_voice

        landing_page = await generator.generate(
            page_type=page_type,
            product_name=brand_data.get("name", request.goal),
            product_description=request.goal,
            target_audience=request.target_audience,
            brand_context=brand_context,
            sections_requested=request.sections,
            key_benefits=request.key_benefits
        )

        # Map sections to response schema
        sections_response = [
            LandingPageSectionResponse(
                type=s.section_type,
                title=s.headline,
                content={
                    "subheadline": s.subheadline,
                    **(s.content or {}),
                    "cta_text": s.cta_text,
                    "cta_url": s.cta_url,
                    "image_prompt": s.image_prompt,
                }
            )
            for s in landing_page.sections
        ]

        # Build response using correct LandingPageContent attributes
        response_data = {
            "title": landing_page.title,
            "description": landing_page.meta_description,
            "sections": sections_response,
            "seo_title": landing_page.og_title,
            "seo_description": landing_page.og_description,
            "keywords": landing_page.keywords
        }

        if request.output_format in ["html", "all"]:
            response_data["html_tailwind"] = landing_page.to_html(brand_data)
        if request.output_format in ["react", "all"]:
            components = landing_page.to_nextjs_components(brand_data)
            # Combine all component files into a single string for the response
            response_data["react_component"] = components.get(
                "components/LandingPage.tsx",
                "\n\n".join(components.values())
            )
        if request.output_format in ["nextjs", "all"]:
            response_data["nextjs_project"] = landing_page.to_nextjs_components(brand_data)

        return LandingPageResponse(**response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate landing page: {str(e)}")

@router.post("/landing-page/scaffold")
async def scaffold_landing_page_project(
    request: LandingPageGenerateRequest,
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Scaffold a complete Next.js project for the landing page.

    Returns a complete project structure ready for deployment.
    """
    # First generate the landing page
    query = select(KnowledgeBase).where(KnowledgeBase.organization_id == organization_id)
    result = await session.execute(query)
    kb = result.scalars().first()

    brand_voice = kb.brand_data.get("voice") if kb else None
    brand_data = {
        "primary_color": kb.brand_data.get("visual_identity", {}).get("primary_color", "#3b82f6"),
        "font_family": kb.brand_data.get("visual_identity", {}).get("fonts", {}).get("body", "Inter")
    } if kb else {
        "primary_color": "#3b82f6",
        "font_family": "Inter"
    }

    # Infer page type from goal
    goal_lower = request.goal.lower()
    if "lead" in goal_lower or "capture" in goal_lower:
        page_type = LandingPageType.LEAD_CAPTURE
    elif "event" in goal_lower:
        page_type = LandingPageType.EVENT
    elif "webinar" in goal_lower:
        page_type = LandingPageType.WEBINAR
    elif "coming soon" in goal_lower or "launch" in goal_lower:
        page_type = LandingPageType.COMING_SOON
    elif "compar" in goal_lower:
        page_type = LandingPageType.COMPARISON
    else:
        page_type = LandingPageType.PRODUCT

    brand_context = {**brand_data}
    if brand_voice:
        brand_context["voice"] = brand_voice

    generator = LandingPageGenerator()
    try:
        landing_page = await generator.generate(
            page_type=page_type,
            product_name=brand_data.get("name", request.goal),
            product_description=request.goal,
            target_audience=request.target_audience,
            brand_context=brand_context,
            sections_requested=request.sections,
            key_benefits=request.key_benefits
        )
        
        # Scaffold the Next.js project
        project_name = request.goal.lower().replace(' ', '-')[:20] + '-landing'
        project = scaffold_nextjs_project(
            project_name=project_name,
            landing_page_content=landing_page.to_dict(),
            brand_data=brand_data
        )
        
        return {
            "project_name": project.name,
            "files": project.files,
            "instructions": {
                "setup": f"1. Create directory: {project.name}\n2. Create files as listed\n3. Run: npm install\n4. Run: npm run dev",
                "deploy_vercel": "Connect to Vercel or run: vercel --prod",
                "deploy_netlify": "Connect to Netlify or drag 'dist' folder after build"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scaffold project: {str(e)}")


# --- Campaign-Based Landing Page Generation Endpoints ---

from ..services.content.static_site_builder import get_static_site_builder, LANDING_PAGES_DIR, SITES_DIR
from fastapi.responses import FileResponse
from pathlib import Path


class CampaignLandingPageRequest(BaseModel):
    """Request schema for campaign-based landing page generation."""
    campaign_id: str = Field(..., description="Campaign identifier")
    template: str = Field("product_launch", description="Template type: product_launch, lead_gen, event, webinar")
    headline: str = Field(..., description="Main headline")
    subheadline: str = Field(..., description="Supporting subheadline")
    cta_text: str = Field("Get Started", description="Call-to-action button text")
    cta_url: str = Field("#", description="Call-to-action URL")
    features: List[str] = Field(default_factory=list, description="List of features")
    testimonials: List[Dict[str, str]] = Field(default_factory=list, description="List of testimonials")
    brand_colors: Dict[str, str] = Field(
        default_factory=lambda: {"primary": "#007bff", "secondary": "#6c757d"},
        description="Brand color configuration"
    )


class CampaignLandingPageResponse(BaseModel):
    """Response schema for campaign-based landing page generation."""
    success: bool
    page_id: str
    html: str
    css: str
    preview_url: Optional[str] = None
    download_url: Optional[str] = None


class WebsiteGenerateRequest(BaseModel):
    """Request schema for website generation."""
    campaign_id: str = Field(..., description="Campaign identifier")
    pages: List[str] = Field(
        default_factory=lambda: ["home", "about", "contact", "product"],
        description="List of pages to generate"
    )
    brand_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Brand configuration including name, colors, etc."
    )


class WebsitePageResponse(BaseModel):
    """Response schema for a single website page."""
    page_id: str
    name: str
    html_length: int
    css_length: int
    js_length: int
    metadata: Dict[str, Any]
    created_at: str


class WebsiteGenerateResponse(BaseModel):
    """Response schema for website generation."""
    success: bool
    site_id: str
    pages: List[WebsitePageResponse]
    preview_url: Optional[str] = None
    download_url: Optional[str] = None


@router.post("/landing-page/campaign-generate", response_model=CampaignLandingPageResponse)
async def generate_campaign_landing_page(
    request: CampaignLandingPageRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a landing page based on campaign data.
    
    Creates a complete HTML/CSS landing page with:
    - Hero section with headline, subheadline, and CTA
    - Features section
    - Testimonials section
    - Responsive design
    - Brand colors applied
    
    Returns the generated HTML, CSS, and URLs for preview and download.
    """
    builder = get_static_site_builder()
    
    try:
        result = await builder.generate_landing_page(
            campaign_id=request.campaign_id,
            template=request.template,
            headline=request.headline,
            subheadline=request.subheadline,
            cta_text=request.cta_text,
            cta_url=request.cta_url,
            features=request.features,
            testimonials=request.testimonials,
            brand_colors=request.brand_colors,
            save_to_disk=True
        )
        
        return CampaignLandingPageResponse(
            success=result["success"],
            page_id=result["page_id"],
            html=result["html"],
            css=result["css"],
            preview_url=result.get("preview_url"),
            download_url=result.get("download_url")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate landing page: {str(e)}")


@router.post("/website/generate", response_model=WebsiteGenerateResponse)
async def generate_website(
    request: WebsiteGenerateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a complete multi-page website.
    
    Creates a static website with:
    - Multiple pages (home, about, contact, product, etc.)
    - Consistent navigation and footer
    - Global CSS and JavaScript
    - Responsive design
    - Brand colors and styling
    
    Returns the generated site with URLs for preview and download.
    """
    builder = get_static_site_builder()
    
    try:
        result = await builder.generate_website(
            campaign_id=request.campaign_id,
            pages=request.pages,
            brand_data=request.brand_data,
            save_to_disk=True
        )
        
        return WebsiteGenerateResponse(
            success=result["success"],
            site_id=result["site_id"],
            pages=[
                WebsitePageResponse(
                    page_id=p["page_id"],
                    name=p["name"],
                    html_length=p["html_length"],
                    css_length=p["css_length"],
                    js_length=p["js_length"],
                    metadata=p["metadata"],
                    created_at=p["created_at"]
                )
                for p in result["pages"]
            ],
            preview_url=result.get("preview_url"),
            download_url=result.get("download_url")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate website: {str(e)}")


@router.get("/landing-pages")
async def list_landing_pages(
    current_user: User = Depends(get_current_active_user)
):
    """List all generated landing pages."""
    builder = get_static_site_builder()
    return {"landing_pages": builder.list_landing_pages()}


@router.get("/landing-pages/{page_id}")
async def get_landing_page(
    page_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific landing page by ID."""
    builder = get_static_site_builder()
    page = builder.get_landing_page(page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Landing page not found")
    return page


@router.delete("/landing-pages/{page_id}")
async def delete_landing_page(
    page_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a landing page."""
    builder = get_static_site_builder()
    if builder.delete_landing_page(page_id):
        return {"success": True, "message": "Landing page deleted"}
    raise HTTPException(status_code=404, detail="Landing page not found")


@router.get("/websites")
async def list_websites(
    current_user: User = Depends(get_current_active_user)
):
    """List all generated websites."""
    builder = get_static_site_builder()
    return {"websites": builder.list_sites()}


@router.get("/websites/{site_id}")
async def get_website(
    site_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific website by ID."""
    builder = get_static_site_builder()
    site = builder.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    return site


@router.delete("/websites/{site_id}")
async def delete_website(
    site_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a website."""
    builder = get_static_site_builder()
    if builder.delete_site(site_id):
        return {"success": True, "message": "Website deleted"}
    raise HTTPException(status_code=404, detail="Website not found")


# --- Preview and Download Endpoints ---

@router.get("/preview/landing-pages/{page_id}")
async def preview_landing_page(page_id: str):
    """
    Serve the landing page preview.
    
    Returns the index.html file for the landing page.
    """
    preview_path = LANDING_PAGES_DIR / page_id / "index.html"
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Landing page not found")
    return FileResponse(preview_path, media_type="text/html")


@router.get("/preview/landing-pages/{page_id}/{file_path:path}")
async def preview_landing_page_asset(page_id: str, file_path: str):
    """
    Serve landing page assets (CSS, JS, images).
    """
    asset_path = LANDING_PAGES_DIR / page_id / file_path
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Determine media type
    media_type = "application/octet-stream"
    if file_path.endswith(".css"):
        media_type = "text/css"
    elif file_path.endswith(".js"):
        media_type = "application/javascript"
    elif file_path.endswith(".html"):
        media_type = "text/html"
    
    return FileResponse(asset_path, media_type=media_type)


@router.get("/preview/sites/{site_id}")
async def preview_site(site_id: str):
    """
    Serve the website preview (index.html).
    """
    preview_path = SITES_DIR / site_id / "index.html"
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Website not found")
    return FileResponse(preview_path, media_type="text/html")


@router.get("/preview/sites/{site_id}/{file_path:path}")
async def preview_site_asset(site_id: str, file_path: str):
    """
    Serve website assets (CSS, JS, images, other pages).
    """
    asset_path = SITES_DIR / site_id / file_path
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Determine media type
    media_type = "application/octet-stream"
    if file_path.endswith(".css"):
        media_type = "text/css"
    elif file_path.endswith(".js"):
        media_type = "application/javascript"
    elif file_path.endswith(".html"):
        media_type = "text/html"
    
    return FileResponse(asset_path, media_type=media_type)


@router.get("/download/landing-pages/{page_id}.zip")
async def download_landing_page(page_id: str):
    """
    Download the landing page as a ZIP file.
    """
    zip_path = LANDING_PAGES_DIR / f"{page_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Landing page ZIP not found")
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"landing-page-{page_id}.zip"
    )


@router.get("/download/sites/{site_id}.zip")
async def download_site(site_id: str):
    """
    Download the website as a ZIP file.
    """
    zip_path = SITES_DIR / f"{site_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Website ZIP not found")
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"website-{site_id}.zip"
    )