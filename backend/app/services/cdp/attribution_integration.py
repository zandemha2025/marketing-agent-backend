"""
Attribution Integration for CDP Event Processing.

Integrates the Conversion Tracker with the CDP event processing pipeline
to automatically track conversions and create attribution touchpoints
from customer behavioral events.
"""
import logging
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.customer_event import CustomerEvent, EventType
from ...models.conversion_event import ConversionType
from ..analytics.conversion_tracker import ConversionTracker

logger = logging.getLogger(__name__)


class AttributionIntegration:
    """
    Attribution Integration for CDP.

    Automatically tracks conversions and creates attribution touchpoints
    from customer events processed by the CDP pipeline.
    """

    # Event types that trigger conversion tracking
    CONVERSION_EVENT_TYPES = {
        EventType.PURCHASE,
        EventType.SIGN_UP,
        EventType.FORM_SUBMIT,
    }

    def __init__(self, db: AsyncSession):
        """
        Initialize the Attribution Integration.

        Args:
            db: SQLAlchemy async session.
        """
        self.db = db
        self.conversion_tracker = ConversionTracker(db)

    async def process_event(
        self,
        event: CustomerEvent
    ) -> Optional[Dict[str, Any]]:
        """
        Process a customer event for attribution.

        Automatically tracks conversions and creates touchpoints
        based on event type and properties.

        Args:
            event: The customer event to process.

        Returns:
            Conversion tracking result if a conversion was created.
        """
        try:
            # Check if this is a conversion event
            if event.event_type in self.CONVERSION_EVENT_TYPES:
                conversion = await self.conversion_tracker.track_conversion_from_event(
                    event=event
                )

                if conversion:
                    return {
                        "conversion_id": conversion.id,
                        "conversion_type": conversion.conversion_type.value if conversion.conversion_type else None,
                        "conversion_value": conversion.conversion_value,
                        "touchpoint_count": conversion.attributed_touchpoint_count or 0,
                        "status": "tracked"
                    }

            # Create touchpoint for non-conversion events
            else:
                touchpoint = await self._create_touchpoint_from_event(event)
                if touchpoint:
                    return {
                        "touchpoint_id": touchpoint.id,
                        "channel": touchpoint.channel,
                        "touchpoint_type": touchpoint.touchpoint_type.value if touchpoint.touchpoint_type else None,
                        "status": "created"
                    }

            return None

        except Exception as e:
            logger.error(f"Error processing event {event.id} for attribution: {e}")
            return None

    async def _create_touchpoint_from_event(
        self,
        event: CustomerEvent
    ) -> Optional[Any]:
        """
        Create an attribution touchpoint from a non-conversion event.

        Args:
            event: The customer event.

        Returns:
            Created touchpoint or None.
        """
        from ...models.attribution_touchpoint import TouchpointType

        # Map event type to touchpoint type
        touchpoint_type = self._map_event_to_touchpoint_type(event)
        if not touchpoint_type:
            return None

        # Extract UTM parameters
        campaign_context = event.context.get("campaign", {})
        utm_source = campaign_context.get("utm_source")
        utm_medium = campaign_context.get("utm_medium")
        utm_campaign = campaign_context.get("utm_campaign")

        # Determine channel
        channel = self._determine_channel(event, utm_source, utm_medium)

        # Create touchpoint
        touchpoint = await self.conversion_tracker.create_touchpoint(
            organization_id=event.organization_id,
            customer_id=event.customer_id,
            anonymous_id=event.anonymous_id,
            touchpoint_type=touchpoint_type,
            channel=channel,
            campaign_id=event.properties.get("campaign_id"),
            properties=event.properties,
            context=event.context,
            cost=event.properties.get("cost"),
            timestamp=event.timestamp
        )

        return touchpoint

    def _map_event_to_touchpoint_type(
        self,
        event: CustomerEvent
    ) -> Optional[TouchpointType]:
        """Map a customer event to a touchpoint type."""
        from ...models.attribution_touchpoint import TouchpointType

        mapping = {
            EventType.AD_CLICK: TouchpointType.PAID_SEARCH,
            EventType.AD_VIEW: TouchpointType.DISPLAY_AD,
            EventType.CAMPAIGN_CLICK: TouchpointType.PAID_SOCIAL,
            EventType.CAMPAIGN_VIEW: TouchpointType.PAID_SOCIAL,
            EventType.EMAIL_CLICK: TouchpointType.EMAIL,
            EventType.EMAIL_OPEN: TouchpointType.EMAIL,
            EventType.PAGE_VIEW: TouchpointType.ORGANIC_SEARCH,
            EventType.CLICK: TouchpointType.DIRECT,
        }

        # Refine based on UTM parameters
        campaign = event.context.get("campaign", {})
        utm_medium = campaign.get("utm_medium", "").lower()
        utm_source = campaign.get("utm_source", "").lower()

        if "cpc" in utm_medium or "ppc" in utm_medium:
            return TouchpointType.PAID_SEARCH
        elif "social" in utm_medium or "facebook" in utm_source or "instagram" in utm_source:
            return TouchpointType.PAID_SOCIAL
        elif "email" in utm_medium:
            return TouchpointType.EMAIL
        elif "display" in utm_medium or "banner" in utm_medium:
            return TouchpointType.DISPLAY_AD
        elif "video" in utm_medium:
            return TouchpointType.VIDEO_AD
        elif "organic" in utm_medium or "referral" in utm_medium:
            return TouchpointType.ORGANIC_SEARCH
        elif "direct" in utm_medium or not utm_medium:
            return TouchpointType.DIRECT

        return mapping.get(event.event_type)

    def _determine_channel(
        self,
        event: CustomerEvent,
        utm_source: str = None,
        utm_medium: str = None
    ) -> str:
        """Determine the marketing channel from event context."""
        if utm_source:
            return utm_source.lower()

        if utm_medium:
            return utm_medium.lower()

        # Infer from event type
        if event.event_type in {EventType.AD_CLICK, EventType.AD_VIEW}:
            return "paid_ads"
        elif event.event_type in {EventType.EMAIL_CLICK, EventType.EMAIL_OPEN}:
            return "email"
        elif event.event_type in {EventType.CAMPAIGN_CLICK, EventType.CAMPAIGN_VIEW}:
            return "social"
        elif event.event_type == EventType.PAGE_VIEW:
            referrer = event.context.get("page", {}).get("referrer", "")
            if "google" in referrer:
                return "organic_search"
            elif "facebook" in referrer or "instagram" in referrer:
                return "organic_social"
            return "direct"

        return "unknown"

    async def merge_customer_journeys(
        self,
        organization_id: str,
        anonymous_id: str,
        customer_id: str
    ) -> Dict[str, Any]:
        """
        Merge anonymous journey with identified customer journey.

        Args:
            organization_id: Organization ID.
            anonymous_id: Anonymous ID to merge.
            customer_id: Customer ID to merge into.

        Returns:
            Merge result summary.
        """
        return await self.conversion_tracker.merge_customer_journeys(
            organization_id=organization_id,
            anonymous_id=anonymous_id,
            customer_id=customer_id
        )


