"""
Synthetic Influencer Generator - THE KILLER FEATURE

Generate AI influencers that:
1. Look completely real (AI-generated humans)
2. Hold and interact with your products naturally
3. Speak with realistic AI voices (ElevenLabs)
4. Are formatted for any social platform

This replaces paying $1000+ per influencer post with unlimited
AI-generated content that looks authentic.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import asyncio
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class InfluencerStyle(str, Enum):
    """Influencer persona styles."""
    CASUAL = "casual"               # Everyday, relatable
    PROFESSIONAL = "professional"   # Business, polished
    ENERGETIC = "energetic"         # High-energy, enthusiastic
    LIFESTYLE = "lifestyle"         # Aspirational, aesthetic
    AUTHENTIC = "authentic"         # Raw, unfiltered UGC style
    EXPERT = "expert"              # Authority, knowledgeable


class InfluencerDemographic(str, Enum):
    """Demographic targeting."""
    GEN_Z = "gen_z"                 # 18-24, trendy
    MILLENNIAL = "millennial"       # 25-40, established
    PROFESSIONAL = "professional"   # Business-focused
    PARENT = "parent"              # Family-oriented
    SENIOR = "senior"              # 50+, mature


@dataclass
class SyntheticInfluencer:
    """
    A generated synthetic influencer persona.

    Can be reused across multiple videos for brand consistency.
    """
    id: str
    name: str
    style: InfluencerStyle
    demographic: InfluencerDemographic

    # Visual characteristics
    appearance: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"gender": "female", "age_range": "25-30", "ethnicity": "diverse"}

    # Voice characteristics
    voice_id: Optional[str] = None  # ElevenLabs voice ID
    voice_style: str = "friendly"

    # Generated assets
    avatar_image_url: Optional[str] = None
    base_video_url: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    videos_generated: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "style": self.style.value,
            "demographic": self.demographic.value,
            "appearance": self.appearance,
            "voice_id": self.voice_id,
            "avatar_image_url": self.avatar_image_url,
            "created_at": self.created_at.isoformat(),
            "videos_generated": self.videos_generated,
        }


@dataclass
class InfluencerResult:
    """Result from generating influencer content."""
    success: bool
    influencer_id: str
    video_path: str
    thumbnail_path: Optional[str] = None
    duration_seconds: float = 0.0
    resolution: Tuple[int, int] = (1080, 1920)

    # The influencer used
    influencer: Optional[SyntheticInfluencer] = None

    # Audio info
    audio_path: Optional[str] = None
    voice_id: Optional[str] = None

    # Error info
    error: Optional[str] = None


class InfluencerGenerator:
    """
    Generate synthetic influencer content.

    The magic pipeline:
    1. Generate or select an influencer persona
    2. Generate base video of the influencer (AI video generation)
    3. Composite the product into their hands/scene
    4. Lip-sync with ElevenLabs voice
    5. Output platform-ready video

    This creates unlimited "influencer" content without
    paying real influencers.
    """

    def __init__(
        self,
        replicate_api_key: str = None,
        runway_api_key: str = None,
        segmind_api_key: str = None,
        output_dir: str = "outputs/kata/influencers",
    ):
        self.replicate_api_key = replicate_api_key
        self.runway_api_key = runway_api_key
        self.segmind_api_key = segmind_api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cache of created influencers
        self._influencers: Dict[str, SyntheticInfluencer] = {}

    async def create_influencer(
        self,
        name: str,
        style: InfluencerStyle = InfluencerStyle.CASUAL,
        demographic: InfluencerDemographic = InfluencerDemographic.MILLENNIAL,
        appearance: Dict[str, Any] = None,
        voice_style: str = "friendly",
        voice_gender: str = "female",
    ) -> SyntheticInfluencer:
        """
        Create a new synthetic influencer persona.

        This generates:
        - A consistent visual identity (AI face)
        - A voice profile (ElevenLabs)
        - Base characteristics for video generation

        Args:
            name: Name for the influencer
            style: Persona style
            demographic: Target demographic
            appearance: Visual characteristics
            voice_style: Voice personality
            voice_gender: Male or female voice

        Returns:
            SyntheticInfluencer that can be reused
        """
        logger.info(f"Creating synthetic influencer: {name}")

        influencer_id = uuid.uuid4().hex[:12]

        # Default appearance if not specified
        if appearance is None:
            appearance = self._get_default_appearance(demographic, voice_gender)

        # Generate avatar image
        avatar_url = await self._generate_avatar(appearance, style)

        # Get or create voice
        voice_id = await self._get_voice_id(voice_style, voice_gender)

        influencer = SyntheticInfluencer(
            id=influencer_id,
            name=name,
            style=style,
            demographic=demographic,
            appearance=appearance,
            voice_id=voice_id,
            voice_style=voice_style,
            avatar_image_url=avatar_url,
        )

        self._influencers[influencer_id] = influencer
        return influencer

    async def generate(
        self,
        style: str = "casual",
        platform: str = "tiktok",
        duration_seconds: float = 15.0,
        audio_path: str = None,
        influencer_id: str = None,
        script: str = None,
    ) -> InfluencerResult:
        """
        Generate an influencer video.

        This creates a video of an AI-generated person that can
        then have products composited in.

        Args:
            style: Visual style (casual, professional, etc.)
            platform: Target platform for dimensions
            duration_seconds: Video length
            audio_path: Pre-generated audio to lip-sync
            influencer_id: Existing influencer to use
            script: Script for the influencer to "say"

        Returns:
            InfluencerResult with video path
        """
        logger.info(f"Generating influencer video: {style} for {platform}")
        output_path = self.output_dir / f"influencer_{uuid.uuid4().hex[:8]}.mp4"

        try:
            # Get or create influencer
            if influencer_id and influencer_id in self._influencers:
                influencer = self._influencers[influencer_id]
            else:
                # Create a one-off influencer
                influencer = await self.create_influencer(
                    name=f"Influencer_{uuid.uuid4().hex[:6]}",
                    style=InfluencerStyle(style) if style in [s.value for s in InfluencerStyle] else InfluencerStyle.CASUAL,
                )

            # Get platform dimensions
            resolution = self._get_platform_resolution(platform)

            # Generate the base video
            # This uses AI video generation (Runway, Kling, etc.)
            video_path = await self._generate_base_video(
                influencer=influencer,
                duration=duration_seconds,
                resolution=resolution,
                audio_path=audio_path,
            )

            # Generate thumbnail
            thumbnail_path = await self._generate_thumbnail(video_path)

            # Update influencer stats
            influencer.videos_generated += 1

            return InfluencerResult(
                success=True,
                influencer_id=influencer.id,
                video_path=str(video_path),
                thumbnail_path=thumbnail_path,
                duration_seconds=duration_seconds,
                resolution=resolution,
                influencer=influencer,
                audio_path=audio_path,
                voice_id=influencer.voice_id,
            )

        except Exception as e:
            logger.error(f"Influencer generation failed: {e}")
            return InfluencerResult(
                success=False,
                influencer_id="",
                video_path="",
                error=str(e),
            )

    async def generate_with_product(
        self,
        product_images: List[str],
        product_description: str,
        script: str,
        style: InfluencerStyle = InfluencerStyle.CASUAL,
        platform: str = "tiktok",
        voice_style: str = "friendly",
        voice_gender: str = "female",
        influencer_id: str = None,
    ) -> InfluencerResult:
        """
        Generate complete influencer video with product.

        This is the all-in-one method that:
        1. Creates/uses an influencer
        2. Generates voice from script
        3. Generates video with lip-sync
        4. Composites product naturally

        Args:
            product_images: Product images to show
            product_description: What the product is
            script: What the influencer says
            style: Influencer style
            platform: Target platform
            voice_style: Voice personality
            voice_gender: Male/female
            influencer_id: Existing influencer to reuse

        Returns:
            InfluencerResult with complete video
        """
        logger.info(f"Generating influencer video with product for {platform}")

        try:
            # Step 1: Get or create influencer
            if influencer_id and influencer_id in self._influencers:
                influencer = self._influencers[influencer_id]
            else:
                influencer = await self.create_influencer(
                    name=f"Influencer_{uuid.uuid4().hex[:6]}",
                    style=style,
                    voice_style=voice_style,
                    voice_gender=voice_gender,
                )

            # Step 2: Generate voice audio
            from ..voice.voice_generator import VoiceGenerator
            voice_gen = VoiceGenerator()
            voice_result = await voice_gen.generate_speech(
                text=script,
                voice_style=voice_style,
                gender=voice_gender,
            )

            # Step 3: Generate base video with lip-sync
            resolution = self._get_platform_resolution(platform)
            video_path = await self._generate_base_video(
                influencer=influencer,
                duration=voice_result.duration_seconds + 1,
                resolution=resolution,
                audio_path=voice_result.audio_path,
                lip_sync=True,
            )

            # Step 4: Composite product
            from ..compositing.compositor import Compositor
            compositor = Compositor(segmind_api_key=self.segmind_api_key)

            composite_result = await compositor.composite_product(
                video_path=str(video_path),
                product_images=product_images,
                placement_style="natural_hold",
                product_description=product_description,
            )

            if not composite_result.success:
                raise Exception(f"Compositing failed: {composite_result.error}")

            # Update stats
            influencer.videos_generated += 1

            return InfluencerResult(
                success=True,
                influencer_id=influencer.id,
                video_path=composite_result.output_path,
                thumbnail_path=composite_result.thumbnail_path,
                duration_seconds=voice_result.duration_seconds,
                resolution=resolution,
                influencer=influencer,
                audio_path=voice_result.audio_path,
                voice_id=influencer.voice_id,
            )

        except Exception as e:
            logger.error(f"Full influencer generation failed: {e}")
            return InfluencerResult(
                success=False,
                influencer_id="",
                video_path="",
                error=str(e),
            )

    def get_influencer(self, influencer_id: str) -> Optional[SyntheticInfluencer]:
        """Get an existing influencer by ID."""
        return self._influencers.get(influencer_id)

    def list_influencers(self) -> List[SyntheticInfluencer]:
        """List all created influencers."""
        return list(self._influencers.values())

    async def _generate_avatar(
        self,
        appearance: Dict[str, Any],
        style: InfluencerStyle,
    ) -> str:
        """Generate a consistent avatar image for the influencer.
        
        Returns a URL to the generated avatar image, or a placeholder URL
        when API keys are not configured (mock mode).
        """
        prompt = self._build_avatar_prompt(appearance, style)
        logger.info(f"Generating avatar with prompt: {prompt[:100]}...")

        # Check for Segmind/Replicate API configuration
        from ....core.config import get_settings
        settings = get_settings()
        
        segmind_key = getattr(settings, 'SEGMIND_API_KEY', None) or self.segmind_api_key
        replicate_key = getattr(settings, 'REPLICATE_API_TOKEN', None) or self.replicate_api_key
        
        if not segmind_key and not replicate_key:
            # Mock mode: return a placeholder avatar URL
            logger.warning(
                "Avatar generation running in MOCK mode. "
                "Set SEGMIND_API_KEY or REPLICATE_API_TOKEN for real avatar generation."
            )
            # Generate a placeholder image using a deterministic seed based on appearance
            gender = appearance.get("gender", "female")
            age = appearance.get("age_range", "25-30")
            # Use placeholder service or generate locally
            placeholder_url = await self._generate_placeholder_avatar(appearance, style)
            return placeholder_url
        
        # Real API implementation
        if replicate_key:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.replicate.com/v1/predictions",
                        headers={
                            "Authorization": f"Token {replicate_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",  # SDXL
                            "input": {
                                "prompt": prompt,
                                "negative_prompt": "blurry, low quality, distorted face, extra limbs",
                                "width": 1024,
                                "height": 1024,
                                "num_outputs": 1
                            }
                        },
                        timeout=120.0
                    )
                    response.raise_for_status()
                    prediction = response.json()
                    
                    # Poll for completion
                    prediction_id = prediction["id"]
                    for _ in range(60):  # Max 60 attempts
                        await asyncio.sleep(2)
                        status_response = await client.get(
                            f"https://api.replicate.com/v1/predictions/{prediction_id}",
                            headers={"Authorization": f"Token {replicate_key}"},
                            timeout=30.0
                        )
                        status_response.raise_for_status()
                        status = status_response.json()
                        
                        if status["status"] == "succeeded":
                            return status["output"][0]
                        elif status["status"] == "failed":
                            raise Exception(f"Replicate prediction failed: {status.get('error')}")
                    
                    raise Exception("Replicate prediction timed out")
            except Exception as e:
                logger.error(f"Replicate avatar generation failed: {e}")
                # Fall back to placeholder
                return await self._generate_placeholder_avatar(appearance, style)
        
        # Fallback to placeholder if no working API
        return await self._generate_placeholder_avatar(appearance, style)
    
    async def _generate_placeholder_avatar(
        self,
        appearance: Dict[str, Any],
        style: InfluencerStyle,
    ) -> str:
        """Generate a placeholder avatar image for mock mode.
        
        Creates a simple placeholder image locally or returns a placeholder URL.
        """
        import hashlib
        
        # Create a deterministic seed from appearance
        seed_str = f"{appearance.get('gender', 'female')}_{appearance.get('age_range', '25-30')}_{style.value}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        
        # Create placeholder image locally
        placeholder_path = self.output_dir / f"avatar_placeholder_{seed}.png"
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple placeholder image
            width, height = 512, 512
            img = Image.new('RGB', (width, height), color=(100, 100, 150))
            draw = ImageDraw.Draw(img)
            
            # Add text
            gender = appearance.get("gender", "female")
            text = f"AI Avatar\n{gender.title()}\n{style.value}"
            
            # Draw centered text
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            except:
                font = ImageFont.load_default()
            
            # Calculate text position
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.text((x, y), text, fill=(255, 255, 255), font=font, align="center")
            
            # Add border
            draw.rectangle([0, 0, width-1, height-1], outline=(200, 200, 200), width=3)
            
            img.save(placeholder_path)
            logger.info(f"Generated placeholder avatar: {placeholder_path}")
            return str(placeholder_path)
            
        except ImportError:
            logger.warning("PIL not available, using URL placeholder")
            # Return a placeholder URL from a service
            return f"https://via.placeholder.com/512x512.png?text=AI+Avatar+{style.value}"

    async def _get_voice_id(self, voice_style: str, gender: str) -> str:
        """Get or create an ElevenLabs voice ID."""
        # In production, this would:
        # 1. Use pre-selected voice IDs for different styles
        # 2. Or create custom voices via ElevenLabs voice cloning

        voice_mapping = {
            ("friendly", "female"): "21m00Tcm4TlvDq8ikWAM",  # Rachel
            ("friendly", "male"): "VR6AewLTigWG4xSOukaG",    # Arnold
            ("professional", "female"): "EXAVITQu4vr4xnSDxMaL",  # Bella
            ("professional", "male"): "pNInz6obpgDQGcFmaJgB",   # Adam
            ("energetic", "female"): "jBpfuIE2acCO8z3wKNLl",   # Gigi
            ("energetic", "male"): "yoZ06aMxZJJ28mfd3POQ",     # Sam
        }

        key = (voice_style, gender)
        return voice_mapping.get(key, voice_mapping[("friendly", "female")])

    async def _generate_base_video(
        self,
        influencer: SyntheticInfluencer,
        duration: float,
        resolution: Tuple[int, int],
        audio_path: str = None,
        lip_sync: bool = False,
    ) -> Path:
        """
        Generate the base influencer video.

        This uses AI video generation to create a realistic
        video of the synthetic person.

        Options:
        - Runway Gen-3 Alpha for high quality
        - Kling for longer videos
        - Stable Video Diffusion via Replicate
        
        Falls back to mock mode with placeholder video when API keys unavailable.
        """
        from ....core.config import get_settings
        settings = get_settings()
        
        runway_key = getattr(settings, 'RUNWAY_API_KEY', None) or self.runway_api_key
        replicate_key = getattr(settings, 'REPLICATE_API_TOKEN', None) or self.replicate_api_key
        
        output_path = self.output_dir / f"base_{uuid.uuid4().hex[:8]}.mp4"
        prompt = self._build_video_prompt(influencer)
        
        logger.info(f"Generating base video: {duration}s at {resolution}")
        
        if not runway_key and not replicate_key:
            # Mock mode: generate placeholder video
            logger.warning(
                "Video generation running in MOCK mode. "
                "Set RUNWAY_API_KEY or REPLICATE_API_TOKEN for real video generation."
            )
            return await self._generate_placeholder_video(
                influencer=influencer,
                duration=duration,
                resolution=resolution,
                audio_path=audio_path,
                output_path=output_path
            )
        
        # Real API implementation with Replicate
        if replicate_key:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    # Use Stable Video Diffusion for video generation
                    response = await client.post(
                        "https://api.replicate.com/v1/predictions",
                        headers={
                            "Authorization": f"Token {replicate_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "version": "3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",  # SVD
                            "input": {
                                "input_image": influencer.avatar_image_url,
                                "motion_bucket_id": 127,
                                "fps": 24,
                                "num_frames": int(duration * 24)
                            }
                        },
                        timeout=120.0
                    )
                    response.raise_for_status()
                    prediction = response.json()
                    
                    # Poll for completion
                    prediction_id = prediction["id"]
                    for _ in range(120):  # Max 4 minutes
                        await asyncio.sleep(2)
                        status_response = await client.get(
                            f"https://api.replicate.com/v1/predictions/{prediction_id}",
                            headers={"Authorization": f"Token {replicate_key}"},
                            timeout=30.0
                        )
                        status_response.raise_for_status()
                        status = status_response.json()
                        
                        if status["status"] == "succeeded":
                            # Download the video
                            video_url = status["output"]
                            video_response = await client.get(video_url, timeout=60.0)
                            video_response.raise_for_status()
                            with open(output_path, "wb") as f:
                                f.write(video_response.content)
                            
                            if lip_sync and audio_path:
                                output_path = await self._apply_lip_sync(output_path, audio_path)
                            
                            return output_path
                        elif status["status"] == "failed":
                            raise Exception(f"Replicate prediction failed: {status.get('error')}")
                    
                    raise Exception("Replicate video generation timed out")
            except Exception as e:
                logger.error(f"Replicate video generation failed: {e}")
                # Fall back to placeholder
                return await self._generate_placeholder_video(
                    influencer=influencer,
                    duration=duration,
                    resolution=resolution,
                    audio_path=audio_path,
                    output_path=output_path
                )
        
        # Fallback to placeholder
        return await self._generate_placeholder_video(
            influencer=influencer,
            duration=duration,
            resolution=resolution,
            audio_path=audio_path,
            output_path=output_path
        )
    
    async def _generate_placeholder_video(
        self,
        influencer: SyntheticInfluencer,
        duration: float,
        resolution: Tuple[int, int],
        audio_path: str = None,
        output_path: Path = None,
    ) -> Path:
        """Generate a placeholder video for mock mode.
        
        Creates a simple video with text overlay indicating mock mode.
        """
        import shutil
        
        if output_path is None:
            output_path = self.output_dir / f"placeholder_{uuid.uuid4().hex[:8]}.mp4"
        
        # Check if ffmpeg is available for video generation
        if shutil.which("ffmpeg"):
            try:
                import subprocess
                
                width, height = resolution
                
                # Create a placeholder video using ffmpeg
                # Generate a colored background with text
                filter_complex = (
                    f"color=c=0x3366AA:s={width}x{height}:d={duration},"
                    f"drawtext=text='MOCK MODE':fontsize=72:fontcolor=white:"
                    f"x=(w-text_w)/2:y=h/3,"
                    f"drawtext=text='AI Influencer Video':fontsize=48:fontcolor=white:"
                    f"x=(w-text_w)/2:y=h/2,"
                    f"drawtext=text='{influencer.style.value} style':fontsize=36:fontcolor=yellow:"
                    f"x=(w-text_w)/2:y=2*h/3"
                )
                
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=0x3366AA:s={width}x{height}:d={duration}",
                    "-vf", f"drawtext=text='MOCK MODE - AI Influencer':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h/2",
                ]
                
                if audio_path and Path(audio_path).exists():
                    cmd.extend(["-i", audio_path, "-shortest"])
                
                cmd.extend([
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-t", str(duration),
                    str(output_path)
                ])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    logger.info(f"Generated placeholder video: {output_path}")
                    return output_path
                else:
                    logger.warning(f"FFmpeg failed: {result.stderr}")
            except Exception as e:
                logger.warning(f"FFmpeg placeholder generation failed: {e}")
        
        # Fallback: create a minimal placeholder file
        logger.warning("Creating minimal placeholder video file")
        output_path.touch()
        return output_path
    
    async def _apply_lip_sync(self, video_path: Path, audio_path: str) -> Path:
        """Apply lip-sync to video using audio.
        
        In mock mode, just combines video and audio without actual lip-sync.
        """
        import shutil
        
        output_path = self.output_dir / f"lipsync_{uuid.uuid4().hex[:8]}.mp4"
        
        if shutil.which("ffmpeg"):
            try:
                import subprocess
                
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    str(output_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    return output_path
            except Exception as e:
                logger.warning(f"Lip-sync failed: {e}")
        
        # Return original video if lip-sync fails
        return video_path
    
    async def _generate_thumbnail(self, video_path: Path) -> str:
        """Generate thumbnail from video.
        
        Falls back to placeholder thumbnail if ffmpeg unavailable or video doesn't exist.
        """
        import shutil
        
        thumbnail_path = self.output_dir / f"thumb_{uuid.uuid4().hex[:8]}.jpg"
        
        # Check if ffmpeg is available and video exists
        if shutil.which("ffmpeg") and video_path.exists() and video_path.stat().st_size > 0:
            try:
                import subprocess
                
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(video_path),
                    "-ss", "00:00:01",
                    "-vframes", "1",
                    "-q:v", "2",
                    str(thumbnail_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and thumbnail_path.exists():
                    logger.info(f"Generated thumbnail: {thumbnail_path}")
                    return str(thumbnail_path)
            except Exception as e:
                logger.warning(f"Thumbnail extraction failed: {e}")
        
        # Fallback: generate placeholder thumbnail
        logger.warning("Generating placeholder thumbnail")
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            img = Image.new('RGB', (320, 180), color=(80, 80, 120))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except:
                font = ImageFont.load_default()
            
            draw.text((80, 70), "Video Thumbnail", fill=(255, 255, 255), font=font)
            draw.rectangle([0, 0, 319, 179], outline=(200, 200, 200), width=2)
            
            img.save(thumbnail_path, "JPEG")
            return str(thumbnail_path)
        except ImportError:
            # Return placeholder URL if PIL not available
            return "https://via.placeholder.com/320x180.png?text=Video+Thumbnail"

    def _build_avatar_prompt(
        self,
        appearance: Dict[str, Any],
        style: InfluencerStyle,
    ) -> str:
        """Build prompt for avatar generation."""
        gender = appearance.get("gender", "female")
        age = appearance.get("age_range", "25-30")
        ethnicity = appearance.get("ethnicity", "diverse")

        style_modifiers = {
            InfluencerStyle.CASUAL: "casual wear, friendly smile, natural lighting",
            InfluencerStyle.PROFESSIONAL: "business attire, confident, studio lighting",
            InfluencerStyle.ENERGETIC: "athletic wear, excited expression, dynamic",
            InfluencerStyle.LIFESTYLE: "trendy fashion, aesthetic, golden hour",
            InfluencerStyle.AUTHENTIC: "everyday clothes, genuine smile, natural",
            InfluencerStyle.EXPERT: "smart casual, thoughtful expression, professional",
        }

        modifier = style_modifiers.get(style, style_modifiers[InfluencerStyle.CASUAL])

        prompt = f"""Portrait photo of a {ethnicity} {gender} in their {age}s,
        {modifier}, looking at camera, high quality, photorealistic,
        social media influencer style, 4K, detailed face"""

        return prompt

    def _build_video_prompt(self, influencer: SyntheticInfluencer) -> str:
        """Build prompt for video generation."""
        style = influencer.style
        appearance = influencer.appearance

        gender = appearance.get("gender", "person")

        action_prompts = {
            InfluencerStyle.CASUAL: f"A {gender} casually talking to camera, friendly gestures, living room setting",
            InfluencerStyle.PROFESSIONAL: f"A {gender} speaking professionally to camera, office background",
            InfluencerStyle.ENERGETIC: f"An energetic {gender} excitedly talking, expressive hand movements",
            InfluencerStyle.LIFESTYLE: f"A stylish {gender} in aesthetic setting, natural movements",
            InfluencerStyle.AUTHENTIC: f"A {gender} filming selfie-style, authentic UGC feel",
            InfluencerStyle.EXPERT: f"A knowledgeable {gender} explaining something, confident demeanor",
        }

        return action_prompts.get(style, action_prompts[InfluencerStyle.CASUAL])

    def _get_default_appearance(
        self,
        demographic: InfluencerDemographic,
        gender: str,
    ) -> Dict[str, Any]:
        """Get default appearance for demographic."""
        age_ranges = {
            InfluencerDemographic.GEN_Z: "20-25",
            InfluencerDemographic.MILLENNIAL: "28-35",
            InfluencerDemographic.PROFESSIONAL: "30-45",
            InfluencerDemographic.PARENT: "30-40",
            InfluencerDemographic.SENIOR: "50-60",
        }

        return {
            "gender": gender,
            "age_range": age_ranges.get(demographic, "25-35"),
            "ethnicity": "diverse",
        }

    def _get_platform_resolution(self, platform: str) -> Tuple[int, int]:
        """Get resolution for target platform."""
        resolutions = {
            "tiktok": (1080, 1920),
            "instagram_reels": (1080, 1920),
            "instagram_feed": (1080, 1080),
            "youtube_shorts": (1080, 1920),
            "youtube": (1920, 1080),
            "linkedin": (1920, 1080),
        }
        return resolutions.get(platform, (1080, 1920))
