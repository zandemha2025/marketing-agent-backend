"""
Landing Page Generator Service

Generates landing pages in multiple output formats:
- HTML + Tailwind: Quick landing pages
- React Component: Integration into existing apps
- Next.js Project: Full deployable sites

Features:
- Multiple landing page types (product, lead capture, event, webinar, coming soon, comparison)
- Brand DNA integration (colors, fonts, voice)
- Section-based page structure
- SEO metadata generation (title, meta description, OG tags)
- Conversion-optimized copy
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import re

from ..ai.openrouter import OpenRouterService
from ...core.config import get_settings

logger = logging.getLogger(__name__)


class LandingPageType(str, Enum):
    """Types of landing pages supported."""
    PRODUCT = "product"
    LEAD_CAPTURE = "lead_capture"
    EVENT = "event"
    WEBINAR = "webinar"
    COMING_SOON = "coming_soon"
    COMPARISON = "comparison"


@dataclass
class LandingPageSection:
    """A section of a landing page."""
    section_type: str  # hero, features, testimonials, pricing, cta, faq, benefits, social_proof, how_it_works
    headline: str
    subheadline: Optional[str] = None
    content: Dict[str, Any] = field(default_factory=dict)
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    image_prompt: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_type": self.section_type,
            "headline": self.headline,
            "subheadline": self.subheadline,
            "content": self.content,
            "cta_text": self.cta_text,
            "cta_url": self.cta_url,
            "image_prompt": self.image_prompt
        }


@dataclass
class LandingPageContent:
    """A generated landing page with all content and metadata."""
    page_type: LandingPageType
    title: str
    meta_description: str
    og_title: str
    og_description: str
    sections: List[LandingPageSection]
    
    # Additional metadata
    keywords: List[str] = field(default_factory=list)
    og_image_prompt: Optional[str] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Cached output formats
    _html_cache: Optional[str] = field(default=None, repr=False)
    _nextjs_cache: Optional[Dict[str, str]] = field(default=None, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_type": self.page_type.value,
            "title": self.title,
            "meta_description": self.meta_description,
            "og_title": self.og_title,
            "og_description": self.og_description,
            "sections": [s.to_dict() for s in self.sections],
            "keywords": self.keywords,
            "og_image_prompt": self.og_image_prompt,
            "generated_at": self.generated_at.isoformat()
        }
    
    def to_html(self, brand_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert landing page content to HTML with Tailwind CSS.
        
        Args:
            brand_data: Optional brand colors/fonts to apply
            
        Returns:
            Complete HTML document string
        """
        brand = brand_data or {}
        primary_color = brand.get("primary_color", "#3b82f6")
        secondary_color = brand.get("secondary_color", "#10b981")
        font_family = brand.get("font_family", "Inter")
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <meta name="description" content="{self.meta_description}">
    <meta name="keywords" content="{', '.join(self.keywords)}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{self.og_title}">
    <meta property="og:description" content="{self.og_description}">
    <meta property="og:type" content="website">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{self.og_title}">
    <meta name="twitter:description" content="{self.og_description}">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family={font_family.replace(' ', '+')}&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        primary: '{primary_color}',
                        secondary: '{secondary_color}',
                    }},
                    fontFamily: {{
                        sans: ['{font_family}', 'sans-serif'],
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="font-sans antialiased">
'''
        
        for section in self.sections:
            html += self._render_section_html(section, primary_color, secondary_color)
        
        html += '''
</body>
</html>'''
        
        return html
    
    def _render_section_html(self, section: LandingPageSection, primary_color: str, secondary_color: str) -> str:
        """Render a single section as HTML."""
        
        if section.section_type == "hero":
            return f'''
    <section class="bg-gradient-to-br from-gray-900 to-gray-800 text-white py-20 px-4">
        <div class="max-w-4xl mx-auto text-center">
            <h1 class="text-5xl font-bold mb-6">{section.headline}</h1>
            <p class="text-xl text-gray-300 mb-8">{section.subheadline or ''}</p>
            <a href="{section.cta_url or '#'}" class="inline-block bg-primary hover:opacity-90 text-white font-bold py-4 px-8 rounded-lg text-lg transition">
                {section.cta_text or 'Get Started'}
            </a>
            {f'<p class="mt-4 text-sm text-gray-400">{section.content.get("cta_subtext", "")}</p>' if section.content.get("cta_subtext") else ''}
        </div>
    </section>
'''
        elif section.section_type == "features":
            features = section.content.get("features", [])
            features_html = ""
            for feature in features:
                features_html += f'''
                <div class="p-6 bg-white rounded-lg shadow-md">
                    <div class="text-4xl mb-4">{feature.get("icon", "✨")}</div>
                    <h3 class="text-xl font-semibold mb-2">{feature.get("title", "")}</h3>
                    <p class="text-gray-600">{feature.get("description", "")}</p>
                </div>
'''
            return f'''
    <section class="py-20 px-4 bg-gray-50">
        <div class="max-w-6xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-4">{section.headline}</h2>
            <p class="text-gray-600 text-center mb-12">{section.subheadline or ''}</p>
            <div class="grid md:grid-cols-3 gap-8">
                {features_html}
            </div>
        </div>
    </section>
'''
        elif section.section_type == "benefits":
            benefits = section.content.get("benefits", [])
            benefits_html = ""
            for benefit in benefits:
                benefits_html += f'''
                <div class="flex items-start gap-4">
                    <div class="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white">✓</div>
                    <div>
                        <h3 class="text-lg font-semibold mb-1">{benefit.get("title", "")}</h3>
                        <p class="text-gray-600">{benefit.get("description", "")}</p>
                    </div>
                </div>
'''
            return f'''
    <section class="py-20 px-4 bg-white">
        <div class="max-w-4xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-4">{section.headline}</h2>
            <p class="text-gray-600 text-center mb-12">{section.subheadline or ''}</p>
            <div class="space-y-6">
                {benefits_html}
            </div>
        </div>
    </section>
'''
        elif section.section_type == "testimonials":
            testimonials = section.content.get("testimonials", [])
            testimonials_html = ""
            for testimonial in testimonials:
                testimonials_html += f'''
                <div class="bg-white p-8 rounded-2xl shadow-sm">
                    <div class="flex gap-1 mb-4">
                        {''.join(['<span class="text-yellow-400">★</span>' for _ in range(5)])}
                    </div>
                    <p class="text-gray-700 mb-6">"{testimonial.get("quote", "")}"</p>
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 bg-gray-200 rounded-full"></div>
                        <div>
                            <p class="font-semibold">{testimonial.get("author", "")}</p>
                            <p class="text-sm text-gray-500">{testimonial.get("title", "")}</p>
                        </div>
                    </div>
                </div>
'''
            return f'''
    <section class="py-20 px-4 bg-gray-50">
        <div class="max-w-6xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-12">{section.headline}</h2>
            <div class="grid md:grid-cols-3 gap-8">
                {testimonials_html}
            </div>
        </div>
    </section>
'''
        elif section.section_type == "pricing":
            tiers = section.content.get("tiers", [])
            tiers_html = ""
            for tier in tiers:
                features_list = "".join([f'<li class="flex items-center gap-2"><span class="text-primary">✓</span>{f}</li>' for f in tier.get("features", [])])
                highlighted = "border-2 border-primary" if tier.get("highlighted") else ""
                tiers_html += f'''
                <div class="bg-white p-8 rounded-2xl shadow-sm {highlighted}">
                    <h3 class="text-xl font-bold mb-2">{tier.get("name", "")}</h3>
                    <p class="text-gray-600 mb-4">{tier.get("description", "")}</p>
                    <div class="text-4xl font-bold mb-6">{tier.get("price", "")}<span class="text-lg text-gray-500">{tier.get("period", "/mo")}</span></div>
                    <ul class="space-y-3 mb-8">
                        {features_list}
                    </ul>
                    <a href="{tier.get("cta_url", "#")}" class="block text-center bg-primary text-white py-3 px-6 rounded-lg hover:opacity-90 transition">
                        {tier.get("cta_text", "Get Started")}
                    </a>
                </div>
'''
            return f'''
    <section class="py-20 px-4 bg-white">
        <div class="max-w-6xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-4">{section.headline}</h2>
            <p class="text-gray-600 text-center mb-12">{section.subheadline or ''}</p>
            <div class="grid md:grid-cols-3 gap-8">
                {tiers_html}
            </div>
        </div>
    </section>
'''
        elif section.section_type == "faq":
            questions = section.content.get("questions", [])
            faq_html = ""
            for q in questions:
                faq_html += f'''
                <div class="border-b border-gray-200 pb-6">
                    <h3 class="text-lg font-semibold mb-2">{q.get("question", "")}</h3>
                    <p class="text-gray-600">{q.get("answer", "")}</p>
                </div>
'''
            return f'''
    <section class="py-20 px-4 bg-gray-50">
        <div class="max-w-3xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-12">{section.headline}</h2>
            <div class="space-y-6">
                {faq_html}
            </div>
        </div>
    </section>
'''
        elif section.section_type == "how_it_works":
            steps = section.content.get("steps", [])
            steps_html = ""
            for i, step in enumerate(steps, 1):
                steps_html += f'''
                <div class="text-center">
                    <div class="w-12 h-12 bg-primary text-white rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-4">{i}</div>
                    <h3 class="text-xl font-semibold mb-2">{step.get("title", "")}</h3>
                    <p class="text-gray-600">{step.get("description", "")}</p>
                </div>
'''
            return f'''
    <section class="py-20 px-4 bg-white">
        <div class="max-w-5xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-4">{section.headline}</h2>
            <p class="text-gray-600 text-center mb-12">{section.subheadline or ''}</p>
            <div class="grid md:grid-cols-{min(len(steps), 4)} gap-8">
                {steps_html}
            </div>
        </div>
    </section>
'''
        elif section.section_type == "social_proof":
            logos = section.content.get("logos", [])
            stats = section.content.get("stats", [])
            logos_html = "".join([f'<div class="text-gray-400 text-lg font-semibold">{logo}</div>' for logo in logos])
            stats_html = "".join([f'<div class="text-center"><div class="text-4xl font-bold text-primary">{s.get("value", "")}</div><div class="text-gray-600">{s.get("label", "")}</div></div>' for s in stats])
            return f'''
    <section class="py-16 px-4 bg-gray-50">
        <div class="max-w-6xl mx-auto">
            <h2 class="text-2xl font-bold text-center mb-8">{section.headline}</h2>
            {f'<div class="flex flex-wrap justify-center gap-12 mb-12">{logos_html}</div>' if logos else ''}
            {f'<div class="grid md:grid-cols-{len(stats)} gap-8">{stats_html}</div>' if stats else ''}
        </div>
    </section>
'''
        elif section.section_type == "cta":
            return f'''
    <section class="py-20 px-4 bg-primary text-white">
        <div class="max-w-4xl mx-auto text-center">
            <h2 class="text-4xl font-bold mb-4">{section.headline}</h2>
            <p class="text-xl mb-8 opacity-90">{section.subheadline or ''}</p>
            <a href="{section.cta_url or '#'}" class="inline-block bg-white text-primary hover:bg-gray-100 font-bold py-4 px-8 rounded-lg text-lg transition">
                {section.cta_text or 'Get Started Now'}
            </a>
            {f'<p class="mt-4 text-sm opacity-75">{section.content.get("guarantee_text", "")}</p>' if section.content.get("guarantee_text") else ''}
        </div>
    </section>
'''
        elif section.section_type == "countdown":
            # For event/webinar pages
            return f'''
    <section class="py-16 px-4 bg-gray-900 text-white">
        <div class="max-w-4xl mx-auto text-center">
            <h2 class="text-3xl font-bold mb-4">{section.headline}</h2>
            <p class="text-xl mb-8 opacity-90">{section.subheadline or ''}</p>
            <div class="flex justify-center gap-8 mb-8">
                <div class="text-center">
                    <div class="text-5xl font-bold" id="days">00</div>
                    <div class="text-sm opacity-75">Days</div>
                </div>
                <div class="text-center">
                    <div class="text-5xl font-bold" id="hours">00</div>
                    <div class="text-sm opacity-75">Hours</div>
                </div>
                <div class="text-center">
                    <div class="text-5xl font-bold" id="minutes">00</div>
                    <div class="text-sm opacity-75">Minutes</div>
                </div>
                <div class="text-center">
                    <div class="text-5xl font-bold" id="seconds">00</div>
                    <div class="text-sm opacity-75">Seconds</div>
                </div>
            </div>
            <a href="{section.cta_url or '#'}" class="inline-block bg-primary hover:opacity-90 text-white font-bold py-4 px-8 rounded-lg text-lg transition">
                {section.cta_text or 'Register Now'}
            </a>
        </div>
    </section>
'''
        elif section.section_type == "comparison":
            # For comparison pages
            comparison = section.content.get("comparison", {})
            our_product = comparison.get("our_product", {})
            competitors = comparison.get("competitors", [])
            features = comparison.get("features", [])
            
            header_html = f'<th class="p-4 text-left">Feature</th><th class="p-4 text-center bg-primary/10 font-bold">{our_product.get("name", "Us")}</th>'
            for comp in competitors:
                header_html += f'<th class="p-4 text-center">{comp.get("name", "")}</th>'
            
            rows_html = ""
            for feature in features:
                row = f'<td class="p-4 border-t">{feature.get("name", "")}</td>'
                row += f'<td class="p-4 border-t text-center bg-primary/5">{feature.get("us", "✓")}</td>'
                for comp in competitors:
                    row += f'<td class="p-4 border-t text-center">{feature.get(comp.get("key", ""), "—")}</td>'
                rows_html += f'<tr>{row}</tr>'
            
            return f'''
    <section class="py-20 px-4 bg-white">
        <div class="max-w-5xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-4">{section.headline}</h2>
            <p class="text-gray-600 text-center mb-12">{section.subheadline or ''}</p>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-50">{header_html}</tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
    </section>
'''
        elif section.section_type == "email_capture":
            # For lead capture pages
            return f'''
    <section class="py-20 px-4 bg-gradient-to-br from-primary to-secondary text-white">
        <div class="max-w-2xl mx-auto text-center">
            <h2 class="text-4xl font-bold mb-4">{section.headline}</h2>
            <p class="text-xl mb-8 opacity-90">{section.subheadline or ''}</p>
            <form class="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
                <input type="email" placeholder="Enter your email" class="flex-1 px-4 py-3 rounded-lg text-gray-900" required>
                <button type="submit" class="bg-white text-primary font-bold px-6 py-3 rounded-lg hover:bg-gray-100 transition">
                    {section.cta_text or 'Subscribe'}
                </button>
            </form>
            {f'<p class="mt-4 text-sm opacity-75">{section.content.get("privacy_note", "")}</p>' if section.content.get("privacy_note") else ''}
        </div>
    </section>
'''
        else:
            return f'''
    <section class="py-16 px-4">
        <div class="max-w-4xl mx-auto">
            <h2 class="text-3xl font-bold mb-4">{section.headline}</h2>
            <p class="text-gray-600">{section.subheadline or ''}</p>
        </div>
    </section>
'''
    
    def to_nextjs_components(self, brand_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Convert landing page content to Next.js components.
        
        Args:
            brand_data: Optional brand colors/fonts to apply
            
        Returns:
            Dictionary of filepath -> file content
        """
        brand = brand_data or {}
        primary_color = brand.get("primary_color", "#3b82f6")
        secondary_color = brand.get("secondary_color", "#10b981")
        font_family = brand.get("font_family", "Inter")
        
        components = {}
        
        # Generate individual section components
        for i, section in enumerate(self.sections):
            component_name = f"{section.section_type.title().replace('_', '')}Section"
            components[f"components/sections/{component_name}.tsx"] = self._generate_section_component(
                section, primary_color, secondary_color, component_name
            )
        
        # Generate main page component
        section_imports = "\n".join([
            f"import {section.section_type.title().replace('_', '')}Section from '@/components/sections/{section.section_type.title().replace('_', '')}Section'"
            for section in self.sections
        ])
        section_renders = "\n      ".join([
            f"<{section.section_type.title().replace('_', '')}Section />"
            for section in self.sections
        ])
        
        components["components/LandingPage.tsx"] = f'''"use client"

import React from 'react'
{section_imports}

export default function LandingPage() {{
  return (
    <div className="min-h-screen bg-white">
      {section_renders}
    </div>
  )
}}
'''
        
        return components
    
    def _generate_section_component(
        self, 
        section: LandingPageSection, 
        primary_color: str, 
        secondary_color: str,
        component_name: str
    ) -> str:
        """Generate a React component for a section."""
        
        content_json = json.dumps(section.content, indent=2)
        
        return f'''"use client"

import React from 'react'
import {{ Button }} from '@/components/ui/button'

// Section content
const content = {content_json}

export default function {component_name}() {{
  return (
    <section className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-4">{section.headline}</h2>
        {f'<p className="text-gray-600 text-center mb-12">{section.subheadline}</p>' if section.subheadline else ''}
        {{/* Section-specific content rendered here */}}
      </div>
    </section>
  )
}}
'''


class LandingPageGenerator:
    """
    Generate landing pages in multiple formats.
    
    Supports:
    - Multiple page types (product, lead capture, event, webinar, coming soon, comparison)
    - HTML + Tailwind CSS
    - React Component
    - Full Next.js Project
    """
    
    # Section recommendations by page type
    PAGE_TYPE_SECTIONS = {
        LandingPageType.PRODUCT: ["hero", "features", "benefits", "social_proof", "testimonials", "pricing", "faq", "cta"],
        LandingPageType.LEAD_CAPTURE: ["hero", "benefits", "social_proof", "email_capture", "testimonials", "faq"],
        LandingPageType.EVENT: ["hero", "countdown", "benefits", "social_proof", "how_it_works", "cta"],
        LandingPageType.WEBINAR: ["hero", "countdown", "benefits", "social_proof", "how_it_works", "email_capture"],
        LandingPageType.COMING_SOON: ["hero", "email_capture", "features", "social_proof"],
        LandingPageType.COMPARISON: ["hero", "comparison", "features", "testimonials", "pricing", "cta"],
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.openrouter = None
        if self.settings.openrouter_api_key:
            self.openrouter = OpenRouterService(
                api_key=self.settings.openrouter_api_key,
                timeout=120.0
            )
    
    async def generate(
        self,
        page_type: LandingPageType,
        product_name: str,
        product_description: str,
        target_audience: str,
        brand_context: Optional[Dict[str, Any]] = None,
        sections_requested: Optional[List[str]] = None,
        key_benefits: Optional[List[str]] = None
    ) -> LandingPageContent:
        """
        Generate a complete landing page.
        
        Args:
            page_type: Type of landing page to generate
            product_name: Name of the product/service
            product_description: Description of the product/service
            target_audience: Target audience description
            brand_context: Brand colors, fonts, voice guidelines
            sections_requested: Specific sections to include (overrides defaults)
            key_benefits: Key benefits to highlight
            
        Returns:
            LandingPageContent with all sections and metadata
        """
        brand_context = brand_context or {}
        brand_voice = brand_context.get("voice", {})
        key_benefits = key_benefits or []
        
        # Determine sections to generate
        if sections_requested:
            section_types = sections_requested
        else:
            section_types = self.PAGE_TYPE_SECTIONS.get(page_type, ["hero", "features", "cta"])
        
        # Generate content for each section
        sections = []
        for section_type in section_types:
            section = await self.generate_section(
                section_type=section_type,
                context={
                    "page_type": page_type.value,
                    "product_name": product_name,
                    "product_description": product_description,
                    "target_audience": target_audience,
                    "key_benefits": key_benefits,
                    "brand_voice": brand_voice
                }
            )
            sections.append(section)
        
        # Generate SEO metadata
        seo_data = await self._generate_seo_metadata(
            page_type=page_type,
            product_name=product_name,
            product_description=product_description,
            target_audience=target_audience,
            key_benefits=key_benefits
        )
        
        return LandingPageContent(
            page_type=page_type,
            title=seo_data.get("title", product_name),
            meta_description=seo_data.get("description", product_description[:160]),
            og_title=seo_data.get("og_title", seo_data.get("title", product_name)),
            og_description=seo_data.get("og_description", seo_data.get("description", product_description[:160])),
            sections=sections,
            keywords=seo_data.get("keywords", []),
            og_image_prompt=seo_data.get("og_image_prompt")
        )
    
    async def generate_section(
        self,
        section_type: str,
        context: Dict[str, Any]
    ) -> LandingPageSection:
        """
        Generate content for a specific section.
        
        Args:
            section_type: Type of section (hero, features, etc.)
            context: Context including product info, audience, brand voice
            
        Returns:
            LandingPageSection with generated content
        """
        if not self.openrouter:
            return self._get_fallback_section(section_type, context)
        
        prompt = self._get_section_prompt(section_type, context)
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an expert conversion copywriter who creates high-converting landing page content. Write compelling, benefit-focused copy that speaks directly to the target audience.",
                temperature=0.7,
                json_mode=True
            )
            
            data = json.loads(response)
            
            return LandingPageSection(
                section_type=section_type,
                headline=data.get("headline", ""),
                subheadline=data.get("subheadline"),
                content=data.get("content", {}),
                cta_text=data.get("cta_text"),
                cta_url=data.get("cta_url"),
                image_prompt=data.get("image_prompt")
            )
            
        except Exception as e:
            logger.error(f"Section generation failed for {section_type}: {e}")
            return self._get_fallback_section(section_type, context)
    
    def _get_section_prompt(self, section_type: str, context: Dict[str, Any]) -> str:
        """Get the prompt for generating a specific section type."""
        
        product_name = context.get("product_name", "Product")
        product_description = context.get("product_description", "")
        target_audience = context.get("target_audience", "")
        key_benefits = context.get("key_benefits", [])
        brand_voice = context.get("brand_voice", {})
        
        voice_guidelines = ""
        if brand_voice:
            voice_guidelines = f"""
Brand Voice Guidelines:
- Tone: {', '.join(brand_voice.get('tone', ['professional']))}
- Personality: {brand_voice.get('personality', '')}
- Key phrases: {', '.join(brand_voice.get('vocabulary', [])[:5])}
"""
        
        base_context = f"""
Product: {product_name}
Description: {product_description}
Target Audience: {target_audience}
Key Benefits: {', '.join(key_benefits[:5])}
{voice_guidelines}
"""
        
        prompts = {
            "hero": f"""
{base_context}

Write a compelling hero section for this landing page.

Return JSON:
{{
    "headline": "Powerful headline (under 10 words) that captures attention",
    "subheadline": "Supporting subheadline (under 25 words) that expands on the value",
    "cta_text": "Primary CTA button text (2-4 words)",
    "content": {{
        "cta_subtext": "Small text under CTA for urgency/trust (optional)"
    }},
    "image_prompt": "Description for hero image generation"
}}
""",
            "features": f"""
{base_context}

Write a features section highlighting 3-4 key features.

Return JSON:
{{
    "headline": "Section headline",
    "subheadline": "Section subheadline",
    "content": {{
        "features": [
            {{
                "title": "Feature title",
                "description": "Feature description (1-2 sentences)",
                "icon": "Relevant emoji"
            }}
        ]
    }}
}}
""",
            "benefits": f"""
{base_context}

Write a benefits section with 4-6 value propositions.

Return JSON:
{{
    "headline": "Section headline",
    "subheadline": "Section subheadline",
    "content": {{
        "benefits": [
            {{
                "title": "Benefit title",
                "description": "How this benefits the user"
            }}
        ]
    }}
}}
""",
            "testimonials": f"""
{base_context}

Write 3 realistic testimonials from satisfied customers.

Return JSON:
{{
    "headline": "Section headline (e.g., 'What Our Customers Say')",
    "content": {{
        "testimonials": [
            {{
                "quote": "Customer testimonial quote",
                "author": "Customer name",
                "title": "Job title, Company"
            }}
        ]
    }}
}}
""",
            "pricing": f"""
{base_context}

Create 3 pricing tiers for this product.

Return JSON:
{{
    "headline": "Section headline",
    "subheadline": "Section subheadline",
    "content": {{
        "tiers": [
            {{
                "name": "Tier name",
                "description": "Brief description",
                "price": "$XX",
                "period": "/mo",
                "features": ["Feature 1", "Feature 2"],
                "cta_text": "Button text",
                "highlighted": false
            }}
        ]
    }}
}}
""",
            "faq": f"""
{base_context}

Write 5-6 frequently asked questions and answers.

Return JSON:
{{
    "headline": "Frequently Asked Questions",
    "content": {{
        "questions": [
            {{
                "question": "Question text",
                "answer": "Answer text"
            }}
        ]
    }}
}}
""",
            "how_it_works": f"""
{base_context}

Explain how the product works in 3-4 simple steps.

Return JSON:
{{
    "headline": "How It Works",
    "subheadline": "Get started in minutes",
    "content": {{
        "steps": [
            {{
                "title": "Step title",
                "description": "Step description"
            }}
        ]
    }}
}}
""",
            "social_proof": f"""
{base_context}

Create social proof content with stats and company logos.

Return JSON:
{{
    "headline": "Trusted by Industry Leaders",
    "content": {{
        "logos": ["Company 1", "Company 2", "Company 3"],
        "stats": [
            {{
                "value": "10K+",
                "label": "Happy Customers"
            }}
        ]
    }}
}}
""",
            "cta": f"""
{base_context}

Write a compelling final call-to-action section.

Return JSON:
{{
    "headline": "Compelling CTA headline",
    "subheadline": "Supporting text that creates urgency",
    "cta_text": "Button text",
    "content": {{
        "guarantee_text": "Risk reversal text (e.g., '30-day money-back guarantee')"
    }}
}}
""",
            "countdown": f"""
{base_context}

Write content for a countdown/urgency section.

Return JSON:
{{
    "headline": "Event/Launch headline",
    "subheadline": "Don't miss out - limited time",
    "cta_text": "Register Now",
    "content": {{
        "event_date": "2024-12-31T00:00:00Z"
    }}
}}
""",
            "comparison": f"""
{base_context}

Create a comparison table showing advantages over competitors.

Return JSON:
{{
    "headline": "See How We Compare",
    "subheadline": "The clear choice for {target_audience}",
    "content": {{
        "comparison": {{
            "our_product": {{
                "name": "{product_name}"
            }},
            "competitors": [
                {{"name": "Competitor A", "key": "comp_a"}},
                {{"name": "Competitor B", "key": "comp_b"}}
            ],
            "features": [
                {{"name": "Feature 1", "us": "✓", "comp_a": "✓", "comp_b": "—"}},
                {{"name": "Feature 2", "us": "✓", "comp_a": "—", "comp_b": "—"}}
            ]
        }}
    }}
}}
""",
            "email_capture": f"""
{base_context}

Write content for an email capture/lead generation section.

Return JSON:
{{
    "headline": "Compelling headline for email signup",
    "subheadline": "What they'll get by signing up",
    "cta_text": "Subscribe",
    "content": {{
        "privacy_note": "We respect your privacy. Unsubscribe anytime."
    }}
}}
"""
        }
        
        return prompts.get(section_type, prompts["hero"])
    
    async def _generate_seo_metadata(
        self,
        page_type: LandingPageType,
        product_name: str,
        product_description: str,
        target_audience: str,
        key_benefits: List[str]
    ) -> Dict[str, Any]:
        """Generate SEO metadata for the landing page."""
        
        if not self.openrouter:
            return {
                "title": f"{product_name} - Best Solution for {target_audience}",
                "description": f"Discover {product_name}. {product_description[:100]}",
                "og_title": f"{product_name} - Transform Your {target_audience.split()[0] if target_audience else 'Business'}",
                "og_description": f"Join thousands who trust {product_name}. {', '.join(key_benefits[:2])}.",
                "keywords": key_benefits[:5] + [product_name.lower()],
                "og_image_prompt": f"Professional marketing image for {product_name}"
            }
        
        prompt = f"""
Generate SEO metadata for this landing page:

Page Type: {page_type.value}
Product: {product_name}
Description: {product_description}
Target Audience: {target_audience}
Key Benefits: {', '.join(key_benefits)}

Return JSON:
{{
    "title": "SEO title (under 60 characters)",
    "description": "Meta description (under 160 characters)",
    "og_title": "Open Graph title (can be slightly different from SEO title)",
    "og_description": "Open Graph description (under 200 characters)",
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "og_image_prompt": "Description for generating an OG image"
}}
"""
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system="You are an SEO expert who creates optimized metadata for landing pages.",
                temperature=0.3,
                json_mode=True
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"SEO metadata generation failed: {e}")
            return {
                "title": product_name,
                "description": product_description[:160],
                "og_title": product_name,
                "og_description": product_description[:200],
                "keywords": key_benefits[:5],
                "og_image_prompt": f"Marketing image for {product_name}"
            }
    
    def _get_fallback_section(self, section_type: str, context: Dict[str, Any]) -> LandingPageSection:
        """Get fallback content for a section when AI is unavailable."""
        
        product_name = context.get("product_name", "Our Product")
        target_audience = context.get("target_audience", "businesses")
        key_benefits = context.get("key_benefits", ["Save time", "Increase efficiency", "Reduce costs"])
        
        fallbacks = {
            "hero": LandingPageSection(
                section_type="hero",
                headline=f"Transform Your Business with {product_name}",
                subheadline=f"The solution that {target_audience} trust for better results.",
                cta_text="Get Started",
                content={"cta_subtext": "No credit card required"},
                image_prompt=f"Professional hero image for {product_name}"
            ),
            "features": LandingPageSection(
                section_type="features",
                headline="Why Choose Us",
                subheadline="Everything you need to succeed",
                content={
                    "features": [
                        {"title": "Easy to Use", "description": "Simple and intuitive interface", "icon": "🚀"},
                        {"title": "Powerful", "description": "Advanced features for professionals", "icon": "⚡"},
                        {"title": "Secure", "description": "Enterprise-grade security", "icon": "🔒"}
                    ]
                }
            ),
            "benefits": LandingPageSection(
                section_type="benefits",
                headline="Benefits That Matter",
                subheadline="See how we can help you succeed",
                content={
                    "benefits": [
                        {"title": benefit, "description": f"Experience the power of {benefit.lower()}"}
                        for benefit in key_benefits[:4]
                    ]
                }
            ),
            "testimonials": LandingPageSection(
                section_type="testimonials",
                headline="What Our Customers Say",
                content={
                    "testimonials": [
                        {"quote": "Amazing product! It has completely transformed how we work.", "author": "Sarah Johnson", "title": "CEO, TechCorp"},
                        {"quote": "The best investment we've made this year.", "author": "Michael Chen", "title": "Director, StartupXYZ"},
                        {"quote": "Highly recommend to anyone looking to scale.", "author": "Emily Davis", "title": "Founder, GrowthCo"}
                    ]
                }
            ),
            "pricing": LandingPageSection(
                section_type="pricing",
                headline="Simple, Transparent Pricing",
                subheadline="Choose the plan that's right for you",
                content={
                    "tiers": [
                        {"name": "Starter", "description": "Perfect for individuals", "price": "$9", "period": "/mo", "features": ["Feature 1", "Feature 2"], "cta_text": "Start Free", "highlighted": False},
                        {"name": "Pro", "description": "Best for growing teams", "price": "$29", "period": "/mo", "features": ["Everything in Starter", "Feature 3", "Feature 4"], "cta_text": "Get Started", "highlighted": True},
                        {"name": "Enterprise", "description": "For large organizations", "price": "Custom", "period": "", "features": ["Everything in Pro", "Feature 5", "Dedicated support"], "cta_text": "Contact Sales", "highlighted": False}
                    ]
                }
            ),
            "faq": LandingPageSection(
                section_type="faq",
                headline="Frequently Asked Questions",
                content={
                    "questions": [
                        {"question": "How do I get started?", "answer": "Simply sign up for a free account and follow our quick setup guide."},
                        {"question": "Is there a free trial?", "answer": "Yes! We offer a 14-day free trial with full access to all features."},
                        {"question": "Can I cancel anytime?", "answer": "Absolutely. No long-term contracts or cancellation fees."},
                        {"question": "Do you offer support?", "answer": "Yes, we provide 24/7 customer support via chat and email."}
                    ]
                }
            ),
            "how_it_works": LandingPageSection(
                section_type="how_it_works",
                headline="How It Works",
                subheadline="Get started in just 3 simple steps",
                content={
                    "steps": [
                        {"title": "Sign Up", "description": "Create your free account in seconds"},
                        {"title": "Configure", "description": "Set up your preferences and integrations"},
                        {"title": "Launch", "description": "Start seeing results immediately"}
                    ]
                }
            ),
            "social_proof": LandingPageSection(
                section_type="social_proof",
                headline="Trusted by Industry Leaders",
                content={
                    "logos": ["TechCorp", "StartupXYZ", "GrowthCo", "InnovateLabs"],
                    "stats": [
                        {"value": "10K+", "label": "Happy Customers"},
                        {"value": "99.9%", "label": "Uptime"},
                        {"value": "24/7", "label": "Support"}
                    ]
                }
            ),
            "cta": LandingPageSection(
                section_type="cta",
                headline="Ready to Get Started?",
                subheadline="Join thousands of satisfied customers today.",
                cta_text="Start Free Trial",
                content={"guarantee_text": "30-day money-back guarantee"}
            ),
            "countdown": LandingPageSection(
                section_type="countdown",
                headline="Don't Miss Out",
                subheadline="Limited time offer ends soon",
                cta_text="Register Now"
            ),
            "comparison": LandingPageSection(
                section_type="comparison",
                headline="See How We Compare",
                subheadline="The clear choice for your needs",
                content={
                    "comparison": {
                        "our_product": {"name": product_name},
                        "competitors": [{"name": "Competitor A", "key": "comp_a"}, {"name": "Competitor B", "key": "comp_b"}],
                        "features": [
                            {"name": "Feature 1", "us": "✓", "comp_a": "✓", "comp_b": "—"},
                            {"name": "Feature 2", "us": "✓", "comp_a": "—", "comp_b": "—"},
                            {"name": "Feature 3", "us": "✓", "comp_a": "—", "comp_b": "✓"}
                        ]
                    }
                }
            ),
            "email_capture": LandingPageSection(
                section_type="email_capture",
                headline="Stay Updated",
                subheadline="Get the latest news and updates delivered to your inbox",
                cta_text="Subscribe",
                content={"privacy_note": "We respect your privacy. Unsubscribe anytime."}
            )
        }
        
        return fallbacks.get(section_type, LandingPageSection(
            section_type=section_type,
            headline=section_type.replace('_', ' ').title()
        ))


# Convenience function for backward compatibility
async def generate_landing_page(
    goal: str,
    target_audience: str,
    key_benefits: List[str],
    brand_data: Dict[str, Any],
    page_type: Optional[LandingPageType] = None,
    **kwargs
) -> LandingPageContent:
    """
    Generate a landing page (backward compatible function).
    
    Args:
        goal: Campaign goal (used as product description)
        target_audience: Target audience description
        key_benefits: Key benefits to highlight
        brand_data: Brand colors, fonts, etc.
        page_type: Type of landing page (defaults to PRODUCT)
        
    Returns:
        LandingPageContent with all sections and metadata
    """
    generator = LandingPageGenerator()
    return await generator.generate(
        page_type=page_type or LandingPageType.PRODUCT,
        product_name=kwargs.get("product_name", "Product"),
        product_description=goal,
        target_audience=target_audience,
        brand_context={"colors": brand_data, "voice": kwargs.get("brand_voice")},
        key_benefits=key_benefits,
        sections_requested=kwargs.get("sections_requested")
    )
