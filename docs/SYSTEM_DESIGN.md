# Marketing Agent Platform - System Design Document

## Executive Summary

This document outlines the architecture for a premium AI-powered marketing agency platform. Unlike generic marketing tools, this system operates like a top-tier agency (Ogilvy, RGA, McKinsey) - deeply understanding each client before any work begins, producing professional-grade deliverables, and maintaining organized, versioned assets throughout the engagement.

---

## 1. Core Philosophy

### The Agency Model
- **Know before you ask**: Deep client intelligence gathered upfront
- **Show, don't tell**: Professional deliverables, not placeholder text
- **Everything is an artifact**: Persistent, versioned, organized assets
- **Client is in control**: Easy to navigate, revise, and approve

### Key Differentiators
1. **Magical Onboarding**: Client provides URL → system builds complete knowledge base
2. **Professional Briefs**: McKinsey-quality documents, not bullet points
3. **Visual First**: Mock-ups and concepts before approval requests
4. **Asset Management**: Campaign-organized, versioned, cross-referenceable

---

## 2. Information Architecture

### 2.1 Data Hierarchy

```
Organization (Client Instance)
├── Knowledge Base
│   ├── Brand DNA
│   │   ├── Visual Identity (colors, fonts, logo analysis)
│   │   ├── Voice & Tone (messaging patterns, vocabulary)
│   │   ├── Values & Mission
│   │   └── Brand Guidelines (if provided)
│   ├── Market Intelligence
│   │   ├── Competitors[] (with deep analysis each)
│   │   ├── Industry Trends
│   │   ├── Target Audiences[]
│   │   └── Market Position
│   ├── Product/Service Catalog
│   │   ├── Products[]
│   │   ├── Services[]
│   │   ├── Pricing (if public)
│   │   └── Key Differentiators
│   └── Historical Context
│       ├── Past Campaigns (scraped/imported)
│       ├── Social Media Presence
│       ├── Press/News
│       └── Reviews/Sentiment
│
├── Campaigns[]
│   ├── Campaign
│   │   ├── Brief (versioned document)
│   │   ├── Strategy
│   │   ├── Creative Territories[]
│   │   ├── Phases[]
│   │   │   └── Phase
│   │   │       ├── Assets[]
│   │   │       ├── Status (draft/review/approved/live)
│   │   │       └── Timeline
│   │   ├── Conversation Thread
│   │   └── Approvals[]
│   │
│   └── Assets[]
│       └── Asset
│           ├── Type (email/social/landing/ad/etc)
│           ├── Versions[]
│           ├── Comments[]
│           ├── Status
│           └── Campaign Reference
│
└── Asset Library (cross-campaign view)
    ├── By Type
    ├── By Campaign
    ├── By Status
    └── By Date
```

### 2.2 Asset Types

| Category | Asset Types |
|----------|-------------|
| **Documents** | Brief, Strategy Deck, Creative Brief, Copy Doc |
| **Email** | Campaign Email, Drip Sequence, Newsletter |
| **Social** | Post (IG/FB/LinkedIn/Twitter), Story, Carousel, Reel Script |
| **Paid Media** | Display Ad, Search Ad, Social Ad, Video Ad Script |
| **Web** | Landing Page, Hero Section, Product Page, Blog Post |
| **Print** | Poster, Flyer, Billboard, Magazine Ad |
| **Video** | Script, Storyboard, Shot List |
| **Brand** | Logo Usage, Color Palette, Typography Guide |

### 2.3 Asset Schema

```python
class Asset:
    id: str
    type: AssetType
    name: str
    campaign_id: str
    phase_id: Optional[str]

    # Versioning
    versions: List[AssetVersion]
    current_version: int

    # Status
    status: Enum[draft, in_review, needs_changes, approved, published]

    # Content (varies by type)
    content: AssetContent  # Type-specific schema

    # Collaboration
    comments: List[Comment]
    approvals: List[Approval]

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str  # 'ai' or user_id

class AssetVersion:
    version_number: int
    content: AssetContent
    change_summary: str
    created_at: datetime
    created_by: str

class Comment:
    id: str
    asset_id: str
    version: int
    content: str
    position: Optional[dict]  # For inline comments (x, y or element reference)
    resolved: bool
    replies: List[Comment]
    created_at: datetime
```

