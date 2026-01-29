"""
Segmind Integration for Premium Image & Video Generation.

Uses best-in-class AI models:
- flux-1.1-pro-ultra: Highest quality images (4MP, excellent text rendering)
- runway-gen4-turbo: Best video generation
- kling-2: Fast video alternative

All generation is brand-authentic through intelligent prompt engineering.
"""
import asyncio
import base64
import os
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import logging

logger = logging.getLogger(__name__)


# API Endpoints - Premium Models Only
MODELS = {
    "image_hero": "https://api.segmind.com/v1/flux-1.1-pro-ultra",
    "image_standard": "https://api.segmind.com/v1/flux-pro",
    "video_premium": "https://api.segmind.com/v2/runway-gen4-turbo",
    "video_fast": "https://api.segmind.com/v1/kling-2",
    "video_text2video": "https://api.segmind.com/v1/kling-text2video",
}

# Platform Dimensions
PLATFORM_DIMS = {
    "instagram_post": (1080, 1080),
    "instagram_story": (1080, 1920),
    "instagram_reel": (1080, 1920),
    "linkedin_post": (1200, 627),
    "linkedin_square": (1080, 1080),
    "twitter_post": (1200, 675),
    "facebook_post": (1200, 630),
    "youtube_thumbnail": (1280, 720),
    "display_banner_large": (728, 90),
    "display_banner_medium": (300, 250),
    "email_header": (600, 400),
    "landing_hero": (1920, 1080),
}


@dataclass
class GeneratedImage:
    """Result of image generation."""
    filename: str
    filepath: str
    width: int
    height: int
    prompt_used: str
    model: str


@dataclass
class GeneratedVideo:
    """Result of video generation."""
    filename: str
    filepath: str
    duration: int
    prompt_used: str
    model: str


