"""
Segment CDP integration client.

Provides bidirectional integration with Segment including:
- Event forwarding to Segment
- User identification
- Group tracking
- Webhook handling for incoming events
"""
import base64
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)


class SegmentError(Exception):
    """Base exception for Segment API errors."""
    pass


class SegmentAPIError(SegmentError):
    """API request error."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class SegmentClient:
    """
    Segment CDP integration client.
    
    Handles event forwarding to Segment and webhook processing
    for bidirectional data flow.
    """
    
    BASE_URL = "https://api.segment.io/v1"
    
    def __init__(self, write_key: str):
        """
        Initialize Segment client.
        
        Args:
            write_key: Segment write key for authentication
        """
        self.write_key = write_key
        self._client: Optional[httpx.AsyncClient] = None
    
    def _get_auth_header(self) -> str:
        """Generate Basic auth header from write key."""
        credentials = base64.b64encode(f"{self.write_key}:".encode()).decode()
        return f"Basic {credentials}"
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json"
                },
                timeout=30.0
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
    
    # Event Forwarding
    
    async def identify_user(
        self,
        user_id: str,
        traits: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Send user identification to Segment.
        
        Args:
            user_id: Unique user identifier
            traits: User traits (name, email, etc.)
            context: Additional context
            timestamp: Event timestamp
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        payload = {
            "userId": user_id,
            "traits": traits
        }
        
        if context:
            payload["context"] = context
        if timestamp:
            payload["timestamp"] = timestamp.isoformat()
        
        response = await client.post(
            f"{self.BASE_URL}/identify",
            json=payload
        )
        
        if response.status_code != 200:
            raise SegmentAPIError(
                f"Identify failed: {response.text}",
                status_code=response.status_code
            )
        
        logger.debug(f"Identified user {user_id} to Segment")
        return True
    
    async def track_event(
        self,
        user_id: str,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        anonymous_id: Optional[str] = None
    ) -> bool:
        """
        Track event in Segment.
        
        Args:
            user_id: Unique user identifier
            event_name: Event name
            properties: Event properties
            context: Additional context
            timestamp: Event timestamp
            anonymous_id: Anonymous ID for pre-login tracking
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        payload = {
            "event": event_name,
            "properties": properties or {}
        }
        
        if user_id:
            payload["userId"] = user_id
        if anonymous_id:
            payload["anonymousId"] = anonymous_id
        if context:
            payload["context"] = context
        if timestamp:
            payload["timestamp"] = timestamp.isoformat()
        
        response = await client.post(
            f"{self.BASE_URL}/track",
            json=payload
        )
        
        if response.status_code != 200:
            raise SegmentAPIError(
                f"Track failed: {response.text}",
                status_code=response.status_code
            )
        
        logger.debug(f"Tracked event {event_name} for user {user_id}")
        return True
    
    async def page(
        self,
        user_id: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Track page view in Segment.
        
        Args:
            user_id: Unique user identifier
            name: Page name
            category: Page category
            properties: Page properties
            context: Additional context
            timestamp: Event timestamp
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        payload = {
            "userId": user_id,
            "properties": properties or {}
        }
        
        if name:
            payload["name"] = name
        if category:
            payload["category"] = category
        if context:
            payload["context"] = context
        if timestamp:
            payload["timestamp"] = timestamp.isoformat()
        
        response = await client.post(
            f"{self.BASE_URL}/page",
            json=payload
        )
        
        if response.status_code != 200:
            raise SegmentAPIError(
                f"Page tracking failed: {response.text}",
                status_code=response.status_code
            )
        
        return True
    
    async def screen(
        self,
        user_id: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Track screen view in Segment (mobile apps).
        
        Args:
            user_id: Unique user identifier
            name: Screen name
            category: Screen category
            properties: Screen properties
            context: Additional context
            timestamp: Event timestamp
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        payload = {
            "userId": user_id,
            "properties": properties or {}
        }
        
        if name:
            payload["name"] = name
        if category:
            payload["category"] = category
        if context:
            payload["context"] = context
        if timestamp:
            payload["timestamp"] = timestamp.isoformat()
        
        response = await client.post(
            f"{self.BASE_URL}/screen",
            json=payload
        )
        
        if response.status_code != 200:
            raise SegmentAPIError(
                f"Screen tracking failed: {response.text}",
                status_code=response.status_code
            )
        
        return True
    
    async def group_user(
        self,
        user_id: str,
        group_id: str,
        traits: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Associate user with group/company.
        
        Args:
            user_id: Unique user identifier
            group_id: Group/company identifier
            traits: Group traits
            context: Additional context
            timestamp: Event timestamp
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        payload = {
            "userId": user_id,
            "groupId": group_id,
            "traits": traits or {}
        }
        
        if context:
            payload["context"] = context
        if timestamp:
            payload["timestamp"] = timestamp.isoformat()
        
        response = await client.post(
            f"{self.BASE_URL}/group",
            json=payload
        )
        
        if response.status_code != 200:
            raise SegmentAPIError(
                f"Group association failed: {response.text}",
                status_code=response.status_code
            )
        
        logger.debug(f"Associated user {user_id} with group {group_id}")
        return True
    
    async def alias(self, previous_id: str, user_id: str) -> bool:
        """
        Merge two user identities.
        
        Args:
            previous_id: Previous anonymous or temporary ID
            user_id: New user ID
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        payload = {
            "previousId": previous_id,
            "userId": user_id
        }
        
        response = await client.post(
            f"{self.BASE_URL}/alias",
            json=payload
        )
        
        if response.status_code != 200:
            raise SegmentAPIError(
                f"Alias failed: {response.text}",
                status_code=response.status_code
            )
        
        logger.debug(f"Aliased {previous_id} to {user_id}")
        return True
    
    async def batch_send(self, batch: List[Dict[str, Any]]) -> bool:
        """
        Send batch of events to Segment.
        
        Args:
            batch: List of event dictionaries
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        payload = {"batch": batch}
        
        response = await client.post(
            f"{self.BASE_URL}/batch",
            json=payload
        )
        
        if response.status_code != 200:
            raise SegmentAPIError(
                f"Batch send failed: {response.text}",
                status_code=response.status_code
            )
        
        logger.debug(f"Sent batch of {len(batch)} events to Segment")
        return True
    
    # Webhook Receiver
    
    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming Segment webhook.
        
        Args:
            payload: Webhook payload from Segment
            
        Returns:
            Processing result
        """
        event_type = payload.get("type", "unknown")
        
        logger.info(f"Processing Segment webhook: {event_type}")
        
        result = {
            "event_type": event_type,
            "processed": False,
            "data": None
        }
        
        if event_type == "identify":
            result["data"] = self._process_identify(payload)
            result["processed"] = True
        elif event_type == "track":
            result["data"] = self._process_track(payload)
            result["processed"] = True
        elif event_type == "page":
            result["data"] = self._process_page(payload)
            result["processed"] = True
        elif event_type == "group":
            result["data"] = self._process_group(payload)
            result["processed"] = True
        
        return result
    
    def _process_identify(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process identify event from Segment."""
        return {
            "user_id": payload.get("userId"),
            "anonymous_id": payload.get("anonymousId"),
            "traits": payload.get("traits", {}),
            "timestamp": payload.get("timestamp"),
            "context": payload.get("context", {})
        }
    
    def _process_track(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process track event from Segment."""
        return {
            "user_id": payload.get("userId"),
            "anonymous_id": payload.get("anonymousId"),
            "event": payload.get("event"),
            "properties": payload.get("properties", {}),
            "timestamp": payload.get("timestamp"),
            "context": payload.get("context", {})
        }
    
    def _process_page(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process page event from Segment."""
        return {
            "user_id": payload.get("userId"),
            "anonymous_id": payload.get("anonymousId"),
            "name": payload.get("name"),
            "category": payload.get("category"),
            "properties": payload.get("properties", {}),
            "timestamp": payload.get("timestamp")
        }
    
    def _process_group(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process group event from Segment."""
        return {
            "user_id": payload.get("userId"),
            "group_id": payload.get("groupId"),
            "traits": payload.get("traits", {}),
            "timestamp": payload.get("timestamp")
        }
    
    # Source Sync
    
    async def sync_from_segment_source(
        self,
        source_id: str,
        since: datetime,
        limit: int = 1000
    ) -> int:
        """
        Sync events from Segment source to CDP.
        
        Note: This requires Segment's HTTP API or a warehouse connection.
        For real-time sync, use webhooks instead.
        
        Args:
            source_id: Segment source ID
            since: Sync events since this time
            limit: Maximum events to sync
            
        Returns:
            Number of events synced
        """
        # This would typically connect to Segment's warehouse or
        # use the Config API to retrieve events
        # For now, this is a placeholder
        logger.info(f"Would sync events from Segment source {source_id}")
        return 0
    
    # Validation
    
    async def validate_connection(self) -> bool:
        """
        Test Segment connection.
        
        Returns:
            True if connection is valid
        """
        try:
            # Try to send a test identify call
            await self.identify_user(
                user_id="test_user",
                traits={"test": True}
            )
            return True
        except SegmentAPIError as e:
            if e.status_code == 401:
                logger.error("Invalid Segment write key")
            return False
        except Exception as e:
            logger.error(f"Segment connection validation failed: {e}")
            return False
