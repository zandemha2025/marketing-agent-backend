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
    # New Brand DNA fields
    brand_heritage: str = ""
    cultural_impact: str = ""
    advertising_strategy: str = ""
    citations: List[str] = field(default_factory=list)


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
            import asyncio
            if asyncio.iscoroutinefunction(on_progress):
                await on_progress("market_research", 0.0, "Starting market research")
            else:
                on_progress("market_research", 0.0, "Starting market research")

        # Research tasks to run in parallel
        tasks = [
            self._research_competitors(company_name, domain, industry_hint),
            self._research_trends(company_name, domain, industry_hint),
            self._research_audience(company_name, domain, industry_hint),
            self._research_news(company_name, domain),
            self._research_brand_dna(company_name, domain)  # New deep research module
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
                if not isinstance(results[4], Exception):
                    # Process Brand DNA results
                    dna_results = results[4]
                    result.brand_heritage = dna_results.get("heritage", "")
                    result.cultural_impact = dna_results.get("cultural_impact", "")
                    result.advertising_strategy = dna_results.get("advertising_strategy", "")
                    result.citations.extend(dna_results.get("citations", []))

                # Determine industry if not provided
                if not industry_hint and result.competitors:
                    result.industry = await self._determine_industry(
                        company_name, domain, result.competitors
                    )

            except Exception as e:
                logger.error(f"Perplexity research failed: {e}")
                raise RuntimeError(
                    f"Perplexity API research failed: {e}. "
                    "Please check your PERPLEXITY_API_KEY and network connectivity."
                ) from e
        else:
            # No API key configured - raise clear error
            logger.error(
                "Perplexity API key not configured. "
                "Set PERPLEXITY_API_KEY environment variable to enable market research."
            )
            raise NotImplementedError(
                "Market research requires PERPLEXITY_API_KEY to be configured. "
                "Please set the PERPLEXITY_API_KEY environment variable."
            )

        if on_progress:
            import asyncio
            if asyncio.iscoroutinefunction(on_progress):
                await on_progress("market_research", 1.0, "Massive research complete")
            else:
                on_progress("market_research", 1.0, "Massive research complete")

        return result

    async def _research_brand_dna(self, company_name: str, domain: str) -> Dict[str, Any]:
        """Conduct deep research into brand history, culture, and strategy."""
        query = f"""
        Conduct a deep strategic analysis of {company_name} ({domain}).
        
        I need a "Brand DNA" report covering:
        1. Brand Heritage & History: Founding story, key milestones, and evolution.
        2. Cultural Impact: How the brand influences culture, key partnerships, and social standing.
        3. Advertising Strategy: Analysis of their marketing approach, tone of voice, and famous campaigns.
        
        Provide detailed, citation-backed insights.
        
        Format as JSON:
        {{
            "heritage": "Detailed history...",
            "cultural_impact": "Analysis of cultural standing...",
            "advertising_strategy": "Marketing strategy analysis...",
            "citations": ["Source 1", "Source 2"]
        }}
        """
        
        result = await self._query_perplexity(
            query,
            "You are a Brand Strategist. Provide deep, cited analysis in JSON format."
        )
        
        try:
            return self._extract_json(result)
        except Exception as e:
            logger.error(f"Error parsing Brand DNA data: {e}")
            return {}

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
        Identify the target audiences for this company.
        
        Company: {company_name}
        Website: {domain}
        Industry: {industry_context}
        
        You MUST identify at least 2-3 distinct audience segments. Consider:
        - Who pays for the product? (B2B buyers, consumers, enterprises)
        - Who uses the product? (developers, marketers, end-users)
        - Company size? (startups, SMBs, enterprise)
        - Job titles? (CTOs, Marketing Directors, individual contributors)
        
        For each audience segment, provide:
        1. Segment name (e.g., "Startup Founders", "Enterprise Finance Teams")
        2. Demographics (company size, industry, location)
        3. Psychographics (values, priorities, pain points)
        4. Preferred channels (LinkedIn, Twitter, email, etc.)
        5. Content preferences (technical docs, case studies, videos)

        Format as JSON:
        {{
            "segments": [
                {{
                    "segment_name": "Segment Name",
                    "demographics": {{
                        "company_size": "startup|smb|enterprise|all",
                        "industries": ["list", "of", "industries"],
                        "job_titles": ["relevant", "titles"],
                        "geography": "global|regional specifics"
                    }},
                    "psychographics": {{
                        "values": ["what they care about"],
                        "pain_points": ["their challenges"],
                        "goals": ["what they want to achieve"]
                    }},
                    "preferred_channels": ["LinkedIn", "Twitter", "Email", "etc"],
                    "content_preferences": ["case studies", "technical docs", "etc"]
                }}
            ]
        }}

        CRITICAL: You MUST return at least 2 audience segments. Never return an empty array.
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
        """Return intelligent default audience segments based on industry context."""
        
        # Consumer brand defaults for well-known companies
        if any(brand in company_name.lower() for brand in ["nike", "adidas", "puma", "reebok", "under armour"]):
            return [
                AudienceInsight(
                    segment_name="Athletes & Fitness Enthusiasts",
                    demographics={
                        "age_range": "16-45",
                        "interests": ["sports", "fitness", "athletics"],
                        "lifestyle": "active",
                        "geography": "Global"
                    },
                    psychographics={
                        "values": ["performance", "achievement", "self-improvement"],
                        "motivations": ["excel in sports", "stay fit", "look athletic"],
                        "priorities": ["quality gear", "performance enhancement"]
                    },
                    pain_points=[
                        "Finding gear that enhances performance",
                        "Staying motivated with fitness goals",
                        "Balancing style with function"
                    ],
                    goals=[
                        "Improve athletic performance",
                        "Look and feel like an athlete",
                        "Stay competitive in sports"
                    ],
                    preferred_channels=["Instagram", "YouTube", "TikTok", "Sports apps"],
                    content_preferences=["Training tips", "Athlete stories", "Product demos"]
                ),
                AudienceInsight(
                    segment_name="Lifestyle Consumers",
                    demographics={
                        "age_range": "18-35",
                        "interests": ["fashion", "streetwear", "sneakers"],
                        "lifestyle": "urban",
                        "geography": "Global"
                    },
                    psychographics={
                        "values": ["style", "authenticity", "trendiness"],
                        "motivations": ["express identity", "stay fashionable", "belong to culture"],
                        "priorities": ["aesthetic appeal", "brand authenticity"]
                    },
                    pain_points=[
                        "Finding unique styles",
                        "Keeping up with trends",
                        "Balancing cost with quality"
                    ],
                    goals=[
                        "Express personal style",
                        "Stay on trend",
                        "Own premium brands"
                    ],
                    preferred_channels=["Instagram", "TikTok", "Fashion blogs", "Sneaker communities"],
                    content_preferences=["Style inspiration", "Behind-the-scenes", "Limited drops"]
                )
            ]

        # General consumer defaults
        if industry and any(keyword in industry.lower() for keyword in ["retail", "fashion", "apparel", "consumer"]):
            return [
                AudienceInsight(
                    segment_name="Brand Enthusiasts",
                    demographics={
                        "age_range": "18-45",
                        "interests": ["fashion", "brands", "lifestyle"],
                        "geography": "Global"
                    },
                    psychographics={
                        "values": ["quality", "style", "authenticity"],
                        "motivations": ["express identity", "stay current", "quality products"],
                        "priorities": ["brand reputation", "product quality"]
                    },
                    pain_points=[
                        "Finding authentic products",
                        "Staying within budget",
                        "Finding right sizes/styles"
                    ],
                    goals=[
                        "Look and feel good",
                        "Express personal style",
                        "Buy quality products"
                    ],
                    preferred_channels=["Instagram", "YouTube", "Fashion websites"],
                    content_preferences=["Product reviews", "Style tips", "Brand stories"]
                )
            ]

        # Original B2B defaults as fallback for actual B2B companies
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
        Analyze this company and identify its PRIMARY industry.
        
        Company: {company_name}
        Website: {domain}
        {"Known competitors: " + competitor_names if competitors else ""}

        IMPORTANT: You MUST provide a specific industry classification.
        Common industries include:
        - Fintech / Financial Technology
        - E-commerce / Retail
        - SaaS / Software
        - Healthcare / Health Tech
        - Education / EdTech
        - Marketing / AdTech
        - Enterprise Software
        - Consumer Technology
        - B2B Services
        - Media / Entertainment

        Based on what this company does, provide:
        1. Primary Industry (be specific, e.g., "Financial Technology" not just "Technology")
        2. Industry Segment (e.g., "Payment Processing" for a payments company)
        
        Respond with ONLY the industry name and segment.
        Example: "Financial Technology - Payment Processing"

        CRITICAL: Never return "Unknown" - always make your best assessment based on the company's products and services.
        """

        try:
            result = await self._query_perplexity(query)
            industry = result.strip().strip('"').strip("'")
            
            # Clean up response if it's too long or chatty
            if len(industry) > 100 or "\n" in industry:
                industry = industry.split("\n")[0].strip()

            # Validate we got a real answer
            if not industry or industry.lower() in ["unknown", "n/a", "not available", "unclear"]:
                # Try to infer from domain
                industry = self._infer_industry_from_domain(domain)

            return industry
        except Exception as e:
            logger.error(f"Error determining industry: {e}")
            return self._infer_industry_from_domain(domain)

    def _infer_industry_from_domain(self, domain: str) -> str:
        """Infer industry from domain name as a last resort - for consumer brands."""
        domain_lower = domain.lower()

        # Consumer brand patterns
        consumer_patterns = {
            "nike": "Athletic Apparel & Footwear",
            "adidas": "Athletic Apparel & Footwear",
            "puma": "Athletic Apparel & Footwear",
            "reebok": "Athletic Apparel & Footwear",
            "underarmour": "Athletic Apparel & Footwear",
            "levi": "Fashion & Apparel",
            "gap": "Fashion & Apparel",
            "h&m": "Fashion & Apparel",
            "zara": "Fashion & Apparel",
            "uniqlo": "Fashion & Apparel",
            "coca": "Food & Beverage",
            "pepsi": "Food & Beverage",
            "starbucks": "Food & Beverage",
            "mcdonalds": "Food & Beverage",
            "apple": "Consumer Technology",
            "samsung": "Consumer Technology",
            "sony": "Consumer Technology",
            "netflix": "Media & Entertainment",
            "spotify": "Media & Entertainment",
            "disney": "Media & Entertainment",
            "toyota": "Automotive",
            "ford": "Automotive",
            "tesla": "Automotive",
        }

        # B2B/Enterprise patterns
        b2b_patterns = {
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

        # Check consumer patterns first
        for pattern, industry in consumer_patterns.items():
            if pattern in domain_lower:
                return industry

        # Check B2B patterns
        for pattern, industry in b2b_patterns.items():
            if pattern in domain_lower:
                return industry

        # If no clear match, return a generic but accurate category
        return "General Business"  # Better than forcing into Technology

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
        # Use our smart logic for industry and audience even in mock mode
        industry = self._infer_industry_from_domain(domain)
        audience_segments = self._get_default_audience_segments(company_name, industry)
        
        return MarketResearchResult(
            company_name=company_name,
            industry=industry,
            competitors=[
                CompetitorProfile(
                    name="Competitor A",
                    domain="competitor-a.com",
                    description="Market leader in the space.",
                    strengths=["Strong brand", "Global reach"],
                    weaknesses=["High price"],
                    positioning="Premium",
                    key_differentiators=["Quality"],
                    target_audience="General public",
                    pricing_model="Retail",
                    social_presence={}
                )
            ],
            trends=[],
            audience_insights=audience_segments,
            news=[],
            market_position="Market Leader",
            opportunities=["Global expansion"],
            threats=["Competition"],
            # New Brand DNA fields for mock data
            brand_heritage=f"Founded in 2020, {company_name} has rapidly evolved.",
            cultural_impact=f"{company_name} is recognized as a leader.",
            advertising_strategy="Focuses on brand building.",
            citations=["Mock Citation 1"]
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
