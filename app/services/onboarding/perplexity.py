"""
Perplexity integration for market intelligence.

Perplexity is used to:
1. Research competitors and market landscape
2. Identify industry trends and opportunities
3. Find target audience insights
4. Gather recent news and sentiment
5. Discover content strategies that work
"""
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import httpx
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CompetitorProfile:
    """Profile of a competitor."""
    name: str
    domain: str
    description: str
    strengths: List[str]
    weaknesses: List[str]
    positioning: str
    key_differentiators: List[str]
    target_audience: str
    pricing_model: str
    social_presence: Dict[str, str]


@dataclass
class MarketTrend:
    """A market trend or insight."""
    trend: str
    description: str
    relevance: str  # high, medium, low
    opportunity: str
    sources: List[str]


@dataclass
class AudienceInsight:
    """Insight about a target audience segment."""
    segment_name: str
    demographics: Dict[str, Any]
    psychographics: Dict[str, Any]
    pain_points: List[str]
    goals: List[str]
    preferred_channels: List[str]
    content_preferences: List[str]


@dataclass
class MarketResearchResult:
    """Complete market research result."""
    company_name: str
    industry: str
    competitors: List[CompetitorProfile] = field(default_factory=list)
    trends: List[MarketTrend] = field(default_factory=list)
    audience_insights: List[AudienceInsight] = field(default_factory=list)
    news: List[Dict[str, str]] = field(default_factory=list)
    market_position: str = ""
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)


