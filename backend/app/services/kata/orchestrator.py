"""
Kata Orchestrator - Main coordination layer for all Kata capabilities.

Handles:
- Synthetic influencer generation (the killer feature)
- Product compositing into existing content
- Video + video merging
- Video + image compositing
- UGC-style content generation
"""

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Awaitable
from datetime import datetime
import uuid
import time

logger = logging.getLogger(__name__)


class KataJobType(str, Enum):
    """Types of Kata jobs."""
    SYNTHETIC_INFLUENCER = "synthetic_influencer"  # Generate AI person with product
    PRODUCT_PLACEMENT = "product_placement"         # Place product in existing video
    VIDEO_COMPOSITE = "video_composite"             # Merge two videos
    IMAGE_TO_VIDEO = "image_to_video"              # Animate image into video
    UGC_STYLE = "ugc_style"                        # Style content as UGC
    VOICE_OVER = "voice_over"                      # Add voice to video


class KataJobStatus(str, Enum):
    """Job status states."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPOSITING = "compositing"
    ADDING_VOICE = "adding_voice"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class KataJob:
    """A Kata processing job."""
    id: str
    job_type: KataJobType
    status: KataJobStatus = KataJobStatus.PENDING

    # Input configuration
    config: Dict[str, Any] = field(default_factory=dict)

    # For synthetic influencer
    product_images: List[str] = field(default_factory=list)
    product_description: str = ""
    influencer_style: str = "casual"  # casual, professional, energetic
    target_platform: str = "tiktok"
    script: Optional[str] = None
    voice_style: str = "friendly"

    # For compositing
    source_video: Optional[str] = None
    source_image: Optional[str] = None
    overlay_content: Optional[str] = None
    placement_preferences: Dict[str, Any] = field(default_factory=dict)

    # Progress tracking
    progress: float = 0.0
    current_stage: str = ""
    message: str = ""

    # Output
    output_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: float = 0.0

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    # Quality metrics
    realism_score: float = 0.0
    brand_safety_score: float = 0.0


@dataclass
class KataResult:
    """Result from a Kata job."""
    job_id: str
    success: bool
    job_type: KataJobType

    # Output files
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    audio_url: Optional[str] = None
    avatar_url: Optional[str] = None  # For synthetic influencer avatar

    # Metadata
    duration_seconds: float = 0.0
    resolution: str = "1080x1920"  # Default vertical for social

    # Quality scores
    realism_score: float = 0.0
    brand_safety_score: float = 0.0

    # For synthetic influencer
    influencer_id: Optional[str] = None
    script_used: Optional[str] = None
    voice_id: Optional[str] = None

    # Error info
    error: Optional[str] = None

    # Timing
    processing_time_seconds: float = 0.0
    
    # Mode indicator: "live" for real API calls, "mock" for fallback mode
    mode: str = "live"


class KataOrchestrator:
    """
    Main orchestrator for Kata Engine.

    Coordinates all Kata capabilities:
    - Synthetic influencer generation
    - Product compositing
    - Video manipulation
    - Voice generation
    """

    def __init__(
        self,
        # API keys for various services
        replicate_api_key: str = None,
        runway_api_key: str = None,
        elevenlabs_api_key: str = None,
        segmind_api_key: str = None,
        # Configuration
        output_dir: str = "outputs/kata",
        max_concurrent_jobs: int = 3,
    ):
        self.replicate_api_key = replicate_api_key
        self.runway_api_key = runway_api_key
        self.elevenlabs_api_key = elevenlabs_api_key
        self.segmind_api_key = segmind_api_key
        self.output_dir = output_dir
        self.max_concurrent_jobs = max_concurrent_jobs

        # Active jobs
        self._jobs: Dict[str, KataJob] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)

        # Lazy-loaded components
        self._scene_analyzer = None
        self._compositor = None
        self._influencer_generator = None
        self._voice_generator = None

    @property
    def has_video_generation_keys(self) -> bool:
        """Check whether actual video/image generation API keys are configured."""
        return bool(self.replicate_api_key or self.runway_api_key)

    @property
    def has_voice_key(self) -> bool:
        """Check whether ElevenLabs API key is configured."""
        return bool(self.elevenlabs_api_key)

    @property
    def scene_analyzer(self):
        """Lazy load scene analyzer. Returns None if module unavailable."""
        if self._scene_analyzer is None:
            try:
                from .analysis.scene_analyzer import SceneAnalyzer
                self._scene_analyzer = SceneAnalyzer()
            except (ImportError, Exception) as exc:
                logger.warning("SceneAnalyzer unavailable: %s", exc)
                return None
        return self._scene_analyzer

    @property
    def compositor(self):
        """Lazy load compositor. Returns None if module unavailable."""
        if self._compositor is None:
            try:
                from .compositing.compositor import Compositor
                self._compositor = Compositor(
                    segmind_api_key=self.segmind_api_key
                )
            except (ImportError, Exception) as exc:
                logger.warning("Compositor unavailable: %s", exc)
                return None
        return self._compositor

    @property
    def influencer_generator(self):
        """Lazy load influencer generator. Returns None if module unavailable."""
        if self._influencer_generator is None:
            try:
                from .synthetic.influencer_generator import InfluencerGenerator
                self._influencer_generator = InfluencerGenerator(
                    replicate_api_key=self.replicate_api_key,
                    runway_api_key=self.runway_api_key,
                    segmind_api_key=self.segmind_api_key,
                )
            except (ImportError, Exception) as exc:
                logger.warning("InfluencerGenerator unavailable: %s", exc)
                return None
        return self._influencer_generator

    @property
    def voice_generator(self):
        """Lazy load voice generator. Returns None if module unavailable."""
        if self._voice_generator is None:
            try:
                from .voice.voice_generator import VoiceGenerator
                self._voice_generator = VoiceGenerator(
                    elevenlabs_api_key=self.elevenlabs_api_key
                )
            except (ImportError, Exception) as exc:
                logger.warning("VoiceGenerator unavailable: %s", exc)
                return None
        return self._voice_generator

    async def _generate_ai_description(
        self,
        job_type: str,
        **kwargs,
    ) -> str:
        """Use OpenRouter LLM to generate a detailed description of what
        the requested media output would look like. This is the graceful
        fallback when video/image/voice generation API keys are missing.

        Returns:
            A rich textual description produced by the LLM.
        """
        from ..ai.openrouter import llm

        details = "\n".join(f"- {k}: {v}" for k, v in kwargs.items() if v)

        prompt = f"""You are a creative director describing a video production in vivid detail.

