"""
Base model configuration for SQLAlchemy.
"""
from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


def generate_id() -> str:
    """Generate a unique ID for database records."""
    return uuid.uuid4().hex[:12]


class Base(DeclarativeBase):
    """Base class for all database models."""

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return ''.join(
            ['_' + c.lower() if c.isupper() else c for c in name]
        ).lstrip('_') + 's'

    # Common columns for all models
    id = Column(String(12), primary_key=True, default=generate_id)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
