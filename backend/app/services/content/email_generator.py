"""
Email Generator Service

Generates complete emails with:
- AI-generated content matching brand voice
- MJML templates for cross-client compatibility
- Subject line generation with A/B variants
- Preheader text generation
- CTA optimization
- Multiple output formats (HTML, MJML, plaintext)
"""
import logging
import os
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from ..ai.openrouter import OpenRouterService
from .mjml_templates import MJMLTemplateSystem, generate_email, GeneratedEmail
from ...core.config import get_settings

logger = logging.getLogger(__name__)


class EmailType(str, Enum):
    """Supported email types."""
    PROMOTIONAL = "promotional"
    NEWSLETTER = "newsletter"
    WELCOME = "welcome"
    ANNOUNCEMENT = "announcement"
    NURTURE = "nurture"
    TRANSACTIONAL = "transactional"


@dataclass
class SubjectLineVariant:
    """A subject line variant for A/B testing."""
    text: str
    predicted_open_rate: float = 0.0
    emoji: bool = False
    urgency_level: str = "medium"  # low, medium, high


@dataclass
class EmailContent:
    """
    Structured email content with multiple output formats.
    
    Provides methods to convert to MJML and HTML for rendering.
    """
    subject: str
    preheader: str
    headline: str
    body_html: str
    body_text: str
    cta_text: str
    cta_url: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_mjml(self, template: str, brand_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert content to MJML using the specified template.
        
        Args:
            template: Template name (welcome, newsletter, promotional, etc.)
            brand_data: Brand colors, fonts, etc.
            
        Returns:
            MJML string
        """
        system = MJMLTemplateSystem()
        brand = brand_data or {"primary_color": "#3b82f6", "font_family": "Arial"}
        
        content_data = {
            "headline": self.headline,
            "body_content": self.body_html,
            "cta_text": self.cta_text,
            "cta_url": self.cta_url,
            "preheader": self.preheader,
            **self.metadata
        }
        
        return system.apply_brand(template, brand, content_data)
    
    def to_html(self, template: str = "promotional", brand_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert content to HTML.
        
        Args:
            template: Template name
            brand_data: Brand colors, fonts, etc.
            
        Returns:
            HTML string
        """
        system = MJMLTemplateSystem()
        mjml = self.to_mjml(template, brand_data)
        return system.mjml_to_html(mjml)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "preheader": self.preheader,
            "headline": self.headline,
            "body_html": self.body_html,
            "body_text": self.body_text,
            "cta_text": self.cta_text,
            "cta_url": self.cta_url,
            "metadata": self.metadata
        }


@dataclass
class NewsletterSection:
    """A section within a newsletter."""
    title: str
    content: str
    image_url: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None


