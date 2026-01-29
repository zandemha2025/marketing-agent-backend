"""
Onboarding Pipeline Orchestrator.

This is the heart of the "magical onboarding" experience.
It orchestrates all research services to build a comprehensive
knowledge base for each new client.
"""
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from .firecrawl import FirecrawlService, CrawlResult
from .perplexity import PerplexityService, MarketResearchResult

logger = logging.getLogger(__name__)


class OnboardingStage(str, Enum):
    """Stages of the onboarding pipeline."""
    INITIALIZING = "initializing"
    CRAWLING_WEBSITE = "crawling_website"
    ANALYZING_BRAND = "analyzing_brand"
    RESEARCHING_MARKET = "researching_market"
    RESEARCHING_AUDIENCE = "researching_audience"
    SYNTHESIZING = "synthesizing"
    GENERATING_PROFILE = "generating_profile"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class OnboardingProgress:
    """Current progress of onboarding."""
    stage: OnboardingStage
    progress: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class OnboardingResult:
    """Complete result of the onboarding pipeline."""
    success: bool
    organization_id: str
    domain: str

    # Raw research data
    crawl_result: Optional[CrawlResult] = None
    market_research: Optional[MarketResearchResult] = None

    # Synthesized knowledge base data
    brand_data: Dict[str, Any] = field(default_factory=dict)
    market_data: Dict[str, Any] = field(default_factory=dict)
    audiences_data: Dict[str, Any] = field(default_factory=dict)
    offerings_data: Dict[str, Any] = field(default_factory=dict)
    context_data: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    duration_seconds: float = 0.0
    pages_analyzed: int = 0
    error: Optional[str] = None


# Type for progress callback
ProgressCallback = Callable[[OnboardingProgress], Awaitable[None]]


