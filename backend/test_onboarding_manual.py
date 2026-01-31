"""
Manual test script for the onboarding pipeline.
Tests the complete flow from API to database.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings
from app.services.onboarding.pipeline import OnboardingPipeline
from app.services.onboarding.firecrawl import FirecrawlService
from app.services.onboarding.perplexity import PerplexityService


async def test_api_keys():
    """Test that API keys are loaded correctly."""
    settings = get_settings()
    print("=" * 60)
    print("API KEY VERIFICATION")
    print("=" * 60)
    print(f"Firecrawl API Key: {'✓ CONFIGURED' if settings.firecrawl_api_key else '✗ MISSING'}")
    print(f"Perplexity API Key: {'✓ CONFIGURED' if settings.perplexity_api_key else '✗ MISSING'}")
    print()
    return settings.firecrawl_api_key and settings.perplexity_api_key


async def test_firecrawl():
    """Test Firecrawl service directly."""
    settings = get_settings()
    print("=" * 60)
    print("FIRECRAWL SERVICE TEST")
    print("=" * 60)
    
    service = FirecrawlService(api_key=settings.firecrawl_api_key)
    
    try:
        print("Testing Firecrawl API with nike.com...")
        result = await service.crawl_website(
            "nike.com",
            max_pages=5,  # Small number for quick test
            on_progress=lambda stage, progress, msg: print(f"  [{stage}] {progress:.0%} - {msg}")
        )
        
        print(f"\n✓ Crawl successful!")
        print(f"  - Pages crawled: {result.pages_crawled}")
        print(f"  - Domain: {result.domain}")
        print(f"  - Brand elements found: {list(result.brand_elements.keys())}")
        print(f"  - Products found: {len(result.products)}")
        
        if result.pages:
            print(f"\n  Sample page titles:")
            for page in result.pages[:3]:
                print(f"    - {page.title[:60]}... ({page.page_type})")
        
        return True, result
        
    except Exception as e:
        print(f"\n✗ Firecrawl test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None
    finally:
        await service.close()


async def test_perplexity():
    """Test Perplexity service directly."""
    settings = get_settings()
    print("\n" + "=" * 60)
    print("PERPLEXITY SERVICE TEST")
    print("=" * 60)
    
    service = PerplexityService(api_key=settings.perplexity_api_key)
    
    try:
        print("Testing Perplexity API with Nike research...")
        result = await service.research_market(
            "Nike",
            "nike.com",
            on_progress=lambda stage, progress, msg: print(f"  [{stage}] {progress:.0%} - {msg}")
        )
        
        print(f"\n✓ Research successful!")
        print(f"  - Industry: {result.industry}")
        print(f"  - Competitors found: {len(result.competitors)}")
        print(f"  - Trends found: {len(result.trends)}")
        print(f"  - Audience segments: {len(result.audience_insights)}")
        print(f"  - Brand heritage: {result.brand_heritage[:100] if result.brand_heritage else 'N/A'}...")
        
        if result.competitors:
            print(f"\n  Top competitors:")
            for comp in result.competitors[:3]:
                print(f"    - {comp.name}")
        
        return True, result
        
    except Exception as e:
        print(f"\n✗ Perplexity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None
    finally:
        await service.close()


async def test_full_pipeline():
    """Test the complete onboarding pipeline."""
    settings = get_settings()
    print("\n" + "=" * 60)
    print("FULL PIPELINE TEST")
    print("=" * 60)
    
    pipeline = OnboardingPipeline(
        firecrawl_api_key=settings.firecrawl_api_key,
        perplexity_api_key=settings.perplexity_api_key,
        max_pages=5  # Small number for quick test
    )
    
    try:
        print("Running full onboarding pipeline for nike.com...")
        
        async def progress_callback(progress):
            print(f"  [{progress.stage.value}] {progress.progress:.0%} - {progress.message}")
        
        result = await pipeline.run(
            domain="nike.com",
            organization_id="test_org_123",
            on_progress=progress_callback
        )
        
        print(f"\n{'✓' if result.success else '✗'} Pipeline completed!")
        print(f"  - Success: {result.success}")
        print(f"  - Duration: {result.duration_seconds:.1f}s")
        print(f"  - Pages analyzed: {result.pages_analyzed}")
        print(f"  - Error: {result.error or 'None'}")
        
        if result.success:
            print(f"\n  Brand Data:")
            print(f"    - Name: {result.brand_data.get('name', 'N/A')}")
            print(f"    - Description: {result.brand_data.get('description', 'N/A')[:80]}...")
            print(f"    - Values: {result.brand_data.get('values', [])}")
            
            print(f"\n  Market Data:")
            print(f"    - Industry: {result.market_data.get('industry', 'N/A')}")
            print(f"    - Competitors: {len(result.market_data.get('competitors', []))}")
            
            print(f"\n  Audience Data:")
            print(f"    - Segments: {len(result.audiences_data.get('segments', []))}")
            
            print(f"\n  Offerings Data:")
            print(f"    - Products: {len(result.offerings_data.get('products', []))}")
            
            print(f"\n  Brand DNA:")
            print(f"    - Heritage: {result.brand_dna.get('heritage', 'N/A')[:80] if result.brand_dna.get('heritage') else 'N/A'}...")
        
        return result.success, result
        
    except Exception as e:
        print(f"\n✗ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ONBOARDING PIPELINE TEST SUITE")
    print("=" * 60)
    print()
    
    # Test 1: API Keys
    keys_ok = await test_api_keys()
    if not keys_ok:
        print("\n✗ API keys not configured. Cannot continue.")
        return
    
    # Test 2: Firecrawl
    firecrawl_ok, crawl_result = await test_firecrawl()
    
    # Test 3: Perplexity
    perplexity_ok, research_result = await test_perplexity()
    
    # Test 4: Full Pipeline
    pipeline_ok, pipeline_result = await test_full_pipeline()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"API Keys: {'✓ PASS' if keys_ok else '✗ FAIL'}")
    print(f"Firecrawl: {'✓ PASS' if firecrawl_ok else '✗ FAIL'}")
    print(f"Perplexity: {'✓ PASS' if perplexity_ok else '✗ FAIL'}")
    print(f"Full Pipeline: {'✓ PASS' if pipeline_ok else '✗ FAIL'}")
    print()
    
    if pipeline_ok and pipeline_result:
        print("Sample extracted data:")
        print(f"  Brand Name: {pipeline_result.brand_data.get('name')}")
        print(f"  Industry: {pipeline_result.market_data.get('industry')}")
        print(f"  Competitors: {len(pipeline_result.market_data.get('competitors', []))}")
        print(f"  Audience Segments: {len(pipeline_result.audiences_data.get('segments', []))}")
        print(f"  Products: {len(pipeline_result.offerings_data.get('products', []))}")


if __name__ == "__main__":
    asyncio.run(main())
