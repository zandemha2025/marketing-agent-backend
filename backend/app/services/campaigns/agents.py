"""
AI Agents for Campaign Execution.

This module provides specialized AI agents for different aspects of campaign creation:
- CopywriterAgent: Generates ad copy, headlines, social posts
- DesignerAgent: Creates image prompts and visual concepts
- StrategistAgent: Develops campaign strategy and audience targeting
"""
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ..ai.openrouter import OpenRouterService

logger = logging.getLogger(__name__)


@dataclass
class CopyOutput:
    """Output from the Copywriter Agent."""
    headlines: List[str]
    body_copy: str
    cta: str
    social_posts: List[Dict[str, str]]  # platform -> content
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    ad_copy: Dict[str, str] = field(default_factory=dict)  # platform -> copy


@dataclass
class VisualConcept:
    """Visual concept from the Designer Agent."""
    description: str
    style: str
    mood: str
    color_palette: List[str]
    composition: str
    image_prompt: str
    platform_specs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyOutput:
    """Strategy output from the Strategist Agent."""
    target_audience: Dict[str, Any]
    key_insight: str
    strategic_proposition: str
    messaging_framework: Dict[str, Any]
    channel_strategy: List[Dict[str, Any]]
    success_metrics: List[Dict[str, str]]
    creative_territories: List[Dict[str, Any]]


