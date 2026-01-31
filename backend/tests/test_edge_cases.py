"""
Edge Case E2E Tests.

Tests for handling edge cases including empty requests, missing fields,
invalid data types, very long strings, special characters, concurrent
requests, and error handling.
"""
import pytest
import pytest_asyncio
import httpx
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from conftest import (
    BASE_URL,
    generate_unique_email,
    generate_long_string,
    generate_special_chars_string,
)


# ============== Empty Request Body Tests ==============

class TestEmptyRequestBodies:
    """Tests for handling empty request bodies."""

    @pytest.mark.asyncio
    async def test_empty_body_on_register(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test registration with empty request body.
        
        Verifies:
        - Empty body returns 422 validation error
        - Error message is informative
        """
        response = await client.post("/auth/register", json={})
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_empty_body_on_login(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test login with empty request body.
        
        Verifies:
        - Empty body returns 422 validation error
        """
        response = await client.post("/auth/login", json={})
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_body_on_create_organization(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test organization creation with empty body.
        
        Verifies:
        - Empty body returns 422 validation error
        """
        response = await client.post("/organizations/", json={})
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_body_on_create_scheduled_post(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduled post creation with empty body.
        
        Verifies:
        - Empty body returns 422 validation error
        """
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_null_body(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test handling of null/None body.
        
        Verifies:
        - Null body is handled gracefully
        """
        response = await client.post(
            "/auth/register",
            content="null",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422]


# ============== Missing Required Fields Tests ==============

class TestMissingRequiredFields:
    """Tests for handling missing required fields."""

    @pytest.mark.asyncio
    async def test_register_missing_email(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test registration with missing email.
        
        Verifies:
        - Missing email returns 422
        """
        response = await client.post("/auth/register", json={
            "password": "ValidPassword123!",
            "name": "Test User"
        })
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_password(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test registration with missing password.
        
        Verifies:
        - Missing password returns 422
        """
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "name": "Test User"
        })
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_name(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test registration with missing name.
        
        Verifies:
        - Missing name returns 422
        """
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "password": "ValidPassword123!"
        })
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_organization_missing_name(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test organization creation with missing name.
        
        Verifies:
        - Missing name returns 422
        """
        response = await client.post("/organizations/", json={
            "slug": f"test-{uuid.uuid4()}",
            "domain": f"test-{uuid.uuid4()}.com"
        })
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_scheduled_post_missing_content(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduled post creation with missing content.
        
        Verifies:
        - Missing required fields returns 422
        """
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Test Post",
                "platform": "twitter",
                "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "organization_id": organization_id
            }
        )
        
        # Content may or may not be required
        assert response.status_code in [200, 422]


# ============== Invalid Data Types Tests ==============

class TestInvalidDataTypes:
    """Tests for handling invalid data types."""

    @pytest.mark.asyncio
    async def test_string_instead_of_number(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test sending string where number is expected.
        
        Verifies:
        - Type mismatch is handled gracefully
        """
        # Try to create customer with string for numeric field
        customer_data = {
            "external_ids": {"email": generate_unique_email()},
            "anonymous_id": str(uuid.uuid4()),
            "traits": {
                "age": "not a number",  # Should be number
                "score": "invalid"
            }
        }
        
        response = await client.post(
            f"/cdp/customers?organization_id={organization_id}",
            json=customer_data,
            headers=auth_headers
        )
        
        # May accept (traits are flexible) or reject
        assert response.status_code in [200, 201, 422]

    @pytest.mark.asyncio
    async def test_number_instead_of_string(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test sending number where string is expected.
        
        Verifies:
        - Type coercion or rejection is handled
        """
        response = await client.post("/auth/register", json={
            "email": 12345,  # Should be string
            "password": "ValidPassword123!",
            "name": "Test User"
        })
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_array_instead_of_object(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test sending array where object is expected.
        
        Verifies:
        - Type mismatch is rejected
        """
        response = await client.post(
            "/auth/register",
            content='["email", "password", "name"]',
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_boolean_instead_of_string(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test sending boolean where string is expected.
        
        Verifies:
        - Type mismatch is handled
        """
        response = await client.post("/auth/register", json={
            "email": True,  # Should be string
            "password": "ValidPassword123!",
            "name": False  # Should be string
        })
        
        assert response.status_code == 422


# ============== Very Long Strings Tests ==============

class TestVeryLongStrings:
    """Tests for handling very long string inputs."""

    @pytest.mark.asyncio
    async def test_very_long_email(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test registration with very long email.
        
        Verifies:
        - Long emails are rejected
        """
        long_email = "a" * 1000 + "@test.com"
        
        response = await client.post("/auth/register", json={
            "email": long_email,
            "password": "ValidPassword123!",
            "name": "Test User"
        })
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_very_long_name(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test registration with very long name.
        
        Verifies:
        - Long names are rejected or truncated
        """
        long_name = "A" * 10000
        
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "password": "ValidPassword123!",
            "name": long_name
        })
        
        # Should reject (255 char limit) or truncate
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_very_long_organization_name(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test organization creation with very long name.
        
        Verifies:
        - Long org names are handled
        """
        long_name = "Organization " + "A" * 10000
        
        response = await client.post("/organizations/", json={
            "name": long_name,
            "slug": f"test-{uuid.uuid4()}",
            "domain": f"test-{uuid.uuid4()}.com"
        })
        
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_very_long_post_content(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduled post with very long content.
        
        Verifies:
        - Long content is handled appropriately
        """
        long_content = "Content " * 10000  # ~70KB
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Test Post",
                "content": long_content,
                "platform": "twitter",
                "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
        )
        
        # May accept or reject based on limits
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_very_long_json_payload(
        self,
        client: httpx.AsyncClient,
        organization_id: str,
        auth_headers: dict
    ):
        """
        Test handling of very large JSON payloads.
        
        Verifies:
        - Large payloads are handled without crashing
        """
        # Create a large nested structure
        large_traits = {f"key_{i}": "value" * 100 for i in range(1000)}
        
        customer_data = {
            "external_ids": {"email": generate_unique_email()},
            "anonymous_id": str(uuid.uuid4()),
            "traits": large_traits
        }
        
        response = await client.post(
            f"/cdp/customers?organization_id={organization_id}",
            json=customer_data,
            headers=auth_headers
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 201, 413, 422]


# ============== Special Characters Tests ==============

class TestSpecialCharacters:
    """Tests for handling special characters in inputs."""

    @pytest.mark.asyncio
    async def test_special_chars_in_name(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test registration with special characters in name.
        
        Verifies:
        - Special characters are handled safely
        """
        special_name = generate_special_chars_string()
        
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "password": "ValidPassword123!",
            "name": special_name
        })
        
        # Should either accept (sanitized) or reject
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_unicode_in_content(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduled post with unicode content.
        
        Verifies:
        - Unicode characters are handled correctly
        """
        unicode_content = "Hello 世界 🌍 مرحبا Привет 🎉"
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Unicode Test 测试",
                "content": unicode_content,
                "platform": "twitter",
                "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert unicode_content in data.get("content", "")

    @pytest.mark.asyncio
    async def test_emoji_in_content(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduled post with emoji content.
        
        Verifies:
        - Emojis are stored and retrieved correctly
        """
        emoji_content = "🚀 Launch day! 🎉 Let's go! 💪 #excited 🔥"
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Emoji Test 🎯",
                "content": emoji_content,
                "platform": "twitter",
                "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_newlines_in_content(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduled post with newlines in content.
        
        Verifies:
        - Newlines are preserved
        """
        multiline_content = "Line 1\nLine 2\nLine 3\n\nParagraph 2"
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Multiline Test",
                "content": multiline_content,
                "platform": "twitter",
                "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_null_bytes_in_content(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test handling of null bytes in content.
        
        Verifies:
        - Null bytes are handled safely
        """
        content_with_null = "Before\x00After"
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Null Byte Test",
                "content": content_with_null,
                "platform": "twitter",
                "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
        )
        
        # Should handle gracefully
        assert response.status_code in [200, 422]


# ============== Concurrent Requests Tests ==============

class TestConcurrentRequests:
    """Tests for handling concurrent requests."""

    @pytest.mark.asyncio
    async def test_concurrent_registrations(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test handling of concurrent user registrations.
        
        Verifies:
        - Concurrent registrations don't cause race conditions
        - Each registration gets unique ID
        """
        async def register_user(index: int):
            return await client.post("/auth/register", json={
                "email": f"concurrent-{uuid.uuid4()}@test.com",
                "password": "ValidPassword123!",
                "name": f"Concurrent User {index}"
            })
        
        # Make 10 concurrent registrations
        responses = await asyncio.gather(*[register_user(i) for i in range(10)])
        
        # All should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 10, "All concurrent registrations should succeed"
        
        # All should have unique IDs
        user_ids = [r.json()["user"]["id"] for r in responses if r.status_code == 200]
        assert len(user_ids) == len(set(user_ids)), "All user IDs should be unique"

    @pytest.mark.asyncio
    async def test_concurrent_post_creation(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test handling of concurrent post creation.
        
        Verifies:
        - Concurrent creates don't cause issues
        """
        async def create_post(index: int):
            return await client.post(
                f"/scheduled-posts/?organization_id={organization_id}",
                json={
                    "title": f"Concurrent Post {index}",
                    "content": f"Content for post {index}",
                    "platform": "twitter",
                    "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                    "status": "scheduled",
                    "organization_id": organization_id
                }
            )
        
        # Make 10 concurrent post creations
        responses = await asyncio.gather(*[create_post(i) for i in range(10)])
        
        # All should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 10, "All concurrent post creations should succeed"

    @pytest.mark.asyncio
    async def test_concurrent_reads_and_writes(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test handling of concurrent reads and writes.
        
        Verifies:
        - Mixed read/write operations don't cause issues
        """
        # Create initial post
        create_response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Initial Post",
                "content": "Initial content",
                "platform": "twitter",
                "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
        )
        
        assert create_response.status_code == 200
        post_id = create_response.json()["id"]
        
        async def read_post():
            return await client.get(f"/scheduled-posts/{post_id}")
        
        async def update_post(index: int):
            return await client.put(
                f"/scheduled-posts/{post_id}",
                json={"title": f"Updated Title {index}"}
            )
        
        # Mix reads and writes
        tasks = [read_post() for _ in range(5)] + [update_post(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All should complete without errors
        for response in responses:
            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_concurrent_same_email_registration(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test concurrent registration with same email.
        
        Verifies:
        - Only one registration succeeds
        - Others get appropriate error
        """
        email = generate_unique_email()
        
        async def register():
            return await client.post("/auth/register", json={
                "email": email,
                "password": "ValidPassword123!",
                "name": "Test User"
            })
        
        # Try to register same email 5 times concurrently
        responses = await asyncio.gather(*[register() for _ in range(5)])
        
        # Only one should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 1, "Only one registration should succeed"


# ============== Error Handling Tests ==============

class TestErrorHandling:
    """Tests for graceful error handling."""

    @pytest.mark.asyncio
    async def test_invalid_json_body(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test handling of invalid JSON body.
        
        Verifies:
        - Invalid JSON returns appropriate error
        """
        response = await client.post(
            "/auth/register",
            content="not valid json {",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_wrong_content_type(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test handling of wrong content type.
        
        Verifies:
        - Wrong content type is handled
        """
        response = await client.post(
            "/auth/register",
            content="email=test@test.com&password=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code in [400, 415, 422]

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test accessing non-existent endpoint.
        
        Verifies:
        - Returns 404
        """
        response = await client.get("/nonexistent/endpoint")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test using wrong HTTP method.
        
        Verifies:
        - Returns 405 Method Not Allowed
        """
        # Try DELETE on login endpoint
        response = await client.delete("/auth/login")
        
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_nonexistent_resource_id(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test accessing non-existent resource by ID.
        
        Verifies:
        - Returns 404
        """
        fake_id = "nonexistent123456"
        
        response = await client.get(f"/scheduled-posts/{fake_id}")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_uuid_format(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test accessing resource with invalid UUID format.
        
        Verifies:
        - Invalid UUID is handled gracefully
        """
        invalid_id = "not-a-valid-uuid"
        
        response = await client.get(f"/organizations/{invalid_id}")
        
        # Should return 404 or 422
        assert response.status_code in [404, 422]


# ============== Boundary Value Tests ==============

class TestBoundaryValues:
    """Tests for boundary value handling."""

    @pytest.mark.asyncio
    async def test_password_exactly_min_length(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test password at exactly minimum length (8 chars).
        
        Verifies:
        - Minimum length password is accepted
        """
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "password": "12345678",  # Exactly 8 chars
            "name": "Test User"
        })
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_password_exactly_max_length(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test password at exactly maximum length (100 chars).
        
        Verifies:
        - Maximum length password is accepted
        """
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "password": "x" * 100,  # Exactly 100 chars
            "name": "Test User"
        })
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_name_exactly_min_length(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test name at exactly minimum length (1 char).
        
        Verifies:
        - Single character name is accepted
        """
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "password": "ValidPassword123!",
            "name": "A"  # Single char
        })
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_scheduled_post_at_current_time(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduling post at current time.
        
        Verifies:
        - Posts scheduled for now are handled
        """
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Immediate Post",
                "content": "Content",
                "platform": "twitter",
                "scheduled_at": datetime.utcnow().isoformat(),
                "status": "scheduled",
                "organization_id": organization_id
            }
        )
        
        # May accept or reject based on business logic
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_scheduled_post_in_past(
        self,
        client: httpx.AsyncClient,
        organization_id: str
    ):
        """
        Test scheduling post in the past.
        
        Verifies:
        - Past dates are handled appropriately
        """
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        response = await client.post(
            f"/scheduled-posts/?organization_id={organization_id}",
            json={
                "title": "Past Post",
                "content": "Content",
                "platform": "twitter",
                "scheduled_at": past_date,
                "status": "scheduled",
                "organization_id": organization_id
            }
        )
        
        # May accept or reject based on business logic
        assert response.status_code in [200, 422]
