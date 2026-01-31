"""
Press Release Generator Service

Generates professional press releases in standard AP format with:
- Compelling headlines
- Proper datelines
- Strong lead paragraphs
- Informative body sections
- Boilerplate company descriptions
- AI-generated executive quotes
- Brand voice integration
- Multiple output formats (text, HTML, markdown)
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import html

from ..ai.openrouter import OpenRouterService
from ...core.config import get_settings

logger = logging.getLogger(__name__)


class AnnouncementType(str, Enum):
    """Types of press release announcements."""
    PRODUCT_LAUNCH = "product_launch"
    PARTNERSHIP = "partnership"
    FUNDING = "funding"
    EVENT = "event"
    MILESTONE = "milestone"
    EXECUTIVE = "executive"
    AWARD = "award"
    ACQUISITION = "acquisition"
    EXPANSION = "expansion"
    RESEARCH = "research"


@dataclass
class PressReleaseInput:
    """Input parameters for press release generation."""
    announcement_type: AnnouncementType
    company_name: str
    announcement_details: str
    key_facts: List[str]
    executive_name: str
    executive_title: str
    contact_name: str
    contact_email: str
    contact_phone: str
    city: str = "New York"
    state: str = "NY"
    brand_voice: str = "professional"
    additional_context: Optional[str] = None
    company_description: Optional[str] = None
    company_website: Optional[str] = None
    target_audience: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "announcement_type": self.announcement_type.value,
            "company_name": self.company_name,
            "announcement_details": self.announcement_details,
            "key_facts": self.key_facts,
            "executive_name": self.executive_name,
            "executive_title": self.executive_title,
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "city": self.city,
            "state": self.state,
            "brand_voice": self.brand_voice,
            "additional_context": self.additional_context,
            "company_description": self.company_description,
            "company_website": self.company_website,
            "target_audience": self.target_audience,
        }


@dataclass
class PressReleaseSection:
    """A section of a press release."""
    type: str  # "headline", "subheadline", "dateline", "lead", "body", "quote", "boilerplate"
    content: str
    attribution: Optional[str] = None  # For quotes


@dataclass
class PressRelease:
    """A complete press release."""
    headline: str
    subheadline: Optional[str] = None
    dateline: str = ""
    lead: str = ""
    body: List[str] = field(default_factory=list)
    quotes: List[Dict[str, str]] = field(default_factory=list)
    boilerplate: str = ""
    contact_info: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    word_count: int = 0
    announcement_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "headline": self.headline,
            "subheadline": self.subheadline,
            "dateline": self.dateline,
            "lead": self.lead,
            "body": self.body,
            "quotes": self.quotes,
            "boilerplate": self.boilerplate,
            "contact_info": self.contact_info,
            "created_at": self.created_at.isoformat(),
            "word_count": self.word_count,
            "announcement_type": self.announcement_type,
        }
    
    def to_html(self) -> str:
        """Convert to HTML format with proper styling."""
        # Escape HTML in content
        safe_headline = html.escape(self.headline)
        safe_subheadline = html.escape(self.subheadline) if self.subheadline else ""
        safe_dateline = html.escape(self.dateline)
        safe_lead = html.escape(self.lead)
        safe_boilerplate = html.escape(self.boilerplate)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_headline}</title>
    <style>
        .press-release {{
            max-width: 800px;
            margin: 0 auto;
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.6;
            padding: 20px;
        }}
        .press-release h1 {{
            font-size: 1.8em;
            margin-bottom: 0.5em;
            color: #1a1a1a;
        }}
        .press-release h2 {{
            font-size: 1.3em;
            font-weight: normal;
            color: #444;
            margin-bottom: 1em;
        }}
        .press-release .dateline {{
            font-weight: bold;
            margin-bottom: 1em;
        }}
        .press-release .lead {{
            font-size: 1.1em;
            margin-bottom: 1.5em;
        }}
        .press-release .body p {{
            margin-bottom: 1em;
        }}
        .press-release blockquote {{
            border-left: 3px solid #ccc;
            padding-left: 1em;
            margin: 1.5em 0;
            font-style: italic;
        }}
        .press-release blockquote footer {{
            font-style: normal;
            font-weight: bold;
            margin-top: 0.5em;
        }}
        .press-release .boilerplate {{
            margin-top: 2em;
            padding-top: 1em;
            border-top: 1px solid #ccc;
        }}
        .press-release .boilerplate h3 {{
            font-size: 1em;
            margin-bottom: 0.5em;
        }}
        .press-release .contact {{
            margin-top: 1.5em;
        }}
        .press-release .end-marker {{
            text-align: center;
            margin-top: 2em;
            font-weight: bold;
        }}
    </style>
</head>
<body>
<article class="press-release">
    <header>
        <h1>{safe_headline}</h1>
        {f'<h2>{safe_subheadline}</h2>' if safe_subheadline else ''}
        <p class="dateline">{safe_dateline}</p>
    </header>
    <section class="lead">
        <p>{safe_lead}</p>
    </section>
    <section class="body">
"""
        for paragraph in self.body:
            safe_para = html.escape(paragraph)
            html_content += f"        <p>{safe_para}</p>\n"
        
        for quote in self.quotes:
            safe_quote = html.escape(quote.get('text', ''))
            safe_attr = html.escape(quote.get('attribution', ''))
            html_content += f"""
        <blockquote>
            <p>"{safe_quote}"</p>
            <footer>— {safe_attr}</footer>
        </blockquote>
"""
        
        html_content += f"""    </section>
    <section class="boilerplate">
        <h3>About {html.escape(self.contact_info.get('company', 'the Company'))}</h3>
        <p>{safe_boilerplate}</p>
    </section>
    <section class="contact">
        <h3>Media Contact</h3>
        <p>
            {html.escape(self.contact_info.get('name', ''))}<br>
            Email: {html.escape(self.contact_info.get('email', ''))}<br>
            Phone: {html.escape(self.contact_info.get('phone', ''))}
        </p>
    </section>
    <p class="end-marker">###</p>
</article>
</body>
</html>"""
        return html_content
    
    def to_text(self) -> str:
        """Convert to plain text format (AP style)."""
        lines = []
        
        # Header
        lines.append("FOR IMMEDIATE RELEASE")
        lines.append("")
        
        # Headline
        lines.append(self.headline.upper())
        lines.append("=" * min(len(self.headline), 80))
        lines.append("")
        
        # Subheadline
        if self.subheadline:
            lines.append(self.subheadline)
            lines.append("")
        
        # Dateline and lead
        lines.append(f"{self.dateline} — {self.lead}")
        lines.append("")
        
        # Body paragraphs
        for paragraph in self.body:
            lines.append(paragraph)
            lines.append("")
        
        # Quotes
        for quote in self.quotes:
            lines.append(f'"{quote.get("text", "")}"')
            lines.append(f"— {quote.get('attribution', '')}")
            lines.append("")
        
        # Boilerplate
        lines.append("About " + self.contact_info.get('company', 'the Company'))
        lines.append("-" * 40)
        lines.append(self.boilerplate)
        lines.append("")
        
        # Contact info
        lines.append("Media Contact:")
        lines.append(self.contact_info.get('name', ''))
        lines.append(f"Email: {self.contact_info.get('email', '')}")
        lines.append(f"Phone: {self.contact_info.get('phone', '')}")
        lines.append("")
        
        # End marker
        lines.append("###")
        
        return "\n".join(lines)
    
    def to_plaintext(self) -> str:
        """Alias for to_text() for backward compatibility."""
        return self.to_text()
    
    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        lines = []
        
        # Header
        lines.append("**FOR IMMEDIATE RELEASE**")
        lines.append("")
        
        # Headline
        lines.append(f"# {self.headline}")
        lines.append("")
        
        # Subheadline
        if self.subheadline:
            lines.append(f"## {self.subheadline}")
            lines.append("")
        
        # Dateline and lead
        lines.append(f"**{self.dateline}** — {self.lead}")
        lines.append("")
        
        # Body paragraphs
        for paragraph in self.body:
            lines.append(paragraph)
            lines.append("")
        
        # Quotes
        for quote in self.quotes:
            lines.append(f'> "{quote.get("text", "")}"')
            lines.append(f">")
            lines.append(f"> — *{quote.get('attribution', '')}*")
            lines.append("")
        
        # Boilerplate
        lines.append(f"### About {self.contact_info.get('company', 'the Company')}")
        lines.append("")
        lines.append(self.boilerplate)
        lines.append("")
        
        # Contact info
        lines.append("---")
        lines.append("")
        lines.append("**Media Contact:**")
        lines.append("")
        lines.append(f"- **Name:** {self.contact_info.get('name', '')}")
        lines.append(f"- **Email:** {self.contact_info.get('email', '')}")
        lines.append(f"- **Phone:** {self.contact_info.get('phone', '')}")
        lines.append("")
        
        # End marker
        lines.append("---")
        lines.append("")
        lines.append("**###**")
        
        return "\n".join(lines)


