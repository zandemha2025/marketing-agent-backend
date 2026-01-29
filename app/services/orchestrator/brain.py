"""
Orchestrator Brain

The central intelligence that coordinates all departments.
Invisible to the user - they just see magic happening.

Enhanced with dynamic intelligence loading for deep domain expertise.
"""

import uuid
import asyncio
import logging
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from dataclasses import asdict

from .state import CampaignState, CampaignPhase, Deliverable, Concept
from .router import DepartmentRouter, Department
from .composer import DeliverablesComposer
from ..ai import OpenRouterService
from ..convex_sync import get_convex_service, ConvexSyncService

# Import intelligence layer for deep domain expertise
try:
    from ...intelligence import (
        load_department,
        load_format,
        load_rubric,
        get_department_prompt
    )
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False

logger = logging.getLogger(__name__)


class OrchestratorBrain:
    """
    The brain that makes everything work together.

    Flow:
    1. User says what they want
    2. Quick campaign-specific research (if needed)
    3. Generate strategy and concepts
    4. Pitch to user (unless YOLO mode)
    5. User selects concept
    6. Generate creative briefs
    7. Produce all assets in parallel
    8. Bundle into complete deliverables
    9. User can refine anything by clicking + chatting
    """

    def __init__(
        self,
        openrouter_api_key: str,
        firecrawl_api_key: Optional[str] = None,
        perplexity_api_key: Optional[str] = None,
        segmind_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
        sync_to_convex: bool = True
    ):
        self.llm = OpenRouterService(api_key=openrouter_api_key)
        self.router = DepartmentRouter(self.llm)
        self.composer = DeliverablesComposer()

        # Store API keys for department use
        self.api_keys = {
            "openrouter": openrouter_api_key,
            "firecrawl": firecrawl_api_key,
            "perplexity": perplexity_api_key,
            "segmind": segmind_api_key,
            "elevenlabs": elevenlabs_api_key
        }

        # Convex sync
        self.sync_to_convex = sync_to_convex
        self._convex: Optional[ConvexSyncService] = None
        if sync_to_convex:
            self._convex = get_convex_service()

        # Active campaign states
        self._states: Dict[str, CampaignState] = {}

        # Map local deliverable IDs to Convex IDs
        self._convex_deliverable_ids: Dict[str, str] = {}

    async def start_campaign(
        self,
        campaign_id: str,
        organization_id: str,
        user_request: str,
        knowledge_base: Dict[str, Any],
        yolo_mode: bool = False,
        progress_callback: Optional[Callable] = None,
        convex_campaign_id: Optional[str] = None
    ) -> CampaignState:
        """
        Start a new campaign from user request.

        This is the main entry point. The orchestrator takes over from here.

        Args:
            campaign_id: Local campaign ID
            organization_id: Organization ID
            user_request: What the user wants
            knowledge_base: Brand/market data
            yolo_mode: Skip approval gates
            progress_callback: Async callback for progress updates
            convex_campaign_id: Optional Convex campaign ID for real-time sync
        """
        # Initialize state
        state = CampaignState(
            campaign_id=campaign_id,
            organization_id=organization_id,
            user_request=user_request,
            knowledge_base=knowledge_base,
            yolo_mode=yolo_mode,
            started_at=datetime.utcnow()
        )
        # Store Convex ID in state for later use
        state.convex_campaign_id = convex_campaign_id
        self._states[campaign_id] = state

        # Sync status to Convex
        if convex_campaign_id:
            await self._sync_campaign_status_to_convex(convex_campaign_id, "running")

        try:
            # Phase 1: Quick campaign-specific research
            await self._research_phase(state, progress_callback)

            # Phase 2: Strategy and concepts
            await self._strategy_phase(state, progress_callback)

            # Sync concepts to Convex
            if convex_campaign_id and state.concepts:
                await self._sync_concepts_to_convex(
                    convex_campaign_id,
                    state.concepts
                )

            # Phase 3: Pitch (unless YOLO)
            if not yolo_mode:
                state.phase = CampaignPhase.PITCHING
                state.status_message = "Here's what I'm thinking..."
                if progress_callback:
                    await progress_callback(state)
                # Return here - user needs to approve
                state.phase = CampaignPhase.AWAITING_APPROVAL
                return state

            # YOLO mode: auto-select best concept and continue
            state.select_concept(0)  # Select first concept
            if convex_campaign_id:
                await self._sync_concepts_to_convex(
                    convex_campaign_id,
                    state.concepts,
                    selected_index=0
                )

            # Phase 4: Create briefs
            await self._briefing_phase(state, progress_callback)

            # Phase 5: Produce assets
            await self._production_phase(state, progress_callback, convex_campaign_id)

            # Complete
            state.phase = CampaignPhase.COMPLETE
            state.status_message = "Campaign complete!"
            state.completed_at = datetime.utcnow()

            if convex_campaign_id:
                await self._sync_campaign_status_to_convex(convex_campaign_id, "complete")

            if progress_callback:
                await progress_callback(state)

            return state

        except Exception as e:
            logger.error(f"Campaign {campaign_id} failed: {e}")
            state.phase = CampaignPhase.FAILED
            state.errors.append(str(e))
            if convex_campaign_id:
                await self._sync_campaign_status_to_convex(convex_campaign_id, "failed")
            if progress_callback:
                await progress_callback(state)
            raise

    async def continue_after_approval(
        self,
        campaign_id: str,
        selected_concept_index: int,
        progress_callback: Optional[Callable] = None
    ) -> CampaignState:
        """
        Continue campaign after user approves a concept.

        Called when user clicks "Go with this concept" in the pitch.
        """
        state = self._states.get(campaign_id)
        if not state:
            raise ValueError(f"Campaign {campaign_id} not found")

        if state.phase != CampaignPhase.AWAITING_APPROVAL:
            raise ValueError(f"Campaign not awaiting approval, current phase: {state.phase}")

        # Select the concept
        state.select_concept(selected_concept_index)
        state.status_message = f"Great choice! Let's bring '{state.selected_concept.name}' to life..."

        # Sync selected concept to Convex
        convex_campaign_id = getattr(state, 'convex_campaign_id', None)
        if convex_campaign_id:
            await self._sync_concepts_to_convex(
                convex_campaign_id,
                state.concepts,
                selected_index=selected_concept_index
            )

        if progress_callback:
            await progress_callback(state)

        try:
            # Phase 4: Create briefs
            await self._briefing_phase(state, progress_callback)

            # Phase 5: Produce assets
            await self._production_phase(state, progress_callback, convex_campaign_id)

            # Complete
            state.phase = CampaignPhase.COMPLETE
            state.status_message = "Campaign complete!"
            state.completed_at = datetime.utcnow()

            if convex_campaign_id:
                await self._sync_campaign_status_to_convex(convex_campaign_id, "complete")

            if progress_callback:
                await progress_callback(state)

            return state

        except Exception as e:
            logger.error(f"Campaign {campaign_id} failed: {e}")
            state.phase = CampaignPhase.FAILED
            state.errors.append(str(e))
            if convex_campaign_id:
                await self._sync_campaign_status_to_convex(convex_campaign_id, "failed")
            if progress_callback:
                await progress_callback(state)
            raise

    async def refine_deliverable(
        self,
        campaign_id: str,
        deliverable_id: str,
        feedback: str,
        progress_callback: Optional[Callable] = None
    ) -> Deliverable:
        """
        Refine a specific deliverable based on user feedback.

        Called when user clicks a deliverable and says "make this punchier" etc.
        """
        state = self._states.get(campaign_id)
        if not state:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Find the deliverable
        deliverable = next(
            (d for d in state.deliverables if d.id == deliverable_id),
            None
        )
        if not deliverable:
            raise ValueError(f"Deliverable {deliverable_id} not found")

        state.phase = CampaignPhase.REFINING
        state.status_message = f"Refining {deliverable.type}..."
        deliverable.status = "generating"
        deliverable.feedback = feedback

        if progress_callback:
            await progress_callback(state)

        # Route the refinement to the appropriate department
        tasks = await self.router.route_message(
            f"Refine this {deliverable.type}: {feedback}",
            {
                "deliverable": deliverable.data,
                "selected_concept": state.selected_concept.__dict__ if state.selected_concept else {},
                "knowledge_base": state.knowledge_base
            }
        )

        # Execute refinement
        for task in tasks:
            result = await self._execute_department_task(
                state=state,
                department=task["department"],
                action=task["action"],
                input_data={
                    **task.get("input", {}),
                    "original": deliverable.data,
                    "feedback": feedback,
                    "brand_dna": state.knowledge_base.get("brand", {})
                }
            )

            # Update deliverable with new content
            if result:
                deliverable.data.update(result)
                deliverable.updated_at = datetime.utcnow()

        deliverable.status = "ready"
        state.phase = CampaignPhase.COMPLETE
        state.status_message = "Refinement complete!"

        # Sync refined deliverable to Convex
        convex_campaign_id = getattr(state, 'convex_campaign_id', None)
        if convex_campaign_id:
            await self._sync_deliverable_to_convex(deliverable, convex_campaign_id)

        if progress_callback:
            await progress_callback(state)

        return deliverable

    async def handle_chat_message(
        self,
        campaign_id: str,
        message: str,
        selected_deliverable_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Handle a chat message in the context of a campaign.

        If a deliverable is selected, the message is about that deliverable.
        Otherwise, it's a general campaign question or new request.
        """
        state = self._states.get(campaign_id)
        if not state:
            raise ValueError(f"Campaign {campaign_id} not found")

        # If a deliverable is selected, treat as refinement
        if selected_deliverable_id:
            deliverable = await self.refine_deliverable(
                campaign_id=campaign_id,
                deliverable_id=selected_deliverable_id,
                feedback=message,
                progress_callback=progress_callback
            )
            return {
                "type": "refinement",
                "deliverable": deliverable.data,
                "message": f"I've updated the {deliverable.type}. Take a look!"
            }

        # Route the message to appropriate department(s)
        tasks = await self.router.route_message(
            message,
            {
                "knowledge_base": state.knowledge_base,
                "campaign_research": state.campaign_research,
                "concepts": [c.__dict__ for c in state.concepts],
                "selected_concept_index": state.selected_concept_index,
                "creative_briefs": state.creative_briefs
            }
        )

        results = []
        for task in tasks:
            result = await self._execute_department_task(
                state=state,
                department=task["department"],
                action=task["action"],
                input_data={
                    **task.get("input", {}),
                    "brand_dna": state.knowledge_base.get("brand", {}),
                    "user_request": message
                }
            )
            results.append(result)

        return {
            "type": "response",
            "results": results,
            "message": "Here's what I found."
        }

    # === Private Phase Methods ===

    async def _research_phase(
        self,
        state: CampaignState,
        progress_callback: Optional[Callable] = None
    ):
        """Quick, targeted research for this specific campaign."""
        state.phase = CampaignPhase.RESEARCHING
        state.progress = 0.0
        state.status_message = "Researching market context..."

        if progress_callback:
            await progress_callback(state)

        # Determine what research is needed based on the request
        research_needed = await self._determine_research_needs(state.user_request, state.knowledge_base)

        research_tasks = []

        if research_needed.get("competitor"):
            research_tasks.append(
                self._execute_department_task(
                    state=state,
                    department="researcher",
                    action="competitor_analysis",
                    input_data={
                        "brand_name": state.knowledge_base.get("brand", {}).get("name", ""),
                        "industry": state.knowledge_base.get("market", {}).get("industry", "")
                    }
                )
            )

        if research_needed.get("cultural"):
            research_tasks.append(
                self._execute_department_task(
                    state=state,
                    department="researcher",
                    action="cultural_research",
                    input_data={
                        "brand_name": state.knowledge_base.get("brand", {}).get("name", ""),
                        "industry": state.knowledge_base.get("market", {}).get("industry", ""),
                        "target_audience": state.knowledge_base.get("audiences", {}).get("primary", "")
                    }
                )
            )

        if research_needed.get("topic"):
            research_tasks.append(
                self._execute_department_task(
                    state=state,
                    department="researcher",
                    action="topic_research",
                    input_data={"topic": research_needed.get("topic_query", state.user_request)}
                )
            )

        # Execute research in parallel
        if research_tasks:
            results = await asyncio.gather(*research_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, dict) and "type" in result:
                    state.campaign_research[result["type"]] = result

        state.progress = 1.0
        state.status_message = "Research complete."

        if progress_callback:
            await progress_callback(state)

    async def _strategy_phase(
        self,
        state: CampaignState,
        progress_callback: Optional[Callable] = None
    ):
        """Develop strategy and creative concepts."""
        state.phase = CampaignPhase.STRATEGIZING
        state.progress = 0.0
        state.status_message = "Developing creative concepts..."

        if progress_callback:
            await progress_callback(state)

        brand_dna = state.knowledge_base.get("brand", {})

        # Step 1: Develop concepts (2-3 options)
        concepts_result = await self._generate_concepts(state, brand_dna)

        state.progress = 0.5

        if progress_callback:
            await progress_callback(state)

        # Parse concepts into state
        concepts_data = concepts_result.get("concepts", [concepts_result.get("concept", {})])
        if not isinstance(concepts_data, list):
            concepts_data = [concepts_data]

        for i, c in enumerate(concepts_data[:3]):  # Max 3 concepts
            concept = Concept(
                id=f"concept_{i}_{uuid.uuid4().hex[:6]}",
                name=c.get("concept_name", f"Concept {i+1}"),
                description=c.get("concept_description", ""),
                manifesto=c.get("manifesto", ""),
                visual_world=c.get("visual_world", ""),
                tone_of_voice=c.get("tone_of_voice", ""),
                channel_expressions=c.get("channel_expressions", [])
            )
            state.concepts.append(concept)

        # Step 2: Develop strategy for each concept
        state.status_message = "Building campaign strategy..."

        if progress_callback:
            await progress_callback(state)

        # For efficiency, just build strategy for the first concept
        # (will rebuild if different concept is selected)
        strategy_result = await self._execute_department_task(
            state=state,
            department="strategist",
            action="campaign_strategy",
            input_data={
                "brand_dna": brand_dna,
                "goal": state.user_request,
                "concept_name": state.concepts[0].name if state.concepts else ""
            },
            context={
                "concept": {"type": "concept", "concept": concepts_data[0] if concepts_data else {}}
            }
        )

        state.strategy = strategy_result.get("strategy", strategy_result)
        state.progress = 1.0
        state.status_message = "Strategy ready for review."

        if progress_callback:
            await progress_callback(state)

    async def _briefing_phase(
        self,
        state: CampaignState,
        progress_callback: Optional[Callable] = None
    ):
        """Create creative briefs for all deliverables."""
        state.phase = CampaignPhase.BRIEFING
        state.progress = 0.0
        state.status_message = "Creating creative briefs..."

        if progress_callback:
            await progress_callback(state)

        concept = state.selected_concept
        if not concept:
            raise ValueError("No concept selected")

        # Get channels from strategy
        channels = []
        if state.strategy and isinstance(state.strategy, dict):
            channels = state.strategy.get("channels", [])
        if not channels:
            channels = ["instagram", "email", "blog"]  # Default channels

        # Create briefs
        briefs_result = await self._execute_department_task(
            state=state,
            department="creative_director",
            action="create_briefs",
            input_data={
                "brand_dna": state.knowledge_base.get("brand", {}),
                "channels": channels
            },
            context={
                "concept": {"type": "concept", "concept": concept.__dict__},
                "strategy": {"type": "campaign_strategy", "strategy": state.strategy}
            }
        )

        state.creative_briefs = briefs_result.get("briefs", [])
        state.progress = 1.0
        state.status_message = f"Created {len(state.creative_briefs)} creative briefs."

        if progress_callback:
            await progress_callback(state)

    async def _production_phase(
        self,
        state: CampaignState,
        progress_callback: Optional[Callable] = None,
        convex_campaign_id: Optional[str] = None
    ):
        """Produce all assets from briefs."""
        state.phase = CampaignPhase.PRODUCING
        state.progress = 0.0
        state.status_message = "Producing campaign assets..."

        if progress_callback:
            await progress_callback(state)

        total_briefs = len(state.creative_briefs)
        completed = 0

        for brief in state.creative_briefs:
            # Get the production pipeline for this brief
            pipeline = self.router.get_production_pipeline(brief)

            # Execute pipeline
            outputs = {}
            for task in pipeline:
                result = await self._execute_department_task(
                    state=state,
                    department=task["department"],
                    action=task["action"],
                    input_data={
                        **task.get("input", {}),
                        "brand_dna": state.knowledge_base.get("brand", {}),
                        "selected_territory": state.selected_concept.__dict__ if state.selected_concept else {}
                    },
                    context={
                        "concept": {"type": "concept", "concept": state.selected_concept.__dict__} if state.selected_concept else {},
                        "creative_briefs": {"type": "creative_briefs", "briefs": state.creative_briefs}
                    }
                )
                outputs[task["department"]] = result

            # Compose into deliverable
            deliverable = await self._compose_deliverable(brief, outputs)
            if deliverable:
                state.add_deliverable(deliverable)

                # Sync deliverable to Convex for real-time updates
                if convex_campaign_id:
                    await self._sync_deliverable_to_convex(deliverable, convex_campaign_id)

                # Send update for each deliverable
                if progress_callback:
                    await progress_callback(state)

            completed += 1
            state.progress = completed / total_briefs
            state.status_message = f"Produced {completed}/{total_briefs} assets..."

            if progress_callback:
                await progress_callback(state)

        state.status_message = f"Production complete! {len(state.deliverables)} deliverables ready."

    # === Helper Methods ===

    async def _determine_research_needs(
        self,
        user_request: str,
        knowledge_base: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine what research is needed for this specific campaign."""
        prompt = f"""Based on this campaign request, determine what additional research is needed.

Request: "{user_request}"

We already have:
- Brand info: {bool(knowledge_base.get('brand'))}
- Market data: {bool(knowledge_base.get('market'))}
- Audience data: {bool(knowledge_base.get('audiences'))}

Return JSON indicating what research to do:
{{
  "competitor": true/false,  // Need fresh competitor analysis?
  "cultural": true/false,    // Need cultural/trend research?
  "topic": true/false,       // Need specific topic research?
  "topic_query": "the specific topic to research if topic is true"
}}

Only request research that will meaningfully improve the campaign.
A simple "create a social post" doesn't need research.
A "launch campaign for new product line" probably does."""

        try:
            result = await self.llm.complete_json(prompt)
            return result if isinstance(result, dict) else {}
        except Exception:
            # Default: minimal research
            return {"competitor": False, "cultural": False, "topic": False}

    async def _generate_concepts(
        self,
        state: CampaignState,
        brand_dna: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate 2-3 creative concepts."""
        # Use concept developer
        return await self._execute_department_task(
            state=state,
            department="concept_developer",
            action="develop_concept",
            input_data={"brand_dna": brand_dna},
            context={
                "cultural": state.campaign_research.get("cultural_research", {}),
                "competitor": state.campaign_research.get("competitor_analysis", {})
            }
        )

    async def _execute_department_task(
        self,
        state: CampaignState,
        department: str,
        action: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a task on a specific department."""
        start_time = datetime.utcnow()

        # TODO: Actually call the department agents
        # For now, use LLM directly with department-style prompts
        result = await self._simulate_department(department, action, input_data, context or {})

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        state.log_department_action(
            department=department,
            action=action,
            input_data=input_data,
            output_data=result,
            duration_ms=duration_ms
        )

        return result

    async def _simulate_department(
        self,
        department: str,
        action: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate department execution using LLM with deep domain expertise.

        Uses the intelligence layer to give each department real expertise,
        not just generic prompts. This is where the "soul" of each department
        comes from.

        TODO: Replace with actual department agent calls.
        """
        # Load department expertise from intelligence layer
        system_prompt = self._build_department_prompt(department, action, input_data)

        # Build the action prompt
        prompt = f"""Action: {action}

Input:
{self._format_input(input_data)}

Context:
{self._format_input(context)}

Perform the requested action and return the result as JSON.

Your response must be valid JSON only."""

        try:
            result = await self.llm.complete_json(prompt, system_prompt)
            return {"type": action, **result} if isinstance(result, dict) else {"type": action, "result": result}
        except Exception as e:
            logger.error(f"Department {department} failed on {action}: {e}")
            return {"type": action, "error": str(e)}

    def _build_department_prompt(
        self,
        department: str,
        action: str,
        input_data: Dict[str, Any]
    ) -> str:
        """
        Build a comprehensive department prompt using the intelligence layer.

        This gives each department its deep expertise, quality rubrics,
        and format-specific knowledge.
        """
        if not INTELLIGENCE_AVAILABLE:
            # Fallback to basic prompt
            return f"You are the {department} department at a marketing agency. Be thorough and creative."

        try:
            # Determine format type from input data for format-specific knowledge
            format_type = None
            platform = input_data.get("platform", "").lower()
            channel = input_data.get("channel", "").lower()

            # Map platforms/channels to format types
            format_mapping = {
                "tiktok": "tiktok",
                "instagram": "instagram",
                "linkedin": "linkedin",
                "twitter": "twitter",
                "x": "twitter",
                "email": "email",
                "blog": "blog",
                "landing_page": "landing_page",
                "ads": "ads",
            }

            for key, fmt in format_mapping.items():
                if key in platform or key in channel:
                    format_type = fmt
                    break

            # Build comprehensive prompt with department expertise
            prompt = get_department_prompt(
                department=department,
                format_type=format_type,
                include_rubric=True
            )

            if prompt:
                logger.debug(f"Loaded intelligence for {department} (format: {format_type})")
                return prompt

            # Fallback if intelligence doesn't exist for this department
            fallback = load_department(department)
            if fallback:
                return fallback

            return f"You are the {department} department at a marketing agency. Be thorough and creative."

        except Exception as e:
            logger.warning(f"Failed to load intelligence for {department}: {e}")
            return f"You are the {department} department at a marketing agency. Be thorough and creative."

    def _format_input(self, data: Dict[str, Any]) -> str:
        """Format input data for the prompt, handling large objects."""
        import json

        try:
            # Limit size to avoid token overflow
            formatted = json.dumps(data, indent=2, default=str)
            if len(formatted) > 3000:
                formatted = formatted[:3000] + "\n... (truncated)"
            return formatted
        except Exception:
            return str(data)[:3000]

    async def _compose_deliverable(
        self,
        brief: Dict[str, Any],
        outputs: Dict[str, Dict[str, Any]]
    ) -> Optional[Deliverable]:
        """Compose outputs into a deliverable."""
        deliverable_type = brief.get("deliverable_type", "")
        channel = brief.get("channel", "")

        try:
            if deliverable_type in ("social_post", "social_graphic"):
                return self.composer.compose_social_post(
                    platform=channel,
                    copy_output=outputs.get("writer", {}),
                    design_output=outputs.get("designer", {}),
                    brief=brief,
                    video_output=outputs.get("video")
                )

            elif deliverable_type in ("email", "email_copy"):
                return self.composer.compose_email(
                    copy_output=outputs.get("writer", {}),
                    design_output=outputs.get("designer"),
                    brief=brief
                )

            elif deliverable_type in ("video", "video_script"):
                return self.composer.compose_video(
                    script_output=outputs.get("writer", {}),
                    video_output=outputs.get("video", {}),
                    audio_output=outputs.get("audio"),
                    platform=channel
                )

            elif deliverable_type in ("blog", "blog_post"):
                return self.composer.compose_blog(
                    copy_output=outputs.get("writer", {}),
                    design_output=outputs.get("designer")
                )

            elif deliverable_type in ("ad_copy", "ad_creative"):
                return self.composer.compose_ad(
                    copy_output=outputs.get("writer", {}),
                    design_output=outputs.get("designer", {}),
                    platform=channel
                )

            elif deliverable_type in ("landing_page", "web"):
                return self.composer.compose_landing_page(
                    webdev_output=outputs.get("webdev", {}),
                    copy_output=outputs.get("writer")
                )

            else:
                logger.warning(f"Unknown deliverable type: {deliverable_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to compose deliverable: {e}")
            return None

    async def _sync_deliverable_to_convex(
        self,
        deliverable: Deliverable,
        convex_campaign_id: str
    ) -> Optional[str]:
        """
        Sync a deliverable to Convex for real-time updates.

        Args:
            deliverable: The deliverable to sync
            convex_campaign_id: The Convex campaign ID

        Returns:
            The Convex deliverable ID if successful
        """
        if not self._convex or not self.sync_to_convex:
            return None

        try:
            # Check if we already have a Convex ID for this deliverable
            existing_convex_id = self._convex_deliverable_ids.get(deliverable.id)

            if existing_convex_id:
                # Update existing deliverable
                await self._convex.update_deliverable(
                    deliverable_id=existing_convex_id,
                    data=deliverable.data,
                    status=deliverable.status,
                    platform=deliverable.platform
                )
                return existing_convex_id
            else:
                # Create new deliverable
                convex_id = await self._convex.create_deliverable(
                    campaign_id=convex_campaign_id,
                    deliverable_type=deliverable.type,
                    data=deliverable.data,
                    platform=deliverable.platform,
                    status=deliverable.status
                )
                self._convex_deliverable_ids[deliverable.id] = convex_id
                return convex_id

        except Exception as e:
            logger.error(f"Failed to sync deliverable to Convex: {e}")
            return None

    async def _sync_campaign_status_to_convex(
        self,
        convex_campaign_id: str,
        status: str
    ):
        """Sync campaign status to Convex."""
        if not self._convex or not self.sync_to_convex:
            return

        try:
            await self._convex.update_campaign_status(convex_campaign_id, status)
        except Exception as e:
            logger.error(f"Failed to sync campaign status to Convex: {e}")

    async def _sync_concepts_to_convex(
        self,
        convex_campaign_id: str,
        concepts: List[Concept],
        selected_index: Optional[int] = None
    ):
        """Sync creative concepts to Convex."""
        if not self._convex or not self.sync_to_convex:
            return

        try:
            concepts_data = [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "manifesto": c.manifesto,
                    "visual_world": c.visual_world,
                    "tone_of_voice": c.tone_of_voice
                }
                for c in concepts
            ]
            await self._convex.update_campaign_concepts(
                convex_campaign_id,
                concepts_data,
                selected_index
            )
        except Exception as e:
            logger.error(f"Failed to sync concepts to Convex: {e}")

    async def close(self):
        """Cleanup resources."""
        await self.llm.close()
        if self._convex:
            await self._convex.close()
