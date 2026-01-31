"""
Instagram Basic Display API integration for publishing posts.

Uses Instagram Graph API for business/creator accounts to publish:
- Single image posts
- Carousel posts (multiple images)
- Stories
- Reels (video posts)

Note: Instagram Basic Display API is read-only. For publishing,
we use the Instagram Graph API which requires a business/creator account
connected to a Facebook Page.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)

INSTAGRAM_GRAPH_BASE = "https://graph.instagram.com/v18.0"
FACEBOOK_GRAPH_BASE = "https://graph.facebook.com/v18.0"


@dataclass
class InstagramPostResult:
    """Result of an Instagram post operation."""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    permalink: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None
    platform: str = "instagram"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with consistent response format."""
        result = {
            "success": self.success,
            "platform": self.platform,
            "post_id": self.post_id,
            "url": self.permalink or self.post_url
        }
        if self.error:
            result["error"] = self.error
        return result


class InstagramService:
    """
    Instagram publishing service using Instagram Graph API.
    
    Requirements:
    - Instagram Business or Creator account
    - Account connected to a Facebook Page
    - Page access token with instagram_content_publish permission
    
    Features:
    - Post single images
    - Post carousel (multiple images)
    - Post Reels (videos)
    - Post Stories
    """
    
    def __init__(
        self,
        access_token: str,
        instagram_account_id: Optional[str] = None,
        facebook_page_id: Optional[str] = None
    ):
        self.access_token = access_token
        self.instagram_account_id = instagram_account_id
        self.facebook_page_id = facebook_page_id
        self._http_client = httpx.AsyncClient(timeout=120.0)
    
    async def _get_instagram_business_account_id(self) -> Optional[str]:
        """
        Get Instagram Business Account ID from Facebook Page.
        
        Returns:
            Instagram account ID or None
        """
        if not self.facebook_page_id:
            return None
        
        try:
            url = f"{FACEBOOK_GRAPH_BASE}/{self.facebook_page_id}"
            params = {
                "fields": "instagram_business_account",
                "access_token": self.access_token
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            ig_account = data.get("instagram_business_account", {})
            account_id = ig_account.get("id")
            
            if account_id:
                self.instagram_account_id = account_id
                return account_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Instagram business account ID: {e}")
            return None
    
    def _get_account_id(self) -> str:
        """Get the Instagram account ID, fetching if necessary."""
        if self.instagram_account_id:
            return self.instagram_account_id
        raise ValueError("Instagram account ID not configured. Call get_account_info() first.")
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get information about the Instagram account.
        
        Returns:
            Dictionary with account details
        """
        try:
            # Try to get account ID from Facebook page if not set
            if not self.instagram_account_id and self.facebook_page_id:
                await self._get_instagram_business_account_id()
            
            if not self.instagram_account_id:
                return {
                    "success": False,
                    "error": "No Instagram account ID available"
                }
            
            url = f"{INSTAGRAM_GRAPH_BASE}/{self.instagram_account_id}"
            params = {
                "fields": "username,name,biography,followers_count,follows_count,media_count,profile_picture_url",
                "access_token": self.access_token
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "id": self.instagram_account_id,
                "username": data.get("username"),
                "name": data.get("name"),
                "biography": data.get("biography"),
                "followers": data.get("followers_count"),
                "following": data.get("follows_count"),
                "media_count": data.get("media_count"),
                "profile_picture": data.get("profile_picture_url")
            }
            
        except Exception as e:
            logger.error(f"Failed to get Instagram account info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_media_container(
        self,
        image_url: str,
        caption: str = "",
        is_carousel_item: bool = False
    ) -> Optional[str]:
        """
        Create a media container for publishing.
        
        Args:
            image_url: URL of the image (must be publicly accessible)
            caption: Post caption
            is_carousel_item: Whether this is a carousel item
            
        Returns:
            Container ID or None
        """
        try:
            account_id = self._get_account_id()
            url = f"{INSTAGRAM_GRAPH_BASE}/{account_id}/media"
            
            params = {
                "image_url": image_url,
                "access_token": self.access_token
            }
            
            if caption:
                params["caption"] = caption
            
            if is_carousel_item:
                params["is_carousel_item"] = "true"
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("id")
            
        except Exception as e:
            logger.error(f"Failed to create media container: {e}")
            return None
    
    async def _create_video_container(
        self,
        video_url: str,
        caption: str = "",
        cover_url: Optional[str] = None,
        share_to_feed: bool = True
    ) -> Optional[str]:
        """
        Create a video container for Reels or video posts.
        
        Args:
            video_url: URL of the video (must be publicly accessible)
            caption: Post caption
            cover_url: Optional cover image URL
            share_to_feed: Whether to share to feed (for Reels)
            
        Returns:
            Container ID or None
        """
        try:
            account_id = self._get_account_id()
            url = f"{INSTAGRAM_GRAPH_BASE}/{account_id}/media"
            
            params = {
                "media_type": "REELS",
                "video_url": video_url,
                "access_token": self.access_token
            }
            
            if caption:
                params["caption"] = caption
            if cover_url:
                params["cover_url"] = cover_url
            if share_to_feed:
                params["share_to_feed"] = "true"
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("id")
            
        except Exception as e:
            logger.error(f"Failed to create video container: {e}")
            return None
    
    async def _create_carousel_container(
        self,
        children: List[str],
        caption: str = ""
    ) -> Optional[str]:
        """
        Create a carousel container from child media containers.
        
        Args:
            children: List of media container IDs
            caption: Post caption
            
        Returns:
            Container ID or None
        """
        try:
            account_id = self._get_account_id()
            url = f"{INSTAGRAM_GRAPH_BASE}/{account_id}/media"
            
            params = {
                "media_type": "CAROUSEL",
                "children": ",".join(children),
                "access_token": self.access_token
            }
            
            if caption:
                params["caption"] = caption
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("id")
            
        except Exception as e:
            logger.error(f"Failed to create carousel container: {e}")
            return None
    
    async def _publish_container(self, container_id: str) -> Optional[str]:
        """
        Publish a media container.
        
        Args:
            container_id: ID of the container to publish
            
        Returns:
            Media ID of the published post or None
        """
        try:
            account_id = self._get_account_id()
            url = f"{INSTAGRAM_GRAPH_BASE}/{account_id}/media_publish"
            
            params = {
                "creation_id": container_id,
                "access_token": self.access_token
            }
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("id")
            
        except Exception as e:
            logger.error(f"Failed to publish container: {e}")
            return None
    
    async def _wait_for_container_status(
        self,
        container_id: str,
        max_attempts: int = 30,
        delay: int = 2
    ) -> bool:
        """
        Wait for a container to be ready for publishing.
        
        Args:
            container_id: ID of the container
            max_attempts: Maximum number of status checks
            delay: Seconds between checks
            
        Returns:
            True if container is ready
        """
        url = f"{INSTAGRAM_GRAPH_BASE}/{container_id}"
        params = {
            "fields": "status_code",
            "access_token": self.access_token
        }
        
        for attempt in range(max_attempts):
            try:
                response = await self._http_client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                status = data.get("status_code")
                
                if status == "FINISHED":
                    return True
                elif status == "ERROR":
                    logger.error(f"Container {container_id} processing failed")
                    return False
                elif status == "EXPIRED":
                    logger.error(f"Container {container_id} expired")
                    return False
                
                # Still processing, wait
                logger.debug(f"Container {container_id} status: {status}, waiting...")
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error checking container status: {e}")
                await asyncio.sleep(delay)
        
        logger.warning(f"Container {container_id} not ready after {max_attempts} attempts")
        return False
    
    async def post_image(
        self,
        image_url: str,
        caption: str = ""
    ) -> InstagramPostResult:
        """
        Post a single image to Instagram.
        
        Args:
            image_url: Publicly accessible URL of the image
            caption: Post caption (supports hashtags and mentions)
            
        Returns:
            InstagramPostResult with post details
        """
        try:
            # Create container
            container_id = await self._create_media_container(
                image_url=image_url,
                caption=caption
            )
            
            if not container_id:
                return InstagramPostResult(
                    success=False,
                    error="Failed to create media container",
                    text=caption
                )
            
            # Wait for processing
            ready = await self._wait_for_container_status(container_id)
            
            if not ready:
                return InstagramPostResult(
                    success=False,
                    error="Media processing failed or timed out",
                    text=caption
                )
            
            # Publish
            media_id = await self._publish_container(container_id)
            
            if not media_id:
                return InstagramPostResult(
                    success=False,
                    error="Failed to publish media",
                    text=caption
                )
            
            # Get permalink
            permalink = await self._get_permalink(media_id)
            post_url = permalink or f"https://instagram.com/p/{media_id}"
            
            logger.info(f"Posted to Instagram: {post_url}")
            
            return InstagramPostResult(
                success=True,
                post_id=media_id,
                post_url=post_url,
                permalink=permalink,
                text=caption
            )
            
        except Exception as e:
            logger.error(f"Failed to post to Instagram: {e}")
            return InstagramPostResult(
                success=False,
                error=str(e),
                text=caption
            )
    
    async def post_carousel(
        self,
        image_urls: List[str],
        caption: str = ""
    ) -> InstagramPostResult:
        """
        Post a carousel (multiple images) to Instagram.
        
        Args:
            image_urls: List of publicly accessible image URLs (2-10 images)
            caption: Post caption
            
        Returns:
            InstagramPostResult with post details
        """
        try:
            if len(image_urls) < 2 or len(image_urls) > 10:
                return InstagramPostResult(
                    success=False,
                    error="Instagram carousels require 2-10 images",
                    text=caption
                )
            
            # Create containers for each image
            child_containers = []
            for url in image_urls:
                container_id = await self._create_media_container(
                    image_url=url,
                    is_carousel_item=True
                )
                if container_id:
                    child_containers.append(container_id)
                else:
                    logger.error(f"Failed to create container for image: {url}")
            
            if len(child_containers) < 2:
                return InstagramPostResult(
                    success=False,
                    error="Failed to create enough media containers for carousel",
                    text=caption
                )
            
            # Wait for all children to be ready
            ready_results = await asyncio.gather(*[
                self._wait_for_container_status(cid)
                for cid in child_containers
            ])
            
            if not all(ready_results):
                return InstagramPostResult(
                    success=False,
                    error="Some carousel items failed to process",
                    text=caption
                )
            
            # Create carousel container
            carousel_id = await self._create_carousel_container(
                children=child_containers,
                caption=caption
            )
            
            if not carousel_id:
                return InstagramPostResult(
                    success=False,
                    error="Failed to create carousel container",
                    text=caption
                )
            
            # Wait for carousel to be ready
            ready = await self._wait_for_container_status(carousel_id)
            
            if not ready:
                return InstagramPostResult(
                    success=False,
                    error="Carousel processing failed or timed out",
                    text=caption
                )
            
            # Publish
            media_id = await self._publish_container(carousel_id)
            
            if not media_id:
                return InstagramPostResult(
                    success=False,
                    error="Failed to publish carousel",
                    text=caption
                )
            
            permalink = await self._get_permalink(media_id)
            post_url = permalink or f"https://instagram.com/p/{media_id}"
            
            logger.info(f"Posted carousel to Instagram: {post_url}")
            
            return InstagramPostResult(
                success=True,
                post_id=media_id,
                post_url=post_url,
                permalink=permalink,
                text=caption
            )
            
        except Exception as e:
            logger.error(f"Failed to post carousel to Instagram: {e}")
            return InstagramPostResult(
                success=False,
                error=str(e),
                text=caption
            )
    
    async def post_reel(
        self,
        video_url: str,
        caption: str = "",
        cover_url: Optional[str] = None
    ) -> InstagramPostResult:
        """
        Post a Reel (video) to Instagram.
        
        Args:
            video_url: Publicly accessible URL of the video
            caption: Post caption
            cover_url: Optional cover image URL
            
        Returns:
            InstagramPostResult with post details
        """
        try:
            # Create video container
            container_id = await self._create_video_container(
                video_url=video_url,
                caption=caption,
                cover_url=cover_url,
                share_to_feed=True
            )
            
            if not container_id:
                return InstagramPostResult(
                    success=False,
                    error="Failed to create video container",
                    text=caption
                )
            
            # Videos take longer to process
            ready = await self._wait_for_container_status(
                container_id,
                max_attempts=60,  # 2 minutes
                delay=2
            )
            
            if not ready:
                return InstagramPostResult(
                    success=False,
                    error="Video processing failed or timed out",
                    text=caption
                )
            
            # Publish
            media_id = await self._publish_container(container_id)
            
            if not media_id:
                return InstagramPostResult(
                    success=False,
                    error="Failed to publish reel",
                    text=caption
                )
            
            permalink = await self._get_permalink(media_id)
            post_url = permalink or f"https://instagram.com/reel/{media_id}"
            
            logger.info(f"Posted reel to Instagram: {post_url}")
            
            return InstagramPostResult(
                success=True,
                post_id=media_id,
                post_url=post_url,
                permalink=permalink,
                text=caption
            )
            
        except Exception as e:
            logger.error(f"Failed to post reel to Instagram: {e}")
            return InstagramPostResult(
                success=False,
                error=str(e),
                text=caption
            )
    
    async def _get_permalink(self, media_id: str) -> Optional[str]:
        """Get the permalink for a media post."""
        try:
            url = f"{INSTAGRAM_GRAPH_BASE}/{media_id}"
            params = {
                "fields": "permalink",
                "access_token": self.access_token
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("permalink")
            
        except Exception as e:
            logger.error(f"Failed to get permalink: {e}")
            return None
    
    async def delete_media(self, media_id: str) -> bool:
        """
        Delete a media post from Instagram.
        
        Args:
            media_id: ID of the media to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            url = f"{INSTAGRAM_GRAPH_BASE}/{media_id}"
            params = {
                "access_token": self.access_token
            }
            
            response = await self._http_client.delete(url, params=params)
            response.raise_for_status()
            
            logger.info(f"Deleted Instagram media: {media_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Instagram media {media_id}: {e}")
            return False
    
    async def get_media_insights(self, media_id: str) -> Dict[str, Any]:
        """
        Get insights/metrics for a media post.
        
        Args:
            media_id: ID of the media
            
        Returns:
            Dictionary with metrics
        """
        try:
            url = f"{INSTAGRAM_GRAPH_BASE}/{media_id}/insights"
            params = {
                "metric": "impressions,reach,engagement,saved",
                "access_token": self.access_token
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            metrics = {}
            for item in data.get("data", []):
                metric_name = item.get("name")
                metric_value = item.get("values", [{}])[0].get("value", 0)
                metrics[metric_name] = metric_value
            
            return {
                "success": True,
                "media_id": media_id,
                **metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get insights for media {media_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "media_id": media_id
            }
    
    async def validate_credentials(self) -> Dict[str, Any]:
        """
        Validate that Instagram credentials are working.
        
        Returns:
            Dictionary with validation status
        """
        try:
            # Try to get account info
            info = await self.get_account_info()
            
            if info.get("success"):
                return {
                    "valid": True,
                    "username": info.get("username"),
                    "name": info.get("name"),
                    "account_type": "business/creator"
                }
            else:
                return {
                    "valid": False,
                    "error": info.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"Instagram credentials validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
