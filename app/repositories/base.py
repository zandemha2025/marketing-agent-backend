"""
Base repository with common CRUD operations.
"""
from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: str) -> Optional[ModelType]:
        """Get a record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """Get all records with optional filtering and pagination."""
        query = select(self.model)

        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.where(getattr(self.model, key) == value)

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **data) -> ModelType:
        """Create a new record."""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: str, **data) -> Optional[ModelType]:
        """Update a record by ID."""
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        if data:
            await self.session.execute(
                update(self.model)
                .where(self.model.id == id)
                .values(**data)
            )

        return await self.get(id)

    async def delete(self, id: str) -> bool:
        """Delete a record by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0

    async def exists(self, id: str) -> bool:
        """Check if a record exists."""
        result = await self.session.execute(
            select(self.model.id).where(self.model.id == id)
        )
        return result.scalar_one_or_none() is not None

    async def count(self, **filters) -> int:
        """Count records with optional filtering."""
        from sqlalchemy import func
        query = select(func.count(self.model.id))

        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalar_one()
