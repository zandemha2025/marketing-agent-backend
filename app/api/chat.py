"""
Chat API endpoints.

Intelligent chat interface for campaign creation and management.
Uses the knowledge base and campaign context to provide informed assistance.
"""
import asyncio
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from ..core.config import get_settings
from ..core.database import get_session
from ..services.ai import OpenRouterService
from ..repositories.conversation import ConversationRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository
from ..repositories.campaign import CampaignRepository

router = APIRouter()


# === Pydantic Models ===

class ConversationCreateRequest(BaseModel):
    """Request to create a conversation."""
    organization_id: str
    campaign_id: Optional[str] = None
    title: Optional[str] = None
    context_type: str = Field("general", description="Type: general, campaign, brief, creative, assets")


class MessageRequest(BaseModel):
    """Request to send a message."""
    content: str
    attachments: Optional[List[dict]] = None


class MessageResponse(BaseModel):
    """Message response model."""
    id: str
    role: str
    content: str
    created_at: datetime
    metadata: Optional[dict] = None


class ConversationResponse(BaseModel):
    """Conversation response model."""
    id: str
    organization_id: str
    campaign_id: Optional[str]
    title: str
    context_type: str
    created_at: datetime
    message_count: int


class ConversationListResponse(BaseModel):
    """List of conversations."""
    conversations: List[ConversationResponse]
    total: int


# === System Prompts ===

SYSTEM_PROMPTS = {
    "general": """You are a world-class marketing strategist with expertise across all aspects of marketing - brand strategy, creative development, media planning, and campaign execution.

You work for a leading marketing agency and help clients create exceptional campaigns. You have access to the client's knowledge base which includes their brand information, market data, target audiences, and past campaign history.

Be direct, insightful, and proactive. Anticipate needs and provide strategic recommendations backed by marketing best practices. Always think about:
- Business objectives and how marketing supports them
- Target audience insights and motivation
- Competitive differentiation
- Channel strategy and media mix
- Creative excellence
- Measurement and optimization

When discussing campaigns, be specific and actionable. Avoid generic advice - leverage the client's unique context.""",

    "campaign": """You are the lead strategist on this campaign. You have full context on:
- The campaign brief and objectives
- Target audiences and their motivations
- Creative concepts being explored
- Assets being produced

Help the client refine their campaign, make strategic decisions, and optimize for success. Be opinionated but collaborative. Challenge assumptions constructively. Always tie recommendations back to campaign objectives.""",

    "brief": """You are helping develop the creative brief for this campaign. Focus on:
- Clarifying business objectives
- Defining target audiences precisely
- Identifying key insights and tensions
- Crafting compelling messaging strategy
- Establishing creative guardrails

Ask probing questions to uncover the real challenge. Push for specificity and strategic clarity.""",

    "creative": """You are the creative director developing concepts for this campaign. Focus on:
- Big ideas that capture attention
- Visual and tonal direction
- Copy and messaging refinement
- Platform-specific adaptations
- Creative executions across touchpoints

Be bold and imaginative while staying true to strategy. Present options with clear rationale.""",

    "assets": """You are overseeing asset production for this campaign. Focus on:
- Ensuring brand consistency
- Optimizing for each platform
- Copy refinement and A/B variations
- Visual quality and impact
- Production timelines and priorities

Help the client review, refine, and approve assets efficiently."""
}


# === Helper Functions ===

async def _get_llm_service():
    """Get LLM service."""
    settings = get_settings()
    return OpenRouterService(api_key=settings.openrouter_api_key)


