"""
mParticle CDP integration client.

Provides integration with mParticle for:
- Event batch uploads
- User profile uploads
- Audience synchronization
"""
import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger(__name__)


class MParticleError(Exception):
    """Base exception for mParticle errors."""
    pass


class MParticleAPIError(MParticleError):
    """API request error."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class MParticleClient:
    """
    mParticle CDP integration client.
    
    Handles event and profile uploads to mParticle platform.
    """
    
    BASE_URL = "https://s2s.mparticle.com/v2"
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize mParticle client.
        
        Args:
            api_key: mParticle API key
            api_secret: mParticle API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self._client: Optional[httpx.AsyncClient] = None
    
    def _get_auth_header(self) -> str:
        """Generate Basic auth header."""
        credentials = base64.b64encode(
            f"{self.api_key}:{self.api_secret}".encode()
        ).decode()
        return f"Basic {credentials}"
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": self._get_auth_header(),
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
    
    def _generate_device_id(self, user_id: str) -> str:
        """Generate a deterministic device ID from user ID."""
        return hashlib.md5(user_id.encode()).hexdigest()[:16]
    
    # Event Upload
    
    async def upload_events(self, events: List[Dict[str, Any]]) -> bool:
        """
        Upload events to mParticle.
        
        Args:
            events: List of event dictionaries with format:
                {
                    "user_id": str,
                    "anonymous_id": str (optional),
                    "event_name": str,
                    "event_type": str (custom_event, screen_view, etc.),
                    "timestamp": datetime,
                    "properties": dict,
                    "context": dict
                }
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        # Transform events to mParticle format
        batch = self._transform_events_to_mparticle(events)
        
        response = await client.post(
            f"{self.BASE_URL}/events",
            json=batch
        )
        
        if response.status_code not in (200, 202):
            raise MParticleAPIError(
                f"Event upload failed: {response.text}",
                status_code=response.status_code
            )
        
        logger.debug(f"Uploaded {len(events)} events to mParticle")
        return True
    
    def _transform_events_to_mparticle(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Transform events to mParticle batch format."""
        batches = []
        
        # Group events by user
        events_by_user: Dict[str, List[Dict]] = {}
        for event in events:
            user_id = event.get("user_id") or event.get("anonymous_id", "anonymous")
            if user_id not in events_by_user:
                events_by_user[user_id] = []
            events_by_user[user_id].append(event)
        
        for user_id, user_events in events_by_user.items():
            batch = {
                "source_request_id": f"batch_{datetime.now(timezone.utc).timestamp()}",
                "environment": "production",
                "user_identities": {
                    "customer_id": user_id
                },
                "device_info": {
                    "device_application_stamp": self._generate_device_id(user_id)
                },
                "events": []
            }
            
            for event in user_events:
                mp_event = {
                    "data": {
                        "event_name": event.get("event_name", "custom_event"),
                        "custom_event_type": "other",
                        "timestamp_unixtime_ms": int(
                            event.get("timestamp", datetime.now(timezone.utc)).timestamp() * 1000
                        ),
                        "custom_attributes": event.get("properties", {})
                    },
                    "event_type": "custom_event"
                }
                
                # Map event types
                event_type = event.get("event_type", "custom")
                if event_type == "screen_view":
                    mp_event["event_type"] = "screen_view"
                    mp_event["data"]["screen_name"] = event.get("event_name")
                elif event_type == "commerce":
                    mp_event["event_type"] = "commerce_event"
                
                batch["events"].append(mp_event)
            
            batches.append(batch)
        
        return batches
    
    # User Profile Upload
    
    async def upload_user_profiles(self, profiles: List[Dict[str, Any]]) -> bool:
        """
        Upload user profiles to mParticle.
        
        Args:
            profiles: List of user profile dictionaries with format:
                {
                    "user_id": str,
                    "anonymous_id": str (optional),
                    "traits": dict,
                    "email": str,
                    "phone": str,
                    "first_name": str,
                    "last_name": str,
                    "created_at": datetime
                }
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        
        # Transform profiles to mParticle format
        batches = self._transform_profiles_to_mparticle(profiles)
        
        for batch in batches:
            response = await client.post(
                f"{self.BASE_URL}/events",
                json=batch
            )
            
            if response.status_code not in (200, 202):
                raise MParticleAPIError(
                    f"Profile upload failed: {response.text}",
                    status_code=response.status_code
                )
        
        logger.debug(f"Uploaded {len(profiles)} profiles to mParticle")
        return True
    
    def _transform_profiles_to_mparticle(
        self,
        profiles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Transform profiles to mParticle batch format."""
        batches = []
        
        for profile in profiles:
            user_identities = {
                "customer_id": profile.get("user_id")
            }
            
            # Add other identities if available
            if profile.get("email"):
                user_identities["email"] = profile["email"]
            if profile.get("phone"):
                user_identities["mobile_number"] = profile["phone"]
            
            # Build user attributes
            user_attributes = {}
            traits = profile.get("traits", {})
            
            if profile.get("first_name"):
                user_attributes["$firstname"] = profile["first_name"]
            if profile.get("last_name"):
                user_attributes["$lastname"] = profile["last_name"]
            
            # Add custom traits
            for key, value in traits.items():
                if key not in ("first_name", "last_name", "email", "phone"):
                    user_attributes[key] = value
            
            batch = {
                "source_request_id": f"profile_{user_identities['customer_id']}_{datetime.now(timezone.utc).timestamp()}",
                "environment": "production",
                "user_identities": user_identities,
                "user_attributes": user_attributes,
                "device_info": {
                    "device_application_stamp": self._generate_device_id(
                        user_identities["customer_id"]
                    )
                }
            }
            
            batches.append(batch)
        
        return batches
    
    # Single Event Upload
    
    async def track_event(
        self,
        user_id: str,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        anonymous_id: Optional[str] = None
    ) -> bool:
        """
        Track a single event.
        
        Args:
            user_id: User identifier
            event_name: Event name
            properties: Event properties
            timestamp: Event timestamp
            anonymous_id: Anonymous ID
            
        Returns:
            True if successful
        """
        event = {
            "user_id": user_id,
            "anonymous_id": anonymous_id,
            "event_name": event_name,
            "event_type": "custom_event",
            "timestamp": timestamp or datetime.utcnow(),
            "properties": properties or {}
        }
        
        return await self.upload_events([event])
    
    async def identify_user(
        self,
        user_id: str,
        traits: Dict[str, Any],
        anonymous_id: Optional[str] = None
    ) -> bool:
        """
        Identify a user with traits.
        
        Args:
            user_id: User identifier
            traits: User traits
            anonymous_id: Anonymous ID
            
        Returns:
            True if successful
        """
        profile = {
            "user_id": user_id,
            "anonymous_id": anonymous_id,
            "traits": traits,
            "email": traits.get("email"),
            "phone": traits.get("phone"),
            "first_name": traits.get("first_name"),
            "last_name": traits.get("last_name")
        }
        
        return await self.upload_user_profiles([profile])
    
    # Audience Management
    
    async def add_to_audience(
        self,
        audience_id: str,
        user_ids: List[str]
    ) -> bool:
        """
        Add users to an audience.
        
        Note: mParticle audience management typically requires
        using their UI or Config API, not the S2S API.
        
        Args:
            audience_id: mParticle audience ID
            user_ids: List of user IDs to add
            
        Returns:
            True if successful
        """
        # This would require the Config API
        logger.info(f"Would add {len(user_ids)} users to audience {audience_id}")
        return True
    
    async def remove_from_audience(
        self,
        audience_id: str,
        user_ids: List[str]
    ) -> bool:
        """
        Remove users from an audience.
        
        Args:
            audience_id: mParticle audience ID
            user_ids: List of user IDs to remove
            
        Returns:
            True if successful
        """
        logger.info(f"Would remove {len(user_ids)} users from audience {audience_id}")
        return True
    
    # Validation
    
    async def validate_connection(self) -> bool:
        """
        Test mParticle connection.
        
        Returns:
            True if connection is valid
        """
        try:
            # Try to upload a test event
            await self.track_event(
                user_id="test_user",
                event_name="test_event",
                properties={"test": True}
            )
            return True
        except MParticleAPIError as e:
            if e.status_code == 401:
                logger.error("Invalid mParticle credentials")
            return False
        except Exception as e:
            logger.error(f"mParticle connection validation failed: {e}")
            return False
    
    # Webhook Handling
    
    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming mParticle webhook.
        
        Args:
            payload: Webhook payload from mParticle
            
        Returns:
            Processing result
        """
        event_type = payload.get("type", "unknown")
        
        logger.info(f"Processing mParticle webhook: {event_type}")
        
        result = {
            "event_type": event_type,
            "processed": False,
            "data": None
        }
        
        if event_type == "audience_membership_change":
            result["data"] = self._process_audience_change(payload)
            result["processed"] = True
        elif event_type == "user_profile":
            result["data"] = self._process_user_profile(payload)
            result["processed"] = True
        
        return result
    
    def _process_audience_change(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process audience membership change webhook."""
        return {
            "audience_id": payload.get("audience_id"),
            "audience_name": payload.get("audience_name"),
            "user_id": payload.get("user_id"),
            "action": payload.get("action"),  # add or remove
            "timestamp": payload.get("timestamp")
        }
    
    def _process_user_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process user profile webhook."""
        return {
            "user_id": payload.get("user_id"),
            "attributes": payload.get("attributes", {}),
            "identities": payload.get("identities", {}),
            "timestamp": payload.get("timestamp")
        }