class PressReleaseGeneratorError(Exception):
    """Custom exception for press release generation errors."""
    pass


class PressReleaseGenerator:
    """
    Generates professional press releases with AI assistance.
    
    Features:
    - Standard AP format compliance
    - Brand voice integration
    - Executive quote generation
    - Multiple output formats (HTML, text, markdown, JSON)
    - Support for various announcement types
    """
    
    # Announcement type specific prompts
    ANNOUNCEMENT_PROMPTS = {
        AnnouncementType.PRODUCT_LAUNCH: "Focus on the product's unique features, benefits, and availability. Emphasize innovation and customer value.",
        AnnouncementType.PARTNERSHIP: "Highlight the strategic value of the partnership, combined strengths, and expected outcomes for both parties.",
        AnnouncementType.FUNDING: "Emphasize the funding amount, investors, company valuation if appropriate, and planned use of funds.",
        AnnouncementType.EVENT: "Include event details (date, location, speakers), registration information, and expected outcomes.",
        AnnouncementType.MILESTONE: "Celebrate the achievement, provide context on its significance, and outline future goals.",
        AnnouncementType.EXECUTIVE: "Introduce the executive's background, qualifications, and vision for the role.",
        AnnouncementType.AWARD: "Detail the award, selection criteria, and what it means for the company's reputation.",
        AnnouncementType.ACQUISITION: "Explain the strategic rationale, terms if disclosed, and integration plans.",
        AnnouncementType.EXPANSION: "Describe the expansion scope, new markets or locations, and growth strategy.",
        AnnouncementType.RESEARCH: "Present key findings, methodology highlights, and implications for the industry.",
    }
    
    def __init__(self, openrouter_api_key: Optional[str] = None):
        """
        Initialize the press release generator.
        
        Args:
            openrouter_api_key: Optional API key. If not provided, uses settings.
        """
        self.settings = get_settings()
        api_key = openrouter_api_key or self.settings.openrouter_api_key
        self.openrouter = None
        if api_key:
            self.openrouter = OpenRouterService(
                api_key=api_key,
                timeout=120.0
            )
    
    async def generate(
        self,
        input_data: PressReleaseInput,
        brand_context: Optional[Dict[str, Any]] = None
    ) -> PressRelease:
        """
        Generate a complete press release from structured input.
        
        Args:
            input_data: PressReleaseInput with all required fields
            brand_context: Optional brand context from KnowledgeBase
            
        Returns:
            Complete PressRelease object
            
        Raises:
            PressReleaseGeneratorError: If generation fails critically
        """
        try:
            if not self.openrouter:
                logger.warning("OpenRouter not configured, using basic generation")
                return self._create_basic_pr_from_input(input_data)
            
            # Get announcement-specific guidance
            announcement_guidance = self.ANNOUNCEMENT_PROMPTS.get(
                input_data.announcement_type,
                "Create a professional and newsworthy press release."
            )
            
            # Build brand voice context
            voice_guidelines = self._build_voice_guidelines(
                input_data.brand_voice,
                brand_context
            )
            
            # Format key facts
            key_facts_text = "\n".join(f"- {fact}" for fact in input_data.key_facts)
            
            prompt = f"""
Create a professional press release following AP style guidelines.

ANNOUNCEMENT TYPE: {input_data.announcement_type.value.replace('_', ' ').title()}
GUIDANCE: {announcement_guidance}

COMPANY: {input_data.company_name}
COMPANY DESCRIPTION: {input_data.company_description or 'A leading company in its industry'}
WEBSITE: {input_data.company_website or ''}

ANNOUNCEMENT DETAILS:
{input_data.announcement_details}

KEY FACTS:
{key_facts_text}

ADDITIONAL CONTEXT:
{input_data.additional_context or 'None provided'}

{voice_guidelines}

EXECUTIVE FOR QUOTE:
- Name: {input_data.executive_name}
- Title: {input_data.executive_title}

TARGET AUDIENCE: {input_data.target_audience or 'general business audience'}
LOCATION: {input_data.city}, {input_data.state}

Generate a complete press release with these sections:
1. Compelling headline (attention-grabbing, under 100 characters, no quotes)
2. Subheadline (expands on headline, provides key detail)
3. Dateline (format: CITY, State — Month Day, Year)
4. Lead paragraph (who, what, when, where, why - most important info first)
5. Body paragraphs (2-4 paragraphs with supporting details, context, and implications)
6. Executive quote (1-2 natural-sounding quotes that add perspective)
7. Boilerplate (company description, 2-3 sentences)

Return as JSON:
{{
    "headline": "...",
    "subheadline": "...",
    "dateline": "...",
    "lead": "...",
    "body": ["paragraph 1", "paragraph 2", ...],
    "quotes": [
        {{
            "text": "Quote text here...",
            "attribution": "Name, Title"
        }}
    ],
    "boilerplate": "..."
}}

AP Style Guidelines to follow:
- Use active voice throughout
- Include concrete facts and figures
- Keep sentences concise (under 30 words)
- Avoid marketing superlatives and buzzwords
- Make quotes sound authentic and conversational
- Use proper AP date format (Month Day, Year)
- Spell out numbers one through nine
- Use figures for 10 and above
"""
            
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are a senior PR professional with 20+ years of experience writing press releases for Fortune 500 companies. You follow AP style guidelines perfectly and create compelling, newsworthy content.",
                temperature=0.7,
                json_mode=True
            )
            
            data = json.loads(response)
            
            # Calculate word count
            word_count = self._calculate_word_count(data)
            
            return PressRelease(
                headline=data.get("headline", ""),
                subheadline=data.get("subheadline"),
                dateline=data.get("dateline", self._generate_dateline(input_data.city, input_data.state)),
                lead=data.get("lead", ""),
                body=data.get("body", []),
                quotes=data.get("quotes", []),
                boilerplate=data.get("boilerplate", ""),
                contact_info={
                    "company": input_data.company_name,
                    "name": input_data.contact_name,
                    "email": input_data.contact_email,
                    "phone": input_data.contact_phone,
                },
                word_count=word_count,
                announcement_type=input_data.announcement_type.value
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._create_basic_pr_from_input(input_data)
        except Exception as e:
            logger.error(f"Press release generation failed: {e}")
            raise PressReleaseGeneratorError(f"Failed to generate press release: {e}") from e
    
    async def generate_from_dict(
        self,
        topic: str,
        key_points: List[str],
        company_info: Dict[str, Any],
        brand_voice: Optional[Dict[str, Any]] = None,
        executive_name: Optional[str] = None,
        executive_title: Optional[str] = None,
        target_audience: Optional[str] = None,
        tone: str = "professional"
    ) -> PressRelease:
        """
        Generate a press release from dictionary inputs (legacy interface).
        
        Args:
            topic: The main topic/news of the press release
            key_points: Bullet points to cover
            company_info: Company details (name, description, website, etc.)
            brand_voice: Brand voice guidelines
            executive_name: Name for quote attribution
            executive_title: Title for quote attribution
            target_audience: Target audience description
            tone: Overall tone (professional, excited, serious, etc.)
            
        Returns:
            Complete PressRelease object
        """
        # Convert to PressReleaseInput
        input_data = PressReleaseInput(
            announcement_type=AnnouncementType.MILESTONE,  # Default type
            company_name=company_info.get('name', 'Company'),
            announcement_details=topic,
            key_facts=key_points,
            executive_name=executive_name or 'CEO',
            executive_title=executive_title or 'Chief Executive Officer',
            contact_name=company_info.get('contact', {}).get('name', ''),
            contact_email=company_info.get('contact', {}).get('email', ''),
            contact_phone=company_info.get('contact', {}).get('phone', ''),
            city=company_info.get('location', 'New York').split(',')[0].strip(),
            state=company_info.get('location', 'NY').split(',')[-1].strip() if ',' in company_info.get('location', '') else 'NY',
            brand_voice=tone,
            company_description=company_info.get('description'),
            company_website=company_info.get('website'),
            target_audience=target_audience,
        )
        
        return await self.generate(input_data, brand_voice)
    
    async def generate_headline(
        self,
        details: str,
        announcement_type: AnnouncementType,
        company_name: Optional[str] = None
    ) -> str:
        """
        Generate a compelling headline for a press release.
        
        Args:
            details: The announcement details
            announcement_type: Type of announcement
            company_name: Optional company name to include
            
        Returns:
            A compelling headline string
        """
        if not self.openrouter:
            return self._create_basic_headline(details, announcement_type, company_name)
        
        prompt = f"""
Generate a compelling press release headline.

Announcement Type: {announcement_type.value.replace('_', ' ').title()}
Details: {details}
Company: {company_name or 'the company'}

Requirements:
- Under 100 characters
- Attention-grabbing but professional
- No quotes or punctuation at the end
- Active voice
- Specific and newsworthy

Return only the headline text, nothing else.
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are a headline writing expert. Create compelling, newsworthy headlines.",
                temperature=0.8
            )
            return response.strip().strip('"\'')
        except Exception as e:
            logger.error(f"Headline generation failed: {e}")
            return self._create_basic_headline(details, announcement_type, company_name)
    
    async def generate_subheadline(
        self,
        headline: str,
        details: str,
        key_fact: Optional[str] = None
    ) -> str:
        """
        Generate a supporting subheadline.
        
        Args:
            headline: The main headline
            details: Announcement details
            key_fact: Optional key fact to highlight
            
        Returns:
            A supporting subheadline string
        """
        if not self.openrouter:
            return key_fact or details[:100] + "..." if len(details) > 100 else details
        
        prompt = f"""
Generate a subheadline that supports and expands on this headline.

Headline: {headline}
Details: {details}
Key Fact: {key_fact or 'None specified'}

Requirements:
- Provides additional context not in the headline
- Under 150 characters
- Complements but doesn't repeat the headline
- Includes a specific detail or fact

Return only the subheadline text, nothing else.
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You write compelling subheadlines that add value to press releases.",
                temperature=0.7
            )
            return response.strip().strip('"\'')
        except Exception as e:
            logger.error(f"Subheadline generation failed: {e}")
            return key_fact or details[:100]
    
    async def generate_quote(
        self,
        context: str,
        executive_name: str,
        executive_title: str,
        brand_voice: Optional[str] = None,
        angle: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate a natural-sounding executive quote.
        
        Args:
            context: The press release context/topic
            executive_name: Speaker name
            executive_title: Speaker title
            brand_voice: Optional brand voice guidelines
            angle: Optional specific angle for the quote
            
        Returns:
            Quote dict with text and attribution
        """
        if not self.openrouter:
            return self._create_basic_quote(executive_name, executive_title)
        
        prompt = f"""
Write a natural-sounding executive quote for a press release.

Context: {context}
Speaker: {executive_name}, {executive_title}
Brand Voice: {brand_voice or 'professional'}
Angle: {angle or 'general perspective on the announcement'}

The quote should:
- Sound authentic and human (not corporate-speak)
- Be 2-3 sentences
- Add perspective beyond the facts
- Express genuine enthusiasm or insight
- Avoid clichés and buzzwords

Return as JSON:
{{
    "text": "The quote text here...",
    "attribution": "{executive_name}, {executive_title}"
}}
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You write natural executive quotes that sound authentic and human.",
                temperature=0.7,
                json_mode=True
            )
            return json.loads(response)
        except Exception as e:
            logger.error(f"Quote generation failed: {e}")
            return self._create_basic_quote(executive_name, executive_title)
    
    async def generate_boilerplate(
        self,
        company_name: str,
        company_description: Optional[str] = None,
        industry: Optional[str] = None,
        key_facts: Optional[List[str]] = None,
        website: Optional[str] = None
    ) -> str:
        """
        Generate a company boilerplate paragraph.
        
        Args:
            company_name: Company name
            company_description: Existing company description
            industry: Company's industry
            key_facts: Key facts about the company
            website: Company website
            
        Returns:
            Boilerplate paragraph string
        """
        if not self.openrouter:
            return self._create_basic_boilerplate(company_name, company_description, website)
        
        facts_text = "\n".join(f"- {fact}" for fact in (key_facts or []))
        
        prompt = f"""
Write a professional company boilerplate for press releases.

Company Name: {company_name}
Existing Description: {company_description or 'Not provided'}
Industry: {industry or 'Not specified'}
Key Facts:
{facts_text or 'None provided'}
Website: {website or 'Not provided'}

Requirements:
- 2-3 sentences
- Professional and factual
- Includes what the company does
- Mentions key differentiators
- Ends with website if provided
- No marketing fluff

Return only the boilerplate text, nothing else.
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You write professional company boilerplates for press releases.",
                temperature=0.5
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Boilerplate generation failed: {e}")
            return self._create_basic_boilerplate(company_name, company_description, website)
    
    async def generate_headline_variants(
        self,
        topic: str,
        key_point: str,
        count: int = 5
    ) -> List[str]:
        """
        Generate multiple headline options for A/B testing.
        
        Args:
            topic: The press release topic
            key_point: The main news angle
            count: Number of variants to generate
            
        Returns:
            List of headline options
        """
        if not self.openrouter:
            return [
                f"Company Announces {topic}",
                f"New Development: {topic}",
                f"Breaking: {topic}",
            ]
        
        prompt = f"""
