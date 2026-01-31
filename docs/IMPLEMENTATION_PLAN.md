# Implementation Plan - Marketing Agent v2

## Overview

Rebuilding the marketing agent from the ground up with:
- Magical onboarding (deep client intelligence)
- Multi-user collaboration
- Professional asset management
- Claude Desktop-style UI

---

## Phase 1: Foundation (Current Sprint)

### 1.1 Database Schema

```sql
-- Multi-tenancy & Users
organizations
├── id, name, domain, created_at
├── settings (JSON)
└── subscription_tier

users
├── id, email, name, avatar_url
├── organization_id (FK)
├── role (admin, editor, viewer)
└── created_at, last_active

-- Knowledge Base
knowledge_bases
├── id, organization_id (FK)
├── brand_data (JSONB) -- name, visual_identity, voice, values
├── market_data (JSONB) -- competitors, trends, position
├── offerings_data (JSONB) -- products, services
├── context_data (JSONB) -- social, press, history
├── created_at, updated_at
└── research_status (pending, in_progress, complete, failed)

-- Campaigns
campaigns
├── id, organization_id (FK)
├── name, description
├── status (draft, active, paused, completed)
├── brief_data (JSONB)
├── strategy_data (JSONB)
├── created_by (FK users)
├── created_at, updated_at

campaign_phases
├── id, campaign_id (FK)
├── name, order_index
├── status, timeline
├── created_at

-- Assets
assets
├── id, campaign_id (FK), phase_id (FK nullable)
├── type (email, social_post, landing_page, ad, etc.)
├── name
├── current_version
├── status (draft, in_review, needs_changes, approved, published)
├── created_by (FK users)
├── created_at, updated_at

asset_versions
├── id, asset_id (FK)
├── version_number
├── content (JSONB) -- type-specific content
├── change_summary
├── created_by
├── created_at

asset_comments
├── id, asset_id (FK), version_number
├── user_id (FK)
├── content
├── position (JSONB nullable) -- for inline comments
├── resolved
├── parent_id (FK nullable) -- for replies
├── created_at

-- Conversations
conversations
├── id, organization_id (FK)
├── campaign_id (FK nullable)
├── asset_id (FK nullable)
├── scope (global, campaign, asset)
├── created_at

messages
├── id, conversation_id (FK)
├── role (user, assistant, system)
├── content
├── metadata (JSONB) -- options, brand_card, etc.
├── created_at
```

### 1.2 Project Structure

