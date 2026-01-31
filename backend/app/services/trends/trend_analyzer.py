"""
TrendMaster - AI-Powered Trend Analyzer

Analyzes trends for:
- Relevance to brand/industry
- Content opportunities
- Predicted longevity
- Recommended actions
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json

from ..ai.openrouter import OpenRouterService
from .trend_scanner import TrendItem, TrendSource, TrendScanner

logger = logging.getLogger(__name__)


@dataclass
class TrendAnalysis:
    """Analysis result for a trend."""
    trend_id: str
    relevance_score: float  # 0-100
    opportunity_score: float  # 0-100
    longevity: str  # "short", "medium", "long"
    content_ideas: List[str] = field(default_factory=list)
    recommended_platforms: List[str] = field(default_factory=list)
    key_angles: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trend_id": self.trend_id,
            "relevance_score": self.relevance_score,
            "opportunity_score": self.opportunity_score,
            "longevity": self.longevity,
            "content_ideas": self.content_ideas,
            "recommended_platforms": self.recommended_platforms,
            "key_angles": self.key_angles,
            "risks": self.risks,
            "summary": self.summary
        }


# Legacy dataclasses for backward compatibility with existing API
@dataclass
class TrendSourceLegacy:
    """A source where a trend was detected (legacy format)."""
    name: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    engagement_score: int = 0


@dataclass
class TrendPrediction:
    """Prediction about a trend's lifecycle."""
    phase: str  # "emerging", "growth", "peak", "decline"
    confidence: float  # 0.0 - 1.0
    estimated_peak: Optional[datetime] = None
    longevity_days: int = 30
    growth_rate: float = 0.0


@dataclass
class TrendAnalysisLegacy:
    """Complete analysis of a trend (legacy format for existing API)."""
    title: str
    description: str
    category: str
    keywords: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    sources: List[TrendSourceLegacy] = field(default_factory=list)
    source_count: int = 0
    prediction: Optional[TrendPrediction] = None
    relevance_score: int = 0
    audience_match: List[str] = field(default_factory=list)
    content_opportunities: List[str] = field(default_factory=list)
    related_trends: List[str] = field(default_factory=list)
    geographic_scope: str = "global"
    industry_impact: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


