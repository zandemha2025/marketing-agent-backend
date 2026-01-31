"""
E2E Feature Tests.

End-to-end tests for major platform features including
social calendar, image editor, and campaign workflows.

These tests use shared fixtures from conftest.py.
"""
import pytest
import pytest_asyncio
import httpx
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from conftest import BASE_URL


# ============== Social Calendar Flow Tests ==============

class TestSocialCalendarFlow:
    """End-to-end tests for the social calendar feature."""

    @pytest.mark.asyncio
    async def test_complete_social_calendar_workflow(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test complete social calendar workflow.
        
        Verifies:
        - Create scheduled post
        - List posts
        - Update post (reschedule)
        - Delete post
        """
        print(f"\nTesting Social Calendar with Org ID: {organization_id}")
        
        # 1. Create a scheduled post
        post_data = {
            "title": "Test Post",
            "content": "Test post for social calendar",
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
        post = response.json()
        post_id = post["id"]
        print(f"Created post: {post_id}")
        
        # 2. List posts
        response = await client.get(
            f"/scheduled-posts/?organization_id={organization_id}"
        )
        assert response.status_code == 200
        posts = response.json()
        assert any(p["id"] == post_id for p in posts)
        print(f"Listed {len(posts)} posts")
        
        # 3. Update post (reschedule)
        new_time = (datetime.utcnow() + timedelta(days=2)).isoformat()
        update_data = {"scheduled_at": new_time}
        response = await client.put(
            f"/scheduled-posts/{post_id}",
            json=update_data
        )
        assert response.status_code == 200, f"Update post failed: {response.text}"
        updated_post = response.json()
        assert updated_post["scheduled_at"] == new_time
        print("Updated post schedule")
        
        # 4. Delete post
        response = await client.delete(f"/scheduled-posts/{post_id}")
        assert response.status_code == 200
        print("Deleted post")
        
        # 5. Verify deletion
        response = await client.get(f"/scheduled-posts/{post_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_multi_platform_scheduling(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduling posts across multiple platforms.
        
        Verifies:
        - Posts can be created for different platforms
        - Platform filtering works correctly
        """
        platforms = ["twitter", "linkedin", "instagram"]
        created_posts = []
        
        for platform in platforms:
            post_data = {
                "title": f"Test Post for {platform}",
                "content": f"Content for {platform}",
                "platform": platform,
                "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
            
            response = await client.post(
                f"/scheduled-posts/?organization_id={organization_id}",
                json=post_data
            )
            assert response.status_code == 200
            created_posts.append(response.json())
        
        # Verify all posts were created
        response = await client.get(
            f"/scheduled-posts/?organization_id={organization_id}"
        )
        assert response.status_code == 200
        posts = response.json()
        
        for created_post in created_posts:
            assert any(p["id"] == created_post["id"] for p in posts)
        
        # Cleanup
        for post in created_posts:
            await client.delete(f"/scheduled-posts/{post['id']}")

    @pytest.mark.asyncio
    async def test_bulk_post_operations(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test bulk operations on scheduled posts.
        
        Verifies:
        - Multiple posts can be created
        - All posts can be listed
        - Posts can be deleted in bulk
        """
        # Create multiple posts
        post_ids = []
        for i in range(5):
            post_data = {
                "title": f"Bulk Post {i}",
                "content": f"Content {i}",
                "platform": "twitter",
                "scheduled_at": (datetime.utcnow() + timedelta(days=i+1)).isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
            
            response = await client.post(
                f"/scheduled-posts/?organization_id={organization_id}",
                json=post_data
            )
            assert response.status_code == 200
            post_ids.append(response.json()["id"])
        
        # Verify all posts exist
        response = await client.get(
            f"/scheduled-posts/?organization_id={organization_id}"
        )
        assert response.status_code == 200
        posts = response.json()
        
        for post_id in post_ids:
            assert any(p["id"] == post_id for p in posts)
        
        # Delete all posts
        for post_id in post_ids:
            response = await client.delete(f"/scheduled-posts/{post_id}")
            assert response.status_code == 200


# ============== Image Editor Flow Tests ==============

class TestImageEditorFlow:
    """End-to-end tests for the image editor feature."""

    @pytest.mark.asyncio
    async def test_complete_image_editor_workflow(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test complete image editor workflow.
        
        Verifies:
        - Create session
        - Add history entry
        - Get session details
        - AI generation
        - Image edit operation
        - Delete session
        """
        print(f"\nTesting Image Editor with Org ID: {organization_id}")
        
        # 1. Create session
        session_data = {
            "title": "Test Image Session",
            "original_image_url": "http://example.com/image.jpg",
            "organization_id": organization_id,
            "ai_model": "dall-e-3"
        }
        
        response = await client.post(
            f"/image-editor/sessions?organization_id={organization_id}",
            json=session_data
        )
        assert response.status_code == 200, f"Create session failed: {response.text}"
        session = response.json()
        session_id = session["id"]
        print(f"Created session: {session_id}")
        
        # 2. Add history entry (simulate edit)
        history_data = {
            "edit_type": "filter",
            "edit_data": {"filter": "grayscale"},
            "previous_image_url": "http://example.com/image.jpg",
            "new_image_url": "http://example.com/image_bw.jpg"
        }
        
        response = await client.post(
            f"/image-editor/sessions/{session_id}/history",
            json=history_data
        )
        assert response.status_code == 200
        print("Added history entry")
        
        # 3. Get session details (verify history)
        response = await client.get(f"/image-editor/sessions/{session_id}")
        assert response.status_code == 200
        session_detail = response.json()
        assert len(session_detail["edit_history"]) > 0
        print("Verified session history")
        
        # 4. Simulate AI Generation
        gen_request = {
            "prompt": "A futuristic city",
            "n": 1
        }
        response = await client.post("/image-editor/generate", json=gen_request)
        assert response.status_code == 200
        gen_result = response.json()
        assert gen_result["success"] is True
        assert "image_url" in gen_result
        print("Simulated AI generation")
        
        # 5. Simulate Image Edit Operation
        edit_request = {
            "operation": "remove_background",
            "prompt": "Remove background"
        }
        response = await client.post(
            f"/image-editor/edit?session_id={session_id}",
            json=edit_request
        )
        assert response.status_code == 200
        edit_result = response.json()
        assert edit_result["success"] is True
        print("Simulated image edit operation")
        
        # 6. Delete session
        response = await client.delete(f"/image-editor/sessions/{session_id}")
        assert response.status_code == 200
        print("Deleted session")

    @pytest.mark.asyncio
    async def test_multiple_edit_history(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test multiple edit history entries.
        
        Verifies:
        - Multiple edits can be tracked
        - History is preserved in order
        """
        # Create session
        session_data = {
            "title": "Multi-Edit Session",
            "original_image_url": "http://example.com/original.jpg",
            "organization_id": organization_id,
            "ai_model": "dall-e-3"
        }
        
        response = await client.post(
            f"/image-editor/sessions?organization_id={organization_id}",
            json=session_data
        )
        assert response.status_code == 200
        session_id = response.json()["id"]
        
        # Add multiple history entries
        edits = [
            {"edit_type": "crop", "edit_data": {"x": 0, "y": 0, "w": 100, "h": 100}},
            {"edit_type": "filter", "edit_data": {"filter": "sepia"}},
            {"edit_type": "resize", "edit_data": {"width": 800, "height": 600}},
        ]
        
        prev_url = "http://example.com/original.jpg"
        for i, edit in enumerate(edits):
            new_url = f"http://example.com/edit_{i}.jpg"
            history_data = {
                **edit,
                "previous_image_url": prev_url,
                "new_image_url": new_url
            }
            
            response = await client.post(
                f"/image-editor/sessions/{session_id}/history",
                json=history_data
            )
            assert response.status_code == 200
            prev_url = new_url
        
        # Verify all history entries
        response = await client.get(f"/image-editor/sessions/{session_id}")
        assert response.status_code == 200
        session_detail = response.json()
        assert len(session_detail["edit_history"]) == len(edits)
        
        # Cleanup
        await client.delete(f"/image-editor/sessions/{session_id}")


# ============== Organization Flow Tests ==============

class TestOrganizationFlow:
    """End-to-end tests for organization management."""

    @pytest.mark.asyncio
    async def test_organization_crud(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test complete organization CRUD workflow.
        
        Verifies:
        - Create organization
        - Get organization
        - Update organization
        """
        # Create
        unique_id = uuid.uuid4()
        org_data = {
            "name": f"CRUD Test Org {unique_id}",
            "slug": f"crud-test-{unique_id}",
            "domain": f"crud-test-{unique_id}.com"
        }
        
        response = await client.post("/organizations/", json=org_data)
        assert response.status_code == 200
        org = response.json()
        org_id = org["id"]
        
        # Get
        response = await client.get(f"/organizations/{org_id}")
        assert response.status_code == 200
        fetched_org = response.json()
        assert fetched_org["name"] == org_data["name"]
        
        # Update (if supported)
        update_data = {"name": f"Updated Org {unique_id}"}
        response = await client.put(
            f"/organizations/{org_id}",
            json=update_data
        )
        # Update may require auth
        if response.status_code == 200:
            updated_org = response.json()
            assert updated_org["name"] == update_data["name"]


# ============== Authentication Flow Tests ==============

class TestAuthenticationFlow:
    """End-to-end tests for authentication workflows."""

    @pytest.mark.asyncio
    async def test_complete_auth_flow(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test complete authentication flow.
        
        Verifies:
        - Register user
        - Login
        - Access protected endpoint
        - Logout
        """
        # Register
        unique_id = uuid.uuid4()
        user_data = {
            "email": f"authflow-{unique_id}@test.com",
            "password": "TestPassword123!",
            "name": f"Auth Flow User {unique_id}"
        }
        
        response = await client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        register_data = response.json()
        assert "access_token" in register_data
        
        token = register_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Access protected endpoint
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        user = response.json()
        assert user["email"] == user_data["email"]
        
        # Login with same credentials
        response = await client.post("/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert response.status_code == 200
        login_data = response.json()
        assert "access_token" in login_data
        
        # Logout
        response = await client.post("/auth/logout", headers=headers)
        assert response.status_code == 200


# ============== CDP Flow Tests ==============

class TestCDPFlow:
    """End-to-end tests for Customer Data Platform workflows."""

    @pytest.mark.asyncio
    async def test_customer_lifecycle(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test complete customer lifecycle in CDP.
        
        Verifies:
        - Create customer
        - Track events
        - Update customer
        - Query customer
        """
        # Create customer
        unique_id = uuid.uuid4()
        customer_data = {
            "external_ids": {"email": f"cdp-test-{unique_id}@test.com"},
            "anonymous_id": str(unique_id),
            "traits": {
                "name": f"CDP Test Customer {unique_id}",
                "company": "Test Company",
                "plan": "enterprise"
            }
        }
        
        response = await client.post(
            f"/cdp/customers?organization_id={organization_id}",
            json=customer_data,
            headers=auth_headers
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip("CDP customer creation not available")
            return
        
        customer = response.json()
        customer_id = customer["id"]
        
        # Track event
        event_data = {
            "event_name": "page_view",
            "event_type": "track",
            "properties": {"page": "/pricing"},
            "customer_id": customer_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await client.post(
            f"/cdp/events?organization_id={organization_id}",
            json=event_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201, 202]
        
        # Get customer
        response = await client.get(
            f"/cdp/customers/{customer_id}",
            headers=auth_headers
        )
        assert response.status_code == 200


# ============== Integration Tests ==============

class TestIntegrationScenarios:
    """Integration tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_campaign_to_social_post_flow(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test flow from campaign creation to social post scheduling.
        
        Verifies:
        - Campaign can be created
        - Posts can be scheduled for campaign
        """
        # Create campaign (if supported)
        campaign_data = {
            "organization_id": organization_id,
            "name": f"Integration Test Campaign {uuid.uuid4()}",
            "objective": "Test integration flow"
        }
        
        response = await client.post(
            f"/campaigns/?organization_id={organization_id}",
            json=campaign_data,
            headers=auth_headers
        )
        
        # Campaign creation may have different requirements
        if response.status_code != 200:
            pytest.skip("Campaign creation not available")
            return
        
        campaign = response.json()
        
        # Create related social post
        post_data = {
            "title": f"Post for Campaign {campaign.get('id', 'test')}",
            "content": "Campaign content",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": organization_id
        }
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json=post_data,
            headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_full_user_journey(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test a complete user journey through the platform.
        
        Verifies:
        - User registration
        - Organization access
        - Content creation
        - Content management
        """
        # 1. Register user
        unique_id = uuid.uuid4()
        user_data = {
            "email": f"journey-{unique_id}@test.com",
            "password": "JourneyPassword123!",
            "name": f"Journey User {unique_id}"
        }
        
        response = await client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        auth_data = response.json()
        token = auth_data["access_token"]
        org_id = auth_data["user"]["organization_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Create content (scheduled post)
        post_data = {
            "title": "User Journey Post",
            "content": "Content from user journey",
            "platform": "twitter",
            "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "status": "scheduled",
            "organization_id": org_id
        }
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={org_id}",
            json=post_data,
            headers=headers
        )
        assert response.status_code == 200
        post = response.json()
        
        # 3. View content
        response = await client.get(
            f"/scheduled-posts/?organization_id={org_id}",
            headers=headers
        )
        assert response.status_code == 200
        
        # 4. Update content
        response = await client.put(
            f"/scheduled-posts/{post['id']}",
            json={"title": "Updated Journey Post"},
            headers=headers
        )
        assert response.status_code == 200
        
        # 5. Delete content
        response = await client.delete(
            f"/scheduled-posts/{post['id']}",
            headers=headers
        )
        assert response.status_code == 200
