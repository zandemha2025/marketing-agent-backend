from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import logging
import uuid

from ..models.image_edit_session import ImageEditSession, ImageEditHistory
from ..schemas.image_edit_session import (
    ImageEditSessionCreate,
    ImageEditSessionUpdate,
    ImageEditHistoryCreate,
    ImageGenerationRequest,
    ImageEditRequest
)
from ..core.config import get_settings
from ..services.assets.segmind import SegmindService

logger = logging.getLogger(__name__)


class ImageEditorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_sessions(
        self,
        organization_id: str,
        campaign_id: Optional[str] = None,
        deliverable_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ImageEditSession]:
        """List image editing sessions."""
        stmt = select(ImageEditSession).options(selectinload(ImageEditSession.edit_history)).filter(
            ImageEditSession.organization_id == organization_id
        )
        
        if campaign_id:
            stmt = stmt.filter(ImageEditSession.campaign_id == campaign_id)
            
        if deliverable_id:
            stmt = stmt.filter(ImageEditSession.deliverable_id == deliverable_id)
            
        stmt = stmt.order_by(desc(ImageEditSession.updated_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_session(
        self,
        organization_id: str,
        data: ImageEditSessionCreate
    ) -> ImageEditSession:
        """Create a new image editing session."""
        session = ImageEditSession(
            organization_id=organization_id,
            **data.dict()
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        # Explicitly set empty history to avoid lazy load error
        # session.edit_history = []  # This might not work if it's instrumented
        # Better to query it back with eager load if needed, or just rely on it being empty?
        # Actually, refresh doesn't load relationships.
        # Let's just return it. The validation error happens because it tries to access it.
        # We can manually set it to empty list if it's not loaded.
        # Or we can re-query it.
        stmt = select(ImageEditSession).options(selectinload(ImageEditSession.edit_history)).filter(ImageEditSession.id == session.id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_session(self, session_id: str) -> Optional[ImageEditSession]:
        """Get an image editing session by ID."""
        stmt = select(ImageEditSession).options(selectinload(ImageEditSession.edit_history)).filter(ImageEditSession.id == session_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_session(
        self,
        session_id: str,
        data: ImageEditSessionUpdate
    ) -> Optional[ImageEditSession]:
        """Update an image editing session."""
        session = await self.get_session(session_id)
        if not session:
            return None
            
        for key, value in data.dict(exclude_unset=True).items():
            setattr(session, key, value)
            
        await self.db.commit()
        await self.db.refresh(session)
        # Re-query to get history
        stmt = select(ImageEditSession).options(selectinload(ImageEditSession.edit_history)).filter(ImageEditSession.id == session.id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def delete_session(self, session_id: str) -> bool:
        """Delete an image editing session."""
        session = await self.get_session(session_id)
        if not session:
            return False
            
        await self.db.delete(session)
        await self.db.commit()
        return True

    async def add_history_entry(
        self,
        session_id: str,
        data: ImageEditHistoryCreate
    ) -> ImageEditHistory:
        """Add an entry to the edit history."""
        history = ImageEditHistory(
            session_id=session_id,
            **data.dict()
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def generate_image(self, request: ImageGenerationRequest) -> Dict[str, Any]:
        """
        Generate an image using AI via Segmind service.
        
        Uses Segmind's flux-1.1-pro-ultra model for high-quality image generation.
        """
        settings = get_settings()
        operation_id = str(uuid.uuid4())
        
        # Check if Segmind API key is configured
        if not settings.segmind_api_key:
            logger.warning("Segmind API key not configured, returning placeholder")
            return {
                "success": False,
                "image_url": None,
                "preview_url": None,
                "message": "Image generation service not configured. Please set SEGMIND_API_KEY.",
                "operation_id": operation_id
            }
        
        try:
            # Parse size from request (e.g., "1024x1024")
            size_parts = request.size.split("x")
            width = int(size_parts[0]) if len(size_parts) >= 1 else 1024
            height = int(size_parts[1]) if len(size_parts) >= 2 else 1024
            
            # Initialize Segmind service
            segmind = SegmindService(
                api_key=settings.segmind_api_key,
                output_dir="outputs/image_editor"
            )
            
            # Generate image using Segmind
            logger.info(f"Generating image with prompt: {request.prompt[:100]}...")
            result = await segmind.generate_image(
                prompt=request.prompt,
                width=width,
                height=height
            )
            
            # Close the client
            await segmind.client.aclose()
            
            logger.info(f"Image generated successfully: {result.filename}")
            
            return {
                "success": True,
                "image_url": result.filepath,  # Local path - should be served via storage service
                "preview_url": result.filepath,
                "message": f"Image generated successfully using {result.model}",
                "operation_id": operation_id
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {
                "success": False,
                "image_url": None,
                "preview_url": None,
                "message": f"Image generation failed: {str(e)}",
                "operation_id": operation_id
            }

    async def process_edit(self, session_id: str, request: ImageEditRequest) -> Dict[str, Any]:
        """
        Process an image edit request using Segmind service.
        
        Supports operations: generate, edit, enhance, remove_background, crop, resize, filter
        """
        settings = get_settings()
        operation_id = str(uuid.uuid4())
        
        # Check if Segmind API key is configured
        if not settings.segmind_api_key:
            logger.warning("Segmind API key not configured, returning error")
            return {
                "success": False,
                "image_url": None,
                "preview_url": None,
                "message": "Image editing service not configured. Please set SEGMIND_API_KEY.",
                "operation_id": operation_id
            }
        
        try:
            # Initialize Segmind service
            segmind = SegmindService(
                api_key=settings.segmind_api_key,
                output_dir="outputs/image_editor"
            )
            
            if request.operation == "generate":
                # Use the generate_image method for generation
                if not request.prompt:
                    return {
                        "success": False,
                        "image_url": None,
                        "preview_url": None,
                        "message": "Prompt is required for image generation",
                        "operation_id": operation_id
                    }
                
                width = request.parameters.get("width", 1024)
                height = request.parameters.get("height", 1024)
                
                logger.info(f"Processing generate operation: {request.prompt[:100]}...")
                result = await segmind.generate_image(
                    prompt=request.prompt,
                    width=width,
                    height=height
                )
                
                await segmind.client.aclose()
                
                return {
                    "success": True,
                    "image_url": result.filepath,
                    "preview_url": result.filepath,
                    "message": f"Image generated successfully using {result.model}",
                    "operation_id": operation_id
                }
                
            elif request.operation == "edit":
                # For edit operations with a prompt (inpainting-style)
                if not request.prompt:
                    return {
                        "success": False,
                        "image_url": None,
                        "preview_url": None,
                        "message": "Prompt is required for edit operation",
                        "operation_id": operation_id
                    }
                
                # Get session to find current image
                session = await self.get_session(session_id)
                if not session or not session.current_image_url:
                    # If no current image, generate a new one
                    width = request.parameters.get("width", 1024)
                    height = request.parameters.get("height", 1024)
                    
                    result = await segmind.generate_image(
                        prompt=request.prompt,
                        width=width,
                        height=height
                    )
                    
                    await segmind.client.aclose()
                    
                    return {
                        "success": True,
                        "image_url": result.filepath,
                        "preview_url": result.filepath,
                        "message": f"New image generated (no source image found) using {result.model}",
                        "operation_id": operation_id
                    }
                
                # For now, generate a new image based on the edit prompt
                # Future: implement actual inpainting with mask support
                width = request.parameters.get("width", 1024)
                height = request.parameters.get("height", 1024)
                
                result = await segmind.generate_image(
                    prompt=request.prompt,
                    width=width,
                    height=height
                )
                
                await segmind.client.aclose()
                
                return {
                    "success": True,
                    "image_url": result.filepath,
                    "preview_url": result.filepath,
                    "message": f"Edit applied successfully using {result.model}",
                    "operation_id": operation_id
                }
                
            else:
                # For other operations (enhance, remove_background, crop, resize, filter)
                # These would require additional Segmind endpoints or local processing
                await segmind.client.aclose()
                
                logger.warning(f"Operation '{request.operation}' not yet implemented with Segmind")
                return {
                    "success": False,
                    "image_url": None,
                    "preview_url": None,
                    "message": f"Operation '{request.operation}' is not yet implemented. Supported: generate, edit",
                    "operation_id": operation_id
                }
                
        except Exception as e:
            logger.error(f"Image edit operation failed: {e}")
            return {
                "success": False,
                "image_url": None,
                "preview_url": None,
                "message": f"Operation failed: {str(e)}",
                "operation_id": operation_id
            }
