"""
Email Sequence Service

Generates email sequences (drip campaigns) with:
- Multiple sequence types: welcome, nurture, onboarding, re-engagement
- Timing schedules for automated sending
- Unique content for each email in the sequence
- Brand voice consistency across all emails
"""
import logging
import os
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..ai.openrouter import OpenRouterService
from .email_generator import EmailGenerator, EmailType
from .mjml_templates import MJMLTemplateSystem, generate_email, GeneratedEmail
from ...core.config import get_settings

logger = logging.getLogger(__name__)


class SequenceType(str, Enum):
    """Supported email sequence types."""
    WELCOME = "welcome"
    NURTURE = "nurture"
    ONBOARDING = "onboarding"
    RE_ENGAGEMENT = "re_engagement"


# Default timing schedules for each sequence type (days after trigger)
SEQUENCE_SCHEDULES = {
    SequenceType.WELCOME: [1, 3, 5, 7, 14],
    SequenceType.NURTURE: [1, 4, 8, 12, 18, 25, 35],
    SequenceType.ONBOARDING: [1, 2, 4, 7, 10, 14],
    SequenceType.RE_ENGAGEMENT: [1, 3, 7, 14, 30, 45],
}

# Sequence content themes for each type
SEQUENCE_THEMES = {
    SequenceType.WELCOME: [
        {"theme": "Welcome & Introduction", "goal": "Introduce the brand and set expectations"},
        {"theme": "Getting Started", "goal": "Help user take first steps"},
        {"theme": "Key Features", "goal": "Highlight main value propositions"},
        {"theme": "Success Stories", "goal": "Build trust with social proof"},
        {"theme": "Community & Support", "goal": "Connect user with resources"},
        {"theme": "Exclusive Offer", "goal": "Drive first conversion"},
        {"theme": "Check-in", "goal": "Re-engage and gather feedback"},
    ],
    SequenceType.NURTURE: [
        {"theme": "Educational Content", "goal": "Provide value and establish expertise"},
        {"theme": "Industry Insights", "goal": "Share relevant trends and data"},
        {"theme": "Problem-Solution", "goal": "Address common pain points"},
        {"theme": "Case Study", "goal": "Demonstrate real-world results"},
        {"theme": "Tips & Best Practices", "goal": "Actionable advice"},
        {"theme": "Resource Roundup", "goal": "Curated helpful content"},
        {"theme": "Soft Pitch", "goal": "Gentle product introduction"},
    ],
    SequenceType.ONBOARDING: [
        {"theme": "Welcome & Setup", "goal": "Get user started immediately"},
        {"theme": "Quick Win", "goal": "Help achieve first success"},
        {"theme": "Feature Deep Dive", "goal": "Explore key functionality"},
        {"theme": "Pro Tips", "goal": "Advanced usage guidance"},
        {"theme": "Integration Guide", "goal": "Connect with other tools"},
        {"theme": "Progress Check", "goal": "Celebrate milestones"},
        {"theme": "Next Level", "goal": "Introduce advanced features"},
    ],
    SequenceType.RE_ENGAGEMENT: [
        {"theme": "We Miss You", "goal": "Acknowledge absence warmly"},
        {"theme": "What's New", "goal": "Highlight recent improvements"},
        {"theme": "Special Offer", "goal": "Incentivize return"},
        {"theme": "Success Story", "goal": "Remind of value"},
        {"theme": "Last Chance", "goal": "Create urgency"},
        {"theme": "Feedback Request", "goal": "Understand why they left"},
        {"theme": "Final Goodbye", "goal": "Graceful exit with door open"},
    ],
}


@dataclass
class SequenceEmail:
    """A single email within a sequence."""
    day: int
    position: int
    subject: str
    html_content: str
    text_content: str
    preview_text: str
    theme: str
    goal: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self.day,
            "position": self.position,
            "subject": self.subject,
            "html_content": self.html_content,
            "text_content": self.text_content,
            "preview_text": self.preview_text,
            "theme": self.theme,
            "goal": self.goal,
        }


@dataclass
class EmailSequenceResult:
    """Result of generating an email sequence."""
    sequence_id: str
    sequence_type: str
    emails: List[SequenceEmail]
    timing_schedule: List[int]
    total_emails: int
    brand_data: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "sequence_type": self.sequence_type,
            "emails": [e.to_dict() for e in self.emails],
            "timing_schedule": self.timing_schedule,
            "total_emails": self.total_emails,
            "brand_data": self.brand_data,
            "file_path": self.file_path,
        }


