"""
Task models for Kanban board and project management.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_id


class Task(Base):
    """A task in the Kanban board."""
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=generate_id)
    organization_id: Mapped[str] = mapped_column(String(12), ForeignKey("organizations.id"))
    campaign_id: Mapped[Optional[str]] = mapped_column(String(12), ForeignKey("campaigns.id"), nullable=True)
    
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo, in_progress, review, done
    priority: Mapped[str] = mapped_column(String(10), default="medium")  # low, medium, high
    
    assignee_id: Mapped[Optional[str]] = mapped_column(String(12), ForeignKey("users.id"), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    campaign = relationship("Campaign")
    assignee = relationship("User")
