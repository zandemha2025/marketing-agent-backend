"""
Tests for Email Generator Service

Tests email generation, MJML templates, and output formats.
"""
import pytest
import asyncio
from app.services.content.email_generator import (
    EmailGenerator,
    EmailType,
    EmailContent,
    SubjectLineVariant,
    NewsletterSection,
    generate_email_content
)
from app.services.content.mjml_templates import (
    MJMLTemplateSystem,
    GeneratedEmail,
    EmailTemplate,
    generate_email
)


class TestEmailType:
    """Test EmailType enum."""
    
    def test_email_types_exist(self):
        """Verify all required email types exist."""
        assert EmailType.PROMOTIONAL == "promotional"
        assert EmailType.NEWSLETTER == "newsletter"
        assert EmailType.WELCOME == "welcome"
        assert EmailType.ANNOUNCEMENT == "announcement"
        assert EmailType.NURTURE == "nurture"
        assert EmailType.TRANSACTIONAL == "transactional"
    
    def test_email_type_values(self):
        """Test that email types are strings."""
        for email_type in EmailType:
            assert isinstance(email_type.value, str)


class TestEmailContent:
    """Test EmailContent dataclass."""
    
    def test_email_content_creation(self):
        """Test creating EmailContent."""
        content = EmailContent(
            subject="Test Subject",
            preheader="Test preheader text",
            headline="Test Headline",
            body_html="<p>Test body</p>",
            body_text="Test body",
            cta_text="Click Here",
            cta_url="/test"
        )
        
        assert content.subject == "Test Subject"
        assert content.preheader == "Test preheader text"
        assert content.headline == "Test Headline"
        assert content.cta_text == "Click Here"
    
    def test_email_content_to_dict(self):
        """Test EmailContent to_dict method."""
        content = EmailContent(
            subject="Test",
            preheader="Preview",
            headline="Headline",
            body_html="<p>Body</p>",
            body_text="Body",
            cta_text="CTA",
            cta_url="/url"
        )
        
        data = content.to_dict()
        assert data["subject"] == "Test"
        assert data["preheader"] == "Preview"
        assert "metadata" in data
    
    def test_email_content_to_mjml(self):
        """Test EmailContent to_mjml method."""
        content = EmailContent(
            subject="Test",
            preheader="Preview",
            headline="Welcome!",
            body_html="<p>Welcome to our service.</p>",
            body_text="Welcome to our service.",
            cta_text="Get Started",
            cta_url="/start"
        )
        
        mjml = content.to_mjml("welcome")
        assert "<mjml>" in mjml
        assert "Welcome!" in mjml
    
    def test_email_content_to_html(self):
        """Test EmailContent to_html method."""
        content = EmailContent(
            subject="Test",
            preheader="Preview",
            headline="Welcome!",
            body_html="<p>Welcome to our service.</p>",
            body_text="Welcome to our service.",
            cta_text="Get Started",
            cta_url="/start"
        )
        
        html = content.to_html("welcome")
        assert "<!DOCTYPE html>" in html
        assert "Welcome!" in html


