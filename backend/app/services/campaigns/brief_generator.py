"""
AI-Powered Brief Generator.

Generates McKinsey/Ogilvy-quality creative briefs using:
- Knowledge Base (brand, market, audience data)
- Claude Opus for strategic thinking
- Perplexity for real-time market intelligence

Enhanced with dynamic intelligence loading for deep domain expertise.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import logging

from ..ai.openrouter import OpenRouterService, llm, llm_json

# Import intelligence layer
try:
    from ...intelligence import load_department, load_format, load_rubric, get_department_prompt
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CampaignObjective:
    """A specific, measurable campaign objective."""
    objective: str
    metric: str
    target: str
    timeframe: str


@dataclass
class KeyMessage:
    """A key message with supporting proof points."""
    message: str
    proof_points: List[str]
    emotional_hook: str
    rational_benefit: str


@dataclass
class CreativeTerritory:
    """A creative territory/direction for the campaign."""
    name: str
    concept: str
    visual_direction: str
    tone: str
    tagline_options: List[str]
    risk_level: str  # low, medium, high
    rationale: str


@dataclass
class ChannelStrategy:
    """Strategy for a specific channel."""
    channel: str
    role: str  # awareness, consideration, conversion
    formats: List[str]
    frequency: str
    budget_allocation: str  # percentage


@dataclass
class CampaignBrief:
    """Complete campaign brief - the strategic foundation."""
    # Meta
    campaign_name: str
    campaign_type: str
    created_at: datetime = field(default_factory=datetime.now)
    version: int = 1

    # Executive Summary
    executive_summary: str = ""

    # Background & Context
    business_context: str = ""
    market_situation: str = ""
    competitive_landscape: str = ""
    brand_position: str = ""

    # Strategic Framework
    objectives: List[CampaignObjective] = field(default_factory=list)
    target_audience: Dict[str, Any] = field(default_factory=dict)
    key_insight: str = ""
    strategic_proposition: str = ""

    # Messaging
    key_messages: List[KeyMessage] = field(default_factory=list)
    tone_of_voice: List[str] = field(default_factory=list)
    mandatory_inclusions: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)

    # Creative Direction
    creative_territories: List[CreativeTerritory] = field(default_factory=list)

    # Channel Strategy
    channel_strategy: List[ChannelStrategy] = field(default_factory=list)

    # Budget & Timeline
    budget: Dict[str, Any] = field(default_factory=dict)
    timeline: Dict[str, Any] = field(default_factory=dict)

    # Success Metrics
    success_metrics: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "campaign_name": self.campaign_name,
            "campaign_type": self.campaign_type,
            "created_at": self.created_at.isoformat(),
            "version": self.version,
            "executive_summary": self.executive_summary,
            "business_context": self.business_context,
            "market_situation": self.market_situation,
            "competitive_landscape": self.competitive_landscape,
            "brand_position": self.brand_position,
            "objectives": [
                {
                    "objective": o.objective,
                    "metric": o.metric,
                    "target": o.target,
                    "timeframe": o.timeframe
                }
                for o in self.objectives
            ],
            "target_audience": self.target_audience,
            "key_insight": self.key_insight,
            "strategic_proposition": self.strategic_proposition,
            "key_messages": [
                {
                    "message": m.message,
                    "proof_points": m.proof_points,
                    "emotional_hook": m.emotional_hook,
                    "rational_benefit": m.rational_benefit
                }
                for m in self.key_messages
            ],
            "tone_of_voice": self.tone_of_voice,
            "mandatory_inclusions": self.mandatory_inclusions,
            "restrictions": self.restrictions,
            "creative_territories": [
                {
                    "name": t.name,
                    "concept": t.concept,
                    "visual_direction": t.visual_direction,
                    "tone": t.tone,
                    "tagline_options": t.tagline_options,
                    "risk_level": t.risk_level,
                    "rationale": t.rationale
                }
                for t in self.creative_territories
            ],
            "channel_strategy": [
                {
                    "channel": c.channel,
                    "role": c.role,
                    "formats": c.formats,
                    "frequency": c.frequency,
                    "budget_allocation": c.budget_allocation
                }
                for c in self.channel_strategy
            ],
            "budget": self.budget,
            "timeline": self.timeline,
            "success_metrics": self.success_metrics
        }


class BriefGenerator:
    """
    Generates premium-quality campaign briefs.

    The brief is the strategic foundation for everything that follows.
    It must be thorough, insightful, and actionable.

    Enhanced with dynamic intelligence loading for deep domain expertise.
    """

    # Fallback system prompt if intelligence layer is not available
    _FALLBACK_PROMPT = """You are a world-class strategy director at a top-tier creative agency
