"""
Organization API endpoints.

All endpoints require authentication via JWT token.
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..core.database import get_session
from ..repositories.organization import OrganizationRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository
# Auth dependency available for securing endpoints
from .auth import get_current_user, get_current_active_user

router = APIRouter()


# === Pydantic Models ===

class OrganizationResponse(BaseModel):
    """Organization response model."""
    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    settings: dict = {}
    created_at: datetime


class OrganizationCreateRequest(BaseModel):
    """Request to create an organization."""
    name: str
    slug: str
    domain: Optional[str] = None


class OrganizationUpdateRequest(BaseModel):
    """Request to update an organization."""
    name: Optional[str] = None
    domain: Optional[str] = None
    settings: Optional[dict] = None


class KnowledgeBaseResponse(BaseModel):
    """Knowledge base response model."""
    id: str
    organization_id: str
    brand_data: dict = {}
    market_data: dict = {}
    audiences_data: dict = {}
    offerings_data: dict = {}
    context_data: dict = {}
    brand_dna: dict = {}
    last_updated: Optional[datetime] = None


class KnowledgeBaseUpdateRequest(BaseModel):
    """Request to update knowledge base."""
    brand_data: Optional[dict] = None
    market_data: Optional[dict] = None
    audiences_data: Optional[dict] = None
    offerings_data: Optional[dict] = None
    context_data: Optional[dict] = None
    brand_dna: Optional[dict] = None


# === Endpoints ===

@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Get organization details. Requires authentication."""
    repo = OrganizationRepository(session)
    org = await repo.get(organization_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        domain=org.domain,
        settings=org.settings or {},
        created_at=org.created_at
    )


@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    request: OrganizationCreateRequest,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Create a new organization. Requires authentication."""
    repo = OrganizationRepository(session)

    # Check if slug is taken
    existing = await repo.get_by_slug(request.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already in use")

    org = await repo.create(
        name=request.name,
        slug=request.slug,
        domain=request.domain
    )

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        domain=org.domain,
        settings=org.settings or {},
        created_at=org.created_at
    )


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    request: OrganizationUpdateRequest,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Update an organization. Requires authentication."""
    repo = OrganizationRepository(session)
    org = await repo.get(organization_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.domain is not None:
        update_data["domain"] = request.domain
    if request.settings is not None:
        update_data["settings"] = request.settings

    if update_data:
        org = await repo.update(organization_id, **update_data)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        domain=org.domain,
        settings=org.settings or {},
        created_at=org.created_at
    )


@router.get("/{organization_id}/knowledge-base", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    organization_id: str,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Get organization's knowledge base. Requires authentication."""
    kb_repo = KnowledgeBaseRepository(session)
    kb = await kb_repo.get_by_organization(organization_id)

    if not kb:
        # Return empty knowledge base structure
        return KnowledgeBaseResponse(
            id="",
            organization_id=organization_id,
            brand_data={},
            market_data={},
            audiences_data={},
            offerings_data={},
            context_data={},
            brand_dna={},
            last_updated=None
        )

    return KnowledgeBaseResponse(
        id=kb.id,
        organization_id=kb.organization_id,
        brand_data=kb.brand_data or {},
        market_data=kb.market_data or {},
        audiences_data=kb.audiences_data or {},
        offerings_data=kb.offerings_data or {},
        context_data=kb.context_data or {},
        brand_dna=kb.brand_dna or {},
        last_updated=kb.updated_at
    )


@router.put("/{organization_id}/knowledge-base", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    organization_id: str,
    request: KnowledgeBaseUpdateRequest,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Update organization's knowledge base. Requires authentication."""
    kb_repo = KnowledgeBaseRepository(session)
    kb = await kb_repo.get_by_organization(organization_id)

    update_data = {}
    if request.brand_data is not None:
        update_data["brand_data"] = request.brand_data
    if request.market_data is not None:
        update_data["market_data"] = request.market_data
    if request.audiences_data is not None:
        update_data["audiences_data"] = request.audiences_data
    if request.offerings_data is not None:
        update_data["offerings_data"] = request.offerings_data
    if request.context_data is not None:
        update_data["context_data"] = request.context_data
    if request.brand_dna is not None:
        update_data["brand_dna"] = request.brand_dna

    if kb:
        kb = await kb_repo.update(kb.id, **update_data)
    else:
        # Create new knowledge base
        kb = await kb_repo.create(
            organization_id=organization_id,
            **update_data
        )

    return KnowledgeBaseResponse(
        id=kb.id,
        organization_id=kb.organization_id,
        brand_data=kb.brand_data or {},
        market_data=kb.market_data or {},
        audiences_data=kb.audiences_data or {},
        offerings_data=kb.offerings_data or {},
        context_data=kb.context_data or {},
        brand_dna=kb.brand_dna or {},
        last_updated=kb.updated_at
    )
