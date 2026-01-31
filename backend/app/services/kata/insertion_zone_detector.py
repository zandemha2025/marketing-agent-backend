"""
Insertion Zone Detector - Identifies valid product placement areas in video frames.

Based on the XAI Hackathon winner "Halftime" approach, this module:
- Detects valid placement zones (hands, surfaces, walls, screens)
- Scores zones by visibility and context fit
- Analyzes depth and occlusion
- Provides placement recommendations

Architecture:
Scene Context → Zone Detection → Scoring → Placement Recommendations
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    np = None

from PIL import Image

logger = logging.getLogger(__name__)


class ZoneType(str, Enum):
    """Types of insertion zones."""
    HAND = "hand"                    # Person holding product
    TABLE_SURFACE = "table"          # Table, desk, counter
    SHELF = "shelf"                  # Shelf or ledge
    WALL = "wall"                    # Wall background
    SCREEN = "screen"                # TV, monitor, phone screen
    FLOOR = "floor"                  # Floor/ground
    PROP = "prop"                    # Existing object to place on/near
    FOREGROUND = "foreground"        # Floating in foreground


class PlacementStyle(str, Enum):
    """Style of product placement."""
    NATURAL = "natural"              # As if naturally in scene
    PROMINENT = "prominent"          # Clearly visible but integrated
    SUBTLE = "subtle"                # Background element
    DYNAMIC = "dynamic"              # Moving with action


@dataclass
class InsertionZone:
    """A detected zone suitable for product insertion."""
    zone_type: ZoneType
    bbox: Tuple[int, int, int, int]  # x, y, width, height (pixels)
    normalized_bbox: Tuple[float, float, float, float]  # 0-1 normalized
    
    # Scoring
    visibility_score: float  # 0-1, how visible is this zone
    context_fit_score: float  # 0-1, how well does product fit
    lighting_match_score: float  # 0-1, lighting compatibility
    overall_score: float  # Combined score
    
    # Placement info
    suggested_scale: float  # Recommended product scale
    suggested_rotation: float  # Recommended rotation (degrees)
    depth_layer: str  # foreground, midground, background
    
    # Constraints
    occlusion_risk: float  # 0-1, risk of being blocked
    motion_compensation: Optional[Tuple[float, float]] = None  # For moving scenes
    
    # Metadata
    description: str = ""
    nearby_objects: List[str] = None


@dataclass
class DepthMap:
    """Depth information for a frame."""
    map_data: Any  # numpy array of depth values
    relative_depths: Dict[str, float]  # Zone type -> average depth
    focal_point: Tuple[float, float]  # Where the eye is drawn


@dataclass
class PlacementRecommendation:
    """A complete placement recommendation."""
    zone: InsertionZone
    confidence: float
    style: PlacementStyle
    reasoning: str
    alternative_zones: List[InsertionZone]


class InsertionZoneDetector:
    """
    Detects and scores zones for product placement in video frames.
    
    Uses computer vision techniques combined with scene context to:
    - Identify hands, surfaces, and other valid placement areas
    - Score zones based on visibility and fit
    - Account for depth and occlusion
    - Provide placement recommendations
    
    Usage:
        detector = InsertionZoneDetector()
        zones = detector.detect_zones(image, scene_context)
        recommendation = detector.get_best_placement(zones, product_type="beverage")
    """
    
    def __init__(self):
        self._depth_estimator = None
        self._segmentation_model = None
    
    def _load_models(self):
        """Lazy load CV models if available."""
        if not CV2_AVAILABLE:
            return
        
        # Try to load MiDaS for depth estimation
        try:
            self._depth_estimator = cv2.dnn.readNet(
                "midas_model.onnx"  # Would need actual model file
            )
        except cv2.error as e:
            logger.warning(f"Depth estimation model not available (OpenCV error): {e}")
        except FileNotFoundError as e:
            logger.warning(f"Depth estimation model file not found: {e}")
        except Exception as e:
            logger.warning(f"Failed to load depth estimation model: {type(e).__name__}: {e}")
    
    def detect_surfaces(
        self,
        image: Image.Image,
        scene_context: Optional[Any] = None
    ) -> List[InsertionZone]:
        """
        Detect flat surfaces suitable for product placement.
        
        Args:
            image: PIL Image
            scene_context: Optional scene analysis context
            
        Returns:
            List of surface zones
        """
        if not CV2_AVAILABLE:
            # Fallback to simple heuristics
            return self._detect_surfaces_heuristic(image, scene_context)
        
        # Convert to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        zones = []
        height, width = cv_image.shape[:2]
        
        # Detect horizontal lines (table edges, shelves)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is not None:
            horizontal_lines = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                # Check if roughly horizontal
                if abs(y2 - y1) < abs(x2 - x1) * 0.1:
                    horizontal_lines.append((x1, y1, x2, y2))
            
            # Group nearby lines to find surfaces
            horizontal_lines.sort(key=lambda l: (l[1] + l[3]) / 2)  # Sort by Y
            
            for i, line in enumerate(horizontal_lines[:5]):  # Top 5 surfaces
                x1, y1, x2, y2 = line
                y_avg = int((y1 + y2) / 2)
                
                # Define surface area below the line
                surface_height = int(height * 0.15)  # 15% of image height
                bbox = (
                    max(0, min(x1, x2)),
                    y_avg,
                    min(width, abs(x2 - x1)),
                    min(surface_height, height - y_avg)
                )
                
                normalized = (
                    bbox[0] / width,
                    bbox[1] / height,
                    bbox[2] / width,
                    bbox[3] / height
                )
                
                zone = InsertionZone(
                    zone_type=ZoneType.TABLE_SURFACE,
                    bbox=bbox,
                    normalized_bbox=normalized,
                    visibility_score=0.7,
                    context_fit_score=0.8,
                    lighting_match_score=0.6,
                    overall_score=0.72,
                    suggested_scale=0.15,
                    suggested_rotation=0.0,
                    depth_layer="midground",
                    occlusion_risk=0.2,
                    description=f"Detected surface at y={y_avg}"
                )
                zones.append(zone)
        
        return zones
    
    def _detect_surfaces_heuristic(
        self,
        image: Image.Image,
        scene_context: Optional[Any]
    ) -> List[InsertionZone]:
        """Fallback surface detection using simple heuristics."""
        width, height = image.size
        zones = []
        
        # Assume bottom third of image often contains surfaces
        bottom_zone = InsertionZone(
            zone_type=ZoneType.TABLE_SURFACE,
            bbox=(int(width * 0.2), int(height * 0.7), int(width * 0.6), int(height * 0.25)),
            normalized_bbox=(0.2, 0.7, 0.6, 0.25),
            visibility_score=0.6,
            context_fit_score=0.7,
            lighting_match_score=0.5,
            overall_score=0.62,
            suggested_scale=0.12,
            suggested_rotation=0.0,
            depth_layer="midground",
            occlusion_risk=0.3,
            description="Heuristic bottom surface"
        )
        zones.append(bottom_zone)
        
        return zones
    
    def detect_hands(
        self,
        image: Image.Image,
        scene_context: Optional[Any] = None
    ) -> List[InsertionZone]:
        """
        Detect hands for product holding placement.
        
        Args:
            image: PIL Image
            scene_context: Optional scene analysis context
            
        Returns:
            List of hand zones
        """
        if not CV2_AVAILABLE:
            return []
        
        # This would use a hand detection model like MediaPipe
        # For now, return empty list - would need actual hand detection
        
        # Check scene context for hand mentions
        if scene_context and hasattr(scene_context, 'objects'):
            hands = [
                obj for obj in scene_context.objects
                if 'hand' in obj.label.lower() or obj.is_holding_area
            ]
            
            zones = []
            width, height = image.size
            
            for hand in hands:
                # Estimate hand position from context
                # In real implementation, would use actual bbox
                bbox = (
                    int(width * 0.3),
                    int(height * 0.4),
                    int(width * 0.15),
                    int(height * 0.15)
                )
                
                normalized = (
                    bbox[0] / width,
                    bbox[1] / height,
                    bbox[2] / width,
                    bbox[3] / height
                )
                
                zone = InsertionZone(
                    zone_type=ZoneType.HAND,
                    bbox=bbox,
                    normalized_bbox=normalized,
                    visibility_score=0.9,
                    context_fit_score=0.95,
                    lighting_match_score=0.7,
                    overall_score=0.88,
                    suggested_scale=0.08,
                    suggested_rotation=15.0,
                    depth_layer="foreground",
                    occlusion_risk=0.1,
                    description="Hand holding position"
                )
                zones.append(zone)
            
            return zones
        
        return []
    
    def detect_background_zones(
        self,
        image: Image.Image,
        scene_context: Optional[Any] = None
    ) -> List[InsertionZone]:
        """
        Detect background zones (walls, screens) for subtle placement.
        
        Args:
            image: PIL Image
            scene_context: Optional scene analysis context
            
        Returns:
            List of background zones
        """
        width, height = image.size
        zones = []
        
        # Wall/shelf zones in upper areas
        wall_zone = InsertionZone(
            zone_type=ZoneType.WALL,
            bbox=(int(width * 0.1), int(height * 0.1), int(width * 0.3), int(height * 0.4)),
            normalized_bbox=(0.1, 0.1, 0.3, 0.4),
            visibility_score=0.6,
            context_fit_score=0.5,
            lighting_match_score=0.6,
            overall_score=0.55,
            suggested_scale=0.1,
            suggested_rotation=0.0,
            depth_layer="background",
            occlusion_risk=0.4,
            description="Background wall area"
        )
        zones.append(wall_zone)
        
        # Screen/product display area
        screen_zone = InsertionZone(
            zone_type=ZoneType.SCREEN,
            bbox=(int(width * 0.6), int(height * 0.2), int(width * 0.3), int(height * 0.3)),
            normalized_bbox=(0.6, 0.2, 0.3, 0.3),
            visibility_score=0.7,
            context_fit_score=0.6,
            lighting_match_score=0.5,
            overall_score=0.62,
            suggested_scale=0.12,
            suggested_rotation=0.0,
            depth_layer="midground",
            occlusion_risk=0.3,
            description="Screen/display area"
        )
        zones.append(screen_zone)
        
        return zones
    
    def detect_zones(
        self,
        image: Image.Image,
        scene_context: Optional[Any] = None
    ) -> List[InsertionZone]:
        """
        Detect all valid insertion zones in an image.
        
        Args:
            image: PIL Image
            scene_context: Optional scene analysis context
            
        Returns:
            List of all detected zones sorted by score
        """
        all_zones = []
        
        # Detect different zone types
        all_zones.extend(self.detect_surfaces(image, scene_context))
        all_zones.extend(self.detect_hands(image, scene_context))
        all_zones.extend(self.detect_background_zones(image, scene_context))
        
        # Add floating foreground option
        width, height = image.size
        foreground_zone = InsertionZone(
            zone_type=ZoneType.FOREGROUND,
            bbox=(int(width * 0.4), int(height * 0.3), int(width * 0.2), int(height * 0.2)),
            normalized_bbox=(0.4, 0.3, 0.2, 0.2),
            visibility_score=0.95,
            context_fit_score=0.4,
            lighting_match_score=0.5,
            overall_score=0.65,
            suggested_scale=0.15,
            suggested_rotation=0.0,
            depth_layer="foreground",
            occlusion_risk=0.0,
            description="Floating foreground placement"
        )
        all_zones.append(foreground_zone)
        
        # Sort by overall score
        all_zones.sort(key=lambda z: z.overall_score, reverse=True)
        
        return all_zones
    
    def score_zone_for_product(
        self,
        zone: InsertionZone,
        product_type: str,
        product_size: str = "medium",
        placement_style: PlacementStyle = PlacementStyle.NATURAL
    ) -> float:
        """
        Score a zone for a specific product.
        
        Args:
            zone: The insertion zone to score
            product_type: Type of product (beverage, electronics, etc.)
            product_size: small, medium, large
            placement_style: Desired placement style
            
        Returns:
            Score from 0-1
        """
        score = zone.overall_score
        
        # Adjust based on product type
        product_zone_preferences = {
            "beverage": [ZoneType.HAND, ZoneType.TABLE_SURFACE, ZoneType.PROP],
            "electronics": [ZoneType.TABLE_SURFACE, ZoneType.HAND, ZoneType.SHELF],
            "apparel": [ZoneType.FOREGROUND, ZoneType.PROP, ZoneType.TABLE_SURFACE],
            "food": [ZoneType.TABLE_SURFACE, ZoneType.HAND, ZoneType.PROP],
            "cosmetics": [ZoneType.TABLE_SURFACE, ZoneType.HAND, ZoneType.SHELF],
            "accessory": [ZoneType.HAND, ZoneType.TABLE_SURFACE, ZoneType.PROP],
        }
        
        preferred_zones = product_zone_preferences.get(product_type, [ZoneType.TABLE_SURFACE])
        
        if zone.zone_type in preferred_zones:
            # Boost score for preferred zone types
            preference_boost = 0.15 * (len(preferred_zones) - preferred_zones.index(zone.zone_type))
            score += preference_boost
        else:
            # Penalize non-preferred zones
            score -= 0.1
        
        # Adjust based on placement style
        style_adjustments = {
            PlacementStyle.NATURAL: {
                ZoneType.HAND: 0.1,
                ZoneType.TABLE_SURFACE: 0.05,
                ZoneType.FOREGROUND: -0.1
            },
            PlacementStyle.PROMINENT: {
                ZoneType.FOREGROUND: 0.15,
                ZoneType.HAND: 0.1,
                ZoneType.TABLE_SURFACE: 0.05
            },
            PlacementStyle.SUBTLE: {
                ZoneType.WALL: 0.1,
                ZoneType.SCREEN: 0.05,
                ZoneType.BACKGROUND: 0.05,
                ZoneType.FOREGROUND: -0.2
            },
            PlacementStyle.DYNAMIC: {
                ZoneType.HAND: 0.15,
                ZoneType.PROP: 0.1
            }
        }
        
        adjustments = style_adjustments.get(placement_style, {})
        score += adjustments.get(zone.zone_type, 0)
        
        # Adjust based on size
        size_scale = {
            "small": 0.05,
            "medium": 0.0,
            "large": -0.05
        }
        score += size_scale.get(product_size, 0)
        
        # Penalize high occlusion risk
        score -= zone.occlusion_risk * 0.2
        
        return max(0.0, min(1.0, score))
    
    def get_best_placement(
        self,
        zones: List[InsertionZone],
        product_type: str,
        product_size: str = "medium",
        placement_style: PlacementStyle = PlacementStyle.NATURAL,
        min_score: float = 0.5
    ) -> Optional[PlacementRecommendation]:
        """
        Get the best placement recommendation for a product.
        
        Args:
            zones: List of detected zones
            product_type: Type of product
            product_size: Size category
            placement_style: Desired style
            min_score: Minimum acceptable score
            
        Returns:
            PlacementRecommendation or None if no suitable zone
        """
        if not zones:
            return None
        
        # Score all zones for this product
        scored_zones = []
        for zone in zones:
            score = self.score_zone_for_product(zone, product_type, product_size, placement_style)
            scored_zones.append((zone, score))
        
        # Sort by score
        scored_zones.sort(key=lambda x: x[1], reverse=True)
        
        # Get best zone above minimum score
        best_zone, best_score = scored_zones[0]
        
        if best_score < min_score:
            return None
        
        # Get alternatives (other top zones)
        alternatives = [z for z, s in scored_zones[1:4] if s >= min_score * 0.8]
        
        # Generate reasoning
        reasoning = self._generate_reasoning(best_zone, product_type, placement_style, best_score)
        
        return PlacementRecommendation(
            zone=best_zone,
            confidence=best_score,
            style=placement_style,
            reasoning=reasoning,
            alternative_zones=alternatives
        )
    
    def _generate_reasoning(
        self,
        zone: InsertionZone,
        product_type: str,
        style: PlacementStyle,
        score: float
    ) -> str:
        """Generate human-readable reasoning for placement choice."""
        reasons = []
        
        if zone.zone_type == ZoneType.HAND:
            reasons.append("Hand placement creates natural product interaction")
        elif zone.zone_type == ZoneType.TABLE_SURFACE:
            reasons.append("Table surface provides stable, visible placement")
        elif zone.zone_type == ZoneType.WALL:
            reasons.append("Background placement for subtle brand presence")
        elif zone.zone_type == ZoneType.FOREGROUND:
            reasons.append("Foreground placement ensures high visibility")
        
        if zone.visibility_score > 0.8:
            reasons.append("High visibility zone")
        
        if zone.occlusion_risk < 0.2:
            reasons.append("Low risk of being blocked")
        
        if style == PlacementStyle.NATURAL:
            reasons.append("Natural integration with scene")
        elif style == PlacementStyle.PROMINENT:
            reasons.append("Prominent positioning for brand awareness")
        
        return "; ".join(reasons) if reasons else "Optimal placement based on scene analysis"
    
    def estimate_depth_map(self, image: Image.Image) -> Optional[DepthMap]:
        """
        Estimate depth map for the image.
        
        Args:
            image: PIL Image
            
        Returns:
            DepthMap or None if estimation fails
        """
        if not CV2_AVAILABLE or self._depth_estimator is None:
            return None
        
        try:
            # This would use MiDaS or similar depth estimation
            # Simplified version returns approximate depth based on position
            width, height = image.size
            
            # Create simple depth approximation (lower = closer)
            depth_data = np.zeros((height, width))
            for y in range(height):
                # Things lower in frame tend to be closer
                depth_data[y, :] = 1.0 - (y / height) * 0.5
            
            relative_depths = {
                "foreground": 0.2,
                "midground": 0.5,
                "background": 0.8
            }
            
            focal_point = (0.5, 0.4)  # Assume center-upper area
            
            return DepthMap(
                map_data=depth_data,
                relative_depths=relative_depths,
                focal_point=focal_point
            )
            
        except Exception as e:
            logger.error(f"Depth estimation failed: {e}")
            return None
    
    def check_occlusion(
        self,
        zone: InsertionZone,
        frame_index: int,
        video_frames: List[Image.Image]
    ) -> float:
        """
        Check occlusion risk across video frames.
        
        Args:
            zone: Insertion zone to check
            frame_index: Current frame index
            video_frames: All video frames
            
        Returns:
            Occlusion risk score 0-1
        """
        if not CV2_AVAILABLE or len(video_frames) < 2:
            return zone.occlusion_risk
        
        # Check neighboring frames for motion/occlusion
        check_range = 5  # Check 5 frames before and after
        start_idx = max(0, frame_index - check_range)
        end_idx = min(len(video_frames), frame_index + check_range + 1)
        
        occlusion_events = 0
        
        for i in range(start_idx, end_idx):
            if i == frame_index:
                continue
            
            # Simple frame difference in zone area
            current = np.array(video_frames[frame_index])
            neighbor = np.array(video_frames[i])
            
            x, y, w, h = zone.bbox
            diff = np.abs(current[y:y+h, x:x+w] - neighbor[y:y+h, x:x+w])
            
            if np.mean(diff) > 30:  # Threshold for significant change
                occlusion_events += 1
        
        risk = occlusion_events / (end_idx - start_idx - 1)
        return max(zone.occlusion_risk, risk)
    
    def get_zone_at_timestamp(
        self,
        zones: List[InsertionZone],
        timestamp: float,
        video_duration: float
    ) -> List[InsertionZone]:
        """
        Get zones relevant to a specific timestamp in video.
        
        Args:
            zones: All detected zones
            timestamp: Current timestamp
            video_duration: Total video duration
            
        Returns:
            Filtered/scored zones for this timestamp
        """
        # Adjust scores based on temporal position
        progress = timestamp / video_duration if video_duration > 0 else 0
        
        adjusted_zones = []
        for zone in zones:
            adjusted_zone = InsertionZone(
                zone_type=zone.zone_type,
                bbox=zone.bbox,
                normalized_bbox=zone.normalized_bbox,
                visibility_score=zone.visibility_score,
                context_fit_score=zone.context_fit_score,
                lighting_match_score=zone.lighting_match_score,
                overall_score=zone.overall_score,
                suggested_scale=zone.suggested_scale,
                suggested_rotation=zone.suggested_rotation,
                depth_layer=zone.depth_layer,
                occlusion_risk=zone.occlusion_risk,
                description=zone.description
            )
            
            # Boost zones in middle of video (typically best engagement)
            if 0.2 <= progress <= 0.8:
                adjusted_zone.overall_score *= 1.1
            
            adjusted_zones.append(adjusted_zone)
        
        return sorted(adjusted_zones, key=lambda z: z.overall_score, reverse=True)
