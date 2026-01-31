"""
LinkedIn API integration for publishing posts.

Uses LinkedIn REST API v2 for sharing content to personal profiles and company pages.
Supports text posts, posts with images, and posts with links.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import httpx
import base64
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_UPLOAD_BASE = "https://api.linkedin.com/v2/assets"


@dataclass
class LinkedInPostResult:
    """Result of a LinkedIn post operation."""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None
    platform: str = "linkedin"
    
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


class LinkedInService:
    """
    LinkedIn publishing service.
    
    Features:
    - Post text updates to personal profile
    - Post to company pages
    - Post with images (up to 9)
    - Post with article links
    - Rich media posts
    """
    
    def __init__(
        self,
        access_token: str,
        person_urn: Optional[str] = None,
        organization_urn: Optional[str] = None
    ):
        self.access_token = access_token
        self.person_urn = person_urn
        self.organization_urn = organization_urn
        self._http_client = httpx.AsyncClient(
            base_url=LINKEDIN_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            },
            timeout=60.0
        )
    
    def _get_author_urn(self, use_organization: bool = False) -> str:
        """Get the URN for posting (person or organization)."""
        if use_organization and self.organization_urn:
            return self.organization_urn
        if not self.person_urn:
            raise ValueError("No person URN configured. Call get_profile_urn() first or provide person_urn.")
        return self.person_urn
    
    async def get_profile_urn(self) -> Optional[str]:
        """
        Get the current user's person URN.
        
        Returns:
            Person URN string or None if failed
        """
        try:
            response = await self._http_client.get("/me")
            response.raise_for_status()
            data = response.json()
            
            # Extract URN from ID
            person_id = data.get("id")
            if person_id:
                self.person_urn = f"urn:li:person:{person_id}"
                return self.person_urn
            return None
            
        except Exception as e:
            logger.error(f"Failed to get LinkedIn profile URN: {e}")
            return None
    
    async def get_organization_urns(self) -> List[Dict[str, str]]:
        """
        Get list of organizations the user can post to.
        
        Returns:
            List of organization dicts with 'urn' and 'name'
        """
        try:
            # Get organization memberships
            response = await self._http_client.get(
                "/organizationalEntityAcls",
                params={"q": "roleAssignee", "role": "ADMINISTRATOR"}
            )
            response.raise_for_status()
            data = response.json()
            
            organizations = []
            for element in data.get("elements", []):
                org_urn = element.get("organizationalTarget")
                if org_urn:
                    # Get org details
                    org_id = org_urn.split(":")[-1]
                    org_response = await self._http_client.get(
                        f"/organizations/{org_id}",
                        params={"projection": "(id,localizedName)"}
                    )
                    if org_response.status_code == 200:
                        org_data = org_response.json()
                        organizations.append({
                            "urn": org_urn,
                            "id": org_id,
                            "name": org_data.get("localizedName", "Unknown")
                        })
            
            return organizations
            
        except Exception as e:
            logger.error(f"Failed to get LinkedIn organizations: {e}")
            return []
    
    async def _upload_image(self, image_data: bytes, image_name: str = "image.jpg") -> Optional[str]:
        """
        Upload an image to LinkedIn for use in a post.
        
        Args:
            image_data: Raw image bytes
            image_name: Name of the image file
            
        Returns:
            Asset URN for the uploaded image
        """
        try:
            # Step 1: Register upload
            register_payload = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": self._get_author_urn(),
                    "serviceRelationships": [{
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }]
                }
            }
            
            response = await self._http_client.post(
                "/assets?action=registerUpload",
                json=register_payload
            )
            response.raise_for_status()
            register_data = response.json()
            
            upload_url = register_data["value"]["uploadMechanism"][
                "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
            ]["uploadUrl"]
            asset_urn = register_data["value"]["asset"]
            
            # Step 2: Upload the image
            upload_response = await self._http_client.post(
                upload_url,
                content=image_data,
                headers={"Content-Type": "application/octet-stream"}
            )
            upload_response.raise_for_status()
            
            return asset_urn
            
        except Exception as e:
            logger.error(f"Failed to upload image to LinkedIn: {e}")
            return None
    
    async def _download_media(self, media_url: str) -> bytes:
        """Download media from URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(media_url, timeout=60.0)
            response.raise_for_status()
            return response.content
    
    async def post_text(
        self,
        text: str,
        use_organization: bool = False
    ) -> LinkedInPostResult:
        """
        Post a text-only update to LinkedIn.
        
        Args:
            text: Post text content
            use_organization: Whether to post as organization
            
        Returns:
            LinkedInPostResult with post details
        """
        try:
            author_urn = self._get_author_urn(use_organization)
            
            # LinkedIn has a 3000 character limit for posts
            if len(text) > 3000:
                logger.warning(f"LinkedIn post truncated from {len(text)} to 3000 characters")
                text = text[:2997] + "..."
            
            payload = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = await self._http_client.post("/ugcPosts", json=payload)
            response.raise_for_status()
            
            # Extract post ID from response
            post_urn = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
            if not post_urn:
                # Try to get from response body
                post_urn = response.json().get("id")
            
            post_url = None
            if post_urn:
                # Convert URN to web URL
                post_id = post_urn.split(":")[-1] if ":" in post_urn else post_urn
                if use_organization and self.organization_urn:
                    org_id = self.organization_urn.split(":")[-1]
                    post_url = f"https://www.linkedin.com/feed/update/{post_urn}"
                else:
                    post_url = f"https://www.linkedin.com/feed/update/{post_urn}"
            
            logger.info(f"Posted to LinkedIn: {post_url}")
            
            return LinkedInPostResult(
                success=True,
                post_id=post_urn,
                post_url=post_url,
                text=text
            )
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e, 'response') else str(e)
            logger.error(f"LinkedIn API error: {error_detail}")
            return LinkedInPostResult(
                success=False,
                error=f"LinkedIn API error: {error_detail}",
                text=text
            )
        except Exception as e:
            logger.error(f"Failed to post to LinkedIn: {e}")
            return LinkedInPostResult(
                success=False,
                error=str(e),
                text=text
            )
    
    async def post_with_images(
        self,
        text: str,
        image_urls: List[str],
        use_organization: bool = False
    ) -> LinkedInPostResult:
        """
        Post an update with images to LinkedIn.
        
        Args:
            text: Post text content
            image_urls: List of image URLs (max 9 for LinkedIn)
            use_organization: Whether to post as organization
            
        Returns:
            LinkedInPostResult with post details
        """
        try:
            if len(image_urls) > 9:
                return LinkedInPostResult(
                    success=False,
                    error="LinkedIn allows maximum 9 images per post",
                    text=text
                )
            
            author_urn = self._get_author_urn(use_organization)
            
            # Truncate text if needed
            if len(text) > 3000:
                text = text[:2997] + "..."
            
            # Upload all images
            media_assets = []
            for i, url in enumerate(image_urls):
                try:
                    image_data = await self._download_media(url)
                    asset_urn = await self._upload_image(image_data, f"image_{i}.jpg")
                    if asset_urn:
                        media_assets.append({
                            "status": "READY",
                            "media": asset_urn
                        })
                except Exception as e:
                    logger.error(f"Failed to upload image {url}: {e}")
            
            if not media_assets:
                # Fall back to text-only
                logger.warning("No images uploaded successfully, posting text only")
                return await self.post_text(text, use_organization)
            
            payload = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "IMAGE",
                        "media": media_assets
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = await self._http_client.post("/ugcPosts", json=payload)
            response.raise_for_status()
            
            post_urn = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
            post_url = f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else None
            
            logger.info(f"Posted to LinkedIn with {len(media_assets)} images: {post_url}")
            
            return LinkedInPostResult(
                success=True,
                post_id=post_urn,
                post_url=post_url,
                text=text
            )
            
        except Exception as e:
            logger.error(f"Failed to post to LinkedIn with images: {e}")
            return LinkedInPostResult(
                success=False,
                error=str(e),
                text=text
            )
    
    async def post_with_link(
        self,
        text: str,
        link_url: str,
        link_title: Optional[str] = None,
        link_description: Optional[str] = None,
        link_image_url: Optional[str] = None,
        use_organization: bool = False
    ) -> LinkedInPostResult:
        """
        Post an update with a link preview to LinkedIn.
        
        Args:
            text: Post text content
            link_url: URL to share
            link_title: Optional custom title
            link_description: Optional custom description
            link_image_url: Optional custom thumbnail image
            use_organization: Whether to post as organization
            
        Returns:
            LinkedInPostResult with post details
        """
        try:
            author_urn = self._get_author_urn(use_organization)
            
            if len(text) > 3000:
                text = text[:2997] + "..."
            
            # Build media content for link
            media_content = {
                "status": "READY",
                "originalUrl": link_url
            }
            
            if link_title:
                media_content["title"] = {"text": link_title}
            if link_description:
                media_content["description"] = {"text": link_description}
            if link_image_url:
                # Upload thumbnail image
                try:
                    image_data = await self._download_media(link_image_url)
                    asset_urn = await self._upload_image(image_data, "thumbnail.jpg")
                    if asset_urn:
                        media_content["thumbnails"] = [{"resolvedUrl": link_image_url}]
                except Exception as e:
                    logger.warning(f"Failed to upload link thumbnail: {e}")
            
            payload = {
                "author": author_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "ARTICLE",
                        "media": [media_content]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = await self._http_client.post("/ugcPosts", json=payload)
            response.raise_for_status()
            
            post_urn = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
            post_url = f"https://www.linkedin.com/feed/update/{post_urn}" if post_urn else None
            
            logger.info(f"Posted to LinkedIn with link: {post_url}")
            
            return LinkedInPostResult(
                success=True,
                post_id=post_urn,
                post_url=post_url,
                text=text
            )
            
        except Exception as e:
            logger.error(f"Failed to post to LinkedIn with link: {e}")
            return LinkedInPostResult(
                success=False,
                error=str(e),
                text=text
            )
    
    async def delete_post(self, post_urn: str) -> bool:
        """
        Delete a LinkedIn post.
        
        Args:
            post_urn: URN of the post to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            response = await self._http_client.delete(f"/ugcPosts/{post_urn}")
            response.raise_for_status()
            logger.info(f"Deleted LinkedIn post: {post_urn}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete LinkedIn post {post_urn}: {e}")
            return False
    
    async def get_post_metrics(self, post_urn: str) -> Dict[str, Any]:
        """
        Get engagement metrics for a LinkedIn post.
        
        Args:
            post_urn: URN of the post
            
        Returns:
            Dictionary with metrics
        """
        try:
            # Get social actions (likes, comments)
            response = await self._http_client.get(
                f"/socialActions/{post_urn}",
                params={"projection": "(likesSummary,commentsSummary)"}
            )
            response.raise_for_status()
            data = response.json()
            
            likes = data.get("likesSummary", {}).get("totalLikes", 0)
            comments = data.get("commentsSummary", {}).get("totalComments", 0)
            
            return {
                "success": True,
                "post_urn": post_urn,
                "likes": likes,
                "comments": comments,
                # Note: LinkedIn doesn't provide impression data via API for UGC posts
                "impressions": None
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics for LinkedIn post {post_urn}: {e}")
            return {
                "success": False,
                "error": str(e),
                "post_urn": post_urn
            }
    
    async def validate_credentials(self) -> Dict[str, Any]:
        """
        Validate that LinkedIn credentials are working.
        
        Returns:
            Dictionary with validation status and profile info
        """
        try:
            # Get current user profile
            response = await self._http_client.get(
                "/me",
                params={"projection": "(id,firstName,lastName,profilePicture)"}
            )
            response.raise_for_status()
            data = response.json()
            
            first_name = data.get("firstName", {}).get("localized", {}).get("en_US", "")
            last_name = data.get("lastName", {}).get("localized", {}).get("en_US", "")
            
            # Get email
            email_response = await self._http_client.get(
                "/emailAddress",
                params={"q": "members", "projection": "(elements*(handle~))"}
            )
            email_data = email_response.json() if email_response.status_code == 200 else {}
            email = None
            elements = email_data.get("elements", [])
            if elements:
                email = elements[0].get("handle~", {}).get("emailAddress")
            
            return {
                "valid": True,
                "id": data.get("id"),
                "name": f"{first_name} {last_name}".strip(),
                "email": email
            }
            
        except Exception as e:
            logger.error(f"LinkedIn credentials validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
