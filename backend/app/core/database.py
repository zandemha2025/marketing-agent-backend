"""
Database connection and session management.

Supports both PostgreSQL (production) and SQLite (local development).
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, StaticPool

from .config import get_settings
from ..models.base import Base


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str = None):
        settings = get_settings()
        url = database_url or settings.database_url

        # Determine database type and configure accordingly
        pool_class = None
        connect_args = {}

        if url.startswith("sqlite"):
            # SQLite for local development
            # Try to use a temp directory to avoid disk I/O issues on certain filesystems
            import tempfile
            db_dir = os.environ.get('SQLITE_DB_DIR')
            if not db_dir:
                # Use the backend directory as default
                db_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(db_dir, "data.db")
            url = f"sqlite+aiosqlite:///{db_path}"
            pool_class = StaticPool
            connect_args = {"check_same_thread": False}

        elif url.startswith("postgresql://"):
            # PostgreSQL for production
            url = url.replace("postgresql://", "postgresql+asyncpg://")
            if settings.environment == "test":
                pool_class = NullPool
            # Enable SSL for Railway and other cloud PostgreSQL providers
            # asyncpg uses 'ssl' parameter directly
            if settings.database_ssl:
                connect_args = {"ssl": "require"}
            else:
                connect_args = {}

        self.engine = create_async_engine(
            url,
            echo=settings.debug,
            poolclass=pool_class,
            connect_args=connect_args if connect_args else {}
        )

        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_tables(self):
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Drop all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self):
        """Close the database connection."""
        await self.engine.dispose()


# Global database manager
_db_manager: DatabaseManager = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    db = get_database_manager()
    async with db.session() as session:
        yield session


# Alias for consistency - some modules use get_session
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions (alias for get_db)."""
    db = get_database_manager()
    async with db.session() as session:
        yield session
