"""
Event Ingestion Service for the Customer Data Platform.

Handles multiple ingestion channels including HTTP API, webhooks,
queue processing, and real-time streaming.
"""
import logging
import hashlib
import hmac
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...models.customer_event import CustomerEvent
from ...models.customer import Customer
from .event_processor import EventProcessor, ValidationResult

logger = logging.getLogger(__name__)


class EventIngestionService:
    """
    Event ingestion endpoints and queue handling.

    Supports multiple ingestion channels:
    - HTTP API (direct)
    - Webhook (third-party integrations)
    - Queue processing (async batch processing)
    - Real-time streaming (WebSocket)
    """

    def __init__(self, db: AsyncSession):
        """Initialize the event ingestion service.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db
        self.event_processor = EventProcessor(db)

    # ============== HTTP Ingestion ==============

    async def ingest_http(
        self,
        event_data: Dict[str, Any],
        headers: Dict[str, str],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingest event via HTTP API.

        Args:
            event_data: Event data from HTTP request.
            headers: HTTP headers.
            api_key: API key for authentication.

        Returns:
            Ingestion result with event ID and status.
        """
        # Extract organization from headers or API key
        organization_id = self._extract_organization(headers, api_key)

        if not organization_id:
            raise ValueError("Organization ID required (provide via header or API key)")

        # Add metadata from headers
        event_data = self._enrich_from_headers(event_data, headers)

        # Process event
        try:
            event, customer = await self.event_processor.ingest_event(
                event_data, organization_id
            )

            return {
                "success": True,
                "event_id": event.id,
                "customer_id": customer.id if customer else None,
                "anonymous_id": event.anonymous_id,
                "received_at": event.received_at.isoformat(),
                "message": "Event processed successfully"
            }

        except ValueError as e:
            logger.warning(f"Event validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation_error"
            }
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            return {
                "success": False,
                "error": "Internal processing error",
                "error_type": "processing_error"
            }

    async def ingest_batch_http(
        self,
        events: List[Dict[str, Any]],
        headers: Dict[str, str],
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingest batch of events via HTTP API.

        Args:
            events: List of event data.
            headers: HTTP headers.
            api_key: API key for authentication.

        Returns:
            Batch ingestion results.
        """
        organization_id = self._extract_organization(headers, api_key)

        if not organization_id:
            raise ValueError("Organization ID required")

        results = await self.event_processor.process_batch(events, organization_id)

        return {
            "success": results["failed"] == 0,
            "batch_size": len(events),
            "processed": results["processed"],
            "failed": results["failed"],
            "customers_resolved": results["customers_resolved"],
            "errors": results["errors"]
        }

    def _extract_organization(
        self,
        headers: Dict[str, str],
        api_key: Optional[str] = None
    ) -> Optional[str]:
        """Extract organization ID from headers or API key."""
        # Check header first
        org_header = headers.get("X-Organization-ID") or headers.get("x-organization-id")
        if org_header:
            return org_header

        # TODO: Lookup organization from API key
        if api_key:
            # This would typically query a database
            pass

        return None

    def _enrich_from_headers(
        self,
        event_data: Dict[str, Any],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Enrich event data from HTTP headers."""
        enriched = dict(event_data)

        # Initialize context if not present
        if "context" not in enriched:
            enriched["context"] = {}

        # Extract user agent
        user_agent = headers.get("User-Agent") or headers.get("user-agent")
        if user_agent:
            enriched["context"]["user_agent"] = user_agent
            enriched["context"]["device"] = self._parse_user_agent(user_agent)

        # Extract IP
        ip = headers.get("X-Forwarded-For") or headers.get("X-Real-IP") or headers.get("Remote-Addr")
        if ip:
            enriched["context"]["ip"] = ip.split(",")[0].strip() if "," in ip else ip

        # Extract referrer
        referrer = headers.get("Referer") or headers.get("Referrer")
        if referrer:
            enriched["context"]["page"] = enriched["context"].get("page", {})
            enriched["context"]["page"]["referrer"] = referrer

        # Extract library info
        lib_version = headers.get("X-Lib-Version")
        if lib_version:
            enriched["context"]["library"] = {
                "version": lib_version,
                "name": headers.get("X-Lib-Name", "unknown")
            }

        return enriched

    def _parse_user_agent(self, user_agent: str) -> Dict[str, str]:
        """Parse user agent string for device info."""
        device = {"type": "unknown", "os": "unknown", "browser": "unknown"}

        ua_lower = user_agent.lower()

        # Device type
        if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
            device["type"] = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device["type"] = "tablet"
        else:
            device["type"] = "desktop"

        # OS
        if "windows" in ua_lower:
            device["os"] = "Windows"
        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            device["os"] = "macOS"
        elif "linux" in ua_lower:
            device["os"] = "Linux"
        elif "android" in ua_lower:
            device["os"] = "Android"
        elif "iphone" in ua_lower or "ipad" in ua_lower:
            device["os"] = "iOS"

        # Browser
        if "chrome" in ua_lower:
            device["browser"] = "Chrome"
        elif "firefox" in ua_lower:
            device["browser"] = "Firefox"
        elif "safari" in ua_lower:
            device["browser"] = "Safari"
        elif "edge" in ua_lower:
            device["browser"] = "Edge"

        return device

    # ============== Webhook Ingestion ==============

    async def ingest_webhook(
        self,
        source: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingest event from webhook.

        Args:
            source: Webhook source (e.g., 'stripe', 'shopify').
            payload: Webhook payload.
            signature: Webhook signature for verification.
            secret: Webhook secret for signature verification.

        Returns:
            Ingestion result.
        """
        # Verify signature if provided
        if signature and secret:
            if not self._verify_webhook_signature(payload, signature, secret):
                raise ValueError("Invalid webhook signature")

        # Transform webhook payload to standard event format
        event_data = self._transform_webhook_payload(source, payload)

        # Process event
        return await self.ingest_http(event_data, {}, None)

    def _verify_webhook_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature."""
        try:
            payload_bytes = json.dumps(payload, sort_keys=True).encode()
            expected = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def _transform_webhook_payload(
        self,
        source: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform webhook payload to standard event format."""
        transformers = {
            "stripe": self._transform_stripe_webhook,
            "shopify": self._transform_shopify_webhook,
            "hubspot": self._transform_hubspot_webhook,
        }

        transformer = transformers.get(source.lower())
        if transformer:
            return transformer(payload)

        # Default: wrap payload as custom event
        return {
            "event_name": f"{source}.webhook",
            "event_type": "custom",
            "properties": payload,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _transform_stripe_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Stripe webhook to event."""
        event_type = payload.get("type", "stripe.unknown")
        data = payload.get("data", {}).get("object", {})

        event_name = event_type.replace(".", "_")

        return {
            "event_name": event_name,
            "event_type": "purchase" if "payment" in event_type else "custom",
            "properties": {
                "stripe_event_id": payload.get("id"),
                "stripe_data": data,
                "external_ids": {
                    "stripe_id": data.get("customer")
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def _transform_shopify_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Shopify webhook to event."""
        topic = payload.get("topic", "shopify/unknown")

        return {
            "event_name": topic.replace("/", "_"),
            "event_type": "purchase" if "order" in topic else "custom",
            "properties": {
                "shopify_data": payload,
                "external_ids": {
                    "shopify_id": payload.get("customer", {}).get("id")
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    def _transform_hubspot_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot webhook to event."""
        return {
            "event_name": "hubspot_contact_update",
            "event_type": "profile_update",
            "properties": {
                "hubspot_data": payload,
                "external_ids": {
                    "hubspot_id": payload.get("vid")
                },
                "traits": payload.get("properties", {})
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    # ============== Queue Processing ==============

    async def process_event_queue(
        self,
        event_ids: List[str]
    ) -> Dict[str, Any]:
        """Process events from queue (Celery task handler).

        Args:
            event_ids: List of event IDs to process.

        Returns:
            Processing results.
        """
        results = {
            "processed": 0,
            "failed": 0,
            "errors": []
        }

        for event_id in event_ids:
            try:
                # Fetch event from database
                result = await self.db.execute(
                    select(CustomerEvent).where(CustomerEvent.id == event_id)
                )
                event = result.scalar_one_or_none()

                if not event:
                    results["errors"].append({
                        "event_id": event_id,
                        "error": "Event not found"
                    })
                    results["failed"] += 1
                    continue

                # Re-process for identity resolution if needed
                if not event.customer_id and event.anonymous_id:
                    await self.event_processor.resolve_identity(event)

                results["processed"] += 1

            except Exception as e:
                logger.error(f"Failed to process queued event {event_id}: {e}")
                results["errors"].append({
                    "event_id": event_id,
                    "error": str(e)
                })
                results["failed"] += 1

        return results

    # ============== Real-time Streaming ==============

    async def stream_events(
        self,
        organization_id: str,
        filters: Optional[Dict[str, Any]] = None
    ):
        """Stream events in real-time (WebSocket handler).

        Args:
            organization_id: Organization to stream events for.
            filters: Optional filters (event_types, customer_id, etc.).

        Yields:
            Event data dictionaries.
        """
        filters = filters or {}

        # Build query
        query = select(CustomerEvent).where(
            and_(
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.timestamp > datetime.utcnow()
            )
        )

        # Apply filters
        if filters.get("event_types"):
            query = query.where(
                CustomerEvent.event_type.in_(filters["event_types"])
            )

        if filters.get("customer_id"):
            query = query.where(
                CustomerEvent.customer_id == filters["customer_id"]
            )

        if filters.get("event_name"):
            query = query.where(
                CustomerEvent.event_name == filters["event_name"]
            )

        # This is a placeholder - real implementation would use
        # database triggers, Redis pub/sub, or Kafka for real-time streaming
        logger.info(f"Event streaming initialized for org {organization_id}")

        # Yield existing recent events first
        result = await self.db.execute(
            query.order_by(CustomerEvent.timestamp.desc()).limit(100)
        )
        events = result.scalars().all()

        for event in reversed(events):  # Oldest first
            yield event.to_dict()

    # ============== Anonymous ID Management ==============

    async def alias_anonymous_id(
        self,
        anonymous_id: str,
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """Alias anonymous ID to identified user.

        Args:
            anonymous_id: Anonymous ID to alias.
            user_id: Identified user ID.
            organization_id: Organization ID.

        Returns:
            Aliasing result.
        """
        # Find customer by user_id
        result = await self.db.execute(
            select(Customer).where(
                and_(
                    Customer.id == user_id,
                    Customer.organization_id == organization_id
                )
            )
        )
        customer = result.scalar_one_or_none()

        if not customer:
            return {
                "success": False,
                "error": f"Customer {user_id} not found"
            }

        # Update events with this anonymous_id
        events_result = await self.db.execute(
            select(CustomerEvent).where(
                and_(
                    CustomerEvent.anonymous_id == anonymous_id,
                    CustomerEvent.organization_id == organization_id,
                    CustomerEvent.customer_id.is_(None)
                )
            )
        )
        events = events_result.scalars().all()

        for event in events:
            event.customer_id = customer.id

        # Store anonymous_id on customer for future reference
        if not customer.anonymous_id:
            customer.anonymous_id = anonymous_id

        await self.db.commit()

        return {
            "success": True,
            "aliased_events": len(events),
            "customer_id": customer.id,
            "anonymous_id": anonymous_id
        }