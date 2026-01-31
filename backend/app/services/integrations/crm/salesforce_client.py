"""
Salesforce CRM integration client.

Provides comprehensive API integration with Salesforce including:
- OAuth authentication and token refresh
- Contact, Lead, Opportunity, and Campaign management
- SOQL query execution
- Webhook handling for real-time updates
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class SalesforceError(Exception):
    """Base exception for Salesforce API errors."""
    pass


class SalesforceAuthError(SalesforceError):
    """Authentication error."""
    pass


class SalesforceAPIError(SalesforceError):
    """API request error."""
    def __init__(self, message: str, status_code: int = None, response_body: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SalesforceClient:
    """
    Salesforce CRM integration client.
    
    Handles all Salesforce API operations including authentication,
    data retrieval, and synchronization.
    """
    
    OAUTH_URL = "https://login.salesforce.com/services/oauth2/token"
    OAUTH_URL_SANDBOX = "https://test.salesforce.com/services/oauth2/token"
    
    def __init__(self, auth_config: Dict[str, Any]):
        """
        Initialize Salesforce client.
        
        Args:
            auth_config: Authentication configuration containing:
                - access_token: OAuth access token
                - refresh_token: OAuth refresh token
                - instance_url: Salesforce instance URL
                - client_id: OAuth client ID
                - client_secret: OAuth client secret
                - is_sandbox: Whether using sandbox environment
        """
        self.access_token = auth_config.get("access_token")
        self.refresh_token = auth_config.get("refresh_token")
        self.instance_url = auth_config.get("instance_url", "").rstrip("/")
        self.client_id = auth_config.get("client_id")
        self.client_secret = auth_config.get("client_secret")
        self.is_sandbox = auth_config.get("is_sandbox", False)
        self.api_version = auth_config.get("api_version", "v58.0")
        
        self.oauth_url = self.OAUTH_URL_SANDBOX if self.is_sandbox else self.OAUTH_URL
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
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
    
    # Authentication
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh OAuth access token using refresh token.
        
        Returns:
            Updated auth configuration with new tokens
        """
        if not self.refresh_token:
            raise SalesforceAuthError("No refresh token available")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.oauth_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            
            if response.status_code != 200:
                raise SalesforceAuthError(
                    f"Token refresh failed: {response.text}"
                )
            
            data = response.json()
            self.access_token = data["access_token"]
            
            # Update instance URL if provided
            if "instance_url" in data:
                self.instance_url = data["instance_url"].rstrip("/")
            
            # Reset client to use new token
            if self._client:
                await self._client.aclose()
                self._client = None
            
            logger.info("Salesforce access token refreshed successfully")
            
            return {
                "access_token": self.access_token,
                "instance_url": self.instance_url,
                "refresh_token": self.refresh_token,  # Usually same
                "issued_at": data.get("issued_at"),
                "signature": data.get("signature")
            }
    
    async def validate_connection(self) -> bool:
        """
        Test API connection by querying user info.
        
        Returns:
            True if connection is valid
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.instance_url}/services/oauth2/userinfo"
            )
            
            if response.status_code == 401:
                # Try refreshing token
                await self.refresh_access_token()
                client = await self._get_client()
                response = await client.get(
                    f"{self.instance_url}/services/oauth2/userinfo"
                )
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Salesforce connection validation failed: {e}")
            return False
    
    # Data Retrieval
    
    async def get_contacts(
        self,
        modified_since: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Fetch contacts from Salesforce.
        
        Args:
            modified_since: Only return contacts modified after this date
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of contact records
        """
        fields = [
            "Id", "FirstName", "LastName", "Email", "Phone", "MobilePhone",
            "Title", "Department", "AccountId", "Account.Name",
            "MailingStreet", "MailingCity", "MailingState", "MailingPostalCode", "MailingCountry",
            "CreatedDate", "LastModifiedDate", "IsDeleted", "OwnerId"
        ]
        
        where_clauses = ["IsDeleted = false"]
        if modified_since:
            where_clauses.append(f"LastModifiedDate >= {modified_since.isoformat()}")
        
        soql = f"""
            SELECT {', '.join(fields)}
            FROM Contact
            WHERE {' AND '.join(where_clauses)}
            ORDER BY LastModifiedDate DESC
            LIMIT {limit}
        """
        
        return await self.query(soql)
    
    async def get_leads(
        self,
        modified_since: Optional[datetime] = None,
        limit: int = 1000,
        converted: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch leads from Salesforce.
        
        Args:
            modified_since: Only return leads modified after this date
            limit: Maximum number of records to return
            converted: Filter by converted status
            
        Returns:
            List of lead records
        """
        fields = [
            "Id", "FirstName", "LastName", "Email", "Phone", "MobilePhone",
            "Company", "Title", "Industry", "Status", "Rating",
            "Street", "City", "State", "PostalCode", "Country",
            "Website", "NumberOfEmployees", "AnnualRevenue",
            "LeadSource", "Description",
            "CreatedDate", "LastModifiedDate", "IsConverted", "ConvertedDate",
            "ConvertedAccountId", "ConvertedContactId", "ConvertedOpportunityId",
            "OwnerId"
        ]
        
        where_clauses = ["IsDeleted = false"]
        if modified_since:
            where_clauses.append(f"LastModifiedDate >= {modified_since.isoformat()}")
        if converted is not None:
            where_clauses.append(f"IsConverted = {str(converted).lower()}")
        
        soql = f"""
            SELECT {', '.join(fields)}
            FROM Lead
            WHERE {' AND '.join(where_clauses)}
            ORDER BY LastModifiedDate DESC
            LIMIT {limit}
        """
        
        return await self.query(soql)
    
    async def get_opportunities(
        self,
        modified_since: Optional[datetime] = None,
        limit: int = 1000,
        stage_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch opportunities for revenue attribution.
        
        Args:
            modified_since: Only return opportunities modified after this date
            limit: Maximum number of records to return
            stage_name: Filter by stage name
            
        Returns:
            List of opportunity records
        """
        fields = [
            "Id", "Name", "AccountId", "Account.Name",
            "Amount", "Probability", "StageName", "Type",
            "LeadSource", "CampaignId", "Campaign.Name",
            "CloseDate", "IsClosed", "IsWon",
            "CreatedDate", "LastModifiedDate",
            "OwnerId", "Owner.Name"
        ]
        
        where_clauses = ["IsDeleted = false"]
        if modified_since:
            where_clauses.append(f"LastModifiedDate >= {modified_since.isoformat()}")
        if stage_name:
            where_clauses.append(f"StageName = '{stage_name}'")
        
        soql = f"""
            SELECT {', '.join(fields)}
            FROM Opportunity
            WHERE {' AND '.join(where_clauses)}
            ORDER BY LastModifiedDate DESC
            LIMIT {limit}
        """
        
        return await self.query(soql)
    
    async def get_campaigns(
        self,
        modified_since: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Fetch Salesforce campaigns.
        
        Args:
            modified_since: Only return campaigns modified after this date
            limit: Maximum number of records to return
            
        Returns:
            List of campaign records
        """
        fields = [
            "Id", "Name", "Type", "Status", "StartDate", "EndDate",
            "ExpectedRevenue", "BudgetedCost", "ActualCost",
            "NumberOfLeads", "NumberOfConvertedLeads",
            "NumberOfOpportunities", "NumberOfWonOpportunities",
            "AmountAllOpportunities", "AmountWonOpportunities",
            "Description", "ParentId",
            "CreatedDate", "LastModifiedDate"
        ]
        
        where_clauses = ["IsDeleted = false"]
        if modified_since:
            where_clauses.append(f"LastModifiedDate >= {modified_since.isoformat()}")
        
        soql = f"""
            SELECT {', '.join(fields)}
            FROM Campaign
            WHERE {' AND '.join(where_clauses)}
            ORDER BY LastModifiedDate DESC
            LIMIT {limit}
        """
        
        return await self.query(soql)
    
    async def get_campaign_members(
        self,
        campaign_id: str,
        limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Fetch members of a specific campaign.
        
        Args:
            campaign_id: Salesforce campaign ID
            limit: Maximum number of records to return
            
        Returns:
            List of campaign member records
        """
        fields = [
            "Id", "CampaignId", "LeadId", "ContactId",
            "Status", "HasResponded", "CreatedDate", "LastModifiedDate"
        ]
        
        soql = f"""
            SELECT {', '.join(fields)}
            FROM CampaignMember
            WHERE CampaignId = '{campaign_id}' AND IsDeleted = false
            LIMIT {limit}
        """
        
        return await self.query(soql)
    
    # Data Sync to Salesforce
    
    async def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a contact in Salesforce.
        
        Args:
            contact_data: Contact fields to create
            
        Returns:
            Created contact with Id
        """
        return await self._create_record("Contact", contact_data)
    
    async def update_contact(
        self,
        contact_id: str,
        contact_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a contact in Salesforce.
        
        Args:
            contact_id: Salesforce contact ID
            contact_data: Contact fields to update
            
        Returns:
            Updated contact
        """
        return await self._update_record("Contact", contact_id, contact_data)
    
    async def create_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a lead in Salesforce.
        
        Args:
            lead_data: Lead fields to create
            
        Returns:
            Created lead with Id
        """
        return await self._create_record("Lead", lead_data)
    
    async def update_lead(
        self,
        lead_id: str,
        lead_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update a lead in Salesforce.
        
        Args:
            lead_id: Salesforce lead ID
            lead_data: Lead fields to update
            
        Returns:
            Updated lead
        """
        return await self._update_record("Lead", lead_id, lead_data)
    
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a task (e.g., follow-up reminder) in Salesforce.
        
        Args:
            task_data: Task fields including:
                - Subject: Task subject
                - Status: Not Started, In Progress, Completed
                - Priority: High, Normal, Low
                - ActivityDate: Due date
                - WhoId: Contact or Lead ID
                - WhatId: Related object ID
                - OwnerId: Task owner
                
        Returns:
            Created task with Id
        """
        return await self._create_record("Task", task_data)
    
    async def create_campaign_member(
        self,
        campaign_id: str,
        lead_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        status: str = "Sent"
    ) -> Dict[str, Any]:
        """
        Add a lead or contact to a campaign.
        
        Args:
            campaign_id: Salesforce campaign ID
            lead_id: Lead ID (either lead_id or contact_id required)
            contact_id: Contact ID
            status: Campaign member status
            
        Returns:
            Created campaign member
        """
        data = {
            "CampaignId": campaign_id,
            "Status": status
        }
        if lead_id:
            data["LeadId"] = lead_id
        if contact_id:
            data["ContactId"] = contact_id
        
        return await self._create_record("CampaignMember", data)
    
    # SOQL Query
    
    async def query(self, soql: str) -> List[Dict[str, Any]]:
        """
        Execute a SOQL query.
        
        Args:
            soql: SOQL query string
            
        Returns:
            List of query results
        """
        client = await self._get_client()
        
        encoded_query = soql.replace(" ", "+").replace("\n", " ")
        url = f"{self.instance_url}/services/data/{self.api_version}/query?q={encoded_query}"
        
        response = await client.get(url)
        
        if response.status_code == 401:
            # Token expired, refresh and retry
            await self.refresh_access_token()
            client = await self._get_client()
            response = await client.get(url)
        
        if response.status_code != 200:
            raise SalesforceAPIError(
                f"Query failed: {response.text}",
                status_code=response.status_code,
                response_body=response.json() if response.text else None
            )
        
        data = response.json()
        records = data.get("records", [])
        
        # Handle pagination
        next_url = data.get("nextRecordsUrl")
        while next_url and len(records) < data.get("totalSize", 0):
            response = await client.get(f"{self.instance_url}{next_url}")
            if response.status_code == 200:
                page_data = response.json()
                records.extend(page_data.get("records", []))
                next_url = page_data.get("nextRecordsUrl")
            else:
                break
        
        return records
    
    # Webhook Handling
    
    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming Salesforce webhook (Platform Event or Outbound Message).
        
        Args:
            payload: Webhook payload
            
        Returns:
            Processing result
        """
        event_type = payload.get("event", {}).get("type", "unknown")
        sobject_type = payload.get("sobjectType")
        record_id = payload.get("Id")
        
        logger.info(f"Processing Salesforce webhook: {event_type} on {sobject_type}")
        
        result = {
            "event_type": event_type,
            "sobject_type": sobject_type,
            "record_id": record_id,
            "processed": False
        }
        
        # Handle different event types
        if sobject_type == "Contact":
            if event_type in ["created", "updated"]:
                # Fetch full contact record
                contact = await self._get_record("Contact", record_id)
                result["data"] = contact
                result["processed"] = True
                
        elif sobject_type == "Lead":
            if event_type in ["created", "updated"]:
                lead = await self._get_record("Lead", record_id)
                result["data"] = lead
                result["processed"] = True
                
        elif sobject_type == "Opportunity":
            if event_type in ["created", "updated"]:
                opp = await self._get_record("Opportunity", record_id)
                result["data"] = opp
                result["processed"] = True
        
        return result
    
    # Private helper methods
    
    async def _create_record(
        self,
        sobject_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a Salesforce record."""
        client = await self._get_client()
        
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/{sobject_type}"
        
        response = await client.post(url, json=data)
        
        if response.status_code == 401:
            await self.refresh_access_token()
            client = await self._get_client()
            response = await client.post(url, json=data)
        
        if response.status_code not in (200, 201):
            raise SalesforceAPIError(
                f"Failed to create {sobject_type}: {response.text}",
                status_code=response.status_code
            )
        
        result = response.json()
        
        # Fetch the created record
        if result.get("success") and result.get("id"):
            return await self._get_record(sobject_type, result["id"])
        
        return result
    
    async def _update_record(
        self,
        sobject_type: str,
        record_id: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a Salesforce record."""
        client = await self._get_client()
        
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/{sobject_type}/{record_id}"
        
        response = await client.patch(url, json=data)
        
        if response.status_code == 401:
            await self.refresh_access_token()
            client = await self._get_client()
            response = await client.patch(url, json=data)
        
        if response.status_code not in (200, 204):
            raise SalesforceAPIError(
                f"Failed to update {sobject_type}: {response.text}",
                status_code=response.status_code
            )
        
        # Fetch the updated record
        return await self._get_record(sobject_type, record_id)
    
    async def _get_record(
        self,
        sobject_type: str,
        record_id: str
    ) -> Dict[str, Any]:
        """Get a Salesforce record by ID."""
        client = await self._get_client()
        
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/{sobject_type}/{record_id}"
        
        response = await client.get(url)
        
        if response.status_code == 401:
            await self.refresh_access_token()
            client = await self._get_client()
            response = await client.get(url)
        
        if response.status_code != 200:
            raise SalesforceAPIError(
                f"Failed to get {sobject_type}: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
    
    async def get_object_schema(self, sobject_type: str) -> Dict[str, Any]:
        """
        Get schema for a Salesforce object.
        
        Args:
            sobject_type: Object type (Contact, Lead, etc.)
            
        Returns:
            Object schema with fields
        """
        client = await self._get_client()
        
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/{sobject_type}/describe"
        
        response = await client.get(url)
        
        if response.status_code == 401:
            await self.refresh_access_token()
            client = await self._get_client()
            response = await client.get(url)
        
        if response.status_code != 200:
            raise SalesforceAPIError(
                f"Failed to get schema for {sobject_type}: {response.text}",
                status_code=response.status_code
            )
        
        return response.json()
