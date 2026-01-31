"""
Halftime Compositor - Intelligent video compositing with scene-aware rendering.

Based on the XAI Hackathon winner "Halftime" approach, this module:
- Matches generated assets to scene lighting and physics
- Performs seamless product placement without disrupting content
- Integrates with SegMind for image generation
- Uses FFmpeg for final video compositing
- Supports UGC-style effects for TikTok, Instagram, YouTube formats

Architecture:
Scene Analysis + Insertion Zones + Asset Generation → Context-Aware Rendering → 
Dynamic Compositing → FFmpeg Processing → Output
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import tempfile
import subprocess
import os
import asyncio

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import httpx

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    np = None

from .grok_scene_analyzer import VideoAnalysis, SceneContext, LightingInfo
from .insertion_zone_detector import InsertionZone, PlacementRecommendation, ZoneType

logger = logging.getLogger(__name__)


@dataclass
class CompositingConfig:
    """Configuration for video compositing."""
    # Output settings
    output_resolution: Tuple[int, int] = (1080, 1920)  # Default vertical
    output_format: str = "mp4"
    quality: str = "high"  # low, medium, high
    
    # Style settings
    style: str = "natural"  # natural, prominent, subtle, ugc
    ugc_effects: bool = False
    platform: str = "tiktok"  # tiktok, instagram, youtube
    
    # Technical settings
    match_lighting: bool = True
    match_perspective: bool = True
    add_shadows: bool = True
    motion_blur: bool = False
    
    # Timing
    start_time: float = 0.0
    duration: Optional[float] = None


@dataclass
class GeneratedAsset:
    """A generated product asset ready for compositing."""
    image: Image.Image
    mask: Image.Image  # Alpha mask
    original_url: Optional[str] = None
    generation_prompt: str = ""
    lighting_profile: Dict[str, Any] = None


@dataclass
class CompositedFrame:
    """A frame with composited product."""
    frame_index: int
    timestamp: float
    original_frame: Image.Image
    composited_frame: Image.Image
    placement_zone: InsertionZone
    transform_params: Dict[str, Any]


@dataclass
class HalftimeResult:
    """Result of Halftime compositing."""
    success: bool
    output_path: Optional[str] = None
    output_url: Optional[str] = None
    duration_seconds: float = 0.0
    frames_processed: int = 0
    placement_info: Dict[str, Any] = None
    error: Optional[str] = None


class HalftimeCompositor:
    """
    Intelligent video compositor for seamless product placement.
    
    Features:
    - Scene-aware rendering that matches lighting and physics
    - Integration with SegMind for product image generation
    - FFmpeg-based video processing
    - UGC-style effects for social platforms
    - Support for multiple output formats
    
    Usage:
        compositor = HalftimeCompositor(segmind_api_key="...")
        result = await compositor.composite_product(
            video_path="input.mp4",
            product_description="Red energy drink can",
            video_analysis=analysis,
            placement=placement_recommendation
        )
    """
    
    def __init__(
        self,
        segmind_api_key: Optional[str] = None,
        output_dir: str = "outputs/kata/halftime"
    ):
        self.segmind_api_key = segmind_api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._http_client = httpx.AsyncClient(timeout=300.0)
    
    async def generate_product_asset(
        self,
        product_description: str,
        scene_context: SceneContext,
        style: str = "photorealistic",
        size: Tuple[int, int] = (512, 512)
    ) -> Optional[GeneratedAsset]:
        """
        Generate a product image using SegMind that matches the scene.
        
        Args:
            product_description: Description of the product
            scene_context: Scene analysis for matching
            style: Generation style
            size: Output image size
            
        Returns:
            GeneratedAsset or None if generation fails
        """
        if not self.segmind_api_key:
            logger.error("SegMind API key not configured")
            return None
        
        # Build prompt with scene context
        lighting_desc = f"{scene_context.lighting.type} lighting, {scene_context.lighting.direction} light"
        color_desc = f"colors: {', '.join(scene_context.dominant_colors[:3])}"
        
        prompt = f"""Product photography of {product_description}.
{lighting_desc}, {color_desc}.
{style}, professional product shot, isolated on transparent background, 
studio lighting matching scene, high detail, 8k quality"""
        
        try:
            # Call SegMind API
            url = "https://api.segmind.com/v1/flux-1.1-pro-ultra"
            
            payload = {
                "prompt": prompt,
                "width": size[0],
                "height": size[1],
                "output_format": "png",  # PNG for transparency
                "raw": False
            }
            
            headers = {
                "x-api-key": self.segmind_api_key,
                "Content-Type": "application/json"
            }
            
            response = await self._http_client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # Load image from response
            from io import BytesIO
            image = Image.open(BytesIO(response.content))
            
            # Create mask (simplified - would use background removal in production)
            mask = self._create_alpha_mask(image)
            
            return GeneratedAsset(
                image=image,
                mask=mask,
                generation_prompt=prompt,
                lighting_profile={
                    "type": scene_context.lighting.type,
                    "direction": scene_context.lighting.direction,
                    "intensity": scene_context.lighting.intensity,
                    "dominant_colors": scene_context.dominant_colors
                }
            )
            
        except Exception as e:
            logger.error(f"Product generation failed: {e}")
            return None
    
    def _create_alpha_mask(self, image: Image.Image) -> Image.Image:
        """Create an alpha mask for the product image."""
        # Convert to RGBA if needed
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Extract alpha channel or create from brightness
        r, g, b, a = image.split()
        
        # If image has transparency, use it
        if a.getextrema()[1] > 0:
            return a
        
        # Otherwise, create mask from brightness (white = foreground)
        gray = ImageOps.grayscale(image)
        # Invert so white areas become opaque
        mask = ImageOps.invert(gray)
        return mask
    
    def match_lighting(
        self,
        asset: GeneratedAsset,
        target_lighting: LightingInfo
    ) -> Image.Image:
        """
        Adjust asset lighting to match scene.
        
        Args:
            asset: The generated asset
            target_lighting: Target lighting conditions
            
        Returns:
            Adjusted image
        """
        image = asset.image.copy()
        
        # Adjust brightness based on intensity
        brightness_factor = target_lighting.intensity * 1.5  # Scale up a bit
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(brightness_factor)
        
        # Adjust color temperature
        if target_lighting.color_temperature == "warm":
            # Add warmth (increase red/yellow)
            r, g, b, a = image.split()
            r = r.point(lambda i: min(255, int(i * 1.1)))
            b = b.point(lambda i: int(i * 0.9))
            image = Image.merge('RGBA', (r, g, b, a))
        elif target_lighting.color_temperature == "cool":
            # Add coolness (increase blue)
            r, g, b, a = image.split()
            r = r.point(lambda i: int(i * 0.9))
            b = b.point(lambda i: min(255, int(i * 1.1)))
            image = Image.merge('RGBA', (r, g, b, a))
        
        # Adjust contrast based on shadows
        if target_lighting.shadows == "hard":
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
        elif target_lighting.shadows == "soft":
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(0.9)
        
        return image
    
    def add_shadow(
        self,
        image: Image.Image,
        zone: InsertionZone,
        lighting: LightingInfo
    ) -> Image.Image:
        """
        Add realistic shadow to product.
        
        Args:
            image: Product image with alpha
            zone: Placement zone
            lighting: Lighting info
            
        Returns:
            Image with shadow
        """
        # Create shadow layer
        shadow = Image.new('RGBA', image.size, (0, 0, 0, 0))
        
        # Get alpha mask
        if image.mode == 'RGBA':
            alpha = image.split()[3]
        else:
            alpha = Image.new('L', image.size, 255)
        
        # Create shadow based on light direction
        shadow_offset_x = 10
        shadow_offset_y = 10
        
        if lighting.direction == "front":
            shadow_offset_x, shadow_offset_y = 0, 5
        elif lighting.direction == "back":
            shadow_offset_x, shadow_offset_y = 0, -10
        elif lighting.direction == "side":
            shadow_offset_x, shadow_offset_y = 15, 5
        elif lighting.direction == "top":
            shadow_offset_x, shadow_offset_y = 0, 15
        
        # Blur alpha for shadow
        shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(radius=8))
        # Reduce opacity
        shadow_alpha = shadow_alpha.point(lambda p: int(p * 0.3))
        
        # Create shadow image
        shadow_rgba = Image.merge('RGBA', [
            Image.new('L', image.size, 0),
            Image.new('L', image.size, 0),
            Image.new('L', image.size, 0),
            shadow_alpha
        ])
        
        # Composite shadow and product
        canvas = Image.new('RGBA', image.size, (0, 0, 0, 0))
        canvas.paste(shadow_rgba, (shadow_offset_x, shadow_offset_y), shadow_alpha)
        canvas.paste(image, (0, 0), alpha)
        
        return canvas
    
    def transform_for_placement(
        self,
        image: Image.Image,
        zone: InsertionZone,
        frame_size: Tuple[int, int]
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Transform product image for placement in zone.
        
        Args:
            image: Product image
            zone: Target zone
            frame_size: Size of video frame
            
        Returns:
            Transformed image and transform parameters
        """
        # Calculate target size based on zone
        zone_width = int(frame_size[0] * zone.normalized_bbox[2])
        zone_height = int(frame_size[1] * zone.normalized_bbox[3])
        
        # Scale based on suggested scale
        target_width = int(zone_width * zone.suggested_scale * 3)
        target_height = int(target_width * image.height / image.width)
        
        # Resize
        resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Rotate if needed
        if zone.suggested_rotation != 0:
            resized = resized.rotate(
                zone.suggested_rotation,
                expand=True,
                resample=Image.Resampling.BICUBIC
            )
        
        # Calculate position
        zone_x = int(frame_size[0] * zone.normalized_bbox[0])
        zone_y = int(frame_size[1] * zone.normalized_bbox[1])
        
        # Center in zone
        pos_x = zone_x + (zone_width - resized.width) // 2
        pos_y = zone_y + (zone_height - resized.height) // 2
        
        transform_params = {
            "scale": zone.suggested_scale,
            "rotation": zone.suggested_rotation,
            "position": (pos_x, pos_y),
            "size": (resized.width, resized.height)
        }
        
        return resized, transform_params
    
    def composite_frame(
        self,
        frame: Image.Image,
        asset: GeneratedAsset,
        zone: InsertionZone,
        lighting: LightingInfo,
        add_shadow: bool = True
    ) -> Image.Image:
        """
        Composite product into a single frame.
        
        Args:
            frame: Video frame
            asset: Product asset
            zone: Placement zone
            lighting: Scene lighting
            add_shadow: Whether to add shadow
            
        Returns:
            Composited frame
        """
        # Match lighting
        adjusted_asset = self.match_lighting(asset, lighting)
        
        # Add shadow
        if add_shadow:
            adjusted_asset = self.add_shadow(adjusted_asset, zone, lighting)
        
        # Transform for placement
        transformed, params = self.transform_for_placement(
            adjusted_asset, zone, frame.size
        )
        
        # Composite onto frame
        pos_x, pos_y = params["position"]
        
        # Ensure frame is RGBA
        if frame.mode != 'RGBA':
            frame = frame.convert('RGBA')
        
        # Create canvas and paste
        canvas = frame.copy()
        canvas.paste(transformed, (pos_x, pos_y), transformed)
        
        # Convert back to RGB
        final = canvas.convert('RGB')
        
        return final
    
    def apply_ugc_effects(
        self,
        frame: Image.Image,
        platform: str = "tiktok",
        intensity: float = 0.3
    ) -> Image.Image:
        """
        Apply UGC-style effects to make content look authentic.
        
        Args:
            frame: Video frame
            platform: Target platform style
            intensity: Effect intensity 0-1
            
        Returns:
            Frame with effects
        """
        if intensity <= 0:
            return frame
        
        image = frame.copy()
        
        # Platform-specific adjustments
        if platform == "tiktok":
            # Slightly oversaturated, vibrant
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.0 + 0.1 * intensity)
            
            # Slight contrast boost
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.0 + 0.05 * intensity)
            
        elif platform == "instagram":
            # Warmer tones
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.0 + 0.08 * intensity)
            
        elif platform == "youtube":
            # More natural, slight clarity
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.0 + 0.1 * intensity)
        
        # Add subtle grain/noise for authenticity
        if CV2_AVAILABLE and intensity > 0.2:
            img_array = np.array(image)
            noise = np.random.normal(0, 3 * intensity, img_array.shape).astype(np.uint8)
            img_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            image = Image.fromarray(img_array)
        
        return image
    
    async def composite_product(
        self,
        video_path: str,
        product_description: str,
        video_analysis: VideoAnalysis,
        placement: PlacementRecommendation,
        config: Optional[CompositingConfig] = None
    ) -> HalftimeResult:
        """
        Main compositing pipeline.
        
        Args:
            video_path: Input video path
            product_description: Product to insert
            video_analysis: Video analysis from GrokSceneAnalyzer
            placement: Placement recommendation
            config: Compositing configuration
            
        Returns:
            HalftimeResult with output video
        """
        if config is None:
            config = CompositingConfig()
        
        if not CV2_AVAILABLE:
            return HalftimeResult(
                success=False,
                error="OpenCV required for video processing"
            )
        
        try:
            # Generate product asset
            logger.info(f"Generating product asset: {product_description}")
            
            # Use first keyframe scene for generation
            scene = video_analysis.keyframe_scenes[0] if video_analysis.keyframe_scenes else None
            
            if scene:
                asset = await self.generate_product_asset(
                    product_description=product_description,
                    scene_context=scene
                )
            else:
                return HalftimeResult(
                    success=False,
                    error="No scene analysis available"
                )
            
            if not asset:
                return HalftimeResult(
                    success=False,
                    error="Failed to generate product asset"
                )
            
            # Open video
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Setup output
            output_filename = f"halftime_{Path(video_path).stem}_{int(asyncio.get_event_loop().time())}.mp4"
            output_path = self.output_dir / output_filename
            
            # Video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                str(output_path),
                fourcc,
                fps,
                config.output_resolution,
                True
            )
            
            # Determine which frames to composite
            zone = placement.zone
            start_frame = int(config.start_time * fps)
            
            if config.duration:
                end_frame = start_frame + int(config.duration * fps)
            else:
                end_frame = total_frames
            
            end_frame = min(end_frame, total_frames)
            
            frames_processed = 0
            
            logger.info(f"Processing frames {start_frame} to {end_frame}")
            
            # Process frames
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_frame = Image.fromarray(frame_rgb)
                
                # Resize to output resolution
                pil_frame = pil_frame.resize(config.output_resolution, Image.Resampling.LANCZOS)
                
                # Composite if in range
                if start_frame <= frame_idx < end_frame:
                    # Get lighting from nearest keyframe
                    nearest_scene = self._get_nearest_scene(
                        frame_idx, fps, video_analysis.keyframe_scenes
                    )
                    
                    if nearest_scene:
                        pil_frame = self.composite_frame(
                            pil_frame,
                            asset,
                            zone,
                            nearest_scene.lighting,
                            add_shadow=config.add_shadows
                        )
                
                # Apply UGC effects
                if config.ugc_effects:
                    pil_frame = self.apply_ugc_effects(
                        pil_frame,
                        platform=config.platform,
                        intensity=0.3
                    )
                
                # Convert back to OpenCV
                final_frame = cv2.cvtColor(np.array(pil_frame), cv2.COLOR_RGB2BGR)
                out.write(final_frame)
                
                frames_processed += 1
                frame_idx += 1
                
                if frame_idx % 30 == 0:
                    logger.debug(f"Processed frame {frame_idx}/{total_frames}")
            
            cap.release()
            out.release()
            
            # Post-process with FFmpeg for better quality
            final_output = await self._ffmpeg_post_process(
                str(output_path),
                config
            )
            
            logger.info(f"Compositing complete: {final_output}")
            
            return HalftimeResult(
                success=True,
                output_path=final_output,
                duration_seconds=frames_processed / fps,
                frames_processed=frames_processed,
                placement_info={
                    "zone_type": zone.zone_type.value,
                    "position": zone.normalized_bbox,
                    "confidence": placement.confidence,
                    "reasoning": placement.reasoning
                }
            )
            
        except Exception as e:
            logger.error(f"Compositing failed: {e}")
            return HalftimeResult(
                success=False,
                error=str(e)
            )
    
    def _get_nearest_scene(
        self,
        frame_idx: int,
        fps: float,
        scenes: List[SceneContext]
    ) -> Optional[SceneContext]:
        """Get the scene context nearest to the current frame."""
        if not scenes:
            return None
        
        current_time = frame_idx / fps
        
        nearest = min(scenes, key=lambda s: abs(s.timestamp - current_time))
        return nearest
    
    async def _ffmpeg_post_process(
        self,
        input_path: str,
        config: CompositingConfig
    ) -> str:
        """
        Post-process video with FFmpeg for optimal quality.
        
        Args:
            input_path: Path to raw output
            config: Configuration
            
        Returns:
            Path to final video
        """
        output_path = input_path.replace('.mp4', '_final.mp4')
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '18' if config.quality == 'high' else '23',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',  # Web optimization
            output_path
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Remove intermediate file
                os.remove(input_path)
                return output_path
            else:
                logger.warning(f"FFmpeg post-processing failed, using raw output")
                return input_path
                
        except FileNotFoundError:
            logger.warning("FFmpeg not found, using raw output")
            return input_path
        except Exception as e:
            logger.error(f"FFmpeg error: {e}")
            return input_path
    
    async def create_ugc_style_video(
        self,
        video_path: str,
        product_description: str,
        platform: str = "tiktok",
        duration: Optional[float] = None
    ) -> HalftimeResult:
        """
        Create UGC-style video with product placement.
        
        Convenience method that runs the full pipeline with UGC effects.
        
        Args:
            video_path: Input video
            product_description: Product to place
            platform: Target platform
            duration: Optional duration limit
            
        Returns:
            HalftimeResult
        """
        from .grok_scene_analyzer import GrokSceneAnalyzer
        from ...core.config import get_settings
        
        settings = get_settings()
        
        # Check for xAI API key - required for video analysis
        xai_api_key = getattr(settings, 'xai_api_key', None) or ""
        if not xai_api_key:
            raise NotImplementedError(
                "Video analysis requires xAI API key. "
                "Set XAI_API_KEY environment variable to enable Grok vision analysis. "
                "See: https://x.ai/api for API access."
            )
        
        # Analyze video with Grok vision
        analyzer = GrokSceneAnalyzer(api_key=xai_api_key, model="grok-2-vision-latest")
        
        # Perform actual video analysis
        video_analysis = await analyzer.analyze_video(video_path)
        
        if not video_analysis:
            raise RuntimeError(f"Failed to analyze video: {video_path}")
        
        # Create placement recommendation
        from .insertion_zone_detector import InsertionZoneDetector, PlacementStyle
        detector = InsertionZoneDetector()
        
        # Open first frame for zone detection
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            zones = detector.detect_zones(pil_frame)
            
            placement = detector.get_best_placement(
                zones,
                product_type="product",
                placement_style=PlacementStyle.NATURAL
            )
        else:
            placement = None
        
        if not placement:
            return HalftimeResult(
                success=False,
                error="Could not determine placement zone"
            )
        
        # Configure for UGC
        config = CompositingConfig(
            output_resolution=(1080, 1920),
            style="ugc",
            ugc_effects=True,
            platform=platform,
            quality="high",
            duration=duration
        )
        
        return await self.composite_product(
            video_path=video_path,
            product_description=product_description,
            video_analysis=video_analysis,
            placement=placement,
            config=config
        )
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