```
/workflow-v2
├── /backend
│   ├── /app
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # DB connection
│   │   │
│   │   ├── /models              # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── organization.py
│   │   │   ├── knowledge_base.py
│   │   │   ├── campaign.py
│   │   │   ├── asset.py
│   │   │   └── conversation.py
│   │   │
│   │   ├── /schemas             # Pydantic schemas
│   │   │   ├── user.py
│   │   │   ├── knowledge_base.py
│   │   │   ├── campaign.py
│   │   │   └── asset.py
│   │   │
│   │   ├── /api                 # Route handlers
│   │   │   ├── auth.py
│   │   │   ├── onboarding.py
│   │   │   ├── knowledge_base.py
│   │   │   ├── campaigns.py
│   │   │   ├── assets.py
│   │   │   └── chat.py
│   │   │
│   │   ├── /services            # Business logic
│   │   │   ├── /onboarding
│   │   │   │   ├── pipeline.py      # Orchestrator
│   │   │   │   ├── firecrawl.py     # Website analysis
│   │   │   │   ├── perplexity.py    # Market research
│   │   │   │   ├── brand_analyzer.py
│   │   │   │   └── competitor_analyzer.py
│   │   │   │
│   │   │   ├── /campaigns
│   │   │   │   ├── brief_generator.py
│   │   │   │   ├── strategy_engine.py
│   │   │   │   └── phase_planner.py
│   │   │   │
│   │   │   ├── /assets
│   │   │   │   ├── generator.py
│   │   │   │   ├── version_control.py
│   │   │   │   └── /generators      # Type-specific
│   │   │   │       ├── email.py
│   │   │   │       ├── social.py
│   │   │   │       ├── landing_page.py
│   │   │   │       └── ad.py
│   │   │   │
│   │   │   └── /ai
│   │   │       ├── claude.py        # Claude API wrapper
│   │   │       ├── prompts.py       # Prompt templates
│   │   │       └── context.py       # Context builder
│   │   │
│   │   └── /utils
│   │       ├── auth.py
│   │       └── helpers.py
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── /frontend
│   ├── /src
│   │   ├── index.html
│   │   ├── app.js               # Main app
│   │   ├── state.js             # State management
│   │   ├── api.js               # API client
│   │   │
│   │   ├── /components
│   │   │   ├── Layout.js
│   │   │   ├── Sidebar.js
│   │   │   ├── Chat.js
│   │   │   ├── RightPanel.js
│   │   │   │
│   │   │   ├── /onboarding
│   │   │   │   ├── DomainInput.js
│   │   │   │   ├── ResearchProgress.js
│   │   │   │   └── KnowledgePresentation.js
│   │   │   │
│   │   │   ├── /brand
│   │   │   │   ├── BrandCard.js
│   │   │   │   ├── CompetitorList.js
│   │   │   │   └── AudienceInsights.js
│   │   │   │
│   │   │   ├── /campaign
│   │   │   │   ├── CampaignList.js
│   │   │   │   ├── CampaignDashboard.js
│   │   │   │   ├── BriefViewer.js
│   │   │   │   └── PhaseTimeline.js
│   │   │   │
│   │   │   └── /assets
│   │   │       ├── AssetLibrary.js
│   │   │       ├── AssetPreview.js
│   │   │       ├── VersionHistory.js
│   │   │       └── CommentThread.js
│   │   │
│   │   └── /styles
│   │       └── tailwind.css
│   │
│   └── package.json
│
├── /docs
│   ├── SYSTEM_DESIGN.md
│   ├── API.md
│   └── DEPLOYMENT.md
│
└── docker-compose.yml
```

### 1.3 Onboarding Pipeline

