"""
TrendMaster - Multi-Source Trend Scanning and Analysis

This module provides:
- TrendScanner: Multi-source trend scanning (NewsAPI, Reddit, etc.)
- TrendAnalyzer: AI-powered trend analysis and recommendations
- TrendItem: Data class for individual trend items
- TrendAnalysis: Data class for trend analysis results
"""

from .trend_scanner import TrendScanner, TrendItem, TrendSource, trend_scanner
from .trend_analyzer import (
    TrendAnalyzer,
    TrendAnalysis,
    # Legacy exports for backward compatibility
    TrendAnalysisLegacy,
    TrendPrediction,
    TrendSourceLegacy,
)

__all__ = [
    # New TrendMaster exports
    'TrendScanner',
    'TrendItem',
    'TrendSource',
    'TrendAnalyzer',
    'TrendAnalysis',
    # Legacy exports for backward compatibility
    'TrendAnalysisLegacy',
    'TrendPrediction',
    'TrendSourceLegacy',
    # Default scanner instance
    'trend_scanner',
]
