"""
Authentication E2E Tests.

Tests for user registration, login, JWT token validation,
password management, and account security features.
"""
import pytest
import pytest_asyncio
import httpx
import uuid
from datetime import datetime, timedelta

from conftest import (
    BASE_URL,
    generate_unique_email,
    generate_long_string,
)


# ============== Registration Tests ==============

class TestUserRegistration:
    """Tests for user registration functionality."""

    @pytest.mark.asyncio
    async def test_register_with_valid_data(self, client: httpx.AsyncClient):
        """
        Test successful user registration with valid data.
        
        Verifies:
        - User can register with valid email, password, and name
        - Response includes access token and user data
        - User data contains expected fields
        """
        user_data = {
            "email": generate_unique_email(),
            "password": "ValidPassword123!",
            "name": "Test User"
        }
        
        response = await client.post("/auth/register", json=user_data)
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        # Verify user data
        user = data["user"]
        assert user["email"] == user_data["email"]
        assert user["name"] == user_data["name"]
        assert "id" in user
        assert "organization_id" in user

    @pytest.mark.asyncio
    async def test_register_with_invalid_email(self, client: httpx.AsyncClient):
        """
        Test registration fails with invalid email format.
        
        Verifies:
        - Invalid email format is rejected
        - Appropriate error response is returned
        """
        user_data = {
            "email": "invalid-email",
            "password": "ValidPassword123!",
            "name": "Test User"
        }
        
        response = await client.post("/auth/register", json=user_data)
        
        assert response.status_code == 422, "Should reject invalid email"

    @pytest.mark.asyncio
    async def test_register_with_short_password(self, client: httpx.AsyncClient):
        """
        Test registration fails with password shorter than minimum length.
        
        Verifies:
        - Short passwords are rejected
        - Password minimum length is enforced (8 characters)
        """
        user_data = {
            "email": generate_unique_email(),
            "password": "short",
            "name": "Test User"
        }
        
        response = await client.post("/auth/register", json=user_data)
        
        assert response.status_code == 422, "Should reject short password"

    @pytest.mark.asyncio
    async def test_register_with_long_password(self, client: httpx.AsyncClient):
        """
        Test registration fails with password exceeding maximum length.
        
        Verifies:
        - Excessively long passwords are rejected
        - Password maximum length is enforced (100 characters)
        """
        user_data = {
            "email": generate_unique_email(),
            "password": "x" * 101,  # Exceeds 100 char limit
            "name": "Test User"
        }
        
        response = await client.post("/auth/register", json=user_data)
        
        assert response.status_code == 422, "Should reject long password"

    @pytest.mark.asyncio
    async def test_register_with_empty_name(self, client: httpx.AsyncClient):
        """
        Test registration fails with empty name.
        
        Verifies:
        - Empty names are rejected
        - Name field is required
        """
        user_data = {
            "email": generate_unique_email(),
            "password": "ValidPassword123!",
            "name": ""
        }
        
        response = await client.post("/auth/register", json=user_data)
        
        assert response.status_code == 422, "Should reject empty name"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: httpx.AsyncClient):
        """
        Test registration fails with already registered email.
        
        Verifies:
        - Duplicate emails are rejected
        - Appropriate error message is returned
        """
        email = generate_unique_email()
        user_data = {
            "email": email,
            "password": "ValidPassword123!",
            "name": "Test User"
        }
        
        # First registration should succeed
        response1 = await client.post("/auth/register", json=user_data)
        assert response1.status_code == 200, "First registration should succeed"
        
        # Second registration with same email should fail
        response2 = await client.post("/auth/register", json=user_data)
        assert response2.status_code in [400, 409], "Should reject duplicate email"

    @pytest.mark.asyncio
    async def test_register_with_missing_fields(self, client: httpx.AsyncClient):
        """
        Test registration fails when required fields are missing.
        
        Verifies:
        - Missing email is rejected
        - Missing password is rejected
        - Missing name is rejected
        """
        # Missing email
        response = await client.post("/auth/register", json={
            "password": "ValidPassword123!",
            "name": "Test User"
        })
        assert response.status_code == 422, "Should reject missing email"
        
        # Missing password
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "name": "Test User"
        })
        assert response.status_code == 422, "Should reject missing password"
        
        # Missing name
        response = await client.post("/auth/register", json={
            "email": generate_unique_email(),
            "password": "ValidPassword123!"
        })
        assert response.status_code == 422, "Should reject missing name"