```python
# /services/onboarding/pipeline.py

class OnboardingPipeline:
    """
    Orchestrates the magical onboarding experience.

    Flow:
    1. User enters domain
    2. We crawl their website deeply
    3. We research their market with Perplexity
    4. We analyze and structure everything
    5. We present a comprehensive knowledge base
    """

    def __init__(
        self,
        firecrawl: FirecrawlService,
        perplexity: PerplexityService,
        brand_analyzer: BrandAnalyzer,
        competitor_analyzer: CompetitorAnalyzer,
        db: Database
    ):
        self.firecrawl = firecrawl
        self.perplexity = perplexity
        self.brand_analyzer = brand_analyzer
        self.competitor_analyzer = competitor_analyzer
        self.db = db

    async def run(
        self,
        domain: str,
        organization_id: str,
        progress_callback: Callable[[str, float], None] = None
    ) -> KnowledgeBase:
        """
        Run the full onboarding pipeline.

        Args:
            domain: The client's website domain
            organization_id: The org to attach this to
            progress_callback: Optional callback for progress updates
                              (stage_name, percent_complete)
        """

        def update_progress(stage: str, pct: float):
            if progress_callback:
                progress_callback(stage, pct)

        # Stage 1: Deep website crawl (30%)
        update_progress("Analyzing your website...", 0.05)
        website_data = await self.firecrawl.deep_crawl(
            domain,
            max_pages=50,
            extract=['text', 'images', 'meta', 'structured_data', 'links']
        )
        update_progress("Website structure mapped", 0.15)

        # Stage 2: Extract brand identity (45%)
        update_progress("Extracting brand identity...", 0.20)
        brand_identity = await self.brand_analyzer.analyze(website_data)
        # - Colors (from CSS + images)
        # - Typography
        # - Logo
        # - Voice & tone
        # - Key messaging
        update_progress("Brand identity extracted", 0.35)

        # Stage 3: Extract products/services (55%)
        update_progress("Cataloging products & services...", 0.40)
        offerings = await self.brand_analyzer.extract_offerings(website_data)
        update_progress("Products & services cataloged", 0.50)

        # Stage 4: Competitor research (70%)
        update_progress("Researching competitors...", 0.55)
        competitors = await self.perplexity.research(
            f"Main competitors of {domain} in their industry, "
            f"with brief analysis of each"
        )
        competitor_analyses = await self.competitor_analyzer.analyze_batch(
            competitors[:5]
        )
        update_progress("Competitor analysis complete", 0.65)

        # Stage 5: Market intelligence (85%)
        update_progress("Gathering market intelligence...", 0.70)
        market_research = await self.perplexity.research_batch([
            f"Target audience demographics for {domain}",
            f"Industry trends affecting {domain}'s market",
            f"Recent news and developments about {domain}",
        ])
        update_progress("Market intelligence gathered", 0.80)

        # Stage 6: Social & sentiment (95%)
        update_progress("Analyzing social presence...", 0.85)
        social_data = await self.perplexity.research(
            f"Social media presence and public perception of {domain}"
        )
        update_progress("Social analysis complete", 0.90)

        # Stage 7: Compile knowledge base
        update_progress("Compiling knowledge base...", 0.95)
        knowledge_base = KnowledgeBase(
            organization_id=organization_id,
            brand=BrandData(
                name=brand_identity.name,
                domain=domain,
                tagline=brand_identity.tagline,
                visual_identity=VisualIdentity(
                    primary_color=brand_identity.colors.primary,
                    secondary_colors=brand_identity.colors.secondary,
                    fonts=brand_identity.fonts,
                    logo_url=brand_identity.logo_url,
                    image_style=brand_identity.image_style,
                ),
                voice=VoiceProfile(
                    tone=brand_identity.tone,
                    personality=brand_identity.personality,
                    vocabulary=brand_identity.key_terms,
                    sample_phrases=brand_identity.sample_phrases,
                ),
                values=brand_identity.values,
                mission=brand_identity.mission,
            ),
            market=MarketData(
                competitors=[
                    CompetitorProfile(
                        name=c.name,
                        domain=c.domain,
                        strengths=c.strengths,
                        weaknesses=c.weaknesses,
                        positioning=c.positioning,
                    )
                    for c in competitor_analyses
                ],
                industry_trends=market_research['trends'],
                market_position=market_research.get('position'),
            ),
            audiences=[
                AudienceSegment(
                    name=a['name'],
                    demographics=a['demographics'],
                    psychographics=a['psychographics'],
                    pain_points=a['pain_points'],
                    channels=a['preferred_channels'],
                )
                for a in market_research['audiences']
            ],
            offerings=Offerings(
                products=[
                    Product(
                        name=p['name'],
                        description=p['description'],
                        features=p['features'],
                        pricing=p.get('pricing'),
                    )
                    for p in offerings.get('products', [])
                ],
                services=[
                    Service(
                        name=s['name'],
                        description=s['description'],
                        benefits=s['benefits'],
                    )
                    for s in offerings.get('services', [])
                ],
            ),
            context=ContextData(
                social_presence=social_data,
                recent_news=market_research.get('news', []),
            ),
            research_status='complete',
        )

        # Save to database
        await self.db.save_knowledge_base(knowledge_base)

        update_progress("Knowledge base ready!", 1.0)

        return knowledge_base
```

---

## Phase 2: Core Services

### 2.1 Firecrawl Integration

