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
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from datetime import datetime

try:
    from PIL import Image
except ImportError:
    Image = None

from ..core.config import get_settings, Settings
from .auth import get_current_active_user
from ..models.user import User
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
    """Get or create Kata orchestrator.

    Validates that at minimum the OpenRouter API key is available so the
    system can fall back to AI-generated descriptions when video/image
    generation keys (Replicate, Runway, ElevenLabs, Segmind) are absent.
    """
    global _orchestrator
    if _orchestrator is None:
        openrouter_key = getattr(settings, 'openrouter_api_key', None)
        if not openrouter_key:
            raise HTTPException(
                status_code=400,
                detail=(
                    "OPENROUTER_API_KEY is not configured. "
                    "The Kata engine requires at minimum an OpenRouter API key "
                    "to provide AI-powered content descriptions. "
                    "Set the OPENROUTER_API_KEY environment variable to proceed."
                ),
            )

        replicate_key = getattr(settings, 'replicate_api_key', None)
        runway_key = getattr(settings, 'runway_api_key', None)
        elevenlabs_key = getattr(settings, 'elevenlabs_api_key', None)
        segmind_key = getattr(settings, 'segmind_api_key', None)

        missing = []
        if not replicate_key:
            missing.append("REPLICATE_API_KEY")
        if not runway_key:
            missing.append("RUNWAY_API_KEY")
        if not elevenlabs_key:
            missing.append("ELEVENLABS_API_KEY")
        if not segmind_key:
            missing.append("SEGMIND_API_KEY")

        if missing:
            logger.warning(
                "Kata engine running in AI-description fallback mode. "
                "Missing keys: %s. Video/image/voice generation will return "
                "AI-generated descriptions instead of actual media files.",
                ", ".join(missing),
            )

        _orchestrator = KataOrchestrator(
            replicate_api_key=replicate_key,
            runway_api_key=runway_key,
            elevenlabs_api_key=elevenlabs_key,
            segmind_api_key=segmind_key,
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
    avatar_url: Optional[str] = None
    voice_url: Optional[str] = None  # Alias for audio_url
    duration_seconds: float = 0.0
    realism_score: float = 0.0
    brand_safety_score: float = 0.0
    error: Optional[str] = None
    mode: str = "live"  # "live" for real API calls, "mock" for fallback mode


# === Endpoints ===

@router.post("/synthetic-influencer", response_model=KataJobResponse)
async def create_synthetic_influencer(
    request: SyntheticInfluencerRequest,
    background_tasks: BackgroundTasks,
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
    current_user: User = Depends(get_current_active_user)
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
    current_user: User = Depends(get_current_active_user)
):
    """
    Composite a product naturally into an existing video.

    Takes a video and seamlessly places your product in it:
    - Analyzes scene for best placement zones
    - Adds realistic shadows
    - Matches lighting conditions
    """
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
    current_user: User = Depends(get_current_active_user)
):
    """
    Merge two videos together.

    Supports multiple merge styles:
    - blend: Smooth alpha blend
    - overlay: Video B on top of Video A
    - split_screen: Side by side
    - picture_in_picture: Video B in corner
    """
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
    current_user: User = Depends(get_current_active_user)
):
    """
    Apply UGC (User Generated Content) styling to a video.

    Makes polished content look like authentic user-generated content:
    - Adds subtle camera shake
    - Realistic lighting variations
    - Minor imperfections
    - Platform-specific styling
    """
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
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate voice audio from text using ElevenLabs.

    Returns audio file that can be used with synthetic influencers.
    Falls back to an AI-generated voice description when the
    ElevenLabs API key is not configured.
    """
    if orchestrator.voice_generator is None or not orchestrator.has_voice_key:
        # Fallback: use LLM to describe what the voice would sound like
        from ..services.ai.openrouter import llm

        prompt = (
            f"Describe in detail what a {request.voice_style} {request.gender} "
            f"voice reading the following script would sound like. "
            f"Include pacing, emphasis, tone shifts, and emotional beats.\n\n"
            f"Script:\n{request.text}"
        )
        description = await llm(prompt)
        word_count = len(request.text.split())
        estimated_duration = word_count / 2.5

        logger.warning(
            "Voice generation running in AI-description fallback mode. "
            "Set ELEVENLABS_API_KEY for actual audio generation."
        )

        return {
            "success": True,
            "audio_url": None,
            "duration_seconds": estimated_duration,
            "voice_id": None,
            "fallback_mode": True,
            "voice_description": description.strip(),
            "message": (
                "AI-description fallback: actual voice generation "
                "requires ELEVENLABS_API_KEY."
            ),
        }

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
    current_user: User = Depends(get_current_active_user)
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
    current_user: User = Depends(get_current_active_user)
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


class ScriptGenerateRequest(BaseModel):
    """Request to generate a script."""
    format: str = Field("tiktok", description="Script format (tiktok, youtube, product_demo, etc.)")
    answers: dict = Field(..., description="User answers to script questions")
    organization_id: Optional[str] = Field(None, description="Organization ID for context")


class ScriptGenerateResponse(BaseModel):
    """Response with generated script."""
    script: str
    format: str
    estimated_duration_seconds: int


@router.post("/generate-script", response_model=ScriptGenerateResponse)
async def generate_script(
    request: ScriptGenerateRequest,
    orchestrator: KataOrchestrator = Depends(get_orchestrator),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a script based on user answers.

    Uses AI to create platform-optimized scripts from user questionnaire answers.
    """
    try:
        # Build a prompt based on the format and answers
        format_config = {
            'tiktok': {'name': 'TikTok/Reels', 'max_length': 60, 'style': 'short, punchy, engaging'},
            'youtube': {'name': 'YouTube Short', 'max_length': 60, 'style': 'story-driven, hook-focused'},
            'product_demo': {'name': 'Product Demo', 'max_length': 90, 'style': 'informative, feature-focused'},
            'testimonial': {'name': 'Testimonial', 'max_length': 45, 'style': 'authentic, personal'},
            'educational': {'name': 'Educational', 'max_length': 60, 'style': 'helpful, clear, informative'},
        }

        fmt = format_config.get(request.format, format_config['tiktok'])
        answers_text = "\n".join([f"{k}: {v}" for k, v in request.answers.items()])

        prompt = f"""You are an expert copywriter specializing in short-form video scripts.

Format: {fmt['name']}
Target Length: {fmt['max_length']} seconds
Style: {fmt['style']}

User Input:
{answers_text}

Create a compelling script that:
1. Has a strong hook in the first 3 seconds
2. Follows the natural flow of the format
3. Includes a clear call-to-action
4. Sounds natural when spoken aloud
5. Fits within the target time limit

Return ONLY the script text, formatted for speaking. No stage directions, no markdown, just the spoken words."""

        # Generate the script using the LLM
        from ..services.ai.openrouter import llm
        script = await llm(prompt)

        # Clean up the script
        script = script.strip()
        if script.startswith('"') and script.endswith('"'):
            script = script[1:-1]

        # Estimate duration (average speaking rate ~150 words per minute = 2.5 words per second)
        word_count = len(script.split())
        estimated_duration = int(word_count / 2.5)

        return ScriptGenerateResponse(
            script=script,
            format=request.format,
            estimated_duration_seconds=estimated_duration
        )

    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Script generation failed: {str(e)}")


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

        logger.info(f"Synthetic influencer result: success={result.success}, error={result.error}")
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


