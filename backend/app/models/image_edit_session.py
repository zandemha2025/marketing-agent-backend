from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, generate_id


class ImageEditSession(Base):
    """Image editing session model for tracking collaborative image editing."""
    
    __tablename__ = "image_edit_sessions"
    
    id = Column(String(12), primary_key=True, default=generate_id)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True, index=True)
    deliverable_id = Column(String, ForeignKey("deliverables.id"), nullable=True, index=True)
    
    # Session metadata
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="active")  # active, completed, archived
    
    # Image data
    original_image_url = Column(String, nullable=True)
    current_image_url = Column(String, nullable=True)
    preview_image_url = Column(String, nullable=True)
    
    # Editing context and instructions
    editing_context = Column(JSON, default=dict)  # Store editing history, layers, etc.
    instructions = Column(Text, nullable=True)  # Current editing instructions
    
    # AI generation settings
    ai_model = Column(String, default="dall-e-3")
    generation_settings = Column(JSON, default=dict)
    
    # Collaboration settings
    is_collaborative = Column(Boolean, default=True)
    allow_real_time_editing = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="image_edit_sessions")
    campaign = relationship("Campaign", back_populates="image_edit_sessions")
    deliverable = relationship("Deliverable", back_populates="image_edit_sessions")
    edit_history = relationship("ImageEditHistory", back_populates="session", cascade="all, delete-orphan")


class ImageEditHistory(Base):
    """History of edits made to an image session."""
    
    __tablename__ = "image_edit_history"
    
    id = Column(String(12), primary_key=True, default=generate_id)
    session_id = Column(String, ForeignKey("image_edit_sessions.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)  # Optional user tracking
    
    # Edit details
    edit_type = Column(String, nullable=False)  # text_prompt, brush, filter, etc.
    edit_data = Column(JSON, default=dict)  # Store the actual edit parameters
    
    # Before/after states
    previous_image_url = Column(String, nullable=True)
    new_image_url = Column(String, nullable=True)
    
    # AI generation details
    ai_prompt = Column(Text, nullable=True)
    ai_model_used = Column(String, nullable=True)
    generation_id = Column(String, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ImageEditSession", back_populates="edit_history")