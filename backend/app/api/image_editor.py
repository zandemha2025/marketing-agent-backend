from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..models.user import User
from ..services.image_editor import ImageEditorService
from ..schemas.image_edit_session import (
    ImageEditSessionResponse,
    ImageEditSessionCreate,
    ImageEditSessionUpdate,
    ImageEditHistoryResponse,
    ImageEditHistoryCreate,
    ImageGenerationRequest,
    ImageEditRequest,
    ImageEditResponse
)
# Import proper authentication from auth module
from .auth import get_current_user

router = APIRouter(prefix="/image-editor", tags=["image-editor"])


@router.get("/sessions", response_model=List[ImageEditSessionResponse])
async def list_image_edit_sessions(
    organization_id: str = Query(..., description="Organization ID"),
    campaign_id: Optional[str] = Query(None, description="Filter by campaign ID"),
    deliverable_id: Optional[str] = Query(None, description="Filter by deliverable ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List image editing sessions for an organization."""
    service = ImageEditorService(db)
    sessions = await service.list_sessions(
        organization_id=organization_id,
        campaign_id=campaign_id,
        deliverable_id=deliverable_id,
        limit=limit,
        offset=offset
    )
    return sessions


@router.post("/sessions", response_model=ImageEditSessionResponse)
async def create_image_edit_session(
    session_data: ImageEditSessionCreate,
    organization_id: str = Query(..., description="Organization ID"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new image editing session."""
    service = ImageEditorService(db)
    session = await service.create_session(organization_id, session_data)
    return session


@router.get("/sessions/{session_id}", response_model=ImageEditSessionResponse)
async def get_image_edit_session(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific image editing session."""
    service = ImageEditorService(db)
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Image edit session not found")
    return session


@router.patch("/sessions/{session_id}", response_model=ImageEditSessionResponse)
async def update_image_edit_session(
    session_id: str,
    session_data: ImageEditSessionUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update an image editing session."""
    service = ImageEditorService(db)
    session = await service.update_session(session_id, session_data)
    if not session:
        raise HTTPException(status_code=404, detail="Image edit session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_image_edit_session(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete an image editing session."""
    service = ImageEditorService(db)
    success = await service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Image edit session not found")
    return {"message": "Image edit session deleted successfully"}


@router.post("/sessions/{session_id}/history", response_model=ImageEditHistoryResponse)
async def add_history_entry(
    session_id: str,
    history_data: ImageEditHistoryCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Add an entry to the edit history."""
    service = ImageEditorService(db)
    history_entry = await service.add_history_entry(session_id, history_data)
    return history_entry


@router.get("/sessions/{session_id}/history", response_model=List[ImageEditHistoryResponse])
async def get_edit_history(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get the edit history for a session."""
    service = ImageEditorService(db)
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Image edit session not found")
    return session.edit_history


@router.post("/generate", response_model=ImageEditResponse)
async def generate_image(
    generation_request: ImageGenerationRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Generate an image using AI."""
    service = ImageEditorService(db)
    result = await service.generate_image(generation_request)
    return result


@router.post("/edit", response_model=ImageEditResponse)
async def edit_image(
    edit_request: ImageEditRequest,
    session_id: Optional[str] = Query(None, description="Optional session ID to save to"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Edit an image using various operations."""
    service = ImageEditorService(db)
    result = await service.process_edit(session_id, edit_request)
    
    # If session_id is provided, save the result to the session
    if session_id and result.get("success"):
        await service.update_session(session_id, ImageEditSessionUpdate(
            current_image_url=result.get("image_url"),
            preview_image_url=result.get("preview_url")
        ))
    
    return result