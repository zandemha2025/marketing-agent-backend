"""
Campaign API endpoints.

Full campaign workflow with WebSocket progress updates.
"""
import asyncio
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.config import get_settings
from ..core.database import get_session
from ..services.campaigns import (
    CampaignOrchestrator,
    CampaignResult,
    CampaignProgress,
    CampaignPhase,
    run_campaign
)
from ..repositories.campaign import CampaignRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository

router = APIRouter()

# In-memory store for active campaign sessions
# In production, use Redis
active_campaigns = {}


# === Pydantic Models ===

class CampaignCreateRequest(BaseModel):
    """Request to create a new campaign."""
    organization_id: str
    name: str
    objective: str = Field(..., description="What the campaign aims to achieve")
    product_focus: Optional[str] = Field(None, description="Specific product/service to promote")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    budget_tier: str = Field("medium", description="Budget tier: low, medium, high")
    timeline: str = Field("4 weeks", description="Campaign timeline")
    platforms: Optional[List[str]] = Field(None, description="Target platforms")
    brand_url: Optional[str] = Field(None, description="Brand website for research")


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
    session=Depends(get_session)
):
    """List campaigns for an organization."""
    repo = CampaignRepository(session)

    if status:
        campaigns = await repo.get_by_status(organization_id, status, limit, offset)
    else:
        campaigns = await repo.get_by_organization(organization_id, limit, offset)

    total = await repo.count_by_organization(organization_id)

    return CampaignListResponse(
        campaigns=[
            CampaignResponse(
                id=c.id,
                organization_id=c.organization_id,
                name=c.name,
                status=c.status,
                objective=c.objective or "",
                created_at=c.created_at,
                brief=c.brief_data,
                concepts=c.creative_concepts,
                selected_concept_index=c.selected_concept_index,
                asset_count=len(c.assets) if hasattr(c, 'assets') else 0
            )
            for c in campaigns
        ],
        total=total
    )


@router.post("/", response_model=CampaignResponse)
async def create_campaign(
    request: CampaignCreateRequest,
    background_tasks: BackgroundTasks,
    session=Depends(get_session)
):
    """
    Create a new campaign.

    This initializes the campaign and returns immediately.
    Use WebSocket endpoint to track execution progress.
    """
    repo = CampaignRepository(session)

    # Create campaign record
    campaign = await repo.create(
        organization_id=request.organization_id,
        name=request.name,
        status="draft",
        objective=request.objective,
        config={
            "product_focus": request.product_focus,
            "target_audience": request.target_audience,
            "budget_tier": request.budget_tier,
            "timeline": request.timeline,
            "platforms": request.platforms,
            "brand_url": request.brand_url
        }
    )

    return CampaignResponse(
        id=campaign.id,
        organization_id=campaign.organization_id,
        name=campaign.name,
        status=campaign.status,
        objective=campaign.objective or "",
        created_at=campaign.created_at,
        asset_count=0
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    session=Depends(get_session)
):
    """Get campaign details."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

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
        asset_count=len(campaign.assets) if hasattr(campaign, 'assets') else 0
    )


@router.post("/{campaign_id}/execute")
async def execute_campaign(
    campaign_id: str,
    session=Depends(get_session)
):
    """
    Start campaign execution.

    Returns a session ID to connect via WebSocket for progress updates.
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

    # Update status
    await repo.update(campaign_id, status="queued")

    # Store session info
    import uuid
    session_id = uuid.uuid4().hex

    active_campaigns[session_id] = {
        "campaign_id": campaign_id,
        "organization_id": campaign.organization_id,
        "config": campaign.config,
        "status": "queued",
        "websocket": None
    }

    return {
        "session_id": session_id,
        "websocket_url": f"/api/campaigns/{campaign_id}/ws/{session_id}",
        "message": "Connect to WebSocket to start execution and receive progress updates"
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
    session=Depends(get_session)
):
    """Delete a campaign."""
    repo = CampaignRepository(session)
    campaign = await repo.get_by_id(campaign_id)

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await repo.delete(campaign_id)

    return {"status": "deleted", "id": campaign_id}


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
        async with get_session() as session:
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
        async with get_session() as session:
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
    """Convert CreativeBrief to dict."""
    if not brief:
        return None
    return {
        "campaign_name": brief.campaign_name,
        "executive_summary": brief.executive_summary,
        "business_context": brief.business_context,
        "market_situation": brief.market_situation,
        "competitive_landscape": brief.competitive_landscape,
        "objectives": brief.objectives,
        "target_audiences": brief.target_audiences,
        "key_messages": brief.key_messages,
        "creative_territories": brief.creative_territories,
        "channel_strategy": brief.channel_strategy,
        "success_metrics": brief.success_metrics,
        "constraints": brief.constraints,
        "timeline": brief.timeline
    }


def _concept_to_dict(concept) -> dict:
    """Convert CreativeConcept to dict."""
    if not concept:
        return None
    return {
        "name": concept.name,
        "tagline": concept.tagline,
        "concept_summary": concept.concept_summary,
        "visual_direction": concept.visual_direction,
        "tone_and_voice": concept.tone_and_voice,
        "key_visuals": concept.key_visuals,
        "messaging_framework": concept.messaging_framework,
        "asset_specs": concept.asset_specs,
        "territory_name": concept.territory_name
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
