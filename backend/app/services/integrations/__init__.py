"""
Enterprise integration services for CRMs, data warehouses, and CDPs.
"""
from .oauth_manager import OAuthManager, OAuthError
from .crm import SalesforceClient, HubSpotClient, CRMSyncService
from .warehouse import SnowflakeClient, BigQueryClient, WarehouseSyncService
from .cdp import SegmentClient, MParticleClient, CDPIntegrationService

__all__ = [
    # OAuth
    "OAuthManager",
    "OAuthError",
    
    # CRM
    "SalesforceClient",
    "HubSpotClient",
    "CRMSyncService",
    
    # Warehouse
    "SnowflakeClient",
    "BigQueryClient",
    "WarehouseSyncService",
    
    # CDP
    "SegmentClient",
    "MParticleClient",
    "CDPIntegrationService",
]
