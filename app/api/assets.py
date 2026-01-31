"""
Asset API endpoints.

CRUD operations for marketing assets with versioning, comments, and branching.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends

from ..core.database import get_session
from ..repositories.asset import AssetRepository, AssetVersionRepository, AssetCommentRepository
from ..models.asset import AssetType, AssetStatus
from ..schemas.asset import AssetCreate, AssetUpdate, AssetResponse, AssetVersionResponse

router = APIRouter()


# === Additional response schemas ===

class AssetListResponse(BaseModel):
    """List of assets."""
    assets: List[AssetResponse]
    total: int


class CommentCreate(BaseModel):
    """Create comment request."""
    content: str
    user_id: str
    version_number: Optional[int] = None
    position: Optional[Dict[str, Any]] = None
    parent_id: Optional[str] = None


class CommentResponse(BaseModel):
    """Comment response."""
    id: str
    asset_id: str
    version_number: int
    user_id: str
    content: str
    position: Optional[Dict[str, Any]] = None
    parent_id: Optional[str] = None
    resolved: bool
    resolved_by: Optional[str] = None
    created_at: datetime


class BranchRequest(BaseModel):
    """Branch asset request."""
    new_name: str
    created_by: str


# === Endpoints ===

@router.get("/", response_model=AssetListResponse)
async def list_assets(
    campaign_id: str,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    session=Depends(get_session)
):
    """List assets for a campaign, with optional type and status filters."""
    repo = AssetRepository(session)

    parsed_type = AssetType(asset_type) if asset_type else None
    parsed_status = AssetStatus(status) if status else None

    assets = await repo.get_by_campaign(
        campaign_id=campaign_id,
        asset_type=parsed_type,
        status=parsed_status,
    )

    return AssetListResponse(
        assets=[
            AssetResponse(
                id=a.id,
                name=a.name,
                asset_type=a.asset_type.value,
                status=a.status.value,
                description=a.description,
                platform=a.platform,
                current_version=a.current_version,
                campaign_id=a.campaign_id,
                phase_id=a.phase_id,
                current_content=None,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in assets
        ],
        total=len(assets),
    )


@router.post("/", response_model=AssetResponse)
async def create_asset(
    request: AssetCreate,
    session=Depends(get_session)
):
    """Create a new asset with optional initial content."""
    repo = AssetRepository(session)

    asset = await repo.create_asset(
        campaign_id=request.campaign_id,
        name=request.name,
        asset_type=AssetType(request.asset_type),
        created_by="system",  # TODO: extract from auth
        phase_id=request.phase_id,
        description=request.description,
        platform=request.platform,
        initial_content=request.initial_content,
    )

    return AssetResponse(
        id=asset.id,
        name=asset.name,
        asset_type=asset.asset_type.value,
        status=asset.status.value,
        description=asset.description,
        platform=asset.platform,
        current_version=asset.current_version,
        campaign_id=asset.campaign_id,
        phase_id=asset.phase_id,
        current_content=None,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    session=Depends(get_session)
):
    """Get asset details with current content."""
    repo = AssetRepository(session)
    asset = await repo.get_with_versions(asset_id)

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return AssetResponse(
        id=asset.id,
        name=asset.name,
        asset_type=asset.asset_type.value,
        status=asset.status.value,
        description=asset.description,
        platform=asset.platform,
        current_version=asset.current_version,
        campaign_id=asset.campaign_id,
        phase_id=asset.phase_id,
        current_content=asset.current_content,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    request: AssetUpdate,
    session=Depends(get_session)
):
    """Update asset name, description, or status."""
    repo = AssetRepository(session)
    asset = await repo.get(asset_id)

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.status is not None:
        update_data["status"] = AssetStatus(request.status)

    if update_data:
        asset = await repo.update(asset_id, **update_data)

    return AssetResponse(
        id=asset.id,
        name=asset.name,
        asset_type=asset.asset_type.value,
        status=asset.status.value,
        description=asset.description,
        platform=asset.platform,
        current_version=asset.current_version,
        campaign_id=asset.campaign_id,
        phase_id=asset.phase_id,
        current_content=None,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    session=Depends(get_session)
):
    """Delete an asset."""
    repo = AssetRepository(session)
    asset = await repo.get(asset_id)

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await repo.delete(asset_id)

    return {"status": "deleted", "id": asset_id}


@router.get("/{asset_id}/versions", response_model=List[AssetVersionResponse])
async def get_asset_versions(
    asset_id: str,
    session=Depends(get_session)
):
    """Get version history for an asset."""
    asset_repo = AssetRepository(session)
    asset = await asset_repo.get(asset_id)

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    version_repo = AssetVersionRepository(session)
    versions = await version_repo.get_by_asset(asset_id)

    return [
        AssetVersionResponse(
            version_number=v.version_number,
            content=v.content,
            change_summary=v.change_summary,
            created_by_ai=v.created_by_ai,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.get("/{asset_id}/versions/{version_number}", response_model=AssetVersionResponse)
async def get_asset_version(
    asset_id: str,
    version_number: int,
    session=Depends(get_session)
):
    """Get a specific version of an asset."""
    version_repo = AssetVersionRepository(session)
    version = await version_repo.get_version(asset_id, version_number)

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return AssetVersionResponse(
        version_number=version.version_number,
        content=version.content,
        change_summary=version.change_summary,
        created_by_ai=version.created_by_ai,
        created_at=version.created_at,
    )


@router.get("/{asset_id}/comments", response_model=List[CommentResponse])
async def list_comments(
    asset_id: str,
    version_number: Optional[int] = None,
    include_resolved: bool = False,
    session=Depends(get_session)
):
    """List comments for an asset."""
    asset_repo = AssetRepository(session)
    asset = await asset_repo.get(asset_id)

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    comment_repo = AssetCommentRepository(session)
    comments = await comment_repo.get_by_asset(
        asset_id=asset_id,
        version_number=version_number,
        include_resolved=include_resolved,
    )

    return [
        CommentResponse(
            id=c.id,
            asset_id=c.asset_id,
            version_number=c.version_number,
            user_id=c.user_id,
            content=c.content,
            position=c.position,
            parent_id=c.parent_id,
            resolved=c.resolved,
            resolved_by=c.resolved_by,
            created_at=c.created_at,
        )
        for c in comments
    ]


@router.post("/{asset_id}/comments", response_model=CommentResponse)
async def create_comment(
    asset_id: str,
    request: CommentCreate,
    session=Depends(get_session)
):
    """Add a comment to an asset."""
    asset_repo = AssetRepository(session)
    asset = await asset_repo.get(asset_id)

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    version_number = request.version_number or asset.current_version

    comment_repo = AssetCommentRepository(session)
    comment = await comment_repo.create_comment(
        asset_id=asset_id,
        version_number=version_number,
        user_id=request.user_id,
        content=request.content,
        position=request.position,
        parent_id=request.parent_id,
    )

    return CommentResponse(
        id=comment.id,
        asset_id=comment.asset_id,
        version_number=comment.version_number,
        user_id=comment.user_id,
        content=comment.content,
        position=comment.position,
        parent_id=comment.parent_id,
        resolved=comment.resolved,
        resolved_by=comment.resolved_by,
        created_at=comment.created_at,
    )


@router.post("/{asset_id}/branch", response_model=AssetResponse)
async def branch_asset(
    asset_id: str,
    request: BranchRequest,
    session=Depends(get_session)
):
    """Branch/duplicate an asset."""
    repo = AssetRepository(session)
    branch = await repo.branch_asset(
        original_id=asset_id,
        new_name=request.new_name,
        created_by=request.created_by,
    )

    if not branch:
        raise HTTPException(status_code=404, detail="Asset not found")

    return AssetResponse(
        id=branch.id,
        name=branch.name,
        asset_type=branch.asset_type.value,
        status=branch.status.value,
        description=branch.description,
        platform=branch.platform,
        current_version=branch.current_version,
        campaign_id=branch.campaign_id,
        phase_id=branch.phase_id,
        current_content=None,
        created_at=branch.created_at,
        updated_at=branch.updated_at,
    )
