"""
Chat API endpoints.

Intelligent chat interface for campaign creation and management.
Uses the knowledge base and campaign context to provide informed assistance.
All endpoints require authentication via JWT token.
"""
import asyncio
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import httpx

from ..core.config import get_settings
from ..core.database import get_session
from ..services.ai import OpenRouterService
from ..repositories.conversation import ConversationRepository
from ..repositories.knowledge_base import KnowledgeBaseRepository
from ..repositories.campaign import CampaignRepository
# Auth dependency available for securing endpoints
from .auth import get_current_user, get_current_active_user

logger = logging.getLogger(__name__)

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

IMPORTANT: When answering questions about the brand, ALWAYS reference the specific brand information provided in the context below. This includes:
- Brand name, description, tagline, and mission
- Brand voice and tone (how the brand communicates)
- Brand values (what the brand stands for)
- Products and services offered
- Competitors and market position
- Target audiences

When asked about "our brand voice", "our products", "our competitors", etc., provide specific answers using the brand context data. Do not give generic responses - use the actual brand information.

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
- The brand's voice, values, and identity (see context below)

IMPORTANT: Always reference the brand information provided in the context when making recommendations. Use the brand's actual voice/tone, values, and products in your responses.

Help the client refine their campaign, make strategic decisions, and optimize for success. Be opinionated but collaborative. Challenge assumptions constructively. Always tie recommendations back to campaign objectives and brand identity.""",

    "brief": """You are helping develop the creative brief for this campaign. Focus on:
- Clarifying business objectives
- Defining target audiences precisely
- Identifying key insights and tensions
- Crafting compelling messaging strategy
- Establishing creative guardrails

IMPORTANT: Reference the brand's voice, values, and products from the context below. Ensure the brief aligns with the brand's established identity.

Ask probing questions to uncover the real challenge. Push for specificity and strategic clarity.""",

    "creative": """You are the creative director developing concepts for this campaign. Focus on:
- Big ideas that capture attention
- Visual and tonal direction
- Copy and messaging refinement
- Platform-specific adaptations
- Creative executions across touchpoints

IMPORTANT: All creative work must align with the brand's voice/tone and values as specified in the context below. Reference specific brand attributes when presenting concepts.

Be bold and imaginative while staying true to strategy. Present options with clear rationale.""",

    "assets": """You are overseeing asset production for this campaign. Focus on:
- Ensuring brand consistency
- Optimizing for each platform
- Copy refinement and A/B variations
- Visual quality and impact
- Production timelines and priorities

IMPORTANT: All assets must reflect the brand's voice, values, and visual identity as specified in the context below. Reference specific brand guidelines when reviewing assets.

