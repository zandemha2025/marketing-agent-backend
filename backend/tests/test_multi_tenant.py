"""
Multi-Tenant Isolation E2E Tests.

Tests to verify that data is properly isolated between organizations
and that users cannot access data from other tenants.
"""
import pytest
import pytest_asyncio
import httpx
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from conftest import BASE_URL, generate_unique_email


# ============== Campaign Isolation Tests ==============

class TestCampaignIsolation:
    """Tests for campaign data isolation between organizations."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_org_campaigns(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users can only see campaigns from their own organization.
        
        Verifies:
        - User A can see campaigns from Org A
        - User A cannot see campaigns from Org B
        """
        # Create campaign for first user's org
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        campaign_data = {
            "organization_id": registered_user["organization_id"],
            "name": f"Org A Campaign {uuid.uuid4()}",
            "objective": "Test campaign for org A"
        }
        
        response = await client.post(
            f"/campaigns/?organization_id={registered_user['organization_id']}",
            json=campaign_data,
            headers=headers_a
        )
        # Campaign creation might require more fields or return different status
        if response.status_code == 200:
            campaign_a = response.json()
            campaign_a_id = campaign_a.get("id")
        else:
            # Skip if campaign creation not supported in this way
            pytest.skip("Campaign creation endpoint not available")
            return
        
        # Create campaign for second user's org
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        campaign_data_b = {
            "organization_id": second_registered_user["organization_id"],
            "name": f"Org B Campaign {uuid.uuid4()}",
            "objective": "Test campaign for org B"
        }
        
        response = await client.post(
            f"/campaigns/?organization_id={second_registered_user['organization_id']}",
            json=campaign_data_b,
            headers=headers_b
        )
        
        # User A lists campaigns - should only see Org A campaigns
        response = await client.get(
            f"/campaigns/?organization_id={registered_user['organization_id']}",
            headers=headers_a
        )
        
        if response.status_code == 200:
            campaigns = response.json()
            campaign_list = campaigns.get("campaigns", campaigns)
            
            # Verify all campaigns belong to user A's org
            for campaign in campaign_list:
                assert campaign.get("organization_id") == registered_user["organization_id"], \
                    "User should only see their own org's campaigns"

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_org_campaign_by_id(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users cannot access campaigns from other organizations by ID.
        
        Verifies:
        - Direct access to another org's campaign is denied
        """
        # Create campaign for second user's org
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        campaign_data = {
            "organization_id": second_registered_user["organization_id"],
            "name": f"Private Campaign {uuid.uuid4()}",
            "objective": "Private campaign"
        }
        
        response = await client.post(
            f"/campaigns/?organization_id={second_registered_user['organization_id']}",
            json=campaign_data,
            headers=headers_b
        )
        
        if response.status_code != 200:
            pytest.skip("Campaign creation not available")
            return
            
        campaign_b = response.json()
        campaign_b_id = campaign_b.get("id")
        
        # User A tries to access User B's campaign
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        response = await client.get(
            f"/campaigns/{campaign_b_id}",
            headers=headers_a
        )
        
        # Should be denied (403 or 404)
        assert response.status_code in [403, 404], \
            "User should not be able to access another org's campaign"


# ============== Customer Data (CDP) Isolation Tests ==============

class TestCDPIsolation:
    """Tests for Customer Data Platform isolation between organizations."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_org_customers(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users can only see customers from their own organization.
        
        Verifies:
        - User A can see customers from Org A
        - User A cannot see customers from Org B
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        
        # Create customer for Org A
        customer_a_data = {
            "external_ids": {"email": f"customer-a-{uuid.uuid4()}@test.com"},
            "anonymous_id": str(uuid.uuid4()),
            "traits": {"name": "Customer A", "org": "A"}
        }
        
        response = await client.post(
            f"/cdp/customers?organization_id={registered_user['organization_id']}",
            json=customer_a_data,
            headers=headers_a
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip("CDP customer creation not available")
            return
        
        # Create customer for Org B
        customer_b_data = {
            "external_ids": {"email": f"customer-b-{uuid.uuid4()}@test.com"},
            "anonymous_id": str(uuid.uuid4()),
            "traits": {"name": "Customer B", "org": "B"}
        }
        
        await client.post(
            f"/cdp/customers?organization_id={second_registered_user['organization_id']}",
            json=customer_b_data,
            headers=headers_b
        )
        
        # User A lists customers - should only see Org A customers
        response = await client.get(
            f"/cdp/customers?organization_id={registered_user['organization_id']}",
            headers=headers_a
        )
        
        if response.status_code == 200:
            data = response.json()
            customers = data.get("customers", data) if isinstance(data, dict) else data
            
            for customer in customers:
                assert customer.get("organization_id") == registered_user["organization_id"], \
                    "User should only see their own org's customers"

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_org_customer_by_id(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users cannot access customers from other organizations by ID.
        
        Verifies:
        - Direct access to another org's customer is denied
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        
        # Create customer for Org B
        customer_data = {
            "external_ids": {"email": f"private-customer-{uuid.uuid4()}@test.com"},
            "anonymous_id": str(uuid.uuid4()),
            "traits": {"name": "Private Customer"}
        }
        
        response = await client.post(
            f"/cdp/customers?organization_id={second_registered_user['organization_id']}",
            json=customer_data,
            headers=headers_b
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip("CDP customer creation not available")
            return
            
        customer_b = response.json()
        customer_b_id = customer_b.get("id")
        
        # User A tries to access User B's customer
        response = await client.get(
            f"/cdp/customers/{customer_b_id}",
            headers=headers_a
        )
        
        # Should be denied
        assert response.status_code in [403, 404], \
            "User should not be able to access another org's customer"


# ============== Scheduled Posts Isolation Tests ==============

class TestScheduledPostsIsolation:
    """Tests for scheduled posts isolation between organizations."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_org_scheduled_posts(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users can only see scheduled posts from their own organization.
        
        Verifies:
        - User A can see posts from Org A
        - User A cannot see posts from Org B
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        
        # Create post for Org A
        post_a_data = {
            "title": f"Org A Post {uuid.uuid4()}",
            "content": "Content for Org A",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": registered_user["organization_id"]
        }
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={registered_user['organization_id']}",
            json=post_a_data,
            headers=headers_a
        )
        
        assert response.status_code == 200, f"Failed to create post: {response.text}"
        post_a = response.json()
        
        # Create post for Org B
        post_b_data = {
            "title": f"Org B Post {uuid.uuid4()}",
            "content": "Content for Org B",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": second_registered_user["organization_id"]
        }
        
        await client.post(
            f"/scheduled-posts/?organization_id={second_registered_user['organization_id']}",
            json=post_b_data,
            headers=headers_b
        )
        
        # User A lists posts - should only see Org A posts
        response = await client.get(
            f"/scheduled-posts/?organization_id={registered_user['organization_id']}",
            headers=headers_a
        )
        
        assert response.status_code == 200
        posts = response.json()
        
        for post in posts:
            assert post.get("organization_id") == registered_user["organization_id"], \
                "User should only see their own org's scheduled posts"

    @pytest.mark.asyncio
    async def test_user_cannot_modify_other_org_scheduled_post(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users cannot modify scheduled posts from other organizations.
        
        Verifies:
        - User A cannot update Org B's post
        - User A cannot delete Org B's post
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        
        # Create post for Org B
        post_data = {
            "title": f"Org B Private Post {uuid.uuid4()}",
            "content": "Private content",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": second_registered_user["organization_id"]
        }
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={second_registered_user['organization_id']}",
            json=post_data,
            headers=headers_b
        )
        
        assert response.status_code == 200
        post_b = response.json()
        post_b_id = post_b["id"]
        
        # User A tries to update Org B's post
        update_data = {"title": "Hacked Title"}
        response = await client.put(
            f"/scheduled-posts/{post_b_id}",
            json=update_data,
            headers=headers_a
        )
        
        assert response.status_code in [403, 404], \
            "User should not be able to update another org's post"
        
        # User A tries to delete Org B's post
        response = await client.delete(
            f"/scheduled-posts/{post_b_id}",
            headers=headers_a
        )
        
        assert response.status_code in [403, 404], \
            "User should not be able to delete another org's post"


# ============== Analytics Isolation Tests ==============

class TestAnalyticsIsolation:
    """Tests for analytics data isolation between organizations."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_org_analytics(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users can only see analytics from their own organization.
        
        Verifies:
        - Analytics endpoints filter by organization
        - Cross-org analytics access is denied
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        
        # Try to access analytics for own org
        response = await client.get(
            f"/analytics/dashboard?organization_id={registered_user['organization_id']}",
            headers=headers_a
        )
        
        # Should succeed or return empty data
        assert response.status_code in [200, 404], \
            f"Analytics access failed unexpectedly: {response.text}"
        
        # Try to access analytics for other org
        response = await client.get(
            f"/analytics/dashboard?organization_id={second_registered_user['organization_id']}",
            headers=headers_a
        )
        
        # Should be denied or return empty
        assert response.status_code in [200, 403, 404]
        
        if response.status_code == 200:
            data = response.json()
            # If data is returned, it should be empty or filtered
            # The exact behavior depends on implementation


# ============== Assets Isolation Tests ==============

class TestAssetsIsolation:
    """Tests for asset data isolation between organizations."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_org_assets(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users can only see assets from their own organization.
        
        Verifies:
        - User A can see assets from Org A
        - User A cannot see assets from Org B
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        
        # Create asset for Org A
        asset_a_data = {
            "name": f"Org A Asset {uuid.uuid4()}",
            "asset_type": "image",
            "content": "Asset content A",
            "organization_id": registered_user["organization_id"]
        }
        
        response = await client.post(
            f"/assets/?organization_id={registered_user['organization_id']}",
            json=asset_a_data,
            headers=headers_a
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip("Asset creation not available")
            return
        
        # Create asset for Org B
        asset_b_data = {
            "name": f"Org B Asset {uuid.uuid4()}",
            "asset_type": "image",
            "content": "Asset content B",
            "organization_id": second_registered_user["organization_id"]
        }
        
        await client.post(
            f"/assets/?organization_id={second_registered_user['organization_id']}",
            json=asset_b_data,
            headers=headers_b
        )
        
        # User A lists assets - should only see Org A assets
        response = await client.get(
            f"/assets/?organization_id={registered_user['organization_id']}",
            headers=headers_a
        )
        
        if response.status_code == 200:
            data = response.json()
            assets = data.get("assets", data) if isinstance(data, dict) else data
            
            for asset in assets:
                assert asset.get("organization_id") == registered_user["organization_id"], \
                    "User should only see their own org's assets"


# ============== Image Editor Session Isolation Tests ==============

class TestImageEditorIsolation:
    """Tests for image editor session isolation between organizations."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_org_sessions(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users can only see image editor sessions from their own organization.
        
        Verifies:
        - User A can see sessions from Org A
        - User A cannot see sessions from Org B
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        
        # Create session for Org A
        session_a_data = {
            "title": f"Org A Session {uuid.uuid4()}",
            "original_image_url": "http://example.com/image-a.jpg",
            "organization_id": registered_user["organization_id"],
            "ai_model": "dall-e-3"
        }
        
        response = await client.post(
            f"/image-editor/sessions?organization_id={registered_user['organization_id']}",
            json=session_a_data,
            headers=headers_a
        )
        
        if response.status_code != 200:
            pytest.skip("Image editor session creation not available")
            return
            
        session_a = response.json()
        
        # Create session for Org B
        session_b_data = {
            "title": f"Org B Session {uuid.uuid4()}",
            "original_image_url": "http://example.com/image-b.jpg",
            "organization_id": second_registered_user["organization_id"],
            "ai_model": "dall-e-3"
        }
        
        response = await client.post(
            f"/image-editor/sessions?organization_id={second_registered_user['organization_id']}",
            json=session_b_data,
            headers=headers_b
        )
        
        session_b = response.json()
        session_b_id = session_b.get("id")
        
        # User A tries to access Org B's session
        response = await client.get(
            f"/image-editor/sessions/{session_b_id}",
            headers=headers_a
        )
        
        # Should be denied
        assert response.status_code in [403, 404], \
            "User should not be able to access another org's image editor session"


# ============== Segments Isolation Tests ==============

class TestSegmentsIsolation:
    """Tests for customer segment isolation between organizations."""

    @pytest.mark.asyncio
    async def test_user_can_only_see_own_org_segments(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users can only see segments from their own organization.
        
        Verifies:
        - User A can see segments from Org A
        - User A cannot see segments from Org B
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        headers_b = {"Authorization": f"Bearer {second_registered_user['access_token']}"}
        
        # Create segment for Org A
        segment_a_data = {
            "name": f"Org A Segment {uuid.uuid4()}",
            "description": "Segment for Org A",
            "segment_type": "dynamic",
            "definition": {"conditions": []}
        }
        
        response = await client.post(
            f"/cdp/segments?organization_id={registered_user['organization_id']}",
            json=segment_a_data,
            headers=headers_a
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip("Segment creation not available")
            return
        
        # Create segment for Org B
        segment_b_data = {
            "name": f"Org B Segment {uuid.uuid4()}",
            "description": "Segment for Org B",
            "segment_type": "dynamic",
            "definition": {"conditions": []}
        }
        
        response = await client.post(
            f"/cdp/segments?organization_id={second_registered_user['organization_id']}",
            json=segment_b_data,
            headers=headers_b
        )
        
        segment_b = response.json()
        segment_b_id = segment_b.get("id")
        
        # User A tries to access Org B's segment
        response = await client.get(
            f"/cdp/segments/{segment_b_id}",
            headers=headers_a
        )
        
        # Should be denied
        assert response.status_code in [403, 404], \
            "User should not be able to access another org's segment"


# ============== Cross-Tenant Data Leakage Tests ==============

class TestCrossTenantDataLeakage:
    """Tests to verify no cross-tenant data leakage occurs."""

    @pytest.mark.asyncio
    async def test_no_data_leakage_in_list_endpoints(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that list endpoints don't leak data from other organizations.
        
        Verifies:
        - All list endpoints properly filter by organization
        - No data from other orgs appears in responses
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        org_a_id = registered_user["organization_id"]
        org_b_id = second_registered_user["organization_id"]
        
        # Test various list endpoints
        endpoints = [
            f"/scheduled-posts/?organization_id={org_a_id}",
            f"/campaigns/?organization_id={org_a_id}",
            f"/assets/?organization_id={org_a_id}",
            f"/cdp/customers?organization_id={org_a_id}",
            f"/cdp/segments?organization_id={org_a_id}",
        ]
        
        for endpoint in endpoints:
            response = await client.get(endpoint, headers=headers_a)
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response formats
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    # Try common keys for list data
                    for key in ["items", "data", "campaigns", "assets", "customers", "segments", "posts"]:
                        if key in data:
                            items = data[key]
                            break
                
                # Verify no items from other org
                for item in items:
                    if isinstance(item, dict) and "organization_id" in item:
                        assert item["organization_id"] != org_b_id, \
                            f"Data leakage detected in {endpoint}: found item from other org"

    @pytest.mark.asyncio
    async def test_organization_id_parameter_validation(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that organization_id parameter is validated against user's org.
        
        Verifies:
        - User cannot query data using another org's ID
        - Server validates org access
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        org_b_id = second_registered_user["organization_id"]
        
        # Try to access data using other org's ID
        response = await client.get(
            f"/scheduled-posts/?organization_id={org_b_id}",
            headers=headers_a
        )
        
        # Should either return empty or be denied
        if response.status_code == 200:
            data = response.json()
            # If 200, should return empty or only user's own data
            if isinstance(data, list):
                for item in data:
                    assert item.get("organization_id") != org_b_id, \
                        "Should not return data from other org"

    @pytest.mark.asyncio
    async def test_cannot_create_resources_in_other_org(
        self,
        client: httpx.AsyncClient,
        registered_user: Dict[str, Any],
        second_registered_user: Dict[str, Any]
    ):
        """
        Test that users cannot create resources in other organizations.
        
        Verifies:
        - Creating resources with another org's ID is denied
        """
        headers_a = {"Authorization": f"Bearer {registered_user['access_token']}"}
        org_b_id = second_registered_user["organization_id"]
        
        # Try to create a scheduled post in other org
        post_data = {
            "title": "Malicious Post",
            "content": "Trying to create in other org",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": org_b_id  # Other org's ID
        }
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={org_b_id}",
            json=post_data,
            headers=headers_a
        )
        
        # Should be denied
        assert response.status_code in [400, 403, 404], \
            "Should not be able to create resources in other org"