async def _build_context(
    organization_id: str,
    campaign_id: Optional[str],
    context_type: str,
    session
) -> str:
    """Build context string from knowledge base and campaign data."""
    context_parts = []

    # Get knowledge base
    kb_repo = KnowledgeBaseRepository(session)
    kb = await kb_repo.get_by_organization(organization_id)

    if kb:
        # Brand context
        if kb.brand_data:
            brand = kb.brand_data
            context_parts.append(f"""
BRAND CONTEXT:
- Name: {brand.get('name', 'Unknown')}
- Description: {brand.get('description', '')}
- Voice/Tone: {brand.get('voice', {})}
- Visual Identity: {brand.get('visual_identity', {})}
""")

        # Market context
        if kb.market_data:
            market = kb.market_data
            context_parts.append(f"""
MARKET CONTEXT:
- Industry: {market.get('industry', '')}
- Competitors: {market.get('competitors', [])}
- Trends: {market.get('trends', [])}
""")

        # Target audiences
        if kb.audiences_data:
            audiences = kb.audiences_data
            context_parts.append(f"""
TARGET AUDIENCES:
{json.dumps(audiences, indent=2)}
""")

    # Get campaign context if applicable
    if campaign_id:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if campaign:
            context_parts.append(f"""
CURRENT CAMPAIGN:
- Name: {campaign.name}
- Objective: {campaign.objective}
- Status: {campaign.status}
""")

            if campaign.brief_data:
                context_parts.append(f"""
CAMPAIGN BRIEF:
{json.dumps(campaign.brief_data, indent=2)}
""")

            if campaign.creative_concepts:
                context_parts.append(f"""
CREATIVE CONCEPTS:
{json.dumps(campaign.creative_concepts, indent=2)}
""")

    return "\n".join(context_parts) if context_parts else "No additional context available."


async def _get_conversation_history(
    conversation_id: str,
    session,
    limit: int = 20
) -> List[dict]:
    """Get recent conversation history."""
    repo = ConversationRepository(session)
    messages = await repo.get_messages(conversation_id, limit=limit)

    return [
        {"role": m.role.value if hasattr(m.role, 'value') else m.role, "content": m.content}
        for m in reversed(messages)  # Oldest first
    ]


