# Marketing Agent - Comprehensive Fix Plan

## Overview

This document provides a detailed, step-by-step plan to fix all issues with the Marketing Agent application. Each task includes specific file paths, exact changes needed, and testing instructions.

**Priority Order:**
1. Backend stability (get it online)
2. API keys and configuration
3. Brand analysis quality
4. AI chat functionality
5. Error handling (frontend)
6. Campaign functionality

---

## PHASE 1: Backend Stability (CRITICAL)

### Task 1.1: Check Railway Deployment Status

**Goal:** Understand why backend returns HTTP 503

**Steps:**
1. Check Railway deployment logs for errors
2. Look for crash loops, memory issues, or startup failures

**Commands to run:**
```bash
# If you have Railway CLI access:
railway logs

# Or check via Railway dashboard for:
# - Build logs
# - Runtime logs
# - Memory usage
# - CPU usage
```

**Common Issues to Look For:**
- Missing environment variables
- Database connection failures
- Module import errors
- Memory exceeded (Railway free tier = 512MB)

### Task 1.2: Verify Environment Variables on Railway

**Goal:** Ensure all required API keys are set

**Required Environment Variables:**
```env
# CRITICAL - Required for AI features
OPENROUTER_API_KEY=sk-or-v1-xxxx

# CRITICAL - Required for brand analysis
FIRECRAWL_API_KEY=fc-xxxx
PERPLEXITY_API_KEY=pplx-xxxx

# OPTIONAL - For asset generation
SEGMIND_API_KEY=SG_xxxx
ELEVENLABS_API_KEY=xxxx

# Database (Railway auto-provides for PostgreSQL add-on)
DATABASE_URL=postgresql://...

# CORS - Must include frontend URL
CORS_ORIGINS=https://frontend-arcus1.vercel.app,http://localhost:3000
```

**File to check:** `backend/app/core/config.py`

**Action:** Verify each variable is set in Railway dashboard → Variables

### Task 1.3: Fix Database Connection

**Goal:** Ensure PostgreSQL connection works

**File:** `backend/app/core/database.py`

**Check for:**
1. Async engine creation with proper pool settings
2. SSL mode for Railway PostgreSQL

**Potential Fix (if SSL issues):**
```python
# In database.py, ensure connect_args includes SSL
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"ssl": "require"} if "postgresql" in settings.database_url else {}
)
```

### Task 1.4: Add Health Check Debugging

**Goal:** Better visibility into startup issues

**File:** `backend/app/main.py`

**Add to health endpoint:**
```python
@app.get("/health")
async def health_check():
    """Health check endpoint with diagnostics."""
    import sys
    checks = {
        "status": "healthy",
        "python_version": sys.version,
        "checks": {}
    }

    # Check database
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        checks["checks"]["database"] = "connected"
    except Exception as e:
        checks["checks"]["database"] = f"error: {str(e)}"
        checks["status"] = "unhealthy"

    # Check required API keys
    from app.core.config import settings
    checks["checks"]["openrouter_key"] = "set" if settings.openrouter_api_key else "MISSING"
    checks["checks"]["firecrawl_key"] = "set" if settings.firecrawl_api_key else "MISSING"
    checks["checks"]["perplexity_key"] = "set" if settings.perplexity_api_key else "MISSING"

    return checks
```

---

## PHASE 2: Fix Brand Analysis Quality

### Task 2.1: Fix Language Detection in Firecrawl

**Goal:** Ensure English content is scraped, not localized versions

**File:** `backend/app/services/onboarding/firecrawl.py`

**Problem:** Scraper gets localized content (e.g., Dutch for stripe.com)

**Solution - Add Accept-Language header and URL parameter:**