class EmailGenerator:
    """
    Generate complete emails with AI-powered content.
    
    Features:
    - Brand voice integration
    - MJML template system
    - Subject line generation with A/B variants
    - Preheader text generation
    - CTA optimization
    - Multiple email types (promotional, newsletter, welcome, announcement, nurture, transactional)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.openrouter = None
        if self.settings.openrouter_api_key:
            self.openrouter = OpenRouterService(
                api_key=self.settings.openrouter_api_key,
                timeout=120.0
            )
        self.template_system = MJMLTemplateSystem()
    
    async def generate_email_content(
        self,
        email_type: EmailType,
        topic: str,
        brand_context: Optional[Dict[str, Any]] = None,
        target_audience: Optional[str] = None
    ) -> EmailContent:
        """
        Generate structured email content.
        
        Args:
            email_type: Type of email to generate
            topic: Main topic/subject of the email
            brand_context: Brand voice, colors, fonts
            target_audience: Target audience description
            
        Returns:
            EmailContent with all fields populated
        """
        brand_voice = brand_context.get("voice", {}) if brand_context else {}
        
        # Generate subject and preheader
        subject = await self._generate_subject_line(topic, email_type.value, brand_voice)
        preheader = await self._generate_preheader(topic, email_type.value, brand_voice)
        
        # Generate main content
        content_data = await self._generate_content(
            email_type=email_type.value,
            topic=topic,
            key_points=[],
            brand_voice=brand_voice,
            target_audience=target_audience,
            tone=brand_voice.get("tone", ["professional"])[0] if brand_voice.get("tone") else "professional"
        )
        
        # Generate optimized CTA
        cta = await self._optimize_cta(email_type.value, topic, brand_voice)
        
        return EmailContent(
            subject=subject,
            preheader=preheader,
            headline=content_data.get("headline", f"About {topic}"),
            body_html=content_data.get("body_content", ""),
            body_text=self._html_to_text(content_data.get("body_content", "")),
            cta_text=cta.get("text", content_data.get("cta_text", "Learn More")),
            cta_url=cta.get("url", content_data.get("cta_url", "/")),
            metadata=content_data
        )
    
    async def generate(
        self,
        email_type: str,
        topic: str,
        key_points: List[str],
        brand_voice: Optional[Dict[str, Any]] = None,
        brand_data: Optional[Dict[str, Any]] = None,
        target_audience: Optional[str] = None,
        tone: str = "professional"
    ) -> GeneratedEmail:
        """
        Generate a complete email.
        
        Args:
            email_type: Type of email (welcome, newsletter, promotional, etc.)
            topic: Main topic of the email
            key_points: Key points to include
            brand_voice: Brand voice guidelines
            brand_data: Brand colors, fonts, etc.
            target_audience: Target audience description
            tone: Email tone
            
        Returns:
            GeneratedEmail with all formats
        """
        # Generate content with AI
        content_data = await self._generate_content(
            email_type=email_type,
            topic=topic,
            key_points=key_points,
            brand_voice=brand_voice,
            target_audience=target_audience,
            tone=tone
        )
        
        # Generate subject line
        subject = await self._generate_subject_line(
            topic=topic,
            email_type=email_type,
            brand_voice=brand_voice
        )
        
        # Get default brand data if not provided
        if not brand_data:
            brand_data = {
                "primary_color": "#3b82f6",
                "font_family": "Arial"
            }
        
        # Generate email using template system
        email = generate_email(
            template_name=email_type,
            brand_data=brand_data,
            content_data=content_data,
            subject=subject
        )
        
        return email
    
    async def _generate_content(
        self,
        email_type: str,
        topic: str,
        key_points: List[str],
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str],
        tone: str
    ) -> Dict[str, str]:
        """Generate email content using AI."""
        voice_guidelines = ""
        if brand_voice:
            voice_tone = ", ".join(brand_voice.get("tone", [tone]))
            personality = brand_voice.get("personality", "")
            vocabulary = ", ".join(brand_voice.get("vocabulary", []))
            voice_guidelines = f"""
Brand Voice:
- Tone: {voice_tone}
- Personality: {personality}
- Preferred words: {vocabulary}
"""
        
        # Template-specific prompts
        template_prompts = {
            "welcome": f"""
Create welcome email content for: {topic}

Key points to include:
{chr(10).join(f"- {point}" for point in key_points)}

Target audience: {target_audience or "new subscribers"}
{voice_guidelines}

Generate content for these sections:
- headline: Main welcome headline
- subheadline: Supporting text
- welcome_message: Personal welcome paragraph
- body_content: Main content (2-3 paragraphs)
- cta_text: Call-to-action button text
- cta_url: URL placeholder (/welcome-action)
- closing_message: Sign-off paragraph
- footer_text: Brief footer message

Return as JSON with these exact keys.
""",
            "newsletter": f"""
Create newsletter content for: {topic}

Key points to include:
{chr(10).join(f"- {point}" for point in key_points)}

Target audience: {target_audience or "subscribers"}
{voice_guidelines}

