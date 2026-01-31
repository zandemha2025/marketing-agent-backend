"""
Integration management API.

Provides endpoints for managing enterprise integrations including:
- CRUD operations for integrations
- OAuth flow handling
- Sync operations and monitoring
- Field mapping management
- Webhook handling
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from .auth import get_current_user
from app.models.user import User
from app.models.integration import (
    Integration, IntegrationType, IntegrationProvider, IntegrationStatus
)
from app.models.integration_sync_log import IntegrationSyncLog, SyncType, SyncDirection
from app.models.integration_mapping import (
    IntegrationMapping, MappingDirection, ConflictStrategy
)

from app.services.integrations.crm.crm_sync_service import CRMSyncService
from app.services.integrations.warehouse.warehouse_sync_service import WarehouseSyncService
from app.services.integrations.cdp.cdp_sync_service import CDPIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter()


# Schemas

class IntegrationCreate(BaseModel):
    """Schema for creating an integration."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    integration_type: IntegrationType
    provider: IntegrationProvider
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    sync_config: Dict[str, Any] = Field(default_factory=dict)
    webhook_config: Dict[str, Any] = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[IntegrationStatus] = None
    auth_config: Optional[Dict[str, Any]] = None
    sync_config: Optional[Dict[str, Any]] = None
    webhook_config: Optional[Dict[str, Any]] = None


class MappingCreate(BaseModel):
    """Schema for creating a field mapping."""
    source_entity: str
    target_entity: str
    direction: MappingDirection = MappingDirection.BIDIRECTIONAL
    field_mappings: Dict[str, str] = Field(default_factory=dict)
    transformation_rules: Dict[str, Any] = Field(default_factory=dict)
    default_values: Dict[str, Any] = Field(default_factory=dict)
    required_fields: List[str] = Field(default_factory=list)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    conflict_strategy: ConflictStrategy = ConflictStrategy.TIMESTAMP_WINS
    filter_conditions: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    priority: int = 0


class MappingUpdate(BaseModel):
    """Schema for updating a field mapping."""
    field_mappings: Optional[Dict[str, str]] = None
    transformation_rules: Optional[Dict[str, Any]] = None
    default_values: Optional[Dict[str, Any]] = None
    required_fields: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    conflict_strategy: Optional[ConflictStrategy] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class SyncTriggerRequest(BaseModel):
    """Schema for triggering a sync."""
    sync_type: SyncType = SyncType.INCREMENTAL
    entity_type: Optional[str] = None


class WebhookConfigRequest(BaseModel):
    """Schema for webhook configuration."""
    webhook_url: str
    events: List[str]
    secret: Optional[str] = None


class TestMappingRequest(BaseModel):
    """Schema for testing field mapping."""
    test_data: Dict[str, Any]


# CRUD Operations

