# Enterprise Marketing AGI Integration Plan

## Executive Summary

This document provides a comprehensive integration plan for incorporating enterprise-grade capabilities into the existing Marketing Agent Platform. Based on the gap analysis, this plan details the architecture evolution, implementation phases, and technical specifications required to support $1M ARR enterprise deals.

**Integration Scope:**
- Security & Compliance (SOC 2, GDPR, Enterprise SSO)
- Customer Data Platform (CDP) with identity resolution
- Autonomous Optimization Engine (A/B testing, self-optimizing campaigns)
- Multi-Touch Attribution & Advanced Analytics
- Enterprise Integrations (CRM, Data Warehouse, CDP connectors)

**Estimated Timeline:** 24 weeks across 6 phases
**Critical Dependencies:** Redis, Message Queue (Celery), Time-series DB

---

## Table of Contents

1. [Architecture Evolution](#1-architecture-evolution)
2. [Security & Compliance Integration](#2-security--compliance-integration)
3. [Customer Data Platform Integration](#3-customer-data-platform-integration)
4. [Autonomous Optimization Engine](#4-autonomous-optimization-engine)
5. [Attribution & Analytics](#5-attribution--analytics)
6. [Enterprise Integrations](#6-enterprise-integrations)
7. [Implementation Phases](#7-implementation-phases)
8. [Technical Specifications](#8-technical-specifications)

---

## 1. Architecture Evolution

### 1.1 New Service Modules Required

#### 1.1.1 Security & Compliance Services

```
backend/app/services/security/
├── audit_logger.py          # Centralized audit logging
├── compliance_monitor.py    # SOC 2 compliance checks
├── encryption.py            # Data encryption utilities
├── saml_provider.py         # SAML SSO implementation
├── oauth_provider.py        # OAuth 2.0/OIDC support
├── scim_handler.py          # SCIM 2.0 provisioning
└── __init__.py

backend/app/services/privacy/
├── gdpr_handler.py          # GDPR compliance workflows
├── consent_manager.py       # Consent tracking & management
├── data_exporter.py         # Data export for DSAR requests
├── data_retention.py        # Retention policy enforcement
└── __init__.py
```

**Dependencies:**
- `python-saml` or `onelogin/python-saml` for SAML
- `authlib` for OAuth/OIDC
- `cryptography` for encryption
- Redis for session storage (replacing in-memory)

**Integration Points:**
- Modify [`backend/app/api/auth.py`](backend/app/api/auth.py) to add SSO endpoints
- Add audit decorators to all API endpoints
- Integrate with existing User model in [`backend/app/models/user.py`](backend/app/models/user.py)

#### 1.1.2 CDP & Customer Data Services

```
backend/app/services/cdp/
├── profile_unifier.py       # Profile unification logic
├── identity_resolver.py     # Cross-channel identity resolution
├── event_processor.py       # Real-time event processing
├── segment_engine.py        # Dynamic segmentation
├── profile_enrichment.py    # Profile enrichment pipeline
└── __init__.py

backend/app/services/tracking/
├── event_ingestion.py       # Event ingestion API
├── event_validator.py       # Event schema validation
├── event_router.py          # Route events to processors
└── __init__.py
```

**Dependencies:**
- Kafka or Redis Streams for event streaming
- Elasticsearch for customer profile search
- ML libraries (scikit-learn) for identity matching

**Integration Points:**
- New API endpoints in `backend/app/api/customers.py`
- Webhook receivers for external event sources
- Integration with campaign orchestrator for audience targeting

#### 1.1.3 Optimization & Experimentation Services

```
backend/app/services/optimization/
├── campaign_optimizer.py    # Auto-optimization engine
├── budget_allocator.py      # Budget reallocation algorithm
├── performance_predictor.py # ML performance prediction
├── creative_optimizer.py    # Creative performance optimization
└── __init__.py

backend/app/services/experimentation/
├── ab_test_engine.py        # A/B testing framework
├── variant_generator.py     # AI variant generation
├── stats_calculator.py      # Statistical significance
├── experiment_scheduler.py  # Experiment lifecycle management
└── __init__.py
```

**Dependencies:**
- `statsmodels` for statistical analysis
- `scipy` for hypothesis testing
- Redis for experiment assignment caching

**Integration Points:**
- Hook into [`backend/app/services/campaigns/orchestrator.py`](backend/app/services/campaigns/orchestrator.py)
- Extend campaign model with experiment fields
- Add optimization API endpoints

#### 1.1.4 Attribution & Analytics Services

```
backend/app/services/attribution/
├── mta_engine.py            # Multi-touch attribution engine
├── channel_analyzer.py      # Channel performance analysis
├── mmm_engine.py            # Marketing mix modeling
├── incrementality.py        # Incrementality testing
├── attribution_models.py    # Attribution model implementations
└── __init__.py

backend/app/services/reporting/
├── dashboard_builder.py     # Custom dashboard builder
├── report_scheduler.py      # Scheduled report generation
├── export_engine.py         # Report export (PDF, CSV, etc.)
├── metric_calculator.py     # KPI calculation engine
└── __init__.py
```

**Dependencies:**
- TimescaleDB or InfluxDB for time-series metrics
- ClickHouse or BigQuery for large-scale analytics
- `pandas`, `numpy` for data processing

**Integration Points:**
- Extend [`backend/app/api/analytics.py`](backend/app/api/analytics.py)
- Add attribution tracking to campaign models
- Integrate with CDP for customer journey data

#### 1.1.5 Enterprise Integration Services

```
backend/app/services/integrations/
├── base.py                  # Base integration class
├── crm/
│   ├── salesforce.py        # Salesforce connector
│   ├── hubspot.py           # HubSpot connector
│   ├── dynamics.py          # Microsoft Dynamics
│   └── __init__.py
├── warehouse/
│   ├── snowflake.py         # Snowflake connector
│   ├── bigquery.py          # BigQuery connector
│   ├── redshift.py          # Redshift connector
│   └── __init__.py
├── cdp/
│   ├── segment.py           # Segment integration
│   ├── mparticle.py         # mParticle integration
│   └── __init__.py
├── sync_engine.py           # Bi-directional sync engine
├── webhook_handler.py       # Webhook processing
└── __init__.py
```

**Dependencies:**
- `simple-salesforce` for Salesforce
- `hubspot-api-client` for HubSpot
- `snowflake-connector-python` for Snowflake
- `google-cloud-bigquery` for BigQuery

**Integration Points:**
- New API endpoints in `backend/app/api/integrations.py`
- Background sync jobs via Celery
- Webhook endpoints for real-time updates

### 1.2 Infrastructure Requirements

#### 1.2.1 Redis (Required)

**Purpose:**
- Session storage (replacing in-memory dict)
- Rate limiting counters
- Caching layer for API responses
- Pub/sub for real-time updates
- Experiment assignment caching

**Configuration:**
```python
# backend/app/core/config.py additions
redis_url: str = "redis://localhost:6379/0"
redis_session_ttl: int = 3600  # 1 hour
redis_cache_ttl: int = 300     # 5 minutes
```

**Implementation:**
```python
# backend/app/core/redis.py
import redis.asyncio as redis
from .config import get_settings

class RedisManager:
    def __init__(self):
        self._client = None
    
    async def connect(self):
        settings = get_settings()
        self._client = await redis.from_url(settings.redis_url)
    
    async def disconnect(self):
        if self._client:
            await self._client.close()
    
    @property
    def client(self):
        return self._client

redis_manager = RedisManager()
```

#### 1.2.2 Message Queue (Celery + Redis/RabbitMQ)

**Purpose:**
- Background job processing
- Async asset generation
- Report generation
- Data export processing
- Integration sync jobs

**New Files:**
```
backend/app/tasks/
├── __init__.py
├── celery_app.py           # Celery configuration
├── asset_tasks.py          # Asset generation tasks
├── report_tasks.py         # Report generation tasks
├── sync_tasks.py           # Integration sync tasks
└── optimization_tasks.py   # Optimization tasks
```

**Dependencies:**
```
celery>=5.3.0
redis>=5.0.0  # or
amqp>=5.2.0   # for RabbitMQ
```

#### 1.2.3 Time-Series Database (TimescaleDB)

**Purpose:**
- Event tracking data
- Performance metrics over time
- Attribution touchpoints
- Analytics aggregations

**Schema:**
```sql
-- TimescaleDB hypertables for time-series data
CREATE TABLE customer_events (
    time TIMESTAMPTZ NOT NULL,
    customer_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    campaign_id TEXT,
    channel TEXT,
    metadata JSONB,
    organization_id TEXT NOT NULL
);

SELECT create_hypertable('customer_events', 'time');

CREATE TABLE performance_metrics (
    time TIMESTAMPTZ NOT NULL,
    campaign_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    channel TEXT,
    organization_id TEXT NOT NULL
);

SELECT create_hypertable('performance_metrics', 'time');
```

#### 1.2.4 Search Engine (Elasticsearch)

**Purpose:**
- Audit log search
- Customer profile search
- Content search
- Analytics queries

**Indices:**
```
audit-logs-{date}
customer-profiles
campaign-content
```

---

## 2. Security & Compliance Integration

### 2.1 Audit Logging System

#### 2.1.1 Database Schema

**New Model:** [`backend/app/models/audit_log.py`](backend/app/models/audit_log.py)

```python
"""
Audit Log Model for SOC 2 Compliance
"""
from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, Text, Index
from .base import Base

class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    APPROVE = "approve"
    REJECT = "reject"

class AuditLog(Base):
    """
    Comprehensive audit log for all system actions.
    
    SOC 2 Requirements:
    - Who performed the action (user_id, email)
    - What action was performed (action, resource_type, resource_id)
    - When it occurred (timestamp)
    - Where it originated (ip_address, user_agent)
    - What changed (before_state, after_state)
    """
    
    # Actor information
    user_id = Column(String(12), nullable=True)  # Null for system actions
    user_email = Column(String(255), nullable=True)
    organization_id = Column(String(12), nullable=False)
    
    # Action details
    action = Column(String(50), nullable=False)  # AuditAction
    resource_type = Column(String(100), nullable=False)  # e.g., "campaign", "asset"
    resource_id = Column(String(12), nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Data changes (sensitive data masked)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    changes_summary = Column(Text, nullable=True)
    
    # Compliance
    retention_until = Column(DateTime, nullable=True)
    compliance_flags = Column(JSON, default=list)  # ["gdpr", "soc2"]
    
    # Indexes for query performance
    __table_args__ = (
        Index('ix_audit_log_org_time', 'organization_id', 'timestamp'),
        Index('ix_audit_log_user', 'user_id', 'timestamp'),
        Index('ix_audit_log_resource', 'resource_type', 'resource_id'),
        Index('ix_audit_log_action', 'action', 'timestamp'),
    )
```

#### 2.1.2 Audit Logger Service

**New File:** [`backend/app/services/security/audit_logger.py`](backend/app/services/security/audit_logger.py)

```python
"""
Audit Logging Service

Provides centralized audit logging with:
- Sensitive data masking
- Async logging to database
- Elasticsearch indexing
- Log retention management
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.audit_log import AuditLog, AuditAction
from ...core.config import get_settings

logger = logging.getLogger(__name__)

# Sensitive fields that should be masked
SENSITIVE_FIELDS = {
    'password', 'password_hash', 'token', 'secret', 'api_key',
    'credit_card', 'ssn', 'email', 'phone', 'address'
}

class AuditLogger:
    """Centralized audit logging service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in data."""
        if not isinstance(data, dict):
            return data
        
        masked = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                masked[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_data(value)
            elif isinstance(value, list):
                masked[key] = [
                    self._mask_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked[key] = value
        return masked
    
    async def log(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str],
        user_id: Optional[str],
        user_email: Optional[str],
        organization_id: str,
        request: Optional[Request] = None,
        before_state: Optional[Dict] = None,
        after_state: Optional[Dict] = None,
        changes_summary: Optional[str] = None,
        compliance_flags: Optional[List[str]] = None
    ) -> AuditLog:
        """Create an audit log entry."""
        
        # Extract request context
        ip_address = None
        user_agent = None
        session_id = None
        
        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent")
            session_id = request.headers.get("x-session-id")
        
        # Mask sensitive data
        masked_before = self._mask_sensitive_data(before_state) if before_state else None
        masked_after = self._mask_sensitive_data(after_state) if after_state else None
        
        # Calculate retention date (7 years for SOC 2)
        retention_until = datetime.utcnow() + timedelta(days=2555)
        
        audit_entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            before_state=masked_before,
            after_state=masked_after,
            changes_summary=changes_summary,
            retention_until=retention_until,
            compliance_flags=compliance_flags or []
        )
        
        self.session.add(audit_entry)
        await self.session.commit()
        
        # Also index to Elasticsearch for search
        await self._index_to_elasticsearch(audit_entry)
        
        return audit_entry
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else None
    
    async def _index_to_elasticsearch(self, audit_entry: AuditLog):
        """Index audit log to Elasticsearch for search."""
        # Implementation depends on ES setup
        pass
    
    # Convenience methods
    async def log_create(self, **kwargs):
        """Log a create action."""
        return await self.log(action=AuditAction.CREATE, **kwargs)
    
    async def log_update(self, **kwargs):
        """Log an update action."""
        return await self.log(action=AuditAction.UPDATE, **kwargs)
    
    async def log_delete(self, **kwargs):
        """Log a delete action."""
        return await self.log(action=AuditAction.DELETE, **kwargs)
    
    async def log_login(self, **kwargs):
        """Log a login action."""
        return await self.log(action=AuditAction.LOGIN, **kwargs)
    
    async def log_logout(self, **kwargs):
        """Log a logout action."""
        return await self.log(action=AuditAction.LOGOUT, **kwargs)


# Decorator for automatic audit logging
def audit_log(
    action: AuditAction,
    resource_type: str,
    get_resource_id=None,
    get_organization_id=None
):
    """
    Decorator to automatically log API endpoint access.
    
    Usage:
        @router.post("/campaigns")
        @audit_log(
            action=AuditAction.CREATE,
            resource_type="campaign",
            get_resource_id=lambda result: result.get("id"),
            get_organization_id=lambda request: request.state.user.organization_id
        )
        async def create_campaign(...):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs or args
            request = kwargs.get('request')
            if not request and args:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            # Execute the endpoint
            result = await func(*args, **kwargs)
            
            # Log the action (async fire-and-forget)
            try:
                # Extract user info from request state
                user = getattr(request.state, 'user', None) if request else None
                
                resource_id = None
                if get_resource_id and result:
                    resource_id = get_resource_id(result)
                
                organization_id = None
                if get_organization_id and request:
                    organization_id = get_organization_id(request)
                elif user:
                    organization_id = user.organization_id
                
                if organization_id:
                    # Create audit log (non-blocking)
                    asyncio.create_task(_async_log(
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        user_id=getattr(user, 'id', None),
                        user_email=getattr(user, 'email', None),
                        organization_id=organization_id,
                        request=request
                    ))
            except Exception as e:
                logger.error(f"Failed to create audit log: {e}")
            
            return result
        return wrapper
    return decorator
```

#### 2.1.3 Middleware Integration

**Modify:** [`backend/app/main.py`](backend/app/main.py)

```python
# Add audit logging middleware
@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    """Middleware to capture request context for audit logging."""
    # Store request start time
    request.state.start_time = datetime.utcnow()
    
    # Extract and store user info if authenticated
    try:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Decode token without verifying (just for user info)
            # Full verification happens in endpoint dependencies
            payload = jwt.decode(token, options={"verify_signature": False})
            request.state.user_id = payload.get("sub")
            request.state.user_email = payload.get("email")
            request.state.org_id = payload.get("org_id")
    except:
        pass
    
    response = await call_next(request)
    return response
```

### 2.2 Enterprise SSO/SAML Integration

#### 2.2.1 SAML Provider Service

**New File:** [`backend/app/services/security/saml_provider.py`](backend/app/services/security/saml_provider.py)

```python
"""
SAML 2.0 SSO Provider

Supports Identity Providers:
- Okta
- Auth0
- Azure AD
- OneLogin
- Custom SAML providers
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings

from ...models.user import User, UserRole
from ...core.config import get_settings

@dataclass
class SAMLUser:
    """User data extracted from SAML response."""
    email: str
    name: str
    saml_id: str
    idp_name: str
    groups: list
    attributes: Dict[str, Any]

class SAMLProvider:
    """SAML 2.0 authentication provider."""
    
    def __init__(self, organization_id: str):
        self.organization_id = organization_id
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load SAML settings for organization."""
        # Load from database based on organization_id
        # This would be configured per-organization
        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": f"https://api.marketingagent.com/saml/{self.organization_id}/metadata",
                "assertionConsumerService": {
                    "url": f"https://api.marketingagent.com/api/auth/saml/{self.organization_id}/acs",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": f"https://api.marketingagent.com/api/auth/saml/{self.organization_id}/sls",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
            },
            "idp": {
                # Loaded from organization configuration
                "entityId": "",
                "singleSignOnService": {
                    "url": "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": ""
            }
        }
    
    def prepare_request(self, request) -> Dict:
        """Prepare request data for SAML processing."""
        return {
            'https': 'on' if request.url.scheme == 'https' else 'off',
            'http_host': request.headers.get('host'),
            'script_name': request.url.path,
            'get_data': dict(request.query_params),
            'post_data': dict(request.form()) if request.method == "POST" else {}
        }
    
    def get_auth(self, request) -> OneLogin_Saml2_Auth:
        """Get SAML auth instance."""
        req = self.prepare_request(request)
        return OneLogin_Saml2_Auth(req, self.settings)
    
    def get_login_url(self, request, return_to: Optional[str] = None) -> str:
        """Get SAML login URL."""
        auth = self.get_auth(request)
        return auth.login(return_to=return_to)
    
    def process_response(self, request) -> SAMLUser:
        """Process SAML response and extract user data."""
        auth = self.get_auth(request)
        auth.process_response()
        
        errors = auth.get_errors()
        if errors:
            raise SAMLException(f"SAML errors: {', '.join(errors)}")
        
        if not auth.is_authenticated():
            raise SAMLException("SAML authentication failed")
        
        attributes = auth.get_attributes()
        
        return SAMLUser(
            email=auth.get_nameid(),
            name=self._extract_name(attributes),
            saml_id=auth.get_nameid(),
            idp_name=self._get_idp_name(),
            groups=attributes.get('groups', []),
            attributes=attributes
        )
    
    def _extract_name(self, attributes: Dict) -> str:
        """Extract user name from SAML attributes."""
        # Try common attribute names
        for key in ['name', 'displayName', 'cn', 'fullName']:
            if key in attributes:
                return attributes[key][0]
        
        # Fallback to email
        return attributes.get('email', ['Unknown'])[0]
    
    def _get_idp_name(self) -> str:
        """Get Identity Provider name."""
        return self.settings.get('idp', {}).get('entityId', 'unknown')


class SAMLException(Exception):
    """SAML-related exception."""
    pass
```

#### 2.2.2 Auth API Extensions

**Modify:** [`backend/app/api/auth.py`](backend/app/api/auth.py)

```python
# Add to existing auth.py

from ..services.security.saml_provider import SAMLProvider, SAMLException
from ..services.security.oauth_provider import OAuthProvider
from ..services.security.scim_handler import SCIMHandler

# === SSO Endpoints ===

@router.get("/saml/{organization_id}/login")
async def saml_login(
    organization_id: str,
    return_to: Optional[str] = None,
    request: Request = None
):
    """
    Initiate SAML login flow.
    
    Redirects to Identity Provider for authentication.
    """
    try:
        provider = SAMLProvider(organization_id)
        login_url = provider.get_login_url(request, return_to)
        return RedirectResponse(url=login_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SAML configuration error: {str(e)}"
        )


@router.post("/saml/{organization_id}/acs")
async def saml_acs(
    organization_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """
    SAML Assertion Consumer Service.
    
    Receives authentication response from Identity Provider.
    """
    try:
        provider = SAMLProvider(organization_id)
        saml_user = provider.process_response(request)
        
        # Find or create user
        user_repo = UserRepository(session)
        user = await user_repo.get_by_email(saml_user.email)
        
        if not user:
            # Create new user from SAML data
            user = await user_repo.create_sso_user(
                email=saml_user.email,
                name=saml_user.name,
                organization_id=organization_id,
                saml_id=saml_user.saml_id,
                idp_name=saml_user.idp_name,
                role=_map_saml_groups_to_role(saml_user.groups)
            )
        
        # Create access token
        access_token = create_access_token(
            data={
                "sub": user.id,
                "email": user.email,
                "org_id": organization_id,
                "auth_method": "saml"
            }
        )
        
        # Log the SSO login
        await audit_logger.log_login(
            user_id=user.id,
            user_email=user.email,
            organization_id=organization_id,
            request=request,
            changes_summary=f"SSO login via {saml_user.idp_name}"
        )
        
        # Redirect to frontend with token
        frontend_url = get_settings().frontend_url
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?token={access_token}"
        )
        
    except SAMLException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"SAML authentication failed: {str(e)}"
        )


def _map_saml_groups_to_role(groups: list) -> UserRole:
    """Map SAML groups to application roles."""
    group_str = ','.join(groups).lower()
    
    if 'admin' in group_str or 'administrator' in group_str:
        return UserRole.ADMIN
    elif 'editor' in group_str or 'creator' in group_str:
        return UserRole.EDITOR
    else:
        return UserRole.VIEWER


# === OAuth Endpoints ===

@router.get("/oauth/{provider}/login")
async def oauth_login(
    provider: str,  # google, microsoft, github
    organization_id: str,
    return_to: Optional[str] = None
):
    """Initiate OAuth login flow."""
    oauth = OAuthProvider(provider)
    auth_url = oauth.get_authorization_url(organization_id, return_to)
    return RedirectResponse(url=auth_url)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session)
):
    """OAuth callback handler."""
    oauth = OAuthProvider(provider)
    oauth_user = await oauth.process_callback(code, state)
    
    # Similar to SAML - find/create user and issue token
    # ... implementation


# === SCIM Endpoints (for user provisioning) ===

@router.post("/scim/v2/{organization_id}/Users")
async def scim_create_user(
    organization_id: str,
    user_data: SCIMUserRequest,
    request: Request
):
    """SCIM endpoint for creating users (auto-provisioning)."""
    # Verify SCIM authentication
    if not _verify_scim_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    scim = SCIMHandler(organization_id)
    return await scim.create_user(user_data)


@router.put("/scim/v2/{organization_id}/Users/{user_id}")
async def scim_update_user(
    organization_id: str,
    user_id: str,
    user_data: SCIMUserRequest,
    request: Request
):
    """SCIM endpoint for updating users."""
    if not _verify_scim_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    scim = SCIMHandler(organization_id)
    return await scim.update_user(user_id, user_data)


@router.delete("/scim/v2/{organization_id}/Users/{user_id}")
async def scim_delete_user(
    organization_id: str,
    user_id: str,
    request: Request
):
    """SCIM endpoint for deactivating users."""
    if not _verify_scim_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    scim = SCIMHandler(organization_id)
    return await scim.deactivate_user(user_id)


def _verify_scim_auth(request: Request) -> bool:
    """Verify SCIM request authentication."""
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return False
    
    # Verify bearer token against stored SCIM token
    # Implementation depends on organization configuration
    return True
```

#### 2.2.3 User Model Extensions

**Modify:** [`backend/app/models/user.py`](backend/app/models/user.py)

```python
# Add to User model

class User(Base):
    # ... existing fields ...
    
    # SSO fields
    saml_id = Column(String(255), nullable=True, index=True)
    idp_name = Column(String(100), nullable=True)  # e.g., "okta", "auth0"
    oauth_provider = Column(String(50), nullable=True)  # e.g., "google", "microsoft"
    oauth_subject = Column(String(255), nullable=True)
    
    # MFA fields
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)  # Encrypted TOTP secret
    mfa_backup_codes = Column(JSON, default=list)  # Hashed backup codes
    
    # Security fields
    last_login_at = Column(DateTime, nullable=True)
    last_password_change = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_history = Column(JSON, default=list)  # Last 12 password hashes
    
    # Session management
    active_sessions = Column(JSON, default=list)  # List of active session IDs
    
    async def check_mfa(self, token: str) -> bool:
        """Verify MFA TOTP token."""
        if not self.mfa_enabled or not self.mfa_secret:
            return False
        
        import pyotp
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token)
    
    async def record_login(self, session_id: str, ip_address: str):
        """Record successful login."""
        self.last_login_at = datetime.utcnow()
        self.failed_login_attempts = 0
        self.locked_until = None
        
        # Add session
        sessions = self.active_sessions or []
        sessions.append({
            "session_id": session_id,
            "ip_address": ip_address,
            "started_at": datetime.utcnow().isoformat()
        })
        # Keep only last 10 sessions
        self.active_sessions = sessions[-10:]
    
    async def record_failed_login(self):
        """Record failed login attempt."""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
```

### 2.3 GDPR/CCPA Compliance

#### 2.3.1 Consent Management

**New Model:** [`backend/app/models/consent.py`](backend/app/models/consent.py)

```python
"""
Consent Management Models for GDPR/CCPA Compliance
"""
from enum import Enum
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Index, Text
from .base import Base

class ConsentType(str, Enum):
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    THIRD_PARTY = "third_party"
    EMAIL = "email"
    TRACKING = "tracking"

class ConsentStatus(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"

class ConsentRecord(Base):
    """
    Records of user consent for GDPR compliance.
    
    Requirements:
    - Record when consent was given
    - Record what user was told
    - Allow withdrawal
    - Maintain audit trail
    """
    
    user_id = Column(String(12), ForeignKey("users.id"), nullable=False)
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    
    consent_type = Column(String(50), nullable=False)  # ConsentType
    status = Column(String(50), nullable=False)  # ConsentStatus
    
    # Consent context
    consent_version = Column(String(20), nullable=False)  # Version of consent text
    consent_text = Column(Text, nullable=False)  # What user agreed to
    privacy_policy_version = Column(String(20), nullable=False)
    
    # Mechanism
    given_via = Column(String(50), nullable=False)  # e.g., "web_form", "api", "mobile_app"
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Withdrawal
    withdrawn_at = Column(DateTime, nullable=True)
    withdrawal_reason = Column(Text, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_consent_user_type', 'user_id', 'consent_type'),
        Index('ix_consent_org', 'organization_id', 'consent_type'),
    )


class DataRequest(Base):
    """
    Data Subject Access Request (DSAR) tracking.
    
    GDPR Article 15 - Right of access
    GDPR Article 17 - Right to erasure
    CCPA - Right to know/delete
    """
    
    REQUEST_TYPE_ACCESS = "access"
    REQUEST_TYPE_DELETION = "deletion"
    REQUEST_TYPE_PORTABILITY = "portability"
    REQUEST_TYPE_RECTIFICATION = "rectification"
    
    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_REJECTED = "rejected"
    
    user_id = Column(String(12), ForeignKey("users.id"), nullable=False)
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    
    request_type = Column(String(50), nullable=False)
    status = Column(String(50), default=STATUS_PENDING)
    
    # Request details
    request_reason = Column(Text, nullable=True)
    verification_method = Column(String(100), nullable=True)
    
    # Processing
    assigned_to = Column(String(12), nullable=True)  # Admin user ID
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    data_export_url = Column(String(500), nullable=True)  # S3 URL for export
    data_summary = Column(JSON, nullable=True)  # Summary of what was found
    
    # Rejection
    rejection_reason = Column(Text, nullable=True)
    
    # Compliance tracking
    deadline_at = Column(DateTime, nullable=False)  # 30 days from request
    days_remaining = Column(Integer, nullable=True)
```

#### 2.3.2 GDPR Handler Service

**New File:** [`backend/app/services/privacy/gdpr_handler.py`](backend/app/services/privacy/gdpr_handler.py)

```python
"""
GDPR Compliance Handler

Implements:
- Right to access (Article 15)
- Right to rectification (Article 16)
- Right to erasure (Article 17)
- Right to data portability (Article 20)
- Right to object (Article 21)
"""
import json
import zipfile
import io
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.consent import ConsentRecord, DataRequest
from ...models.user import User
from ...models.campaign import Campaign
from ...models.asset import Asset
from ...services.storage import StorageService

class GDPRHandler:
    """Handle GDPR data subject requests."""
    
    def __init__(self, session: AsyncSession, storage: StorageService):
        self.session = session
        self.storage = storage
    
    async def create_data_request(
        self,
        user_id: str,
        organization_id: str,
        request_type: str,
        reason: str = None
    ) -> DataRequest:
        """Create a new data subject request."""
        
        # Calculate deadline (30 days)
        deadline = datetime.utcnow() + timedelta(days=30)
        
        request = DataRequest(
            user_id=user_id,
            organization_id=organization_id,
            request_type=request_type,
            request_reason=reason,
            deadline_at=deadline,
            days_remaining=30
        )
        
        self.session.add(request)
        await self.session.commit()
        
        # Queue for processing
        await self._queue_for_processing(request)
        
        return request
    
    async def export_user_data(self, user_id: str) -> str:
        """
        Export all user data for portability request.
        
        Returns S3 URL to downloadable ZIP file.
        """
        user = await self.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        # Collect all user data
        export_data = {
            "user_profile": await self._export_user_profile(user),
            "campaigns": await self._export_user_campaigns(user_id),
            "assets": await self._export_user_assets(user_id),
            "consent_records": await self._export_consent_records(user_id),
            "audit_logs": await self._export_audit_logs(user_id),
            "conversations": await self._export_conversations(user_id),
        }
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for section, data in export_data.items():
                zip_file.writestr(
                    f"{section}.json",
                    json.dumps(data, indent=2, default=str)
                )
        
        zip_buffer.seek(0)
        
        # Upload to S3
        filename = f"exports/{user_id}/data_export_{datetime.utcnow().isoformat()}.zip"
        url = await self.storage.upload_file(
            file_data=zip_buffer.getvalue(),
            filename=filename,
            content_type="application/zip"
        )
        
        return url
    
    async def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Delete user data (Right to be forgotten).
        
        Returns summary of what was deleted vs anonymized.
        """
        summary = {
            "deleted": [],
            "anonymized": [],
            "retained": []
        }
        
        # Delete campaigns created by user
        campaigns = await self._get_user_campaigns(user_id)
        for campaign in campaigns:
            # Check if campaign has legal retention requirements
            if await self._has_retention_requirement(campaign):
                # Anonymize instead of delete
                await self._anonymize_campaign(campaign)
                summary["anonymized"].append(f"campaign:{campaign.id}")
            else:
                await self.session.delete(campaign)
                summary["deleted"].append(f"campaign:{campaign.id}")
        
        # Delete assets
        assets = await self._get_user_assets(user_id)
        for asset in assets:
            await self.session.delete(asset)
            summary["deleted"].append(f"asset:{asset.id}")
        
        # Anonymize user record (keep for audit/legal)
        await self._anonymize_user(user_id)
        summary["anonymized"].append(f"user:{user_id}")
        
        # Delete PII from conversations
        await self._anonymize_conversations(user_id)
        summary["anonymized"].append("conversations")
        
        await self.session.commit()
        
        return summary
    
    async def _anonymize_user(self, user_id: str):
        """Anonymize user record while keeping for audit."""
        user = await self.session.get(User, user_id)
        if user:
            user.email = f"anonymized_{user_id}@deleted.local"
            user.name = "Deleted User"
            user.password_hash = None
            user.saml_id = None
            user.oauth_subject = None
            user.preferences = {}
            user.is_active = False
    
    async def _has_retention_requirement(self, campaign) -> bool:
        """Check if campaign has legal/financial retention requirements."""
        # Check if campaign has associated financial records
        # Check if campaign is part of legal hold
        # Default: no retention for marketing campaigns
        return False
    
    async def _queue_for_processing(self, request: DataRequest):
        """Queue data request for async processing."""
        from ..tasks.privacy_tasks import process_data_request
        process_data_request.delay(request.id)
```

---

## 3. Customer Data Platform Integration

### 3.1 Customer Profile Model

**New Model:** [`backend/app/models/customer.py`](backend/app/models/customer.py)

```python
"""
Customer Data Platform Models

Unified customer profiles with identity resolution,
behavioral tracking, and segmentation.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, JSON, Float, Index, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from .base import Base

class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHURNED = "churned"
    PROSPECT = "prospect"

class Customer(Base):
    """
    Unified Customer Profile
    
    The central entity in the CDP - represents a single person
    across all touchpoints and devices.
    """
    
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    
    # Identity
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    
    # Profile data
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(255), nullable=True)
    
    # Demographics
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    language = Column(String(10), nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # Location
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
    # Business (B2B)
    company = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    
    # Status
    status = Column(String(50), default=CustomerStatus.PROSPECT)
    lifecycle_stage = Column(String(50), nullable=True)  # lead, qualified, customer, advocate
    
    # Engagement
    first_seen_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    first_touch_source = Column(String(100), nullable=True)
    last_touch_source = Column(String(100), nullable=True)
    
    # Computed scores
    engagement_score = Column(Float, default=0.0)
    churn_risk_score = Column(Float, nullable=True)
    ltv_prediction = Column(Float, nullable=True)
    lead_score = Column(Float, nullable=True)
    
    # Identity graph (linked identifiers)
    # {
    #     "anonymous_ids": ["anon_123", "anon_456"],
    #     "device_ids": ["device_abc"],
    #     "crm_ids": {"salesforce": "001...", "hubspot": "123..."},
    #     "ad_ids": {"facebook": "fb.123", "google": "ga.456"}
    # }
    identity_graph = Column(JSONB, default=dict)
    
    # Unified traits (merged from all sources)
    traits = Column(JSONB, default=dict)
    
    # Consent
    consent = Column(JSONB, default=dict)
    
    # Metadata
    source = Column(String(100), nullable=True)  # Where profile was created
    merged_from = Column(ARRAY(String), default=list)  # IDs this profile was merged from
    
    __table_args__ = (
        Index('ix_customer_org_email', 'organization_id', 'email'),
        Index('ix_customer_org_status', 'organization_id', 'status'),
        Index('ix_customer_engagement', 'organization_id', 'engagement_score'),
    )


class CustomerEvent(Base):
    """
    Customer behavioral events.
    
    Stores all customer interactions across channels.
    Uses TimescaleDB hypertable for time-series optimization.
    """
    
    __tablename__ = "customer_events"
    
    # Time-series data
    timestamp = Column(DateTime, nullable=False)
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=False)
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    
    # Event classification
    event_type = Column(String(100), nullable=False)  # page_view, click, purchase, etc.
    event_name = Column(String(255), nullable=False)
    
    # Source
    channel = Column(String(50), nullable=True)  # web, mobile, email, social
    source = Column(String(100), nullable=True)  # google, facebook, direct
    campaign_id = Column(String(12), nullable=True)
    
    # Context
    url = Column(String(2000), nullable=True)
    referrer = Column(String(2000), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Event data
    properties = Column(JSONB, default=dict)
    
    # Session
    session_id = Column(String(255), nullable=True)
    
    __table_args__ = (
        Index('ix_events_customer_time', 'customer_id', 'timestamp'),
        Index('ix_events_org_time', 'organization_id', 'timestamp'),
        Index('ix_events_type_time', 'event_type', 'timestamp'),
    )


class CustomerSegment(Base):
    """
    Dynamic customer segments.
    
    Segments are defined by rules and computed dynamically.
    """
    
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Segment definition (rules)
    # {
    #     "conditions": [
    #         {"field": "engagement_score", "operator": ">", "value": 50},
    #         {"field": "status", "operator": "=", "value": "active"}
    #     ],
    #     "match_type": "all"  # or "any"
    # }
    definition = Column(JSONB, nullable=False)
    
    # Computed stats
    customer_count = Column(Integer, default=0)
    last_computed_at = Column(DateTime, nullable=True)
    
    # Usage
    is_system = Column(Boolean, default=False)  # Built-in segments
    used_in_campaigns = Column(ARRAY(String), default=list)
    
    # Auto-refresh
    refresh_frequency = Column(String(20), default="daily")  # realtime, hourly, daily


class IdentityGraph(Base):
    """
    Identity resolution graph.
    
    Tracks relationships between identifiers to enable
    cross-device and cross-channel identity resolution.
    """
    
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    
    # Primary customer
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=False)
    
    # Linked identifier
    identifier_type = Column(String(50), nullable=False)  # email, phone, device_id, anonymous_id
    identifier_value = Column(String(500), nullable=False)
    
    # Link metadata
    link_confidence = Column(Float, default=1.0)  # 0.0 - 1.0
    link_method = Column(String(50), nullable=True)  # deterministic, probabilistic, manual
    linked_at = Column(DateTime, default=datetime.utcnow)
    
    # Source of the link
    source = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index('ix_identity_org_type_value', 'organization_id', 'identifier_type', 'identifier_value'),
    )
```

### 3.2 Identity Resolution Algorithm

**New File:** [`backend/app/services/cdp/identity_resolver.py`](backend/app/services/cdp/identity_resolver.py)

```python
"""
Identity Resolution Service

Resolves multiple identifiers to a single customer profile using:
1. Deterministic matching (exact matches on email, phone, etc.)
2. Probabilistic matching (fuzzy matching, behavioral similarity)
3. Graph-based resolution (connected components)
"""
from typing import Optional, List, Dict, Any, Set
from datetime import datetime
from collections import defaultdict
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...models.customer import Customer, IdentityGraph, CustomerEvent

class IdentityResolver:
    """Resolve identities across touchpoints."""
    
    # Confidence thresholds
    DETERMINISTIC_CONFIDENCE = 1.0
    PROBABILISTIC_CONFIDENCE = 0.75
    MIN_CONFIDENCE = 0.5
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def resolve_event(
        self,
        organization_id: str,
        event_data: Dict[str, Any]
    ) -> Optional[Customer]:
        """
        Resolve a customer from event data.
        
        Args:
            event_data: Contains identifiers like email, phone, device_id, etc.
        
        Returns:
            Customer if resolved, None if new
        """
        identifiers = self._extract_identifiers(event_data)
        
        if not identifiers:
            return None
        
        # Try deterministic matching first
        customer = await self._deterministic_match(organization_id, identifiers)
        if customer:
            return customer
        
        # Try probabilistic matching
        customer = await self._probabilistic_match(organization_id, identifiers, event_data)
        if customer:
            return customer
        
        # No match - new customer
        return None
    
    async def merge_profiles(
        self,
        primary_customer_id: str,
        secondary_customer_id: str,
        reason: str = "identity_resolution"
    ) -> Customer:
        """
        Merge two customer profiles.
        
        All data from secondary is merged into primary.
        Secondary is then deleted.
        """
        primary = await self.session.get(Customer, primary_customer_id)
        secondary = await self.session.get(Customer, secondary_customer_id)
        
        if not primary or not secondary:
            raise ValueError("One or both customers not found")
        
        # Merge identity graphs
        await self._merge_identity_graphs(primary, secondary)
        
        # Merge traits (primary takes precedence)
        merged_traits = {**secondary.traits, **primary.traits}
        primary.traits = merged_traits
        
        # Update engagement scores
        primary.engagement_score = max(
            primary.engagement_score or 0,
            secondary.engagement_score or 0
        )
        
        # Merge source tracking
        if secondary.source and not primary.source:
            primary.source = secondary.source
        
        # Track merge
        if not primary.merged_from:
            primary.merged_from = []
        primary.merged_from.append(secondary.id)
        
        # Update all events to point to primary
        await self._reassign_events(secondary.id, primary.id)
        
        # Delete secondary
        await self.session.delete(secondary)
        await self.session.commit()
        
        return primary
    
    def _extract_identifiers(self, event_data: Dict) -> Dict[str, str]:
        """Extract all identifiers from event data."""
        identifiers = {}
        
        # Standard identifiers
        for key in ['email', 'phone', 'user_id', 'device_id', 'anonymous_id']:
            if key in event_data and event_data[key]:
                identifiers[key] = str(event_data[key]).lower().strip()
        
        # External IDs
        if 'external_ids' in event_data:
            identifiers.update(event_data['external_ids'])
        
        return identifiers
    
    async def _deterministic_match(
        self,
        organization_id: str,
        identifiers: Dict[str, str]
    ) -> Optional[Customer]:
        """Try exact deterministic matching."""
        
        # Match by email
        if 'email' in identifiers:
            result = await self.session.execute(
                select(Customer).where(
                    and_(
                        Customer.organization_id == organization_id,
                        Customer.email == identifiers['email']
                    )
                )
            )
            customer = result.scalar_one_or_none()
            if customer:
                return customer
        
        # Match by phone
        if 'phone' in identifiers:
            # Normalize phone number
            phone = self._normalize_phone(identifiers['phone'])
            result = await self.session.execute(
                select(Customer).where(
                    and_(
                        Customer.organization_id == organization_id,
                        Customer.phone == phone
                    )
                )
            )
            customer = result.scalar_one_or_none()
            if customer:
                return customer
        
        # Match by identity graph
        for id_type, id_value in identifiers.items():
            result = await self.session.execute(
                select(IdentityGraph).where(
                    and_(
                        IdentityGraph.organization_id == organization_id,
                        IdentityGraph.identifier_type == id_type,
                        IdentityGraph.identifier_value == id_value
                    )
                )
            )
            graph_entry = result.scalar_one_or_none()
            if graph_entry:
                return await self.session.get(Customer, graph_entry.customer_id)
        
        return None
    
    async def _probabilistic_match(
        self,
        organization_id: str,
        identifiers: Dict[str, str],
        event_data: Dict
    ) -> Optional[Customer]:
        """
        Try probabilistic/fuzzy matching.
        
        Uses behavioral similarity and fuzzy field matching.
        """
        candidates = []
        
        # Find candidates by partial email match
        if 'email' in identifiers:
            email = identifiers['email']
            domain = email.split('@')[-1]
            
            # Same domain emails
            result = await self.session.execute(
                select(Customer).where(
                    and_(
                        Customer.organization_id == organization_id,
                        Customer.email.like(f'%@{domain}')
                    )
                )
            )
            candidates.extend(result.scalars().all())
        
        # Score candidates
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            score = self._calculate_similarity(candidate, identifiers, event_data)
            if score > best_score and score >= self.MIN_CONFIDENCE:
                best_score = score
                best_match = candidate
        
        return best_match
    
    def _calculate_similarity(
        self,
        customer: Customer,
        identifiers: Dict,
        event_data: Dict
    ) -> float:
        """Calculate similarity score between customer and event."""
        scores = []
        
        # Email similarity (fuzzy match)
        if 'email' in identifiers and customer.email:
            scores.append(self._email_similarity(identifiers['email'], customer.email))
        
        # Phone similarity
        if 'phone' in identifiers and customer.phone:
            scores.append(1.0 if identifiers['phone'] == customer.phone else 0.0)
        
        # Location similarity
        if 'ip_address' in event_data:
            # Check if IP is in same range as previous events
            pass  # Implementation depends on GeoIP
        
        # Device similarity
        if 'device_fingerprint' in event_data:
            # Compare device fingerprints
            pass
        
        # Behavioral similarity
        if 'user_agent' in event_data and customer.traits.get('user_agent'):
            scores.append(0.5 if event_data['user_agent'] == customer.traits['user_agent'] else 0.0)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for comparison."""
        # Remove all non-numeric characters
        return ''.join(c for c in phone if c.isdigit())
    
    def _email_similarity(self, email1: str, email2: str) -> float:
        """Calculate email similarity (1.0 = exact match)."""
        if email1 == email2:
            return 1.0
        
        # Check for common variations
        local1, domain1 = email1.rsplit('@', 1)
        local2, domain2 = email2.rsplit('@', 1)
        
        if domain1 != domain2:
            return 0.0
        
        # Gmail ignores dots and everything after +
        if domain1 in ['gmail.com', 'googlemail.com']:
            norm1 = local1.replace('.', '').split('+')[0]
            norm2 = local2.replace('.', '').split('+')[0]
            return 1.0 if norm1 == norm2 else 0.0
        
        return 0.0
    
    async def _merge_identity_graphs(self, primary: Customer, secondary: Customer):
        """Merge identity graphs from secondary into primary."""
        # Get all secondary identifiers
        result = await self.session.execute(
            select(IdentityGraph).where(
                IdentityGraph.customer_id == secondary.id
            )
        )
        secondary_graphs = result.scalars().all()
        
        for graph in secondary_graphs:
            # Check if primary already has this identifier
            existing = await self.session.execute(
                select(IdentityGraph).where(
                    and_(
                        IdentityGraph.customer_id == primary.id,
                        IdentityGraph.identifier_type == graph.identifier_type,
                        IdentityGraph.identifier_value == graph.identifier_value
                    )
                )
            )
            
            if not existing.scalar_one_or_none():
                # Create new link
                new_graph = IdentityGraph(
                    organization_id=graph.organization_id,
                    customer_id=primary.id,
                    identifier_type=graph.identifier_type,
                    identifier_value=graph.identifier_value,
                    link_confidence=graph.link_confidence,
                    link_method=graph.link_method,
                    source=f"merge_from_{secondary.id}"
                )
                self.session.add(new_graph)
    
    async def _reassign_events(self, from_customer_id: str, to_customer_id: str):
        """Reassign all events from one customer to another."""
        result = await self.session.execute(
            select(CustomerEvent).where(
                CustomerEvent.customer_id == from_customer_id
            )
        )
        events = result.scalars().all()
        
        for event in events:
            event.customer_id = to_customer_id
```

### 3.3 Event Processing Pipeline

**New File:** [`backend/app/services/cdp/event_processor.py`](backend/app/services/cdp/event_processor.py)

```python
"""
Real-time Event Processing Pipeline

Processes customer events in real-time:
1. Validation
2. Enrichment
3. Identity resolution
4. Profile updates
5. Segment evaluation
6. Trigger evaluation
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from .identity_resolver import IdentityResolver
from .segment_engine import SegmentEngine
from ...models.customer import Customer, CustomerEvent

@dataclass
class ProcessingResult:
    success: bool
    customer_id: Optional[str]
    events_processed: int
    errors: List[str]

class EventProcessor:
    """Process customer events in real-time."""
    
    def __init__(self, session, redis_client=None):
        self.session = session
        self.redis = redis_client
        self.resolver = IdentityResolver(session)
        self.segment_engine = SegmentEngine(session)
    
    async def process_event(
        self,
        organization_id: str,
        event_data: Dict[str, Any]
    ) -> ProcessingResult:
        """
        Process a single event through the pipeline.
        
        Pipeline stages:
        1. Validate
        2. Enrich
        3. Resolve identity
        4. Store event
        5. Update profile
        6. Evaluate segments
        7. Check triggers
        """
        errors = []
        
        try:
            # Stage 1: Validate
            if not self._validate_event(event_data):
                return ProcessingResult(
                    success=False,
                    customer_id=None,
                    events_processed=0,
                    errors=["Event validation failed"]
                )
            
            # Stage 2: Enrich
            event_data = await self._enrich_event(event_data)
            
            # Stage 3: Resolve identity
            customer = await self.resolver.resolve_event(organization_id, event_data)
            
            if customer:
                customer_id = customer.id
            else:
                # Create new customer
                customer = await self._create_customer(organization_id, event_data)
                customer_id = customer.id
            
            # Stage 4: Store event
            event = await self._store_event(organization_id, customer_id, event_data)
            
            # Stage 5: Update profile
            await self._update_profile(customer, event_data)
            
            # Stage 6: Evaluate segments (async)
            asyncio.create_task(
                self.segment_engine.evaluate_customer(organization_id, customer_id)
            )
            
            # Stage 7: Check triggers (async)
            asyncio.create_task(
                self._check_triggers(organization_id, customer_id, event)
            )
            
            return ProcessingResult(
                success=True,
                customer_id=customer_id,
                events_processed=1,
                errors=[]
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                customer_id=None,
                events_processed=0,
                errors=[str(e)]
            )
    
    async def process_batch(
        self,
        organization_id: str,
        events: List[Dict[str, Any]]
    ) -> ProcessingResult:
        """Process a batch of events."""
        processed = 0
        errors = []
        last_customer_id = None
        
        for event_data in events:
            result = await self.process_event(organization_id, event_data)
            if result.success:
                processed += 1
                last_customer_id = result.customer_id
            else:
                errors.extend(result.errors)
        
        return ProcessingResult(
            success=processed > 0,
            customer_id=last_customer_id,
            events_processed=processed,
            errors=errors
        )
    
    def _validate_event(self, event_data: Dict) -> bool:
        """Validate event structure."""
        required = ['event_type', 'event_name', 'timestamp']
        return all(field in event_data for field in required)
    
    async def _enrich_event(self, event_data: Dict) -> Dict:
        """Enrich event with additional data."""
        enriched = event_data.copy()
        
        # Add processing timestamp
        enriched['processed_at'] = datetime.utcnow().isoformat()
        
        # GeoIP enrichment
        if 'ip_address' in enriched:
            geo_data = await self._get_geoip(enriched['ip_address'])
            enriched['geo'] = geo_data
        
        # Device parsing
        if 'user_agent' in enriched:
            device_data = self._parse_user_agent(enriched['user_agent'])
            enriched['device'] = device_data
        
        # UTM parsing
        if 'url' in enriched:
            utm_data = self._parse_utm_parameters(enriched['url'])
            enriched['utm'] = utm_data
        
        return enriched
    
    async def _create_customer(
        self,
        organization_id: str,
        event_data: Dict
    ) -> Customer:
        """Create a new customer from event data."""
        customer = Customer(
            organization_id=organization_id,
            email=event_data.get('email'),
            phone=event_data.get('phone'),
            first_name=event_data.get('first_name'),
            last_name=event_data.get('last_name'),
            source=event_data.get('source', 'unknown'),
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            first_touch_source=event_data.get('source'),
            last_touch_source=event_data.get('source'),
            traits=event_data.get('traits', {})
        )
        
        self.session.add(customer)
        await self.session.commit()
        
        # Create identity graph entries
        for key in ['email', 'phone', 'device_id', 'anonymous_id']:
            if key in event_data and event_data[key]:
                from ...models.customer import IdentityGraph
                graph = IdentityGraph(
                    organization_id=organization_id,
                    customer_id=customer.id,
                    identifier_type=key,
                    identifier_value=str(event_data[key]),
                    link_confidence=1.0,
                    link_method='deterministic',
                    source='event_ingestion'
                )
                self.session.add(graph)
        
        await self.session.commit()
        return customer
    
    async def _store_event(
        self,
        organization_id: str,
        customer_id: str,
        event_data: Dict
    ) -> CustomerEvent:
        """Store the event in the database."""
        event = CustomerEvent(
            timestamp=datetime.fromisoformat(event_data['timestamp']),
            customer_id=customer_id,
            organization_id=organization_id,
            event_type=event_data['event_type'],
            event_name=event_data['event_name'],
            channel=event_data.get('channel'),
            source=event_data.get('source'),
            campaign_id=event_data.get('campaign_id'),
            url=event_data.get('url'),
            referrer=event_data.get('referrer'),
            ip_address=event_data.get('ip_address'),
            user_agent=event_data.get('user_agent'),
            properties=event_data.get('properties', {}),
            session_id=event_data.get('session_id')
        )
        
        self.session.add(event)
        await self.session.commit()
        
        return event
    
    async def _update_profile(self, customer: Customer, event_data: Dict):
        """Update customer profile based on event."""
        customer.last_seen_at = datetime.utcnow()
        customer.last_touch_source = event_data.get('source')
        
        # Update engagement score
        customer.engagement_score = self._calculate_engagement(customer, event_data)
        
        # Update traits
        if 'traits' in event_data:
            customer.traits.update(event_data['traits'])
        
        await self.session.commit()
    
    def _calculate_engagement(self, customer: Customer, event_data: Dict) -> float:
        """Calculate updated engagement score."""
        # Simple scoring model - can be enhanced with ML
        base_score = customer.engagement_score or 0
        
        # Event type weights
        weights = {
            'page_view': 1,
            'click': 2,
            'form_submit': 5,
            'purchase': 10,
            'email_open': 3,
            'email_click': 5
        }
        
        weight = weights.get(event_data['event_type'], 1)
        
        # Decay old score
        decayed = base_score * 0.95
        
        # Add new score
        new_score = min(100, decayed + weight)
        
        return new_score
    
    async def _check_triggers(
        self,
        organization_id: str,
        customer_id: str,
        event: CustomerEvent
    ):
        """Check if any automation triggers should fire."""
        # Implementation depends on automation engine
        pass
    
    async def _get_geoip(self, ip_address: str) -> Dict:
        """Get GeoIP data for IP address."""
        # Implementation using MaxMind GeoIP2
        return {}
    
    def _parse_user_agent(self, user_agent: str) -> Dict:
        """Parse user agent string."""
        # Implementation using user-agents library
        return {}
    
    def _parse_utm_parameters(self, url: str) -> Dict:
        """Extract UTM parameters from URL."""
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        return {
            'utm_source': params.get('utm_source', [None])[0],
            'utm_medium': params.get('utm_medium', [None])[0],
            'utm_campaign': params.get('utm_campaign', [None])[0],
            'utm_term': params.get('utm_term', [None])[0],
            'utm_content': params.get('utm_content', [None])[0]
        }
```

---

## 4. Autonomous Optimization Engine

### 4.1 A/B Testing Framework

**New Models:** [`backend/app/models/experiment.py`](backend/app/models/experiment.py)

```python
"""
Experimentation Models for A/B Testing
"""
from enum import Enum
from sqlalchemy import Column, String, DateTime, JSON, Float, Integer, Boolean, Text
from .base import Base

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class ExperimentType(str, Enum):
    AB_TEST = "ab_test"           # Simple A/B
    MULTIVARIATE = "multivariate" # Multiple variables
    SPLIT_URL = "split_url"       # URL redirect test
    BANDIT = "bandit"             # Multi-armed bandit

class Experiment(Base):
    """
    A/B Test or Multivariate Experiment
    """
    
    organization_id = Column(String(12), ForeignKey("organizations.id"), nullable=False)
    campaign_id = Column(String(12), ForeignKey("campaigns.id"), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=True)
    
    experiment_type = Column(String(50), default=ExperimentType.AB_TEST)
    status = Column(String(50), default=ExperimentStatus.DRAFT)
    
    # Targeting
    target_segment_id = Column(String(12), nullable=True)  # Optional segment targeting
    traffic_allocation = Column(Float, default=1.0)  # % of traffic included
    
    # Variants
    # {
    #     "control": {
    #         "id": "control",
    #         "name": "Control",
    #         "traffic_allocation": 0.5,
    #         "content": {...}
    #     },
    #     "variant_a": {
    #         "id": "variant_a",
    #         "name": "Headline Variant",
    #         "traffic_allocation": 0.5,
    #         "content": {...}
    #     }
    # }
    variants = Column(JSON, nullable=False)
    
    # Metrics
    primary_metric = Column(String(100), nullable=False)  # e.g., "conversion_rate"
    secondary_metrics = Column(JSON, default=list)  # ["bounce_rate", "time_on_page"]
    
    # Statistical parameters
    confidence_level = Column(Float, default=0.95)  # 95%
    minimum_detectable_effect = Column(Float, default=0.05)  # 5%
    required_sample_size = Column(Integer, nullable=True)
    
    # Schedule
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Auto-optimization
    auto_winner_enabled = Column(Boolean, default=False)
    auto_winner_threshold = Column(Float, default=0.99)  # 99% confidence
    
    # Results
    winner_variant_id = Column(String(50), nullable=True)
    results_summary = Column(JSON, nullable=True)
    
    # Audit
    started_by = Column(String(12), nullable=True)
    stopped_by = Column(String(12), nullable=True)


class ExperimentAssignment(Base):
    """
    Tracks which variant each user was assigned to.
    """
    
    __tablename__ = "experiment_assignments"
    
    experiment_id = Column(String(12), ForeignKey("experiments.id"), nullable=False)
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=False)
    variant_id = Column(String(50), nullable=False)
    
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    # Ensure unique assignment per customer per experiment
    __table_args__ = (
        UniqueConstraint('experiment_id', 'customer_id'),
    )


class ExperimentEvent(Base):
    """
    Events tracked for experiment analysis.
    """
    
    __tablename__ = "experiment_events"
    
    timestamp = Column(DateTime, nullable=False)
    experiment_id = Column(String(12), ForeignKey("experiments.id"), nullable=False)
    customer_id = Column(String(12), ForeignKey("customers.id"), nullable=False)
    variant_id = Column(String(50), nullable=False)
    
    event_type = Column(String(100), nullable=False)  # impression, conversion, etc.
    event_value = Column(Float, nullable=True)  # For revenue, etc.
    
    __table_args__ = (
        Index('ix_exp_event_exp_time', 'experiment_id', 'timestamp'),
        Index('ix_exp_event_customer', 'customer_id', 'experiment_id'),
    )
```

**New Service:** [`backend/app/services/experimentation/ab_test_engine.py`](backend/app/services/experimentation/ab_test_engine.py)

```python
"""
A/B Testing Engine

Manages experiment lifecycle:
- Traffic allocation
- Variant assignment
- Statistical analysis
- Winner selection
"""
import hashlib
import random
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ...models.experiment import Experiment, ExperimentStatus, ExperimentAssignment, ExperimentEvent

@dataclass
class AssignmentResult:
    experiment_id: str
    variant_id: str
    variant_name: str
    is_new_assignment: bool

@dataclass
class ExperimentResults:
    experiment_id: str
    status: str
    variants: Dict[str, Dict]
    winner: Optional[str]
    confidence: float
    is_significant: bool
    recommended_action: str

class ABTestEngine:
    """A/B testing engine with statistical analysis."""
    
    def __init__(self, session: AsyncSession, redis_client=None):
        self.session = session
        self.redis = redis_client
    
    async def assign_variant(
        self,
        experiment_id: str,
        customer_id: str
    ) -> AssignmentResult:
        """
        Assign a customer to a variant.
        
        Uses consistent hashing to ensure same customer always
        gets same variant.
        """
        # Check if already assigned
        existing = await self.session.execute(
            select(ExperimentAssignment).where(
                and_(
                    ExperimentAssignment.experiment_id == experiment_id,
                    ExperimentAssignment.customer_id == customer_id
                )
            )
        )
        assignment = existing.scalar_one_or_none()
        
        if assignment:
            experiment = await self.session.get(Experiment, experiment_id)
            variant = experiment.variants.get(assignment.variant_id)
            return AssignmentResult(
                experiment_id=experiment_id,
                variant_id=assignment.variant_id,
                variant_name=variant['name'],
                is_new_assignment=False
            )
        
        # Get experiment
        experiment = await self.session.get(Experiment, experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            raise ValueError("Experiment not found or not running")
        
        # Assign using consistent hashing
        variant_id = self._hash_assignment(customer_id, experiment.variants)
        
        # Record assignment
        assignment = ExperimentAssignment(
            experiment_id=experiment_id,
            customer_id=customer_id,
            variant_id=variant_id
        )
        self.session.add(assignment)
        await self.session.commit()
        
        # Record impression event
        await self._record_event(experiment_id, customer_id, variant_id, 'impression')
        
        variant = experiment.variants[variant_id]
        return AssignmentResult(
            experiment_id=experiment_id,
            variant_id=variant_id,
            variant_name=variant['name'],
            is_new_assignment=True
        )
    
    async def track_conversion(
        self,
        experiment_id: str,
        customer_id: str,
        event_type: str = 'conversion',
        event_value: float = None
    ):
        """Track a conversion event for a customer."""
        # Get customer's variant assignment
        result = await self.session.execute(
            select(ExperimentAssignment).where(
                and_(
                    ExperimentAssignment.experiment_id == experiment_id,
                    ExperimentAssignment.customer_id == customer_id
                )
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            return  # Customer not in experiment
        
        await self._record_event(
            experiment_id,
            customer_id,
            assignment.variant_id,
            event_type,
            event_value
        )
    
    async def get_results(self, experiment_id: str) -> ExperimentResults:
        """Calculate experiment results with statistical significance."""
        experiment = await self.session.get(Experiment, experiment_id)
        if not experiment:
            raise ValueError("Experiment not found")
        
        # Get event counts for each variant
        variant_stats = {}
        
        for variant_id in experiment.variants.keys():
            # Get impressions
            impressions_result = await self.session.execute(
                select(func.count(ExperimentEvent.id)).where(
                    and_(
                        ExperimentEvent.experiment_id == experiment_id,
                        ExperimentEvent.variant_id == variant_id,
                        ExperimentEvent.event_type == 'impression'
                    )
                )
            )
            impressions = impressions_result.scalar()
            
            # Get conversions
            conversions_result = await self.session.execute(
                select(
                    func.count(ExperimentEvent.id),
                    func.sum(ExperimentEvent.event_value)
                ).where(
                    and_(
                        ExperimentEvent.experiment_id == experiment_id,
                        ExperimentEvent.variant_id == variant_id,
                        ExperimentEvent.event_type == 'conversion'
                    )
                )
            )
            conversions, revenue = conversions_result.one()
            
            conversion_rate = conversions / impressions if impressions > 0 else 0
            
            variant_stats[variant_id] = {
                'impressions': impressions,
                'conversions': conversions,
                'conversion_rate': conversion_rate,
                'revenue': revenue or 0
            }
        
        # Calculate statistical significance
        control_id = 'control'
        control_stats = variant_stats.get(control_id)
        
        winner = None
        winner_confidence = 0
        
        if control_stats and control_stats['impressions'] > 100:
            for variant_id, stats in variant_stats.items():
                if variant_id == control_id:
                    continue
                
                if stats['impressions'] > 100:
                    confidence = self._calculate_confidence(
                        control_stats['conversions'],
                        control_stats['impressions'],
                        stats['conversions'],
                        stats['impressions']
                    )
                    
                    if confidence > winner_confidence:
                        winner_confidence = confidence
                        winner = variant_id
        
        # Determine recommended action
        is_significant = winner_confidence >= experiment.confidence_level
        
        if is_significant and winner:
            if experiment.auto_winner_enabled and winner_confidence >= experiment.auto_winner_threshold:
                recommended_action = "auto_deploy"
            else:
                recommended_action = "manual_review"
        elif self._has_sufficient_sample(experiment, variant_stats):
            recommended_action = "declare_no_difference"
        else:
            recommended_action = "continue_running"
        
        return ExperimentResults(
            experiment_id=experiment_id,
            status=experiment.status,
            variants=variant_stats,
            winner=winner,
            confidence=winner_confidence,
            is_significant=is_significant,
            recommended_action=recommended_action
        )
    
    def _hash_assignment(self, customer_id: str, variants: Dict) -> str:
        """
        Consistently assign customer to variant using hashing.
        
        This ensures the same customer always gets the same variant
        while maintaining the desired traffic allocation.
        """
        # Create hash of customer_id
        hash_value = int(hashlib.md5(customer_id.encode()).hexdigest(), 16)
        
        # Map to 0-1 range
        normalized = (hash_value % 10000) / 10000
        
        # Assign based on traffic allocation
        cumulative = 0
        for variant_id, variant in variants.items():
            allocation = variant.get('traffic_allocation', 1.0 / len(variants))
            cumulative += allocation
            if normalized <= cumulative:
                return variant_id
        
        # Fallback to last variant
        return list(variants.keys())[-1]
    
    def _calculate_confidence(
        self,
        control_conversions: int,
        control_impressions: int,
        variant_conversions: int,
        variant_impressions: int
    ) -> float:
        """
        Calculate statistical confidence using two-proportion z-test.
        
        Returns confidence level (0-1) that variant is better than control.
        """
        from scipy import stats
        import numpy as np
        
        # Conversion rates
        p1 = control_conversions / control_impressions
        p2 = variant_conversions / variant_impressions
        
        # Pooled probability
        p_pool = (control_conversions + variant_conversions) / (
            control_impressions + variant_impressions
        )
        
        # Standard error
        se = np.sqrt(
            p_pool * (1 - p_pool) * (
                1/control_impressions + 1/variant_impressions
            )
        )
        
        if se == 0:
            return 0.5
        
        # Z-score
        z = (p2 - p1) / se
        
        # Convert to confidence
        confidence = stats.norm.cdf(abs(z))
        
        return confidence
    
    def _has_sufficient_sample(
        self,
        experiment: Experiment,
        variant_stats: Dict
    ) -> bool:
        """Check if experiment has collected sufficient sample size."""
        if not experiment.required_sample_size:
            return False
        
        total_impressions = sum(s['impressions'] for s in variant_stats.values())
        return total_impressions >= experiment.required_sample_size
    
    async def _record_event(
        self,
        experiment_id: str,
        customer_id: str,
        variant_id: str,
        event_type: str,
        event_value: float = None
    ):
        """Record an experiment event."""
        event = ExperimentEvent(
            timestamp=datetime.utcnow(),
            experiment_id=experiment_id,
            customer_id=customer_id,
            variant_id=variant_id,
            event_type=event_type,
            event_value=event_value
        )
        self.session.add(event)
        await self.session.commit()
```

### 4.2 Self-Optimizing Campaigns

**New Service:** [`backend/app/services/optimization/campaign_optimizer.py`](backend/app/services/optimization/campaign_optimizer.py)

```python
"""
Campaign Optimization Engine

Automatically optimizes campaigns based on performance:
- Budget reallocation
- Creative rotation
- Audience targeting
- Bid adjustments
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.campaign import Campaign
from ...models.experiment import Experiment
from .budget_allocator import BudgetAllocator
from .performance_predictor import PerformancePredictor

class OptimizationAction(str, Enum):
    INCREASE_BUDGET = "increase_budget"
    DECREASE_BUDGET = "decrease_budget"
    PAUSE_CAMPAIGN = "pause_campaign"
    ROTATE_CREATIVE = "rotate_creative"
    EXPAND_AUDIENCE = "expand_audience"
    REFINE_AUDIENCE = "refine_audience"

@dataclass
class OptimizationRecommendation:
    campaign_id: str
    action: OptimizationAction
    confidence: float
    expected_improvement: float
    reason: str
    parameters: Dict[str, Any]

class CampaignOptimizer:
    """AI-powered campaign optimization engine."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.budget_allocator = BudgetAllocator(session)
        self.performance_predictor = PerformancePredictor(session)
    
    async def analyze_campaign(
        self,
        campaign_id: str
    ) -> List[OptimizationRecommendation]:
        """
        Analyze a campaign and generate optimization recommendations.
        """
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            return []
        
        recommendations = []
        
        # Get performance data
        performance = await self._get_performance_data(campaign_id)
        
        # Check budget optimization
        budget_recs = await self._analyze_budget(campaign, performance)
        recommendations.extend(budget_recs)
        
        # Check creative performance
        creative_recs = await self._analyze_creatives(campaign, performance)
        recommendations.extend(creative_recs)
        
        # Check audience performance
        audience_recs = await self._analyze_audience(campaign, performance)
        recommendations.extend(audience_recs)
        
        # Get AI predictions
        prediction_recs = await self.performance_predictor.predict_improvements(
            campaign_id, performance
        )
        recommendations.extend(prediction_recs)
        
        # Sort by expected improvement
        recommendations.sort(
            key=lambda r: r.expected_improvement * r.confidence,
            reverse=True
        )
        
        return recommendations
    
    async def apply_optimization(
        self,
        recommendation: OptimizationRecommendation,
        auto_apply: bool = False
    ) -> bool:
        """
        Apply an optimization recommendation.
        
        If auto_apply is False, creates a proposal for manual approval.
        """
        if not auto_apply and recommendation.confidence < 0.9:
            # Create proposal for manual review
            await self._create_proposal(recommendation)
            return False
        
        # Apply the optimization
        if recommendation.action == OptimizationAction.INCREASE_BUDGET:
            await self.budget_allocator.increase_budget(
                recommendation.campaign_id,
                recommendation.parameters['amount']
            )
        
        elif recommendation.action == OptimizationAction.DECREASE_BUDGET:
            await self.budget_allocator.decrease_budget(
                recommendation.campaign_id,
                recommendation.parameters['amount']
            )
        
        elif recommendation.action == OptimizationAction.ROTATE_CREATIVE:
            await self._rotate_creative(
                recommendation.campaign_id,
                recommendation.parameters['new_creative_id']
            )
        
        elif recommendation.action == OptimizationAction.PAUSE_CAMPAIGN:
            await self._pause_campaign(recommendation.campaign_id)
        
        # Log the optimization
        await self._log_optimization(recommendation)
        
        return True
    
    async def run_auto_optimization(self, organization_id: str):
        """
        Run automatic optimization for all campaigns in an organization.
        
        This is called by a scheduled job.
        """
        from sqlalchemy import select
        
        result = await self.session.execute(
            select(Campaign).where(
                and_(
                    Campaign.organization_id == organization_id,
                    Campaign.status == 'active'
                )
            )
        )
        campaigns = result.scalars().all()
        
        for campaign in campaigns:
            recommendations = await self.analyze_campaign(campaign.id)
            
            for rec in recommendations:
                # Only auto-apply high-confidence recommendations
                if rec.confidence >= 0.95 and rec.expected_improvement > 0.2:
                    await self.apply_optimization(rec, auto_apply=True)
    
    async def _analyze_budget(
        self,
        campaign: Campaign,
        performance: Dict
    ) -> List[OptimizationRecommendation]:
        """Analyze budget performance and make recommendations."""
        recommendations = []
        
        current_roas = performance.get('roas', 0)
        current_spend = performance.get('spend', 0)
        budget = performance.get('budget', 0)
        
        # High ROAS - recommend increasing budget
        if current_roas > 3.0 and current_spend < budget * 0.9:
            recommendations.append(OptimizationRecommendation(
                campaign_id=campaign.id,
                action=OptimizationAction.INCREASE_BUDGET,
                confidence=0.85,
                expected_improvement=0.15,
                reason=f"High ROAS ({current_roas:.2f}x) - scale up",
                parameters={'amount': budget * 0.2}
            ))
        
        # Low ROAS - recommend decreasing budget
        elif current_roas < 1.0 and current_spend > budget * 0.5:
            recommendations.append(OptimizationRecommendation(
                campaign_id=campaign.id,
                action=OptimizationAction.DECREASE_BUDGET,
                confidence=0.80,
                expected_improvement=0.10,
                reason=f"Low ROAS ({current_roas:.2f}x) - reduce spend",
                parameters={'amount': budget * 0.3}
            ))
        
        # Very low ROAS - recommend pausing
        elif current_roas < 0.5 and current_spend > budget * 0.3:
            recommendations.append(OptimizationRecommendation(
                campaign_id=campaign.id,
                action=OptimizationAction.PAUSE_CAMPAIGN,
                confidence=0.75,
                expected_improvement=0.50,
                reason=f"Very low ROAS ({current_roas:.2f}x) - pause campaign",
                parameters={}
            ))
        
        return recommendations
    
    async def _analyze_creatives(
        self,
        campaign: Campaign,
        performance: Dict
    ) -> List[OptimizationRecommendation]:
        """Analyze creative performance and recommend rotation."""
        recommendations = []
        
        creatives = performance.get('creatives', [])
        if len(creatives) < 2:
            return recommendations
        
        # Sort by performance
        creatives.sort(key=lambda c: c.get('ctr', 0), reverse=True)
        
        best_creative = creatives[0]
        worst_creative = creatives[-1]
        
        # If significant difference, recommend rotation
        if best_creative['ctr'] > worst_creative['ctr'] * 2:
            recommendations.append(OptimizationRecommendation(
                campaign_id=campaign.id,
                action=OptimizationAction.ROTATE_CREATIVE,
                confidence=0.80,
                expected_improvement=(best_creative['ctr'] - worst_creative['ctr']),
                reason=f"Best creative ({best_creative['name']}) has {best_creative['ctr']:.2%} CTR vs {worst_creative['ctr']:.2%}",
                parameters={'new_creative_id': best_creative['id']}
            ))
        
        return recommendations
    
    async def _analyze_audience(
        self,
        campaign: Campaign,
        performance: Dict
    ) -> List[OptimizationRecommendation]:
        """Analyze audience performance and recommend targeting changes."""
        recommendations = []
        
        segments = performance.get('segments', [])
        
        # Find high-performing segments
        high_performers = [
            s for s in segments
            if s.get('conversion_rate', 0) > 0.05
        ]
        
        # Find low-performing segments
        low_performers = [
            s for s in segments
            if s.get('conversion_rate', 0) < 0.01
        ]
        
        if high_performers and len(segments) < 5:
            recommendations.append(OptimizationRecommendation(
                campaign_id=campaign.id,
                action=OptimizationAction.EXPAND_AUDIENCE,
                confidence=0.75,
                expected_improvement=0.12,
                reason=f"High-performing segments found - expand reach",
                parameters={'lookalike_segments': [s['id'] for s in high_performers]}
            ))
        
        if low_performers:
            recommendations.append(OptimizationRecommendation(
                campaign_id=campaign.id,
                action=OptimizationAction.REFINE_AUDIENCE,
                confidence=0.70,
                expected_improvement=0.08,
                reason=f"Low-performing segments - refine targeting",
                parameters={'exclude_segments': [s['id'] for s in low_performers]}
            ))
        
        return recommendations
    
    async def _get_performance_data(self, campaign_id: str) -> Dict:
        """Fetch performance data for a campaign."""
        # This would aggregate data from various sources
        # For now, return placeholder structure
        return {
            'campaign_id': campaign_id,
            'spend': 0,
            'budget': 0,
            'roas': 0,
            'creatives': [],
            'segments': []
        }
```

### 4.3 Integration with Campaign Orchestrator

**Modify:** [`backend/app/services/campaigns/orchestrator.py`](backend/app/services/campaigns/orchestrator.py)

```python
# Add optimization hooks to existing orchestrator

class CampaignOrchestrator:
    def __init__(self, ...):
        # ... existing initialization ...
        
        # Add optimizer
        from ..optimization.campaign_optimizer import CampaignOptimizer
        self.optimizer = None  # Initialized per-session
    
    async def execute_campaign(self, ...):
        # ... existing execution ...
        
        # After campaign completion, trigger optimization analysis
        if result.status == "complete":
            await self._schedule_optimization_analysis(campaign_id)
        
        return result
    
    async def _schedule_optimization_analysis(self, campaign_id: str):
        """Schedule optimization analysis for a campaign."""
        from ..tasks.optimization_tasks import analyze_campaign_performance
        
        # Run after 24 hours of data collection
        analyze_campaign_performance.apply_async(
            args=[campaign_id],
            countdown=86400  # 24 hours
        )
```

---

## 5. Attribution & Analytics

### 5.1 Multi-Touch Attribution

**New Service:** [`backend/app/services/attribution/mta_engine.py`](backend/app/services/attribution/mta_engine.py)

```python
"""
Multi-Touch Attribution Engine

Supports multiple attribution models:
- First-touch
- Last-touch
- Linear (equal weight)
- Time-decay
- Position-based (U-shaped)
- Data-driven (algorithmic)
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ...models.customer import CustomerEvent
from ...models.campaign import Campaign

class AttributionModel(str, Enum):
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    POSITION_BASED = "position_based"
    DATA_DRIVEN = "data_driven"

@dataclass
class Touchpoint:
    timestamp: datetime
    channel: str
    campaign_id: Optional[str]
    source: str
    medium: str
    interaction_type: str  # impression, click, engagement
    weight: float = 0.0

@dataclass
class AttributionResult:
    conversion_id: str
    customer_id: str
    conversion_value: float
    touchpoints: List[Touchpoint]
    model: AttributionModel
    attributed_values: Dict[str, float]  # channel -> value

class MTAEngine:
    """Multi-touch attribution engine."""
    
    # Attribution window (default 30 days)
    ATTRIBUTION_WINDOW_DAYS = 30
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def attribute_conversion(
        self,
        customer_id: str,
        conversion_event: CustomerEvent,
        model: AttributionModel = AttributionModel.LINEAR
    ) -> AttributionResult:
        """
        Attribute a conversion to touchpoints using specified model.
        """
        # Get all touchpoints in attribution window
        touchpoints = await self._get_touchpoints(
            customer_id,
            conversion_event.timestamp
        )
        
        if not touchpoints:
            return AttributionResult(
                conversion_id=conversion_event.id,
                customer_id=customer_id,
                conversion_value=conversion_event.properties.get('value', 0),
                touchpoints=[],
                model=model,
                attributed_values={}
            )
        
        # Apply attribution model
        if model == AttributionModel.FIRST_TOUCH:
            weighted_touchpoints = self._apply_first_touch(touchpoints)
        elif model == AttributionModel.LAST_TOUCH:
            weighted_touchpoints = self._apply_last_touch(touchpoints)
        elif model == AttributionModel.LINEAR:
            weighted_touchpoints = self._apply_linear(touchpoints)
        elif model == AttributionModel.TIME_DECAY:
            weighted_touchpoints = self._apply_time_decay(
                touchpoints, conversion_event.timestamp
            )
        elif model == AttributionModel.POSITION_BASED:
            weighted_touchpoints = self._apply_position_based(touchpoints)
        elif model == AttributionModel.DATA_DRIVEN:
            weighted_touchpoints = await self._apply_data_driven(touchpoints)
        else:
            weighted_touchpoints = self._apply_linear(touchpoints)
        
        # Calculate attributed values
        conversion_value = conversion_event.properties.get('value', 0)
        attributed_values = self._calculate_attributed_values(
            weighted_touchpoints, conversion_value
        )
        
        return AttributionResult(
            conversion_id=conversion_event.id,
            customer_id=customer_id,
            conversion_value=conversion_value,
            touchpoints=weighted_touchpoints,
            model=model,
            attributed_values=attributed_values
        )
    
    async def get_attribution_report(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        model: AttributionModel = AttributionModel.LINEAR
    ) -> Dict[str, Any]:
        """
        Generate attribution report for organization.
        """
        # Get all conversions in date range
        conversions = await self._get_conversions(
            organization_id, start_date, end_date
        )
        
        # Attribute each conversion
        results = []
        for conversion in conversions:
            result = await self.attribute_conversion(
                conversion.customer_id,
                conversion,
                model
            )
            results.append(result)
        
        # Aggregate by channel
        channel_attribution = {}
        for result in results:
            for channel, value in result.attributed_values.items():
                if channel not in channel_attribution:
                    channel_attribution[channel] = {
                        'attributed_value': 0,
                        'conversions': 0,
                        'touchpoints': 0
                    }
                channel_attribution[channel]['attributed_value'] += value
                channel_attribution[channel]['conversions'] += 1
        
        # Calculate ROI by channel
        for channel, data in channel_attribution.items():
            spend = await self._get_channel_spend(
                organization_id, channel, start_date, end_date
            )
            data['spend'] = spend
            data['roi'] = (data['attributed_value'] - spend) / spend if spend > 0 else 0
        
        return {
            'model': model,
            'date_range': {'start': start_date, 'end': end_date},
            'total_conversions': len(results),
            'total_attributed_value': sum(r.conversion_value for r in results),
            'channel_attribution': channel_attribution
        }
    
    async def _get_touchpoints(
        self,
        customer_id: str,
        conversion_time: datetime
    ) -> List[Touchpoint]:
        """Get all touchpoints for a customer in attribution window."""
        window_start = conversion_time - timedelta(days=self.ATTRIBUTION_WINDOW_DAYS)
        
        result = await self.session.execute(
            select(CustomerEvent).where(
                and_(
                    CustomerEvent.customer_id == customer_id,
                    CustomerEvent.timestamp >= window_start,
                    CustomerEvent.timestamp < conversion_time,
                    CustomerEvent.event_type.in_([
                        'page_view', 'click', 'email_open', 'email_click',
                        'ad_impression', 'ad_click', 'social_engagement'
                    ])
                )
            ).order_by(CustomerEvent.timestamp)
        )
        
        events = result.scalars().all()
        
        touchpoints = []
        for event in events:
            tp = Touchpoint(
                timestamp=event.timestamp,
                channel=event.channel or 'unknown',
                campaign_id=event.campaign_id,
                source=event.properties.get('utm_source', 'direct'),
                medium=event.properties.get('utm_medium', 'unknown'),
                interaction_type=event.event_type
            )
            touchpoints.append(tp)
        
        return touchpoints
    
    def _apply_first_touch(self, touchpoints: List[Touchpoint]) -> List[Touchpoint]:
        """100% credit to first touchpoint."""
        for i, tp in enumerate(touchpoints):
            tp.weight = 1.0 if i == 0 else 0.0
        return touchpoints
    
    def _apply_last_touch(self, touchpoints: List[Touchpoint]) -> List[Touchpoint]:
        """100% credit to last touchpoint."""
        for i, tp in enumerate(touchpoints):
            tp.weight = 1.0 if i == len(touchpoints) - 1 else 0.0
        return touchpoints
    
    def _apply_linear(self, touchpoints: List[Touchpoint]) -> List[Touchpoint]:
        """Equal credit to all touchpoints."""
        weight = 1.0 / len(touchpoints)
        for tp in touchpoints:
            tp.weight = weight
        return touchpoints
    
    def _apply_time_decay(
        self,
        touchpoints: List[Touchpoint],
        conversion_time: datetime,
        half_life_days: float = 7.0
    ) -> List[Touchpoint]:
        """
        Credit decays exponentially based on time before conversion.
        
        Touchpoints closer to conversion get more credit.
        """
        import math
        
        half_life_seconds = half_life_days * 24 * 3600
        
        weights = []
        for tp in touchpoints:
            time_before = (conversion_time - tp.timestamp).total_seconds()
            # Exponential decay
            weight = math.exp(-time_before / half_life_seconds)
            weights.append(weight)
        
        # Normalize to sum to 1
        total_weight = sum(weights)
        for i, tp in enumerate(touchpoints):
            tp.weight = weights[i] / total_weight
        
        return touchpoints
    
    def _apply_position_based(
        self,
        touchpoints: List[Touchpoint],
        first_touch_weight: float = 0.4,
        last_touch_weight: float = 0.4
    ) -> List[Touchpoint]:
        """
        U-shaped attribution.
        
        First and last touch get 40% each (configurable),
        remaining touchpoints split the remaining 20%.
        """
        n = len(touchpoints)
        
        if n == 1:
            touchpoints[0].weight = 1.0
        elif n == 2:
            touchpoints[0].weight = first_touch_weight
            touchpoints[1].weight = last_touch_weight
            # Normalize
            total = first_touch_weight + last_touch_weight
            for tp in touchpoints:
                tp.weight /= total
        else:
            middle_weight = (1 - first_touch_weight - last_touch_weight) / (n - 2)
            
            for i, tp in enumerate(touchpoints):
                if i == 0:
                    tp.weight = first_touch_weight
                elif i == n - 1:
                    tp.weight = last_touch_weight
                else:
                    tp.weight = middle_weight
        
        return touchpoints
    
    async def _apply_data_driven(
        self,
        touchpoints: List[Touchpoint]
    ) -> List[Touchpoint]:
        """
        Data-driven attribution using Shapley values or Markov chains.
        
        This is a simplified implementation. Production would use
        more sophisticated algorithms.
        """
        # For now, use position-based as fallback
        # Full implementation would analyze all conversion paths
        # and calculate marginal contribution of each touchpoint
        return self._apply_position_based(touchpoints)
    
    def _calculate_attributed_values(
        self,
        touchpoints: List[Touchpoint],
        conversion_value: float
    ) -> Dict[str, float]:
        """Calculate attributed value by channel."""
        channel_values = {}
        
        for tp in touchpoints:
            channel = tp.channel
            if channel not in channel_values:
                channel_values[channel] = 0
            channel_values[channel] += conversion_value * tp.weight
        
        return channel_values
    
    async def _get_conversions(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[CustomerEvent]:
        """Get all conversion events in date range."""
        result = await self.session.execute(
            select(CustomerEvent).where(
                and_(
                    CustomerEvent.organization_id == organization_id,
                    CustomerEvent.timestamp >= start_date,
                    CustomerEvent.timestamp <= end_date,
                    CustomerEvent.event_type == 'conversion'
                )
            )
        )
        return list(result.scalars().all())
    
    async def _get_channel_spend(
        self,
        organization_id: str,
        channel: str,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Get ad spend for a channel in date range."""
        # This would integrate with ad platforms
        # For now, return placeholder
        return 0.0


class AttributionCalculator:
    """
    Calculate attribution for campaigns and channels.
    
    Used by the analytics API to provide attribution data.
    """
    
    def __init__(self, mta_engine: MTAEngine):
        self.mta = mta_engine
    
    async def calculate_campaign_attribution(
        self,
        campaign_id: str,
        model: AttributionModel = AttributionModel.LINEAR
    ) -> Dict[str, Any]:
        """Calculate attribution for a specific campaign."""
        # Get all conversions influenced by this campaign
        # Calculate attributed revenue
        # Return breakdown by touchpoint
        pass
```

---

## 6. Enterprise Integrations

### 6.1 CRM Integration Framework

**New File:** [`backend/app/services/integrations/base.py`](backend/app/services/integrations/base.py)

```python
"""
Base Integration Class

Provides common interface for all enterprise integrations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SyncResult:
    success: bool
    records_synced: int
    errors: List[str]
    last_sync_timestamp: Optional[datetime]

class BaseIntegration(ABC):
    """Base class for all enterprise integrations."""
    
    def __init__(self, organization_id: str, config: Dict[str, Any]):
        self.organization_id = organization_id
        self.config = config
        self.client = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to external system."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection and return status."""
        pass
    
    @abstractmethod
    async def sync_to_external(self, data: List[Dict]) -> SyncResult:
        """Sync data from our system to external system."""
        pass
    
    @abstractmethod
    async def sync_from_external(self, since: Optional[datetime] = None) -> SyncResult:
        """Sync data from external system to our system."""
        pass
    
    @abstractmethod
    async def handle_webhook(self, payload: Dict[str, Any]) -> bool:
        """Handle incoming webhook from external system."""
        pass
```

**New File:** [`backend/app/services/integrations/crm/salesforce.py`](backend/app/services/integrations/crm/salesforce.py)

```python
"""
Salesforce CRM Integration

Syncs:
- Contacts -> Customers
- Leads -> Prospects
- Opportunities -> Campaigns
- Campaigns -> Marketing campaigns
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from simple_salesforce import Salesforce
from ..base import BaseIntegration, SyncResult
from ....models.customer import Customer
from ....models.campaign import Campaign

class SalesforceIntegration(BaseIntegration):
    """Salesforce CRM integration."""
    
    def __init__(self, organization_id: str, config: Dict[str, Any]):
        super().__init__(organization_id, config)
        self.sf = None
    
    async def connect(self) -> bool:
        """Connect to Salesforce."""
        try:
            self.sf = Salesforce(
                username=self.config['username'],
                password=self.config['password'],
                security_token=self.config['security_token'],
                domain=self.config.get('domain', 'login')
            )
            return True
        except Exception as e:
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Salesforce connection."""
        try:
            if not self.sf:
                await self.connect()
            
            # Try to get organization info
            org_info = self.sf.query("SELECT Id, Name FROM Organization LIMIT 1")
            
            return {
                'success': True,
                'organization': org_info['records'][0]['Name'],
                'api_version': self.sf.sf_version
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def sync_contacts_to_customers(self, since: Optional[datetime] = None) -> SyncResult:
        """Sync Salesforce contacts to CDP customers."""
        errors = []
        synced = 0
        
        try:
            # Build SOQL query
            query = """
                SELECT Id, FirstName, LastName, Email, Phone, 
                       MailingCity, MailingState, MailingCountry,
                       Title, Account.Name, LastModifiedDate
                FROM Contact
            """
            
            if since:
                query += f" WHERE LastModifiedDate > {since.isoformat()}"
            
            results = self.sf.query_all(query)
            
            for record in results['records']:
                try:
                    # Map Salesforce contact to Customer
                    customer_data = {
                        'external_id': record['Id'],
                        'first_name': record.get('FirstName'),
                        'last_name': record.get('LastName'),
                        'email': record.get('Email'),
                        'phone': record.get('Phone'),
                        'city': record.get('MailingCity'),
                        'region': record.get('MailingState'),
                        'country': record.get('MailingCountry'),
                        'job_title': record.get('Title'),
                        'company': record.get('Account', {}).get('Name'),
                        'source': 'salesforce'
                    }
                    
                    # Create or update customer
                    await self._upsert_customer(customer_data)
                    synced += 1
                    
                except Exception as e:
                    errors.append(f"Contact {record['Id']}: {str(e)}")
            
            return SyncResult(
                success=len(errors) == 0,
                records_synced=synced,
                errors=errors,
                last_sync_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return SyncResult(
                success=False,
                records_synced=synced,
                errors=[str(e)],
                last_sync_timestamp=None
            )
    
    async def sync_opportunities_to_campaigns(self) -> SyncResult:
        """Sync Salesforce opportunities to campaigns."""
        # Implementation for opportunity sync
        pass
    
    async def create_lead(self, customer: Customer) -> Dict[str, Any]:
        """Create a lead in Salesforce from a customer."""
        lead_data = {
            'FirstName': customer.first_name,
            'LastName': customer.last_name,
            'Email': customer.email,
            'Phone': customer.phone,
            'Company': customer.company or 'Unknown',
            'Title': customer.job_title,
            'LeadSource': 'Marketing Agent',
            'Description': f"Synced from Marketing Agent CDP"
        }
        
        result = self.sf.Lead.create(lead_data)
        return result
    
    async def handle_webhook(self, payload: Dict[str, Any]) -> bool:
        """Handle Salesforce outbound message or platform event."""
        # Process webhook payload
        # Update corresponding records in our system
        return True
    
    async def _upsert_customer(self, customer_data: Dict[str, Any]):
        """Create or update a customer from Salesforce data."""
        # Implementation using Customer repository
        pass
```

### 6.2 Data Warehouse Connectors

**New File:** [`backend/app/services/integrations/warehouse/snowflake.py`](backend/app/services/integrations/warehouse/snowflake.py)

```python
"""
Snowflake Data Warehouse Integration

Exports marketing data to Snowflake for analysis.
"""
import snowflake.connector
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import BaseIntegration, SyncResult

class SnowflakeIntegration(BaseIntegration):
    """Snowflake data warehouse integration."""
    
    def __init__(self, organization_id: str, config: Dict[str, Any]):
        super().__init__(organization_id, config)
        self.conn = None
    
    async def connect(self) -> bool:
        """Connect to Snowflake."""
        try:
            self.conn = snowflake.connector.connect(
                user=self.config['username'],
                password=self.config['password'],
                account=self.config['account'],
                warehouse=self.config.get('warehouse'),
                database=self.config.get('database'),
                schema=self.config.get('schema')
            )
            return True
        except Exception as e:
            return False
    
    async def export_customer_data(self) -> SyncResult:
        """Export customer data to Snowflake."""
        # Create or update customer table in Snowflake
        # Export customer records
        pass
    
    async def export_event_data(self, start_date: datetime, end_date: datetime) -> SyncResult:
        """Export event data to Snowflake."""
        # Export events in date range
        pass
    
    async def create_tables(self):
        """Create required tables in Snowflake."""
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS marketing_customers (
                customer_id VARCHAR(12),
                organization_id VARCHAR(12),
                email VARCHAR(255),
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS marketing_events (
                event_id VARCHAR(12),
                customer_id VARCHAR(12),
                event_type VARCHAR(100),
                timestamp TIMESTAMP,
                properties VARIANT
            )
            """
        ]
        
        for ddl in ddl_statements:
            self.conn.cursor().execute(ddl)
```

### 6.3 CDP Integrations

**New File:** [`backend/app/services/integrations/cdp/segment.py`](backend/app/services/integrations/cdp/segment.py)

```python
"""
Segment CDP Integration

Bidirectional integration with Segment:
- Receive events from Segment (source)
- Send events to Segment (destination)
"""
from typing import Dict, Any, List
import analytics

from ..base import BaseIntegration, SyncResult

class SegmentIntegration(BaseIntegration):
    """Segment.com integration."""
    
    def __init__(self, organization_id: str, config: Dict[str, Any]):
        super().__init__(organization_id, config)
        analytics.write_key = config.get('write_key')
    
    async def send_identify(self, customer: Dict[str, Any]):
        """Send user identity to Segment."""
        analytics.identify(
            user_id=customer['id'],
            traits={
                'email': customer.get('email'),
                'first_name': customer.get('first_name'),
                'last_name': customer.get('last_name'),
                'company': customer.get('company'),
                'created_at': customer.get('created_at')
            }
        )
    
    async def send_track(self, customer_id: str, event_name: str, properties: Dict):
        """Send track event to Segment."""
        analytics.track(
            user_id=customer_id,
            event=event_name,
            properties=properties
        )
    
    async def handle_webhook(self, payload: Dict[str, Any]) -> bool:
        """Handle incoming event from Segment."""
        # Segment webhook payload processing
        event_type = payload.get('type')
        
        if event_type == 'identify':
            # Process user identification
            pass
        elif event_type == 'track':
            # Process track event
            pass
        elif event_type == 'page':
            # Process page view
            pass
        
        return True
```

---

## 7. Implementation Phases

### Phase 1: Security Foundation (Weeks 1-4)

**Goal:** Establish enterprise-grade security and compliance foundation

**Files to Create:**
1. [`backend/app/models/audit_log.py`](backend/app/models/audit_log.py) - Audit log model
2. [`backend/app/models/consent.py`](backend/app/models/consent.py) - Consent management models
3. [`backend/app/services/security/audit_logger.py`](backend/app/services/security/audit_logger.py) - Audit logging service
4. [`backend/app/services/security/saml_provider.py`](backend/app/services/security/saml_provider.py) - SAML implementation
5. [`backend/app/services/security/oauth_provider.py`](backend/app/services/security/oauth_provider.py) - OAuth implementation
6. [`backend/app/services/privacy/gdpr_handler.py`](backend/app/services/privacy/gdpr_handler.py) - GDPR compliance
7. [`backend/app/core/redis.py`](backend/app/core/redis.py) - Redis connection manager

**Files to Modify:**
1. [`backend/app/api/auth.py`](backend/app/api/auth.py) - Add SSO endpoints
2. [`backend/app/models/user.py`](backend/app/models/user.py) - Add SSO fields, MFA
3. [`backend/app/core/config.py`](backend/app/core/config.py) - Add SSO, Redis config
4. [`backend/app/main.py`](backend/app/main.py) - Add audit middleware
5. [`backend/requirements.txt`](backend/requirements.txt) - Add new dependencies

**Dependencies:**
- Redis server
- SAML Identity Provider (Okta/Auth0) for testing

**Testing Requirements:**
- SAML authentication flow
- OAuth login flow
- Audit log generation
- GDPR data export/deletion

---

### Phase 2: CDP Foundation (Weeks 5-8)

**Goal:** Build customer data platform core

**Files to Create:**
1. [`backend/app/models/customer.py`](backend/app/models/customer.py) - Customer models
2. [`backend/app/services/cdp/identity_resolver.py`](backend/app/services/cdp/identity_resolver.py) - Identity resolution
3. [`backend/app/services/cdp/event_processor.py`](backend/app/services/cdp/event_processor.py) - Event processing
4. [`backend/app/services/cdp/segment_engine.py`](backend/app/services/cdp/segment_engine.py) - Segmentation
5. [`backend/app/api/customers.py`](backend/app/api/customers.py) - Customer API endpoints
6. [`backend/app/api/events.py`](backend/app/api/events.py) - Event ingestion API

**Files to Modify:**
1. [`backend/app/models/__init__.py`](backend/app/models/__init__.py) - Export new models
2. [`backend/app/api/__init__.py`](backend/app/api/__init__.py) - Register new routers

**Dependencies:**
- TimescaleDB for time-series data
- Elasticsearch for customer search

**Testing Requirements:**
- Identity resolution accuracy
- Event processing pipeline
- Segment computation

---

### Phase 3: Attribution & Analytics (Weeks 9-12)

**Goal:** Implement multi-touch attribution and advanced analytics

**Files to Create:**
1. [`backend/app/services/attribution/mta_engine.py`](backend/app/services/attribution/mta_engine.py) - Attribution engine
2. [`backend/app/services/attribution/channel_analyzer.py`](backend/app/services/attribution/channel_analyzer.py) - Channel analysis
3. [`backend/app/services/reporting/dashboard_builder.py`](backend/app/services/reporting/dashboard_builder.py) - Dashboard builder
4. [`backend/app/services/reporting/report_scheduler.py`](backend/app/services/reporting/report_scheduler.py) - Report scheduling
5. [`backend/app/tasks/report_tasks.py`](backend/app/tasks/report_tasks.py) - Background report tasks

**Files to Modify:**
1. [`backend/app/api/analytics.py`](backend/app/api/analytics.py) - Add attribution endpoints
2. [`backend/app/models/campaign.py`](backend/app/models/campaign.py) - Add performance fields

**Dependencies:**
- Celery for background processing
- TimescaleDB for metrics storage

**Testing Requirements:**
- Attribution model accuracy
- Report generation
- Dashboard data accuracy

---

### Phase 4: Optimization Engine (Weeks 13-16)

**Goal:** Build autonomous optimization capabilities

**Files to Create:**
1. [`backend/app/models/experiment.py`](backend/app/models/experiment.py) - Experiment models
2. [`backend/app/services/experimentation/ab_test_engine.py`](backend/app/services/experimentation/ab_test_engine.py) - A/B testing
3. [`backend/app/services/optimization/campaign_optimizer.py`](backend/app/services/optimization/campaign_optimizer.py) - Campaign optimizer
4. [`backend/app/services/optimization/budget_allocator.py`](backend/app/services/optimization/budget_allocator.py) - Budget allocation
5. [`backend/app/api/experiments.py`](backend/app/api/experiments.py) - Experiment API
6. [`backend/app/tasks/optimization_tasks.py`](backend/app/tasks/optimization_tasks.py) - Optimization jobs

**Files to Modify:**
1. [`backend/app/services/campaigns/orchestrator.py`](backend/app/services/campaigns/orchestrator.py) - Add optimization hooks
2. [`backend/app/models/__init__.py`](backend/app/models/__init__.py) - Export experiment models

**Dependencies:**
- scipy/statsmodels for statistics
- Redis for experiment caching

**Testing Requirements:**
- Statistical significance calculation
- Variant assignment consistency
- Optimization recommendation accuracy

---

### Phase 5: Enterprise Integrations (Weeks 17-20)

**Goal:** Implement CRM and data warehouse integrations

**Files to Create:**
1. [`backend/app/services/integrations/base.py`](backend/app/services/integrations/base.py) - Base integration class
2. [`backend/app/services/integrations/crm/salesforce.py`](backend/app/services/integrations/crm/salesforce.py) - Salesforce connector
3. [`backend/app/services/integrations/crm/hubspot.py`](backend/app/services/integrations/crm/hubspot.py) - HubSpot connector
4. [`backend/app/services/integrations/warehouse/snowflake.py`](backend/app/services/integrations/warehouse/snowflake.py) - Snowflake connector
5. [`backend/app/services/integrations/warehouse/bigquery.py`](backend/app/services/integrations/warehouse/bigquery.py) - BigQuery connector
6. [`backend/app/services/integrations/cdp/segment.py`](backend/app/services/integrations/cdp/segment.py) - Segment integration
7. [`backend/app/api/integrations.py`](backend/app/api/integrations.py) - Integration API
8. [`backend/app/tasks/sync_tasks.py`](backend/app/tasks/sync_tasks.py) - Sync background jobs

**Files to Modify:**
1. [`backend/app/api/__init__.py`](backend/app/api/__init__.py) - Register integration router
2. [`backend/requirements.txt`](backend/requirements.txt) - Add integration dependencies

**Dependencies:**
- Salesforce test account
- Snowflake/BigQuery test instances
- Segment account

**Testing Requirements:**
- Bi-directional sync accuracy
- Webhook handling
- Error recovery

---

### Phase 6: AI Enhancement & Polish (Weeks 21-24)

**Goal:** Add AI-powered features and production hardening

**Files to Create:**
1. [`backend/app/services/optimization/performance_predictor.py`](backend/app/services/optimization/performance_predictor.py) - ML prediction
2. [`backend/app/services/cdp/predictive_analytics.py`](backend/app/services/cdp/predictive_analytics.py) - Churn/LTV prediction
3. [`backend/app/services/ai/recommendation_engine.py`](backend/app/services/ai/recommendation_engine.py) - Next-best-action
4. [`backend/app/api/attribution.py`](backend/app/api/attribution.py) - Attribution API

**Files to Modify:**
1. [`frontend/src/services/api.js`](frontend/src/services/api.js) - Add new API methods
2. [`backend/app/core/config.py`](backend/app/core/config.py) - Add ML service config

**Dependencies:**
- ML model training pipeline
- Feature engineering infrastructure

**Testing Requirements:**
- Prediction accuracy
- Recommendation relevance
- End-to-end integration tests

---

## 8. Technical Specifications

### 8.1 API Endpoints

#### Security & Compliance

```
POST   /api/auth/saml/{org_id}/login       # Initiate SAML login
POST   /api/auth/saml/{org_id}/acs         # SAML callback
GET    /api/auth/oauth/{provider}/login    # OAuth login
GET    /api/auth/oauth/{provider}/callback # OAuth callback
POST   /api/auth/mfa/enable                # Enable MFA
POST   /api/auth/mfa/verify                # Verify MFA token

GET    /api/audit-logs                     # List audit logs
GET    /api/audit-logs/export              # Export audit logs

POST   /api/privacy/data-request           # Create DSAR request
GET    /api/privacy/data-request/{id}      # Get request status
GET    /api/privacy/export/{id}/download   # Download data export

GET    /api/consent                        # List consent records
POST   /api/consent                        # Record consent
PUT    /api/consent/{id}/withdraw          # Withdraw consent
```

#### CDP & Customers

```
GET    /api/customers                      # List customers
POST   /api/customers                      # Create customer
GET    /api/customers/{id}                 # Get customer profile
PUT    /api/customers/{id}                 # Update customer
DELETE /api/customers/{id}                 # Delete customer
GET    /api/customers/{id}/events          # Get customer events
GET    /api/customers/{id}/journeys        # Get customer journey

POST   /api/events/ingest                  # Ingest single event
POST   /api/events/batch                   # Batch event ingestion
GET    /api/events/schema                  # Get event schema

GET    /api/segments                       # List segments
POST   /api/segments                       # Create segment
GET    /api/segments/{id}/customers        # Get segment customers
POST   /api/segments/{id}/compute          # Recompute segment
```

#### Attribution & Analytics

```
GET    /api/analytics/attribution          # Get attribution report
POST   /api/analytics/attribution/compute  # Compute attribution
GET    /api/analytics/attribution/models   # List attribution models

GET    /api/analytics/dashboards           # List dashboards
POST   /api/analytics/dashboards           # Create dashboard
GET    /api/analytics/dashboards/{id}      # Get dashboard data

GET    /api/analytics/reports              # List reports
POST   /api/analytics/reports              # Create report
POST   /api/analytics/reports/{id}/schedule # Schedule report
GET    /api/analytics/reports/{id}/export  # Export report
```

#### Experiments & Optimization

```
GET    /api/experiments                    # List experiments
POST   /api/experiments                    # Create experiment
GET    /api/experiments/{id}               # Get experiment
PUT    /api/experiments/{id}               # Update experiment
POST   /api/experiments/{id}/start         # Start experiment
POST   /api/experiments/{id}/stop          # Stop experiment
GET    /api/experiments/{id}/results       # Get results
POST   /api/experiments/{id}/deploy-winner # Deploy winner

POST   /api/experiments/assign-variant     # Assign variant to user
POST   /api/experiments/track-conversion   # Track conversion

GET    /api/optimization/recommendations   # Get optimization recommendations
POST   /api/optimization/apply             # Apply recommendation
GET    /api/optimization/autopilot         # Get autopilot status
PUT    /api/optimization/autopilot         # Configure autopilot
```

#### Integrations

```
GET    /api/integrations                   # List integrations
POST   /api/integrations                   # Create integration
GET    /api/integrations/{id}              # Get integration
PUT    /api/integrations/{id}              # Update integration
DELETE /api/integrations/{id}              # Delete integration
POST   /api/integrations/{id}/test         # Test connection
POST   /api/integrations/{id}/sync         # Trigger sync
GET    /api/integrations/{id}/sync-status  # Get sync status
GET    /api/integrations/{id}/logs         # Get sync logs

POST   /api/webhooks/segment               # Segment webhook
POST   /api/webhooks/salesforce            # Salesforce webhook
POST   /api/webhooks/hubspot               # HubSpot webhook
```

### 8.2 Database Migrations

**Migration 001: Audit Logging**
```sql
CREATE TABLE audit_logs (
    id VARCHAR(12) PRIMARY KEY,
    user_id VARCHAR(12),
    user_email VARCHAR(255),
    organization_id VARCHAR(12) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(12),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    session_id VARCHAR(255),
    before_state JSONB,
    after_state JSONB,
    changes_summary TEXT,
    retention_until TIMESTAMP,
    compliance_flags JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_org_time ON audit_logs(organization_id, created_at);
CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
```

**Migration 002: Customer Data Platform**
```sql
CREATE TABLE customers (
    id VARCHAR(12) PRIMARY KEY,
    organization_id VARCHAR(12) NOT NULL REFERENCES organizations(id),
    email VARCHAR(255),
    phone VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    status VARCHAR(50) DEFAULT 'prospect',
    engagement_score FLOAT DEFAULT 0,
    identity_graph JSONB DEFAULT '{}',
    traits JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_customer_org_email ON customers(organization_id, email);
CREATE INDEX idx_customer_org_status ON customers(organization_id, status);

-- TimescaleDB hypertable for events
CREATE TABLE customer_events (
    time TIMESTAMPTZ NOT NULL,
    id VARCHAR(12),
    customer_id VARCHAR(12) NOT NULL,
    organization_id VARCHAR(12) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    channel VARCHAR(50),
    properties JSONB DEFAULT '{}'
);

SELECT create_hypertable('customer_events', 'time');
```

**Migration 003: Experiments**
```sql
CREATE TABLE experiments (
    id VARCHAR(12) PRIMARY KEY,
    organization_id VARCHAR(12) NOT NULL,
    campaign_id VARCHAR(12),
    name VARCHAR(255) NOT NULL,
    experiment_type VARCHAR(50) DEFAULT 'ab_test',
    status VARCHAR(50) DEFAULT 'draft',
    variants JSONB NOT NULL,
    primary_metric VARCHAR(100) NOT NULL,
    confidence_level FLOAT DEFAULT 0.95,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    winner_variant_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE experiment_assignments (
    experiment_id VARCHAR(12) NOT NULL,
    customer_id VARCHAR(12) NOT NULL,
    variant_id VARCHAR(50) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (experiment_id, customer_id)
);
```

**Migration 004: User SSO & MFA**
```sql
ALTER TABLE users ADD COLUMN saml_id VARCHAR(255);
ALTER TABLE users ADD COLUMN idp_name VARCHAR(100);
ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50);
ALTER TABLE users ADD COLUMN oauth_subject VARCHAR(255);
ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(255);
ALTER TABLE users ADD COLUMN mfa_backup_codes JSONB DEFAULT '[]';
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP;
ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until TIMESTAMP;

CREATE INDEX idx_user_saml ON users(saml_id);
```

### 8.3 Environment Variables

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# SAML SSO
SAML_CERTIFICATE_PATH=/path/to/cert.pem
SAML_PRIVATE_KEY_PATH=/path/to/key.pem

# OAuth
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
MICROSOFT_OAUTH_CLIENT_ID=
MICROSOFT_OAUTH_CLIENT_SECRET=

# TimescaleDB
TIMESCALE_URL=postgresql://user:pass@localhost:5432/marketing_agent_timescale

# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=

# Salesforce
SALESFORCE_CLIENT_ID=
SALESFORCE_CLIENT_SECRET=

# Snowflake
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USERNAME=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=

# Segment
SEGMENT_WRITE_KEY=

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 8.4 Dependencies to Add

```txt
# Security & Auth
python-saml>=1.15.0
authlib>=1.3.0
pyotp>=2.9.0
cryptography>=42.0.0

# CDP & Analytics
redis>=5.0.0
celery>=5.3.0
timescale-python>=0.0.7
elasticsearch>=8.12.0

# ML & Statistics
scipy>=1.12.0
statsmodels>=0.14.0
scikit-learn>=1.4.0
pandas>=2.2.0
numpy>=1.26.0

# Integrations
simple-salesforce>=1.12.0
hubspot-api-client>=8.2.0
snowflake-connector-python>=3.7.0
google-cloud-bigquery>=3.17.0
segment-analytics-python>=2.3.0

# Utilities
user-agents>=2.2.0
geoip2>=4.8.0
maxminddb>=2.2.0
```

---

## Summary

This integration plan provides a comprehensive roadmap for transforming the Marketing Agent Platform into an enterprise-grade solution. The 24-week implementation schedule is organized into logical phases that build upon each other:

1. **Security Foundation** - Essential for enterprise adoption
2. **CDP Foundation** - Core customer data infrastructure
3. **Attribution & Analytics** - Proving ROI to CMOs
4. **Optimization Engine** - Key differentiator
5. **Enterprise Integrations** - CRM and data warehouse connectivity
6. **AI Enhancement** - Advanced predictive capabilities

### Critical Success Factors

1. **Infrastructure First** - Redis, Celery, and TimescaleDB must be provisioned before feature development
2. **Backward Compatibility** - All changes must maintain existing API contracts
3. **Incremental Rollout** - Use feature flags to enable functionality per organization
4. **Testing Coverage** - Enterprise features require >90% test coverage
5. **Documentation** - API docs and integration guides required for each feature

### Next Steps

1. Review and approve this plan with stakeholders
2. Provision infrastructure (Redis, TimescaleDB, Elasticsearch)
3. Begin Phase 1 implementation with Security Foundation
4. Set up monitoring and alerting for new services
5. Create feature flags for gradual rollout

---

*Document generated: 2026-01-30*
*Based on: Enterprise Gap Analysis v1.0*
