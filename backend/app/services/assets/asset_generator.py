"""
Asset Generator Orchestrator.

Orchestrates all asset generation services to produce complete campaign assets:
- Images (Segmind)
- Videos (Segmind)
- Voiceovers (ElevenLabs)
- Copy (OpenRouter + Claude Opus)

Takes creative specs and produces production-ready assets.

Enhanced with dynamic intelligence loading for deep domain expertise.
"""
import os
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .segmind import SegmindService, GeneratedImage, GeneratedVideo
from .elevenlabs import ElevenLabsService, GeneratedAudio
from ..ai.openrouter import OpenRouterService

# Import intelligence layer
try:
    from ...intelligence import load_department, load_format, load_rubric, get_department_prompt
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CopyAsset:
    """Generated copy content."""
    format: str
    content: str
    character_count: int
    variations: List[str] = field(default_factory=list)


@dataclass
class ImageAsset:
    """Generated image asset."""
    filename: str
    filepath: str
    platform: str
    dimensions: str
    has_text_overlay: bool
    prompt_used: str


@dataclass
class VideoAsset:
    """Generated video asset."""
    filename: str
    filepath: str
    duration: int
    has_voiceover: bool
    voiceover_filepath: Optional[str] = None


@dataclass
class CompleteAsset:
    """A complete, production-ready asset."""
    asset_id: str
    asset_type: str
    platform: str
    name: str

    # Content
    copy: Optional[CopyAsset] = None
    image: Optional[ImageAsset] = None
    video: Optional[VideoAsset] = None
    audio: Optional[GeneratedAudio] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    spec_used: Dict[str, Any] = field(default_factory=dict)


