"""
AI Creative Director.

Takes a campaign brief and creative territory, then generates:
- Detailed creative concepts
- Copy variations for different formats
- Art direction guidelines
- Asset specifications

Enhanced with dynamic intelligence loading for deep domain expertise.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import logging

from ..ai.openrouter import OpenRouterService

# Import intelligence layer
try:
    from ...intelligence import load_department, load_format, load_rubric, get_department_prompt
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CopyVariation:
    """A piece of copy for a specific format."""
    format: str  # headline, body, cta, social_post, email_subject, etc.
    content: str
    character_count: int
    tone: str
    notes: str = ""


@dataclass
class VisualConcept:
    """A visual concept for an asset."""
    description: str
    style: str
    mood: str
    color_palette: List[str]
    imagery_type: str  # photography, illustration, 3d, mixed
    composition_notes: str
    reference_keywords: List[str]  # For image generation prompts


@dataclass
class AssetSpec:
    """Specification for a single asset."""
    asset_type: str  # social_post, banner, email, video, etc.
    platform: str
    dimensions: str
    copy: List[CopyVariation]
    visual: VisualConcept
    cta: str
    notes: str = ""


@dataclass
class CreativeConcept:
    """A fully developed creative concept."""
    territory_name: str
    concept_name: str
    tagline: str
    concept_statement: str
    key_visual_idea: str
    tone_description: str
    assets: List[AssetSpec] = field(default_factory=list)
    campaign_narrative: str = ""
    execution_notes: str = ""


class CreativeDirector:
    """
    The AI Creative Director develops creative territories into
    fully realized concepts with asset specifications.

    Enhanced with dynamic intelligence loading for deep domain expertise.
    """

    # Fallback system prompt if intelligence layer is not available
    _FALLBACK_PROMPT = """You are an award-winning Executive Creative Director with 20+ years
at top agencies (Wieden+Kennedy, Droga5, 72andSunny). You've created iconic campaigns
that became part of culture.

Your creative philosophy:
- Ideas should be simple enough to explain in one sentence, rich enough to execute infinitely
- Every piece of work should earn attention, not demand it
- Great creative makes people feel something, then do something
- Craft matters - the details are not the details, they make the design

You think in systems, not just executions. You see how an idea can live across channels
while maintaining its core truth. You push for brave work but know when to pick battles.

