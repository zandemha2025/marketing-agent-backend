"""
Image Generation Service with Multiple Backend Support.

Supports:
- Segmind API (primary)
- Replicate API (fallback)
- Mock/placeholder images (for testing without API keys)

Provides a unified interface for image generation with automatic fallback.
"""
import os
import uuid
import base64
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ImageStyle(str, Enum):
    """Supported image generation styles."""
    PHOTOREALISTIC = "photorealistic"
    ARTISTIC = "artistic"
    MINIMAL = "minimal"


@dataclass
class GeneratedImageResult:
    """Result of image generation."""
    success: bool
    asset_id: str
    url: Optional[str] = None
    filepath: Optional[str] = None
    width: int = 1024
    height: int = 1024
    prompt: str = ""
    style: str = "photorealistic"
    error: Optional[str] = None
    backend_used: Optional[str] = None


# Style-specific prompt modifiers
STYLE_MODIFIERS = {
    ImageStyle.PHOTOREALISTIC: (
        "professional photography, 8k resolution, sharp focus, "
        "photorealistic, highly detailed, natural lighting"
    ),
    ImageStyle.ARTISTIC: (
        "artistic interpretation, creative composition, "
        "vibrant colors, expressive brushstrokes, fine art style"
    ),
    ImageStyle.MINIMAL: (
        "minimalist design, clean lines, simple composition, "
        "negative space, modern aesthetic, elegant simplicity"
    ),
}