# === Halftime/Grok Video Engine Endpoints ===

class HalftimeAnalyzeRequest(BaseModel):
    """Request to analyze video with Grok scene analyzer."""
    video_url: str = Field(..., description="URL to video file")
    num_keyframes: int = Field(default=8, ge=4, le=16, description="Number of keyframes to analyze")


class HalftimeAnalyzeResponse(BaseModel):
    """Response with video analysis."""
    success: bool
    duration_seconds: float
    resolution: Tuple[int, int]
    overall_mood: str
    narrative_arc: List[str]
    recommended_insertion_frames: List[int]
    dominant_colors: List[str]
    scenes: List[Dict[str, Any]]
    error: Optional[str] = None


class HalftimePlacementRequest(BaseModel):
    """Request to detect insertion zones."""
    video_url: str
    product_type: str = Field(..., description="Type of product (beverage, electronics, etc.)")
    product_size: str = Field(default="medium", description="small, medium, large")
    placement_style: str = Field(default="natural", description="natural, prominent, subtle, dynamic")


class HalftimePlacementResponse(BaseModel):
    """Response with placement recommendations."""
    success: bool
    zones: List[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]] = None
    confidence: float
    reasoning: str
    error: Optional[str] = None


class HalftimeCompositeRequest(BaseModel):
    """Request to composite product into video."""
    video_url: str
    product_description: str
    product_type: str = "product"
    platform: str = Field(default="tiktok", description="tiktok, instagram, youtube")
    style: str = Field(default="natural", description="natural, prominent, subtle, ugc")
    ugc_effects: bool = Field(default=False, description="Apply UGC-style effects")
    start_time: float = Field(default=0.0, description="Start time in seconds")
    duration: Optional[float] = Field(default=None, description="Duration in seconds (None for full)")


