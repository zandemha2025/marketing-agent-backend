"""
KATA ENGINE - Contextual AI Compositing & Synthetic Influencer Platform

The Kata Engine provides:
1. Scene Analysis - Find placement zones in video/images
2. Compositing - Naturally place products into content
3. Synthetic Influencers - Generate AI humans with your products
4. Voice Generation - ElevenLabs integration for speaking
5. UGC Styling - Make content look organic/authentic

This is the differentiator - NO ONE else can do this.
"""

from .orchestrator import KataOrchestrator, KataJob, KataResult
from .analysis.scene_analyzer import SceneAnalyzer, PlacementZone
from .compositing.compositor import Compositor, CompositeResult
from .synthetic.influencer_generator import InfluencerGenerator, SyntheticInfluencer
from .voice.voice_generator import VoiceGenerator

__all__ = [
    "KataOrchestrator",
    "KataJob",
    "KataResult",
    "SceneAnalyzer",
    "PlacementZone",
    "Compositor",
    "CompositeResult",
    "InfluencerGenerator",
    "SyntheticInfluencer",
    "VoiceGenerator",
]
