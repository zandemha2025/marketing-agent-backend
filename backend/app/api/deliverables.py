"""
Deliverables API endpoints.

All endpoints require authentication via JWT token.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from ..core.database import get_session
from ..models.deliverable import Deliverable
from ..services.ai.openrouter import llm
# Auth dependency available for securing endpoints
from .auth import get_current_user, get_current_active_user

router = APIRouter(prefix="/deliverables", tags=["Deliverables"])

# --- Schemas ---

class DeliverableBase(BaseModel):
    title: str
    type: str
    content: Optional[str] = None
    platform: Optional[str] = None
    status: str = "draft"
    campaign_id: str

class DeliverableCreate(DeliverableBase):
    pass

class DeliverableUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    platform: Optional[str] = None
    status: Optional[str] = None

class DeliverableResponse(DeliverableBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RefineRequest(BaseModel):
    text: str
    action: str  # shorten, expand, tone_casual, tone_professional, fix_grammar
    type: str    # social_post, email, etc.
    deliverable_id: Optional[str] = None  # If provided, save refined content to this deliverable

class RefineResponse(BaseModel):
    refined_text: str
    deliverable: Optional[DeliverableResponse] = None  # Included when deliverable_id was provided and saved

# --- Endpoints ---

@router.get("/", response_model=List[DeliverableResponse])
async def list_deliverables(
    campaign_id: str,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """List deliverables for a campaign. Requires authentication."""
    query = select(Deliverable).where(Deliverable.campaign_id == campaign_id).order_by(desc(Deliverable.created_at))
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/", response_model=DeliverableResponse)
async def create_deliverable(
    deliverable_in: DeliverableCreate,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new deliverable. Requires authentication."""
    deliverable = Deliverable(**deliverable_in.model_dump())
    session.add(deliverable)
    await session.commit()
    await session.refresh(deliverable)
    return deliverable

@router.get("/{deliverable_id}", response_model=DeliverableResponse)
async def get_deliverable(
    deliverable_id: str,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific deliverable. Requires authentication."""
    deliverable = await session.get(Deliverable, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return deliverable

@router.put("/{deliverable_id}", response_model=DeliverableResponse)
async def update_deliverable(
    deliverable_id: str,
    deliverable_in: DeliverableUpdate,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a deliverable. Requires authentication."""
    deliverable = await session.get(Deliverable, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    update_data = deliverable_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deliverable, field, value)
        
    await session.commit()
    await session.refresh(deliverable)
    return deliverable

@router.delete("/{deliverable_id}")
async def delete_deliverable(
    deliverable_id: str,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a deliverable. Requires authentication."""
    deliverable = await session.get(Deliverable, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    
    await session.delete(deliverable)
    await session.commit()
    return {"success": True}

@router.post("/refine", response_model=RefineResponse)
async def refine_content(
    request: RefineRequest,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    """Refine content using AI and optionally save to database. Requires authentication."""
    prompt = f"""
    You are an expert copywriter.

    Task: {request.action}
    Content Type: {request.type}
    Original Text:
    "{request.text}"

    Instructions:
    - shorten: Make it more concise
    - expand: Add more detail and depth
    - tone_casual: Make it friendly and conversational
    - tone_professional: Make it formal and business-like
    - fix_grammar: Fix spelling and grammar errors only

    Return ONLY the refined text. Do not include quotes or explanations.
    """

    try:
        refined_text = await llm(prompt)

        # If deliverable_id is provided, update the deliverable
        if request.deliverable_id:
            deliverable = await session.get(Deliverable, request.deliverable_id)
            if not deliverable:
                raise HTTPException(status_code=404, detail="Deliverable not found")

            # Update the deliverable with refined content
            deliverable.content = refined_text
            deliverable.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(deliverable)
            
            return RefineResponse(
                refined_text=refined_text,
                deliverable=DeliverableResponse(
                    id=deliverable.id,
                    title=deliverable.title,
                    type=deliverable.type,
                    content=deliverable.content,
                    platform=deliverable.platform,
                    status=deliverable.status,
                    campaign_id=deliverable.campaign_id,
                    created_at=deliverable.created_at,
                    updated_at=deliverable.updated_at
                )
            )

        # Return just the refined text if no deliverable_id
        return RefineResponse(refined_text=refined_text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI refinement failed: {str(e)}")
