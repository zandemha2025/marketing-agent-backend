"""
Campaign services - The heart of the marketing agent.

This module orchestrates the complete campaign workflow:
1. Brief Generation - Strategic creative briefs
2. Creative Direction - Concept development
3. Campaign Orchestration - End-to-end execution
"""
from .brief_generator import BriefGenerator, CampaignBrief
from .creative_director import CreativeDirector, CreativeConcept
from .orchestrator import (
    CampaignOrchestrator,
    CampaignResult,
    CampaignProgress,
    CampaignPhase,
    run_campaign
)

__all__ = [
    # Brief Generation
    "BriefGenerator",
    "CampaignBrief",

    # Creative Direction
    "CreativeDirector",
    "CreativeConcept",

    # Orchestration
    "CampaignOrchestrator",
    "CampaignResult",
    "CampaignProgress",
    "CampaignPhase",
    "run_campaign",
]
