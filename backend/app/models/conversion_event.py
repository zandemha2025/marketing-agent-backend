"""
Conversion Event model for attribution tracking.

Tracks conversion events (purchases, signups, etc.) that can be attributed
to marketing touchpoints for ROI analysis and campaign optimization.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, Index, Enum as SQLEnum, Float, Integer, Boolean, Text
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class ConversionType(str, Enum):
    """Types of conversion events."""
    PURCHASE = "purchase"                       # E-commerce purchase events
    SIGNUP = "signup"                           # User registration/signup
    LEAD = "lead"                               # Lead generation (form submissions)
    SUBSCRIPTION = "subscription"               # Subscription starts/renewals
    DOWNLOAD = "download"                       # Content/app downloads
    ENGAGEMENT = "engagement"                   # High-value engagement actions
    TRIAL_START = "trial_start"
    TRIAL_CONVERSION = "trial_conversion"
    SUBSCRIPTION_START = "subscription_start"
    SUBSCRIPTION_RENEWAL = "subscription_renewal"
    UPGRADE = "upgrade"
    REFERRAL = "referral"
    APPOINTMENT_BOOKED = "appointment_booked"
    DEMO_REQUESTED = "demo_requested"
    WHITEPAPER_DOWNLOAD = "whitepaper_download"
    WEBINAR_REGISTRATION = "webinar_registration"
    CUSTOM = "custom"                           # Custom conversion events


class MarketingChannel(str, Enum):
    """Marketing channels for attribution."""
    ORGANIC = "organic"           # Organic search
    PAID_SEARCH = "paid_search"   # Paid search (SEM)
    PAID_SOCIAL = "paid_social"   # Paid social media
    ORGANIC_SOCIAL = "organic_social"  # Organic social media
    EMAIL = "email"               # Email marketing
    DISPLAY = "display"           # Display advertising
    AFFILIATE = "affiliate"       # Affiliate marketing
    REFERRAL = "referral"         # Referral traffic
    DIRECT = "direct"             # Direct traffic
    VIDEO = "video"               # Video advertising (YouTube, etc.)
    PODCAST = "podcast"           # Podcast advertising
    INFLUENCER = "influencer"     # Influencer marketing
    SMS = "sms"                   # SMS marketing
    PUSH = "push"                 # Push notifications
    OFFLINE = "offline"           # Offline channels
    OTHER = "other"               # Other/unknown channels


class ConversionStatus(str, Enum):
    """Status of conversion processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    ATTRIBUTED = "attributed"
    FAILED = "failed"
    EXCLUDED = "excluded"


