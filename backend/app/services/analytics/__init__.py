"""
Analytics services for the Marketing Agent Platform.

Provides comprehensive analytics capabilities including:
- Attribution Engine for multi-touch attribution
- Marketing Mix Modeling for channel effectiveness
- Analytics Dashboard for reporting and visualization
- Conversion Tracking for funnel analysis
"""

from .attribution_engine import AttributionEngine, AttributionResult
from .marketing_mix_modeling import MarketingMixModelingService
from .analytics_dashboard import AnalyticsDashboardService
from .conversion_tracker import ConversionTracker

__all__ = [
    "AttributionEngine",
    "AttributionResult",
    "MarketingMixModelingService",
    "AnalyticsDashboardService",
    "ConversionTracker",
]