class CopywriterAgent:
    """
    AI Copywriter Agent.
    
    Generates compelling copy for various formats:
    - Headlines and taglines
    - Body copy
    - Social media posts
    - Email content
    - Ad copy for different platforms
    """
    
    SYSTEM_PROMPT = """You are an award-winning copywriter at a top creative agency.
You've written campaigns that have won Cannes Lions, One Show pencils, and D&AD pencils.

Your copy is:
- Attention-grabbing and memorable
- On-brand and strategically sound
- Tailored to each platform's unique constraints
- Written with a clear understanding of the target audience

You write copy that makes people stop, feel, and act."""

    def __init__(self, openrouter_api_key: str):
        self.llm = OpenRouterService(api_key=openrouter_api_key)

    async def generate_copy(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        platforms: List[str],
        brand_voice: Dict[str, Any] = None
    ) -> CopyOutput:
        """
        Generate complete copy package for a campaign.
        
        Args:
            brief: Campaign brief data
            concept: Creative concept data
            platforms: Target platforms (e.g., ['instagram', 'linkedin', 'facebook'])
            brand_voice: Brand voice guidelines
            
        Returns:
            CopyOutput with all generated copy
        """
        # Generate headlines
        headlines = await self._generate_headlines(brief, concept, brand_voice)
        
        # Generate body copy
        body_copy = await self._generate_body_copy(brief, concept, brand_voice)
        
        # Generate CTA
        cta = await self._generate_cta(brief, concept)
        
        # Generate platform-specific copy
        social_posts = []
        ad_copy = {}
        
        for platform in platforms:
            platform_copy = await self._generate_platform_copy(
                platform, brief, concept, headlines, body_copy, cta, brand_voice
            )
            
            if platform in ['instagram', 'twitter', 'linkedin', 'tiktok']:
                social_posts.append({
                    'platform': platform,
                    'content': platform_copy.get('post', ''),
                    'hashtags': platform_copy.get('hashtags', [])
                })
            else:
                ad_copy[platform] = platform_copy.get('ad_copy', '')
        
        # Generate email if requested
        email_subject = None
        email_body = None
        if 'email' in platforms:
            email = await self._generate_email(brief, concept, headlines, body_copy, cta, brand_voice)
            email_subject = email.get('subject', '')
            email_body = email.get('body', '')
        
        return CopyOutput(
            headlines=headlines,
            body_copy=body_copy,
            cta=cta,
            social_posts=social_posts,
            email_subject=email_subject,
            email_body=email_body,
            ad_copy=ad_copy
        )

    async def _generate_headlines(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        brand_voice: Dict[str, Any] = None
    ) -> List[str]:
        """Generate 5 headline options."""
        prompt = f"""Generate 5 compelling headline options for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept: {concept.get('concept_statement', '')}
Tagline: {concept.get('tagline', '')}
Key Insight: {brief.get('key_insight', '')}
Strategic Proposition: {brief.get('strategic_proposition', '')}

{self._format_brand_voice(brand_voice)}

Generate 5 headlines that:
1. Capture attention immediately
2. Communicate the core idea
3. Are memorable and shareable
4. Vary in approach (some emotional, some rational, some provocative)

Return as a JSON array of strings."""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            if isinstance(response, list):
                return response[:5]
            elif isinstance(response, dict) and 'headlines' in response:
                return response['headlines'][:5]
            return ["Headline 1", "Headline 2", "Headline 3", "Headline 4", "Headline 5"]
        except Exception as e:
            logger.error(f"Failed to generate headlines: {e}")
            return [concept.get('tagline', 'Your Headline Here')] * 5

    async def _generate_body_copy(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        brand_voice: Dict[str, Any] = None
    ) -> str:
        """Generate main body copy."""
        prompt = f"""Write compelling body copy for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept: {concept.get('concept_statement', '')}
Key Insight: {brief.get('key_insight', '')}
Strategic Proposition: {brief.get('strategic_proposition', '')}

{self._format_brand_voice(brand_voice)}

Write 2-3 paragraphs of body copy that:
1. Expands on the headline
2. Tells a compelling story
3. Addresses the audience's needs/desires
4. Builds toward a call-to-action

Return the copy as a string."""

        try:
            response = await self.llm.complete(prompt, system=self.SYSTEM_PROMPT)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate body copy: {e}")
            return concept.get('concept_statement', '')

    async def _generate_cta(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any]
    ) -> str:
        """Generate call-to-action."""
        prompt = f"""Write a compelling call-to-action for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept: {concept.get('concept_statement', '')}
Objective: {brief.get('objective', 'Drive action')}

Generate a short, action-oriented CTA (2-5 words) that:
1. Is clear and direct
2. Creates urgency or excitement
3. Tells the user exactly what to do

Return just the CTA text."""

        try:
            response = await self.llm.complete(prompt, system=self.SYSTEM_PROMPT)
            return response.strip().strip('"').strip("'")
        except Exception as e:
            logger.error(f"Failed to generate CTA: {e}")
            return "Learn More"

    async def _generate_platform_copy(
        self,
        platform: str,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        headlines: List[str],
        body_copy: str,
        cta: str,
        brand_voice: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate platform-specific copy."""
        platform_constraints = {
            'instagram': {'max_chars': 2200, 'hashtags': True},
            'twitter': {'max_chars': 280, 'hashtags': True},
            'linkedin': {'max_chars': 3000, 'hashtags': False},
            'facebook': {'max_chars': 63206, 'hashtags': True},
            'tiktok': {'max_chars': 2200, 'hashtags': True},
        }
        
        constraints = platform_constraints.get(platform, {'max_chars': 500, 'hashtags': True})
        
        prompt = f"""Write {platform} copy for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept: {concept.get('concept_statement', '')}
Headline options: {headlines}
Main CTA: {cta}

Platform: {platform}
Character limit: {constraints['max_chars']}
Include hashtags: {constraints['hashtags']}

Generate copy that:
1. Fits the platform's style and audience
2. Stays within character limits
3. Includes relevant hashtags if applicable
4. Encourages engagement

Return as JSON:
{{
    "post": "the main post copy",
    "hashtags": ["tag1", "tag2", "tag3"]
}}"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            return {
                'post': response.get('post', ''),
                'hashtags': response.get('hashtags', []),
                'ad_copy': response.get('post', '')
            }
        except Exception as e:
            logger.error(f"Failed to generate {platform} copy: {e}")
            return {'post': headlines[0] if headlines else concept.get('tagline', ''), 'hashtags': []}

    async def _generate_email(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        headlines: List[str],
        body_copy: str,
        cta: str,
        brand_voice: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Generate email content."""
        prompt = f"""Write email content for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept: {concept.get('concept_statement', '')}
Headline: {headlines[0] if headlines else 'Your Headline'}
Body Copy: {body_copy[:500]}...
CTA: {cta}

Generate:
1. Subject line (under 50 characters, compelling)
2. Email body (HTML-friendly, engaging)

Return as JSON:
{{
    "subject": "email subject line",
    "body": "email body content"
}}"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            return {
                'subject': response.get('subject', headlines[0] if headlines else 'Check this out'),
                'body': response.get('body', body_copy)
            }
        except Exception as e:
            logger.error(f"Failed to generate email: {e}")
            return {
                'subject': headlines[0] if headlines else 'Your Campaign',
                'body': body_copy
            }

    def _format_brand_voice(self, brand_voice: Dict[str, Any] = None) -> str:
        """Format brand voice for prompts."""
        if not brand_voice:
            return ""
        return f"""
Brand Voice:
- Tone: {brand_voice.get('tone', 'Professional')}
- Style: {brand_voice.get('style', 'Clear and direct')}
- Keywords: {', '.join(brand_voice.get('keywords', []))}
"""

    async def close(self):
        """Close the LLM client."""
        await self.llm.close()