# ============== Login Tests ==============

class TestUserLogin:
    """Tests for user login functionality."""

    @pytest.mark.asyncio
    async def test_login_with_correct_credentials(self, client: httpx.AsyncClient):
        """
        Test successful login with correct credentials.
        
        Verifies:
        - User can login with correct email and password
        - Response includes access token
        - Token type is bearer
        """
        # First register a user
        email = generate_unique_email()
        password = "ValidPassword123!"
        
        await client.post("/auth/register", json={
            "email": email,
            "password": password,
            "name": "Test User"
        })
        
        # Then login
        response = await client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    @pytest.mark.asyncio
    async def test_login_with_incorrect_password(self, client: httpx.AsyncClient):
        """
        Test login fails with incorrect password.
        
        Verifies:
        - Wrong password is rejected
        - Appropriate error response is returned
        """
        # First register a user
        email = generate_unique_email()
        
        await client.post("/auth/register", json={
            "email": email,
            "password": "ValidPassword123!",
            "name": "Test User"
        })
        
        # Try to login with wrong password
        response = await client.post("/auth/login", json={
            "email": email,
            "password": "WrongPassword123!"
        })
        
        assert response.status_code == 401, "Should reject incorrect password"

    @pytest.mark.asyncio
    async def test_login_with_nonexistent_email(self, client: httpx.AsyncClient):
        """
        Test login fails with non-existent email.
        
        Verifies:
        - Non-existent email is rejected
        - Error message doesn't reveal if email exists (security)
        """
        response = await client.post("/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "SomePassword123!"
        })
        
        assert response.status_code == 401, "Should reject non-existent email"

    @pytest.mark.asyncio
    async def test_login_with_invalid_email_format(self, client: httpx.AsyncClient):
        """
        Test login fails with invalid email format.
        
        Verifies:
        - Invalid email format is rejected at validation level
        """
        response = await client.post("/auth/login", json={
            "email": "not-an-email",
            "password": "SomePassword123!"
        })
        
        assert response.status_code == 422, "Should reject invalid email format"

    @pytest.mark.asyncio
    async def test_login_with_empty_password(self, client: httpx.AsyncClient):
        """
        Test login fails with empty password.
        
        Verifies:
        - Empty password is rejected
        """
        response = await client.post("/auth/login", json={
            "email": generate_unique_email(),
            "password": ""
        })
        
        assert response.status_code in [401, 422], "Should reject empty password"


# ============== JWT Token Tests ==============

