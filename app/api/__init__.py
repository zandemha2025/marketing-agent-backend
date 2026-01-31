"""
API routes for the Marketing Agent v2.
"""
from fastapi import APIRouter

from .onboarding import router as onboarding_router
from .organizations import router as organizations_router
from .campaigns import router as campaigns_router
from .assets import router as assets_router
from .chat import router as chat_router
from .orchestrator import router as orchestrator_router
from .kata import router as kata_router

router = APIRouter()

# Include all routers
router.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
router.include_router(organizations_router, prefix="/organizations", tags=["Organizations"])
router.include_router(campaigns_router, prefix="/campaigns", tags=["Campaigns"])
router.include_router(assets_router, prefix="/assets", tags=["Assets"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(orchestrator_router, prefix="/orchestrator", tags=["Orchestrator"])
router.include_router(kata_router, prefix="/kata", tags=["Kata Engine"])