(think Ogilvy, BBDO, Wieden+Kennedy). You've worked on global campaigns for Fortune 500 brands
and have deep expertise in brand strategy, consumer psychology, and creative development.

Your briefs are renowned for:
- Deep consumer insights that reveal unexpected truths
- Clear strategic frameworks that inspire creative teams
- Measurable objectives tied to real business outcomes
- Creative territories that push boundaries while staying on-brand

You write with precision, clarity, and strategic rigor. No fluff, no jargon - just sharp thinking
that drives results. Every recommendation is grounded in data and consumer understanding."""

    def __init__(self, openrouter_api_key: str, perplexity_api_key: Optional[str] = None):
        self.llm = OpenRouterService(api_key=openrouter_api_key)
        self.perplexity_api_key = perplexity_api_key
        self._system_prompt = self._load_intelligence()

    def _load_intelligence(self) -> str:
        """Load deep domain expertise from intelligence layer."""
        if not INTELLIGENCE_AVAILABLE:
            logger.warning("Intelligence layer not available, using fallback prompt")
            return self._FALLBACK_PROMPT

        try:
            # Load strategist expertise with strategy quality rubric
            prompt = get_department_prompt(
                department="strategist",
                include_rubric=True
            )
            if prompt:
                logger.info("Loaded strategist intelligence for brief generation")
                return prompt

            return self._FALLBACK_PROMPT
        except Exception as e:
            logger.error(f"Failed to load intelligence: {e}")
            return self._FALLBACK_PROMPT

    @property
    def SYSTEM_PROMPT(self) -> str:
        """Dynamic system prompt property that uses loaded intelligence."""
        return self._system_prompt

    async def generate_brief(
        self,
        campaign_type: str,
        user_request: str,
        knowledge_base: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> CampaignBrief:
        """
        Generate a complete campaign brief.

        Args:
            campaign_type: Type of campaign (product_launch, brand_awareness, etc.)
            user_request: What the user asked for
            knowledge_base: Brand, market, audience data from onboarding
            additional_context: Any extra context from the conversation

        Returns:
            Complete CampaignBrief object
        """
        # Build comprehensive context
        context = self._build_context(knowledge_base, additional_context)

        # Generate brief sections in parallel for speed
        # But we'll do it sequentially for quality and coherence

        # 1. Strategic Foundation
        strategic_foundation = await self._generate_strategic_foundation(
            campaign_type, user_request, context
        )

        # 2. Objectives & Audience
        objectives_audience = await self._generate_objectives_audience(
            campaign_type, user_request, context, strategic_foundation
        )

        # 3. Messaging Framework
        messaging = await self._generate_messaging(
            campaign_type, context, strategic_foundation, objectives_audience
        )

        # 4. Creative Territories
        territories = await self._generate_creative_territories(
            campaign_type, context, strategic_foundation, messaging
        )

        # 5. Channel Strategy
        channels = await self._generate_channel_strategy(
            campaign_type, context, objectives_audience
        )

        # 6. Executive Summary (written last, summarizes everything)
        executive_summary = await self._generate_executive_summary(
            campaign_type, strategic_foundation, objectives_audience, messaging, territories
        )

        # Assemble the brief
        brief = CampaignBrief(
            campaign_name=strategic_foundation.get("campaign_name", "Untitled Campaign"),
            campaign_type=campaign_type,
            executive_summary=executive_summary,
            business_context=strategic_foundation.get("business_context", ""),
            market_situation=strategic_foundation.get("market_situation", ""),
            competitive_landscape=strategic_foundation.get("competitive_landscape", ""),
            brand_position=strategic_foundation.get("brand_position", ""),
            objectives=[
                CampaignObjective(**obj)
                for obj in objectives_audience.get("objectives", [])
            ],
            target_audience=objectives_audience.get("target_audience", {}),
            key_insight=strategic_foundation.get("key_insight", ""),
            strategic_proposition=strategic_foundation.get("strategic_proposition", ""),
            key_messages=[
                KeyMessage(**msg)
                for msg in messaging.get("key_messages", [])
            ],
            tone_of_voice=messaging.get("tone_of_voice", []),
            mandatory_inclusions=messaging.get("mandatory_inclusions", []),
            restrictions=messaging.get("restrictions", []),
            creative_territories=[
                CreativeTerritory(**territory)
                for territory in territories.get("territories", [])
            ],
            channel_strategy=[
                ChannelStrategy(**channel)
                for channel in channels.get("channels", [])
            ],
            budget=channels.get("budget", {}),
            timeline=channels.get("timeline", {}),
            success_metrics=objectives_audience.get("success_metrics", [])
        )

        return brief

    def _build_context(
        self,
        knowledge_base: Dict[str, Any],
        additional_context: Optional[str]
    ) -> str:
        """Build comprehensive context from knowledge base."""
        sections = []

        # Brand information
        brand = knowledge_base.get("brand", {})
        if brand:
            sections.append(f"""
