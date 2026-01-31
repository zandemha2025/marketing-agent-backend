"""
Landing Page Generation Tests

Tests for:
1. Landing page generation with each template
2. HTML validity verification
3. CSS inclusion verification
4. Preview URL functionality
5. Website generation

Results are saved to test_results/landing_pages_test.json
"""
import asyncio
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.content.static_site_builder import (
    StaticSiteBuilder,
    get_static_site_builder,
    LANDING_PAGES_DIR,
    SITES_DIR
)
from app.services.content.landing_page_generator import (
    LandingPageGenerator,
    LandingPageType,
    LandingPageContent
)


class LandingPageTestSuite:
    """Test suite for landing page generation."""
    
    def __init__(self):
        self.builder = get_static_site_builder()
        self.generator = LandingPageGenerator()
        self.results: Dict[str, Any] = {
            "test_run_at": datetime.utcnow().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            }
        }
        self.generated_page_ids: List[str] = []
        self.generated_site_ids: List[str] = []
    
    def add_result(self, test_name: str, passed: bool, details: Dict[str, Any] = None):
        """Add a test result."""
        result = {
            "test_name": test_name,
            "passed": passed,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.results["tests"].append(result)
        self.results["summary"]["total"] += 1
        if passed:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
        
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        if details and not passed:
            print(f"   Details: {json.dumps(details, indent=2)[:200]}")
    
    def validate_html(self, html: str) -> Dict[str, Any]:
        """Validate HTML structure."""
        issues = []
        
        # Check for DOCTYPE
        if not html.strip().startswith("<!DOCTYPE html>"):
            issues.append("Missing DOCTYPE declaration")
        
        # Check for required tags
        required_tags = ["<html", "<head>", "<body", "<title>", "</html>", "</head>", "</body>"]
        for tag in required_tags:
            if tag not in html.lower():
                issues.append(f"Missing required tag: {tag}")
        
        # Check for meta viewport (responsive design)
        if 'name="viewport"' not in html.lower():
            issues.append("Missing viewport meta tag for responsive design")
        
        # Check for meta description
        if 'name="description"' not in html.lower():
            issues.append("Missing meta description")
        
        # Check for proper closing tags
        open_tags = re.findall(r'<(\w+)[^>]*(?<!/)>', html)
        close_tags = re.findall(r'</(\w+)>', html)
        
        # Self-closing tags that don't need closing
        self_closing = {'meta', 'link', 'img', 'br', 'hr', 'input', 'area', 'base', 'col', 'embed', 'param', 'source', 'track', 'wbr'}
        
        open_count = {}
        close_count = {}
        
        for tag in open_tags:
            tag_lower = tag.lower()
            if tag_lower not in self_closing:
                open_count[tag_lower] = open_count.get(tag_lower, 0) + 1
        
        for tag in close_tags:
            tag_lower = tag.lower()
            close_count[tag_lower] = close_count.get(tag_lower, 0) + 1
        
        # Check for mismatched tags (basic check)
        for tag, count in open_count.items():
            if close_count.get(tag, 0) < count:
                issues.append(f"Potentially unclosed tag: <{tag}>")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "html_length": len(html)
        }
    
    def validate_css(self, css: str) -> Dict[str, Any]:
        """Validate CSS content."""
        issues = []
        
        if not css or len(css) < 100:
            issues.append("CSS content is too short or empty")
        
        # Check for common CSS properties
        expected_properties = ["color", "font", "margin", "padding", "background"]
        for prop in expected_properties:
            if prop not in css.lower():
                issues.append(f"Missing common CSS property: {prop}")
        
        # Check for responsive media queries
        if "@media" not in css:
            issues.append("Missing responsive media queries")
        
        # Check for CSS variables (modern CSS)
        if "--" not in css:
            issues.append("Not using CSS custom properties (variables)")
        
        return {
            "valid": len(issues) <= 2,  # Allow some minor issues
            "issues": issues,
            "css_length": len(css)
        }
    
    async def test_landing_page_template(self, template: str) -> bool:
        """Test landing page generation with a specific template."""
        test_name = f"Landing Page Generation - {template}"
        
        try:
            result = await self.builder.generate_landing_page(
                campaign_id=f"test-campaign-{template}",
                template=template,
                headline=f"Amazing {template.replace('_', ' ').title()} Product",
                subheadline="Transform your workflow with our innovative solution",
                cta_text="Get Started Free",
                cta_url="https://example.com/signup",
                features=[
                    "Lightning Fast Performance",
                    "Enterprise Security",
                    "24/7 Support",
                    "Easy Integration"
                ],
                testimonials=[
                    {"name": "John Smith", "quote": "This product changed everything for us!"},
                    {"name": "Sarah Johnson", "quote": "Best investment we've made this year."},
                    {"name": "Mike Chen", "quote": "Highly recommend to any business."}
                ],
                brand_colors={
                    "primary": "#007bff",
                    "secondary": "#6c757d"
                },
                save_to_disk=True
            )
            
            # Track generated page for cleanup
            if result.get("page_id"):
                self.generated_page_ids.append(result["page_id"])
            
            # Validate result structure
            if not result.get("success"):
                self.add_result(test_name, False, {"error": "Generation failed"})
                return False
            
            if not result.get("html"):
                self.add_result(test_name, False, {"error": "No HTML generated"})
                return False
            
            if not result.get("css"):
                self.add_result(test_name, False, {"error": "No CSS generated"})
                return False
            
            # Validate HTML
            html_validation = self.validate_html(result["html"])
            
            # Validate CSS
            css_validation = self.validate_css(result["css"])
            
            # Check preview URL
            has_preview = result.get("preview_url") is not None
            
            # Check download URL
            has_download = result.get("download_url") is not None
            
            passed = (
                html_validation["valid"] and
                css_validation["valid"] and
                has_preview and
                has_download
            )
            
            self.add_result(test_name, passed, {
                "page_id": result.get("page_id"),
                "html_validation": html_validation,
                "css_validation": css_validation,
                "has_preview_url": has_preview,
                "has_download_url": has_download,
                "preview_url": result.get("preview_url"),
                "download_url": result.get("download_url")
            })
            
            return passed
            
        except Exception as e:
            self.add_result(test_name, False, {"error": str(e)})
            return False
    
    async def test_website_generation(self) -> bool:
        """Test multi-page website generation."""
        test_name = "Website Generation"
        
        try:
            result = await self.builder.generate_website(
                campaign_id="test-campaign-website",
                pages=["home", "about", "contact", "product"],
                brand_data={
                    "name": "Test Company",
                    "colors": {
                        "primary": "#3b82f6",
                        "secondary": "#10b981"
                    },
                    "target_audience": "small businesses",
                    "key_benefits": [
                        "Save time",
                        "Increase productivity",
                        "Reduce costs"
                    ]
                },
                save_to_disk=True
            )
            
            # Track generated site for cleanup
            if result.get("site_id"):
                self.generated_site_ids.append(result["site_id"])
            
            # Validate result structure
            if not result.get("success"):
                self.add_result(test_name, False, {"error": "Generation failed"})
                return False
            
            if not result.get("pages") or len(result["pages"]) != 4:
                self.add_result(test_name, False, {"error": f"Expected 4 pages, got {len(result.get('pages', []))}"})
                return False
            
            # Check preview URL
            has_preview = result.get("preview_url") is not None
            
            # Check download URL
            has_download = result.get("download_url") is not None
            
            # Validate each page
            page_validations = []
            for page in result["pages"]:
                page_validations.append({
                    "name": page["name"],
                    "has_html": page["html_length"] > 0,
                    "has_css": page["css_length"] > 0
                })
            
            all_pages_valid = all(p["has_html"] and p["has_css"] for p in page_validations)
            
            passed = all_pages_valid and has_preview and has_download
            
            self.add_result(test_name, passed, {
                "site_id": result.get("site_id"),
                "page_count": len(result["pages"]),
                "page_validations": page_validations,
                "has_preview_url": has_preview,
                "has_download_url": has_download,
                "preview_url": result.get("preview_url"),
                "download_url": result.get("download_url")
            })
            
            return passed
            
        except Exception as e:
            self.add_result(test_name, False, {"error": str(e)})
            return False
    
    async def test_landing_page_generator_direct(self) -> bool:
        """Test the LandingPageGenerator directly."""
        test_name = "LandingPageGenerator Direct Test"
        
        try:
            landing_page = await self.generator.generate(
                page_type=LandingPageType.PRODUCT,
                product_name="Test Product",
                product_description="A revolutionary product for modern businesses",
                target_audience="entrepreneurs and small business owners",
                brand_context={
                    "primary_color": "#007bff",
                    "secondary_color": "#6c757d",
                    "voice": {
                        "tone": ["professional", "friendly"],
                        "personality": "innovative"
                    }
                },
                key_benefits=[
                    "Increase productivity by 50%",
                    "Save 10 hours per week",
                    "Reduce costs by 30%"
                ]
            )
            
            # Validate landing page content
            has_title = bool(landing_page.title)
            has_description = bool(landing_page.meta_description)
            has_sections = len(landing_page.sections) > 0
            
            # Generate HTML
            html = landing_page.to_html({
                "primary_color": "#007bff",
                "secondary_color": "#6c757d"
            })
            
            html_validation = self.validate_html(html)
            
            passed = has_title and has_description and has_sections and html_validation["valid"]
            
            self.add_result(test_name, passed, {
                "title": landing_page.title,
                "meta_description": landing_page.meta_description[:100] if landing_page.meta_description else None,
                "section_count": len(landing_page.sections),
                "section_types": [s.section_type for s in landing_page.sections],
                "html_validation": html_validation
            })
            
            return passed
            
        except Exception as e:
            self.add_result(test_name, False, {"error": str(e)})
            return False
    
    async def test_preview_files_exist(self) -> bool:
        """Test that preview files are created correctly."""
        test_name = "Preview Files Existence"
        
        try:
            # Generate a test page
            result = await self.builder.generate_landing_page(
                campaign_id="test-preview-files",
                template="product_launch",
                headline="Preview Test Page",
                subheadline="Testing file creation",
                cta_text="Test CTA",
                cta_url="#",
                features=["Feature 1", "Feature 2"],
                testimonials=[],
                brand_colors={"primary": "#007bff", "secondary": "#6c757d"},
                save_to_disk=True
            )
            
            if result.get("page_id"):
                self.generated_page_ids.append(result["page_id"])
            
            page_id = result.get("page_id")
            if not page_id:
                self.add_result(test_name, False, {"error": "No page_id returned"})
                return False
            
            # Check files exist
            page_dir = LANDING_PAGES_DIR / page_id
            index_exists = (page_dir / "index.html").exists()
            css_exists = (page_dir / "css" / "styles.css").exists()
            js_exists = (page_dir / "js" / "main.js").exists()
            zip_exists = (LANDING_PAGES_DIR / f"{page_id}.zip").exists()
            metadata_exists = (page_dir / "metadata.json").exists()
            
            passed = index_exists and css_exists and js_exists and zip_exists and metadata_exists
            
            self.add_result(test_name, passed, {
                "page_id": page_id,
                "index_html_exists": index_exists,
                "css_exists": css_exists,
                "js_exists": js_exists,
                "zip_exists": zip_exists,
                "metadata_exists": metadata_exists,
                "page_dir": str(page_dir)
            })
            
            return passed
            
        except Exception as e:
            self.add_result(test_name, False, {"error": str(e)})
            return False
    
    async def test_all_page_types(self) -> bool:
        """Test all landing page types."""
        test_name = "All Page Types Generation"
        
        try:
            page_types = [
                LandingPageType.PRODUCT,
                LandingPageType.LEAD_CAPTURE,
                LandingPageType.EVENT,
                LandingPageType.WEBINAR,
                LandingPageType.COMING_SOON,
                LandingPageType.COMPARISON
            ]
            
            results = []
            for page_type in page_types:
                try:
                    landing_page = await self.generator.generate(
                        page_type=page_type,
                        product_name=f"Test {page_type.value}",
                        product_description=f"Testing {page_type.value} page type",
                        target_audience="test audience",
                        brand_context={"primary_color": "#007bff"},
                        key_benefits=["Benefit 1", "Benefit 2"]
                    )
                    
                    html = landing_page.to_html()
                    
                    results.append({
                        "page_type": page_type.value,
                        "success": True,
                        "section_count": len(landing_page.sections),
                        "html_length": len(html)
                    })
                except Exception as e:
                    results.append({
                        "page_type": page_type.value,
                        "success": False,
                        "error": str(e)
                    })
            
            all_passed = all(r["success"] for r in results)
            
            self.add_result(test_name, all_passed, {
                "page_type_results": results,
                "total_types": len(page_types),
                "successful_types": sum(1 for r in results if r["success"])
            })
            
            return all_passed
            
        except Exception as e:
            self.add_result(test_name, False, {"error": str(e)})
            return False
    
    def cleanup(self):
        """Clean up generated test files."""
        print("\n🧹 Cleaning up test files...")
        
        for page_id in self.generated_page_ids:
            try:
                self.builder.delete_landing_page(page_id)
                print(f"   Deleted landing page: {page_id}")
            except Exception as e:
                print(f"   Failed to delete landing page {page_id}: {e}")
        
        for site_id in self.generated_site_ids:
            try:
                self.builder.delete_site(site_id)
                print(f"   Deleted site: {site_id}")
            except Exception as e:
                print(f"   Failed to delete site {site_id}: {e}")
    
    def save_results(self):
        """Save test results to JSON file."""
        results_dir = Path(__file__).parent.parent / "test_results"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results_file = results_dir / "landing_pages_test.json"
        
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Results saved to: {results_file}")
    
    async def run_all_tests(self):
        """Run all tests."""
        print("=" * 60)
        print("🚀 Landing Page Generation Test Suite")
        print("=" * 60)
        print()
        
        # Test 1: Landing page templates
        templates = ["product_launch", "lead_gen", "event", "webinar"]
        print("📋 Testing Landing Page Templates...")
        for template in templates:
            await self.test_landing_page_template(template)
        
        print()
        
        # Test 2: Website generation
        print("📋 Testing Website Generation...")
        await self.test_website_generation()
        
        print()
        
        # Test 3: Direct generator test
        print("📋 Testing LandingPageGenerator Directly...")
        await self.test_landing_page_generator_direct()
        
        print()
        
        # Test 4: Preview files
        print("📋 Testing Preview Files Creation...")
        await self.test_preview_files_exist()
        
        print()
        
        # Test 5: All page types
        print("📋 Testing All Page Types...")
        await self.test_all_page_types()
        
        print()
        print("=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        print(f"Total Tests: {self.results['summary']['total']}")
        print(f"Passed: {self.results['summary']['passed']} ✅")
        print(f"Failed: {self.results['summary']['failed']} ❌")
        print(f"Success Rate: {self.results['summary']['passed'] / max(self.results['summary']['total'], 1) * 100:.1f}%")
        print()
        
        # Save results
        self.save_results()
        
        # Cleanup
        self.cleanup()
        
        return self.results["summary"]["failed"] == 0


async def main():
    """Main entry point."""
    test_suite = LandingPageTestSuite()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
