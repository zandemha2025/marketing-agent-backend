"""
Storage service for file uploads to S3.

Supports:
- Direct file uploads with validation
- Presigned URL generation for direct browser uploads
- File type and size validation
- Unique filename generation
"""

import uuid
import mimetypes
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError


@dataclass
class UploadResult:
    """Result of a file upload operation."""
    success: bool
    url: Optional[str] = None
    key: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    size_bytes: int = 0
    content_type: Optional[str] = None


@dataclass
class PresignedUrlResult:
    """Result of a presigned URL generation."""
    success: bool
    url: Optional[str] = None
    fields: Optional[dict] = None
    key: Optional[str] = None
    error: Optional[str] = None


# File type validation
ALLOWED_IMAGE_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'
}
ALLOWED_VIDEO_TYPES = {
    'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/x-matroska'
}
ALLOWED_DOCUMENT_TYPES = {
    'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 'text/markdown',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

# Size limits in bytes
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20MB


class StorageService:
    """Service for handling file uploads to S3."""

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        bucket_name: str,
        region: str = 'us-east-1',
        endpoint_url: Optional[str] = None,
        cdn_domain: Optional[str] = None
    ):
        self.bucket_name = bucket_name
        self.region = region
        self.cdn_domain = cdn_domain

        # Initialize S3 client
        session_kwargs = {
            'aws_access_key_id': aws_access_key_id,
            'aws_secret_access_key': aws_secret_access_key,
            'region_name': region,
        }
        if endpoint_url:
            session_kwargs['endpoint_url'] = endpoint_url

        self.s3_client = boto3.client('s3', **session_kwargs)

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate a unique filename with UUID prefix."""
        ext = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
        unique_id = uuid.uuid4().hex[:16]
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        if ext:
            return f"{timestamp}_{unique_id}.{ext.lower()}"
        return f"{timestamp}_{unique_id}"

    def _get_content_type(self, filename: str, provided_content_type: Optional[str] = None) -> str:
        """Determine content type from filename or use provided type."""
        if provided_content_type:
            return provided_content_type

        guessed_type, _ = mimetypes.guess_type(filename)
        return guessed_type or 'application/octet-stream'

    def _validate_file(
        self,
        filename: str,
        content_type: str,
        size_bytes: int,
        file_type: str = 'image'
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate file type and size.

        Args:
            filename: Original filename
            content_type: MIME type of the file
            size_bytes: File size in bytes
            file_type: Expected file type ('image', 'video', 'document')

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate file type
        if file_type == 'image':
            if content_type not in ALLOWED_IMAGE_TYPES:
                return False, f"Invalid image type: {content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
            if size_bytes > MAX_IMAGE_SIZE:
                return False, f"Image too large: {size_bytes / 1024 / 1024:.1f}MB. Max: {MAX_IMAGE_SIZE / 1024 / 1024}MB"

        elif file_type == 'video':
            if content_type not in ALLOWED_VIDEO_TYPES:
                return False, f"Invalid video type: {content_type}. Allowed: {', '.join(ALLOWED_VIDEO_TYPES)}"
            if size_bytes > MAX_VIDEO_SIZE:
                return False, f"Video too large: {size_bytes / 1024 / 1024:.1f}MB. Max: {MAX_VIDEO_SIZE / 1024 / 1024}MB"

        elif file_type == 'document':
            if content_type not in ALLOWED_DOCUMENT_TYPES:
                return False, f"Invalid document type: {content_type}. Allowed: {', '.join(ALLOWED_DOCUMENT_TYPES)}"
            if size_bytes > MAX_DOCUMENT_SIZE:
                return False, f"Document too large: {size_bytes / 1024 / 1024:.1f}MB. Max: {MAX_DOCUMENT_SIZE / 1024 / 1024}MB"

        else:
            return False, f"Unknown file type category: {file_type}"

        return True, None

    def _get_key_prefix(self, file_type: str) -> str:
        """Get the S3 key prefix based on file type."""
        prefixes = {
            'image': 'images',
            'video': 'videos',
            'document': 'documents'
        }
        return prefixes.get(file_type, 'uploads')

    def _get_public_url(self, key: str) -> str:
        """Get the public URL for an S3 object."""
        if self.cdn_domain:
            return f"https://{self.cdn_domain}/{key}"

        if self.region == 'us-east-1':
            return f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: str = 'image',
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> UploadResult:
        """
        Upload a file to S3.

        Args:
            file_content: Raw file bytes
            filename: Original filename
            file_type: Type category ('image', 'video', 'document')
            content_type: MIME type (auto-detected if not provided)
            metadata: Optional metadata to store with the object

        Returns:
            UploadResult with success status and URL
        """
        try:
            # Determine content type
            actual_content_type = self._get_content_type(filename, content_type)

            # Validate file
            is_valid, error = self._validate_file(
                filename, actual_content_type, len(file_content), file_type
            )
            if not is_valid:
                return UploadResult(success=False, error=error)

            # Generate unique key
            prefix = self._get_key_prefix(file_type)
            unique_filename = self._generate_unique_filename(filename)
            key = f"{prefix}/{unique_filename}"

            # Prepare upload arguments
            upload_args = {
                'Bucket': self.bucket_name,
                'Key': key,
                'Body': file_content,
                'ContentType': actual_content_type,
            }

            # Add metadata if provided
            if metadata:
                upload_args['Metadata'] = {
                    k: str(v) for k, v in metadata.items()
                }

            # Upload to S3
            self.s3_client.put_object(**upload_args)

            # Generate public URL
            url = self._get_public_url(key)

            return UploadResult(
                success=True,
                url=url,
                key=key,
                filename=unique_filename,
                size_bytes=len(file_content),
                content_type=actual_content_type
            )

        except ClientError as e:
            error_msg = f"S3 upload failed: {str(e)}"
            return UploadResult(success=False, error=error_msg)
        except Exception as e:
            error_msg = f"Upload failed: {str(e)}"
            return UploadResult(success=False, error=error_msg)

    async def generate_presigned_url(
        self,
        filename: str,
        content_type: str,
        file_type: str = 'image',
        expiration_seconds: int = 3600,
        metadata: Optional[dict] = None
    ) -> PresignedUrlResult:
        """
        Generate a presigned URL for direct browser upload.

        Args:
            filename: Original filename
            content_type: MIME type of the file
            file_type: Type category ('image', 'video', 'document')
            expiration_seconds: How long the URL is valid (max 7 days)
            metadata: Optional metadata to include

        Returns:
            PresignedUrlResult with URL and fields for POST upload
        """
        try:
            # Generate unique key
            prefix = self._get_key_prefix(file_type)
            unique_filename = self._generate_unique_filename(filename)
            key = f"{prefix}/{unique_filename}"

            # Prepare conditions for presigned POST
            conditions = [
                {'Content-Type': content_type},
                ['content-length-range', 0, self._get_max_size(file_type)]
            ]

            # Prepare fields
            fields = {
                'Content-Type': content_type,
            }

            # Add metadata if provided
            if metadata:
                for k, v in metadata.items():
                    fields[f'x-amz-meta-{k}'] = str(v)

            # Generate presigned POST
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration_seconds
            )

            return PresignedUrlResult(
                success=True,
                url=response['url'],
                fields=response['fields'],
                key=key
            )

        except ClientError as e:
            error_msg = f"Failed to generate presigned URL: {str(e)}"
            return PresignedUrlResult(success=False, error=error_msg)
        except Exception as e:
            error_msg = f"Presigned URL generation failed: {str(e)}"
            return PresignedUrlResult(success=False, error=error_msg)

    def _get_max_size(self, file_type: str) -> int:
        """Get max file size for a file type."""
        sizes = {
            'image': MAX_IMAGE_SIZE,
            'video': MAX_VIDEO_SIZE,
            'document': MAX_DOCUMENT_SIZE
        }
        return sizes.get(file_type, MAX_IMAGE_SIZE)

    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            key: S3 object key

        Returns:
            True if deleted successfully
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError:
            return False

    async def get_file_info(self, key: str) -> Optional[dict]:
        """
        Get information about a file in S3.

        Args:
            key: S3 object key

        Returns:
            Dict with file info or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return {
                'key': key,
                'size': response['ContentLength'],
                'content_type': response['ContentType'],
                'last_modified': response['LastModified'],
                'url': self._get_public_url(key)
            }
        except ClientError:
            return None


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service(
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    bucket_name: Optional[str] = None,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    cdn_domain: Optional[str] = None
) -> Optional[StorageService]:
    """
    Get or create the storage service singleton.

    If called without arguments, returns the existing instance or None.
    If called with arguments, creates a new instance.
    """
    global _storage_service

    if aws_access_key_id and bucket_name:
        _storage_service = StorageService(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key or '',
            bucket_name=bucket_name,
            region=region or 'us-east-1',
            endpoint_url=endpoint_url,
            cdn_domain=cdn_domain
        )

    return _storage_service
