# Technical Architecture: Next Generation

## Current State (What We Have)

```
URL Input → Linear Pipeline → File Outputs

researcher → brand_strategist → concept_developer →
strategist → creative_director → [writer, designer, video, webdev, social]
```

**Problems:**
- No persistent brand knowledge
- No product integration
- Fixed deliverable set
- No approval gates
- No conversation
- No variations per persona/channel

---

## Target State (What We Need)

### 1. Brand Intelligence Layer

```python
# New: brands/ module

class BrandProfile:
    """Persistent brand knowledge - stored, not researched each time"""

    # Core Identity
    name: str
    industry: str
    positioning: str  # Who they are, who they're not

    # Visual DNA
    logos: List[str]  # URLs to logo variants
    colors: ColorPalette  # Primary, secondary, accent with semantic roles
    typography: Typography  # Heading/body fonts with weights
    photography_style: str  # Described style + reference images
    visual_references: List[str]  # Actual brand campaign images

    # Verbal DNA
    tone_of_voice: str
    vocabulary: List[str]  # Words they use
    avoid_words: List[str]  # Words they don't use
    taglines: List[str]
    manifesto: str

    # Audience
    personas: List[Persona]
    icp: ICP  # For B2B

    # Products/Services
    products: List[Product]

    # History
    past_campaigns: List[Campaign]  # What they've done
    guidelines: str  # Dos and don'ts

    # Storage
    @classmethod
    async def load(cls, brand_id: str) -> "BrandProfile":
        """Load from persistent storage"""

    async def save(self):
        """Save to persistent storage"""

    async def update_from_url(self, url: str):
        """Update profile from new website crawl"""
```

### 2. Product Intelligence

```python
class Product:
    """Deep product understanding for launch campaigns"""

    name: str
    sku: str
    category: str

    # Details
    features: List[Feature]
    benefits: List[str]
    specs: dict
    pricing: Pricing
    availability: Availability

    # Visual
    product_images: List[str]  # For compositing
    lifestyle_images: List[str]  # In-context shots

    # Positioning
    unique_selling_points: List[str]
    target_audience: str  # May differ from brand-wide
    competitors: List[str]

    # Content
    description: str
    key_messages: List[str]
```

### 3. Campaign Intelligence

```python
class CampaignType(Enum):
    PRODUCT_LAUNCH = "product_launch"
    BRAND_AWARENESS = "brand_awareness"
    LEAD_GENERATION = "lead_generation"
    SEASONAL_PROMO = "seasonal_promo"
    EVENT = "event"
    RETENTION = "retention"

class CampaignRequirements:
    """What each campaign type needs"""

    @staticmethod
    def get_requirements(campaign_type: CampaignType) -> dict:
        """Return required deliverables, channels, timeline structure"""

        if campaign_type == CampaignType.PRODUCT_LAUNCH:
            return {
                "required_inputs": ["product"],
                "recommended_channels": ["social", "email", "landing_page", "paid"],
                "deliverable_types": [
                    "hero_creative",
                    "product_landing_page",
                    "email_announcement",
                    "email_sequence",
                    "social_teaser",
                    "social_launch",
                    "social_sustain",
                    "paid_awareness",
                    "paid_retargeting",
                ],
                "timeline_structure": ["teaser", "launch", "sustain"],
            }
```

### 4. Channel Intelligence

```python
class ChannelSpec:
    """What each channel requires"""

    name: str
    formats: List[Format]

    # Per format
    dimensions: dict  # {format: (width, height)}
    duration_limits: dict  # {format: (min, max) seconds}
    copy_limits: dict  # {field: char_limit}

    # Best practices
    best_practices: List[str]
    avoid: List[str]

    # Creative requirements
    needs_video: bool
    needs_image: bool
    text_overlay_ok: bool
    native_style: str  # "polished", "ugc", "professional"

CHANNELS = {
    "tiktok": ChannelSpec(
        name="TikTok",
        formats=["video", "carousel"],
        dimensions={"video": (1080, 1920)},
        duration_limits={"video": (15, 60)},
        copy_limits={"caption": 2200},
        best_practices=["Hook in first second", "Native look", "Trending audio"],
        needs_video=True,
        needs_image=False,
        text_overlay_ok=True,
        native_style="ugc",
    ),
    "instagram": ChannelSpec(
        name="Instagram",
        formats=["post", "carousel", "story", "reel"],
        dimensions={
            "post": (1080, 1080),
            "carousel": (1080, 1080),
            "story": (1080, 1920),
            "reel": (1080, 1920),
        },
        # ...
    ),
    # ...
}
```

