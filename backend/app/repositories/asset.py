"""
Asset repository.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.asset import Asset, AssetVersion, AssetComment, AssetType, AssetStatus


class AssetRepository(BaseRepository[Asset]):
    """Repository for Asset operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Asset, session)

    async def get_by_campaign(
        self,
        campaign_id: str,
        asset_type: Optional[AssetType] = None,
        status: Optional[AssetStatus] = None
    ) -> List[Asset]:
        """Get assets for a campaign."""
        query = select(Asset).where(Asset.campaign_id == campaign_id)

        if asset_type:
            query = query.where(Asset.asset_type == asset_type)
        if status:
            query = query.where(Asset.status == status)

        query = query.order_by(Asset.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_organization(
        self,
        organization_id: str,
        asset_type: Optional[AssetType] = None,
        status: Optional[AssetStatus] = None
    ) -> List[Asset]:
        """Get all assets for an organization (across all campaigns)."""
        from ..models.campaign import Campaign
        
        query = (
            select(Asset)
            .join(Campaign, Asset.campaign_id == Campaign.id)
            .where(Campaign.organization_id == organization_id)
        )

        if asset_type:
            query = query.where(Asset.asset_type == asset_type)
        if status:
            query = query.where(Asset.status == status)

        query = query.order_by(Asset.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_phase(
        self,
        phase_id: str,
        asset_type: Optional[AssetType] = None
    ) -> List[Asset]:
        """Get assets for a specific phase."""
        query = select(Asset).where(Asset.phase_id == phase_id)

        if asset_type:
            query = query.where(Asset.asset_type == asset_type)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_versions(self, id: str) -> Optional[Asset]:
        """Get asset with all versions loaded."""
        result = await self.session.execute(
            select(Asset)
            .options(selectinload(Asset.versions))
            .where(Asset.id == id)
        )
        return result.scalar_one_or_none()

    async def get_with_comments(self, id: str) -> Optional[Asset]:
        """Get asset with comments loaded."""
        result = await self.session.execute(
            select(Asset)
            .options(selectinload(Asset.comments))
            .where(Asset.id == id)
        )
        return result.scalar_one_or_none()

    async def create_asset(
        self,
        campaign_id: str,
        name: str,
        asset_type: AssetType,
        created_by: str,
        phase_id: Optional[str] = None,
        description: Optional[str] = None,
        platform: Optional[str] = None,
        initial_content: Dict[str, Any] = None
    ) -> Asset:
        """Create a new asset with initial version."""
        # Create the asset
        asset = await self.create(
            campaign_id=campaign_id,
            phase_id=phase_id,
            name=name,
            asset_type=asset_type,
            description=description,
            platform=platform,
            created_by=created_by,
            current_version=1,
            status=AssetStatus.DRAFT
        )

        # Create initial version if content provided
        if initial_content:
            version_repo = AssetVersionRepository(self.session)
            await version_repo.create_version(
                asset_id=asset.id,
                version_number=1,
                content=initial_content,
                created_by=created_by,
                created_by_ai=True
            )

        return asset

    async def update_status(
        self,
        id: str,
        status: AssetStatus
    ) -> Optional[Asset]:
        """Update asset status."""
        return await self.update(id, status=status)

    async def increment_version(self, id: str) -> Optional[Asset]:
        """Increment the current version number."""
        asset = await self.get(id)
        if asset:
            return await self.update(id, current_version=asset.current_version + 1)
        return None

    async def branch_asset(
        self,
        original_id: str,
        new_name: str,
        created_by: str
    ) -> Optional[Asset]:
        """Create a branch of an existing asset."""
        original = await self.get_with_versions(original_id)
        if not original:
            return None

        # Create new asset as branch
        branch = await self.create(
            campaign_id=original.campaign_id,
            phase_id=original.phase_id,
            name=new_name,
            asset_type=original.asset_type,
            description=f"Branch of {original.name}",
            platform=original.platform,
            created_by=created_by,
            current_version=1,
            status=AssetStatus.DRAFT,
            branched_from=original_id,
            is_branch=True
        )

        # Copy current version content
        if original.current_content:
            version_repo = AssetVersionRepository(self.session)
            await version_repo.create_version(
                asset_id=branch.id,
                version_number=1,
                content=original.current_content,
                created_by=created_by,
                created_by_ai=False,
                change_summary=f"Branched from {original.name} v{original.current_version}"
            )

        return branch


class AssetVersionRepository(BaseRepository[AssetVersion]):
    """Repository for AssetVersion operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AssetVersion, session)

    async def get_by_asset(
        self,
        asset_id: str
    ) -> List[AssetVersion]:
        """Get all versions for an asset."""
        result = await self.session.execute(
            select(AssetVersion)
            .where(AssetVersion.asset_id == asset_id)
            .order_by(AssetVersion.version_number)
        )
        return list(result.scalars().all())

    async def get_version(
        self,
        asset_id: str,
        version_number: int
    ) -> Optional[AssetVersion]:
        """Get a specific version of an asset."""
        result = await self.session.execute(
            select(AssetVersion).where(
                AssetVersion.asset_id == asset_id,
                AssetVersion.version_number == version_number
            )
        )
        return result.scalar_one_or_none()

    async def get_latest(self, asset_id: str) -> Optional[AssetVersion]:
        """Get the latest version of an asset."""
        result = await self.session.execute(
            select(AssetVersion)
            .where(AssetVersion.asset_id == asset_id)
            .order_by(AssetVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_version(
        self,
        asset_id: str,
        version_number: int,
        content: Dict[str, Any],
        created_by: Optional[str] = None,
        created_by_ai: bool = True,
        change_summary: Optional[str] = None,
        parent_version: Optional[int] = None
    ) -> AssetVersion:
        """Create a new version of an asset."""
        return await self.create(
            asset_id=asset_id,
            version_number=version_number,
            content=content,
            created_by=created_by,
            created_by_ai=created_by_ai,
            change_summary=change_summary,
            parent_version=parent_version
        )


class AssetCommentRepository(BaseRepository[AssetComment]):
    """Repository for AssetComment operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AssetComment, session)

    async def get_by_asset(
        self,
        asset_id: str,
        version_number: Optional[int] = None,
        include_resolved: bool = False
    ) -> List[AssetComment]:
        """Get comments for an asset."""
        query = (
            select(AssetComment)
            .where(
                AssetComment.asset_id == asset_id,
                AssetComment.parent_id.is_(None)  # Top-level only
            )
        )

        if version_number:
            query = query.where(AssetComment.version_number == version_number)

        if not include_resolved:
            query = query.where(AssetComment.resolved == False)

        query = query.order_by(AssetComment.created_at)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_comment(
        self,
        asset_id: str,
        version_number: int,
        user_id: str,
        content: str,
        position: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None
    ) -> AssetComment:
        """Create a new comment."""
        return await self.create(
            asset_id=asset_id,
            version_number=version_number,
            user_id=user_id,
            content=content,
            position=position,
            parent_id=parent_id,
            resolved=False
        )

    async def resolve_comment(
        self,
        id: str,
        resolved_by: str
    ) -> Optional[AssetComment]:
        """Resolve a comment."""
        return await self.update(id, resolved=True, resolved_by=resolved_by)

    async def unresolve_comment(self, id: str) -> Optional[AssetComment]:
        """Unresolve a comment."""
        return await self.update(id, resolved=False, resolved_by=None)

    async def get_thread(self, parent_id: str) -> List[AssetComment]:
        """Get all replies to a comment."""
        result = await self.session.execute(
            select(AssetComment)
            .where(AssetComment.parent_id == parent_id)
            .order_by(AssetComment.created_at)
        )
        return list(result.scalars().all())
