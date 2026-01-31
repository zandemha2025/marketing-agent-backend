"""
Static Site Builder Service

Builds complete static sites from generated landing pages.
Supports:
- Multi-page website generation
- CSS/JS bundling
- Asset management
- ZIP packaging for download
- Local storage and cloud deployment
"""
import os
import uuid
import json
import zipfile
import shutil
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from io import BytesIO

from .landing_page_generator import LandingPageGenerator, LandingPageType, LandingPageContent

logger = logging.getLogger(__name__)

# Base output directory for generated sites
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "outputs"
LANDING_PAGES_DIR = OUTPUT_DIR / "landing_pages"
SITES_DIR = OUTPUT_DIR / "sites"


@dataclass
class GeneratedPage:
    """A single generated page."""
    page_id: str
    name: str
    html: str
    css: str
    js: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "name": self.name,
            "html_length": len(self.html),
            "css_length": len(self.css),
            "js_length": len(self.js) if self.js else 0,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class GeneratedSite:
    """A complete generated static site."""
    site_id: str
    name: str
    pages: List[GeneratedPage]
    global_css: str
    global_js: str
    assets: Dict[str, bytes] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "name": self.name,
            "pages": [p.to_dict() for p in self.pages],
            "page_count": len(self.pages),
            "asset_count": len(self.assets),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class StaticSiteBuilder:
    """
    Build complete static sites from landing page content.
    
    Features:
    - Generate multi-page websites
    - Bundle CSS and JS
    - Create downloadable ZIP files
    - Support for local and cloud storage
    """
    
    # Page templates for different page types
    PAGE_TEMPLATES = {
        "home": LandingPageType.PRODUCT,
        "about": LandingPageType.PRODUCT,
        "contact": LandingPageType.LEAD_CAPTURE,
        "product": LandingPageType.PRODUCT,
        "pricing": LandingPageType.PRODUCT,
        "features": LandingPageType.PRODUCT,
        "blog": LandingPageType.PRODUCT,
        "landing": LandingPageType.LEAD_CAPTURE,
        "event": LandingPageType.EVENT,
        "webinar": LandingPageType.WEBINAR,
    }
    
    # Section configurations for different page types
    PAGE_SECTIONS = {
        "home": ["hero", "features", "benefits", "testimonials", "cta"],
        "about": ["hero", "benefits", "social_proof", "testimonials"],
        "contact": ["hero", "email_capture", "faq"],
        "product": ["hero", "features", "benefits", "pricing", "testimonials", "faq", "cta"],
        "pricing": ["hero", "pricing", "faq", "cta"],
        "features": ["hero", "features", "benefits", "how_it_works", "cta"],
        "blog": ["hero", "features"],
        "landing": ["hero", "benefits", "email_capture", "testimonials"],
        "event": ["hero", "countdown", "benefits", "how_it_works", "cta"],
        "webinar": ["hero", "countdown", "benefits", "email_capture"],
    }
    
    def __init__(self):
        self.generator = LandingPageGenerator()
        self._ensure_output_dirs()
    
    def _ensure_output_dirs(self):
        """Ensure output directories exist."""
        LANDING_PAGES_DIR.mkdir(parents=True, exist_ok=True)
        SITES_DIR.mkdir(parents=True, exist_ok=True)
    
    def _generate_global_css(self, brand_colors: Dict[str, str]) -> str:
        """Generate global CSS with brand colors."""
        primary = brand_colors.get("primary", "#3b82f6")
        secondary = brand_colors.get("secondary", "#10b981")
        
        return f"""
/* Global Styles */
:root {{
    --color-primary: {primary};
    --color-secondary: {secondary};
    --color-text: #1f2937;
    --color-text-light: #6b7280;
    --color-bg: #ffffff;
    --color-bg-alt: #f9fafb;
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{
    font-family: var(--font-sans);
    color: var(--color-text);
    background-color: var(--color-bg);
    line-height: 1.6;
}}

a {{
    color: var(--color-primary);
    text-decoration: none;
    transition: opacity 0.2s;
}}

a:hover {{
    opacity: 0.8;
}}

img {{
    max-width: 100%;
    height: auto;
}}

/* Navigation */
.nav {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    z-index: 1000;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}}

.nav-logo {{
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-primary);
}}

.nav-links {{
    display: flex;
    gap: 2rem;
    list-style: none;
}}

.nav-links a {{
    color: var(--color-text);
    font-weight: 500;
}}

.nav-links a:hover {{
    color: var(--color-primary);
}}

/* Footer */
.footer {{
    background: #1f2937;
    color: white;
    padding: 4rem 2rem 2rem;
}}

.footer-content {{
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 2rem;
}}

.footer-section h4 {{
    font-size: 1rem;
    margin-bottom: 1rem;
    color: white;
}}

.footer-section ul {{
    list-style: none;
}}

.footer-section li {{
    margin-bottom: 0.5rem;
}}

.footer-section a {{
    color: #9ca3af;
}}

.footer-section a:hover {{
    color: white;
}}

.footer-bottom {{
    max-width: 1200px;
    margin: 2rem auto 0;
    padding-top: 2rem;
    border-top: 1px solid #374151;
    text-align: center;
    color: #9ca3af;
}}

/* Utility Classes */
.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}}

.btn {{
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border-radius: 0.5rem;
    font-weight: 600;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
}}

.btn-primary {{
    background: var(--color-primary);
    color: white;
}}

.btn-primary:hover {{
    opacity: 0.9;
    transform: translateY(-1px);
}}

.btn-secondary {{
    background: var(--color-secondary);
    color: white;
}}

/* Responsive */
@media (max-width: 768px) {{
    .nav {{
        padding: 1rem;
    }}
    
    .nav-links {{
        display: none;
    }}
    
    .footer-content {{
        grid-template-columns: 1fr;
    }}
}}
"""
    
    def _generate_global_js(self) -> str:
        """Generate global JavaScript."""
        return """
// Global JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
    
    // Mobile menu toggle
    const menuToggle = document.querySelector('.menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }
    
    // Form submission handling
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            console.log('Form submitted:', Object.fromEntries(formData));
            // Add your form submission logic here
            alert('Thank you for your submission!');
            this.reset();
        });
    });
    
    // Countdown timer (for event/webinar pages)
    const countdownElements = document.querySelectorAll('[data-countdown]');
    countdownElements.forEach(el => {
        const targetDate = new Date(el.dataset.countdown).getTime();
        
        const updateCountdown = () => {
            const now = new Date().getTime();
            const distance = targetDate - now;
            
            if (distance < 0) {
                el.innerHTML = 'Event has started!';
                return;
            }
            
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            const daysEl = el.querySelector('#days');
            const hoursEl = el.querySelector('#hours');
            const minutesEl = el.querySelector('#minutes');
            const secondsEl = el.querySelector('#seconds');
            
            if (daysEl) daysEl.textContent = String(days).padStart(2, '0');
            if (hoursEl) hoursEl.textContent = String(hours).padStart(2, '0');
            if (minutesEl) minutesEl.textContent = String(minutes).padStart(2, '0');
            if (secondsEl) secondsEl.textContent = String(seconds).padStart(2, '0');
        };
        
        updateCountdown();
        setInterval(updateCountdown, 1000);
    });
    
    // Intersection Observer for animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('section').forEach(section => {
        observer.observe(section);
    });
});
"""
    
    def _wrap_with_layout(
        self,
        content: str,
        page_name: str,
        site_name: str,
        pages: List[str],
        brand_colors: Dict[str, str]
    ) -> str:
        """Wrap page content with navigation and footer."""
        primary = brand_colors.get("primary", "#3b82f6")
        
        # Generate navigation links
        nav_links = ""
        for page in pages:
            active = "active" if page == page_name else ""
            href = "index.html" if page == "home" else f"{page}.html"
            nav_links += f'<li><a href="{href}" class="{active}">{page.title()}</a></li>\n'
        
        # Extract body content from the generated HTML
        # The landing page generator creates full HTML documents, we need just the body
        import re
        body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
        body_content = body_match.group(1) if body_match else content
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_name.title()} - {site_name}</title>
    <link rel="stylesheet" href="css/styles.css">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        primary: '{primary}',
                        secondary: '{brand_colors.get("secondary", "#10b981")}',
                    }},
                    fontFamily: {{
                        sans: ['Inter', 'sans-serif'],
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="font-sans antialiased">
    <!-- Navigation -->
    <nav class="nav">
        <a href="index.html" class="nav-logo">{site_name}</a>
        <ul class="nav-links">
            {nav_links}
        </ul>
        <button class="menu-toggle md:hidden">☰</button>
    </nav>
    
    <!-- Main Content -->
    <main style="padding-top: 80px;">
        {body_content}
    </main>
    
    <!-- Footer -->
    <footer class="footer">
        <div class="footer-content">
            <div class="footer-section">
                <h4>{site_name}</h4>
                <p style="color: #9ca3af;">Building the future, one page at a time.</p>
            </div>
            <div class="footer-section">
                <h4>Pages</h4>
                <ul>
                    {nav_links}
                </ul>
            </div>
            <div class="footer-section">
                <h4>Contact</h4>
                <ul>
                    <li><a href="mailto:hello@example.com">hello@example.com</a></li>
                    <li><a href="tel:+1234567890">+1 (234) 567-890</a></li>
                </ul>
            </div>
            <div class="footer-section">
                <h4>Follow Us</h4>
                <ul>
                    <li><a href="#">Twitter</a></li>
                    <li><a href="#">LinkedIn</a></li>
                    <li><a href="#">Instagram</a></li>
                </ul>
            </div>
        </div>
        <div class="footer-bottom">
            <p>&copy; {datetime.utcnow().year} {site_name}. All rights reserved.</p>
        </div>
    </footer>
    
    <script src="js/main.js"></script>
</body>
</html>'''
    
    async def generate_landing_page(
        self,
        campaign_id: str,
        template: str,
        headline: str,
        subheadline: str,
        cta_text: str,
        cta_url: str,
        features: List[str],
        testimonials: List[Dict[str, str]],
        brand_colors: Dict[str, str],
        save_to_disk: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a single landing page based on campaign data.
        
        Args:
            campaign_id: Campaign identifier
            template: Template type (product_launch, lead_gen, event, webinar)
            headline: Main headline
            subheadline: Supporting subheadline
            cta_text: Call-to-action button text
            cta_url: Call-to-action URL
            features: List of feature descriptions
            testimonials: List of testimonial objects
            brand_colors: Brand color configuration
            save_to_disk: Whether to save files to disk
            
        Returns:
            Dictionary with page_id, html, css, preview_url, download_url
        """
        page_id = str(uuid.uuid4())
        
        # Map template to page type
        template_map = {
            "product_launch": LandingPageType.PRODUCT,
            "lead_gen": LandingPageType.LEAD_CAPTURE,
            "event": LandingPageType.EVENT,
            "webinar": LandingPageType.WEBINAR,
        }
        page_type = template_map.get(template, LandingPageType.PRODUCT)
        
        # Generate landing page content using the existing generator
        landing_page = await self.generator.generate(
            page_type=page_type,
            product_name=headline,
            product_description=subheadline,
            target_audience="target customers",
            brand_context={
                "primary_color": brand_colors.get("primary", "#007bff"),
                "secondary_color": brand_colors.get("secondary", "#6c757d"),
            },
            key_benefits=features[:5]
        )
        
        # Override with provided content
        if landing_page.sections:
            # Update hero section
            for section in landing_page.sections:
                if section.section_type == "hero":
                    section.headline = headline
                    section.subheadline = subheadline
                    section.cta_text = cta_text
                    section.cta_url = cta_url
                    break
            
            # Update features section
            for section in landing_page.sections:
                if section.section_type == "features":
                    section.content["features"] = [
                        {"title": f, "description": f"Experience the power of {f.lower()}", "icon": "✨"}
                        for f in features
                    ]
                    break
            
            # Update testimonials section
            for section in landing_page.sections:
                if section.section_type == "testimonials":
                    section.content["testimonials"] = [
                        {"quote": t.get("quote", ""), "author": t.get("name", ""), "title": "Customer"}
                        for t in testimonials
                    ]
                    break
        
        # Generate HTML with brand colors
        html = landing_page.to_html(brand_colors)
        
        # Generate CSS
        css = self._generate_global_css(brand_colors)
        
        # Save to disk if requested
        preview_url = None
        download_url = None
        
        if save_to_disk:
            page_dir = LANDING_PAGES_DIR / page_id
            page_dir.mkdir(parents=True, exist_ok=True)
            
            # Save HTML
            (page_dir / "index.html").write_text(html)
            
            # Save CSS
            css_dir = page_dir / "css"
            css_dir.mkdir(exist_ok=True)
            (css_dir / "styles.css").write_text(css)
            
            # Save JS
            js_dir = page_dir / "js"
            js_dir.mkdir(exist_ok=True)
            (js_dir / "main.js").write_text(self._generate_global_js())
            
            # Create ZIP file
            zip_path = LANDING_PAGES_DIR / f"{page_id}.zip"
            self._create_zip(page_dir, zip_path)
            
            preview_url = f"/preview/landing-pages/{page_id}"
            download_url = f"/download/landing-pages/{page_id}.zip"
            
            # Save metadata
            metadata = {
                "page_id": page_id,
                "campaign_id": campaign_id,
                "template": template,
                "headline": headline,
                "created_at": datetime.utcnow().isoformat()
            }
            (page_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
        
        return {
            "success": True,
            "page_id": page_id,
            "html": html,
            "css": css,
            "preview_url": preview_url,
            "download_url": download_url
        }
    
    async def generate_website(
        self,
        campaign_id: str,
        pages: List[str],
        brand_data: Dict[str, Any],
        save_to_disk: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a complete multi-page website.
        
        Args:
            campaign_id: Campaign identifier
            pages: List of page names to generate (home, about, contact, product)
            brand_data: Brand configuration including colors, name, etc.
            save_to_disk: Whether to save files to disk
            
        Returns:
            Dictionary with site_id, pages, preview_url, download_url
        """
        site_id = str(uuid.uuid4())
        site_name = brand_data.get("name", "My Website")
        brand_colors = brand_data.get("colors", {"primary": "#3b82f6", "secondary": "#10b981"})
        
        generated_pages = []
        
        for page_name in pages:
            # Determine page type and sections
            page_type = self.PAGE_TEMPLATES.get(page_name, LandingPageType.PRODUCT)
            sections = self.PAGE_SECTIONS.get(page_name, ["hero", "features", "cta"])
            
            # Generate page content
            landing_page = await self.generator.generate(
                page_type=page_type,
                product_name=f"{site_name} - {page_name.title()}",
                product_description=f"{page_name.title()} page for {site_name}",
                target_audience=brand_data.get("target_audience", "customers"),
                brand_context={
                    "primary_color": brand_colors.get("primary", "#3b82f6"),
                    "secondary_color": brand_colors.get("secondary", "#10b981"),
                    "voice": brand_data.get("voice", {})
                },
                sections_requested=sections,
                key_benefits=brand_data.get("key_benefits", [])
            )
            
            # Generate HTML
            raw_html = landing_page.to_html(brand_colors)
            
            # Wrap with site layout
            html = self._wrap_with_layout(
                content=raw_html,
                page_name=page_name,
                site_name=site_name,
                pages=pages,
                brand_colors=brand_colors
            )
            
            page_id = str(uuid.uuid4())
            generated_pages.append(GeneratedPage(
                page_id=page_id,
                name=page_name,
                html=html,
                css=self._generate_global_css(brand_colors),
                js=self._generate_global_js(),
                metadata={
                    "title": landing_page.title,
                    "description": landing_page.meta_description,
                    "sections": [s.section_type for s in landing_page.sections]
                }
            ))
        
        # Create site object
        site = GeneratedSite(
            site_id=site_id,
            name=site_name,
            pages=generated_pages,
            global_css=self._generate_global_css(brand_colors),
            global_js=self._generate_global_js(),
            metadata={
                "campaign_id": campaign_id,
                "brand_data": brand_data,
                "page_count": len(pages)
            }
        )
        
        preview_url = None
        download_url = None
        
        if save_to_disk:
            site_dir = SITES_DIR / site_id
            site_dir.mkdir(parents=True, exist_ok=True)
            
            # Save global CSS
            css_dir = site_dir / "css"
            css_dir.mkdir(exist_ok=True)
            (css_dir / "styles.css").write_text(site.global_css)
            
            # Save global JS
            js_dir = site_dir / "js"
            js_dir.mkdir(exist_ok=True)
            (js_dir / "main.js").write_text(site.global_js)
            
            # Save each page
            for page in generated_pages:
                filename = "index.html" if page.name == "home" else f"{page.name}.html"
                (site_dir / filename).write_text(page.html)
            
            # Create ZIP file
            zip_path = SITES_DIR / f"{site_id}.zip"
            self._create_zip(site_dir, zip_path)
            
            preview_url = f"/preview/sites/{site_id}"
            download_url = f"/download/sites/{site_id}.zip"
            
            # Save metadata
            (site_dir / "metadata.json").write_text(json.dumps(site.to_dict(), indent=2))
        
        return {
            "success": True,
            "site_id": site_id,
            "pages": [p.to_dict() for p in generated_pages],
            "preview_url": preview_url,
            "download_url": download_url
        }
    
    def _create_zip(self, source_dir: Path, zip_path: Path):
        """Create a ZIP file from a directory."""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
    
    def get_landing_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get a generated landing page by ID."""
        page_dir = LANDING_PAGES_DIR / page_id
        if not page_dir.exists():
            return None
        
        metadata_path = page_dir / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text())
        else:
            metadata = {"page_id": page_id}
        
        html_path = page_dir / "index.html"
        html = html_path.read_text() if html_path.exists() else ""
        
        css_path = page_dir / "css" / "styles.css"
        css = css_path.read_text() if css_path.exists() else ""
        
        return {
            "page_id": page_id,
            "html": html,
            "css": css,
            "metadata": metadata
        }
    
    def get_site(self, site_id: str) -> Optional[Dict[str, Any]]:
        """Get a generated site by ID."""
        site_dir = SITES_DIR / site_id
        if not site_dir.exists():
            return None
        
        metadata_path = site_dir / "metadata.json"
        if metadata_path.exists():
            return json.loads(metadata_path.read_text())
        
        return {"site_id": site_id}
    
    def get_zip_path(self, resource_type: str, resource_id: str) -> Optional[Path]:
        """Get the path to a ZIP file for download."""
        if resource_type == "landing-pages":
            zip_path = LANDING_PAGES_DIR / f"{resource_id}.zip"
        elif resource_type == "sites":
            zip_path = SITES_DIR / f"{resource_id}.zip"
        else:
            return None
        
        return zip_path if zip_path.exists() else None
    
    def get_preview_path(self, resource_type: str, resource_id: str) -> Optional[Path]:
        """Get the path to preview files."""
        if resource_type == "landing-pages":
            preview_path = LANDING_PAGES_DIR / resource_id
        elif resource_type == "sites":
            preview_path = SITES_DIR / resource_id
        else:
            return None
        
        return preview_path if preview_path.exists() else None
    
    def list_landing_pages(self) -> List[Dict[str, Any]]:
        """List all generated landing pages."""
        pages = []
        for page_dir in LANDING_PAGES_DIR.iterdir():
            if page_dir.is_dir():
                metadata_path = page_dir / "metadata.json"
                if metadata_path.exists():
                    pages.append(json.loads(metadata_path.read_text()))
                else:
                    pages.append({"page_id": page_dir.name})
        return pages
    
    def list_sites(self) -> List[Dict[str, Any]]:
        """List all generated sites."""
        sites = []
        for site_dir in SITES_DIR.iterdir():
            if site_dir.is_dir():
                metadata_path = site_dir / "metadata.json"
                if metadata_path.exists():
                    sites.append(json.loads(metadata_path.read_text()))
                else:
                    sites.append({"site_id": site_dir.name})
        return sites
    
    def delete_landing_page(self, page_id: str) -> bool:
        """Delete a generated landing page."""
        page_dir = LANDING_PAGES_DIR / page_id
        zip_path = LANDING_PAGES_DIR / f"{page_id}.zip"
        
        deleted = False
        if page_dir.exists():
            shutil.rmtree(page_dir)
            deleted = True
        if zip_path.exists():
            zip_path.unlink()
            deleted = True
        
        return deleted
    
    def delete_site(self, site_id: str) -> bool:
        """Delete a generated site."""
        site_dir = SITES_DIR / site_id
        zip_path = SITES_DIR / f"{site_id}.zip"
        
        deleted = False
        if site_dir.exists():
            shutil.rmtree(site_dir)
            deleted = True
        if zip_path.exists():
            zip_path.unlink()
            deleted = True
        
        return deleted


# Singleton instance
_builder: Optional[StaticSiteBuilder] = None


def get_static_site_builder() -> StaticSiteBuilder:
    """Get or create the static site builder singleton."""
    global _builder
    if _builder is None:
        _builder = StaticSiteBuilder()
    return _builder