```python
# /services/onboarding/firecrawl.py

class FirecrawlService:
    """
    Deep website crawling using Firecrawl API.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.firecrawl.dev/v1"

    async def deep_crawl(
        self,
        domain: str,
        max_pages: int = 50,
        extract: List[str] = None
    ) -> WebsiteData:
        """
        Crawl a website deeply, extracting all relevant data.
        """

        # Start crawl job
        crawl_response = await self._request(
            "POST",
            "/crawl",
            json={
                "url": f"https://{domain}",
                "limit": max_pages,
                "scrapeOptions": {
                    "formats": ["markdown", "html"],
                    "includeTags": ["main", "article", "section", "header", "footer"],
                    "excludeTags": ["nav", "script", "style"],
                    "onlyMainContent": False,  # We want everything
                }
            }
        )

        crawl_id = crawl_response["id"]

        # Poll for completion
        while True:
            status = await self._request("GET", f"/crawl/{crawl_id}")
            if status["status"] == "completed":
                break
            elif status["status"] == "failed":
                raise Exception(f"Crawl failed: {status.get('error')}")
            await asyncio.sleep(2)

        # Process results
        pages = status["data"]

        return WebsiteData(
            domain=domain,
            pages=[
                PageData(
                    url=p["metadata"]["url"],
                    title=p["metadata"].get("title"),
                    description=p["metadata"].get("description"),
                    content=p["markdown"],
                    html=p["html"],
                    links=self._extract_links(p["html"]),
                    images=self._extract_images(p["html"], domain),
                    structured_data=self._extract_structured_data(p["html"]),
                )
                for p in pages
            ],
            total_pages=len(pages),
        )

    def _extract_images(self, html: str, domain: str) -> List[ImageData]:
        """Extract all images with their context."""
        # Parse HTML, find images, get alt text, surrounding context
        pass

    def _extract_structured_data(self, html: str) -> dict:
        """Extract JSON-LD, OpenGraph, etc."""
        pass
```

### 2.2 Perplexity Integration

```python
# /services/onboarding/perplexity.py

class PerplexityService:
    """
    Market research and intelligence using Perplexity API.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )

    async def research(self, query: str) -> dict:
        """
        Research a topic and return structured insights.
        """
        response = await self.client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=[
                {
                    "role": "system",
                    "content": """You are a market research analyst.
                    Provide detailed, factual information with specific examples.
                    Structure your response as JSON with clear categories.
                    Always cite sources when possible."""
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
        )

        # Parse and structure the response
        return self._parse_research(response.choices[0].message.content)

    async def research_batch(self, queries: List[str]) -> dict:
        """Run multiple research queries in parallel."""
        tasks = [self.research(q) for q in queries]
        results = await asyncio.gather(*tasks)

        # Merge results
        merged = {}
        for query, result in zip(queries, results):
            key = self._query_to_key(query)
            merged[key] = result

        return merged
```

### 2.3 Brand Analyzer

```python
# /services/onboarding/brand_analyzer.py

class BrandAnalyzer:
    """
    Analyzes website data to extract brand identity.
    """

    def __init__(self, claude: ClaudeService):
        self.claude = claude

    async def analyze(self, website_data: WebsiteData) -> BrandIdentity:
        """
        Extract comprehensive brand identity from website data.
        """

        # Extract colors from CSS and images
        colors = await self._analyze_colors(website_data)

        # Extract typography
        fonts = await self._analyze_typography(website_data)

        # Find and analyze logo
        logo = await self._find_logo(website_data)

        # Analyze voice and tone
        voice = await self._analyze_voice(website_data)

        # Extract key messaging
        messaging = await self._analyze_messaging(website_data)

        # Use Claude to synthesize everything
        synthesis = await self.claude.complete(
            prompt=f"""Analyze this brand based on the extracted data:

            Colors: {colors}
            Typography: {fonts}
            Voice indicators: {voice}
            Key messaging: {messaging}

            Provide a comprehensive brand identity profile including:
            1. Brand personality traits
            2. Tone of voice (formal/casual, technical/simple, etc.)
            3. Core values (inferred)
            4. Target audience (inferred)
            5. Unique positioning

            Return as structured JSON.""",
            response_format="json"
        )

        return BrandIdentity(
            name=website_data.extract_brand_name(),
            colors=colors,
            fonts=fonts,
            logo_url=logo.url if logo else None,
            tone=synthesis['tone'],
            personality=synthesis['personality'],
            values=synthesis['values'],
            key_terms=messaging['key_terms'],
            sample_phrases=messaging['sample_phrases'],
            tagline=messaging.get('tagline'),
            mission=synthesis.get('mission'),
        )

    async def _analyze_colors(self, data: WebsiteData) -> ColorPalette:
        """Extract color palette from CSS and images."""
        # Parse CSS for color values
        # Analyze hero images for dominant colors
        # Cluster and rank by frequency/prominence
        pass

    async def _analyze_voice(self, data: WebsiteData) -> dict:
        """Analyze writing style and tone."""
        # Sample text from key pages
        sample_text = "\n\n".join([
            p.content[:2000] for p in data.pages[:10]
        ])

        analysis = await self.claude.complete(
            prompt=f"""Analyze the writing style and tone of this brand:

            {sample_text}

            Identify:
            1. Formality level (1-10)
            2. Technical complexity (1-10)
            3. Emotional warmth (1-10)
            4. Key vocabulary patterns
            5. Sentence structure tendencies
            6. Brand voice characteristics

            Return as JSON.""",
            response_format="json"
        )

        return analysis
```

