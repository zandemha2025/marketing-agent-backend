"""
Shared pytest fixtures for E2E testing.

Provides common fixtures for authentication, database setup,
and test client configuration.
"""
import os
import pytest
import pytest_asyncio
import httpx
import uuid
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, Any

# Test configuration
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000/api")
TEST_TIMEOUT = 30.0


# ============== Client Fixtures ==============

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Create an async HTTP client for API testing.
    
    Yields:
        httpx.AsyncClient: Configured async client
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TEST_TIMEOUT) as ac:
        yield ac


@pytest_asyncio.fixture
async def organization_id(client: httpx.AsyncClient) -> str:
    """
    Create a test organization and return its ID.
    
    Args:
        client: HTTP client fixture
        
    Returns:
        str: Organization ID
    """
    unique_id = uuid.uuid4()
    org_data = {
        "name": f"Test Org {unique_id}",
        "slug": f"test-org-{unique_id}",
        "domain": f"test-{unique_id}.com"
    }
    response = await client.post("/organizations/", json=org_data)
    assert response.status_code == 200, f"Create org failed: {response.text}"
    return response.json()["id"]


@pytest_asyncio.fixture
async def second_organization_id(client: httpx.AsyncClient) -> str:
    """
    Create a second test organization for multi-tenant testing.
    
    Args:
        client: HTTP client fixture
        
    Returns:
        str: Second organization ID
    """
    unique_id = uuid.uuid4()
    org_data = {
        "name": f"Second Test Org {unique_id}",
        "slug": f"second-test-org-{unique_id}",
        "domain": f"second-test-{unique_id}.com"
    }
    response = await client.post("/organizations/", json=org_data)
    assert response.status_code == 200, f"Create second org failed: {response.text}"
    return response.json()["id"]


@pytest_asyncio.fixture
async def test_user_data(organization_id: str) -> Dict[str, Any]:
    """
    Generate test user data.
    
    Args:
        organization_id: Organization ID fixture
        
    Returns:
        dict: User registration data
    """
    unique_id = uuid.uuid4()
    return {
        "email": f"testuser-{unique_id}@test.com",
        "password": "TestPassword123!",
        "name": f"Test User {unique_id}",
        "organization_name": None  # Will use existing org
    }


@pytest_asyncio.fixture
async def second_user_data(second_organization_id: str) -> Dict[str, Any]:
    """
    Generate test user data for second organization.
    
    Args:
        second_organization_id: Second organization ID fixture
        
    Returns:
        dict: User registration data
    """
    unique_id = uuid.uuid4()
    return {
        "email": f"seconduser-{unique_id}@test.com",
        "password": "SecondPassword123!",
        "name": f"Second User {unique_id}",
        "organization_name": None
    }


