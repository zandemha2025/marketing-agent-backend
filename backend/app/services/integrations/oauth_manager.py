"""
OAuth flow management for CRM integrations.

Handles OAuth 2.0 authentication flows for:
- Salesforce
- HubSpot
- Microsoft Dynamics
"""
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)


class OAuthManager:
    """
    OAuth flow manager for CRM integrations.
    
    Handles the complete OAuth 2.0 flow including:
    - Authorization URL generation
    - Token exchange
    - Token refresh
    """
    
    # Salesforce OAuth endpoints
    SALESFORCE_AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
    SALESFORCE_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
    SALESFORCE_AUTH_URL_SANDBOX = "https://test.salesforce.com/services/oauth2/authorize"
    SALESFORCE_TOKEN_URL_SANDBOX = "https://test.salesforce.com/services/oauth2/token"
    
    # HubSpot OAuth endpoints
    HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
    HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    
    # Microsoft Dynamics OAuth endpoints
    DYNAMICS_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    DYNAMICS_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    def __init__(self):
        """Initialize OAuth manager."""
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # Salesforce OAuth
    
    async def get_salesforce_auth_url(
        self,
        client_id: str,
        redirect_uri: str,
        state: str,
        scopes: Optional[list] = None,
        is_sandbox: bool = False
    ) -> str:
        """
        Generate Salesforce OAuth authorization URL.
        
        Args:
            client_id: Salesforce connected app client ID
            redirect_uri: OAuth callback URL
            state: CSRF protection state parameter
            scopes: OAuth scopes (default: api refresh_token)
            is_sandbox: Use sandbox environment
            
        Returns:
            Authorization URL
        """
        auth_url = self.SALESFORCE_AUTH_URL_SANDBOX if is_sandbox else self.SALESFORCE_AUTH_URL
        
        if scopes is None:
            scopes = ["api", "refresh_token"]
        
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes)
        }
        
        return f"{auth_url}?{urlencode(params)}"
    
    async def exchange_salesforce_code(
        self,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        is_sandbox: bool = False
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for Salesforce tokens.
        
        Args:
            client_id: Salesforce connected app client ID
            client_secret: Salesforce connected app client secret
            code: Authorization code from callback
            redirect_uri: OAuth callback URL
            is_sandbox: Use sandbox environment
            
        Returns:
            Token response with access_token, refresh_token, etc.
        """
        token_url = self.SALESFORCE_TOKEN_URL_SANDBOX if is_sandbox else self.SALESFORCE_TOKEN_URL
        
        client = await self._get_client()
        
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Salesforce token exchange failed: {response.text}")
            raise OAuthError(f"Token exchange failed: {response.text}")
        
        data = response.json()
        
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "instance_url": data.get("instance_url"),
            "id": data.get("id"),
            "issued_at": data.get("issued_at"),
            "signature": data.get("signature"),
            "scope": data.get("scope"),
            "token_type": data.get("token_type", "Bearer"),
            "is_sandbox": is_sandbox
        }
    
    async def refresh_salesforce_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        is_sandbox: bool = False
    ) -> Dict[str, Any]:
        """
        Refresh Salesforce access token.
        
        Args:
            client_id: Salesforce connected app client ID
            client_secret: Salesforce connected app client secret
            refresh_token: Refresh token
            is_sandbox: Use sandbox environment
            
        Returns:
            New token response
        """
        token_url = self.SALESFORCE_TOKEN_URL_SANDBOX if is_sandbox else self.SALESFORCE_TOKEN_URL
        
        client = await self._get_client()
        
        response = await client.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Salesforce token refresh failed: {response.text}")
            raise OAuthError(f"Token refresh failed: {response.text}")
        
        data = response.json()
        
        return {
            "access_token": data["access_token"],
            "instance_url": data.get("instance_url"),
            "id": data.get("id"),
            "issued_at": data.get("issued_at"),
            "signature": data.get("signature"),
            "scope": data.get("scope"),
            "token_type": data.get("token_type", "Bearer")
        }
    
    # HubSpot OAuth
    
    async def get_hubspot_auth_url(
        self,
        client_id: str,
        redirect_uri: str,
        state: str,
        scopes: Optional[list] = None,
        optional_scopes: Optional[list] = None
    ) -> str:
        """
        Generate HubSpot OAuth authorization URL.
        
        Args:
            client_id: HubSpot app client ID
            redirect_uri: OAuth callback URL
            state: CSRF protection state parameter
            scopes: Required OAuth scopes
            optional_scopes: Optional OAuth scopes
            
        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = [
                "oauth",
                "crm.objects.contacts.read",
                "crm.objects.contacts.write",
                "crm.objects.companies.read",
                "crm.objects.companies.write",
                "crm.objects.deals.read",
                "crm.objects.deals.write",
                "crm.schemas.contacts.read"
            ]
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state
        }
        
        if optional_scopes:
            params["optional_scope"] = " ".join(optional_scopes)
        
        return f"{self.HUBSPOT_AUTH_URL}?{urlencode(params)}"
    
    async def exchange_hubspot_code(
        self,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for HubSpot tokens.
        
        Args:
            client_id: HubSpot app client ID
            client_secret: HubSpot app client secret
            code: Authorization code from callback
            redirect_uri: OAuth callback URL
            
        Returns:
            Token response
        """
        client = await self._get_client()
        
        response = await client.post(
            self.HUBSPOT_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri
            }
        )
        
        if response.status_code != 200:
            logger.error(f"HubSpot token exchange failed: {response.text}")
            raise OAuthError(f"Token exchange failed: {response.text}")
        
        data = response.json()
        
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope")
        }
    
    async def refresh_hubspot_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh HubSpot access token.
        
        Args:
            client_id: HubSpot app client ID
            client_secret: HubSpot app client secret
            refresh_token: Refresh token
            
        Returns:
            New token response
        """
        client = await self._get_client()
        
        response = await client.post(
            self.HUBSPOT_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
        )
        
        if response.status_code != 200:
            logger.error(f"HubSpot token refresh failed: {response.text}")
            raise OAuthError(f"Token refresh failed: {response.text}")
        
        data = response.json()
        
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope")
        }
    
    # Microsoft Dynamics OAuth
    
    async def get_dynamics_auth_url(
        self,
        client_id: str,
        redirect_uri: str,
        state: str,
        scopes: Optional[list] = None
    ) -> str:
        """
        Generate Microsoft Dynamics OAuth authorization URL.
        
        Args:
            client_id: Azure AD app client ID
            redirect_uri: OAuth callback URL
            state: CSRF protection state parameter
            scopes: OAuth scopes
            
        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = [
                "https://org.crm.dynamics.com/.default",
                "offline_access"
            ]
        
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "response_mode": "query"
        }
        
        return f"{self.DYNAMICS_AUTH_URL}?{urlencode(params)}"
    
    async def exchange_dynamics_code(
        self,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for Dynamics tokens.
        
        Args:
            client_id: Azure AD app client ID
            client_secret: Azure AD app client secret
            code: Authorization code from callback
            redirect_uri: OAuth callback URL
            
        Returns:
            Token response
        """
        client = await self._get_client()
        
        response = await client.post(
            self.DYNAMICS_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Dynamics token exchange failed: {response.text}")
            raise OAuthError(f"Token exchange failed: {response.text}")
        
        data = response.json()
        
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope")
        }
    
    async def refresh_dynamics_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """
        Refresh Dynamics access token.
        
        Args:
            client_id: Azure AD app client ID
            client_secret: Azure AD app client secret
            refresh_token: Refresh token
            
        Returns:
            New token response
        """
        client = await self._get_client()
        
        response = await client.post(
            self.DYNAMICS_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Dynamics token refresh failed: {response.text}")
            raise OAuthError(f"Token refresh failed: {response.text}")
        
        data = response.json()
        
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope")
        }


class OAuthError(Exception):
    """OAuth operation error."""
    pass