class TrendAnalyzer:
    """AI-powered trend analysis service."""
    
    def __init__(self, openrouter_api_key: Optional[str] = None):
        self._api_key = openrouter_api_key
        self._ai = None
        self._scanner = None
        
        # Initialize from settings if no key provided
        if not self._api_key:
            try:
                from ...core.config import get_settings
                settings = get_settings()
                self._api_key = settings.openrouter_api_key
            except Exception:
                pass
    
    @property
    def ai(self) -> Optional[OpenRouterService]:
        """Lazy initialization of AI service."""
        if self._ai is None and self._api_key:
            self._ai = OpenRouterService(self._api_key)
        return self._ai
    
    @property
    def scanner(self) -> TrendScanner:
        """Lazy initialization of trend scanner."""
        if self._scanner is None:
            try:
                from ...core.config import get_settings
                settings = get_settings()
                self._scanner = TrendScanner(
                    newsapi_key=getattr(settings, 'newsapi_api_key', None),
                    reddit_client_id=getattr(settings, 'reddit_client_id', None),
                    reddit_client_secret=getattr(settings, 'reddit_client_secret', None)
                )
            except Exception:
                self._scanner = TrendScanner()
        return self._scanner
    
    async def analyze_trend(
        self,
        trend: TrendItem,
        brand_context: Optional[Dict[str, Any]] = None
    ) -> TrendAnalysis:
        """
        Analyze a single trend for marketing opportunities.
        
        Args:
            trend: The trend to analyze
            brand_context: Optional brand info for relevance scoring
            
        Returns:
            TrendAnalysis with scores and recommendations
        """
        # Build context
        brand_info = ""
        if brand_context:
            brand_info = f"""
Brand Context:
- Industry: {brand_context.get('industry', 'Unknown')}
- Target Audience: {', '.join(brand_context.get('audiences', []))}
- Brand Voice: {brand_context.get('voice', 'Professional')}
- Key Topics: {', '.join(brand_context.get('topics', []))}
"""
        
        prompt = f"""Analyze this trend for marketing opportunities:

Trend: {trend.title}
Description: {trend.description}
Source: {trend.source.value}
Category: {trend.category}
{brand_info}

Provide analysis in this exact JSON format:
{{
    "relevance_score": <0-100 based on brand fit>,
    "opportunity_score": <0-100 based on content potential>,
    "longevity": "<short|medium|long>",
    "content_ideas": ["idea1", "idea2", "idea3"],
    "recommended_platforms": ["platform1", "platform2"],
    "key_angles": ["angle1", "angle2"],
    "risks": ["risk1", "risk2"],
    "summary": "<2-3 sentence summary of the opportunity>"
}}

Return ONLY valid JSON, no other text."""

        try:
            if not self.ai:
                raise ValueError("AI service not configured")
                
            response = await self.ai.complete(
                prompt=prompt,
                system="You are a marketing trend analyst. Analyze trends and provide actionable insights in JSON format.",
                temperature=0.3
            )
            
            # Parse JSON response
            # Clean response - remove markdown code blocks if present
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            
            data = json.loads(clean_response)
            
            return TrendAnalysis(
                trend_id=trend.id,
                relevance_score=data.get("relevance_score", 50),
                opportunity_score=data.get("opportunity_score", 50),
                longevity=data.get("longevity", "medium"),
                content_ideas=data.get("content_ideas", []),
                recommended_platforms=data.get("recommended_platforms", []),
                key_angles=data.get("key_angles", []),
                risks=data.get("risks", []),
                summary=data.get("summary", "")
            )
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            # Return default analysis
            return TrendAnalysis(
                trend_id=trend.id,
                relevance_score=50,
                opportunity_score=50,
                longevity="medium",
                content_ideas=["Create informative content about this topic"],
                recommended_platforms=["LinkedIn", "Twitter"],
                key_angles=["Industry perspective"],
                risks=["Trend may be short-lived"],
                summary=f"This trend about '{trend.title}' may present content opportunities."
            )
    
    async def analyze_batch(
        self,
        trends: List[TrendItem],
        brand_context: Optional[Dict[str, Any]] = None,
        top_n: int = 5
    ) -> List[TrendAnalysis]:
        """
        Analyze multiple trends and return top opportunities.
        
        Args:
            trends: List of trends to analyze
            brand_context: Optional brand info
            top_n: Number of top trends to return
            
        Returns:
            List of analyzed trends sorted by opportunity score
        """
        analyses = []
        
        # Analyze top trends by initial score
        sorted_trends = sorted(trends, key=lambda t: t.score, reverse=True)[:top_n * 2]
        
        for trend in sorted_trends:
            analysis = await self.analyze_trend(trend, brand_context)
            analyses.append(analysis)
        
        # Sort by combined score and return top N
        analyses.sort(
            key=lambda a: (a.relevance_score + a.opportunity_score) / 2,
            reverse=True
        )
        
        return analyses[:top_n]
    
    async def generate_trend_report(
        self,
        trends: List[TrendItem],
        analyses: List[TrendAnalysis],
        brand_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a comprehensive trend report."""
        
        trend_summaries = "\n".join([
            f"- {t.title} (Score: {t.score:.0f})" for t in trends[:10]
        ])
        
        analysis_summaries = "\n".join([
            f"- {a.summary}" for a in analyses[:5]
        ])
        
        prompt = f"""Generate a marketing trend report based on this data:

Top Trends:
{trend_summaries}

Key Analyses:
{analysis_summaries}

Brand Context: {brand_context or 'General marketing'}

Write a professional 3-paragraph trend report covering:
1. Overview of current trends
2. Top opportunities for content creation
3. Recommended actions for the next week"""

        try:
            if not self.ai:
                raise ValueError("AI service not configured")
                
            report = await self.ai.complete(
                prompt=prompt,
                system="You are a marketing strategist writing trend reports.",
                temperature=0.5
            )
            return report
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return "Unable to generate trend report at this time."
    
    # Legacy methods for backward compatibility with existing API
    async def analyze_trends(
        self,
        industry: str,
        keywords: Optional[List[str]] = None,
        organization_context: Optional[Dict[str, Any]] = None
    ) -> List[TrendAnalysisLegacy]:
        """
        Analyze trends for an industry with AI-powered insights.
        Legacy method for backward compatibility.
        
        Args:
            industry: The industry to analyze
            keywords: Optional keywords to focus on
            organization_context: Organization's brand data for relevance scoring
            
        Returns:
            List of analyzed trends with predictions
        """
        logger.info(f"Analyzing trends for industry: {industry}")
        
        # Scan for trends using the scanner
        trend_items = await self.scanner.scan_all_sources(
            keywords=keywords or [industry],
            limit=20
        )
        
        # If no trends from APIs, log warning and return empty list
        # Don't silently use mock data - let the caller know no real data is available
        if not trend_items:
            logger.warning(
                f"No trends found for industry '{industry}'. "
                "This may indicate missing API keys (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
                "NEWSAPI_KEY, GOOGLE_TRENDS_API_KEY) or network issues. "
                "Returning empty trend list instead of mock data."
            )
            return []
        
        # Analyze each trend
        analyzed_trends = []
        for trend_item in trend_items[:10]:  # Limit to top 10
            try:
                analysis = await self._analyze_trend_legacy(
                    trend_item,
                    industry,
                    organization_context
                )
                if analysis:
                    analyzed_trends.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing trend '{trend_item.title}': {e}")
                continue
        
        # Sort by relevance score
        analyzed_trends.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return analyzed_trends
    
    async def _analyze_trend_legacy(
        self,
        trend_item: TrendItem,
        industry: str,
        organization_context: Optional[Dict[str, Any]] = None
    ) -> Optional[TrendAnalysisLegacy]:
        """Analyze a single trend and return legacy format."""
        if not self.ai:
            return self._create_basic_analysis_legacy(trend_item, industry)
        
        try:
            org_context = ""
            if organization_context:
                brand_name = organization_context.get("name", "")
                brand_description = organization_context.get("description", "")
                org_context = f"""
                Organization Context:
                - Name: {brand_name}
                - Description: {brand_description}
                - Industry: {industry}
                """
            
            prompt = f"""
            Analyze this trend for a {industry} company:
            
            Trend Title: {trend_item.title}
            Description: {trend_item.description}
            Category: {trend_item.category}
            Source: {trend_item.source.value}
            Score: {trend_item.score}
            
            {org_context}
            
            Provide a comprehensive analysis in this JSON format:
            {{
                "keywords": ["keyword1", "keyword2", "keyword3"],
                "sentiment": "positive|negative|neutral|mixed",
                "sentiment_score": 0.7,
                "prediction": {{
                    "phase": "emerging|growth|peak|decline",
                    "confidence": 0.85,
                    "longevity_days": 45,
                    "growth_rate": 15.5
                }},
                "relevance_score": 85,
                "audience_match": ["audience_segment_1", "audience_segment_2"],
                "content_opportunities": [
                    "Specific content idea 1",
                    "Specific content idea 2"
                ],
                "related_trends": ["related trend 1", "related trend 2"],
                "geographic_scope": "global|regional|local",
                "industry_impact": ["impact area 1", "impact area 2"]
            }}
            
            Be specific and actionable. Return ONLY valid JSON.
            """
            
            response = await self.ai.complete(
                prompt=prompt,
                system="You are a trend analysis expert. Analyze trends and predict their lifecycle with high accuracy.",
                temperature=0.3,
                json_mode=True
            )
            
            analysis_data = json.loads(response)
            
            # Build sources list
            sources = [
                TrendSourceLegacy(
                    name=trend_item.source.value,
                    url=trend_item.url,
                    engagement_score=int(trend_item.score)
                )
            ]
            
            prediction_data = analysis_data.get("prediction", {})
            prediction = TrendPrediction(
                phase=prediction_data.get("phase", "emerging"),
                confidence=prediction_data.get("confidence", 0.5),
                longevity_days=prediction_data.get("longevity_days", 30),
                growth_rate=prediction_data.get("growth_rate", 0.0)
            )
            
            return TrendAnalysisLegacy(
                title=trend_item.title,
                description=trend_item.description,
                category=trend_item.category,
                keywords=analysis_data.get("keywords", []),
                sentiment=analysis_data.get("sentiment", "neutral"),
                sentiment_score=analysis_data.get("sentiment_score", 0.0),
                sources=sources,
                source_count=1,
                prediction=prediction,
                relevance_score=analysis_data.get("relevance_score", 50),
                audience_match=analysis_data.get("audience_match", []),
                content_opportunities=analysis_data.get("content_opportunities", []),
                related_trends=analysis_data.get("related_trends", []),
                geographic_scope=analysis_data.get("geographic_scope", "global"),
                industry_impact=analysis_data.get("industry_impact", [])
            )
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._create_basic_analysis_legacy(trend_item, industry)
    
    def _create_basic_analysis_legacy(
        self,
        trend_item: TrendItem,
        industry: str
    ) -> TrendAnalysisLegacy:
        """Create a basic analysis without AI (legacy format)."""
        sources = [
            TrendSourceLegacy(
                name=trend_item.source.value,
                url=trend_item.url,
                engagement_score=int(trend_item.score)
            )
        ]
        
        # Calculate basic relevance based on score
        relevance = min(100, int(trend_item.score))
        
        return TrendAnalysisLegacy(
            title=trend_item.title,
            description=trend_item.description,
            category=trend_item.category,
            keywords=[],
            sentiment="neutral",
            sentiment_score=0.0,
            sources=sources,
            source_count=1,
            prediction=TrendPrediction(
                phase="emerging",
                confidence=0.5,
                longevity_days=30,
                growth_rate=5.0
            ),
            relevance_score=relevance,
            audience_match=[],
            content_opportunities=[
                f"Create content about {trend_item.title}"
            ],
            related_trends=[],
            geographic_scope="global",
            industry_impact=[industry]
        )
    
    def _get_mock_analyzed_trends(self, industry: str) -> List[TrendAnalysisLegacy]:
        """Generate mock analyzed trends for development."""
        return [
            TrendAnalysisLegacy(
                title=f"AI Transformation in {industry}",
                description="Companies are rapidly adopting AI to transform operations.",
                category="Technology",
                keywords=["AI", "automation", "digital transformation"],
                sentiment="positive",
                sentiment_score=0.8,
                sources=[TrendSourceLegacy(name="TechCrunch", engagement_score=95)],
                source_count=1,
                prediction=TrendPrediction(
                    phase="growth",
                    confidence=0.85,
                    longevity_days=180,
                    growth_rate=25.0
                ),
                relevance_score=92,
                audience_match=["Business Leaders", "Tech Professionals"],
                content_opportunities=[
                    "How AI is reshaping the industry",
                    "Case studies of successful AI adoption"
                ],
                related_trends=["Machine Learning", "Automation"],
                geographic_scope="global",
                industry_impact=["Operations", "Customer Service"]
            ),
            TrendAnalysisLegacy(
                title="Sustainability Focus",
                description="Consumers demanding eco-friendly practices.",
                category="Consumer Behavior",
                keywords=["sustainability", "eco-friendly", "green"],
                sentiment="positive",
                sentiment_score=0.7,
                sources=[TrendSourceLegacy(name="Forbes", engagement_score=88)],
                source_count=1,
                prediction=TrendPrediction(
                    phase="growth",
                    confidence=0.9,
                    longevity_days=365,
                    growth_rate=15.0
                ),
                relevance_score=85,
                audience_match=["Millennials", "Gen Z"],
                content_opportunities=[
                    "Sustainability initiatives showcase",
                    "Green practices guide"
                ],
                related_trends=["ESG", "Climate Action"],
                geographic_scope="global",
                industry_impact=["Supply Chain", "Marketing"]
            )
        ]
    
    async def generate_content_from_trend(
        self,
        trend: TrendAnalysisLegacy,
        content_type: str,
        brand_voice: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate content based on a trend.
        Legacy method for backward compatibility.
        
        Args:
            trend: The trend to create content from
            content_type: Type of content (blog, social, email, etc.)
            brand_voice: Brand voice guidelines
            
        Returns:
            Generated content with metadata
        """
        if not self.ai:
            raise NotImplementedError(
                "Content generation requires AI service. "
                "Configure OPENROUTER_API_KEY in environment to enable AI-powered content generation. "
                "See: https://openrouter.ai/docs for API setup."
            )
        
        voice_guidelines = ""
        if brand_voice:
            tone = ", ".join(brand_voice.get("tone", ["professional"]))
            personality = brand_voice.get("personality", "")
            vocabulary = ", ".join(brand_voice.get("vocabulary", []))
            voice_guidelines = f"""
            Brand Voice Guidelines:
            - Tone: {tone}
            - Personality: {personality}
            - Preferred vocabulary: {vocabulary}
            """
        
        prompt = f"""
        Create a {content_type} based on this trend:
        
        Trend: {trend.title}
        Description: {trend.description}
        Keywords: {', '.join(trend.keywords)}
        Sentiment: {trend.sentiment}
        
        {voice_guidelines}
        
        Generate content that:
        1. Connects the trend to the brand's perspective
        2. Provides value to the audience
        3. Includes a clear call-to-action
        4. Uses appropriate tone and vocabulary
        
        Return JSON:
        {{
            "title": "Compelling title",
            "content": "Full content text",
            "suggested_hashtags": ["tag1", "tag2"],
            "tone": "description of tone used",
            "cta": "call to action text",
            "target_audience": "primary audience for this content"
        }}
        """
        
        try:
            response = await self.ai.complete(
                prompt=prompt,
                system="You are a content strategist who creates engaging, on-brand content. Always return valid JSON with properly escaped strings.",
                temperature=0.7,
                json_mode=True
            )
            
            # Sanitize the response to handle control characters
            # Replace literal newlines in string values with escaped newlines
            import re
            
            # First try direct parsing
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Try to fix common JSON issues from AI responses
                # Replace unescaped newlines within strings
                sanitized = response.strip()
                
                # Remove any markdown code blocks if present
                if sanitized.startswith("```"):
                    sanitized = re.sub(r'^```(?:json)?\s*', '', sanitized)
                    sanitized = re.sub(r'\s*```$', '', sanitized)
                
                # Try parsing again
                try:
                    return json.loads(sanitized)
                except json.JSONDecodeError:
                    # Last resort: use strict=False to allow control characters
                    return json.loads(sanitized, strict=False)
                    
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return {
                "title": f"Content about {trend.title}",
                "content": f"Error generating content: {str(e)}",
                "suggested_hashtags": trend.keywords[:5],
                "tone": "professional",
                "cta": None,
                "target_audience": None
            }
    
    async def close(self):
        """Close any open connections."""
        if self._ai:
            await self._ai.close()