class EmailSequenceGenerator:
    """
    Generate email sequences (drip campaigns).
    
    Features:
    - Multiple sequence types (welcome, nurture, onboarding, re-engagement)
    - Customizable timing schedules
    - AI-generated unique content for each email
    - Brand voice consistency
    - File storage for generated sequences
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.openrouter = None
        if self.settings.openrouter_api_key:
            self.openrouter = OpenRouterService(
                api_key=self.settings.openrouter_api_key,
                timeout=120.0
            )
        self.email_generator = EmailGenerator()
        self.template_system = MJMLTemplateSystem()
    
    async def generate_sequence(
        self,
        sequence_type: SequenceType,
        num_emails: int = 5,
        brand_data: Optional[Dict[str, Any]] = None,
        brand_voice: Optional[Dict[str, Any]] = None,
        target_audience: Optional[str] = None,
        custom_schedule: Optional[List[int]] = None,
        campaign_id: Optional[str] = None,
        save_to_file: bool = True,
    ) -> EmailSequenceResult:
        """
        Generate a complete email sequence.
        
        Args:
            sequence_type: Type of sequence (welcome, nurture, onboarding, re_engagement)
            num_emails: Number of emails in the sequence (1-10)
            brand_data: Brand colors, fonts, etc.
            brand_voice: Brand voice guidelines
            target_audience: Target audience description
            custom_schedule: Custom timing schedule (days)
            campaign_id: Optional campaign ID for reference
            save_to_file: Whether to save the sequence to files
            
        Returns:
            EmailSequenceResult with all generated emails
        """
        # Validate num_emails
        num_emails = max(1, min(10, num_emails))
        
        # Get timing schedule
        if custom_schedule:
            timing_schedule = custom_schedule[:num_emails]
        else:
            default_schedule = SEQUENCE_SCHEDULES.get(sequence_type, SEQUENCE_SCHEDULES[SequenceType.NURTURE])
            timing_schedule = default_schedule[:num_emails]
        
        # Extend schedule if needed
        while len(timing_schedule) < num_emails:
            last_day = timing_schedule[-1] if timing_schedule else 0
            timing_schedule.append(last_day + 7)
        
        # Get themes for this sequence type
        themes = SEQUENCE_THEMES.get(sequence_type, SEQUENCE_THEMES[SequenceType.NURTURE])
        
        # Generate sequence ID
        sequence_id = str(uuid.uuid4())
        
        # Generate each email in the sequence
        emails = []
        for i, day in enumerate(timing_schedule):
            theme_data = themes[i % len(themes)]
            
            email = await self._generate_sequence_email(
                sequence_type=sequence_type,
                position=i + 1,
                total_emails=num_emails,
                day=day,
                theme=theme_data["theme"],
                goal=theme_data["goal"],
                brand_data=brand_data,
                brand_voice=brand_voice,
                target_audience=target_audience,
            )
            emails.append(email)
        
        # Create result
        result = EmailSequenceResult(
            sequence_id=sequence_id,
            sequence_type=sequence_type.value,
            emails=emails,
            timing_schedule=timing_schedule,
            total_emails=num_emails,
            brand_data=brand_data,
        )
        
        # Save to file if requested
        if save_to_file:
            file_path = await self._save_sequence(result, campaign_id)
            result.file_path = file_path
        
        return result
    
    async def _generate_sequence_email(
        self,
        sequence_type: SequenceType,
        position: int,
        total_emails: int,
        day: int,
        theme: str,
        goal: str,
        brand_data: Optional[Dict[str, Any]],
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str],
    ) -> SequenceEmail:
        """Generate a single email in the sequence."""
        
        # Map sequence type to email type
        email_type_map = {
            SequenceType.WELCOME: "welcome",
            SequenceType.NURTURE: "nurture",
            SequenceType.ONBOARDING: "welcome",
            SequenceType.RE_ENGAGEMENT: "promotional",
        }
        email_type = email_type_map.get(sequence_type, "nurture")
        
        # Generate content with AI
        content = await self._generate_email_content(
            sequence_type=sequence_type,
            position=position,
            total_emails=total_emails,
            day=day,
            theme=theme,
            goal=goal,
            brand_voice=brand_voice,
            target_audience=target_audience,
        )
        
        # Generate the email using the template system
        email = generate_email(
            template_name=email_type,
            brand_data=brand_data or {"primary_color": "#3b82f6", "font_family": "Arial"},
            content_data=content,
            subject=content.get("subject", f"{theme} - Email {position}")
        )
        
        return SequenceEmail(
            day=day,
            position=position,
            subject=content.get("subject", f"{theme} - Email {position}"),
            html_content=email.html,
            text_content=email.plaintext,
            preview_text=content.get("preheader", ""),
            theme=theme,
            goal=goal,
        )
    
    async def _generate_email_content(
        self,
        sequence_type: SequenceType,
        position: int,
        total_emails: int,
        day: int,
        theme: str,
        goal: str,
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str],
    ) -> Dict[str, str]:
        """Generate email content using AI."""
        
        voice_guidelines = ""
        if brand_voice:
            voice_tone = ", ".join(brand_voice.get("tone", ["professional"]))
            personality = brand_voice.get("personality", "")
            vocabulary = ", ".join(brand_voice.get("vocabulary", []))
            voice_guidelines = f"""