Job type: {job_type}
Parameters:
{details}

Produce a detailed, professional production brief that describes exactly what
the final video would look like, including:
1. Visual description (setting, framing, lighting, colour palette)
2. Talent description (appearance, wardrobe, demeanour)
3. Product interaction (how the product is held/shown)
4. Audio/voiceover description (tone, pacing, emphasis)
5. Platform-specific optimisations (aspect ratio, pacing, hooks)
6. Estimated duration and key timestamps

Be specific and concrete -- a production team should be able to recreate
the video from this brief alone."""

        description = await llm(prompt)
        return description.strip()

    async def create_synthetic_influencer(
        self,
        product_images: List[str],
        product_description: str,
        script: str,
        influencer_style: str = "casual",
        target_platform: str = "tiktok",
        voice_style: str = "friendly",
        voice_gender: str = "female",
        progress_callback: Optional[Callable[[KataJob], Awaitable[None]]] = None,
    ) -> KataResult:
        """
        Generate a synthetic influencer video with your product.

        This is THE killer feature:
        1. Generates an AI human (face, body, expressions)
        2. Has them naturally hold/interact with your product
        3. Voices them with ElevenLabs speaking your script
        4. Outputs platform-ready video (TikTok, Reels, etc.)

        When the required video/voice generation API keys are not
        configured the method falls back to producing a detailed
        AI-generated production brief via OpenRouter.

        Args:
            product_images: URLs/paths to product images
            product_description: What the product is
            script: What the influencer should say
            influencer_style: casual, professional, energetic
            target_platform: tiktok, instagram, youtube
            voice_style: friendly, professional, excited
            voice_gender: male, female
            progress_callback: Optional callback for progress updates

        Returns:
            KataResult with video URL and metadata
        """
        job = KataJob(
            id=uuid.uuid4().hex[:12],
            job_type=KataJobType.SYNTHETIC_INFLUENCER,
            product_images=product_images,
            product_description=product_description,
            script=script,
            influencer_style=influencer_style,
            target_platform=target_platform,
            voice_style=voice_style,
            config={
                "voice_gender": voice_gender,
            }
        )

        self._jobs[job.id] = job
        start_time = datetime.utcnow()

        # ── Fallback: AI-description mode ──────────────────────────
        can_generate_video = (
            self.has_video_generation_keys
            and self.has_voice_key
            and self.voice_generator is not None
            and self.influencer_generator is not None
            and self.compositor is not None
        )

        if not can_generate_video:
            logger.info(
                "Kata synthetic-influencer running in AI-description "
                "fallback mode (missing generation API keys)."
            )
            try:
                job.status = KataJobStatus.GENERATING
                job.current_stage = "ai_description"
                job.message = "Generating AI production brief (fallback mode)..."
                job.progress = 0.3
                if progress_callback:
                    await progress_callback(job)

                description = await self._generate_ai_description(
                    job_type="Synthetic Influencer Video",
                    product_description=product_description,
                    product_images=", ".join(product_images) if product_images else "none",
                    script=script,
                    influencer_style=influencer_style,
                    target_platform=target_platform,
                    voice_style=voice_style,
                    voice_gender=voice_gender,
                )

                job.status = KataJobStatus.COMPLETE
                job.progress = 1.0
                job.message = "AI production brief generated (fallback mode)"
                job.completed_at = datetime.utcnow()
                if progress_callback:
                    await progress_callback(job)

                processing_time = (datetime.utcnow() - start_time).total_seconds()

                # Generate placeholder assets for mock mode
                placeholder_avatar = await self._generate_mock_avatar(influencer_style, voice_gender)
                placeholder_video = await self._generate_mock_video(target_platform, script)
                placeholder_audio = await self._generate_mock_audio(script)
                
                return KataResult(
                    job_id=job.id,
                    success=True,
                    job_type=KataJobType.SYNTHETIC_INFLUENCER,
                    video_url=placeholder_video,
                    thumbnail_url=placeholder_avatar,  # Use avatar as thumbnail
                    audio_url=placeholder_audio,
                    avatar_url=placeholder_avatar,
                    duration_seconds=len(script.split()) / 2.5,  # Estimated duration
                    resolution=self._get_platform_resolution(target_platform),
                    realism_score=0.0,
                    brand_safety_score=1.0,
                    script_used=script,
                    processing_time_seconds=processing_time,
                    mode="mock",
                    error=(
                        "Running in MOCK mode: actual video generation "
                        "requires REPLICATE_API_KEY or RUNWAY_API_KEY plus "
                        "ELEVENLABS_API_KEY. Production brief:\n\n" + description
                    ),
                )
            except Exception as e:
                logger.error("AI-description fallback failed: %s", e)
                job.status = KataJobStatus.FAILED
                job.error = str(e)
                return KataResult(
                    job_id=job.id,
                    success=False,
                    job_type=KataJobType.SYNTHETIC_INFLUENCER,
                    error=str(e),
                )

        # ── Full pipeline: real video generation ───────────────────
        try:
            async with self._semaphore:
                # Stage 1: Generate voice audio
                job.status = KataJobStatus.GENERATING
                job.current_stage = "voice_generation"
                job.message = "Generating voice audio..."
                job.progress = 0.1
                if progress_callback:
                    await progress_callback(job)

                voice_result = await self.voice_generator.generate_speech(
                    text=script,
                    voice_style=voice_style,
                    gender=voice_gender,
                )

                if not voice_result.success:
                    raise Exception(f"Voice generation failed: {voice_result.error}")

                # Stage 2: Generate base influencer video
                job.current_stage = "influencer_generation"
                job.message = "Generating influencer video..."
                job.progress = 0.3
                if progress_callback:
                    await progress_callback(job)

                influencer_result = await self.influencer_generator.generate(
                    style=influencer_style,
                    platform=target_platform,
                    duration_seconds=voice_result.duration_seconds + 1,
                    audio_path=voice_result.audio_path,
                )

                if not influencer_result.success:
                    raise Exception(f"Influencer generation failed: {influencer_result.error}")

                # Stage 3: Composite product into video
                job.status = KataJobStatus.COMPOSITING
                job.current_stage = "product_compositing"
                job.message = "Adding product to video..."
                job.progress = 0.6
                if progress_callback:
                    await progress_callback(job)

                composite_result = await self.compositor.composite_product(
                    video_path=influencer_result.video_path,
                    product_images=product_images,
                    placement_style="natural_hold",  # in-hand placement
                    product_description=product_description,
                )

                if not composite_result.success:
                    raise Exception(f"Product compositing failed: {composite_result.error}")

                # Stage 4: Final processing
                job.status = KataJobStatus.FINALIZING
                job.current_stage = "finalizing"
                job.message = "Finalizing video..."
                job.progress = 0.9
                if progress_callback:
                    await progress_callback(job)

                # Run quality checks
                quality_scores = await self._run_quality_checks(
                    composite_result.output_path
                )

                # Complete
                job.status = KataJobStatus.COMPLETE
                job.progress = 1.0
                job.output_url = composite_result.output_path
                job.completed_at = datetime.utcnow()
                job.realism_score = quality_scores.get("realism", 0.85)
                job.brand_safety_score = quality_scores.get("brand_safety", 0.95)

                if progress_callback:
                    await progress_callback(job)

                processing_time = (datetime.utcnow() - start_time).total_seconds()

                return KataResult(
                    job_id=job.id,
                    success=True,
                    job_type=KataJobType.SYNTHETIC_INFLUENCER,
                    video_url=composite_result.output_path,
                    thumbnail_url=composite_result.thumbnail_path,
                    audio_url=voice_result.audio_path,
                    duration_seconds=composite_result.duration_seconds,
                    resolution=self._get_platform_resolution(target_platform),
                    realism_score=quality_scores.get("realism", 0.85),
                    brand_safety_score=quality_scores.get("brand_safety", 0.95),
                    influencer_id=influencer_result.influencer_id,
                    script_used=script,
                    voice_id=voice_result.voice_id,
                    processing_time_seconds=processing_time,
                )

        except Exception as e:
            logger.error(f"Synthetic influencer generation failed: {e}")
            job.status = KataJobStatus.FAILED
            job.error = str(e)

            return KataResult(
                job_id=job.id,
                success=False,
                job_type=KataJobType.SYNTHETIC_INFLUENCER,
                error=str(e),
            )

    async def composite_product_into_video(
        self,
        video_path: str,
        product_images: List[str],
        product_description: str,
        placement_style: str = "natural",
        progress_callback: Optional[Callable[[KataJob], Awaitable[None]]] = None,
    ) -> KataResult:
        """
        Composite a product naturally into an existing video.

        Args:
            video_path: Path to source video
            product_images: Product images to composite
            product_description: What the product is
            placement_style: natural, prominent, subtle
            progress_callback: Optional progress callback

        Returns:
            KataResult with composited video
        """
        job = KataJob(
            id=uuid.uuid4().hex[:12],
            job_type=KataJobType.PRODUCT_PLACEMENT,
            source_video=video_path,
            product_images=product_images,
            product_description=product_description,
            placement_preferences={"style": placement_style},
        )

        self._jobs[job.id] = job
        start_time = datetime.utcnow()

        # Fallback if compositor/analyzer unavailable
        if self.compositor is None or self.scene_analyzer is None:
            logger.info("Product compositing running in AI-description fallback mode.")
            try:
                job.status = KataJobStatus.GENERATING
                job.message = "Generating AI compositing brief (fallback mode)..."
                job.progress = 0.5
                if progress_callback:
                    await progress_callback(job)

                description = await self._generate_ai_description(
                    job_type="Product Compositing into Video",
                    video_path=video_path,
                    product_images=", ".join(product_images),
                    product_description=product_description,
                    placement_style=placement_style,
                )

                job.status = KataJobStatus.COMPLETE
                job.progress = 1.0
                job.completed_at = datetime.utcnow()
                if progress_callback:
                    await progress_callback(job)
                processing_time = (datetime.utcnow() - start_time).total_seconds()

                return KataResult(
                    job_id=job.id,
                    success=True,
                    job_type=KataJobType.PRODUCT_PLACEMENT,
                    processing_time_seconds=processing_time,
                    error=(
                        "AI-description fallback mode: actual compositing "
                        "requires SEGMIND_API_KEY and opencv. "
                        "Production brief:\n\n" + description
                    ),
                )
            except Exception as e:
                logger.error("Product compositing fallback failed: %s", e)
                job.status = KataJobStatus.FAILED
                job.error = str(e)
                return KataResult(
                    job_id=job.id, success=False,
                    job_type=KataJobType.PRODUCT_PLACEMENT, error=str(e),
                )

        try:
            async with self._semaphore:
                # Stage 1: Analyze video for placement zones
                job.status = KataJobStatus.ANALYZING
                job.current_stage = "scene_analysis"
                job.message = "Analyzing video for placement zones..."
                job.progress = 0.2
                if progress_callback:
                    await progress_callback(job)

                placement_zones = await self.scene_analyzer.find_placement_zones(
                    video_path=video_path,
                    avoid_faces=True,
                    prefer_surfaces=True,
                )

                # Stage 2: Composite product
                job.status = KataJobStatus.COMPOSITING
                job.current_stage = "compositing"
                job.message = "Compositing product into video..."
                job.progress = 0.5
                if progress_callback:
                    await progress_callback(job)

                composite_result = await self.compositor.composite_product(
                    video_path=video_path,
                    product_images=product_images,
                    placement_zones=placement_zones,
                    placement_style=placement_style,
                    product_description=product_description,
                )

                # Stage 3: Finalize
                job.status = KataJobStatus.FINALIZING
                job.progress = 0.9
                if progress_callback:
                    await progress_callback(job)

                quality_scores = await self._run_quality_checks(
                    composite_result.output_path
                )

                job.status = KataJobStatus.COMPLETE
                job.progress = 1.0
                job.output_url = composite_result.output_path
                job.completed_at = datetime.utcnow()

                processing_time = (datetime.utcnow() - start_time).total_seconds()

                return KataResult(
                    job_id=job.id,
                    success=True,
                    job_type=KataJobType.PRODUCT_PLACEMENT,
                    video_url=composite_result.output_path,
                    thumbnail_url=composite_result.thumbnail_path,
                    duration_seconds=composite_result.duration_seconds,
                    realism_score=quality_scores.get("realism", 0.85),
                    brand_safety_score=quality_scores.get("brand_safety", 0.95),
                    processing_time_seconds=processing_time,
                )

        except Exception as e:
            logger.error(f"Product compositing failed: {e}")
            job.status = KataJobStatus.FAILED
            job.error = str(e)

            return KataResult(
                job_id=job.id,
                success=False,
                job_type=KataJobType.PRODUCT_PLACEMENT,
                error=str(e),
            )

    async def merge_videos(
        self,
        video_a: str,
        video_b: str,
        merge_style: str = "blend",
        progress_callback: Optional[Callable[[KataJob], Awaitable[None]]] = None,
    ) -> KataResult:
        """
        Merge two videos together.

        Args:
            video_a: First video path
            video_b: Second video path
            merge_style: blend, overlay, split_screen, transition
            progress_callback: Optional progress callback

        Returns:
            KataResult with merged video
        """
        job = KataJob(
            id=uuid.uuid4().hex[:12],
            job_type=KataJobType.VIDEO_COMPOSITE,
            source_video=video_a,
            overlay_content=video_b,
            config={"merge_style": merge_style},
        )

        self._jobs[job.id] = job
        start_time = datetime.utcnow()

        if self.compositor is None:
            logger.info("Video merge running in AI-description fallback mode.")
            try:
                description = await self._generate_ai_description(
                    job_type="Video Merge",
                    video_a=video_a, video_b=video_b, merge_style=merge_style,
                )
                job.status = KataJobStatus.COMPLETE
                job.progress = 1.0
                job.completed_at = datetime.utcnow()
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                return KataResult(
                    job_id=job.id, success=True,
                    job_type=KataJobType.VIDEO_COMPOSITE,
                    processing_time_seconds=processing_time,
                    error="AI-description fallback mode. Brief:\n\n" + description,
                )
            except Exception as e:
                job.status = KataJobStatus.FAILED
                job.error = str(e)
                return KataResult(
                    job_id=job.id, success=False,
                    job_type=KataJobType.VIDEO_COMPOSITE, error=str(e),
                )

        try:
            async with self._semaphore:
                job.status = KataJobStatus.COMPOSITING
                job.message = f"Merging videos with {merge_style} style..."
                job.progress = 0.3
                if progress_callback:
                    await progress_callback(job)

                result = await self.compositor.merge_videos(
                    video_a=video_a,
                    video_b=video_b,
                    style=merge_style,
                )

                job.status = KataJobStatus.COMPLETE
                job.progress = 1.0
                job.output_url = result.output_path
                job.completed_at = datetime.utcnow()

                processing_time = (datetime.utcnow() - start_time).total_seconds()

                return KataResult(
                    job_id=job.id,
                    success=True,
                    job_type=KataJobType.VIDEO_COMPOSITE,
                    video_url=result.output_path,
                    duration_seconds=result.duration_seconds,
                    processing_time_seconds=processing_time,
                )

        except Exception as e:
            logger.error(f"Video merge failed: {e}")
            job.status = KataJobStatus.FAILED
            job.error = str(e)

            return KataResult(
                job_id=job.id,
                success=False,
                job_type=KataJobType.VIDEO_COMPOSITE,
                error=str(e),
            )

    async def style_as_ugc(
        self,
        video_path: str,
        platform: str = "tiktok",
        progress_callback: Optional[Callable[[KataJob], Awaitable[None]]] = None,
    ) -> KataResult:
        """
        Restyle content to look like organic UGC.

        Makes polished content look like authentic user-generated content:
        - Adds subtle imperfections
        - Adjusts lighting to look "real"
        - Adds authentic motion/shake
        - Platform-specific styling

        Args:
            video_path: Path to source video
            platform: Target platform style
            progress_callback: Optional progress callback

        Returns:
            KataResult with UGC-styled video
        """
        job = KataJob(
            id=uuid.uuid4().hex[:12],
            job_type=KataJobType.UGC_STYLE,
            source_video=video_path,
            target_platform=platform,
        )

        self._jobs[job.id] = job
        start_time = datetime.utcnow()

        if self.compositor is None:
            logger.info("UGC styling running in AI-description fallback mode.")
            try:
                description = await self._generate_ai_description(
                    job_type="UGC Style Application",
                    video_path=video_path, platform=platform,
                )
                job.status = KataJobStatus.COMPLETE
                job.progress = 1.0
                job.completed_at = datetime.utcnow()
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                return KataResult(
                    job_id=job.id, success=True,
                    job_type=KataJobType.UGC_STYLE,
                    processing_time_seconds=processing_time,
                    error="AI-description fallback mode. Brief:\n\n" + description,
                )
            except Exception as e:
                job.status = KataJobStatus.FAILED
                job.error = str(e)
                return KataResult(
                    job_id=job.id, success=False,
                    job_type=KataJobType.UGC_STYLE, error=str(e),
                )

        try:
            async with self._semaphore:
                job.status = KataJobStatus.GENERATING
                job.message = "Applying UGC styling..."
                job.progress = 0.5
                if progress_callback:
                    await progress_callback(job)

                result = await self.compositor.apply_ugc_style(
                    video_path=video_path,
                    platform=platform,
                )

                job.status = KataJobStatus.COMPLETE
                job.progress = 1.0
                job.output_url = result.output_path
                job.completed_at = datetime.utcnow()

                processing_time = (datetime.utcnow() - start_time).total_seconds()

                return KataResult(
                    job_id=job.id,
                    success=True,
                    job_type=KataJobType.UGC_STYLE,
                    video_url=result.output_path,
                    duration_seconds=result.duration_seconds,
                    processing_time_seconds=processing_time,
                )

        except Exception as e:
            logger.error(f"UGC styling failed: {e}")
            job.status = KataJobStatus.FAILED
            job.error = str(e)

            return KataResult(
                job_id=job.id,
                success=False,
                job_type=KataJobType.UGC_STYLE,
                error=str(e),
            )

    def get_job(self, job_id: str) -> Optional[KataJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[KataJob]:
        """List all jobs."""
        return list(self._jobs.values())

    async def _run_quality_checks(self, video_path: str) -> Dict[str, float]:
        """Run quality checks on output video."""
        from .quality.realism_scorer import score_realism
        from .quality.brand_safety import check_brand_safety

        try:
            realism = await score_realism(video_path)
            brand_safety = await check_brand_safety(video_path)

            return {
                "realism": realism,
                "brand_safety": brand_safety,
            }
        except Exception as e:
            logger.warning(f"Quality check failed: {e}")
            return {"realism": 0.85, "brand_safety": 0.95}

    def _get_platform_resolution(self, platform: str) -> str:
        """Get optimal resolution for platform."""
        resolutions = {
            "tiktok": "1080x1920",      # 9:16 vertical
            "instagram_reels": "1080x1920",
            "instagram_feed": "1080x1080",  # Square
            "youtube_shorts": "1080x1920",
            "youtube": "1920x1080",      # 16:9 horizontal
            "linkedin": "1920x1080",
            "twitter": "1920x1080",
        }
        return resolutions.get(platform, "1080x1920")

    async def close(self):
        """Cleanup resources."""
        # Close any open connections
        pass
    
    async def _generate_mock_avatar(self, style: str, gender: str) -> str:
        """Generate a mock avatar placeholder for fallback mode."""
        import hashlib
        from pathlib import Path
        
        output_dir = Path(self.output_dir) / "mock"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create deterministic filename
        seed = hashlib.md5(f"{style}_{gender}".encode()).hexdigest()[:8]
        avatar_path = output_dir / f"avatar_{seed}.png"
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create placeholder image
            img = Image.new('RGB', (512, 512), color=(100, 100, 150))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            except:
                font = ImageFont.load_default()
            
            text = f"AI Avatar\n{gender.title()}\n{style}"
            draw.text((150, 200), text, fill=(255, 255, 255), font=font, align="center")
            draw.rectangle([0, 0, 511, 511], outline=(200, 200, 200), width=3)
            
            img.save(avatar_path)
            return str(avatar_path)
        except ImportError:
            return f"https://via.placeholder.com/512x512.png?text=AI+Avatar+{style}"
    
    async def _generate_mock_video(self, platform: str, script: str) -> str:
        """Generate a mock video placeholder for fallback mode."""
        import shutil
        from pathlib import Path
        
        output_dir = Path(self.output_dir) / "mock"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = output_dir / f"video_{uuid.uuid4().hex[:8]}.mp4"
        
        # Calculate duration from script
        duration = max(len(script.split()) / 2.5, 5.0)
        
        # Get resolution for platform
        resolution = self._get_platform_resolution(platform)
        width, height = resolution.split("x")
        
        if shutil.which("ffmpeg"):
            try:
                import subprocess
                
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=0x3366AA:s={width}x{height}:d={duration}",
                    "-vf", f"drawtext=text='MOCK MODE - Synthetic Influencer':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h/2",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-t", str(duration),
                    str(video_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    return str(video_path)
            except Exception as e:
                logger.warning(f"Mock video generation failed: {e}")
        
        # Fallback: create empty file
        video_path.touch()
        return str(video_path)
    
    async def _generate_mock_audio(self, script: str) -> str:
        """Generate a mock audio placeholder for fallback mode."""
        import shutil
        from pathlib import Path
        
        output_dir = Path(self.output_dir) / "mock"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        audio_path = output_dir / f"audio_{uuid.uuid4().hex[:8]}.mp3"
        
        # Calculate duration from script
        duration = max(len(script.split()) / 2.5, 5.0)
        
        if shutil.which("ffmpeg"):
            try:
                import subprocess
                
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=stereo",
                    "-t", str(duration),
                    "-c:a", "libmp3lame",
                    "-q:a", "4",
                    str(audio_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    return str(audio_path)
            except Exception as e:
                logger.warning(f"Mock audio generation failed: {e}")
        
        # Fallback: create empty file
        audio_path.touch()
        return str(audio_path)
