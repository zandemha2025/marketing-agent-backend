# Composio Integration for Ad Platforms

## Summary

Using **Composio** for ad platform integrations is the recommended approach because:

1. **No custom OAuth code needed** - Composio handles all OAuth flows
2. **Automatic token refresh** - No expired token issues
3. **Unified API** - Same interface for all platforms
4. **MCP compatible** - Works directly with AI agents
5. **850+ integrations** - Future-proof for adding more platforms

---

## Available Platforms in Composio

| Platform | Auth Method | Use Case |
|----------|-------------|----------|
| **Google Ads** | OAuth2 | Paid search/display campaigns |
| **Meta Ads (Metaads)** | OAuth2 + API Key | Facebook/Instagram paid ads |
| **Google Analytics** | OAuth2 | GA4 tracking & attribution |
| **TikTok** | OAuth2 + Bearer | Organic + potentially ads |
| **Twitter/X** | OAuth2 + Bearer | Organic posting |
| **LinkedIn** | OAuth2 | Organic + Adyntel for ads |

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MARKETING AGENT                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              COMPOSIO SDK LAYER                       │  │
│  │                                                       │  │
│  │   from composio import ComposioToolSet               │  │
│  │   toolset = ComposioToolSet()                        │  │
│  │                                                       │  │
│  │   # All platforms through one interface:             │  │
│  │   - toolset.get_tools(apps=["googleads"])           │  │
│  │   - toolset.get_tools(apps=["metaads"])             │  │
│  │   - toolset.get_tools(apps=["googleanalytics"])     │  │
│  │   - toolset.get_tools(apps=["tiktok"])              │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              COMPOSIO MANAGED AUTH                    │  │
│  │                                                       │  │
│  │   - OAuth flows handled by Composio                  │  │
│  │   - Token storage & refresh automatic                │  │
│  │   - User connects accounts via Composio UI           │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Google  │  │  Meta   │  │   GA4   │  │ TikTok  │       │
│  │  Ads    │  │  Ads    │  │         │  │         │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Install Composio SDK

```bash
pip install composio-core composio-openai
```

### Step 2: Set up Composio API Key

```bash
# Get from https://app.composio.dev
export COMPOSIO_API_KEY=your_api_key
```

Add to `.env`:
```
COMPOSIO_API_KEY=your_composio_api_key
```

### Step 3: Create Composio Service

