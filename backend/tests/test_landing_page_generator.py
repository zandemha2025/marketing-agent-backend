"""
Tests for Landing Page Generator and Next.js Scaffolder

Tests cover:
- LandingPageType enum
- LandingPageSection dataclass
- LandingPageContent with to_html() and to_nextjs_components()
- LandingPageGenerator for all page types
- NextJSScaffolder project generation
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.content.landing_page_generator import (
    LandingPageType,
    LandingPageSection,
    LandingPageContent,
    LandingPageGenerator,
    generate_landing_page
)
from app.services.content.nextjs_scaffolder import (
    NextJSScaffolder,
    NextJSProject,
    scaffold_nextjs_project
)


class TestLandingPageType:
    """Test LandingPageType enum."""
    
    def test_all_page_types_exist(self):
        """Verify all required page types are defined."""
        assert LandingPageType.PRODUCT == "product"
        assert LandingPageType.LEAD_CAPTURE == "lead_capture"
        assert LandingPageType.EVENT == "event"
        assert LandingPageType.WEBINAR == "webinar"
        assert LandingPageType.COMING_SOON == "coming_soon"
        assert LandingPageType.COMPARISON == "comparison"
    
    def test_page_type_is_string_enum(self):
        """Verify page types can be used as strings."""
        # String enum value access
        assert LandingPageType.PRODUCT.value == "product"
        # Can compare directly with string
        assert LandingPageType.PRODUCT == "product"


class TestLandingPageSection:
    """Test LandingPageSection dataclass."""
    
    def test_section_creation(self):
        """Test creating a section with all fields."""
        section = LandingPageSection(
            section_type="hero",
            headline="Transform Your Business",
            subheadline="The best solution for your needs",
            content={"cta_subtext": "No credit card required"},
            cta_text="Get Started",
            cta_url="https://example.com/signup",
            image_prompt="Professional hero image"
        )
        
        assert section.section_type == "hero"
        assert section.headline == "Transform Your Business"
        assert section.subheadline == "The best solution for your needs"
        assert section.cta_text == "Get Started"
        assert section.cta_url == "https://example.com/signup"
        assert section.image_prompt == "Professional hero image"
    
    def test_section_to_dict(self):
        """Test section serialization."""
        section = LandingPageSection(
            section_type="features",
            headline="Why Choose Us",
            content={"features": [{"title": "Fast", "description": "Lightning fast"}]}
        )
        
        data = section.to_dict()
        
        assert data["section_type"] == "features"
        assert data["headline"] == "Why Choose Us"
        assert "features" in data["content"]
    
    def test_section_optional_fields(self):
        """Test section with minimal fields."""
        section = LandingPageSection(
            section_type="cta",
            headline="Ready to Start?"
        )
        
        assert section.subheadline is None
        assert section.cta_text is None
        assert section.cta_url is None
        assert section.image_prompt is None


class TestLandingPageContent:
    """Test LandingPageContent dataclass."""
    
    def test_content_creation(self):
        """Test creating landing page content."""
        sections = [
            LandingPageSection(section_type="hero", headline="Welcome"),
            LandingPageSection(section_type="features", headline="Features"),
        ]
        
        content = LandingPageContent(
            page_type=LandingPageType.PRODUCT,
            title="Product Landing Page",
            meta_description="Best product for your needs",
            og_title="Product - Transform Your Business",
            og_description="Join thousands of happy customers",
            sections=sections,
            keywords=["product", "solution", "business"]
        )
        
        assert content.page_type == LandingPageType.PRODUCT
        assert content.title == "Product Landing Page"
        assert len(content.sections) == 2
        assert "product" in content.keywords
    
    def test_content_to_dict(self):
        """Test content serialization."""
        content = LandingPageContent(
            page_type=LandingPageType.LEAD_CAPTURE,
            title="Get Our Free Guide",
            meta_description="Download our comprehensive guide",
            og_title="Free Guide Download",
            og_description="Get instant access",
            sections=[LandingPageSection(section_type="hero", headline="Free Guide")]
        )
        
        data = content.to_dict()
        
        assert data["page_type"] == "lead_capture"
        assert data["title"] == "Get Our Free Guide"
        assert data["og_title"] == "Free Guide Download"
        assert len(data["sections"]) == 1
    
    def test_to_html_generates_valid_html(self):
        """Test HTML generation."""
        sections = [
            LandingPageSection(
                section_type="hero",
                headline="Welcome to Our Product",
                subheadline="The best solution",
                cta_text="Get Started"
            ),
            LandingPageSection(
                section_type="features",
                headline="Features",
                content={"features": [
                    {"title": "Fast", "description": "Lightning fast", "icon": "⚡"}
                ]}
            ),
            LandingPageSection(
                section_type="cta",
                headline="Ready?",
                cta_text="Sign Up Now"
            )
        ]
        
        content = LandingPageContent(
            page_type=LandingPageType.PRODUCT,
            title="Product Page",
            meta_description="Best product",
            og_title="Product",
            og_description="Best product",
            sections=sections,
            keywords=["product"]
        )
        
        html = content.to_html({"primary_color": "#3b82f6"})
        
        # Verify HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "<head>" in html
        assert "<body" in html
        
        # Verify SEO tags
        assert 'meta name="description"' in html
        assert 'property="og:title"' in html
        assert 'property="og:description"' in html
        
        # Verify content
        assert "Welcome to Our Product" in html
        assert "Features" in html
        assert "Get Started" in html
    
    def test_to_html_with_all_section_types(self):
        """Test HTML generation with all section types."""
        sections = [
            LandingPageSection(section_type="hero", headline="Hero"),
            LandingPageSection(section_type="features", headline="Features", content={"features": []}),
            LandingPageSection(section_type="benefits", headline="Benefits", content={"benefits": []}),
            LandingPageSection(section_type="testimonials", headline="Testimonials", content={"testimonials": []}),
            LandingPageSection(section_type="pricing", headline="Pricing", content={"tiers": []}),
            LandingPageSection(section_type="faq", headline="FAQ", content={"questions": []}),
            LandingPageSection(section_type="how_it_works", headline="How It Works", content={"steps": []}),
            LandingPageSection(section_type="social_proof", headline="Trusted By", content={"logos": [], "stats": []}),
            LandingPageSection(section_type="cta", headline="CTA"),
        ]
        
        content = LandingPageContent(
            page_type=LandingPageType.PRODUCT,
            title="Full Page",
            meta_description="Full page",
            og_title="Full",
            og_description="Full",
            sections=sections
        )
        
        html = content.to_html()
        
        # All sections should be rendered
        assert "Hero" in html
        assert "Features" in html
        assert "Benefits" in html
        assert "Testimonials" in html
        assert "Pricing" in html
        assert "FAQ" in html
        assert "How It Works" in html
        assert "Trusted By" in html
        assert "CTA" in html
    
    def test_to_nextjs_components(self):
        """Test Next.js component generation."""
        sections = [
            LandingPageSection(section_type="hero", headline="Hero"),
            LandingPageSection(section_type="features", headline="Features", content={"features": []}),
        ]
        
        content = LandingPageContent(
            page_type=LandingPageType.PRODUCT,
            title="Product",
            meta_description="Product",
            og_title="Product",
            og_description="Product",
            sections=sections
        )
        
        components = content.to_nextjs_components()
        
        # Should have section components
        assert "components/sections/HeroSection.tsx" in components
        assert "components/sections/FeaturesSection.tsx" in components
        
        # Should have main landing page component
        assert "components/LandingPage.tsx" in components


class TestLandingPageGenerator:
    """Test LandingPageGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        with patch('app.services.content.landing_page_generator.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(openrouter_api_key=None)
            return LandingPageGenerator()
    
    @pytest.mark.asyncio
    async def test_generate_product_page(self, generator):
        """Test generating a product landing page."""
        result = await generator.generate(
            page_type=LandingPageType.PRODUCT,
            product_name="TestProduct",
            product_description="A great product for testing",
            target_audience="developers",
            key_benefits=["Fast", "Reliable", "Easy to use"]
        )
        
        assert result.page_type == LandingPageType.PRODUCT
        assert result.title is not None
        assert len(result.sections) > 0
        
        # Product pages should have hero and features
        section_types = [s.section_type for s in result.sections]
        assert "hero" in section_types
        assert "features" in section_types
    
    @pytest.mark.asyncio
    async def test_generate_lead_capture_page(self, generator):
        """Test generating a lead capture page."""
        result = await generator.generate(
            page_type=LandingPageType.LEAD_CAPTURE,
            product_name="Free Guide",
            product_description="Download our comprehensive guide",
            target_audience="marketers"
        )
        
        assert result.page_type == LandingPageType.LEAD_CAPTURE
        
        # Lead capture should have email capture section
        section_types = [s.section_type for s in result.sections]
        assert "email_capture" in section_types
    
    @pytest.mark.asyncio
    async def test_generate_event_page(self, generator):
        """Test generating an event page."""
        result = await generator.generate(
            page_type=LandingPageType.EVENT,
            product_name="Tech Conference 2024",
            product_description="Annual technology conference",
            target_audience="tech professionals"
        )
        
        assert result.page_type == LandingPageType.EVENT
        
        # Event pages should have countdown
        section_types = [s.section_type for s in result.sections]
        assert "countdown" in section_types
    
    @pytest.mark.asyncio
    async def test_generate_webinar_page(self, generator):
        """Test generating a webinar page."""
        result = await generator.generate(
            page_type=LandingPageType.WEBINAR,
            product_name="Marketing Masterclass",
            product_description="Learn advanced marketing strategies",
            target_audience="marketing managers"
        )
        
        assert result.page_type == LandingPageType.WEBINAR
        
        # Webinar pages should have countdown and email capture
        section_types = [s.section_type for s in result.sections]
        assert "countdown" in section_types
        assert "email_capture" in section_types
    
    @pytest.mark.asyncio
    async def test_generate_coming_soon_page(self, generator):
        """Test generating a coming soon page."""
        result = await generator.generate(
            page_type=LandingPageType.COMING_SOON,
            product_name="New Product",
            product_description="Something amazing is coming",
            target_audience="early adopters"
        )
        
        assert result.page_type == LandingPageType.COMING_SOON
        
        # Coming soon should have email capture
        section_types = [s.section_type for s in result.sections]
        assert "email_capture" in section_types
    
    @pytest.mark.asyncio
    async def test_generate_comparison_page(self, generator):
        """Test generating a comparison page."""
        result = await generator.generate(
            page_type=LandingPageType.COMPARISON,
            product_name="Our Solution",
            product_description="Better than the competition",
            target_audience="decision makers"
        )
        
        assert result.page_type == LandingPageType.COMPARISON
        
        # Comparison pages should have comparison section
        section_types = [s.section_type for s in result.sections]
        assert "comparison" in section_types
    
    @pytest.mark.asyncio
    async def test_generate_with_custom_sections(self, generator):
        """Test generating with custom section list."""
        result = await generator.generate(
            page_type=LandingPageType.PRODUCT,
            product_name="Custom Product",
            product_description="Custom sections",
            target_audience="everyone",
            sections_requested=["hero", "pricing", "faq"]
        )
        
        section_types = [s.section_type for s in result.sections]
        assert section_types == ["hero", "pricing", "faq"]
    
    @pytest.mark.asyncio
    async def test_generate_with_brand_context(self, generator):
        """Test generating with brand context."""
        result = await generator.generate(
            page_type=LandingPageType.PRODUCT,
            product_name="Branded Product",
            product_description="With brand voice",
            target_audience="customers",
            brand_context={
                "colors": {"primary_color": "#ff0000"},
                "voice": {"tone": ["friendly", "professional"]}
            }
        )
        
        assert result is not None
        assert len(result.sections) > 0
    
    @pytest.mark.asyncio
    async def test_generate_section(self, generator):
        """Test generating individual sections."""
        section = await generator.generate_section(
            section_type="hero",
            context={
                "product_name": "Test Product",
                "product_description": "A test product",
                "target_audience": "testers",
                "key_benefits": ["Fast", "Reliable"]
            }
        )
        
        assert section.section_type == "hero"
        assert section.headline is not None
    
    @pytest.mark.asyncio
    async def test_seo_metadata_generation(self, generator):
        """Test SEO metadata is generated."""
        result = await generator.generate(
            page_type=LandingPageType.PRODUCT,
            product_name="SEO Test",
            product_description="Testing SEO generation",
            target_audience="SEO experts",
            key_benefits=["Better rankings", "More traffic"]
        )
        
        assert result.title is not None
        assert result.meta_description is not None
        assert result.og_title is not None
        assert result.og_description is not None
        assert len(result.keywords) > 0


class TestNextJSScaffolder:
    """Test NextJSScaffolder class."""
    
    @pytest.fixture
    def scaffolder(self):
        """Create scaffolder instance."""
        return NextJSScaffolder()
    
    @pytest.fixture
    def sample_landing_page(self):
        """Create sample landing page content."""
        return LandingPageContent(
            page_type=LandingPageType.PRODUCT,
            title="Test Product",
            meta_description="Test description",
            og_title="Test OG Title",
            og_description="Test OG Description",
            sections=[
                LandingPageSection(section_type="hero", headline="Welcome"),
                LandingPageSection(section_type="features", headline="Features", content={"features": []}),
                LandingPageSection(section_type="cta", headline="Get Started"),
            ],
            keywords=["test", "product"]
        )
    
    def test_scaffold_project(self, scaffolder, sample_landing_page):
        """Test scaffolding a complete project."""
        files = scaffolder.scaffold_project(
            project_name="test-project",
            landing_page=sample_landing_page,
            brand_context={"colors": {"primary_color": "#3b82f6"}}
        )
        
        # Core config files
        assert "package.json" in files
        assert "tsconfig.json" in files
        assert "tailwind.config.ts" in files
        assert "next.config.js" in files
        assert "postcss.config.js" in files
        
        # Lib utilities
        assert "lib/utils.ts" in files
        
        # App files
        assert "app/layout.tsx" in files
        assert "app/globals.css" in files
        assert "app/page.tsx" in files
        
        # UI components
        assert "components/ui/button.tsx" in files
        assert "components/ui/input.tsx" in files
        assert "components/ui/card.tsx" in files
        
        # Section components
        assert "components/sections/HeroSection.tsx" in files
        assert "components/sections/FeaturesSection.tsx" in files
        assert "components/sections/CtaSection.tsx" in files
        
        # Main component
        assert "components/LandingPage.tsx" in files
        
        # Deployment configs
        assert "vercel.json" in files
        assert "netlify.toml" in files
        
        # Documentation
        assert "README.md" in files
    
    def test_scaffold_legacy_interface(self, scaffolder):
        """Test legacy scaffold() method."""
        landing_page_dict = {
            "page_type": "product",
            "title": "Test",
            "seo_description": "Test desc",
            "sections": [
                {"type": "hero", "title": "Hero", "content": {}}
            ]
        }
        
        result = scaffolder.scaffold(
            project_name="legacy-test",
            landing_page_content=landing_page_dict,
            brand_data={"primary_color": "#ff0000"}
        )
        
        assert isinstance(result, NextJSProject)
        assert result.name == "legacy-test"
        assert len(result.files) > 0
    
    def test_generate_component(self, scaffolder):
        """Test generating individual components."""
        section = LandingPageSection(
            section_type="hero",
            headline="Test Hero",
            subheadline="Test subheadline",
            cta_text="Click Me"
        )
        
        component = scaffolder.generate_component(
            section=section,
            brand_colors={"primary_color": "#3b82f6"}
        )
        
        assert '"use client"' in component
        assert "export default function HeroSection" in component
        assert "Test Hero" in component
    
    def test_generate_tailwind_config(self, scaffolder):
        """Test Tailwind config generation."""
        config = scaffolder.generate_tailwind_config({
            "primary_color": "#ff0000",
            "secondary_color": "#00ff00"
        })
        
        assert "tailwindcss" in config
        assert "#ff0000" in config
        assert "#00ff00" in config
        assert "primary" in config
        assert "secondary" in config
    
    def test_generate_layout(self, scaffolder):
        """Test layout generation."""
        layout = scaffolder.generate_layout({
            "font_family": "Roboto"
        })
        
        assert "Roboto" in layout
        assert "RootLayout" in layout
        assert "next/font/google" in layout
    
    def test_package_json_content(self, scaffolder, sample_landing_page):
        """Test package.json has correct dependencies."""
        files = scaffolder.scaffold_project(
            project_name="dep-test",
            landing_page=sample_landing_page
        )
        
        package_json = files["package.json"]
        
        assert '"next"' in package_json
        assert '"react"' in package_json
        assert '"tailwindcss"' in package_json
        assert '"lucide-react"' in package_json
        assert '"class-variance-authority"' in package_json
    
    def test_all_section_types_generate_components(self, scaffolder):
        """Test all section types generate valid components."""
        section_types = [
            "hero", "features", "benefits", "testimonials", "pricing",
            "faq", "how_it_works", "social_proof", "cta", "countdown",
            "comparison", "email_capture"
        ]
        
        for section_type in section_types:
            section = LandingPageSection(
                section_type=section_type,
                headline=f"Test {section_type}",
                content={}
            )
            
            component = scaffolder.generate_component(
                section=section,
                brand_colors={}
            )
            
            assert '"use client"' in component
            assert "export default function" in component


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.asyncio
    async def test_generate_landing_page_function(self):
        """Test generate_landing_page convenience function."""
        with patch('app.services.content.landing_page_generator.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(openrouter_api_key=None)
            
            result = await generate_landing_page(
                goal="Increase signups",
                target_audience="developers",
                key_benefits=["Fast", "Easy"],
                brand_data={"primary_color": "#3b82f6"},
                product_name="TestApp"
            )
            
            assert isinstance(result, LandingPageContent)
            assert len(result.sections) > 0
    
    def test_scaffold_nextjs_project_function(self):
        """Test scaffold_nextjs_project convenience function."""
        landing_page = LandingPageContent(
            page_type=LandingPageType.PRODUCT,
            title="Test",
            meta_description="Test",
            og_title="Test",
            og_description="Test",
            sections=[LandingPageSection(section_type="hero", headline="Test")]
        )
        
        result = scaffold_nextjs_project(
            project_name="test",
            landing_page_content=landing_page,
            brand_data={}
        )
        
        assert isinstance(result, NextJSProject)
        assert result.name == "test"


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_generator_handles_missing_openrouter(self):
        """Test generator works without OpenRouter API key."""
        with patch('app.services.content.landing_page_generator.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(openrouter_api_key=None)
            
            generator = LandingPageGenerator()
            result = await generator.generate(
                page_type=LandingPageType.PRODUCT,
                product_name="Test",
                product_description="Test",
                target_audience="Test"
            )
            
            # Should use fallback content
            assert result is not None
            assert len(result.sections) > 0
    
    @pytest.mark.asyncio
    async def test_generator_handles_api_error(self):
        """Test generator handles API errors gracefully."""
        with patch('app.services.content.landing_page_generator.get_settings') as mock_settings:
            mock_settings.return_value = MagicMock(openrouter_api_key="test-key")
            
            generator = LandingPageGenerator()
            
            # Mock OpenRouter to raise an error
            generator.openrouter = MagicMock()
            generator.openrouter.complete = AsyncMock(side_effect=Exception("API Error"))
            
            result = await generator.generate(
                page_type=LandingPageType.PRODUCT,
                product_name="Test",
                product_description="Test",
                target_audience="Test"
            )
            
            # Should fall back to default content
            assert result is not None
            assert len(result.sections) > 0
