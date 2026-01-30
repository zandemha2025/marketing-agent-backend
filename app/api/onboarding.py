"""
Onboarding API endpoints.

Handles the "magical onboarding" flow:
1. POST /start - Start onboarding with a domain
2. GET /status/{org_id} - Get current onboarding status
3. WS /progress/{org_id} - WebSocket for real-time progress
4. GET /result/{org_id} - Get final onboarding result
5. PUT /result/{org_id} - Update/refine onboarding result
"""
from typing import Dict, Any
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings, Settings
from ..core.database import get_db
from ..models.knowledge_base import ResearchStatus
from ..repositories.organization import OrganizationRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository
from ..services.onboarding.pipeline import OnboardingPipeline, OnboardingProgress as PipelineProgress
from ..schemas.onboarding import (
    OnboardingRequest,
    OnboardingStatus,
    OnboardingProgress,
    OnboardingResult,
    OnboardingUpdateRequest,
    BrandProfile,
    MarketProfile,
    AudienceProfile,
    AudienceSegment,
    CompetitorProfile,
    MarketTrend,
    VisualIdentity,
    BrandVoice,
)

router = APIRouter()

# Store for active onboarding sessions (in production, use Redis)
_active_sessions: Dict[str, OnboardingPipeline] = {}
_progress_subscribers: Dict[str, list] = {}