@router.post("/integrations", response_model=Dict[str, Any])
async def create_integration(
    integration: IntegrationCreate,
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new integration."""
    # Check permissions
    if str(current_user.organization_id) != str(organization_id) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized for this organization")
    
    db_integration = Integration(
        organization_id=str(organization_id),
        name=integration.name,
        description=integration.description,
        integration_type=integration.integration_type,
        provider=integration.provider,
        status=IntegrationStatus.PENDING,
        auth_config=integration.auth_config,
        sync_config=integration.sync_config,
        webhook_config=integration.webhook_config,
        connected_by=current_user.id
    )
    
    db.add(db_integration)
    db.commit()
    db.refresh(db_integration)
    
    logger.info(f"Created integration {db_integration.id} for organization {organization_id}")
    
    return {
        "success": True,
        "integration": db_integration.to_dict()
    }


@router.get("/integrations", response_model=List[Dict[str, Any]])
async def list_integrations(
    organization_id: UUID,
    integration_type: Optional[IntegrationType] = None,
    provider: Optional[IntegrationProvider] = None,
    status: Optional[IntegrationStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List integrations for an organization."""
    if str(current_user.organization_id) != str(organization_id) and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized for this organization")
    
    query = db.query(Integration).filter(
        Integration.organization_id == str(organization_id)
    )
    
    if integration_type:
        query = query.filter(Integration.integration_type == integration_type)
    if provider:
        query = query.filter(Integration.provider == provider)
    if status:
        query = query.filter(Integration.status == status)
    
    integrations = query.order_by(Integration.created_at.desc()).all()
    
    return [i.to_dict() for i in integrations]


@router.get("/integrations/{integration_id}", response_model=Dict[str, Any])
async def get_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return integration.to_dict()


@router.put("/integrations/{integration_id}", response_model=Dict[str, Any])
async def update_integration(
    integration_id: UUID,
    integration_update: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update fields
    if integration_update.name is not None:
        integration.name = integration_update.name
    if integration_update.description is not None:
        integration.description = integration_update.description
    if integration_update.status is not None:
        integration.status = integration_update.status
    if integration_update.auth_config is not None:
        integration.auth_config.update(integration_update.auth_config)
    if integration_update.sync_config is not None:
        integration.sync_config.update(integration_update.sync_config)
    if integration_update.webhook_config is not None:
        integration.webhook_config.update(integration_update.webhook_config)
    
    db.commit()
    db.refresh(integration)
    
    return {
        "success": True,
        "integration": integration.to_dict()
    }


@router.delete("/integrations/{integration_id}")
async def delete_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(integration)
    db.commit()
    
    logger.info(f"Deleted integration {integration_id}")
    
    return {"success": True, "message": "Integration deleted"}


# OAuth Flow

@router.get("/integrations/oauth/{provider}/start")
async def start_oauth_flow(
    provider: str,
    redirect_uri: str,
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start OAuth flow for a provider."""
    from app.services.integrations.oauth_manager import OAuthManager
    
    oauth_manager = OAuthManager()
    
    # Generate state parameter for security
    import secrets
    state = secrets.token_urlsafe(32)
    
    # Store state in session/cache for validation
    # TODO: Implement state storage
    
    if provider.lower() == "salesforce":
        auth_url = await oauth_manager.get_salesforce_auth_url(redirect_uri, state)
    elif provider.lower() == "hubspot":
        auth_url = await oauth_manager.get_hubspot_auth_url(redirect_uri, state)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported OAuth provider: {provider}")
    
    return {
        "success": True,
        "auth_url": auth_url,
        "state": state
    }


@router.get("/integrations/oauth/{provider}/callback")
async def handle_oauth_callback(
    provider: str,
    code: str,
    state: str,
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Handle OAuth callback."""
    from app.services.integrations.oauth_manager import OAuthManager
    
    oauth_manager = OAuthManager()
    
    # Validate state parameter
    # TODO: Implement state validation
    
    try:
        if provider.lower() == "salesforce":
            tokens = await oauth_manager.exchange_salesforce_code(code, "")
            provider_enum = IntegrationProvider.SALESFORCE
            integration_type = IntegrationType.CRM
        elif provider.lower() == "hubspot":
            tokens = await oauth_manager.exchange_hubspot_code(code, "")
            provider_enum = IntegrationProvider.HUBSPOT
            integration_type = IntegrationType.CRM
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
        
        # Create or update integration
        integration = Integration(
            organization_id=str(organization_id),
            name=f"{provider.title()} Integration",
            integration_type=integration_type,
            provider=provider_enum,
            status=IntegrationStatus.ACTIVE,
            auth_config=tokens,
            connected_at=datetime.now(timezone.utc),
            connected_by=current_user.id
        )
        
        db.add(integration)
        db.commit()
        db.refresh(integration)
        
        return {
            "success": True,
            "integration": integration.to_dict()
        }
        
    except Exception as e:
        logger.exception(f"OAuth callback failed for {provider}")
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


# Sync Operations

@router.post("/integrations/{integration_id}/sync")
async def trigger_sync(
    integration_id: UUID,
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger a sync for an integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Run sync based on integration type
    if integration.integration_type == IntegrationType.CRM:
        service = CRMSyncService(db)
        
        if request.entity_type == "contacts" or request.entity_type is None:
            background_tasks.add_task(
                service.sync_contacts_to_cdp,
                integration_id,
                "bidirectional",
                request.sync_type
            )
        elif request.entity_type == "leads":
            background_tasks.add_task(
                service.sync_leads_to_cdp,
                integration_id,
                request.sync_type
            )
        elif request.entity_type == "opportunities":
            background_tasks.add_task(
                service.sync_opportunities,
                integration_id,
                request.sync_type
            )
            
    elif integration.integration_type == IntegrationType.DATA_WAREHOUSE:
        service = WarehouseSyncService(db)
        
        if request.entity_type == "customers":
            background_tasks.add_task(
                service.schedule_customer_export,
                integration_id,
                "manual",
                request.sync_type == SyncType.FULL
            )
        elif request.entity_type == "events":
            background_tasks.add_task(
                service.schedule_event_export,
                integration_id,
                "manual"
            )
    
    return {
        "success": True,
        "message": "Sync triggered",
        "integration_id": str(integration_id),
        "sync_type": request.sync_type.value
    }


@router.get("/integrations/{integration_id}/sync/status")
async def get_sync_status(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current sync status for an integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get latest sync log
    latest_log = db.query(IntegrationSyncLog).filter(
        IntegrationSyncLog.integration_id == str(integration_id)
    ).order_by(IntegrationSyncLog.started_at.desc()).first()
    
    return {
        "integration_id": str(integration_id),
        "status": integration.status.value,
        "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        "last_sync_status": integration.last_sync_status,
        "last_sync_records": integration.last_sync_records,
        "latest_log": latest_log.to_dict() if latest_log else None
    }


@router.get("/integrations/{integration_id}/sync/logs")
async def get_sync_logs(
    integration_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get sync logs for an integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    logs = db.query(IntegrationSyncLog).filter(
        IntegrationSyncLog.integration_id == str(integration_id)
    ).order_by(
        IntegrationSyncLog.started_at.desc()
    ).offset(offset).limit(limit).all()
    
    return {
        "logs": [log.to_dict() for log in logs],
        "total": db.query(IntegrationSyncLog).filter(
            IntegrationSyncLog.integration_id == str(integration_id)
        ).count()
    }


# Field Mapping

@router.post("/integrations/{integration_id}/mappings")
async def create_field_mapping(
    integration_id: UUID,
    mapping: MappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a field mapping for an integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_mapping = IntegrationMapping(
        integration_id=str(integration_id),
        source_entity=mapping.source_entity,
        target_entity=mapping.target_entity,
        direction=mapping.direction,
        field_mappings=mapping.field_mappings,
        transformation_rules=mapping.transformation_rules,
        default_values=mapping.default_values,
        required_fields=mapping.required_fields,
        validation_rules=mapping.validation_rules,
        conflict_strategy=mapping.conflict_strategy,
        filter_conditions=mapping.filter_conditions,
        description=mapping.description,
        priority=mapping.priority
    )
    
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    
    return {
        "success": True,
        "mapping": db_mapping.to_dict()
    }


@router.get("/integrations/{integration_id}/mappings")
async def list_field_mappings(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List field mappings for an integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    mappings = db.query(IntegrationMapping).filter(
        IntegrationMapping.integration_id == str(integration_id)
    ).order_by(IntegrationMapping.priority.desc()).all()
    
    return [m.to_dict() for m in mappings]


@router.put("/integrations/{integration_id}/mappings/{mapping_id}")
async def update_field_mapping(
    integration_id: UUID,
    mapping_id: UUID,
    mapping_update: MappingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a field mapping."""
    mapping = db.query(IntegrationMapping).filter(
        IntegrationMapping.id == str(mapping_id),
        IntegrationMapping.integration_id == str(integration_id)
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    integration = db.query(Integration).get(str(integration_id))
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update fields
    if mapping_update.field_mappings is not None:
        mapping.field_mappings = mapping_update.field_mappings
    if mapping_update.transformation_rules is not None:
        mapping.transformation_rules = mapping_update.transformation_rules
    if mapping_update.default_values is not None:
        mapping.default_values = mapping_update.default_values
    if mapping_update.required_fields is not None:
        mapping.required_fields = mapping_update.required_fields
    if mapping_update.validation_rules is not None:
        mapping.validation_rules = mapping_update.validation_rules
    if mapping_update.conflict_strategy is not None:
        mapping.conflict_strategy = mapping_update.conflict_strategy
    if mapping_update.is_active is not None:
        mapping.is_active = mapping_update.is_active
    if mapping_update.priority is not None:
        mapping.priority = mapping_update.priority
    
    db.commit()
    db.refresh(mapping)
    
    return {
        "success": True,
        "mapping": mapping.to_dict()
    }


@router.delete("/integrations/{integration_id}/mappings/{mapping_id}")
async def delete_field_mapping(
    integration_id: UUID,
    mapping_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a field mapping."""
    mapping = db.query(IntegrationMapping).filter(
        IntegrationMapping.id == str(mapping_id),
        IntegrationMapping.integration_id == str(integration_id)
    ).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    integration = db.query(Integration).get(str(integration_id))
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(mapping)
    db.commit()
    
    return {"success": True, "message": "Mapping deleted"}


# Webhooks

@router.post("/integrations/{integration_id}/webhooks")
async def configure_webhook(
    integration_id: UUID,
    config: WebhookConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Configure webhook for an integration."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    integration.webhook_config = {
        "webhook_url": config.webhook_url,
        "events": config.events,
        "webhook_secret": config.secret
    }
    
    db.commit()
    
    return {
        "success": True,
        "webhook_config": {
            "webhook_url": config.webhook_url,
            "events": config.events
        }
    }


@router.post("/integrations/webhooks/{provider}")
async def receive_webhook(
    provider: str,
    payload: Dict[str, Any],
    signature: Optional[str] = Header(None, alias="X-Webhook-Signature"),
    db: Session = Depends(get_db)
):
    """Receive webhooks from external systems."""
    logger.info(f"Received webhook from {provider}")
    
    # Find integration by provider
    # This is simplified - in production, you'd identify the specific integration
    # based on webhook URL, signature, or payload content
    
    try:
        if provider.lower() == "salesforce":
            from app.services.integrations.crm.salesforce_client import SalesforceClient
            # Process Salesforce webhook
            pass
        elif provider.lower() == "segment":
            from app.services.integrations.cdp.segment_client import SegmentClient
            # Process Segment webhook
            pass
        else:
            logger.warning(f"Unknown webhook provider: {provider}")
    
    except Exception as e:
        logger.exception(f"Webhook processing failed for {provider}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
    
    return {"success": True}


# Testing

@router.post("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test an integration connection."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        if integration.integration_type == IntegrationType.CRM:
            if integration.provider == IntegrationProvider.SALESFORCE:
                from app.services.integrations.crm.salesforce_client import SalesforceClient
                async with SalesforceClient(integration.auth_config) as client:
                    is_valid = await client.validate_connection()
            elif integration.provider == IntegrationProvider.HUBSPOT:
                from app.services.integrations.crm.hubspot_client import HubSpotClient
                async with HubSpotClient(integration.auth_config) as client:
                    is_valid = await client.validate_connection()
            else:
                is_valid = False
                
        elif integration.integration_type == IntegrationType.DATA_WAREHOUSE:
            if integration.provider == IntegrationProvider.SNOWFLAKE:
                from app.services.integrations.warehouse.snowflake_client import SnowflakeClient
                async with SnowflakeClient(integration.auth_config) as client:
                    is_valid = await client.validate_connection()
            elif integration.provider == IntegrationProvider.BIGQUERY:
                from app.services.integrations.warehouse.bigquery_client import BigQueryClient
                credentials = integration.auth_config.get("credentials_json", "")
                async with BigQueryClient(credentials) as client:
                    is_valid = await client.validate_connection()
            else:
                is_valid = False
                
        elif integration.integration_type == IntegrationType.CDP:
            service = CDPIntegrationService(db)
            result = await service.validate_connection(integration_id)
            is_valid = result.get("valid", False)
        else:
            is_valid = False
        
        return {
            "success": is_valid,
            "valid": is_valid,
            "message": "Connection successful" if is_valid else "Connection failed"
        }
        
    except Exception as e:
        logger.exception(f"Integration test failed for {integration_id}")
        return {
            "success": False,
            "valid": False,
            "message": str(e)
        }


@router.post("/integrations/{integration_id}/test/mapping")
async def test_field_mapping(
    integration_id: UUID,
    request: TestMappingRequest,
    mapping_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test field mapping with sample data."""
    integration = db.query(Integration).get(str(integration_id))
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    if str(current_user.organization_id) != integration.organization_id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get mapping
    if mapping_id:
        mapping = db.query(IntegrationMapping).filter(
            IntegrationMapping.id == str(mapping_id),
            IntegrationMapping.integration_id == str(integration_id)
        ).first()
    else:
        # Get first active mapping
        mapping = db.query(IntegrationMapping).filter(
            IntegrationMapping.integration_id == str(integration_id),
            IntegrationMapping.is_active == True
        ).first()
    
    if not mapping:
        raise HTTPException(status_code=404, detail="No mapping found")
    
    # Apply mapping
    try:
        result = mapping.apply_mapping(request.test_data)
        validation_errors = mapping.validate_data(result)
        
        return {
            "success": True,
            "input": request.test_data,
            "output": result,
            "validation_errors": validation_errors
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Provider Info

@router.get("/integrations/providers")
async def list_providers():
    """List available integration providers."""
    return {
        "crm": [
            {"id": "salesforce", "name": "Salesforce", "auth_type": "oauth"},
            {"id": "hubspot", "name": "HubSpot", "auth_type": "oauth"},
            {"id": "dynamics", "name": "Microsoft Dynamics", "auth_type": "oauth"}
        ],
        "data_warehouse": [
            {"id": "snowflake", "name": "Snowflake", "auth_type": "credentials"},
            {"id": "bigquery", "name": "Google BigQuery", "auth_type": "service_account"},
            {"id": "databricks", "name": "Databricks", "auth_type": "token"},
            {"id": "redshift", "name": "Amazon Redshift", "auth_type": "credentials"}
        ],
        "cdp": [
            {"id": "segment", "name": "Segment", "auth_type": "write_key"},
            {"id": "mparticle", "name": "mParticle", "auth_type": "api_key"},
            {"id": "tealium", "name": "Tealium", "auth_type": "api_key"}
        ]
    }