class SegmindService:
    """
    Premium image and video generation service.

    Handles:
    - Brand-authentic prompt engineering
    - Multi-format image generation
    - Video generation from images or text
    - Text compositing with brand styling
    """

    def __init__(self, api_key: str, output_dir: str = "outputs"):
        self.api_key = api_key
        self.output_dir = output_dir
        self.client = httpx.AsyncClient(timeout=300.0)

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

    async def generate_image(
        self,
        prompt: str,
        width: int = 1080,
        height: int = 1080,
        brand_colors: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ) -> GeneratedImage:
        """
        Generate a premium quality image.

        Args:
            prompt: The image generation prompt
            width: Image width
            height: Image height
            brand_colors: Optional brand colors for post-processing
            seed: Random seed for reproducibility

        Returns:
            GeneratedImage with file info
        """
        model_url = MODELS["image_hero"]  # Always use best model

        payload = {
            "prompt": prompt,
            "aspect_ratio": self._get_aspect_ratio(width, height),
            "output_format": "png",
            "raw": False,
        }

        if seed is not None:
            payload["seed"] = seed

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        response = await self.client.post(model_url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(f"Segmind error {response.status_code}: {response.text[:500]}")
            raise Exception(f"Segmind API error: {response.status_code}")

        # Save image
        filename = f"{uuid.uuid4().hex[:12]}.png"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "wb") as f:
            f.write(response.content)

        # Apply subtle brand color grading if colors provided
        if brand_colors:
            graded_path = await self._apply_color_grade(filepath, brand_colors)
            if graded_path:
                filepath = graded_path
                filename = os.path.basename(filepath)

        logger.info(f"Generated image: {filename}")

        return GeneratedImage(
            filename=filename,
            filepath=filepath,
            width=width,
            height=height,
            prompt_used=prompt,
            model="flux-1.1-pro-ultra"
        )

    async def generate_image_for_asset(
        self,
        visual_concept: Dict[str, Any],
        platform: str,
        brand_data: Optional[Dict[str, Any]] = None,
    ) -> GeneratedImage:
        """
        Generate an image based on asset visual specification.

        Args:
            visual_concept: Visual specification from CreativeDirector
            platform: Target platform (instagram_post, linkedin_post, etc.)
            brand_data: Brand information for styling

        Returns:
            GeneratedImage
        """
        # Get dimensions for platform
        width, height = PLATFORM_DIMS.get(platform, (1080, 1080))

        # Build comprehensive prompt
        prompt = self._build_image_prompt(visual_concept, brand_data)

        # Get brand colors
        brand_colors = None
        if brand_data:
            visual_identity = brand_data.get("visual_identity", {})
            primary = visual_identity.get("primary_color")
            secondary = visual_identity.get("secondary_colors", [])
            if primary:
                brand_colors = [primary] + secondary[:2]

        return await self.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            brand_colors=brand_colors
        )

    def _build_image_prompt(
        self,
        visual_concept: Dict[str, Any],
        brand_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build a detailed image generation prompt from visual concept."""
        parts = []

        # Main visual description
        if visual_concept.get("description"):
            parts.append(visual_concept["description"])

        # Style and mood
        if visual_concept.get("style"):
            parts.append(f"Style: {visual_concept['style']}")

        if visual_concept.get("mood"):
            parts.append(f"Mood: {visual_concept['mood']}")

        # Composition
        if visual_concept.get("composition_notes"):
            parts.append(visual_concept["composition_notes"])

        # Reference keywords for generation
        if visual_concept.get("reference_keywords"):
            parts.append(", ".join(visual_concept["reference_keywords"]))

        # Brand tone influence
        if brand_data:
            tone = brand_data.get("voice", {}).get("tone", [])
            if tone:
                tone_str = ", ".join(tone[:3])
                parts.append(f"{tone_str} aesthetic")

        # Technical quality markers
        parts.append("professional photography, 8k resolution, sharp focus, masterful composition")

        # Important: No text in the image
        parts.append("no text, no words, no letters, no watermarks")

        return ", ".join(parts)

    async def generate_video(
        self,
        prompt: str,
        source_image: Optional[str] = None,
        duration: int = 5,
        use_premium: bool = True,
    ) -> GeneratedVideo:
        """
        Generate a premium video.

        Args:
            prompt: Video description/motion prompt
            source_image: Optional source image path for image-to-video
            duration: Video duration in seconds
            use_premium: Use Runway (best) vs Kling (fast)

        Returns:
            GeneratedVideo with file info
        """
        if source_image:
            model_url = MODELS["video_premium"] if use_premium else MODELS["video_fast"]

            # Read and encode source image
            with open(source_image, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            if use_premium:
                payload = {
                    "text_prompt": prompt,
                    "image": img_b64,
                    "duration": duration,
                    "ratio": "16:9",
                }
            else:
                payload = {
                    "prompt": prompt,
                    "image": img_b64,
                    "duration": str(duration),
                    "aspect_ratio": "16:9",
                }
        else:
            model_url = MODELS["video_text2video"]
            payload = {
                "prompt": prompt,
                "duration": str(duration),
                "aspect_ratio": "16:9",
            }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        logger.info(f"Generating video with {model_url}...")

        response = await self.client.post(model_url, headers=headers, json=payload)

        if response.status_code != 200:
            logger.error(f"Video error {response.status_code}: {response.text[:500]}")
            raise Exception(f"Video API error: {response.status_code}")

        content_type = response.headers.get("content-type", "")

        # Handle async response (request_id polling)
        if content_type.startswith("application/json"):
            data = response.json()
            if "request_id" in data:
                filename = await self._poll_video_result(data["request_id"])
            else:
                raise Exception(f"Unexpected response: {data}")
        else:
            # Direct video content
            filename = f"{uuid.uuid4().hex[:12]}.mp4"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)

        filepath = os.path.join(self.output_dir, filename)
        logger.info(f"Generated video: {filename}")

        return GeneratedVideo(
            filename=filename,
            filepath=filepath,
            duration=duration,
            prompt_used=prompt,
            model="runway-gen4-turbo" if use_premium else "kling-2"
        )

    async def _poll_video_result(self, request_id: str, max_wait: int = 600) -> str:
        """Poll for async video generation result."""
        poll_url = f"https://api.segmind.com/v2/request/{request_id}"
        headers = {"x-api-key": self.api_key}

        import time
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"Video generation timed out after {max_wait}s")

            response = await self.client.get(poll_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                status = data.get("status")

                if status == "completed":
                    video_url = data.get("output", {}).get("video_url") or data.get("video_url")
                    if video_url:
                        video_response = await self.client.get(video_url)

                        filename = f"{uuid.uuid4().hex[:12]}.mp4"
                        filepath = os.path.join(self.output_dir, filename)
                        with open(filepath, "wb") as f:
                            f.write(video_response.content)
                        return filename
                    else:
                        raise Exception("No video URL in response")

                elif status == "failed":
                    raise Exception(f"Video generation failed: {data.get('error', 'Unknown error')}")

                logger.info(f"Video generation in progress... ({int(elapsed)}s)")

            await asyncio.sleep(10)

    async def composite_text(
        self,
        image_path: str,
        headline: Optional[str] = None,
        subheadline: Optional[str] = None,
        cta: Optional[str] = None,
        brand_colors: Optional[List[str]] = None,
        position: str = "center",
    ) -> str:
        """
        Add text overlay to an image with brand styling.

        Args:
            image_path: Path to source image
            headline: Main headline text
            subheadline: Secondary text
            cta: Call-to-action button text
            brand_colors: Brand colors for styling
            position: Text position (top, center, bottom)

        Returns:
            Path to composited image
        """
        img = Image.open(image_path)
        W, H = img.size

        # Determine text colors
        text_color = "#FFFFFF"
        shadow_color = "#000000"
        btn_color = brand_colors[0] if brand_colors else "#7C3AED"

        # Add text backdrop for readability
        img = self._add_text_backdrop(img, position)

        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                int(W * 0.055)
            )
            font_medium = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                int(W * 0.032)
            )
            font_cta = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                int(W * 0.028)
            )
        except (OSError, IOError):
            # Font files not found, use default
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_cta = font_large

        # Calculate starting position
        if position == "top":
            y_cursor = H * 0.15
        elif position == "bottom":
            y_cursor = H * 0.65
        else:  # center
            y_cursor = H * 0.4

        # Draw headline
        if headline:
            headline = self._wrap_text(headline, font_large, W * 0.85)
            for line in headline.split('\n'):
                bbox = draw.textbbox((0, 0), line, font=font_large)
                text_w = bbox[2] - bbox[0]
                x = (W - text_w) // 2

                # Shadow for readability
                draw.text((x + 2, y_cursor + 2), line, font=font_large, fill=shadow_color)
                draw.text((x, y_cursor), line, font=font_large, fill=text_color)
                y_cursor += bbox[3] - bbox[1] + 10

            y_cursor += 15

        # Draw subheadline
        if subheadline:
            subheadline = self._wrap_text(subheadline, font_medium, W * 0.8)
            for line in subheadline.split('\n'):
                bbox = draw.textbbox((0, 0), line, font=font_medium)
                text_w = bbox[2] - bbox[0]
                x = (W - text_w) // 2

                draw.text((x + 1, y_cursor + 1), line, font=font_medium, fill=shadow_color)
                draw.text((x, y_cursor), line, font=font_medium, fill=text_color)
                y_cursor += bbox[3] - bbox[1] + 8

            y_cursor += 20

        # Draw CTA button
        if cta:
            bbox = draw.textbbox((0, 0), cta, font=font_cta)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            padding_x = 25
            padding_y = 12
            btn_x = (W - text_w - padding_x * 2) // 2
            btn_y = y_cursor

            draw.rounded_rectangle(
                [btn_x, btn_y, btn_x + text_w + padding_x * 2, btn_y + text_h + padding_y * 2],
                radius=8,
                fill=btn_color
            )
            draw.text((btn_x + padding_x, btn_y + padding_y), cta, font=font_cta, fill="#FFFFFF")

        # Save
        filename = f"{uuid.uuid4().hex[:12]}_text.png"
        filepath = os.path.join(self.output_dir, filename)
        img.save(filepath, "PNG", quality=95)

        logger.info(f"Composited text: {filename}")
        return filepath

    def _add_text_backdrop(self, img: Image.Image, position: str) -> Image.Image:
        """Add gradient backdrop for text readability."""
        W, H = img.size
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        if position == "top":
            for i in range(int(H * 0.5)):
                alpha = int(120 * (1 - i / (H * 0.5)))
                draw.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))
        elif position == "bottom":
            start = int(H * 0.5)
            for i in range(start, H):
                alpha = int(120 * ((i - start) / (H * 0.5)))
                draw.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))
        else:  # center - vignette
            for i in range(H):
                dist_from_center = abs(i - H * 0.5) / (H * 0.5)
                alpha = int(100 * (1 - dist_from_center * 0.7))
                draw.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))

        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)
        return img.convert("RGB")

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    async def _apply_color_grade(
        self,
        image_path: str,
        brand_colors: List[str],
        intensity: float = 0.12
    ) -> Optional[str]:
        """Apply subtle brand color grading."""
        try:
            primary = brand_colors[0]
            if not primary or not primary.startswith("#"):
                return None

            # Parse color
            hex_str = primary[1:]
            if len(hex_str) == 3:
                hex_str = hex_str[0]*2 + hex_str[1]*2 + hex_str[2]*2

            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)

            # Open and blend
            img = Image.open(image_path).convert("RGB")
            overlay = Image.new("RGB", img.size, (r, g, b))
            graded = Image.blend(img, overlay, intensity)

            # Restore contrast
            enhancer = ImageEnhance.Contrast(graded)
            graded = enhancer.enhance(1.1)

            # Save
            filename = os.path.basename(image_path).replace(".png", "_graded.png")
            filepath = os.path.join(self.output_dir, filename)
            graded.save(filepath, "PNG", quality=95)

            return filepath

        except Exception as e:
            logger.warning(f"Color grading failed: {e}")
            return None

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """Convert dimensions to Flux aspect ratio string."""
        ratio = width / height
        if ratio > 1.7:
            return "16:9"
        elif ratio > 1.3:
            return "4:3"
        elif ratio > 0.9:
            return "1:1"
        elif ratio > 0.7:
            return "3:4"
        else:
            return "9:16"

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
