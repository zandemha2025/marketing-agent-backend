"""
Schemas for organization endpoints.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class OrganizationCreate(BaseModel):
    """Create organization request."""
    name: str
    domain: str


class OrganizationUpdate(BaseModel):
    """Update organization request."""
    name: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class OrganizationResponse(BaseModel):
    """Organization response."""
    id: str
    name: str
    domain: str
    logo_url: Optional[str] = None
    subscription_tier: str
    created_at: datetime
    updated_at: datetime
