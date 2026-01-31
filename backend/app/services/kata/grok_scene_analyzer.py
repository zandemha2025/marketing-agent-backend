"""
Grok Scene Analyzer - AI-powered video scene analysis using xAI API.

Based on the XAI Hackathon winner "Halftime" approach, this module:
- Analyzes video frames for narrative context
- Detects lighting conditions and mood
- Identifies setting and environment
- Recognizes objects and their relationships
- Provides context for intelligent product placement

Architecture:
Video Input → Frame Extraction → Grok Analysis → Scene Context
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import json
import base64
import asyncio

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

import httpx
from PIL import Image
import io

logger = logging.getLogger(__name__)

XAI_API_BASE = "https://api.x.ai/v1"


@dataclass
class LightingInfo:
    """Lighting conditions in the scene."""
    type: str  # natural, artificial, mixed, low_light, bright
    direction: str  # front, back, side, top, diffused
    intensity: float  # 0.0 to 1.0
    color_temperature: str  # warm, cool, neutral
    shadows: str  # hard, soft, minimal
    key_light_position: Optional[Tuple[float, float]] = None  # Normalized x, y


@dataclass
class SceneObject:
    """An object detected in the scene."""
    label: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # x, y, width, height (normalized)
    category: str  # person, furniture, prop, surface, background
    depth_estimate: float = 0.5  # Relative depth 0-1
    is_holding_area: bool = False  # Could hold a product


@dataclass
class SceneContext:
    """Complete scene analysis context."""
    # Narrative
    scene_type: str  # indoor, outdoor, studio, event, casual
    activity: str  # What is happening in the scene
    mood: str  # energetic, calm, professional, casual, luxury
    
    # Setting
    location_description: str
    background_elements: List[str]
    dominant_colors: List[str]
    
    # Lighting
    lighting: LightingInfo
    
    # Objects
    objects: List[SceneObject]
    people_count: int
    
    # Composition (required field - must come before optional fields)
    composition_style: str  # centered, rule_of_thirds, dynamic, static
    
    # Optional fields with defaults
    main_subject: Optional[str] = None
    depth_layers: int = 1  # Foreground, midground, background count
    
    # Temporal (for video)
    timestamp: float = 0.0  # Seconds into video
    motion_level: str = "static"  # static, slow, medium, fast


@dataclass
class VideoAnalysis:
    """Complete video analysis result."""
    video_path: str
    duration_seconds: float
    fps: float
    resolution: Tuple[int, int]
    
    # Scene analysis at keyframes
    keyframe_scenes: List[SceneContext]
    
    # Overall narrative
    overall_mood: str
    narrative_arc: List[str]  # Beginning, middle, end descriptions
    
    # Best frames for insertion
    recommended_insertion_frames: List[int]
    
    # Technical
    dominant_color_palette: List[str]
    average_lighting: LightingInfo


class GrokSceneAnalyzer:
    """
    AI-powered scene analyzer using xAI's Grok API.
    
    Analyzes video frames to extract:
    - Narrative context and mood
    - Lighting conditions
    - Object detection and relationships
    - Setting and environment
    - Composition analysis
    
    Usage:
        analyzer = GrokSceneAnalyzer(api_key="your-xai-key")
        analysis = await analyzer.analyze_video("path/to/video.mp4")
    """
    
    def __init__(self, api_key: str, model: str = "grok-2-vision-latest"):
        self.api_key = api_key
        self.model = model
        self._http_client = httpx.AsyncClient(
            base_url=XAI_API_BASE,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=120.0
        )
    
    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL Image to base64 string."""
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode()
    
    async def _call_grok_vision(
        self,
        image_base64: str,
        prompt: str,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Call xAI Grok Vision API for image analysis.
        
        Args:
            image_base64: Base64-encoded image
            prompt: Analysis prompt
            max_tokens: Maximum response tokens
            
        Returns:
            Parsed JSON response
        """
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens
        }
        
        try:
            response = await self._http_client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract content from response
            content = data["choices"][0]["message"]["content"]
            
            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, wrap in structure
                return {"description": content, "raw": True}
                
        except Exception as e:
            logger.error(f"Grok API error: {e}")
            raise
    
    async def analyze_frame(
        self,
        image: Image.Image,
        timestamp: float = 0.0
    ) -> SceneContext:
        """
        Analyze a single video frame.
        
        Args:
            image: PIL Image of the frame
            timestamp: Timestamp in video (seconds)
            
        Returns:
            SceneContext with complete analysis
        """
        # Encode image
        image_base64 = self._encode_image(image)
        
        # Comprehensive analysis prompt
        prompt = """Analyze this video frame in detail. Provide a JSON response with:

{
    "scene_type": "indoor/outdoor/studio/event/casual",
    "activity": "what is happening in this scene",
    "mood": "energetic/calm/professional/casual/luxury/intimate",
    "location_description": "detailed description of the setting",
    "background_elements": ["list", "of", "key", "background", "elements"],
    "dominant_colors": ["#hexcolor1", "#hexcolor2", "#hexcolor3"],
    "lighting": {
        "type": "natural/artificial/mixed/low_light/bright",
        "direction": "front/back/side/top/diffused",
        "intensity": 0.7,
        "color_temperature": "warm/cool/neutral",
        "shadows": "hard/soft/minimal"
    },
    "objects": [
        {
            "label": "object name",
            "category": "person/furniture/prop/surface/background",
            "confidence": 0.95,
            "is_holding_area": true/false,
            "depth": "foreground/midground/background"
        }
    ],
    "people_count": 2,
    "main_subject": "description of main focus",
    "composition_style": "centered/rule_of_thirds/dynamic/static",
    "motion_level": "static/slow/medium/fast"
}

Focus on details relevant for product placement. Identify surfaces where products could naturally appear (tables, hands, shelves, etc.)."""
        
        try:
            result = await self._call_grok_vision(image_base64, prompt)
            
            # Parse lighting
            lighting_data = result.get("lighting", {})
            lighting = LightingInfo(
                type=lighting_data.get("type", "natural"),
                direction=lighting_data.get("direction", "front"),
                intensity=lighting_data.get("intensity", 0.5),
                color_temperature=lighting_data.get("color_temperature", "neutral"),
                shadows=lighting_data.get("shadows", "soft")
            )
            
            # Parse objects
            objects = []
            for obj_data in result.get("objects", []):
                depth_map = {"foreground": 0.2, "midground": 0.5, "background": 0.8}
                obj = SceneObject(
                    label=obj_data.get("label", "unknown"),
                    confidence=obj_data.get("confidence", 0.5),
                    bbox=(0, 0, 0, 0),  # Would need object detection model for bbox
                    category=obj_data.get("category", "prop"),
                    depth_estimate=depth_map.get(obj_data.get("depth", "midground"), 0.5),
                    is_holding_area=obj_data.get("is_holding_area", False)
                )
                objects.append(obj)
            
            return SceneContext(
                scene_type=result.get("scene_type", "indoor"),
                activity=result.get("activity", "unknown activity"),
                mood=result.get("mood", "neutral"),
                location_description=result.get("location_description", ""),
                background_elements=result.get("background_elements", []),
                dominant_colors=result.get("dominant_colors", []),
                lighting=lighting,
                objects=objects,
                people_count=result.get("people_count", 0),
                main_subject=result.get("main_subject"),
                composition_style=result.get("composition_style", "centered"),
                motion_level=result.get("motion_level", "static"),
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Frame analysis failed: {e}")
            # Return minimal context on failure
            return SceneContext(
                scene_type="unknown",
                activity="unknown",
                mood="neutral",
                location_description="",
                background_elements=[],
                dominant_colors=[],
                lighting=LightingInfo("natural", "front", 0.5, "neutral", "soft"),
                objects=[],
                people_count=0,
                timestamp=timestamp
            )
    
    def _extract_keyframes(
        self,
        video_path: str,
        num_keyframes: int = 8
    ) -> List[Tuple[Image.Image, float]]:
        """
        Extract keyframes from video for analysis.
        
        Args:
            video_path: Path to video file
            num_keyframes: Number of frames to extract
            
        Returns:
            List of (PIL Image, timestamp) tuples
        """
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV (cv2) is required for video processing")
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # Calculate frame positions
        frame_positions = [
            int((i / (num_keyframes - 1)) * total_frames)
            for i in range(num_keyframes)
        ]
        
        keyframes = []
        for frame_pos in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                timestamp = frame_pos / fps if fps > 0 else 0
                keyframes.append((pil_image, timestamp))
        
        cap.release()
        return keyframes
    
    async def analyze_video(
        self,
        video_path: str,
        num_keyframes: int = 8
    ) -> VideoAnalysis:
        """
        Analyze a complete video.
        
        Args:
            video_path: Path to video file
            num_keyframes: Number of frames to analyze
            
        Returns:
            VideoAnalysis with complete scene information
        """
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV (cv2) is required for video processing. Install with: pip install opencv-python")
        
        # Get video info
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()
        
        logger.info(f"Analyzing video: {video_path} ({duration:.1f}s, {width}x{height})")
        
        # Extract keyframes
        keyframes = self._extract_keyframes(video_path, num_keyframes)
        
        # Analyze each keyframe
        scene_contexts = []
        for image, timestamp in keyframes:
            context = await self.analyze_frame(image, timestamp)
            scene_contexts.append(context)
        
        # Determine overall mood
        moods = [s.mood for s in scene_contexts]
        overall_mood = max(set(moods), key=moods.count) if moods else "neutral"
        
        # Build narrative arc
        narrative_arc = [
            scene_contexts[0].activity if scene_contexts else "",
            scene_contexts[len(scene_contexts)//2].activity if len(scene_contexts) > 2 else "",
            scene_contexts[-1].activity if scene_contexts else ""
        ]
        
        # Find recommended insertion frames
        recommended_frames = self._find_insertion_frames(scene_contexts)
        
        # Aggregate color palette
        all_colors = []
        for scene in scene_contexts:
            all_colors.extend(scene.dominant_colors)
        dominant_palette = list(set(all_colors))[:5]  # Top 5 unique colors
        
        # Average lighting
        avg_intensity = sum(s.lighting.intensity for s in scene_contexts) / len(scene_contexts) if scene_contexts else 0.5
        lighting_types = [s.lighting.type for s in scene_contexts]
        dominant_lighting = max(set(lighting_types), key=lighting_types.count) if lighting_types else "natural"
        
        average_lighting = LightingInfo(
            type=dominant_lighting,
            direction="diffused",  # Average
            intensity=avg_intensity,
            color_temperature="neutral",
            shadows="soft"
        )
        
        return VideoAnalysis(
            video_path=video_path,
            duration_seconds=duration,
            fps=fps,
            resolution=(width, height),
            keyframe_scenes=scene_contexts,
            overall_mood=overall_mood,
            narrative_arc=narrative_arc,
            recommended_insertion_frames=recommended_frames,
            dominant_color_palette=dominant_palette,
            average_lighting=average_lighting
        )
    
    def _find_insertion_frames(self, scenes: List[SceneContext]) -> List[int]:
        """
        Find the best frames for product insertion.
        
        Args:
            scenes: List of scene contexts
            
        Returns:
            List of recommended frame indices
        """
        recommendations = []
        
        for i, scene in enumerate(scenes):
            score = 0
            
            # Prefer scenes with holding areas
            holding_areas = sum(1 for obj in scene.objects if obj.is_holding_area)
            score += holding_areas * 2
            
            # Prefer stable lighting
            if scene.lighting.shadows == "soft":
                score += 1
            
            # Prefer medium intensity lighting
            if 0.4 <= scene.lighting.intensity <= 0.8:
                score += 1
            
            # Prefer scenes with surfaces
            surfaces = sum(1 for obj in scene.objects if obj.category == "surface")
            score += surfaces
            
            # Penalize fast motion
            if scene.motion_level == "static":
                score += 2
            elif scene.motion_level == "slow":
                score += 1
            
            if score >= 3:
                recommendations.append(i)
        
        # Always include at least one frame
        if not recommendations and scenes:
            recommendations = [len(scenes) // 2]
        
        return recommendations
    
    async def analyze_frame_batch(
        self,
        images: List[Image.Image],
        timestamps: Optional[List[float]] = None
    ) -> List[SceneContext]:
        """
        Analyze multiple frames in batch.
        
        Args:
            images: List of PIL Images
            timestamps: Optional list of timestamps
            
        Returns:
            List of SceneContext objects
        """
        if timestamps is None:
            timestamps = [0.0] * len(images)
        
        # Process in parallel
        tasks = [
            self.analyze_frame(img, ts)
            for img, ts in zip(images, timestamps)
        ]
        
        return await asyncio.gather(*tasks)
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
