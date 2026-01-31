"""
Database models for the Marketing Agent v2.
"""
from .base import Base, generate_id
from .user import User, Organization, UserRole, SubscriptionTier, IdentityProvider
from .knowledge_base import KnowledgeBase, ResearchStatus
from .campaign import Campaign, CampaignPhase, CampaignStatus, CampaignType, PhaseStatus
from .asset import Asset, AssetVersion, AssetComment, AssetType, AssetStatus
from .conversation import Conversation, Message, ConversationScope, MessageRole
from .task import Task
from .deliverable import Deliverable
from .trend import Trend
from .scheduled_post import ScheduledPost
from .image_edit_session import ImageEditSession, ImageEditHistory
from .audit_log import AuditLog, AuditAction, ResourceType
from .consent import Consent, ConsentType, ConsentStatus
from .data_subject_request import (
    DataSubjectRequest, DSRType, DSRStatus, DSRPriority,
    VerificationMethod
)
from .customer import Customer
from .customer_identity import CustomerIdentity, IdentityType, IdentitySource
from .customer_event import CustomerEvent, EventType, EventSource
from .customer_segment import CustomerSegment, SegmentType, SegmentStatus
from .segment_membership import SegmentMembership

# Attribution & Analytics Models
from .conversion_event import ConversionEvent, ConversionType, ConversionStatus
from .attribution_touchpoint import AttributionTouchpoint, TouchpointType, TouchpointStatus
from .attribution import Attribution, AttributionModelType, AttributionStatus, AttributionModelConfig
from .marketing_mix_model import (
    MarketingMixModel, MMMChannel, MMMChannelDaily, MMMPrediction,
    MMMBudgetOptimizer, MMMModelStatus, MMMChannelType
)

# Optimization & Experiments
from .experiment import Experiment, ExperimentType, ExperimentStatus
from .experiment_variant import ExperimentVariant
from .experiment_assignment import ExperimentAssignment
from .experiment_result import ExperimentResult
from .predictive_model import PredictiveModel, PredictiveModelType, PredictiveModelStatus

__all__ = [
    # Base
    "Base",
    "generate_id",

    # User & Organization
    "User",
    "Organization",
    "UserRole",
    "SubscriptionTier",
    "IdentityProvider",

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
    
    # Task
    "Task",
    
    # Deliverable
    "Deliverable",
    
    # Trend
    "Trend",
    
    # Scheduled Post
    "ScheduledPost",
    
    # Image Edit Session
    "ImageEditSession",
    "ImageEditHistory",
    
    # Audit & Compliance
    "AuditLog",
    "AuditAction",
    "ResourceType",
    "Consent",
    "ConsentType",
    "ConsentStatus",
    "DataSubjectRequest",
    "DSRType",
    "DSRStatus",
    "DSRPriority",
    "VerificationMethod",

    # CDP - Customer Data Platform
    "Customer",
    "CustomerIdentity",
    "IdentityType",
    "IdentitySource",
    "CustomerEvent",
    "EventType",
    "EventSource",
    "CustomerSegment",
    "SegmentType",
    "SegmentStatus",
    "SegmentMembership",

    # Attribution & Analytics
    "ConversionEvent",
    "ConversionType",
    "ConversionStatus",
    "AttributionTouchpoint",
    "TouchpointType",
    "TouchpointStatus",
    "Attribution",
    "AttributionModelType",
    "AttributionStatus",
    "AttributionModelConfig",
    "MarketingMixModel",
    "MMMChannel",
    "MMMChannelDaily",
    "MMMPrediction",
    "MMMBudgetOptimizer",
    "MMMModelStatus",
    "MMMChannelType",

    # Optimization & Experiments
    "Experiment",
    "ExperimentType",
    "ExperimentStatus",
    "ExperimentVariant",
    "ExperimentAssignment",
    "ExperimentResult",
    "PredictiveModel",
    "PredictiveModelType",
    "PredictiveModelStatus",
]
