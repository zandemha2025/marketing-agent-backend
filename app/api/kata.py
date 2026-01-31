"""
Kata Engine API Endpoints.

Provides REST API access to:
- Synthetic influencer generation
- Product compositing
- Video manipulation
- Voice generation
- Quality assessment
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.config import get_settings, Settings
from ..services.kata.orchestrator import (
    KataOrchestrator,
    KataJob,
    KataJobType,
    KataJobStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store for jobs (use Redis in production)
_jobs: dict = {}
_orchestrator: KataOrchestrator = None


def get_orchestrator(settings: Settings = Depends(get_settings)) -> KataOrchestrator:
    """Get or create Kata orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = KataOrchestrator(
            replicate_api_key=settings.replicate_api_key if hasattr(settings, 'replicate_api_key') else None,
            runway_api_key=settings.runway_api_key if hasattr(settings, 'runway_api_key') else None,
            elevenlabs_api_key=settings.elevenlabs_api_key if hasattr(settings, 'elevenlabs_api_key') else None,
            segmind_api_key=settings.segmind_api_key if hasattr(settings, 'segmind_api_key') else None,
        )
    return _orchestrator


# === Request/Response Models ===

class SyntheticInfluencerRequest(BaseModel):
    """Request to create a synthetic influencer video."""
    product_images: List[str] = Field(..., description="URLs/paths to product images")
    product_description: str = Field(..., description="Description of the product")
    script: str = Field(..., description="What the influencer should say")
    influencer_style: str = Field("casual", description="Style: casual, professional, energetic")
    target_platform: str = Field("tiktok", description="Target platform")
    voice_style: str = Field("friendly", description="Voice style")
    voice_gender: str = Field("female", description="Voice gender: male, female")


class ProductCompositeRequest(BaseModel):
    """Request to composite a product into video."""
    video_url: str = Field(..., description="URL/path to source video")
    product_images: List[str] = Field(..., description="Product images to composite")
    product_description: str = Field("", description="Product description")
    placement_style: str = Field("natural", description="Placement style")


class VideoMergeRequest(BaseModel):
    """Request to merge two videos."""
    video_a: str = Field(..., description="First video URL/path")
    video_b: str = Field(..., description="Second video URL/path")
    merge_style: str = Field("blend", description="Merge style: blend, overlay, split_screen")


class UGCStyleRequest(BaseModel):
    """Request to apply UGC styling."""
    video_url: str = Field(..., description="Video to style")
    platform: str = Field("tiktok", description="Target platform style")


class VoiceGenerateRequest(BaseModel):
    """Request to generate voice audio."""
    text: str = Field(..., description="Text to speak")
    voice_style: str = Field("friendly", description="Voice style")
    gender: str = Field("female", description="Voice gender")


class CreateInfluencerRequest(BaseModel):
    """Request to create a reusable influencer persona."""
    name: str = Field(..., description="Name for the influencer")
    style: str = Field("casual", description="Persona style")
    demographic: str = Field("millennial", description="Target demographic")
    voice_style: str = Field("friendly", description="Voice style")
    voice_gender: str = Field("female", description="Voice gender")


class KataJobResponse(BaseModel):
    """Response with job information."""
    job_id: str
    job_type: str
    status: str
    progress: float
    message: str
    output_url: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime


class KataResultResponse(BaseModel):
    """Response with completed job result."""
    job_id: str
    success: bool
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: float = 0.0
    realism_score: float = 0.0
    brand_safety_score: float = 0.0
    error: Optional[str] = None


# === Endpoints ===

@router.post("/synthetic-influencer", response_model=KataJobResponse)
async def create_synthetic_influencer(
    request: SyntheticInfluencerRequest,
    background_tasks: BackgroundTasks,
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
):
    """
    Generate a synthetic influencer video with your product.

    This is THE killer feature - creates an AI influencer:
    1. Generates realistic AI human
    2. Has them hold/interact with your product
    3. Voices them speaking your script
    4. Outputs platform-ready video

    Returns a job ID to track progress.
    """
    import uuid
    job_id = uuid.uuid4().hex[:12]

    job = KataJob(
        id=job_id,
        job_type=KataJobType.SYNTHETIC_INFLUENCER,
        status=KataJobStatus.PENDING,
        product_images=request.product_images,
        product_description=request.product_description,
        script=request.script,
        influencer_style=request.influencer_style,
        target_platform=request.target_platform,
        voice_style=request.voice_style,
        message="Job queued",
    )

    _jobs[job_id] = job

    # Run in background
    background_tasks.add_task(
        _run_synthetic_influencer,
        orchestrator,
        job,
        request,
    )

    return KataJobResponse(
        job_id=job.id,
        job_type=job.job_type.value,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
    )


