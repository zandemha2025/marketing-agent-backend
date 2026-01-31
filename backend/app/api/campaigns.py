"""
Campaign API endpoints.

Full campaign workflow with WebSocket progress updates.
All endpoints require authentication via JWT token.
"""
import asyncio
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

from ..core.config import get_settings
from ..core.database import get_session, get_database_manager
from ..services.campaigns import (
    CampaignOrchestrator,
    CampaignResult,
    CampaignProgress,
    CampaignPhase,
    run_campaign
)
from ..repositories.campaign import CampaignRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository
# Auth dependency available for securing endpoints
from .auth import get_current_user, get_current_active_user

router = APIRouter()

# In-memory store for active campaign sessions
# In production, use Redis
active_campaigns = {}


# === Pydantic Models ===

class CampaignCreateRequest(BaseModel):
    """Request to create a new campaign."""
    organization_id: str
    name: str
    objective: Optional[str] = Field(None, description="What the campaign aims to achieve")
    goal: Optional[str] = Field(None, description="Campaign goal (alias for objective)")
    product_focus: Optional[str] = Field(None, description="Specific product/service to promote")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    budget_tier: str = Field("medium", description="Budget tier: low, medium, high")
    timeline: str = Field("4 weeks", description="Campaign timeline")
    platforms: Optional[List[str]] = Field(None, description="Target platforms")
    brand_url: Optional[str] = Field(None, description="Brand website for research")
    
    @property
    def effective_objective(self) -> str:
        """Get the objective, falling back to goal if not provided."""
        return self.objective or self.goal or "General marketing campaign"


class CampaignResponse(BaseModel):
    """Campaign response model."""
    id: str
    organization_id: str
    name: str
    status: str
    objective: str
    created_at: datetime
    brief: Optional[dict] = None
    concepts: Optional[List[dict]] = None
    selected_concept_index: Optional[int] = None
    asset_count: int = 0
    # Additional fields from config
    target_audience: Optional[str] = None
    platforms: Optional[List[str]] = None
    product_focus: Optional[str] = None
    budget_tier: Optional[str] = None
    timeline: Optional[str] = None


class ConceptSelectRequest(BaseModel):
    """Request to select a creative concept."""
    concept_index: int


class AssetRegenerateRequest(BaseModel):
    """Request to regenerate an asset."""
    asset_index: int
    modifications: Optional[dict] = None


class CampaignListResponse(BaseModel):
    """List of campaigns."""
    campaigns: List[CampaignResponse]
    total: int


class CampaignUpdateRequest(BaseModel):
    """Request to update a campaign."""
    name: Optional[str] = Field(None, description="Campaign name")
    objective: Optional[str] = Field(None, description="Campaign objective")
    status: Optional[str] = Field(None, description="Campaign status: draft, active, paused, completed, archived")
    product_focus: Optional[str] = Field(None, description="Product/service focus")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    budget_tier: Optional[str] = Field(None, description="Budget tier: low, medium, high")
    timeline: Optional[str] = Field(None, description="Campaign timeline")
    platforms: Optional[List[str]] = Field(None, description="Target platforms")


# === Helper Functions ===

def _get_orchestrator():
    """Create campaign orchestrator with settings."""
    settings = get_settings()
    return CampaignOrchestrator(
        openrouter_api_key=settings.openrouter_api_key,
        firecrawl_api_key=settings.firecrawl_api_key,
        perplexity_api_key=settings.perplexity_api_key,
        segmind_api_key=settings.segmind_api_key,
        elevenlabs_api_key=settings.elevenlabs_api_key,
        output_dir="outputs"
    )


async def _get_knowledge_base(organization_id: str, session) -> Optional[dict]:
    """Get organization's knowledge base."""
    kb_repo = KnowledgeBaseRepository(session)
    kb = await kb_repo.get_by_organization(organization_id)
    if kb:
        return {
            "brand": kb.brand_data or {},
            "market": kb.market_data or {},
            "audiences": kb.audiences_data or {},
            "offerings": kb.offerings_data or {},
            "context": kb.context_data or {}
        }
    return None


