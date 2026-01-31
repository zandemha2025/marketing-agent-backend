"""
SSO middleware for enforcing enterprise authentication requirements.

Ensures that users from organizations with SSO configured must use
SAML authentication, while allowing local/JWT auth for organizations
without SSO configured.
"""
import logging
from typing import Optional

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..models.user import User, IdentityProvider
from ..services.security.saml_provider import get_saml_provider

logger = logging.getLogger(__name__)


# Paths that are exempt from SSO enforcement
SSO_EXEMPT_PATHS = {
    "/health",
    "/healthz",
    "/ready",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/saml/login",
    "/api/auth/saml/acs",
    "/api/auth/saml/metadata",
    "/api/auth/saml/configure",
    "/api/auth/refresh",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
}

# Paths that require SSO if configured
SSO_PROTECTED_PATHS = {
    "/api/",
}


class SSOMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce SSO for enterprise organizations.
    
    Features:
    - Bypass for local/JWT auth if SSO not configured
    - Enforce SSO for organizations with SAML configured
    - Session management for SAML users
    - Graceful fallback for mixed environments
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    def _is_path_exempt(self, path: str) -> bool:
        """Check if path is exempt from SSO enforcement."""
        for exempt_path in SSO_EXEMPT_PATHS:
            if path.startswith(exempt_path) or path == exempt_path.rstrip('/'):
                return True
        return False
    
    def _is_sso_protected(self, path: str) -> bool:
        """Check if path requires SSO protection."""
        for protected_path in SSO_PROTECTED_PATHS:
            if path.startswith(protected_path):
                return True
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Process request and enforce SSO if required.
        
        NOTE: SSO enforcement in middleware is currently disabled because
        request.state.user is not available at middleware time (the auth
        dependency runs AFTER middleware). SSO enforcement should be done
        at the route level using the require_sso_if_configured() dependency.
        
        This middleware now only logs requests for debugging purposes.
        """
        path = request.url.path
        
        # Skip SSO check for exempt paths
        if self._is_path_exempt(path):
            return await call_next(request)
        
        # Only log for protected API paths
        if not self._is_sso_protected(path):
            return await call_next(request)
        
        # NOTE: request.state.user is NEVER set at middleware time because
        # the auth dependency (get_current_user) runs AFTER middleware.
        # The SSO enforcement logic below is kept for reference but will
        # never execute because user is always None.
        #
        # To enforce SSO, use the require_sso_if_configured() dependency
        # in your route handlers instead.
        
        # Get current user from request state (set by auth dependency)
        user: Optional[User] = getattr(request.state, "user", None)
        
        # User is always None at middleware time - just proceed
        if user is None:
            return await call_next(request)
        
        # The code below will never execute but is kept for reference
        # in case request.state.user is set in the future
        
        # Check if user's organization has SSO configured
        saml_provider = get_saml_provider(user.organization_id)
        
        if saml_provider is None:
            # No SSO configured for this organization, allow local auth
            return await call_next(request)
        
        # SSO is configured - check if user is using SSO
        if user.identity_provider == IdentityProvider.LOCAL:
            # User is trying to use local auth but SSO is required
            logger.warning(
                f"SSO enforcement: User {user.id} attempted local auth "
                f"for org {user.organization_id} with SSO configured"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "sso_required",
                    "message": "Single Sign-On is required for your organization. Please use SSO to login.",
                    "sso_url": f"/api/auth/saml/login?organization_id={user.organization_id}",
                }
            )
        
        # User is using SSO, check session validity
        if not await self._validate_sso_session(request, user):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "sso_session_expired",
                    "message": "Your SSO session has expired. Please login again.",
                    "sso_url": f"/api/auth/saml/login?organization_id={user.organization_id}",
                }
            )
        
        # SSO session is valid, proceed
        return await call_next(request)
    
    async def _validate_sso_session(self, request: Request, user: User) -> bool:
        """
        Validate SSO session for user.
        
        Checks:
        - Session hasn't expired
        - User hasn't been deactivated
        - Organization still has SSO enabled
        """
        from datetime import datetime, timedelta
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"SSO session invalid: User {user.id} is deactivated")
            return False
        
        # Check last SSO login time (sessions valid for 12 hours by default)
        if user.last_sso_login:
            session_duration = timedelta(hours=12)
            if datetime.utcnow() - user.last_sso_login > session_duration:
                logger.info(f"SSO session expired for user {user.id}")
                return False
        
        # Check if organization still has SSO configured
        saml_provider = get_saml_provider(user.organization_id)
        if saml_provider is None:
            # SSO was disabled for organization
            logger.info(f"SSO disabled for organization {user.organization_id}")
            return True  # Allow session to continue with local auth
        
        return True


class SSOSessionManager:
    """
    Manager for SSO session lifecycle.
    
    Handles:
    - Session creation after successful SAML login
    - Session validation
    - Session termination (logout)
    """
    
    def __init__(self):
        self._sessions: dict = {}  # In production, use Redis
    
    def create_session(
        self,
        user_id: str,
        session_index: str,
        organization_id: str,
        expires_in_hours: int = 12
    ) -> str:
        """
        Create new SSO session.
        
        Returns:
            Session token
        """
        from datetime import datetime, timedelta
        import secrets
        
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        self._sessions[session_token] = {
            "user_id": user_id,
            "session_index": session_index,
            "organization_id": organization_id,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
        }
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[dict]:
        """Validate and return session data if valid."""
        from datetime import datetime
        
        session = self._sessions.get(session_token)
        if not session:
            return None
        
        if datetime.utcnow() > session["expires_at"]:
            # Session expired
            del self._sessions[session_token]
            return None
        
        return session
    
    def terminate_session(self, session_token: str):
        """Terminate SSO session."""
        if session_token in self._sessions:
            del self._sessions[session_token]
    
    def terminate_user_sessions(self, user_id: str):
        """Terminate all sessions for a user."""
        tokens_to_remove = [
            token for token, session in self._sessions.items()
            if session["user_id"] == user_id
        ]
        for token in tokens_to_remove:
            del self._sessions[token]


# Global session manager instance
sso_session_manager = SSOSessionManager()


def require_sso_if_configured():
    """
    Dependency to require SSO if configured for user's organization.
    
    Usage:
        @router.get("/protected")
        async def protected_endpoint(
            user: User = Depends(require_sso_if_configured())
        ):
            ...
    """
    from fastapi import Depends
    from ..api.auth import get_current_active_user
    
    async def check_sso(user: User = Depends(get_current_active_user)) -> User:
        saml_provider = get_saml_provider(user.organization_id)
        
        if saml_provider and user.identity_provider == IdentityProvider.LOCAL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SSO is required for your organization"
            )
        
        return user
    
    return check_sso