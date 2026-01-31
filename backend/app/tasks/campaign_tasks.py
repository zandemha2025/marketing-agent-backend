"""
Campaign execution tasks for Celery.

This module contains Celery tasks for:
- Campaign execution and orchestration
- Deliverable generation
- AI agent coordination
- Progress tracking and status updates
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import asdict

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from ..core.celery_app import celery_app
from ..core.config import get_settings
from ..core.database import get_database_manager
from ..repositories.campaign import CampaignRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository
from ..models.deliverable import Deliverable
from ..services.campaigns import CampaignOrchestrator, CampaignPhase

logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    Run an async coroutine safely from sync context.

    Handles the case where an event loop may already be running
    (e.g., inside some Celery worker configurations or test environments).
    Falls back to creating a new event loop if asyncio.run() fails.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # There's already a running event loop - create a new one in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


# Progress tracking - in production use Redis
_campaign_progress = {}


def _update_progress(campaign_id: str, phase: str, progress: float, message: str, details: Dict = None):
    """Update campaign progress."""
    _campaign_progress[campaign_id] = {
        "phase": phase,
        "progress": progress,
        "message": message,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(f"[{campaign_id}] {phase} - {progress}%: {message}")


def _get_sync_db_session():
    """Get a synchronous database session for Celery tasks."""
    db = get_database_manager()
    return db


@celery_app.task(bind=True, max_retries=3)
def execute_campaign_task(self, campaign_id: str, organization_id: str, config: Dict[str, Any]):
    """
    Execute a campaign asynchronously.
    
    This task:
    1. Loads the campaign from database
    2. Fetches knowledge base for the organization
    3. Runs the campaign orchestration
    4. Generates deliverables
    5. Updates campaign status
    
    Args:
        campaign_id: ID of the campaign to execute
        organization_id: Organization ID
        config: Campaign configuration
    """
    logger.info(f"Starting campaign execution task for {campaign_id}")
    
    # Update progress
    _update_progress(campaign_id, "INIT", 0, "Initializing campaign execution")
    
    try:
        # Run the async campaign execution, handling existing event loops safely
        result = _run_async(_execute_campaign_async(
            campaign_id=campaign_id,
            organization_id=organization_id,
            config=config,
            task=self
        ))

        logger.info(f"Campaign {campaign_id} execution completed with status: {result.get('status')}")
        return result

    except Exception as exc:
        logger.error(f"Campaign execution failed: {exc}", exc_info=True)

        # Update campaign status to failed
        try:
            _run_async(_update_campaign_status(campaign_id, "failed"))
        except Exception as update_exc:
            logger.error(f"Failed to update campaign status: {update_exc}")
        
        # Retry with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for campaign {campaign_id}")
            return {
                "campaign_id": campaign_id,
                "status": "failed",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat()
            }


async def _execute_campaign_async(
    campaign_id: str,
    organization_id: str,
    config: Dict[str, Any],
    task=None
) -> Dict[str, Any]:
    """
    Async campaign execution.
    
    This is the core execution logic that runs within the Celery task.
    """
    db = get_database_manager()
    settings = get_settings()
    
    async with db.session() as session:
        # Update status to in_progress
        repo = CampaignRepository(session)
        await repo.update(campaign_id, status="in_progress")
        await session.commit()
        
        _update_progress(campaign_id, "RESEARCH", 5, "Loading knowledge base")
        
        # Get knowledge base
        kb_repo = KnowledgeBaseRepository(session)
        kb = await kb_repo.get_by_organization(organization_id)
        
        knowledge_base = None
        if kb:
            knowledge_base = {
                "brand": kb.brand_data or {},
                "market": kb.market_data or {},
                "audiences": kb.audiences_data or {},
                "offerings": kb.offerings_data or {},
                "context": kb.context_data or {}
            }
            _update_progress(campaign_id, "RESEARCH", 10, "Knowledge base loaded")
        else:
            _update_progress(campaign_id, "RESEARCH", 10, "No knowledge base found, using defaults")
        
        # Build campaign request
        campaign_request = {
            "objective": config.get("objective", ""),
            "product_focus": config.get("product_focus"),
            "target_audience": config.get("target_audience"),
            "budget_tier": config.get("budget_tier", "medium"),
            "timeline": config.get("timeline", "4 weeks"),
            "platforms": config.get("platforms"),
            "brand_url": config.get("brand_url"),
            "brand_name": knowledge_base.get("brand", {}).get("name", "") if knowledge_base else ""
        }
        
        # Initialize orchestrator
        _update_progress(campaign_id, "STRATEGY", 15, "Initializing AI orchestrator")
        
        orchestrator = CampaignOrchestrator(
            openrouter_api_key=settings.openrouter_api_key,
            firecrawl_api_key=settings.firecrawl_api_key or "",
            perplexity_api_key=settings.perplexity_api_key or "",
            segmind_api_key=settings.segmind_api_key or "",
            elevenlabs_api_key=settings.elevenlabs_api_key or "",
            output_dir="outputs"
        )
        
        # Set up progress callback
        async def progress_callback(progress):
            _update_progress(
                campaign_id,
                progress.phase.value,
                progress.progress,
                progress.message,
                progress.details
            )
        
        orchestrator.set_progress_callback(progress_callback)
        
        try:
            # Execute campaign
            _update_progress(campaign_id, "STRATEGY", 20, "Starting campaign orchestration")
            
            result = await orchestrator.execute_campaign(
                campaign_request=campaign_request,
                knowledge_base=knowledge_base,
                skip_research=bool(knowledge_base)
            )
            
            _update_progress(campaign_id, "PRODUCTION", 90, "Saving campaign results")
            
            # Save results to database
            await _save_campaign_results(
                session=session,
                campaign_id=campaign_id,
                result=result
            )
            
            # Generate deliverables
            _update_progress(campaign_id, "PRODUCTION", 95, "Creating deliverables")
            deliverables = await _create_deliverables(
                session=session,
                campaign_id=campaign_id,
                result=result
            )
            
            # Update final status
            final_status = "completed" if result.status == "complete" else "failed"
            await repo.update(
                campaign_id,
                status=final_status,
                brief_data=_brief_to_dict(result.brief) if result.brief else None,
                creative_concepts=[_concept_to_dict(c) for c in result.concepts],
                selected_concept_index=0 if result.concepts else None
            )
            await session.commit()
            
            _update_progress(campaign_id, "COMPLETE", 100, "Campaign execution complete")
            
            return {
                "campaign_id": campaign_id,
                "status": final_status,
                "deliverables_count": len(deliverables),
                "concepts_count": len(result.concepts),
                "assets_count": len(result.assets),
                "duration_seconds": result.total_duration_seconds,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            await orchestrator.close()


async def _save_campaign_results(session, campaign_id: str, result):
    """Save campaign results to database."""
    # Results are saved in the campaign update above
    pass


async def _create_deliverables(
    session,
    campaign_id: str,
    result
) -> List[Deliverable]:
    """
    Create deliverable records from campaign result.
    
    Creates deliverables for:
    - Copy/content
    - Strategy documents
    - Creative concepts
    """
    deliverables = []
    
    # Create deliverable for the brief/strategy
    if result.brief:
        brief_content = _format_brief_content(result.brief)
        brief_deliverable = Deliverable(
            campaign_id=campaign_id,
            title=f"Campaign Strategy: {result.brief.campaign_name}",
            type="STRATEGY",
            content=brief_content,
            platform="",
            status="completed"
        )
        session.add(brief_deliverable)
        deliverables.append(brief_deliverable)
    
    # Create deliverables for creative concepts
    for i, concept in enumerate(result.concepts):
        concept_content = _format_concept_content(concept)
        concept_deliverable = Deliverable(
            campaign_id=campaign_id,
            title=f"Creative Concept {i+1}: {concept.concept_name}",
            type="CONCEPT",
            content=concept_content,
            platform="",
            status="completed"
        )
        session.add(concept_deliverable)
        deliverables.append(concept_deliverable)
        
        # Create copy deliverables from concept assets
        for asset in concept.assets:
            for copy_var in asset.copy:
                copy_deliverable = Deliverable(
                    campaign_id=campaign_id,
                    title=f"{copy_var.format.replace('_', ' ').title()} - {concept.concept_name}",
                    type="COPY",
                    content=copy_var.content,
                    platform=asset.platform,
                    status="completed"
                )
                session.add(copy_deliverable)
                deliverables.append(copy_deliverable)
    
    # Create deliverables for generated assets
    for asset in result.assets:
        if asset.copy:
            asset_deliverable = Deliverable(
                campaign_id=campaign_id,
                title=f"Asset: {asset.name}",
                type="ASSET",
                content=asset.copy.content if asset.copy else "",
                platform=asset.platform,
                status="completed"
            )
            session.add(asset_deliverable)
            deliverables.append(asset_deliverable)

    # Research Report
    if getattr(result, "research_report", ""):
        d = Deliverable(
            campaign_id=campaign_id,
            title="Research Report",
            type="RESEARCH_REPORT",
            content=result.research_report,
            platform="",
            status="completed"
        )
        session.add(d)
        deliverables.append(d)

    # Competitive Analysis
    if getattr(result, "competitive_analysis", ""):
        d = Deliverable(
            campaign_id=campaign_id,
            title="Competitive Analysis",
            type="COMPETITIVE_ANALYSIS",
            content=result.competitive_analysis,
            platform="",
            status="completed"
        )
        session.add(d)
        deliverables.append(d)

    # Media Plan
    if getattr(result, "media_plan", ""):
        d = Deliverable(
            campaign_id=campaign_id,
            title="Media Plan",
            type="MEDIA_PLAN",
            content=result.media_plan,
            platform="",
            status="completed"
        )
        session.add(d)
        deliverables.append(d)

    # Headlines (one deliverable with all headlines)
    headlines = getattr(result, "headlines", [])
    if headlines:
        headline_content = "\n".join(f"- {h}" for h in headlines)
        d = Deliverable(
            campaign_id=campaign_id,
            title=f"Campaign Headlines ({len(headlines)} variations)",
            type="HEADLINE",
            content=headline_content,
            platform="",
            status="completed"
        )
        session.add(d)
        deliverables.append(d)

    # Body Copy (one deliverable per variation)
    body_copy_variations = getattr(result, "body_copy_variations", [])
    for idx, copy_text in enumerate(body_copy_variations, 1):
        d = Deliverable(
            campaign_id=campaign_id,
            title=f"Body Copy Variation {idx}",
            type="BODY_COPY",
            content=copy_text,
            platform="",
            status="completed"
        )
        session.add(d)
        deliverables.append(d)

    # Social Posts (one deliverable per post, with platform field set)
    social_posts = getattr(result, "social_posts", {})
    for platform_name, posts in social_posts.items():
        for post_idx, post_text in enumerate(posts, 1):
            d = Deliverable(
                campaign_id=campaign_id,
                title=f"Social Post - {platform_name.title()} #{post_idx}",
                type="SOCIAL_POST",
                content=post_text,
                platform=platform_name,
                status="completed"
            )
            session.add(d)
            deliverables.append(d)

    # Video Scripts
    video_scripts = getattr(result, "video_scripts", [])
    for idx, script_text in enumerate(video_scripts, 1):
        d = Deliverable(
            campaign_id=campaign_id,
            title=f"Video Script {idx}",
            type="VIDEO_SCRIPT",
            content=script_text,
            platform="",
            status="completed"
        )
        session.add(d)
        deliverables.append(d)

    # Display Ads (one per size)
    display_ad_copy = getattr(result, "display_ad_copy", {})
    for size, ad_content in display_ad_copy.items():
        d = Deliverable(
            campaign_id=campaign_id,
            title=f"Display Ad - {size}",
            type="DISPLAY_AD",
            content=ad_content,
            platform="display",
            status="completed"
        )
        session.add(d)
        deliverables.append(d)

    await session.commit()
    return deliverables


async def _update_campaign_status(campaign_id: str, status: str):
    """Update campaign status."""
    db = get_database_manager()
    async with db.session() as session:
        repo = CampaignRepository(session)
        await repo.update(campaign_id, status=status)
        await session.commit()


def _brief_to_dict(brief) -> Dict[str, Any]:
    """Convert brief to dictionary."""
    if hasattr(brief, 'to_dict'):
        return brief.to_dict()
    return {
        "campaign_name": getattr(brief, 'campaign_name', ''),
        "campaign_type": getattr(brief, 'campaign_type', ''),
        "executive_summary": getattr(brief, 'executive_summary', ''),
        "key_insight": getattr(brief, 'key_insight', ''),
        "strategic_proposition": getattr(brief, 'strategic_proposition', ''),
    }


def _concept_to_dict(concept) -> Dict[str, Any]:
    """Convert concept to dictionary."""
    return {
        "territory_name": concept.territory_name,
        "concept_name": concept.concept_name,
        "tagline": concept.tagline,
        "concept_statement": concept.concept_statement,
        "key_visual_idea": concept.key_visual_idea,
        "tone_description": concept.tone_description,
        "campaign_narrative": concept.campaign_narrative,
        "execution_notes": concept.execution_notes,
        "asset_count": len(concept.assets)
    }


def _format_brief_content(brief) -> str:
    """Format brief as readable content."""
    sections = []
    
    sections.append(f"# {brief.campaign_name}")
    sections.append(f"\n## Executive Summary\n{brief.executive_summary}")
    sections.append(f"\n## Business Context\n{brief.business_context}")
    sections.append(f"\n## Market Situation\n{brief.market_situation}")
    sections.append(f"\n## Key Insight\n{brief.key_insight}")
    sections.append(f"\n## Strategic Proposition\n{brief.strategic_proposition}")
    
    if brief.objectives:
        sections.append("\n## Objectives")
        for obj in brief.objectives:
            sections.append(f"- {obj.objective}: {obj.target} ({obj.metric})")
    
    if brief.key_messages:
        sections.append("\n## Key Messages")
        for msg in brief.key_messages:
            sections.append(f"- {msg.message}")
            if msg.proof_points:
                sections.append(f"  Proof points: {', '.join(msg.proof_points)}")
    
    return "\n".join(sections)


def _format_concept_content(concept) -> str:
    """Format concept as readable content."""
    sections = []
    
    sections.append(f"# {concept.concept_name}")
    sections.append(f"\n## Tagline\n{concept.tagline}")
    sections.append(f"\n## Concept Statement\n{concept.concept_statement}")
    sections.append(f"\n## Key Visual Idea\n{concept.key_visual_idea}")
    sections.append(f"\n## Tone\n{concept.tone_description}")
    
    if concept.campaign_narrative:
        sections.append(f"\n## Campaign Narrative\n{concept.campaign_narrative}")
    
    if concept.assets:
        sections.append(f"\n## Assets ({len(concept.assets)})")
        for asset in concept.assets:
            sections.append(f"\n### {asset.asset_type} for {asset.platform}")
            sections.append(f"Dimensions: {asset.dimensions}")
            if asset.copy:
                for copy in asset.copy:
                    sections.append(f"\n**{copy.format}:** {copy.content}")
    
    return "\n".join(sections)


def get_campaign_progress(campaign_id: str) -> Dict[str, Any]:
    """
    Get the current progress of a campaign execution.
    
    This is a regular function (not a Celery task) that can be called
    directly to check progress stored in memory.
    
    Args:
        campaign_id: ID of the campaign
        
    Returns:
        Progress information
    """
    return _campaign_progress.get(campaign_id, {
        "phase": "UNKNOWN",
        "progress": 0,
        "message": "No progress information available"
    })


@celery_app.task(bind=True, max_retries=3)
def generate_copy_task(
    self,
    campaign_id: str,
    deliverable_type: str,
    platform: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate copy for a specific deliverable type.
    
    Args:
        campaign_id: Campaign ID
        deliverable_type: Type of copy (headline, body, cta, etc.)
        platform: Target platform
        context: Context for generation
    """
    logger.info(f"Generating {deliverable_type} copy for {platform}")
    
    try:
        settings = get_settings()
        
        # This would call the copywriter agent
        # For now, return a placeholder
        return {
            "campaign_id": campaign_id,
            "type": deliverable_type,
            "platform": platform,
            "content": f"Generated {deliverable_type} for {platform}",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Copy generation failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def generate_image_task(
    self,
    campaign_id: str,
    prompt: str,
    platform: str,
    dimensions: str
) -> Dict[str, Any]:
    """
    Generate an image for a campaign.
    
    Args:
        campaign_id: Campaign ID
        prompt: Image generation prompt
        platform: Target platform
        dimensions: Image dimensions
    """
    logger.info(f"Generating image for {platform}")
    
    try:
        settings = get_settings()
        
        # This would call the image generation service
        return {
            "campaign_id": campaign_id,
            "platform": platform,
            "dimensions": dimensions,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Image generation failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
