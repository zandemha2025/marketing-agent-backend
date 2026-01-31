import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel, Field
import logging

from ..core.database import get_session
from ..core.config import get_settings
from ..models.scheduled_post import ScheduledPost
from .auth import get_current_active_user
from ..models.user import User
from ..services.social import (
    TwitterService,
    LinkedInService,
    InstagramService,
    FacebookService
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduled-posts", tags=["Scheduled Posts"])

# --- Schemas ---

class ScheduledPostBase(BaseModel):
    title: str
    content: str
    platform: str  # twitter, linkedin, instagram, facebook
    scheduled_at: datetime
    status: str = "scheduled"  # scheduled, published, failed, publishing
    campaign_id: Optional[str] = None
    image_urls: Optional[List[str]] = Field(default=None, description="URLs of images to include")
    video_url: Optional[str] = Field(default=None, description="URL of video to include")

class ScheduledPostCreate(ScheduledPostBase):
    organization_id: str

class ScheduledPostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    platform: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    image_urls: Optional[List[str]] = None
    video_url: Optional[str] = None

class ScheduledPostResponse(ScheduledPostBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class PublishRequest(BaseModel):
    """Request to publish a post immediately."""
    image_urls: Optional[List[str]] = None
    video_url: Optional[str] = None

class PublishResult(BaseModel):
    """Result of a publish operation."""
    success: bool
    platform: str
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None

class PlatformStatus(BaseModel):
    """Status of a social platform connection."""
    platform: str
    connected: bool
    username: Optional[str] = None
    error: Optional[str] = None

# --- Helper Functions ---

def get_twitter_service() -> Optional[TwitterService]:
    """Get Twitter service if credentials are configured."""
    settings = get_settings()
    
    # Check for Twitter credentials in settings or environment
    api_key = getattr(settings, 'twitter_api_key', None) or os.environ.get('TWITTER_API_KEY')
    api_secret = getattr(settings, 'twitter_api_secret', None) or os.environ.get('TWITTER_API_SECRET')
    access_token = getattr(settings, 'twitter_access_token', None) or os.environ.get('TWITTER_ACCESS_TOKEN')
    access_secret = getattr(settings, 'twitter_access_secret', None) or os.environ.get('TWITTER_ACCESS_SECRET')
    
    if all([api_key, api_secret, access_token, access_secret]):
        return TwitterService(
            api_key=api_key,
            api_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )
    return None

def get_linkedin_service() -> Optional[LinkedInService]:
    """Get LinkedIn service if credentials are configured."""
    settings = get_settings()
    
    access_token = getattr(settings, 'linkedin_access_token', None) or os.environ.get('LINKEDIN_ACCESS_TOKEN')
    
    if access_token:
        return LinkedInService(access_token=access_token)
    return None

def get_instagram_service() -> Optional[InstagramService]:
    """Get Instagram service if credentials are configured."""
    settings = get_settings()
    
    access_token = getattr(settings, 'instagram_access_token', None) or os.environ.get('INSTAGRAM_ACCESS_TOKEN')
    account_id = getattr(settings, 'instagram_account_id', None) or os.environ.get('INSTAGRAM_ACCOUNT_ID')
    
    if access_token:
        return InstagramService(
            access_token=access_token,
            instagram_account_id=account_id
        )
    return None

def get_facebook_service() -> Optional[FacebookService]:
    """Get Facebook service if credentials are configured."""
    settings = get_settings()
    
    access_token = getattr(settings, 'facebook_access_token', None) or os.environ.get('FACEBOOK_ACCESS_TOKEN')
    page_id = getattr(settings, 'facebook_page_id', None) or os.environ.get('FACEBOOK_PAGE_ID')
    
    if access_token and page_id:
        return FacebookService(
            access_token=access_token,
            page_id=page_id
        )
    return None

async def publish_to_platform(
    post: ScheduledPost,
    image_urls: Optional[List[str]] = None,
    video_url: Optional[str] = None
) -> PublishResult:
    """
    Publish a post to the appropriate social platform.
    
    Args:
        post: The scheduled post to publish
        image_urls: Optional list of image URLs to include
        video_url: Optional video URL to include
        
    Returns:
        PublishResult with success/failure details
    """
    platform = post.platform.lower()
    
    try:
        if platform == "twitter":
            service = get_twitter_service()
            if not service:
                return PublishResult(
                    success=False,
                    platform=platform,
                    error="Twitter credentials not configured"
                )
            
            # Publish based on content type
            if video_url:
                result = await service.post_with_video(
                    text=post.content,
                    video_url=video_url
                )
            elif image_urls and len(image_urls) > 0:
                result = await service.post_with_images(
                    text=post.content,
                    image_urls=image_urls
                )
            else:
                result = await service.post_text(text=post.content)
            
            await service.close()
            
            return PublishResult(
                success=result.success,
                platform=platform,
                post_id=result.post_id,
                post_url=result.post_url,
                error=result.error
            )
        
        elif platform == "linkedin":
            service = get_linkedin_service()
            if not service:
                return PublishResult(
                    success=False,
                    platform=platform,
                    error="LinkedIn credentials not configured"
                )
            
            # Get profile URN if not set
            if not service.person_urn:
                await service.get_profile_urn()
            
            # Publish based on content type
            if image_urls and len(image_urls) > 0:
                result = await service.post_with_images(
                    text=post.content,
                    image_urls=image_urls
                )
            else:
                result = await service.post_text(text=post.content)
            
            await service.close()
            
            return PublishResult(
                success=result.success,
                platform=platform,
                post_id=result.post_id,
                post_url=result.post_url,
                error=result.error
            )
        
        elif platform == "instagram":
            service = get_instagram_service()
            if not service:
                return PublishResult(
                    success=False,
                    platform=platform,
                    error="Instagram credentials not configured"
                )
            
            # Get account info to validate
            account_info = await service.get_account_info()
            if not account_info.get("success"):
                return PublishResult(
                    success=False,
                    platform=platform,
                    error=f"Instagram account error: {account_info.get('error')}"
                )
            
            # Instagram requires media - use first image or video
            if video_url:
                result = await service.post_reel(
                    video_url=video_url,
                    caption=post.content
                )
            elif image_urls and len(image_urls) == 1:
                result = await service.post_image(
                    image_url=image_urls[0],
                    caption=post.content
                )
            elif image_urls and len(image_urls) > 1:
                result = await service.post_carousel(
                    image_urls=image_urls,
                    caption=post.content
                )
            else:
                return PublishResult(
                    success=False,
                    platform=platform,
                    error="Instagram requires at least one image or video"
                )
            
            await service.close()
            
            return PublishResult(
                success=result.success,
                platform=platform,
                post_id=result.post_id,
                post_url=result.post_url,
                error=result.error
            )
        
        elif platform == "facebook":
            service = get_facebook_service()
            if not service:
                return PublishResult(
                    success=False,
                    platform=platform,
                    error="Facebook credentials not configured"
                )
            
            # Publish based on content type
            if video_url:
                result = await service.post_with_video(
                    message=post.content,
                    video_url=video_url
                )
            elif image_urls and len(image_urls) > 0:
                result = await service.post_with_images(
                    message=post.content,
                    image_urls=image_urls
                )
            else:
                result = await service.post_text(message=post.content)
            
            await service.close()
            
            return PublishResult(
                success=result.success,
                platform=platform,
                post_id=result.post_id,
                post_url=result.post_url,
                error=result.error
            )
        
        else:
            return PublishResult(
                success=False,
                platform=platform,
                error=f"Unsupported platform: {platform}"
            )
    
    except Exception as e:
        logger.error(f"Error publishing to {platform}: {e}")
        return PublishResult(
            success=False,
            platform=platform,
            error=str(e)
        )

# --- Endpoints ---

@router.get("/", response_model=List[ScheduledPostResponse])
async def list_scheduled_posts(
    organization_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """List scheduled posts for an organization with optional filters."""
    query = select(ScheduledPost).where(ScheduledPost.organization_id == organization_id)
    
    if start_date:
        query = query.where(ScheduledPost.scheduled_at >= start_date)
    
    if end_date:
        query = query.where(ScheduledPost.scheduled_at <= end_date)
    
    if status:
        query = query.where(ScheduledPost.status == status)
    
    if platform:
        query = query.where(ScheduledPost.platform == platform)
        
    query = query.order_by(desc(ScheduledPost.scheduled_at))
    
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/", response_model=ScheduledPostResponse)
async def create_scheduled_post(
    post_in: ScheduledPostCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Schedule a new post."""
    post = ScheduledPost(**post_in.model_dump())
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post

@router.get("/{post_id}", response_model=ScheduledPostResponse)
async def get_scheduled_post(
    post_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific scheduled post."""
    post = await session.get(ScheduledPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    return post

@router.put("/{post_id}", response_model=ScheduledPostResponse)
async def update_scheduled_post(
    post_id: str,
    post_in: ScheduledPostUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Update a scheduled post."""
    post = await session.get(ScheduledPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    
    # Don't allow updates to already published posts
    if post.status == "published":
        raise HTTPException(status_code=400, detail="Cannot update a published post")
    
    update_data = post_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
        
    await session.commit()
    await session.refresh(post)
    return post

@router.delete("/{post_id}")
async def delete_scheduled_post(
    post_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a scheduled post."""
    post = await session.get(ScheduledPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    
    await session.delete(post)
    await session.commit()
    return {"success": True}

@router.post("/{post_id}/publish", response_model=PublishResult)
async def publish_post(
    post_id: str,
    request: Optional[PublishRequest] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Publish a post immediately to the configured social platform.
    
    This uses the actual social media APIs to publish the content.
    """
    post = await session.get(ScheduledPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    
    # Update status to publishing
    post.status = "publishing"
    await session.commit()
    
    # Get media URLs from request or post
    image_urls = request.image_urls if request else None
    video_url = request.video_url if request else None
    
    # Publish to platform
    result = await publish_to_platform(post, image_urls, video_url)
    
    # Update post status based on result
    if result.success:
        post.status = "published"
        post.published_at = datetime.utcnow()
        post.platform_post_id = result.post_id
        post.platform_post_url = result.post_url
        post.error_message = None
    else:
        post.status = "failed"
        post.error_message = result.error
    
    await session.commit()
    await session.refresh(post)
    
    return result

@router.post("/{post_id}/publish-async")
async def publish_post_async(
    post_id: str,
    background_tasks: BackgroundTasks,
    request: Optional[PublishRequest] = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Queue a post for publishing in the background.
    
    Returns immediately and processes publishing asynchronously.
    """
    post = await session.get(ScheduledPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")
    
    # Update status to publishing
    post.status = "publishing"
    await session.commit()
    
    # Get media URLs
    image_urls = request.image_urls if request else None
    video_url = request.video_url if request else None
    
    # Add to background tasks
    background_tasks.add_task(
        _publish_post_background,
        post_id,
        image_urls,
        video_url
    )
    
    return {
        "success": True,
        "message": "Post queued for publishing",
        "post_id": post_id
    }

async def _publish_post_background(
    post_id: str,
    image_urls: Optional[List[str]],
    video_url: Optional[str]
):
    """Background task to publish a post."""
    from ..core.database import get_database_manager
    
    db = get_database_manager()
    async with db.session() as session:
        try:
            post = await session.get(ScheduledPost, post_id)
            if not post:
                logger.error(f"Post {post_id} not found for background publishing")
                return
            
            # Publish to platform
            result = await publish_to_platform(post, image_urls, video_url)
            
            # Update post status
            if result.success:
                post.status = "published"
                post.published_at = datetime.utcnow()
                post.platform_post_id = result.post_id
                post.platform_post_url = result.post_url
                post.error_message = None
            else:
                post.status = "failed"
                post.error_message = result.error
            
            await session.commit()
            
        except Exception as e:
            logger.error(f"Background publishing failed for post {post_id}: {e}")
            # Try to update status to failed
            try:
                post = await session.get(ScheduledPost, post_id)
                if post:
                    post.status = "failed"
                    post.error_message = str(e)
                    await session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update post status after publishing error: {update_error}")

@router.get("/platforms/status", response_model=List[PlatformStatus])
async def get_platform_status():
    """Get the connection status of all social platforms."""
    import os
    
    platforms = []
    
    # Twitter
    try:
        service = get_twitter_service()
        if service:
            validation = await service.validate_credentials()
            platforms.append(PlatformStatus(
                platform="twitter",
                connected=validation.get("valid", False),
                username=validation.get("username"),
                error=validation.get("error")
            ))
            await service.close()
        else:
            platforms.append(PlatformStatus(
                platform="twitter",
                connected=False,
                error="Credentials not configured"
            ))
    except Exception as e:
        platforms.append(PlatformStatus(
            platform="twitter",
            connected=False,
            error=str(e)
        ))
    
    # LinkedIn
    try:
        service = get_linkedin_service()
        if service:
            validation = await service.validate_credentials()
            platforms.append(PlatformStatus(
                platform="linkedin",
                connected=validation.get("valid", False),
                username=validation.get("name"),
                error=validation.get("error")
            ))
            await service.close()
        else:
            platforms.append(PlatformStatus(
                platform="linkedin",
                connected=False,
                error="Credentials not configured"
            ))
    except Exception as e:
        platforms.append(PlatformStatus(
            platform="linkedin",
            connected=False,
            error=str(e)
        ))
    
    # Instagram
    try:
        service = get_instagram_service()
        if service:
            validation = await service.validate_credentials()
            platforms.append(PlatformStatus(
                platform="instagram",
                connected=validation.get("valid", False),
                username=validation.get("username"),
                error=validation.get("error")
            ))
            await service.close()
        else:
            platforms.append(PlatformStatus(
                platform="instagram",
                connected=False,
                error="Credentials not configured"
            ))
    except Exception as e:
        platforms.append(PlatformStatus(
            platform="instagram",
            connected=False,
            error=str(e)
        ))
    
    # Facebook
    try:
        service = get_facebook_service()
        if service:
            validation = await service.validate_credentials()
            platforms.append(PlatformStatus(
                platform="facebook",
                connected=validation.get("valid", False),
                username=validation.get("page_name"),
                error=validation.get("error")
            ))
            await service.close()
        else:
            platforms.append(PlatformStatus(
                platform="facebook",
                connected=False,
                error="Credentials not configured"
            ))
    except Exception as e:
        platforms.append(PlatformStatus(
            platform="facebook",
            connected=False,
            error=str(e)
        ))
    
    return platforms

@router.get("/stats/overview")
async def get_posting_stats(
    organization_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get posting statistics for an organization."""
    # Total posts
    total_result = await session.execute(
        select(func.count(ScheduledPost.id))
        .where(ScheduledPost.organization_id == organization_id)
    )
    total = total_result.scalar() or 0
    
    # By status
    status_result = await session.execute(
        select(ScheduledPost.status, func.count(ScheduledPost.id))
        .where(ScheduledPost.organization_id == organization_id)
        .group_by(ScheduledPost.status)
    )
    by_status = {status: count for status, count in status_result.all()}
    
    # By platform
    platform_result = await session.execute(
        select(ScheduledPost.platform, func.count(ScheduledPost.id))
        .where(ScheduledPost.organization_id == organization_id)
        .group_by(ScheduledPost.platform)
    )
    by_platform = {platform: count for platform, count in platform_result.all()}
    
    # Published this week
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_result = await session.execute(
        select(func.count(ScheduledPost.id))
        .where(ScheduledPost.organization_id == organization_id)
        .where(ScheduledPost.status == "published")
        .where(ScheduledPost.published_at >= week_ago)
    )
    published_this_week = week_result.scalar() or 0
    
    return {
        "total": total,
        "by_status": by_status,
        "by_platform": by_platform,
        "published_this_week": published_this_week
    }