Generate content for these sections:
- newsletter_title: Newsletter name/issue
- issue_date: Date placeholder (Month Year)
- headline: Main story headline
- intro_text: Brief introduction
- articles: Article summaries (use placeholder {{article_content}})
- cta_section_title: Section title
- cta_section_text: Call-to-action text
- cta_text: Button text
- cta_url: URL placeholder (/read-more)
- footer_text: Footer message

Return as JSON with these exact keys.
""",
            "promotional": f"""
Create promotional email content for: {topic}

Key points to include:
{chr(10).join(f"- {point}" for point in key_points)}

Target audience: {target_audience or "customers"}
{voice_guidelines}

Generate content for these sections:
- headline: Attention-grabbing headline
- subheadline: Supporting offer text
- offer_text: Main offer description
- discount_code: Placeholder code (SAVE20)
- expiry_text: Urgency message
- cta_text: Button text (Shop Now)
- cta_url: URL placeholder (/shop)
- terms_text: Brief terms
- footer_text: Footer message

Return as JSON with these exact keys.
""",
            "announcement": f"""
Create announcement email content for: {topic}

Key points to include:
{chr(10).join(f"- {point}" for point in key_points)}

Target audience: {target_audience or "customers and subscribers"}
{voice_guidelines}

Generate content for these sections:
- announcement_label: Label (e.g., "BIG NEWS")
- headline: Main announcement headline
- hero_image: Placeholder image URL
- hero_alt: Image alt text
- section_title: Content section title
- body_content: Main announcement text (2-3 paragraphs)
- key_features: Key features/benefits list
- cta_text: Button text
- cta_url: URL placeholder (/learn-more)
- additional_info: Additional details
- footer_text: Footer message

Return as JSON with these exact keys.
""",
            "nurture": f"""
Create nurture email content for: {topic}

Key points to include:
{chr(10).join(f"- {point}" for point in key_points)}

Target audience: {target_audience or "prospects"}
{voice_guidelines}

Generate content for these sections:
- headline: Educational headline
- subheadline: Supporting text
- opening_text: Opening paragraph
- tip_title: Tip/insight title
- tip_content: Tip content
- resource_title: Resource section title
- resource_content: Resource description
- cta_text: Button text (Learn More)
- cta_url: URL placeholder (/resources)
- closing_text: Friendly closing
- footer_text: Footer message

Return as JSON with these exact keys.
""",
            "transactional": f"""
Create transactional email content for: {topic}

Key points to include:
{chr(10).join(f"- {point}" for point in key_points)}

Target audience: {target_audience or "customers"}
{voice_guidelines}

