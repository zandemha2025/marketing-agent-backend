"""
Customer Data Platform (CDP) services.

This module provides enterprise-grade customer data management including:
- Identity resolution and profile merging
- Real-time event processing
- Profile enrichment and segmentation
- Client-side tracking SDK
"""

from .identity_resolver import IdentityResolver, MatchResult, MatchConfidence
from .event_processor import EventProcessor, ValidationResult
from .event_ingestion import EventIngestionService
from .profile_enricher import ProfileEnricher
from .client_sdk import ClientSDK

__all__ = [
    "IdentityResolver",
    "MatchResult",
    "MatchConfidence",
    "EventProcessor",
    "ValidationResult",
    "EventIngestionService",
    "ProfileEnricher",
    "ClientSDK",
]