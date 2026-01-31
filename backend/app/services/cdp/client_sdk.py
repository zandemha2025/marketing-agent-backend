"""
Client SDK Service for the Customer Data Platform.

Provides server-side support for client-side tracking including
JavaScript snippet generation, event validation, and anonymous ID management.
"""
import logging
import json
import hashlib
import secrets
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...models.customer import Customer
from ...models.customer_event import CustomerEvent
from ...models.customer_identity import CustomerIdentity, IdentityType
from .event_processor import EventProcessor

logger = logging.getLogger(__name__)


class ClientSDK:
    """
    Server-side handler for client-side tracking.

    Manages client SDK configuration, event validation,
    and anonymous ID aliasing.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the client SDK service.

        Args:
            db: SQLAlchemy async session for database operations.
        """
        self.db = db
        self.event_processor = EventProcessor(db)

    # ============== JavaScript Snippet Generation ==============

    def generate_snippet(
        self,
        organization_id: str,
        workspace_id: Optional[str] = None,
        api_host: str = "https://api.example.com",
        cdn_host: str = "https://cdn.example.com",
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate JavaScript snippet for client tracking.

        Args:
            organization_id: Organization ID.
            workspace_id: Optional workspace ID.
            api_host: API host URL.
            cdn_host: CDN host URL.
            options: Additional configuration options.

        Returns:
            JavaScript snippet as string.
        """
        options = options or {}

        config = {
            "organizationId": organization_id,
            "workspaceId": workspace_id,
            "apiHost": api_host,
            "cdnHost": cdn_host,
            "debug": options.get("debug", False),
            "trackPageView": options.get("track_page_view", True),
            "trackClicks": options.get("track_clicks", False),
            "trackForms": options.get("track_forms", True),
            "cookieDomain": options.get("cookie_domain"),
            "cookieExpiryDays": options.get("cookie_expiry_days", 365),
        }

        snippet = f"""
<!-- Marketing Agent CDP Tracking -->
<script>
(function() {{
  'use strict';

  // Configuration
  var CONFIG = {json.dumps(config, indent=2)};

  // Initialize analytics object
  window.marketingAgent = window.marketingAgent || [];
  window.marketingAgent.methods = [
    'track', 'identify', 'page', 'alias', 'group',
    'ready', 'reset', 'debug', 'on', 'off'
  ];

  // Factory method
  window.marketingAgent.factory = function(method) {{
    return function() {{
      var args = Array.prototype.slice.call(arguments);
      args.unshift(method);
      window.marketingAgent.push(args);
      return window.marketingAgent;
    }};
  }};

  // Attach methods
  for (var i = 0; i < window.marketingAgent.methods.length; i++) {{
    var method = window.marketingAgent.methods[i];
    window.marketingAgent[method] = window.marketingAgent.factory(method);
  }}

  // Load the SDK
  var script = document.createElement('script');
  script.type = 'text/javascript';
  script.async = true;
  script.src = CONFIG.cdnHost + '/js/cdp-sdk.min.js';

  var firstScript = document.getElementsByTagName('script')[0];
  firstScript.parentNode.insertBefore(script, firstScript);

  // Initialize when ready
  window.marketingAgent.ready(function() {{
    window.marketingAgent.init(CONFIG);
  }});
}})();
</script>
<!-- End Marketing Agent CDP Tracking -->
"""
        return snippet.strip()

    def generate_npm_config(
        self,
        organization_id: str,
        workspace_id: Optional[str] = None,
        api_host: str = "https://api.example.com"
    ) -> Dict[str, Any]:
        """Generate configuration for NPM package usage.

        Args:
            organization_id: Organization ID.
            workspace_id: Optional workspace ID.
            api_host: API host URL.

        Returns:
            Configuration dictionary.
        """
        return {
            "organizationId": organization_id,
            "workspaceId": workspace_id,
            "apiHost": api_host,
            "flushAt": 20,  # Events to batch before sending
            "flushInterval": 10000,  # Milliseconds
        }

    # ============== Client Event Validation ==============

    def validate_client_event(
        self,
        event: Dict[str, Any],
        api_key: str,
        origin: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate event from client SDK.

        Args:
            event: Event data from client.
            api_key: API key for validation.
            origin: Request origin for CORS validation.

        Returns:
            Validation result with status and errors.
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check required fields
        if not event.get("event_name"):
            result["errors"].append("event_name is required")

        if not event.get("timestamp"):
            result["errors"].append("timestamp is required")

        # Validate timestamp format
        if event.get("timestamp"):
            try:
                ts = event["timestamp"]
                if isinstance(ts, (int, float)):
                    # Assume milliseconds if large number
                    if ts > 946684800000:  # Year 2000 in ms
                        ts = ts / 1000
                    datetime.utcfromtimestamp(ts)
                elif isinstance(ts, str):
                    datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                result["errors"].append("Invalid timestamp format")

        # Validate properties size
        if event.get("properties"):
            props_size = len(json.dumps(event["properties"]))
            if props_size > 100000:  # 100KB limit
                result["errors"].append("Properties exceed 100KB limit")
            elif props_size > 50000:
                result["warnings"].append("Properties are large (>50KB)")

        # Check for required context fields
        if not event.get("context"):
            result["warnings"].append("context is recommended for better tracking")

        # Validate anonymous_id or user_id
        if not event.get("anonymous_id") and not event.get("customer_id"):
            result["errors"].append("Either anonymous_id or customer_id is required")

        result["valid"] = len(result["errors"]) == 0
        return result

    async def process_client_batch(
        self,
        events: List[Dict[str, Any]],
        context: Dict[str, Any],
        organization_id: str
    ) -> Dict[str, Any]:
        """Process batch of events from client SDK.

        Args:
            events: List of event data.
            context: Shared context for all events.
            organization_id: Organization ID.

        Returns:
            Batch processing results.
        """
        results = {
            "sent": len(events),
            "success": 0,
            "failed": 0,
            "errors": []
        }

        for i, event in enumerate(events):
            try:
                # Merge shared context
                event["context"] = {**context, **event.get("context", {})}
                event["organization_id"] = organization_id

                # Process event
                processed_event, customer = await self.event_processor.ingest_event(event)
                results["success"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "index": i,
                    "error": str(e),
                    "event_name": event.get("event_name", "unknown")
                })
                logger.error(f"Failed to process client event {i}: {e}")

        return results

    # ============== Anonymous ID Management ==============

    def generate_anonymous_id(self) -> str:
        """Generate a new anonymous ID.

        Returns:
            New anonymous ID string.
        """
        return f"anon_{uuid4().hex}_{secrets.token_hex(8)}"

    async def alias_anonymous_id(
        self,
        anonymous_id: str,
        user_id: str,
        organization_id: str,
        traits: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Alias anonymous ID to identified user.

        Args:
            anonymous_id: Anonymous ID to alias.
            user_id: Identified user ID.
            organization_id: Organization ID.
            traits: Optional traits to update.

        Returns:
            Aliasing result.
        """
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
                "error": "Customer not found"
            }

        # Update anonymous events
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

        # Update customer
        if not customer.anonymous_id:
            customer.anonymous_id = anonymous_id

        if traits:
            current_traits = customer.traits or {}
            current_traits.update(traits)
            customer.traits = current_traits

        await self.db.commit()

        return {
            "success": True,
            "aliased_events": len(events),
            "customer_id": customer.id,
            "anonymous_id": anonymous_id
        }

    async def merge_anonymous_profile(
        self,
        anonymous_id: str,
        customer_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """Merge anonymous profile into identified customer.

        Args:
            anonymous_id: Anonymous ID to merge.
            customer_id: Target customer ID.
            organization_id: Organization ID.

        Returns:
            Merge result.
        """
        # Find anonymous customer
        anon_result = await self.db.execute(
            select(Customer).where(
                and_(
                    Customer.anonymous_id == anonymous_id,
                    Customer.organization_id == organization_id,
                    Customer.external_ids == {{}}  # No external IDs = anonymous
                )
            )
        )
        anonymous_customer = anon_result.scalar_one_or_none()

        if not anonymous_customer:
            # Just alias events, no profile to merge
            return await self.alias_anonymous_id(
                anonymous_id, customer_id, organization_id
            )

        # Find target customer
        target_result = await self.db.execute(
            select(Customer).where(
                and_(
                    Customer.id == customer_id,
                    Customer.organization_id == organization_id
                )
            )
        )
        target_customer = target_result.scalar_one_or_none()

        if not target_customer:
            return {
                "success": False,
                "error": "Target customer not found"
            }

        # Merge traits
        merged_traits = {**(anonymous_customer.traits or {})}
        merged_traits.update(target_customer.traits or {})
        target_customer.traits = merged_traits

        # Merge computed traits
        merged_computed = {**(anonymous_customer.computed_traits or {})}
        merged_computed.update(target_customer.computed_traits or {})
        target_customer.computed_traits = merged_computed

        # Update events
        events_result = await self.db.execute(
            select(CustomerEvent).where(
                CustomerEvent.customer_id == anonymous_customer.id
            )
        )
        for event in events_result.scalars().all():
            event.customer_id = target_customer.id

        # Merge metrics (take max)
        target_customer.engagement_score = max(
            target_customer.engagement_score or 0,
            anonymous_customer.engagement_score or 0
        )

        # Delete anonymous profile
        anonymous_customer.soft_delete()

        await self.db.commit()

        return {
            "success": True,
            "merged_profile": True,
            "customer_id": target_customer.id
        }

    # ============== API Key Management ==============

    def generate_write_key(self, organization_id: str) -> str:
        """Generate a new write key for client SDK.

        Args:
            organization_id: Organization ID.

        Returns:
            New write key.
        """
        # Format: ma_{org_id_hash}_{random}
        org_hash = hashlib.sha256(organization_id.encode()).hexdigest()[:16]
        random_part = secrets.token_urlsafe(32)
        return f"ma_{org_hash}_{random_part}"

    def validate_write_key(self, write_key: str, organization_id: str) -> bool:
        """Validate write key for organization.

        Args:
            write_key: Write key to validate.
            organization_id: Expected organization ID.

        Returns:
            True if valid, False otherwise.
        """
        if not write_key.startswith("ma_"):
            return False

        parts = write_key.split("_")
        if len(parts) < 3:
            return False

        # Verify organization hash
        org_hash = hashlib.sha256(organization_id.encode()).hexdigest()[:16]
        return parts[1] == org_hash

    # ============== SDK Configuration ==============

    def get_sdk_settings(self, organization_id: str) -> Dict[str, Any]:
        """Get SDK settings for organization.

        Args:
            organization_id: Organization ID.

        Returns:
            SDK settings dictionary.
        """
        return {
            "organizationId": organization_id,
            "batchSize": 20,
            "flushInterval": 10000,
            "retryAttempts": 3,
            "retryDelay": 1000,
            "maxEventsInMemory": 100,
            "cookieDomain": None,  # Auto-detect
            "cookieExpiryDays": 365,
            "trackPageViewOnLoad": True,
            "trackClicks": False,
            "trackFormSubmissions": True,
            "debug": False
        }

    async def get_identified_traits(
        self,
        customer_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """Get traits for identified customer.

        Args:
            customer_id: Customer ID.
            organization_id: Organization ID.

        Returns:
            Customer traits.
        """
        result = await self.db.execute(
            select(Customer).where(
                and_(
                    Customer.id == customer_id,
                    Customer.organization_id == organization_id
                )
            )
        )
        customer = result.scalar_one_or_none()

        if not customer:
            return {}

        return {
            "traits": customer.traits or {},
            "computedTraits": customer.computed_traits or {},
            "engagementScore": customer.engagement_score,
            "lifetimeValue": customer.lifetime_value,
            "churnRisk": customer.churn_risk
        }