@router.post("/composite-product", response_model=KataJobResponse)
async def composite_product(
    request: ProductCompositeRequest,
    background_tasks: BackgroundTasks,
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
):
    """
    Composite a product naturally into an existing video.

    Takes a video and seamlessly places your product in it:
    - Analyzes scene for best placement zones
    - Adds realistic shadows
    - Matches lighting conditions
    """
    import uuid
    job_id = uuid.uuid4().hex[:12]

    job = KataJob(
        id=job_id,
        job_type=KataJobType.PRODUCT_PLACEMENT,
        status=KataJobStatus.PENDING,
        source_video=request.video_url,
        product_images=request.product_images,
        product_description=request.product_description,
        message="Job queued",
    )

    _jobs[job_id] = job

    background_tasks.add_task(
        _run_product_composite,
        orchestrator,
        job,
        request,
    )

    return KataJobResponse(
        job_id=job.id,
        job_type=job.job_type.value,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
    )


@router.post("/merge-videos", response_model=KataJobResponse)
async def merge_videos(
    request: VideoMergeRequest,
    background_tasks: BackgroundTasks,
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
):
    """
    Merge two videos together.

    Supports multiple merge styles:
    - blend: Smooth alpha blend
    - overlay: Video B on top of Video A
    - split_screen: Side by side
    - picture_in_picture: Video B in corner
    """
    import uuid
    job_id = uuid.uuid4().hex[:12]

    job = KataJob(
        id=job_id,
        job_type=KataJobType.VIDEO_COMPOSITE,
        status=KataJobStatus.PENDING,
        source_video=request.video_a,
        overlay_content=request.video_b,
        message="Job queued",
    )

    _jobs[job_id] = job

    background_tasks.add_task(
        _run_video_merge,
        orchestrator,
        job,
        request,
    )

    return KataJobResponse(
        job_id=job.id,
        job_type=job.job_type.value,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
    )


@router.post("/ugc-style", response_model=KataJobResponse)
async def apply_ugc_style(
    request: UGCStyleRequest,
    background_tasks: BackgroundTasks,
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
):
    """
    Apply UGC (User Generated Content) styling to a video.

    Makes polished content look like authentic user-generated content:
    - Adds subtle camera shake
    - Realistic lighting variations
    - Minor imperfections
    - Platform-specific styling
    """
    import uuid
    job_id = uuid.uuid4().hex[:12]

    job = KataJob(
        id=job_id,
        job_type=KataJobType.UGC_STYLE,
        status=KataJobStatus.PENDING,
        source_video=request.video_url,
        target_platform=request.platform,
        message="Job queued",
    )

    _jobs[job_id] = job

    background_tasks.add_task(
        _run_ugc_style,
        orchestrator,
        job,
        request,
    )

    return KataJobResponse(
        job_id=job.id,
        job_type=job.job_type.value,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
    )


@router.post("/generate-voice")
async def generate_voice(
    request: VoiceGenerateRequest,
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
):
    """
    Generate voice audio from text using ElevenLabs.

    Returns audio file that can be used with synthetic influencers.
    """
    result = await orchestrator.voice_generator.generate_speech(
        text=request.text,
        voice_style=request.voice_style,
        gender=request.gender,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return {
        "success": True,
        "audio_url": result.audio_path,
        "duration_seconds": result.duration_seconds,
        "voice_id": result.voice_id,
    }


@router.post("/influencers", response_model=dict)
async def create_influencer_persona(
    request: CreateInfluencerRequest,
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
):
    """
    Create a reusable synthetic influencer persona.

    This influencer can be used for multiple videos to maintain
    brand consistency.
    """
    from ..services.kata.synthetic.influencer_generator import (
        InfluencerStyle,
        InfluencerDemographic,
    )

    influencer = await orchestrator.influencer_generator.create_influencer(
        name=request.name,
        style=InfluencerStyle(request.style) if request.style in [s.value for s in InfluencerStyle] else InfluencerStyle.CASUAL,
        demographic=InfluencerDemographic(request.demographic) if request.demographic in [d.value for d in InfluencerDemographic] else InfluencerDemographic.MILLENNIAL,
        voice_style=request.voice_style,
        voice_gender=request.voice_gender,
    )

    return influencer.to_dict()


@router.get("/influencers")
async def list_influencers(
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
):
    """List all created influencer personas."""
    influencers = orchestrator.influencer_generator.list_influencers()
    return {
        "influencers": [i.to_dict() for i in influencers],
        "total": len(influencers),
    }


@router.get("/jobs/{job_id}", response_model=KataJobResponse)
async def get_job_status(job_id: str):
    """Get the status of a Kata job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]

    return KataJobResponse(
        job_id=job.id,
        job_type=job.job_type.value,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        output_url=job.output_url,
        error=job.error,
        created_at=job.created_at,
    )


@router.get("/jobs/{job_id}/result", response_model=KataResultResponse)
async def get_job_result(job_id: str):
    """Get the result of a completed Kata job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]

    if job.status != KataJobStatus.COMPLETE:
        raise HTTPException(
            status_code=400,
            detail=f"Job not complete. Status: {job.status.value}"
        )

    return KataResultResponse(
        job_id=job.id,
        success=True,
        video_url=job.output_url,
        thumbnail_url=job.thumbnail_url,
        duration_seconds=job.duration_seconds,
        realism_score=job.realism_score,
        brand_safety_score=job.brand_safety_score,
    )


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 20,
):
    """List all Kata jobs."""
    jobs = list(_jobs.values())

    if status:
        jobs = [j for j in jobs if j.status.value == status]

    # Sort by created_at descending
    jobs.sort(key=lambda j: j.created_at, reverse=True)

    return {
        "jobs": [
            KataJobResponse(
                job_id=j.id,
                job_type=j.job_type.value,
                status=j.status.value,
                progress=j.progress,
                message=j.message,
                output_url=j.output_url,
                error=j.error,
                created_at=j.created_at,
            )
            for j in jobs[:limit]
        ],
        "total": len(jobs),
    }


