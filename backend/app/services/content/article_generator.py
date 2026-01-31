"""
Article Generator Service

Generates multiple content formats from a single interview:
- Blog articles
- Thought leadership pieces
- Case studies
- LinkedIn posts
- Twitter threads
- Press releases
- Email newsletters

Features:
- SEO optimization (meta descriptions, keywords)
- Brand voice integration
- Multiple output formats (HTML, Markdown)
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import re
import html

from ..ai.openrouter import OpenRouterService
from .interview_processor import ProcessedInterview, Quote, Theme
from ...core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """A generated article with SEO optimization and multiple output formats."""
    title: str
    subtitle: str
    content: str
    meta_description: str
    keywords: List[str] = field(default_factory=list)
    word_count: int = 0
    reading_time: int = 0  # minutes
    
    # Extended fields
    format_type: str = "blog"  # blog, thought_leadership, case_study
    author: str = ""
    featured_quotes: List[str] = field(default_factory=list)
    sections: List[Dict[str, str]] = field(default_factory=list)
    call_to_action: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_html(self) -> str:
        """Convert article to HTML format."""
        # Escape content for HTML safety
        safe_title = html.escape(self.title)
        safe_subtitle = html.escape(self.subtitle)
        
        # Convert markdown-style content to HTML
        html_content = self._markdown_to_html(self.content)
        
        # Build featured quotes HTML
        quotes_html = ""
        if self.featured_quotes:
            quotes_html = '<div class="featured-quotes">\n'
            for quote in self.featured_quotes:
                safe_quote = html.escape(quote)
                quotes_html += f'  <blockquote class="pull-quote">{safe_quote}</blockquote>\n'
            quotes_html += '</div>\n'
        
        # Build keywords meta tag
        keywords_meta = ""
        if self.keywords:
            keywords_meta = f'<meta name="keywords" content="{", ".join(self.keywords)}">'
        
        # Build the full HTML document
        html_doc = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{html.escape(self.meta_description)}">
    {keywords_meta}
    <title>{safe_title}</title>
    <style>
        article {{
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
        }}
        h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        .subtitle {{ font-size: 1.25rem; color: #666; margin-bottom: 1rem; }}
        .meta {{ color: #888; font-size: 0.9rem; margin-bottom: 2rem; }}
        .pull-quote {{
            border-left: 4px solid #007bff;
            padding-left: 1rem;
            margin: 2rem 0;
            font-style: italic;
            font-size: 1.1rem;
        }}
        .cta {{
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            margin-top: 2rem;
        }}
    </style>
</head>
<body>
    <article>
        <header>
            <h1>{safe_title}</h1>
            <p class="subtitle">{safe_subtitle}</p>
            <p class="meta">
                {f'By {html.escape(self.author)} • ' if self.author else ''}
                {self.reading_time} min read • {self.word_count} words
            </p>
        </header>
        
        <main>
            {html_content}
            {quotes_html}
        </main>
        
        {f'<div class="cta">{html.escape(self.call_to_action)}</div>' if self.call_to_action else ''}
    </article>
</body>
</html>'''
        
        return html_doc
    
    def to_markdown(self) -> str:
        """Convert article to Markdown format."""
        # Build frontmatter
        frontmatter = f'''---
title: "{self.title}"
subtitle: "{self.subtitle}"
description: "{self.meta_description}"
keywords: [{", ".join(f'"{k}"' for k in self.keywords)}]
author: "{self.author}"
reading_time: {self.reading_time}
word_count: {self.word_count}
date: "{self.created_at.strftime('%Y-%m-%d')}"
---

'''
        
        # Build main content
        markdown = frontmatter
        markdown += f"# {self.title}\n\n"
        
        if self.subtitle:
            markdown += f"*{self.subtitle}*\n\n"
        
        markdown += f"**{self.reading_time} min read** | {self.word_count} words"
        if self.author:
            markdown += f" | By {self.author}"
        markdown += "\n\n---\n\n"
        
        # Add main content
        markdown += self.content + "\n\n"
        
        # Add featured quotes
        if self.featured_quotes:
            markdown += "## Key Quotes\n\n"
            for quote in self.featured_quotes:
                markdown += f"> {quote}\n\n"
        
        # Add call to action
        if self.call_to_action:
            markdown += f"---\n\n**{self.call_to_action}**\n"
        
        return markdown
    
    def _markdown_to_html(self, text: str) -> str:
        """Convert basic markdown to HTML."""
        # Headers
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # Bold and italic
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        
        # Links
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
        
        # Blockquotes
        text = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)
        
        # Lists
        text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', text)
        
        # Paragraphs
        paragraphs = text.split('\n\n')
        processed = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('<'):
                p = f'<p>{p}</p>'
            processed.append(p)
        
        return '\n'.join(processed)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "content": self.content,
            "meta_description": self.meta_description,
            "keywords": self.keywords,
            "word_count": self.word_count,
            "reading_time": self.reading_time,
            "format_type": self.format_type,
            "author": self.author,
            "featured_quotes": self.featured_quotes,
            "sections": self.sections,
            "call_to_action": self.call_to_action,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class GeneratedContent:
    """A piece of generated content (for backward compatibility)."""
    format: str  # "blog", "linkedin", "twitter", "press_release", "email"
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    estimated_read_time: int = 0  # minutes
    suggested_hashtags: List[str] = field(default_factory=list)
    key_takeaways: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.format,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "word_count": self.word_count,
            "estimated_read_time": self.estimated_read_time,
            "suggested_hashtags": self.suggested_hashtags,
            "key_takeaways": self.key_takeaways
        }


class ArticleGenerator:
    """
    Generate multiple content formats from interviews.
    
    Supports:
    - Blog articles (long-form)
    - Thought leadership pieces (expert positioning)
    - Case studies (success stories)
    - LinkedIn posts (professional social)
    - Twitter threads (short-form social)
    - Press releases (formal announcement)
    - Email newsletters (direct communication)
    
    Features:
    - SEO optimization (meta descriptions, keywords)
    - Brand voice integration
    - Multiple output formats (HTML, Markdown)
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.openrouter = None
        if self.settings.openrouter_api_key:
            self.openrouter = OpenRouterService(
                api_key=self.settings.openrouter_api_key,
                timeout=120.0
            )
    
    async def generate_from_interview(
        self,
        processed_interview: ProcessedInterview,
        article_type: str,
        brand_context: Optional[Dict] = None
    ) -> Article:
        """
        Generate article from processed interview.
        
        Args:
            processed_interview: The processed interview data
            article_type: Type of article (blog, thought_leadership, case_study)
            brand_context: Optional brand voice and context
            
        Returns:
            Article object with SEO optimization
        """
        generators = {
            "blog": self.generate_blog_post,
            "thought_leadership": self.generate_thought_leadership,
            "case_study": self.generate_case_study
        }
        
        generator = generators.get(article_type)
        if not generator:
            raise ValueError(f"Unknown article type: {article_type}. Use: blog, thought_leadership, case_study")
        
        # Extract relevant content from interview
        content = processed_interview.summary
        if processed_interview.key_insights:
            content += "\n\nKey Insights:\n" + "\n".join(f"- {i}" for i in processed_interview.key_insights)
        
        # Get topic/expert info
        topic = processed_interview.themes[0].name if processed_interview.themes else processed_interview.title
        expert = processed_interview.speakers[0] if processed_interview.speakers else "Industry Expert"
        company = brand_context.get("company_name", "the company") if brand_context else "the company"
        
        # Generate based on type
        if article_type == "blog":
            return await generator(content, topic, brand_context)
        elif article_type == "thought_leadership":
            return await generator(content, expert, brand_context)
        elif article_type == "case_study":
            return await generator(content, company, brand_context)
        
        return await generator(content, topic, brand_context)
    
    async def generate_blog_post(
        self,
        content: str,
        topic: str,
        brand_context: Optional[Dict] = None
    ) -> Article:
        """
        Generate blog post format.
        
        Args:
            content: Source content/interview summary
            topic: Main topic of the blog post
            brand_context: Optional brand voice guidelines
            
        Returns:
            Article object
        """
        voice_guidelines = self._format_voice_guidelines(brand_context)
        
        prompt = f"""
        Write a compelling blog article about "{topic}".
        
        SOURCE CONTENT:
        {content[:3000]}
        
        {voice_guidelines}
        
        Create a blog post that:
        - Has an engaging headline (under 70 characters)
        - Has a compelling subtitle (under 120 characters)
        - Opens with a hook that draws readers in
        - Has clear sections with subheadings (use ## for H2)
        - Is 800-1200 words
        - Uses an engaging, readable style
        - Ends with a strong conclusion and call-to-action
        
        Also provide:
        - SEO meta description (150-160 characters)
        - 5-7 SEO keywords
        - 2-3 pull quotes from the content
        
        Return as JSON:
        {{
            "title": "Blog title",
            "subtitle": "Compelling subtitle",
            "content": "Full blog content with markdown formatting",
            "meta_description": "SEO meta description",
            "keywords": ["keyword1", "keyword2"],
            "featured_quotes": ["Quote 1", "Quote 2"],
            "call_to_action": "CTA text"
        }}
        """
        
        return await self._generate_article_with_ai(prompt, "blog", topic, brand_context)
    
    async def generate_thought_leadership(
        self,
        content: str,
        expert: str,
        brand_context: Optional[Dict] = None
    ) -> Article:
        """
        Generate thought leadership piece.
        
        Args:
            content: Source content/interview summary
            expert: Name of the expert/thought leader
            brand_context: Optional brand voice guidelines
            
        Returns:
            Article object
        """
        voice_guidelines = self._format_voice_guidelines(brand_context)
        
        prompt = f"""
        Write a thought leadership article featuring insights from {expert}.
        
        SOURCE CONTENT:
        {content[:3000]}
        
        {voice_guidelines}
        
        Create a thought leadership piece that:
        - Positions {expert} as an industry authority
        - Has a bold, attention-grabbing headline
        - Opens with a provocative statement or industry challenge
        - Presents unique perspectives and forward-thinking ideas
        - Includes specific examples and evidence
        - Challenges conventional thinking
        - Is 1000-1500 words
        - Ends with a vision for the future
        
        Also provide:
        - SEO meta description (150-160 characters)
        - 5-7 SEO keywords focused on industry expertise
        - 3-4 quotable statements from the expert
        
        Return as JSON:
        {{
            "title": "Thought leadership title",
            "subtitle": "Subtitle positioning expertise",
            "content": "Full article with markdown formatting",
            "meta_description": "SEO meta description",
            "keywords": ["keyword1", "keyword2"],
            "featured_quotes": ["Expert quote 1", "Expert quote 2"],
            "call_to_action": "CTA text"
        }}
        """
        
        return await self._generate_article_with_ai(prompt, "thought_leadership", expert, brand_context)
    
    async def generate_case_study(
        self,
        content: str,
        company: str,
        brand_context: Optional[Dict] = None
    ) -> Article:
        """
        Generate case study format.
        
        Args:
            content: Source content/interview summary
            company: Company name for the case study
            brand_context: Optional brand voice guidelines
            
        Returns:
            Article object
        """
        voice_guidelines = self._format_voice_guidelines(brand_context)
        
        prompt = f"""
        Write a case study article about {company}'s success.
        
        SOURCE CONTENT:
        {content[:3000]}
        
        {voice_guidelines}
        
        Create a case study that follows this structure:
        1. **Challenge**: What problem did they face?
        2. **Solution**: What approach did they take?
        3. **Results**: What outcomes did they achieve?
        4. **Key Learnings**: What can others learn?
        
        The case study should:
        - Have a results-focused headline
        - Include specific metrics and outcomes where possible
        - Tell a compelling story of transformation
        - Be 800-1200 words
        - Include testimonial quotes
        - End with actionable takeaways
        
        Also provide:
        - SEO meta description (150-160 characters)
        - 5-7 SEO keywords
        - 2-3 key testimonial quotes
        
        Return as JSON:
        {{
            "title": "Case study title",
            "subtitle": "Results-focused subtitle",
            "content": "Full case study with markdown formatting",
            "meta_description": "SEO meta description",
            "keywords": ["keyword1", "keyword2"],
            "featured_quotes": ["Testimonial 1", "Testimonial 2"],
            "call_to_action": "CTA text"
        }}
        """
        
        return await self._generate_article_with_ai(prompt, "case_study", company, brand_context)
    
    async def _generate_article_with_ai(
        self,
        prompt: str,
        format_type: str,
        subject: str,
        brand_context: Optional[Dict] = None
    ) -> Article:
        """Generate article using AI."""
        if not self.openrouter:
            return self._create_fallback_article(format_type, subject)
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system=f"You are an expert content strategist specializing in {format_type.replace('_', ' ')} articles with SEO optimization.",
                temperature=0.7,
                json_mode=True
            )
            
            data = json.loads(response)
            content = data.get("content", "")
            
            # Calculate word count and read time
            word_count = len(content.split())
            reading_time = max(1, word_count // 200)  # 200 words per minute
            
            return Article(
                title=data.get("title", "Untitled"),
                subtitle=data.get("subtitle", ""),
                content=content,
                meta_description=data.get("meta_description", ""),
                keywords=data.get("keywords", []),
                word_count=word_count,
                reading_time=reading_time,
                format_type=format_type,
                author=brand_context.get("author", "") if brand_context else "",
                featured_quotes=data.get("featured_quotes", []),
                call_to_action=data.get("call_to_action", "")
            )
            
        except Exception as e:
            logger.error(f"AI article generation failed for {format_type}: {e}")
            return self._create_fallback_article(format_type, subject)
    
    def _create_fallback_article(self, format_type: str, subject: str) -> Article:
        """Create fallback article when AI fails."""
        fallbacks = {
            "blog": Article(
                title=f"Insights on {subject}",
                subtitle="Key takeaways from our latest research",
                content=f"We recently explored {subject} and discovered several important insights...\n\n## Key Findings\n\nOur research revealed...",
                meta_description=f"Discover key insights about {subject} and learn how it impacts your business.",
                keywords=[subject.lower(), "insights", "business", "strategy"],
                word_count=100,
                reading_time=1,
                format_type="blog"
            ),
            "thought_leadership": Article(
                title=f"The Future of {subject}: An Expert Perspective",
                subtitle=f"Why {subject} is reshaping our industry",
                content=f"The landscape of {subject} is evolving rapidly...\n\n## A New Paradigm\n\nIndustry leaders are recognizing...",
                meta_description=f"Expert insights on the future of {subject} and what it means for industry leaders.",
                keywords=[subject.lower(), "thought leadership", "future", "innovation", "expert"],
                word_count=120,
                reading_time=1,
                format_type="thought_leadership"
            ),
            "case_study": Article(
                title=f"How {subject} Achieved Remarkable Results",
                subtitle="A deep dive into their transformation journey",
                content=f"## The Challenge\n\n{subject} faced significant obstacles...\n\n## The Solution\n\nThey implemented a strategic approach...\n\n## The Results\n\nThe outcomes exceeded expectations...",
                meta_description=f"Learn how {subject} overcame challenges and achieved impressive results through strategic transformation.",
                keywords=[subject.lower(), "case study", "success story", "results", "transformation"],
                word_count=150,
                reading_time=1,
                format_type="case_study"
            )
        }
        
        return fallbacks.get(format_type, Article(
            title=f"Article about {subject}",
            subtitle="",
            content="Content generation in progress...",
            meta_description=f"Learn more about {subject}.",
            keywords=[subject.lower()],
            word_count=50,
            reading_time=1,
            format_type=format_type
        ))
    
    async def generate_all_formats(
        self,
        interview: ProcessedInterview,
        brand_voice: Optional[Dict[str, Any]] = None,
        target_audience: Optional[str] = None
    ) -> Dict[str, GeneratedContent]:
        """
        Generate all content formats from an interview.
        
        Args:
            interview: The processed interview
            brand_voice: Brand voice guidelines
            target_audience: Target audience description
            
        Returns:
            Dictionary of format -> GeneratedContent
        """
        formats = ["blog", "linkedin", "twitter", "press_release", "email"]
        results = {}
        
        for fmt in formats:
            try:
                content = await self.generate_format(
                    interview=interview,
                    format_type=fmt,
                    brand_voice=brand_voice,
                    target_audience=target_audience
                )
                results[fmt] = content
            except Exception as e:
                logger.error(f"Failed to generate {fmt}: {e}")
                results[fmt] = self._create_error_content(fmt, str(e))
        
        return results
    
    async def generate_format(
        self,
        interview: ProcessedInterview,
        format_type: str,
        brand_voice: Optional[Dict[str, Any]] = None,
        target_audience: Optional[str] = None
    ) -> GeneratedContent:
        """
        Generate a specific content format.
        
        Args:
            interview: The processed interview
            format_type: One of "blog", "linkedin", "twitter", "press_release", "email"
            brand_voice: Brand voice guidelines
            target_audience: Target audience description
            
        Returns:
            GeneratedContent object
        """
        generators = {
            "blog": self._generate_blog,
            "linkedin": self._generate_linkedin,
            "twitter": self._generate_twitter,
            "press_release": self._generate_press_release,
            "email": self._generate_email
        }
        
        generator = generators.get(format_type)
        if not generator:
            raise ValueError(f"Unknown format: {format_type}")
        
        return await generator(interview, brand_voice, target_audience)
    
    async def _generate_blog(
        self,
        interview: ProcessedInterview,
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str]
    ) -> GeneratedContent:
        """Generate a blog article."""
        voice_guidelines = self._format_voice_guidelines(brand_voice)
        
        # Get quotes from the new Quote objects
        quote_texts = [q.text for q in interview.quotes[:3]] if interview.quotes else interview.key_insights[:3]
        
        prompt = f"""
        Write a compelling blog article based on this interview.
        
        INTERVIEW SUMMARY:
        {interview.summary}
        
        KEY INSIGHTS:
        {chr(10).join(f"- {i}" for i in interview.key_insights[:5])}
        
        KEY QUOTES:
        {chr(10).join(f'"{q}"' for q in quote_texts)}
        
        {voice_guidelines}
        
        TARGET AUDIENCE: {target_audience or "General business audience"}
        
        Write a blog article that:
        - Has an engaging headline (under 70 characters)
        - Opens with a hook that draws readers in
        - Includes the key insights and quotes naturally
        - Has clear sections with subheadings
        - Ends with a strong conclusion and call-to-action
        - Is 800-1200 words
        - Uses an engaging, readable style
        
        Return as JSON:
        {{
            "title": "Blog title",
            "content": "Full blog content with markdown formatting",
            "suggested_hashtags": ["tag1", "tag2", "tag3"],
            "key_takeaways": ["point 1", "point 2", "point 3"]
        }}
        """
        
        return await self._generate_with_ai(prompt, "blog", "blog")
    
    async def _generate_linkedin(
        self,
        interview: ProcessedInterview,
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str]
    ) -> GeneratedContent:
        """Generate a LinkedIn post."""
        voice_guidelines = self._format_voice_guidelines(brand_voice)
        
        key_insight = interview.key_insights[0] if interview.key_insights else interview.summary
        
        prompt = f"""
        Write a LinkedIn post based on this interview.
        
        INTERVIEW SUMMARY:
        {interview.summary}
        
        KEY INSIGHT:
        {key_insight}
        
        {voice_guidelines}
        
        Write a LinkedIn post that:
        - Starts with a hook in the first 2 lines (visible before "see more")
        - Is 150-300 words
        - Includes 1-2 key insights
        - Uses line breaks for readability
        - Ends with a question or call-to-action to drive engagement
        - Includes 3-5 relevant hashtags
        - Has a professional but conversational tone
        
        Return as JSON:
        {{
            "title": "LinkedIn post title",
            "content": "Full post content",
            "suggested_hashtags": ["tag1", "tag2", "tag3"],
            "key_takeaways": ["main point"]
        }}
        """
        
        return await self._generate_with_ai(prompt, "linkedin", "LinkedIn post")
    
    async def _generate_twitter(
        self,
        interview: ProcessedInterview,
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str]
    ) -> GeneratedContent:
        """Generate a Twitter/X thread."""
        voice_guidelines = self._format_voice_guidelines(brand_voice)
        
        prompt = f"""
        Write a Twitter/X thread based on this interview.
        
        INTERVIEW SUMMARY:
        {interview.summary}
        
        KEY INSIGHTS:
        {chr(10).join(f"- {i}" for i in interview.key_insights[:3])}
        
        {voice_guidelines}
        
        Write a Twitter thread that:
        - Has 5-8 tweets
        - First tweet is a hook (under 280 characters)
        - Each tweet is under 280 characters
        - Uses line breaks between tweets marked with numbers (1/, 2/, etc.)
        - Includes key insights from the interview
        - Ends with a call-to-action
        - Uses 1-2 hashtags maximum
        
        Return as JSON:
        {{
            "title": "Thread hook tweet",
            "content": "Full thread with numbered tweets",
            "suggested_hashtags": ["tag1"],
            "key_takeaways": ["main point"]
        }}
        """
        
        return await self._generate_with_ai(prompt, "twitter", "Twitter thread")
    
    async def _generate_press_release(
        self,
        interview: ProcessedInterview,
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str]
    ) -> GeneratedContent:
        """Generate a press release."""
        voice_guidelines = self._format_voice_guidelines(brand_voice)
        
        quote_texts = [q.text for q in interview.quotes[:2]] if interview.quotes else []
        
        prompt = f"""
        Write a press release based on this interview.
        
        INTERVIEW SUMMARY:
        {interview.summary}
        
        KEY QUOTES:
        {chr(10).join(f'"{q}"' for q in quote_texts)}
        
        {voice_guidelines}
        
        Write a press release that:
        - Follows AP style guidelines
        - Has a compelling headline
        - Includes a dateline (CITY, State — Date)
        - Lead paragraph covers who, what, when, where, why
        - Includes quotes from the interview
        - Is 300-500 words
        - Ends with a boilerplate and contact info
        
        Return as JSON:
        {{
            "title": "Press release headline",
            "content": "Full press release text",
            "suggested_hashtags": [],
            "key_takeaways": ["main news"]
        }}
        """
        
        return await self._generate_with_ai(prompt, "press_release", "press release")
    
    async def _generate_email(
        self,
        interview: ProcessedInterview,
        brand_voice: Optional[Dict[str, Any]],
        target_audience: Optional[str]
    ) -> GeneratedContent:
        """Generate an email newsletter."""
        voice_guidelines = self._format_voice_guidelines(brand_voice)
        
        prompt = f"""
        Write an email newsletter based on this interview.
        
        INTERVIEW SUMMARY:
        {interview.summary}
        
        KEY INSIGHTS:
        {chr(10).join(f"- {i}" for i in interview.key_insights[:4])}
        
        {voice_guidelines}
        
        Write an email newsletter that:
        - Has a compelling subject line (under 50 characters)
        - Opens with a personal greeting
        - Summarizes key insights in a scannable format
        - Includes quotes from the interview
        - Has a clear call-to-action
        - Is 200-400 words
        - Has a friendly, conversational tone
        
        Return as JSON:
        {{
            "title": "Email subject line",
            "content": "Full email content",
            "suggested_hashtags": [],
            "key_takeaways": ["point 1", "point 2", "point 3"]
        }}
        """
        
        return await self._generate_with_ai(prompt, "email", "email newsletter")
    
    async def _generate_with_ai(
        self,
        prompt: str,
        format_type: str,
        content_type: str
    ) -> GeneratedContent:
        """Generate content using AI."""
        if not self.openrouter:
            return self._create_fallback_content(format_type, content_type)
        
        try:
            response = await self.openrouter.complete(
                prompt=prompt,
                system=f"You are an expert content creator specializing in {content_type}.",
                temperature=0.7,
                json_mode=True
            )
            
            data = json.loads(response)
            content = data.get("content", "")
            
            # Calculate word count and read time
            word_count = len(content.split())
            read_time = max(1, word_count // 200)  # 200 words per minute
            
            return GeneratedContent(
                format=format_type,
                title=data.get("title", "Untitled"),
                content=content,
                word_count=word_count,
                estimated_read_time=read_time,
                suggested_hashtags=data.get("suggested_hashtags", []),
                key_takeaways=data.get("key_takeaways", [])
            )
            
        except Exception as e:
            logger.error(f"AI generation failed for {format_type}: {e}")
            return self._create_fallback_content(format_type, content_type)
    
    def _format_voice_guidelines(self, brand_voice: Optional[Dict[str, Any]]) -> str:
        """Format brand voice guidelines for prompts."""
        if not brand_voice:
            return ""
        
        tone = ", ".join(brand_voice.get("tone", ["professional"]))
        personality = brand_voice.get("personality", "")
        vocabulary = ", ".join(brand_voice.get("vocabulary", []))
        avoid = ", ".join(brand_voice.get("avoid", []))
        
        return f"""
BRAND VOICE GUIDELINES:
- Tone: {tone}
- Personality: {personality}
- Preferred vocabulary: {vocabulary}
- Words to avoid: {avoid}
"""
    
    def _create_fallback_content(self, format_type: str, content_type: str) -> GeneratedContent:
        """Create fallback content when AI fails."""
        fallbacks = {
            "blog": GeneratedContent(
                format="blog",
                title="Insights from Our Latest Interview",
                content="We recently had an insightful conversation that revealed several key takeaways...",
                word_count=100,
                estimated_read_time=1
            ),
            "linkedin": GeneratedContent(
                format="linkedin",
                title="Key Insights from Recent Interview",
                content="Just finished an incredible interview that opened my eyes to several important trends in our industry...",
                word_count=80,
                estimated_read_time=1
            ),
            "twitter": GeneratedContent(
                format="twitter",
                title="Key insights from today's interview 🧵",
                content="1/ Just had an amazing conversation. Here are the key takeaways:\n\n2/ First, the industry is changing rapidly...",
                word_count=60,
                estimated_read_time=1
            ),
            "press_release": GeneratedContent(
                format="press_release",
                title="Company Announces New Insights from Industry Interview",
                content="FOR IMMEDIATE RELEASE\n\nToday, the company shared insights from a recent interview...",
                word_count=120,
                estimated_read_time=1
            ),
            "email": GeneratedContent(
                format="email",
                title="This week's insights from our latest interview",
                content="Hi there,\n\nI wanted to share some fascinating insights from a recent interview we conducted...",
                word_count=90,
                estimated_read_time=1
            )
        }
        
        return fallbacks.get(format_type, GeneratedContent(
            format=format_type,
            title="Generated Content",
            content="Content generation in progress...",
            word_count=50,
            estimated_read_time=1
        ))
    
    def _create_error_content(self, format_type: str, error: str) -> GeneratedContent:
        """Create error content."""
        return GeneratedContent(
            format=format_type,
            title="Error Generating Content",
            content=f"There was an error generating this content: {error}. Please try again.",
            word_count=20,
            estimated_read_time=1
        )


# Convenience functions
async def generate_content_from_interview(
    interview: ProcessedInterview,
    formats: Optional[List[str]] = None,
    brand_voice: Optional[Dict[str, Any]] = None,
    target_audience: Optional[str] = None
) -> Dict[str, GeneratedContent]:
    """
    Generate content from an interview.
    
    Args:
        interview: The processed interview
        formats: List of formats to generate (default: all)
        brand_voice: Brand voice guidelines
        target_audience: Target audience description
        
    Returns:
        Dictionary of format -> GeneratedContent
    """
    generator = ArticleGenerator()
    
    if formats:
        results = {}
        for fmt in formats:
            results[fmt] = await generator.generate_format(
                interview=interview,
                format_type=fmt,
                brand_voice=brand_voice,
                target_audience=target_audience
            )
        return results
    
    return await generator.generate_all_formats(
        interview=interview,
        brand_voice=brand_voice,
        target_audience=target_audience
    )


async def generate_article_from_interview(
    interview: ProcessedInterview,
    article_type: str = "blog",
    brand_context: Optional[Dict] = None
) -> Article:
    """
    Generate a specific article type from an interview.
    
    Args:
        interview: The processed interview
        article_type: Type of article (blog, thought_leadership, case_study)
        brand_context: Optional brand voice and context
        
    Returns:
        Article object with SEO optimization and HTML/Markdown output
    """
    generator = ArticleGenerator()
    return await generator.generate_from_interview(
        processed_interview=interview,
        article_type=article_type,
        brand_context=brand_context
    )
