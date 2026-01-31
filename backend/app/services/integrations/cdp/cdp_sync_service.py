"""
CDP integration service for external CDP platforms.

Manages bidirectional sync with external CDPs like Segment and mParticle:
- Event forwarding to external CDPs
- Profile synchronization
- Real-time and batch processing
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.integration import Integration, IntegrationProvider, IntegrationStatus
from app.models.integration_sync_log import (
    IntegrationSyncLog, SyncType, SyncStatus, SyncDirection
)
from app.models.customer import Customer
from app.models.customer_segment import CustomerSegment
from app.models.customer_event import CustomerEvent

from .segment_client import SegmentClient
from .mparticle_client import MParticleClient

logger = logging.getLogger(__name__)


class CDPIntegrationService:
    """
    CDP integration service.
    
    Manages data flow between internal CDP and external CDP platforms:
    - Event forwarding configuration
    - Profile synchronization
    - Segment/audience syncing
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # Event Forwarding
    
    async def enable_event_forwarding(
        self,
        integration_id: UUID,
        event_types: List[str]
    ) -> Dict[str, Any]:
        """
        Enable real-time event forwarding to external CDP.
        
        Args:
            integration_id: Integration ID
            event_types: List of event types to forward
            
        Returns:
            Configuration result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        # Update sync config
        if not integration.sync_config:
            integration.sync_config = {}
        
        integration.sync_config["event_forwarding"] = {
            "enabled": True,
            "event_types": event_types,
            "mode": "realtime"
        }
        
        integration.status = IntegrationStatus.ACTIVE
        self.db.commit()
        
        logger.info(f"Enabled event forwarding for integration {integration_id}")
        
        return {
            "success": True,
            "integration_id": str(integration_id),
            "event_types": event_types
        }
    
    async def disable_event_forwarding(self, integration_id: UUID) -> Dict[str, Any]:
        """
        Disable event forwarding.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        if integration.sync_config and "event_forwarding" in integration.sync_config:
            integration.sync_config["event_forwarding"]["enabled"] = False
            self.db.commit()
        
        logger.info(f"Disabled event forwarding for integration {integration_id}")
        
        return {"success": True}
    
    async def forward_event(
        self,
        integration_id: UUID,
        event: CustomerEvent
    ) -> bool:
        """
        Forward a single event to external CDP.
        
        Args:
            integration_id: Integration ID
            event: Customer event to forward
            
        Returns:
            True if successful
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return False
        
        # Check if event forwarding is enabled for this event type
        sync_config = integration.sync_config or {}
        forwarding_config = sync_config.get("event_forwarding", {})
        
        if not forwarding_config.get("enabled"):
            return False
        
        allowed_types = forwarding_config.get("event_types", [])
        if event.event_type.value not in allowed_types and "*" not in allowed_types:
            return False
        
        try:
            if integration.provider == IntegrationProvider.SEGMENT:
                return await self._forward_to_segment(integration, event)
            elif integration.provider == IntegrationProvider.MPARTICLE:
                return await self._forward_to_mparticle(integration, event)
            else:
                logger.warning(f"Unsupported CDP provider: {integration.provider}")
                return False
        except Exception as e:
            logger.error(f"Event forwarding failed: {e}")
            return False
    
    async def _forward_to_segment(
        self,
        integration: Integration,
        event: CustomerEvent
    ) -> bool:
        """Forward event to Segment."""
        auth_config = integration.auth_config
        write_key = auth_config.get("write_key")
        
        if not write_key:
            logger.error("No Segment write key configured")
            return False
        
        async with SegmentClient(write_key) as client:
            # Get customer for user ID
            customer = self.db.query(Customer).get(event.customer_id)
            user_id = customer.external_ids.get("segment") if customer else None
            
            if not user_id:
                user_id = event.customer_id
            
            # Map event type
            event_name = event.event_name or event.event_type.value
            
            return await client.track_event(
                user_id=user_id,
                event_name=event_name,
                properties=event.properties,
                timestamp=event.timestamp,
                anonymous_id=event.anonymous_id
            )
    
    async def _forward_to_mparticle(
        self,
        integration: Integration,
        event: CustomerEvent
    ) -> bool:
        """Forward event to mParticle."""
        auth_config = integration.auth_config
        api_key = auth_config.get("api_key")
        api_secret = auth_config.get("api_secret")
        
        if not api_key or not api_secret:
            logger.error("mParticle credentials not configured")
            return False
        
        async with MParticleClient(api_key, api_secret) as client:
            customer = self.db.query(Customer).get(event.customer_id)
            user_id = customer.external_ids.get("mparticle") if customer else event.customer_id
            
            event_name = event.event_name or event.event_type.value
            
            return await client.track_event(
                user_id=user_id,
                event_name=event_name,
                properties=event.properties,
                timestamp=event.timestamp,
                anonymous_id=event.anonymous_id
            )
    
    # Profile Sync
    
    async def sync_profiles_to_cdp(
        self,
        integration_id: UUID,
        segment_id: Optional[UUID] = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Sync customer profiles to external CDP.
        
        Args:
            integration_id: Integration ID
            segment_id: Optional segment ID to filter profiles
            batch_size: Number of profiles per batch
            
        Returns:
            Sync result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        sync_log = IntegrationSyncLog(
            integration_id=str(integration_id),
            sync_type=SyncType.SCHEDULED,
            sync_direction=SyncDirection.OUTBOUND,
            entity_type="profiles",
            started_at=datetime.now(timezone.utc),
            status=SyncStatus.RUNNING
        )
        self.db.add(sync_log)
        self.db.commit()
        
        result = {"success": True, "records_synced": 0}
        
        try:
            # Get customers to sync
            query = self.db.query(Customer).filter(
                Customer.organization_id == integration.organization_id
            )
            
            if segment_id:
                from app.models.segment_membership import SegmentMembership
                customer_ids = self.db.query(SegmentMembership.customer_id).filter(
                    SegmentMembership.segment_id == str(segment_id)
                ).all()
                customer_ids = [c[0] for c in customer_ids]
                query = query.filter(Customer.id.in_(customer_ids))
            
            customers = query.all()
            
            if integration.provider == IntegrationProvider.SEGMENT:
                result = await self._sync_profiles_to_segment(
                    integration, customers, batch_size, sync_log
                )
            elif integration.provider == IntegrationProvider.MPARTICLE:
                result = await self._sync_profiles_to_mparticle(
                    integration, customers, batch_size, sync_log
                )
            
            sync_log.complete(SyncStatus.SUCCESS)
            sync_log.records_processed = result.get("records_synced", 0)
            
            integration.update_last_sync(
                "success",
                {"synced": result.get("records_synced", 0)}
            )
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Profile sync failed for integration {integration_id}")
            sync_log.complete(SyncStatus.FAILED)
            sync_log.set_error("SyncError", "SYNC_FAILED", str(e))
            integration.record_error(str(e))
            self.db.commit()
            result = {"success": False, "error": str(e)}
        
        return result
    
    async def _sync_profiles_to_segment(
        self,
        integration: Integration,
        customers: List[Customer],
        batch_size: int,
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Sync profiles to Segment."""
        auth_config = integration.auth_config
        write_key = auth_config.get("write_key")
        
        if not write_key:
            return {"success": False, "error": "No write key configured"}
        
        count = 0
        
        async with SegmentClient(write_key) as client:
            for customer in customers:
                try:
                    traits = {
                        **(customer.traits or {}),
                        **(customer.computed_traits or {}),
                        "engagement_score": customer.engagement_score,
                        "lifetime_value": customer.lifetime_value,
                        "churn_risk": customer.churn_risk
                    }
                    
                    await client.identify_user(
                        user_id=customer.id,
                        traits=traits
                    )
                    
                    count += 1
                    sync_log.record_success(created=1)
                    
                except Exception as e:
                    logger.error(f"Failed to sync profile {customer.id}: {e}")
                    sync_log.record_failure(customer.id, str(e))
        
        return {"success": True, "records_synced": count}
    
    async def _sync_profiles_to_mparticle(
        self,
        integration: Integration,
        customers: List[Customer],
        batch_size: int,
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Sync profiles to mParticle."""
        auth_config = integration.auth_config
        api_key = auth_config.get("api_key")
        api_secret = auth_config.get("api_secret")
        
        if not api_key or not api_secret:
            return {"success": False, "error": "Credentials not configured"}
        
        count = 0
        
        async with MParticleClient(api_key, api_secret) as client:
            # Process in batches
            for i in range(0, len(customers), batch_size):
                batch = customers[i:i + batch_size]
                
                profiles = []
                for customer in batch:
                    profiles.append({
                        "user_id": customer.id,
                        "traits": {
                            **(customer.traits or {}),
                            "engagement_score": customer.engagement_score,
                            "lifetime_value": customer.lifetime_value
                        },
                        "email": customer.traits.get("email") if customer.traits else None,
                        "first_name": customer.traits.get("first_name") if customer.traits else None,
                        "last_name": customer.traits.get("last_name") if customer.traits else None
                    })
                
                try:
                    await client.upload_user_profiles(profiles)
                    count += len(batch)
                    sync_log.record_success(created=len(batch))
                except Exception as e:
                    logger.error(f"Failed to sync batch: {e}")
                    for customer in batch:
                        sync_log.record_failure(customer.id, str(e))
        
        return {"success": True, "records_synced": count}
    
    # Batch Event Processing
    
    async def sync_events_batch(
        self,
        integration_id: UUID,
        since: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        limit: int = 10000
    ) -> Dict[str, Any]:
        """
        Sync events in batch to external CDP.
        
        Args:
            integration_id: Integration ID
            since: Sync events since this time
            event_types: Filter by event types
            limit: Maximum events to sync
            
        Returns:
            Sync result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        # Get events
        query = self.db.query(CustomerEvent).filter(
            CustomerEvent.organization_id == integration.organization_id
        )
        
        if since:
            query = query.filter(CustomerEvent.created_at >= since)
        
        if event_types:
            query = query.filter(CustomerEvent.event_type.in_(event_types))
        
        events = query.limit(limit).all()
        
        if not events:
            return {"success": True, "records_synced": 0}
        
        sync_log = IntegrationSyncLog(
            integration_id=str(integration_id),
            sync_type=SyncType.BATCH,
            sync_direction=SyncDirection.OUTBOUND,
            entity_type="events",
            started_at=datetime.now(timezone.utc),
            status=SyncStatus.RUNNING
        )
        self.db.add(sync_log)
        self.db.commit()
        
        result = {"success": True, "records_synced": 0}
        
        try:
            if integration.provider == IntegrationProvider.SEGMENT:
                result = await self._sync_events_to_segment(
                    integration, events, sync_log
                )
            elif integration.provider == IntegrationProvider.MPARTICLE:
                result = await self._sync_events_to_mparticle(
                    integration, events, sync_log
                )
            
            sync_log.complete(SyncStatus.SUCCESS)
            sync_log.records_processed = result.get("records_synced", 0)
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Event batch sync failed for integration {integration_id}")
            sync_log.complete(SyncStatus.FAILED)
            integration.record_error(str(e))
            self.db.commit()
            result = {"success": False, "error": str(e)}
        
        return result
    
    async def _sync_events_to_segment(
        self,
        integration: Integration,
        events: List[CustomerEvent],
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Sync events batch to Segment."""
        auth_config = integration.auth_config
        write_key = auth_config.get("write_key")
        
        if not write_key:
            return {"success": False, "error": "No write key configured"}
        
        async with SegmentClient(write_key) as client:
            batch = []
            
            for event in events:
                batch.append({
                    "type": "track",
                    "userId": event.customer_id,
                    "event": event.event_name or event.event_type.value,
                    "properties": event.properties or {},
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    "context": event.context or {}
                })
            
            await client.batch_send(batch)
            
            sync_log.record_success(created=len(events))
            
            return {"success": True, "records_synced": len(events)}
    
    async def _sync_events_to_mparticle(
        self,
        integration: Integration,
        events: List[CustomerEvent],
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Sync events batch to mParticle."""
        auth_config = integration.auth_config
        api_key = auth_config.get("api_key")
        api_secret = auth_config.get("api_secret")
        
        if not api_key or not api_secret:
            return {"success": False, "error": "Credentials not configured"}
        
        async with MParticleClient(api_key, api_secret) as client:
            mp_events = []
            
            for event in events:
                mp_events.append({
                    "user_id": event.customer_id,
                    "anonymous_id": event.anonymous_id,
                    "event_name": event.event_name or event.event_type.value,
                    "event_type": "custom_event",
                    "timestamp": event.timestamp,
                    "properties": event.properties or {}
                })
            
            await client.upload_events(mp_events)
            
            sync_log.record_success(created=len(events))
            
            return {"success": True, "records_synced": len(events)}
    
    # Validation
    
    async def validate_connection(self, integration_id: UUID) -> Dict[str, Any]:
        """
        Validate connection to external CDP.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Validation result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        try:
            if integration.provider == IntegrationProvider.SEGMENT:
                return await self._validate_segment_connection(integration)
            elif integration.provider == IntegrationProvider.MPARTICLE:
                return await self._validate_mparticle_connection(integration)
            else:
                return {"success": False, "error": "Unsupported provider"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _validate_segment_connection(
        self,
        integration: Integration
    ) -> Dict[str, Any]:
        """Validate Segment connection."""
        auth_config = integration.auth_config
        write_key = auth_config.get("write_key")
        
        if not write_key:
            return {"success": False, "error": "No write key configured"}
        
        async with SegmentClient(write_key) as client:
            is_valid = await client.validate_connection()
            
            return {
                "success": is_valid,
                "valid": is_valid,
                "message": "Connection valid" if is_valid else "Connection failed"
            }
    
    async def _validate_mparticle_connection(
        self,
        integration: Integration
    ) -> Dict[str, Any]:
        """Validate mParticle connection."""
        auth_config = integration.auth_config
        api_key = auth_config.get("api_key")
        api_secret = auth_config.get("api_secret")
        
        if not api_key or not api_secret:
            return {"success": False, "error": "Credentials not configured"}
        
        async with MParticleClient(api_key, api_secret) as client:
            is_valid = await client.validate_connection()
            
            return {
                "success": is_valid,
                "valid": is_valid,
                "message": "Connection valid" if is_valid else "Connection failed"
            }