### 5. Intelligent Campaign Planner

```python
class CampaignPlanner:
    """Determines what a campaign needs based on brief"""

    async def plan(
        self,
        brief: str,
        brand: BrandProfile,
        product: Optional[Product] = None,
    ) -> CampaignPlan:
        """
        Analyzes brief and determines:
        - Campaign type
        - Target audience (persona selection)
        - Recommended channels
        - Required deliverables per channel
        - Timeline structure
        - Success metrics
        """

        # Use LLM to understand brief
        analysis = await self._analyze_brief(brief, brand)

        # Get campaign type requirements
        requirements = CampaignRequirements.get_requirements(analysis.campaign_type)

        # Determine channels based on audience + objective
        channels = await self._select_channels(analysis, brand)

        # Build deliverable list per channel
        deliverables = []
        for channel in channels:
            channel_spec = CHANNELS[channel]
            channel_deliverables = await self._plan_channel_deliverables(
                channel_spec, analysis, brand, product
            )
            deliverables.extend(channel_deliverables)

        # Add personas/variations if multiple audiences
        if len(analysis.target_personas) > 1:
            deliverables = await self._add_persona_variations(deliverables, analysis)

        return CampaignPlan(
            campaign_type=analysis.campaign_type,
            objective=analysis.objective,
            personas=analysis.target_personas,
            channels=channels,
            deliverables=deliverables,
            timeline=self._build_timeline(requirements, analysis),
            success_metrics=self._define_metrics(analysis),
        )
```

### 6. Approval Gate System

```python
class ApprovalGate:
    """Pause points requiring user decision"""

    gate_type: str  # "strategy", "territory", "concept", "creative", "final"
    title: str
    description: str
    options: List[ApprovalOption]
    required: bool

class ApprovalOption:
    id: str
    title: str
    description: str
    preview: Optional[str]  # Image/content preview

class WorkflowState:
    """Tracks where we are in the workflow"""

    current_gate: Optional[ApprovalGate]
    approvals: List[Approval]  # History of decisions

    async def present_gate(self, gate: ApprovalGate) -> ApprovalOption:
        """Present options to user and wait for decision"""
        # This pauses the workflow until user responds

    async def record_approval(self, gate: ApprovalGate, option: ApprovalOption):
        """Record the decision and continue workflow"""
```

### 7. Conversational Interface

```python
class ConversationAgent:
    """Handles brief intake through dialogue"""

    async def intake(self, initial_message: str, brand: BrandProfile) -> Brief:
        """
        Conversational brief development:
        1. Understand what they want
        2. Ask clarifying questions
        3. Confirm understanding
        4. Return structured brief
        """

        # Initial understanding
        understanding = await self._initial_parse(initial_message, brand)

        # Identify gaps
        gaps = self._identify_gaps(understanding)

        # Ask questions (if needed)
        while gaps:
            questions = self._formulate_questions(gaps)
            answers = await self._ask_user(questions)
            understanding = await self._update_understanding(understanding, answers)
            gaps = self._identify_gaps(understanding)

        # Confirm
        confirmed = await self._confirm_with_user(understanding)

        return self._to_brief(confirmed)
```

### 8. Visual Generation with Brand DNA

```python
class BrandAuthenticGenerator:
    """Generate visuals that look like the brand, not generic AI"""

    async def generate_image(
        self,
        brief: dict,
        brand: BrandProfile,
        product: Optional[Product] = None,
        reference_images: List[str] = None,
    ) -> str:
        """
        Generate image that:
        1. Matches brand visual DNA
        2. Integrates product if provided
        3. Uses reference images for style
        4. Applies brand colors/aesthetic
        """

        # Get brand reference images
        if not reference_images:
            reference_images = brand.visual_references[:3]

        # Build prompt with brand DNA
        prompt = await self._build_brand_prompt(brief, brand)

        # Generate with style transfer / IP-Adapter
        if reference_images:
            image = await self._generate_with_reference(prompt, reference_images)
        else:
            image = await self._generate_base(prompt)

        # Composite product if provided
        if product and product.product_images:
            image = await self._composite_product(image, product)

        # Apply brand color grading
        image = await self._apply_brand_treatment(image, brand)

        return image
```

