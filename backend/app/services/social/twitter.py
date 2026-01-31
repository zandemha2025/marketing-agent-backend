"""
Twitter/X API integration for publishing posts.

Uses tweepy library for OAuth 1.0a authentication and API access.
Supports text posts, posts with images, and thread creation.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import tempfile
import httpx

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TwitterPostResult:
    """Result of a Twitter post operation."""
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    text: Optional[str] = None
    error: Optional[str] = None
    platform: str = "twitter"
    
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


class TwitterService:
    """
    Twitter/X publishing service.
    
    Features:
    - Post text-only tweets
    - Post tweets with up to 4 images
    - Post tweets with videos
    - Create tweet threads
    - Track post status and metrics
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
        bearer_token: Optional[str] = None
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token
        
        self._client_v1 = None  # Media upload (v1.1 API)
        self._client_v2 = None  # Posting (v2 API)
        self._http_client = httpx.AsyncClient(timeout=60.0)
        
    def _get_v1_client(self):
        """Get or create Tweepy v1.1 client for media uploads."""
        if not TWEEPY_AVAILABLE:
            raise ImportError("tweepy is required for Twitter integration. Install with: pip install tweepy")
        
        if self._client_v1 is None:
            auth = tweepy.OAuth1UserHandler(
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret
            )
            self._client_v1 = tweepy.API(auth)
        return self._client_v1
    
    def _get_v2_client(self):
        """Get or create Tweepy v2 client for posting tweets."""
        if not TWEEPY_AVAILABLE:
            raise ImportError("tweepy is required for Twitter integration. Install with: pip install tweepy")
        
        if self._client_v2 is None:
            self._client_v2 = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )
        return self._client_v2
    
    async def _download_media(self, media_url: str) -> bytes:
        """Download media from URL."""
        response = await self._http_client.get(media_url)
        response.raise_for_status()
        return response.content
    
    async def _upload_media_v1(self, media_data: bytes, media_type: str = "image") -> Optional[str]:
        """
        Upload media using Twitter v1.1 API.
        
        Args:
            media_data: Raw media bytes
            media_type: 'image' or 'video'
            
        Returns:
            Media ID string for attaching to tweets
        """
        try:
            client = self._get_v1_client()
            
            # Save to temp file for tweepy
            suffix = ".jpg" if media_type == "image" else ".mp4"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(media_data)
                tmp_path = tmp.name
            
            try:
                if media_type == "video":
                    # Videos require chunked upload
                    media = client.media_upload(
                        filename=tmp_path,
                        media_category="tweet_video"
                    )
                else:
                    media = client.media_upload(filename=tmp_path)
                
                return media.media_id_string
            finally:
                Path(tmp_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Failed to upload media to Twitter: {e}")
            return None
    
    async def post_text(
        self,
        text: str,
        reply_to_tweet_id: Optional[str] = None
    ) -> TwitterPostResult:
        """
        Post a text-only tweet.
        
        Args:
            text: Tweet text (max 280 characters for standard, 4000 for Twitter Blue)
            reply_to_tweet_id: Optional tweet ID to reply to
            
        Returns:
            TwitterPostResult with post details
        """
        try:
            client = self._get_v2_client()
            
            # Truncate if needed (Twitter will reject if too long)
            if len(text) > 280:
                logger.warning(f"Tweet text truncated from {len(text)} to 280 characters")
                text = text[:277] + "..."
            
            # Post the tweet
            response = client.create_tweet(
                text=text,
                in_reply_to_tweet_id=reply_to_tweet_id
            )
            
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
            
            logger.info(f"Posted tweet: {tweet_url}")
            
            return TwitterPostResult(
                success=True,
                post_id=tweet_id,
                post_url=tweet_url,
                text=text
            )
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return TwitterPostResult(
                success=False,
                error=str(e),
                text=text
            )
    
    async def post_with_images(
        self,
        text: str,
        image_urls: List[str],
        reply_to_tweet_id: Optional[str] = None
    ) -> TwitterPostResult:
        """
        Post a tweet with images.
        
        Args:
            text: Tweet text
            image_urls: List of image URLs (max 4)
            reply_to_tweet_id: Optional tweet ID to reply to
            
        Returns:
            TwitterPostResult with post details
        """
        try:
            if len(image_urls) > 4:
                return TwitterPostResult(
                    success=False,
                    error="Twitter allows maximum 4 images per tweet",
                    text=text
                )
            
            client = self._get_v2_client()
            
            # Truncate text if needed
            if len(text) > 280:
                text = text[:277] + "..."
            
            # Upload all images
            media_ids = []
            for url in image_urls:
                try:
                    media_data = await self._download_media(url)
                    media_id = await self._upload_media_v1(media_data, "image")
                    if media_id:
                        media_ids.append(media_id)
                except Exception as e:
                    logger.error(f"Failed to upload image {url}: {e}")
            
            if not media_ids:
                # Fall back to text-only if media upload failed
                logger.warning("No images uploaded successfully, posting text only")
                return await self.post_text(text, reply_to_tweet_id)
            
            # Post tweet with media
            response = client.create_tweet(
                text=text,
                media_ids=media_ids,
                in_reply_to_tweet_id=reply_to_tweet_id
            )
            
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
            
            logger.info(f"Posted tweet with {len(media_ids)} images: {tweet_url}")
            
            return TwitterPostResult(
                success=True,
                post_id=tweet_id,
                post_url=tweet_url,
                text=text
            )
            
        except Exception as e:
            logger.error(f"Failed to post tweet with images: {e}")
            return TwitterPostResult(
                success=False,
                error=str(e),
                text=text
            )
    
    async def post_with_video(
        self,
        text: str,
        video_url: str,
        reply_to_tweet_id: Optional[str] = None
    ) -> TwitterPostResult:
        """
        Post a tweet with a video.
        
        Args:
            text: Tweet text
            video_url: URL to video file
            reply_to_tweet_id: Optional tweet ID to reply to
            
        Returns:
            TwitterPostResult with post details
        """
        try:
            client = self._get_v2_client()
            
            # Truncate text if needed
            if len(text) > 280:
                text = text[:277] + "..."
            
            # Download and upload video
            video_data = await self._download_media(video_url)
            media_id = await self._upload_media_v1(video_data, "video")
            
            if not media_id:
                return TwitterPostResult(
                    success=False,
                    error="Failed to upload video",
                    text=text
                )
            
            # Post tweet with video
            response = client.create_tweet(
                text=text,
                media_ids=[media_id],
                in_reply_to_tweet_id=reply_to_tweet_id
            )
            
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
            
            logger.info(f"Posted tweet with video: {tweet_url}")
            
            return TwitterPostResult(
                success=True,
                post_id=tweet_id,
                post_url=tweet_url,
                text=text
            )
            
        except Exception as e:
            logger.error(f"Failed to post tweet with video: {e}")
            return TwitterPostResult(
                success=False,
                error=str(e),
                text=text
            )
    
    async def create_thread(
        self,
        tweets: List[str],
        image_urls: Optional[List[List[str]]] = None
    ) -> List[TwitterPostResult]:
        """
        Create a tweet thread (connected series of tweets).
        
        Args:
            tweets: List of tweet texts
            image_urls: Optional list of image URL lists for each tweet
            
        Returns:
            List of TwitterPostResult for each tweet in the thread
        """
        results = []
        previous_tweet_id = None
        
        for i, text in enumerate(tweets):
            # Get images for this tweet if provided
            tweet_images = None
            if image_urls and i < len(image_urls):
                tweet_images = image_urls[i]
            
            # Post the tweet
            if tweet_images:
                result = await self.post_with_images(
                    text=text,
                    image_urls=tweet_images,
                    reply_to_tweet_id=previous_tweet_id
                )
            else:
                result = await self.post_text(
                    text=text,
                    reply_to_tweet_id=previous_tweet_id
                )
            
            results.append(result)
            
            # If successful, use this tweet ID for the next reply
            if result.success and result.post_id:
                previous_tweet_id = result.post_id
            else:
                # Stop thread if a tweet fails
                logger.error(f"Thread broken at tweet {i+1}: {result.error}")
                break
        
        return results
    
    async def delete_tweet(self, tweet_id: str) -> bool:
        """
        Delete a tweet.
        
        Args:
            tweet_id: ID of tweet to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            client = self._get_v2_client()
            client.delete_tweet(id=tweet_id)
            logger.info(f"Deleted tweet: {tweet_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete tweet {tweet_id}: {e}")
            return False
    
    async def get_tweet_metrics(self, tweet_id: str) -> Dict[str, Any]:
        """
        Get engagement metrics for a tweet.
        
        Args:
            tweet_id: ID of the tweet
            
        Returns:
            Dictionary with metrics (likes, retweets, replies, impressions)
        """
        try:
            client = self._get_v2_client()
            
            tweet = client.get_tweet(
                id=tweet_id,
                tweet_fields=["public_metrics", "non_public_metrics"]
            )
            
            metrics = tweet.data.public_metrics if tweet.data else {}
            
            return {
                "success": True,
                "tweet_id": tweet_id,
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "quotes": metrics.get("quote_count", 0),
                "impressions": metrics.get("impression_count", 0),
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics for tweet {tweet_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tweet_id": tweet_id
            }
    
    async def validate_credentials(self) -> Dict[str, Any]:
        """
        Validate that Twitter credentials are working.
        
        Returns:
            Dictionary with validation status and user info
        """
        try:
            client = self._get_v2_client()
            me = client.get_me(user_fields=["username", "name", "verified"])
            
            return {
                "valid": True,
                "username": me.data.username if me.data else None,
                "name": me.data.name if me.data else None,
                "verified": me.data.verified if me.data else False,
            }
        except Exception as e:
            logger.error(f"Twitter credentials validation failed: {e}")
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