@pytest_asyncio.fixture
async def registered_user(
    client: httpx.AsyncClient,
    organization_id: str,
    test_user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Register a test user and return user data with credentials.
    
    Args:
        client: HTTP client fixture
        organization_id: Organization ID fixture
        test_user_data: User data fixture
        
    Returns:
        dict: Registered user data including credentials
    """
    # Register user
    response = await client.post("/auth/register", json=test_user_data)
    assert response.status_code == 200, f"Registration failed: {response.text}"
    
    user_response = response.json()
    return {
        **test_user_data,
        "id": user_response["user"]["id"],
        "organization_id": user_response["user"]["organization_id"],
        "access_token": user_response["access_token"]
    }


@pytest_asyncio.fixture
async def auth_headers(registered_user: Dict[str, Any]) -> Dict[str, str]:
    """
    Get authentication headers for a registered user.
    
    Args:
        registered_user: Registered user fixture
        
    Returns:
        dict: Authorization headers
    """
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest_asyncio.fixture
async def authenticated_client(
    client: httpx.AsyncClient,
    auth_headers: Dict[str, str]
) -> httpx.AsyncClient:
    """
    Create an authenticated client with auth headers.
    
    Args:
        client: HTTP client fixture
        auth_headers: Auth headers fixture
        
    Returns:
        httpx.AsyncClient: Client with auth headers set
    """
    client.headers.update(auth_headers)
    return client


@pytest_asyncio.fixture
async def second_registered_user(
    client: httpx.AsyncClient,
    second_organization_id: str,
    second_user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Register a second test user in a different organization.
    
    Args:
        client: HTTP client fixture
        second_organization_id: Second organization ID fixture
        second_user_data: Second user data fixture
        
    Returns:
        dict: Registered user data including credentials
    """
    response = await client.post("/auth/register", json=second_user_data)
    assert response.status_code == 200, f"Second user registration failed: {response.text}"
    
    user_response = response.json()
    return {
        **second_user_data,
        "id": user_response["user"]["id"],
        "organization_id": user_response["user"]["organization_id"],
        "access_token": user_response["access_token"]
    }


@pytest_asyncio.fixture
async def second_auth_headers(second_registered_user: Dict[str, Any]) -> Dict[str, str]:
    """
    Get authentication headers for the second registered user.
    
    Args:
        second_registered_user: Second registered user fixture
        
    Returns:
        dict: Authorization headers
    """
    return {"Authorization": f"Bearer {second_registered_user['access_token']}"}


# ============== Test Data Fixtures ==============

@pytest_asyncio.fixture
async def test_campaign_data(organization_id: str) -> Dict[str, Any]:
    """
    Generate test campaign data.
    
    Args:
        organization_id: Organization ID fixture
        
    Returns:
        dict: Campaign creation data
    """
    return {
        "organization_id": organization_id,
        "name": f"Test Campaign {uuid.uuid4()}",
        "objective": "Increase brand awareness",
        "product_focus": "Test Product",
        "target_audience": "Young professionals 25-35",
        "budget_tier": "medium",
        "timeline": "4 weeks",
        "platforms": ["twitter", "linkedin"]
    }


@pytest_asyncio.fixture
async def test_asset_data(organization_id: str) -> Dict[str, Any]:
    """
    Generate test asset data.
    
    Args:
        organization_id: Organization ID fixture
        
    Returns:
        dict: Asset creation data
    """
    return {
        "organization_id": organization_id,
        "name": f"Test Asset {uuid.uuid4()}",
        "asset_type": "image",
        "content": "Test content",
        "metadata": {"format": "png", "dimensions": "1080x1080"}
    }


@pytest_asyncio.fixture
async def test_scheduled_post_data(organization_id: str) -> Dict[str, Any]:
    """
    Generate test scheduled post data.
    
    Args:
        organization_id: Organization ID fixture
        
    Returns:
        dict: Scheduled post creation data
    """
    return {
        "title": f"Test Post {uuid.uuid4()}",
        "content": "Test post content for social calendar",
        "platform": "twitter",
        "scheduled_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "status": "scheduled",
        "organization_id": organization_id
    }


@pytest_asyncio.fixture
async def test_customer_data(organization_id: str) -> Dict[str, Any]:
    """
    Generate test customer data for CDP.
    
    Args:
        organization_id: Organization ID fixture
        
    Returns:
        dict: Customer creation data
    """
    unique_id = uuid.uuid4()
    return {
        "external_ids": {"email": f"customer-{unique_id}@test.com"},
        "anonymous_id": str(unique_id),
        "traits": {
            "name": f"Test Customer {unique_id}",
            "company": "Test Company",
            "plan": "enterprise"
        }
    }


@pytest_asyncio.fixture
async def test_segment_data(organization_id: str) -> Dict[str, Any]:
    """
    Generate test segment data for CDP.
    
    Args:
        organization_id: Organization ID fixture
        
    Returns:
        dict: Segment creation data
    """
    return {
        "name": f"Test Segment {uuid.uuid4()}",
        "description": "Test segment for high-value customers",
        "segment_type": "dynamic",
        "definition": {
            "conditions": [
                {"field": "traits.plan", "operator": "equals", "value": "enterprise"}
            ]
        }
    }


# ============== Cleanup Fixtures ==============

@pytest.fixture(autouse=True)
def reset_rate_limits():
    """
    Reset rate limits between tests.
    
    This fixture runs automatically before each test.
    """
    # Rate limits are typically reset by time or by clearing Redis
    # For testing, we rely on the test server's rate limit configuration
    yield


# ============== Helper Functions ==============

def generate_unique_email() -> str:
    """Generate a unique email address for testing."""
    return f"test-{uuid.uuid4()}@test.com"


def generate_unique_slug() -> str:
    """Generate a unique slug for testing."""
    return f"test-slug-{uuid.uuid4()}"


def generate_long_string(length: int = 10000) -> str:
    """Generate a long string for edge case testing."""
    return "x" * length


def generate_special_chars_string() -> str:
    """Generate a string with special characters for testing."""
    return "<script>alert('xss')</script>'; DROP TABLE users; --"


def generate_sql_injection_payloads() -> list:
    """Generate common SQL injection payloads for testing."""
    return [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "1; SELECT * FROM users",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "1' AND '1'='1",
        "'; EXEC xp_cmdshell('dir'); --",
    ]


def generate_xss_payloads() -> list:
    """Generate common XSS payloads for testing."""
    return [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<body onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "'\"><script>alert('XSS')</script>",
    ]
