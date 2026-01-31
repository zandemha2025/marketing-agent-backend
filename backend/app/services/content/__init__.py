"""
Content generation services.

Provides:
- Email generation with MJML templates
- Press release generation
- Article generation
- Landing page generation
- Interview processing
"""
from .email_generator import EmailGenerator, EmailContent, EmailType, generate_email_content
from .mjml_templates import MJMLTemplateSystem, GeneratedEmail, generate_email
from .press_release import PressReleaseGenerator
from .article_generator import ArticleGenerator
from .landing_page_generator import LandingPageGenerator
from .interview_processor import InterviewProcessor

__all__ = [
    "EmailGenerator",
    "EmailContent",
    "EmailType",
    "generate_email_content",
    "MJMLTemplateSystem",
    "GeneratedEmail",
    "generate_email",
    "PressReleaseGenerator",
    "ArticleGenerator",
    "LandingPageGenerator",
    "InterviewProcessor",
]