```python
# Find the crawl/scrape method and add:

async def crawl_website(self, url: str) -> dict:
    """Crawl website with English locale forcing."""

    # Force English version
    headers = {
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (compatible; MarketingAgent/1.0)"
    }

    # Try to use English locale in URL if needed
    # For sites like stripe.com, ensure we're hitting the main domain
    parsed = urlparse(url)

    # Remove country-specific subdomains if present
    # e.g., nl.stripe.com -> stripe.com
    hostname = parsed.netloc
    if hostname.count('.') > 1:
        # Check if first part is a 2-letter country code
        parts = hostname.split('.')
        if len(parts[0]) == 2 and parts[0].isalpha():
            hostname = '.'.join(parts[1:])
            url = f"{parsed.scheme}://{hostname}{parsed.path}"

    # If using Firecrawl API:
    payload = {
        "url": url,
        "pageOptions": {
            "headers": headers,
            "waitFor": 2000,  # Wait for JS rendering
        },
        "crawlerOptions": {
            "maxPages": 50,
            "acceptLanguage": "en-US"
        }
    }

    # ... rest of implementation
```

### Task 2.2: Improve Industry Detection

**Goal:** Correctly identify company industry (e.g., Stripe = Fintech)

**File:** `backend/app/services/onboarding/perplexity.py`

**Current Issue:** Returns "Unknown" for industry

**Solution - Improve the industry detection prompt:**

```python
INDUSTRY_PROMPT = """
Analyze this company and identify its PRIMARY industry.

Company: {company_name}
Website: {website_url}
Description from website: {description}

IMPORTANT: You MUST provide a specific industry classification.
Common industries include:
- Fintech / Financial Technology
- E-commerce / Retail
- SaaS / Software
- Healthcare / Health Tech
- Education / EdTech
- Marketing / AdTech
- Enterprise Software
- Consumer Technology
- B2B Services
- Media / Entertainment

Based on what this company does, provide:
1. Primary Industry (be specific, e.g., "Financial Technology" not just "Technology")
2. Industry Segment (e.g., "Payment Processing" for a payments company)
3. Confidence level (high/medium/low)

Respond in JSON format:
{{
    "industry": "Primary Industry Name",
    "segment": "Specific Segment",
    "confidence": "high|medium|low",
    "reasoning": "Brief explanation"
}}

CRITICAL: Never return "Unknown" - always make your best assessment based on the company's products and services.
"""
```

### Task 2.3: Fix Audience Detection

**Goal:** Properly extract target audiences

**File:** `backend/app/services/onboarding/perplexity.py`

**Current Issue:** Returns "No audience data available"

**Solution - Improve audience extraction prompt:**

```python
AUDIENCE_PROMPT = """
Identify the target audiences for this company.

Company: {company_name}
Industry: {industry}
Products/Services: {offerings}
Website content: {website_summary}

You MUST identify at least 2-3 distinct audience segments. Consider:
- Who pays for the product? (B2B buyers, consumers, enterprises)
- Who uses the product? (developers, marketers, end-users)
- Company size? (startups, SMBs, enterprise)
- Job titles? (CTOs, Marketing Directors, individual contributors)

For each audience segment, provide:
1. Segment name (e.g., "Startup Founders", "Enterprise Finance Teams")
2. Demographics (company size, industry, location)
3. Psychographics (values, priorities, pain points)
4. Preferred channels (LinkedIn, Twitter, email, etc.)
5. Content preferences (technical docs, case studies, videos)

Respond in JSON:
{{
    "audiences": [
        {{
            "name": "Segment Name",
            "description": "Brief description",
            "demographics": {{
                "company_size": "startup|smb|enterprise|all",
                "industries": ["list", "of", "industries"],
                "job_titles": ["relevant", "titles"],
                "geography": "global|regional specifics"
            }},
            "psychographics": {{
                "values": ["what they care about"],
                "pain_points": ["their challenges"],
                "goals": ["what they want to achieve"]
            }},
            "channels": ["LinkedIn", "Twitter", "Email", "etc"],
            "content_preferences": ["case studies", "technical docs", "etc"]
        }}
    ]
}}

CRITICAL: You MUST return at least 2 audience segments. Never return an empty array.
"""
```

### Task 2.4: Fix Offerings Detection

**Goal:** Properly extract products and services

**File:** `backend/app/services/onboarding/firecrawl.py` (for extraction) and `perplexity.py` (for analysis)

**Current Issue:** Returns "No products or services detected"

**Solution - Improve product extraction:**

