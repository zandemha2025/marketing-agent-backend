"""
Deliverables Composer

Bundles individual outputs from departments into complete, platform-specific units.
A TikTok isn't just a video - it's video + caption + hashtags + sound + timing.
An email isn't just copy - it's subject lines + preview + designed body.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .state import Deliverable

logger = logging.getLogger(__name__)


class DeliverablesComposer:
    """
    Composes department outputs into complete deliverables.

    Each deliverable is a self-contained unit that can be displayed,
    edited, and exported as a whole.
    """

    def compose_social_post(
        self,
        platform: str,
        copy_output: Dict[str, Any],
        design_output: Dict[str, Any],
        brief: Optional[Dict[str, Any]] = None,
        video_output: Optional[Dict[str, Any]] = None
    ) -> Deliverable:
        """
        Compose a complete social post from copy + design + optional video.

        The result is a single unit that shows:
        - The visual (image or video)
        - The caption
        - Hashtags
        - Platform-specific metadata
        """
        deliverable_id = f"social_{platform}_{uuid.uuid4().hex[:8]}"

        # Parse copy output
        caption = ""
        hashtags = []
        slides = []

        if isinstance(copy_output, dict):
            content = copy_output.get("content", "")
            if isinstance(content, str):
                # Extract hashtags from content
                words = content.split()
                hashtags = [w for w in words if w.startswith("#")]
                caption = content
            elif isinstance(content, dict):
                caption = content.get("text", content.get("caption", ""))
                hashtags = content.get("hashtags", [])
                slides = content.get("slides", [])

        # Parse design output
        image_url = None
        image_urls = []

        if isinstance(design_output, dict):
            image_url = design_output.get("filename")
            image_urls = design_output.get("all_filenames", [image_url] if image_url else [])

        # Parse video output if present
        video_url = None
        if video_output and isinstance(video_output, dict):
            video_url = video_output.get("filename", video_output.get("video_url"))

        # Compose the complete deliverable
        data = {
            "platform": platform,
            "caption": caption,
            "hashtags": hashtags if isinstance(hashtags, list) else [],
        }

        # Add media based on what we have
        if video_url:
            data["media_type"] = "video"
            data["video_url"] = video_url
            if image_url:
                data["thumbnail_url"] = image_url
        elif image_urls:
            if len(image_urls) > 1:
                data["media_type"] = "carousel"
                data["image_urls"] = image_urls
                data["slides"] = slides
            else:
                data["media_type"] = "image"
                data["image_url"] = image_urls[0]
        else:
            data["media_type"] = "text"

        # Add platform-specific fields
        if platform == "tiktok":
            data["sound_suggestion"] = brief.get("sound_suggestion") if brief else None
            data["duration_seconds"] = video_output.get("duration") if video_output else 15
        elif platform == "instagram":
            data["format_type"] = design_output.get("format_type", "post")
        elif platform == "linkedin":
            data["article_preview"] = None  # Could add article link preview
        elif platform == "twitter":
            data["thread"] = slides if slides else None

        return Deliverable(
            id=deliverable_id,
            type="social_post",
            platform=platform,
            status="ready",
            data=data,
            source_department="social"
        )

    def compose_email(
        self,
        copy_output: Dict[str, Any],
        design_output: Optional[Dict[str, Any]] = None,
        brief: Optional[Dict[str, Any]] = None
    ) -> Deliverable:
        """
        Compose a complete email from copy + optional design.

        The result shows:
        - Subject line variants (A/B)
        - Preview text
        - Email body (styled)
        - CTA
        """
        deliverable_id = f"email_{uuid.uuid4().hex[:8]}"

        # Parse copy output
        email_data = copy_output.get("email", copy_output.get("content", {}))

        if isinstance(email_data, str):
            # Plain text response
            data = {
                "subject": {
                    "primary": brief.get("subject", "Your subject line") if brief else "Your subject line",
                    "variant_a": "",
                    "variant_b": ""
                },
                "preview": "",
                "body_text": email_data,
                "body_html": f"<p>{email_data}</p>",
                "cta": {
                    "text": "Learn More",
                    "url": "#"
                }
            }
        else:
            # Structured email data
            subject = email_data.get("subject", {})
            if isinstance(subject, str):
                subject = {"primary": subject, "variant_a": "", "variant_b": ""}

            sections = email_data.get("sections", [])
            body_parts = []
            cta_data = {"text": "Learn More", "url": "#"}

            for section in sections:
                if section.get("type") == "cta":
                    cta_data = {
                        "text": section.get("button_text", "Learn More"),
                        "supporting": section.get("supporting", "")
                    }
                else:
                    body_parts.append(section.get("content", ""))

            body_text = "\n\n".join(body_parts)

            data = {
                "subject": subject,
                "preview": email_data.get("preview", ""),
                "body_text": body_text,
                "body_html": self._text_to_email_html(body_parts, cta_data),
                "cta": cta_data,
                "sign_off": email_data.get("sign_off", {}),
                "tone": email_data.get("tone", "professional")
            }

        # Add design if present
        if design_output:
            data["header_image"] = design_output.get("filename")
            data["template_style"] = design_output.get("style", "minimal")

        return Deliverable(
            id=deliverable_id,
            type="email",
            platform="email",
            status="ready",
            data=data,
            source_department="writer"
        )

    def compose_video(
        self,
        script_output: Dict[str, Any],
        video_output: Dict[str, Any],
        audio_output: Optional[Dict[str, Any]] = None,
        platform: str = "general"
    ) -> Deliverable:
        """
        Compose a complete video from script + video + optional voiceover.

        The result shows:
        - Video player
        - Script/captions
        - Voiceover status
        - Duration
        """
        deliverable_id = f"video_{platform}_{uuid.uuid4().hex[:8]}"

        data = {
            "platform": platform,
            "video_url": video_output.get("filename", video_output.get("video_url")),
            "duration_seconds": video_output.get("duration", 30),
            "script": script_output.get("content", ""),
            "has_captions": video_output.get("has_captions", False),
        }

        if audio_output:
            data["voiceover_url"] = audio_output.get("filename", audio_output.get("audio_url"))
            data["has_voiceover"] = True
        else:
            data["has_voiceover"] = False

        # Platform-specific
        if platform in ("tiktok", "reels", "shorts"):
            data["aspect_ratio"] = "9:16"
            data["format"] = "vertical"
        else:
            data["aspect_ratio"] = "16:9"
            data["format"] = "horizontal"

        return Deliverable(
            id=deliverable_id,
            type="video",
            platform=platform,
            status="ready",
            data=data,
            source_department="video"
        )

    def compose_blog(
        self,
        copy_output: Dict[str, Any],
        design_output: Optional[Dict[str, Any]] = None
    ) -> Deliverable:
        """
        Compose a complete blog post from copy + hero image.
        """
        deliverable_id = f"blog_{uuid.uuid4().hex[:8]}"

        data = {
            "title": copy_output.get("title", "Untitled"),
            "content": copy_output.get("content", ""),
            "content_html": self._markdown_to_html(copy_output.get("content", "")),
            "word_count": len(copy_output.get("content", "").split()),
            "read_time_minutes": len(copy_output.get("content", "").split()) // 200
        }

        if design_output:
            data["hero_image"] = design_output.get("filename")

        return Deliverable(
            id=deliverable_id,
            type="blog_post",
            platform="web",
            status="ready",
            data=data,
            source_department="writer"
        )

    def compose_ad(
        self,
        copy_output: Dict[str, Any],
        design_output: Dict[str, Any],
        platform: str = "display"
    ) -> Deliverable:
        """
        Compose a complete ad from copy + creative.

        Shows the ad as it would appear (headline + image + CTA).
        """
        deliverable_id = f"ad_{platform}_{uuid.uuid4().hex[:8]}"

        # Parse copy variations
        content = copy_output.get("content", "")
        variations = []

        if isinstance(content, str):
            # Parse variations from text
            parts = content.split("Variation")
            for i, part in enumerate(parts[1:], 1):
                variations.append({
                    "headline": f"Variation {i}",
                    "body": part.strip()[:200],
                    "cta": "Learn More"
                })
        elif isinstance(content, list):
            variations = content

        if not variations:
            variations = [{
                "headline": "Your Headline Here",
                "body": content[:200] if isinstance(content, str) else "",
                "cta": "Learn More"
            }]

        data = {
            "platform": platform,
            "image_url": design_output.get("filename"),
            "variations": variations,
            "selected_variation": 0,
            "dimensions": design_output.get("dimensions", "1200x628"),
            "format_type": design_output.get("format_type", "display")
        }

        return Deliverable(
            id=deliverable_id,
            type="ad",
            platform=platform,
            status="ready",
            data=data,
            source_department="designer"
        )

    def compose_landing_page(
        self,
        webdev_output: Dict[str, Any],
        copy_output: Optional[Dict[str, Any]] = None
    ) -> Deliverable:
        """
        Compose a complete landing page.
        """
        deliverable_id = f"landing_{uuid.uuid4().hex[:8]}"

        data = {
            "html": webdev_output.get("html", ""),
            "preview_url": webdev_output.get("preview_url"),
            "sections": webdev_output.get("sections", []),
        }

        if copy_output:
            data["headline"] = copy_output.get("headline")
            data["body_copy"] = copy_output.get("body")

        return Deliverable(
            id=deliverable_id,
            type="landing_page",
            platform="web",
            status="ready",
            data=data,
            source_department="webdev"
        )

    def compose_strategy_doc(
        self,
        strategy_output: Dict[str, Any],
        rationale_output: Optional[Dict[str, Any]] = None
    ) -> Deliverable:
        """
        Compose a strategy document deliverable.
        """
        deliverable_id = f"strategy_{uuid.uuid4().hex[:8]}"

        strategy = strategy_output.get("strategy", strategy_output)

        data = {
            "campaign_name": strategy.get("campaign_name", "Campaign Strategy"),
            "target_audience": strategy.get("target_audience", ""),
            "key_messages": strategy.get("key_messages", []),
            "channels": strategy.get("channels", []),
            "content_pillars": strategy.get("content_pillars", []),
            "tone_guidelines": strategy.get("tone_guidelines", ""),
            "success_metrics": strategy.get("success_metrics", [])
        }

        if rationale_output:
            rationale = rationale_output.get("rationale", rationale_output)
            data["executive_summary"] = rationale.get("executive_summary", "")
            data["channel_justification"] = rationale.get("channel_justification", [])
            data["competitive_advantage"] = rationale.get("competitive_advantage", "")

        return Deliverable(
            id=deliverable_id,
            type="strategy_doc",
            platform=None,
            status="ready",
            data=data,
            source_department="strategist"
        )

    def _text_to_email_html(
        self,
        body_parts: List[str],
        cta: Dict[str, Any]
    ) -> str:
        """Convert text sections to styled email HTML."""
        html_parts = []
        for part in body_parts:
            paragraphs = part.split("\n\n")
            for p in paragraphs:
                if p.strip():
                    html_parts.append(f"<p style='margin: 0 0 16px 0; line-height: 1.6;'>{p.strip()}</p>")

        cta_html = ""
        if cta.get("text"):
            cta_html = f"""
            <div style="text-align: center; margin: 32px 0;">
                <a href="#" style="background-color: #000; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                    {cta.get('text', 'Learn More')}
                </a>
            </div>
            """
            if cta.get("supporting"):
                cta_html += f"<p style='text-align: center; color: #666; font-size: 14px;'>{cta['supporting']}</p>"

        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            {''.join(html_parts)}
            {cta_html}
        </div>
        """

    def _markdown_to_html(self, markdown: str) -> str:
        """Simple markdown to HTML conversion."""
        import re

        html = markdown

        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Paragraphs
        paragraphs = html.split('\n\n')
        html = ''.join([
            f'<p>{p.strip()}</p>' if not p.strip().startswith('<h') else p
            for p in paragraphs if p.strip()
        ])

        return html