class EventProcessorWithAttribution:
    """
    Extended Event Processor with Attribution Integration.

    Wraps the standard EventProcessor and adds attribution tracking
    to the event processing pipeline.
    """

    def __init__(self, db: AsyncSession, event_processor: Any):
        """
        Initialize the processor.

        Args:
            db: SQLAlchemy async session.
            event_processor: The base event processor to wrap.
        """
        self.db = db
        self.event_processor = event_processor
        self.attribution_integration = AttributionIntegration(db)

    async def ingest_event(
        self,
        event_data: Dict[str, Any],
        organization_id: Optional[str] = None
    ) -> Tuple[Any, Any, Optional[Dict[str, Any]]]:
        """
        Ingest an event with attribution tracking.

        Args:
            event_data: Raw event data.
            organization_id: Optional organization ID.

        Returns:
            Tuple of (event, customer, attribution_result).
        """
        # Process event with base processor
        event, customer = await self.event_processor.ingest_event(
            event_data, organization_id
        )

        # Process for attribution
        attribution_result = None
        if event:
            attribution_result = await self.attribution_integration.process_event(event)

        return event, customer, attribution_result

    async def process_event_batch(
        self,
        events: List[Dict[str, Any]],
        organization_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Process a batch of events with attribution tracking.

        Args:
            events: List of event data dictionaries.
            organization_id: Optional organization ID.

        Returns:
            List of processing results with attribution.
        """
        results = []

        for event_data in events:
            try:
                event, customer, attribution = await self.ingest_event(
                    event_data, organization_id
                )

                results.append({
                    "event_id": event.id if event else None,
                    "customer_id": customer.id if customer else None,
                    "attribution": attribution,
                    "status": "success"
                })

            except Exception as e:
                logger.error(f"Error processing event in batch: {e}")
                results.append({
                    "event_id": None,
                    "customer_id": None,
                    "attribution": None,
                    "status": "error",
                    "error": str(e)
                })

        return results
