"""
Campaign and Phase models.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import date

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON, Integer, Date, Text
from sqlalchemy.orm import relationship

from .base import Base


class CampaignStatus(str, Enum):
    """Campaign lifecycle status."""
    DRAFT = "draft"           # Being planned
    ACTIVE = "active"         # In progress
    PAUSED = "paused"         # Temporarily stopped
    COMPLETED = "completed"   # Finished
    ARCHIVED = "archived"     # Historical


class CampaignType(str, Enum):
    """Types of marketing campaigns."""
    PRODUCT_LAUNCH = "product_launch"
    BRAND_AWARENESS = "brand_awareness"
    LEAD_GENERATION = "lead_generation"
    SEASONAL = "seasonal"
    EVENT_PROMOTION = "event_promotion"
    CONTENT_MARKETING = "content_marketing"
    REBRANDING = "rebranding"
    CUSTOMER_RETENTION = "customer_retention"


class PhaseStatus(str, Enum):
    """Phase completion status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"


class Campaign(Base):
    """
    Marketing Campaign model.

    A campaign consists of:
    - Brief (strategy document)
    - Phases (timeline stages)
    - Assets (deliverables)
    - Conversations (chat history)
    """

    organization_id = Column(
        String(12),
        ForeignKey("organizations.id"),
        nullable=False
    )

    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)  # Campaign goal/objective
    campaign_type = Column(SQLEnum(CampaignType), default=CampaignType.BRAND_AWARENESS, nullable=False)
    status = Column(String(50), default="draft", nullable=False)  # Use string for flexibility

    # Creative concepts (JSONB) - Generated concepts for selection
    creative_concepts = Column(JSON, default=list, nullable=False)
    selected_concept_index = Column(Integer, nullable=True)

    # Campaign config (JSONB) - Stores creation parameters
    config = Column(JSON, default=dict, nullable=False)

    # Timeline
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Brief Data (JSONB) - The strategic document
    # Structure:
    # {
    #     "version": 1,
    #     "executive_summary": "...",
    #     "background": {
    #         "context": "...",
    #         "challenge": "...",
    #         "opportunity": "..."
    #     },
    #     "objectives": [
    #         {
    #             "objective": "Increase brand awareness",
    #             "metric": "Social impressions",
    #             "target": "1M impressions"
    #         }
    #     ],
    #     "target_audience": {
    #         "primary": {...},  # From knowledge base, potentially refined
    #         "secondary": {...}
    #     },
    #     "key_messages": [
    #         {
    #             "message": "...",
    #             "supporting_points": ["...", "..."]
    #         }
    #     ],
    #     "creative_territories": [
    #         {
    #             "name": "Territory A",
    #             "concept": "...",
    #             "tone": "...",
    #             "visual_direction": "...",
    #             "sample_headlines": ["...", "..."]
    #         }
    #     ],
    #     "channels": [
    #         {
    #             "channel": "LinkedIn",
    #             "role": "Primary awareness driver",
    #             "content_types": ["posts", "ads"],
    #             "frequency": "3x/week"
    #         }
    #     ],
    #     "budget": {
    #         "total": 50000,
    #         "breakdown": {...}
    #     },
    #     "timeline": {
    #         "phases": [...],  # Summary
    #         "key_dates": [...]
    #     },
    #     "success_metrics": [
    #         {
    #             "metric": "...",
    #             "target": "...",
    #             "measurement": "..."
    #         }
    #     ],
    #     "competitive_context": "...",
    #     "risks_and_mitigations": [...]
    # }
    brief_data = Column(JSON, default=dict, nullable=False)
    brief_version = Column(Integer, default=1, nullable=False)

    # Strategy Data (JSONB) - AI's strategic thinking
    # Structure:
    # {
    #     "rationale": "...",
    #     "approach": "...",
    #     "differentiators": [...],
    #     "selected_territory": {...},
    #     "content_strategy": {...}
    # }
    strategy_data = Column(JSON, default=dict, nullable=False)

    # Creator (nullable until auth is implemented)
    created_by = Column(String(12), ForeignKey("users.id"), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="campaigns")
    created_by_user = relationship(
        "User",
        back_populates="created_campaigns",
        foreign_keys=[created_by]
    )
    phases = relationship(
        "CampaignPhase",
        back_populates="campaign",
        order_by="CampaignPhase.order_index"
    )
    assets = relationship("Asset", back_populates="campaign")
    conversations = relationship("Conversation", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign {self.name} ({self.status.value})>"

    @property
    def progress(self) -> float:
        """Calculate overall campaign progress."""
        if not self.phases:
            return 0.0

        completed = sum(1 for p in self.phases if p.status == PhaseStatus.COMPLETED)
        return completed / len(self.phases)

    @property
    def current_phase(self) -> Optional["CampaignPhase"]:
        """Get the current active phase."""
        for phase in self.phases:
            if phase.status == PhaseStatus.IN_PROGRESS:
                return phase
        return None

    def get_brief_summary(self) -> Dict[str, Any]:
        """Get a summarized version of the brief for chat display."""
        brief = self.brief_data
        return {
            "name": self.name,
            "type": self.campaign_type.value,
            "summary": brief.get("executive_summary", ""),
            "objectives": [o["objective"] for o in brief.get("objectives", [])],
            "channels": [c["channel"] for c in brief.get("channels", [])],
            "timeline": f"{self.start_date} - {self.end_date}" if self.start_date else "TBD",
            "phases_count": len(self.phases),
            "assets_count": len(self.assets),
        }


class CampaignPhase(Base):
    """
    Campaign Phase - a stage in the campaign timeline.

    Examples: Teaser, Launch, Sustain, Retarget
    """

    __tablename__ = "campaign_phases"

    campaign_id = Column(
        String(12),
        ForeignKey("campaigns.id"),
        nullable=False
    )

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False)

    status = Column(
        SQLEnum(PhaseStatus),
        default=PhaseStatus.NOT_STARTED,
        nullable=False
    )

    # Timeline
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Phase details (JSONB)
    # Structure:
    # {
    #     "objectives": ["Build anticipation", "..."],
    #     "tactics": ["Social teaser posts", "..."],
    #     "deliverables": ["3x teaser posts", "1x email"],
    #     "success_criteria": ["...", "..."]
    # }
    details = Column(JSON, default=dict, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="phases")
    assets = relationship("Asset", back_populates="phase")

    def __repr__(self):
        return f"<Phase {self.name} ({self.status.value})>"

    @property
    def progress(self) -> float:
        """Calculate phase progress based on assets."""
        if not self.assets:
            return 0.0

        from .asset import AssetStatus
        approved = sum(
            1 for a in self.assets
            if a.status in [AssetStatus.APPROVED, AssetStatus.PUBLISHED]
        )
        return approved / len(self.assets)

    @property
    def pending_assets(self) -> int:
        """Count assets needing attention."""
        from .asset import AssetStatus
        return sum(
            1 for a in self.assets
            if a.status in [AssetStatus.DRAFT, AssetStatus.NEEDS_CHANGES]
        )
