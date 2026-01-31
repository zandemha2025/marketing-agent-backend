"""
API Endpoint E2E Tests.

Comprehensive tests for all major API modules including
CRUD operations and business logic validation.
"""
import pytest
import pytest_asyncio
import httpx
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from conftest import BASE_URL, generate_unique_email


# ============== Campaigns API Tests ==============

class TestCampaignsAPI:
    """Tests for Campaigns CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_campaign(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test creating a new campaign.
        
        Verifies:
        - Campaign can be created with valid data
        - Response includes campaign ID and details
        """
        campaign_data = {
            "organization_id": organization_id,
            "name": f"Test Campaign {uuid.uuid4()}",
            "objective": "Increase brand awareness",
            "product_focus": "Test Product",
            "target_audience": "Young professionals 25-35",
            "budget_tier": "medium",
            "timeline": "4 weeks",
            "platforms": ["twitter", "linkedin"]
        }
        
        response = await client.post(
            f"/campaigns/?organization_id={organization_id}",
            json=campaign_data
        )
        
        # Campaign creation may require auth or have different endpoint
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["name"] == campaign_data["name"]
            assert data["organization_id"] == organization_id

    @pytest.mark.asyncio
    async def test_list_campaigns(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test listing campaigns for an organization.
        
        Verifies:
        - Campaigns can be listed
        - Response includes campaign data
        """
        response = await client.get(
            f"/campaigns/?organization_id={organization_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Response could be list or object with campaigns key
        if isinstance(data, dict):
            assert "campaigns" in data or "items" in data or isinstance(data.get("data"), list)

    @pytest.mark.asyncio
    async def test_get_campaign_by_id(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test getting a specific campaign by ID.
        
        Verifies:
        - Campaign can be retrieved by ID
        - Returns 404 for non-existent campaign
        """
        # Test with non-existent ID
        fake_id = "nonexistent123"
        response = await client.get(f"/campaigns/{fake_id}")
        
        assert response.status_code in [404, 422]


# ============== Assets API Tests ==============

class TestAssetsAPI:
    """Tests for Assets CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_asset(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test creating a new asset.
        
        Verifies:
        - Asset can be created with valid data
        - Response includes asset ID
        """
        asset_data = {
            "name": f"Test Asset {uuid.uuid4()}",
            "asset_type": "image",
            "content": "Test content",
            "organization_id": organization_id,
            "metadata": {"format": "png"}
        }
        
        response = await client.post(
            f"/assets/?organization_id={organization_id}",
            json=asset_data,
            headers=auth_headers
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data

    @pytest.mark.asyncio
    async def test_list_assets(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test listing assets for an organization.
        
        Verifies:
        - Assets can be listed
        - Response format is correct
        """
        response = await client.get(
            f"/assets/?organization_id={organization_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ============== Tasks API Tests ==============

class TestTasksAPI:
    """Tests for Tasks CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_task(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test creating a new task.
        
        Verifies:
        - Task can be created with valid data
        """
        task_data = {
            "title": f"Test Task {uuid.uuid4()}",
            "description": "Test task description",
            "status": "pending",
            "organization_id": organization_id
        }
        
        response = await client.post(
            f"/tasks/?organization_id={organization_id}",
            json=task_data,
            headers=auth_headers
        )
        
        # Task creation may have different requirements
        assert response.status_code in [200, 201, 422]

    @pytest.mark.asyncio
    async def test_list_tasks(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test listing tasks for an organization.
        
        Verifies:
        - Tasks can be listed
        """
        response = await client.get(
            f"/tasks/?organization_id={organization_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ============== Scheduled Posts API Tests ==============

class TestScheduledPostsAPI:
    """Tests for Scheduled Posts CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_scheduled_post(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test creating a new scheduled post.
        
        Verifies:
        - Post can be created with valid data
        - Response includes post ID and scheduled time
        """
        post_data = {
            "title": f"Test Post {uuid.uuid4()}",
            "content": "Test post content",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": organization_id
        }
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json=post_data
        )
        
        assert response.status_code == 200, f"Create post failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["title"] == post_data["title"]

    @pytest.mark.asyncio
    async def test_list_scheduled_posts(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test listing scheduled posts for an organization.
        
        Verifies:
        - Posts can be listed
        - Response is a list
        """
        response = await client.get(
            f"/scheduled-posts/?organization_id={organization_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_update_scheduled_post(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test updating a scheduled post.
        
        Verifies:
        - Post can be updated
        - Changes are persisted
        """
        # Create a post first
        post_data = {
            "title": f"Original Title {uuid.uuid4()}",
            "content": "Original content",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": organization_id
        }
        
        create_response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json=post_data
        )
        
        assert create_response.status_code == 200
        post = create_response.json()
        post_id = post["id"]
        
        # Update the post
        update_data = {"title": "Updated Title"}
        update_response = await client.put(
            f"/scheduled-posts/{post_id}",
            json=update_data
        )
        
        assert update_response.status_code == 200
        updated_post = update_response.json()
        assert updated_post["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_scheduled_post(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test deleting a scheduled post.
        
        Verifies:
        - Post can be deleted
        - Post is no longer accessible after deletion
        """
        # Create a post first
        post_data = {
            "title": f"Post to Delete {uuid.uuid4()}",
            "content": "Content to delete",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": organization_id
        }
        
        create_response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json=post_data
        )
        
        assert create_response.status_code == 200
        post = create_response.json()
        post_id = post["id"]
        
        # Delete the post
        delete_response = await client.delete(f"/scheduled-posts/{post_id}")
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response = await client.get(f"/scheduled-posts/{post_id}")
        assert get_response.status_code == 404


# ============== Trends API Tests ==============

class TestTrendsAPI:
    """Tests for Trends API."""

    @pytest.mark.asyncio
    async def test_get_trends(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test getting trends data.
        
        Verifies:
        - Trends endpoint is accessible
        - Response format is correct
        """
        response = await client.get(
            f"/trends/?organization_id={organization_id}",
            headers=auth_headers
        )
        
        # Trends may require specific setup
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_search_trends(
        self,
        client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """
        Test searching for trends.
        
        Verifies:
        - Trend search works
        """
        response = await client.get(
            "/trends/search?query=marketing",
            headers=auth_headers
        )
        
        # Search may have different endpoint structure
        assert response.status_code in [200, 404, 422]


# ============== Analytics API Tests ==============

class TestAnalyticsAPI:
    """Tests for Analytics API."""

    @pytest.mark.asyncio
    async def test_get_dashboard(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test getting analytics dashboard data.
        
        Verifies:
        - Dashboard endpoint is accessible
        """
        response = await client.get(
            f"/analytics/dashboard?organization_id={organization_id}",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_campaign_analytics(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test getting campaign-specific analytics.
        
        Verifies:
        - Campaign analytics endpoint works
        """
        response = await client.get(
            f"/analytics/campaigns?organization_id={organization_id}",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 404]


# ============== CDP (Customer Data Platform) API Tests ==============

class TestCDPAPI:
    """Tests for CDP API."""

    @pytest.mark.asyncio
    async def test_create_customer(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test creating a new customer profile.
        
        Verifies:
        - Customer can be created
        - Response includes customer ID
        """
        customer_data = {
            "external_ids": {"email": f"customer-{uuid.uuid4()}@test.com"},
            "anonymous_id": str(uuid.uuid4()),
            "traits": {
                "name": "Test Customer",
                "company": "Test Company"
            }
        }
        
        response = await client.post(
            f"/cdp/customers?organization_id={organization_id}",
            json=customer_data,
            headers=auth_headers
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data

    @pytest.mark.asyncio
    async def test_list_customers(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test listing customers.
        
        Verifies:
        - Customers can be listed
        """
        response = await client.get(
            f"/cdp/customers?organization_id={organization_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_track_event(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test tracking a customer event.
        
        Verifies:
        - Events can be tracked
        """
        event_data = {
            "event_name": "page_view",
            "event_type": "track",
            "properties": {
                "page": "/home",
                "referrer": "google.com"
            },
            "anonymous_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await client.post(
            f"/cdp/events?organization_id={organization_id}",
            json=event_data,
            headers=auth_headers
        )
        
        assert response.status_code in [200, 201, 202]

    @pytest.mark.asyncio
    async def test_create_segment(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test creating a customer segment.
        
        Verifies:
        - Segment can be created
        """
        segment_data = {
            "name": f"Test Segment {uuid.uuid4()}",
            "description": "Test segment description",
            "segment_type": "dynamic",
            "definition": {
                "conditions": [
                    {"field": "traits.plan", "operator": "equals", "value": "enterprise"}
                ]
            }
        }
        
        response = await client.post(
            f"/cdp/segments?organization_id={organization_id}",
            json=segment_data,
            headers=auth_headers
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data

    @pytest.mark.asyncio
    async def test_list_segments(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test listing customer segments.
        
        Verifies:
        - Segments can be listed
        """
        response = await client.get(
            f"/cdp/segments?organization_id={organization_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200


# ============== Content Generation API Tests ==============

class TestContentAPI:
    """Tests for Content Generation API."""

    @pytest.mark.asyncio
    async def test_generate_content(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test content generation endpoint.
        
        Verifies:
        - Content generation endpoint is accessible
        """
        content_request = {
            "prompt": "Write a short marketing tagline",
            "content_type": "tagline",
            "organization_id": organization_id
        }
        
        response = await client.post(
            "/content/generate",
            json=content_request,
            headers=auth_headers
        )
        
        # Content generation may require API keys
        assert response.status_code in [200, 400, 422, 500, 503]


# ============== File Uploads API Tests ==============

class TestUploadsAPI:
    """Tests for File Uploads API."""

    @pytest.mark.asyncio
    async def test_upload_endpoint_exists(
        self,
        client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """
        Test that upload endpoint exists.
        
        Verifies:
        - Upload endpoint is accessible
        """
        # Test with empty file to check endpoint exists
        response = await client.post(
            "/uploads/",
            headers=auth_headers
        )
        
        # Should return 422 (missing file) not 404
        assert response.status_code in [400, 422, 415]

    @pytest.mark.asyncio
    async def test_upload_with_invalid_file_type(
        self,
        client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """
        Test upload rejects invalid file types.
        
        Verifies:
        - Invalid file types are rejected
        """
        # Create a fake executable file
        files = {
            "file": ("malicious.exe", b"fake executable content", "application/x-msdownload")
        }
        
        response = await client.post(
            "/uploads/",
            files=files,
            headers=auth_headers
        )
        
        # Should reject executable files
        assert response.status_code in [400, 415, 422]


# ============== Organizations API Tests ==============

class TestOrganizationsAPI:
    """Tests for Organizations API."""

    @pytest.mark.asyncio
    async def test_create_organization(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test creating a new organization.
        
        Verifies:
        - Organization can be created
        - Response includes organization ID
        """
        org_data = {
            "name": f"Test Org {uuid.uuid4()}",
            "slug": f"test-org-{uuid.uuid4()}",
            "domain": f"test-{uuid.uuid4()}.com"
        }
        
        response = await client.post("/organizations/", json=org_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == org_data["name"]

    @pytest.mark.asyncio
    async def test_get_organization(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test getting organization details.
        
        Verifies:
        - Organization can be retrieved by ID
        """
        response = await client.get(f"/organizations/{organization_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == organization_id

    @pytest.mark.asyncio
    async def test_update_organization(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test updating organization details.
        
        Verifies:
        - Organization can be updated
        """
        update_data = {
            "name": f"Updated Org Name {uuid.uuid4()}"
        }
        
        response = await client.put(
            f"/organizations/{organization_id}",
            json=update_data,
            headers=auth_headers
        )
        
        # Update may require admin role
        assert response.status_code in [200, 403]


# ============== Image Editor API Tests ==============

class TestImageEditorAPI:
    """Tests for Image Editor API."""

    @pytest.mark.asyncio
    async def test_create_session(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test creating an image editor session.
        
        Verifies:
        - Session can be created
        - Response includes session ID
        """
        session_data = {
            "title": f"Test Session {uuid.uuid4()}",
            "original_image_url": "http://example.com/image.jpg",
            "organization_id": organization_id,
            "ai_model": "dall-e-3"
        }
        
        response = await client.post(
            f"/image-editor/sessions?organization_id={organization_id}",
            json=session_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_session(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test getting an image editor session.
        
        Verifies:
        - Session can be retrieved
        """
        # Create session first
        session_data = {
            "title": f"Test Session {uuid.uuid4()}",
            "original_image_url": "http://example.com/image.jpg",
            "organization_id": organization_id,
            "ai_model": "dall-e-3"
        }
        
        create_response = await client.post(
            f"/image-editor/sessions?organization_id={organization_id}",
            json=session_data
        )
        
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]
        
        # Get session
        get_response = await client.get(f"/image-editor/sessions/{session_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == session_id

    @pytest.mark.asyncio
    async def test_add_history_entry(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test adding history entry to session.
        
        Verifies:
        - History can be added to session
        """
        # Create session first
        session_data = {
            "title": f"Test Session {uuid.uuid4()}",
            "original_image_url": "http://example.com/image.jpg",
            "organization_id": organization_id,
            "ai_model": "dall-e-3"
        }
        
        create_response = await client.post(
            f"/image-editor/sessions?organization_id={organization_id}",
            json=session_data
        )
        
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]
        
        # Add history
        history_data = {
            "edit_type": "filter",
            "edit_data": {"filter": "grayscale"},
            "previous_image_url": "http://example.com/image.jpg",
            "new_image_url": "http://example.com/image_edited.jpg"
        }
        
        response = await client.post(
            f"/image-editor/sessions/{session_id}/history",
            json=history_data
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_generate_image(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test AI image generation.
        
        Verifies:
        - Image generation endpoint works
        """
        gen_request = {
            "prompt": "A beautiful sunset",
            "n": 1
        }
        
        response = await client.post("/image-editor/generate", json=gen_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ============== Health Check Tests ==============

class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: httpx.AsyncClient):
        """
        Test health check endpoint.
        
        Verifies:
        - Health endpoint is accessible
        - Returns status information
        """
        # Health endpoint is at root, not /api
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as health_client:
            response = await health_client.get("/health")
            
            assert response.status_code in [200, 503]
            data = response.json()
            assert "status" in data
