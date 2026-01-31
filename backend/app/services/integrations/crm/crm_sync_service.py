"""
Unified CRM synchronization service.

Manages bidirectional sync between CRM systems (Salesforce, HubSpot)
and the CDP, handling field mapping, transformations, and conflict resolution.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.integration import Integration, IntegrationProvider, IntegrationStatus
from app.models.integration_sync_log import (
    IntegrationSyncLog, SyncType, SyncStatus, SyncDirection
)
from app.models.integration_mapping import IntegrationMapping, ConflictStrategy
from app.models.customer import Customer
from app.models.customer_identity import CustomerIdentity, IdentityType, IdentitySource
from app.models.customer_event import CustomerEvent, EventType

from .salesforce_client import SalesforceClient
from .hubspot_client import HubSpotClient

logger = logging.getLogger(__name__)


class SyncResult:
    """Result of a sync operation."""
    
    def __init__(
        self,
        success: bool = True,
        records_processed: int = 0,
        records_created: int = 0,
        records_updated: int = 0,
        records_failed: int = 0,
        errors: List[str] = None
    ):
        self.success = success
        self.records_processed = records_processed
        self.records_created = records_created
        self.records_updated = records_updated
        self.records_failed = records_failed
        self.errors = errors or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "records_processed": self.records_processed,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "records_failed": self.records_failed,
            "errors": self.errors
        }


class CRMSyncService:
    """
    Unified CRM sync service.
    
    Handles synchronization between CRM systems and the CDP with:
    - Field mapping and transformations
    - Conflict resolution strategies
    - Incremental and full sync support
    - Comprehensive logging and error handling
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # Sync Operations
    
    async def sync_contacts_to_cdp(
        self,
        integration_id: UUID,
        direction: str = "bidirectional",
        sync_type: SyncType = SyncType.INCREMENTAL
    ) -> SyncResult:
        """
        Sync contacts between CRM and CDP.
        
        Args:
            integration_id: Integration ID
            direction: Sync direction (to_cdp, to_crm, bidirectional)
            sync_type: Type of sync (initial, incremental, full)
            
        Returns:
            Sync result with counts and errors
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return SyncResult(success=False, errors=["Integration not found"])
        
        # Create sync log
        sync_log = IntegrationSyncLog(
            integration_id=str(integration_id),
            sync_type=sync_type,
            sync_direction=SyncDirection(direction.upper()),
            entity_type="contacts",
            started_at=datetime.utcnow(),
            status=SyncStatus.RUNNING
        )
        self.db.add(sync_log)
        self.db.commit()
        
        result = SyncResult()
        
        try:
            # Update integration status
            integration.status = IntegrationStatus.SYNCING
            self.db.commit()
            
            # Get field mapping
            mapping = self._get_field_mapping(integration_id, "Contact", "customer")
            
            # Sync based on provider
            if integration.provider == IntegrationProvider.SALESFORCE:
                result = await self._sync_salesforce_contacts(
                    integration, mapping, direction, sync_type, sync_log
                )
            elif integration.provider == IntegrationProvider.HUBSPOT:
                result = await self._sync_hubspot_contacts(
                    integration, mapping, direction, sync_type, sync_log
                )
            else:
                result = SyncResult(success=False, errors=[f"Unsupported provider: {integration.provider}"])
            
            # Update sync log
            sync_log.complete(SyncStatus.SUCCESS if result.success else SyncStatus.FAILED)
            sync_log.records_processed = result.records_processed
            sync_log.records_created = result.records_created
            sync_log.records_updated = result.records_updated
            sync_log.records_failed = result.records_failed
            
            if result.errors:
                sync_log.error_message = "; ".join(result.errors[:5])
            
            # Update integration status
            integration.status = IntegrationStatus.ACTIVE
            integration.update_last_sync(
                "success" if result.success else "failed",
                {
                    "processed": result.records_processed,
                    "created": result.records_created,
                    "updated": result.records_updated,
                    "failed": result.records_failed
                }
            )
            
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Contact sync failed for integration {integration_id}")
            sync_log.complete(SyncStatus.FAILED)
            sync_log.set_error("SyncError", "SYNC_FAILED", str(e))
            integration.record_error(str(e))
            self.db.commit()
            result = SyncResult(success=False, errors=[str(e)])
        
        return result
    
    async def sync_leads_to_cdp(
        self,
        integration_id: UUID,
        sync_type: SyncType = SyncType.INCREMENTAL
    ) -> SyncResult:
        """
        Sync leads from CRM to CDP as prospects.
        
        Args:
            integration_id: Integration ID
            sync_type: Type of sync
            
        Returns:
            Sync result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return SyncResult(success=False, errors=["Integration not found"])
        
        sync_log = IntegrationSyncLog(
            integration_id=str(integration_id),
            sync_type=sync_type,
            sync_direction=SyncDirection.INBOUND,
            entity_type="leads",
            started_at=datetime.utcnow(),
            status=SyncStatus.RUNNING
        )
        self.db.add(sync_log)
        self.db.commit()
        
        result = SyncResult()
        
        try:
            integration.status = IntegrationStatus.SYNCING
            self.db.commit()
            
            mapping = self._get_field_mapping(integration_id, "Lead", "lead")
            
            if integration.provider == IntegrationProvider.SALESFORCE:
                result = await self._sync_salesforce_leads(
                    integration, mapping, sync_type, sync_log
                )
            elif integration.provider == IntegrationProvider.HUBSPOT:
                # HubSpot uses contacts with lifecycle stage
                result = await self._sync_hubspot_leads(
                    integration, mapping, sync_type, sync_log
                )
            
            sync_log.complete(SyncStatus.SUCCESS if result.success else SyncStatus.FAILED)
            sync_log.records_processed = result.records_processed
            sync_log.records_created = result.records_created
            sync_log.records_updated = result.records_updated
            
            integration.status = IntegrationStatus.ACTIVE
            integration.update_last_sync(
                "success" if result.success else "failed",
                result.to_dict()
            )
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Lead sync failed for integration {integration_id}")
            sync_log.complete(SyncStatus.FAILED)
            sync_log.set_error("SyncError", "SYNC_FAILED", str(e))
            integration.record_error(str(e))
            self.db.commit()
            result = SyncResult(success=False, errors=[str(e)])
        
        return result
    
    async def sync_opportunities(
        self,
        integration_id: UUID,
        sync_type: SyncType = SyncType.INCREMENTAL
    ) -> SyncResult:
        """
        Sync opportunities for revenue attribution.
        
        Args:
            integration_id: Integration ID
            sync_type: Type of sync
            
        Returns:
            Sync result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return SyncResult(success=False, errors=["Integration not found"])
        
        sync_log = IntegrationSyncLog(
            integration_id=str(integration_id),
            sync_type=sync_type,
            sync_direction=SyncDirection.INBOUND,
            entity_type="opportunities",
            started_at=datetime.utcnow(),
            status=SyncStatus.RUNNING
        )
        self.db.add(sync_log)
        self.db.commit()
        
        result = SyncResult()
        
        try:
            integration.status = IntegrationStatus.SYNCING
            self.db.commit()
            
            if integration.provider == IntegrationProvider.SALESFORCE:
                result = await self._sync_salesforce_opportunities(
                    integration, sync_type, sync_log
                )
            elif integration.provider == IntegrationProvider.HUBSPOT:
                result = await self._sync_hubspot_deals(
                    integration, sync_type, sync_log
                )
            
            sync_log.complete(SyncStatus.SUCCESS if result.success else SyncStatus.FAILED)
            sync_log.records_processed = result.records_processed
            
            integration.status = IntegrationStatus.ACTIVE
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Opportunity sync failed for integration {integration_id}")
            sync_log.complete(SyncStatus.FAILED)
            integration.record_error(str(e))
            self.db.commit()
            result = SyncResult(success=False, errors=[str(e)])
        
        return result
    
    async def push_cdp_segments_to_crm(
        self,
        integration_id: UUID,
        segment_ids: List[UUID]
    ) -> SyncResult:
        """
        Push CDP segments to CRM as lists/audiences.
        
        Args:
            integration_id: Integration ID
            segment_ids: List of segment IDs to sync
            
        Returns:
            Sync result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return SyncResult(success=False, errors=["Integration not found"])
        
        result = SyncResult()
        
        try:
            from app.models.customer_segment import CustomerSegment
            from app.models.segment_membership import SegmentMembership
            
            for segment_id in segment_ids:
                segment = self.db.query(CustomerSegment).get(str(segment_id))
                if not segment:
                    continue
                
                # Get segment members
                memberships = self.db.query(SegmentMembership).filter(
                    SegmentMembership.segment_id == str(segment_id)
                ).all()
                
                customer_ids = [m.customer_id for m in memberships]
                
                # Push to CRM
                if integration.provider == IntegrationProvider.SALESFORCE:
                    # Create campaign and add members
                    await self._push_to_salesforce_campaign(
                        integration, segment, customer_ids
                    )
                elif integration.provider == IntegrationProvider.HUBSPOT:
                    # Add to list
                    await self._push_to_hubspot_list(
                        integration, segment, customer_ids
                    )
                
                result.records_processed += len(customer_ids)
            
            result.success = True
            
        except Exception as e:
            logger.exception(f"Segment push failed for integration {integration_id}")
            result.success = False
            result.errors.append(str(e))
        
        return result
    
    # Conflict Resolution
    
    def resolve_conflict(
        self,
        cdp_record: Dict[str, Any],
        crm_record: Dict[str, Any],
        strategy: str = "timestamp_wins"
    ) -> Dict[str, Any]:
        """
        Resolve data conflicts between CDP and CRM.
        
        Args:
            cdp_record: Record from CDP
            crm_record: Record from CRM
            strategy: Conflict resolution strategy
            
        Returns:
            Resolved record
        """
        if strategy == "cdp_wins":
            return cdp_record
        elif strategy == "crm_wins":
            return crm_record
        elif strategy == "timestamp_wins":
            cdp_updated = cdp_record.get("updated_at") or cdp_record.get("lastmodifieddate")
            crm_updated = crm_record.get("updated_at") or crm_record.get("LastModifiedDate")
            
            if cdp_updated and crm_updated:
                try:
                    cdp_dt = datetime.fromisoformat(str(cdp_updated).replace("Z", "+00:00"))
                    crm_dt = datetime.fromisoformat(str(crm_updated).replace("Z", "+00:00"))
                    return cdp_record if cdp_dt >= crm_dt else crm_record
                except:
                    pass
            
            return cdp_record
        elif strategy == "merge":
            # Merge non-null values, preferring CDP for conflicts
            merged = dict(crm_record)
            for key, value in cdp_record.items():
                if value is not None:
                    merged[key] = value
            return merged
        
        return cdp_record
    
    # Field Mapping
    
    def apply_field_mapping(
        self,
        source_data: Dict[str, Any],
        mapping: IntegrationMapping
    ) -> Dict[str, Any]:
        """
        Apply field mappings and transformations.
        
        Args:
            source_data: Source record data
            mapping: Field mapping configuration
            
        Returns:
            Mapped and transformed data
        """
        if not mapping:
            return source_data
        
        return mapping.apply_mapping(source_data)
    
    # Private helper methods
    
    def _get_field_mapping(
        self,
        integration_id: UUID,
        source_entity: str,
        target_entity: str
    ) -> Optional[IntegrationMapping]:
        """Get field mapping for entity pair."""
        return self.db.query(IntegrationMapping).filter(
            IntegrationMapping.integration_id == str(integration_id),
            IntegrationMapping.source_entity == source_entity,
            IntegrationMapping.target_entity == target_entity,
            IntegrationMapping.is_active == True
        ).first()
    
    async def _sync_salesforce_contacts(
        self,
        integration: Integration,
        mapping: Optional[IntegrationMapping],
        direction: str,
        sync_type: SyncType,
        sync_log: IntegrationSyncLog
    ) -> SyncResult:
        """Sync contacts from Salesforce."""
        result = SyncResult()
        
        async with SalesforceClient(integration.auth_config) as client:
            # Determine sync window
            modified_since = None
            if sync_type == SyncType.INCREMENTAL and integration.last_sync_at:
                modified_since = integration.last_sync_at
            
            # Fetch contacts
            contacts = await client.get_contacts(
                modified_since=modified_since,
                limit=1000
            )
            
            sync_log.record_api_call(success=True, bytes_count=len(str(contacts)))
            
            for contact in contacts:
                try:
                    # Apply field mapping
                    mapped_data = self.apply_field_mapping(contact, mapping) if mapping else contact
                    
                    # Check for existing customer
                    email = mapped_data.get("email") or contact.get("Email")
                    existing = self._find_customer_by_email(
                        integration.organization_id, email
                    )
                    
                    if existing:
                        # Update existing
                        if direction in ("bidirectional", "to_cdp"):
                            self._update_customer_from_crm(existing, mapped_data, "salesforce")
                            result.records_updated += 1
                    else:
                        # Create new
                        if direction in ("bidirectional", "to_cdp"):
                            self._create_customer_from_crm(
                                integration.organization_id, mapped_data, "salesforce"
                            )
                            result.records_created += 1
                    
                    result.records_processed += 1
                    sync_log.record_success(
                        created=0 if existing else 1,
                        updated=1 if existing else 0
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to sync contact {contact.get('Id')}: {e}")
                    result.records_failed += 1
                    result.errors.append(f"Contact {contact.get('Id')}: {str(e)}")
                    sync_log.record_failure(contact.get("Id"), str(e))
        
        result.success = result.records_failed == 0 or result.records_processed > result.records_failed
        return result
    
    async def _sync_hubspot_contacts(
        self,
        integration: Integration,
        mapping: Optional[IntegrationMapping],
        direction: str,
        sync_type: SyncType,
        sync_log: IntegrationSyncLog
    ) -> SyncResult:
        """Sync contacts from HubSpot."""
        result = SyncResult()
        
        async with HubSpotClient(integration.auth_config) as client:
            modified_since = None
            if sync_type == SyncType.INCREMENTAL and integration.last_sync_at:
                modified_since = integration.last_sync_at
            
            # Fetch contacts with pagination
            after = None
            has_more = True
            
            while has_more and result.records_processed < 10000:
                response = await client.get_contacts(
                    modified_since=modified_since,
                    limit=100,
                    after=after
                )
                
                contacts = response.get("results", [])
                
                for contact in contacts:
                    try:
                        properties = contact.get("properties", {})
                        mapped_data = self.apply_field_mapping(properties, mapping) if mapping else properties
                        
                        email = mapped_data.get("email") or properties.get("email")
                        existing = self._find_customer_by_email(
                            integration.organization_id, email
                        )
                        
                        if existing:
                            if direction in ("bidirectional", "to_cdp"):
                                self._update_customer_from_crm(existing, mapped_data, "hubspot")
                                result.records_updated += 1
                        else:
                            if direction in ("bidirectional", "to_cdp"):
                                self._create_customer_from_crm(
                                    integration.organization_id, mapped_data, "hubspot"
                                )
                                result.records_created += 1
                        
                        result.records_processed += 1
                        sync_log.record_success(
                            created=0 if existing else 1,
                            updated=1 if existing else 0
                        )
                        
                    except Exception as e:
                        logger.error(f"Failed to sync contact {contact.get('id')}: {e}")
                        result.records_failed += 1
                        sync_log.record_failure(contact.get("id"), str(e))
                
                # Check for more pages
                paging = response.get("paging", {})
                next_page = paging.get("next", {})
                after = next_page.get("after")
                has_more = after is not None
        
        result.success = result.records_failed == 0 or result.records_processed > result.records_failed
        return result
    
    async def _sync_salesforce_leads(
        self,
        integration: Integration,
        mapping: Optional[IntegrationMapping],
        sync_type: SyncType,
        sync_log: IntegrationSyncLog
    ) -> SyncResult:
        """Sync leads from Salesforce."""
        result = SyncResult()
        
        async with SalesforceClient(integration.auth_config) as client:
            modified_since = None
            if sync_type == SyncType.INCREMENTAL and integration.last_sync_at:
                modified_since = integration.last_sync_at
            
            leads = await client.get_leads(
                modified_since=modified_since,
                limit=1000,
                converted=False  # Only unconverted leads
            )
            
            for lead in leads:
                try:
                    mapped_data = self.apply_field_mapping(lead, mapping) if mapping else lead
                    
                    email = mapped_data.get("email") or lead.get("Email")
                    existing = self._find_customer_by_email(
                        integration.organization_id, email
                    )
                    
                    if not existing:
                        # Create as prospect
                        self._create_customer_from_crm(
                            integration.organization_id,
                            mapped_data,
                            "salesforce",
                            is_prospect=True
                        )
                        result.records_created += 1
                    
                    result.records_processed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync lead {lead.get('Id')}: {e}")
                    result.records_failed += 1
        
        result.success = result.records_failed == 0 or result.records_processed > result.records_failed
        return result
    
    async def _sync_hubspot_leads(
        self,
        integration: Integration,
        mapping: Optional[IntegrationMapping],
        sync_type: SyncType,
        sync_log: IntegrationSyncLog
    ) -> SyncResult:
        """Sync leads from HubSpot (contacts with lead lifecycle stage)."""
        result = SyncResult()
        
        async with HubSpotClient(integration.auth_config) as client:
            # HubSpot uses lifecycle stage to identify leads
            after = None
            has_more = True
            
            while has_more:
                response = await client.get_contacts(
                    limit=100,
                    after=after
                )
                
                contacts = response.get("results", [])
                
                for contact in contacts:
                    properties = contact.get("properties", {})
                    lifecycle = properties.get("hs_lifecyclestage", "")
                    
                    # Only sync leads/subscribers
                    if lifecycle in ("lead", "subscriber", "marketingqualifiedlead"):
                        try:
                            mapped_data = self.apply_field_mapping(properties, mapping) if mapping else properties
                            
                            email = mapped_data.get("email") or properties.get("email")
                            existing = self._find_customer_by_email(
                                integration.organization_id, email
                            )
                            
                            if not existing:
                                self._create_customer_from_crm(
                                    integration.organization_id,
                                    mapped_data,
                                    "hubspot",
                                    is_prospect=True
                                )
                                result.records_created += 1
                            
                            result.records_processed += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to sync lead {contact.get('id')}: {e}")
                            result.records_failed += 1
                
                paging = response.get("paging", {})
                next_page = paging.get("next", {})
                after = next_page.get("after")
                has_more = after is not None
        
        result.success = result.records_failed == 0 or result.records_processed > result.records_failed
        return result
    
    async def _sync_salesforce_opportunities(
        self,
        integration: Integration,
        sync_type: SyncType,
        sync_log: IntegrationSyncLog
    ) -> SyncResult:
        """Sync opportunities from Salesforce for attribution."""
        result = SyncResult()
        
        async with SalesforceClient(integration.auth_config) as client:
            modified_since = None
            if sync_type == SyncType.INCREMENTAL and integration.last_sync_at:
                modified_since = integration.last_sync_at
            
            opportunities = await client.get_opportunities(
                modified_since=modified_since,
                limit=1000
            )
            
            for opp in opportunities:
                try:
                    # Store as conversion event for attribution
                    self._record_opportunity_conversion(integration.organization_id, opp)
                    result.records_processed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync opportunity {opp.get('Id')}: {e}")
                    result.records_failed += 1
        
        result.success = True
        return result
    
    async def _sync_hubspot_deals(
        self,
        integration: Integration,
        sync_type: SyncType,
        sync_log: IntegrationSyncLog
    ) -> SyncResult:
        """Sync deals from HubSpot for attribution."""
        result = SyncResult()
        
        async with HubSpotClient(integration.auth_config) as client:
            modified_since = None
            if sync_type == SyncType.INCREMENTAL and integration.last_sync_at:
                modified_since = integration.last_sync_at
            
            after = None
            has_more = True
            
            while has_more:
                response = await client.get_deals(
                    modified_since=modified_since,
                    limit=100,
                    after=after
                )
                
                deals = response.get("results", [])
                
                for deal in deals:
                    try:
                        properties = deal.get("properties", {})
                        self._record_deal_conversion(integration.organization_id, deal, properties)
                        result.records_processed += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to sync deal {deal.get('id')}: {e}")
                        result.records_failed += 1
                
                paging = response.get("paging", {})
                next_page = paging.get("next", {})
                after = next_page.get("after")
                has_more = after is not None
        
        result.success = True
        return result
    
    async def _push_to_salesforce_campaign(
        self,
        integration: Integration,
        segment: Any,
        customer_ids: List[str]
    ) -> None:
        """Push segment members to Salesforce campaign."""
        async with SalesforceClient(integration.auth_config) as client:
            # Create or get campaign
            campaign_data = {
                "Name": segment.name,
                "Description": segment.description or f"CDP Segment: {segment.name}",
                "Status": "Planned",
                "Type": "Marketing"
            }
            
            # For now, just log the operation
            # In production, would create campaign and add members
            logger.info(f"Would create Salesforce campaign for segment {segment.name}")
    
    async def _push_to_hubspot_list(
        self,
        integration: Integration,
        segment: Any,
        customer_ids: List[str]
    ) -> None:
        """Push segment members to HubSpot list."""
        async with HubSpotClient(integration.auth_config) as client:
            # Get contact IDs for customers
            # For now, just log the operation
            logger.info(f"Would add {len(customer_ids)} contacts to HubSpot list for segment {segment.name}")
    
    def _find_customer_by_email(
        self,
        organization_id: str,
        email: Optional[str]
    ) -> Optional[Customer]:
        """Find customer by email address."""
        if not email:
            return None
        
        # Search in identities
        identity = self.db.query(CustomerIdentity).filter(
            CustomerIdentity.identity_value == email.lower(),
            CustomerIdentity.identity_type == IdentityType.EMAIL
        ).first()
        
        if identity:
            return self.db.query(Customer).filter(
                Customer.id == identity.customer_id,
                Customer.organization_id == organization_id
            ).first()
        
        # Search in traits
        return self.db.query(Customer).filter(
            Customer.organization_id == organization_id,
            Customer.traits.contains({"email": email.lower()})
        ).first()
    
    def _create_customer_from_crm(
        self,
        organization_id: str,
        data: Dict[str, Any],
        source: str,
        is_prospect: bool = False
    ) -> Customer:
        """Create a new customer from CRM data."""
        customer = Customer(
            organization_id=organization_id,
            external_ids={source: data.get("id") or data.get("Id")},
            traits={
                "first_name": data.get("first_name") or data.get("FirstName"),
                "last_name": data.get("last_name") or data.get("LastName"),
                "email": data.get("email") or data.get("Email"),
                "phone": data.get("phone") or data.get("Phone"),
                "company": data.get("company") or data.get("Company"),
                "title": data.get("title") or data.get("Title"),
                "source": source,
                "is_prospect": is_prospect
            }
        )
        
        self.db.add(customer)
        self.db.flush()
        
        # Create identity record
        email = data.get("email") or data.get("Email")
        if email:
            identity = CustomerIdentity(
                customer_id=customer.id,
                identity_type=IdentityType.EMAIL,
                identity_value=email.lower(),
                source=IdentitySource.CRM,
                confidence_score=1.0
            )
            self.db.add(identity)
        
        self.db.commit()
        return customer
    
    def _update_customer_from_crm(
        self,
        customer: Customer,
        data: Dict[str, Any],
        source: str
    ) -> None:
        """Update existing customer from CRM data."""
        # Update traits
        if not customer.traits:
            customer.traits = {}
        
        customer.traits.update({
            "first_name": data.get("first_name") or data.get("FirstName") or customer.traits.get("first_name"),
            "last_name": data.get("last_name") or data.get("LastName") or customer.traits.get("last_name"),
            "phone": data.get("phone") or data.get("Phone") or customer.traits.get("phone"),
            "company": data.get("company") or data.get("Company") or customer.traits.get("company"),
            "title": data.get("title") or data.get("Title") or customer.traits.get("title"),
        })
        
        # Update external IDs
        if not customer.external_ids:
            customer.external_ids = {}
        customer.external_ids[source] = data.get("id") or data.get("Id")
        
        self.db.commit()
    
    def _record_opportunity_conversion(
        self,
        organization_id: str,
        opp: Dict[str, Any]
    ) -> None:
        """Record opportunity as conversion event for attribution."""
        from app.models.conversion_event import ConversionEvent, ConversionType
        
        # Find associated contact
        # This would link to customer via external_ids
        
        conversion = ConversionEvent(
            organization_id=organization_id,
            conversion_type=ConversionType.OPPORTUNITY,
            value=float(opp.get("Amount") or 0),
            currency="USD",
            external_id=opp.get("Id"),
            metadata={
                "name": opp.get("Name"),
                "stage": opp.get("StageName"),
                "probability": opp.get("Probability"),
                "close_date": opp.get("CloseDate"),
                "is_won": opp.get("IsWon"),
                "campaign_id": opp.get("CampaignId")
            }
        )
        
        self.db.add(conversion)
        self.db.commit()
    
    def _record_deal_conversion(
        self,
        organization_id: str,
        deal: Dict[str, Any],
        properties: Dict[str, Any]
    ) -> None:
        """Record deal as conversion event for attribution."""
        from app.models.conversion_event import ConversionEvent, ConversionType
        
        amount = 0
        try:
            amount = float(properties.get("amount") or 0)
        except:
            pass
        
        conversion = ConversionEvent(
            organization_id=organization_id,
            conversion_type=ConversionType.PURCHASE,
            value=amount,
            currency="USD",
            external_id=deal.get("id"),
            metadata={
                "name": properties.get("dealname"),
                "stage": properties.get("dealstage"),
                "pipeline": properties.get("pipeline"),
                "is_closed": properties.get("hs_is_closed"),
                "is_closed_won": properties.get("hs_is_closed_won")
            }
        )
        
        self.db.add(conversion)
        self.db.commit()
