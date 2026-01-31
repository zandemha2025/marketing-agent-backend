"""
Social media publishing services.

Provides integrations with major social platforms:
- Twitter/X (via tweepy)
- LinkedIn (via REST API)
- Instagram (via Graph API for Business/Creator accounts)
- Facebook (via Graph API)

Each service provides:
- Post methods for text, images, and videos
- Delete methods for removing posts
- Metrics/insights retrieval
- Credential validation
- Consistent response format via to_dict() method

Response Format (via to_dict()):
{
    "success": bool,
    "platform": str,
    "post_id": str | None,
    "url": str | None,
    "error": str | None  # Only present on failure
}
"""

from .twitter import TwitterService, TwitterPostResult
from .linkedin import LinkedInService, LinkedInPostResult
from .instagram import InstagramService, InstagramPostResult
from .facebook import FacebookService, FacebookPostResult

__all__ = [
    # Services
    "TwitterService",
    "LinkedInService",
    "InstagramService",
    "FacebookService",
    # Result types
    "TwitterPostResult",
    "LinkedInPostResult",
    "InstagramPostResult",
    "FacebookPostResult",
]