```python
# backend/app/services/composio_service.py

from composio import ComposioToolSet, Action, App
from typing import Optional, Dict, Any, List
import os

class ComposioService:
    """Unified service for all ad platform integrations via Composio."""

    def __init__(self):
        self.toolset = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY"))

    # ==================== CONNECTION MANAGEMENT ====================

    def get_connection_url(self, app: str, user_id: str) -> str:
        """Generate OAuth connection URL for a user to connect their account."""
        return self.toolset.initiate_connection(
            app=app,
            entity_id=user_id,  # Your user's ID
            redirect_url="https://yourapp.com/integrations/callback"
        )

    def get_connected_accounts(self, user_id: str) -> List[Dict]:
        """Get list of connected accounts for a user."""
        return self.toolset.get_entity(entity_id=user_id).get_connections()

    # ==================== GOOGLE ADS ====================

    async def google_ads_get_campaigns(self, user_id: str, customer_id: str) -> Dict:
        """Get all campaigns from Google Ads."""
        return await self.toolset.execute_action(
            action=Action.GOOGLEADS_GET_CAMPAIGNS,
            params={"customer_id": customer_id},
            entity_id=user_id
        )

    async def google_ads_get_metrics(
        self,
        user_id: str,
        customer_id: str,
        start_date: str,
        end_date: str
    ) -> Dict:
        """Get campaign performance metrics."""
        return await self.toolset.execute_action(
            action=Action.GOOGLEADS_GET_CAMPAIGN_METRICS,
            params={
                "customer_id": customer_id,
                "start_date": start_date,
                "end_date": end_date
            },
            entity_id=user_id
        )

    async def google_ads_create_campaign(
        self,
        user_id: str,
        customer_id: str,
        campaign_data: Dict
    ) -> Dict:
        """Create a new Google Ads campaign."""
        return await self.toolset.execute_action(
            action=Action.GOOGLEADS_CREATE_CAMPAIGN,
            params={
                "customer_id": customer_id,
                **campaign_data
            },
            entity_id=user_id
        )

    # ==================== META ADS (Facebook/Instagram) ====================

    async def meta_ads_get_campaigns(self, user_id: str, ad_account_id: str) -> Dict:
        """Get all campaigns from Meta Ads."""
        return await self.toolset.execute_action(
            action=Action.METAADS_GET_CAMPAIGNS,
            params={"ad_account_id": ad_account_id},
            entity_id=user_id
        )

    async def meta_ads_get_insights(
        self,
        user_id: str,
        ad_account_id: str,
        date_preset: str = "last_30d"
    ) -> Dict:
        """Get campaign insights/metrics."""
        return await self.toolset.execute_action(
            action=Action.METAADS_GET_INSIGHTS,
            params={
                "ad_account_id": ad_account_id,
                "date_preset": date_preset
            },
            entity_id=user_id
        )

    async def meta_ads_create_campaign(
        self,
        user_id: str,
        ad_account_id: str,
        campaign_data: Dict
    ) -> Dict:
        """Create a new Meta Ads campaign."""
        return await self.toolset.execute_action(
            action=Action.METAADS_CREATE_CAMPAIGN,
            params={
                "ad_account_id": ad_account_id,
                **campaign_data
            },
            entity_id=user_id
        )

    # ==================== GOOGLE ANALYTICS (GA4) ====================

    async def ga4_get_report(
        self,
        user_id: str,
        property_id: str,
        metrics: List[str],
        dimensions: List[str],
        start_date: str,
        end_date: str
    ) -> Dict:
        """Get analytics report from GA4."""
        return await self.toolset.execute_action(
            action=Action.GOOGLEANALYTICS_RUN_REPORT,
            params={
                "property_id": property_id,
                "metrics": metrics,
                "dimensions": dimensions,
                "start_date": start_date,
                "end_date": end_date
            },
            entity_id=user_id
        )

    async def ga4_get_realtime(self, user_id: str, property_id: str) -> Dict:
        """Get real-time analytics data."""
        return await self.toolset.execute_action(
            action=Action.GOOGLEANALYTICS_GET_REALTIME_REPORT,
            params={"property_id": property_id},
            entity_id=user_id
        )

    # ==================== CROSS-PLATFORM AGGREGATION ====================

    async def get_all_platform_metrics(
        self,
        user_id: str,
        connections: Dict[str, str],  # platform -> account_id mapping
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Aggregate metrics from all connected ad platforms."""
        results = {}

        if "google_ads" in connections:
            results["google_ads"] = await self.google_ads_get_metrics(
                user_id, connections["google_ads"], start_date, end_date
            )

        if "meta_ads" in connections:
            results["meta_ads"] = await self.meta_ads_get_insights(
                user_id, connections["meta_ads"]
            )

        if "ga4" in connections:
            results["ga4"] = await self.ga4_get_report(
                user_id,
                connections["ga4"],
                metrics=["sessions", "conversions", "totalRevenue"],
                dimensions=["date", "source", "medium"],
                start_date=start_date,
                end_date=end_date
            )

        return results
```

### Step 4: Add API Endpoints

