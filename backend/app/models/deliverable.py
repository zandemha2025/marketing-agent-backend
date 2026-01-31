"""
Deliverable model for content drafting and editing.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_id


class Deliverable(Base):
    """A content deliverable in the drafting stage."""
    __tablename__ = "deliverables"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=generate_id)
    campaign_id: Mapped[str] = mapped_column(String(12), ForeignKey("campaigns.id"))
    
    title: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(50))  # social_post, email, blog_post, etc.
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign")
    image_edit_sessions = relationship("ImageEditSession", back_populates="deliverable")
