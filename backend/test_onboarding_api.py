"""
Test the onboarding API endpoint with nike.com.
This tests the complete flow from API to database.
"""
import asyncio
import httpx
import time
import json

BASE_URL = "http://localhost:8000"

def get_auth_token():
    """Get a test auth token."""
    # For testing, we'll use a simple approach
    # In production, you'd need proper authentication
    return "test_token"

async def test_onboarding_api():
    """Test the onboarding API with nike.com."""
    print("=" * 60)
    print("TESTING ONBOARDING API")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Step 1: Get auth token by creating a test user or logging in
        print("\n[1] Getting auth token...")
        
        # Try to login with test credentials
        login_data = {
            "email": "admin@example.com",
            "password": "admin123"
        }
        
        try:
            resp = await client.post(f"{BASE_URL}/api/auth/login", json=login_data)
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                print(f"✓ Logged in successfully")
            else:
                print(f"✗ Login failed: {resp.status_code}")
                print("Creating test user...")
                # Create a test user
                user_data = {
                    "email": "admin@example.com",
                    "password": "admin123",
                    "name": "Admin User"
                }
                resp = await client.post(f"{BASE_URL}/api/auth/register", json=user_data)
                if resp.status_code == 200:
                    print("✓ User created")
                    # Login again
                    resp = await client.post(f"{BASE_URL}/api/auth/login", data=login_data)
                    token = resp.json()["access_token"]
                    print("✓ Logged in successfully")
                else:
                    print(f"✗ Failed to create user: {resp.text}")
                    return
        except Exception as e:
            print(f"✗ Error during login: {e}")
            return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Start onboarding
        print("\n[2] Starting onboarding for nike.com...")
        # Use unique domain to avoid conflicts
        import time
        unique_domain = f"nike-test-{int(time.time())}.com"
        onboarding_data = {
            "domain": unique_domain,
            "company_name": "Nike Test"
        }
        
        try:
            resp = await client.post(
                f"{BASE_URL}/api/onboarding/start",
                json=onboarding_data,
                headers=headers
            )
            
            if resp.status_code == 200:
                result = resp.json()
                org_id = result["organization_id"]
                print(f"✓ Onboarding started")
                print(f"  Organization ID: {org_id}")
                print(f"  Status: {result['status']}")
                print(f"  Progress: {result['progress']['progress']:.0%}")
                print(f"  Stage: {result['progress']['stage']}")
            else:
                print(f"✗ Failed to start onboarding: {resp.status_code}")
                print(f"  Response: {resp.text}")
                return
        except Exception as e:
            print(f"✗ Error starting onboarding: {e}")
            return
        
        # Step 3: Poll for status
        print("\n[3] Polling for onboarding status...")
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                resp = await client.get(
                    f"{BASE_URL}/api/onboarding/status/{org_id}",
                    headers=headers
                )
                
                if resp.status_code == 200:
                    status = resp.json()
                    progress = status['progress']['progress']
                    stage = status['progress']['stage']
                    
                    print(f"  Attempt {attempt + 1}: {progress:.0%} - {stage}")
                    
                    if status['status'] == 'complete':
                        print(f"\n✓ Onboarding complete!")
                        break
                    elif status['status'] == 'failed':
                        print(f"\n✗ Onboarding failed: {status['progress'].get('error', 'Unknown error')}")
                        return
                else:
                    print(f"  Attempt {attempt + 1}: Error {resp.status_code}")
                
                attempt += 1
                await asyncio.sleep(2)
            except Exception as e:
                print(f"  Attempt {attempt + 1}: Error - {e}")
                attempt += 1
                await asyncio.sleep(2)
        
        # Step 4: Get the result
        print("\n[4] Getting onboarding result...")
        try:
            resp = await client.get(
                f"{BASE_URL}/api/onboarding/result/{org_id}",
                headers=headers
            )
            
            if resp.status_code == 200:
                result = resp.json()
                print("✓ Got onboarding result")
                
                # Display key data
                print("\n" + "=" * 60)
                print("EXTRACTED BRAND DNA")
                print("=" * 60)
                
                brand = result.get('brand', {})
                print(f"\nBrand Name: {brand.get('name', 'N/A')}")
                print(f"Domain: {brand.get('domain', 'N/A')}")
                print(f"Tagline: {brand.get('tagline', 'N/A')}")
                print(f"Description: {brand.get('description', 'N/A')[:100]}..." if brand.get('description') else "Description: N/A")
                
                voice = brand.get('voice', {})
                print(f"\nVoice Tone: {voice.get('tone', 'N/A')}")
                print(f"Values: {brand.get('values', 'N/A')}")
                
                market = result.get('market', {})
                print(f"\nIndustry: {market.get('industry', 'N/A')}")
                print(f"Competitors: {len(market.get('competitors', []))}")
                
                audiences = result.get('audiences', [])
                print(f"Audience Segments: {len(audiences)}")
                if isinstance(audiences, list):
                    for i, seg in enumerate(audiences[:3]):
                        print(f"  - {seg.get('name', 'N/A')}")
                
                offerings = result.get('offerings', {})
                products = offerings.get('products', [])
                print(f"\nProducts: {len(products)}")
                for i, prod in enumerate(products[:5]):
                    print(f"  - {prod.get('name', 'N/A')}")
                
                brand_dna = result.get('brand_dna', {})
                print(f"\nBrand DNA Heritage: {brand_dna.get('heritage', 'N/A')[:80] if brand_dna.get('heritage') else 'N/A'}...")
                
                # Save result to file
                with open('test_onboarding_result.json', 'w') as f:
                    json.dump(result, f, indent=2)
                print("\n✓ Full result saved to test_onboarding_result.json")
                
            else:
                print(f"✗ Failed to get result: {resp.status_code}")
                print(f"  Response: {resp.text}")
        except Exception as e:
            print(f"✗ Error getting result: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_onboarding_api())