```python
# In firecrawl.py - Add better product extraction logic

def extract_products_from_pages(self, pages: list) -> list:
    """Extract products/services from crawled pages."""
    products = []

    # Look for product pages
    product_keywords = [
        'products', 'solutions', 'services', 'features',
        'platform', 'pricing', 'plans', 'offerings'
    ]

    for page in pages:
        url_lower = page.get('url', '').lower()
        title_lower = page.get('title', '').lower()

        # Check if this is a product/feature page
        is_product_page = any(kw in url_lower or kw in title_lower for kw in product_keywords)

        if is_product_page:
            # Extract product info from this page
            product = {
                "name": self._extract_product_name(page),
                "description": self._extract_description(page),
                "features": self._extract_features(page),
                "url": page.get('url')
            }
            if product["name"]:
                products.append(product)

    # Also look at structured data (JSON-LD)
    for page in pages:
        structured_data = page.get('structured_data', {})
        if structured_data.get('@type') in ['Product', 'Service', 'SoftwareApplication']:
            products.append({
                "name": structured_data.get('name'),
                "description": structured_data.get('description'),
                "features": structured_data.get('features', []),
                "url": page.get('url')
            })

    return products if products else self._infer_products_from_homepage(pages)

def _infer_products_from_homepage(self, pages: list) -> list:
    """Fallback: Infer products from homepage content."""
    # Find homepage
    homepage = next((p for p in pages if p.get('page_type') == 'home'), pages[0] if pages else None)
    if not homepage:
        return []

    # Look for product mentions in headings and key phrases
    # This is a fallback when explicit product pages aren't found
    # ... implementation
```

### Task 2.5: Update Knowledge Base Synthesis

**Goal:** Ensure all extracted data gets saved properly

**File:** `backend/app/services/onboarding/pipeline.py`

**Add validation before saving:**

```python
async def synthesize_and_save(self, org_id: str, brand_data: dict, market_data: dict,
                               audiences: list, offerings: list) -> KnowledgeBase:
    """Synthesize all data and save to knowledge base."""

    # Validate we have meaningful data
    if not brand_data.get('name'):
        brand_data['name'] = self._extract_name_from_domain(self.domain)

    if not market_data.get('industry') or market_data.get('industry') == 'Unknown':
        # Make one more attempt with AI
        market_data['industry'] = await self._infer_industry(brand_data)

    if not audiences or len(audiences) == 0:
        # Generate default audiences based on industry
        audiences = await self._generate_default_audiences(brand_data, market_data)

    if not offerings or len(offerings) == 0:
        # Infer offerings from brand description
        offerings = await self._infer_offerings(brand_data)

    # Now save
    kb = KnowledgeBase(
        organization_id=org_id,
        brand_data=brand_data,
        market_data=market_data,
        audiences_data={"segments": audiences},
        offerings_data={"products": offerings},
        research_status="complete"
    )

    return await self.kb_repo.create_or_update(kb)
```

---

## PHASE 3: Fix AI Chat Functionality

### Task 3.1: Verify OpenRouter API Connection

**Goal:** Ensure AI responses work

**File:** `backend/app/services/ai/openrouter.py`

**Add connection test:**

```python
async def test_connection(self) -> dict:
    """Test OpenRouter API connection."""
    try:
        response = await self.complete(
            prompt="Say 'Hello, I am working!' in exactly those words.",
            max_tokens=20
        )
        return {"status": "connected", "response": response}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

**Add to health check in main.py:**
```python
# In health_check endpoint
from app.services.ai.openrouter import OpenRouterService

