"""
Attribution Touchpoint model for tracking customer interactions.

Represents individual touchpoints in a customer's journey that can be
attributed to conversions for multi-touch attribution analysis.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, Index, Enum as SQLEnum, Float, Integer, Text
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class TouchpointType(str, Enum):
    """Types of marketing touchpoints."""
    # Paid Media
    PAID_SEARCH = "paid_search"
    PAID_SOCIAL = "paid_social"
    DISPLAY_AD = "display_ad"
    VIDEO_AD = "video_ad"
    NATIVE_AD = "native_ad"
    PROGRAMMATIC = "programmatic"
    RETARGETING = "retargeting"

    # Organic
    ORGANIC_SEARCH = "organic_search"
    ORGANIC_SOCIAL = "organic_social"
    DIRECT = "direct"
    REFERRAL = "referral"

    # Email
    EMAIL = "email"
    EMAIL_NEWSLETTER = "email_newsletter"
    EMAIL_PROMOTIONAL = "email_promotional"
    EMAIL_TRANSACTIONAL = "email_transactional"
    EMAIL_AUTOMATED = "email_automated"

    # Content
    BLOG = "blog"
    CONTENT_DOWNLOAD = "content_download"
    WEBINAR = "webinar"
    PODCAST = "podcast"
    VIDEO_CONTENT = "video_content"

    # Events
    TRADE_SHOW = "trade_show"
    CONFERENCE = "conference"
    WEBINAR_EVENT = "webinar_event"
    WORKSHOP = "workshop"

    # Sales
    SALES_CALL = "sales_call"
    DEMO = "demo"
    SALES_EMAIL = "sales_email"

    # Support
    SUPPORT_INTERACTION = "support_interaction"
    CHAT = "chat"

    # Other
    AFFILIATE = "affiliate"
    PARTNER = "partner"
    PR = "pr"
    CUSTOM = "custom"


class TouchpointStatus(str, Enum):
    """Status of touchpoint processing."""
    ACTIVE = "active"
    ATTRIBUTED = "attributed"
    EXCLUDED = "excluded"
    DUPLICATE = "duplicate"


class AttributionTouchpoint(Base):
    """
    Attribution Touchpoint model.

    Represents individual touchpoints in a customer's journey that can be
    attributed to conversions for multi-touch attribution analysis.
    """

    # Organization/workspace scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(String(12), ForeignKey("organizations.id"), nullable=True)

    # Customer reference
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=True, index=True)
    anonymous_id = Column(String(64), nullable=True, index=True)

    # Conversion reference (if attributed)
    conversion_event_id = Column(String(12), ForeignKey("conversion_events.id"), nullable=True, index=True)

    # Touchpoint classification
    touchpoint_type = Column(SQLEnum(TouchpointType), nullable=False, index=True)
    channel = Column(String(50), nullable=False, index=True)  # e.g., "google_ads", "facebook", "email"
    sub_channel = Column(String(50), nullable=True)  # e.g., "search", "display", "retargeting"

    # Campaign association
    campaign_id = Column(String(12), ForeignKey("campaigns.id"), nullable=True, index=True)
    campaign_name = Column(String(255), nullable=True)

    # Ad/creative details
    ad_group_id = Column(String(100), nullable=True)
    ad_id = Column(String(100), nullable=True)
    creative_id = Column(String(100), nullable=True)
    creative_name = Column(String(255), nullable=True)

    # UTM parameters
    utm_source = Column(String(100), nullable=True, index=True)
    utm_medium = Column(String(100), nullable=True, index=True)
    utm_campaign = Column(String(255), nullable=True, index=True)
    utm_content = Column(String(255), nullable=True)
    utm_term = Column(String(255), nullable=True)

    # Touchpoint metadata
    properties = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "keyword": "marketing software",
    #     "match_type": "exact",
    #     "device": "mobile",
    #     "placement": "news_feed",
    #     "cost": 2.50,
    #     "impressions": 1000,
    #     "clicks": 50
    # }

    # Context at time of touchpoint
    context = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "page": {"url": "...", "title": "...", "referrer": "..."},
    #     "device": {"type": "desktop", "os": "macOS", "browser": "Chrome"},
    #     "location": {"country": "US", "city": "NYC"}
    # }

    # Journey positioning
    position_in_journey = Column(Integer, nullable=True)  # 1st, 2nd, 3rd touchpoint, etc.
    time_to_conversion_hours = Column(Float, nullable=True)  # Hours until conversion

    # Engagement metrics
    engagement_score = Column(Float, nullable=True)  # 0.0 to 1.0
    time_on_page_seconds = Column(Integer, nullable=True)
    pages_viewed = Column(Integer, nullable=True)

    # Cost data (if available)
    cost = Column(Float, nullable=True)
    cost_currency = Column(String(3), default="USD", nullable=True)

    # Timestamps
    touchpoint_timestamp = Column(DateTime, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Status
    status = Column(SQLEnum(TouchpointStatus), default=TouchpointStatus.ACTIVE, nullable=False)

    # Source event reference
    source_event_id = Column(String(12), ForeignKey("customer_events.id"), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="touchpoints")
    conversion_event = relationship("ConversionEvent", back_populates="touchpoints")
    campaign = relationship("Campaign")
    source_event = relationship("CustomerEvent")
    attributions = relationship(
        "Attribution",
        back_populates="touchpoint",
        cascade="all, delete-orphan"
    )

    # Indexes for analytics queries
    __table_args__ = (
        # Composite index for time-series queries by organization
        Index("ix_touchpoints_org_time", "organization_id", "touchpoint_timestamp"),
        # Composite index for customer journey queries
        Index("ix_touchpoints_customer_time", "customer_id", "touchpoint_timestamp"),
        # Composite index for conversion attribution
        Index("ix_touchpoints_conversion", "conversion_event_id", "touchpoint_timestamp"),
        # Composite index for campaign performance
        Index("ix_touchpoints_campaign", "campaign_id", "touchpoint_timestamp"),
        # Composite index for channel analysis
        Index("ix_touchpoints_org_channel", "organization_id", "channel", "touchpoint_timestamp"),
        # Index for UTM campaign tracking
        Index("ix_touchpoints_utm_campaign", "utm_campaign", "touchpoint_timestamp"),
        # Index for source/medium analysis
        Index("ix_touchpoints_utm_source_medium", "utm_source", "utm_medium", "touchpoint_timestamp"),
    )

    def __repr__(self):
        return f"<AttributionTouchpoint {self.touchpoint_type} channel={self.channel} position={self.position_in_journey}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert touchpoint to dictionary representation."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "customer_id": self.customer_id,
            "anonymous_id": self.anonymous_id,
            "conversion_event_id": self.conversion_event_id,
            "touchpoint_type": self.touchpoint_type.value if self.touchpoint_type else None,
            "channel": self.channel,
            "sub_channel": self.sub_channel,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "ad_group_id": self.ad_group_id,
            "ad_id": self.ad_id,
            "creative_id": self.creative_id,
            "creative_name": self.creative_name,
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
            "utm_content": self.utm_content,
            "utm_term": self.utm_term,
            "properties": self.properties,
            "context": self.context,
            "position_in_journey": self.position_in_journey,
            "time_to_conversion_hours": self.time_to_conversion_hours,
            "engagement_score": self.engagement_score,
            "time_on_page_seconds": self.time_on_page_seconds,
            "pages_viewed": self.pages_viewed,
            "cost": self.cost,
            "cost_currency": self.cost_currency,
            "touchpoint_timestamp": self.touchpoint_timestamp.isoformat() if self.touchpoint_timestamp else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "status": self.status.value if self.status else None,
            "source_event_id": self.source_event_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_attributed_value(self, model: str = None) -> float:
        """
        Get the total attributed value across all attribution models.

        Args:
            model: Optional specific attribution model to filter by

        Returns:
            Total attributed value
        """
        if not self.attributions:
            return 0.0

        if model:
            return sum(
                attr.attributed_value
                for attr in self.attributions
                if attr.model_type == model
            )
        return sum(attr.attributed_value for attr in self.attributions)

    def is_paid_touchpoint(self) -> bool:
        """Check if this is a paid media touchpoint."""
        paid_types = {
            TouchpointType.PAID_SEARCH,
            TouchpointType.PAID_SOCIAL,
            TouchpointType.DISPLAY_AD,
            TouchpointType.VIDEO_AD,
            TouchpointType.NATIVE_AD,
            TouchpointType.PROGRAMMATIC,
            TouchpointType.RETARGETING,
        }
        return self.touchpoint_type in paid_types

    def get_journey_stage(self) -> str:
        """
        Determine the customer journey stage based on position.

        Returns:
            Journey stage: "awareness", "consideration", "decision", or "retention"
        """
        if not self.position_in_journey:
            return "unknown"

        if self.position_in_journey == 1:
            return "awareness"
        elif self.time_to_conversion_hours and self.time_to_conversion_hours > 168:  # > 7 days
            return "consideration"
        elif self.time_to_conversion_hours and self.time_to_conversion_hours <= 24:  # < 1 day
            return "decision"
        else:
            return "consideration"
