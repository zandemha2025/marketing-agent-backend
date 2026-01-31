"""
Orchestrator API

WebSocket-based API for the intelligent campaign orchestrator.
Provides real-time updates as campaigns progress through phases.
"""

import json
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel, Field

from ..core.config import get_settings
from ..core.database import get_session
from ..services.orchestrator import OrchestratorBrain, CampaignState, CampaignPhase
from ..repositories.campaign import CampaignRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository

logger = logging.getLogger(__name__)
router = APIRouter()

# Active orchestrator sessions
_active_sessions: dict[str, dict] = {}


# === Pydantic Models ===

class CampaignStartRequest(BaseModel):
    """Request to start a new campaign."""
    organization_id: str
    name: str
    request: str = Field(..., description="What the user wants to create")
    yolo_mode: bool = Field(False, description="Skip approval gates")
    convex_campaign_id: Optional[str] = Field(None, description="Convex campaign ID for real-time sync")


class ConceptSelectRequest(BaseModel):
    """Request to select a concept."""
    concept_index: int


class DeliverableRefineRequest(BaseModel):
    """Request to refine a deliverable."""
    deliverable_id: str
    feedback: str


class ChatMessageRequest(BaseModel):
    """Chat message in campaign context."""
    message: str
    selected_deliverable_id: Optional[str] = None


# === REST Endpoints ===

@router.post("/start")
async def start_campaign(
    request: CampaignStartRequest,
    session=Depends(get_session)
):
    """
    Start a new campaign with the orchestrator.

    Returns a session_id to connect via WebSocket for real-time updates.
    """
    settings = get_settings()

    # Get knowledge base
    kb_repo = KnowledgeBaseRepository(session)
    kb = await kb_repo.get_by_organization(request.organization_id)

    if not kb:
        raise HTTPException(
            status_code=400,
            detail="Organization has no knowledge base. Complete onboarding first."
        )

    knowledge_base = {
        "brand": kb.brand_data or {},
        "market": kb.market_data or {},
        "audiences": kb.audiences_data or {},
        "offerings": kb.offerings_data or {},
        "context": kb.context_data or {}
    }

    # Create campaign record
    campaign_repo = CampaignRepository(session)
    campaign = await campaign_repo.create(
        organization_id=request.organization_id,
        name=request.name,
        objective=request.request,
        status="initializing",
        config={
            "yolo_mode": request.yolo_mode,
            "user_request": request.request
        }
    )

    # Create session
    import uuid
    session_id = uuid.uuid4().hex

    _active_sessions[session_id] = {
        "campaign_id": campaign.id,
        "organization_id": request.organization_id,
        "knowledge_base": knowledge_base,
        "yolo_mode": request.yolo_mode,
        "user_request": request.request,
        "convex_campaign_id": request.convex_campaign_id,
        "websocket": None,
        "state": None
    }

    return {
        "session_id": session_id,
        "campaign_id": campaign.id,
        "convex_campaign_id": request.convex_campaign_id,
        "websocket_url": f"/api/orchestrator/{session_id}/ws",
        "message": "Connect to WebSocket to begin campaign creation"
    }


@router.get("/{session_id}/state")
async def get_campaign_state(session_id: str):
    """Get current state of a campaign session."""
    session_data = _active_sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session_data.get("state")
    if not state:
        return {"phase": "not_started", "message": "Connect via WebSocket to start"}

    if state.phase == CampaignPhase.AWAITING_APPROVAL:
        return state.to_pitch_format()
    else:
        return state.to_deliverables_format()


@router.post("/{session_id}/select-concept")
async def select_concept(
    session_id: str,
    request: ConceptSelectRequest,
    db_session=Depends(get_session)
):
    """
    Select a concept and continue campaign.

    Called when user clicks "Go with this concept" in the pitch.
    """
    session_data = _active_sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session_data.get("state")
    if not state:
        raise HTTPException(status_code=400, detail="Campaign not started")

    if state.phase != CampaignPhase.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot select concept in {state.phase} phase"
        )

    # Continue will happen via WebSocket
    session_data["pending_selection"] = request.concept_index

    return {
        "status": "pending",
        "message": "Selection received. Continue via WebSocket."
    }


# === WebSocket Endpoint ===