ai_service = OpenRouterService()
ai_check = await ai_service.test_connection()
checks["checks"]["openrouter"] = ai_check["status"]
```

### Task 3.2: Fix Chat API Error Handling

**Goal:** Return proper errors instead of silent failures

**File:** `backend/app/api/chat.py`

**Improve error handling:**

```python
@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: MessageRequest,
    session: AsyncSession = Depends(get_session)
):
    """Send a message and get AI response."""
    try:
        # Get conversation
        conversation = await conv_repo.get(session, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        user_message = await conv_repo.add_message(
            session, conversation_id, "user", request.content
        )

        # Build context
        context = await build_chat_context(session, conversation)

        # Get AI response
        ai_service = OpenRouterService()

        try:
            response = await ai_service.complete(
                prompt=request.content,
                system_prompt=context.system_prompt,
                conversation_history=context.messages
            )
        except Exception as e:
            # Log the error
            logger.error(f"AI service error: {e}")
            # Return a helpful error to the user
            raise HTTPException(
                status_code=503,
                detail=f"AI service temporarily unavailable: {str(e)}"
            )

        # Save assistant message
        assistant_message = await conv_repo.add_message(
            session, conversation_id, "assistant", response
        )

        return {
            "user_message": user_message,
            "assistant_message": assistant_message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Task 3.3: Fix Streaming Chat Response

**Goal:** Ensure SSE streaming works properly

**File:** `backend/app/api/chat.py`

**Fix streaming endpoint:**

```python
@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: str,
    request: MessageRequest,
    session: AsyncSession = Depends(get_session)
):
    """Stream AI response using Server-Sent Events."""

    async def generate():
        try:
            # ... context building ...

            ai_service = OpenRouterService()
            full_response = ""

            async for chunk in ai_service.stream(
                prompt=request.content,
                system_prompt=context.system_prompt,
                conversation_history=context.messages
            ):
                full_response += chunk
                yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"

            # Save the complete response
            await conv_repo.add_message(
                session, conversation_id, "assistant", full_response
            )

            yield f"data: {json.dumps({'content': '', 'done': True, 'full_content': full_response})}\n\n"

        except Exception as e:
            logger.exception(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Important for nginx proxies
        }
    )
```

---

## PHASE 4: Fix Frontend Error Handling

### Task 4.1: Add Global Error Boundary

**Goal:** Catch and display React errors

**Create new file:** `frontend/src/components/ErrorBoundary.jsx`

```jsx
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('React Error Boundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message || 'An unexpected error occurred'}</p>
          <button onClick={() => window.location.reload()}>
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

**Update:** `frontend/src/main.jsx`
```jsx
import ErrorBoundary from './components/ErrorBoundary';

// Wrap app with ErrorBoundary
<ErrorBoundary>
  <ConvexProvider client={convex}>
    <App />
  </ConvexProvider>
</ErrorBoundary>
```

### Task 4.2: Add API Error Toast Notifications

**Goal:** Show user-friendly errors for API failures

**Create:** `frontend/src/components/Toast.jsx`

```jsx
import React, { useState, useEffect } from 'react';

export const ToastContext = React.createContext();

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'error', duration = 5000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, duration);
    }
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast toast--${toast.type}`}>
            <span>{toast.message}</span>
            <button onClick={() => removeToast(toast.id)}>×</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => React.useContext(ToastContext);
```

### Task 4.3: Update API Service with Better Errors

**File:** `frontend/src/services/api.js`

**Improve error handling:**

```javascript
class ApiService {
  constructor() {
    this.baseUrl = `${import.meta.env.VITE_API_URL || ''}/api`;
    this.onError = null; // Callback for error handling
  }

  setErrorHandler(handler) {
    this.onError = handler;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;

        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          // Response wasn't JSON
        }

        // Map common errors to user-friendly messages
        const userMessage = this.getUserFriendlyError(response.status, errorMessage);

        const error = new Error(userMessage);
        error.status = response.status;
        error.originalMessage = errorMessage;

        // Call error handler if set
        if (this.onError) {
          this.onError(userMessage, response.status);
        }

        throw error;
      }

      return await response.json();
    } catch (error) {
      if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
        const networkError = new Error('Unable to connect to server. Please check your connection.');
        networkError.status = 0;

        if (this.onError) {
          this.onError(networkError.message, 0);
        }

        throw networkError;
      }
      throw error;
    }
  }

  getUserFriendlyError(status, originalMessage) {
    const errorMap = {
      400: 'Invalid request. Please check your input.',
      401: 'Please log in to continue.',
      403: 'You don\'t have permission for this action.',
      404: 'The requested resource was not found.',
      429: 'Too many requests. Please wait a moment.',
      500: 'Server error. Our team has been notified.',
      502: 'Server is temporarily unavailable. Please try again.',
      503: 'Service is temporarily unavailable. Please try again in a moment.',
    };

    return errorMap[status] || originalMessage;
  }
}

export const api = new ApiService();
```

