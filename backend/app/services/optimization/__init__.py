"""
Optimization services for the Marketing Agent Platform.

This module provides self-optimizing campaign capabilities including:
- A/B testing framework with statistical significance
- Multi-armed bandit algorithms for continuous optimization
- Campaign budget and creative optimization
- Predictive performance modeling
"""

from .ab_testing import ABTestingEngine
from .bandit_engine import BanditEngine
from .campaign_optimizer import CampaignOptimizer
from .predictive_modeling import PredictivePerformanceModel

__all__ = [
    "ABTestingEngine",
    "BanditEngine", 
    "CampaignOptimizer",
    "PredictivePerformanceModel",
]