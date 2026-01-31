"""
Organization repository.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.user import Organization, SubscriptionTier


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for Organization operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Organization, session)

    async def get_by_domain(self, domain: str) -> Optional[Organization]:
        """Get organization by domain."""
        result = await self.session.execute(
            select(Organization).where(Organization.domain == domain)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        result = await self.session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_with_knowledge_base(self, id: str) -> Optional[Organization]:
        """Get organization with its knowledge base loaded."""
        result = await self.session.execute(
            select(Organization)
            .options(selectinload(Organization.knowledge_base))
            .where(Organization.id == id)
        )
        return result.scalar_one_or_none()

    async def get_with_users(self, id: str) -> Optional[Organization]:
        """Get organization with its users loaded."""
        result = await self.session.execute(
            select(Organization)
            .options(selectinload(Organization.users))
            .where(Organization.id == id)
        )
        return result.scalar_one_or_none()

    async def create_organization(
        self,
        name: str,
        slug: str,
        domain: str = None,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        settings: dict = None
    ) -> Organization:
        """Create a new organization."""
        return await self.create(
            name=name,
            slug=slug,
            domain=domain,
            subscription_tier=tier,
            settings=settings or {}
        )

    async def update_settings(
        self,
        id: str,
        settings: dict
    ) -> Optional[Organization]:
        """Update organization settings (merge with existing)."""
        org = await self.get(id)
        if org:
            merged_settings = {**org.settings, **settings}
            return await self.update(id, settings=merged_settings)
        return None

    async def upgrade_tier(
        self,
        id: str,
        tier: SubscriptionTier
    ) -> Optional[Organization]:
        """Upgrade organization subscription tier."""
        return await self.update(id, subscription_tier=tier)