Generate {count} compelling press release headlines for this news:

Topic: {topic}
Key Point: {key_point}

Create headlines that are:
- Attention-grabbing
- Under 100 characters each
- Clear and specific
- Newsworthy (not marketing fluff)
- Varied in approach (some direct, some creative)

Return as JSON array: ["headline 1", "headline 2", ...]
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are a headline writing expert for PR Newswire.",
                temperature=0.8,
                json_mode=True
            )
            
            headlines = json.loads(response)
            if isinstance(headlines, list):
                return headlines[:count]
            return headlines.get("headlines", [])
            
        except Exception as e:
            logger.error(f"Headline generation failed: {e}")
            return [f"Company Announces {topic}"]
    
    async def optimize_for_seo(
        self,
        press_release: PressRelease,
        keywords: List[str]
    ) -> PressRelease:
        """
        Optimize a press release for SEO.
        
        Args:
            press_release: The press release to optimize
            keywords: Target keywords
            
        Returns:
            Optimized PressRelease
        """
        if not self.openrouter:
            return press_release
        
        prompt = f"""
Optimize this press release for SEO while maintaining journalistic quality.

TARGET KEYWORDS: {', '.join(keywords)}

CURRENT PRESS RELEASE:
Headline: {press_release.headline}
Subheadline: {press_release.subheadline or 'None'}
Lead: {press_release.lead}
Body: {' '.join(press_release.body)}

Optimize by:
- Including keywords naturally in headline and first paragraph
- Improving readability
- Maintaining AP style and journalistic standards
- Not stuffing keywords unnaturally

Return optimized version as JSON:
{{
    "headline": "...",
    "subheadline": "...",
    "lead": "...",
    "body": ["paragraph 1", "paragraph 2", ...]
}}
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an SEO expert who specializes in press release optimization.",
                temperature=0.5,
                json_mode=True
            )
            
            data = json.loads(response)
            
            return PressRelease(
                headline=data.get("headline", press_release.headline),
                subheadline=data.get("subheadline", press_release.subheadline),
                dateline=press_release.dateline,
                lead=data.get("lead", press_release.lead),
                body=data.get("body", press_release.body),
                quotes=press_release.quotes,
                boilerplate=press_release.boilerplate,
                contact_info=press_release.contact_info,
                word_count=press_release.word_count,
                announcement_type=press_release.announcement_type
            )
            
        except Exception as e:
            logger.error(f"SEO optimization failed: {e}")
            return press_release
    
    def _build_voice_guidelines(
        self,
        tone: str,
        brand_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build voice guidelines string from tone and brand context."""
        guidelines = [f"Tone: {tone}"]
        
        if brand_context:
            if "voice" in brand_context:
                voice = brand_context["voice"]
                if isinstance(voice, dict):
                    if "tone" in voice:
                        guidelines.append(f"Brand Tone: {', '.join(voice['tone']) if isinstance(voice['tone'], list) else voice['tone']}")
                    if "personality" in voice:
                        guidelines.append(f"Personality: {voice['personality']}")
                    if "vocabulary" in voice:
                        vocab = voice['vocabulary']
                        guidelines.append(f"Preferred Vocabulary: {', '.join(vocab) if isinstance(vocab, list) else vocab}")
            
            if "values" in brand_context:
                guidelines.append(f"Brand Values: {', '.join(brand_context['values']) if isinstance(brand_context['values'], list) else brand_context['values']}")
        
        return "Brand Voice Guidelines:\n" + "\n".join(f"- {g}" for g in guidelines)
    
    def _calculate_word_count(self, data: Dict[str, Any]) -> int:
        """Calculate total word count from press release data."""
        count = 0
        count += len(data.get("headline", "").split())
        count += len(data.get("subheadline", "").split()) if data.get("subheadline") else 0
        count += len(data.get("lead", "").split())
        for para in data.get("body", []):
            count += len(para.split())
        for quote in data.get("quotes", []):
            count += len(quote.get("text", "").split())
        count += len(data.get("boilerplate", "").split())
        return count
    
    def _generate_dateline(self, city: str, state: str) -> str:
        """Generate a proper AP-style dateline."""
        date_str = datetime.utcnow().strftime("%B %d, %Y")
        return f"{city.upper()}, {state}"
    
    def _create_basic_headline(
        self,
        details: str,
        announcement_type: AnnouncementType,
        company_name: Optional[str]
    ) -> str:
        """Create a basic headline without AI."""
        type_verbs = {
            AnnouncementType.PRODUCT_LAUNCH: "Launches",
            AnnouncementType.PARTNERSHIP: "Announces Partnership",
            AnnouncementType.FUNDING: "Secures Funding",
            AnnouncementType.EVENT: "Announces Event",
            AnnouncementType.MILESTONE: "Achieves Milestone",
            AnnouncementType.EXECUTIVE: "Appoints New Executive",
            AnnouncementType.AWARD: "Receives Award",
            AnnouncementType.ACQUISITION: "Announces Acquisition",
            AnnouncementType.EXPANSION: "Expands Operations",
            AnnouncementType.RESEARCH: "Releases Research",
        }
        verb = type_verbs.get(announcement_type, "Announces")
        company = company_name or "Company"
        return f"{company} {verb}: {details[:50]}..."
    
    def _create_basic_quote(self, executive_name: str, executive_title: str) -> Dict[str, str]:
        """Create a basic quote without AI."""
        return {
            "text": "We're excited about this development and believe it will bring significant value to our customers and stakeholders.",
            "attribution": f"{executive_name}, {executive_title}"
        }
    
    def _create_basic_boilerplate(
        self,
        company_name: str,
        description: Optional[str],
        website: Optional[str]
    ) -> str:
        """Create a basic boilerplate without AI."""
        boilerplate = description or f"{company_name} is a leading company in its industry, committed to delivering innovative solutions."
        if website:
            boilerplate += f" For more information, visit {website}."
        return boilerplate
    
    def _create_basic_pr_from_input(self, input_data: PressReleaseInput) -> PressRelease:
        """Create a basic press release from input without AI."""
        dateline = f"{input_data.city.upper()}, {input_data.state} — {datetime.utcnow().strftime('%B %d, %Y')}"
        
        lead = f"{input_data.company_name} today announced {input_data.announcement_details}. "
        if input_data.key_facts:
            lead += input_data.key_facts[0]
        
        body = []
        for fact in input_data.key_facts[1:]:
            body.append(fact)
        
        if not body:
            body = ["The company continues to focus on delivering value to customers through innovative solutions."]
        
        boilerplate = input_data.company_description or f"{input_data.company_name} is a leading company in its industry."
        if input_data.company_website:
            boilerplate += f" For more information, visit {input_data.company_website}."
        
        word_count = len(lead.split()) + sum(len(p.split()) for p in body)
        
        return PressRelease(
            headline=f"{input_data.company_name} Announces {input_data.announcement_type.value.replace('_', ' ').title()}",
            dateline=dateline,
            lead=lead,
            body=body,
            quotes=[{
                "text": "We are excited about this milestone and look forward to the opportunities it brings.",
                "attribution": f"{input_data.executive_name}, {input_data.executive_title}"
            }],
            boilerplate=boilerplate,
            contact_info={
                "company": input_data.company_name,
                "name": input_data.contact_name,
                "email": input_data.contact_email,
                "phone": input_data.contact_phone,
            },
            word_count=word_count,
            announcement_type=input_data.announcement_type.value
        )


# Convenience functions
async def generate_press_release(
    topic: str,
    key_points: List[str],
    company_info: Dict[str, Any],
    **kwargs
) -> PressRelease:
    """Generate a press release using the legacy dictionary interface."""
    generator = PressReleaseGenerator()
    return await generator.generate_from_dict(topic, key_points, company_info, **kwargs)


async def generate_press_release_from_input(
    input_data: PressReleaseInput,
    brand_context: Optional[Dict[str, Any]] = None,
    openrouter_api_key: Optional[str] = None
) -> PressRelease:
    """Generate a press release using the structured input interface."""
    generator = PressReleaseGenerator(openrouter_api_key)
    return await generator.generate(input_data, brand_context)
