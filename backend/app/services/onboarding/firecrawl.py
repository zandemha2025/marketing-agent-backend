"""
Firecrawl integration for deep website analysis.

Firecrawl is used to:
1. Crawl the client's entire website (50+ pages)
2. Extract text content, images, metadata
3. Identify brand elements (colors, fonts, logos)
4. Map site structure and navigation
5. Gather all product/service information
"""
import asyncio
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

import logging

logger = logging.getLogger(__name__)


@dataclass
class PageData:
    """Data extracted from a single page."""
    url: str
    title: str
    description: str
    content: str
    headings: List[str]
    links: List[str]
    images: List[Dict[str, str]]
    meta_tags: Dict[str, str]
    structured_data: Dict[str, Any]
    page_type: str  # home, about, product, blog, contact, etc.


@dataclass
class CrawlResult:
    """Complete result from crawling a website."""
    domain: str
    pages: List[PageData] = field(default_factory=list)
    brand_elements: Dict[str, Any] = field(default_factory=dict)
    site_structure: Dict[str, Any] = field(default_factory=dict)
    products: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    crawl_time: float = 0.0
    pages_crawled: int = 0


class FirecrawlService:
    """
    Deep website analysis using Firecrawl API.

    For development/testing, we also include a fallback
    that does basic scraping if Firecrawl isn't available.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.firecrawl.dev/v1"
    ):
        self.api_key = api_key
        self.base_url = base_url
        # Explicitly disable proxy to avoid SOCKS proxy issues in sandboxed environments
        self.client = httpx.AsyncClient(timeout=60.0, proxy=None)

    async def crawl_website(
        self,
        domain: str,
        max_pages: int = 100,  # Increased from 50 for deeper research
        on_progress: Optional[callable] = None
    ) -> CrawlResult:
        """
        Crawl an entire website using strategic prioritization for brand DNA extraction.
        
        Uses smart sampling to prioritize high-value pages while still getting comprehensive coverage.
        
        Args:
            domain: The domain to crawl (e.g., "acme.com")
            max_pages: Maximum number of pages to crawl (increased for deeper research)
            on_progress: Callback for progress updates (stage, progress, message)

        Returns:
            CrawlResult with all extracted data
        """
        start_time = datetime.now()

        # Normalize domain
        if not domain.startswith("http"):
            domain = f"https://{domain}"

        parsed = urlparse(domain)
        hostname = parsed.netloc

        # Strip country-specific subdomains (e.g., nl.stripe.com -> stripe.com)
        # to ensure we get the main/English version
        parts = hostname.split(".")
        if len(parts) > 2:
            # Check if first part is a 2-letter country code
            if len(parts[0]) == 2 and parts[0].isalpha() and parts[0].lower() not in ["go", "my", "co"]:
                hostname = ".".join(parts[1:])
                logger.info(f"Stripped country subdomain: {parsed.netloc} -> {hostname}")

        base_domain = f"{parsed.scheme}://{hostname}"

        if on_progress:
            # Handle both sync and async callbacks
            import asyncio
            if asyncio.iscoroutinefunction(on_progress):
                await on_progress("crawling", 0.0, f"Starting strategic crawl of {base_domain}")
            else:
                on_progress("crawling", 0.0, f"Starting strategic crawl of {base_domain}")

        result = CrawlResult(domain=parsed.netloc)

        # Try Firecrawl API first with enhanced settings
        if self.api_key:
            try:
                result = await self._crawl_with_firecrawl_strategic(
                    base_domain, max_pages, on_progress
                )
            except Exception as e:
                logger.warning(f"Firecrawl API failed, falling back to basic scraping: {e}")
                result = await self._crawl_basic_strategic(base_domain, max_pages, on_progress)
        else:
            # Fallback to basic scraping for development
            result = await self._crawl_basic_strategic(base_domain, max_pages, on_progress)

        # Extract brand elements from crawled data
        if on_progress:
            import asyncio
            if asyncio.iscoroutinefunction(on_progress):
                await on_progress("analyzing", 0.8, "Extracting brand elements")
            else:
                on_progress("analyzing", 0.8, "Extracting brand elements")

        result.brand_elements = await self._extract_brand_elements(result.pages)
        result.site_structure = self._analyze_site_structure(result.pages)
        result.products = self.extract_products_from_pages(result.pages)

        result.crawl_time = (datetime.now() - start_time).total_seconds()
        result.pages_crawled = len(result.pages)

        if on_progress:
            import asyncio
            if asyncio.iscoroutinefunction(on_progress):
                await on_progress("crawling", 1.0, f"Strategic crawl complete: {result.pages_crawled} pages analyzed")
            else:
                on_progress("crawling", 1.0, f"Strategic crawl complete: {result.pages_crawled} pages analyzed")

        return result

    async def _crawl_with_firecrawl_strategic(
        self,
        base_url: str,
        max_pages: int,
        on_progress: Optional[callable]
    ) -> CrawlResult:
        """Use Firecrawl API with strategic prioritization for brand DNA extraction."""
        result = CrawlResult(domain=urlparse(base_url).netloc)

        # Start crawl job with enhanced settings for brand research
        response = await self.client.post(
            f"{self.base_url}/crawl",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "url": base_url,
                "limit": max_pages,
                "scrapeOptions": {
                    "formats": ["markdown", "html"],
                    "includeTags": ["title", "meta", "h1", "h2", "h3", "h4", "p", "a", "img", "nav", "header", "footer"],
                    "excludeTags": ["script", "style"],
                    "headers": {
                        "Accept-Language": "en-US,en;q=0.9"  # Force English content
                    }
                },
                # Enhanced crawler options for strategic crawling
                "crawlerOptions": {
                    "maxDepth": 4,  # Deeper crawl for comprehensive research
                    "limit": max_pages,
                    "includePaths": [  # Prioritize these paths
                        "/about", "/about-us", "/company", "/our-story",
                        "/products", "/collections", "/shop", "/store",
                        "/history", "/heritage", "/mission", "/values",
                        "/press", "/news", "/media", "/investors",
                        "/careers", "/team", "/leadership"
                    ],
                    "excludePaths": [  # Exclude low-value paths
                        "/cart", "/checkout", "/account", "/login",
                        "/privacy", "/terms", "/legal", "/cookie"
                    ]
                }
            }
        )
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data.get("id")

        if not job_id:
            raise ValueError("No job ID returned from Firecrawl")

        # Poll for completion
        while True:
            status_response = await self.client.get(
                f"{self.base_url}/crawl/{job_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            status_response.raise_for_status()
            status_data = status_response.json()

            status = status_data.get("status")
            progress = status_data.get("completed", 0) / max(status_data.get("total", 1), 1)

            if on_progress:
                import asyncio
                if asyncio.iscoroutinefunction(on_progress):
                    await on_progress(
                        "crawling",
                        progress * 0.7,  # Reserve 30% for analysis
                        f"Strategic crawl: {status_data.get('completed', 0)} pages"
                    )
                else:
                    on_progress(
                        "crawling",
                        progress * 0.7,
                        f"Strategic crawl: {status_data.get('completed', 0)} pages"
                    )

            if status == "completed":
                # Process results
                for page_data in status_data.get("data", []):
                    page = self._parse_firecrawl_page(page_data)
                    if page:
                        result.pages.append(page)
                break
            elif status == "failed":
                raise Exception(f"Crawl failed: {status_data.get('error')}")

            await asyncio.sleep(2)

        return result

    def _parse_firecrawl_page(self, data: Dict[str, Any]) -> Optional[PageData]:
        """Parse Firecrawl page data into our PageData format."""
        try:
            metadata = data.get("metadata", {})
            return PageData(
                url=data.get("url", ""),
                title=metadata.get("title", ""),
                description=metadata.get("description", ""),
                content=data.get("markdown", data.get("content", "")),
                headings=self._extract_headings_from_html(data.get("html", "")),
                links=data.get("links", []),
                images=self._extract_images_from_html(data.get("html", "")),
                meta_tags=metadata,
                structured_data=data.get("structuredData", {}),
                page_type=self._classify_page_type(data.get("url", ""), metadata)
            )
        except Exception as e:
            logger.error(f"Error parsing Firecrawl page: {e}")
            return None

    async def _crawl_basic_strategic(
        self,
        base_url: str,
        max_pages: int,
        on_progress: Optional[callable]
    ) -> CrawlResult:
        """Basic fallback crawling with strategic prioritization for brand DNA extraction."""
        result = CrawlResult(domain=urlparse(base_url).netloc)
        visited = set()
        to_visit = [base_url]
        
        # Priority scoring for strategic crawling
        priority_keywords = [
            'about', 'company', 'story', 'mission', 'values', 'history', 'heritage',
            'products', 'collections', 'shop', 'store', 'catalog',
            'press', 'news', 'media', 'investors', 'careers'
        ]

        while to_visit and len(result.pages) < max_pages:
            # Sort by priority (pages with strategic keywords first)
            to_visit.sort(key=lambda url: sum(1 for keyword in priority_keywords if keyword in url.lower()), reverse=True)
            
            url = to_visit.pop(0)

            if url in visited:
                continue

            visited.add(url)

            try:
                page = await self._scrape_page(url, base_url)
                if page:
                    result.pages.append(page)

                    # Add new links to crawl queue
                    for link in page.links:
                        if link not in visited and link.startswith(base_url):
                            to_visit.append(link)

                    if on_progress:
                        import asyncio
                        progress = len(result.pages) / max_pages
                        if asyncio.iscoroutinefunction(on_progress):
                            await on_progress(
                                "crawling",
                                progress * 0.7,
                                f"Strategic crawl: {len(result.pages)} pages"
                            )
                        else:
                            on_progress(
                                "crawling",
                                progress * 0.7,
                                f"Strategic crawl: {len(result.pages)} pages"
                            )

            except Exception as e:
                result.errors.append({"url": url, "error": str(e)})
                logger.warning(f"Error crawling {url}: {e}")

        return result

    async def _scrape_page(self, url: str, base_url: str) -> Optional[PageData]:
        """Scrape a single page."""
        try:
            response = await self.client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; MarketingAgent/1.0)",
                    "Accept-Language": "en-US,en;q=0.9",  # Force English content
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                follow_redirects=True
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Extract description
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")

            # Extract main content
            content = self._extract_main_content(soup)

            # Extract headings
            headings = []
            for tag in ["h1", "h2", "h3"]:
                for heading in soup.find_all(tag):
                    headings.append(heading.get_text(strip=True))

            # Extract links
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                full_url = urljoin(base_url, href)
                if full_url.startswith(base_url):
                    links.append(full_url)

            # Extract images
            images = []
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src:
                    images.append({
                        "src": urljoin(base_url, src),
                        "alt": img.get("alt", ""),
                        "title": img.get("title", "")
                    })

            # Extract meta tags
            meta_tags = {}
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property", "")
                content_val = meta.get("content", "")
                if name and content_val:
                    meta_tags[name] = content_val

            # Extract structured data (JSON-LD)
            structured_data = {}
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    import json
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        structured_data.update(data)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                structured_data.update(item)
                except (json.JSONDecodeError, TypeError, AttributeError) as e:
                    logger.debug(f"Failed to parse JSON-LD from {url}: {e}")

            return PageData(
                url=url,
                title=title,
                description=description,
                content=content,
                headings=headings,
                links=list(set(links)),
                images=images,
                meta_tags=meta_tags,
                structured_data=structured_data,
                page_type=self._classify_page_type(url, meta_tags)
            )

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main text content from a page."""
        # Remove script, style, nav, footer elements
        for element in soup.find_all(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Try to find main content area
        main = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|main", re.I))

        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else ""

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    def _extract_headings_from_html(self, html: str) -> List[str]:
        """Extract headings from HTML string."""
        soup = BeautifulSoup(html, "html.parser")
        headings = []
        for tag in ["h1", "h2", "h3"]:
            for heading in soup.find_all(tag):
                headings.append(heading.get_text(strip=True))
        return headings

    def _extract_images_from_html(self, html: str) -> List[Dict[str, str]]:
        """Extract images from HTML string."""
        soup = BeautifulSoup(html, "html.parser")
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                images.append({
                    "src": src,
                    "alt": img.get("alt", ""),
                    "title": img.get("title", "")
                })
        return images

    def _classify_page_type(self, url: str, meta_tags: Dict[str, str]) -> str:
        """Classify the type of page based on URL and metadata."""
        url_lower = url.lower()

        # Check URL patterns
        patterns = {
            "home": [r"/$", r"/index", r"/home"],
            "about": [r"/about", r"/company", r"/team", r"/our-story"],
            "product": [r"/product", r"/service", r"/solution", r"/feature"],
            "pricing": [r"/pricing", r"/plans", r"/packages"],
            "blog": [r"/blog", r"/article", r"/news", r"/post"],
            "contact": [r"/contact", r"/support", r"/help"],
            "legal": [r"/privacy", r"/terms", r"/legal", r"/cookie"],
            "careers": [r"/careers", r"/jobs", r"/hiring"],
        }

        for page_type, url_patterns in patterns.items():
            for pattern in url_patterns:
                if re.search(pattern, url_lower):
                    return page_type

        # Check Open Graph type
        og_type = meta_tags.get("og:type", "")
        if og_type:
            if "product" in og_type.lower():
                return "product"
            if "article" in og_type.lower():
                return "blog"

        return "other"

    async def _extract_brand_elements(self, pages: List[PageData]) -> Dict[str, Any]:
        """Extract brand elements from crawled pages using intelligent analysis."""
        brand = {
            "colors": [],
            "fonts": [],
            "logo_candidates": [],
            "tagline_candidates": [],
            "tone_indicators": [],
            "key_phrases": [],
            "brand_voice": "",
            "core_values": []
        }

        all_images = []
        all_content = []

        for page in pages:
            all_images.extend(page.images)
            all_content.append(page.content)

            # Look for logo in images
            for img in page.images:
                alt_lower = img.get("alt", "").lower()
                src_lower = img.get("src", "").lower()
                if "logo" in alt_lower or "logo" in src_lower:
                    brand["logo_candidates"].append(img["src"])

            # Extract potential taglines from structured data
            if page.structured_data.get("slogan"):
                brand["tagline_candidates"].append(page.structured_data["slogan"])

            # Extract from meta tags
            if page.meta_tags.get("og:site_name"):
                brand["site_name"] = page.meta_tags["og:site_name"]

        # Use intelligent analysis instead of word counting
        combined_content = " ".join(all_content)
        brand_analysis = self._analyze_brand_intelligence(combined_content)
        
        brand["key_phrases"] = brand_analysis.get("key_phrases", [])
        brand["brand_voice"] = brand_analysis.get("brand_voice", "")
        brand["core_values"] = brand_analysis.get("core_values", [])
        brand["tone_indicators"] = brand_analysis.get("tone_indicators", [])

        return brand

    def _analyze_brand_intelligence(self, text: str) -> Dict[str, Any]:
        """Intelligent brand analysis using content patterns."""
        # Look for brand voice indicators in content
        voice_indicators = {
            "inspirational": ["just do it", "achieve", "inspire", "dream", "believe", "never give up"],
            "professional": ["enterprise", "solution", "optimize", "streamline", "efficiency", "ROI"],
            "casual": ["hey", "let's", "you'll love", "awesome", "cool", "amazing"],
            "luxury": ["premium", "exclusive", "sophisticated", "elegant", "refined", "crafted"],
            "athletic": ["performance", "training", "athlete", "competition", "sport", "fitness"]
        }
        
        text_lower = text.lower()
        detected_voice = []
        
        for voice, indicators in voice_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            if score >= 2:
                detected_voice.append(voice)
        
        # Look for brand values
        value_indicators = {
            "innovation": ["innovative", "cutting-edge", "revolutionary", "breakthrough"],
            "quality": ["premium", "high-quality", "durable", "crafted", "excellence"],
            "authenticity": ["authentic", "genuine", "real", "original"],
            "sustainability": ["sustainable", "eco-friendly", "green", "environmental"],
            "performance": ["performance", "efficiency", "powerful", "effective"]
        }
        
        detected_values = []
        for value, indicators in value_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                detected_values.append(value)
        
        # Extract meaningful phrases (improved from simple word counting)
        meaningful_phrases = []
        
        # Look for slogans and taglines
        slogan_patterns = [
            r'"([^"]{10,80})"',  # Quoted phrases
            r'“([^”]{10,80})”',  # Smart quotes
            r'([A-Z][^.]{10,80})\.',  # Sentences that might be slogans
        ]
        
        import re
        for pattern in slogan_patterns:
            matches = re.findall(pattern, text)
            meaningful_phrases.extend(matches[:3])  # Take top 3
        
        # Look for repeated phrases or concepts
        if len(text) > 1000:  # Only if we have enough content
            words = text_lower.split()
            word_freq = {}
            for word in words:
                if len(word) > 4 and word.isalpha():
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get words that appear frequently but aren't common
            common_words = {'their', 'there', 'where', 'would', 'could', 'should', 'about', 'other', 'which', 'these', 'those'}
            frequent_meaningful = [word for word, count in word_freq.items() 
                                 if count >= 3 and word not in common_words][:10]
            meaningful_phrases.extend(frequent_meaningful)
        
        return {
            "key_phrases": meaningful_phrases[:10],
            "brand_voice": ", ".join(detected_voice) if detected_voice else "professional",
            "core_values": detected_values[:5],
            "tone_indicators": detected_voice
        }

    def _extract_key_phrases(self, text: str, top_n: int = 10) -> List[str]:
        """Extract frequently used meaningful phrases."""
        # Simple extraction - in production, use NLP
        words = re.findall(r'\b[A-Za-z]{4,}\b', text.lower())

        # Count word frequency
        from collections import Counter
        word_counts = Counter(words)

        # Filter out common words
        stop_words = {
            "that", "this", "with", "from", "have", "been", "will",
            "they", "their", "about", "which", "when", "there", "what",
            "more", "your", "also", "some", "into", "other", "than"
        }

        filtered = [
            (word, count) for word, count in word_counts.most_common(50)
            if word not in stop_words
        ]

        return [word for word, count in filtered[:top_n]]

    def _analyze_site_structure(self, pages: List[PageData]) -> Dict[str, Any]:
        """Analyze the structure of the website."""
        structure = {
            "page_types": {},
            "total_pages": len(pages),
            "navigation": [],
            "content_areas": []
        }

        # Count page types
        for page in pages:
            page_type = page.page_type
            if page_type not in structure["page_types"]:
                structure["page_types"][page_type] = 0
            structure["page_types"][page_type] += 1

        # Identify main content areas based on page types
        if structure["page_types"].get("product", 0) > 0:
            structure["content_areas"].append("products")
        if structure["page_types"].get("blog", 0) > 0:
            structure["content_areas"].append("blog")
        if structure["page_types"].get("pricing", 0) > 0:
            structure["content_areas"].append("pricing")

        return structure

    def extract_products_from_pages(self, pages: List[PageData]) -> List[Dict[str, Any]]:
        """Extract products/services from crawled pages using content analysis."""
        products = []
        
        # First, use content analysis to identify product pages
        for page in pages:
            # Skip pages that are clearly not product pages (navigation, legal, etc.)
            if any(keyword in page.url.lower() for keyword in ['privacy', 'terms', 'cookie', 'legal', 'sitemap']):
                continue
                
            # Analyze content to determine if this is a product page
            product_info = self._analyze_page_for_products(page)
            if product_info:
                products.append(product_info)

        # Also look at structured data (JSON-LD) - this is reliable
        for page in pages:
            structured_data = page.structured_data
            if structured_data.get('@type') in ['Product', 'Service', 'SoftwareApplication']:
                products.append({
                    "name": structured_data.get('name'),
                    "description": structured_data.get('description'),
                    "features": structured_data.get('features', []),
                    "url": page.url
                })

        # Remove duplicates based on name
        unique_products = {}
        for p in products:
            if p["name"] and p["name"] not in unique_products:
                unique_products[p["name"]] = p
        
        return list(unique_products.values())

    def _analyze_page_for_products(self, page: PageData) -> Optional[Dict[str, Any]]:
        """Analyze page content to determine if it describes a product."""
        # Simple heuristic analysis for now - will enhance with LLM later
        content_lower = page.content.lower()
        title_lower = page.title.lower()
        
        # Product indicators in content
        product_indicators = [
            'buy now', 'add to cart', 'purchase', 'price', 'available in',
            'sizes', 'colors', 'material', 'features', 'specifications'
        ]
        
        # Skip if this looks like a blog post or news article
        blog_indicators = ['blog', 'news', 'article', 'post', 'published', 'author']
        if any(indicator in page.url.lower() or title_lower for indicator in blog_indicators):
            return None
            
        # Check if this has product-like content
        product_score = 0
        for indicator in product_indicators:
            if indicator in content_lower:
                product_score += 1
                
        # Check title for product-like patterns
        if any(word in title_lower for word in ['shoe', 'sneaker', 'apparel', 'clothing', 'accessory']):
            product_score += 2
            
        # If it has strong product indicators, extract info
        if product_score >= 2:
            return {
                "name": self._extract_product_name(page),
                "description": self._extract_first_paragraph(page.content) or page.description,
                "features": self._extract_features_from_content(page.content),
                "url": page.url
            }
            
        return None

    def _extract_product_name(self, page: PageData) -> str:
        """Extract product name from page title or h1."""
        # Try H1 first
        soup = BeautifulSoup(page.content, "html.parser") # Note: content is markdown/text usually, but might contain HTML artifacts or we should use headings
        
        # Use extracted headings
        if page.headings:
            return page.headings[0]
            
        # Fallback to title
        if page.title:
            # Remove common suffixes like " | Company Name"
            return page.title.split('|')[0].split('-')[0].strip()
            
        return ""

    def _extract_first_paragraph(self, content: str) -> str:
        """Extract first meaningful paragraph."""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 50:
                return line
        return ""

    def _extract_features_from_content(self, content: str) -> List[str]:
        """Extract bullet points that look like features."""
        features = []
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('-', '*', '•')):
                feature = line.lstrip('-*• ').strip()
                if 10 < len(feature) < 100:
                    features.append(feature)
        return features[:5]  # Limit to top 5 features

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Convenience function for simple usage
async def crawl_website(
    domain: str,
    api_key: Optional[str] = None,
    max_pages: int = 50,
    on_progress: Optional[callable] = None
) -> CrawlResult:
    """
    Crawl a website and extract all relevant data.

    Args:
        domain: The domain to crawl
        api_key: Firecrawl API key (optional, falls back to basic scraping)
        max_pages: Maximum pages to crawl
        on_progress: Progress callback

    Returns:
        CrawlResult with all extracted data
    """
    service = FirecrawlService(api_key=api_key)
    try:
        return await service.crawl_website(domain, max_pages, on_progress)
    finally:
        await service.close()
