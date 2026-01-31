"""
Campaign Orchestrator.

The master conductor that brings together all services to execute
complete campaign workflows:

1. Research (Firecrawl + Perplexity) → Deep brand/market knowledge
2. Strategy (BriefGenerator) → Professional creative brief
3. Creative (CreativeDirector) → Concept development
4. Production (AssetGenerator) → Final assets

This is the heart of the AI-powered campaign system.
"""
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from ..onboarding.firecrawl import FirecrawlService
from ..onboarding.perplexity import PerplexityService
from .brief_generator import BriefGenerator, CampaignBrief
from .creative_director import CreativeDirector, CreativeConcept
from ..assets.asset_generator import AssetGenerator, CompleteAsset
from ..optimization.predictive_modeling import PredictivePerformanceModel, CampaignPrediction
from ..optimization.campaign_optimizer import CampaignOptimizer
from ..ai.openrouter import llm, llm_json

logger = logging.getLogger(__name__)


class CampaignPhase(Enum):
    """Campaign workflow phases."""
    RESEARCH = "research"
    STRATEGY = "strategy"
    CREATIVE = "creative"
    PRODUCTION = "production"
    REVIEW = "review"
    COMPLETE = "complete"


@dataclass
class CampaignProgress:
    """Real-time campaign progress tracking."""
    phase: CampaignPhase
    progress: float  # 0-100
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CampaignResult:
    """Complete campaign execution result."""
    campaign_id: str
    status: str

    # Research outputs
    brand_analysis: Optional[Dict[str, Any]] = None
    market_research: Optional[Dict[str, Any]] = None

    # Strategy outputs
    brief: Optional[CampaignBrief] = None

    # Creative outputs
    concepts: List[CreativeConcept] = field(default_factory=list)
    selected_concept: Optional[CreativeConcept] = None

    # Production outputs
    assets: List[CompleteAsset] = field(default_factory=list)

    # Optimization outputs
    performance_prediction: Optional[CampaignPrediction] = None
    optimization_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    auto_optimization_enabled: bool = False

    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None

    # Additional deliverable content
    research_report: str = ""
    competitive_analysis: str = ""
    media_plan: str = ""
    headlines: List[str] = field(default_factory=list)
    body_copy_variations: List[str] = field(default_factory=list)
    social_posts: Dict[str, List[str]] = field(default_factory=dict)
    video_scripts: List[str] = field(default_factory=list)
    display_ad_copy: Dict[str, str] = field(default_factory=dict)

    # Errors
    errors: List[str] = field(default_factory=list)


