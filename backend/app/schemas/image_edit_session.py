"""
Schemas for image editing sessions.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ImageEditSessionCreate(BaseModel):
    """Create image editing session request."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    campaign_id: Optional[str] = None
    deliverable_id: Optional[str] = None
    original_image_url: Optional[str] = None
    ai_model: str = Field(default="dall-e-3")
    generation_settings: Dict[str, Any] = Field(default_factory=dict)
    is_collaborative: bool = Field(default=True)
    allow_real_time_editing: bool = Field(default=True)


class ImageEditSessionUpdate(BaseModel):
    """Update image editing session request."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|completed|archived)$")
    current_image_url: Optional[str] = None
    preview_image_url: Optional[str] = None
    editing_context: Optional[Dict[str, Any]] = None
    instructions: Optional[str] = None
    generation_settings: Optional[Dict[str, Any]] = None
    is_collaborative: Optional[bool] = None
    allow_real_time_editing: Optional[bool] = None


class ImageEditHistoryCreate(BaseModel):
    """Create image edit history entry request."""
    edit_type: str = Field(..., pattern="^(text_prompt|brush|filter|crop|resize|ai_generate)$")
    edit_data: Dict[str, Any] = Field(default_factory=dict)
    previous_image_url: Optional[str] = None
    new_image_url: Optional[str] = None
    ai_prompt: Optional[str] = None
    ai_model_used: Optional[str] = None
    generation_id: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[str] = None


class ImageEditHistoryResponse(BaseModel):
    """Image edit history response."""
    id: str
    session_id: str
    user_id: Optional[str]
    edit_type: str
    edit_data: Dict[str, Any]
    previous_image_url: Optional[str]
    new_image_url: Optional[str]
    ai_prompt: Optional[str]
    ai_model_used: Optional[str]
    generation_id: Optional[str]
    description: Optional[str]
    timestamp: datetime


class ImageEditSessionResponse(BaseModel):
    """Image editing session response."""
    id: str
    organization_id: str
    campaign_id: Optional[str]
    deliverable_id: Optional[str]
    title: str
    description: Optional[str]
    status: str
    original_image_url: Optional[str]
    current_image_url: Optional[str]
    preview_image_url: Optional[str]
    editing_context: Dict[str, Any]
    instructions: Optional[str]
    ai_model: str
    generation_settings: Dict[str, Any]
    is_collaborative: bool
    allow_real_time_editing: bool
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    edit_history: List[ImageEditHistoryResponse] = Field(default_factory=list)


class ImageGenerationRequest(BaseModel):
    """Request for AI image generation."""
    prompt: str = Field(..., min_length=1)
    model: str = Field(default="dall-e-3")
    size: str = Field(default="1024x1024")
    quality: str = Field(default="standard")
    style: str = Field(default="vivid")
    n: int = Field(default=1, ge=1, le=4)


class ImageEditRequest(BaseModel):
    """Request for image editing operations."""
    operation: str = Field(..., pattern="^(generate|edit|enhance|remove_background|crop|resize|filter)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    prompt: Optional[str] = None
    mask_url: Optional[str] = None


class ImageEditResponse(BaseModel):
    """Response from image editing operations."""
    success: bool
    image_url: Optional[str] = None
    preview_url: Optional[str] = None
    message: str
    operation_id: Optional[str] = None