```python
# backend/app/api/ad_platforms.py

from fastapi import APIRouter, Depends, HTTPException
from app.services.composio_service import ComposioService
from app.auth import get_current_user

router = APIRouter(prefix="/api/ad-platforms", tags=["Ad Platforms"])
composio = ComposioService()

@router.get("/connect/{platform}")
async def get_connection_url(
    platform: str,
    current_user = Depends(get_current_user)
):
    """Get OAuth URL to connect an ad platform."""
    valid_platforms = ["googleads", "metaads", "googleanalytics", "tiktok"]
    if platform not in valid_platforms:
        raise HTTPException(400, f"Invalid platform. Choose from: {valid_platforms}")

    url = composio.get_connection_url(platform, str(current_user.id))
    return {"connect_url": url}

@router.get("/connections")
async def get_connections(current_user = Depends(get_current_user)):
    """Get all connected ad platform accounts."""
    connections = composio.get_connected_accounts(str(current_user.id))
    return {"connections": connections}

@router.get("/metrics")
async def get_aggregated_metrics(
    start_date: str,
    end_date: str,
    current_user = Depends(get_current_user)
):
    """Get aggregated metrics from all connected platforms."""
    # Get user's connections from database
    connections = await get_user_connections(current_user.id)

    metrics = await composio.get_all_platform_metrics(
        str(current_user.id),
        connections,
        start_date,
        end_date
    )
    return metrics

@router.post("/campaigns")
async def create_cross_platform_campaign(
    campaign_data: dict,
    current_user = Depends(get_current_user)
):
    """Create a campaign across multiple platforms."""
    results = {}
    platforms = campaign_data.get("platforms", [])

    for platform in platforms:
        if platform == "google_ads":
            results["google_ads"] = await composio.google_ads_create_campaign(
                str(current_user.id),
                campaign_data["google_ads_customer_id"],
                campaign_data["google_ads_config"]
            )
        elif platform == "meta_ads":
            results["meta_ads"] = await composio.meta_ads_create_campaign(
                str(current_user.id),
                campaign_data["meta_ad_account_id"],
                campaign_data["meta_ads_config"]
            )

    return results
```

### Step 5: Update Onboarding Flow

Add ad platform connection to onboarding:

```python
# Add to onboarding pipeline

ONBOARDING_STAGES = [
    "brand_discovery",
    "market_research",
    "audience_analysis",
    "ad_platform_connection",  # NEW
    "analytics_setup",          # NEW
    "strategy_generation"
]

async def ad_platform_connection_stage(user_id: str, org_id: str):
    """Stage 4: Connect ad platforms."""
    composio = ComposioService()

    # Generate connection URLs for each platform
    platforms = ["googleads", "metaads", "googleanalytics", "tiktok"]
    connection_urls = {}

    for platform in platforms:
        connection_urls[platform] = composio.get_connection_url(platform, user_id)

    return {
        "stage": "ad_platform_connection",
        "connection_urls": connection_urls,
        "message": "Connect your ad platforms to import historical performance data"
    }
```

---

## Environment Variables

Add to `.env`:

```bash
# Composio
COMPOSIO_API_KEY=your_composio_api_key

# Platform-specific (optional, Composio handles these via OAuth)
# These are now managed by Composio, not needed in .env
# GOOGLE_ADS_CLIENT_ID=
# GOOGLE_ADS_CLIENT_SECRET=
# META_ADS_APP_ID=
# META_ADS_APP_SECRET=
```

---

## Benefits Over Custom Implementation

| Aspect | Custom Implementation | Composio |
|--------|----------------------|----------|
| OAuth Flows | Write for each platform | Handled automatically |
| Token Refresh | Implement & monitor | Automatic |
| API Changes | Update code manually | Composio updates |
| New Platforms | Build from scratch | Add in minutes |
| Maintenance | High | Low |
| Time to Launch | Weeks | Days |

---

## Next Steps

1. **Sign up for Composio** at https://app.composio.dev
2. **Get API key** from dashboard
3. **Install SDK**: `pip install composio-core`
4. **Implement ComposioService** as shown above
5. **Add connection UI** in onboarding flow
6. **Build performance dashboard** using aggregated metrics

---

## Cost Considerations

Composio pricing (as of 2026):
- Free tier: 1,000 actions/month
- Pro: $49/month for 10,000 actions
- Enterprise: Custom pricing

For a marketing platform, the Pro tier should cover most use cases, and it's significantly cheaper than the engineering time to build and maintain custom integrations.