Help the client review, refine, and approve assets efficiently."""
}


# === Helper Functions ===

async def _get_llm_service():
    """Get LLM service."""
    settings = get_settings()
    return OpenRouterService(api_key=settings.openrouter_api_key)


def _format_voice_tone(voice_data: dict) -> str:
    """Format voice/tone data into readable string."""
    if not voice_data:
        return "Not specified"
    
    parts = []
    if voice_data.get('tone'):
        tone = voice_data['tone']
        if isinstance(tone, list):
            parts.append(f"Tone: {', '.join(tone)}")
        else:
            parts.append(f"Tone: {tone}")
    if voice_data.get('personality'):
        parts.append(f"Personality: {voice_data['personality']}")
    if voice_data.get('vocabulary'):
        vocab = voice_data['vocabulary']
        if isinstance(vocab, list):
            parts.append(f"Key vocabulary: {', '.join(vocab)}")
    if voice_data.get('avoid'):
        avoid = voice_data['avoid']
        if isinstance(avoid, list):
            parts.append(f"Words to avoid: {', '.join(avoid)}")
    if voice_data.get('sample_phrases'):
        phrases = voice_data['sample_phrases']
        if isinstance(phrases, list):
            parts.append(f"Sample phrases: {'; '.join(phrases[:3])}")
    
    return '\n  '.join(parts) if parts else str(voice_data)


def _format_competitors(competitors: list) -> str:
    """Format competitors list into readable string."""
    if not competitors:
        return "Not specified"
    
    formatted = []
    for comp in competitors[:5]:  # Limit to top 5
        if isinstance(comp, dict):
            name = comp.get('name', 'Unknown')
            positioning = comp.get('positioning', '')
            strengths = comp.get('strengths', [])
            if isinstance(strengths, list):
                strengths = ', '.join(strengths[:3])
            formatted.append(f"- {name}: {positioning} (Strengths: {strengths})")
        else:
            formatted.append(f"- {comp}")
    
    return '\n'.join(formatted) if formatted else "Not specified"


def _format_products(offerings_data: dict) -> str:
    """Format products/services into readable string."""
    if not offerings_data:
        return "Not specified"
    
    parts = []
    
    products = offerings_data.get('products', [])
    if products:
        parts.append("Products:")
        for prod in products[:5]:
            if isinstance(prod, dict):
                name = prod.get('name', 'Unknown')
                desc = prod.get('description', '')
                parts.append(f"  - {name}: {desc[:100]}..." if len(desc) > 100 else f"  - {name}: {desc}")
            else:
                parts.append(f"  - {prod}")
    
    services = offerings_data.get('services', [])
    if services:
        parts.append("Services:")
        for svc in services[:5]:
            if isinstance(svc, dict):
                name = svc.get('name', 'Unknown')
                desc = svc.get('description', '')
                parts.append(f"  - {name}: {desc[:100]}..." if len(desc) > 100 else f"  - {name}: {desc}")
            else:
                parts.append(f"  - {svc}")
    
    differentiators = offerings_data.get('key_differentiators', [])
    if differentiators:
        parts.append(f"Key Differentiators: {', '.join(differentiators[:5])}")
    
    return '\n'.join(parts) if parts else "Not specified"


def _format_values(values: list) -> str:
    """Format brand values into readable string."""
    if not values:
        return "Not specified"
    if isinstance(values, list):
        return ', '.join(values)
    return str(values)


async def _build_context(
    organization_id: str,
    campaign_id: Optional[str],
    context_type: str,
    session
) -> str:
    """
    Build context string from knowledge base and campaign data.
    
    This function creates a comprehensive brand context that enables the AI
    to answer questions about the brand's voice, products, competitors, etc.
    """
    context_parts = []

    # Get knowledge base
    kb_repo = KnowledgeBaseRepository(session)
    kb = await kb_repo.get_by_organization(organization_id)

    if kb:
        # Brand context - formatted for easy AI reference
        if kb.brand_data:
            brand = kb.brand_data
            brand_name = brand.get('name', 'Unknown')
            brand_description = brand.get('description', 'No description available')
            brand_tagline = brand.get('tagline', '')
            brand_mission = brand.get('mission', '')
            brand_values = _format_values(brand.get('values', []))
            brand_voice = _format_voice_tone(brand.get('voice', {}))
            
            context_parts.append(f"""
=== BRAND INFORMATION ===
Brand Name: {brand_name}
Tagline: {brand_tagline}
Description: {brand_description}
Mission: {brand_mission}

Brand Values: {brand_values}

Brand Voice/Tone:
  {brand_voice}
""")

        # Market context - formatted for competitor questions
        if kb.market_data:
            market = kb.market_data
            industry = market.get('industry', 'Not specified')
            market_position = market.get('market_position', 'Not specified')
            competitors_formatted = _format_competitors(market.get('competitors', []))
            
            trends = market.get('trends', [])
            trends_formatted = []
            for trend in trends[:5]:
                if isinstance(trend, dict):
                    trends_formatted.append(f"- {trend.get('trend', 'Unknown')}: {trend.get('opportunity', '')}")
                else:
                    trends_formatted.append(f"- {trend}")
            trends_str = '\n'.join(trends_formatted) if trends_formatted else "Not specified"
            
            context_parts.append(f"""
=== MARKET INTELLIGENCE ===
Industry: {industry}
Market Position: {market_position}

Competitors:
{competitors_formatted}

Market Trends:
{trends_str}
""")

        # Target audiences
        if kb.audiences_data:
            audiences = kb.audiences_data
            segments = audiences.get('segments', [])
            if segments:
                audience_parts = ["=== TARGET AUDIENCES ==="]
                for seg in segments[:3]:
                    if isinstance(seg, dict):
                        name = seg.get('name', 'Unknown Segment')
                        size = seg.get('size', '')
                        demographics = seg.get('demographics', {})
                        psychographics = seg.get('psychographics', {})
                        pain_points = seg.get('pain_points', [])
                        channels = seg.get('preferred_channels', [])
                        
                        audience_parts.append(f"\nSegment: {name} ({size})")
                        if demographics:
                            audience_parts.append(f"  Demographics: {json.dumps(demographics)}")
                        if psychographics:
                            audience_parts.append(f"  Psychographics: {json.dumps(psychographics)}")
                        if pain_points:
                            audience_parts.append(f"  Pain Points: {', '.join(pain_points[:5])}")
                        if channels:
                            audience_parts.append(f"  Preferred Channels: {', '.join(channels)}")
                
                context_parts.append('\n'.join(audience_parts))

        # Products & services - formatted for product questions
        if kb.offerings_data:
            products_formatted = _format_products(kb.offerings_data)
            context_parts.append(f"""
