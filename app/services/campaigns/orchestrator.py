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

    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None

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
        self.brief_generator = BriefGenerator(api_key=openrouter_api_key)
        self.creative_director = CreativeDirector(api_key=openrouter_api_key)
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
                {"concept_names": [c.name for c in concepts]}
            )

            # Phase 4: Production (Asset Generation)
            if result.selected_concept:
                await self._emit_progress(
                    CampaignPhase.PRODUCTION, 0,
                    f"Producing assets for '{result.selected_concept.name}'..."
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
            logger.error(f"Campaign execution failed: {e}")
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
            "audiences": [
                market_research.get("audience", {})
            ],
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

        # Use knowledge base for context
        brand_data = knowledge_base.get("brand", {})
        market_data = knowledge_base.get("market", {})

        await self._emit_progress(
            CampaignPhase.STRATEGY, 50,
            "Crafting strategic brief..."
        )

        brief = await self.brief_generator.generate_brief(
            objective=objective,
            brand_data=brand_data,
            market_data=market_data,
            target_audience=target_audience,
            product_focus=product_focus,
            budget_constraints=self._budget_to_constraints(budget_tier),
            timeline=timeline
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
                f"Developing concept for '{territory.get('name', 'Primary')}'..."
            )

            concept = await self.creative_director.develop_concept(
                brief=brief,
                territory=territory,
                brand_data=brand_data
            )
            concepts.append(concept)

            # Generate additional concepts for other territories
            for i, alt_territory in enumerate(brief.creative_territories[1:3], 2):
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

        return concepts

    async def _execute_production(
        self,
        concept: CreativeConcept,
        knowledge_base: Dict[str, Any],
        platforms: Optional[List[str]] = None
    ) -> List[CompleteAsset]:
        """Execute production phase - generate assets."""
        brand_data = knowledge_base.get("brand", {})

        # Get asset specs from concept
        asset_specs = concept.asset_specs

        # Filter by platform if specified
        if platforms:
            asset_specs = [
                spec for spec in asset_specs
                if spec.get("platform", "").lower() in [p.lower() for p in platforms]
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