class HalftimeCompositeResponse(BaseModel):
    """Response with composited video."""
    success: bool
    output_url: Optional[str] = None
    output_path: Optional[str] = None
    duration_seconds: float
    frames_processed: int
    placement_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/halftime/analyze", response_model=HalftimeAnalyzeResponse)
async def halftime_analyze_video(
    request: HalftimeAnalyzeRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Analyze video using Grok AI for scene understanding.
    
    This endpoint uses xAI's Grok Vision API to analyze video frames
    and extract scene context, lighting, mood, and objects.
    """
    from ..services.kata.grok_scene_analyzer import GrokSceneAnalyzer
    
    api_key = getattr(settings, 'xai_api_key', None) or os.environ.get('XAI_API_KEY')
    
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="XAI_API_KEY not configured"
        )
    
    try:
        # Download video if URL
        video_path = request.video_url
        if request.video_url.startswith('http'):
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(request.video_url)
                response.raise_for_status()
                
                # Save to temp file
                suffix = Path(request.video_url).suffix or '.mp4'
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(response.content)
                    video_path = tmp.name
        
        # Analyze video
        analyzer = GrokSceneAnalyzer(api_key=api_key)
        analysis = await analyzer.analyze_video(video_path, num_keyframes=request.num_keyframes)
        await analyzer.close()
        
        # Clean up temp file if downloaded
        if video_path != request.video_url and os.path.exists(video_path):
            os.unlink(video_path)
        
        # Convert scenes to dict
        scenes = []
        for scene in analysis.keyframe_scenes:
            scenes.append({
                "timestamp": scene.timestamp,
                "scene_type": scene.scene_type,
                "activity": scene.activity,
                "mood": scene.mood,
                "location": scene.location_description,
                "lighting": {
                    "type": scene.lighting.type,
                    "direction": scene.lighting.direction,
                    "intensity": scene.lighting.intensity,
                    "color_temperature": scene.lighting.color_temperature,
                },
                "people_count": scene.people_count,
                "main_subject": scene.main_subject,
                "composition": scene.composition_style,
            })
        
        return HalftimeAnalyzeResponse(
            success=True,
            duration_seconds=analysis.duration_seconds,
            resolution=analysis.resolution,
            overall_mood=analysis.overall_mood,
            narrative_arc=analysis.narrative_arc,
            recommended_insertion_frames=analysis.recommended_insertion_frames,
            dominant_colors=analysis.dominant_color_palette,
            scenes=scenes
        )
        
    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        return HalftimeAnalyzeResponse(
            success=False,
            duration_seconds=0,
            resolution=(0, 0),
            overall_mood="",
            narrative_arc=[],
            recommended_insertion_frames=[],
            dominant_colors=[],
            scenes=[],
            error=str(e)
        )


@router.post("/halftime/detect-zones", response_model=HalftimePlacementResponse)
async def halftime_detect_zones(
    request: HalftimePlacementRequest,
):
    """
    Detect insertion zones in video for product placement.
    
    Analyzes video frames to find optimal areas for product placement
    like tables, hands, shelves, and surfaces.
    """
    from ..services.kata.insertion_zone_detector import (
        InsertionZoneDetector,
        PlacementStyle,
        ZoneType
    )
    
    try:
        # Download video and extract first frame
        video_path = request.video_url
        if request.video_url.startswith('http'):
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(request.video_url)
                response.raise_for_status()
                
                suffix = Path(request.video_url).suffix or '.mp4'
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(response.content)
                    video_path = tmp.name
        
        # Extract first frame
        import cv2
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError("Could not read video frame")
        
        # Convert to PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_frame = Image.fromarray(frame_rgb)
        
        # Detect zones
        detector = InsertionZoneDetector()
        zones = detector.detect_zones(pil_frame)
        
        # Get placement recommendation
        style_map = {
            "natural": PlacementStyle.NATURAL,
            "prominent": PlacementStyle.PROMINENT,
            "subtle": PlacementStyle.SUBTLE,
            "dynamic": PlacementStyle.DYNAMIC,
        }
        placement_style = style_map.get(request.placement_style, PlacementStyle.NATURAL)
        
        recommendation = detector.get_best_placement(
            zones,
            product_type=request.product_type,
            product_size=request.product_size,
            placement_style=placement_style
        )
        
        # Clean up
        if video_path != request.video_url and os.path.exists(video_path):
            os.unlink(video_path)
        
        # Convert zones to dict
        zones_data = []
        for zone in zones:
            zones_data.append({
                "type": zone.zone_type.value,
                "bbox": zone.normalized_bbox,
                "visibility_score": zone.visibility_score,
                "context_fit_score": zone.context_fit_score,
                "overall_score": zone.overall_score,
                "suggested_scale": zone.suggested_scale,
                "depth_layer": zone.depth_layer,
                "description": zone.description,
            })
        
        response = HalftimePlacementResponse(
            success=True,
            zones=zones_data,
            confidence=recommendation.confidence if recommendation else 0,
            reasoning=recommendation.reasoning if recommendation else "",
        )
        
        if recommendation:
            response.recommendation = {
                "zone_type": recommendation.zone.zone_type.value,
                "position": recommendation.zone.normalized_bbox,
                "scale": recommendation.zone.suggested_scale,
                "rotation": recommendation.zone.suggested_rotation,
                "confidence": recommendation.confidence,
                "style": recommendation.style.value,
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Zone detection failed: {e}")
        return HalftimePlacementResponse(
            success=False,
            zones=[],
            confidence=0,
            reasoning="",
            error=str(e)
        )


@router.post("/halftime/composite", response_model=HalftimeCompositeResponse)
async def halftime_composite(
    request: HalftimeCompositeRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
):
    """
    Composite product into video using Halftime engine.
    
    This is the main endpoint that runs the full Halftime pipeline:
    1. Analyzes video with Grok AI
    2. Detects insertion zones
    3. Generates product asset with SegMind
    4. Composites with lighting/perspective matching
    5. Outputs platform-optimized video
    """
    from ..services.kata.halftime_compositor import (
        HalftimeCompositor,
        CompositingConfig,
        PlacementRecommendation
    )
    from ..services.kata.grok_scene_analyzer import GrokSceneAnalyzer
    from ..services.kata.insertion_zone_detector import InsertionZoneDetector, PlacementStyle
    
    api_key = getattr(settings, 'xai_api_key', None) or os.environ.get('XAI_API_KEY')
    segmind_key = getattr(settings, 'segmind_api_key', None) or os.environ.get('SEGMIND_API_KEY')
    
    if not api_key:
        raise HTTPException(status_code=400, detail="XAI_API_KEY not configured")
    if not segmind_key:
        raise HTTPException(status_code=400, detail="SEGMIND_API_KEY not configured")
    
    job_id = uuid.uuid4().hex[:12]
    
    # Create job
    job = KataJob(
        id=job_id,
        job_type=KataJobType.PRODUCT_PLACEMENT,
        status=KataJobStatus.PENDING,
        source_video=request.video_url,
        message="Halftime compositing queued",
    )
    _jobs[job_id] = job
    
    # Start background processing
    background_tasks.add_task(
        _run_halftime_composite,
        job_id,
        request,
        api_key,
        segmind_key,
    )
    
    return HalftimeCompositeResponse(
        success=True,
        output_url=None,
        duration_seconds=0,
        frames_processed=0,
        placement_info={"job_id": job_id, "status": "processing"}
    )


async def _run_halftime_composite(
    job_id: str,
    request: HalftimeCompositeRequest,
    xai_api_key: str,
    segmind_api_key: str,
):
    """Background task for Halftime compositing."""
    from ..services.kata.halftime_compositor import HalftimeCompositor, CompositingConfig
    from ..services.kata.grok_scene_analyzer import GrokSceneAnalyzer
    from ..services.kata.insertion_zone_detector import InsertionZoneDetector, PlacementStyle
    
    job = _jobs.get(job_id)
    if not job:
        return
    
    try:
        job.status = KataJobStatus.ANALYZING
        job.message = "Analyzing video scenes..."
        _jobs[job_id] = job
        
        # Download video
        video_path = request.video_url
        if request.video_url.startswith('http'):
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(request.video_url)
                response.raise_for_status()
                
                suffix = Path(request.video_url).suffix or '.mp4'
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(response.content)
                    video_path = tmp.name
        
        # Analyze video
        analyzer = GrokSceneAnalyzer(api_key=xai_api_key)
        analysis = await analyzer.analyze_video(video_path)
        await analyzer.close()
        
        job.status = KataJobStatus.GENERATING
        job.message = "Detecting placement zones..."
        _jobs[job_id] = job
        
        # Detect zones
        import cv2
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        detector = InsertionZoneDetector()
        
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(frame_rgb)
            zones = detector.detect_zones(pil_frame)
            
            style_map = {
                "natural": PlacementStyle.NATURAL,
                "prominent": PlacementStyle.PROMINENT,
                "subtle": PlacementStyle.SUBTLE,
                "ugc": PlacementStyle.NATURAL,
            }
            placement_style = style_map.get(request.style, PlacementStyle.NATURAL)
            
            placement = detector.get_best_placement(
                zones,
                product_type=request.product_type,
                placement_style=placement_style
            )
        else:
            placement = None
        
        if not placement:
            job.status = KataJobStatus.FAILED
            job.error = "Could not find suitable placement zone"
            _jobs[job_id] = job
            return
        
        job.status = KataJobStatus.COMPOSITING
        job.message = "Compositing product into video..."
        _jobs[job_id] = job
        
        # Configure compositing
        config = CompositingConfig(
            output_resolution=(1080, 1920) if request.platform in ["tiktok", "instagram"] else (1920, 1080),
            style=request.style,
            ugc_effects=request.ugc_effects,
            platform=request.platform,
            start_time=request.start_time,
            duration=request.duration,
            quality="high"
        )
        
        # Run compositing
        compositor = HalftimeCompositor(segmind_api_key=segmind_api_key)
        result = await compositor.composite_product(
            video_path=video_path,
            product_description=request.product_description,
            video_analysis=analysis,
            placement=placement,
            config=config
        )
        await compositor.close()
        
        # Clean up temp file
        if video_path != request.video_url and os.path.exists(video_path):
            os.unlink(video_path)
        
        # Update job
        if result.success:
            job.status = KataJobStatus.COMPLETE
            job.output_url = result.output_url or result.output_path
            job.duration_seconds = result.duration_seconds
            job.progress = 1.0
            job.message = "Compositing complete"
        else:
            job.status = KataJobStatus.FAILED
            job.error = result.error
            job.message = f"Failed: {result.error}"
        
        _jobs[job_id] = job
        
    except Exception as e:
        logger.error(f"Halftime compositing failed: {e}")
        job.status = KataJobStatus.FAILED
        job.error = str(e)
        job.message = f"Error: {str(e)}"
        _jobs[job_id] = job


@router.get("/halftime/job/{job_id}")
async def get_halftime_job_status(job_id: str):
    """Get status of a Halftime compositing job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = _jobs[job_id]
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "progress": job.progress,
        "message": job.message,
        "output_url": job.output_url,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
    }


@router.post("/halftime/quick-ugc")
async def halftime_quick_ugc(
    request: HalftimeCompositeRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
):
    """
    Quick UGC-style video creation with product placement.
    
    Simplified endpoint that automatically applies UGC effects
    and optimizes for the target platform.
    """
    # Force UGC settings
    request.ugc_effects = True
    request.style = "ugc"
    
    return await halftime_composite(request, background_tasks, settings)