@router.websocket("/{session_id}/ws")
async def orchestrator_websocket(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket for real-time campaign orchestration.

    Events sent to client:
    - {type: "connected", session_id: str}
    - {type: "phase", phase: str, message: str, progress: float}
    - {type: "pitch", data: {concepts: [...], strategy: {...}}}
    - {type: "deliverable", deliverable: {...}}
    - {type: "complete", data: {...}}
    - {type: "error", message: str}

    Events from client:
    - {action: "start"} - Begin campaign
    - {action: "select_concept", index: int} - Select concept
    - {action: "refine", deliverable_id: str, feedback: str} - Refine deliverable
    - {action: "chat", message: str, deliverable_id?: str} - Chat message
    """
    await websocket.accept()

    session_data = _active_sessions.get(session_id)
    if not session_data:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid session ID"
        })
        await websocket.close()
        return

    session_data["websocket"] = websocket

    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "campaign_id": session_data["campaign_id"]
    })

    settings = get_settings()
    brain = OrchestratorBrain(
        openrouter_api_key=settings.openrouter_api_key,
        firecrawl_api_key=settings.firecrawl_api_key,
        perplexity_api_key=settings.perplexity_api_key,
        segmind_api_key=settings.segmind_api_key,
        elevenlabs_api_key=settings.elevenlabs_api_key
    )

    async def progress_callback(state: CampaignState):
        """Send state updates to client."""
        try:
            if state.phase == CampaignPhase.AWAITING_APPROVAL:
                # Send pitch data
                await websocket.send_json({
                    "type": "pitch",
                    "phase": state.phase.value,
                    "message": state.status_message,
                    "data": state.to_pitch_format()
                })
            elif state.phase == CampaignPhase.PRODUCING:
                # Send each new deliverable
                if state.deliverables:
                    latest = state.deliverables[-1]
                    await websocket.send_json({
                        "type": "deliverable",
                        "phase": state.phase.value,
                        "progress": state.progress,
                        "message": state.status_message,
                        "deliverable": {
                            "id": latest.id,
                            "type": latest.type,
                            "platform": latest.platform,
                            "status": latest.status,
                            "data": latest.data
                        }
                    })
            else:
                # Send phase update
                await websocket.send_json({
                    "type": "phase",
                    "phase": state.phase.value,
                    "progress": state.progress,
                    "message": state.status_message
                })
        except Exception as e:
            logger.error(f"Progress callback error: {e}")

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "start":
                # Start campaign execution
                state = await brain.start_campaign(
                    campaign_id=session_data["campaign_id"],
                    organization_id=session_data["organization_id"],
                    user_request=session_data["user_request"],
                    knowledge_base=session_data["knowledge_base"],
                    yolo_mode=session_data["yolo_mode"],
                    progress_callback=progress_callback,
                    convex_campaign_id=session_data.get("convex_campaign_id")
                )
                session_data["state"] = state

                if state.phase == CampaignPhase.COMPLETE:
                    await websocket.send_json({
                        "type": "complete",
                        "data": state.to_deliverables_format()
                    })

            elif action == "select_concept":
                # Continue after concept selection
                index = data.get("index", 0)
                state = session_data.get("state")

                if not state:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No campaign in progress"
                    })
                    continue

                state = await brain.continue_after_approval(
                    campaign_id=session_data["campaign_id"],
                    selected_concept_index=index,
                    progress_callback=progress_callback
                )
                session_data["state"] = state

                if state.phase == CampaignPhase.COMPLETE:
                    await websocket.send_json({
                        "type": "complete",
                        "data": state.to_deliverables_format()
                    })

            elif action == "refine":
                # Refine a deliverable
                deliverable_id = data.get("deliverable_id")
                feedback = data.get("feedback")

                if not deliverable_id or not feedback:
                    await websocket.send_json({
                        "type": "error",
                        "message": "deliverable_id and feedback required"
                    })
                    continue

                deliverable = await brain.refine_deliverable(
                    campaign_id=session_data["campaign_id"],
                    deliverable_id=deliverable_id,
                    feedback=feedback,
                    progress_callback=progress_callback
                )

                await websocket.send_json({
                    "type": "refinement_complete",
                    "deliverable": {
                        "id": deliverable.id,
                        "type": deliverable.type,
                        "platform": deliverable.platform,
                        "status": deliverable.status,
                        "data": deliverable.data
                    }
                })

            elif action == "chat":
                # Handle chat message
                message = data.get("message")
                deliverable_id = data.get("deliverable_id")

                if not message:
                    continue

                result = await brain.handle_chat_message(
                    campaign_id=session_data["campaign_id"],
                    message=message,
                    selected_deliverable_id=deliverable_id,
                    progress_callback=progress_callback
                )

                await websocket.send_json({
                    "type": "chat_response",
                    "data": result
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {action}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
    finally:
        session_data["websocket"] = None
        await brain.close()


# === Panel State Endpoint ===

@router.get("/{session_id}/panel")
async def get_panel_state(
    session_id: str,
    panel: str = "context"  # "context" or "deliverables"
):
    """
    Get the current state for a specific panel.

    - panel=context: Progress, working folder, context (during work)
    - panel=deliverables: The deliverables feed (when ready)
    """
    session_data = _active_sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session_data.get("state")

    if panel == "deliverables":
        if not state:
            return {"deliverables": [], "phase": "not_started"}

        return state.to_deliverables_format()

    else:  # context
        if not state:
            return {
                "phase": "not_started",
                "progress": 0,
                "message": "Connect via WebSocket to start"
            }

        return {
            "phase": state.phase.value,
            "progress": state.progress,
            "message": state.status_message,
            "has_concepts": len(state.concepts) > 0,
            "has_deliverables": len(state.deliverables) > 0,
            "concept_count": len(state.concepts),
            "deliverable_count": len(state.deliverables)
        }
