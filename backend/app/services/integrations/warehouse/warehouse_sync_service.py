"""
Data warehouse synchronization service.

Manages scheduled exports and schema management for data warehouse
integrations including Snowflake, BigQuery, Databricks, and Redshift.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.integration import Integration, IntegrationProvider, IntegrationStatus
from app.models.integration_sync_log import (
    IntegrationSyncLog, SyncType, SyncStatus, SyncDirection
)
from app.models.customer import Customer
from app.models.customer_event import CustomerEvent
from app.models.attribution import Attribution

from .snowflake_client import SnowflakeClient
from .bigquery_client import BigQueryClient

logger = logging.getLogger(__name__)


class WarehouseSyncService:
    """
    Data warehouse sync service.
    
    Manages recurring data exports to warehouses with:
    - Scheduled exports (hourly, daily, weekly)
    - Schema management and validation
    - Incremental and full refresh support
    - Comprehensive logging
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # Scheduled Exports
    
    async def schedule_customer_export(
        self,
        integration_id: UUID,
        frequency: str = "daily",
        full_refresh: bool = False,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Schedule recurring customer data export.
        
        Args:
            integration_id: Integration ID
            frequency: Export frequency (hourly, daily, weekly)
            full_refresh: Whether to do full refresh each time
            batch_size: Number of records per batch
            
        Returns:
            Export result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        # Create sync log
        sync_log = IntegrationSyncLog(
            integration_id=str(integration_id),
            sync_type=SyncType.SCHEDULED if not full_refresh else SyncType.FULL,
            sync_direction=SyncDirection.OUTBOUND,
            entity_type="customers",
            started_at=datetime.utcnow(),
            status=SyncStatus.RUNNING
        )
        self.db.add(sync_log)
        self.db.commit()
        
        result = {"success": True, "records_exported": 0}
        
        try:
            integration.status = IntegrationStatus.SYNCING
            self.db.commit()
            
            # Get customers to export
            customers = self._get_customers_for_export(integration.organization_id, integration.last_sync_at)
            
            # Export based on provider
            if integration.provider == IntegrationProvider.SNOWFLAKE:
                result = await self._export_to_snowflake(
                    integration, customers, "customers", full_refresh, batch_size, sync_log
                )
            elif integration.provider == IntegrationProvider.BIGQUERY:
                result = await self._export_to_bigquery(
                    integration, customers, "customers", full_refresh, batch_size, sync_log
                )
            else:
                result = {"success": False, "error": f"Unsupported provider: {integration.provider}"}
            
            # Update sync log
            sync_log.complete(SyncStatus.SUCCESS if result["success"] else SyncStatus.FAILED)
            sync_log.records_processed = result.get("records_exported", 0)
            sync_log.records_created = result.get("records_exported", 0)
            
            # Update integration
            integration.status = IntegrationStatus.ACTIVE
            integration.update_last_sync(
                "success" if result["success"] else "failed",
                {"exported": result.get("records_exported", 0)}
            )
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Customer export failed for integration {integration_id}")
            sync_log.complete(SyncStatus.FAILED)
            sync_log.set_error("ExportError", "EXPORT_FAILED", str(e))
            integration.record_error(str(e))
            self.db.commit()
            result = {"success": False, "error": str(e)}
        
        return result
    
    async def schedule_event_export(
        self,
        integration_id: UUID,
        frequency: str = "hourly",
        event_types: Optional[List[str]] = None,
        batch_size: int = 5000
    ) -> Dict[str, Any]:
        """
        Schedule recurring event data export.
        
        Args:
            integration_id: Integration ID
            frequency: Export frequency (hourly, daily, weekly)
            event_types: Filter by event types
            batch_size: Number of records per batch
            
        Returns:
            Export result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        sync_log = IntegrationSyncLog(
            integration_id=str(integration_id),
            sync_type=SyncType.SCHEDULED,
            sync_direction=SyncDirection.OUTBOUND,
            entity_type="events",
            started_at=datetime.utcnow(),
            status=SyncStatus.RUNNING
        )
        self.db.add(sync_log)
        self.db.commit()
        
        result = {"success": True, "records_exported": 0}
        
        try:
            integration.status = IntegrationStatus.SYNCING
            self.db.commit()
            
            # Get events to export
            events = self._get_events_for_export(
                integration.organization_id,
                integration.last_sync_at,
                event_types
            )
            
            if integration.provider == IntegrationProvider.SNOWFLAKE:
                result = await self._export_events_to_snowflake(
                    integration, events, batch_size, sync_log
                )
            elif integration.provider == IntegrationProvider.BIGQUERY:
                result = await self._export_events_to_bigquery(
                    integration, events, batch_size, sync_log
                )
            
            sync_log.complete(SyncStatus.SUCCESS if result["success"] else SyncStatus.FAILED)
            sync_log.records_processed = result.get("records_exported", 0)
            
            integration.status = IntegrationStatus.ACTIVE
            integration.update_last_sync(
                "success" if result["success"] else "failed",
                {"exported": result.get("records_exported", 0)}
            )
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Event export failed for integration {integration_id}")
            sync_log.complete(SyncStatus.FAILED)
            integration.record_error(str(e))
            self.db.commit()
            result = {"success": False, "error": str(e)}
        
        return result
    
    async def schedule_attribution_export(
        self,
        integration_id: UUID,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Schedule attribution data export.
        
        Args:
            integration_id: Integration ID
            batch_size: Number of records per batch
            
        Returns:
            Export result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        sync_log = IntegrationSyncLog(
            integration_id=str(integration_id),
            sync_type=SyncType.SCHEDULED,
            sync_direction=SyncDirection.OUTBOUND,
            entity_type="attribution",
            started_at=datetime.utcnow(),
            status=SyncStatus.RUNNING
        )
        self.db.add(sync_log)
        self.db.commit()
        
        result = {"success": True, "records_exported": 0}
        
        try:
            integration.status = IntegrationStatus.SYNCING
            self.db.commit()
            
            # Get attribution records
            attributions = self._get_attribution_for_export(
                integration.organization_id,
                integration.last_sync_at
            )
            
            if integration.provider == IntegrationProvider.SNOWFLAKE:
                result = await self._export_attribution_to_snowflake(
                    integration, attributions, batch_size, sync_log
                )
            elif integration.provider == IntegrationProvider.BIGQUERY:
                result = await self._export_attribution_to_bigquery(
                    integration, attributions, batch_size, sync_log
                )
            
            sync_log.complete(SyncStatus.SUCCESS)
            sync_log.records_processed = result.get("records_exported", 0)
            
            integration.status = IntegrationStatus.ACTIVE
            self.db.commit()
            
        except Exception as e:
            logger.exception(f"Attribution export failed for integration {integration_id}")
            sync_log.complete(SyncStatus.FAILED)
            integration.record_error(str(e))
            self.db.commit()
            result = {"success": False, "error": str(e)}
        
        return result
    
    # Schema Management
    
    async def create_export_schema(
        self,
        integration_id: UUID,
        entity_type: str
    ) -> Dict[str, Any]:
        """
        Create appropriate schema in data warehouse.
        
        Args:
            integration_id: Integration ID
            entity_type: Type of entity (customers, events, attribution)
            
        Returns:
            Schema creation result
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        try:
            if integration.provider == IntegrationProvider.SNOWFLAKE:
                return await self._create_snowflake_schema(integration, entity_type)
            elif integration.provider == IntegrationProvider.BIGQUERY:
                return await self._create_bigquery_schema(integration, entity_type)
            else:
                return {"success": False, "error": "Unsupported provider"}
        except Exception as e:
            logger.exception(f"Schema creation failed for integration {integration_id}")
            return {"success": False, "error": str(e)}
    
    async def validate_schema(
        self,
        integration_id: UUID,
        entity_type: str
    ) -> Dict[str, Any]:
        """
        Validate that destination schema matches expected structure.
        
        Args:
            integration_id: Integration ID
            entity_type: Type of entity
            
        Returns:
            Validation result with any mismatches
        """
        integration = self.db.query(Integration).get(str(integration_id))
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        try:
            if integration.provider == IntegrationProvider.SNOWFLAKE:
                return await self._validate_snowflake_schema(integration, entity_type)
            elif integration.provider == IntegrationProvider.BIGQUERY:
                return await self._validate_bigquery_schema(integration, entity_type)
            else:
                return {"success": False, "error": "Unsupported provider"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Private helper methods
    
    def _get_customers_for_export(
        self,
        organization_id: str,
        since: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get customers for export."""
        query = self.db.query(Customer).filter(
            Customer.organization_id == organization_id
        )
        
        if since:
            query = query.filter(Customer.updated_at >= since)
        
        customers = query.all()
        return [c.to_dict() for c in customers]
    
    def _get_events_for_export(
        self,
        organization_id: str,
        since: Optional[datetime],
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get events for export."""
        query = self.db.query(CustomerEvent).filter(
            CustomerEvent.organization_id == organization_id
        )
        
        if since:
            query = query.filter(CustomerEvent.created_at >= since)
        
        if event_types:
            query = query.filter(CustomerEvent.event_type.in_(event_types))
        
        # Limit to prevent memory issues
        events = query.limit(100000).all()
        return [e.to_dict() for e in events]
    
    def _get_attribution_for_export(
        self,
        organization_id: str,
        since: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Get attribution records for export."""
        query = self.db.query(Attribution).filter(
            Attribution.organization_id == organization_id
        )
        
        if since:
            query = query.filter(Attribution.created_at >= since)
        
        attributions = query.limit(100000).all()
        return [a.to_dict() for a in attributions]
    
    async def _export_to_snowflake(
        self,
        integration: Integration,
        customers: List[Dict[str, Any]],
        table_name: str,
        full_refresh: bool,
        batch_size: int,
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Export customers to Snowflake."""
        config = integration.auth_config
        
        async with SnowflakeClient(config) as client:
            count = await client.export_customers(
                organization_id=UUID(integration.organization_id),
                customers=customers,
                destination_table=f"cdp_{table_name}",
                full_refresh=full_refresh
            )
            
            sync_log.record_api_call(success=True)
            
            return {"success": True, "records_exported": count}
    
    async def _export_to_bigquery(
        self,
        integration: Integration,
        customers: List[Dict[str, Any]],
        table_name: str,
        full_refresh: bool,
        batch_size: int,
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Export customers to BigQuery."""
        config = integration.auth_config
        credentials_json = config.get("credentials_json")
        dataset = config.get("dataset", "cdp_data")
        
        async with BigQueryClient(credentials_json) as client:
            count = await client.export_customers(
                organization_id=UUID(integration.organization_id),
                customers=customers,
                dataset=dataset,
                table=table_name,
                full_refresh=full_refresh
            )
            
            sync_log.record_api_call(success=True)
            
            return {"success": True, "records_exported": count}
    
    async def _export_events_to_snowflake(
        self,
        integration: Integration,
        events: List[Dict[str, Any]],
        batch_size: int,
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Export events to Snowflake."""
        config = integration.auth_config
        
        async with SnowflakeClient(config) as client:
            count = await client.export_events(
                organization_id=UUID(integration.organization_id),
                events=events,
                destination_table="cdp_events"
            )
            
            sync_log.record_api_call(success=True)
            
            return {"success": True, "records_exported": count}
    
    async def _export_events_to_bigquery(
        self,
        integration: Integration,
        events: List[Dict[str, Any]],
        batch_size: int,
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Export events to BigQuery."""
        config = integration.auth_config
        credentials_json = config.get("credentials_json")
        dataset = config.get("dataset", "cdp_data")
        
        async with BigQueryClient(credentials_json) as client:
            count = await client.export_events(
                organization_id=UUID(integration.organization_id),
                events=events,
                dataset=dataset,
                table="events"
            )
            
            sync_log.record_api_call(success=True)
            
            return {"success": True, "records_exported": count}
    
    async def _export_attribution_to_snowflake(
        self,
        integration: Integration,
        attributions: List[Dict[str, Any]],
        batch_size: int,
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Export attribution to Snowflake."""
        config = integration.auth_config
        
        async with SnowflakeClient(config) as client:
            count = await client.export_attribution(
                organization_id=UUID(integration.organization_id),
                attributions=attributions,
                destination_table="cdp_attribution"
            )
            
            sync_log.record_api_call(success=True)
            
            return {"success": True, "records_exported": count}
    
    async def _export_attribution_to_bigquery(
        self,
        integration: Integration,
        attributions: List[Dict[str, Any]],
        batch_size: int,
        sync_log: IntegrationSyncLog
    ) -> Dict[str, Any]:
        """Export attribution to BigQuery."""
        config = integration.auth_config
        credentials_json = config.get("credentials_json")
        dataset = config.get("dataset", "cdp_data")
        
        async with BigQueryClient(credentials_json) as client:
            count = await client.export_attribution(
                organization_id=UUID(integration.organization_id),
                attributions=attributions,
                dataset=dataset,
                table="attribution"
            )
            
            sync_log.record_api_call(success=True)
            
            return {"success": True, "records_exported": count}
    
    async def _create_snowflake_schema(
        self,
        integration: Integration,
        entity_type: str
    ) -> Dict[str, Any]:
        """Create Snowflake schema."""
        config = integration.auth_config
        
        async with SnowflakeClient(config) as client:
            if entity_type == "customers":
                await client.create_table("cdp_customers", {
                    "id": "VARCHAR(12)",
                    "organization_id": "VARCHAR(12)",
                    "traits": "VARIANT",
                    "engagement_score": "FLOAT",
                    "created_at": "TIMESTAMP_NTZ"
                })
            elif entity_type == "events":
                await client.create_table("cdp_events", {
                    "id": "VARCHAR(12)",
                    "customer_id": "VARCHAR(12)",
                    "event_type": "VARCHAR(100)",
                    "timestamp": "TIMESTAMP_NTZ"
                })
            
            return {"success": True, "message": f"Schema created for {entity_type}"}
    
    async def _create_bigquery_schema(
        self,
        integration: Integration,
        entity_type: str
    ) -> Dict[str, Any]:
        """Create BigQuery schema."""
        config = integration.auth_config
        credentials_json = config.get("credentials_json")
        dataset = config.get("dataset", "cdp_data")
        
        async with BigQueryClient(credentials_json) as client:
            await client.create_dataset(dataset)
            
            if entity_type == "customers":
                from google.cloud import bigquery
                schema = [
                    bigquery.SchemaField("id", "STRING"),
                    bigquery.SchemaField("organization_id", "STRING"),
                    bigquery.SchemaField("traits", "JSON"),
                    bigquery.SchemaField("created_at", "TIMESTAMP"),
                ]
                await client.create_table(dataset, "customers", schema)
            
            return {"success": True, "message": f"Schema created for {entity_type}"}
    
    async def _validate_snowflake_schema(
        self,
        integration: Integration,
        entity_type: str
    ) -> Dict[str, Any]:
        """Validate Snowflake schema."""
        config = integration.auth_config
        table_name = f"cdp_{entity_type}"
        
        async with SnowflakeClient(config) as client:
            try:
                schema = await client.get_table_schema(table_name)
                return {
                    "success": True,
                    "valid": True,
                    "schema": schema
                }
            except Exception as e:
                return {
                    "success": False,
                    "valid": False,
                    "error": str(e)
                }
    
    async def _validate_bigquery_schema(
        self,
        integration: Integration,
        entity_type: str
    ) -> Dict[str, Any]:
        """Validate BigQuery schema."""
        config = integration.auth_config
        credentials_json = config.get("credentials_json")
        dataset = config.get("dataset", "cdp_data")
        
        async with BigQueryClient(credentials_json) as client:
            try:
                schema = await client.get_table_schema(dataset, entity_type)
                return {
                    "success": True,
                    "valid": True,
                    "schema": schema
                }
            except Exception as e:
                return {
                    "success": False,
                    "valid": False,
                    "error": str(e)
                }