---

## 3. Onboarding System

### 3.1 Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT ONBOARDING                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Entry                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  "Enter your website or brand name"                      │   │
│  │  [________________example.com________________] [Start]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  Step 2: Deep Research (30-60 seconds, animated progress)       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  🔍 Analyzing your brand...                              │   │
│  │  ├── ✓ Website structure mapped                         │   │
│  │  ├── ✓ Visual identity extracted                        │   │
│  │  ├── ● Analyzing competitors...                         │   │
│  │  ├── ○ Gathering market intelligence                    │   │
│  │  └── ○ Building knowledge base                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  Step 3: Knowledge Presentation                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  "Here's what we learned about [Brand]"                  │   │
│  │                                                          │   │
│  │  [Brand Card - Visual Identity]                          │   │
│  │  [Competitors Analysis]                                  │   │
│  │  [Audience Insights]                                     │   │
│  │  [Products/Services]                                     │   │
│  │  [Market Position]                                       │   │
│  │                                                          │   │
│  │  [Edit] [Looks Good - Let's Start]                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  Step 4: Chat Opens                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  "Hey! I've learned a lot about [Brand]. What would     │   │
│  │   you like to work on today?"                            │   │
│  │                                                          │   │
│  │  Quick actions:                                          │   │
│  │  [Launch Campaign] [Create Content] [Brand Refresh]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Research Pipeline

```python
class OnboardingPipeline:
    """
    Orchestrates deep client research during onboarding.
    Uses Firecrawl for web scraping, Perplexity for intelligence.
    """

    async def research_client(self, domain: str) -> KnowledgeBase:
        # Phase 1: Direct Website Analysis
        website_data = await self.firecrawl.deep_crawl(domain, {
            'max_pages': 50,
            'extract': ['text', 'images', 'meta', 'links', 'structured_data']
        })

        # Phase 2: Visual Identity Extraction
        brand_visuals = await self.extract_brand_identity(website_data)
        # - Dominant colors (from images + CSS)
        # - Typography (font analysis)
        # - Logo detection and analysis
        # - Image style patterns

        # Phase 3: Content & Messaging Analysis
        brand_voice = await self.analyze_messaging(website_data)
        # - Tone analysis (formal/casual, technical/simple)
        # - Key phrases and vocabulary
        # - Value propositions
        # - CTAs used

        # Phase 4: Product/Service Extraction
        offerings = await self.extract_offerings(website_data)
        # - Products with descriptions, pricing
        # - Services with details
        # - Key differentiators

        # Phase 5: Competitor Intelligence (Perplexity)
        competitors = await self.perplexity.research(
            f"Main competitors of {domain} in their industry"
        )
        competitor_analysis = []
        for comp in competitors[:5]:
            analysis = await self.analyze_competitor(comp)
            competitor_analysis.append(analysis)

        # Phase 6: Market Intelligence (Perplexity)
        market_data = await self.perplexity.research_batch([
            f"Target audience and customer demographics for {domain}",
            f"Industry trends affecting {domain}",
            f"Recent news and press about {domain}",
            f"Social media presence and sentiment for {domain}",
        ])

        # Phase 7: Compile Knowledge Base
        return KnowledgeBase(
            brand=BrandDNA(
                name=extracted_name,
                domain=domain,
                visual_identity=brand_visuals,
                voice=brand_voice,
                values=extracted_values,
            ),
            market=MarketIntelligence(
                competitors=competitor_analysis,
                industry_trends=market_data['trends'],
                target_audiences=market_data['audiences'],
            ),
            offerings=offerings,
            context=HistoricalContext(
                social_presence=market_data['social'],
                press=market_data['news'],
            )
        )
```

### 3.3 Knowledge Base Storage

```python
# Each client gets their own knowledge base instance
# Stored in a vector database for semantic retrieval + structured DB for relationships

class KnowledgeBaseStore:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.vector_store = ChromaDB(collection=f"kb_{client_id}")
        self.structured_store = PostgreSQL(schema=f"client_{client_id}")

    async def store(self, knowledge_base: KnowledgeBase):
        # Store structured data
        await self.structured_store.upsert('brand', knowledge_base.brand)
        await self.structured_store.upsert('market', knowledge_base.market)
        await self.structured_store.upsert('offerings', knowledge_base.offerings)

        # Create embeddings for semantic search
        documents = knowledge_base.to_documents()
        await self.vector_store.add(documents)

    async def query(self, question: str) -> List[Document]:
        """Semantic search across knowledge base"""
        return await self.vector_store.similarity_search(question, k=10)

    async def get_context_for_campaign(self, campaign_type: str) -> dict:
        """Get relevant context for a specific campaign type"""
        # Returns brand voice, relevant competitors, audience insights, etc.
        pass
```

---

## 4. Campaign & Asset Management

### 4.1 Campaign Creation Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                    CAMPAIGN CREATION                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User: "I want to launch our new AI feature next month"            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ System (with full context):                                  │   │
│  │                                                              │   │
│  │ "Perfect! Based on what I know about [Brand]:                │   │
│  │  • Your audience of [specific demographic] responds well     │   │
│  │    to [specific messaging style]                             │   │
│  │  • Your competitor [X] recently launched similar - here's    │   │
│  │    how we can differentiate                                  │   │
│  │  • Your brand voice is [tone] - I'll match that              │   │
│  │                                                              │   │
│  │  I'm putting together a full campaign brief. Give me a       │   │
│  │  moment..."                                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                            │                                        │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [Generating Brief...]                                        │   │
│  │  • Creating strategic framework                              │   │
│  │  • Developing creative territories                           │   │
│  │  • Mapping campaign phases                                   │   │
│  │  • Defining deliverables                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                            │                                        │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ CAMPAIGN BRIEF PRESENTATION                                  │   │
│  │                                                              │   │
│  │ ┌──────────────────────────────────────────────────────┐    │   │
│  │ │ [Beautiful PDF/Deck Preview]                          │    │   │
│  │ │                                                        │    │   │
│  │ │  Campaign: AI Feature Launch                          │    │   │
│  │ │  Client: [Brand]                                      │    │   │
│  │ │                                                        │    │   │
│  │ │  Sections:                                            │    │   │
│  │ │  1. Executive Summary                                 │    │   │
│  │ │  2. Strategic Context                                 │    │   │
│  │ │  3. Target Audience Deep-Dive                         │    │   │
│  │ │  4. Competitive Landscape                             │    │   │
│  │ │  5. Creative Territories (3 options)                  │    │   │
│  │ │  6. Campaign Phases & Timeline                        │    │   │
│  │ │  7. Deliverables & Assets                             │    │   │
│  │ │  8. Success Metrics                                   │    │   │
│  │ │                                                        │    │   │
│  │ │  [Download PDF] [View Full Screen]                    │    │   │
│  │ └──────────────────────────────────────────────────────┘    │   │
│  │                                                              │   │
│  │ SUMMARY:                                                     │   │
│  │ "Here's your campaign brief. Key highlights:                 │   │
│  │  • 3-phase approach over 4 weeks                             │   │
│  │  • Primary channels: LinkedIn, Twitter, Email                │   │
│  │  • 3 creative territories to choose from                     │   │
│  │  • 12 total deliverables                                     │   │
│  │                                                              │   │
│  │  Want me to walk you through it, or ready to pick a          │   │
│  │  creative direction?"                                        │   │
│  │                                                              │   │
│  │ [Walk Me Through] [Show Creative Territories] [Make Changes] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### 4.2 Asset Generation & Review

```
┌────────────────────────────────────────────────────────────────────┐
│                    ASSET WORKSPACE                                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┬───────────────────────────────────────────────┐   │
│  │             │                                                │   │
│  │  CAMPAIGN   │           ASSET PREVIEW                        │   │
│  │  ASSETS     │                                                │   │
│  │             │   ┌────────────────────────────────────────┐   │   │
│  │  Phase 1    │   │                                        │   │   │
│  │  ├─ Email 1 │   │     [Visual Preview of Asset]          │   │   │
│  │  ├─ Email 2 │   │                                        │   │   │
│  │  ├─ Social  │   │     - Email with actual design         │   │   │
│  │  │  ├─ IG   │   │     - Social post with imagery         │   │   │
│  │  │  ├─ TW   │   │     - Landing page rendered            │   │   │
│  │  │  └─ LI   │   │     - Ad creative with copy            │   │   │
│  │  └─ Ads     │   │                                        │   │   │
│  │             │   └────────────────────────────────────────┘   │   │
│  │  Phase 2    │                                                │   │
│  │  ├─ ...     │   Version: v2 ← [v1] [v2] [v3]                │   │
│  │             │                                                │   │
│  │  Phase 3    │   Status: [In Review ▼]                        │   │
│  │  ├─ ...     │                                                │   │
│  │             │   ┌────────────────────────────────────────┐   │   │
│  │             │   │ COMMENTS                                │   │   │
│  │  ───────    │   │                                        │   │   │
│  │             │   │ 💬 "Can we try a different headline?"  │   │   │
│  │  [+] New    │   │    ↳ AI: "Sure, here are 3 options..." │   │   │
│  │      Asset  │   │                                        │   │   │
│  │             │   │ [Add Comment]                          │   │   │
│  │             │   └────────────────────────────────────────┘   │   │
│  │             │                                                │   │
│  │             │   [✓ Approve] [✎ Request Changes] [🗑 Delete]  │   │
│  │             │                                                │   │
│  └─────────────┴───────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ CHAT                                                         │   │
│  │                                                              │   │
│  │ You: "The headline on Email 1 isn't quite right"             │   │
│  │                                                              │   │
│  │ AI: "I understand. For Email 1, the current headline is      │   │
│  │      'Unlock the Power of AI'. What direction would you      │   │
│  │      prefer? Here are some alternatives:                     │   │
│  │                                                              │   │
│  │      1. 'Your Work, Supercharged' (benefit-focused)          │   │
│  │      2. 'Meet Your New AI Assistant' (introduction-style)    │   │
│  │      3. 'AI That Actually Gets You' (personality-driven)     │   │
│  │                                                              │   │
│  │      Or describe what you're looking for."                   │   │
│  │                                                              │   │
│  │ [1] [2] [3] [Something else...]                              │   │
│  │                                                              │   │
│  │ [Type a message...]                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### 4.3 Version Control & History

```python
class AssetVersionControl:
    """
    Manages asset versions, enabling:
    - Full history tracking
    - Easy rollback
    - Comparison between versions
    - Branching (explore alternatives without losing original)
    """

    async def create_version(
        self,
        asset_id: str,
        content: AssetContent,
        change_summary: str,
        created_by: str
    ) -> AssetVersion:
        """Create a new version of an asset"""
        asset = await self.get_asset(asset_id)
        new_version = AssetVersion(
            version_number=asset.current_version + 1,
            content=content,
            change_summary=change_summary,
            created_at=datetime.now(),
            created_by=created_by,
            parent_version=asset.current_version
        )
        asset.versions.append(new_version)
        asset.current_version = new_version.version_number
        await self.save(asset)
        return new_version

    async def rollback(self, asset_id: str, to_version: int) -> Asset:
        """Restore an asset to a previous version"""
        asset = await self.get_asset(asset_id)
        target = next(v for v in asset.versions if v.version_number == to_version)

        # Create a new version that copies the old content
        await self.create_version(
            asset_id,
            content=target.content,
            change_summary=f"Rolled back to version {to_version}",
            created_by="user"
        )
        return await self.get_asset(asset_id)

    async def compare(self, asset_id: str, v1: int, v2: int) -> Diff:
        """Compare two versions of an asset"""
        asset = await self.get_asset(asset_id)
        version1 = next(v for v in asset.versions if v.version_number == v1)
        version2 = next(v for v in asset.versions if v.version_number == v2)
        return self.diff_content(version1.content, version2.content)

    async def branch(self, asset_id: str, name: str) -> Asset:
        """Create a branch to explore alternatives"""
        original = await self.get_asset(asset_id)
        branch = Asset(
            **original.dict(),
            id=generate_id(),
            name=f"{original.name} ({name})",
            branched_from=asset_id,
            is_branch=True
        )
        await self.save(branch)
        return branch
```

---

## 5. UI Architecture

### 5.1 Layout Options

**Option A: Chat-Driven with Asset Panel**
```
┌─────────┬────────────────────────┬──────────────────┐
│ Nav     │ Chat                   │ Asset Preview    │
│         │                        │                  │
│ • Chat  │ Conversation drives    │ Current asset    │
│ • Assets│ the experience         │ being discussed  │
│ • Brand │                        │                  │
│         │ Assets appear inline   │ Full preview     │
│         │ as cards in chat       │ with actions     │
└─────────┴────────────────────────┴──────────────────┘
```

**Option B: Asset-Centric with Chat Sidebar**
```
┌─────────┬──────────────────────────────┬───────────┐
│ Nav     │ Asset Workspace              │ Chat      │
│         │                              │           │
│ • Dash  │ Campaign → Phase → Asset     │ Context   │
│ • Assets│                              │ aware     │
│ • Brand │ Visual editor/preview        │ chat      │
│         │                              │           │
│         │ Version control, comments    │ Scoped to │
│         │                              │ selection │
└─────────┴──────────────────────────────┴───────────┘
```

**Option C: Dashboard + Drill-down (Recommended)**
```
┌─────────────────────────────────────────────────────┐
│                 CAMPAIGN DASHBOARD                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Phase 1 │ │ Phase 2 │ │ Phase 3 │ │ Phase 4 │   │
│  │ ████░░░ │ │ ░░░░░░░ │ │ ░░░░░░░ │ │ ░░░░░░░ │   │
│  │ 4/6     │ │ 0/8     │ │ 0/4     │ │ 0/2     │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                     │
│  CURRENT FOCUS: Phase 1 - Teaser Campaign          │
│  ┌──────────────────────────────────────────────┐  │
│  │ [Email 1] [Email 2] [IG Post] [TW Post] [Ad] │  │
│  │    ✓        ✓         ●         ○         ○  │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  CHAT: "Ready to review the Instagram post?"        │
│  [Yes, show me] [Skip to ads] [Overview first]     │
└─────────────────────────────────────────────────────┘
                         │
                         ▼ (drill down)
┌─────────────────────────────────────────────────────┐
│              ASSET VIEW: Instagram Post             │
│  ┌────────────────────────┬────────────────────┐   │
│  │                        │ Chat               │   │
│  │   [Visual Preview]     │                    │   │
│  │                        │ Scoped to this     │   │
│  │   Caption: "..."       │ asset              │   │
│  │   Hashtags: ...        │                    │   │
│  │                        │ "What would you    │   │
│  │   [v1] [v2] [v3]       │  like to change?"  │   │
│  │                        │                    │   │
│  │   [Approve] [Edit]     │ [________________] │   │
│  └────────────────────────┴────────────────────┘   │
│  [← Back to Dashboard]                              │
└─────────────────────────────────────────────────────┘
```

### 5.2 Navigation Structure

```
Primary Navigation (Left Sidebar):
├── 💬 Chat (Global conversation + campaign creation)
├── 📊 Dashboard (Active campaigns overview)
├── 📁 Assets (Library view - all assets)
├── 🎨 Brand (Knowledge base - editable)
├── 📈 Analytics (Performance tracking)
└── ⚙️ Settings

Secondary Navigation (Context-dependent):
Campaign View:
├── Overview (Brief, status, timeline)
├── Phases (Phase-by-phase breakdown)
├── Assets (All assets for campaign)
├── Approvals (Pending approvals)
└── History (Activity log)
```

---

## 6. Technical Architecture

### 6.1 Backend Services

```
┌─────────────────────────────────────────────────────────────┐
│                      API GATEWAY                             │
│                    (FastAPI / Node)                          │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  ONBOARDING   │    │   CAMPAIGN    │    │    ASSET      │
│   SERVICE     │    │   SERVICE     │    │   SERVICE     │
│               │    │               │    │               │
│ • Firecrawl   │    │ • Brief Gen   │    │ • CRUD        │
│ • Perplexity  │    │ • Strategy    │    │ • Versioning  │
│ • Analysis    │    │ • Planning    │    │ • Generation  │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI ORCHESTRATION                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Claude    │  │  DALL-E /   │  │   Custom    │         │
│  │   (Text)    │  │  Midjourney │  │   Models    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  PostgreSQL │  │  ChromaDB   │  │    S3       │         │
│  │  (Struct)   │  │  (Vectors)  │  │  (Files)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Key APIs

```python
# Onboarding
POST /onboard
  body: { domain: str }
  response: { knowledge_base: KnowledgeBase, client_id: str }

GET /knowledge-base/{client_id}
PUT /knowledge-base/{client_id}

# Campaigns
POST /campaigns
  body: { prompt: str }  # Natural language request
  response: { campaign: Campaign, brief: Brief }

GET /campaigns
GET /campaigns/{id}
PUT /campaigns/{id}

POST /campaigns/{id}/brief/regenerate
GET /campaigns/{id}/brief/download  # PDF

# Assets
POST /campaigns/{id}/assets
  body: { type: AssetType, prompt: str }
  response: { asset: Asset }

GET /assets?campaign_id=X&type=Y&status=Z
GET /assets/{id}
PUT /assets/{id}

POST /assets/{id}/versions
  body: { content: AssetContent, change_summary: str }

POST /assets/{id}/rollback
  body: { to_version: int }

POST /assets/{id}/comments
GET /assets/{id}/comments

POST /assets/{id}/approve
POST /assets/{id}/request-changes
  body: { feedback: str }

# Chat (Contextual)
POST /chat
  body: {
    message: str,
    context: {
      campaign_id?: str,
      asset_id?: str,
      scope: 'global' | 'campaign' | 'asset'
    }
  }
```

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Knowledge Base schema and storage
- [ ] Onboarding pipeline (Firecrawl + Perplexity integration)
- [ ] Basic asset CRUD with versioning
- [ ] Database setup (PostgreSQL + ChromaDB)

### Phase 2: Core Experience (Week 3-4)
- [ ] Campaign creation flow
- [ ] Brief generation (professional template)
- [ ] Asset generation by type
- [ ] Chat with context awareness

### Phase 3: UI/UX (Week 5-6)
- [ ] Dashboard view
- [ ] Asset workspace
- [ ] Approval flow
- [ ] Comment system

### Phase 4: Polish (Week 7-8)
- [ ] Version comparison
- [ ] Asset library views
- [ ] Export capabilities
- [ ] Performance optimization

---

## 8. Open Questions

1. **Multi-user**: Will there be teams? Roles? Permissions?
2. **Integrations**: Connect to Figma, Slack, project management tools?
3. **White-label**: Will this be resold to agencies?
4. **Pricing model**: Per-campaign? Per-asset? Subscription?
5. **AI costs**: How to manage token/generation costs at scale?

---

## 9. Success Metrics

- **Onboarding completion rate**: >90%
- **Time to first campaign**: <5 minutes
- **Asset approval rate**: >70% on first version
- **Client retention**: >80% month-over-month
- **NPS**: >50

