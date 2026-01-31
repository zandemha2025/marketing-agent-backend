"""
Conversation repository for chat functionality.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.conversation import Conversation, Message, MessageRole


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for conversation operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return await self.get(conversation_id)

    async def get_by_organization(
        self,
        organization_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Conversation]:
        """Get conversations for an organization."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.organization_id == organization_id)
            .order_by(desc(Conversation.updated_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_campaign(
        self,
        campaign_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Conversation]:
        """Get conversations for a campaign."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.campaign_id == campaign_id)
            .order_by(desc(Conversation.updated_at))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_organization(self, organization_id: str) -> int:
        """Count conversations for an organization."""
        result = await self.session.execute(
            select(func.count(Conversation.id))
            .where(Conversation.organization_id == organization_id)
        )
        return result.scalar_one()

    async def create(self, data: Dict[str, Any]) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            organization_id=data["organization_id"],
            campaign_id=data.get("campaign_id"),
            title=data.get("title", "New Conversation"),
            context_type=data.get("context_type", "general"),
            metadata=data.get("metadata", {})
        )
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def update(self, conversation_id: str, data: Dict[str, Any]) -> Optional[Conversation]:
        """Update a conversation."""
        conversation = await self.get(conversation_id)
        if conversation:
            for key, value in data.items():
                if hasattr(conversation, key) and value is not None:
                    setattr(conversation, key, value)
            await self.session.flush()
            await self.session.refresh(conversation)
        return conversation

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        """Get messages for a conversation."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Add a message to a conversation."""
        # Map role string to enum
        role_enum = MessageRole(role) if isinstance(role, str) else role

        message = Message(
            conversation_id=conversation_id,
            role=role_enum,
            content=content,
            user_id=user_id,
            metadata=metadata or {}
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)

        # Update conversation timestamp
        conversation = await self.get(conversation_id)
        if conversation:
            await self.session.flush()

        return message

    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Message]:
        """Get most recent messages for a conversation."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def count_messages(self, conversation_id: str) -> int:
        """Count messages in a conversation."""
        result = await self.session.execute(
            select(func.count(Message.id))
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar_one()
