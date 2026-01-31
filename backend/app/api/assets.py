"""
Asset API endpoints.

CRUD operations for marketing assets with versioning, comments, and branching.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends

from ..core.database import get_session
from ..core.config import get_settings
from ..repositories.asset import AssetRepository, AssetVersionRepository, AssetCommentRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository
from ..models.asset import AssetType, AssetStatus
from ..models.user import User
from ..schemas.asset import AssetCreate, AssetUpdate, AssetResponse, AssetVersionResponse
from ..services.assets.asset_generator import AssetGenerator, CompleteAsset
from .auth import get_current_user, get_current_active_user

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


class AssetGenerateRequest(BaseModel):
    """Request body for asset generation."""
    prompt: str
    asset_type: str = "social_post"
    platform: str = "instagram"
    campaign_id: Optional[str] = None
    organization_id: str


class AssetGenerateResponse(BaseModel):
    """Response from asset generation."""
    id: Optional[str] = None
    asset_type: str
    platform: str
    name: str
    copy: Optional[Dict[str, Any]] = None
    image: Optional[Dict[str, Any]] = None
    video: Optional[Dict[str, Any]] = None
    spec_used: Dict[str, Any] = {}
    created_at: str


class ImageGenerateRequest(BaseModel):
    """Request body for simple image generation."""
    prompt: str
    style: str = "photorealistic"  # photorealistic, artistic, minimal
    width: int = 1024
    height: int = 1024
    negative_prompt: Optional[str] = None


class ImageGenerateResponse(BaseModel):
    """Response from image generation."""
    success: bool
    asset_id: Optional[str] = None
    url: Optional[str] = None
    width: int
    height: int
    prompt: str
    style: str
    error: Optional[str] = None


# === Endpoints ===

@router.post("/generate", response_model=AssetGenerateResponse)
async def generate_asset(
    request: AssetGenerateRequest,
    session=Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate a complete marketing asset using AI.

    Orchestrates copy, image, and video generation based on the prompt,
    asset type, and platform. Brand data is pulled from the organization's
    knowledge base to ensure brand consistency.
    """
    settings = get_settings()

    # Get brand data from organization's knowledge base
    kb_repo = KnowledgeBaseRepository(session)
    kb = await kb_repo.get_by_organization(request.organization_id)
    brand_data = kb.brand_data if kb else {}

    # Build asset spec compatible with AssetGenerator.generate_asset()
    asset_spec = {
        "asset_type": request.asset_type,
        "platform": request.platform,
        "name": f"Generated {request.asset_type}",
        "copy": [{"format": "body", "content": request.prompt}],
        "visual": {
            "description": request.prompt,
            "style": "photography",
            "mood": "professional",
        },
    }

    # Instantiate generator with available API keys
    generator = AssetGenerator(
        openrouter_api_key=settings.openrouter_api_key or "",
        segmind_api_key=settings.segmind_api_key or "",
        elevenlabs_api_key=settings.elevenlabs_api_key or "",
    )

    try:
        complete_asset: CompleteAsset = await generator.generate_asset(
            asset_spec=asset_spec,
            brand_data=brand_data,
        )
    finally:
        await generator.close()

    # Save to database as an Asset record
    asset_repo = AssetRepository(session)
    initial_content = {}
    if complete_asset.copy:
        initial_content["copy"] = {
            "format": complete_asset.copy.format,
            "content": complete_asset.copy.content,
            "character_count": complete_asset.copy.character_count,
            "variations": complete_asset.copy.variations,
        }
    if complete_asset.image:
        initial_content["image"] = {
            "filename": complete_asset.image.filename,
            "filepath": complete_asset.image.filepath,
            "dimensions": complete_asset.image.dimensions,
            "prompt_used": complete_asset.image.prompt_used,
        }
    if complete_asset.video:
        initial_content["video"] = {
            "filename": complete_asset.video.filename,
            "filepath": complete_asset.video.filepath,
            "duration": complete_asset.video.duration,
        }

    db_asset = await asset_repo.create_asset(
        campaign_id=request.campaign_id or "",
        name=complete_asset.name,
        asset_type=AssetType(request.asset_type),
        created_by=current_user.id,
        description=request.prompt,
        platform=request.platform,
        initial_content=initial_content,
    )

    return AssetGenerateResponse(
        id=db_asset.id,
        asset_type=complete_asset.asset_type,
        platform=complete_asset.platform,
        name=complete_asset.name,
        copy=initial_content.get("copy"),
        image=initial_content.get("image"),
        video=initial_content.get("video"),
        spec_used=complete_asset.spec_used,
        created_at=complete_asset.created_at.isoformat(),
    )


@router.post("/generate-image", response_model=ImageGenerateResponse)
async def generate_image(
    request: ImageGenerateRequest,
):
    """
    Generate an image using AI.
    
    This endpoint generates images using available AI backends:
    1. Segmind API (if SEGMIND_API_KEY is set)
    2. Replicate API (if REPLICATE_API_TOKEN is set)
    3. Mock placeholder (fallback for testing)
    
    Supports multiple styles:
    - photorealistic: Professional photography style
    - artistic: Creative, expressive style
    - minimal: Clean, minimalist design
    
    No authentication required for testing purposes.
    """
    from ..services.assets.image_generator import ImageGeneratorService
    import os
    
    settings = get_settings()
    
    # Initialize the image generator with available API keys
    generator = ImageGeneratorService(
        segmind_api_key=settings.segmind_api_key,
        replicate_api_token=os.environ.get("REPLICATE_API_TOKEN"),
        output_dir="outputs/generated_images"
    )
    
    try:
        result = await generator.generate_image(
            prompt=request.prompt,
            style=request.style,
            width=request.width,
            height=request.height,
            negative_prompt=request.negative_prompt,
        )
        
        return ImageGenerateResponse(
            success=result.success,
            asset_id=result.asset_id,
            url=result.url,
            width=result.width,
            height=result.height,
            prompt=result.prompt,
            style=result.style,
            error=result.error,
        )
    finally:
        await generator.close()


@router.get("/", response_model=AssetListResponse)
async def list_assets(
    campaign_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    session=Depends(get_session)
):
    """
    List assets with optional filters.
    
    Either campaign_id or organization_id must be provided:
    - campaign_id: List assets for a specific campaign
    - organization_id: List all assets across campaigns in the organization
    """
    if not campaign_id and not organization_id:
        raise HTTPException(
            status_code=400,
            detail="Either campaign_id or organization_id must be provided"
        )

    repo = AssetRepository(session)

    parsed_type = AssetType(asset_type) if asset_type else None
    parsed_status = AssetStatus(status) if status else None

    if campaign_id:
        assets = await repo.get_by_campaign(
            campaign_id=campaign_id,
            asset_type=parsed_type,
            status=parsed_status,
        )
    else:
        assets = await repo.get_by_organization(
            organization_id=organization_id,
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
    session=Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new asset with optional initial content."""
    repo = AssetRepository(session)

    # Extract user ID from auth context, fallback to "system" for service calls
    created_by = current_user.id if current_user else "system"

    asset = await repo.create_asset(
        campaign_id=request.campaign_id,
        name=request.name,
        asset_type=AssetType(request.asset_type),
        created_by=created_by,
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