class PerplexityService:
    """
    Market intelligence using Perplexity API.

    Perplexity excels at synthesizing information from multiple
    sources to provide comprehensive market analysis.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.perplexity.ai"
    ):
        self.api_key = api_key
        self.base_url = base_url
        # Explicitly disable proxy to avoid SOCKS proxy issues in sandboxed environments
        self.client = httpx.AsyncClient(timeout=120.0, proxy=None)

    async def research_market(
        self,
        company_name: str,
        domain: str,
        industry_hint: Optional[str] = None,
        on_progress: Optional[callable] = None
    ) -> MarketResearchResult:
        """
        Conduct comprehensive market research for a company.

        Args:
            company_name: Name of the company to research
            domain: Company's domain
            industry_hint: Optional hint about the industry
            on_progress: Callback for progress updates

        Returns:
            MarketResearchResult with all findings
        """
        result = MarketResearchResult(
            company_name=company_name,
            industry=industry_hint or "Unknown"
        )

        if on_progress:
            await on_progress("market_research", 0.0, "Starting market research")

        # Research tasks to run in parallel
        tasks = [
            self._research_competitors(company_name, domain, industry_hint),
            self._research_trends(company_name, domain, industry_hint),
            self._research_audience(company_name, domain, industry_hint),
            self._research_news(company_name, domain),
        ]

        # Execute research in parallel
        if self.api_key:
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                if not isinstance(results[0], Exception):
                    result.competitors, result.market_position = results[0]
                if not isinstance(results[1], Exception):
                    result.trends, result.opportunities, result.threats = results[1]
                if not isinstance(results[2], Exception):
                    result.audience_insights = results[2]
                if not isinstance(results[3], Exception):
                    result.news = results[3]

                # Determine industry if not provided
                if not industry_hint and result.competitors:
                    result.industry = await self._determine_industry(
                        company_name, domain, result.competitors
                    )

            except Exception as e:
                logger.error(f"Perplexity research failed: {e}")
                # Fall back to mock data for development
                result = await self._get_mock_research(company_name, domain)
        else:
            # Use mock data for development without API key
            result = await self._get_mock_research(company_name, domain)

        if on_progress:
            await on_progress("market_research", 1.0, "Market research complete")

        return result

    async def _query_perplexity(
        self,
        query: str,
        system_prompt: str = "You are a market research analyst."
    ) -> str:
        """Make a query to Perplexity API."""
        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-sonar-large-128k-online",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.2,
                "return_citations": True
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _research_competitors(
        self,
        company_name: str,
        domain: str,
        industry: Optional[str]
    ) -> tuple[List[CompetitorProfile], str]:
        """Research competitors in the market."""
        industry_str = f"in the {industry} industry" if industry else ""

        query = f"""
        Research the main competitors of {company_name} ({domain}) {industry_str}.

        For each competitor, provide:
        1. Company name and domain
        2. Brief description
        3. Key strengths (3-5 points)
        4. Key weaknesses (2-3 points)
        5. Market positioning
        6. Key differentiators
        7. Target audience
        8. Pricing model (if known)

        Also analyze {company_name}'s position relative to these competitors.

        Format your response as JSON with this structure:
        {{
            "competitors": [
                {{
                    "name": "...",
                    "domain": "...",
                    "description": "...",
                    "strengths": ["...", "..."],
                    "weaknesses": ["...", "..."],
                    "positioning": "...",
                    "key_differentiators": ["...", "..."],
                    "target_audience": "...",
                    "pricing_model": "..."
                }}
            ],
            "market_position": "Analysis of {company_name}'s position..."
        }}
        """

        result = await self._query_perplexity(
            query,
            "You are a competitive intelligence analyst. Respond only with valid JSON."
        )

        # Parse JSON response
        try:
            data = self._extract_json(result)
            competitors = [
                CompetitorProfile(
                    name=c.get("name", ""),
                    domain=c.get("domain", ""),
                    description=c.get("description", ""),
                    strengths=c.get("strengths", []),
                    weaknesses=c.get("weaknesses", []),
                    positioning=c.get("positioning", ""),
                    key_differentiators=c.get("key_differentiators", []),
                    target_audience=c.get("target_audience", ""),
                    pricing_model=c.get("pricing_model", ""),
                    social_presence=c.get("social_presence", {})
                )
                for c in data.get("competitors", [])
            ]
            return competitors, data.get("market_position", "")
        except Exception as e:
            logger.error(f"Error parsing competitor data: {e}")
            return [], ""

    async def _research_trends(
        self,
        company_name: str,
        domain: str,
        industry: Optional[str]
    ) -> tuple[List[MarketTrend], List[str], List[str]]:
        """Research market trends and opportunities."""
        industry_str = industry or "their industry"

        query = f"""
        Research current market trends, opportunities, and threats for {company_name}
        ({domain}) in {industry_str}.

        Identify:
        1. Top 5 market trends affecting this space
        2. Key opportunities for growth
        3. Potential threats to be aware of

        Format as JSON:
        {{
            "trends": [
                {{
                    "trend": "Name of trend",
                    "description": "Detailed description",
                    "relevance": "high/medium/low",
                    "opportunity": "How this creates opportunity"
                }}
            ],
            "opportunities": ["Opportunity 1", "Opportunity 2"],
            "threats": ["Threat 1", "Threat 2"]
        }}
        """

        result = await self._query_perplexity(
            query,
            "You are a market trends analyst. Respond only with valid JSON."
        )

        try:
            data = self._extract_json(result)
            trends = [
                MarketTrend(
                    trend=t.get("trend", ""),
                    description=t.get("description", ""),
                    relevance=t.get("relevance", "medium"),
                    opportunity=t.get("opportunity", ""),
                    sources=t.get("sources", [])
                )
                for t in data.get("trends", [])
            ]
            return trends, data.get("opportunities", []), data.get("threats", [])
        except Exception as e:
            logger.error(f"Error parsing trends data: {e}")
            return [], [], []

    async def _research_audience(
        self,
        company_name: str,
        domain: str,
        industry: Optional[str]
    ) -> List[AudienceInsight]:
        """Research target audience segments."""
        industry_context = f"operating in {industry}" if industry else ""

        query = f"""
        Research the target audience for {company_name} ({domain}) {industry_context}.

        CRITICAL: You MUST identify exactly 2-3 distinct audience segments.
        Consider:
        - Who PAYS for the product? (decision makers, budget holders)
        - Who USES the product? (end users, implementers)
        - What SIZE companies? (startups, SMBs, enterprise)

        For EACH segment provide:
        1. Segment name (descriptive, e.g., "Startup Technical Founders" not just "Users")
        2. Demographics (age range, job titles, company size, industries, geography)
        3. Psychographics (values, motivations, priorities)
        4. Pain points (at least 3 specific challenges they face)
        5. Goals (at least 3 things they want to achieve)
        6. Preferred channels (LinkedIn, Twitter, Email, YouTube, etc.)
        7. Content preferences (case studies, tutorials, webinars, etc.)

        Format as JSON:
        {{
            "segments": [
                {{
                    "segment_name": "Descriptive Segment Name",
                    "demographics": {{
                        "age_range": "25-45",
                        "job_titles": ["CTO", "VP Engineering", "Tech Lead"],
                        "company_size": "10-500 employees",
                        "industries": ["SaaS", "Technology"],
                        "geography": "Global, primarily US and Europe"
                    }},
                    "psychographics": {{
                        "values": ["efficiency", "innovation", "reliability"],
                        "motivations": ["scale their business", "stay competitive"],
                        "priorities": ["time to market", "cost efficiency"]
                    }},
                    "pain_points": ["specific pain 1", "specific pain 2", "specific pain 3"],
                    "goals": ["goal 1", "goal 2", "goal 3"],
                    "preferred_channels": ["LinkedIn", "Twitter", "Tech blogs"],
                    "content_preferences": ["Technical documentation", "Case studies", "Webinars"]
                }}
            ]
        }}

        IMPORTANT: You MUST return at least 2 complete segments. Never return an empty array.
        """

        result = await self._query_perplexity(
            query,
            "You are an audience research analyst. You MUST respond with valid JSON containing 2-3 audience segments."
        )

        try:
            data = self._extract_json(result)
            segments = [
                AudienceInsight(
                    segment_name=s.get("segment_name", ""),
                    demographics=s.get("demographics", {}),
                    psychographics=s.get("psychographics", {}),
                    pain_points=s.get("pain_points", []),
                    goals=s.get("goals", []),
                    preferred_channels=s.get("preferred_channels", []),
                    content_preferences=s.get("content_preferences", [])
                )
                for s in data.get("segments", [])
            ]

            # If we still got no segments, return default segments
            if not segments:
                segments = self._get_default_audience_segments(company_name, industry)

            return segments
        except Exception as e:
            logger.error(f"Error parsing audience data: {e}")
            return self._get_default_audience_segments(company_name, industry)

    def _get_default_audience_segments(
        self,
        company_name: str,
        industry: Optional[str]
    ) -> List[AudienceInsight]:
        """Return default audience segments when research fails."""
        return [
            AudienceInsight(
                segment_name="Business Decision Makers",
                demographics={
                    "age_range": "30-50",
                    "job_titles": ["CEO", "CMO", "VP", "Director"],
                    "company_size": "50-500 employees",
                    "industries": ["Technology", "Professional Services"],
                    "geography": "North America, Europe"
                },
                psychographics={
                    "values": ["ROI", "efficiency", "innovation"],
                    "motivations": ["grow revenue", "reduce costs", "stay competitive"],
                    "priorities": ["business outcomes", "team productivity"]
                },
                pain_points=[
                    "Limited time to evaluate solutions",
                    "Need to demonstrate ROI to stakeholders",
                    "Integration with existing tools"
                ],
                goals=[
                    "Find solutions that deliver measurable results",
                    "Streamline operations",
                    "Enable team growth"
                ],
                preferred_channels=["LinkedIn", "Email", "Industry events"],
                content_preferences=["Case studies", "ROI calculators", "Executive summaries"]
            ),
            AudienceInsight(
                segment_name="End Users & Implementers",
                demographics={
                    "age_range": "25-40",
                    "job_titles": ["Manager", "Specialist", "Analyst", "Coordinator"],
                    "company_size": "10-500 employees",
                    "industries": ["Various"],
                    "geography": "Global"
                },
                psychographics={
                    "values": ["ease of use", "reliability", "support"],
                    "motivations": ["do job better", "save time", "impress leadership"],
                    "priorities": ["daily workflow", "learning curve"]
                },
                pain_points=[
                    "Complex tools that are hard to learn",
                    "Lack of training resources",
                    "Poor customer support"
                ],
                goals=[
                    "Master tools quickly",
                    "Improve personal productivity",
                    "Deliver better results"
                ],
                preferred_channels=["YouTube", "Twitter", "Online communities"],
                content_preferences=["Tutorials", "How-to guides", "Video demos"]
            )
        ]

    async def _research_news(
        self,
        company_name: str,
        domain: str
    ) -> List[Dict[str, str]]:
        """Research recent news about the company."""
        query = f"""
        Find the most recent news and announcements about {company_name} ({domain})
        from the past 6 months.

        Include:
        - Major product launches or updates
        - Funding announcements
        - Partnership news
        - Company milestones
        - Press coverage

        Format as JSON:
        {{
            "news": [
                {{
                    "title": "...",
                    "date": "YYYY-MM-DD",
                    "summary": "...",
                    "source": "...",
                    "sentiment": "positive/neutral/negative"
                }}
            ]
        }}
        """

        result = await self._query_perplexity(
            query,
            "You are a news researcher. Respond only with valid JSON."
        )

        try:
            data = self._extract_json(result)
            return data.get("news", [])
        except Exception as e:
            logger.error(f"Error parsing news data: {e}")
            return []

    async def _determine_industry(
        self,
        company_name: str,
        domain: str,
        competitors: List[CompetitorProfile]
    ) -> str:
        """Determine the industry based on company and competitor info."""
        competitor_names = ", ".join([c.name for c in competitors[:5]]) if competitors else "general competitors"

        query = f"""
        Analyze {company_name} ({domain}) and determine its PRIMARY industry.

        {"Known competitors: " + competitor_names if competitors else ""}

        IMPORTANT: You MUST provide a specific industry classification.
        Common industry categories include:
        - Financial Technology (Fintech) / Payment Processing
        - E-commerce / Retail Technology
        - SaaS / Software as a Service
        - Healthcare Technology
        - Marketing Technology (MarTech)
        - Human Resources Technology (HRTech)
        - Enterprise Software
        - Developer Tools
        - Cybersecurity
        - Artificial Intelligence / Machine Learning
        - Cloud Infrastructure
        - Education Technology (EdTech)
        - Real Estate Technology (PropTech)

        Based on what this company does, respond with ONLY the industry name.
        Be specific (e.g., "Financial Technology - Payment Processing" not just "Technology").

        NEVER respond with "Unknown" - always make your best assessment.
        """

        try:
            result = await self._query_perplexity(query)
            industry = result.strip().strip('"').strip("'")

            # Validate we got a real answer
            if not industry or industry.lower() in ["unknown", "n/a", "not available", "unclear"]:
                # Try to infer from domain
                industry = self._infer_industry_from_domain(domain)

            return industry
        except Exception as e:
            logger.error(f"Error determining industry: {e}")
            return self._infer_industry_from_domain(domain)

    def _infer_industry_from_domain(self, domain: str) -> str:
        """Infer industry from domain name as a last resort."""
        domain_lower = domain.lower()

        # Common domain patterns
        patterns = {
            "pay": "Financial Technology - Payments",
            "stripe": "Financial Technology - Payment Processing",
            "shop": "E-commerce / Retail",
            "health": "Healthcare Technology",
            "med": "Healthcare Technology",
            "edu": "Education Technology",
            "learn": "Education Technology",
            "hr": "Human Resources Technology",
            "recruit": "Human Resources Technology",
            "market": "Marketing Technology",
            "ad": "Advertising Technology",
            "cloud": "Cloud Infrastructure",
            "secure": "Cybersecurity",
            "cyber": "Cybersecurity",
            "ai": "Artificial Intelligence",
            "data": "Data & Analytics",
            "crm": "Customer Relationship Management",
            "erp": "Enterprise Software",
            "dev": "Developer Tools",
            "code": "Developer Tools",
        }

        for pattern, industry in patterns.items():
            if pattern in domain_lower:
                return industry

        return "Technology / Software"  # Better than "Unknown"

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from a text response."""
        # Try to find JSON in the response
        import re

        # Look for JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try to find raw JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        # Try parsing the whole response
        return json.loads(text)

    async def _get_mock_research(
        self,
        company_name: str,
        domain: str
    ) -> MarketResearchResult:
        """Generate mock research data for development."""
        return MarketResearchResult(
            company_name=company_name,
            industry="Technology / SaaS",
            competitors=[
                CompetitorProfile(
                    name="Competitor A",
                    domain="competitor-a.com",
                    description="Market leader in the space with established brand.",
                    strengths=[
                        "Strong brand recognition",
                        "Large customer base",
                        "Comprehensive feature set"
                    ],
                    weaknesses=[
                        "Higher pricing",
                        "Slower innovation cycle"
                    ],
                    positioning="Premium enterprise solution",
                    key_differentiators=["Enterprise support", "Security certifications"],
                    target_audience="Enterprise companies",
                    pricing_model="Annual subscription",
                    social_presence={"linkedin": "competitor-a", "twitter": "@competitora"}
                ),
                CompetitorProfile(
                    name="Competitor B",
                    domain="competitor-b.com",
                    description="Fast-growing startup with modern approach.",
                    strengths=[
                        "Modern UI/UX",
                        "Competitive pricing",
                        "Fast iteration"
                    ],
                    weaknesses=[
                        "Limited integrations",
                        "Smaller team"
                    ],
                    positioning="Modern alternative for growing teams",
                    key_differentiators=["AI-powered features", "Simple pricing"],
                    target_audience="SMBs and startups",
                    pricing_model="Monthly subscription",
                    social_presence={"linkedin": "competitor-b", "twitter": "@competitorb"}
                ),
            ],
            trends=[
                MarketTrend(
                    trend="AI Integration",
                    description="AI-powered automation is becoming table stakes.",
                    relevance="high",
                    opportunity="Early AI adoption can be a key differentiator.",
                    sources=["Industry reports"]
                ),
                MarketTrend(
                    trend="Privacy-First Marketing",
                    description="Increasing focus on first-party data and privacy.",
                    relevance="high",
                    opportunity="Building trust through transparent data practices.",
                    sources=["Market analysis"]
                ),
            ],
            audience_insights=[
                AudienceInsight(
                    segment_name="Growth-Stage Startups",
                    demographics={
                        "age_range": "25-40",
                        "job_titles": ["CEO", "CMO", "Marketing Manager"],
                        "company_size": "10-100 employees"
                    },
                    psychographics={
                        "values": ["efficiency", "innovation", "growth"],
                        "motivations": ["scale quickly", "stay competitive"]
                    },
                    pain_points=[
                        "Limited marketing resources",
                        "Need to move fast",
                        "Budget constraints"
                    ],
                    goals=[
                        "Increase brand awareness",
                        "Generate quality leads",
                        "Scale marketing efforts"
                    ],
                    preferred_channels=["LinkedIn", "Twitter", "Email"],
                    content_preferences=["How-to guides", "Case studies", "Templates"]
                ),
            ],
            news=[
                {
                    "title": f"{company_name} Continues Growth",
                    "date": "2024-01-15",
                    "summary": "Company reports strong growth in user adoption.",
                    "source": "Industry Publication",
                    "sentiment": "positive"
                }
            ],
            market_position="Challenger with opportunity to differentiate through innovation and customer experience.",
            opportunities=[
                "AI-powered personalization",
                "Vertical market expansion",
                "Partnership ecosystem development"
            ],
            threats=[
                "Increasing competition from well-funded players",
                "Market consolidation",
                "Economic uncertainty affecting budgets"
            ]
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Convenience function
async def research_market(
    company_name: str,
    domain: str,
    api_key: Optional[str] = None,
    industry_hint: Optional[str] = None,
    on_progress: Optional[callable] = None
) -> MarketResearchResult:
    """
    Conduct market research for a company.

    Args:
        company_name: Name of the company
        domain: Company's domain
        api_key: Perplexity API key (optional)
        industry_hint: Hint about the industry
        on_progress: Progress callback

    Returns:
        MarketResearchResult with findings
    """
    service = PerplexityService(api_key=api_key)
    try:
        return await service.research_market(
            company_name, domain, industry_hint, on_progress
        )
    finally:
        await service.close()