## Brand Profile
- **Name**: {brand.get('name', 'Unknown')}
- **Tagline**: {brand.get('tagline', 'N/A')}
- **Description**: {brand.get('description', 'N/A')}
- **Values**: {', '.join(brand.get('values', []))}
- **Voice**: {', '.join(brand.get('voice', {}).get('tone', []))}
""")

        # Market information
        market = knowledge_base.get("market", {})
        if market:
            competitors = market.get("competitors", [])
            if isinstance(competitors, dict):
                competitors = list(competitors.values()) if competitors else []
            if not isinstance(competitors, list):
                competitors = []
            competitor_summary = "\n".join([
                f"  - {c.get('name', 'Unknown') if isinstance(c, dict) else str(c)}: {c.get('positioning', 'N/A') if isinstance(c, dict) else 'N/A'}"
                for c in competitors[:5]
            ])
            sections.append(f"""
## Market Context
- **Industry**: {market.get('industry', 'Unknown')}
- **Market Position**: {market.get('market_position', 'N/A')}
- **Key Competitors**:
{competitor_summary}
- **Opportunities**: {', '.join(list(market.get('opportunities', []))[:3] if isinstance(market.get('opportunities', []), list) else [])}
- **Threats**: {', '.join(list(market.get('threats', []))[:3] if isinstance(market.get('threats', []), list) else [])}
""")

        # Audience information
        audiences = knowledge_base.get("audiences", {})
        if audiences:
            segments = audiences.get("segments", [])
            for segment in segments[:2]:
                sections.append(f"""
## Target Audience: {segment.get('name', 'Unknown')}
- **Demographics**: {segment.get('demographics', {})}
- **Pain Points**: {', '.join(segment.get('pain_points', [])[:3])}
- **Goals**: {', '.join(segment.get('goals', [])[:3])}
- **Preferred Channels**: {', '.join(segment.get('preferred_channels', [])[:3])}
""")

        # Offerings
        offerings = knowledge_base.get("offerings", {})
        if offerings:
            products = offerings.get("products", [])
            if products:
                sections.append(f"""
## Products/Services
{chr(10).join([f"- {p.get('name', 'Unknown')}: {p.get('description', 'N/A')}" for p in products[:5]])}
""")

        # Additional context
        if additional_context:
            sections.append(f"""
