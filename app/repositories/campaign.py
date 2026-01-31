"""
Campaign repository.
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.campaign import Campaign, CampaignPhase, CampaignStatus, CampaignType, PhaseStatus


class CampaignRepository(BaseRepository[Campaign]):
    """Repository for Campaign operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Campaign, session)

    async def get_by_id(self, campaign_id: str) -> Optional[Campaign]:
        """Get a campaign by ID (alias for base get method)."""
        return await self.get(campaign_id)

    async def get_by_status(
        self,
        organization_id: str,
        status: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Campaign]:
        """Get campaigns by status for an organization."""
        query = (
            select(Campaign)
            .where(Campaign.organization_id == organization_id)
            .where(Campaign.status == status)
            .order_by(Campaign.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_organization(self, organization_id: str) -> int:
        """Count campaigns for an organization."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count(Campaign.id))
            .where(Campaign.organization_id == organization_id)
        )
        return result.scalar_one()

    async def get_by_organization(
        self,
        organization_id: str,
        status: Optional[CampaignStatus] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Campaign]:
        """Get campaigns for an organization."""
        query = (
            select(Campaign)
            .where(Campaign.organization_id == organization_id)
            .order_by(Campaign.created_at.desc())
        )

        if status:
            query = query.where(Campaign.status == status)

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_phases(self, id: str) -> Optional[Campaign]:
        """Get campaign with phases loaded."""
        result = await self.session.execute(
            select(Campaign)
            .options(selectinload(Campaign.phases))
            .where(Campaign.id == id)
        )
        return result.scalar_one_or_none()

    async def get_with_assets(self, id: str) -> Optional[Campaign]:
        """Get campaign with assets loaded."""
        result = await self.session.execute(
            select(Campaign)
            .options(selectinload(Campaign.assets))
            .where(Campaign.id == id)
        )
        return result.scalar_one_or_none()

    async def get_full(self, id: str) -> Optional[Campaign]:
        """Get campaign with all relationships loaded."""
        result = await self.session.execute(
            select(Campaign)
            .options(
                selectinload(Campaign.phases).selectinload(CampaignPhase.assets),
                selectinload(Campaign.assets),
                selectinload(Campaign.conversations)
            )
            .where(Campaign.id == id)
        )
        return result.scalar_one_or_none()

    async def create_campaign(
        self,
        organization_id: str,
        name: str,
        campaign_type: CampaignType,
        created_by: str,
        description: Optional[str] = None,
        brief_data: dict = None,
        strategy_data: dict = None
    ) -> Campaign:
        """Create a new campaign."""
        return await self.create(
            organization_id=organization_id,
            name=name,
            campaign_type=campaign_type,
            created_by=created_by,
            description=description,
            status=CampaignStatus.DRAFT,
            brief_data=brief_data or {},
            strategy_data=strategy_data or {}
        )

    async def update_status(
        self,
        id: str,
        status: CampaignStatus
    ) -> Optional[Campaign]:
        """Update campaign status."""
        return await self.update(id, status=status)

    async def update_brief(
        self,
        id: str,
        brief_data: dict,
        increment_version: bool = True
    ) -> Optional[Campaign]:
        """Update campaign brief."""
        campaign = await self.get(id)
        if not campaign:
            return None

        version = campaign.brief_version + 1 if increment_version else campaign.brief_version
        return await self.update(
            id,
            brief_data=brief_data,
            brief_version=version
        )

    async def update_strategy(
        self,
        id: str,
        strategy_data: dict
    ) -> Optional[Campaign]:
        """Update campaign strategy data."""
        return await self.update(id, strategy_data=strategy_data)

    async def get_active_campaigns(
        self,
        organization_id: str
    ) -> List[Campaign]:
        """Get all active campaigns for an organization."""
        return await self.get_by_organization(
            organization_id,
            status=CampaignStatus.ACTIVE
        )


class CampaignPhaseRepository(BaseRepository[CampaignPhase]):
    """Repository for CampaignPhase operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(CampaignPhase, session)

    async def get_by_campaign(
        self,
        campaign_id: str
    ) -> List[CampaignPhase]:
        """Get all phases for a campaign, ordered by index."""
        result = await self.session.execute(
            select(CampaignPhase)
            .where(CampaignPhase.campaign_id == campaign_id)
            .order_by(CampaignPhase.order_index)
        )
        return list(result.scalars().all())

    async def create_phase(
        self,
        campaign_id: str,
        name: str,
        order_index: int,
        description: Optional[str] = None,
        details: dict = None
    ) -> CampaignPhase:
        """Create a new campaign phase."""
        return await self.create(
            campaign_id=campaign_id,
            name=name,
            order_index=order_index,
            description=description,
            status=PhaseStatus.NOT_STARTED,
            details=details or {}
        )

    async def update_status(
        self,
        id: str,
        status: PhaseStatus
    ) -> Optional[CampaignPhase]:
        """Update phase status."""
        return await self.update(id, status=status)

    async def reorder_phases(
        self,
        campaign_id: str,
        phase_order: List[str]
    ) -> List[CampaignPhase]:
        """Reorder phases by updating their order_index values."""
        phases = await self.get_by_campaign(campaign_id)
        phase_map = {p.id: p for p in phases}

        for index, phase_id in enumerate(phase_order):
            if phase_id in phase_map:
                await self.update(phase_id, order_index=index)

        return await self.get_by_campaign(campaign_id)