@router.post("/start", response_model=OnboardingStatus)
async def start_onboarding(
    request: OnboardingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """
    Start the onboarding process for a new organization.

    This endpoint:
    1. Creates the organization if it doesn't exist
    2. Initializes the knowledge base
    3. Starts the background onboarding pipeline
    4. Returns immediately with status

    Use the /progress WebSocket or poll /status for updates.
    """
    logger.info(f"[START] Received request for domain: {request.domain}")
    print(f"[START] Received request for domain: {request.domain}", flush=True)

    # Check if organization already exists
    org_repo = OrganizationRepository(db)
    existing_org = await org_repo.get_by_domain(request.domain)

    if existing_org:
        # Check if onboarding is already complete
        kb_repo = KnowledgeBaseRepository(db)
        kb = await kb_repo.get_by_organization(existing_org.id)

        if kb and kb.research_status == ResearchStatus.COMPLETE:
            raise HTTPException(
                status_code=400,
                detail="Organization already onboarded. Use /result endpoint to view data."
            )

        if kb and kb.research_status == ResearchStatus.IN_PROGRESS:
            # Return current progress
            return OnboardingStatus(
                organization_id=existing_org.id,
                status="in_progress",
                progress=OnboardingProgress(
                    stage=kb.research_stage or "in_progress",
                    progress=kb.research_progress,
                    message="Onboarding in progress"
                ),
                can_resume=False
            )

        org = existing_org
    else:
        # Create new organization
        logger.info(f"[START] Creating new organization for domain: {request.domain}")
        print(f"[START] Creating new organization for domain: {request.domain}", flush=True)
        company_name = request.company_name or request.domain.replace(".com", "").replace("www.", "").title()
        # Create a slug from the domain
        slug = request.domain.replace(".", "-").replace("www-", "").lower()
        org = await org_repo.create_organization(
            name=company_name,
            slug=slug,
            domain=request.domain
        )
        logger.info(f"[START] Created organization with ID: {org.id}")
        print(f"[START] Created organization with ID: {org.id}", flush=True)

    # Create or get knowledge base
    kb_repo = KnowledgeBaseRepository(db)
    kb = await kb_repo.get_by_organization(org.id)
    if not kb:
        kb = await kb_repo.create_for_organization(org.id)

    # Update status to in progress
    await kb_repo.update_research_status(
        org.id,
        ResearchStatus.IN_PROGRESS,
        progress=0.0,
        stage="initializing"
    )

    # Commit so the org and knowledge base are visible to status polling
    await db.commit()

    # Start background onboarding task
    logger.info(f"[START] Adding background task for org: {org.id}")
    background_tasks.add_task(
        run_onboarding_task,
        org.id,
        request.domain,
        settings
    )

    logger.info(f"[START] Returning response with org_id: {org.id}")
    return OnboardingStatus(
        organization_id=org.id,
        status="in_progress",
        progress=OnboardingProgress(
            stage="initializing",
            progress=0.0,
            message=f"Starting research for {request.domain}..."
        ),
        can_resume=False
    )


async def run_onboarding_task(
    organization_id: str,
    domain: str,
    settings: Settings
):
    """Background task to run the onboarding pipeline."""
    logger.info(f"[BACKGROUND] Starting onboarding task for org={organization_id}, domain={domain}")
    from ..core.database import get_database_manager

    # Use the global database manager to share connection pool
    db = get_database_manager()

    try:
        logger.info(f"[BACKGROUND] Creating pipeline with firecrawl_key={settings.firecrawl_api_key[:10]}... perplexity_key={settings.perplexity_api_key[:10]}...")
        pipeline = OnboardingPipeline(
            firecrawl_api_key=settings.firecrawl_api_key,
            perplexity_api_key=settings.perplexity_api_key,
            max_pages=settings.onboarding_max_pages
        )

        # Store pipeline for progress tracking
        _active_sessions[organization_id] = pipeline

        async def progress_callback(progress: PipelineProgress):
            """Handle progress updates."""
            # Update database
            async with db.session() as session:
                kb_repo = KnowledgeBaseRepository(session)
                await kb_repo.update_research_status(
                    organization_id,
                    ResearchStatus.IN_PROGRESS,
                    progress=progress.progress,
                    stage=progress.stage.value,
                    error=progress.error
                )

            # Notify WebSocket subscribers
            if organization_id in _progress_subscribers:
                for ws in _progress_subscribers[organization_id]:
                    try:
                        await ws.send_json({
                            "stage": progress.stage.value,
                            "progress": progress.progress,
                            "message": progress.message,
                            "details": progress.details
                        })
                    except Exception as e:
                        # WebSocket might be closed, remove from subscribers
                        logger.debug(f"Failed to send progress to WebSocket: {e}")

        # Run the pipeline
        result = await pipeline.run(domain, organization_id, progress_callback)

        # Save results to database
        async with db.session() as session:
            kb_repo = KnowledgeBaseRepository(session)

            if result.success:
                await kb_repo.save_onboarding_result(
                    organization_id,
                    brand_data=result.brand_data,
                    market_data=result.market_data,
                    audiences_data=result.audiences_data,
                    offerings_data=result.offerings_data,
                    context_data=result.context_data
                )
            else:
                await kb_repo.update_research_status(
                    organization_id,
                    ResearchStatus.FAILED,
                    error=result.error
                )

    except Exception as e:
        logger.error(f"[BACKGROUND] Pipeline failed for org={organization_id}: {e}", exc_info=True)
        # Update status to failed
        async with db.session() as session:
            kb_repo = KnowledgeBaseRepository(session)
            await kb_repo.update_research_status(
                organization_id,
                ResearchStatus.FAILED,
                error=str(e)
            )

    finally:
        logger.info(f"[BACKGROUND] Cleaning up for org={organization_id}")
        # Cleanup
        if organization_id in _active_sessions:
            del _active_sessions[organization_id]
        # Note: Don't close db since we're using the global database manager


@router.get("/status/{organization_id}", response_model=OnboardingStatus)
async def get_onboarding_status(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of an onboarding process."""
    kb_repo = KnowledgeBaseRepository(db)
    kb = await kb_repo.get_by_organization(organization_id)

    if not kb:
        raise HTTPException(status_code=404, detail="Organization not found")

    status_map = {
        ResearchStatus.PENDING: "pending",
        ResearchStatus.IN_PROGRESS: "in_progress",
        ResearchStatus.COMPLETE: "complete",
        ResearchStatus.FAILED: "failed",
        ResearchStatus.STALE: "stale",
    }

    return OnboardingStatus(
        organization_id=organization_id,
        status=status_map.get(kb.research_status, "unknown"),
        progress=OnboardingProgress(
            stage=kb.research_stage or kb.research_status.value,
            progress=kb.research_progress,
            message=kb.research_error if kb.research_error else "Processing",
            error=kb.research_error
        ),
        can_resume=kb.research_status in [ResearchStatus.FAILED, ResearchStatus.STALE]
    )


@router.websocket("/progress/{organization_id}")
async def onboarding_progress_websocket(
    websocket: WebSocket,
    organization_id: str,
):
    """WebSocket endpoint for real-time onboarding progress."""
    await websocket.accept()

    # Add to subscribers
    if organization_id not in _progress_subscribers:
        _progress_subscribers[organization_id] = []
    _progress_subscribers[organization_id].append(websocket)

    try:
        # Keep connection alive
        while True:
            # Wait for any message (ping/pong)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        # Remove from subscribers
        if organization_id in _progress_subscribers:
            _progress_subscribers[organization_id].remove(websocket)
            if not _progress_subscribers[organization_id]:
                del _progress_subscribers[organization_id]


@router.get("/result/{organization_id}", response_model=OnboardingResult)
async def get_onboarding_result(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the complete onboarding result for presentation.

    This is the "Here's what we learned about you" moment.
    """
    kb_repo = KnowledgeBaseRepository(db)
    kb = await kb_repo.get_by_organization(organization_id)

    if not kb:
        raise HTTPException(status_code=404, detail="Organization not found")

    if kb.research_status != ResearchStatus.COMPLETE:
        raise HTTPException(
            status_code=400,
            detail=f"Onboarding not complete. Status: {kb.research_status.value}"
        )

    # Convert to presentation format
    presentation = kb.to_presentation_format()

    # Get industry, with fallback if Unknown
    industry = presentation["market"].get("industry", "Technology / Software")
    if not industry or industry.lower() in ["unknown", "n/a", ""]:
        industry = "Technology / Software"

    # Get audience segments from the presentation data and convert to Pydantic models
    raw_segments = presentation.get("audiences", [])
    if not raw_segments:
        # Fallback to default segments if none found
        raw_segments = [
            {
                "name": "Business Decision Makers",
                "size": "primary",
                "demographics": {"job_titles": ["CEO", "CMO", "VP"], "company_size": "50-500"},
                "psychographics": {"values": ["ROI", "efficiency"]},
                "pain_points": ["Limited time", "Need ROI"],
                "goals": ["Grow revenue", "Reduce costs"],
                "preferred_channels": ["LinkedIn", "Email"],
                "content_preferences": ["Case studies", "ROI calculators"]
            },
            {
                "name": "End Users & Implementers",
                "size": "secondary",
                "demographics": {"job_titles": ["Manager", "Specialist"], "company_size": "10-500"},
                "psychographics": {"values": ["ease of use", "reliability"]},
                "pain_points": ["Complex tools", "Lack of training"],
                "goals": ["Master tools quickly", "Improve productivity"],
                "preferred_channels": ["YouTube", "Twitter"],
                "content_preferences": ["Tutorials", "How-to guides"]
            }
        ]

    # Convert raw segment dicts to AudienceSegment models
    audience_segments = []
    for seg in raw_segments:
        try:
            audience_segments.append(AudienceSegment(
                name=seg.get("name", "Unknown Segment"),
                size=seg.get("size", "secondary"),
                demographics=seg.get("demographics", {}),
                psychographics=seg.get("psychographics", {}),
                pain_points=seg.get("pain_points", []),
                goals=seg.get("goals", []),
                preferred_channels=seg.get("preferred_channels", []),
                content_preferences=seg.get("content_preferences", [])
            ))
        except Exception as e:
            logger.warning(f"Failed to parse audience segment: {e}")

    # Convert competitors to Pydantic models
    raw_competitors = presentation["market"].get("competitors", [])
    competitors = []
    for comp in raw_competitors:
        try:
            competitors.append(CompetitorProfile(
                name=comp.get("name", "Unknown"),
                domain=comp.get("domain"),
                strengths=comp.get("strengths", []),
                weaknesses=comp.get("weaknesses", []),
                positioning=comp.get("positioning"),
                key_differentiators=comp.get("key_differentiators", [])
            ))
        except Exception as e:
            logger.warning(f"Failed to parse competitor: {e}")

    # Convert trends to Pydantic models
    raw_trends = presentation["market"].get("trends", [])
    trends = []
    for trend in raw_trends:
        try:
            trends.append(MarketTrend(
                trend=trend.get("trend", "Unknown"),
                relevance=trend.get("relevance", "medium"),
                opportunity=trend.get("opportunity")
            ))
        except Exception as e:
            logger.warning(f"Failed to parse trend: {e}")

    return OnboardingResult(
        organization_id=organization_id,
        brand=BrandProfile(
            name=presentation["brand"].get("name", ""),
            domain=presentation["brand"].get("domain", ""),
            tagline=presentation["brand"].get("tagline"),
            description=presentation["brand"].get("description"),
            visual_identity=VisualIdentity(**presentation["brand"].get("visual_identity", {})),
            voice=BrandVoice(**presentation["brand"].get("voice", {})),
            values=presentation["brand"].get("values", []),
            mission=presentation["brand"].get("mission"),
        ),
        market=MarketProfile(
            industry=industry,
            competitors=competitors,
            trends=trends,
            market_position=presentation["market"].get("position"),
            opportunities=[],
            threats=[],
        ),
        audiences=AudienceProfile(
            segments=audience_segments
        ),
        offerings=presentation.get("offerings", {}),
        context=presentation.get("context", {}),
        research_status=presentation.get("research_status", "complete"),
    )


@router.put("/result/{organization_id}")
async def update_onboarding_result(
    organization_id: str,
    request: OnboardingUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Update/refine onboarding results.

    Allows the user to correct or enhance the auto-discovered data.
    """
    kb_repo = KnowledgeBaseRepository(db)

    section_handlers = {
        "brand": kb_repo.update_brand_data,
        "market": kb_repo.update_market_data,
        "audiences": kb_repo.update_audiences_data,
        "offerings": kb_repo.update_offerings_data,
        "context": kb_repo.update_context_data,
    }

    if request.section not in section_handlers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section. Must be one of: {list(section_handlers.keys())}"
        )

    handler = section_handlers[request.section]
    result = await handler(organization_id, request.data, merge=True)

    if not result:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {"status": "updated", "section": request.section}


@router.post("/retry/{organization_id}", response_model=OnboardingStatus)
async def retry_onboarding(
    organization_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Retry a failed onboarding."""
    org_repo = OrganizationRepository(db)
    org = await org_repo.get(organization_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    kb_repo = KnowledgeBaseRepository(db)
    kb = await kb_repo.get_by_organization(organization_id)

    if kb and kb.research_status not in [ResearchStatus.FAILED, ResearchStatus.STALE]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry onboarding in status: {kb.research_status.value}"
        )

    # Reset status
    await kb_repo.update_research_status(
        organization_id,
        ResearchStatus.IN_PROGRESS,
        progress=0.0,
        stage="initializing",
        error=None
    )

    # Start background task
    background_tasks.add_task(
        run_onboarding_task,
        organization_id,
        org.domain,
        settings
    )

    return OnboardingStatus(
        organization_id=organization_id,
        status="in_progress",
        progress=OnboardingProgress(
            stage="initializing",
            progress=0.0,
            message=f"Retrying research for {org.domain}..."
        ),
        can_resume=False
    )