# === REST Endpoints ===

@router.get("/", response_model=CampaignListResponse)
async def list_campaigns(
    organization_id: str,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """List campaigns for an organization. Requires authentication."""
    # Validation
    if not organization_id or not organization_id.strip():
        raise HTTPException(
            status_code=400,
            detail="organization_id query parameter is required"
        )

    repo = CampaignRepository(session)

    try:
        if status:
            campaigns = await repo.get_by_status(organization_id, status, limit, offset)
        else:
            # Use keyword arguments to avoid parameter order issues
            campaigns = await repo.get_by_organization(
                organization_id=organization_id,
                skip=offset,
                limit=limit
            )

        total = await repo.count_by_organization(organization_id)

        def make_campaign_response(c):
            config = c.config or {}
            return CampaignResponse(
                id=c.id,
                organization_id=c.organization_id,
                name=c.name,
                status=c.status,
                objective=c.objective or "",
                created_at=c.created_at,
                brief=c.brief_data,
                concepts=c.creative_concepts,
                selected_concept_index=c.selected_concept_index,
                asset_count=0,  # Avoid lazy loading in async context
                target_audience=config.get("target_audience"),
                platforms=config.get("platforms"),
                product_focus=config.get("product_focus"),
                budget_tier=config.get("budget_tier"),
                timeline=config.get("timeline"),
            )

        return CampaignListResponse(
            campaigns=[make_campaign_response(c) for c in campaigns],
            total=total
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list campaigns: {str(e)}"
        )


@router.post("", response_model=CampaignResponse)
async def create_campaign(
    request: CampaignCreateRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """
    Create a new campaign. Requires authentication.

    This initializes the campaign and returns immediately.
    Use WebSocket endpoint to track execution progress.
    """
    # Validation
    if not request.organization_id or not request.organization_id.strip():
        raise HTTPException(
            status_code=400,
            detail="organization_id is required"
        )

    if not request.name or not request.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Campaign name is required"
        )

    if len(request.name.strip()) > 255:
        raise HTTPException(
            status_code=400,
            detail="Campaign name must be less than 255 characters"
        )

    repo = CampaignRepository(session)

    try:
        # Create campaign record
        # Use effective_objective to handle both 'objective' and 'goal' fields from frontend
        campaign = await repo.create(
            organization_id=request.organization_id,
            name=request.name.strip(),
            status="draft",
            objective=request.effective_objective,
            config={
                "product_focus": request.product_focus,
                "target_audience": request.target_audience,
                "budget_tier": request.budget_tier,
                "timeline": request.timeline,
                "platforms": request.platforms,
                "brand_url": request.brand_url
            }
        )

        # Extract config fields for response
        config = campaign.config or {}
        return CampaignResponse(
            id=campaign.id,
            organization_id=campaign.organization_id,
            name=campaign.name,
            status=campaign.status,
            objective=campaign.objective or "",
            created_at=campaign.created_at,
            asset_count=0,
            target_audience=config.get("target_audience"),
            platforms=config.get("platforms"),
            product_focus=config.get("product_focus"),
            budget_tier=config.get("budget_tier"),
            timeline=config.get("timeline"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create campaign: {str(e)}"
        )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Get campaign details. Requires authentication."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    config = campaign.config or {}
    return CampaignResponse(
        id=campaign.id,
        organization_id=campaign.organization_id,
        name=campaign.name,
        status=campaign.status,
        objective=campaign.objective or "",
        created_at=campaign.created_at,
        brief=campaign.brief_data,
        concepts=campaign.creative_concepts,
        selected_concept_index=campaign.selected_concept_index,
        asset_count=0,  # Avoid lazy loading in async context
        target_audience=config.get("target_audience"),
        platforms=config.get("platforms"),
        product_focus=config.get("product_focus"),
        budget_tier=config.get("budget_tier"),
        timeline=config.get("timeline"),
    )


@router.get("/{campaign_id}/deliverables")
async def get_campaign_deliverables(
    campaign_id: str,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Get all deliverables for a campaign."""
    from sqlalchemy import select, desc
    from ..models.deliverable import Deliverable
    query = select(Deliverable).where(Deliverable.campaign_id == campaign_id).order_by(desc(Deliverable.created_at))
    result = await session.execute(query)
    deliverables = result.scalars().all()
    return [
        {
            "id": d.id, "title": d.title, "type": d.type,
            "content": d.content, "platform": d.platform,
            "status": d.status, "created_at": d.created_at.isoformat(),
        }
        for d in deliverables
    ]


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    request: CampaignUpdateRequest,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """
    Update a campaign. Requires authentication.

    Only provided fields will be updated.
    """
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Build update dict from provided fields
    update_data = {}

    if request.name is not None:
        if not request.name.strip():
            raise HTTPException(status_code=400, detail="Campaign name cannot be empty")
        if len(request.name.strip()) > 255:
            raise HTTPException(status_code=400, detail="Campaign name must be less than 255 characters")
        update_data["name"] = request.name.strip()

    if request.objective is not None:
        update_data["objective"] = request.objective

    if request.status is not None:
        valid_statuses = ["draft", "active", "paused", "completed", "archived"]
        if request.status.lower() not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        update_data["status"] = request.status.lower()

    # Update config fields if provided
    config_updates = {}
    if request.product_focus is not None:
        config_updates["product_focus"] = request.product_focus
    if request.target_audience is not None:
        config_updates["target_audience"] = request.target_audience
    if request.budget_tier is not None:
        config_updates["budget_tier"] = request.budget_tier
    if request.timeline is not None:
        config_updates["timeline"] = request.timeline
    if request.platforms is not None:
        config_updates["platforms"] = request.platforms

    if config_updates:
        # Merge with existing config
        existing_config = campaign.config or {}
        existing_config.update(config_updates)
        update_data["config"] = existing_config

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        updated_campaign = await repo.update(campaign_id, **update_data)

        return CampaignResponse(
            id=updated_campaign.id,
            organization_id=updated_campaign.organization_id,
            name=updated_campaign.name,
            status=updated_campaign.status,
            objective=updated_campaign.objective or "",
            created_at=updated_campaign.created_at,
            brief=updated_campaign.brief_data,
            concepts=updated_campaign.creative_concepts,
            selected_concept_index=updated_campaign.selected_concept_index,
            asset_count=0  # Avoid lazy loading in async context
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update campaign: {str(e)}"
        )


# Store running background tasks to prevent garbage collection
_running_tasks: dict = {}


@router.post("/{campaign_id}/execute")
async def execute_campaign(
    campaign_id: str,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """
    Start campaign execution. Requires authentication.

    Enqueues a Celery task to process the campaign asynchronously.
    Use the status endpoint to track progress.
    """
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ("draft", "failed"):
        raise HTTPException(
            status_code=400,
            detail=f"Campaign cannot be executed in {campaign.status} status"
        )

    # Update status to in_progress immediately (not queued - we're starting now)
    await repo.update(campaign_id, status="in_progress")
    await session.commit()

    # Prepare config for the task
    config = campaign.config or {}
    config["objective"] = campaign.objective or config.get("objective", "")

    # Try to enqueue Celery task, fallback to direct async execution
    try:
        from ..tasks.campaign_tasks import execute_campaign_task

        # Enqueue the Celery task
        task = execute_campaign_task.delay(
            campaign_id=campaign_id,
            organization_id=campaign.organization_id,
            config=config
        )
        
        logger.info(f"Enqueued Celery task {task.id} for campaign {campaign_id}")

        return {
            "campaign_id": campaign_id,
            "status": "in_progress",
            "task_id": task.id,
            "message": "Campaign execution started via Celery. Check status endpoint for progress.",
            "status_url": f"/api/campaigns/{campaign_id}/status"
        }
    except (ImportError, Exception) as exc:
        # Celery not available or broker connection failed - run directly via BackgroundTasks
        logger.warning(f"Celery unavailable ({type(exc).__name__}: {exc}), falling back to direct execution")

        async def _run_campaign_directly(cid: str, org_id: str, cfg: dict):
            """Run campaign orchestration directly without Celery."""
            try:
                settings = get_settings()
                db = get_database_manager()
                async with db.session() as s:
                    repo2 = CampaignRepository(s)
                    await repo2.update(cid, status="in_progress")
                    await s.commit()

                    # Load knowledge base
                    kb_repo = KnowledgeBaseRepository(s)
                    kb = await kb_repo.get_by_organization(org_id)
                    knowledge_base = None
                    if kb:
                        knowledge_base = {
                            "brand": kb.brand_data or {},
                            "market": kb.market_data or {},
                            "audiences": kb.audiences_data or {},
                            "offerings": kb.offerings_data or {},
                            "context": kb.context_data or {},
                        }

                    campaign_request = {
                        "objective": cfg.get("objective", ""),
                        "product_focus": cfg.get("product_focus"),
                        "target_audience": cfg.get("target_audience"),
                        "budget_tier": cfg.get("budget_tier", "medium"),
                        "timeline": cfg.get("timeline", "4 weeks"),
                        "platforms": cfg.get("platforms"),
                        "brand_url": cfg.get("brand_url"),
                        "brand_name": (knowledge_base or {}).get("brand", {}).get("name", ""),
                    }

                    orchestrator = CampaignOrchestrator(
                        openrouter_api_key=settings.openrouter_api_key,
                        firecrawl_api_key=settings.firecrawl_api_key or "",
                        perplexity_api_key=settings.perplexity_api_key or "",
                        segmind_api_key=settings.segmind_api_key or "",
                        elevenlabs_api_key=settings.elevenlabs_api_key or "",
                        output_dir="outputs",
                    )

                    try:
                        result = await orchestrator.execute_campaign(
                            campaign_request=campaign_request,
                            knowledge_base=knowledge_base,
                            skip_research=bool(knowledge_base),
                        )

                        final_status = "completed" if result.status == "complete" else "failed"
                        await repo2.update(
                            cid,
                            status=final_status,
                            brief_data=_brief_to_dict(result.brief) if result.brief else None,
                            creative_concepts=[_concept_to_dict(c) for c in result.concepts],
                            selected_concept_index=0 if result.concepts else None,
                        )
                        await s.commit()

                        # Create deliverables from result
                        from ..models.deliverable import Deliverable
                        if result.brief:
                            brief_sections = [
                                f"# {result.brief.campaign_name}",
                                f"\n## Executive Summary\n{result.brief.executive_summary}",
                                f"\n## Business Context\n{result.brief.business_context}",
                                f"\n## Market Situation\n{result.brief.market_situation}",
                                f"\n## Key Insight\n{result.brief.key_insight}",
                                f"\n## Strategic Proposition\n{result.brief.strategic_proposition}",
                            ]
                            s.add(Deliverable(
                                campaign_id=cid, title=f"Campaign Strategy: {result.brief.campaign_name}",
                                type="STRATEGY", content="\n".join(brief_sections), platform="", status="completed",
                            ))
                        for ci, concept in enumerate(result.concepts):
                            concept_sections = [
                                f"# {concept.concept_name}", f"\n## Tagline\n{concept.tagline}",
                                f"\n## Concept Statement\n{concept.concept_statement}",
                                f"\n## Key Visual Idea\n{concept.key_visual_idea}",
                                f"\n## Tone\n{concept.tone_description}",
                            ]
                            s.add(Deliverable(
                                campaign_id=cid, title=f"Creative Concept {ci+1}: {concept.concept_name}",
                                type="CONCEPT", content="\n".join(concept_sections), platform="", status="completed",
                            ))
                            for asset in concept.assets:
                                for copy_var in asset.copy:
                                    s.add(Deliverable(
                                        campaign_id=cid,
                                        title=f"{copy_var.format.replace('_', ' ').title()} - {concept.concept_name}",
                                        type="COPY", content=copy_var.content, platform=asset.platform, status="completed",
                                    ))
                        # Additional deliverables from expanded result
                        for attr, dtype, title in [
                            ("research_report", "RESEARCH_REPORT", "Research Report"),
                            ("competitive_analysis", "COMPETITIVE_ANALYSIS", "Competitive Analysis"),
                            ("media_plan", "MEDIA_PLAN", "Media Plan"),
                        ]:
                            val = getattr(result, attr, None)
                            if val:
                                s.add(Deliverable(campaign_id=cid, title=title, type=dtype, content=val, platform="", status="completed"))
                        if getattr(result, 'headlines', None):
                            s.add(Deliverable(campaign_id=cid, title="Headlines", type="HEADLINE", content="\n".join(result.headlines), platform="", status="completed"))
                        for j, bc in enumerate(getattr(result, 'body_copy_variations', []) or []):
                            s.add(Deliverable(campaign_id=cid, title=f"Body Copy Variation {j+1}", type="BODY_COPY", content=bc, platform="", status="completed"))
                        for plat, posts in (getattr(result, 'social_posts', {}) or {}).items():
                            for k, post in enumerate(posts):
                                s.add(Deliverable(campaign_id=cid, title=f"{plat.title()} Post {k+1}", type="SOCIAL_POST", content=post, platform=plat, status="completed"))
                        for j, vs in enumerate(getattr(result, 'video_scripts', []) or []):
                            s.add(Deliverable(campaign_id=cid, title=f"Video Script {j+1}", type="VIDEO_SCRIPT", content=vs, platform="", status="completed"))
                        for size, ctxt in (getattr(result, 'display_ad_copy', {}) or {}).items():
                            s.add(Deliverable(campaign_id=cid, title=f"Display Ad ({size})", type="DISPLAY_AD", content=ctxt, platform="display", status="completed"))
                        await s.commit()
                        logger.info(f"Direct campaign execution completed: {final_status}")
                    finally:
                        await orchestrator.close()

            except Exception as run_exc:
                logger.error(f"Direct campaign execution failed: {run_exc}", exc_info=True)
                try:
                    db = get_database_manager()
                    async with db.session() as s:
                        r = CampaignRepository(s)
                        await r.update(cid, status="failed")
                        await s.commit()
                except Exception:
                    pass

        # Create and store the background task to prevent garbage collection
        async def _task_wrapper():
            """Wrapper to clean up task reference when done."""
            try:
                await _run_campaign_directly(campaign_id, campaign.organization_id, config)
            finally:
                # Clean up task reference
                _running_tasks.pop(campaign_id, None)
        
        task = asyncio.create_task(_task_wrapper())
        _running_tasks[campaign_id] = task
        
        logger.info(f"Started background task for campaign {campaign_id}")

        return {
            "campaign_id": campaign_id,
            "status": "in_progress",
            "message": "Campaign execution started directly (Celery unavailable). Check status endpoint for progress.",
            "status_url": f"/api/campaigns/{campaign_id}/status"
        }


@router.post("/{campaign_id}/select-concept")
async def select_concept(
    campaign_id: str,
    request: ConceptSelectRequest,
    session=Depends(get_session)
):
    """Select a creative concept for the campaign."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    concepts = campaign.creative_concepts or []
    if request.concept_index >= len(concepts):
        raise HTTPException(status_code=400, detail="Invalid concept index")

    await repo.update(campaign_id, selected_concept_index=request.concept_index)

    return {
        "status": "success",
        "selected_concept": concepts[request.concept_index]
    }


@router.post("/{campaign_id}/regenerate-asset")
async def regenerate_asset(
    campaign_id: str,
    request: AssetRegenerateRequest,
    session=Depends(get_session)
):
    """Regenerate a specific asset with optional modifications."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get knowledge base
    kb = await _get_knowledge_base(campaign.organization_id, session)

    # Get the campaign result from storage
    if campaign_id not in active_campaigns:
        raise HTTPException(status_code=400, detail="Campaign session not found")

    session_data = active_campaigns[campaign_id]
    result = session_data.get("result")

    if not result:
        raise HTTPException(status_code=400, detail="No campaign result available")

    orchestrator = _get_orchestrator()

    try:
        new_asset = await orchestrator.regenerate_asset(
            campaign_result=result,
            asset_index=request.asset_index,
            modifications=request.modifications
        )

        return {
            "status": "success",
            "asset": {
                "id": new_asset.asset_id,
                "type": new_asset.asset_type,
                "platform": new_asset.platform,
                "name": new_asset.name
            }
        }
    finally:
        await orchestrator.close()


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Delete a campaign. Requires authentication."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await repo.delete(campaign_id)

    return {"status": "deleted", "id": campaign_id}


# === Optimization Endpoints ===

@router.post("/{campaign_id}/experiments")
async def create_campaign_experiment(
    campaign_id: str,
    experiment_config: dict,
    session=Depends(get_session)
):
    """Create an A/B test experiment for a campaign."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # This would create an experiment linked to the campaign
    return {
        "campaign_id": campaign_id,
        "experiment_id": None,  # Would be created
        "status": "created"
    }


@router.get("/{campaign_id}/optimization-status")
async def get_campaign_optimization_status(
    campaign_id: str,
    session=Depends(get_session)
):
    """Get optimization status for a campaign."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    config = campaign.config or {}
    auto_opt = config.get('auto_optimization', {})

    return {
        "campaign_id": campaign_id,
        "auto_optimization_enabled": auto_opt.get('enabled', False),
        "optimization_settings": auto_opt.get('settings', {}),
        "experiments_count": len(campaign.experiments) if hasattr(campaign, 'experiments') else 0
    }


@router.get("/{campaign_id}/status")
async def get_campaign_execution_status(
    campaign_id: str,
    session=Depends(get_session)
):
    """
    Get campaign execution status and progress.
    
    Returns current status, progress information, and task results if available.
    """
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get progress from task tracking if available
    progress = None
    try:
        from ..tasks.campaign_tasks import get_campaign_progress
        progress = get_campaign_progress(campaign_id)
    except ImportError:
        pass  # Celery not available

    return {
        "campaign_id": campaign_id,
        "status": campaign.status,
        "progress": progress,
        "brief_data": campaign.brief_data,
        "concepts_count": len(campaign.creative_concepts) if campaign.creative_concepts else 0,
        "selected_concept_index": campaign.selected_concept_index
    }


# === WebSocket Endpoint ===

@router.websocket("/{campaign_id}/ws/{session_id}")
async def campaign_websocket(
    websocket: WebSocket,
    campaign_id: str,
    session_id: str
):
    """
    WebSocket endpoint for campaign execution with real-time progress.

    Connect to this endpoint after calling /execute to:
    1. Start the campaign execution
    2. Receive real-time progress updates
    3. Get the final result when complete
    """
    await websocket.accept()

    # Validate session
    if session_id not in active_campaigns:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid session ID"
        })
        await websocket.close()
        return

    session_data = active_campaigns[session_id]

    if session_data["campaign_id"] != campaign_id:
        await websocket.send_json({
            "type": "error",
            "message": "Session/campaign mismatch"
        })
        await websocket.close()
        return

    # Store websocket
    session_data["websocket"] = websocket
    session_data["status"] = "connected"

    await websocket.send_json({
        "type": "connected",
        "message": "Connected to campaign execution"
    })

    try:
        # Wait for start command
        data = await websocket.receive_json()

        if data.get("action") != "start":
            await websocket.send_json({
                "type": "error",
                "message": "Send {action: 'start'} to begin execution"
            })
            return

        # Get settings and knowledge base
        settings = get_settings()
        db = get_database_manager()
        async with db.session() as session:
            kb = await _get_knowledge_base(session_data["organization_id"], session)

        # Progress callback
        async def progress_callback(progress: CampaignProgress):
            await websocket.send_json({
                "type": "progress",
                "phase": progress.phase.value,
                "progress": progress.progress,
                "message": progress.message,
                "details": progress.details,
                "timestamp": progress.timestamp.isoformat()
            })

        # Build campaign request
        config = session_data["config"] or {}
        campaign_request = {
            "objective": config.get("objective", ""),
            "product_focus": config.get("product_focus"),
            "target_audience": config.get("target_audience"),
            "budget_tier": config.get("budget_tier", "medium"),
            "timeline": config.get("timeline", "4 weeks"),
            "platforms": config.get("platforms"),
            "brand_url": config.get("brand_url"),
            "brand_name": kb.get("brand", {}).get("name", "") if kb else ""
        }

        await websocket.send_json({
            "type": "started",
            "message": "Campaign execution started"
        })

        # Execute campaign
        api_keys = {
            "openrouter": settings.openrouter_api_key,
            "firecrawl": settings.firecrawl_api_key,
            "perplexity": settings.perplexity_api_key,
            "segmind": settings.segmind_api_key,
            "elevenlabs": settings.elevenlabs_api_key
        }

        result = await run_campaign(
            campaign_request=campaign_request,
            api_keys=api_keys,
            knowledge_base=kb,
            output_dir="outputs",
            progress_callback=progress_callback
        )

        # Store result
        session_data["result"] = result
        session_data["status"] = "complete"

        # Save to database
        async with db.session() as session:
            repo = CampaignRepository(session)

            await repo.update(
                campaign_id,
                status="complete" if result.status == "complete" else "failed",
                brief_data=_brief_to_dict(result.brief) if result.brief else None,
                creative_concepts=[_concept_to_dict(c) for c in result.concepts],
                selected_concept_index=0 if result.concepts else None
            )

        # Send final result
        await websocket.send_json({
            "type": "complete",
            "status": result.status,
            "campaign_id": result.campaign_id,
            "brief": _brief_to_dict(result.brief) if result.brief else None,
            "concepts": [_concept_to_dict(c) for c in result.concepts],
            "assets": [_asset_to_dict(a) for a in result.assets],
            "duration_seconds": result.total_duration_seconds,
            "errors": result.errors
        })

    except WebSocketDisconnect:
        session_data["status"] = "disconnected"
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        session_data["status"] = "error"
    finally:
        # Cleanup
        if session_id in active_campaigns:
            active_campaigns[session_id]["websocket"] = None


# === Serialization Helpers ===

def _brief_to_dict(brief) -> dict:
    """Convert CampaignBrief to dict."""
    if not brief:
        return None
    # Use the dataclass's own to_dict() if available
    if hasattr(brief, 'to_dict'):
        return brief.to_dict()
    # Fallback: manually map using correct CampaignBrief field names
    return {
        "campaign_name": getattr(brief, 'campaign_name', ''),
        "campaign_type": getattr(brief, 'campaign_type', ''),
        "executive_summary": getattr(brief, 'executive_summary', ''),
        "business_context": getattr(brief, 'business_context', ''),
        "market_situation": getattr(brief, 'market_situation', ''),
        "competitive_landscape": getattr(brief, 'competitive_landscape', ''),
        "brand_position": getattr(brief, 'brand_position', ''),
        "objectives": [
            {"objective": o.objective, "metric": o.metric, "target": o.target, "timeframe": o.timeframe}
            for o in getattr(brief, 'objectives', [])
        ] if hasattr(brief, 'objectives') and brief.objectives else [],
        "target_audience": getattr(brief, 'target_audience', {}),
        "key_insight": getattr(brief, 'key_insight', ''),
        "strategic_proposition": getattr(brief, 'strategic_proposition', ''),
        "key_messages": [
            {"message": m.message, "proof_points": m.proof_points, "emotional_hook": m.emotional_hook, "rational_benefit": m.rational_benefit}
            for m in getattr(brief, 'key_messages', [])
        ] if hasattr(brief, 'key_messages') and brief.key_messages else [],
        "tone_of_voice": getattr(brief, 'tone_of_voice', []),
        "mandatory_inclusions": getattr(brief, 'mandatory_inclusions', []),
        "restrictions": getattr(brief, 'restrictions', []),
        "creative_territories": [
            {"name": t.name, "concept": t.concept, "visual_direction": t.visual_direction, "tone": t.tone, "tagline_options": t.tagline_options, "risk_level": t.risk_level, "rationale": t.rationale}
            for t in getattr(brief, 'creative_territories', [])
        ] if hasattr(brief, 'creative_territories') and brief.creative_territories else [],
        "channel_strategy": [
            {"channel": c.channel, "role": c.role, "formats": c.formats, "frequency": c.frequency, "budget_allocation": c.budget_allocation}
            for c in getattr(brief, 'channel_strategy', [])
        ] if hasattr(brief, 'channel_strategy') and brief.channel_strategy else [],
        "budget": getattr(brief, 'budget', {}),
        "timeline": getattr(brief, 'timeline', {}),
        "success_metrics": getattr(brief, 'success_metrics', [])
    }


def _concept_to_dict(concept) -> dict:
    """Convert CreativeConcept to dict."""
    if not concept:
        return None
    return {
        "territory_name": getattr(concept, 'territory_name', ''),
        "concept_name": getattr(concept, 'concept_name', ''),
        "tagline": getattr(concept, 'tagline', ''),
        "concept_statement": getattr(concept, 'concept_statement', ''),
        "key_visual_idea": getattr(concept, 'key_visual_idea', ''),
        "tone_description": getattr(concept, 'tone_description', ''),
        "campaign_narrative": getattr(concept, 'campaign_narrative', ''),
        "execution_notes": getattr(concept, 'execution_notes', ''),
        "asset_count": len(concept.assets) if hasattr(concept, 'assets') and concept.assets else 0
    }


def _asset_to_dict(asset) -> dict:
    """Convert CompleteAsset to dict."""
    if not asset:
        return None

    result = {
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type,
        "platform": asset.platform,
        "name": asset.name,
        "created_at": asset.created_at.isoformat() if asset.created_at else None
    }

    if asset.copy:
        result["copy"] = {
            "format": asset.copy.format,
            "content": asset.copy.content,
            "character_count": asset.copy.character_count,
            "variations": asset.copy.variations
        }

    if asset.image:
        result["image"] = {
            "filename": asset.image.filename,
            "filepath": asset.image.filepath,
            "platform": asset.image.platform,
            "dimensions": asset.image.dimensions,
            "has_text_overlay": asset.image.has_text_overlay
        }

    if asset.video:
        result["video"] = {
            "filename": asset.video.filename,
            "filepath": asset.video.filepath,
            "duration": asset.video.duration,
            "has_voiceover": asset.video.has_voiceover
        }

    if asset.audio:
        result["audio"] = {
            "filename": asset.audio.filename,
            "filepath": asset.audio.filepath,
            "duration_seconds": asset.audio.duration_seconds
        }

    return result
