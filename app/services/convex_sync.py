"""
Convex Sync Service

Provides HTTP interface to sync data with Convex for real-time updates.
The FastAPI backend uses this to push deliverables and campaign updates
to Convex, which then broadcasts to all connected frontend clients.
"""

import httpx
from typing import Any, Dict, List, Optional
import logging

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class ConvexSyncService:
    """
    Service for syncing data with Convex via HTTP mutations.

    Convex provides an HTTP API for mutations that we can call from the backend.
    This allows the orchestrator to push real-time updates that all frontend
    clients will receive through Convex's built-in subscriptions.
    """

    def __init__(self):
        settings = get_settings()
        self.convex_url = settings.convex_url
        self.convex_deploy_key = settings.convex_deploy_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _call_mutation(self, function_name: str, args: Dict[str, Any]) -> Any:
        """
        Call a Convex mutation via HTTP.

        Args:
            function_name: Full function path (e.g., "deliverables:create")
            args: Arguments to pass to the mutation

        Returns:
            The result from Convex
        """
        url = f"{self.convex_url}/api/mutation"

        headers = {
            "Content-Type": "application/json",
        }

        # Add deploy key if available (for authenticated mutations)
        if self.convex_deploy_key:
            headers["Authorization"] = f"Convex {self.convex_deploy_key}"

        payload = {
            "path": function_name,
            "args": args,
            "format": "json"
        }

        try:
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result.get("value")
        except httpx.HTTPStatusError as e:
            logger.error(f"Convex mutation error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Convex sync error: {e}")
            raise

    async def _call_query(self, function_name: str, args: Dict[str, Any]) -> Any:
        """
        Call a Convex query via HTTP.

        Args:
            function_name: Full function path (e.g., "deliverables:listByCampaign")
            args: Arguments to pass to the query

        Returns:
            The result from Convex
        """
        url = f"{self.convex_url}/api/query"

        headers = {
            "Content-Type": "application/json",
        }

        if self.convex_deploy_key:
            headers["Authorization"] = f"Convex {self.convex_deploy_key}"

        payload = {
            "path": function_name,
            "args": args,
            "format": "json"
        }

        try:
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result.get("value")
        except Exception as e:
            logger.error(f"Convex query error: {e}")
            raise

    # ==================== Deliverables ====================

    async def create_deliverable(
        self,
        campaign_id: str,
        deliverable_type: str,
        data: Dict[str, Any],
        platform: Optional[str] = None,
        status: str = "generating",
        order: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Create a new deliverable in Convex.

        Args:
            campaign_id: Convex campaign ID
            deliverable_type: Type of deliverable (social_post, video, email, etc.)
            data: Deliverable data (varies by type)
            platform: Optional platform (tiktok, instagram, etc.)
            status: Status (generating, ready, approved)
            order: Optional ordering
            created_by: Optional user ID

        Returns:
            The created deliverable's Convex ID
        """
        args = {
            "campaign_id": campaign_id,
            "type": deliverable_type,
            "data": data,
            "status": status
        }

        if platform:
            args["platform"] = platform
        if order is not None:
            args["order"] = order
        if created_by:
            args["created_by"] = created_by

        return await self._call_mutation("deliverables:create", args)

    async def update_deliverable(
        self,
        deliverable_id: str,
        data: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        platform: Optional[str] = None
    ) -> str:
        """
        Update an existing deliverable in Convex.

        Args:
            deliverable_id: Convex deliverable ID
            data: Optional new data
            status: Optional new status
            platform: Optional platform update

        Returns:
            The deliverable ID
        """
        args = {"id": deliverable_id}

        if data is not None:
            args["data"] = data
        if status is not None:
            args["status"] = status
        if platform is not None:
            args["platform"] = platform

        return await self._call_mutation("deliverables:update", args)

    async def update_deliverable_status(
        self,
        deliverable_id: str,
        status: str
    ) -> str:
        """Update just the status of a deliverable."""
        return await self._call_mutation("deliverables:updateStatus", {
            "id": deliverable_id,
            "status": status
        })

    async def get_deliverables_by_campaign(self, campaign_id: str) -> List[Dict]:
        """Get all deliverables for a campaign."""
        return await self._call_query("deliverables:listByCampaign", {
            "campaign_id": campaign_id
        })

    # ==================== Campaigns ====================

    async def update_campaign_status(self, campaign_id: str, status: str) -> str:
        """
        Update a campaign's status in Convex.

        Args:
            campaign_id: Convex campaign ID
            status: New status (draft, queued, running, complete, failed)

        Returns:
            The campaign ID
        """
        return await self._call_mutation("campaigns:updateStatus", {
            "id": campaign_id,
            "status": status
        })

    async def update_campaign_concepts(
        self,
        campaign_id: str,
        concepts: List[Dict[str, Any]],
        selected_index: Optional[int] = None
    ) -> str:
        """
        Update a campaign's creative concepts in Convex.

        Args:
            campaign_id: Convex campaign ID
            concepts: List of concept objects
            selected_index: Optional index of selected concept

        Returns:
            The campaign ID
        """
        args = {
            "id": campaign_id,
            "creative_concepts": concepts
        }

        if selected_index is not None:
            args["selected_concept_index"] = selected_index

        return await self._call_mutation("campaigns:updateCreativeConcepts", args)

    async def update_campaign_brief(
        self,
        campaign_id: str,
        brief_data: Dict[str, Any]
    ) -> str:
        """Update a campaign's brief data in Convex."""
        return await self._call_mutation("campaigns:updateBriefData", {
            "id": campaign_id,
            "brief_data": brief_data
        })

    # ==================== Messages ====================

    async def add_user_message(
        self,
        conversation_id: str,
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a user message to a conversation."""
        args = {
            "conversation_id": conversation_id,
            "content": content
        }
        if user_id:
            args["user_id"] = user_id
        if metadata:
            args["metadata"] = metadata

        return await self._call_mutation("messages:addUserMessage", args)

    async def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add an assistant message to a conversation."""
        args = {
            "conversation_id": conversation_id,
            "content": content
        }
        if metadata:
            args["metadata"] = metadata

        return await self._call_mutation("messages:addAssistantMessage", args)

    # ==================== Conversations ====================

    async def create_conversation(
        self,
        organization_id: str,
        campaign_id: Optional[str] = None,
        title: Optional[str] = None,
        context_type: str = "general"
    ) -> str:
        """Create a new conversation in Convex."""
        args = {
            "organization_id": organization_id,
            "context_type": context_type
        }
        if campaign_id:
            args["campaign_id"] = campaign_id
        if title:
            args["title"] = title

        return await self._call_mutation("conversations:create", args)

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Singleton instance
_convex_service: Optional[ConvexSyncService] = None


def get_convex_service() -> ConvexSyncService:
    """Get the singleton Convex sync service."""
    global _convex_service
    if _convex_service is None:
        _convex_service = ConvexSyncService()
    return _convex_service