=== PRODUCTS & SERVICES ===
{products_formatted}
""")

        # Brand DNA (heritage, cultural impact, advertising strategy)
        if kb.brand_dna:
            dna = kb.brand_dna
            heritage = dna.get('heritage', '')
            cultural_impact = dna.get('cultural_impact', '')
            advertising_strategy = dna.get('advertising_strategy', '')
            
            dna_parts = ["=== BRAND DNA ==="]
            if heritage:
                dna_parts.append(f"Heritage: {heritage[:500]}..." if len(heritage) > 500 else f"Heritage: {heritage}")
            if cultural_impact:
                dna_parts.append(f"Cultural Impact: {cultural_impact[:500]}..." if len(cultural_impact) > 500 else f"Cultural Impact: {cultural_impact}")
            if advertising_strategy:
                dna_parts.append(f"Advertising Strategy: {advertising_strategy[:500]}..." if len(advertising_strategy) > 500 else f"Advertising Strategy: {advertising_strategy}")
            
            if len(dna_parts) > 1:
                context_parts.append('\n'.join(dna_parts))

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
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """List conversations for an organization. Requires authentication."""
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
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Create a new conversation. Requires authentication."""
    repo = ConversationRepository(session)

    conversation = await repo.create({
        "organization_id": request.organization_id,
        "campaign_id": request.campaign_id,
        "title": request.title or "New Conversation",
        "context_type": request.context_type
    })

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
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Get conversation with messages. Requires authentication."""
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
                "metadata": m.extra_data  # Use extra_data (column name) instead of metadata
            }
            for m in messages
        ]
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: MessageRequest,
    stream: bool = True,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """
    Send a message and get AI response. Requires authentication.

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
            error_occurred = False
            try:
                # Test connection first
                connection_test = await llm.test_connection()
                if connection_test.get("status") != "connected":
                    error_msg = "AI service is currently unavailable. Please try again in a moment."
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
                    error_occurred = True
                    return

                async for chunk in llm.stream(
                    prompt=request.content,
                    system=full_system,
                    history=history[:-1] if history else None  # Exclude current message
                ):
                    full_response.append(chunk)
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                # Save assistant message
                assistant_content = "".join(full_response)
                if assistant_content.strip():
                    await repo.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=assistant_content
                    )

                yield f"data: {json.dumps({'done': True})}\n\n"
            except httpx.TimeoutException:
                error_msg = "The AI is taking longer than expected. Please try a shorter message or try again."
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                error_occurred = True
            except httpx.HTTPStatusError as e:
                error_msg = f"AI service error: {e.response.status_code}. Please try again."
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                error_occurred = True
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                error_msg = "Something went wrong. Please try again."
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                error_occurred = True
            finally:
                # Save error message if something went wrong
                if error_occurred and full_response:
                    try:
                        partial_content = "".join(full_response)
                        if partial_content.strip():
                            await repo.add_message(
                                conversation_id=conversation_id,
                                role="assistant",
                                content=partial_content + "\n\n[Error: Response incomplete]"
                            )
                    except Exception as save_error:
                        logger.debug(f"Failed to save partial response after error: {save_error}")
                await llm.close()

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Important for nginx proxies
                "Content-Type": "text/event-stream",
            }
        )
    else:
        try:
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

            return {
                "content": response,
                "response": response,
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
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="The AI is taking longer than expected. Please try a shorter message or try again."
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"AI service error ({e.response.status_code}). Please try again."
            )
        except Exception as e:
            logger.error(f"Non-streaming chat error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Something went wrong. Please try again."
            )
        finally:
            await llm.close()


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user=Depends(get_current_active_user),
    session=Depends(get_session)
):
    """Delete a conversation. Requires authentication."""
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
        except Exception as close_error:
            logger.debug(f"LLM client close error (may already be closed): {close_error}")


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