class TestMJMLTemplateSystem:
    """Test MJML template system."""
    
    def test_template_system_init(self):
        """Test MJMLTemplateSystem initialization."""
        system = MJMLTemplateSystem()
        assert system.templates is not None
        assert len(system.templates) >= 6  # All 6 email types
    
    def test_all_templates_exist(self):
        """Test that all required templates exist."""
        system = MJMLTemplateSystem()
        required_templates = ["welcome", "newsletter", "promotional", "announcement", "nurture", "transactional"]
        
        for template_name in required_templates:
            assert template_name in system.templates, f"Missing template: {template_name}"
    
    def test_template_structure(self):
        """Test that templates have correct structure."""
        system = MJMLTemplateSystem()
        
        for name, template in system.templates.items():
            assert isinstance(template, EmailTemplate)
            assert template.name
            assert template.category
            assert template.description
            assert template.mjml_template
    
    def test_apply_brand(self):
        """Test applying brand data to template."""
        system = MJMLTemplateSystem()
        
        brand_data = {
            "primary_color": "#ff5500",
            "font_family": "Helvetica"
        }
        
        content_data = {
            "headline": "Test Headline",
            "subheadline": "Test Subheadline",
            "welcome_message": "Welcome!",
            "body_content": "Body content here.",
            "cta_text": "Click Me",
            "cta_url": "/click",
            "closing_message": "Thanks!",
            "footer_text": "Footer"
        }
        
        mjml = system.apply_brand("welcome", brand_data, content_data)
        
        assert "<mjml>" in mjml
        assert "#ff5500" in mjml
        assert "Helvetica" in mjml
        assert "Test Headline" in mjml
    
    def test_mjml_to_html(self):
        """Test MJML to HTML conversion."""
        system = MJMLTemplateSystem()
        
        mjml = '''<mjml>
  <mj-body background-color="#f4f4f4">
    <mj-section background-color="#3b82f6" padding="20px">
      <mj-column>
        <mj-text align="center" color="white" font-size="24px">Hello World</mj-text>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>'''
        
        html = system.mjml_to_html(mjml)
        
        assert "<!DOCTYPE html>" in html
        assert "Hello World" in html
        assert "#3b82f6" in html or "background-color" in html
    
    def test_html_to_plaintext(self):
        """Test HTML to plaintext conversion."""
        system = MJMLTemplateSystem()
        
        html = "<p>Hello <strong>World</strong>!</p><p>This is a test.</p>"
        plaintext = system.html_to_plaintext(html)
        
        assert "Hello" in plaintext
        assert "World" in plaintext
        assert "<" not in plaintext
    
    def test_get_available_templates(self):
        """Test getting available templates list."""
        system = MJMLTemplateSystem()
        templates = system.get_available_templates()
        
        assert isinstance(templates, list)
        assert len(templates) >= 6
        
        for template in templates:
            assert "id" in template
            assert "name" in template
            assert "category" in template
            assert "description" in template


class TestGenerateEmail:
    """Test generate_email convenience function."""
    
    def test_generate_email_welcome(self):
        """Test generating a welcome email."""
        brand_data = {"primary_color": "#3b82f6", "font_family": "Arial"}
        content_data = {
            "headline": "Welcome!",
            "subheadline": "We're glad you're here",
            "welcome_message": "Thanks for joining.",
            "body_content": "Here's what to expect.",
            "cta_text": "Get Started",
            "cta_url": "/start",
            "closing_message": "See you soon!",
            "footer_text": "Footer text"
        }
        
        email = generate_email("welcome", brand_data, content_data, "Welcome to Our Service!")
        
        assert isinstance(email, GeneratedEmail)
        assert email.subject == "Welcome to Our Service!"
        assert "<mjml>" in email.mjml
        assert "<!DOCTYPE html>" in email.html
        assert len(email.plaintext) > 0
    
    def test_generate_email_promotional(self):
        """Test generating a promotional email."""
        brand_data = {"primary_color": "#e11d48", "font_family": "Georgia"}
        content_data = {
            "headline": "50% Off Sale!",
            "subheadline": "Limited time only",
            "offer_text": "Don't miss this deal.",
            "discount_code": "SAVE50",
            "expiry_text": "Ends Sunday",
            "cta_text": "Shop Now",
            "cta_url": "/shop",
            "terms_text": "Terms apply",
            "footer_text": "Footer"
        }
        
        email = generate_email("promotional", brand_data, content_data, "50% Off Everything!")
        
        assert email.subject == "50% Off Everything!"
        assert "SAVE50" in email.mjml
        assert "Shop Now" in email.html
    
    def test_generate_email_transactional(self):
        """Test generating a transactional email."""
        brand_data = {"primary_color": "#059669", "font_family": "Arial"}
        content_data = {
            "headline": "Order Confirmed",
            "transaction_type": "Order Confirmation",
            "transaction_id": "#ORD-12345",
            "summary_text": "Your order has been placed.",
            "details_content": "Order details here.",
            "next_steps": "We'll email you when it ships.",
            "support_text": "Need help? Contact us.",
            "cta_text": "Track Order",
            "cta_url": "/orders/12345",
            "footer_text": "Automated message"
        }
        
        email = generate_email("transactional", brand_data, content_data, "Order Confirmed #ORD-12345")
        
        assert "#ORD-12345" in email.mjml
        assert "Order Confirmation" in email.html


