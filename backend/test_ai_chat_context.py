"""
AI Chat Context Test Script

Tests that the AI chat feature properly loads and uses brand context
from the knowledge base when answering questions.

Test Questions:
1. "What is our brand voice?" → Should mention the brand's tone/voice
2. "What products do we offer?" → Should list the brand's products
3. "Who are our competitors?" → Should list competitors from knowledge base

Quality Criteria:
- Response mentions brand name
- Response references brand values
- Response uses correct tone
- Response knows products/services
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import httpx

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_RESULTS_DIR = Path(__file__).parent.parent / "test_results"

# Test brand data - using a fictional brand for testing
TEST_BRAND_DATA = {
    "name": "TechFlow Solutions",
    "domain": "techflow.io",
    "tagline": "Streamline Your Digital Future",
    "description": "TechFlow Solutions is a leading B2B SaaS company that helps businesses automate their workflows and increase productivity through AI-powered tools.",
    "mission": "To democratize access to enterprise-grade automation tools for businesses of all sizes.",
    "values": ["innovation", "customer-first", "transparency", "simplicity"],
    "voice": {
        "tone": ["professional", "approachable", "innovative", "confident"],
        "personality": "We're the knowledgeable friend who makes complex technology simple",
        "vocabulary": ["streamline", "empower", "seamless", "intelligent", "future-proof"],
        "avoid": ["cheap", "basic", "complicated", "legacy"],
        "sample_phrases": [
            "Let's build something amazing together",
            "Your success is our mission",
            "Simplify. Automate. Grow."
        ]
    },
    "visual_identity": {
        "primary_color": "#2563EB",
        "secondary_colors": ["#1E40AF", "#DBEAFE"],
        "fonts": {"heading": "Inter", "body": "Open Sans"}
    }
}

TEST_MARKET_DATA = {
    "industry": "B2B SaaS / Workflow Automation",
    "market_position": "Challenger in mid-market segment, growing rapidly",
    "competitors": [
        {
            "name": "Zapier",
            "domain": "zapier.com",
            "positioning": "Market leader in no-code automation",
            "strengths": ["brand recognition", "large integration library", "ease of use"],
            "weaknesses": ["expensive at scale", "limited enterprise features"]
        },
        {
            "name": "Make (Integromat)",
            "domain": "make.com",
            "positioning": "Visual automation platform for power users",
            "strengths": ["powerful visual builder", "competitive pricing"],
            "weaknesses": ["steeper learning curve", "smaller ecosystem"]
        },
        {
            "name": "Workato",
            "domain": "workato.com",
            "positioning": "Enterprise integration and automation",
            "strengths": ["enterprise-grade security", "deep integrations"],
            "weaknesses": ["high price point", "complex setup"]
        }
    ],
    "trends": [
        {"trend": "AI-powered automation", "relevance": "high", "opportunity": "Early mover advantage with AI features"},
        {"trend": "Low-code/no-code movement", "relevance": "high", "opportunity": "Expand accessibility"},
        {"trend": "Remote work tools", "relevance": "medium", "opportunity": "Integration opportunities"}
    ]
}

TEST_OFFERINGS_DATA = {
    "products": [
        {
            "name": "TechFlow Starter",
            "description": "Perfect for small teams getting started with automation",
            "features": ["5 workflows", "1,000 tasks/month", "Email support"],
            "pricing": "$29/month",
            "target_segment": "Small businesses"
        },
        {
            "name": "TechFlow Pro",
            "description": "Advanced automation for growing businesses",
            "features": ["Unlimited workflows", "50,000 tasks/month", "Priority support", "Custom integrations"],
            "pricing": "$99/month",
            "target_segment": "Mid-market"
        },
        {
            "name": "TechFlow Enterprise",
            "description": "Full-scale automation with enterprise security",
            "features": ["Unlimited everything", "SSO/SAML", "Dedicated support", "SLA guarantee"],
            "pricing": "Custom pricing",
            "target_segment": "Enterprise"
        }
    ],
    "services": [
        {
            "name": "Implementation Support",
            "description": "White-glove onboarding and setup assistance",
            "benefits": ["Faster time to value", "Best practices guidance"]
        },
        {
            "name": "Custom Integration Development",
            "description": "Build custom connectors for your unique systems",
            "benefits": ["Connect any system", "Dedicated engineering support"]
        }
    ],
    "key_differentiators": [
        "AI-powered workflow suggestions",
        "Industry-leading uptime (99.99%)",
        "Transparent pricing with no hidden fees",
        "24/7 human support on all plans"
    ]
}

TEST_AUDIENCES_DATA = {
    "segments": [
        {
            "name": "Operations Managers",
            "size": "primary",
            "demographics": {
                "age_range": "30-50",
                "job_titles": ["Operations Manager", "COO", "Process Manager"],
                "company_size": "50-500 employees"
            },
            "psychographics": {
                "values": ["efficiency", "reliability", "cost savings"],
                "challenges": ["manual processes", "data silos", "scaling operations"],
                "goals": ["reduce manual work", "improve accuracy", "scale without hiring"]
            },
            "pain_points": ["Too many manual tasks", "Disconnected systems", "Lack of visibility"],
            "preferred_channels": ["linkedin", "email", "webinars"]
        }
    ]
}


async def create_test_user_and_org(client: httpx.AsyncClient) -> dict:
    """Create a test user and organization with knowledge base."""
    
    # Generate unique identifiers
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_email = f"test_chat_{timestamp}@example.com"
    test_org_name = f"TechFlow Test {timestamp}"
    
    # Register user - this also creates an organization automatically
    register_response = await client.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "email": test_email,
            "password": "TestPassword123!",
            "name": "Test User"
        }
    )
    
    if register_response.status_code != 200:
        # User might already exist, try login
        login_response = await client.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": test_email,
                "password": "TestPassword123!"
            }
        )
        if login_response.status_code != 200:
            raise Exception(f"Failed to register/login: {register_response.text}")
        auth_data = login_response.json()
    else:
        auth_data = register_response.json()
    
    token = auth_data.get("access_token")
    user_data = auth_data.get("user", {})
    user_id = user_data.get("id") or auth_data.get("user_id")
    # Organization is created during registration
    org_id = user_data.get("organization_id") or auth_data.get("organization_id")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # If org_id not in response, get it from user profile
    if not org_id:
        me_response = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers=headers
        )
        if me_response.status_code == 200:
            me_data = me_response.json()
            org_id = me_data.get("organization_id")
    
    if not org_id:
        raise Exception("Could not determine organization ID from registration")
    
    # Update knowledge base via the organizations API
    kb_response = await client.put(
        f"{BASE_URL}/api/organizations/{org_id}/knowledge-base",
        headers=headers,
        json={
            "brand_data": TEST_BRAND_DATA,
            "market_data": TEST_MARKET_DATA,
            "offerings_data": TEST_OFFERINGS_DATA,
            "audiences_data": TEST_AUDIENCES_DATA,
            "context_data": {}
        }
    )
    
    if kb_response.status_code != 200:
        print(f"Note: Could not save KB via API ({kb_response.status_code}: {kb_response.text}), will use direct DB access")
    else:
        print(f"  ✓ Knowledge base updated via API")
    
    return {
        "token": token,
        "user_id": user_id,
        "org_id": org_id,
        "org_name": test_org_name,
        "headers": headers
    }


async def create_knowledge_base_direct(org_id: str) -> bool:
    """Create knowledge base directly in database."""
    from app.core.database import get_session
    from app.repositories.knowledge_base import KnowledgeBaseRepository
    
    async for session in get_session():
        repo = KnowledgeBaseRepository(session)
        
        # Check if KB already exists
        existing = await repo.get_by_organization(org_id)
        if existing:
            # Update existing KB
            await repo.save_onboarding_result(
                organization_id=org_id,
                brand_data=TEST_BRAND_DATA,
                market_data=TEST_MARKET_DATA,
                audiences_data=TEST_AUDIENCES_DATA,
                offerings_data=TEST_OFFERINGS_DATA,
                context_data={}
            )
        else:
            # Create new KB
            await repo.save_onboarding_result(
                organization_id=org_id,
                brand_data=TEST_BRAND_DATA,
                market_data=TEST_MARKET_DATA,
                audiences_data=TEST_AUDIENCES_DATA,
                offerings_data=TEST_OFFERINGS_DATA,
                context_data={}
            )
        
        await session.commit()
        return True
    
    return False


async def create_conversation(client: httpx.AsyncClient, headers: dict, org_id: str) -> str:
    """Create a new conversation."""
    response = await client.post(
        f"{BASE_URL}/api/chat/conversations",
        headers=headers,
        json={
            "organization_id": org_id,
            "title": "AI Chat Context Test",
            "context_type": "general"
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to create conversation: {response.text}")
    
    return response.json().get("id")


async def send_message(client: httpx.AsyncClient, headers: dict, conversation_id: str, message: str) -> str:
    """Send a message and get AI response."""
    response = await client.post(
        f"{BASE_URL}/api/chat/conversations/{conversation_id}/messages",
        headers=headers,
        params={"stream": "false"},
        json={"content": message},
        timeout=120.0  # Longer timeout for AI response
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to send message: {response.text}")
    
    data = response.json()
    return data.get("response") or data.get("content") or ""


def evaluate_response(question: str, response: str, criteria: dict) -> dict:
    """Evaluate if the response meets quality criteria."""
    response_lower = response.lower()
    
    results = {
        "question": question,
        "response": response,
        "checks": {},
        "score": 0.0
    }
    
    total_checks = 0
    passed_checks = 0
    
    for check_name, check_terms in criteria.items():
        total_checks += 1
        # Check if any of the terms appear in the response
        found = any(term.lower() in response_lower for term in check_terms)
        results["checks"][check_name] = {
            "passed": found,
            "expected_terms": check_terms,
            "found_in_response": found
        }
        if found:
            passed_checks += 1
    
    results["score"] = passed_checks / total_checks if total_checks > 0 else 0.0
    return results


async def run_tests():
    """Run the AI chat context tests."""
    print("=" * 60)
    print("AI Chat Context Test")
    print("=" * 60)
    print()
    
    results = {
        "test_name": "AI Chat Context Test",
        "timestamp": datetime.now().isoformat(),
        "test_brand": TEST_BRAND_DATA["name"],
        "questions": [],
        "overall_score": 0.0,
        "status": "pending"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Step 1: Create test user and organization
            print("Step 1: Creating test user and organization...")
            test_data = await create_test_user_and_org(client)
            print(f"  ✓ Created organization: {test_data['org_name']}")
            print(f"  ✓ Organization ID: {test_data['org_id']}")
            
            # Step 2: Ensure knowledge base exists
            print("\nStep 2: Setting up knowledge base...")
            try:
                kb_created = await create_knowledge_base_direct(test_data['org_id'])
                if kb_created:
                    print("  ✓ Knowledge base created/updated with test brand data")
            except Exception as e:
                print(f"  ! Warning: Could not create KB directly: {e}")
                print("  ! Will proceed with test anyway")
            
            # Step 3: Create conversation
            print("\nStep 3: Creating conversation...")
            conversation_id = await create_conversation(
                client, 
                test_data['headers'], 
                test_data['org_id']
            )
            print(f"  ✓ Conversation created: {conversation_id}")
            
            # Step 4: Test questions
            print("\nStep 4: Testing brand context questions...")
            print("-" * 40)
            
            test_questions = [
                {
                    "question": "What is our brand voice?",
                    "criteria": {
                        "mentions_tone": ["professional", "approachable", "innovative", "confident"],
                        "mentions_personality": ["knowledgeable", "friend", "simple", "technology"],
                        "mentions_vocabulary": ["streamline", "empower", "seamless", "intelligent"]
                    }
                },
                {
                    "question": "What products do we offer?",
                    "criteria": {
                        "mentions_products": ["TechFlow Starter", "TechFlow Pro", "TechFlow Enterprise", "Starter", "Pro", "Enterprise"],
                        "mentions_features": ["workflow", "automation", "tasks", "support"],
                        "mentions_pricing": ["$29", "$99", "custom", "month"]
                    }
                },
                {
                    "question": "Who are our competitors?",
                    "criteria": {
                        "mentions_competitors": ["Zapier", "Make", "Integromat", "Workato"],
                        "mentions_positioning": ["automation", "integration", "enterprise", "no-code"],
                        "mentions_differentiation": ["AI", "uptime", "pricing", "support"]
                    }
                }
            ]
            
            total_score = 0.0
            
            for i, test in enumerate(test_questions, 1):
                print(f"\nQuestion {i}: {test['question']}")
                
                try:
                    response = await send_message(
                        client,
                        test_data['headers'],
                        conversation_id,
                        test['question']
                    )
                    
                    evaluation = evaluate_response(
                        test['question'],
                        response,
                        test['criteria']
                    )
                    
                    results["questions"].append(evaluation)
                    total_score += evaluation["score"]
                    
                    print(f"  Response preview: {response[:200]}...")
                    print(f"  Score: {evaluation['score']:.2f}")
                    
                    for check_name, check_result in evaluation["checks"].items():
                        status = "✓" if check_result["passed"] else "✗"
                        print(f"    {status} {check_name}: {check_result['passed']}")
                    
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    results["questions"].append({
                        "question": test['question'],
                        "error": str(e),
                        "score": 0.0
                    })
            
            # Calculate overall score
            results["overall_score"] = total_score / len(test_questions) if test_questions else 0.0
            results["status"] = "passed" if results["overall_score"] >= 0.5 else "failed"
            
            print("\n" + "=" * 60)
            print("TEST RESULTS")
            print("=" * 60)
            print(f"Overall Quality Score: {results['overall_score']:.2f}")
            print(f"Status: {results['status'].upper()}")
            print()
            
            # Quality criteria summary
            print("Quality Criteria:")
            for q_result in results["questions"]:
                q = q_result.get("question", "Unknown")
                s = q_result.get("score", 0)
                status = "✓" if s >= 0.5 else "✗"
                print(f"  {status} {q}: {s:.2f}")
            
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            import traceback
            traceback.print_exc()
    
    # Save results
    TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_file = TEST_RESULTS_DIR / "ai_chat_context_test.json"
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {results_file}")
    
    return results


if __name__ == "__main__":
    results = asyncio.run(run_tests())
    
    # Exit with appropriate code
    if results.get("status") == "passed":
        sys.exit(0)
    else:
        sys.exit(1)