### Task 4.4: Fix DashboardPage Error Handling

**File:** `frontend/src/pages/DashboardPage.jsx`

**Add proper error states:**

```jsx
// Add state for errors and loading
const [error, setError] = useState(null);
const [isLoading, setIsLoading] = useState(true);

// Update loadData function
const loadData = async () => {
  setIsLoading(true);
  setError(null);

  try {
    const kb = await api.getKnowledgeBase(organizationId);
    setKnowledgeBase(kb);
  } catch (err) {
    console.error('Failed to load knowledge base:', err);
    setError(err.message || 'Failed to load brand data');
  }

  try {
    const campaigns = await api.listCampaigns(organizationId);
    setCampaigns(campaigns);
  } catch (err) {
    console.error('Failed to load campaigns:', err);
    // Don't overwrite existing error, but log it
  }

  setIsLoading(false);
};

// In render, show error state
if (error) {
  return (
    <div className="dashboard-error">
      <h2>Unable to load dashboard</h2>
      <p>{error}</p>
      <button onClick={loadData}>Try Again</button>
    </div>
  );
}

if (isLoading) {
  return <div className="dashboard-loading">Loading...</div>;
}
```

### Task 4.5: Fix Brand Knowledge Base Display

**File:** `frontend/src/pages/DashboardPage.jsx`

**Current Issue:** Brand page shows empty despite data being loaded

**Fix the renderBrandView function:**

```jsx
const renderBrandView = () => {
  if (!knowledgeBase) {
    return (
      <div className="brand-empty">
        <p>No brand data available</p>
        <p>Complete onboarding to analyze your brand.</p>
      </div>
    );
  }

  const { brand_data, market_data, audiences_data, offerings_data } = knowledgeBase;

  return (
    <div className="brand-view">
      <h2>Brand Knowledge Base</h2>

      {/* Brand Identity Section */}
      <section className="brand-section">
        <h3>Brand Identity</h3>
        <div className="brand-grid">
          <div className="brand-item">
            <label>Name</label>
            <p>{brand_data?.name || 'Not set'}</p>
          </div>
          <div className="brand-item">
            <label>Tagline</label>
            <p>{brand_data?.tagline || 'Not set'}</p>
          </div>
          <div className="brand-item">
            <label>Description</label>
            <p>{brand_data?.description || 'Not set'}</p>
          </div>
          <div className="brand-item">
            <label>Voice & Tone</label>
            <p>{brand_data?.voice || brand_data?.tone || 'Not set'}</p>
          </div>
        </div>
      </section>

      {/* Market Section */}
      <section className="brand-section">
        <h3>Market Position</h3>
        <div className="brand-grid">
          <div className="brand-item">
            <label>Industry</label>
            <p>{market_data?.industry || 'Not identified'}</p>
          </div>
          <div className="brand-item">
            <label>Market Position</label>
            <p>{market_data?.position || market_data?.market_position || 'Not analyzed'}</p>
          </div>
        </div>

        {market_data?.competitors?.length > 0 && (
          <div className="brand-item">
            <label>Competitors</label>
            <ul>
              {market_data.competitors.map((c, i) => (
                <li key={i}>{typeof c === 'string' ? c : c.name}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Audiences Section */}
      <section className="brand-section">
        <h3>Target Audiences</h3>
        {audiences_data?.segments?.length > 0 ? (
          <div className="audience-grid">
            {audiences_data.segments.map((segment, i) => (
              <div key={i} className="audience-card">
                <h4>{segment.name}</h4>
                <p>{segment.description}</p>
                {segment.pain_points && (
                  <div>
                    <label>Pain Points</label>
                    <ul>
                      {segment.pain_points.map((p, j) => <li key={j}>{p}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="no-data">No audience data available</p>
        )}
      </section>

      {/* Offerings Section */}
      <section className="brand-section">
        <h3>Products & Services</h3>
        {offerings_data?.products?.length > 0 ? (
          <div className="offerings-grid">
            {offerings_data.products.map((product, i) => (
              <div key={i} className="offering-card">
                <h4>{product.name}</h4>
                <p>{product.description}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="no-data">No products or services detected</p>
        )}
      </section>
    </div>
  );
};
```

