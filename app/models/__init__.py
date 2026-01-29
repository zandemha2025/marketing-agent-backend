"""
Database models for the Marketing Agent v2.
"""
from .base import Base, generate_id
from .user import User, Organization, UserRole, SubscriptionTier
from .knowledge_base import KnowledgeBase, ResearchStatus
from .campaign import Campaign, CampaignPhase, CampaignStatus, CampaignType, PhaseStatus
from .asset import Asset, AssetVersion, AssetComment, AssetType, AssetStatus
from .conversation import Conversation, Message, ConversationScope, MessageRole

__all__ = [
    # Base
    "Base",
    "generate_id",

    # User & Organization
    "User",
    "Organization",
    "UserRole",
    "SubscriptionTier",

    # Knowledge Base
    "KnowledgeBase",
    "ResearchStatus",

    # Campaign
    "Campaign",
    "CampaignPhase",
    "CampaignStatus",
    "CampaignType",
    "PhaseStatus",

    # Asset
    "Asset",
    "AssetVersion",
    "AssetComment",
    "AssetType",
    "AssetStatus",

    # Conversation
    "Conversation",
    "Message",
    "ConversationScope",
    "MessageRole",
]
