"""
TrendMaster - Multi-Source Trend Scanner

Scans multiple sources for trending topics:
- NewsAPI for news trends
- Google Trends for search trends
- Reddit for social trends
- Twitter/X for real-time trends
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TrendSource(str, Enum):
    NEWS_API = "newsapi"
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    TWITTER = "twitter"


@dataclass
class TrendItem:
    """Represents a single trend item."""
    id: str
    title: str
    description: str
    source: TrendSource
    category: str
    score: float  # 0-100 relevance score
    url: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source": self.source.value,
            "category": self.category,
            "score": self.score,
            "url": self.url,
            "image_url": self.image_url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "metadata": self.metadata
        }


class TrendScanner:
    """Multi-source trend scanner service."""
    
    def __init__(
        self,
        newsapi_key: Optional[str] = None,
        reddit_client_id: Optional[str] = None,
        reddit_client_secret: Optional[str] = None
    ):
        self.newsapi_key = newsapi_key
        self.reddit_client_id = reddit_client_id
        self.reddit_client_secret = reddit_client_secret
        self._reddit_token = None
    
    async def scan_all_sources(
        self,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[TrendItem]:
        """
        Scan all available sources for trends.
        
        Args:
            keywords: Optional keywords to filter trends
            categories: Optional categories to focus on
            limit: Maximum trends per source
            
        Returns:
            Combined list of trends from all sources
        """
        all_trends = []
        
        # Scan each source
        if self.newsapi_key:
            news_trends = await self.scan_newsapi(keywords, categories, limit)
            all_trends.extend(news_trends)
        
        if self.reddit_client_id:
            reddit_trends = await self.scan_reddit(keywords, limit)
            all_trends.extend(reddit_trends)
        
        # Sort by score and return
        all_trends.sort(key=lambda t: t.score, reverse=True)
        return all_trends
    
    async def scan_newsapi(
        self,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[TrendItem]:
        """Scan NewsAPI for trending news."""
        if not self.newsapi_key:
            return []
        
        trends = []
        
        try:
            async with httpx.AsyncClient() as client:
                # Build query
                params = {
                    "apiKey": self.newsapi_key,
                    "language": "en",
                    "sortBy": "popularity",
                    "pageSize": limit
                }
                
                if keywords:
                    params["q"] = " OR ".join(keywords)
                else:
                    # Get top headlines
                    params["country"] = "us"
                
                endpoint = "https://newsapi.org/v2/top-headlines" if not keywords else "https://newsapi.org/v2/everything"
                
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()
                
                for i, article in enumerate(data.get("articles", [])):
                    trends.append(TrendItem(
                        id=f"news_{i}_{hash(article.get('title', ''))}",
                        title=article.get("title", ""),
                        description=article.get("description", ""),
                        source=TrendSource.NEWS_API,
                        category=self._categorize_article(article),
                        score=self._calculate_news_score(article, i, limit),
                        url=article.get("url"),
                        image_url=article.get("urlToImage"),
                        published_at=datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")) if article.get("publishedAt") else None,
                        metadata={
                            "source_name": article.get("source", {}).get("name"),
                            "author": article.get("author")
                        }
                    ))
                    
        except Exception as e:
            logger.error(f"NewsAPI scan failed: {e}")
        
        return trends
    
    async def scan_reddit(
        self,
        keywords: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[TrendItem]:
        """Scan Reddit for trending posts."""
        if not self.reddit_client_id:
            return []
        
        trends = []
        
        try:
            # Get Reddit access token
            token = await self._get_reddit_token()
            if not token:
                return []
            
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "MarketingAgent/1.0"
                }
                
                # Subreddits to scan for marketing trends
                subreddits = ["marketing", "socialmedia", "digital_marketing", "advertising", "business"]
                
                for subreddit in subreddits:
                    response = await client.get(
                        f"https://oauth.reddit.com/r/{subreddit}/hot",
                        headers=headers,
                        params={"limit": limit // len(subreddits)}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        for post in data.get("data", {}).get("children", []):
                            post_data = post.get("data", {})
                            
                            # Filter by keywords if provided
                            if keywords:
                                title_lower = post_data.get("title", "").lower()
                                if not any(kw.lower() in title_lower for kw in keywords):
                                    continue
                            
                            trends.append(TrendItem(
                                id=f"reddit_{post_data.get('id')}",
                                title=post_data.get("title", ""),
                                description=post_data.get("selftext", "")[:500],
                                source=TrendSource.REDDIT,
                                category=subreddit,
                                score=self._calculate_reddit_score(post_data),
                                url=f"https://reddit.com{post_data.get('permalink')}",
                                image_url=post_data.get("thumbnail") if post_data.get("thumbnail", "").startswith("http") else None,
                                published_at=datetime.fromtimestamp(post_data.get("created_utc", 0)),
                                metadata={
                                    "subreddit": subreddit,
                                    "upvotes": post_data.get("ups"),
                                    "comments": post_data.get("num_comments"),
                                    "author": post_data.get("author")
                                }
                            ))
                            
        except Exception as e:
            logger.error(f"Reddit scan failed: {e}")
        
        return trends
    
    async def scan_trends(self, industry: str) -> List[Dict[str, Any]]:
        """
        Legacy method for backward compatibility with existing API.
        Scans for trends in a specific industry.
        
        Args:
            industry: The industry to scan trends for
            
        Returns:
            List of trend dictionaries
        """
        logger.info(f"Scanning trends for industry: {industry}")
        
        # Use industry as keyword for scanning
        keywords = [industry]
        
        # Scan all available sources
        trend_items = await self.scan_all_sources(keywords=keywords, limit=20)
        
        # If no trends found from APIs, log warning and return empty list
        # Don't silently use mock data - let the caller know no real data is available
        if not trend_items:
            logger.warning(
                f"No trends found for industry '{industry}'. "
                "This may indicate missing API keys (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
                "NEWSAPI_KEY, GOOGLE_TRENDS_API_KEY) or network issues. "
                "Returning empty trend list instead of mock data."
            )
            return []
        
        # Convert TrendItem objects to dictionaries for legacy API
        return [
            {
                "title": item.title,
                "description": item.description,
                "category": item.category,
                "score": int(item.score),
                "source": item.source.value,
                "url": item.url
            }
            for item in trend_items
        ]
    
    async def _get_reddit_token(self) -> Optional[str]:
        """Get Reddit OAuth token."""
        if self._reddit_token:
            return self._reddit_token
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.reddit.com/api/v1/access_token",
                    auth=(self.reddit_client_id, self.reddit_client_secret),
                    data={"grant_type": "client_credentials"},
                    headers={"User-Agent": "MarketingAgent/1.0"}
                )
                response.raise_for_status()
                self._reddit_token = response.json().get("access_token")
                return self._reddit_token
        except Exception as e:
            logger.error(f"Failed to get Reddit token: {e}")
            return None
    
    def _categorize_article(self, article: Dict[str, Any]) -> str:
        """Categorize an article based on content."""
        title = (article.get("title", "") + " " + article.get("description", "")).lower()
        
        categories = {
            "technology": ["tech", "ai", "software", "digital", "app", "startup"],
            "business": ["business", "market", "economy", "finance", "stock"],
            "marketing": ["marketing", "brand", "advertising", "campaign", "social media"],
            "lifestyle": ["lifestyle", "health", "wellness", "fashion", "food"],
            "entertainment": ["entertainment", "movie", "music", "celebrity", "game"]
        }
        
        for category, keywords in categories.items():
            if any(kw in title for kw in keywords):
                return category
        
        return "general"
    
    def _calculate_news_score(self, article: Dict[str, Any], position: int, total: int) -> float:
        """Calculate relevance score for news article."""
        # Position-based score (earlier = higher)
        position_score = (total - position) / total * 50
        
        # Recency score
        recency_score = 30
        if article.get("publishedAt"):
            try:
                pub_date = datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
                hours_old = (datetime.now(pub_date.tzinfo) - pub_date).total_seconds() / 3600
                recency_score = max(0, 30 - hours_old)
            except Exception:
                pass
        
        # Content quality score
        quality_score = 20
        if article.get("description") and len(article["description"]) > 100:
            quality_score = 20
        elif article.get("description"):
            quality_score = 10
        else:
            quality_score = 5
        
        return min(100, position_score + recency_score + quality_score)
    
    def _calculate_reddit_score(self, post: Dict[str, Any]) -> float:
        """Calculate relevance score for Reddit post."""
        upvotes = post.get("ups", 0)
        comments = post.get("num_comments", 0)
        
        # Engagement score
        engagement = min(50, (upvotes / 100) * 25 + (comments / 50) * 25)
        
        # Recency score
        created = post.get("created_utc", 0)
        hours_old = (datetime.now().timestamp() - created) / 3600
        recency = max(0, 30 - hours_old)
        
        # Content score
        content = 20 if len(post.get("selftext", "")) > 200 else 10
        
        return min(100, engagement + recency + content)
    
    def _get_mock_trends(self, industry: str) -> List[Dict[str, Any]]:
        """Return mock trends if API fails."""
        return [
            {
                "title": f"AI in {industry}",
                "description": "Increasing adoption of artificial intelligence for automation.",
                "category": "Technology",
                "score": 95,
                "source": "TechCrunch",
                "url": None
            },
            {
                "title": "Sustainability Focus",
                "description": "Consumers demanding eco-friendly practices.",
                "category": "Consumer Behavior",
                "score": 88,
                "source": "Forbes",
                "url": None
            },
            {
                "title": "Remote Work Impact",
                "description": "How distributed teams are changing the landscape.",
                "category": "Workplace",
                "score": 82,
                "source": "HBR",
                "url": None
            }
        ]


# Create a default scanner instance for backward compatibility
def _create_default_scanner() -> TrendScanner:
    """Create a default scanner with settings from config."""
    try:
        from ...core.config import get_settings
        settings = get_settings()
        return TrendScanner(
            newsapi_key=getattr(settings, 'newsapi_api_key', None),
            reddit_client_id=getattr(settings, 'reddit_client_id', None),
            reddit_client_secret=getattr(settings, 'reddit_client_secret', None)
        )
    except Exception:
        return TrendScanner()


trend_scanner = _create_default_scanner()
