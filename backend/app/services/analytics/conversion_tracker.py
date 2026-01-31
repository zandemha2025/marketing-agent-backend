"""
Conversion Tracker Service.

Tracks conversions and touchpoints for attribution analysis.
Integrates with the CDP event processing pipeline to capture
conversion events and create attribution touchpoints.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from ...models.conversion_event import ConversionEvent, ConversionType, ConversionStatus
from ...models.attribution_touchpoint import AttributionTouchpoint, TouchpointType, TouchpointStatus
from ...models.customer_event import CustomerEvent, EventType
from ...models.campaign import Campaign

logger = logging.getLogger(__name__)


@dataclass
class ConversionTrackingResult:
    """Result of conversion tracking."""
    conversion_event_id: str
    touchpoint_count: int
    status: str
    errors: List[str]


class ConversionTracker:
    """
    Conversion Tracker Service.

    Tracks conversions from customer events and creates attribution
    touchpoints for multi-touch attribution analysis.

    Integrates with the CDP event processing pipeline to:
    - Detect conversion events
    - Create conversion records
    - Track touchpoints in the customer journey
    - Link touchpoints to conversions
    """

    # Event types that count as conversions
    CONVERSION_EVENT_TYPES = {
        EventType.PURCHASE,
        EventType.SIGN_UP,
        EventType.FORM_SUBMIT,
    }

    # Event types that create touchpoints
    TOUCHPOINT_EVENT_TYPES = {
        EventType.AD_CLICK,
        EventType.AD_VIEW,
        EventType.CAMPAIGN_CLICK,
        EventType.CAMPAIGN_VIEW,
        EventType.EMAIL_CLICK,
        EventType.EMAIL_OPEN,
        EventType.PAGE_VIEW,
        EventType.CLICK,
    }

    def __init__(self, db: AsyncSession):
        """
        Initialize the Conversion Tracker.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db

    # ============== Conversion Detection ==============

    async def track_conversion_from_event(
        self,
        event: CustomerEvent,
        conversion_type: ConversionType = None,
        conversion_value: float = None,
        lookback_window_days: int = 30
    ) -> Optional[ConversionEvent]:
        """
        Track a conversion from a customer event.

        Args:
            event: The customer event that triggered conversion.
            conversion_type: Type of conversion (auto-detected if None).
            conversion_value: Conversion value (from event properties if None).
            lookback_window_days: Days to look back for touchpoints.

        Returns:
            Created conversion event or None if not a conversion.
        """
        # Check if event is a conversion type
        if event.event_type not in self.CONVERSION_EVENT_TYPES:
            return None

        # Auto-detect conversion type
        if conversion_type is None:
            conversion_type = self._detect_conversion_type(event)

        # Get conversion value from event properties
        if conversion_value is None:
            conversion_value = event.properties.get("value", 0) or event.properties.get("revenue", 0) or 0

        # Create conversion event
        conversion = ConversionEvent(
            organization_id=event.organization_id,
            workspace_id=event.workspace_id,
            customer_id=event.customer_id,
            anonymous_id=event.anonymous_id,
            conversion_type=conversion_type,
            conversion_name=event.event_name,
            currency=event.properties.get("currency", "USD"),
            conversion_value=float(conversion_value),
            quantity=event.properties.get("quantity"),
            properties=event.properties,
            context=event.context,
            lookback_window_days=lookback_window_days,
            conversion_timestamp=event.timestamp,
            status=ConversionStatus.PENDING,
            campaign_id=event.properties.get("campaign_id")
        )

        self.db.add(conversion)
        await self.db.flush()

        # Create touchpoints from customer journey
        touchpoint_count = await self._create_touchpoints_for_conversion(
            conversion, lookback_window_days
        )

        logger.info(
            f"Created conversion {conversion.id} with {touchpoint_count} touchpoints "
            f"for customer {event.customer_id}"
        )

        return conversion

    def _detect_conversion_type(self, event: CustomerEvent) -> ConversionType:
        """Detect conversion type from event."""
        event_name_lower = event.event_name.lower()

        if event.event_type == EventType.PURCHASE:
            return ConversionType.PURCHASE
        elif event.event_type == EventType.SIGN_UP:
            if "trial" in event_name_lower:
                return ConversionType.TRIAL_START
            return ConversionType.SIGNUP
        elif event.event_type == EventType.FORM_SUBMIT:
            if "demo" in event_name_lower:
                return ConversionType.DEMO_REQUESTED
            elif "contact" in event_name_lower or "lead" in event_name_lower:
                return ConversionType.LEAD
            elif "whitepaper" in event_name_lower or "download" in event_name_lower:
                return ConversionType.WHITEPAPER_DOWNLOAD
            elif "webinar" in event_name_lower:
                return ConversionType.WEBINAR_REGISTRATION

        return ConversionType.CUSTOM

    # ============== Touchpoint Creation ==============

    async def _create_touchpoints_for_conversion(
        self,
        conversion: ConversionEvent,
        lookback_window_days: int
    ) -> int:
        """
        Create touchpoints for a conversion from customer events.

        Args:
            conversion: The conversion event.
            lookback_window_days: Days to look back for events.

        Returns:
            Number of touchpoints created.
        """
        # Calculate lookback window
        lookback_start = conversion.conversion_timestamp - timedelta(days=lookback_window_days)

        # Query customer events in lookback window
        query = select(CustomerEvent).where(
            and_(
                CustomerEvent.organization_id == conversion.organization_id,
                CustomerEvent.customer_id == conversion.customer_id,
                CustomerEvent.timestamp >= lookback_start,
                CustomerEvent.timestamp <= conversion.conversion_timestamp
            )
        ).order_by(CustomerEvent.timestamp)

        result = await self.db.execute(query)
        events = result.scalars().all()

        touchpoint_count = 0
        for i, event in enumerate(events):
            touchpoint = await self._create_touchpoint_from_event(
                event, conversion, position=i+1
            )
            if touchpoint:
                touchpoint_count += 1

        return touchpoint_count

    async def _create_touchpoint_from_event(
        self,
        event: CustomerEvent,
        conversion: ConversionEvent,
        position: int
    ) -> Optional[AttributionTouchpoint]:
        """
        Create an attribution touchpoint from a customer event.

        Args:
            event: The customer event.
            conversion: The associated conversion.
            position: Position in the customer journey.

        Returns:
            Created touchpoint or None.
        """
        # Determine touchpoint type from event
        touchpoint_type = self._map_event_to_touchpoint_type(event)
        if not touchpoint_type:
            return None

        # Extract UTM parameters from context
        campaign_context = event.context.get("campaign", {})
        utm_source = campaign_context.get("utm_source")
        utm_medium = campaign_context.get("utm_medium")
        utm_campaign = campaign_context.get("utm_campaign")
        utm_content = campaign_context.get("utm_content")
        utm_term = campaign_context.get("utm_term")

        # Determine channel
        channel = self._determine_channel(event, utm_source, utm_medium)

        # Calculate time to conversion
        time_to_conversion = (conversion.conversion_timestamp - event.timestamp).total_seconds() / 3600

        # Extract engagement metrics
        properties = event.properties
        engagement_score = self._calculate_engagement_score(event)

        # Create touchpoint
        touchpoint = AttributionTouchpoint(
            organization_id=event.organization_id,
            workspace_id=event.workspace_id,
            customer_id=event.customer_id,
            anonymous_id=event.anonymous_id,
            conversion_event_id=conversion.id,
            touchpoint_type=touchpoint_type,
            channel=channel,
            sub_channel=utm_medium,
            campaign_id=event.properties.get("campaign_id"),
            campaign_name=utm_campaign,
            ad_id=event.properties.get("ad_id"),
            creative_id=event.properties.get("creative_id"),
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            properties=properties,
            context=event.context,
            position_in_journey=position,
            time_to_conversion_hours=time_to_conversion,
            engagement_score=engagement_score,
            time_on_page_seconds=properties.get("time_on_page"),
            pages_viewed=properties.get("pages_viewed"),
            cost=properties.get("cost"),
            cost_currency=properties.get("cost_currency", "USD"),
            touchpoint_timestamp=event.timestamp,
            status=TouchpointStatus.ACTIVE,
            source_event_id=event.id
        )

        self.db.add(touchpoint)
        await self.db.flush()

        return touchpoint

    def _map_event_to_touchpoint_type(
        self,
        event: CustomerEvent
    ) -> Optional[TouchpointType]:
        """Map a customer event to a touchpoint type."""
        mapping = {
            EventType.AD_CLICK: TouchpointType.PAID_SEARCH,
            EventType.AD_VIEW: TouchpointType.DISPLAY_AD,
            EventType.CAMPAIGN_CLICK: TouchpointType.PAID_SOCIAL,
            EventType.CAMPAIGN_VIEW: TouchpointType.PAID_SOCIAL,
            EventType.EMAIL_CLICK: TouchpointType.EMAIL,
            EventType.EMAIL_OPEN: TouchpointType.EMAIL,
            EventType.PAGE_VIEW: TouchpointType.ORGANIC_SEARCH,
            EventType.CLICK: TouchpointType.DIRECT,
            EventType.ORGANIC_SEARCH: TouchpointType.ORGANIC_SEARCH,
            EventType.SOCIAL_SHARE: TouchpointType.ORGANIC_SOCIAL,
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

    def _calculate_engagement_score(self, event: CustomerEvent) -> float:
        """Calculate an engagement score for a touchpoint (0-1)."""
        score = 0.5  # Base score

        properties = event.properties

        # Time on page
        time_on_page = properties.get("time_on_page", 0)
        if time_on_page:
            if time_on_page > 300:  # > 5 minutes
                score += 0.3
            elif time_on_page > 60:  # > 1 minute
                score += 0.2
            elif time_on_page > 10:  # > 10 seconds
                score += 0.1

        # Pages viewed
        pages_viewed = properties.get("pages_viewed", 1)
        if pages_viewed > 5:
            score += 0.2
        elif pages_viewed > 2:
            score += 0.1

        # Scroll depth
        scroll_depth = properties.get("scroll_depth", 0)
        if scroll_depth > 0.8:
            score += 0.1

        return min(score, 1.0)

    # ============== Manual Conversion Tracking ==============

    async def track_conversion(
        self,
        organization_id: str,
        customer_id: str = None,
        anonymous_id: str = None,
        conversion_type: ConversionType = ConversionType.CUSTOM,
        conversion_name: str = None,
        conversion_value: float = 0,
        currency: str = "USD",
        properties: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        timestamp: datetime = None,
        lookback_window_days: int = 30
    ) -> ConversionEvent:
        """
        Manually track a conversion.

        Args:
            organization_id: Organization ID.
            customer_id: Customer ID (if known).
            anonymous_id: Anonymous ID (if not identified).
            conversion_type: Type of conversion.
            conversion_name: Name of conversion.
            conversion_value: Conversion value.
            currency: Currency code.
            properties: Additional properties.
            context: Context data.
            timestamp: Conversion timestamp (default now).
            lookback_window_days: Days to look back for touchpoints.

        Returns:
            Created conversion event.
        """
        if not timestamp:
            timestamp = datetime.utcnow()

        if not conversion_name:
            conversion_name = conversion_type.value

        conversion = ConversionEvent(
            organization_id=organization_id,
            customer_id=customer_id,
            anonymous_id=anonymous_id,
            conversion_type=conversion_type,
            conversion_name=conversion_name,
            currency=currency,
            conversion_value=conversion_value,
            properties=properties or {},
            context=context or {},
            lookback_window_days=lookback_window_days,
            conversion_timestamp=timestamp,
            status=ConversionStatus.PENDING
        )

        self.db.add(conversion)
        await self.db.flush()

        # Create touchpoints if customer_id is available
        if customer_id:
            touchpoint_count = await self._create_touchpoints_for_conversion(
                conversion, lookback_window_days
            )
            logger.info(f"Created {touchpoint_count} touchpoints for manual conversion")

        return conversion

    # ============== Touchpoint Management ==============

    async def create_touchpoint(
        self,
        organization_id: str,
        customer_id: str = None,
        anonymous_id: str = None,
        touchpoint_type: TouchpointType = TouchpointType.CUSTOM,
        channel: str = "unknown",
        campaign_id: str = None,
        properties: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        cost: float = None,
        timestamp: datetime = None
    ) -> AttributionTouchpoint:
        """
        Manually create a touchpoint.

        Args:
            organization_id: Organization ID.
            customer_id: Customer ID.
            anonymous_id: Anonymous ID.
            touchpoint_type: Type of touchpoint.
            channel: Marketing channel.
            campaign_id: Campaign ID.
            properties: Additional properties.
            context: Context data.
            cost: Touchpoint cost.
            timestamp: Touchpoint timestamp.

        Returns:
            Created touchpoint.
        """
        if not timestamp:
            timestamp = datetime.utcnow()

        touchpoint = AttributionTouchpoint(
            organization_id=organization_id,
            customer_id=customer_id,
            anonymous_id=anonymous_id,
            touchpoint_type=touchpoint_type,
            channel=channel,
            campaign_id=campaign_id,
            properties=properties or {},
            context=context or {},
            cost=cost,
            touchpoint_timestamp=timestamp,
            status=TouchpointStatus.ACTIVE
        )

        self.db.add(touchpoint)
        await self.db.flush()

        return touchpoint

    # ============== Batch Processing ==============

    async def process_event_batch(
        self,
        events: List[CustomerEvent]
    ) -> List[ConversionTrackingResult]:
        """
        Process a batch of events for conversions.

        Args:
            events: List of customer events.

        Returns:
            List of tracking results.
        """
        results = []

        for event in events:
            try:
                conversion = await self.track_conversion_from_event(event)
                if conversion:
                    results.append(ConversionTrackingResult(
                        conversion_event_id=conversion.id,
                        touchpoint_count=conversion.attributed_touchpoint_count or 0,
                        status="success",
                        errors=[]
                    ))
            except Exception as e:
                logger.error(f"Error processing event {event.id}: {e}")
                results.append(ConversionTrackingResult(
                    conversion_event_id=None,
                    touchpoint_count=0,
                    status="error",
                    errors=[str(e)]
                ))

        return results

    # ============== Reporting ==============

    async def get_conversion_summary(
        self,
        organization_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get summary of conversions.

        Args:
            organization_id: Organization ID.
            start_date: Start date filter.
            end_date: End date filter.

        Returns:
            Conversion summary.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Total conversions
        query = select(func.count(ConversionEvent.id)).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.conversion_timestamp >= start_date,
                ConversionEvent.conversion_timestamp <= end_date
            )
        )
        result = await self.db.execute(query)
        total_conversions = result.scalar() or 0

        # Total value
        query = select(func.sum(ConversionEvent.conversion_value)).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.conversion_timestamp >= start_date,
                ConversionEvent.conversion_timestamp <= end_date
            )
        )
        result = await self.db.execute(query)
        total_value = result.scalar() or 0

        # By type
        query = select(
            ConversionEvent.conversion_type,
            func.count(ConversionEvent.id).label("count"),
            func.sum(ConversionEvent.conversion_value).label("total_value")
        ).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.conversion_timestamp >= start_date,
                ConversionEvent.conversion_timestamp <= end_date
            )
        ).group_by(ConversionEvent.conversion_type)

        result = await self.db.execute(query)
        rows = result.all()

        by_type = {
            row.conversion_type.value if row.conversion_type else "unknown": {
                "count": row.count,
                "total_value": float(row.total_value or 0)
            }
            for row in rows
        }

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_conversions": total_conversions,
                "total_value": float(total_value),
                "avg_value": float(total_value / total_conversions) if total_conversions > 0 else 0
            },
            "by_type": by_type
        }

    async def get_touchpoint_summary(
        self,
        organization_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get summary of touchpoints.

        Args:
            organization_id: Organization ID.
            start_date: Start date filter.
            end_date: End date filter.

        Returns:
            Touchpoint summary.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Total touchpoints
        query = select(func.count(AttributionTouchpoint.id)).where(
            and_(
                AttributionTouchpoint.organization_id == organization_id,
                AttributionTouchpoint.touchpoint_timestamp >= start_date,
                AttributionTouchpoint.touchpoint_timestamp <= end_date
            )
        )
        result = await self.db.execute(query)
        total_touchpoints = result.scalar() or 0

        # Total cost
        query = select(func.sum(AttributionTouchpoint.cost)).where(
            and_(
                AttributionTouchpoint.organization_id == organization_id,
                AttributionTouchpoint.touchpoint_timestamp >= start_date,
                AttributionTouchpoint.touchpoint_timestamp <= end_date
            )
        )
        result = await self.db.execute(query)
        total_cost = result.scalar() or 0

        # By channel
        query = select(
            AttributionTouchpoint.channel,
            func.count(AttributionTouchpoint.id).label("count"),
            func.sum(AttributionTouchpoint.cost).label("total_cost")
        ).where(
            and_(
                AttributionTouchpoint.organization_id == organization_id,
                AttributionTouchpoint.touchpoint_timestamp >= start_date,
                AttributionTouchpoint.touchpoint_timestamp <= end_date
            )
        ).group_by(AttributionTouchpoint.channel)

        result = await self.db.execute(query)
        rows = result.all()

        by_channel = {
            row.channel: {
                "count": row.count,
                "total_cost": float(row.total_cost or 0)
            }
            for row in rows
        }

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_touchpoints": total_touchpoints,
                "total_cost": float(total_cost)
            },
            "by_channel": by_channel
        }

    async def link_touchpoint_to_conversion(
        self,
        touchpoint_id: str,
        conversion_id: str
    ) -> bool:
        """
        Link an existing touchpoint to a conversion.

        Args:
            touchpoint_id: Touchpoint ID.
            conversion_id: Conversion event ID.

        Returns:
            True if successful.
        """
        query = select(AttributionTouchpoint).where(
            AttributionTouchpoint.id == touchpoint_id
        )
        result = await self.db.execute(query)
        touchpoint = result.scalar_one_or_none()

        if not touchpoint:
            return False

        query = select(ConversionEvent).where(
            ConversionEvent.id == conversion_id
        )
        result = await self.db.execute(query)
        conversion = result.scalar_one_or_none()

        if not conversion:
            return False

        touchpoint.conversion_event_id = conversion_id
        touchpoint.time_to_conversion_hours = (
            conversion.conversion_timestamp - touchpoint.touchpoint_timestamp
        ).total_seconds() / 3600

        await self.db.commit()
        return True

    async def update_conversion_value(
        self,
        conversion_id: str,
        new_value: float
    ) -> bool:
        """
        Update the value of a conversion.

        Args:
            conversion_id: Conversion event ID.
            new_value: New conversion value.

        Returns:
            True if successful.
        """
        query = select(ConversionEvent).where(
            ConversionEvent.id == conversion_id
        )
        result = await self.db.execute(query)
        conversion = result.scalar_one_or_none()

        if not conversion:
            return False

        conversion.conversion_value = new_value
        await self.db.commit()

        # Re-process attribution if already attributed
        if conversion.status == ConversionStatus.ATTRIBUTED:
            conversion.status = ConversionStatus.PENDING
            await self.db.commit()

        return True

    async def exclude_touchpoint(
        self,
        touchpoint_id: str,
        reason: str = None
    ) -> bool:
        """
        Exclude a touchpoint from attribution.

        Args:
            touchpoint_id: Touchpoint ID.
            reason: Reason for exclusion.

        Returns:
            True if successful.
        """
        query = select(AttributionTouchpoint).where(
            AttributionTouchpoint.id == touchpoint_id
        )
        result = await self.db.execute(query)
        touchpoint = result.scalar_one_or_none()

        if not touchpoint:
            return False

        touchpoint.status = TouchpointStatus.EXCLUDED
        if reason:
            touchpoint.properties["exclusion_reason"] = reason

        await self.db.commit()
        return True

    async def get_customer_journey(
        self,
        organization_id: str,
        customer_id: str = None,
        anonymous_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get the complete customer journey.

        Args:
            organization_id: Organization ID.
            customer_id: Customer ID.
            anonymous_id: Anonymous ID.
            start_date: Start date filter.
            end_date: End date filter.

        Returns:
            Customer journey data.
        """
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=90)

        # Build filter
        filters = [
            AttributionTouchpoint.organization_id == organization_id,
            AttributionTouchpoint.touchpoint_timestamp >= start_date,
            AttributionTouchpoint.touchpoint_timestamp <= end_date
        ]

        if customer_id:
            filters.append(AttributionTouchpoint.customer_id == customer_id)
        elif anonymous_id:
            filters.append(AttributionTouchpoint.anonymous_id == anonymous_id)
        else:
            return {"error": "Either customer_id or anonymous_id required"}

        query = select(AttributionTouchpoint).where(
            and_(*filters)
        ).order_by(AttributionTouchpoint.touchpoint_timestamp)

        result = await self.db.execute(query)
        touchpoints = result.scalars().all()

        # Get associated conversions
        conversion_ids = [tp.conversion_event_id for tp in touchpoints if tp.conversion_event_id]
        conversions = []

        if conversion_ids:
            query = select(ConversionEvent).where(
                ConversionEvent.id.in_(conversion_ids)
            )
            result = await self.db.execute(query)
            conversions = result.scalars().all()

        conversion_map = {c.id: c for c in conversions}

        journey = []
        for tp in touchpoints:
            entry = {
                "type": "touchpoint",
                "id": tp.id,
                "timestamp": tp.touchpoint_timestamp.isoformat(),
                "channel": tp.channel,
                "touchpoint_type": tp.touchpoint_type.value if tp.touchpoint_type else None,
                "campaign_name": tp.campaign_name,
                "engagement_score": tp.engagement_score,
                "cost": tp.cost
            }

            if tp.conversion_event_id and tp.conversion_event_id in conversion_map:
                conv = conversion_map[tp.conversion_event_id]
                entry["conversion"] = {
                    "id": conv.id,
                    "type": conv.conversion_type.value if conv.conversion_type else None,
                    "value": conv.conversion_value
                }

            journey.append(entry)

        return {
            "customer_id": customer_id,
            "anonymous_id": anonymous_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "touchpoint_count": len(touchpoints),
            "conversion_count": len(conversions),
            "journey": journey
        }

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
        # Update touchpoints
        query = select(AttributionTouchpoint).where(
            and_(
                AttributionTouchpoint.organization_id == organization_id,
                AttributionTouchpoint.anonymous_id == anonymous_id
            )
        )
        result = await self.db.execute(query)
        touchpoints = result.scalars().all()

        touchpoint_count = 0
        for tp in touchpoints:
            tp.customer_id = customer_id
            touchpoint_count += 1

        # Update conversions
        query = select(ConversionEvent).where(
            and_(
                ConversionEvent.organization_id == organization_id,
                ConversionEvent.anonymous_id == anonymous_id
            )
        )
        result = await self.db.execute(query)
        conversions = result.scalars().all()

        conversion_count = 0
        for conv in conversions:
            conv.customer_id = customer_id
            conversion_count += 1

        await self.db.commit()

        logger.info(
            f"Merged {touchpoint_count} touchpoints and {conversion_count} conversions "
            f"from anonymous_id {anonymous_id} to customer {customer_id}"
        )

        return {
            "anonymous_id": anonymous_id,
            "customer_id": customer_id,
            "touchpoints_merged": touchpoint_count,
            "conversions_merged": conversion_count
        }