# === Background Task Runners ===

async def _run_synthetic_influencer(
    orchestrator: KataOrchestrator,
    job: KataJob,
    request: SyntheticInfluencerRequest,
):
    """Background task for synthetic influencer generation."""
    try:
        async def progress_callback(updated_job: KataJob):
            _jobs[job.id] = updated_job

        result = await orchestrator.create_synthetic_influencer(
            product_images=request.product_images,
            product_description=request.product_description,
            script=request.script,
            influencer_style=request.influencer_style,
            target_platform=request.target_platform,
            voice_style=request.voice_style,
            voice_gender=request.voice_gender,
            progress_callback=progress_callback,
        )

        job.status = KataJobStatus.COMPLETE if result.success else KataJobStatus.FAILED
        job.output_url = result.video_url
        job.thumbnail_url = result.thumbnail_url
        job.duration_seconds = result.duration_seconds
        job.realism_score = result.realism_score
        job.brand_safety_score = result.brand_safety_score
        job.error = result.error
        job.progress = 1.0

    except Exception as e:
        logger.error(f"Synthetic influencer job failed: {e}")
        job.status = KataJobStatus.FAILED
        job.error = str(e)

    _jobs[job.id] = job


async def _run_product_composite(
    orchestrator: KataOrchestrator,
    job: KataJob,
    request: ProductCompositeRequest,
):
    """Background task for product compositing."""
    try:
        result = await orchestrator.composite_product_into_video(
            video_path=request.video_url,
            product_images=request.product_images,
            product_description=request.product_description,
            placement_style=request.placement_style,
        )

        job.status = KataJobStatus.COMPLETE if result.success else KataJobStatus.FAILED
        job.output_url = result.video_url
        job.error = result.error
        job.progress = 1.0

    except Exception as e:
        logger.error(f"Product composite job failed: {e}")
        job.status = KataJobStatus.FAILED
        job.error = str(e)

    _jobs[job.id] = job


async def _run_video_merge(
    orchestrator: KataOrchestrator,
    job: KataJob,
    request: VideoMergeRequest,
):
    """Background task for video merging."""
    try:
        result = await orchestrator.merge_videos(
            video_a=request.video_a,
            video_b=request.video_b,
            merge_style=request.merge_style,
        )

        job.status = KataJobStatus.COMPLETE if result.success else KataJobStatus.FAILED
        job.output_url = result.video_url
        job.error = result.error
        job.progress = 1.0

    except Exception as e:
        logger.error(f"Video merge job failed: {e}")
        job.status = KataJobStatus.FAILED
        job.error = str(e)

    _jobs[job.id] = job


async def _run_ugc_style(
    orchestrator: KataOrchestrator,
    job: KataJob,
    request: UGCStyleRequest,
):
    """Background task for UGC styling."""
    try:
        result = await orchestrator.style_as_ugc(
            video_path=request.video_url,
            platform=request.platform,
        )

        job.status = KataJobStatus.COMPLETE if result.success else KataJobStatus.FAILED
        job.output_url = result.video_url
        job.error = result.error
        job.progress = 1.0

    except Exception as e:
        logger.error(f"UGC style job failed: {e}")
        job.status = KataJobStatus.FAILED
        job.error = str(e)

    _jobs[job.id] = job
