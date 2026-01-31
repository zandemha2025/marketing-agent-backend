"""
Campaign State Management

Tracks the full state of a campaign as it flows through departments.
This is the shared context that all departments can access.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class CampaignPhase(str, Enum):
    """Campaign execution phases."""
    INITIALIZING = "initializing"
    RESEARCHING = "researching"  # Quick campaign-specific research
    STRATEGIZING = "strategizing"  # Building strategy and concepts
    PITCHING = "pitching"  # Presenting to user for approval
    AWAITING_APPROVAL = "awaiting_approval"  # Waiting for user selection
    BRIEFING = "briefing"  # Creating creative briefs
    PRODUCING = "producing"  # Generating assets
    REFINING = "refining"  # User requested changes
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Deliverable:
    """A complete deliverable unit (bundled asset)."""
    id: str
    type: str  # social_post, video, email, landing_page, press_release, ad, strategy_doc, etc.
    platform: Optional[str] = None  # tiktok, instagram, facebook, linkedin, email, web
    status: str = "generating"  # generating, ready, approved, rejected

    # The bundled content - varies by type
    # Social post: {video/image, caption, hashtags, sound, timing}
    # Email: {subject_lines, preview, body_html, body_text}
    # Video: {video_url, script, voiceover, captions}
    # Landing page: {html, preview_image, sections}
    data: Dict[str, Any] = field(default_factory=dict)

    # For display ordering
    order: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Which department produced this
    source_department: Optional[str] = None

    # User feedback
    feedback: Optional[str] = None


@dataclass
class Concept:
    """A creative concept for the campaign."""
    id: str
    name: str
    description: str
    manifesto: str
    visual_world: str
    tone_of_voice: str
    channel_expressions: List[Dict[str, str]] = field(default_factory=list)

    # Mood board / visual previews
    mood_images: List[str] = field(default_factory=list)

    # Whether this concept was selected
    selected: bool = False


@dataclass
class CampaignState:
    """
    Full state of a campaign execution.

    This is the shared context that flows through all departments.
    The orchestrator updates this as work progresses.
    """

    # Identity
    campaign_id: str
    organization_id: str

    # User's original request
    user_request: str

    # Current phase
    phase: CampaignPhase = CampaignPhase.INITIALIZING

    # Progress within current phase (0.0 - 1.0)
    progress: float = 0.0

    # Current status message for UI
    status_message: str = ""

    # YOLO mode - skip approval gates
    yolo_mode: bool = False

    # === Knowledge Base (from onboarding) ===
    knowledge_base: Dict[str, Any] = field(default_factory=dict)

    # === Campaign-Specific Research (quick, targeted) ===
    campaign_research: Dict[str, Any] = field(default_factory=dict)

    # === Strategy Phase Outputs ===
    tension: Optional[Dict[str, Any]] = None  # Brand tension analysis
    concepts: List[Concept] = field(default_factory=list)
    selected_concept_index: Optional[int] = None
    strategy: Optional[Dict[str, Any]] = None

    # === Briefing Phase Outputs ===
    creative_briefs: List[Dict[str, Any]] = field(default_factory=list)

    # === Production Phase Outputs ===
    deliverables: List[Deliverable] = field(default_factory=list)

    # === Execution Tracking ===
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    # === Department Execution Log ===
    # Tracks what each department did (invisible to user, for debugging)
    department_log: List[Dict[str, Any]] = field(default_factory=list)

    # === Convex Sync ===
    # Convex campaign ID for real-time sync (optional)
    convex_campaign_id: Optional[str] = None

    @property
    def selected_concept(self) -> Optional[Concept]:
        """Get the currently selected concept."""
        if self.selected_concept_index is not None and self.concepts:
            if 0 <= self.selected_concept_index < len(self.concepts):
                return self.concepts[self.selected_concept_index]
        return None

    def select_concept(self, index: int) -> None:
        """Select a concept by index."""
        if 0 <= index < len(self.concepts):
            # Deselect all
            for c in self.concepts:
                c.selected = False
            # Select the chosen one
            self.concepts[index].selected = True
            self.selected_concept_index = index

    def add_deliverable(self, deliverable: Deliverable) -> None:
        """Add a deliverable and assign order."""
        deliverable.order = len(self.deliverables)
        self.deliverables.append(deliverable)

    def get_deliverables_by_type(self, type: str) -> List[Deliverable]:
        """Get all deliverables of a specific type."""
        return [d for d in self.deliverables if d.type == type]

    def get_deliverables_by_platform(self, platform: str) -> List[Deliverable]:
        """Get all deliverables for a specific platform."""
        return [d for d in self.deliverables if d.platform == platform]

    def log_department_action(
        self,
        department: str,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: int
    ) -> None:
        """Log a department's action (for debugging, invisible to user)."""
        self.department_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "department": department,
            "action": action,
            "input": input_data,
            "output": output_data,
            "duration_ms": duration_ms
        })

    def to_pitch_format(self) -> Dict[str, Any]:
        """
        Format state for the pitch/presentation moment.

        This is what gets sent to the frontend when presenting concepts.
        """
        return {
            "campaign_id": self.campaign_id,
            "phase": self.phase.value,
            "user_request": self.user_request,
            "research_summary": self._summarize_research(),
            "tension": self.tension,
            "concepts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "manifesto": c.manifesto,
                    "visual_world": c.visual_world,
                    "tone_of_voice": c.tone_of_voice,
                    "channel_expressions": c.channel_expressions,
                    "mood_images": c.mood_images,
                    "selected": c.selected
                }
                for c in self.concepts
            ],
            "strategy": self.strategy
        }

    def to_deliverables_format(self) -> Dict[str, Any]:
        """
        Format state for the deliverables panel.

        Groups deliverables by type/platform for organized display.
        """
        # Group by type
        by_type = {}
        for d in self.deliverables:
            if d.type not in by_type:
                by_type[d.type] = []
            by_type[d.type].append({
                "id": d.id,
                "platform": d.platform,
                "status": d.status,
                "data": d.data,
                "order": d.order,
                "source_department": d.source_department
            })

        return {
            "campaign_id": self.campaign_id,
            "phase": self.phase.value,
            "progress": self.progress,
            "status_message": self.status_message,
            "selected_concept": {
                "name": self.selected_concept.name,
                "description": self.selected_concept.description
            } if self.selected_concept else None,
            "deliverables_by_type": by_type,
            "total_count": len(self.deliverables),
            "ready_count": len([d for d in self.deliverables if d.status == "ready"]),
            "approved_count": len([d for d in self.deliverables if d.status == "approved"])
        }

    def _summarize_research(self) -> str:
        """Create a brief summary of the campaign research."""
        if not self.campaign_research:
            return "No additional research conducted."

        summaries = []
        if "competitor_analysis" in self.campaign_research:
            summaries.append("Analyzed current competitor positioning")
        if "cultural_research" in self.campaign_research:
            summaries.append("Identified relevant cultural moments and trends")
        if "topic_research" in self.campaign_research:
            summaries.append("Researched topic-specific insights")

        return ". ".join(summaries) + "." if summaries else "Research complete."
