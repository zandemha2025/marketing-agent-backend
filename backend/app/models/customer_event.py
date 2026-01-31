"""
Customer behavioral event model for the CDP.

Tracks all customer interactions and behaviors across touchpoints
for analytics, personalization, and segmentation.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship

from .base import Base, generate_id


class EventType(str, Enum):
    """Standard event types for customer behavior tracking."""
    # Page/Content
    PAGE_VIEW = "page_view"
    PAGE_SCROLL = "page_scroll"
    CONTENT_VIEW = "content_view"

    # Engagement
    CLICK = "click"
    HOVER = "hover"
    FORM_START = "form_start"
    FORM_SUBMIT = "form_submit"
    FORM_ABANDON = "form_abandon"

    # E-commerce
    PRODUCT_VIEW = "product_view"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    BEGIN_CHECKOUT = "begin_checkout"
    PURCHASE = "purchase"
    REFUND = "refund"

    # User Actions
    SIGN_UP = "sign_up"
    LOGIN = "login"
    LOGOUT = "logout"
    PROFILE_UPDATE = "profile_update"

    # Communication
    EMAIL_OPEN = "email_open"
    EMAIL_CLICK = "email_click"
    EMAIL_BOUNCE = "email_bounce"
    EMAIL_UNSUBSCRIBE = "email_unsubscribe"
    PUSH_OPEN = "push_open"
    SMS_RECEIVED = "sms_received"

    # Campaign
    CAMPAIGN_VIEW = "campaign_view"
    CAMPAIGN_CLICK = "campaign_click"
    AD_VIEW = "ad_view"
    AD_CLICK = "ad_click"

    # Support
    SUPPORT_TICKET_CREATED = "support_ticket_created"
    SUPPORT_CHAT_STARTED = "support_chat_started"
    SUPPORT_ARTICLE_VIEW = "support_article_view"

    # Custom
    CUSTOM = "custom"


class EventSource(str, Enum):
    """Source of the event data."""
    WEB = "web"
    MOBILE_APP = "mobile_app"
    MOBILE_WEB = "mobile_web"
    SERVER = "server"
    API = "api"
    WEBHOOK = "webhook"
    IMPORT = "import"
    THIRD_PARTY = "third_party"


class CustomerEvent(Base):
    """
    Customer behavioral event model.

    Stores all customer interactions with comprehensive context
    for deep analytics and personalization.
    """

    # Organization/workspace scoping
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    workspace_id = Column(String(12), ForeignKey("organizations.id"), nullable=True)

    # Customer reference (null if anonymous)
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=True, index=True)

    # Anonymous ID for pre-identification tracking
    anonymous_id = Column(String(64), nullable=True, index=True)

    # Event classification
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    event_name = Column(String(100), nullable=False, index=True)

    # Event properties (flexible JSON)
    # Example for purchase: {"product_id": "123", "quantity": 2, "price": 99.99}
    properties = Column(JSON, default=dict, nullable=False)

    # Event context (page, device, location, campaign)
    context = Column(JSON, default=dict, nullable=False)
    # Example:
    # {
    #     "page": {"url": "...", "title": "...", "referrer": "..."},
    #     "device": {"type": "desktop", "os": "macOS", "browser": "Chrome"},
    #     "location": {"country": "US", "city": "NYC"},
    #     "campaign": {"utm_source": "google", "utm_medium": "cpc"},
    #     "ip": "192.168.1.1",
    #     "user_agent": "..."
    # }

    # Event source
    source = Column(SQLEnum(EventSource), default=EventSource.WEB, nullable=False)

    # Timestamps
    # timestamp: When the event occurred (client time)
    timestamp = Column(DateTime, nullable=False, index=True)
    # received_at: When the event was received by our servers
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # sent_at: When the event was sent from the client (for latency calculation)
    sent_at = Column(DateTime, nullable=True)

    # Integration metadata
    integration_id = Column(String(12), nullable=True)  # Source integration
    api_key_id = Column(String(12), nullable=True)  # API key used

    # GDPR/privacy
    # Hashed IP for privacy-preserving analytics
    ip_hash = Column(String(64), nullable=True)
    # Consent flags at time of event
    consent_context = Column(JSON, default=dict, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="events")

    # Indexes for time-series queries and analytics
    __table_args__ = (
        # Composite index for time-series queries by organization
        Index("ix_customer_events_org_time", "organization_id", "timestamp"),
        # Composite index for customer timeline queries
        Index("ix_customer_events_customer_time", "customer_id", "timestamp"),
        # Composite index for anonymous tracking
        Index("ix_customer_events_anon_time", "anonymous_id", "timestamp"),
        # Index for event type filtering
        Index("ix_customer_events_org_type", "organization_id", "event_type"),
        # Index for event name filtering
        Index("ix_customer_events_org_name", "organization_id", "event_name"),
        # Index for source filtering
        Index("ix_customer_events_source", "source"),
    )

    def __repr__(self):
        return f"<CustomerEvent {self.event_name} ({self.event_type}) customer={self.customer_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "workspace_id": self.workspace_id,
            "customer_id": self.customer_id,
            "anonymous_id": self.anonymous_id,
            "event_type": self.event_type.value if self.event_type else None,
            "event_name": self.event_name,
            "properties": self.properties,
            "context": self.context,
            "source": self.source.value if self.source else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "integration_id": self.integration_id,
            "api_key_id": self.api_key_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def get_latency_ms(self) -> Optional[int]:
        """Calculate event latency in milliseconds."""
        if self.sent_at and self.received_at:
            delta = self.received_at - self.sent_at
            return int(delta.total_seconds() * 1000)
        return None

    def get_page_url(self) -> Optional[str]:
        """Extract page URL from context."""
        if self.context and "page" in self.context:
            return self.context["page"].get("url")
        return None

    def get_campaign_source(self) -> Optional[str]:
        """Extract UTM source from context."""
        if self.context and "campaign" in self.context:
            return self.context["campaign"].get("utm_source")
        return None

    def get_device_type(self) -> Optional[str]:
        """Extract device type from context."""
        if self.context and "device" in self.context:
            return self.context["device"].get("type")
        return None

    @classmethod
    def create_page_view(
        cls,
        organization_id: str,
        url: str,
        title: str,
        customer_id: Optional[str] = None,
        anonymous_id: Optional[str] = None,
        referrer: Optional[str] = None,
        **kwargs
    ) -> "CustomerEvent":
        """Factory method to create a page view event."""
        context = {
            "page": {
                "url": url,
                "title": title,
                "referrer": referrer,
            }
        }
        if "context" in kwargs:
            context.update(kwargs.pop("context"))

        return cls(
            organization_id=organization_id,
            customer_id=customer_id,
            anonymous_id=anonymous_id,
            event_type=EventType.PAGE_VIEW,
            event_name="Page View",
            context=context,
            timestamp=datetime.utcnow(),
            **kwargs
        )

    @classmethod
    def create_purchase(
        cls,
        organization_id: str,
        product_id: str,
        quantity: int,
        price: float,
        currency: str = "USD",
        customer_id: Optional[str] = None,
        anonymous_id: Optional[str] = None,
        **kwargs
    ) -> "CustomerEvent":
        """Factory method to create a purchase event."""
        properties = {
            "product_id": product_id,
            "quantity": quantity,
            "price": price,
            "currency": currency,
            "total": quantity * price,
        }
        if "properties" in kwargs:
            properties.update(kwargs.pop("properties"))

        return cls(
            organization_id=organization_id,
            customer_id=customer_id,
            anonymous_id=anonymous_id,
            event_type=EventType.PURCHASE,
            event_name="Order Completed",
            properties=properties,
            timestamp=datetime.utcnow(),
            **kwargs
        )