---

## Phase 3: API Endpoints

### 3.1 Onboarding API

```python
# /api/onboarding.py

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

@router.post("/start")
async def start_onboarding(
    request: OnboardingRequest,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start the onboarding process for a new organization.
    Returns immediately with a job ID for progress tracking.
    """

    # Create organization if needed
    org = await db.get_or_create_organization(
        domain=request.domain,
        created_by=current_user.id
    )

    # Create knowledge base record (pending)
    kb = await db.create_knowledge_base(
        organization_id=org.id,
        research_status="pending"
    )

    # Start background research
    background_tasks.add_task(
        run_onboarding_pipeline,
        domain=request.domain,
        organization_id=org.id,
        knowledge_base_id=kb.id,
    )

    return {
        "organization_id": org.id,
        "knowledge_base_id": kb.id,
        "status": "started",
        "ws_channel": f"onboarding:{kb.id}"  # WebSocket channel for progress
    }

@router.get("/progress/{knowledge_base_id}")
async def get_onboarding_progress(
    knowledge_base_id: str,
    db: Database = Depends(get_db),
):
    """Get current progress of onboarding."""
    kb = await db.get_knowledge_base(knowledge_base_id)
    return {
        "status": kb.research_status,
        "progress": kb.research_progress,
        "current_stage": kb.research_stage,
    }

@router.get("/result/{knowledge_base_id}")
async def get_onboarding_result(
    knowledge_base_id: str,
    db: Database = Depends(get_db),
):
    """Get completed knowledge base."""
    kb = await db.get_knowledge_base(knowledge_base_id)
    if kb.research_status != "complete":
        raise HTTPException(400, "Research not complete")

    return kb.to_presentation_format()
```

### 3.2 WebSocket for Real-time Progress

```python
# /api/websocket.py

@router.websocket("/ws/onboarding/{knowledge_base_id}")
async def onboarding_progress_ws(
    websocket: WebSocket,
    knowledge_base_id: str,
):
    """
    WebSocket for real-time onboarding progress updates.
    """
    await websocket.accept()

    # Subscribe to progress updates
    async for update in progress_stream(knowledge_base_id):
        await websocket.send_json({
            "type": "progress",
            "stage": update.stage,
            "progress": update.progress,
            "message": update.message,
        })

        if update.progress >= 1.0:
            # Send final result
            kb = await db.get_knowledge_base(knowledge_base_id)
            await websocket.send_json({
                "type": "complete",
                "knowledge_base": kb.to_presentation_format(),
            })
            break

    await websocket.close()
```

---

## Phase 4: Frontend Components

### 4.1 Onboarding Flow