### Task 4.6: Add Loading States to Chat

**File:** `frontend/src/pages/DashboardPage.jsx` (chat section)

**Add visual feedback while waiting for AI:**

```jsx
// In chat section
const [isSending, setIsSending] = useState(false);

const handleSendMessage = async () => {
  if (!inputMessage.trim() || isSending) return;

  setIsSending(true);

  // Add user message immediately (optimistic)
  const userMsg = { role: 'user', content: inputMessage };
  setMessages(prev => [...prev, userMsg]);
  setInputMessage('');

  // Add placeholder for assistant
  const placeholderId = Date.now();
  setMessages(prev => [...prev, {
    id: placeholderId,
    role: 'assistant',
    content: '',
    isLoading: true
  }]);

  try {
    const response = await api.sendMessage(conversationId, inputMessage);

    // Replace placeholder with real response
    setMessages(prev => prev.map(m =>
      m.id === placeholderId
        ? { ...response.assistant_message, isLoading: false }
        : m
    ));
  } catch (err) {
    // Remove placeholder and show error
    setMessages(prev => prev.filter(m => m.id !== placeholderId));
    setError(err.message || 'Failed to send message');
  } finally {
    setIsSending(false);
  }
};

// In render, show loading indicator
{messages.map((msg, i) => (
  <div key={i} className={`message message--${msg.role}`}>
    {msg.isLoading ? (
      <div className="message-loading">
        <span className="dot"></span>
        <span className="dot"></span>
        <span className="dot"></span>
      </div>
    ) : (
      msg.content
    )}
  </div>
))}
```

---

## PHASE 5: Fix Campaign Functionality

### Task 5.1: Fix Campaign Creation API

**File:** `backend/app/api/campaigns.py`

**Improve error handling and validation:**

```python
@router.post("/")
async def create_campaign(
    request: CampaignCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new campaign."""
    try:
        # Validate organization exists
        org = await org_repo.get(session, request.organization_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Create campaign
        campaign = Campaign(
            organization_id=request.organization_id,
            name=request.name,
            objective=request.goal,
            target_audience=request.target_audience,
            platforms=request.platforms or [],
            status="draft"
        )

        session.add(campaign)
        await session.commit()
        await session.refresh(campaign)

        return campaign

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create campaign: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")
```

### Task 5.2: Fix Frontend Campaign Creation

**File:** `frontend/src/pages/DashboardPage.jsx` or `CampaignCreate.jsx`

**Add proper error handling:**

```jsx
const handleCreateCampaign = async (campaignData) => {
  setIsCreating(true);
  setCreateError(null);

  try {
    const newCampaign = await api.createCampaign({
      ...campaignData,
      organization_id: organizationId
    });

    // Add to list
    setCampaigns(prev => [...prev, newCampaign]);

    // Close modal and navigate
    setShowCreateModal(false);
    setSelectedCampaign(newCampaign);

  } catch (err) {
    console.error('Failed to create campaign:', err);
    setCreateError(err.message || 'Failed to create campaign. Please try again.');
  } finally {
    setIsCreating(false);
  }
};

// In modal, show error
{createError && (
  <div className="form-error">
    {createError}
    <button onClick={() => setCreateError(null)}>Dismiss</button>
  </div>
)}
```

---

## PHASE 6: Testing & Verification

### Task 6.1: Create Backend Health Test Script

**Create:** `backend/test_health.py`

