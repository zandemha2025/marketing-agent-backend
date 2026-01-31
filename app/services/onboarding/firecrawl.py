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
        max_pages: int = 50,
        on_progress: Optional[callable] = None
    ) -> CrawlResult:
        """
        Crawl an entire website and extract all relevant data.

        Args:
            domain: The domain to crawl (e.g., "acme.com")
            max_pages: Maximum number of pages to crawl
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
            await on_progress("crawling", 0.0, f"Starting crawl of {base_domain}")

        result = CrawlResult(domain=parsed.netloc)

        # Try Firecrawl API first
        if self.api_key:
            try:
                result = await self._crawl_with_firecrawl(
                    base_domain, max_pages, on_progress
                )
            except Exception as e:
                logger.warning(f"Firecrawl API failed, falling back to basic scraping: {e}")
                result = await self._crawl_basic(base_domain, max_pages, on_progress)
        else:
            # Fallback to basic scraping for development
            result = await self._crawl_basic(base_domain, max_pages, on_progress)

        # Extract brand elements from crawled data
        if on_progress:
            await on_progress("analyzing", 0.8, "Extracting brand elements")

        result.brand_elements = await self._extract_brand_elements(result.pages)
        result.site_structure = self._analyze_site_structure(result.pages)

        result.crawl_time = (datetime.now() - start_time).total_seconds()
        result.pages_crawled = len(result.pages)

        if on_progress:
            await on_progress("crawling", 1.0, f"Crawled {result.pages_crawled} pages")

        return result

    async def _crawl_with_firecrawl(
        self,
        base_url: str,
        max_pages: int,
        on_progress: Optional[callable]
    ) -> CrawlResult:
        """Use Firecrawl API for comprehensive crawling."""
        result = CrawlResult(domain=urlparse(base_url).netloc)

        # Start crawl job
        response = await self.client.post(
            f"{self.base_url}/crawl",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "url": base_url,
                "limit": max_pages,
                "scrapeOptions": {
                    "formats": ["markdown", "html"],
                    "includeTags": ["title", "meta", "h1", "h2", "h3", "p", "a", "img"],
                    "excludeTags": ["script", "style", "nav", "footer"],
                    "headers": {
                        "Accept-Language": "en-US,en;q=0.9"  # Force English content
                    }
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
                await on_progress(
                    "crawling",
                    progress * 0.7,  # Reserve 30% for analysis
                    f"Crawled {status_data.get('completed', 0)} pages"
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

    async def _crawl_basic(
        self,
        base_url: str,
        max_pages: int,
        on_progress: Optional[callable]
    ) -> CrawlResult:
        """Basic fallback crawling without Firecrawl API."""
        result = CrawlResult(domain=urlparse(base_url).netloc)
        visited = set()
        to_visit = [base_url]

        while to_visit and len(result.pages) < max_pages:
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
                        progress = len(result.pages) / max_pages
                        await on_progress(
                            "crawling",
                            progress * 0.7,
                            f"Crawled {len(result.pages)} pages"
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
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass  # Invalid JSON-LD, skip

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
        """Extract brand elements from crawled pages."""
        brand = {
            "colors": [],
            "fonts": [],
            "logo_candidates": [],
            "tagline_candidates": [],
            "tone_indicators": [],
            "key_phrases": []
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

        # Analyze content for key phrases (most common meaningful phrases)
        combined_content = " ".join(all_content)
        brand["key_phrases"] = self._extract_key_phrases(combined_content)

        return brand

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