## Additional Context
{additional_context}
""")

        return "\n".join(sections)

    async def _generate_strategic_foundation(
        self,
        campaign_type: str,
        user_request: str,
        context: str
    ) -> Dict[str, Any]:
        """Generate the strategic foundation of the brief."""
        prompt = f"""Based on the following brand context and campaign request, develop the strategic foundation.

{context}

## Campaign Request
Type: {campaign_type}
Request: {user_request}

Generate:
1. A compelling campaign name
2. Business context (why this campaign, why now)
3. Market situation analysis (current state, trends affecting this campaign)
4. Competitive landscape (how competitors are positioning, white space opportunities)
5. Brand position (how the brand should show up in this campaign)
6. Key consumer insight (the unexpected truth that will drive the creative)
7. Strategic proposition (the single-minded idea the campaign will be built on)

Return as JSON:
{{
    "campaign_name": "...",
    "business_context": "2-3 paragraphs",
    "market_situation": "2-3 paragraphs",
    "competitive_landscape": "2-3 paragraphs",
    "brand_position": "1-2 paragraphs",
    "key_insight": "A sharp, unexpected consumer truth in 1-2 sentences",
    "strategic_proposition": "The single idea in one powerful sentence"
}}"""

        return await self.llm.complete_json(prompt, self.SYSTEM_PROMPT)

    async def _generate_objectives_audience(
        self,
        campaign_type: str,
        user_request: str,
        context: str,
        strategic_foundation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate objectives and refined audience definition."""
        prompt = f"""Based on the strategic foundation, define specific objectives and target audience.

## Strategic Foundation
- Campaign: {strategic_foundation.get('campaign_name')}
- Proposition: {strategic_foundation.get('strategic_proposition')}
- Key Insight: {strategic_foundation.get('key_insight')}

## Brand Context
{context}

## Campaign Request
{user_request}

Generate:
1. 3-4 SMART objectives (Specific, Measurable, Achievable, Relevant, Time-bound)
2. Detailed target audience profile
3. Success metrics for each objective

Return as JSON:
{{
    "objectives": [
        {{
            "objective": "What we want to achieve",
            "metric": "How we'll measure it",
            "target": "Specific number/percentage",
            "timeframe": "By when"
        }}
    ],
    "target_audience": {{
        "primary_segment": "Name",
        "demographics": "Age, location, income, etc.",
        "psychographics": "Values, attitudes, lifestyle",
        "behaviors": "Shopping habits, media consumption",
        "pain_points": ["..."],
        "aspirations": ["..."],
        "media_habits": "Where they spend time",
        "purchase_drivers": "What influences their decisions"
    }},
    "success_metrics": [
        {{
            "metric": "Name",
            "current_baseline": "Where we are now",
            "target": "Where we want to be",
            "measurement_method": "How we'll track it"
        }}
    ]
}}"""

        return await self.llm.complete_json(prompt, self.SYSTEM_PROMPT)

    async def _generate_messaging(
        self,
        campaign_type: str,
        context: str,
        strategic_foundation: Dict[str, Any],
        objectives_audience: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate the messaging framework."""
        prompt = f"""Develop a comprehensive messaging framework for this campaign.

## Strategic Foundation
- Campaign: {strategic_foundation.get('campaign_name')}
- Proposition: {strategic_foundation.get('strategic_proposition')}
- Key Insight: {strategic_foundation.get('key_insight')}

## Target Audience
{objectives_audience.get('target_audience', {})}

## Brand Context
{context}

Generate:
1. 3-4 key messages, each with proof points and emotional/rational hooks
2. Tone of voice guidelines (5-7 adjectives)
3. Mandatory inclusions (brand elements that must appear)
4. Restrictions (what to avoid)

Return as JSON:
{{
    "key_messages": [
        {{
            "message": "The core message in consumer language",
            "proof_points": ["Evidence that supports this message", "..."],
            "emotional_hook": "The feeling this message evokes",
            "rational_benefit": "The logical reason to believe"
        }}
    ],
    "tone_of_voice": ["adjective1", "adjective2", "..."],
    "mandatory_inclusions": ["Brand element 1", "..."],
    "restrictions": ["What to avoid", "..."]
}}"""

        return await self.llm.complete_json(prompt, self.SYSTEM_PROMPT)

    async def _generate_creative_territories(
        self,
        campaign_type: str,
        context: str,
        strategic_foundation: Dict[str, Any],
        messaging: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate creative territories for the campaign."""
        prompt = f"""Develop 3 distinct creative territories for this campaign.

## Strategic Foundation
- Campaign: {strategic_foundation.get('campaign_name')}
- Proposition: {strategic_foundation.get('strategic_proposition')}
- Key Insight: {strategic_foundation.get('key_insight')}

## Messaging
- Key Messages: {[m.get('message') for m in messaging.get('key_messages', [])]}
- Tone: {messaging.get('tone_of_voice', [])}

## Brand Context
{context}

Generate 3 creative territories that:
- Are strategically sound but creatively brave
- Range from safe (evolution) to bold (revolution)
- Could work across all channels
- Are distinct from each other

Return as JSON:
{{
    "territories": [
        {{
            "name": "Short, memorable name for the territory",
            "concept": "2-3 sentences describing the creative idea",
            "visual_direction": "What it looks like - imagery, style, mood",
            "tone": "How it sounds and feels",
            "tagline_options": ["Option 1", "Option 2", "Option 3"],
            "risk_level": "low/medium/high",
            "rationale": "Why this territory could work"
        }}
    ]
}}"""

        return await self.llm.complete_json(prompt, self.SYSTEM_PROMPT)

    async def _generate_channel_strategy(
        self,
        campaign_type: str,
        context: str,
        objectives_audience: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate channel strategy and budget allocation."""
        audience = objectives_audience.get("target_audience", {})

        prompt = f"""Develop a channel strategy for this campaign.

## Target Audience
{audience}

## Objectives
{objectives_audience.get('objectives', [])}

## Brand Context
{context}

Generate:
1. Channel mix with role, formats, and budget allocation
2. High-level budget framework
3. Campaign timeline

Return as JSON:
{{
    "channels": [
        {{
            "channel": "Channel name (e.g., Instagram, YouTube, OOH)",
            "role": "awareness/consideration/conversion",
            "formats": ["Format 1", "Format 2"],
            "frequency": "How often/how much",
            "budget_allocation": "Percentage of budget"
        }}
    ],
    "budget": {{
        "total_range": "Recommended budget range",
        "production": "Percentage for production",
        "media": "Percentage for media",
        "contingency": "Percentage for contingency"
    }},
    "timeline": {{
        "total_duration": "Campaign length",
        "phases": [
            {{
                "name": "Phase name",
                "duration": "Length",
                "focus": "What happens in this phase"
            }}
        ]
    }}
}}"""

        return await self.llm.complete_json(prompt, self.SYSTEM_PROMPT)

    async def _generate_executive_summary(
        self,
        campaign_type: str,
        strategic_foundation: Dict[str, Any],
        objectives_audience: Dict[str, Any],
        messaging: Dict[str, Any],
        territories: Dict[str, Any]
    ) -> str:
        """Generate the executive summary that ties everything together."""
        prompt = f"""Write a compelling executive summary for this campaign brief.

## Campaign: {strategic_foundation.get('campaign_name')}

## Strategic Proposition
{strategic_foundation.get('strategic_proposition')}

## Key Insight
{strategic_foundation.get('key_insight')}

## Objectives
{[obj.get('objective') for obj in objectives_audience.get('objectives', [])]}

## Creative Territories
{[t.get('name') + ': ' + t.get('concept') for t in territories.get('territories', [])]}

Write a 2-3 paragraph executive summary that:
1. Opens with the business challenge and opportunity
2. Presents the strategic solution and key insight
3. Previews the creative direction and expected outcomes

Make it compelling enough that a busy CMO would want to read the full brief.
Write in a confident, strategic tone. No bullet points - flowing prose only."""

        return await self.llm.complete(prompt, self.SYSTEM_PROMPT)

    async def close(self):
        """Close resources."""
        await self.llm.close()