Brand Voice:
- Tone: {voice_tone}
- Personality: {personality}
- Preferred words: {vocabulary}
"""
        
        prompt = f"""
Create email content for a {sequence_type.value} sequence.

Email Details:
- Position: Email {position} of {total_emails}
- Send Day: Day {day}
- Theme: {theme}
- Goal: {goal}
- Target Audience: {target_audience or "general subscribers"}

{voice_guidelines}

Generate content for these fields:
- subject: Compelling subject line (under 50 characters)
- preheader: Preview text (40-90 characters)
- headline: Main headline
- subheadline: Supporting text
- body_content: Main email body (2-3 paragraphs)
- cta_text: Call-to-action button text
- cta_url: Suggested URL path
- closing_message: Sign-off message
- footer_text: Brief footer

Requirements:
- Content should be unique and not repeat previous emails
- Build on the sequence narrative
- Match the theme and goal
- Be engaging and action-oriented

Return as JSON with these exact keys.
"""
        
        if not self.openrouter:
            return self._get_fallback_content(sequence_type, position, day, theme, goal)
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an expert email marketing copywriter who creates engaging email sequences.",
                temperature=0.7,
                json_mode=True
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Email content generation failed: {e}")
            return self._get_fallback_content(sequence_type, position, day, theme, goal)
    
    def _get_fallback_content(
        self,
        sequence_type: SequenceType,
        position: int,
        day: int,
        theme: str,
        goal: str,
    ) -> Dict[str, str]:
        """Get fallback content when AI fails."""
        
        fallback_subjects = {
            SequenceType.WELCOME: [
                "Welcome to the family! 🎉",
                "Let's get you started",
                "Discover what makes us special",
                "See what others are saying",
                "You're part of something great",
            ],
            SequenceType.NURTURE: [
                "Something valuable for you",
                "Industry insights you'll love",
                "Solving your biggest challenge",
                "Real results, real stories",
                "Tips from the experts",
            ],
            SequenceType.ONBOARDING: [
                "Welcome! Let's set you up",
                "Your first quick win awaits",
                "Unlock powerful features",
                "Pro tips for power users",
                "You're making great progress!",
            ],
            SequenceType.RE_ENGAGEMENT: [
                "We've missed you!",
                "Look what's new",
                "A special offer just for you",
                "Success stories to inspire you",
                "One last thing...",
            ],
        }
        
        subjects = fallback_subjects.get(sequence_type, fallback_subjects[SequenceType.NURTURE])
        subject = subjects[(position - 1) % len(subjects)]
        
        return {
            "subject": subject,
            "preheader": f"{theme} - Day {day} of your journey",
            "headline": theme,
            "subheadline": goal,
            "body_content": f"""