class ImageGeneratorService:
    """
    Unified image generation service with multiple backend support.
    
    Automatically falls back through available backends:
    1. Segmind API (if SEGMIND_API_KEY is set)
    2. Replicate API (if REPLICATE_API_TOKEN is set)
    3. Mock placeholder (always available for testing)
    """
    
    def __init__(
        self,
        segmind_api_key: Optional[str] = None,
        replicate_api_token: Optional[str] = None,
        output_dir: str = "outputs/generated_images"
    ):
        self.segmind_api_key = segmind_api_key
        self.replicate_api_token = replicate_api_token
        self.output_dir = output_dir
        self.client = httpx.AsyncClient(timeout=120.0)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"ImageGeneratorService initialized. Segmind: {'✓' if segmind_api_key else '✗'}, Replicate: {'✓' if replicate_api_token else '✗'}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def generate_image(
        self,
        prompt: str,
        style: str = "photorealistic",
        width: int = 1024,
        height: int = 1024,
        negative_prompt: Optional[str] = None,
    ) -> GeneratedImageResult:
        """
        Generate an image using the best available backend.
        
        Args:
            prompt: The image generation prompt
            style: Style preset (photorealistic, artistic, minimal)
            width: Image width
            height: Image height
            negative_prompt: Things to avoid in the image
            
        Returns:
            GeneratedImageResult with image URL and metadata
        """
        asset_id = uuid.uuid4().hex[:16]
        
        # Normalize style
        try:
            style_enum = ImageStyle(style.lower())
        except ValueError:
            style_enum = ImageStyle.PHOTOREALISTIC
        
        # Build enhanced prompt with style modifiers
        enhanced_prompt = self._build_enhanced_prompt(prompt, style_enum)
        
        # Try backends in order of preference
        if self.segmind_api_key:
            try:
                result = await self._generate_with_segmind(
                    asset_id=asset_id,
                    prompt=enhanced_prompt,
                    width=width,
                    height=height,
                    negative_prompt=negative_prompt,
                    original_prompt=prompt,
                    style=style,
                )
                if result.success:
                    return result
                logger.warning(f"Segmind failed: {result.error}, trying fallback...")
            except Exception as e:
                logger.warning(f"Segmind exception: {e}, trying fallback...")
        
        if self.replicate_api_token:
            try:
                result = await self._generate_with_replicate(
                    asset_id=asset_id,
                    prompt=enhanced_prompt,
                    width=width,
                    height=height,
                    negative_prompt=negative_prompt,
                    original_prompt=prompt,
                    style=style,
                )
                if result.success:
                    return result
                logger.warning(f"Replicate failed: {result.error}, trying fallback...")
            except Exception as e:
                logger.warning(f"Replicate exception: {e}, trying fallback...")
        
        # Fallback to mock/placeholder
        logger.info("Using mock image generator (no API keys available)")
        return await self._generate_mock_image(
            asset_id=asset_id,
            prompt=prompt,
            style=style,
            width=width,
            height=height,
        )
    
    def _build_enhanced_prompt(self, prompt: str, style: ImageStyle) -> str:
        """Build an enhanced prompt with style modifiers."""
        style_modifier = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS[ImageStyle.PHOTOREALISTIC])
        return f"{prompt}, {style_modifier}"
    
    async def _generate_with_segmind(
        self,
        asset_id: str,
        prompt: str,
        width: int,
        height: int,
        negative_prompt: Optional[str],
        original_prompt: str,
        style: str,
    ) -> GeneratedImageResult:
        """Generate image using Segmind API (Flux model)."""
        model_url = "https://api.segmind.com/v1/flux-1.1-pro-ultra"
        
        # Calculate aspect ratio
        aspect_ratio = self._get_aspect_ratio(width, height)
        
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
            "raw": False,
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        headers = {
            "x-api-key": self.segmind_api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Generating image with Segmind: {prompt[:100]}...")
        
        response = await self.client.post(model_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            error_msg = f"Segmind API error {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            return GeneratedImageResult(
                success=False,
                asset_id=asset_id,
                width=width,
                height=height,
                prompt=original_prompt,
                style=style,
                error=error_msg,
                backend_used="segmind"
            )
        
        # Save image
        filename = f"{asset_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        # Generate URL (relative path for now, can be replaced with S3 URL)
        url = f"/outputs/generated_images/{filename}"
        
        logger.info(f"Segmind image generated: {filepath}")
        
        return GeneratedImageResult(
            success=True,
            asset_id=asset_id,
            url=url,
            filepath=filepath,
            width=width,
            height=height,
            prompt=original_prompt,
            style=style,
            backend_used="segmind"
        )
    
    async def _generate_with_replicate(
        self,
        asset_id: str,
        prompt: str,
        width: int,
        height: int,
        negative_prompt: Optional[str],
        original_prompt: str,
        style: str,
    ) -> GeneratedImageResult:
        """Generate image using Replicate API (SDXL or Flux)."""
        # Use Replicate's SDXL model
        model_url = "https://api.replicate.com/v1/predictions"
        
        payload = {
            "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",  # SDXL
            "input": {
                "prompt": prompt,
                "width": min(width, 1024),  # SDXL max
                "height": min(height, 1024),
                "num_outputs": 1,
                "scheduler": "K_EULER",
                "num_inference_steps": 50,
                "guidance_scale": 7.5,
            }
        }
        
        if negative_prompt:
            payload["input"]["negative_prompt"] = negative_prompt
        
        headers = {
            "Authorization": f"Token {self.replicate_api_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Generating image with Replicate: {prompt[:100]}...")
        
        # Start prediction
        response = await self.client.post(model_url, headers=headers, json=payload)
        
        if response.status_code not in (200, 201):
            error_msg = f"Replicate API error {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            return GeneratedImageResult(
                success=False,
                asset_id=asset_id,
                width=width,
                height=height,
                prompt=original_prompt,
                style=style,
                error=error_msg,
                backend_used="replicate"
            )
        
        prediction = response.json()
        prediction_id = prediction.get("id")
        
        # Poll for completion
        get_url = f"{model_url}/{prediction_id}"
        for _ in range(60):  # Max 60 seconds
            await asyncio.sleep(1)
            status_response = await self.client.get(get_url, headers=headers)
            status_data = status_response.json()
            
            if status_data.get("status") == "succeeded":
                output = status_data.get("output", [])
                if output:
                    image_url = output[0]
                    
                    # Download image
                    img_response = await self.client.get(image_url)
                    if img_response.status_code == 200:
                        filename = f"{asset_id}.png"
                        filepath = os.path.join(self.output_dir, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(img_response.content)
                        
                        url = f"/outputs/generated_images/{filename}"
                        
                        logger.info(f"Replicate image generated: {filepath}")
                        
                        return GeneratedImageResult(
                            success=True,
                            asset_id=asset_id,
                            url=url,
                            filepath=filepath,
                            width=width,
                            height=height,
                            prompt=original_prompt,
                            style=style,
                            backend_used="replicate"
                        )
                break
            elif status_data.get("status") == "failed":
                error_msg = status_data.get("error", "Unknown error")
                return GeneratedImageResult(
                    success=False,
                    asset_id=asset_id,
                    width=width,
                    height=height,
                    prompt=original_prompt,
                    style=style,
                    error=f"Replicate prediction failed: {error_msg}",
                    backend_used="replicate"
                )
        
        return GeneratedImageResult(
            success=False,
            asset_id=asset_id,
            width=width,
            height=height,
            prompt=original_prompt,
            style=style,
            error="Replicate prediction timed out",
            backend_used="replicate"
        )
    
    async def _generate_mock_image(
        self,
        asset_id: str,
        prompt: str,
        style: str,
        width: int,
        height: int,
    ) -> GeneratedImageResult:
        """Generate a mock/placeholder image for testing."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a gradient background based on style
            img = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(img)
            
            # Style-based colors
            if style == "photorealistic":
                color1, color2 = (41, 128, 185), (52, 152, 219)  # Blue gradient
            elif style == "artistic":
                color1, color2 = (142, 68, 173), (155, 89, 182)  # Purple gradient
            else:  # minimal
                color1, color2 = (236, 240, 241), (189, 195, 199)  # Gray gradient
            
            # Draw gradient
            for y in range(height):
                r = int(color1[0] + (color2[0] - color1[0]) * y / height)
                g = int(color1[1] + (color2[1] - color1[1]) * y / height)
                b = int(color1[2] + (color2[2] - color1[2]) * y / height)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Add text overlay
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            except:
                font = ImageFont.load_default()
            
            # Wrap prompt text
            max_chars = 40
            wrapped_prompt = prompt[:max_chars] + "..." if len(prompt) > max_chars else prompt
            
            text_lines = [
                "🎨 Mock Generated Image",
                f"Style: {style}",
                f"Size: {width}x{height}",
                f"Prompt: {wrapped_prompt}",
            ]
            
            y_offset = height // 2 - 60
            for line in text_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
                y_offset += 40
            
            # Save image
            filename = f"{asset_id}.png"
            filepath = os.path.join(self.output_dir, filename)
            img.save(filepath, "PNG")
            
            url = f"/outputs/generated_images/{filename}"
            
            logger.info(f"Mock image generated: {filepath}")
            
            return GeneratedImageResult(
                success=True,
                asset_id=asset_id,
                url=url,
                filepath=filepath,
                width=width,
                height=height,
                prompt=prompt,
                style=style,
                backend_used="mock"
            )
            
        except ImportError:
            # PIL not available, return a placeholder URL
            logger.warning("PIL not available, returning placeholder URL")
            
            # Use placehold.co for a placeholder
            placeholder_url = f"https://placehold.co/{width}x{height}/2980b9/ffffff?text=Generated+Image"
            
            return GeneratedImageResult(
                success=True,
                asset_id=asset_id,
                url=placeholder_url,
                width=width,
                height=height,
                prompt=prompt,
                style=style,
                backend_used="placeholder"
            )
    
    def _get_aspect_ratio(self, width: int, height: int) -> str:
        """Calculate aspect ratio string for Segmind API."""
        ratio = width / height
        
        if abs(ratio - 1.0) < 0.1:
            return "1:1"
        elif abs(ratio - 16/9) < 0.1:
            return "16:9"
        elif abs(ratio - 9/16) < 0.1:
            return "9:16"
        elif abs(ratio - 4/3) < 0.1:
            return "4:3"
        elif abs(ratio - 3/4) < 0.1:
            return "3:4"
        elif abs(ratio - 21/9) < 0.1:
            return "21:9"
        else:
            # Default to closest standard ratio
            if ratio > 1:
                return "16:9" if ratio > 1.5 else "4:3"
            else:
                return "9:16" if ratio < 0.67 else "3:4"


# Import asyncio for Replicate polling
import asyncio