class OnboardingPipeline:
    """
    Orchestrates the complete onboarding research pipeline.

    Flow:
    1. Initialize with domain
    2. Crawl website with Firecrawl
    3. Analyze brand elements from crawled data
    4. Research market with Perplexity (competitors, trends)
    5. Research audience segments
    6. Synthesize all data into knowledge base format
    7. Generate client profile for presentation

    Usage:
        pipeline = OnboardingPipeline(
            firecrawl_api_key="...",
            perplexity_api_key="..."
        )

        async for progress in pipeline.run("acme.com", "org_123"):
            print(f"{progress.stage}: {progress.progress:.0%} - {progress.message}")

        result = pipeline.result
    """

    def __init__(
        self,
        firecrawl_api_key: Optional[str] = None,
        perplexity_api_key: Optional[str] = None,
        claude_api_key: Optional[str] = None,  # For synthesis
        max_pages: int = 50
    ):
        self.firecrawl = FirecrawlService(api_key=firecrawl_api_key)
        self.perplexity = PerplexityService(api_key=perplexity_api_key)
        self.claude_api_key = claude_api_key
        self.max_pages = max_pages

        self.result: Optional[OnboardingResult] = None
        self._current_progress = OnboardingProgress(
            stage=OnboardingStage.INITIALIZING,
            progress=0.0,
            message="Waiting to start"
        )

    async def run(
        self,
        domain: str,
        organization_id: str,
        on_progress: Optional[ProgressCallback] = None
    ) -> OnboardingResult:
        """
        Run the complete onboarding pipeline.

        Args:
            domain: Client's domain to research
            organization_id: ID of the organization being onboarded
            on_progress: Optional callback for progress updates

        Returns:
            OnboardingResult with all research data
        """
        start_time = datetime.now()

        # Initialize result
        self.result = OnboardingResult(
            success=False,
            organization_id=organization_id,
            domain=domain
        )

        try:
            # Stage 1: Initialize
            await self._update_progress(
                OnboardingStage.INITIALIZING,
                0.05,
                f"Preparing to analyze {domain}",
                on_progress
            )

            # Stage 2: Crawl website
            crawl_result = await self._crawl_website(domain, on_progress)
            self.result.crawl_result = crawl_result
            self.result.pages_analyzed = crawl_result.pages_crawled

            # Extract company name from crawl
            company_name = self._extract_company_name(crawl_result)

            # Stage 3: Analyze brand
            brand_analysis = await self._analyze_brand(crawl_result, on_progress)

            # Stage 4-5: Research market (runs in parallel with audience)
            market_research = await self._research_market(
                company_name, domain, on_progress
            )
            self.result.market_research = market_research

            # Stage 6: Synthesize all data
            await self._synthesize_data(
                crawl_result, brand_analysis, market_research, on_progress
            )

            # Stage 7: Generate profile
            await self._generate_profile(on_progress)

            # Mark complete
            self.result.success = True
            self.result.duration_seconds = (datetime.now() - start_time).total_seconds()

            await self._update_progress(
                OnboardingStage.COMPLETE,
                1.0,
                f"Research complete! Analyzed {self.result.pages_analyzed} pages.",
                on_progress,
                completed=True
            )

        except Exception as e:
            logger.error(f"Onboarding pipeline failed: {e}")
            self.result.error = str(e)
            await self._update_progress(
                OnboardingStage.FAILED,
                self._current_progress.progress,
                f"Research failed: {str(e)}",
                on_progress,
                error=str(e)
            )

        finally:
            # Cleanup
            await self.firecrawl.close()
            await self.perplexity.close()

        return self.result

    async def _update_progress(
        self,
        stage: OnboardingStage,
        progress: float,
        message: str,
        callback: Optional[ProgressCallback],
        details: Dict[str, Any] = None,
        completed: bool = False,
        error: Optional[str] = None
    ):
        """Update and broadcast progress."""
        self._current_progress = OnboardingProgress(
            stage=stage,
            progress=progress,
            message=message,
            details=details or {},
            started_at=self._current_progress.started_at or datetime.now(),
            completed_at=datetime.now() if completed else None,
            error=error
        )

        if callback:
            try:
                await callback(self._current_progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    async def _crawl_website(
        self,
        domain: str,
        on_progress: Optional[ProgressCallback]
    ) -> CrawlResult:
        """Crawl the website using Firecrawl."""
        await self._update_progress(
            OnboardingStage.CRAWLING_WEBSITE,
            0.1,
            f"Crawling {domain}...",
            on_progress
        )

        async def crawl_progress(stage: str, progress: float, message: str):
            # Map crawl progress to overall progress (10% - 35%)
            overall_progress = 0.1 + (progress * 0.25)
            await self._update_progress(
                OnboardingStage.CRAWLING_WEBSITE,
                overall_progress,
                message,
                on_progress
            )

        result = await self.firecrawl.crawl_website(
            domain,
            max_pages=self.max_pages,
            on_progress=crawl_progress
        )

        return result

    def _extract_company_name(self, crawl_result: CrawlResult) -> str:
        """Extract company name from crawl data."""
        # Try to find it in brand elements
        if crawl_result.brand_elements.get("site_name"):
            return crawl_result.brand_elements["site_name"]

        # Try from home page title
        for page in crawl_result.pages:
            if page.page_type == "home" and page.title:
                # Usually format is "Company Name - Tagline" or "Company Name | Product"
                name = page.title.split(" - ")[0].split(" | ")[0].strip()
                if name and len(name) < 50:
                    return name

        # Fall back to domain
        return crawl_result.domain.replace(".com", "").replace("www.", "").title()

    async def _analyze_brand(
        self,
        crawl_result: CrawlResult,
        on_progress: Optional[ProgressCallback]
    ) -> Dict[str, Any]:
        """Analyze brand elements from crawled data."""
        await self._update_progress(
            OnboardingStage.ANALYZING_BRAND,
            0.4,
            "Analyzing brand identity...",
            on_progress
        )

        # Extract brand elements
        brand = crawl_result.brand_elements

        # Extract additional elements from page content
        home_page = next(
            (p for p in crawl_result.pages if p.page_type == "home"),
            crawl_result.pages[0] if crawl_result.pages else None
        )
        about_page = next(
            (p for p in crawl_result.pages if p.page_type == "about"),
            None
        )

        analysis = {
            "name": self._extract_company_name(crawl_result),
            "domain": crawl_result.domain,
            "logo_candidates": brand.get("logo_candidates", []),
            "tagline_candidates": brand.get("tagline_candidates", []),
            "key_phrases": brand.get("key_phrases", []),
            "home_page_content": home_page.content[:5000] if home_page else "",
            "about_page_content": about_page.content[:5000] if about_page else "",
            "headings": [],
            "structured_data": {}
        }

        # Gather all headings
        for page in crawl_result.pages:
            analysis["headings"].extend(page.headings)

        # Gather structured data
        for page in crawl_result.pages:
            if page.structured_data:
                analysis["structured_data"].update(page.structured_data)

        await self._update_progress(
            OnboardingStage.ANALYZING_BRAND,
            0.45,
            "Brand elements extracted",
            on_progress
        )

        return analysis

    async def _research_market(
        self,
        company_name: str,
        domain: str,
        on_progress: Optional[ProgressCallback]
    ) -> MarketResearchResult:
        """Research market using Perplexity."""
        await self._update_progress(
            OnboardingStage.RESEARCHING_MARKET,
            0.5,
            "Researching competitors and market trends...",
            on_progress
        )

        async def research_progress(stage: str, progress: float, message: str):
            # Map research progress to overall progress (50% - 75%)
            overall_progress = 0.5 + (progress * 0.25)
            await self._update_progress(
                OnboardingStage.RESEARCHING_MARKET,
                overall_progress,
                message,
                on_progress
            )

        result = await self.perplexity.research_market(
            company_name,
            domain,
            on_progress=research_progress
        )

        return result

    async def _synthesize_data(
        self,
        crawl_result: CrawlResult,
        brand_analysis: Dict[str, Any],
        market_research: MarketResearchResult,
        on_progress: Optional[ProgressCallback]
    ):
        """Synthesize all research into knowledge base format."""
        await self._update_progress(
            OnboardingStage.SYNTHESIZING,
            0.8,
            "Synthesizing research findings...",
            on_progress
        )

        # Build brand data
        self.result.brand_data = {
            "name": brand_analysis.get("name", ""),
            "domain": brand_analysis.get("domain", ""),
            "tagline": (
                brand_analysis.get("tagline_candidates", [""])[0]
                if brand_analysis.get("tagline_candidates")
                else ""
            ),
            "description": self._extract_description(crawl_result, brand_analysis),
            "visual_identity": {
                "logo_url": (
                    brand_analysis.get("logo_candidates", [""])[0]
                    if brand_analysis.get("logo_candidates")
                    else ""
                ),
                "primary_color": None,  # Would extract from CSS if available
                "secondary_colors": [],
                "fonts": {},
                "image_style": ""
            },
            "voice": {
                "tone": self._infer_tone(brand_analysis),
                "personality": "",
                "vocabulary": brand_analysis.get("key_phrases", [])[:10],
                "avoid": [],
                "sample_phrases": []
            },
            "values": self._extract_values(brand_analysis),
            "mission": self._extract_mission(brand_analysis)
        }

        # Build market data
        self.result.market_data = {
            "industry": market_research.industry,
            "competitors": [
                {
                    "name": c.name,
                    "domain": c.domain,
                    "strengths": c.strengths,
                    "weaknesses": c.weaknesses,
                    "positioning": c.positioning,
                    "key_differentiators": c.key_differentiators
                }
                for c in market_research.competitors
            ],
            "trends": [
                {
                    "trend": t.trend,
                    "relevance": t.relevance,
                    "opportunity": t.opportunity
                }
                for t in market_research.trends
            ],
            "market_position": market_research.market_position,
            "opportunities": market_research.opportunities,
            "threats": market_research.threats
        }

        # Build audience data
        self.result.audiences_data = {
            "segments": [
                {
                    "name": s.segment_name,
                    "size": "primary" if i == 0 else "secondary",
                    "demographics": s.demographics,
                    "psychographics": s.psychographics,
                    "pain_points": s.pain_points,
                    "goals": s.goals,
                    "preferred_channels": s.preferred_channels,
                    "content_preferences": s.content_preferences
                }
                for i, s in enumerate(market_research.audience_insights)
            ]
        }

        # Build offerings data (from crawled product pages)
        self.result.offerings_data = self._extract_offerings(crawl_result)

        # Build context data
        self.result.context_data = {
            "social_presence": self._extract_social_presence(crawl_result),
            "recent_news": market_research.news,
            "sentiment": {
                "overall": self._calculate_sentiment(market_research.news),
                "score": 0.7  # Default positive
            }
        }

        await self._update_progress(
            OnboardingStage.SYNTHESIZING,
            0.9,
            "Research synthesized",
            on_progress
        )

    def _extract_description(
        self,
        crawl_result: CrawlResult,
        brand_analysis: Dict[str, Any]
    ) -> str:
        """Extract company description from crawl data."""
        # Try structured data first
        structured = brand_analysis.get("structured_data", {})
        if structured.get("description"):
            return structured["description"]

        # Try about page
        if brand_analysis.get("about_page_content"):
            content = brand_analysis["about_page_content"]
            # Take first paragraph
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if paragraphs:
                return paragraphs[0][:500]

        # Try home page
        if brand_analysis.get("home_page_content"):
            content = brand_analysis["home_page_content"]
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if paragraphs:
                return paragraphs[0][:500]

        return ""

    def _infer_tone(self, brand_analysis: Dict[str, Any]) -> List[str]:
        """Infer brand tone from content."""
        # Simple heuristic - would use Claude for better analysis
        key_phrases = brand_analysis.get("key_phrases", [])

        tone = []
        if any(w in key_phrases for w in ["innovative", "cutting-edge", "future"]):
            tone.append("innovative")
        if any(w in key_phrases for w in ["trusted", "reliable", "secure"]):
            tone.append("trustworthy")
        if any(w in key_phrases for w in ["simple", "easy", "effortless"]):
            tone.append("approachable")
        if any(w in key_phrases for w in ["expert", "professional", "enterprise"]):
            tone.append("professional")

        return tone or ["professional"]

    def _extract_values(self, brand_analysis: Dict[str, Any]) -> List[str]:
        """Extract brand values from analysis."""
        # Would use Claude for better extraction
        key_phrases = brand_analysis.get("key_phrases", [])
        value_words = ["innovation", "quality", "trust", "customer", "sustainability"]
        return [w for w in key_phrases if w in value_words][:5]

    def _extract_mission(self, brand_analysis: Dict[str, Any]) -> str:
        """Extract mission statement if available."""
        # Would search for explicit mission statements
        return ""

    def _extract_offerings(self, crawl_result: CrawlResult) -> Dict[str, Any]:
        """Extract products/services from crawled pages."""
        products = []
        services = []

        for page in crawl_result.pages:
            if page.page_type == "product":
                # Extract product info from page
                products.append({
                    "name": page.title,
                    "description": page.description,
                    "url": page.url
                })

        return {
            "products": products,
            "services": services,
            "key_differentiators": []
        }

    def _extract_social_presence(self, crawl_result: CrawlResult) -> Dict[str, Any]:
        """Extract social media presence from crawled data."""
        social = {}

        # Look for social links in all pages
        social_patterns = {
            "twitter": ["twitter.com", "x.com"],
            "linkedin": ["linkedin.com"],
            "facebook": ["facebook.com"],
            "instagram": ["instagram.com"],
            "youtube": ["youtube.com"]
        }

        for page in crawl_result.pages:
            for link in page.links:
                for platform, patterns in social_patterns.items():
                    if any(p in link for p in patterns):
                        social[platform] = {"url": link}

        return social

    def _calculate_sentiment(self, news: List[Dict[str, str]]) -> str:
        """Calculate overall sentiment from news."""
        if not news:
            return "neutral"

        sentiments = [n.get("sentiment", "neutral") for n in news]
        positive = sentiments.count("positive")
        negative = sentiments.count("negative")

        if positive > negative:
            return "positive"
        elif negative > positive:
            return "negative"
        return "neutral"

    async def _generate_profile(self, on_progress: Optional[ProgressCallback]):
        """Generate the final client profile for presentation."""
        await self._update_progress(
            OnboardingStage.GENERATING_PROFILE,
            0.95,
            "Generating your brand profile...",
            on_progress
        )

        # The profile is already built in synthesize_data
        # This stage is for any final polish or Claude-powered summary

        await self._update_progress(
            OnboardingStage.GENERATING_PROFILE,
            0.98,
            "Profile ready",
            on_progress
        )

    @property
    def current_progress(self) -> OnboardingProgress:
        """Get current progress."""
        return self._current_progress


# Convenience function for simple usage
async def run_onboarding(
    domain: str,
    organization_id: str,
    firecrawl_api_key: Optional[str] = None,
    perplexity_api_key: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None
) -> OnboardingResult:
    """
    Run the complete onboarding pipeline for a domain.

    Args:
        domain: Client's website domain
        organization_id: ID of the organization
        firecrawl_api_key: Firecrawl API key (optional)
        perplexity_api_key: Perplexity API key (optional)
        on_progress: Progress callback

    Returns:
        OnboardingResult with all research data
    """
    pipeline = OnboardingPipeline(
        firecrawl_api_key=firecrawl_api_key,
        perplexity_api_key=perplexity_api_key
    )
    return await pipeline.run(domain, organization_id, on_progress)