### 9. New Agent Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     BRAND INTELLIGENCE LAYER                     │
│  (Persistent storage of brand DNA, products, past campaigns)     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONVERSATIONAL INTAKE                         │
│  (Understand brief, ask questions, confirm understanding)        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAMPAIGN PLANNER                              │
│  (Determine type, channels, deliverables, timeline)              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DISCOVERY AGENT                               │
│  (Research product, audience, competitors, trends)               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STRATEGY AGENT                                │
│  (Develop strategic foundation, identify tension/opportunity)    │
└─────────────────────────────────────────────────────────────────┘
                                │
                         ══════════════
                         APPROVAL GATE 1
                         "Strategy Alignment"
                         ══════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TERRITORY AGENT                               │
│  (Develop 3 creative territories with mood boards)               │
└─────────────────────────────────────────────────────────────────┘
                                │
                         ══════════════
                         APPROVAL GATE 2
                         "Territory Selection"
                         ══════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONCEPT AGENT                                 │
│  (Develop full concept from selected territory)                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                         ══════════════
                         APPROVAL GATE 3
                         "Concept Approval"
                         ══════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BRIEFING AGENT                                │
│  (Create detailed briefs per deliverable)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 EXECUTION AGENTS (Parallel)                      │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Copy    │ │  Visual  │ │  Video   │ │   Web    │           │
│  │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  - Brand-authentic output                                        │
│  - Product integration                                           │
│  - Persona variations                                            │
│  - Channel-specific formats                                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                         ══════════════
                         APPROVAL GATE 4
                         "Creative Review"
                         ══════════════
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION AGENT                            │
│  (Package everything into client-ready format)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                         ══════════════
                         APPROVAL GATE 5
                         "Final Sign-off"
                         ══════════════
```

---

## Database Schema (New)

```sql
-- Brands (persistent)
CREATE TABLE brands (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT,
    positioning TEXT,
    visual_dna JSONB,      -- colors, fonts, photography_style, references
    verbal_dna JSONB,      -- tone, vocabulary, taglines
    guidelines TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Products (per brand)
CREATE TABLE products (
    id TEXT PRIMARY KEY,
    brand_id TEXT REFERENCES brands(id),
    name TEXT NOT NULL,
    category TEXT,
    features JSONB,
    benefits JSONB,
    specs JSONB,
    images JSONB,          -- product shots for compositing
    key_messages JSONB,
    created_at TIMESTAMP
);

-- Personas (per brand)
CREATE TABLE personas (
    id TEXT PRIMARY KEY,
    brand_id TEXT REFERENCES brands(id),
    name TEXT NOT NULL,
    demographics JSONB,
    psychographics JSONB,
    pain_points JSONB,
    goals JSONB,
    channels JSONB,        -- where they hang out
    created_at TIMESTAMP
);

-- Campaigns
CREATE TABLE campaigns (
    id TEXT PRIMARY KEY,
    brand_id TEXT REFERENCES brands(id),
    product_id TEXT REFERENCES products(id),
    name TEXT,
    brief TEXT,
    campaign_type TEXT,
    status TEXT,           -- intake, discovery, strategy, creative, review, complete
    plan JSONB,            -- channels, deliverables, timeline
    approvals JSONB,       -- history of approval decisions
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Deliverables (per campaign)
CREATE TABLE deliverables (
    id TEXT PRIMARY KEY,
    campaign_id TEXT REFERENCES campaigns(id),
    channel TEXT,
    format TEXT,
    persona_id TEXT REFERENCES personas(id),
    brief JSONB,
    content JSONB,         -- copy, headlines, etc.
    assets JSONB,          -- file paths
    status TEXT,           -- pending, draft, review, approved
    feedback JSONB,
    created_at TIMESTAMP
);

-- Conversations (per campaign)
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    campaign_id TEXT REFERENCES campaigns(id),
    messages JSONB,        -- [{role, content, timestamp}]
    created_at TIMESTAMP
);
```

---

## UI Components Needed

1. **Brand Dashboard**
   - List of saved brands
   - Brand profile editor
   - Product catalog
   - Persona library

2. **Campaign Creation**
   - Conversational interface
   - Brief summary
   - Plan preview

3. **Workflow View**
   - Visual pipeline with stages
   - Current stage highlighted
   - Approval gate modals

4. **Creative Review**
   - Side-by-side deliverable view
   - Comment/annotation tools
   - Approve/reject/request changes

5. **Presentation Mode**
   - Full-screen beautiful view
   - Shareable links
   - Export to PDF/PPTX

6. **Asset Library**
   - All deliverables organized
   - Filter by channel/format/status
   - Download/share
