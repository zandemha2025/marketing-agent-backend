"""
Asset and Version models for creative deliverables.
"""
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, JSON, Integer, Text, Boolean
from sqlalchemy.orm import relationship

from .base import Base


class AssetType(str, Enum):
    """Types of marketing assets."""
    # Documents
    BRIEF = "brief"
    STRATEGY_DECK = "strategy_deck"
    CREATIVE_BRIEF = "creative_brief"
    COPY_DOC = "copy_doc"

    # Email
    EMAIL_CAMPAIGN = "email_campaign"
    EMAIL_DRIP = "email_drip"
    NEWSLETTER = "newsletter"

    # Social
    SOCIAL_POST = "social_post"
    SOCIAL_STORY = "social_story"
    SOCIAL_CAROUSEL = "social_carousel"
    SOCIAL_REEL = "social_reel"

    # Paid
    DISPLAY_AD = "display_ad"
    SEARCH_AD = "search_ad"
    SOCIAL_AD = "social_ad"
    VIDEO_AD = "video_ad"

    # Web
    LANDING_PAGE = "landing_page"
    HERO_SECTION = "hero_section"
    PRODUCT_PAGE = "product_page"
    BLOG_POST = "blog_post"

    # Print
    POSTER = "poster"
    FLYER = "flyer"
    BILLBOARD = "billboard"

    # Video
    VIDEO_SCRIPT = "video_script"
    STORYBOARD = "storyboard"


class AssetStatus(str, Enum):
    """Asset workflow status."""
    DRAFT = "draft"                 # Initial creation
    IN_REVIEW = "in_review"         # Waiting for feedback
    NEEDS_CHANGES = "needs_changes" # Feedback received, needs revision
    APPROVED = "approved"           # Ready for use
    PUBLISHED = "published"         # Live/deployed


class Asset(Base):
    """
    Marketing Asset - a creative deliverable.

    Each asset:
    - Has a type (email, social post, landing page, etc.)
    - Belongs to a campaign (and optionally a phase)
    - Has version history
    - Can have comments
    - Goes through approval workflow
    """

    campaign_id = Column(
        String(12),
        ForeignKey("campaigns.id"),
        nullable=False
    )
    phase_id = Column(
        String(12),
        ForeignKey("campaign_phases.id"),
        nullable=True  # Some assets might not be tied to a specific phase
    )

    # Basic info
    name = Column(String(255), nullable=False)
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    description = Column(Text, nullable=True)

    # Versioning
    current_version = Column(Integer, default=1, nullable=False)

    # Status
    status = Column(
        SQLEnum(AssetStatus),
        default=AssetStatus.DRAFT,
        nullable=False
    )

    # Platform-specific (for social/ads)
    platform = Column(String(50), nullable=True)  # twitter, linkedin, facebook, etc.

    # Creator
    created_by = Column(String(12), ForeignKey("users.id"), nullable=False)

    # Is this a branch/variant of another asset?
    branched_from = Column(String(12), ForeignKey("assets.id"), nullable=True)
    is_branch = Column(Boolean, default=False, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="assets")
    phase = relationship("CampaignPhase", back_populates="assets")
    created_by_user = relationship(
        "User",
        back_populates="created_assets",
        foreign_keys=[created_by]
    )
    versions = relationship(
        "AssetVersion",
        back_populates="asset",
        order_by="AssetVersion.version_number"
    )
    comments = relationship("AssetComment", back_populates="asset")

    def __repr__(self):
        return f"<Asset {self.name} ({self.asset_type.value}) v{self.current_version}>"

    @property
    def current_content(self) -> Optional[Dict[str, Any]]:
        """Get the content of the current version."""
        for v in self.versions:
            if v.version_number == self.current_version:
                return v.content
        return None

    def get_version(self, version_number: int) -> Optional["AssetVersion"]:
        """Get a specific version."""
        for v in self.versions:
            if v.version_number == version_number:
                return v
        return None

    def to_preview_format(self) -> Dict[str, Any]:
        """Format for UI preview."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.asset_type.value,
            "status": self.status.value,
            "version": self.current_version,
            "content": self.current_content,
            "platform": self.platform,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AssetVersion(Base):
    """
    Asset Version - a snapshot of an asset's content.

    Enables:
    - Full history tracking
    - Easy rollback
    - Comparison between versions
    """

    __tablename__ = "asset_versions"

    asset_id = Column(
        String(12),
        ForeignKey("assets.id"),
        nullable=False
    )

    version_number = Column(Integer, nullable=False)
    change_summary = Column(String(500), nullable=True)

    # Content (JSONB) - structure varies by asset type
    # Examples:
    #
    # EMAIL:
    # {
    #     "subject": "...",
    #     "preview_text": "...",
    #     "body_html": "...",
    #     "body_text": "...",
    #     "cta": {"text": "...", "url": "..."}
    # }
    #
    # SOCIAL_POST:
    # {
    #     "copy": "...",
    #     "hashtags": ["...", "..."],
    #     "image_url": "...",
    #     "image_alt": "...",
    #     "link": "...",
    #     "platform_specific": {...}
    # }
    #
    # LANDING_PAGE:
    # {
    #     "hero": {"headline": "...", "subhead": "...", "cta": {...}},
    #     "sections": [{...}, {...}],
    #     "meta": {"title": "...", "description": "..."},
    #     "html": "..."
    # }
    #
    # DISPLAY_AD:
    # {
    #     "headline": "...",
    #     "description": "...",
    #     "cta": "...",
    #     "image_url": "...",
    #     "size": "300x250",
    #     "variants": [{...}, {...}]
    # }
    content = Column(JSON, nullable=False)

    # Who created this version
    created_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    created_by_ai = Column(Boolean, default=True, nullable=False)

    # Parent version (for branching)
    parent_version = Column(Integer, nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="versions")

    def __repr__(self):
        return f"<AssetVersion {self.asset_id} v{self.version_number}>"


class AssetComment(Base):
    """
    Comment on an asset - for feedback and collaboration.

    Supports:
    - General comments
    - Inline/positional comments (like Figma)
    - Reply threads
    - Resolution status
    """

    __tablename__ = "asset_comments"

    asset_id = Column(
        String(12),
        ForeignKey("assets.id"),
        nullable=False
    )

    # Which version was this comment made on
    version_number = Column(Integer, nullable=False)

    # Author
    user_id = Column(String(12), ForeignKey("users.id"), nullable=False)

    # Content
    content = Column(Text, nullable=False)

    # Position for inline comments (JSONB)
    # Structure depends on asset type:
    # {
    #     "type": "text_selection",
    #     "start": 100,
    #     "end": 150,
    #     "field": "body_html"
    # }
    # OR
    # {
    #     "type": "coordinate",
    #     "x": 100,
    #     "y": 200
    # }
    position = Column(JSON, nullable=True)

    # Threading
    parent_id = Column(String(12), ForeignKey("asset_comments.id"), nullable=True)

    # Status
    resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(String(12), ForeignKey("users.id"), nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])
    replies = relationship(
        "AssetComment",
        backref="parent",
        remote_side="AssetComment.id"
    )

    def __repr__(self):
        return f"<Comment on {self.asset_id} by {self.user_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "version": self.version_number,
            "content": self.content,
            "position": self.position,
            "resolved": self.resolved,
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "user": {
                "id": self.user.id,
                "name": self.user.name,
                "avatar_url": self.user.avatar_url,
            } if self.user else None,
            "replies": [r.to_dict() for r in self.replies] if self.replies else [],
        }