class DesignerAgent:
    """
    AI Designer Agent.
    
    Creates visual concepts and image generation prompts:
    - Visual concept descriptions
    - Image generation prompts
    - Style and mood guidelines
    - Platform-specific specs
    """
    
    SYSTEM_PROMPT = """You are a visionary Art Director at a top creative agency.
You've created visual campaigns for global brands that have defined visual culture.

Your visual concepts are:
- Distinctive and memorable
- Strategically aligned with the brand
- Technically feasible for production
- Optimized for each platform's format

You think in images, color, and composition."""

    def __init__(self, openrouter_api_key: str):
        self.llm = OpenRouterService(api_key=openrouter_api_key)

    async def generate_visual_concept(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        platforms: List[str],
        brand_visuals: Dict[str, Any] = None
    ) -> VisualConcept:
        """
        Generate visual concept for a campaign.
        
        Args:
            brief: Campaign brief data
            concept: Creative concept data
            platforms: Target platforms
            brand_visuals: Brand visual guidelines
            
        Returns:
            VisualConcept with all visual specifications
        """
        # Generate concept description
        description = await self._generate_concept_description(brief, concept, brand_visuals)
        
        # Generate style and mood
        style, mood = await self._generate_style_mood(brief, concept, brand_visuals)
        
        # Generate color palette
        color_palette = await self._generate_color_palette(brief, concept, brand_visuals)
        
        # Generate composition notes
        composition = await self._generate_composition(brief, concept)
        
        # Generate image prompt
        image_prompt = await self._generate_image_prompt(
            description, style, mood, color_palette, composition
        )
        
        # Generate platform specs
        platform_specs = {}
        for platform in platforms:
            platform_specs[platform] = self._get_platform_specs(platform)
        
        return VisualConcept(
            description=description,
            style=style,
            mood=mood,
            color_palette=color_palette,
            composition=composition,
            image_prompt=image_prompt,
            platform_specs=platform_specs
        )

    async def _generate_concept_description(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        brand_visuals: Dict[str, Any] = None
    ) -> str:
        """Generate visual concept description."""
        prompt = f"""Describe the visual concept for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept Statement: {concept.get('concept_statement', '')}
Key Visual Idea: {concept.get('key_visual_idea', '')}

{self._format_brand_visuals(brand_visuals)}

Describe the visual approach in 2-3 sentences:
1. What is the central visual metaphor?
2. What style of photography/illustration?
3. What is the overall visual feeling?

Return the description as a string."""

        try:
            response = await self.llm.complete(prompt, system=self.SYSTEM_PROMPT)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate concept description: {e}")
            return concept.get('key_visual_idea', 'Visual concept for campaign')

    async def _generate_style_mood(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        brand_visuals: Dict[str, Any] = None
    ) -> tuple:
        """Generate style and mood."""
        prompt = f"""Define the visual style and mood for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept: {concept.get('concept_statement', '')}
Tone: {concept.get('tone_description', '')}

{self._format_brand_visuals(brand_visuals)}

Return as JSON:
{{
    "style": "e.g., cinematic, minimalist, vibrant, editorial",
    "mood": "e.g., uplifting, sophisticated, energetic, calm"
}}"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            return response.get('style', 'Modern'), response.get('mood', 'Professional')
        except Exception as e:
            logger.error(f"Failed to generate style/mood: {e}")
            return 'Modern', 'Professional'

    async def _generate_color_palette(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any],
        brand_visuals: Dict[str, Any] = None
    ) -> List[str]:
        """Generate color palette."""
        # Use brand colors if available
        brand_colors = brand_visuals.get('colors', []) if brand_visuals else []
        
        prompt = f"""Define the color palette for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept: {concept.get('concept_statement', '')}
