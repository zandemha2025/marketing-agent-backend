"""
Pydantic schemas for request/response validation.
"""
from .onboarding import (
    OnboardingRequest,
    OnboardingStatus,
    OnboardingProgress,
    BrandProfile,
    MarketProfile,
    AudienceProfile,
)
from .organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from .campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    CampaignBrief,
)
from .asset import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    AssetVersionResponse,
)

__all__ = [
    # Onboarding
    "OnboardingRequest",
    "OnboardingStatus",
    "OnboardingProgress",
    "BrandProfile",
    "MarketProfile",
    "AudienceProfile",
    # Organization
    "OrganizationCreate",
    "OrganizationResponse",
    "OrganizationUpdate",
    # Campaign
    "CampaignCreate",
    "CampaignResponse",
    "CampaignUpdate",
    "CampaignBrief",
    # Asset
    "AssetCreate",
    "AssetResponse",
    "AssetUpdate",
    "AssetVersionResponse",
]