class CampaignOrchestrator:
    """
    Master orchestrator for end-to-end campaign execution.

    Coordinates all services to transform a simple campaign request
    into production-ready marketing assets.
    """

    def __init__(
        self,
        openrouter_api_key: str,
        firecrawl_api_key: str,
        perplexity_api_key: str,
        segmind_api_key: str,
        elevenlabs_api_key: str,
        output_dir: str = "outputs"
    ):
        # Initialize all services
        self.firecrawl = FirecrawlService(api_key=firecrawl_api_key)
        self.perplexity = PerplexityService(api_key=perplexity_api_key)
        self.brief_generator = BriefGenerator(openrouter_api_key=openrouter_api_key)
        self.creative_director = CreativeDirector(openrouter_api_key=openrouter_api_key)
        self.asset_generator = AssetGenerator(
            openrouter_api_key=openrouter_api_key,
            segmind_api_key=segmind_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            output_dir=output_dir
        )

        self.output_dir = output_dir
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """Set callback for progress updates."""
        self._progress_callback = callback

    async def _emit_progress(self, phase: CampaignPhase, progress: float, message: str, details: Dict = None):
        """Emit progress update."""
        update = CampaignProgress(
            phase=phase,
            progress=progress,
            message=message,
            details=details
        )
        logger.info(f"[{phase.value}] {progress}% - {message}")

        if self._progress_callback:
            await self._progress_callback(update)

    async def execute_campaign(
        self,
        campaign_request: Dict[str, Any],
        knowledge_base: Optional[Dict[str, Any]] = None,
        skip_research: bool = False,
        concept_index: int = 0,
        platforms: Optional[List[str]] = None,
    ) -> CampaignResult:
        """
        Execute a complete campaign workflow.

        Args:
            campaign_request: Campaign parameters including:
                - objective: What the campaign aims to achieve
                - product_focus: Specific product/service (optional)
                - target_audience: Who to target (optional, will use KB)
                - budget_tier: low/medium/high (affects asset complexity)
                - timeline: Campaign timeline
                - channels: List of channels (optional)
            knowledge_base: Pre-existing brand knowledge (from onboarding)
            skip_research: Skip research phase if KB is fresh
            concept_index: Which creative concept to use (0-based)
            platforms: Specific platforms to generate for

        Returns:
            CampaignResult with all outputs
        """
        import uuid
        campaign_id = uuid.uuid4().hex[:12]
        start_time = datetime.now()

        result = CampaignResult(
            campaign_id=campaign_id,
            status="in_progress"
        )

        try:
            # Phase 1: Research (if needed)
            if not skip_research and not knowledge_base:
                await self._emit_progress(
                    CampaignPhase.RESEARCH, 0,
                    "Starting research phase..."
                )

                brand_analysis, market_research = await self._execute_research(
                    campaign_request
                )
                result.brand_analysis = brand_analysis
                result.market_research = market_research

                # Build knowledge base from research
                knowledge_base = self._build_knowledge_from_research(
                    brand_analysis,
                    market_research
                )
            else:
                await self._emit_progress(
                    CampaignPhase.RESEARCH, 100,
                    "Using existing knowledge base"
                )
                if knowledge_base is None:
                    knowledge_base = {}
                result.brand_analysis = knowledge_base.get("brand", {})
                result.market_research = knowledge_base.get("market", {})

            # Phase 2: Strategy (Brief Generation)
            await self._emit_progress(
                CampaignPhase.STRATEGY, 0,
                "Developing strategic brief..."
            )

            brief = await self._execute_strategy(
                campaign_request,
                knowledge_base
            )
            result.brief = brief

            await self._emit_progress(
                CampaignPhase.STRATEGY, 100,
                "Brief complete",
                {"brief_title": brief.campaign_name}
            )

            # Phase 3: Creative (Concept Development)
            await self._emit_progress(
                CampaignPhase.CREATIVE, 0,
                "Developing creative concepts..."
            )

            concepts = await self._execute_creative(
                brief,
                knowledge_base
            )
            result.concepts = concepts

            # Select concept
            if concepts and concept_index < len(concepts):
                result.selected_concept = concepts[concept_index]
            elif concepts:
                result.selected_concept = concepts[0]

            await self._emit_progress(
                CampaignPhase.CREATIVE, 100,
                f"Generated {len(concepts)} creative concepts",
                {"concept_names": [c.concept_name for c in concepts]}
            )

            # Phase 4: Production (Asset Generation)
            if result.selected_concept:
                try:
                    await self._emit_progress(
                        CampaignPhase.PRODUCTION, 0,
                        f"Producing assets for '{result.selected_concept.concept_name}'..."
                    )

                    assets = await self._execute_production(
                        result.selected_concept,
                        knowledge_base,
                        platforms
                    )
                    result.assets = assets

                    await self._emit_progress(
                        CampaignPhase.PRODUCTION, 100,
                        f"Generated {len(assets)} production-ready assets"
                    )
                except Exception as e:
                    logger.warning(f"Production phase failed: {e}")
                    result.errors.append(f"Production: {e}")

            # Phase 5: Generate additional deliverables
            try:
                await self._emit_progress(
                    CampaignPhase.PRODUCTION, 80,
                    "Generating additional deliverable content..."
                )
                await self._generate_additional_deliverables(
                    result, campaign_request, knowledge_base
                )
            except Exception as e:
                logger.warning(f"Additional deliverables failed: {e}")

            # Complete
            result.status = "complete"
            result.completed_at = datetime.now()
            result.total_duration_seconds = (
                result.completed_at - start_time
            ).total_seconds()

            await self._emit_progress(
                CampaignPhase.COMPLETE, 100,
                "Campaign complete!",
                {
                    "total_assets": len(result.assets),
                    "duration_minutes": round(result.total_duration_seconds / 60, 1)
                }
            )

        except Exception as e:
            import traceback as _tb
            logger.error(f"Campaign execution failed: {e}\n{_tb.format_exc()}")
            result.status = "failed"
            result.errors.append(str(e))
            result.completed_at = datetime.now()

        return result

    async def _execute_research(
        self,
        campaign_request: Dict[str, Any]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Execute research phase with Firecrawl and Perplexity."""
        brand_url = campaign_request.get("brand_url")
        brand_name = campaign_request.get("brand_name", "")
        industry = campaign_request.get("industry", "")

        brand_analysis = {}
        market_research = {}

        # Parallel research
        tasks = []

        if brand_url:
            await self._emit_progress(
                CampaignPhase.RESEARCH, 10,
                f"Crawling {brand_url}..."
            )
            tasks.append(("brand", self._research_brand(brand_url)))

        if brand_name or industry:
            await self._emit_progress(
                CampaignPhase.RESEARCH, 20,
                "Researching market landscape..."
            )
            tasks.append(("market", self._research_market(brand_name, industry)))

        # Execute research in parallel
        for name, task in tasks:
            try:
                result = await task
                if name == "brand":
                    brand_analysis = result
                else:
                    market_research = result

                await self._emit_progress(
                    CampaignPhase.RESEARCH, 60 if name == "brand" else 90,
                    f"{name.title()} research complete"
                )
            except Exception as e:
                logger.error(f"Research {name} failed: {e}")

        return brand_analysis, market_research

    async def _research_brand(self, url: str) -> Dict[str, Any]:
        """Deep brand research using Firecrawl."""
        crawl_result = await self.firecrawl.deep_crawl(
            url=url,
            max_pages=20,
            include_screenshots=False
        )

        return {
            "url": url,
            "pages_analyzed": len(crawl_result.get("pages", [])),
            "content": crawl_result.get("content", {}),
            "structure": crawl_result.get("structure", {}),
        }

    async def _research_market(
        self,
        brand_name: str,
        industry: str
    ) -> Dict[str, Any]:
        """Market research using Perplexity."""
        results = {}

        # Research competitors
        if brand_name:
            competitors = await self.perplexity.research(
                f"Who are the main competitors of {brand_name} in the {industry} industry? "
                "List their key differentiators and market positioning."
            )
            results["competitors"] = competitors

        # Research trends
        trends = await self.perplexity.research(
            f"What are the current marketing trends and consumer behavior patterns "
            f"in the {industry} industry? Focus on digital marketing strategies."
        )
        results["trends"] = trends

        # Research audience
        audience = await self.perplexity.research(
            f"Who is the typical target audience for {industry} products/services? "
            "Include demographics, psychographics, and buying behaviors."
        )
        results["audience"] = audience

        return results

    def _build_knowledge_from_research(
        self,
        brand_analysis: Dict[str, Any],
        market_research: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build knowledge base from research results."""
        return {
            "brand": {
                "name": brand_analysis.get("content", {}).get("name", ""),
                "description": brand_analysis.get("content", {}).get("description", ""),
                "voice": brand_analysis.get("content", {}).get("tone", {}),
                "visual_identity": brand_analysis.get("content", {}).get("visual", {}),
            },
            "market": {
                "competitors": market_research.get("competitors", {}),
                "trends": market_research.get("trends", {}),
            },
            "audiences": {
                "segments": [market_research.get("audience", {})] if market_research.get("audience") else []
            },
            "offerings": brand_analysis.get("content", {}).get("products", []),
        }

    async def _execute_strategy(
        self,
        campaign_request: Dict[str, Any],
        knowledge_base: Dict[str, Any]
    ) -> CampaignBrief:
        """Execute strategy phase - generate creative brief."""
        await self._emit_progress(
            CampaignPhase.STRATEGY, 20,
            "Analyzing objectives and constraints..."
        )

        # Extract campaign parameters
        objective = campaign_request.get("objective", "")
        product_focus = campaign_request.get("product_focus")
        target_audience = campaign_request.get("target_audience")
        budget_tier = campaign_request.get("budget_tier", "medium")
        timeline = campaign_request.get("timeline", "4 weeks")

        # Build user request from campaign parameters
        user_request = f"""
Campaign Objective: {objective}
Product Focus: {product_focus or 'General brand'}
Target Audience: {target_audience or 'General audience'}
Budget Tier: {budget_tier}
Timeline: {timeline}
"""

        # Determine campaign type from objective
        campaign_type = "brand_awareness"  # Default
        objective_lower = objective.lower()
        if "launch" in objective_lower or "new product" in objective_lower:
            campaign_type = "product_launch"
        elif "sale" in objective_lower or "conversion" in objective_lower:
            campaign_type = "conversion"
        elif "engagement" in objective_lower:
            campaign_type = "engagement"

        await self._emit_progress(
            CampaignPhase.STRATEGY, 50,
            "Crafting strategic brief..."
        )

        brief = await self.brief_generator.generate_brief(
            campaign_type=campaign_type,
            user_request=user_request,
            knowledge_base=knowledge_base,
            additional_context=None
        )

        return brief

    def _budget_to_constraints(self, budget_tier: str) -> Dict[str, Any]:
        """Convert budget tier to specific constraints."""
        constraints = {
            "low": {
                "max_assets": 5,
                "include_video": False,
                "include_print": False,
                "channels": ["social_organic"]
            },
            "medium": {
                "max_assets": 15,
                "include_video": True,
                "include_print": False,
                "channels": ["social_organic", "social_paid", "email"]
            },
            "high": {
                "max_assets": 30,
                "include_video": True,
                "include_print": True,
                "channels": ["social_organic", "social_paid", "email", "display", "video", "print"]
            }
        }
        return constraints.get(budget_tier, constraints["medium"])

    async def _execute_creative(
        self,
        brief: CampaignBrief,
        knowledge_base: Dict[str, Any]
    ) -> List[CreativeConcept]:
        """Execute creative phase - develop concepts."""
        await self._emit_progress(
            CampaignPhase.CREATIVE, 20,
            "Exploring creative territories..."
        )

        brand_data = knowledge_base.get("brand", {})

        # Generate concepts for the first territory (or all)
        concepts = []

        if brief.creative_territories:
            territory = brief.creative_territories[0]  # Primary territory

            await self._emit_progress(
                CampaignPhase.CREATIVE, 50,
                f"Developing concept for '{getattr(territory, 'name', 'Primary')}'..."
            )

            concept = await self.creative_director.develop_concept(
                brief=brief,
                territory=territory,
                brand_data=brand_data
            )
            concepts.append(concept)

            # Generate additional concepts for other territories
            for i, alt_territory in enumerate(brief.creative_territories[1:3], 2):
                try:
                    await self._emit_progress(
                        CampaignPhase.CREATIVE, 50 + (i * 15),
                        f"Developing alternative concept {i}..."
                    )

                    alt_concept = await self.creative_director.develop_concept(
                        brief=brief,
                        territory=alt_territory,
                        brand_data=brand_data
                    )
                    concepts.append(alt_concept)
                except Exception as e:
                    logger.warning(f"Alternative concept {i} generation failed: {e}")
                    break

        return concepts

    async def _execute_production(
        self,
        concept: CreativeConcept,
        knowledge_base: Dict[str, Any],
        platforms: Optional[List[str]] = None
    ) -> List[CompleteAsset]:
        """Execute production phase - generate assets."""
        brand_data = knowledge_base.get("brand", {})

        # Get asset specs from concept (field is 'assets' on CreativeConcept dataclass)
        asset_specs = getattr(concept, 'assets', []) or getattr(concept, 'asset_specs', [])

        # Filter by platform if specified
        if platforms and asset_specs:
            asset_specs = [
                spec for spec in asset_specs
                if (spec.get("platform", "").lower() if isinstance(spec, dict) else getattr(spec, "platform", "").lower()) in [p.lower() for p in platforms]
            ]

        if not asset_specs:
            logger.warning("No asset specs to produce")
            return []

        # Generate assets with progress updates
        assets = []
        total = len(asset_specs)

        for i, spec in enumerate(asset_specs):
            await self._emit_progress(
                CampaignPhase.PRODUCTION,
                int((i / total) * 100),
                f"Generating {spec.get('asset_type', 'asset')} for {spec.get('platform', 'unknown')}..."
            )

            try:
                asset = await self.asset_generator.generate_asset(
                    asset_spec=spec,
                    brand_data=brand_data
                )
                assets.append(asset)
            except Exception as e:
                logger.error(f"Failed to generate asset: {e}")

        return assets

    async def _generate_additional_deliverables(
        self,
        result: CampaignResult,
        campaign_request: Dict[str, Any],
        knowledge_base: Dict[str, Any]
    ) -> None:
        """
        Post-processing phase: generate all additional deliverable content
        using the LLM and data already available in the CampaignResult.
        
        IMPORTANT: Runs LLM calls SEQUENTIALLY to prevent timeout issues.
        Each call waits for the previous one to complete before starting.
        """
        brand_name = knowledge_base.get("brand", {}).get("name", "") or campaign_request.get("brand_name", "Unknown Brand")
        product_focus = campaign_request.get("product_focus", "general brand offerings")
        target_audience = campaign_request.get("target_audience", "general consumers")
        brief_summary = ""
        if result.brief:
            brief_summary = (
                f"Campaign: {result.brief.campaign_name}\n"
                f"Proposition: {result.brief.strategic_proposition}\n"
                f"Key Insight: {result.brief.key_insight}\n"
                f"Tone: {', '.join(result.brief.tone_of_voice)}"
            )

        concept_summary = ""
        if result.concepts:
            concept_summary = "\n".join(
                f"- {c.concept_name}: {c.concept_statement} (Tagline: {c.tagline})"
                for c in result.concepts
            )

        brand_context = (
            f"Brand: {brand_name}\n"
            f"Product/Service: {product_focus}\n"
            f"Target Audience: {target_audience}\n"
            f"{brief_summary}"
        )

        # Define generation tasks with their field names
        # SEQUENTIAL execution to prevent LLM timeout issues
        generation_tasks = [
            ("research_report", self._gen_research_report, [result, brand_context]),
            ("competitive_analysis", self._gen_competitive_analysis, [result, brand_context]),
            ("media_plan", self._gen_media_plan, [result, brand_context]),
            ("headlines", self._gen_headlines, [brand_context, concept_summary]),
            ("body_copy_variations", self._gen_body_copy, [brand_context, concept_summary]),
            ("social_posts", self._gen_social_posts, [brand_context, concept_summary]),
            ("video_scripts", self._gen_video_scripts, [brand_context, concept_summary]),
            ("display_ad_copy", self._gen_display_ad_copy, [brand_context, concept_summary]),
        ]

        total_tasks = len(generation_tasks)
        for idx, (field_name, gen_func, args) in enumerate(generation_tasks):
            try:
                # Emit progress for each deliverable
                progress_pct = 80 + int((idx / total_tasks) * 15)  # 80-95%
                await self._emit_progress(
                    CampaignPhase.PRODUCTION,
                    progress_pct,
                    f"Generating {field_name.replace('_', ' ')}..."
                )
                
                logger.info(f"Generating {field_name} ({idx + 1}/{total_tasks})...")
                gen_result = await gen_func(*args)
                setattr(result, field_name, gen_result)
                logger.info(f"Successfully generated {field_name}")
                
            except Exception as e:
                logger.error(f"Failed to generate {field_name}: {e}")
                result.errors.append(f"Failed to generate {field_name}: {e}")
                # Continue with other deliverables even if one fails

    async def _gen_research_report(self, result: CampaignResult, brand_context: str) -> str:
        """Format brand_analysis + market_research into a proper markdown research report."""
        brand_data = json.dumps(result.brand_analysis or {}, indent=2, default=str)
        market_data = json.dumps(result.market_research or {}, indent=2, default=str)

        prompt = f"""You are a senior marketing research analyst. Using the raw research data below,
produce a comprehensive, well-structured markdown Research Report.

## Brand Context
{brand_context}

## Raw Brand Analysis Data
{brand_data}

## Raw Market Research Data
{market_data}

Create a professional research report with these sections:
1. Executive Summary (3-4 sentences)
2. Brand Analysis (brand positioning, strengths, weaknesses, brand perception)
3. Market Landscape (market size, growth trends, key dynamics)
4. Consumer Insights (target demographics, behaviors, needs, pain points)
5. Key Opportunities (3-5 actionable opportunities)
6. Key Risks & Challenges (3-5 risks)
7. Recommendations (strategic recommendations based on findings)

Write in professional analyst prose. Use markdown headers, bullet points, and bold for emphasis.
Do NOT wrap the output in code fences. Output only the markdown report."""

        return await llm(prompt, system="You are a senior marketing research analyst producing a comprehensive research report.")

    async def _gen_competitive_analysis(self, result: CampaignResult, brand_context: str) -> str:
        """Extract competitor data and generate a structured competitive analysis with SWOT."""
        market_data = json.dumps(result.market_research or {}, indent=2, default=str)
        brand_data = json.dumps(result.brand_analysis or {}, indent=2, default=str)

        prompt = f"""You are a competitive intelligence analyst. Using the data below, produce
a detailed Competitive Analysis report in markdown.

## Brand Context
{brand_context}

## Market Research Data
{market_data}

## Brand Analysis Data
{brand_data}

Create a competitive analysis with:
1. Competitive Landscape Overview (who the key players are, market dynamics)
2. For each of the top 3-5 competitors, provide:
   - Company overview and positioning
   - SWOT Analysis (Strengths, Weaknesses, Opportunities, Threats)
   - Key differentiators
   - Marketing strategy observations
3. Competitive Positioning Map (describe where each brand sits on key dimensions)
4. White Space Opportunities (gaps in the market our brand can exploit)
5. Strategic Implications (what this means for our campaign)

If competitor data is limited, use your knowledge to fill in realistic competitive context
for the brand's industry. Write in professional analyst prose with markdown formatting.
Do NOT wrap in code fences."""

        return await llm(prompt, system="You are a competitive intelligence analyst producing a detailed competitive analysis.")

    async def _gen_media_plan(self, result: CampaignResult, brand_context: str) -> str:
        """Generate a detailed media plan with calendar from channel_strategy and budget."""
        channel_data = ""
        budget_data = ""
        timeline_data = ""
        if result.brief:
            channel_data = "\n".join(
                f"- {cs.channel}: Role={cs.role}, Formats={cs.formats}, Frequency={cs.frequency}, Budget={cs.budget_allocation}"
                for cs in result.brief.channel_strategy
            )
            budget_data = json.dumps(result.brief.budget, indent=2, default=str)
            timeline_data = json.dumps(result.brief.timeline, indent=2, default=str)

        prompt = f"""You are a senior media planner at a top agency. Create a detailed Media Plan document in markdown.

## Brand Context
{brand_context}

## Channel Strategy
{channel_data or "No specific channel strategy provided - create a recommended plan."}

## Budget Framework
{budget_data or "Medium budget tier"}

## Timeline
{timeline_data or "4-week campaign"}

Create a comprehensive media plan with:
1. Media Strategy Overview (objectives, approach, KPIs)
2. Channel Mix & Rationale (why each channel, what role it plays)
3. Budget Allocation Table (channel, format, budget %, estimated spend)
4. Flight Plan / Media Calendar:
   - Week-by-week breakdown
   - Which channels are active each week
   - Key milestones and tentpole moments
5. Reach & Frequency Estimates (estimated impressions, reach, frequency per channel)
6. Optimization Strategy (how to optimize during campaign flight)
7. Measurement Framework (what to track, when to report)

Format as a professional media plan document. Use markdown tables where appropriate.
Do NOT wrap in code fences."""

        return await llm(prompt, system="You are a senior media planner producing a detailed media plan with calendar.")

    async def _gen_headlines(self, brand_context: str, concept_summary: str) -> List[str]:
        """Generate 12+ consolidated headlines using brief + concepts."""
        prompt = f"""You are a senior copywriter known for crafting compelling headlines.

## Brand Context
{brand_context}

## Creative Concepts
{concept_summary or "No specific concepts - generate headlines based on brand context."}

Generate exactly 15 distinct, powerful advertising headlines for this campaign.

Requirements:
- Mix of lengths: short punchy (3-5 words), medium (6-10 words), and longer editorial (10-15 words)
- Mix of styles: provocative questions, bold statements, emotional appeals, benefit-driven, curiosity-driven
- Each headline must be distinct in approach and angle
- All headlines must align with the brand tone and campaign strategy

Return ONLY a JSON array of strings, no other text:
["headline 1", "headline 2", ...]"""

        raw = await llm(prompt, system="You are a senior copywriter. Respond only with valid JSON.", json_mode=True)
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        parsed = json.loads(text.strip())
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        return []

    async def _gen_body_copy(self, brand_context: str, concept_summary: str) -> List[str]:
        """Generate 6 standalone body copy variations."""
        prompt = f"""You are an award-winning advertising copywriter.

## Brand Context
{brand_context}

## Creative Concepts
{concept_summary or "No specific concepts - generate body copy based on brand context."}

Generate exactly 6 distinct body copy variations for this campaign. Each should be a standalone
piece of advertising body copy (2-4 paragraphs each) that could appear in a print ad, landing page,
or long-form digital ad.

Requirements:
- Each variation takes a different angle or emotional approach
- Include a clear value proposition
- End with a compelling call-to-action
- Vary the tone: one aspirational, one conversational, one authoritative, one emotional, one benefit-focused, one storytelling

Return ONLY a JSON array of strings where each string is one complete body copy variation:
["copy variation 1...", "copy variation 2...", ...]"""

        raw = await llm(prompt, system="You are an award-winning copywriter. Respond only with valid JSON.", json_mode=True)
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        parsed = json.loads(text.strip())
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        return []

    async def _gen_social_posts(self, brand_context: str, concept_summary: str) -> Dict[str, List[str]]:
        """Generate 5 posts per platform for instagram, tiktok, twitter, linkedin, facebook."""
        prompt = f"""You are a social media strategist and copywriter.

## Brand Context
{brand_context}

## Creative Concepts
{concept_summary or "No specific concepts - generate posts based on brand context."}

Generate 5 distinct social media posts for EACH of these platforms:
- instagram
- tiktok
- twitter
- linkedin
- facebook

Each post must include:
- The post caption/text (platform-appropriate length and style)
- 3-5 relevant hashtags
- A clear call-to-action

Requirements per platform:
- Instagram: visual-first, emoji-friendly, 150-300 chars + hashtags
- TikTok: casual, trendy, hook-first, 100-200 chars
- Twitter: concise, punchy, under 280 chars including hashtags
- LinkedIn: professional, thought-leadership tone, 200-400 chars
- Facebook: conversational, community-oriented, 150-300 chars

Return ONLY valid JSON in this exact format:
{{
  "instagram": ["post 1 with #hashtags and CTA", "post 2...", "post 3...", "post 4...", "post 5..."],
  "tiktok": ["post 1...", "post 2...", "post 3...", "post 4...", "post 5..."],
  "twitter": ["post 1...", "post 2...", "post 3...", "post 4...", "post 5..."],
  "linkedin": ["post 1...", "post 2...", "post 3...", "post 4...", "post 5..."],
  "facebook": ["post 1...", "post 2...", "post 3...", "post 4...", "post 5..."]
}}"""

        raw = await llm(prompt, system="You are a social media strategist. Respond only with valid JSON.", json_mode=True)
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return {k: v for k, v in parsed.items() if isinstance(v, list)}
        return {}

    async def _gen_video_scripts(self, brand_context: str, concept_summary: str) -> List[str]:
        """Generate 2 video scripts with scene breakdowns, timing, and voiceover."""
        prompt = f"""You are a creative director specializing in video advertising.

## Brand Context
{brand_context}

## Creative Concepts
{concept_summary or "No specific concepts - generate scripts based on brand context."}

Generate 2 complete video ad scripts. One should be a 30-second spot and one a 60-second spot.

For each script, include:
1. **Title** and **Duration**
2. **Concept/Logline** (1 sentence)
3. **Scene-by-Scene Breakdown** with:
   - Scene number and duration (e.g., "Scene 1 (0:00-0:05)")
   - Visual description (what we see)
   - Audio/Voiceover (what we hear)
   - On-screen text/supers (if any)
4. **Music/Sound Design Notes**
5. **End Card** (final frame with logo, CTA, URL)

Format each script as a complete, professional markdown document.
Separate the two scripts with "---" on its own line.

Do NOT wrap in code fences. Output the scripts directly."""

        raw = await llm(prompt, system="You are a creative director producing professional video ad scripts.")
        scripts = [s.strip() for s in raw.split("---") if s.strip()]
        if not scripts:
            scripts = [raw.strip()]
        return scripts

    async def _gen_display_ad_copy(self, brand_context: str, concept_summary: str) -> Dict[str, str]:
        """Generate copy for each standard IAB display ad size."""
        prompt = f"""You are a digital advertising copywriter specializing in display ads.

## Brand Context
{brand_context}

## Creative Concepts
{concept_summary or "No specific concepts - generate display ad copy based on brand context."}

Generate display ad copy for each of these standard IAB sizes:
- 300x250 (Medium Rectangle)
- 728x90 (Leaderboard)
- 160x600 (Wide Skyscraper)
- 320x50 (Mobile Leaderboard)

For each size, provide:
- Headline (appropriate length for the format)
- Body text (if space allows)
- CTA button text
- Design notes (layout suggestions given the dimensions)

Return ONLY valid JSON in this exact format:
{{
  "300x250": "Headline: ...\\nBody: ...\\nCTA: ...\\nDesign Notes: ...",
  "728x90": "Headline: ...\\nBody: ...\\nCTA: ...\\nDesign Notes: ...",
  "160x600": "Headline: ...\\nBody: ...\\nCTA: ...\\nDesign Notes: ...",
  "320x50": "Headline: ...\\nCTA: ...\\nDesign Notes: ..."
}}"""

        raw = await llm(prompt, system="You are a digital advertising copywriter. Respond only with valid JSON.", json_mode=True)
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict):
            return {k: str(v) for k, v in parsed.items()}
        return {}

    async def regenerate_asset(
        self,
        campaign_result: CampaignResult,
        asset_index: int,
        modifications: Dict[str, Any] = None
    ) -> CompleteAsset:
        """
        Regenerate a specific asset with optional modifications.

        Args:
            campaign_result: Previous campaign result
            asset_index: Index of asset to regenerate
            modifications: Changes to apply to the spec

        Returns:
            New CompleteAsset
        """
        if not campaign_result.selected_concept:
            raise ValueError("No concept available")

        specs = campaign_result.selected_concept.asset_specs
        if asset_index >= len(specs):
            raise ValueError(f"Asset index {asset_index} out of range")

        spec = specs[asset_index].copy()

        # Apply modifications
        if modifications:
            spec.update(modifications)

        brand_data = campaign_result.brand_analysis or {}

        return await self.asset_generator.generate_asset(
            asset_spec=spec,
            brand_data=brand_data
        )

    async def switch_concept(
        self,
        campaign_result: CampaignResult,
        concept_index: int,
        platforms: Optional[List[str]] = None
    ) -> CampaignResult:
        """
        Switch to a different creative concept and regenerate assets.

        Args:
            campaign_result: Previous campaign result
            concept_index: Index of concept to switch to
            platforms: Platforms to generate for

        Returns:
            Updated CampaignResult
        """
        if concept_index >= len(campaign_result.concepts):
            raise ValueError(f"Concept index {concept_index} out of range")

        campaign_result.selected_concept = campaign_result.concepts[concept_index]

        # Build knowledge base
        knowledge_base = {
            "brand": campaign_result.brand_analysis or {},
            "market": campaign_result.market_research or {}
        }

        # Generate new assets
        campaign_result.assets = await self._execute_production(
            campaign_result.selected_concept,
            knowledge_base,
            platforms
        )

        return campaign_result

    async def close(self):
        """Close all services."""
        await self.firecrawl.close()
        await self.perplexity.close()
        await self.brief_generator.close()
        await self.creative_director.close()
        await self.asset_generator.close()


# Convenience function for quick campaign execution
async def run_campaign(
    campaign_request: Dict[str, Any],
    api_keys: Dict[str, str],
    knowledge_base: Optional[Dict[str, Any]] = None,
    output_dir: str = "outputs",
    progress_callback = None
) -> CampaignResult:
    """
    Quick campaign execution function.

    Args:
        campaign_request: Campaign parameters
        api_keys: Dict with keys: openrouter, firecrawl, perplexity, segmind, elevenlabs
        knowledge_base: Pre-existing brand knowledge
        output_dir: Where to save generated assets
        progress_callback: Async callback for progress updates

    Returns:
        CampaignResult
    """
    orchestrator = CampaignOrchestrator(
        openrouter_api_key=api_keys["openrouter"],
        firecrawl_api_key=api_keys["firecrawl"],
        perplexity_api_key=api_keys["perplexity"],
        segmind_api_key=api_keys["segmind"],
        elevenlabs_api_key=api_keys["elevenlabs"],
        output_dir=output_dir
    )

    if progress_callback:
        orchestrator.set_progress_callback(progress_callback)

    try:
        return await orchestrator.execute_campaign(
            campaign_request=campaign_request,
            knowledge_base=knowledge_base
        )
    finally:
        await orchestrator.close()