Brand Colors: {brand_colors}

Return a JSON array of 4-6 hex color codes that:
1. Work with the brand colors (if provided)
2. Support the campaign mood and concept
3. Provide good contrast for text overlays
4. Feel cohesive and intentional

Format: ["#FF5733", "#33FF57", "#3357FF", "#F3FF33"]"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            if isinstance(response, list):
                return response[:6]
            elif isinstance(response, dict) and 'colors' in response:
                return response['colors'][:6]
            return brand_colors if brand_colors else ["#FF5733", "#33FF57", "#3357FF"]
        except Exception as e:
            logger.error(f"Failed to generate color palette: {e}")
            return brand_colors if brand_colors else ["#FF5733", "#33FF57", "#3357FF"]

    async def _generate_composition(
        self,
        brief: Dict[str, Any],
        concept: Dict[str, Any]
    ) -> str:
        """Generate composition notes."""
        prompt = f"""Describe the composition approach for this campaign:

Campaign: {brief.get('campaign_name', 'Untitled')}
Concept: {concept.get('concept_statement', '')}
Key Visual: {concept.get('key_visual_idea', '')}

Describe the composition in terms of:
1. Subject placement
2. Use of negative space
3. Visual hierarchy
4. Rule of thirds or other compositional techniques

Return as a brief description."""

        try:
            response = await self.llm.complete(prompt, system=self.SYSTEM_PROMPT)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate composition: {e}")
            return "Centered subject with balanced composition"

    async def _generate_image_prompt(
        self,
        description: str,
        style: str,
        mood: str,
        color_palette: List[str],
        composition: str
    ) -> str:
        """Generate image generation prompt."""
        prompt = f"""Create an image generation prompt for this visual concept:

Description: {description}
Style: {style}
Mood: {mood}
Color Palette: {color_palette}
Composition: {composition}

Write a detailed prompt for AI image generation (Midjourney/DALL-E style) that:
1. Describes the scene in detail
2. Specifies the style and mood
3. Includes technical parameters (lighting, camera angle, etc.)
4. Is optimized for high-quality output

Return the prompt as a string."""

        try:
            response = await self.llm.complete(prompt, system=self.SYSTEM_PROMPT)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to generate image prompt: {e}")
            return f"{style} image, {mood} mood, {description}"

    def _get_platform_specs(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific specs."""
        specs = {
            'instagram': {
                'feed': {'width': 1080, 'height': 1080, 'ratio': '1:1'},
                'story': {'width': 1080, 'height': 1920, 'ratio': '9:16'},
                'reel': {'width': 1080, 'height': 1920, 'ratio': '9:16'}
            },
            'facebook': {
                'feed': {'width': 1200, 'height': 630, 'ratio': '1.91:1'},
                'story': {'width': 1080, 'height': 1920, 'ratio': '9:16'}
            },
            'linkedin': {
                'feed': {'width': 1200, 'height': 627, 'ratio': '1.91:1'},
                'banner': {'width': 1584, 'height': 396, 'ratio': '4:1'}
            },
            'twitter': {
                'feed': {'width': 1200, 'height': 675, 'ratio': '16:9'}
            }
        }
        return specs.get(platform, {'feed': {'width': 1200, 'height': 630}})

    def _format_brand_visuals(self, brand_visuals: Dict[str, Any] = None) -> str:
        """Format brand visuals for prompts."""
        if not brand_visuals:
            return ""
        return f"""
Brand Visual Guidelines:
- Colors: {brand_visuals.get('colors', [])}
- Style: {brand_visuals.get('style', '')}
- Imagery: {brand_visuals.get('imagery', '')}
"""

    async def close(self):
        """Close the LLM client."""
        await self.llm.close()


class StrategistAgent:
    """
    AI Strategist Agent.
    
    Develops campaign strategy:
    - Audience targeting
    - Strategic framework
    - Channel strategy
    - Success metrics
    - Creative territories
    """
    
    SYSTEM_PROMPT = """You are a world-class strategy director at a top-tier creative agency.
You've developed strategies for Fortune 500 brands that have driven billions in revenue.

Your strategies are:
- Deeply rooted in consumer insight
- Clearly differentiated from competitors
- Measurable and actionable
- Inspiring to creative teams

You think in frameworks but communicate in human terms."""

    def __init__(self, openrouter_api_key: str):
        self.llm = OpenRouterService(api_key=openrouter_api_key)

    async def develop_strategy(
        self,
        campaign_request: Dict[str, Any],
        knowledge_base: Dict[str, Any] = None
    ) -> StrategyOutput:
        """
        Develop complete campaign strategy.
        
        Args:
            campaign_request: Campaign parameters
            knowledge_base: Brand and market knowledge
            
        Returns:
            StrategyOutput with all strategic elements
        """
        kb = knowledge_base or {}
        
        # Develop target audience
        target_audience = await self._develop_target_audience(
            campaign_request, kb.get('audiences', {})
        )
        
        # Develop key insight
        key_insight = await self._develop_key_insight(campaign_request, kb)
        
        # Develop strategic proposition
        strategic_proposition = await self._develop_strategic_proposition(
            campaign_request, key_insight, kb
        )
        
        # Develop messaging framework
        messaging_framework = await self._develop_messaging_framework(
            campaign_request, strategic_proposition, target_audience
        )
        
        # Develop channel strategy
        channel_strategy = await self._develop_channel_strategy(
            campaign_request, target_audience
        )
        
        # Develop success metrics
        success_metrics = await self._develop_success_metrics(campaign_request)
        
        # Develop creative territories
        creative_territories = await self._develop_creative_territories(
            campaign_request, strategic_proposition, key_insight
        )
        
        return StrategyOutput(
            target_audience=target_audience,
            key_insight=key_insight,
            strategic_proposition=strategic_proposition,
            messaging_framework=messaging_framework,
            channel_strategy=channel_strategy,
            success_metrics=success_metrics,
            creative_territories=creative_territories
        )

    async def _develop_target_audience(
        self,
        campaign_request: Dict[str, Any],
        audience_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Develop target audience profile."""
        prompt = f"""Define the target audience for this campaign:

Campaign Objective: {campaign_request.get('objective', '')}
Product Focus: {campaign_request.get('product_focus', 'General')}
Target Audience Input: {campaign_request.get('target_audience', '')}
Existing Audience Data: {audience_data}

Define the primary target audience with:
1. Demographics (age, gender, income, location)
2. Psychographics (values, interests, lifestyle)
3. Behaviors (media consumption, purchase habits)
4. Pain points and desires
5. Where to reach them

Return as JSON:
{{
    "primary": {{
        "demographics": "description",
        "psychographics": "description",
        "behaviors": "description",
        "pain_points": ["point1", "point2"],
        "desires": ["desire1", "desire2"],
        "media_habits": ["habit1", "habit2"]
    }}
}}"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            return response if isinstance(response, dict) else {'primary': {}}
        except Exception as e:
            logger.error(f"Failed to develop target audience: {e}")
            return {
                'primary': {
                    'demographics': campaign_request.get('target_audience', 'General audience'),
                    'psychographics': 'Value-conscious consumers',
                    'behaviors': 'Active on social media',
                    'pain_points': ['Finding quality products'],
                    'desires': ['Better solutions'],
                    'media_habits': ['Social media', 'Online search']
                }
            }

    async def _develop_key_insight(
        self,
        campaign_request: Dict[str, Any],
        knowledge_base: Dict[str, Any]
    ) -> str:
        """Develop key insight."""
        prompt = f"""Develop the key insight for this campaign:

Campaign Objective: {campaign_request.get('objective', '')}
Product Focus: {campaign_request.get('product_focus', 'General')}
Target Audience: {campaign_request.get('target_audience', '')}
Brand Knowledge: {knowledge_base.get('brand', {})}
Market Knowledge: {knowledge_base.get('market', {})}

Identify a powerful insight that:
1. Reveals an unspoken truth about the audience
2. Connects to the brand/product
3. Is ownable and differentiating
4. Can inspire creative work

Return the insight as a single compelling sentence."""

        try:
            response = await self.llm.complete(prompt, system=self.SYSTEM_PROMPT)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to develop key insight: {e}")
            return f"People want {campaign_request.get('product_focus', 'better solutions')} that truly understand their needs."

    async def _develop_strategic_proposition(
        self,
        campaign_request: Dict[str, Any],
        key_insight: str,
        knowledge_base: Dict[str, Any]
    ) -> str:
        """Develop strategic proposition."""
        prompt = f"""Develop the strategic proposition for this campaign:

Campaign Objective: {campaign_request.get('objective', '')}
Product Focus: {campaign_request.get('product_focus', 'General')}
Key Insight: {key_insight}
Brand Position: {knowledge_base.get('brand', {}).get('positioning', {})}

Create a strategic proposition that:
1. Addresses the key insight
2. Positions the brand/product uniquely
3. Is simple and memorable
4. Can guide all creative development

Return the proposition as a clear, compelling statement."""

        try:
            response = await self.llm.complete(prompt, system=self.SYSTEM_PROMPT)
            return response.strip()
        except Exception as e:
            logger.error(f"Failed to develop strategic proposition: {e}")
            return f"The only {campaign_request.get('product_focus', 'solution')} that truly delivers on what matters most."

    async def _develop_messaging_framework(
        self,
        campaign_request: Dict[str, Any],
        strategic_proposition: str,
        target_audience: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Develop messaging framework."""
        prompt = f"""Develop the messaging framework for this campaign:

Strategic Proposition: {strategic_proposition}
Target Audience: {target_audience}
Campaign Objective: {campaign_request.get('objective', '')}

Create a messaging framework with:
1. Core message (the one thing we want people to remember)
2. Supporting messages (3-4 key points)
3. Proof points (evidence for each message)
4. Tone and manner

Return as JSON:
{{
    "core_message": "main message",
    "supporting_messages": ["msg1", "msg2", "msg3"],
    "proof_points": ["proof1", "proof2", "proof3"],
    "tone": ["descriptor1", "descriptor2", "descriptor3"]
}}"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            return response if isinstance(response, dict) else {
                'core_message': strategic_proposition,
                'supporting_messages': [],
                'proof_points': [],
                'tone': ['Professional', 'Authentic']
            }
        except Exception as e:
            logger.error(f"Failed to develop messaging framework: {e}")
            return {
                'core_message': strategic_proposition,
                'supporting_messages': ['Quality you can trust', 'Results that matter'],
                'proof_points': ['Industry leader', 'Customer favorite'],
                'tone': ['Professional', 'Authentic']
            }

    async def _develop_channel_strategy(
        self,
        campaign_request: Dict[str, Any],
        target_audience: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Develop channel strategy."""
        platforms = campaign_request.get('platforms', ['social', 'email'])
        budget_tier = campaign_request.get('budget_tier', 'medium')
        
        prompt = f"""Develop the channel strategy for this campaign:

Platforms: {platforms}
Budget Tier: {budget_tier}
Target Audience Media Habits: {target_audience.get('primary', {}).get('media_habits', [])}
Campaign Objective: {campaign_request.get('objective', '')}

For each channel, define:
1. Role in the customer journey
2. Content formats to use
3. Frequency/posting schedule
4. Budget allocation percentage

Return as JSON array:
[
    {{
        "channel": "channel name",
        "role": "awareness/consideration/conversion",
        "formats": ["format1", "format2"],
        "frequency": "description",
        "budget_allocation": "percentage"
    }}
]"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and 'channels' in response:
                return response['channels']
            return []
        except Exception as e:
            logger.error(f"Failed to develop channel strategy: {e}")
            return [
                {
                    'channel': 'Social Media',
                    'role': 'awareness',
                    'formats': ['Posts', 'Stories'],
                    'frequency': '3-5x per week',
                    'budget_allocation': '40%'
                },
                {
                    'channel': 'Email',
                    'role': 'conversion',
                    'formats': ['Newsletter', 'Promotional'],
                    'frequency': 'Weekly',
                    'budget_allocation': '20%'
                }
            ]

    async def _develop_success_metrics(
        self,
        campaign_request: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Develop success metrics."""
        objective = campaign_request.get('objective', '').lower()
        
        # Determine metrics based on objective
        if 'awareness' in objective or 'brand' in objective:
            default_metrics = [
                {'metric': 'Impressions', 'target': '1M+', 'timeframe': '30 days'},
                {'metric': 'Reach', 'target': '500K+', 'timeframe': '30 days'},
                {'metric': 'Brand Recall', 'target': '25%+', 'timeframe': '60 days'}
            ]
        elif 'conversion' in objective or 'sales' in objective:
            default_metrics = [
                {'metric': 'Conversions', 'target': '1000+', 'timeframe': '30 days'},
                {'metric': 'Conversion Rate', 'target': '3%+', 'timeframe': '30 days'},
                {'metric': 'ROAS', 'target': '4:1+', 'timeframe': '30 days'}
            ]
        else:
            default_metrics = [
                {'metric': 'Engagement Rate', 'target': '5%+', 'timeframe': '30 days'},
                {'metric': 'Click-Through Rate', 'target': '2%+', 'timeframe': '30 days'},
                {'metric': 'Leads Generated', 'target': '500+', 'timeframe': '30 days'}
            ]
        
        prompt = f"""Define success metrics for this campaign:

Campaign Objective: {campaign_request.get('objective', '')}
Budget Tier: {campaign_request.get('budget_tier', 'medium')}
Timeline: {campaign_request.get('timeline', '4 weeks')}

Define 3-5 specific, measurable metrics with targets.

Return as JSON array:
[
    {{
        "metric": "metric name",
        "target": "specific target",
        "timeframe": "when to measure"
    }}
]"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            if isinstance(response, list):
                return response
            elif isinstance(response, dict) and 'metrics' in response:
                return response['metrics']
            return default_metrics
        except Exception as e:
            logger.error(f"Failed to develop success metrics: {e}")
            return default_metrics

    async def _develop_creative_territories(
        self,
        campaign_request: Dict[str, Any],
        strategic_proposition: str,
        key_insight: str
    ) -> List[Dict[str, Any]]:
        """Develop creative territories."""
        prompt = f"""Develop 3 creative territories for this campaign:

Strategic Proposition: {strategic_proposition}
Key Insight: {key_insight}
Campaign Objective: {campaign_request.get('objective', '')}

For each territory, define:
1. Name
2. Core concept/idea
3. Visual direction
4. Tone
5. Sample taglines (3-4)
6. Risk level (low/medium/high)

Return as JSON array:
[
    {{
        "name": "territory name",
        "concept": "core creative idea",
        "visual_direction": "visual approach",
        "tone": "tone of voice",
        "tagline_options": ["tagline1", "tagline2", "tagline3"],
        "risk_level": "low/medium/high"
    }}
]"""

        try:
            response = await self.llm.complete_json(prompt, system=self.SYSTEM_PROMPT)
            if isinstance(response, list) and len(response) >= 2:
                return response[:3]
            elif isinstance(response, dict) and 'territories' in response:
                return response['territories'][:3]
            return self._default_territories(strategic_proposition)
        except Exception as e:
            logger.error(f"Failed to develop creative territories: {e}")
            return self._default_territories(strategic_proposition)

    def _default_territories(self, proposition: str) -> List[Dict[str, Any]]:
        """Generate default territories."""
        return [
            {
                'name': 'The Truth',
                'concept': f'Direct, honest communication about {proposition}',
                'visual_direction': 'Clean, authentic photography',
                'tone': 'Honest, straightforward',
                'tagline_options': ['The Real Choice', 'Honestly Better', 'Truth in Every Detail'],
                'risk_level': 'low'
            },
            {
                'name': 'The Emotion',
                'concept': f'Emotional storytelling around {proposition}',
                'visual_direction': 'Cinematic, emotional imagery',
                'tone': 'Warm, inspiring',
                'tagline_options': ['Feel the Difference', 'Made for You', 'Where Heart Meets Quality'],
                'risk_level': 'medium'
            },
            {
                'name': 'The Bold Move',
                'concept': f'Provocative, challenging approach to {proposition}',
                'visual_direction': 'Bold, unexpected visuals',
                'tone': 'Confident, provocative',
                'tagline_options': ['Challenge Everything', 'Why Settle?', 'Redefine What\'s Possible'],
                'risk_level': 'high'
            }
        ]

    async def close(self):
        """Close the LLM client."""
        await self.llm.close()
