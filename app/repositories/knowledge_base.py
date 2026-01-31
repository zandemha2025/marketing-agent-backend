"""
Knowledge Base repository.
"""
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.knowledge_base import KnowledgeBase, ResearchStatus


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    """Repository for KnowledgeBase operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(KnowledgeBase, session)

    async def get_by_organization(
        self,
        organization_id: str
    ) -> Optional[KnowledgeBase]:
        """Get knowledge base by organization ID."""
        result = await self.session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def create_for_organization(
        self,
        organization_id: str
    ) -> KnowledgeBase:
        """Create a new knowledge base for an organization."""
        return await self.create(
            organization_id=organization_id,
            research_status=ResearchStatus.PENDING,
            research_progress=0.0
        )

    async def update_research_status(
        self,
        organization_id: str,
        status: ResearchStatus,
        progress: float = None,
        stage: str = None,
        error: str = None
    ) -> Optional[KnowledgeBase]:
        """Update the research status of a knowledge base."""
        kb = await self.get_by_organization(organization_id)
        if not kb:
            return None

        update_data = {"research_status": status}
        if progress is not None:
            update_data["research_progress"] = progress
        if stage is not None:
            update_data["research_stage"] = stage
        if error is not None:
            update_data["research_error"] = error

        return await self.update(kb.id, **update_data)

    async def update_brand_data(
        self,
        organization_id: str,
        brand_data: Dict[str, Any],
        merge: bool = True
    ) -> Optional[KnowledgeBase]:
        """Update brand data for a knowledge base."""
        kb = await self.get_by_organization(organization_id)
        if not kb:
            return None

        if merge:
            merged_data = {**kb.brand_data, **brand_data}
        else:
            merged_data = brand_data

        return await self.update(kb.id, brand_data=merged_data)

    async def update_market_data(
        self,
        organization_id: str,
        market_data: Dict[str, Any],
        merge: bool = True
    ) -> Optional[KnowledgeBase]:
        """Update market data for a knowledge base."""
        kb = await self.get_by_organization(organization_id)
        if not kb:
            return None

        if merge:
            merged_data = {**kb.market_data, **market_data}
        else:
            merged_data = market_data

        return await self.update(kb.id, market_data=merged_data)

    async def update_audiences_data(
        self,
        organization_id: str,
        audiences_data: Dict[str, Any],
        merge: bool = True
    ) -> Optional[KnowledgeBase]:
        """Update audiences data for a knowledge base."""
        kb = await self.get_by_organization(organization_id)
        if not kb:
            return None

        if merge:
            merged_data = {**kb.audiences_data, **audiences_data}
        else:
            merged_data = audiences_data

        return await self.update(kb.id, audiences_data=merged_data)

    async def update_offerings_data(
        self,
        organization_id: str,
        offerings_data: Dict[str, Any],
        merge: bool = True
    ) -> Optional[KnowledgeBase]:
        """Update offerings data for a knowledge base."""
        kb = await self.get_by_organization(organization_id)
        if not kb:
            return None

        if merge:
            merged_data = {**kb.offerings_data, **offerings_data}
        else:
            merged_data = offerings_data

        return await self.update(kb.id, offerings_data=merged_data)

    async def update_context_data(
        self,
        organization_id: str,
        context_data: Dict[str, Any],
        merge: bool = True
    ) -> Optional[KnowledgeBase]:
        """Update context data for a knowledge base."""
        kb = await self.get_by_organization(organization_id)
        if not kb:
            return None

        if merge:
            merged_data = {**kb.context_data, **context_data}
        else:
            merged_data = context_data

        return await self.update(kb.id, context_data=merged_data)

    async def save_onboarding_result(
        self,
        organization_id: str,
        brand_data: Dict[str, Any],
        market_data: Dict[str, Any],
        audiences_data: Dict[str, Any],
        offerings_data: Dict[str, Any],
        context_data: Dict[str, Any]
    ) -> Optional[KnowledgeBase]:
        """
        Save complete onboarding result to knowledge base.

        This is called after the onboarding pipeline completes
        to persist all research data.
        """
        kb = await self.get_by_organization(organization_id)
        if not kb:
            kb = await self.create_for_organization(organization_id)

        return await self.update(
            kb.id,
            brand_data=brand_data,
            market_data=market_data,
            audiences_data=audiences_data,
            offerings_data=offerings_data,
            context_data=context_data,
            research_status=ResearchStatus.COMPLETE,
            research_progress=1.0,
            research_stage="complete"
        )

    async def mark_stale(self, organization_id: str) -> Optional[KnowledgeBase]:
        """Mark knowledge base as needing refresh."""
        return await self.update_research_status(
            organization_id,
            ResearchStatus.STALE,
            stage="needs_refresh"
        )

    async def get_for_campaign(
        self,
        organization_id: str,
        campaign_type: str
    ) -> Dict[str, Any]:
        """
        Get relevant knowledge base data for campaign generation.

        Filters and prioritizes information based on campaign type.
        """
        kb = await self.get_by_organization(organization_id)
        if not kb:
            return {}

        return kb.get_context_for_campaign(campaign_type)

    async def get_presentation_data(
        self,
        organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get knowledge base data formatted for presentation.

        Used in the onboarding flow to show "Here's what we learned".
        """
        kb = await self.get_by_organization(organization_id)
        if not kb:
            return None

        return kb.to_presentation_format()
