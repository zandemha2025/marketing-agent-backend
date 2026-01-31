"""
User repository.
"""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.user import User, UserRole


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_organization(
        self,
        organization_id: str,
        role: Optional[UserRole] = None
    ) -> List[User]:
        """Get all users in an organization, optionally filtered by role."""
        query = select(User).where(User.organization_id == organization_id)

        if role:
            query = query.where(User.role == role)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_user(
        self,
        email: str,
        name: str,
        organization_id: str,
        password_hash: Optional[str] = None,
        role: UserRole = UserRole.EDITOR,
        avatar_url: Optional[str] = None
    ) -> User:
        """Create a new user."""
        return await self.create(
            email=email,
            name=name,
            organization_id=organization_id,
            password_hash=password_hash,
            role=role,
            avatar_url=avatar_url,
            is_active=True,
            email_verified=False
        )

    async def update_role(
        self,
        user_id: str,
        role: UserRole
    ) -> Optional[User]:
        """Update a user's role."""
        return await self.update(user_id, role=role)

    async def verify_email(self, user_id: str) -> Optional[User]:
        """Mark user's email as verified."""
        return await self.update(user_id, email_verified=True)

    async def deactivate(self, user_id: str) -> Optional[User]:
        """Deactivate a user."""
        return await self.update(user_id, is_active=False)

    async def activate(self, user_id: str) -> Optional[User]:
        """Activate a user."""
        return await self.update(user_id, is_active=True)

    async def update_preferences(
        self,
        user_id: str,
        preferences: dict
    ) -> Optional[User]:
        """Update user preferences (merge with existing)."""
        user = await self.get(user_id)
        if user:
            merged = {**user.preferences, **preferences}
            return await self.update(user_id, preferences=merged)
        return None

    async def update_password(
        self,
        user_id: str,
        password_hash: str
    ) -> Optional[User]:
        """Update user's password hash."""
        return await self.update(user_id, password_hash=password_hash)

    async def get_admins(self, organization_id: str) -> List[User]:
        """Get all admin users in an organization."""
        return await self.get_by_organization(organization_id, role=UserRole.ADMIN)
