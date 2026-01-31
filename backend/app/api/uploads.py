"""
File upload API endpoints.

Provides:
- Direct file upload endpoint
- Presigned URL generation for direct browser uploads
- File validation and type checking
"""

import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel

from ..core.config import get_settings, Settings
from ..services.storage import get_storage_service, UploadResult
from .auth import get_current_active_user
from ..models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["Uploads"])


# --- Schemas ---

class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str
    type: str = "image"  # image, video, document


class PresignedUrlResponse(BaseModel):
    success: bool
    url: str
    fields: dict
    key: str


class UploadResponse(BaseModel):
    success: bool
    url: str
    filename: str
    size_bytes: int
    content_type: str
    key: str


class UploadErrorResponse(BaseModel):
    success: bool = False
    error: str


# --- Dependencies ---

def get_storage(settings: Settings = Depends(get_settings)):
    """Get initialized storage service."""
    storage = get_storage_service()

    # Initialize if not already done and credentials are available
    if storage is None and settings.aws_access_key_id and settings.s3_bucket_name:
        storage = get_storage_service(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key or '',
            bucket_name=settings.s3_bucket_name,
            region=settings.aws_region or 'us-east-1',
            endpoint_url=settings.s3_endpoint_url,
            cdn_domain=settings.cdn_domain
        )

    return storage


# --- Endpoints ---

@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    type: str = Form("image"),  # image, video, document
    storage=Depends(get_storage),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a file directly to S3.

    Args:
        file: The file to upload
        type: File type category ('image', 'video', 'document')

    Returns:
        UploadResponse with the file URL and metadata

    Raises:
        HTTPException: If storage is not configured or upload fails
    """
    if storage is None:
        raise HTTPException(
            status_code=503,
            detail="Storage service not configured. Please set AWS credentials."
        )

    # Validate file type category
    if type not in ('image', 'video', 'document'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type category: {type}. Must be 'image', 'video', or 'document'."
        )

    try:
        # Read file content
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Upload to S3
        result = await storage.upload_file(
            file_content=content,
            filename=file.filename or 'unnamed',
            file_type=type,
            content_type=file.content_type or 'application/octet-stream',
            metadata={
                'original_filename': file.filename or 'unnamed',
                'uploaded_at': str(__import__('datetime').datetime.utcnow()),
                'organization_id': current_user.organization_id,
                'uploaded_by': current_user.id
            }
        )

        if not result.success:
            logger.error(f"Upload failed: {result.error}")
            raise HTTPException(status_code=400, detail=result.error)

        return UploadResponse(
            success=True,
            url=result.url,
            filename=result.filename,
            size_bytes=result.size_bytes,
            content_type=result.content_type,
            key=result.key
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    request: PresignedUrlRequest,
    storage=Depends(get_storage),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a presigned URL for direct browser upload to S3.

    This allows the client to upload directly to S3 without going through
    our servers, which is more efficient for large files.

    Args:
        request: PresignedUrlRequest with filename, content_type, and type

    Returns:
        PresignedUrlResponse with URL and fields for POST upload

    Raises:
        HTTPException: If storage is not configured or generation fails
    """
    if storage is None:
        raise HTTPException(
            status_code=503,
            detail="Storage service not configured. Please set AWS credentials."
        )

    # Validate file type category
    if request.type not in ('image', 'video', 'document'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type category: {request.type}. Must be 'image', 'video', or 'document'."
        )

    try:
        result = await storage.generate_presigned_url(
            filename=request.filename,
            content_type=request.content_type,
            file_type=request.type,
            expiration_seconds=3600,  # 1 hour
            metadata={
                'uploaded_via': 'presigned_url',
                'organization_id': current_user.organization_id,
                'uploaded_by': current_user.id
            }
        )

        if not result.success:
            logger.error(f"Presigned URL generation failed: {result.error}")
            raise HTTPException(status_code=400, detail=result.error)

        return PresignedUrlResponse(
            success=True,
            url=result.url,
            fields=result.fields,
            key=result.key
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating presigned URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


@router.delete("/{key:path}")
async def delete_file(
    key: str,
    storage=Depends(get_storage),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a file from S3.

    Args:
        key: The S3 object key (path) to delete

    Returns:
        Success status
    """
    if storage is None:
        raise HTTPException(
            status_code=503,
            detail="Storage service not configured."
        )

    try:
        success = await storage.delete_file(key)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete file")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.get("/info/{key:path}")
async def get_file_info(
    key: str,
    storage=Depends(get_storage),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get information about a file in S3.

    Args:
        key: The S3 object key (path)

    Returns:
        File metadata including size, content type, and URL
    """
    if storage is None:
        raise HTTPException(
            status_code=503,
            detail="Storage service not configured."
        )

    try:
        info = await storage.get_file_info(key)
        if info is None:
            raise HTTPException(status_code=404, detail="File not found")
        return info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")