<p>This is email {position} in your {sequence_type.value.replace('_', ' ')} sequence.</p>
<p>Today's focus: {theme}</p>
<p>Our goal is to {goal.lower()}. We're excited to share this with you and help you succeed.</p>
""",
            "cta_text": "Learn More",
            "cta_url": f"/{sequence_type.value}/email-{position}",
            "closing_message": "Looking forward to connecting with you!",
            "footer_text": f"Email {position} of {position} in your {sequence_type.value.replace('_', ' ')} series.",
            "welcome_message": f"Welcome to day {day} of your journey!",
            "opening_text": f"We're excited to share {theme.lower()} with you today.",
            "tip_title": "Today's Tip",
            "tip_content": f"Focus on {goal.lower()} to get the most value.",
            "resource_title": "Helpful Resource",
            "resource_content": "Check out our guides and tutorials for more information.",
        }
    
    async def _save_sequence(
        self,
        result: EmailSequenceResult,
        campaign_id: Optional[str] = None,
    ) -> str:
        """Save the sequence to files."""
        
        # Create output directory
        base_dir = os.path.join(self.settings.output_dir, "emails", "sequences")
        os.makedirs(base_dir, exist_ok=True)
        
        # Create sequence directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sequence_dir = os.path.join(
            base_dir,
            f"{result.sequence_type}_{timestamp}_{result.sequence_id[:8]}"
        )
        os.makedirs(sequence_dir, exist_ok=True)
        
        # Save sequence metadata
        metadata = {
            "sequence_id": result.sequence_id,
            "sequence_type": result.sequence_type,
            "campaign_id": campaign_id,
            "timing_schedule": result.timing_schedule,
            "total_emails": result.total_emails,
            "brand_data": result.brand_data,
            "created_at": datetime.now().isoformat(),
            "emails": [
                {
                    "day": e.day,
                    "position": e.position,
                    "subject": e.subject,
                    "theme": e.theme,
                    "goal": e.goal,
                    "preview_text": e.preview_text,
                }
                for e in result.emails
            ]
        }
        
        metadata_path = os.path.join(sequence_dir, "sequence.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Save each email
        for email in result.emails:
            email_dir = os.path.join(sequence_dir, f"email_{email.position:02d}_day_{email.day:02d}")
            os.makedirs(email_dir, exist_ok=True)
            
            # Save HTML
            html_path = os.path.join(email_dir, "email.html")
            with open(html_path, "w") as f:
                f.write(email.html_content)
            
            # Save plain text
            text_path = os.path.join(email_dir, "email.txt")
            with open(text_path, "w") as f:
                f.write(email.text_content)
            
            # Save email metadata
            email_meta = {
                "day": email.day,
                "position": email.position,
                "subject": email.subject,
                "preview_text": email.preview_text,
                "theme": email.theme,
                "goal": email.goal,
            }
            email_meta_path = os.path.join(email_dir, "metadata.json")
            with open(email_meta_path, "w") as f:
                json.dump(email_meta, f, indent=2)
        
        logger.info(f"Saved email sequence to {sequence_dir}")
        return sequence_dir
    
    def get_sequence_types(self) -> List[Dict[str, Any]]:
        """Get available sequence types with descriptions."""
        return [
            {
                "type": SequenceType.WELCOME.value,
                "name": "Welcome Series",
                "description": "Introduce new subscribers to your brand",
                "default_emails": 5,
                "default_schedule": SEQUENCE_SCHEDULES[SequenceType.WELCOME],
            },
            {
                "type": SequenceType.NURTURE.value,
                "name": "Nurture Campaign",
                "description": "Build relationships with educational content",
                "default_emails": 7,
                "default_schedule": SEQUENCE_SCHEDULES[SequenceType.NURTURE],
            },
            {
                "type": SequenceType.ONBOARDING.value,
                "name": "Onboarding Sequence",
                "description": "Guide new users through product setup",
                "default_emails": 6,
                "default_schedule": SEQUENCE_SCHEDULES[SequenceType.ONBOARDING],
            },
            {
                "type": SequenceType.RE_ENGAGEMENT.value,
                "name": "Re-engagement Campaign",
                "description": "Win back inactive subscribers",
                "default_emails": 5,
                "default_schedule": SEQUENCE_SCHEDULES[SequenceType.RE_ENGAGEMENT],
            },
        ]


# Convenience function
async def generate_email_sequence(
    sequence_type: str,
    num_emails: int = 5,
    **kwargs
) -> EmailSequenceResult:
    """Generate an email sequence."""
    generator = EmailSequenceGenerator()
    seq_type = SequenceType(sequence_type)
    return await generator.generate_sequence(
        sequence_type=seq_type,
        num_emails=num_emails,
        **kwargs
    )
