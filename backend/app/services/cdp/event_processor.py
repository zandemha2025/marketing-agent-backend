"""
Event Processing Service for the Customer Data Platform.

Handles real-time event ingestion, validation, identity resolution,
and profile enrichment from customer behavioral events.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ...models.customer import Customer
from ...models.customer_event import CustomerEvent, EventType, EventSource
from .identity_resolver import IdentityResolver

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of event validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    normalized_event: Optional[Dict[str, Any]] = None


class EventProcessor:
    """
    Real-time event processing service.

    Handles event ingestion, validation, identity resolution,
    and profile enrichment from customer behavioral events.
    """

    # Required fields for all events
    REQUIRED_FIELDS = ["event_name", "timestamp"]

    # Optional but recommended fields
    RECOMMENDED_FIELDS = ["organization_id", "properties", "context"]

    # Maximum event size in bytes (1MB)
    MAX_EVENT_SIZE = 1024 * 1024

    # Maximum properties depth
    MAX_PROPERTIES_DEPTH = 10

    def __init__(self, db: AsyncSession):
        """Initialize the event processor.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db
        self.identity_resolver = IdentityResolver(db)

    # ============== Event Ingestion ==============

    async def ingest_event(
        self,
        event_data: Dict[str, Any],
        organization_id: Optional[str] = None
    ) -> Tuple[CustomerEvent, Optional[Customer]]:
        """Ingest and process a single event.

        Args:
            event_data: Raw event data.
            organization_id: Optional organization ID (can be in event_data).

        Returns:
            Tuple of (processed_event, resolved_customer).
        """
        # Validate event
        validation = self.validate_event(event_data)
        if not validation.is_valid:
            raise ValueError(f"Event validation failed: {', '.join(validation.errors)}")

        event_data = validation.normalized_event or event_data

        # Resolve organization
        org_id = organization_id or event_data.get("organization_id")
        if not org_id:
            raise ValueError("organization_id is required")

        # Resolve identity
        customer, anonymous_id = await self.identity_resolver.resolve_identity_from_event(
            event_data, org_id
        )

        # Create event record
        event = await self._create_event_record(
            event_data=event_data,
            organization_id=org_id,
            customer_id=customer.id if customer else None,
            anonymous_id=anonymous_id
        )

        # Enrich profile if customer found
        if customer:
            await self.enrich_profile(customer.id, event)

        return event, customer

    async def _create_event_record(
        self,
        event_data: Dict[str, Any],
        organization_id: str,
        customer_id: Optional[str],
        anonymous_id: Optional[str]
    ) -> CustomerEvent:
        """Create a CustomerEvent record from event data."""
        # Parse timestamp
        timestamp = self._parse_timestamp(event_data.get("timestamp"))
        sent_at = self._parse_timestamp(event_data.get("sent_at"))

        # Determine event type
        event_type = self._determine_event_type(
            event_data.get("event_type"),
            event_data.get("event_name")
        )

        # Create event
        event = CustomerEvent(
            organization_id=organization_id,
            workspace_id=event_data.get("workspace_id"),
            customer_id=customer_id,
            anonymous_id=anonymous_id,
            event_type=event_type,
            event_name=event_data.get("event_name", "Unknown"),
            properties=event_data.get("properties", {}),
            context=event_data.get("context", {}),
            source=self._determine_event_source(event_data.get("source", "web")),
            timestamp=timestamp,
            sent_at=sent_at,
            integration_id=event_data.get("integration_id"),
            api_key_id=event_data.get("api_key_id"),
            consent_context=event_data.get("consent", {})
        )

        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        logger.debug(f"Created event {event.id}: {event.event_name}")
        return event

    # ============== Event Validation ==============

    def validate_event(self, event: Dict[str, Any]) -> ValidationResult:
        """Validate event data.

        Args:
            event: Raw event data.

        Returns:
            ValidationResult with validation status and errors.
        """
        errors = []
        warnings = []
        normalized = dict(event)  # Copy for normalization

        # Check event size
        event_size = len(json.dumps(event))
        if event_size > self.MAX_EVENT_SIZE:
            errors.append(f"Event size ({event_size} bytes) exceeds maximum ({self.MAX_EVENT_SIZE} bytes)")

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in event or event[field] is None:
                errors.append(f"Missing required field: {field}")

        # Check event name
        if event.get("event_name"):
            if len(event["event_name"]) > 100:
                errors.append("event_name exceeds 100 characters")
            normalized["event_name"] = event["event_name"].strip()

        # Validate timestamp
        if "timestamp" in event:
            try:
                self._parse_timestamp(event["timestamp"])
            except (ValueError, TypeError) as e:
                errors.append(f"Invalid timestamp: {e}")

        # Validate properties
        if "properties" in event:
            props = event["properties"]
            if not isinstance(props, dict):
                errors.append("properties must be an object")
            else:
                depth = self._get_dict_depth(props)
                if depth > self.MAX_PROPERTIES_DEPTH:
                    errors.append(f"properties depth ({depth}) exceeds maximum ({self.MAX_PROPERTIES_DEPTH})")

                # Check property values
                for key, value in props.items():
                    if len(key) > 255:
                        errors.append(f"Property key '{key[:50]}...' exceeds 255 characters")
                    if isinstance(value, (list, dict)) and len(json.dumps(value)) > 10000:
                        warnings.append(f"Property '{key}' is very large and may impact performance")

        # Validate context
        if "context" in event:
            ctx = event["context"]
            if not isinstance(ctx, dict):
                errors.append("context must be an object")

        # Check for PII in properties (basic check)
        pii_warnings = self._check_pii(event)
        warnings.extend(pii_warnings)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            normalized_event=normalized if len(errors) == 0 else None
        )

    def _check_pii(self, event: Dict[str, Any]) -> List[str]:
        """Check for potential PII in event data."""
        warnings = []
        pii_patterns = ["ssn", "password", "credit_card", "cvv", "ssn"]

        def check_dict(d: Dict, path: str = ""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                key_lower = key.lower()

                for pattern in pii_patterns:
                    if pattern in key_lower:
                        warnings.append(f"Potential PII detected in field: {current_path}")

                if isinstance(value, dict):
                    check_dict(value, current_path)

        if "properties" in event:
            check_dict(event["properties"], "properties")
        if "context" in event:
            check_dict(event["context"], "context")

        return warnings

    # ============== Identity Resolution on Events ==============

    async def resolve_identity(
        self,
        event: CustomerEvent
    ) -> Optional[str]:
        """Resolve customer identity from an event.

        Args:
            event: CustomerEvent to resolve identity for.

        Returns:
            Customer ID if resolved, None otherwise.
        """
        event_data = {
            "customer_id": event.customer_id,
            "anonymous_id": event.anonymous_id,
            "external_ids": event.properties.get("external_ids", {}),
            "email": event.properties.get("email"),
            "traits": event.properties.get("traits", {}),
            "context": event.context
        }

        customer, _ = await self.identity_resolver.resolve_identity_from_event(
            event_data, event.organization_id
        )

        if customer:
            # Update event with resolved customer
            event.customer_id = customer.id
            await self.db.commit()
            return customer.id

        return None

    # ============== Profile Enrichment from Events ==============

    async def enrich_profile(
        self,
        customer_id: str,
        event: CustomerEvent
    ):
        """Enrich customer profile from event data.

        Args:
            customer_id: Customer ID to enrich.
            event: Event containing enrichment data.
        """
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            logger.warning(f"Cannot enrich profile: customer {customer_id} not found")
            return

        # Update last seen
        customer.update_last_seen(event.timestamp)

        # Extract traits from event
        if event.properties:
            traits = event.properties.get("traits", {})
            if traits:
                current_traits = customer.traits or {}
                current_traits.update(traits)
                customer.traits = current_traits

        # Update computed traits based on event type
        await self._update_computed_traits(customer, event)

        await self.db.commit()

    async def _update_computed_traits(self, customer: Customer, event: CustomerEvent):
        """Update computed traits based on event."""
        computed = customer.computed_traits or {}

        # Event count
        event_count = computed.get("total_events", 0) + 1
        computed["total_events"] = event_count

        # Event type counts
        event_type_counts = computed.get("event_type_counts", {})
        event_type_key = event.event_type.value if event.event_type else "unknown"
        event_type_counts[event_type_key] = event_type_counts.get(event_type_key, 0) + 1
        computed["event_type_counts"] = event_type_counts

        # First/last event timestamps
        if "first_event_at" not in computed:
            computed["first_event_at"] = event.timestamp.isoformat()
        computed["last_event_at"] = event.timestamp.isoformat()

        # Purchase tracking
        if event.event_type == EventType.PURCHASE:
            purchase_count = computed.get("purchase_count", 0) + 1
            computed["purchase_count"] = purchase_count

            # Update lifetime value
            purchase_value = event.properties.get("total", event.properties.get("value", 0))
            computed["total_purchase_value"] = computed.get("total_purchase_value", 0) + purchase_value

        # Page view tracking
        if event.event_type == EventType.PAGE_VIEW:
            page_views = computed.get("page_view_count", 0) + 1
            computed["page_view_count"] = page_views

            # Track unique pages
            page_url = event.context.get("page", {}).get("url") if event.context else None
            if page_url:
                unique_pages = set(computed.get("unique_pages_viewed", []))
                unique_pages.add(page_url)
                computed["unique_pages_viewed"] = list(unique_pages)

        customer.computed_traits = computed

    # ============== Event Transformation ==============

    def transform_event(
        self,
        event: Dict[str, Any],
        mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Transform event using field mapping.

        Args:
            event: Raw event data.
            mapping: Field mapping (source_field -> target_field).

        Returns:
            Transformed event data.
        """
        transformed = {}

        for source_field, target_field in mapping.items():
            value = self._get_nested_value(event, source_field)
            if value is not None:
                self._set_nested_value(transformed, target_field, value)

        # Copy unmapped fields
        for key, value in event.items():
            if key not in mapping:
                transformed[key] = value

        return transformed

    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _set_nested_value(self, data: Dict, path: str, value: Any):
        """Set value in nested dictionary using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    # ============== Batch Processing ==============

    async def process_batch(
        self,
        events: List[Dict[str, Any]],
        organization_id: str
    ) -> Dict[str, Any]:
        """Process a batch of events.

        Args:
            events: List of event data dictionaries.
            organization_id: Organization ID for all events.

        Returns:
            Processing results summary.
        """
        results = {
            "processed": 0,
            "failed": 0,
            "customers_resolved": 0,
            "errors": []
        }

        for i, event_data in enumerate(events):
            try:
                # Add organization_id if not present
                if "organization_id" not in event_data:
                    event_data["organization_id"] = organization_id

                event, customer = await self.ingest_event(event_data)
                results["processed"] += 1

                if customer:
                    results["customers_resolved"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "index": i,
                    "error": str(e),
                    "event_name": event_data.get("event_name", "unknown")
                })
                logger.error(f"Failed to process event {i}: {e}")

        return results

    # ============== Helper Methods ==============

    def _parse_timestamp(self, timestamp: Any) -> datetime:
        """Parse timestamp from various formats."""
        if timestamp is None:
            return datetime.utcnow()

        if isinstance(timestamp, datetime):
            return timestamp

        if isinstance(timestamp, (int, float)):
            # Assume milliseconds if > year 2000 in seconds
            if timestamp > 946684800000:  # 2000-01-01 in milliseconds
                timestamp = timestamp / 1000
            return datetime.utcfromtimestamp(timestamp)

        if isinstance(timestamp, str):
            # Try ISO format
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                pass

            # Try common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp, fmt)
                except ValueError:
                    continue

        raise ValueError(f"Unable to parse timestamp: {timestamp}")

    def _determine_event_type(
        self,
        event_type: Optional[str],
        event_name: Optional[str]
    ) -> EventType:
        """Determine event type from type or name."""
        if event_type:
            try:
                return EventType(event_type.lower())
            except ValueError:
                pass

        # Infer from event name
        if event_name:
            name_lower = event_name.lower()
            mapping = {
                "page view": EventType.PAGE_VIEW,
                "pageview": EventType.PAGE_VIEW,
                "screen view": EventType.PAGE_VIEW,
                "purchase": EventType.PURCHASE,
                "order completed": EventType.PURCHASE,
                "checkout": EventType.BEGIN_CHECKOUT,
                "add to cart": EventType.ADD_TO_CART,
                "sign up": EventType.SIGN_UP,
                "signup": EventType.SIGN_UP,
                "login": EventType.LOGIN,
                "click": EventType.CLICK,
                "form submit": EventType.FORM_SUBMIT,
                "email open": EventType.EMAIL_OPEN,
                "email click": EventType.EMAIL_CLICK,
            }
            for pattern, etype in mapping.items():
                if pattern in name_lower:
                    return etype

        return EventType.CUSTOM

    def _determine_event_source(self, source: str) -> EventSource:
        """Determine event source from string."""
        try:
            return EventSource(source.lower())
        except ValueError:
            return EventSource.WEB

    def _get_dict_depth(self, d: Dict, level: int = 1) -> int:
        """Calculate maximum depth of nested dictionary."""
        if not isinstance(d, dict) or not d:
            return level
        return max(
            self._get_dict_depth(v, level + 1) if isinstance(v, dict) else level
            for v in d.values()
        )