class ConversionEvent(Base):
    """
    Conversion Event model.

    Stores conversion events that can be attributed to marketing touchpoints
    for ROI analysis and campaign optimization.
    """

    # Organization/workspace scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(String(12), ForeignKey("organizations.id"), nullable=True)

    # Customer reference
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=True, index=True)
    anonymous_id = Column(String(64), nullable=True, index=True)

    # Conversion classification
    conversion_type = Column(SQLEnum(ConversionType), nullable=False, index=True)
    conversion_name = Column(String(100), nullable=False, index=True)
    event_name = Column(String(255), nullable=True)  # Human-readable event name

    # Conversion value
    currency = Column(String(3), default="USD", nullable=False)
    conversion_value = Column(Float, nullable=False, default=0.0)
    quantity = Column(Integer, nullable=True)

    # Marketing attribution fields
    channel = Column(SQLEnum(MarketingChannel), nullable=True, index=True)  # Marketing channel
    source = Column(String(100), nullable=True, index=True)  # Traffic source (e.g., google, facebook)
    medium = Column(String(100), nullable=True, index=True)  # Marketing medium (e.g., cpc, email, social)

    # Conversion metadata
    properties = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "product_id": "prod_123",
    #     "product_name": "Premium Plan",
    #     "order_id": "order_456",
    #     "subscription_tier": "enterprise",
    #     "billing_cycle": "annual"
    # }

    # Context at time of conversion
    context = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "page": {"url": "...", "title": "...", "referrer": "..."},
    #     "device": {"type": "desktop", "os": "macOS", "browser": "Chrome"},
    #     "campaign": {"utm_source": "google", "utm_medium": "cpc"}
    # }

    # Attribution data (JSON field for flexible attribution model data)
    attribution_data = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "first_touch": {"campaign_id": "...", "channel": "paid_search", "credit": 0.4},
    #     "last_touch": {"campaign_id": "...", "channel": "email", "credit": 0.6},
    #     "touchpoint_path": ["paid_search", "organic", "email"],
    #     "time_decay_weights": [0.2, 0.3, 0.5]
    # }

    # Attribution tracking
    attribution_model = Column(String(50), nullable=True)  # first_touch, last_touch, linear, etc.
    attributed_touchpoint_count = Column(Integer, nullable=True)
    attribution_confidence = Column(Float, nullable=True)  # 0.0 to 1.0

    # Lookback window
    lookback_window_days = Column(Integer, default=30, nullable=False)

    # Timestamps
    conversion_timestamp = Column(DateTime, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Status
    status = Column(SQLEnum(ConversionStatus), default=ConversionStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Campaign association
    campaign_id = Column(String(12), ForeignKey("campaigns.id"), nullable=True, index=True)

    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    customer = relationship("Customer", back_populates="conversions")
    campaign = relationship("Campaign")
    touchpoints = relationship(
        "AttributionTouchpoint",
        back_populates="conversion_event",
        cascade="all, delete-orphan"
    )
    attributions = relationship(
        "Attribution",
        back_populates="conversion_event",
        cascade="all, delete-orphan"
    )

    # Indexes for analytics queries
    __table_args__ = (
        # Composite index for time-series queries by organization
        Index("ix_conversion_events_org_time", "organization_id", "conversion_timestamp"),
        # Composite index for customer conversion queries
        Index("ix_conversion_events_customer_time", "customer_id", "conversion_timestamp"),
        # Composite index for campaign attribution
        Index("ix_conversion_events_campaign", "campaign_id", "conversion_timestamp"),
        # Index for status + timestamp filtering
        Index("ix_conversion_events_status_time", "status", "conversion_timestamp"),
        # Index for type filtering
        Index("ix_conversion_events_org_type", "organization_id", "conversion_type"),
        # Index for channel-based analytics
        Index("ix_conversion_events_org_channel", "organization_id", "channel"),
        # Index for source/medium attribution
        Index("ix_conversion_events_source_medium", "source", "medium"),
    )

    def __repr__(self):
        return f"<ConversionEvent {self.conversion_name} ({self.conversion_type}) value={self.conversion_value}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversion event to dictionary representation."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "customer_id": self.customer_id,
            "anonymous_id": self.anonymous_id,
            "conversion_type": self.conversion_type.value if self.conversion_type else None,
            "conversion_name": self.conversion_name,
            "event_name": self.event_name,
            "currency": self.currency,
            "conversion_value": self.conversion_value,
            "quantity": self.quantity,
            "channel": self.channel.value if self.channel else None,
            "source": self.source,
            "medium": self.medium,
            "properties": self.properties,
            "context": self.context,
            "attribution_data": self.attribution_data,
            "attribution_model": self.attribution_model,
            "attributed_touchpoint_count": self.attributed_touchpoint_count,
            "attribution_confidence": self.attribution_confidence,
            "lookback_window_days": self.lookback_window_days,
            "conversion_timestamp": self.conversion_timestamp.isoformat() if self.conversion_timestamp else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "status": self.status.value if self.status else None,
            "campaign_id": self.campaign_id,
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

    def get_primary_attribution(self) -> Optional["Attribution"]:
        """Get the primary (highest value) attribution for this conversion."""
        if not self.attributions:
            return None
        return max(self.attributions, key=lambda a: a.attributed_value)

    def get_touchpoint_summary(self) -> List[Dict[str, Any]]:
        """Get a summary of all touchpoints associated with this conversion."""
        if not self.touchpoints:
            return []

        return [
            {
                "id": tp.id,
                "touchpoint_type": tp.touchpoint_type.value if tp.touchpoint_type else None,
                "channel": tp.channel,
                "campaign_id": tp.campaign_id,
                "timestamp": tp.touchpoint_timestamp.isoformat() if tp.touchpoint_timestamp else None,
                "position": tp.position_in_journey,
                "time_to_conversion_hours": tp.time_to_conversion_hours,
            }
            for tp in sorted(self.touchpoints, key=lambda x: x.touchpoint_timestamp or datetime.min)
        ]

    def mark_as_processed(self, attribution_model: str = None, touchpoint_count: int = None, confidence: float = None):
        """Mark the conversion as processed with attribution data."""
        self.status = ConversionStatus.ATTRIBUTED
        self.processed_at = datetime.utcnow()
        if attribution_model:
            self.attribution_model = attribution_model
        if touchpoint_count is not None:
            self.attributed_touchpoint_count = touchpoint_count
        if confidence is not None:
            self.attribution_confidence = confidence

    def mark_as_failed(self, error_message: str):
        """Mark the conversion as failed with an error message."""
        self.status = ConversionStatus.FAILED
        self.processed_at = datetime.utcnow()
        self.error_message = error_message

    def is_high_value(self, threshold: float = 100.0) -> bool:
        """Check if this is a high-value conversion."""
        return self.conversion_value >= threshold

    def get_utm_params(self) -> Dict[str, Any]:
        """Extract UTM parameters from context."""
        if not self.context:
            return {}
        campaign_data = self.context.get("campaign", {})
        return {
            "utm_source": campaign_data.get("utm_source") or self.source,
            "utm_medium": campaign_data.get("utm_medium") or self.medium,
            "utm_campaign": campaign_data.get("utm_campaign"),
            "utm_term": campaign_data.get("utm_term"),
            "utm_content": campaign_data.get("utm_content"),
        }

    def set_attribution_from_utm(self):
        """Set channel, source, and medium from UTM parameters in context."""
        utm_params = self.get_utm_params()
        if utm_params.get("utm_source") and not self.source:
            self.source = utm_params["utm_source"]
        if utm_params.get("utm_medium") and not self.medium:
            self.medium = utm_params["utm_medium"]
        
        # Auto-detect channel from source/medium if not set
        if not self.channel and self.source:
            self.channel = self._detect_channel_from_source()

    def _detect_channel_from_source(self) -> Optional[MarketingChannel]:
        """Detect marketing channel from source and medium."""
        source_lower = (self.source or "").lower()
        medium_lower = (self.medium or "").lower()
        
        # Check medium first for more specific classification
        if medium_lower in ("cpc", "ppc", "paid", "paidsearch"):
            return MarketingChannel.PAID_SEARCH
        if medium_lower in ("email", "e-mail"):
            return MarketingChannel.EMAIL
        if medium_lower in ("social", "social-media"):
            if "paid" in source_lower:
                return MarketingChannel.PAID_SOCIAL
            return MarketingChannel.ORGANIC_SOCIAL
        if medium_lower in ("display", "banner", "cpm"):
            return MarketingChannel.DISPLAY
        if medium_lower in ("affiliate", "partner"):
            return MarketingChannel.AFFILIATE
        if medium_lower == "referral":
            return MarketingChannel.REFERRAL
        if medium_lower == "organic":
            return MarketingChannel.ORGANIC
        
        # Check source for common patterns
        if source_lower in ("google", "bing", "yahoo", "duckduckgo"):
            if medium_lower in ("cpc", "ppc", "paid"):
                return MarketingChannel.PAID_SEARCH
            return MarketingChannel.ORGANIC
        if source_lower in ("facebook", "instagram", "twitter", "linkedin", "tiktok"):
            if "paid" in medium_lower or "ad" in medium_lower:
                return MarketingChannel.PAID_SOCIAL
            return MarketingChannel.ORGANIC_SOCIAL
        if source_lower == "(direct)" or source_lower == "direct":
            return MarketingChannel.DIRECT
        
        return MarketingChannel.OTHER
