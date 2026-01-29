"""
Schemas for asset endpoints.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel


class AssetCreate(BaseModel):
    """Create asset request."""
    name: str
    asset_type: str
    campaign_id: str
    phase_id: Optional[str] = None
    description: Optional[str] = None
    platform: Optional[str] = None
    initial_content: Optional[Dict[str, Any]] = None


class AssetUpdate(BaseModel):
    """Update asset request."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AssetVersionResponse(BaseModel):
    """Asset version response."""
    version_number: int
    content: Dict[str, Any]
    change_summary: Optional[str] = None
    created_by_ai: bool
    created_at: datetime


class AssetResponse(BaseModel):
    """Asset response."""
    id: str
    name: str
    asset_type: str
    status: str
    description: Optional[str] = None
    platform: Optional[str] = None
    current_version: int
    campaign_id: str
    phase_id: Optional[str] = None
    current_content: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
