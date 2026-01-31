"""
Test script for campaign execution functionality.

This script tests:
1. Campaign creation
2. Campaign execution (via Celery task)
3. Status tracking
4. Deliverable generation
"""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test organization and user credentials
TEST_ORG = {
    "name": "Test Organization",
    "website": "https://example.com"
}

TEST_USER = {
    "email": "test_campaign@example.com",
    "password": "testpassword123",
    "name": "Test User"
}

TEST_CAMPAIGN = {
    "name": "Summer Sale Campaign 2024",
    "objective": "Drive sales and increase brand awareness for summer collection",
    "product_focus": "Summer apparel and accessories",
    "target_audience": "Fashion-conscious millennials aged 25-40",
    "budget_tier": "medium",
    "timeline": "4 weeks",
    "platforms": ["instagram", "facebook", "email"]
}


async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Get authentication token."""
    # Try to login first using JSON body
    response = await client.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
    )
    
    if response.status_code == 200:
        return response.json()["access_token"]
    
    # If login fails, register
    print("Registering new user...")
    response = await client.post(
        f"{BASE_URL}/api/auth/register",
        json=TEST_USER
    )
    
    if response.status_code in (200, 201):
        # Login after registration using JSON body
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        return response.json()["access_token"]
    
    raise Exception(f"Failed to authenticate: {response.text}")


async def get_or_create_organization(client: httpx.AsyncClient, token: str) -> str:
    """Get or create test organization."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # List existing organizations
    response = await client.get(
        f"{BASE_URL}/api/organizations",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        # Handle both list and dict with organizations key
        if isinstance(result, list) and result:
            return result[0]["id"]
        elif isinstance(result, dict):
            orgs = result.get("organizations", [])
            if orgs:
                return orgs[0]["id"]
            # Try other keys
            if "id" in result:
                return result["id"]
    
    # Get current user to find their organization
    response = await client.get(
        f"{BASE_URL}/api/users/me",
        headers=headers
    )
    
    if response.status_code == 200:
        user = response.json()
        org_id = user.get("organization_id")
        if org_id:
            return org_id
    
    raise Exception(f"Failed to get organization. User response: {response.text}")


async def test_campaign_creation(client: httpx.AsyncClient, token: str, org_id: str):
    """Test campaign creation."""
    print("\n=== Testing Campaign Creation ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    campaign_data = {
        **TEST_CAMPAIGN,
        "organization_id": org_id
    }
    
    response = await client.post(
        f"{BASE_URL}/api/campaigns",
        json=campaign_data,
        headers=headers
    )
    
    if response.status_code not in (200, 201):
        print(f"FAILED: Campaign creation failed: {response.text}")
        return None
    
    campaign = response.json()
    print(f"SUCCESS: Created campaign '{campaign['name']}' with ID: {campaign['id']}")
    print(f"  Status: {campaign['status']}")
    print(f"  Objective: {campaign['objective']}")
    
    return campaign["id"]


async def test_campaign_execution(client: httpx.AsyncClient, token: str, campaign_id: str):
    """Test campaign execution."""
    print("\n=== Testing Campaign Execution ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post(
        f"{BASE_URL}/api/campaigns/{campaign_id}/execute",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"FAILED: Campaign execution failed: {response.text}")
        return False
    
    result = response.json()
    print(f"SUCCESS: Campaign execution initiated")
    print(f"  Task ID: {result.get('task_id')}")
    print(f"  Status: {result.get('status')}")
    print(f"  Message: {result.get('message')}")
    
    return True


async def test_campaign_status(client: httpx.AsyncClient, token: str, campaign_id: str):
    """Test campaign status endpoint."""
    print("\n=== Testing Campaign Status ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get(
        f"{BASE_URL}/api/campaigns/{campaign_id}/status",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"FAILED: Status check failed: {response.text}")
        return None
    
    status = response.json()
    print(f"SUCCESS: Campaign status retrieved")
    print(f"  Status: {status.get('status')}")
    print(f"  Progress: {status.get('progress')}")
    print(f"  Concepts: {status.get('concepts_count', 0)}")
    
    return status


async def test_list_campaigns(client: httpx.AsyncClient, token: str, org_id: str):
    """Test listing campaigns."""
    print("\n=== Testing List Campaigns ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get(
        f"{BASE_URL}/api/campaigns",
        params={"organization_id": org_id},
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"FAILED: List campaigns failed: {response.text}")
        return []
    
    result = response.json()
    campaigns = result.get("campaigns", [])
    print(f"SUCCESS: Found {len(campaigns)} campaigns")
    
    for campaign in campaigns:
        print(f"  - {campaign['name']} ({campaign['status']})")
    
    return campaigns


async def test_deliverables(client: httpx.AsyncClient, token: str, campaign_id: str):
    """Test deliverables endpoint."""
    print("\n=== Testing Deliverables ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get(
        f"{BASE_URL}/api/deliverables",
        params={"campaign_id": campaign_id},
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"INFO: Deliverables endpoint not available or error: {response.text}")
        return []
    
    deliverables = response.json()
    if isinstance(deliverables, list):
        print(f"SUCCESS: Found {len(deliverables)} deliverables")
        for d in deliverables[:5]:  # Show first 5
            print(f"  - {d.get('title', 'Untitled')} ({d.get('type', 'unknown')})")
        return deliverables
    else:
        print(f"INFO: Deliverables response: {deliverables}")
        return []


async def run_tests():
    """Run all campaign execution tests."""
    print("=" * 60)
    print("CAMPAIGN EXECUTION TEST SUITE")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Step 1: Authenticate
            print("\n--- Step 1: Authentication ---")
            token = await get_auth_token(client)
            print(f"SUCCESS: Authenticated")
            
            # Step 2: Get organization
            print("\n--- Step 2: Organization ---")
            org_id = await get_or_create_organization(client, token)
            print(f"SUCCESS: Using organization {org_id}")
            
            # Step 3: Create campaign
            print("\n--- Step 3: Campaign Creation ---")
            campaign_id = await test_campaign_creation(client, token, org_id)
            if not campaign_id:
                print("\nFAILED: Cannot continue without campaign")
                return
            
            # Step 4: Execute campaign
            print("\n--- Step 4: Campaign Execution ---")
            execution_started = await test_campaign_execution(client, token, campaign_id)
            if not execution_started:
                print("\nWARNING: Campaign execution may have issues")
            
            # Step 5: Check status
            print("\n--- Step 5: Status Check ---")
            status = await test_campaign_status(client, token, campaign_id)
            
            # Step 6: List campaigns
            print("\n--- Step 6: List Campaigns ---")
            campaigns = await test_list_campaigns(client, token, org_id)
            
            # Step 7: Check deliverables (if available)
            print("\n--- Step 7: Deliverables ---")
            deliverables = await test_deliverables(client, token, campaign_id)
            
            # Summary
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            print(f"Campaign ID: {campaign_id}")
            print(f"Campaign Status: {status.get('status') if status else 'unknown'}")
            print(f"Total Campaigns: {len(campaigns)}")
            print(f"Deliverables: {len(deliverables)}")
            
            if status and status.get('status') in ['queued', 'in_progress', 'completed']:
                print("\n✓ Campaign execution infrastructure is working!")
            else:
                print("\n⚠ Campaign execution may need further investigation")
            
            return {
                "campaign_id": campaign_id,
                "status": status.get('status') if status else 'unknown',
                "campaigns_count": len(campaigns),
                "deliverables_count": len(deliverables)
            }
            
        except Exception as e:
            print(f"\nFAILED: Test suite error: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    result = asyncio.run(run_tests())
    
    if result:
        print("\n" + "=" * 60)
        print("FINAL RESULT")
        print("=" * 60)
        print(json.dumps(result, indent=2))
    else:
        print("\nTests failed to complete")
        exit(1)
