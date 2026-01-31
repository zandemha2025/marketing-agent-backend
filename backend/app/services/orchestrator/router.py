"""
Department Router

Routes requests to the appropriate department based on context.
The user never sees departments - they just see magic happening.
"""

import logging
from typing import Optional, List, Dict, Any
from enum import Enum

from ..ai import OpenRouterService

logger = logging.getLogger(__name__)


class Department(str, Enum):
    """Available departments (invisible to user)."""
    RESEARCHER = "researcher"
    BRAND_STRATEGIST = "brand_strategist"
    STRATEGIST = "strategist"
    CONCEPT_DEVELOPER = "concept_developer"
    CREATIVE_DIRECTOR = "creative_director"
    WRITER = "writer"
    DESIGNER = "designer"
    VIDEO = "video"
    WEBDEV = "webdev"
    SOCIAL = "social"


# Department capabilities for routing
DEPARTMENT_CAPABILITIES = {
    Department.RESEARCHER: {
        "keywords": ["research", "competitor", "market", "trend", "analysis", "data", "insight"],
        "actions": ["competitor_analysis", "cultural_research", "topic_research", "keyword_research", "crawl_page"],
        "description": "Market research, competitive analysis, cultural trends, data gathering"
    },
    Department.BRAND_STRATEGIST: {
        "keywords": ["brand", "positioning", "identity", "voice", "values", "mission", "DNA"],
        "actions": ["brand_analysis", "positioning", "brand_guidelines"],
        "description": "Brand strategy, positioning, voice and tone development"
    },
    Department.STRATEGIST: {
        "keywords": ["strategy", "campaign", "plan", "calendar", "channel", "media"],
        "actions": ["campaign_strategy", "content_calendar", "campaign_rationale"],
        "description": "Campaign strategy, content planning, channel strategy"
    },
    Department.CONCEPT_DEVELOPER: {
        "keywords": ["concept", "idea", "big idea", "creative concept", "campaign idea"],
        "actions": ["develop_concept", "tension_analysis"],
        "description": "Big creative ideas, campaign concepts, creative territories"
    },
    Department.CREATIVE_DIRECTOR: {
        "keywords": ["brief", "creative brief", "direction", "art direction"],
        "actions": ["create_briefs"],
        "description": "Creative briefs, art direction, quality control"
    },
    Department.WRITER: {
        "keywords": ["copy", "write", "headline", "blog", "email", "script", "ad copy", "caption"],
        "actions": ["blog_post", "social_copy", "email_copy", "ad_copy", "video_script"],
        "description": "All written content - copy, scripts, blogs, emails"
    },
    Department.DESIGNER: {
        "keywords": ["design", "image", "visual", "graphic", "hero", "carousel", "banner"],
        "actions": ["hero_image", "social_graphic", "ad_creative", "product_hero"],
        "description": "Visual design, image generation, graphics"
    },
    Department.VIDEO: {
        "keywords": ["video", "reel", "tiktok", "animation", "motion"],
        "actions": ["generate_video", "create_reel", "video_edit"],
        "description": "Video content, reels, TikToks, motion graphics"
    },
    Department.WEBDEV: {
        "keywords": ["website", "landing page", "web", "page", "site", "html"],
        "actions": ["landing_page", "microsite", "web_component"],
        "description": "Landing pages, microsites, web experiences"
    },
    Department.SOCIAL: {
        "keywords": ["social media", "post", "instagram", "linkedin", "twitter", "facebook", "tiktok post"],
        "actions": ["post_set", "content_calendar", "engagement"],
        "description": "Social media strategy and bundled posts"
    }
}