class AssetGenerator:
    """
    Master orchestrator for asset generation.

    Takes asset specifications from CreativeDirector and produces
    complete, production-ready assets using all available services.
    """

    def __init__(
        self,
        openrouter_api_key: str,
        segmind_api_key: str,
        elevenlabs_api_key: str,
        output_dir: str = "outputs"
    ):
        self.llm = OpenRouterService(api_key=openrouter_api_key)
        self.segmind = SegmindService(api_key=segmind_api_key, output_dir=output_dir)
        self.elevenlabs = ElevenLabsService(api_key=elevenlabs_api_key, output_dir=output_dir)
        self.output_dir = output_dir

        os.makedirs(output_dir, exist_ok=True)

    async def generate_asset(
        self,
        asset_spec: Dict[str, Any],
        brand_data: Optional[Dict[str, Any]] = None,
        include_variations: bool = True,
    ) -> CompleteAsset:
        """
        Generate a complete asset from specification.

        Args:
            asset_spec: Asset specification from CreativeDirector
            brand_data: Brand information for styling
            include_variations: Generate copy variations for A/B testing

        Returns:
            CompleteAsset with all components
        """
        asset_type = asset_spec.get("asset_type", "social_post")
        platform = asset_spec.get("platform", "instagram")

        logger.info(f"Generating {asset_type} for {platform}")

        # Generate asset ID
        import uuid
        asset_id = uuid.uuid4().hex[:12]

        # Parallel generation where possible
        tasks = []

        # 1. Generate copy
        copy_task = self._generate_copy(asset_spec, brand_data, include_variations)
        tasks.append(("copy", copy_task))

        # 2. Generate image
        if self._needs_image(asset_type):
            image_task = self._generate_image(asset_spec, brand_data)
            tasks.append(("image", image_task))

        # Execute parallel tasks
        results = {}
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Failed to generate {name}: {e}")
                results[name] = None

        # 3. Generate video (needs image first)
        video_asset = None
        if self._needs_video(asset_type) and results.get("image"):
            try:
                video_asset = await self._generate_video(
                    asset_spec,
                    results["image"],
                    brand_data
                )
            except Exception as e:
                logger.error(f"Failed to generate video: {e}")

        # 4. Generate voiceover (if video or audio asset)
        audio_asset = None
        if self._needs_voiceover(asset_type) and results.get("copy"):
            try:
                audio_asset = await self._generate_voiceover(
                    results["copy"],
                    asset_spec,
                    brand_data
                )
            except Exception as e:
                logger.error(f"Failed to generate voiceover: {e}")

        # 5. Composite text on image (if needed)
        image_asset = results.get("image")
        if image_asset and self._needs_text_overlay(asset_type):
            try:
                image_asset = await self._add_text_overlay(
                    image_asset,
                    results.get("copy"),
                    asset_spec,
                    brand_data
                )
            except Exception as e:
                logger.error(f"Failed to add text overlay: {e}")

        return CompleteAsset(
            asset_id=asset_id,
            asset_type=asset_type,
            platform=platform,
            name=asset_spec.get("name", f"{asset_type}_{asset_id}"),
            copy=results.get("copy"),
            image=image_asset,
            video=video_asset,
            audio=audio_asset,
            spec_used=asset_spec
        )

    async def generate_campaign_assets(
        self,
        asset_specs: List[Dict[str, Any]],
        brand_data: Optional[Dict[str, Any]] = None,
        parallel: bool = True,
    ) -> List[CompleteAsset]:
        """
        Generate multiple assets for a campaign.

        Args:
            asset_specs: List of asset specifications
            brand_data: Brand information
            parallel: Generate assets in parallel

        Returns:
            List of CompleteAsset objects
        """
        if parallel:
            tasks = [
                self.generate_asset(spec, brand_data)
                for spec in asset_specs
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)
        else:
            results = []
            for spec in asset_specs:
                try:
                    asset = await self.generate_asset(spec, brand_data)
                    results.append(asset)
                except Exception as e:
                    logger.error(f"Failed to generate asset: {e}")
            return results

    async def _generate_copy(
        self,
        asset_spec: Dict[str, Any],
        brand_data: Optional[Dict[str, Any]],
        include_variations: bool
    ) -> CopyAsset:
        """Generate copy content for the asset."""
        copy_specs = asset_spec.get("copy", [])
        if not copy_specs:
            return None

        # Build all copy pieces
        all_copy = []
        for spec in copy_specs:
            format_type = spec.get("format", "body")
            content = spec.get("content", "")

            if content:
                all_copy.append(f"{format_type}: {content}")

        # Generate variations if requested
        variations = []
        if include_variations and copy_specs:
            main_copy = copy_specs[0].get("content", "")
            if main_copy:
                variations = await self._generate_copy_variations(
                    main_copy,
                    asset_spec.get("asset_type", "social_post"),
                    brand_data
                )

        # Return primary copy
        primary = copy_specs[0] if copy_specs else {}
        return CopyAsset(
            format=primary.get("format", "body"),
            content=primary.get("content", ""),
            character_count=len(primary.get("content", "")),
            variations=variations
        )

    async def _generate_copy_variations(
        self,
        original: str,
        asset_type: str,
        brand_data: Optional[Dict[str, Any]],
        count: int = 3
    ) -> List[str]:
        """Generate copy variations for A/B testing.

        Enhanced with intelligence layer for deeper copywriting expertise.
        """
        brand_voice = ""
        if brand_data:
            tone = brand_data.get("voice", {}).get("tone", [])
            brand_voice = f"Brand tone: {', '.join(tone)}" if tone else ""

        # Load writer expertise from intelligence layer
        writer_expertise = ""
        if INTELLIGENCE_AVAILABLE:
            try:
                writer_content = load_department("writer")
                if writer_content:
                    # Extract key principles (first 1500 chars to avoid token overflow)
                    writer_expertise = f"\n\n## Writing Expertise\n{writer_content[:1500]}"
            except Exception as e:
                logger.warning(f"Failed to load writer intelligence: {e}")

        prompt = f"""Generate {count} variations of this copy for {asset_type}:

Original: "{original}"

{brand_voice}
{writer_expertise}

Each variation should:
- Maintain the core message
- Take a slightly different angle or emphasis
- Match the brand voice
- Be ready to use (no placeholders)
- Follow copywriting best practices

Return as JSON:
{{
    "variations": ["variation 1", "variation 2", "variation 3"]
}}"""

        try:
            result = await self.llm.complete_json(prompt)
            return result.get("variations", [])
        except Exception as e:
            logger.warning(f"Failed to generate variations: {e}")
            return []

    async def _generate_image(
        self,
        asset_spec: Dict[str, Any],
        brand_data: Optional[Dict[str, Any]]
    ) -> ImageAsset:
        """Generate image for the asset."""
        visual = asset_spec.get("visual", {})
        platform = asset_spec.get("platform", "instagram")

        # Map platform to standard key
        platform_key = self._normalize_platform(platform, asset_spec.get("asset_type"))

        result = await self.segmind.generate_image_for_asset(
            visual_concept=visual,
            platform=platform_key,
            brand_data=brand_data
        )

        return ImageAsset(
            filename=result.filename,
            filepath=result.filepath,
            platform=platform,
            dimensions=f"{result.width}x{result.height}",
            has_text_overlay=False,
            prompt_used=result.prompt_used
        )

    async def _generate_video(
        self,
        asset_spec: Dict[str, Any],
        image_asset: ImageAsset,
        brand_data: Optional[Dict[str, Any]]
    ) -> VideoAsset:
        """Generate video from image."""
        visual = asset_spec.get("visual", {})

        # Build motion prompt
        motion_prompt = visual.get("description", "Subtle cinematic motion")
        mood = visual.get("mood", "")
        if mood:
            motion_prompt = f"{motion_prompt}, {mood} atmosphere"

        result = await self.segmind.generate_video(
            prompt=motion_prompt,
            source_image=image_asset.filepath,
            duration=5,
            use_premium=True
        )

        return VideoAsset(
            filename=result.filename,
            filepath=result.filepath,
            duration=result.duration,
            has_voiceover=False
        )

    async def _generate_voiceover(
        self,
        copy_asset: CopyAsset,
        asset_spec: Dict[str, Any],
        brand_data: Optional[Dict[str, Any]]
    ) -> GeneratedAudio:
        """Generate voiceover for video/audio asset."""
        # Get the script (use CTA + headline + body)
        copy_specs = asset_spec.get("copy", [])
        script_parts = []

        for spec in copy_specs:
            format_type = spec.get("format", "")
            content = spec.get("content", "")

            if format_type in ("headline", "body", "script") and content:
                script_parts.append(content)

        script = " ".join(script_parts)

        if not script:
            script = copy_asset.content

        # Determine brand tone
        brand_tone = "professional"
        if brand_data:
            tone = brand_data.get("voice", {}).get("tone", [])
            if tone:
                brand_tone = tone[0]

        return await self.elevenlabs.generate_for_video_ad(
            script=script,
            brand_tone=brand_tone
        )

    async def _add_text_overlay(
        self,
        image_asset: ImageAsset,
        copy_asset: Optional[CopyAsset],
        asset_spec: Dict[str, Any],
        brand_data: Optional[Dict[str, Any]]
    ) -> ImageAsset:
        """Add text overlay to image."""
        copy_specs = asset_spec.get("copy", [])

        # Extract text components
        headline = None
        subheadline = None
        cta = asset_spec.get("cta")

        for spec in copy_specs:
            format_type = spec.get("format", "")
            content = spec.get("content", "")

            if format_type == "headline":
                headline = content
            elif format_type in ("body", "subheadline", "caption"):
                subheadline = content

        # Get brand colors
        brand_colors = None
        if brand_data:
            visual_identity = brand_data.get("visual_identity", {})
            primary = visual_identity.get("primary_color")
            if primary:
                brand_colors = [primary]

        # Composite text
        new_filepath = await self.segmind.composite_text(
            image_path=image_asset.filepath,
            headline=headline,
            subheadline=subheadline,
            cta=cta,
            brand_colors=brand_colors,
            position="center"
        )

        return ImageAsset(
            filename=os.path.basename(new_filepath),
            filepath=new_filepath,
            platform=image_asset.platform,
            dimensions=image_asset.dimensions,
            has_text_overlay=True,
            prompt_used=image_asset.prompt_used
        )

    def _normalize_platform(self, platform: str, asset_type: str) -> str:
        """Normalize platform name to standard key."""
        platform = platform.lower().replace(" ", "_")

        if "instagram" in platform:
            if "story" in asset_type or "story" in platform:
                return "instagram_story"
            elif "reel" in asset_type or "reel" in platform:
                return "instagram_reel"
            return "instagram_post"

        if "linkedin" in platform:
            return "linkedin_post"

        if "twitter" in platform or platform == "x":
            return "twitter_post"

        if "facebook" in platform:
            return "facebook_post"

        if "youtube" in platform:
            return "youtube_thumbnail"

        if "email" in platform:
            return "email_header"

        if "landing" in platform or "hero" in platform:
            return "landing_hero"

        return "instagram_post"  # Default

    def _needs_image(self, asset_type: str) -> bool:
        """Check if asset type needs image generation."""
        image_types = {
            "social_post", "instagram_post", "instagram_story", "instagram_reel",
            "linkedin_post", "twitter_post", "facebook_post",
            "display_banner", "email_header", "landing_page_hero",
            "youtube_thumbnail", "video_ad", "print_ad"
        }
        return asset_type.lower() in image_types

    def _needs_video(self, asset_type: str) -> bool:
        """Check if asset type needs video generation."""
        video_types = {"video_ad", "instagram_reel", "youtube_video", "social_video"}
        return asset_type.lower() in video_types

    def _needs_voiceover(self, asset_type: str) -> bool:
        """Check if asset type needs voiceover."""
        audio_types = {"video_ad", "radio_spot", "podcast_ad", "youtube_video"}
        return asset_type.lower() in audio_types

    def _needs_text_overlay(self, asset_type: str) -> bool:
        """Check if asset type needs text overlay on image."""
        overlay_types = {
            "social_post", "instagram_post", "instagram_story",
            "linkedin_post", "twitter_post", "facebook_post",
            "display_banner", "youtube_thumbnail"
        }
        return asset_type.lower() in overlay_types

    async def close(self):
        """Close all services."""
        await self.llm.close()
        await self.segmind.close()
        await self.elevenlabs.close()