```python
import asyncio
import httpx

async def test_backend():
    base_url = "https://marketing-agent-backend-production-9983.up.railway.app"

    print("Testing backend health...")

    async with httpx.AsyncClient(timeout=30) as client:
        # Health check
        try:
            r = await client.get(f"{base_url}/health")
            print(f"Health: {r.status_code}")
            print(r.json())
        except Exception as e:
            print(f"Health check failed: {e}")

        # Test onboarding
        try:
            r = await client.post(
                f"{base_url}/api/onboarding/start",
                json={"website_url": "https://stripe.com"}
            )
            print(f"Onboarding: {r.status_code}")
            print(r.json())
        except Exception as e:
            print(f"Onboarding failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_backend())
```

### Task 6.2: Frontend Testing Checklist

**Manual test checklist after fixes:**

1. **Onboarding Flow**
   - [ ] Enter stripe.com as website
   - [ ] Progress shows correctly
   - [ ] Results show English content
   - [ ] Industry is "Financial Technology" or "Fintech"
   - [ ] At least 2 audiences detected
   - [ ] Products/services detected

2. **Chat Functionality**
   - [ ] Send message shows loading indicator
   - [ ] AI responds within 30 seconds
   - [ ] Errors show user-friendly message
   - [ ] Can have multi-turn conversation

3. **Campaign Creation**
   - [ ] Form validates required fields
   - [ ] Submit shows loading state
   - [ ] Success navigates to campaign detail
   - [ ] Error shows message with retry option

4. **Brand Knowledge Base**
   - [ ] Page shows all brand data
   - [ ] Industry displayed correctly
   - [ ] Audiences displayed with details
   - [ ] Offerings/products displayed

5. **Error Handling**
   - [ ] Network errors show toast
   - [ ] Server errors show friendly message
   - [ ] Retry buttons work
   - [ ] No silent failures

---

## Summary of Files to Modify

### Backend Files:
1. `backend/app/main.py` - Add health check diagnostics
2. `backend/app/core/config.py` - Verify settings
3. `backend/app/core/database.py` - Fix PostgreSQL SSL
4. `backend/app/api/chat.py` - Add error handling, fix streaming
5. `backend/app/api/campaigns.py` - Add error handling
6. `backend/app/services/onboarding/firecrawl.py` - Fix language, add product extraction
7. `backend/app/services/onboarding/perplexity.py` - Improve prompts for industry/audience/offerings
8. `backend/app/services/onboarding/pipeline.py` - Add validation before save
9. `backend/app/services/ai/openrouter.py` - Add connection test

### Frontend Files:
1. `frontend/src/main.jsx` - Add ErrorBoundary and ToastProvider
2. `frontend/src/services/api.js` - Improve error handling
3. `frontend/src/pages/DashboardPage.jsx` - Fix error states, brand display, chat loading
4. `frontend/src/components/ErrorBoundary.jsx` - NEW FILE
5. `frontend/src/components/Toast.jsx` - NEW FILE

### Environment Variables to Verify (Railway):
- `OPENROUTER_API_KEY`
- `FIRECRAWL_API_KEY`
- `PERPLEXITY_API_KEY`
- `DATABASE_URL`
- `CORS_ORIGINS`

---

## Prompt for Claude Code

Use this prompt to give Claude Code the tasks:

```
I need you to fix the Marketing Agent application. Here's the detailed plan:

PLAN FILE: Read /sessions/charming-upbeat-galileo/mnt/workflow/MARKETING_AGENT_FIX_PLAN.md

Start with Phase 1 (Backend Stability):
1. First, check Railway deployment logs for errors
2. Verify all environment variables are set correctly
3. Add health check diagnostics to backend/app/main.py

Then move to Phase 2 (Brand Analysis):
1. Fix language detection in firecrawl.py to force English
2. Improve industry detection prompts in perplexity.py
3. Fix audience and offerings extraction

Important rules:
- Read each file before modifying it
- Make minimal, targeted changes
- Test after each major change
- Don't skip any steps in the plan
- Report any errors you encounter
```

---

## Estimated Time

- Phase 1 (Backend Stability): 1-2 hours
- Phase 2 (Brand Analysis): 2-3 hours
- Phase 3 (Chat): 1-2 hours
- Phase 4 (Frontend Errors): 2-3 hours
- Phase 5 (Campaigns): 1 hour
- Phase 6 (Testing): 1 hour

**Total: 8-12 hours**
