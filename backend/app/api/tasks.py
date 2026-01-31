from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from ..core.database import get_session
from ..models.task import Task
from .auth import get_current_active_user
from ..models.user import User

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# --- Schemas ---

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[datetime] = None
    tags: List[str] = []
    campaign_id: Optional[str] = None
    assignee_id: Optional[str] = None

class TaskCreate(TaskBase):
    organization_id: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    assignee_id: Optional[str] = None

class TaskResponse(TaskBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    organization_id: str,
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """List tasks for an organization, optionally filtered by campaign or status."""
    query = select(Task).where(Task.organization_id == organization_id)
    
    if campaign_id:
        query = query.where(Task.campaign_id == campaign_id)
    
    if status:
        query = query.where(Task.status == status)
        
    query = query.order_by(desc(Task.created_at))
    
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/", response_model=TaskResponse)
async def create_task(
    task_in: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new task."""
    task = Task(**task_in.model_dump())
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific task."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_in: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Update a task."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
        
    await session.commit()
    await session.refresh(task)
    return task

@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a task."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await session.delete(task)
    await session.commit()
    return {"success": True}

@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Quickly update task status (for drag and drop)."""
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = status
    await session.commit()
    await session.refresh(task)
    return task
