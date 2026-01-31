"""
Email Campaign and Email Sequence Models

Models for storing email marketing campaigns and sequences.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Text, JSON, Enum as SQLEnum, ForeignKey, Integer
from sqlalchemy.orm import relationship
import enum

from .base import Base, generate_id


class EmailType(str, enum.Enum):
    """Supported email types."""
    PROMOTIONAL = "promotional"
    WELCOME = "welcome"
    NURTURE = "nurture"
    NEWSLETTER = "newsletter"
    TRANSACTIONAL = "transactional"
    ANNOUNCEMENT = "announcement"


class EmailStatus(str, enum.Enum):
    """Email campaign status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    ARCHIVED = "archived"


class SequenceType(str, enum.Enum):
    """Email sequence types."""
    WELCOME = "welcome"
    NURTURE = "nurture"
    ONBOARDING = "onboarding"
    RE_ENGAGEMENT = "re_engagement"


class SequenceStatus(str, enum.Enum):
    """Email sequence status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class EmailCampaign(Base):
    """
    Email Campaign model for storing generated emails.
    
    Stores both the generated content and metadata for email campaigns.
    """
    __tablename__ = "email_campaigns"
    
    # Override id to use UUID format
    id = Column(String(36), primary_key=True, default=lambda: generate_id())
    
    # Campaign metadata
    name = Column(String(255), nullable=False)
    organization_id = Column(String(36), nullable=False, index=True)
    campaign_id = Column(String(36), nullable=True, index=True)  # Parent campaign reference
    
    # Email type and status
    type = Column(SQLEnum(EmailType), nullable=False, default=EmailType.PROMOTIONAL)
    status = Column(SQLEnum(EmailStatus), nullable=False, default=EmailStatus.DRAFT)
    
    # Subject lines (stored as JSON array for A/B testing)
    subject_lines = Column(JSON, nullable=False, default=list)
    
    # Email content
    html_content = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    mjml_content = Column(Text, nullable=True)  # Source MJML for editing
    
    # Preview and metadata
    preview_text = Column(String(255), nullable=True)  # Preheader text
    preview_url = Column(String(500), nullable=True)  # URL to preview the email
    
    # Brand customization
    brand_colors = Column(JSON, nullable=True)  # {"primary": "#007bff", "secondary": "#6c757d"}
    
    # Content structure
    headline = Column(String(500), nullable=True)
    body_content = Column(Text, nullable=True)
    cta_text = Column(String(100), nullable=True)
    cta_url = Column(String(500), nullable=True)
    
    # File storage
    file_path = Column(String(500), nullable=True)  # Path to saved email files
    
    # Timestamps are inherited from Base
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "organization_id": self.organization_id,
            "campaign_id": self.campaign_id,
            "type": self.type.value if self.type else None,
            "status": self.status.value if self.status else None,
            "subject_lines": self.subject_lines or [],
            "html_content": self.html_content,
            "text_content": self.text_content,
            "mjml_content": self.mjml_content,
            "preview_text": self.preview_text,
            "preview_url": self.preview_url,
            "brand_colors": self.brand_colors,
            "headline": self.headline,
            "body_content": self.body_content,
            "cta_text": self.cta_text,
            "cta_url": self.cta_url,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EmailSequence(Base):
    """
    Email Sequence model for storing drip campaigns.
    
    Stores a series of emails with timing schedules.
    """
    __tablename__ = "email_sequences"
    
    # Override id to use UUID format
    id = Column(String(36), primary_key=True, default=lambda: generate_id())
    
    # Sequence metadata
    name = Column(String(255), nullable=False)
    organization_id = Column(String(36), nullable=False, index=True)
    campaign_id = Column(String(36), nullable=True, index=True)  # Parent campaign reference
    
    # Sequence type and status
    type = Column(SQLEnum(SequenceType), nullable=False, default=SequenceType.WELCOME)
    status = Column(SQLEnum(SequenceStatus), nullable=False, default=SequenceStatus.DRAFT)
    
    # Emails in the sequence (stored as JSON array)
    # Each email: {"day": 1, "subject": "...", "html_content": "...", "text_content": "..."}
    emails = Column(JSON, nullable=False, default=list)
    
    # Timing schedule (array of days: [1, 3, 5, 7, 14])
    timing_schedule = Column(JSON, nullable=False, default=list)
    
    # Brand data for consistent styling
    brand_data = Column(JSON, nullable=True)
    
    # File storage
    file_path = Column(String(500), nullable=True)  # Path to saved sequence files
    
    # Statistics
    total_emails = Column(Integer, default=0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "organization_id": self.organization_id,
            "campaign_id": self.campaign_id,
            "type": self.type.value if self.type else None,
            "status": self.status.value if self.status else None,
            "emails": self.emails or [],
            "timing_schedule": self.timing_schedule or [],
            "brand_data": self.brand_data,
            "file_path": self.file_path,
            "total_emails": self.total_emails,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EmailSequenceEmail(Base):
    """
    Individual email within a sequence.
    
    Allows for more detailed tracking of each email in a sequence.
    """
    __tablename__ = "email_sequence_emails"
    
    id = Column(String(36), primary_key=True, default=lambda: generate_id())
    
    # Parent sequence
    sequence_id = Column(String(36), ForeignKey("email_sequences.id"), nullable=False, index=True)
    
    # Position in sequence
    day = Column(Integer, nullable=False)  # Day to send (1, 3, 7, etc.)
    position = Column(Integer, nullable=False)  # Order in sequence (1, 2, 3, etc.)
    
    # Email content
    subject = Column(String(500), nullable=False)
    html_content = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    preview_text = Column(String(255), nullable=True)
    
    # Status
    status = Column(SQLEnum(EmailStatus), nullable=False, default=EmailStatus.DRAFT)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "day": self.day,
            "position": self.position,
            "subject": self.subject,
            "html_content": self.html_content,
            "text_content": self.text_content,
            "preview_text": self.preview_text,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