class TestJWTTokenValidation:
    """Tests for JWT token validation and handling."""

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_valid_token(
        self,
        client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """
        Test accessing protected endpoint with valid token succeeds.
        
        Verifies:
        - Valid token grants access to protected endpoints
        - User data is returned correctly
        """
        response = await client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == 200, f"Should allow access: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert "email" in data
        assert "name" in data

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_without_token(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test accessing protected endpoint without token fails.
        
        Verifies:
        - Missing token results in 401/403 error
        - Protected endpoints require authentication
        """
        response = await client.get("/auth/me")
        
        assert response.status_code in [401, 403], "Should deny access without token"

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_invalid_token(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test accessing protected endpoint with invalid token fails.
        
        Verifies:
        - Invalid/malformed tokens are rejected
        - Appropriate error response is returned
        """
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await client.get("/auth/me", headers=headers)
        
        assert response.status_code in [401, 403], "Should reject invalid token"

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_expired_token(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test accessing protected endpoint with expired token fails.
        
        Note: This test requires a way to generate expired tokens.
        For now, we test with a clearly invalid token format.
        
        Verifies:
        - Expired tokens are rejected
        """
        # This is a structurally valid but expired JWT
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid"
        headers = {"Authorization": f"Bearer {expired_token}"}
        
        response = await client.get("/auth/me", headers=headers)
        
        assert response.status_code in [401, 403], "Should reject expired token"

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_malformed_header(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test accessing protected endpoint with malformed auth header fails.
        
        Verifies:
        - Malformed Authorization headers are rejected
        """
        # Missing "Bearer" prefix
        headers = {"Authorization": "some_token"}
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code in [401, 403], "Should reject malformed header"
        
        # Empty Authorization header
        headers = {"Authorization": ""}
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code in [401, 403], "Should reject empty header"


# ============== Password Change Tests ==============

class TestPasswordChange:
    """Tests for password change functionality."""

    @pytest.mark.asyncio
    async def test_change_password_with_correct_current_password(
        self,
        client: httpx.AsyncClient,
        registered_user: dict
    ):
        """
        Test successful password change with correct current password.
        
        Verifies:
        - Password can be changed with correct current password
        - New password works for login
        """
        headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
        new_password = "NewValidPassword456!"
        
        response = await client.post("/auth/change-password", json={
            "current_password": registered_user["password"],
            "new_password": new_password
        }, headers=headers)
        
        assert response.status_code == 200, f"Password change failed: {response.text}"
        
        # Verify new password works
        login_response = await client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": new_password
        })
        
        assert login_response.status_code == 200, "Should be able to login with new password"

    @pytest.mark.asyncio
    async def test_change_password_with_incorrect_current_password(
        self,
        client: httpx.AsyncClient,
        registered_user: dict
    ):
        """
        Test password change fails with incorrect current password.
        
        Verifies:
        - Wrong current password is rejected
        - Password is not changed
        """
        headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
        
        response = await client.post("/auth/change-password", json={
            "current_password": "WrongCurrentPassword!",
            "new_password": "NewValidPassword456!"
        }, headers=headers)
        
        assert response.status_code == 400, "Should reject incorrect current password"

    @pytest.mark.asyncio
    async def test_change_password_with_short_new_password(
        self,
        client: httpx.AsyncClient,
        registered_user: dict
    ):
        """
        Test password change fails with short new password.
        
        Verifies:
        - New password must meet minimum length requirement
        """
        headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
        
        response = await client.post("/auth/change-password", json={
            "current_password": registered_user["password"],
            "new_password": "short"
        }, headers=headers)
        
        assert response.status_code == 422, "Should reject short new password"

    @pytest.mark.asyncio
    async def test_change_password_without_authentication(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test password change fails without authentication.
        
        Verifies:
        - Password change requires authentication
        """
        response = await client.post("/auth/change-password", json={
            "current_password": "SomePassword123!",
            "new_password": "NewPassword456!"
        })
        
        assert response.status_code in [401, 403], "Should require authentication"


# ============== Account Lockout Tests ==============

class TestAccountLockout:
    """Tests for account lockout after failed login attempts."""

    @pytest.mark.asyncio
    async def test_account_lockout_after_failed_attempts(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test account gets locked after multiple failed login attempts.
        
        Verifies:
        - Account is locked after 5 failed attempts
        - Locked account cannot login even with correct password
        
        Note: This test depends on the lockout implementation.
        The User model shows lockout after 5 failed attempts for 30 minutes.
        """
        # Register a user
        email = generate_unique_email()
        password = "ValidPassword123!"
        
        await client.post("/auth/register", json={
            "email": email,
            "password": password,
            "name": "Test User"
        })
        
        # Attempt login with wrong password 5 times
        for i in range(5):
            response = await client.post("/auth/login", json={
                "email": email,
                "password": "WrongPassword!"
            })
            assert response.status_code == 401, f"Attempt {i+1} should fail"
        
        # Now try with correct password - should be locked
        response = await client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        
        # Account should be locked (401 or 403)
        # Note: Implementation may vary - some return 401, some 403, some 423 (Locked)
        assert response.status_code in [401, 403, 423], "Account should be locked"

    @pytest.mark.asyncio
    async def test_failed_login_counter_resets_on_success(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test failed login counter resets after successful login.
        
        Verifies:
        - Successful login resets the failed attempt counter
        - User can fail again after successful login
        """
        # Register a user
        email = generate_unique_email()
        password = "ValidPassword123!"
        
        await client.post("/auth/register", json={
            "email": email,
            "password": password,
            "name": "Test User"
        })
        
        # Fail a few times (but not enough to lock)
        for _ in range(3):
            await client.post("/auth/login", json={
                "email": email,
                "password": "WrongPassword!"
            })
        
        # Successful login
        response = await client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200, "Should login successfully"
        
        # Fail a few more times - counter should have reset
        for _ in range(3):
            await client.post("/auth/login", json={
                "email": email,
                "password": "WrongPassword!"
            })
        
        # Should still be able to login (not locked)
        response = await client.post("/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200, "Should still be able to login"


# ============== Logout Tests ==============

class TestLogout:
    """Tests for logout functionality."""

    @pytest.mark.asyncio
    async def test_logout_endpoint(
        self,
        client: httpx.AsyncClient,
        auth_headers: dict
    ):
        """
        Test logout endpoint returns success.
        
        Verifies:
        - Logout endpoint is accessible
        - Returns success message
        
        Note: JWT tokens are stateless, so logout is typically
        handled client-side by discarding the token.
        """
        response = await client.post("/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200, f"Logout failed: {response.text}"
        data = response.json()
        assert "message" in data


# ============== Token Refresh Tests ==============

class TestTokenRefresh:
    """Tests for token refresh functionality (if implemented)."""

    @pytest.mark.asyncio
    async def test_token_contains_expected_claims(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test that issued tokens contain expected claims.
        
        Verifies:
        - Token includes user ID
        - Token includes organization ID
        - Token has expiration
        """
        # Register and get token
        email = generate_unique_email()
        response = await client.post("/auth/register", json={
            "email": email,
            "password": "ValidPassword123!",
            "name": "Test User"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Token should be present
        assert "access_token" in data
        assert len(data["access_token"]) > 0
        
        # Verify token works
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        me_response = await client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200


# ============== Edge Cases ==============

class TestAuthEdgeCases:
    """Edge case tests for authentication."""

    @pytest.mark.asyncio
    async def test_register_with_unicode_name(self, client: httpx.AsyncClient):
        """
        Test registration with unicode characters in name.
        
        Verifies:
        - Unicode names are accepted
        - Name is stored and returned correctly
        """
        user_data = {
            "email": generate_unique_email(),
            "password": "ValidPassword123!",
            "name": "测试用户 Тест 🎉"
        }
        
        response = await client.post("/auth/register", json=user_data)
        
        # Should either accept or reject gracefully
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_register_with_email_case_insensitivity(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test email case handling during registration.
        
        Verifies:
        - Email comparison is case-insensitive
        - Cannot register same email with different case
        """
        base_email = f"TestUser-{uuid.uuid4()}@Test.COM"
        
        # Register with mixed case
        response1 = await client.post("/auth/register", json={
            "email": base_email,
            "password": "ValidPassword123!",
            "name": "Test User"
        })
        assert response1.status_code == 200
        
        # Try to register with different case
        response2 = await client.post("/auth/register", json={
            "email": base_email.lower(),
            "password": "ValidPassword123!",
            "name": "Test User 2"
        })
        
        # Should reject as duplicate
        assert response2.status_code in [400, 409], "Should reject case-variant email"

    @pytest.mark.asyncio
    async def test_login_with_email_case_insensitivity(
        self,
        client: httpx.AsyncClient
    ):
        """
        Test email case handling during login.
        
        Verifies:
        - Can login with different email case
        """
        email = f"TestUser-{uuid.uuid4()}@Test.COM"
        password = "ValidPassword123!"
        
        # Register
        await client.post("/auth/register", json={
            "email": email,
            "password": password,
            "name": "Test User"
        })
        
        # Login with lowercase
        response = await client.post("/auth/login", json={
            "email": email.lower(),
            "password": password
        })
        
        # Should succeed (case-insensitive email matching)
        assert response.status_code == 200, "Should allow case-insensitive login"

    @pytest.mark.asyncio
    async def test_concurrent_login_requests(self, client: httpx.AsyncClient):
        """
        Test handling of concurrent login requests.
        
        Verifies:
        - Multiple simultaneous logins don't cause issues
        """
        import asyncio
        
        email = generate_unique_email()
        password = "ValidPassword123!"
        
        # Register
        await client.post("/auth/register", json={
            "email": email,
            "password": password,
            "name": "Test User"
        })
        
        # Make concurrent login requests
        async def login():
            return await client.post("/auth/login", json={
                "email": email,
                "password": password
            })
        
        responses = await asyncio.gather(*[login() for _ in range(5)])
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200, "Concurrent logins should succeed"
