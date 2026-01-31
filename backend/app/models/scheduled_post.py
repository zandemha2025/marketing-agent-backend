"""
Scheduled post model for Social Calendar.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_id


class ScheduledPost(Base):
    """A social media post scheduled for publishing."""
    __tablename__ = "scheduled_posts"

    id: Mapped[str] = mapped_column(String(12), primary_key=True, default=generate_id)
    organization_id: Mapped[str] = mapped_column(String(12), ForeignKey("organizations.id"))
    campaign_id: Mapped[Optional[str]] = mapped_column(String(12), ForeignKey("campaigns.id"), nullable=True)
    
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(50))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled, published, failed, publishing
    
    # Media fields
    image_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Publishing result fields
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    platform_post_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    platform_post_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    campaign = relationship("Campaign")
