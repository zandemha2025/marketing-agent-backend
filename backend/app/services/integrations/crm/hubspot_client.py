"""
HubSpot CRM integration client.

Provides comprehensive API integration with HubSpot including:
- API key and OAuth authentication
- Contact, Company, and Deal management
- Engagement tracking
- List management for audience sync
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class HubSpotError(Exception):
    """Base exception for HubSpot API errors."""
    pass


class HubSpotAuthError(HubSpotError):
    """Authentication error."""
    pass


class HubSpotAPIError(HubSpotError):
    """API request error."""
    def __init__(self, message: str, status_code: int = None, response_body: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class HubSpotClient:
    """
    HubSpot CRM integration client.
    
    Handles all HubSpot API operations including authentication,
    data retrieval, and synchronization.
    """
    
    BASE_URL = "https://api.hubapi.com"
    OAUTH_URL = "https://api.hubapi.com/oauth/v1/token"
    
    def __init__(self, auth_config: Dict[str, Any]):
        """
        Initialize HubSpot client.
        
        Args:
            auth_config: Authentication configuration containing either:
                - api_key: HubSpot API key (private apps)
                - access_token: OAuth access token
                - refresh_token: OAuth refresh token
                - client_id: OAuth client ID
                - client_secret: OAuth client secret
        """
        self.api_key = auth_config.get("api_key")
        self.access_token = auth_config.get("access_token")
        self.refresh_token = auth_config.get("refresh_token")
        self.client_id = auth_config.get("client_id")
        self.client_secret = auth_config.get("client_secret")
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=60.0
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _get_auth_params(self) -> Dict[str, str]:
        """Get authentication parameters for requests."""
        if self.api_key:
            return {"hapikey": self.api_key}
        return {}
    
    # Authentication
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh OAuth access token.
        
        Returns:
            Updated auth configuration with new tokens
        """
        if not self.refresh_token:
            raise HubSpotAuthError("No refresh token available")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.OAUTH_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            
            if response.status_code != 200:
                raise HubSpotAuthError(
                    f"Token refresh failed: {response.text}"
                )
            
            data = response.json()
            self.access_token = data["access_token"]
            
            # Reset client to use new token
            if self._client:
                await self._client.aclose()
                self._client = None
            
            logger.info("HubSpot access token refreshed successfully")
            
            return {
                "access_token": self.access_token,
                "refresh_token": data.get("refresh_token", self.refresh_token),
                "expires_in": data.get("expires_in"),
                "token_type": data.get("token_type")
            }
    
    async def validate_connection(self) -> bool:
        """
        Test API connection by fetching account info.
        
        Returns:
            True if connection is valid
        """
        try:
            client = await self._get_client()
            params = self._get_auth_params()
            
            response = await client.get(
                f"{self.BASE_URL}/integrations/v1/me",
                params=params
            )
            
            if response.status_code == 401 and self.refresh_token:
                # Try refreshing token
                await self.refresh_access_token()
                client = await self._get_client()
                response = await client.get(
                    f"{self.BASE_URL}/integrations/v1/me",
                    params=params
                )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"HubSpot connection validation failed: {e}")
            return False
    
    # Contacts
    
    async def get_contacts(
        self,
        modified_since: Optional[datetime] = None,
        limit: int = 100,
        after: Optional[str] = None,
        properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch contacts from HubSpot.
        
        Args:
            modified_since: Only return contacts modified after this date
            limit: Maximum number of records to return (max 100)
            after: Pagination cursor
            properties: List of properties to return
            
        Returns:
            Dictionary with results and pagination info
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        params["limit"] = min(limit, 100)
        if after:
            params["after"] = after
        
        # Default properties if not specified
        if properties is None:
            properties = [
                "email", "firstname", "lastname", "phone", "mobilephone",
                "company", "jobtitle", "industry", "website",
                "address", "city", "state", "zip", "country",
                "hs_lead_status", "hs_analytics_source", "hs_lifecyclestage",
                "createdate", "lastmodifieddate"
            ]
        
        params["properties"] = ",".join(properties)
        
        if modified_since:
            # Use search API for time-based filtering
            return await self._search_contacts(modified_since, limit, after)
        
        response = await client.get(
            f"{self.BASE_URL}/crm/v3/objects/contacts",
            params=params
        )
        
        if response.status_code == 401 and self.refresh_token:
            await self.refresh_access_token()
            client = await self._get_client()
            response = await client.get(
                f"{self.BASE_URL}/crm/v3/objects/contacts",
                params=params
            )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to fetch contacts: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    async def _search_contacts(
        self,
        modified_since: datetime,
        limit: int = 100,
        after: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search contacts modified since a specific date."""
        client = await self._get_client()
        params = self._get_auth_params()
        
        timestamp = int(modified_since.timestamp() * 1000)
        
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "lastmodifieddate",
                            "operator": "GTE",
                            "value": timestamp
                        }
                    ]
                }
            ],
            "limit": min(limit, 100),
            "properties": [
                "email", "firstname", "lastname", "phone", "mobilephone",
                "company", "jobtitle", "industry", "website",
                "address", "city", "state", "zip", "country",
                "hs_lead_status", "hs_analytics_source", "hs_lifecyclestage",
                "createdate", "lastmodifieddate"
            ]
        }
        
        if after:
            payload["after"] = after
        
        response = await client.post(
            f"{self.BASE_URL}/crm/v3/objects/contacts/search",
            params=params,
            json=payload
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to search contacts: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    async def get_contact_by_id(self, contact_id: str) -> Dict[str, Any]:
        """
        Get a specific contact by ID.
        
        Args:
            contact_id: HubSpot contact ID
            
        Returns:
            Contact record
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        params["properties"] = ",".join([
            "email", "firstname", "lastname", "phone", "mobilephone",
            "company", "jobtitle", "industry", "website",
            "address", "city", "state", "zip", "country",
            "hs_lead_status", "hs_analytics_source", "hs_lifecyclestage"
        ])
        
        response = await client.get(
            f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}",
            params=params
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to get contact: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    async def get_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a contact by email address.
        
        Args:
            email: Contact email address
            
        Returns:
            Contact record or None if not found
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email
                        }
                    ]
                }
            ],
            "limit": 1
        }
        
        response = await client.post(
            f"{self.BASE_URL}/crm/v3/objects/contacts/search",
            params=params,
            json=payload
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to search contact by email: {response.text}",
                status_code=response.status_code
            )
        
        data = response.json()
        results = data.get("results", [])
        
        return results[0] if results else None
    
    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a contact in HubSpot.
        
        Args:
            contact_data: Contact properties
            
        Returns:
            Created contact
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        # Transform property names to HubSpot format
        properties = self._transform_properties(contact_data)
        
        payload = {"properties": properties}
        
        response = await client.post(
            f"{self.BASE_URL}/crm/v3/objects/contacts",
            params=params,
            json=payload
        )
        
        if response.status_code == 409:
            # Contact already exists, update instead
            existing = await self.get_contact_by_email(contact_data.get("email"))
            if existing:
                return await self.update_contact(existing["id"], contact_data)
        
        if response.status_code != 201:
            raise HubSpotAPIError(
                f"Failed to create contact: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    async def update_contact(
        self,
        contact_id: str,
        contact_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a contact in HubSpot.
        
        Args:
            contact_id: HubSpot contact ID
            contact_data: Contact properties to update
            
        Returns:
            Updated contact
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        # Transform property names to HubSpot format
        properties = self._transform_properties(contact_data)
        
        payload = {"properties": properties}
        
        response = await client.patch(
            f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}",
            params=params,
            json=payload
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to update contact: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    # Companies
    
    async def get_companies(
        self,
        limit: int = 100,
        after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch companies from HubSpot.
        
        Args:
            limit: Maximum number of records to return
            after: Pagination cursor
            
        Returns:
            Dictionary with results and pagination info
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        params["limit"] = min(limit, 100)
        if after:
            params["after"] = after
        
        params["properties"] = ",".join([
            "name", "domain", "industry", "type", "phone",
            "address", "city", "state", "zip", "country",
            "website", "numberofemployees", "annualrevenue",
            "description", "hs_lead_status"
        ])
        
        response = await client.get(
            f"{self.BASE_URL}/crm/v3/objects/companies",
            params=params
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to fetch companies: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    async def create_company(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a company in HubSpot.
        
        Args:
            company_data: Company properties
            
        Returns:
            Created company
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        properties = self._transform_properties(company_data)
        payload = {"properties": properties}
        
        response = await client.post(
            f"{self.BASE_URL}/crm/v3/objects/companies",
            params=params,
            json=payload
        )
        
        if response.status_code != 201:
            raise HubSpotAPIError(
                f"Failed to create company: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    # Deals
    
    async def get_deals(
        self,
        modified_since: Optional[datetime] = None,
        limit: int = 100,
        after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch deals for revenue tracking.
        
        Args:
            modified_since: Only return deals modified after this date
            limit: Maximum number of records to return
            after: Pagination cursor
            
        Returns:
            Dictionary with results and pagination info
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        params["limit"] = min(limit, 100)
        if after:
            params["after"] = after
        
        params["properties"] = ",".join([
            "dealname", "amount", "closedate", "dealstage",
            "pipeline", "hs_is_closed", "hs_is_closed_won",
            "hs_object_source", "hubspot_owner_id",
            "createdate", "lastmodifieddate"
        ])
        
        params["associations"] = "contacts,companies"
        
        response = await client.get(
            f"{self.BASE_URL}/crm/v3/objects/deals",
            params=params
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to fetch deals: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    async def create_deal(
        self,
        deal_data: Dict[str, Any],
        contact_ids: Optional[List[str]] = None,
        company_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a deal in HubSpot.
        
        Args:
            deal_data: Deal properties
            contact_ids: Associated contact IDs
            company_ids: Associated company IDs
            
        Returns:
            Created deal
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        properties = self._transform_properties(deal_data)
        payload = {"properties": properties}
        
        # Add associations
        associations = []
        if contact_ids:
            for contact_id in contact_ids:
                associations.append({
                    "to": {"id": contact_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]
                })
        if company_ids:
            for company_id in company_ids:
                associations.append({
                    "to": {"id": company_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}]
                })
        
        if associations:
            payload["associations"] = associations
        
        response = await client.post(
            f"{self.BASE_URL}/crm/v3/objects/deals",
            params=params,
            json=payload
        )
        
        if response.status_code != 201:
            raise HubSpotAPIError(
                f"Failed to create deal: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    # Engagements
    
    async def create_engagement(
        self,
        engagement_type: str,  # NOTE, CALL, EMAIL, TASK, MEETING
        metadata: Dict[str, Any],
        contact_ids: Optional[List[str]] = None,
        company_ids: Optional[List[str]] = None,
        deal_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Log engagement activity.
        
        Args:
            engagement_type: Type of engagement (NOTE, CALL, EMAIL, TASK, MEETING)
            metadata: Engagement metadata
            contact_ids: Associated contact IDs
            company_ids: Associated company IDs
            deal_ids: Associated deal IDs
            
        Returns:
            Created engagement
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        payload = {
            "engagement": {
                "type": engagement_type,
                "timestamp": int(datetime.utcnow().timestamp() * 1000)
            },
            "metadata": metadata,
            "associations": {
                "contactIds": contact_ids or [],
                "companyIds": company_ids or [],
                "dealIds": deal_ids or []
            }
        }
        
        response = await client.post(
            f"{self.BASE_URL}/engagements/v1/engagements",
            params=params,
            json=payload
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to create engagement: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    async def create_note(
        self,
        body: str,
        contact_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a note engagement.
        
        Args:
            body: Note content
            contact_ids: Associated contact IDs
            
        Returns:
            Created note
        """
        return await self.create_engagement(
            engagement_type="NOTE",
            metadata={"body": body},
            contact_ids=contact_ids
        )
    
    # Lists
    
    async def get_lists(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get HubSpot lists for audience sync.
        
        Args:
            limit: Maximum number of lists to return
            
        Returns:
            List of HubSpot lists
        """
        client = await self._get_client()
        params = self._get_auth_params()
        params["limit"] = limit
        
        response = await client.get(
            f"{self.BASE_URL}/contacts/v1/lists",
            params=params
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to fetch lists: {response.text}",
                status_code=response.status_code
            )
        
        data = response.json()
        return data.get("lists", [])
    
    async def add_to_list(self, list_id: str, contact_ids: List[str]) -> bool:
        """
        Add contacts to a HubSpot list.
        
        Args:
            list_id: HubSpot list ID
            contact_ids: List of contact IDs to add
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        payload = {"vids": contact_ids}
        
        response = await client.post(
            f"{self.BASE_URL}/contacts/v1/lists/{list_id}/add",
            params=params,
            json=payload
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to add contacts to list: {response.text}",
                status_code=response.status_code
            )
        
        return True
    
    async def remove_from_list(self, list_id: str, contact_ids: List[str]) -> bool:
        """
        Remove contacts from a HubSpot list.
        
        Args:
            list_id: HubSpot list ID
            contact_ids: List of contact IDs to remove
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        payload = {"vids": contact_ids}
        
        response = await client.post(
            f"{self.BASE_URL}/contacts/v1/lists/{list_id}/remove",
            params=params,
            json=payload
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to remove contacts from list: {response.text}",
                status_code=response.status_code
            )
        
        return True
    
    # Private helper methods
    
    def _transform_properties(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform property names to HubSpot format.
        
        Maps common field names to HubSpot property names.
        """
        mapping = {
            "first_name": "firstname",
            "last_name": "lastname",
            "phone_number": "phone",
            "mobile_phone": "mobilephone",
            "job_title": "jobtitle",
            "lifecycle_stage": "hs_lifecyclestage",
            "lead_status": "hs_lead_status",
            "analytics_source": "hs_analytics_source",
            "company_name": "name",
            "employee_count": "numberofemployees",
            "annual_revenue": "annualrevenue",
            "deal_name": "dealname",
            "close_date": "closedate",
            "deal_stage": "dealstage",
            "is_closed": "hs_is_closed",
            "is_closed_won": "hs_is_closed_won"
        }
        
        result = {}
        for key, value in data.items():
            hubspot_key = mapping.get(key.lower(), key)
            result[hubspot_key] = value
        
        return result
    
    async def get_property_definitions(self, object_type: str = "contacts") -> List[Dict[str, Any]]:
        """
        Get property definitions for an object type.
        
        Args:
            object_type: Type of object (contacts, companies, deals)
            
        Returns:
            List of property definitions
        """
        client = await self._get_client()
        params = self._get_auth_params()
        
        response = await client.get(
            f"{self.BASE_URL}/crm/v3/properties/{object_type}",
            params=params
        )
        
        if response.status_code != 200:
            raise HubSpotAPIError(
                f"Failed to fetch properties: {response.text}",
                status_code=response.status_code
            )
        
        data = response.json()
        return data.get("results", [])
