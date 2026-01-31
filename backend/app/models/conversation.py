"""
Conversation and Message models for chat functionality.
"""
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON, Text
from sqlalchemy.orm import relationship

from .base import Base


class ConversationScope(str, Enum):
    """Scope of a conversation."""
    GLOBAL = "global"       # General chat, not tied to specific content
    CAMPAIGN = "campaign"   # Scoped to a campaign
    ASSET = "asset"         # Scoped to a specific asset


class MessageRole(str, Enum):
    """Who sent the message."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base):
    """
    Conversation thread.

    Can be:
    - Global (general chat, campaign creation)
    - Campaign-scoped (discussing campaign strategy)
    - Asset-scoped (working on a specific asset)
    """

    organization_id = Column(
        String(12),
        ForeignKey("organizations.id"),
        nullable=False
    )

    # Scope
    scope = Column(
        SQLEnum(ConversationScope),
        default=ConversationScope.GLOBAL,
        nullable=False
    )

    # Context type for chat (general, campaign, brief, creative, assets)
    context_type = Column(String(50), default="general", nullable=False)

    # Optional references based on scope
    campaign_id = Column(
        String(12),
        ForeignKey("campaigns.id"),
        nullable=True
    )
    asset_id = Column(
        String(12),
        ForeignKey("assets.id"),
        nullable=True
    )

    # Title (auto-generated or user-set)
    title = Column(String(255), nullable=True)

    # Extra data (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    extra_data = Column(JSON, default=dict, nullable=False)

    # Relationships
    organization = relationship("Organization")
    campaign = relationship("Campaign", back_populates="conversations")
    asset = relationship("Asset")
    messages = relationship(
        "Message",
        back_populates="conversation",
        order_by="Message.created_at"
    )

    def __repr__(self):
        return f"<Conversation {self.scope.value} {self.id[:6]}>"

    def get_context(self) -> Dict[str, Any]:
        """
        Get context for AI based on conversation scope.
        Used to provide relevant information to Claude.
        """
        context = {
            "scope": self.scope.value,
            "organization_id": self.organization_id,
        }

        if self.campaign_id and self.campaign:
            context["campaign"] = self.campaign.get_brief_summary()

        if self.asset_id and self.asset:
            context["asset"] = self.asset.to_preview_format()

        return context

    def get_messages_for_ai(self, limit: int = 50) -> List[Dict[str, str]]:
        """
        Get messages formatted for Claude API.
        Returns most recent messages up to limit.
        """
        recent_messages = self.messages[-limit:] if len(self.messages) > limit else self.messages

        return [
            {"role": m.role.value, "content": m.content}
            for m in recent_messages
            if m.role != MessageRole.SYSTEM  # System messages handled separately
        ]


class Message(Base):
    """
    Individual message in a conversation.
    """

    conversation_id = Column(
        String(12),
        ForeignKey("conversations.id"),
        nullable=False
    )

    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # User who sent (if role=user)
    user_id = Column(String(12), ForeignKey("users.id"), nullable=True)

    # Rich message data for UI (JSONB)
    # Structure:
    # {
    #     "options": [  # Quick reply buttons
    #         {"label": "...", "value": "..."},
    #     ],
    #     "brand_card": {...},  # Rendered brand card
    #     "asset_preview": {...},  # Asset being discussed
    #     "brief_preview": {...},  # Campaign brief preview
    #     "loading": true,  # Show loading state
    #     "loading_text": "Generating...",
    #     "artifacts": [  # Generated artifacts
    #         {"type": "image", "url": "..."},
    #         {"type": "document", "id": "..."},
    #     ]
    # }
    extra_data = Column(JSON, default=dict, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User")

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message {self.role.value}: {preview}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "metadata": self.extra_data,  # Keep API response key as 'metadata' for compatibility
            "created_at": self.created_at.isoformat(),
            "user": {
                "id": self.user.id,
                "name": self.user.name,
                "avatar_url": self.user.avatar_url,
            } if self.user else None,
        }

    @property
    def has_options(self) -> bool:
        """Check if message has quick reply options."""
        return bool(self.extra_data.get("options"))

    @property
    def options(self) -> List[Dict[str, str]]:
        """Get quick reply options."""
        return self.extra_data.get("options", [])