class TestEmailGenerator:
    """Test EmailGenerator class."""
    
    def test_email_generator_init(self):
        """Test EmailGenerator initialization."""
        generator = EmailGenerator()
        assert generator.template_system is not None
    
    def test_get_available_templates(self):
        """Test getting available templates."""
        generator = EmailGenerator()
        templates = generator.get_available_templates()
        
        assert isinstance(templates, list)
        assert len(templates) >= 6
    
    @pytest.mark.asyncio
    async def test_generate_email(self):
        """Test generating an email."""
        generator = EmailGenerator()
        
        email = await generator.generate(
            email_type="welcome",
            topic="New Product Launch",
            key_points=["Feature 1", "Feature 2", "Feature 3"]
        )
        
        assert isinstance(email, GeneratedEmail)
        assert email.subject
        assert email.mjml
        assert email.html
        assert email.plaintext
    
    @pytest.mark.asyncio
    async def test_generate_subject_variants(self):
        """Test generating subject line variants."""
        generator = EmailGenerator()
        
        variants = await generator.generate_subject_variants(
            topic="Summer Sale",
            count=3
        )
        
        assert isinstance(variants, list)
        assert len(variants) >= 1
        
        for variant in variants:
            assert isinstance(variant, SubjectLineVariant)
            assert variant.text
    
    @pytest.mark.asyncio
    async def test_generate_newsletter(self):
        """Test generating a multi-section newsletter."""
        generator = EmailGenerator()
        
        sections = [
            {
                "title": "Top Story",
                "content": "This is the main story of the newsletter.",
                "cta_text": "Read More",
                "cta_url": "/story/1"
            },
            {
                "title": "Product Update",
                "content": "We've released new features.",
                "image_url": "https://example.com/image.jpg",
                "cta_text": "Learn More",
                "cta_url": "/updates"
            },
            {
                "title": "Tips & Tricks",
                "content": "Here are some helpful tips."
            }
        ]
        
        email = await generator.generate_newsletter(
            sections=sections,
            newsletter_title="Monthly Digest"
        )
        
        assert isinstance(email, GeneratedEmail)
        assert "Top Story" in email.mjml
        assert "Product Update" in email.mjml
        assert email.metadata.get("section_count") == 3
    
    @pytest.mark.asyncio
    async def test_generate_email_content(self):
        """Test generating structured email content."""
        generator = EmailGenerator()
        
        content = await generator.generate_email_content(
            email_type=EmailType.PROMOTIONAL,
            topic="Black Friday Sale",
            brand_context={
                "voice": {"tone": ["exciting", "urgent"]},
                "primary_color": "#000000"
            }
        )
        
        assert isinstance(content, EmailContent)
        assert content.subject
        assert content.preheader
        assert content.headline
        assert content.cta_text
    
    def test_fallback_content(self):
        """Test fallback content generation."""
        generator = EmailGenerator()
        
        # Test all email types have fallback content
        for email_type in ["welcome", "newsletter", "promotional", "announcement", "nurture", "transactional"]:
            fallback = generator._get_fallback_content(email_type, "Test Topic")
            assert isinstance(fallback, dict)
            assert "headline" in fallback or "newsletter_title" in fallback


class TestSubjectLineVariant:
    """Test SubjectLineVariant dataclass."""
    
    def test_subject_line_variant_creation(self):
        """Test creating SubjectLineVariant."""
        variant = SubjectLineVariant(
            text="🔥 Hot Deal Inside!",
            predicted_open_rate=32.5,
            emoji=True,
            urgency_level="high"
        )
        
        assert variant.text == "🔥 Hot Deal Inside!"
        assert variant.predicted_open_rate == 32.5
        assert variant.emoji is True
        assert variant.urgency_level == "high"
    
    def test_subject_line_variant_defaults(self):
        """Test SubjectLineVariant default values."""
        variant = SubjectLineVariant(text="Simple Subject")
        
        assert variant.predicted_open_rate == 0.0
        assert variant.emoji is False
        assert variant.urgency_level == "medium"


class TestGeneratedEmail:
    """Test GeneratedEmail dataclass."""
    
    def test_generated_email_creation(self):
        """Test creating GeneratedEmail."""
        email = GeneratedEmail(
            subject="Test Subject",
            mjml="<mjml>...</mjml>",
            html="<!DOCTYPE html>...",
            plaintext="Plain text content"
        )
        
        assert email.subject == "Test Subject"
        assert email.mjml.startswith("<mjml>")
        assert email.html.startswith("<!DOCTYPE")
        assert email.plaintext == "Plain text content"
    
    def test_generated_email_to_dict(self):
        """Test GeneratedEmail to_dict method."""
        email = GeneratedEmail(
            subject="Test",
            mjml="<mjml></mjml>",
            html="<html></html>",
            plaintext="text",
            metadata={"key": "value"}
        )
        
        data = email.to_dict()
        
        assert data["subject"] == "Test"
        assert data["mjml"] == "<mjml></mjml>"
        assert data["html"] == "<html></html>"
        assert data["plaintext"] == "text"
        assert data["metadata"]["key"] == "value"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