Your feedback is direct, constructive, and always in service of making the work better."""

    def __init__(self, openrouter_api_key: str):
        self.llm = OpenRouterService(api_key=openrouter_api_key)
        self._system_prompt = self._load_intelligence()

    def _load_intelligence(self) -> str:
        """Load deep domain expertise from intelligence layer."""
        if not INTELLIGENCE_AVAILABLE:
            logger.warning("Intelligence layer not available, using fallback prompt")
            return self._FALLBACK_PROMPT

        try:
            # Load creative director expertise with concept development focus
            prompt = get_department_prompt(
                department="creative_director",
                include_rubric=True
            )
            if prompt:
                logger.info("Loaded creative director intelligence")
                return prompt

            # Try concept developer as alternative
            prompt = get_department_prompt(
                department="concept_developer",
                include_rubric=True
            )
            if prompt:
                logger.info("Loaded concept developer intelligence")
                return prompt

            return self._FALLBACK_PROMPT
        except Exception as e:
            logger.error(f"Failed to load intelligence: {e}")
            return self._FALLBACK_PROMPT

    @property
    def SYSTEM_PROMPT(self) -> str:
        """Dynamic system prompt property that uses loaded intelligence."""
        return self._system_prompt

    async def develop_concept(
        self,
        brief: Dict[str, Any],
        territory: Dict[str, Any],
        asset_types: List[str]
    ) -> CreativeConcept:
        """
        Develop a creative territory into a full concept with assets.

        Args:
            brief: The campaign brief
            territory: The selected creative territory
            asset_types: Types of assets to generate specs for

        Returns:
            Fully developed CreativeConcept
        """
        # 1. Develop the core concept
        core_concept = await self._develop_core_concept(brief, territory)

        # 2. Create the campaign narrative
        narrative = await self._create_narrative(brief, territory, core_concept)

        # 3. Generate asset specifications
        assets = []
        for asset_type in asset_types:
            asset_spec = await self._generate_asset_spec(
                brief, territory, core_concept, asset_type
            )
            assets.append(asset_spec)

        return CreativeConcept(
            territory_name=territory.get("name", ""),
            concept_name=core_concept.get("concept_name", ""),
            tagline=core_concept.get("tagline", ""),
            concept_statement=core_concept.get("concept_statement", ""),
            key_visual_idea=core_concept.get("key_visual_idea", ""),
            tone_description=core_concept.get("tone_description", ""),
            assets=assets,
            campaign_narrative=narrative,
            execution_notes=core_concept.get("execution_notes", "")
        )

    async def _develop_core_concept(
        self,
        brief: Dict[str, Any],
        territory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Develop the core creative concept from a territory."""
        prompt = f"""Develop this creative territory into a fully realized concept.

## Campaign Brief
- Campaign: {brief.get('campaign_name', 'Untitled')}
- Proposition: {brief.get('strategic_proposition', '')}
- Key Insight: {brief.get('key_insight', '')}
- Target Audience: {brief.get('target_audience', {})}
- Tone: {brief.get('tone_of_voice', [])}

## Creative Territory
- Name: {territory.get('name', '')}
- Concept: {territory.get('concept', '')}
- Visual Direction: {territory.get('visual_direction', '')}
- Tone: {territory.get('tone', '')}
- Tagline Options: {territory.get('tagline_options', [])}

Develop this into a complete creative concept:

Return as JSON:
{{
    "concept_name": "A memorable internal name for this concept",
    "tagline": "The final, polished campaign tagline",
    "concept_statement": "2-3 sentences that capture the creative idea - what it is, why it works",
    "key_visual_idea": "The signature visual element or treatment that makes this campaign recognizable",
    "tone_description": "How the campaign should feel - specific and evocative",
    "execution_notes": "Key principles for bringing this to life across channels"
}}"""

        return await self.llm.complete_json(prompt, self.SYSTEM_PROMPT)

    async def _create_narrative(
        self,
        brief: Dict[str, Any],
        territory: Dict[str, Any],
        core_concept: Dict[str, Any]
    ) -> str:
        """Create the campaign narrative - how the story unfolds."""
        prompt = f"""Write the campaign narrative - how this creative idea unfolds across touchpoints.

## Concept
- Name: {core_concept.get('concept_name', '')}
- Tagline: {core_concept.get('tagline', '')}
- Idea: {core_concept.get('concept_statement', '')}
- Visual: {core_concept.get('key_visual_idea', '')}

## Brief Context
- Proposition: {brief.get('strategic_proposition', '')}
- Key Messages: {[m.get('message', '') for m in brief.get('key_messages', [])]}
- Channels: {[c.get('channel', '') for c in brief.get('channel_strategy', [])]}

Write a compelling narrative (3-4 paragraphs) that describes:
1. How we grab attention and introduce the idea
2. How we build the story and deepen engagement
3. How we drive action and conversion
4. How the campaign evolves over time

Write this as if presenting to a client - confident, inspiring, specific."""

        return await self.llm.complete(prompt, self.SYSTEM_PROMPT)

    async def _generate_asset_spec(
        self,
        brief: Dict[str, Any],
        territory: Dict[str, Any],
        core_concept: Dict[str, Any],
        asset_type: str
    ) -> AssetSpec:
        """Generate specifications for a specific asset type."""
        # Get format-specific requirements
        format_specs = self._get_format_specs(asset_type)

        prompt = f"""Generate detailed specifications for a {asset_type} asset.

## Creative Concept
- Tagline: {core_concept.get('tagline', '')}
- Concept: {core_concept.get('concept_statement', '')}
- Key Visual: {core_concept.get('key_visual_idea', '')}
- Tone: {core_concept.get('tone_description', '')}

## Brand Context
- Voice: {brief.get('tone_of_voice', [])}
- Mandatory Inclusions: {brief.get('mandatory_inclusions', [])}
- Restrictions: {brief.get('restrictions', [])}

## Format Specifications
{format_specs}

Generate complete asset specifications:

Return as JSON:
{{
    "platform": "Primary platform for this asset",
    "dimensions": "Size/format (e.g., 1080x1080, 16:9)",
    "copy": [
        {{
            "format": "headline/body/cta/caption",
            "content": "The actual copy",
            "character_count": 0,
            "tone": "How this specific piece should feel",
            "notes": "Any special considerations"
        }}
    ],
    "visual": {{
        "description": "Detailed description of the visual",
        "style": "Photography/illustration/3D/etc.",
        "mood": "The emotional quality of the visual",
        "color_palette": ["#hex1", "#hex2", "#hex3"],
        "imagery_type": "What kind of imagery",
        "composition_notes": "How elements are arranged",
        "reference_keywords": ["keyword1", "keyword2", "for image generation"]
    }},
    "cta": "The call-to-action",
    "notes": "Additional execution notes"
}}"""

        result = await self.llm.complete_json(prompt, self.SYSTEM_PROMPT)

        return AssetSpec(
            asset_type=asset_type,
            platform=result.get("platform", ""),
            dimensions=result.get("dimensions", ""),
            copy=[
                CopyVariation(
                    format=c.get("format", ""),
                    content=c.get("content", ""),
                    character_count=len(c.get("content", "")),
                    tone=c.get("tone", ""),
                    notes=c.get("notes", "")
                )
                for c in result.get("copy", [])
            ],
            visual=VisualConcept(
                description=result.get("visual", {}).get("description", ""),
                style=result.get("visual", {}).get("style", ""),
                mood=result.get("visual", {}).get("mood", ""),
                color_palette=result.get("visual", {}).get("color_palette", []),
                imagery_type=result.get("visual", {}).get("imagery_type", ""),
                composition_notes=result.get("visual", {}).get("composition_notes", ""),
                reference_keywords=result.get("visual", {}).get("reference_keywords", [])
            ),
            cta=result.get("cta", ""),
            notes=result.get("notes", "")
        )

    def _get_format_specs(self, asset_type: str) -> str:
        """
        Get format-specific requirements and best practices.

        Enhanced to use the intelligence layer's deep format knowledge
        when available, falling back to basic specs if not.
        """
        # Try to load from intelligence layer first
        if INTELLIGENCE_AVAILABLE:
            try:
                # Map asset type to format name
                format_mapping = {
                    "instagram_post": "instagram",
                    "instagram_story": "instagram",
                    "instagram_reel": "instagram",
                    "instagram_carousel": "instagram",
                    "tiktok_video": "tiktok",
                    "tiktok_post": "tiktok",
                    "linkedin_post": "linkedin",
                    "twitter_post": "twitter",
                    "email_header": "email",
                    "email_body": "email",
                    "blog_post": "blog",
                    "display_banner": "ads",
                    "video_ad": "ads",
                    "landing_page_hero": "landing_page",
                    "landing_page": "landing_page",
                }

                format_name = format_mapping.get(asset_type)
                if format_name:
                    format_content = load_format(format_name)
                    if format_content:
                        # Extract relevant section for this specific asset type
                        logger.debug(f"Loaded format intelligence for {format_name}")
                        return format_content[:3000]  # Limit to avoid token overflow
            except Exception as e:
                logger.warning(f"Failed to load format intelligence: {e}")

        # Fallback to basic specs
        specs = {
            "instagram_post": """
- Format: 1080x1080 (square) or 1080x1350 (portrait)
- Caption: Up to 2,200 characters (optimal 125-150)
- Hashtags: 3-5 relevant hashtags
- Must stop the scroll in first 0.5 seconds
- Text overlay should be minimal (under 20% of image)
""",
            "instagram_story": """
- Format: 1080x1920 (9:16 vertical)
- Duration: Up to 15 seconds if video
- Include interactive elements (polls, questions, links)
- Key message in top 2/3 (bottom is covered by UI)
- Designed for sound-off viewing
""",
            "instagram_reel": """
- Format: 1080x1920 (9:16 vertical)
- Duration: 15-30 seconds optimal
- Hook in first 1-2 seconds
- Native, authentic feel preferred over polished
- Must work with sound on AND off
- End with clear CTA
""",
            "facebook_post": """
- Image: 1200x630 (1.91:1) or 1080x1080
- Copy: 1-2 sentences for engagement (full text can be longer)
- Include clear CTA
- Optimize for engagement (comments, shares)
""",
            "linkedin_post": """
- Image: 1200x627 or 1080x1080
- Copy: Professional tone, 1-3 paragraphs
- No hashtag overload (3-5 max)
- Thought leadership angle preferred
- Include a question or discussion prompt
""",
            "twitter_post": """
- Image: 1200x675 (16:9) or 1080x1080
- Copy: Under 280 characters, punchy
- Conversational, witty tone works well
- 1-2 hashtags maximum
- Consider thread potential for complex topics
""",
            "youtube_thumbnail": """
- Format: 1280x720 (16:9)
- High contrast, bold colors
- Face close-ups perform well
- Large, readable text (3-4 words max)
- Must be compelling at small sizes
""",
            "email_header": """
- Format: 600px wide (height varies, typically 200-400px)
- Key message visible without scrolling
- CTA above the fold
- Mobile-first design
- Alt text for images
""",
            "display_banner": """
- Multiple sizes: 300x250, 728x90, 160x600, 320x50
- Clear brand, message, CTA
- Animation if appropriate (15-30 seconds max, loops)
- File size optimized for fast loading
- Works with and without animation
""",
            "video_ad": """
- Format: 16:9 (horizontal) or 9:16 (vertical for social)
- Duration: 15-30 seconds
- Hook in first 3 seconds
- Branding early (in case of skip)
- Captions/subtitles required
- Clear CTA at end
""",
            "landing_page_hero": """
- Format: Full-width (typically 1920px wide, 600-800px tall)
- Clear headline and value proposition
- Single primary CTA
- Mobile responsive design
- Fast loading (optimize image size)
""",
            "print_ad": """
- Format: Varies (full page, half page, etc.)
- High resolution (300 DPI minimum)
- Clear visual hierarchy
- Logo and CTA placement considered
- Works in B&W if needed
"""
        }

        return specs.get(asset_type, """
- Standard digital format
- Clear brand presence
- Compelling visual
- Copy appropriate for format
- Clear call-to-action
""")

    async def generate_copy_variations(
        self,
        brief: Dict[str, Any],
        concept: CreativeConcept,
        copy_type: str,
        count: int = 5
    ) -> List[CopyVariation]:
        """Generate multiple copy variations for A/B testing."""
        prompt = f"""Generate {count} distinct copy variations for {copy_type}.

## Creative Concept
- Tagline: {concept.tagline}
- Concept: {concept.concept_statement}
- Tone: {concept.tone_description}

## Brief Context
- Key Messages: {[m.get('message', '') for m in brief.get('key_messages', [])]}
- Tone: {brief.get('tone_of_voice', [])}

Generate {count} variations that:
- Each takes a slightly different angle
- Range from safe to edgy
- Maintain brand voice throughout
- Are ready to use (no placeholders)

Return as JSON:
{{
    "variations": [
        {{
            "content": "The copy",
            "tone": "Description of this variation's angle",
            "notes": "Why this might work"
        }}
    ]
}}"""

        result = await self.llm.complete_json(prompt, self.SYSTEM_PROMPT)

        return [
            CopyVariation(
                format=copy_type,
                content=v.get("content", ""),
                character_count=len(v.get("content", "")),
                tone=v.get("tone", ""),
                notes=v.get("notes", "")
            )
            for v in result.get("variations", [])
        ]

    async def close(self):
        """Close resources."""
        await self.llm.close()
