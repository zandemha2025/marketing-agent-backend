"""
Facebook Graph API integration for publishing posts.

Uses Facebook Graph API v18.0+ for publishing to Facebook Pages.
Supports text posts, posts with images, videos, links, and stories.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)

FACEBOOK_GRAPH_BASE = "https://graph.facebook.com/v18.0"


@dataclass
class FacebookPostResult:
    """Result of a Facebook post operation."""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None
    platform: str = "facebook"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with consistent response format."""
        result = {
            "success": self.success,
            "platform": self.platform,
            "post_id": self.post_id,
            "url": self.post_url
        }
        if self.error:
            result["error"] = self.error
        return result


class FacebookService:
    """
    Facebook Page publishing service.
    
    Features:
    - Post text updates to Facebook Page
    - Post with single or multiple images
    - Post with videos
    - Post with link previews
    - Schedule posts
    """
    
    def __init__(
        self,
        access_token: str,
        page_id: Optional[str] = None
    ):
        self.access_token = access_token
        self.page_id = page_id
        self._http_client = httpx.AsyncClient(timeout=120.0)
    
    def _get_page_id(self) -> str:
        """Get the Facebook Page ID."""
        if not self.page_id:
            raise ValueError("Facebook Page ID not configured")
        return self.page_id
    
    async def get_page_info(self) -> Dict[str, Any]:
        """
        Get information about the Facebook Page.
        
        Returns:
            Dictionary with page details
        """
        try:
            page_id = self._get_page_id()
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}"
            
            params = {
                "fields": "name,about,description,fan_count,followers_count,link,picture",
                "access_token": self.access_token
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "id": page_id,
                "name": data.get("name"),
                "about": data.get("about"),
                "description": data.get("description"),
                "likes": data.get("fan_count"),
                "followers": data.get("followers_count"),
                "link": data.get("link"),
                "picture": data.get("picture", {}).get("data", {}).get("url")
            }
            
        except Exception as e:
            logger.error(f"Failed to get Facebook page info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _upload_photo(self, photo_url: str, published: bool = True) -> Optional[str]:
        """
        Upload a photo to Facebook for use in posts.
        
        Args:
            photo_url: URL of the photo
            published: Whether to publish immediately or use in a batch
            
        Returns:
            Photo ID or None
        """
        try:
            page_id = self._get_page_id()
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/photos"
            
            params = {
                "url": photo_url,
                "published": "true" if published else "false",
                "access_token": self.access_token
            }
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("id")
            
        except Exception as e:
            logger.error(f"Failed to upload photo to Facebook: {e}")
            return None
    
    async def _upload_video(self, video_url: str, description: str = "") -> Optional[str]:
        """
        Upload a video to Facebook.
        
        Args:
            video_url: URL of the video
            description: Video description
            
        Returns:
            Video ID or None
        """
        try:
            page_id = self._get_page_id()
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/videos"
            
            params = {
                "file_url": video_url,
                "description": description,
                "access_token": self.access_token
            }
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get("id")
            
        except Exception as e:
            logger.error(f"Failed to upload video to Facebook: {e}")
            return None
    
    async def post_text(
        self,
        message: str,
        link: Optional[str] = None
    ) -> FacebookPostResult:
        """
        Post a text update to Facebook Page.
        
        Args:
            message: Post message/text
            link: Optional link to include
            
        Returns:
            FacebookPostResult with post details
        """
        try:
            page_id = self._get_page_id()
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/feed"
            
            params = {
                "message": message,
                "access_token": self.access_token
            }
            
            if link:
                params["link"] = link
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            post_id = data.get("id")
            post_url = f"https://facebook.com/{post_id}" if post_id else None
            
            logger.info(f"Posted to Facebook: {post_url}")
            
            return FacebookPostResult(
                success=True,
                post_id=post_id,
                post_url=post_url,
                text=message
            )
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            logger.error(f"Facebook API error: {error_detail}")
            return FacebookPostResult(
                success=False,
                error=f"Facebook API error: {error_detail}",
                text=message
            )
        except Exception as e:
            logger.error(f"Failed to post to Facebook: {e}")
            return FacebookPostResult(
                success=False,
                error=str(e),
                text=message
            )
    
    async def post_with_image(
        self,
        message: str,
        image_url: str
    ) -> FacebookPostResult:
        """
        Post with a single image to Facebook Page.
        
        Args:
            message: Post message
            image_url: URL of the image
            
        Returns:
            FacebookPostResult with post details
        """
        try:
            page_id = self._get_page_id()
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/photos"
            
            params = {
                "message": message,
                "url": image_url,
                "access_token": self.access_token
            }
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            post_id = data.get("post_id") or data.get("id")
            post_url = f"https://facebook.com/{post_id}" if post_id else None
            
            logger.info(f"Posted image to Facebook: {post_url}")
            
            return FacebookPostResult(
                success=True,
                post_id=post_id,
                post_url=post_url,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to post image to Facebook: {e}")
            return FacebookPostResult(
                success=False,
                error=str(e),
                text=message
            )
    
    async def post_with_images(
        self,
        message: str,
        image_urls: List[str]
    ) -> FacebookPostResult:
        """
        Post with multiple images to Facebook Page.
        
        Args:
            message: Post message
            image_urls: List of image URLs
            
        Returns:
            FacebookPostResult with post details
        """
        try:
            if len(image_urls) == 1:
                return await self.post_with_image(message, image_urls[0])
            
            page_id = self._get_page_id()
            
            # Upload photos as unpublished first
            attached_media = []
            for img_url in image_urls:
                photo_id = await self._upload_photo(img_url, published=False)
                if photo_id:
                    attached_media.append({"media_fbid": photo_id})
            
            if not attached_media:
                return FacebookPostResult(
                    success=False,
                    error="Failed to upload any photos",
                    text=message
                )
            
            # Create post with attached photos
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/feed"
            
            import json
            params = {
                "message": message,
                "attached_media": json.dumps(attached_media),
                "access_token": self.access_token
            }
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            post_id = data.get("id")
            post_url = f"https://facebook.com/{post_id}" if post_id else None
            
            logger.info(f"Posted {len(attached_media)} images to Facebook: {post_url}")
            
            return FacebookPostResult(
                success=True,
                post_id=post_id,
                post_url=post_url,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to post multiple images to Facebook: {e}")
            return FacebookPostResult(
                success=False,
                error=str(e),
                text=message
            )
    
    async def post_with_video(
        self,
        message: str,
        video_url: str,
        title: Optional[str] = None
    ) -> FacebookPostResult:
        """
        Post a video to Facebook Page.
        
        Args:
            message: Post message/description
            video_url: URL of the video
            title: Optional video title
            
        Returns:
            FacebookPostResult with post details
        """
        try:
            page_id = self._get_page_id()
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/videos"
            
            params = {
                "file_url": video_url,
                "description": message,
                "access_token": self.access_token
            }
            
            if title:
                params["title"] = title
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            video_id = data.get("id")
            post_url = f"https://facebook.com/{video_id}" if video_id else None
            
            logger.info(f"Posted video to Facebook: {post_url}")
            
            return FacebookPostResult(
                success=True,
                post_id=video_id,
                post_url=post_url,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to post video to Facebook: {e}")
            return FacebookPostResult(
                success=False,
                error=str(e),
                text=message
            )
    
    async def post_with_link(
        self,
        message: str,
        link: str,
        link_title: Optional[str] = None,
        link_description: Optional[str] = None,
        link_image_url: Optional[str] = None
    ) -> FacebookPostResult:
        """
        Post with a link preview to Facebook Page.
        
        Args:
            message: Post message
            link: URL to share
            link_title: Custom link title (optional)
            link_description: Custom link description (optional)
            link_image_url: Custom link image URL (optional)
            
        Returns:
            FacebookPostResult with post details
        """
        try:
            page_id = self._get_page_id()
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/feed"
            
            params = {
                "message": message,
                "link": link,
                "access_token": self.access_token
            }
            
            # Facebook will scrape the link for preview, but we can override
            if link_title:
                params["name"] = link_title
            if link_description:
                params["description"] = link_description
            if link_image_url:
                params["picture"] = link_image_url
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            post_id = data.get("id")
            post_url = f"https://facebook.com/{post_id}" if post_id else None
            
            logger.info(f"Posted link to Facebook: {post_url}")
            
            return FacebookPostResult(
                success=True,
                post_id=post_id,
                post_url=post_url,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to post link to Facebook: {e}")
            return FacebookPostResult(
                success=False,
                error=str(e),
                text=message
            )
    
    async def schedule_post(
        self,
        message: str,
        scheduled_time: int,  # Unix timestamp
        link: Optional[str] = None,
        image_urls: Optional[List[str]] = None
    ) -> FacebookPostResult:
        """
        Schedule a post for future publishing.
        
        Args:
            message: Post message
            scheduled_time: Unix timestamp for when to publish
            link: Optional link
            image_urls: Optional list of image URLs
            
        Returns:
            FacebookPostResult with post details
        """
        try:
            page_id = self._get_page_id()
            url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/feed"
            
            params = {
                "message": message,
                "scheduled_publish_time": scheduled_time,
                "published": "false",
                "access_token": self.access_token
            }
            
            if link:
                params["link"] = link
            
            if image_urls:
                # Handle single image
                if len(image_urls) == 1:
                    params["url"] = image_urls[0]
                    url = f"{FACEBOOK_GRAPH_BASE}/{page_id}/photos"
                    params["published"] = "false"
                else:
                    # For multiple images, we'd need to upload unpublished first
                    # This is simplified - full implementation would batch upload
                    params["link"] = image_urls[0]
            
            response = await self._http_client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            post_id = data.get("id")
            
            logger.info(f"Scheduled post on Facebook: {post_id}")
            
            return FacebookPostResult(
                success=True,
                post_id=post_id,
                post_url=None,  # Not published yet
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to schedule Facebook post: {e}")
            return FacebookPostResult(
                success=False,
                error=str(e),
                text=message
            )
    
    async def delete_post(self, post_id: str) -> bool:
        """
        Delete a Facebook post.
        
        Args:
            post_id: ID of the post to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            url = f"{FACEBOOK_GRAPH_BASE}/{post_id}"
            params = {
                "access_token": self.access_token
            }
            
            response = await self._http_client.delete(url, params=params)
            response.raise_for_status()
            
            logger.info(f"Deleted Facebook post: {post_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete Facebook post {post_id}: {e}")
            return False
    
    async def get_post_insights(self, post_id: str) -> Dict[str, Any]:
        """
        Get insights/metrics for a Facebook post.
        
        Args:
            post_id: ID of the post
            
        Returns:
            Dictionary with metrics
        """
        try:
            url = f"{FACEBOOK_GRAPH_BASE}/{post_id}/insights"
            
            params = {
                "metric": "post_impressions,post_reach,post_engaged_users,post_reactions_by_type_total",
                "access_token": self.access_token
            }
            
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            insights = {}
            for item in data.get("data", []):
                metric_name = item.get("name")
                values = item.get("values", [])
                if values:
                    insights[metric_name] = values[0].get("value", 0)
            
            return {
                "success": True,
                "post_id": post_id,
                **insights
            }
            
        except Exception as e:
            logger.error(f"Failed to get insights for Facebook post {post_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "post_id": post_id
            }
    
    async def validate_credentials(self) -> Dict[str, Any]:
        """
        Validate that Facebook credentials are working.
        
        Returns:
            Dictionary with validation status and page info
        """
        try:
            # Try to get page info
            info = await self.get_page_info()
            
            if info.get("success"):
                return {
                    "valid": True,
                    "page_name": info.get("name"),
                    "page_id": self.page_id,
                    "followers": info.get("followers")
                }
            else:
                return {
                    "valid": False,
                    "error": info.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"Facebook credentials validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
