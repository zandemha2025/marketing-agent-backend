"""
Knowledge Base model - stores all client intelligence.
"""
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON, Float
from sqlalchemy.orm import relationship

from .base import Base


class ResearchStatus(str, Enum):
    """Status of knowledge base research."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"  # Needs refresh


class KnowledgeBase(Base):
    """
    Knowledge Base - the heart of client intelligence.

    Stores everything we know about a client:
    - Brand identity (visual, voice, values)
    - Market intelligence (competitors, trends)
    - Target audiences
    - Products/services
    - Historical context
    """

    __tablename__ = "knowledge_bases"

    organization_id = Column(
        String(12),
        ForeignKey("organizations.id"),
        unique=True,
        nullable=False
    )

    # Research status
    research_status = Column(
        SQLEnum(ResearchStatus),
        default=ResearchStatus.PENDING,
        nullable=False
    )
    research_progress = Column(Float, default=0.0, nullable=False)
    research_stage = Column(String(100), nullable=True)
    research_error = Column(String(500), nullable=True)

    # Brand Data (JSONB)
    # Structure:
    # {
    #     "name": "Acme Corp",
    #     "domain": "acme.com",
    #     "tagline": "Building the future",
    #     "description": "...",
    #     "visual_identity": {
    #         "primary_color": "#FF5733",
    #         "secondary_colors": ["#333", "#FFF"],
    #         "fonts": {
    #             "heading": "Inter",
    #             "body": "Open Sans"
    #         },
    #         "logo_url": "https://...",
    #         "image_style": "modern, minimal, tech-forward"
    #     },
    #     "voice": {
    #         "tone": ["professional", "innovative", "approachable"],
    #         "personality": "We're the friend who happens to be an expert",
    #         "vocabulary": ["empower", "seamless", "future-proof"],
    #         "avoid": ["cheap", "basic"],
    #         "sample_phrases": [
    #             "Let's build something amazing",
    #             "Your success is our mission"
    #         ]
    #     },
    #     "values": ["innovation", "customer-first", "transparency"],
    #     "mission": "To democratize access to..."
    # }
    brand_data = Column(JSON, default=dict, nullable=False)

    # Market Data (JSONB)
    # Structure:
    # {
    #     "competitors": [
    #         {
    #             "name": "Competitor A",
    #             "domain": "competitor-a.com",
    #             "strengths": ["market leader", "brand recognition"],
    #             "weaknesses": ["expensive", "slow innovation"],
    #             "positioning": "Premium enterprise solution",
    #             "key_differentiators": ["..."]
    #         }
    #     ],
    #     "industry": "SaaS / Productivity",
    #     "trends": [
    #         {
    #             "trend": "AI integration",
    #             "relevance": "high",
    #             "opportunity": "Early mover advantage"
    #         }
    #     ],
    #     "market_position": "Challenger in mid-market segment"
    # }
    market_data = Column(JSON, default=dict, nullable=False)

    # Audiences Data (JSONB)
    # Structure:
    # {
    #     "segments": [
    #         {
    #             "name": "Startup Founders",
    #             "size": "primary",
    #             "demographics": {
    #                 "age_range": "25-45",
    #                 "job_titles": ["CEO", "CTO", "Founder"],
    #                 "company_size": "1-50"
    #             },
    #             "psychographics": {
    #                 "values": ["efficiency", "innovation"],
    #                 "challenges": ["limited time", "wearing many hats"],
    #                 "goals": ["scale quickly", "stay competitive"]
    #             },
    #             "pain_points": [
    #                 "Too many tools",
    #                 "Information silos"
    #             ],
    #             "preferred_channels": ["twitter", "linkedin", "producthunt"],
    #             "content_preferences": ["how-to guides", "case studies"]
    #         }
    #     ]
    # }
    audiences_data = Column(JSON, default=dict, nullable=False)

    # Offerings Data (JSONB)
    # Structure:
    # {
    #     "products": [
    #         {
    #             "name": "Pro Plan",
    #             "description": "...",
    #             "features": ["...", "..."],
    #             "pricing": "$29/mo",
    #             "target_segment": "SMB"
    #         }
    #     ],
    #     "services": [
    #         {
    #             "name": "Implementation Support",
    #             "description": "...",
    #             "benefits": ["..."]
    #         }
    #     ],
    #     "key_differentiators": ["...", "..."]
    # }
    offerings_data = Column(JSON, default=dict, nullable=False)

    # Context Data (JSONB)
    # Structure:
    # {
    #     "social_presence": {
    #         "twitter": {"handle": "@acme", "followers": 50000},
    #         "linkedin": {"url": "...", "followers": 10000},
    #         "instagram": null
    #     },
    #     "recent_news": [
    #         {
    #             "title": "Acme raises $10M",
    #             "date": "2024-01-15",
    #             "source": "TechCrunch",
    #             "url": "..."
    #         }
    #     ],
    #     "past_campaigns": [...],
    #     "sentiment": {
    #         "overall": "positive",
    #         "score": 0.75
    #     }
    # }
    context_data = Column(JSON, default=dict, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="knowledge_base")

    def __repr__(self):
        return f"<KnowledgeBase org={self.organization_id} status={self.research_status.value}>"

    # Helper methods for accessing nested data
    @property
    def brand_name(self) -> Optional[str]:
        return self.brand_data.get("name")

    @property
    def brand_colors(self) -> Dict[str, Any]:
        visual = self.brand_data.get("visual_identity", {})
        return {
            "primary": visual.get("primary_color"),
            "secondary": visual.get("secondary_colors", [])
        }

    @property
    def brand_voice(self) -> Dict[str, Any]:
        return self.brand_data.get("voice", {})

    @property
    def competitors(self) -> List[Dict[str, Any]]:
        return self.market_data.get("competitors", [])

    @property
    def audience_segments(self) -> List[Dict[str, Any]]:
        return self.audiences_data.get("segments", [])

    @property
    def products(self) -> List[Dict[str, Any]]:
        return self.offerings_data.get("products", [])

    @property
    def services(self) -> List[Dict[str, Any]]:
        return self.offerings_data.get("services", [])

    def to_presentation_format(self) -> Dict[str, Any]:
        """
        Convert to a format suitable for frontend presentation.
        Used in the onboarding flow to show "Here's what we learned".
        """
        return {
            "brand": {
                "name": self.brand_name,
                "domain": self.brand_data.get("domain"),
                "tagline": self.brand_data.get("tagline"),
                "description": self.brand_data.get("description"),
                "visual_identity": self.brand_data.get("visual_identity", {}),
                "voice": self.brand_voice,
                "values": self.brand_data.get("values", []),
                "mission": self.brand_data.get("mission"),
            },
            "market": {
                "industry": self.market_data.get("industry"),
                "competitors": self.competitors,
                "trends": self.market_data.get("trends", []),
                "position": self.market_data.get("market_position"),
            },
            "audiences": self.audience_segments,
            "offerings": {
                "products": self.products,
                "services": self.services,
                "differentiators": self.offerings_data.get("key_differentiators", []),
            },
            "context": {
                "social": self.context_data.get("social_presence", {}),
                "news": self.context_data.get("recent_news", []),
                "sentiment": self.context_data.get("sentiment"),
            },
            "research_status": self.research_status.value,
        }

    def get_context_for_campaign(self, campaign_type: str) -> Dict[str, Any]:
        """
        Get relevant context for generating a campaign.
        Filters and prioritizes information based on campaign type.
        """
        # This will be used by the AI to have full context
        return {
            "brand": self.brand_data,
            "voice": self.brand_voice,
            "audiences": self.audience_segments,
            "competitors": self.competitors,
            "market_trends": self.market_data.get("trends", []),
            "offerings": self.offerings_data,
        }
