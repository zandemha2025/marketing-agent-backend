"""
Scene Analyzer - Find placement zones in video/images.

Uses computer vision to analyze scenes and find:
- Safe placement zones (not on faces, text, etc.)
- Surface detection (tables, desks, hands)
- Depth estimation (foreground vs background)
- Optimal insertion points for products
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class PlacementType(str, Enum):
    """Types of placement zones."""
    HAND_HOLD = "hand_hold"          # Product held in hand
    SURFACE = "surface"              # On a table/desk/surface
    BACKGROUND = "background"        # In the background
    FOREGROUND = "foreground"        # In the foreground
    OVERLAY = "overlay"              # Overlaid on scene


class ZoneQuality(str, Enum):
    """Quality rating for placement zones."""
    EXCELLENT = "excellent"   # Perfect placement opportunity
    GOOD = "good"            # Good placement
    FAIR = "fair"            # Acceptable placement
    POOR = "poor"            # Not recommended


@dataclass
class BoundingBox:
    """Bounding box coordinates."""
    x: int      # Left
    y: int      # Top
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> Dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class PlacementZone:
    """A detected placement zone in a video frame."""
    id: str
    frame_number: int
    timestamp_seconds: float
    bounding_box: BoundingBox
    placement_type: PlacementType
    quality: ZoneQuality
    confidence: float  # 0-1 confidence score

    # Depth information
    depth_value: float = 0.5  # 0=near, 1=far
    is_foreground: bool = True

    # Context
    detected_surface: Optional[str] = None  # table, desk, hand, etc.
    nearby_objects: List[str] = field(default_factory=list)
    avoid_areas: List[BoundingBox] = field(default_factory=list)  # Faces, text, etc.

    # Recommended transformations
    suggested_scale: float = 1.0
    suggested_rotation: float = 0.0
    suggested_opacity: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "timestamp_seconds": self.timestamp_seconds,
            "bounding_box": self.bounding_box.to_dict(),
            "placement_type": self.placement_type.value,
            "quality": self.quality.value,
            "confidence": self.confidence,
            "depth_value": self.depth_value,
            "is_foreground": self.is_foreground,
            "detected_surface": self.detected_surface,
            "nearby_objects": self.nearby_objects,
            "suggested_scale": self.suggested_scale,
            "suggested_rotation": self.suggested_rotation,
        }


@dataclass
class SceneAnalysisResult:
    """Result from analyzing a video for placement zones."""
    video_path: str
    total_frames: int
    fps: float
    duration_seconds: float
    resolution: Tuple[int, int]

    # Detected zones
    placement_zones: List[PlacementZone] = field(default_factory=list)

    # Detected elements to avoid
    face_regions: List[Dict] = field(default_factory=list)
    text_regions: List[Dict] = field(default_factory=list)

    # Scene classification
    scene_type: str = "unknown"  # indoor, outdoor, studio, etc.
    lighting_condition: str = "neutral"  # bright, dim, natural, artificial

    # Best frames for placement
    best_frames: List[int] = field(default_factory=list)


class SceneAnalyzer:
    """
    Analyzes video/images to find optimal placement zones.

    Uses:
    - Object detection (YOLO/similar) for finding objects
    - Face detection to avoid faces
    - Depth estimation for realistic placement
    - Surface detection for natural product placement
    """

    def __init__(
        self,
        replicate_api_key: str = None,
        use_gpu: bool = False,
    ):
        self.replicate_api_key = replicate_api_key
        self.use_gpu = use_gpu

        # Models are loaded lazily
        self._depth_model = None
        self._object_detector = None
        self._face_detector = None

    async def find_placement_zones(
        self,
        video_path: str,
        avoid_faces: bool = True,
        prefer_surfaces: bool = True,
        sample_rate: int = 5,  # Analyze every Nth frame
        max_zones_per_frame: int = 3,
    ) -> List[PlacementZone]:
        """
        Find all valid placement zones in a video.

        Args:
            video_path: Path to video file
            avoid_faces: Whether to avoid face regions
            prefer_surfaces: Prefer surface placements (tables, hands)
            sample_rate: Analyze every Nth frame
            max_zones_per_frame: Maximum zones to return per frame

        Returns:
            List of PlacementZone objects
        """
        logger.info(f"Analyzing video for placement zones: {video_path}")

        # Get video metadata
        metadata = await self._get_video_metadata(video_path)
        total_frames = metadata["total_frames"]
        fps = metadata["fps"]
        resolution = metadata["resolution"]

        zones = []
        zone_counter = 0

        # Sample frames for analysis
        frames_to_analyze = range(0, total_frames, sample_rate)

        for frame_idx in frames_to_analyze:
            timestamp = frame_idx / fps

            # Extract frame
            frame = await self._extract_frame(video_path, frame_idx)

            # Detect faces (to avoid)
            face_boxes = []
            if avoid_faces:
                face_boxes = await self._detect_faces(frame)

            # Detect objects and surfaces
            detections = await self._detect_objects(frame)

            # Estimate depth
            depth_map = await self._estimate_depth(frame)

            # Find valid placement zones
            frame_zones = self._calculate_placement_zones(
                frame=frame,
                frame_idx=frame_idx,
                timestamp=timestamp,
                detections=detections,
                face_boxes=face_boxes,
                depth_map=depth_map,
                prefer_surfaces=prefer_surfaces,
                resolution=resolution,
            )

            # Keep best zones
            frame_zones.sort(key=lambda z: z.confidence, reverse=True)
            for zone in frame_zones[:max_zones_per_frame]:
                zone.id = f"zone_{zone_counter}"
                zone_counter += 1
                zones.append(zone)

        logger.info(f"Found {len(zones)} placement zones across {len(list(frames_to_analyze))} frames")
        return zones

    async def analyze_single_frame(
        self,
        image_path: str,
        avoid_faces: bool = True,
    ) -> List[PlacementZone]:
        """Analyze a single image for placement zones."""
        # Similar to video but for single frame
        frame = await self._load_image(image_path)
        resolution = (frame.shape[1], frame.shape[0]) if hasattr(frame, 'shape') else (1920, 1080)

        face_boxes = []
        if avoid_faces:
            face_boxes = await self._detect_faces(frame)

        detections = await self._detect_objects(frame)
        depth_map = await self._estimate_depth(frame)

        zones = self._calculate_placement_zones(
            frame=frame,
            frame_idx=0,
            timestamp=0.0,
            detections=detections,
            face_boxes=face_boxes,
            depth_map=depth_map,
            prefer_surfaces=True,
            resolution=resolution,
        )

        return zones

    async def find_hand_regions(self, video_path: str) -> List[Dict]:
        """
        Find hand regions in video - useful for "holding product" scenarios.

        Returns list of frames where hands are visible and suitable for product.
        """
        logger.info(f"Finding hand regions in: {video_path}")

        metadata = await self._get_video_metadata(video_path)
        hand_regions = []

        for frame_idx in range(0, metadata["total_frames"], 10):
            frame = await self._extract_frame(video_path, frame_idx)
            hands = await self._detect_hands(frame)

            for hand in hands:
                hand_regions.append({
                    "frame": frame_idx,
                    "timestamp": frame_idx / metadata["fps"],
                    "bounding_box": hand["box"],
                    "hand_type": hand.get("type", "unknown"),  # left, right
                    "confidence": hand["confidence"],
                })

        return hand_regions

    def _calculate_placement_zones(
        self,
        frame,
        frame_idx: int,
        timestamp: float,
        detections: List[Dict],
        face_boxes: List[BoundingBox],
        depth_map,
        prefer_surfaces: bool,
        resolution: Tuple[int, int],
    ) -> List[PlacementZone]:
        """Calculate valid placement zones from detections."""
        zones = []
        width, height = resolution

        # Look for surface detections (tables, desks, etc.)
        surface_labels = ["table", "desk", "counter", "shelf", "floor"]
        hand_labels = ["hand", "person"]

        for det in detections:
            label = det.get("label", "").lower()
            box = det.get("box", {})
            confidence = det.get("confidence", 0.5)

            bbox = BoundingBox(
                x=int(box.get("x", 0)),
                y=int(box.get("y", 0)),
                width=int(box.get("width", 100)),
                height=int(box.get("height", 100)),
            )

            # Skip if overlaps with face
            if self._overlaps_with_any(bbox, face_boxes):
                continue

            # Determine placement type
            if label in surface_labels:
                placement_type = PlacementType.SURFACE
                quality = ZoneQuality.EXCELLENT if prefer_surfaces else ZoneQuality.GOOD
            elif "hand" in label:
                placement_type = PlacementType.HAND_HOLD
                quality = ZoneQuality.EXCELLENT
            else:
                placement_type = PlacementType.FOREGROUND
                quality = ZoneQuality.FAIR

            # Get depth at zone center
            depth_value = self._get_depth_at_point(depth_map, bbox.center)

            zone = PlacementZone(
                id="",  # Set later
                frame_number=frame_idx,
                timestamp_seconds=timestamp,
                bounding_box=bbox,
                placement_type=placement_type,
                quality=quality,
                confidence=confidence,
                depth_value=depth_value,
                is_foreground=depth_value < 0.5,
                detected_surface=label if label in surface_labels else None,
                avoid_areas=face_boxes,
                suggested_scale=self._calculate_suggested_scale(bbox, resolution),
            )
            zones.append(zone)

        # If no zones found, create a default center zone
        if not zones:
            center_box = BoundingBox(
                x=width // 4,
                y=height // 4,
                width=width // 2,
                height=height // 2,
            )
            zones.append(PlacementZone(
                id="",
                frame_number=frame_idx,
                timestamp_seconds=timestamp,
                bounding_box=center_box,
                placement_type=PlacementType.FOREGROUND,
                quality=ZoneQuality.FAIR,
                confidence=0.5,
                avoid_areas=face_boxes,
            ))

        return zones

    def _overlaps_with_any(
        self,
        box: BoundingBox,
        others: List[BoundingBox],
        threshold: float = 0.3,
    ) -> bool:
        """Check if box overlaps significantly with any other box."""
        for other in others:
            overlap = self._calculate_iou(box, other)
            if overlap > threshold:
                return True
        return False

    def _calculate_iou(self, box1: BoundingBox, box2: BoundingBox) -> float:
        """Calculate Intersection over Union."""
        x1 = max(box1.x, box2.x)
        y1 = max(box1.y, box2.y)
        x2 = min(box1.x + box1.width, box2.x + box2.width)
        y2 = min(box1.y + box1.height, box2.y + box2.height)

        if x2 < x1 or y2 < y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = box1.area + box2.area - intersection

        return intersection / union if union > 0 else 0.0

    def _get_depth_at_point(self, depth_map, point: Tuple[int, int]) -> float:
        """Get depth value at a point (0=near, 1=far)."""
        if depth_map is None:
            return 0.5

        try:
            x, y = point
            return float(depth_map[y, x]) / 255.0
        except:
            return 0.5

    def _calculate_suggested_scale(
        self,
        box: BoundingBox,
        resolution: Tuple[int, int],
    ) -> float:
        """Calculate suggested scale for product placement."""
        width, height = resolution
        frame_area = width * height
        box_ratio = box.area / frame_area

        # Products should typically be 5-20% of frame
        if box_ratio < 0.05:
            return 1.5  # Scale up
        elif box_ratio > 0.3:
            return 0.5  # Scale down
        return 1.0

    async def _get_video_metadata(self, video_path: str) -> Dict:
        """Get video metadata."""
        # In production, use cv2 or ffprobe
        # For now, return reasonable defaults
        return {
            "total_frames": 300,
            "fps": 30.0,
            "resolution": (1920, 1080),
            "duration": 10.0,
        }

    async def _extract_frame(self, video_path: str, frame_idx: int):
        """Extract a single frame from video."""
        # In production, use cv2.VideoCapture
        # For now, return placeholder
        return None

    async def _load_image(self, image_path: str):
        """Load an image file."""
        # In production, use cv2.imread or PIL
        return None

    async def _detect_faces(self, frame) -> List[BoundingBox]:
        """Detect faces in frame."""
        # In production, use face detection model
        # For now, return empty list
        return []

    async def _detect_hands(self, frame) -> List[Dict]:
        """Detect hands in frame."""
        # In production, use MediaPipe or similar
        return []

    async def _detect_objects(self, frame) -> List[Dict]:
        """Detect objects in frame."""
        # In production, use YOLO or similar
        # For now, return sample detections
        return [
            {"label": "table", "confidence": 0.9, "box": {"x": 100, "y": 400, "width": 400, "height": 200}},
        ]

    async def _estimate_depth(self, frame):
        """Estimate depth map for frame."""
        # In production, use MiDaS or similar depth estimation
        # For now, return None (will use default depth)
        return None