```javascript
// /components/onboarding/OnboardingFlow.js

class OnboardingFlow {
    constructor(container) {
        this.container = container;
        this.state = {
            step: 'input', // input, researching, presentation, complete
            domain: '',
            progress: 0,
            currentStage: '',
            knowledgeBase: null,
        };
    }

    render() {
        switch (this.state.step) {
            case 'input':
                return this.renderDomainInput();
            case 'researching':
                return this.renderResearchProgress();
            case 'presentation':
                return this.renderKnowledgePresentation();
            case 'complete':
                return this.renderComplete();
        }
    }

    renderDomainInput() {
        return `
            <div class="onboarding-input">
                <h1>Let's get to know your brand</h1>
                <p>Enter your website and we'll build a complete profile</p>

                <div class="input-group">
                    <input
                        type="text"
                        placeholder="yourbrand.com"
                        value="${this.state.domain}"
                        onchange="this.setDomain(event.target.value)"
                    />
                    <button onclick="this.startOnboarding()">
                        Start Discovery
                    </button>
                </div>

                <p class="hint">
                    We'll analyze your website, research your market,
                    and build a comprehensive knowledge base.
                </p>
            </div>
        `;
    }

    renderResearchProgress() {
        return `
            <div class="research-progress">
                <div class="progress-animation">
                    <!-- Animated brand analysis visualization -->
                </div>

                <h2>Analyzing your brand...</h2>

                <div class="progress-bar">
                    <div class="fill" style="width: ${this.state.progress * 100}%"></div>
                </div>

                <p class="current-stage">${this.state.currentStage}</p>

                <ul class="stage-list">
                    ${this.renderStageList()}
                </ul>
            </div>
        `;
    }

    renderKnowledgePresentation() {
        const kb = this.state.knowledgeBase;
        return `
            <div class="knowledge-presentation">
                <h1>Here's what we learned about ${kb.brand.name}</h1>

                <div class="knowledge-sections">
                    <!-- Brand Identity Card -->
                    <section class="brand-identity">
                        <h2>Brand Identity</h2>
                        ${this.renderBrandCard(kb.brand)}
                    </section>

                    <!-- Competitors -->
                    <section class="competitors">
                        <h2>Competitive Landscape</h2>
                        ${this.renderCompetitors(kb.market.competitors)}
                    </section>

                    <!-- Audiences -->
                    <section class="audiences">
                        <h2>Target Audiences</h2>
                        ${this.renderAudiences(kb.audiences)}
                    </section>

                    <!-- Products/Services -->
                    <section class="offerings">
                        <h2>Products & Services</h2>
                        ${this.renderOfferings(kb.offerings)}
                    </section>
                </div>

                <div class="actions">
                    <button class="secondary" onclick="this.editKnowledge()">
                        Make Edits
                    </button>
                    <button class="primary" onclick="this.confirmKnowledge()">
                        Looks Good - Let's Start
                    </button>
                </div>
            </div>
        `;
    }

    async startOnboarding() {
        this.state.step = 'researching';
        this.render();

        // Start the process
        const response = await api.post('/onboarding/start', {
            domain: this.state.domain
        });

        // Connect to WebSocket for progress
        const ws = new WebSocket(
            `ws://localhost:8000/ws/onboarding/${response.knowledge_base_id}`
        );

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'progress') {
                this.state.progress = data.progress;
                this.state.currentStage = data.message;
                this.render();
            } else if (data.type === 'complete') {
                this.state.knowledgeBase = data.knowledge_base;
                this.state.step = 'presentation';
                this.render();
            }
        };
    }
}
```

---

## Immediate Next Steps

1. **Set up new project structure** (`/workflow-v2`)
2. **Install dependencies** (FastAPI, SQLAlchemy, httpx, etc.)
3. **Create database models** (User, Org, KnowledgeBase)
4. **Build Firecrawl service** (with mock for testing)
5. **Build Perplexity service** (with mock for testing)
6. **Create onboarding pipeline** (orchestrator)
7. **Build API endpoints** (start, progress, result)
8. **Create basic frontend** (domain input → progress → presentation)

---

## Environment Variables Needed

```bash
# API Keys
FIRECRAWL_API_KEY=
PERPLEXITY_API_KEY=
ANTHROPIC_API_KEY=

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/marketing_agent

# Auth (future)
JWT_SECRET=
```

