"""
Schemas for campaign endpoints.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel


class CampaignCreate(BaseModel):
    """Create campaign request."""
    name: str
    campaign_type: Optional[str] = "marketing"  # Default to marketing if not provided
    description: Optional[str] = None
    goal: Optional[str] = None  # Frontend sends this
    target_audience: Optional[str] = None  # Frontend sends this
    platforms: Optional[List[str]] = None  # Frontend sends this
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignUpdate(BaseModel):
    """Update campaign request."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignBrief(BaseModel):
    """Campaign brief data."""
    executive_summary: Optional[str] = None
    background: Optional[Dict[str, str]] = None
    objectives: List[Dict[str, str]] = []
    target_audience: Optional[Dict[str, Any]] = None
    key_messages: List[Dict[str, Any]] = []
    creative_territories: List[Dict[str, Any]] = []
    channels: List[Dict[str, Any]] = []
    budget: Optional[Dict[str, Any]] = None
    timeline: Optional[Dict[str, Any]] = None
    success_metrics: List[Dict[str, Any]] = []


class CampaignResponse(BaseModel):
    """Campaign response."""
    id: str
    name: str
    campaign_type: str
    status: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    brief_data: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
