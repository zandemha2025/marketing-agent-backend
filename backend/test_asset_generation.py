#!/usr/bin/env python3
"""
Asset Generation Test Script.

Tests the POST /api/assets/generate-image endpoint with various configurations.
Saves results to test_results/asset_generation_test.json
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

import httpx

# Configuration
BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
RESULTS_DIR = "test_results"
RESULTS_FILE = os.path.join(RESULTS_DIR, "asset_generation_test.json")


async def test_generate_image(
    client: httpx.AsyncClient,
    prompt: str,
    style: str = "photorealistic",
    width: int = 1024,
    height: int = 1024,
    negative_prompt: str = None,
) -> Dict[str, Any]:
    """Test the generate-image endpoint."""
    payload = {
        "prompt": prompt,
        "style": style,
        "width": width,
        "height": height,
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    
    start_time = datetime.now()
    
    try:
        response = await client.post(
            f"{BASE_URL}/api/assets/generate-image",
            json=payload,
            timeout=120.0,
        )
        
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        result = {
            "test_name": f"generate_image_{style}",
            "prompt": prompt,
            "style": style,
            "width": width,
            "height": height,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "success": response.status_code == 200,
            "timestamp": datetime.now().isoformat(),
        }
        
        if response.status_code == 200:
            data = response.json()
            result["response"] = data
            result["image_url"] = data.get("url")
            result["asset_id"] = data.get("asset_id")
            result["backend_used"] = data.get("backend_used", "unknown")
            
            # Verify image is accessible if URL is returned
            if data.get("url") and data["url"].startswith("http"):
                try:
                    img_response = await client.get(data["url"], timeout=10.0)
                    result["image_accessible"] = img_response.status_code == 200
                except Exception as e:
                    result["image_accessible"] = False
                    result["image_access_error"] = str(e)
            else:
                result["image_accessible"] = "local_file"
        else:
            result["error"] = response.text[:500]
        
        return result
        
    except Exception as e:
        return {
            "test_name": f"generate_image_{style}",
            "prompt": prompt,
            "style": style,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


async def test_endpoint_exists(client: httpx.AsyncClient) -> Dict[str, Any]:
    """Test that the endpoint exists and accepts POST requests."""
    try:
        # Test POST with minimal payload - this is the key test
        response = await client.post(
            f"{BASE_URL}/api/assets/generate-image",
            json={"prompt": "test endpoint"},
            timeout=30.0,
        )
        
        # 200 = success, 422 = validation error (endpoint exists but bad input)
        # 405 = method not allowed (the bug we're fixing)
        endpoint_works = response.status_code in (200, 422)
        
        return {
            "test_name": "endpoint_exists",
            "success": endpoint_works,
            "status_code": response.status_code,
            "method_allowed": response.status_code != 405,
            "is_405_error": response.status_code == 405,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "test_name": "endpoint_exists",
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


async def run_all_tests() -> Dict[str, Any]:
    """Run all asset generation tests."""
    results = {
        "test_suite": "Asset Generation Tests",
        "started_at": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
        }
    }
    
    async with httpx.AsyncClient() as client:
        # Test 1: Endpoint exists and accepts POST
        print("Test 1: Checking endpoint exists...")
        test_result = await test_endpoint_exists(client)
        results["tests"].append(test_result)
        print(f"  Result: {'✓ PASS' if test_result['success'] else '✗ FAIL'}")
        
        # Test 2: Generate photorealistic image
        print("\nTest 2: Generating photorealistic image...")
        test_result = await test_generate_image(
            client,
            prompt="Product photo of a sleek smartphone on a white background",
            style="photorealistic",
            width=1024,
            height=1024,
            negative_prompt="blurry, low quality, distorted",
        )
        results["tests"].append(test_result)
        print(f"  Result: {'✓ PASS' if test_result['success'] else '✗ FAIL'}")
        if test_result.get("image_url"):
            print(f"  Image URL: {test_result['image_url']}")
        
        # Test 3: Generate artistic image
        print("\nTest 3: Generating artistic image...")
        test_result = await test_generate_image(
            client,
            prompt="Abstract representation of innovation and technology",
            style="artistic",
            width=1024,
            height=1024,
        )
        results["tests"].append(test_result)
        print(f"  Result: {'✓ PASS' if test_result['success'] else '✗ FAIL'}")
        if test_result.get("image_url"):
            print(f"  Image URL: {test_result['image_url']}")
        
        # Test 4: Generate minimal image
        print("\nTest 4: Generating minimal image...")
        test_result = await test_generate_image(
            client,
            prompt="Clean minimalist logo design with geometric shapes",
            style="minimal",
            width=512,
            height=512,
        )
        results["tests"].append(test_result)
        print(f"  Result: {'✓ PASS' if test_result['success'] else '✗ FAIL'}")
        if test_result.get("image_url"):
            print(f"  Image URL: {test_result['image_url']}")
        
        # Test 5: Different aspect ratio (landscape)
        print("\nTest 5: Generating landscape image...")
        test_result = await test_generate_image(
            client,
            prompt="Marketing banner for summer sale campaign",
            style="photorealistic",
            width=1920,
            height=1080,
        )
        results["tests"].append(test_result)
        print(f"  Result: {'✓ PASS' if test_result['success'] else '✗ FAIL'}")
        if test_result.get("image_url"):
            print(f"  Image URL: {test_result['image_url']}")
    
    # Calculate summary
    results["completed_at"] = datetime.now().isoformat()
    results["summary"]["total"] = len(results["tests"])
    results["summary"]["passed"] = sum(1 for t in results["tests"] if t.get("success"))
    results["summary"]["failed"] = results["summary"]["total"] - results["summary"]["passed"]
    results["summary"]["pass_rate"] = f"{(results['summary']['passed'] / results['summary']['total'] * 100):.1f}%"
    
    return results


def save_results(results: Dict[str, Any]):
    """Save test results to JSON file."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {RESULTS_FILE}")


def print_summary(results: Dict[str, Any]):
    """Print test summary."""
    summary = results["summary"]
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests:  {summary['total']}")
    print(f"Passed:       {summary['passed']}")
    print(f"Failed:       {summary['failed']}")
    print(f"Pass Rate:    {summary['pass_rate']}")
    print("=" * 60)
    
    # Print failed tests
    failed_tests = [t for t in results["tests"] if not t.get("success")]
    if failed_tests:
        print("\nFailed Tests:")
        for test in failed_tests:
            print(f"  - {test['test_name']}: {test.get('error', 'Unknown error')}")
    
    # Check for 405 errors specifically
    has_405 = any(t.get("status_code") == 405 for t in results["tests"])
    if has_405:
        print("\n⚠️  WARNING: 405 Method Not Allowed errors detected!")
        print("   The endpoint may not be properly configured for POST requests.")
    else:
        print("\n✓ No 405 errors - POST method is properly configured!")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("ASSET GENERATION TEST SUITE")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = await run_all_tests()
    save_results(results)
    print_summary(results)
    
    # Return exit code based on results
    return 0 if results["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
