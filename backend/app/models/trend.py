"""
Trend model for TrendMaster.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_id


class Trend(Base):
    """A market trend or news item."""
    __tablename__ = "trends"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=generate_id)
    organization_id: Mapped[str] = mapped_column(String(12), ForeignKey("organizations.id"))
    
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    score: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(100))
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
