"""
FastAPI middleware for automatic audit logging of API requests.

Captures all API requests and responses, logging security-relevant events
while skipping health checks and handling sensitive endpoint masking.
"""
import time
import uuid
from typing import Optional, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..models.audit_log import AuditAction, ResourceType
from ..services.security.audit_logger import AuditLogger, get_audit_logger
from ..core.database import get_session


# Endpoints to skip logging (health checks, metrics, etc.)
SKIP_LOG_PATHS = {
    "/health",
    "/healthz",
    "/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/static/",
}

# Sensitive endpoints that need extra masking
SENSITIVE_ENDPOINTS = {
    "/api/auth/login": (AuditAction.LOGIN, ResourceType.USER),
    "/api/auth/register": (AuditAction.CREATE, ResourceType.USER),
    "/api/auth/change-password": (AuditAction.PASSWORD_CHANGE, ResourceType.USER),
    "/api/auth/saml/login": (AuditAction.SAML_LOGIN_INITIATED, ResourceType.USER),
    "/api/auth/saml/acs": (AuditAction.SAML_LOGIN_SUCCESS, ResourceType.USER),
}

# HTTP methods to audit actions mapping
METHOD_TO_ACTION = {
    "POST": AuditAction.CREATE,
    "GET": AuditAction.READ,
    "PUT": AuditAction.UPDATE,
    "PATCH": AuditAction.UPDATE,
    "DELETE": AuditAction.DELETE,
}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log API requests for audit purposes.
    
    Features:
    - Automatic request/response logging
    - PII redaction via AuditLogger
    - Skip logging for health checks
    - Sensitive endpoint detection
    - Request timing
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    def _should_skip_logging(self, request: Request) -> bool:
        """Check if request should be skipped."""
        path = request.url.path
        
        # Skip health checks and static files
        for skip_path in SKIP_LOG_PATHS:
            if path.startswith(skip_path) or path == skip_path.rstrip('/'):
                return True
        
        # Skip non-API routes (frontend assets)
        if not path.startswith("/api/"):
            return True
        
        return False
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request headers."""
        # Check for forwarded headers (when behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain (client IP)
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return None
    
    def _extract_resource_info(self, request: Request) -> tuple[Optional[ResourceType], Optional[str]]:
        """Extract resource type and ID from request path."""
        path = request.url.path
        path_parts = path.strip('/').split('/')
        
        if len(path_parts) < 2:
            return None, None
        
        # Map path segments to resource types
        resource_mapping = {
            "campaigns": ResourceType.CAMPAIGN,
            "assets": ResourceType.ASSET,
            "users": ResourceType.USER,
            "organizations": ResourceType.ORGANIZATION,
            "deliverables": ResourceType.DELIVERABLE,
            "tasks": ResourceType.TASK,
            "conversations": ResourceType.CONVERSATION,
            "knowledge-base": ResourceType.KNOWLEDGE_BASE,
            "scheduled-posts": ResourceType.SCHEDULED_POST,
            "trends": ResourceType.TREND,
        }
        
        # Find resource type in path
        for i, part in enumerate(path_parts):
            if part in resource_mapping:
                resource_type = resource_mapping[part]
                # Check if next part is an ID
                resource_id = None
                if i + 1 < len(path_parts):
                    potential_id = path_parts[i + 1]
                    # Simple heuristic: IDs are typically alphanumeric and not action verbs
                    if potential_id and potential_id not in ('create', 'update', 'delete', 'list'):
                        resource_id = potential_id
                return resource_type, resource_id
        
        return None, None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log to audit system."""
        # Skip if not an API request or health check
        if self._should_skip_logging(request):
            return await call_next(request)
        
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get request metadata
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        path = request.url.path
        method = request.method
        
        # Extract user info if available (from JWT token)
        user_id = getattr(request.state, "user_id", None)
        user_email = getattr(request.state, "user_email", None)
        organization_id = getattr(request.state, "organization_id", None)
        
        # Process request
        try:
            response = await call_next(request)
            success = response.status_code < 400
            status_code = response.status_code
        except Exception as e:
            success = False
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Only log if it's a significant event or error
            if not success or self._should_log_request(path, method, status_code):
                try:
                    await self._log_request(
                        request=request,
                        request_id=request_id,
                        user_id=user_id,
                        user_email=user_email,
                        organization_id=organization_id,
                        client_ip=client_ip,
                        user_agent=user_agent,
                        method=method,
                        path=path,
                        status_code=status_code,
                        success=success,
                        duration_ms=duration_ms,
                    )
                except Exception as e:
                    # Don't let audit logging failures break the request
                    import logging
                    logging.getLogger(__name__).error(f"Audit logging failed: {e}")
        
        return response
    
    def _should_log_request(self, path: str, method: str, status_code: int) -> bool:
        """Determine if request should be logged based on significance."""
        # Always log authentication events
        if path in SENSITIVE_ENDPOINTS:
            return True
        
        # Always log write operations
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            return True
        
        # Always log errors
        if status_code >= 400:
            return True
        
        # Log specific resource types
        if any(resource in path for resource in [
            "/users", "/organizations", "/api-keys", "/settings"
        ]):
            return True
        
        return False
    
    async def _log_request(
        self,
        request: Request,
        request_id: str,
        user_id: Optional[str],
        user_email: Optional[str],
        organization_id: Optional[str],
        client_ip: Optional[str],
        user_agent: Optional[str],
        method: str,
        path: str,
        status_code: int,
        success: bool,
        duration_ms: int,
    ):
        """Log the request to audit system."""
        # Get database session
        async for session in get_session():
            audit_logger = get_audit_logger(session)
            
            # Determine action and resource type
            if path in SENSITIVE_ENDPOINTS:
                action, resource_type = SENSITIVE_ENDPOINTS[path]
            else:
                action = METHOD_TO_ACTION.get(method, AuditAction.READ)
                resource_type, resource_id = self._extract_resource_info(request)
                if resource_type is None:
                    resource_type = ResourceType.API_KEY  # Default fallback
            
            # Build metadata
            metadata = {
                "http_method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "api_endpoint": True,
            }
            
            # Log the event
            await audit_logger.log(
                action=action,
                resource_type=resource_type,
                user_id=user_id,
                user_email=user_email,
                organization_id=organization_id,
                ip_address=client_ip,
                user_agent=user_agent,
                request_id=request_id,
                success=success,
                failure_reason=None if success else f"HTTP {status_code}",
                metadata=metadata,
            )
            
            # Flush immediately for important events
            if path in SENSITIVE_ENDPOINTS or not success:
                await audit_logger.stop()  # This flushes the queue
            
            break  # Only need one session


class AuditContext:
    """
    Context manager for setting audit context in request state.
    
    Usage in dependencies:
        async def get_current_user(...) -> User:
            user = ...
            AuditContext.set_user(request, user)
            return user
    """
    
    @staticmethod
    def set_user(request: Request, user) -> None:
        """Set user context for audit logging."""
        request.state.user_id = getattr(user, 'id', None)
        request.state.user_email = getattr(user, 'email', None)
        request.state.organization_id = getattr(user, 'organization_id', None)
    
    @staticmethod
    def set_organization(request: Request, organization_id: str) -> None:
        """Set organization context for audit logging."""
        request.state.organization_id = organization_id
    
    @staticmethod
    def get_request_id(request: Request) -> Optional[str]:
        """Get the current request ID for tracing."""
        return getattr(request.state, 'request_id', None)