Generate content for these sections:
- headline: Clear action headline
- transaction_type: Type of transaction (order, receipt, confirmation, etc.)
- transaction_id: Placeholder ID (#12345)
- summary_text: Brief summary of the transaction
- details_content: Transaction details
- next_steps: What the user should do next
- support_text: How to get help
- cta_text: Button text (View Details)
- cta_url: URL placeholder (/account)
- footer_text: Footer message

Return as JSON with these exact keys.
"""
        }
        
        prompt = template_prompts.get(email_type, template_prompts["newsletter"])
        
        if not self.openrouter:
            # Return fallback content
            return self._get_fallback_content(email_type, topic)
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an expert email copywriter who creates engaging, high-converting emails.",
                temperature=0.7,
                json_mode=True
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return self._get_fallback_content(email_type, topic)
    
    async def _generate_subject_line(
        self,
        topic: str,
        email_type: str,
        brand_voice: Optional[Dict[str, Any]]
    ) -> str:
        """Generate a subject line."""
        if not self.openrouter:
            return f"New: {topic}"
        
        voice_note = ""
        if brand_voice:
            voice_note = f"Use a {', '.join(brand_voice.get('tone', ['professional']))} tone."
        
        prompt = f"""
Write a compelling subject line for this email:

Topic: {topic}
Type: {email_type}

Requirements:
- Under 50 characters
- No spam trigger words
- Creates curiosity or urgency
- {voice_note}

Return just the subject line text, nothing else.
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You write email subject lines that get opened.",
                temperature=0.8
            )
            
            return response.strip().strip('"\'')
            
        except Exception as e:
            logger.error(f"Subject line generation failed: {e}")
            return f"New: {topic}"
    
    async def generate_subject_variants(
        self,
        topic: str,
        count: int = 5
    ) -> List[SubjectLineVariant]:
        """
        Generate multiple subject line variants for A/B testing.
        
        Args:
            topic: Email topic
            count: Number of variants to generate
            
        Returns:
            List of SubjectLineVariant
        """
        if not self.openrouter:
            return [
                SubjectLineVariant(text=f"New: {topic}", predicted_open_rate=25.0),
                SubjectLineVariant(text=f"Introducing: {topic}", predicted_open_rate=23.0),
                SubjectLineVariant(text=f"You won't believe: {topic}", predicted_open_rate=28.0, urgency_level="high"),
            ]
        
        prompt = f"""
Generate {count} subject line variants for: {topic}

Create variety in:
- Length (short vs. descriptive)
- Tone (professional vs. casual vs. urgent)
- Use of emoji (some with, some without)
- Curiosity gap vs. direct benefit

Return as JSON array:
[
    {{
        "text": "Subject line",
        "predicted_open_rate": 28.5,
        "emoji": false,
        "urgency_level": "medium"
    }}
]
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an email marketing expert who writes high-performing subject lines.",
                temperature=0.8,
                json_mode=True
            )
            
            data = json.loads(response)
            if isinstance(data, list):
                return [
                    SubjectLineVariant(
                        text=item.get("text", ""),
                        predicted_open_rate=item.get("predicted_open_rate", 0.0),
                        emoji=item.get("emoji", False),
                        urgency_level=item.get("urgency_level", "medium")
                    )
                    for item in data
                ]
            return []
            
        except Exception as e:
            logger.error(f"Subject variant generation failed: {e}")
            return [SubjectLineVariant(text=f"New: {topic}")]
    
    def _get_fallback_content(self, email_type: str, topic: str) -> Dict[str, str]:
        """Get fallback content when AI fails."""
        fallbacks = {
            "welcome": {
                "headline": f"Welcome to {topic}!",
                "subheadline": "We're excited to have you on board",
                "welcome_message": "Thank you for joining us! We're thrilled to have you as part of our community.",
                "body_content": "Here's what you can expect from us and how to get started.",
                "cta_text": "Get Started",
                "cta_url": "/welcome",
                "closing_message": "Looking forward to connecting with you!",
                "footer_text": "You're receiving this because you signed up for our updates."
            },
            "newsletter": {
                "newsletter_title": "Monthly Update",
                "issue_date": "January 2026",
                "headline": f"Latest Updates on {topic}",
                "intro_text": "Here's what's new this month.",
                "articles": "{{article_content}}",
                "cta_section_title": "Want to learn more?",
                "cta_section_text": "Check out our latest resources.",
                "cta_text": "Read More",
                "cta_url": "/newsletter",
                "footer_text": "Thanks for reading!"
            },
            "promotional": {
                "headline": f"Special Offer: {topic}",
                "subheadline": "Don't miss out on this limited-time deal",
                "offer_text": "We're excited to offer you something special.",
                "discount_code": "SAVE20",
                "expiry_text": "Offer expires soon!",
                "cta_text": "Shop Now",
                "cta_url": "/shop",
                "terms_text": "Terms and conditions apply.",
                "footer_text": "You're receiving this because you're a valued customer."
            },
            "announcement": {
                "announcement_label": "BIG NEWS",
                "headline": f"Announcing: {topic}",
                "hero_image": get_settings().email_placeholder_image_url,
                "hero_alt": "Announcement",
                "section_title": "What This Means for You",
                "body_content": "We're excited to share this news with you.",
                "key_features": "• New features\n• Better experience\n• More value",
                "cta_text": "Learn More",
                "cta_url": "/announcement",
                "additional_info": "Stay tuned for more updates.",
                "footer_text": "Thanks for being part of our journey!"
            },
            "nurture": {
                "headline": f"Tips on {topic}",
                "subheadline": "Insights to help you succeed",
                "opening_text": "We wanted to share some valuable insights with you.",
                "tip_title": "Pro Tip",
                "tip_content": "Here's something that can make a real difference.",
                "resource_title": "Helpful Resource",
                "resource_content": "Check out this resource we think you'll love.",
                "cta_text": "Learn More",
                "cta_url": "/resources",
                "closing_text": "Happy learning!",
                "footer_text": "Questions? Just reply to this email."
            },
            "transactional": {
                "headline": f"Your {topic}",
                "transaction_type": "Confirmation",
                "transaction_id": "#12345",
                "summary_text": "Here's a summary of your recent activity.",
                "details_content": "Transaction details will appear here.",
                "next_steps": "No action required at this time.",
                "support_text": "Need help? Contact our support team.",
                "cta_text": "View Details",
                "cta_url": "/account",
                "footer_text": "This is an automated message. Please do not reply."
            }
        }
        
        return fallbacks.get(email_type, fallbacks["newsletter"])
    
    async def _generate_preheader(
        self,
        topic: str,
        email_type: str,
        brand_voice: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate preheader text for email preview.
        
        Preheader is the preview text shown in email clients after the subject line.
        """
        if not self.openrouter:
            preheaders = {
                "welcome": "We're excited to have you join us!",
                "newsletter": "This month's top stories and updates",
                "promotional": "Limited time offer inside",
                "announcement": "Big news you won't want to miss",
                "nurture": "Tips and insights just for you",
                "transactional": "Important information about your account"
            }
            return preheaders.get(email_type, f"Learn more about {topic}")
        
        voice_note = ""
        if brand_voice:
            voice_note = f"Use a {', '.join(brand_voice.get('tone', ['professional']))} tone."
        
        prompt = f"""
Write a compelling preheader text for this email:

Topic: {topic}
Type: {email_type}

Requirements:
- 40-90 characters (optimal for most email clients)
- Complements the subject line, doesn't repeat it
- Creates curiosity or provides value preview
- {voice_note}

Return just the preheader text, nothing else.
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You write email preheader text that increases open rates.",
                temperature=0.7
            )
            
            return response.strip().strip('"\'')
            
        except Exception as e:
            logger.error(f"Preheader generation failed: {e}")
            return f"Learn more about {topic}"
    
    async def _optimize_cta(
        self,
        email_type: str,
        topic: str,
        brand_voice: Optional[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Generate optimized CTA (Call-to-Action) text and URL.
        
        Returns:
            Dict with 'text' and 'url' keys
        """
        if not self.openrouter:
            ctas = {
                "welcome": {"text": "Get Started", "url": "/welcome"},
                "newsletter": {"text": "Read More", "url": "/blog"},
                "promotional": {"text": "Shop Now", "url": "/shop"},
                "announcement": {"text": "Learn More", "url": "/announcement"},
                "nurture": {"text": "Explore Resources", "url": "/resources"},
                "transactional": {"text": "View Details", "url": "/account"}
            }
            return ctas.get(email_type, {"text": "Learn More", "url": "/"})
        
        voice_note = ""
        if brand_voice:
            voice_note = f"Use a {', '.join(brand_voice.get('tone', ['professional']))} tone."
        
        prompt = f"""
Create an optimized CTA (Call-to-Action) for this email:

Topic: {topic}
Type: {email_type}

Requirements:
- Button text: 2-4 words, action-oriented
- Creates urgency or clear value
- {voice_note}

Return as JSON:
{{
    "text": "CTA button text",
    "url": "/suggested-path"
}}
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You write high-converting CTAs for email marketing.",
                temperature=0.7,
                json_mode=True
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"CTA optimization failed: {e}")
            return {"text": "Learn More", "url": "/"}
    
    async def generate_newsletter(
        self,
        sections: List[Dict[str, Any]],
        brand_context: Optional[Dict[str, Any]] = None,
        newsletter_title: Optional[str] = None
    ) -> GeneratedEmail:
        """
        Generate a multi-section newsletter.
        
        Args:
            sections: List of section dicts with 'title', 'content', 'image_url', 'cta_text', 'cta_url'
            brand_context: Brand voice, colors, fonts
            newsletter_title: Optional newsletter title/name
            
        Returns:
            GeneratedEmail with all formats
        """
        brand_data = brand_context or {}
        brand_voice = brand_data.get("voice", {})
        
        # Generate newsletter title if not provided
        if not newsletter_title:
            newsletter_title = "Monthly Newsletter"
        
        # Build article content from sections
        article_mjml = ""
        for i, section in enumerate(sections):
            section_title = section.get("title", f"Section {i + 1}")
            section_content = section.get("content", "")
            section_image = section.get("image_url")
            section_cta_text = section.get("cta_text")
            section_cta_url = section.get("cta_url")
            
            article_mjml += f'''
    <mj-section background-color="white" padding="20px 30px">
      <mj-column>
        {"<mj-image src='" + section_image + "' alt='" + section_title + "' padding='0 0 15px' />" if section_image else ""}
        <mj-text font-size="18px" font-weight="bold" color="#333333">
          {section_title}
        </mj-text>
        <mj-text>
          {section_content}
        </mj-text>
        {"<mj-button href='" + section_cta_url + "'>" + section_cta_text + "</mj-button>" if section_cta_text and section_cta_url else ""}
      </mj-column>
    </mj-section>
    <mj-section padding="0 30px">
      <mj-column>
        <mj-divider border-color="#e0e0e0" />
      </mj-column>
    </mj-section>
'''
        
        # Generate subject line
        topics = [s.get("title", "") for s in sections[:3]]
        topic_summary = ", ".join(topics) if topics else "Latest Updates"
        subject = await self._generate_subject_line(topic_summary, "newsletter", brand_voice)
        preheader = await self._generate_preheader(topic_summary, "newsletter", brand_voice)
        
        # Build content data
        from datetime import datetime
        content_data = {
            "newsletter_title": newsletter_title,
            "issue_date": datetime.now().strftime("%B %Y"),
            "headline": f"What's New This Month",
            "intro_text": "Here are the latest updates and stories we've curated for you.",
            "articles": article_mjml,
            "cta_section_title": "Want more?",
            "cta_section_text": "Visit our website for the full experience.",
            "cta_text": "Visit Website",
            "cta_url": "/",
            "footer_text": "Thanks for being a subscriber!",
            "preheader": preheader
        }
        
        # Get brand colors
        primary_color = brand_data.get("primary_color", "#3b82f6")
        font_family = brand_data.get("font_family", "Arial")
        
        brand_styling = {
            "primary_color": primary_color,
            "font_family": font_family
        }
        
        # Generate email
        email = generate_email(
            template_name="newsletter",
            brand_data=brand_styling,
            content_data=content_data,
            subject=subject
        )
        
        # Add preheader to metadata
        email.metadata["preheader"] = preheader
        email.metadata["section_count"] = len(sections)
        
        return email
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode HTML entities (& must be last to avoid double-decoding)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get available email templates."""
        return self.template_system.get_available_templates()
    
    async def generate_complete_email(
        self,
        email_type: str,
        subject: str,
        headline: str,
        body_content: str,
        cta_text: str,
        cta_url: str,
        brand_colors: Optional[Dict[str, str]] = None,
        campaign_id: Optional[str] = None,
        save_to_file: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate a complete email with all components.
        
        This method matches the API spec for POST /api/content/email/generate.
        
        Args:
            email_type: Type of email (promotional, welcome, nurture, newsletter, transactional)
            subject: Email subject line
            headline: Main headline
            body_content: Main message content
            cta_text: Call-to-action button text
            cta_url: Call-to-action URL
            brand_colors: Brand colors dict (e.g., {"primary": "#007bff"})
            campaign_id: Optional campaign ID for reference
            save_to_file: Whether to save the email to files
            
        Returns:
            Dict with email_id, html_content, text_content, subject_lines, preview_text, preview_url
        """
        # Generate email ID
        email_id = str(uuid.uuid4())
        
        # Get brand data
        brand_data = {
            "primary_color": brand_colors.get("primary", "#3b82f6") if brand_colors else "#3b82f6",
            "font_family": "Arial"
        }
        
        # Generate subject line variants
        subject_lines = await self._generate_subject_variants(subject, email_type)
        
        # Generate preview text
        preview_text = await self._generate_preheader(subject, email_type, None)
        
        # Build content data for template
        content_data = {
            "headline": headline,
            "subheadline": "",
            "body_content": body_content,
            "cta_text": cta_text,
            "cta_url": cta_url,
            "preheader": preview_text,
            "footer_text": "You're receiving this email because you subscribed to our updates.",
            "welcome_message": body_content[:200] if email_type == "welcome" else "",
            "closing_message": "Thank you for your continued support!",
            "offer_text": body_content if email_type == "promotional" else "",
            "discount_code": "",
            "expiry_text": "",
            "terms_text": "",
            "newsletter_title": headline if email_type == "newsletter" else "",
            "issue_date": datetime.now().strftime("%B %Y"),
            "intro_text": body_content[:150] if email_type == "newsletter" else "",
            "articles": "",
            "cta_section_title": "Take Action",
            "cta_section_text": "",
            "announcement_label": "ANNOUNCEMENT" if email_type == "announcement" else "",
            "hero_image": self.settings.email_placeholder_image_url,
            "hero_alt": headline,
            "section_title": headline,
            "key_features": "",
            "additional_info": "",
            "opening_text": body_content[:150] if email_type == "nurture" else "",
            "tip_title": "Pro Tip",
            "tip_content": "",
            "resource_title": "Helpful Resource",
            "resource_content": "",
            "closing_text": "Looking forward to connecting with you!",
            "transaction_type": "Notification" if email_type == "transactional" else "",
            "transaction_id": "",
            "summary_text": body_content[:150] if email_type == "transactional" else "",
            "details_content": body_content if email_type == "transactional" else "",
            "next_steps": "",
            "support_text": "Need help? Contact our support team.",
        }
        
        # Generate email using template
        email = generate_email(
            template_name=email_type,
            brand_data=brand_data,
            content_data=content_data,
            subject=subject
        )
        
        # Generate plain text version
        text_content = self._html_to_text(email.html)
        
        # Save to file if requested
        preview_url = None
        file_path = None
        if save_to_file:
            file_path = await self._save_email(
                email_id=email_id,
                email_type=email_type,
                subject=subject,
                html_content=email.html,
                text_content=text_content,
                subject_lines=subject_lines,
                preview_text=preview_text,
                campaign_id=campaign_id,
            )
            preview_url = f"/preview/emails/{email_id}"
        
        return {
            "success": True,
            "email_id": email_id,
            "html_content": email.html,
            "text_content": text_content,
            "subject_lines": subject_lines,
            "preview_text": preview_text,
            "preview_url": preview_url,
            "file_path": file_path,
            "mjml": email.mjml,
        }
    
    async def _generate_subject_variants(
        self,
        base_subject: str,
        email_type: str,
        count: int = 3,
    ) -> List[str]:
        """Generate subject line variants for A/B testing."""
        if not self.openrouter:
            # Return fallback variants
            return [
                base_subject,
                f"🎉 {base_subject}",
                f"Don't miss: {base_subject}",
            ]
        
        prompt = f"""
Generate {count} subject line variants for this email:

Original subject: {base_subject}
Email type: {email_type}

Requirements:
- Each variant should be unique but convey the same message
- Keep under 50 characters
- Mix of styles: direct, curiosity-driven, emoji-enhanced
- No spam trigger words

Return as JSON array of strings:
["Subject 1", "Subject 2", "Subject 3"]
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You write high-performing email subject lines.",
                temperature=0.8,
                json_mode=True
            )
            
            data = json.loads(response)
            if isinstance(data, list):
                return data[:count]
            return [base_subject]
            
        except Exception as e:
            logger.error(f"Subject variant generation failed: {e}")
            return [base_subject, f"🎉 {base_subject}", f"Don't miss: {base_subject}"]
    
    async def _save_email(
        self,
        email_id: str,
        email_type: str,
        subject: str,
        html_content: str,
        text_content: str,
        subject_lines: List[str],
        preview_text: str,
        campaign_id: Optional[str] = None,
    ) -> str:
        """Save email to files."""
        # Create output directory
        base_dir = os.path.join(self.settings.output_dir, "emails")
        os.makedirs(base_dir, exist_ok=True)
        
        # Create email directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        email_dir = os.path.join(base_dir, f"{email_type}_{timestamp}_{email_id[:8]}")
        os.makedirs(email_dir, exist_ok=True)
        
        # Save HTML
        html_path = os.path.join(email_dir, "email.html")
        with open(html_path, "w") as f:
            f.write(html_content)
        
        # Save plain text
        text_path = os.path.join(email_dir, "email.txt")
        with open(text_path, "w") as f:
            f.write(text_content)
        
        # Save metadata
        metadata = {
            "email_id": email_id,
            "email_type": email_type,
            "campaign_id": campaign_id,
            "subject": subject,
            "subject_lines": subject_lines,
            "preview_text": preview_text,
            "created_at": datetime.now().isoformat(),
        }
        metadata_path = os.path.join(email_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Create preview HTML page
        preview_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Preview: {subject}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .preview-container {{ max-width: 800px; margin: 0 auto; }}
        .preview-header {{ background: #333; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .preview-header h1 {{ margin: 0 0 10px 0; font-size: 18px; }}
        .preview-header p {{ margin: 0; opacity: 0.8; font-size: 14px; }}
        .subject-lines {{ background: #fff; padding: 20px; border-bottom: 1px solid #ddd; }}
        .subject-lines h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #666; }}
        .subject-lines ul {{ margin: 0; padding-left: 20px; }}
        .subject-lines li {{ margin: 5px 0; }}
        .email-frame {{ background: white; border: 1px solid #ddd; border-radius: 0 0 8px 8px; }}
        iframe {{ width: 100%; height: 800px; border: none; }}
    </style>
</head>
<body>
    <div class="preview-container">
        <div class="preview-header">
            <h1>📧 Email Preview</h1>
            <p>Type: {email_type} | ID: {email_id}</p>
        </div>
        <div class="subject-lines">
            <h3>Subject Line Variants:</h3>
            <ul>
                {"".join(f"<li>{s}</li>" for s in subject_lines)}
            </ul>
            <p style="margin-top: 10px; color: #666; font-size: 12px;">Preview text: {preview_text}</p>
        </div>
        <div class="email-frame">
            <iframe src="email.html"></iframe>
        </div>
    </div>
</body>
</html>"""
        
        preview_path = os.path.join(email_dir, "preview.html")
        with open(preview_path, "w") as f:
            f.write(preview_html)
        
        logger.info(f"Saved email to {email_dir}")
        return email_dir


# Convenience function
async def generate_email_content(
    email_type: str,
    topic: str,
    key_points: List[str],
    **kwargs
) -> GeneratedEmail:
    """Generate email content."""
    generator = EmailGenerator()
    return await generator.generate(
        email_type=email_type,
        topic=topic,
        key_points=key_points,
        **kwargs
    )