class DepartmentRouter:
    """
    Routes work to the appropriate department.

    The router is invisible to the user - they just describe what they want,
    and the right department handles it.
    """

    def __init__(self, llm_service: OpenRouterService):
        self.llm = llm_service

    async def route_message(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Route a user message to the appropriate department(s).

        Returns a list of tasks to execute, each with:
        - department: which department handles it
        - action: what action to perform
        - input: the input data for the action

        A single message might require multiple departments.
        For example, "Create a TikTok about our sale" needs:
        - Writer (script/caption)
        - Video (video generation)
        - Social (bundling into complete post)
        """
        # First, try quick keyword-based routing
        quick_routes = self._quick_route(message)

        if quick_routes:
            return quick_routes

        # Fall back to LLM-based routing for complex requests
        return await self._llm_route(message, context)

    def _quick_route(self, message: str) -> Optional[List[Dict[str, Any]]]:
        """
        Quick keyword-based routing for obvious requests.

        Returns None if we need LLM routing.
        """
        message_lower = message.lower()

        # Check for exact action triggers
        triggers = {
            "research competitor": (Department.RESEARCHER, "competitor_analysis"),
            "research market": (Department.RESEARCHER, "topic_research"),
            "write blog": (Department.WRITER, "blog_post"),
            "write email": (Department.WRITER, "email_copy"),
            "create image": (Department.DESIGNER, "hero_image"),
            "create video": (Department.VIDEO, "generate_video"),
            "landing page": (Department.WEBDEV, "landing_page"),
            "social post": (Department.SOCIAL, "post_set"),
        }

        for trigger, (dept, action) in triggers.items():
            if trigger in message_lower:
                return [{
                    "department": dept.value,
                    "action": action,
                    "input": {"user_request": message}
                }]

        return None

    async def _llm_route(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to understand complex requests and route appropriately.
        """
        department_list = "\n".join([
            f"- {dept.value}: {caps['description']}. Actions: {', '.join(caps['actions'])}"
            for dept, caps in DEPARTMENT_CAPABILITIES.items()
        ])

        prompt = f"""You are a routing system for a marketing agency. Based on the user's request,
determine which department(s) should handle it and what action(s) they should take.

Available departments:
{department_list}

User request: "{message}"

Current context:
- Has knowledge base: {bool(context.get('knowledge_base'))}
- Has campaign research: {bool(context.get('campaign_research'))}
- Has concepts: {bool(context.get('concepts'))}
- Has selected concept: {context.get('selected_concept_index') is not None}
- Has creative briefs: {bool(context.get('creative_briefs'))}

Return a JSON array of tasks. Each task has:
- department: the department name
- action: the specific action to perform
- input: any specific input data extracted from the request

Example response:
[
  {{"department": "writer", "action": "social_copy", "input": {{"platform": "instagram", "topic": "summer sale"}}}},
  {{"department": "designer", "action": "social_graphic", "input": {{"platform": "instagram", "topic": "summer sale"}}}}
]

If the request is unclear, return a single task for the most likely department.
If the request requires multiple departments working together, list all of them.
"""

        try:
            result = await self.llm.complete_json(prompt)
            if isinstance(result, list):
                return result
            return [result] if result else []
        except Exception as e:
            logger.error(f"LLM routing failed: {e}")
            # Fall back to general strategist
            return [{
                "department": Department.STRATEGIST.value,
                "action": "campaign_strategy",
                "input": {"user_request": message}
            }]

    def get_production_pipeline(
        self,
        brief: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Given a creative brief, determine the production pipeline.

        Returns ordered list of department tasks to produce the deliverable.
        """
        channel = brief.get("channel", "")
        deliverable_type = brief.get("deliverable_type", "")
        format_type = brief.get("format_type", "")

        tasks = []

        # Determine what departments are needed based on deliverable type
        if deliverable_type in ("social_post", "social_graphic"):
            # Social needs copy + visual + bundling
            tasks.append({
                "department": Department.WRITER.value,
                "action": "social_copy",
                "input": {
                    "platform": channel,
                    "format_type": format_type,
                    "brief_id": brief.get("id")
                }
            })
            tasks.append({
                "department": Department.DESIGNER.value,
                "action": "social_graphic",
                "input": {
                    "platform": channel,
                    "format_type": format_type,
                    "brief_id": brief.get("id")
                }
            })

        elif deliverable_type in ("video", "video_script", "reel"):
            # Video needs script + video generation
            tasks.append({
                "department": Department.WRITER.value,
                "action": "video_script",
                "input": {"brief_id": brief.get("id")}
            })
            tasks.append({
                "department": Department.VIDEO.value,
                "action": "generate_video",
                "input": {"brief_id": brief.get("id")}
            })

        elif deliverable_type in ("email", "email_copy", "email_template"):
            # Email needs copy
            tasks.append({
                "department": Department.WRITER.value,
                "action": "email_copy",
                "input": {"brief_id": brief.get("id")}
            })

        elif deliverable_type in ("blog", "blog_post"):
            # Blog needs copy + hero image
            tasks.append({
                "department": Department.WRITER.value,
                "action": "blog_post",
                "input": {"brief_id": brief.get("id")}
            })
            tasks.append({
                "department": Department.DESIGNER.value,
                "action": "hero_image",
                "input": {"platform": "blog", "brief_id": brief.get("id")}
            })

        elif deliverable_type in ("landing_page", "web"):
            # Landing page needs webdev
            tasks.append({
                "department": Department.WEBDEV.value,
                "action": "landing_page",
                "input": {"brief_id": brief.get("id")}
            })

        elif deliverable_type in ("ad_copy", "ad_creative"):
            # Ads need copy + creative
            tasks.append({
                "department": Department.WRITER.value,
                "action": "ad_copy",
                "input": {"brief_id": brief.get("id")}
            })
            tasks.append({
                "department": Department.DESIGNER.value,
                "action": "ad_creative",
                "input": {"brief_id": brief.get("id")}
            })

        else:
            # Default: just writer
            tasks.append({
                "department": Department.WRITER.value,
                "action": "social_copy",
                "input": {"brief_id": brief.get("id")}
            })

        return tasks
