"""
GDPR middleware for privacy compliance.

Handles:
- Consent checking before tracking/analytics
- Do Not Track header support
- Geographic detection for EU users
- Consent banner requirements
"""
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime

import json

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.config import get_settings

logger = logging.getLogger(__name__)


# EU country codes (GDPR applies)
EU_COUNTRY_CODES = {
    'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR',
    'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL',
    'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB',  # UK still follows GDPR
    'IS', 'LI', 'NO', 'CH',  # EEA countries
}

# Tracking endpoints that require consent
TRACKING_PATHS = {
    '/api/analytics/',
    '/api/tracking/',
    '/api/events/',
}

# Paths that are exempt from consent requirements
CONSENT_EXEMPT_PATHS = {
    '/health',
    '/healthz',
    '/ready',
    '/metrics',
    '/docs',
    '/redoc',
    '/api/auth/',
    '/api/compliance/consent',
}


class GDPRMiddleware(BaseHTTPMiddleware):
    """
    Middleware for GDPR compliance.
    
    Features:
    - Respects Do Not Track headers
    - Detects EU users for consent requirements
    - Blocks tracking without consent
    - Sets consent-related headers
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with GDPR compliance checks."""
        # Skip if GDPR is not enabled
        if not self.settings.gdpr_enabled:
            return await call_next(request)
        
        # Extract privacy-related info from request
        privacy_context = self._extract_privacy_context(request)
        request.state.privacy_context = privacy_context
        
        # Check if this is a tracking endpoint
        if self._is_tracking_request(request):
            # Check if tracking is allowed
            if not self._is_tracking_allowed(request, privacy_context):
                return Response(
                    content='{"error": "consent_required", "message": "User consent required for tracking"}',
                    status_code=403,
                    media_type="application/json",
                    headers={
                        "X-Consent-Required": "true",
                        "X-Consent-Types": "analytics",
                    }
                )
        
        # Process the request
        response = await call_next(request)
        
        # Add GDPR-related headers to response
        response = self._add_privacy_headers(response, privacy_context)
        
        return response
    
    def _extract_privacy_context(self, request: Request) -> Dict[str, Any]:
        """Extract privacy-related context from request."""
        context = {
            'do_not_track': False,
            'country_code': None,
            'is_eu_user': False,
            'consent_given': {},
            'gdpr_applies': False,
        }
        
        # Check Do Not Track header
        dnt_header = request.headers.get('DNT') or request.headers.get('Sec-GPC')
        if dnt_header == '1':
            context['do_not_track'] = True
        
        # Try to detect country from various headers
        context['country_code'] = self._detect_country(request)
        
        # Check if EU user
        if context['country_code']:
            context['is_eu_user'] = context['country_code'] in EU_COUNTRY_CODES
        
        # GDPR applies if EU user or GDPR is globally enabled
        context['gdpr_applies'] = context['is_eu_user'] or self.settings.gdpr_enabled
        
        # Extract consent from cookies or headers
        context['consent_given'] = self._extract_consent(request)
        
        return context
    
    def _detect_country(self, request: Request) -> Optional[str]:
        """Detect user's country from request headers."""
        # Check CloudFlare country header
        country = request.headers.get('CF-IPCountry')
        if country and country != 'XX':
            return country.upper()
        
        # Check AWS CloudFront country header
        country = request.headers.get('CloudFront-Viewer-Country')
        if country:
            return country.upper()
        
        # Check Fastly country header
        country = request.headers.get('X-Country-Code')
        if country:
            return country.upper()
        
        # Check for GeoIP header from nginx/apache
        country = request.headers.get('X-GeoIP-Country-Code')
        if country:
            return country.upper()
        
        return None
    
    def _extract_consent(self, request: Request) -> Dict[str, bool]:
        """Extract consent preferences from request."""
        consent = {}
        
        # Check consent cookie
        consent_cookie = request.cookies.get('user_consent')
        if consent_cookie:
            try:
                import json
                consent = json.loads(consent_cookie)
            except json.JSONDecodeError:
                pass
        
        # Check consent header (for API requests)
        consent_header = request.headers.get('X-User-Consent')
        if consent_header:
            try:
                import json
                header_consent = json.loads(consent_header)
                consent.update(header_consent)
            except json.JSONDecodeError:
                pass
        
        return consent
    
    def _is_tracking_request(self, request: Request) -> bool:
        """Check if request is for a tracking endpoint."""
        path = request.url.path
        for tracking_path in TRACKING_PATHS:
            if path.startswith(tracking_path):
                return True
        return False
    
    def _is_tracking_allowed(self, request: Request, privacy_context: Dict) -> bool:
        """Check if tracking is allowed for this request."""
        # Respect Do Not Track
        if privacy_context.get('do_not_track'):
            return False
        
        # Check if GDPR applies and consent is required
        if privacy_context.get('gdpr_applies'):
            # Check for analytics consent
            consent = privacy_context.get('consent_given', {})
            if not consent.get('analytics', False):
                return False
        
        return True
    
    def _add_privacy_headers(self, response: Response, privacy_context: Dict) -> Response:
        """Add GDPR-related headers to response."""
        # Add consent requirements header for EU users
        if privacy_context.get('is_eu_user'):
            response.headers['X-Consent-Required'] = 'true'
            response.headers['X-Consent-Types'] = 'marketing,analytics,personalization'
        
        # Add DNT response header
        if privacy_context.get('do_not_track'):
            response.headers['Tk'] = 'N'  # Not tracking
        else:
            response.headers['Tk'] = '?'  # Tracking status unknown
        
        # Add GDPR applicability header
        if privacy_context.get('gdpr_applies'):
            response.headers['X-GDPR-Applies'] = 'true'
        
        return response


class ConsentMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce consent requirements.
    
    Blocks requests that require specific consent if not granted.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Check consent requirements for request."""
        # Get privacy context from GDPR middleware
        privacy_context = getattr(request.state, 'privacy_context', {})
        
        # Check if request requires specific consent
        required_consent = self._get_required_consent(request)
        
        if required_consent:
            consent_given = privacy_context.get('consent_given', {})
            
            # Check if required consent is granted
            if not consent_given.get(required_consent, False):
                return Response(
                    content=json.dumps({
                        'error': 'consent_required',
                        'message': f'Consent for {required_consent} is required',
                        'consent_type': required_consent,
                    }),
                    status_code=403,
                    media_type="application/json",
                )
        
        return await call_next(request)
    
    def _get_required_consent(self, request: Request) -> Optional[str]:
        """Determine what consent is required for this request."""
        path = request.url.path
        
        # Marketing endpoints
        if '/marketing/' in path or '/campaigns/' in path:
            return 'marketing'
        
        # Analytics endpoints
        if '/analytics/' in path or '/tracking/' in path:
            return 'analytics'
        
        # Personalization endpoints
        if '/recommendations/' in path or '/personalization/' in path:
            return 'personalization'
        
        return None


# Helper functions for consent management

def check_consent_required(request: Request, consent_type: str) -> bool:
    """
    Check if a specific consent is required and granted.
    
    Usage in endpoints:
        if check_consent_required(request, 'analytics'):
            # Track the event
            ...
    """
    privacy_context = getattr(request.state, 'privacy_context', {})
    
    # If GDPR doesn't apply, consent not required
    if not privacy_context.get('gdpr_applies'):
        return True
    
    # Check if consent is granted
    consent_given = privacy_context.get('consent_given', {})
    return consent_given.get(consent_type, False)


def get_privacy_context(request: Request) -> Dict[str, Any]:
    """Get privacy context from request state."""
    return getattr(request.state, 'privacy_context', {
        'do_not_track': False,
        'country_code': None,
        'is_eu_user': False,
        'consent_given': {},
        'gdpr_applies': False,
    })


def is_eu_user(request: Request) -> bool:
    """Check if user is from EU (GDPR applies)."""
    privacy_context = get_privacy_context(request)
    return privacy_context.get('is_eu_user', False)


def respects_do_not_track(request: Request) -> bool:
    """Check if user has Do Not Track enabled."""
    privacy_context = get_privacy_context(request)
    return privacy_context.get('do_not_track', False)