# === REST Endpoints ===

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    organization_id: str,
    campaign_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    session=Depends(get_session)
):
    """List conversations for an organization."""
    repo = ConversationRepository(session)

    if campaign_id:
        conversations = await repo.get_by_campaign(campaign_id, limit, offset)
    else:
        conversations = await repo.get_by_organization(organization_id, limit, offset)

    total = await repo.count_by_organization(organization_id)

    return ConversationListResponse(
        conversations=[
            ConversationResponse(
                id=c.id,
                organization_id=c.organization_id,
                campaign_id=c.campaign_id,
                title=c.title or "Untitled",
                context_type=c.context_type or "general",
                created_at=c.created_at,
                message_count=c.message_count if hasattr(c, 'message_count') else 0
            )
            for c in conversations
        ],
        total=total
    )


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    session=Depends(get_session)
):
    """Create a new conversation."""
    repo = ConversationRepository(session)

    conversation = await repo.create(
        organization_id=request.organization_id,
        campaign_id=request.campaign_id,
        title=request.title or "New Conversation",
        context_type=request.context_type
    )

    return ConversationResponse(
        id=conversation.id,
        organization_id=conversation.organization_id,
        campaign_id=conversation.campaign_id,
        title=conversation.title or "New Conversation",
        context_type=conversation.context_type or "general",
        created_at=conversation.created_at,
        message_count=0
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    session=Depends(get_session)
):
    """Get conversation with messages."""
    repo = ConversationRepository(session)
    conversation = await repo.get_by_id(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await repo.get_messages(conversation_id)

    return {
        "id": conversation.id,
        "organization_id": conversation.organization_id,
        "campaign_id": conversation.campaign_id,
        "title": conversation.title,
        "context_type": conversation.context_type,
        "created_at": conversation.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role.value if hasattr(m.role, 'value') else m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
                "metadata": m.metadata
            }
            for m in messages
        ]
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: MessageRequest,
    stream: bool = True,
    session=Depends(get_session)
):
    """
    Send a message and get AI response.

    Set stream=true for streaming response, stream=false for complete response.
    """
    repo = ConversationRepository(session)
    conversation = await repo.get_by_id(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message
    user_message = await repo.add_message(
        conversation_id=conversation_id,
        role="user",
        content=request.content,
        metadata={"attachments": request.attachments} if request.attachments else None
    )

    # Build context
    context = await _build_context(
        conversation.organization_id,
        conversation.campaign_id,
        conversation.context_type or "general",
        session
    )

    # Get conversation history
    history = await _get_conversation_history(conversation_id, session)

    # Build system prompt
    system_prompt = SYSTEM_PROMPTS.get(conversation.context_type or "general", SYSTEM_PROMPTS["general"])
    full_system = f"{system_prompt}\n\n{context}"

    # Get LLM response
    llm = await _get_llm_service()

    if stream:
        async def generate_stream():
            full_response = []

            async for chunk in llm.stream(
                prompt=request.content,
                system=full_system,
                history=history[:-1] if history else None  # Exclude current message
            ):
                full_response.append(chunk)
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Save assistant message
            assistant_content = "".join(full_response)
            await repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content
            )

            yield f"data: {json.dumps({'done': True})}\n\n"

            await llm.close()

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream"
        )
    else:
        # Non-streaming response - use chat() for multi-turn history
        messages = [{"role": "system", "content": full_system}]
        if history and len(history) > 1:
            messages.extend(history[:-1])  # Exclude current message
        messages.append({"role": "user", "content": request.content})
        response = await llm.chat(messages=messages)

        # Save assistant message
        assistant_message = await repo.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response
        )

        await llm.close()

        return {
            "user_message": {
                "id": user_message.id,
                "role": "user",
                "content": request.content,
                "created_at": user_message.created_at.isoformat()
            },
            "assistant_message": {
                "id": assistant_message.id,
                "role": "assistant",
                "content": response,
                "created_at": assistant_message.created_at.isoformat()
            }
        }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    session=Depends(get_session)
):
    """Delete a conversation."""
    repo = ConversationRepository(session)
    conversation = await repo.get_by_id(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await repo.delete(conversation_id)

    return {"status": "deleted", "id": conversation_id}


# === WebSocket Endpoint ===

@router.websocket("/conversations/{conversation_id}/ws")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: str
):
    """
    WebSocket endpoint for real-time chat.

    Send: {"content": "your message"}
    Receive: {"type": "chunk", "content": "..."} or {"type": "done"}
    """
    await websocket.accept()

    try:
        async with get_session() as session:
            repo = ConversationRepository(session)
            conversation = await repo.get_by_id(conversation_id)

            if not conversation:
                await websocket.send_json({
                    "type": "error",
                    "message": "Conversation not found"
                })
                await websocket.close()
                return

            # Build static context once
            context = await _build_context(
                conversation.organization_id,
                conversation.campaign_id,
                conversation.context_type or "general",
                session
            )

            system_prompt = SYSTEM_PROMPTS.get(
                conversation.context_type or "general",
                SYSTEM_PROMPTS["general"]
            )
            full_system = f"{system_prompt}\n\n{context}"

            await websocket.send_json({
                "type": "connected",
                "conversation_id": conversation_id
            })

            llm = await _get_llm_service()

            while True:
                # Receive message
                data = await websocket.receive_json()
                user_content = data.get("content", "")

                if not user_content:
                    continue

                # Save user message
                await repo.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_content
                )

                # Get history
                history = await _get_conversation_history(conversation_id, session)

                # Stream response
                full_response = []

                async for chunk in llm.stream(
                    prompt=user_content,
                    system=full_system,
                    history=history[:-1] if history else None
                ):
                    full_response.append(chunk)
                    await websocket.send_json({
                        "type": "chunk",
                        "content": chunk
                    })

                # Save assistant message
                assistant_content = "".join(full_response)
                await repo.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_content
                )

                await websocket.send_json({
                    "type": "done",
                    "full_content": assistant_content
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        try:
            await llm.close()
        except Exception:
            pass  # LLM client may already be closed


# === Quick Chat Endpoint (No History) ===

@router.post("/quick")
async def quick_chat(
    organization_id: str,
    content: str,
    context_type: str = "general",
    session=Depends(get_session)
):
    """
    Quick one-off chat without creating a conversation.
    Useful for simple questions or quick assistance.
    """
    # Build context
    context = await _build_context(
        organization_id,
        None,
        context_type,
        session
    )

    system_prompt = SYSTEM_PROMPTS.get(context_type, SYSTEM_PROMPTS["general"])
    full_system = f"{system_prompt}\n\n{context}"

    llm = await _get_llm_service()

    try:
        response = await llm.complete(
            prompt=content,
            system=full_system
        )

        return {
            "response": response
        }
    finally:
        await llm.close()
