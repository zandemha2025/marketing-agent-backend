# V3 Architecture: The Complete AI Marketing Engine

## Vision
The only platform that can **think** like a CMO, **create** like Hollywood, and **place** like a media buyer.

---

## Core Philosophy

### What We're NOT Building
- Another content generation tool (Jasper)
- Another social scheduler (Buffer/Hootsuite)
- Another PR distribution tool (Pressmaster)

### What We ARE Building
**An AI Marketing Agency** that:
1. **Researches** your brand + market deeply (not just a brand interview)
2. **Strategizes** with McKinsey-quality briefs (not content calendars)
3. **Creates** full campaigns: copy + image + VIDEO + AUDIO
4. **Composes** products into content naturally (Halftime tech)
5. **Distributes** with platform-native intelligence
6. **Optimizes** based on real performance data

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         V3 PLATFORM                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ INTELLIGENCE│  │  STRATEGY   │  │  CREATION   │  │ DISTRIBUTION│ │
│  │    LAYER    │  │    LAYER    │  │    LAYER    │  │    LAYER    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │                │         │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐ │
│  │Brand Research│  │Brief Gen    │  │Copy Engine  │  │Social Suite │ │
│  │Market Intel │  │Creative Dir │  │Image Engine │  │Newsroom CMS │ │
│  │Trend Detect │  │Channel Strat│  │Video Engine │  │Email Connect│ │
│  │Competitor   │  │Audience Map │  │Audio Engine │  │Ad Platforms │ │
│  └─────────────┘  └─────────────┘  │             │  └─────────────┘ │
│                                    │ ┌─────────┐ │                   │
│                                    │ │  KATA   │ │                   │
│                                    │ │ ENGINE  │ │                   │
│                                    │ │(compose)│ │                   │
│                                    │ └─────────┘ │                   │
│                                    └─────────────┘                   │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    ORCHESTRATOR (Brain)                        │  │
│  │  Routes tasks → Manages state → Coordinates services           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: INTELLIGENCE (What We Know)

### 1.1 Brand Research Engine (EXISTING - Enhanced)
```
v3/backend/app/services/intelligence/
├── brand_crawler.py        # Firecrawl - deep website analysis
├── market_researcher.py    # Perplexity - competitive intel
├── audience_profiler.py    # Audience segmentation
├── knowledge_base.py       # Unified brand KB
└── brand_voice.py          # Voice/tone extraction
```

### 1.2 Trend Detection (NEW - From Pressmaster)
```
v3/backend/app/services/intelligence/
├── trend_detector.py       # Real-time trend scanning
├── viral_analyzer.py       # What's working on each platform
├── hashtag_tracker.py      # Trending hashtags/sounds
└── news_monitor.py         # Industry news alerts
```
**Key Insight**: Pressmaster scans 500k sources. We use Perplexity + social APIs.

### 1.3 Platform DNA (NEW - From Halftime)
```
v3/backend/app/services/intelligence/
├── platform_analyzer.py    # Analyze what works on each platform
├── format_detector.py      # Trending formats (carousel, reel, thread)
├── timing_predictor.py     # Best times to post
└── competitor_style.py     # Analyze competitor content style
```
**Key Insight**: Halftime finds "insertion zones" in video. We find "content zones" on platforms.

---

## Layer 2: STRATEGY (What We Plan)

### 2.1 Brief Generator (EXISTING - Our Differentiator)
```
v3/backend/app/services/strategy/
├── brief_generator.py      # McKinsey-quality briefs
├── territory_mapper.py     # Creative territories
├── channel_strategist.py   # Platform recommendations
└── audience_mapper.py      # Segment targeting
```

### 2.2 Campaign Planner (NEW - Enhanced)
```
v3/backend/app/services/strategy/
├── calendar_generator.py   # 30-day content calendar
├── sequence_planner.py     # Cross-platform orchestration
├── budget_allocator.py     # Spend recommendations
└── ab_predictor.py         # Predict winning variants
```

---

## Layer 3: CREATION (What We Make)

### 3.1 Copy Engine (EXISTING)
```
v3/backend/app/services/creation/copy/
├── writer.py               # Claude Opus - always premium
├── formats/                # Platform-specific formats
│   ├── social.py          # Social post copy
│   ├── email.py           # Email copy
│   ├── landing.py         # Landing page copy
│   └── ad.py              # Ad copy
├── repurposer.py          # 1 piece → 15 formats (NEW)
└── headline_generator.py   # Hook/headline variants
```

### 3.2 Image Engine (EXISTING)
```
v3/backend/app/services/creation/image/
├── generator.py            # Flux Pro Ultra
├── brand_styler.py         # Apply brand guidelines
├── text_renderer.py        # Text on images
└── formats/                # Platform dimensions
```

### 3.3 Video Engine (EXISTING)
```
v3/backend/app/services/creation/video/
├── generator.py            # Runway Gen4 / Kling
├── animator.py             # Image-to-video
└── editor.py               # Cuts, transitions
```

### 3.4 Audio Engine (EXISTING)
```
v3/backend/app/services/creation/audio/
├── voice_generator.py      # ElevenLabs
├── music_selector.py       # Background music
└── mixer.py                # Audio mixing
```

### 3.5 KATA ENGINE (NEW - Rebuilt)
This is the Halftime magic - contextual compositing:

```
v3/backend/app/services/kata/
├── __init__.py
├── orchestrator.py         # Main pipeline coordinator
│
├── analysis/
│   ├── scene_analyzer.py   # Find placement opportunities
│   ├── depth_estimator.py  # Estimate scene depth
│   ├── shot_detector.py    # Detect shot types
│   ├── object_detector.py  # Find objects in scene
│   └── face_detector.py    # Detect faces (avoid)
│
├── compositing/
│   ├── compositor.py       # Main compositing engine
│   ├── depth_compositor.py # Depth-aware placement
│   ├── shadow_generator.py # Add realistic shadows
│   ├── lighting_matcher.py # Match scene lighting
│   └── blend_modes.py      # Natural blending
│
├── placement/
│   ├── zone_finder.py      # Find valid insertion zones
│   ├── placement_scorer.py # Score placement quality
│   ├── product_analyzer.py # Analyze product for placement
│   └── context_matcher.py  # Match product to context
│
├── synthetic/
│   ├── influencer_gen.py   # Generate synthetic influencer
│   ├── ugc_styler.py       # Make content look like UGC
│   └── avatar_creator.py   # Create brand avatars
│
└── quality/
    ├── realism_scorer.py   # Score how realistic
    ├── brand_safety.py     # Check brand safety
    └── detection_check.py  # AI detection avoidance
```

#### Kata Use Cases:

**Use Case 1: Synthetic Influencers**
```
Input: Brand brief + product images + target platform
Process:
  1. Generate base video (Runway/Kling)
  2. Analyze scene for placement zones
  3. Composite product naturally into scene
  4. Add realistic shadows/lighting
  5. Style as UGC/influencer content
Output: Authentic-looking influencer video with product
```

**Use Case 2: Product Compositing**
```
Input: Existing video + product image + placement preferences
Process:
  1. Analyze video frames for insertion zones
  2. Estimate depth at each zone
  3. Find optimal placement (not on faces, natural context)
  4. Composite product with depth-aware blending
  5. Generate matching shadows
  6. Apply across video frames
Output: Video with seamlessly integrated product
```

**Use Case 3: UGC-Style Ads**
```
Input: Brand assets + campaign brief
Process:
  1. Generate "casual" video content
  2. Place product naturally (on desk, in hand, background)
  3. Add authentic imperfections (slight motion, real lighting)
  4. Style to match organic content on target platform
Output: Ad that looks like organic user content
```

---

## Layer 4: DISTRIBUTION (Where We Place)

### 4.1 Social Publishing Suite (NEW - Critical)
```
v3/backend/app/services/distribution/
├── social_publisher.py     # Unified publishing
├── platforms/
│   ├── linkedin.py         # LinkedIn API
│   ├── twitter.py          # Twitter/X API
│   ├── instagram.py        # Instagram API
│   ├── facebook.py         # Facebook API
│   ├── tiktok.py           # TikTok API
│   └── youtube.py          # YouTube API
├── scheduler.py            # Smart scheduling
├── formatter.py            # Auto-format per platform
└── analytics_collector.py  # Pull performance data
```

### 4.2 Newsroom CMS (NEW - From Pressmaster)
```
v3/backend/app/services/distribution/
├── newsroom/
│   ├── page_builder.py     # Drag-drop page builder
│   ├── templates.py        # Pre-built templates
│   ├── seo_optimizer.py    # SEO optimization
│   └── hosting.py          # Host press pages
```

### 4.3 Email Integration (NEW)
```
v3/backend/app/services/distribution/
├── email/
│   ├── mailchimp.py        # Mailchimp integration
│   ├── klaviyo.py          # Klaviyo integration
│   └── campaign_sync.py    # Sync campaigns
```

### 4.4 Ad Platform Export (NEW)
```
v3/backend/app/services/distribution/
├── ads/
│   ├── meta_export.py      # Meta Ads format
│   ├── google_export.py    # Google Ads format
│   ├── tiktok_export.py    # TikTok Ads format
│   └── spec_validator.py   # Validate ad specs
```

---

## The Orchestrator (Brain)

```
v3/backend/app/services/orchestrator/
├── brain.py                # Main orchestrator
├── workflow_engine.py      # Workflow management
├── state_manager.py        # Campaign state
├── department_router.py    # Route to services
└── quality_gate.py         # Quality checks before output
```

### Campaign Flow:
```
1. USER: "Create a campaign for our new coffee product"
   
2. INTELLIGENCE:
   - Load brand KB (existing)
   - Research market trends
   - Analyze competitor content
   - Detect trending formats

3. STRATEGY:
   - Generate McKinsey brief
   - Map creative territories
   - Plan channel strategy
   - Create content calendar

4. CREATION:
   - Generate copy variants (Claude Opus)
   - Create images (Flux Pro Ultra)
   - Generate videos (Runway)
   - Create voiceovers (ElevenLabs)
   
   KATA LAYER:
   - Analyze generated content for placement zones
   - Composite product naturally
   - Generate synthetic influencer variants
   - Style as UGC for native feel

5. DISTRIBUTION:
   - Format for each platform
   - Schedule at optimal times
   - Publish across channels
   - Track performance

6. OPTIMIZATION:
   - Analyze what's working
   - Generate more of winners
   - Adjust strategy
```

---

## Database Schema (Enhanced)

```sql
-- New tables for v3

-- Kata compositing jobs
CREATE TABLE compositing_jobs (
    id VARCHAR(12) PRIMARY KEY,
    campaign_id VARCHAR(12) REFERENCES campaigns(id),
    source_type VARCHAR(20),  -- 'generated', 'uploaded', 'stock'
    source_url TEXT,
    product_image_url TEXT,
    placement_zones JSONB,
    output_url TEXT,
    quality_score FLOAT,
    status VARCHAR(20),
    created_at TIMESTAMP
);

-- Synthetic influencer profiles
CREATE TABLE synthetic_influencers (
    id VARCHAR(12) PRIMARY KEY,
    organization_id VARCHAR(12) REFERENCES organizations(id),
    name VARCHAR(255),
    persona JSONB,  -- age, style, voice, etc.
    avatar_url TEXT,
    voice_id VARCHAR(50),  -- ElevenLabs voice
    platforms JSONB,  -- which platforms they "post" on
    created_at TIMESTAMP
);

-- Trend tracking
CREATE TABLE trends (
    id VARCHAR(12) PRIMARY KEY,
    platform VARCHAR(50),
    trend_type VARCHAR(50),  -- hashtag, sound, format, topic
    name VARCHAR(255),
    momentum_score FLOAT,
    detected_at TIMESTAMP,
    peak_at TIMESTAMP,
    data JSONB
);

-- Social publishing queue
CREATE TABLE publish_queue (
    id VARCHAR(12) PRIMARY KEY,
    campaign_id VARCHAR(12) REFERENCES campaigns(id),
    asset_id VARCHAR(12) REFERENCES assets(id),
    platform VARCHAR(50),
    scheduled_for TIMESTAMP,
    published_at TIMESTAMP,
    post_url TEXT,
    status VARCHAR(20),
    analytics JSONB
);
```

---

## API Endpoints (New for v3)

```
# Kata Engine
POST   /api/kata/analyze          # Analyze video for placement
POST   /api/kata/composite        # Composite product into video
POST   /api/kata/synthetic        # Generate synthetic influencer content
GET    /api/kata/jobs/{id}        # Get compositing job status

# Social Publishing
POST   /api/publish/schedule      # Schedule content
POST   /api/publish/now           # Publish immediately
GET    /api/publish/queue         # Get publishing queue
DELETE /api/publish/{id}          # Cancel scheduled post

# Trends
GET    /api/trends                # Get current trends
GET    /api/trends/{platform}     # Platform-specific trends
POST   /api/trends/subscribe      # Subscribe to trend alerts

# Synthetic Influencers
POST   /api/influencers           # Create synthetic influencer
GET    /api/influencers           # List influencers
POST   /api/influencers/{id}/generate  # Generate content as influencer
```

---

## Competitive Moat Summary

| Capability | Jasper | Pressmaster | US (V3) |
|------------|--------|-------------|---------|
| Copy Generation | ✅ Core | ✅ | ✅ Claude Opus |
| Strategic Briefs | ❌ | ❌ | ✅ McKinsey-quality |
| Image Generation | Limited | Basic | ✅ Flux Pro Ultra |
| Video Generation | ❌ | ❌ | ✅ Runway/Kling |
| Audio/Voiceover | ❌ | ❌ | ✅ ElevenLabs |
| Product Compositing | ❌ | ❌ | ✅ KATA ENGINE |
| Synthetic Influencers | ❌ | ❌ | ✅ KATA ENGINE |
| UGC-Style Content | ❌ | ❌ | ✅ KATA ENGINE |
| Social Publishing | ❌ | ✅ | ✅ (building) |
| Trend Detection | ❌ | ✅ Trendmaster | ✅ (building) |
| Press Distribution | ❌ | ✅ 400+ outlets | Phase 4 |

**Our Unique Advantages:**
1. Full-stack creation (copy + image + VIDEO + AUDIO)
2. Contextual compositing (Kata - no one else has this)
3. Synthetic influencers (no one else has this)
4. Strategic depth (McKinsey briefs, not templates)
5. Never compromise on AI quality (Opus always)

---

## Build Phases

### Phase 0: Foundation (Week 1-2)
- [ ] Get v2 running in production
- [ ] Add social publishing (LinkedIn, Twitter, Instagram)
- [ ] Add basic plagiarism check API

### Phase 1: Kata Core (Week 3-6)
- [ ] Scene analyzer (find placement zones)
- [ ] Depth estimator
- [ ] Basic compositor
- [ ] Shadow generator
- [ ] Integration with video pipeline

### Phase 2: Distribution (Week 7-10)
- [ ] Complete social publishing suite
- [ ] Newsroom CMS builder
- [ ] Email integrations
- [ ] Ad platform export

### Phase 3: Intelligence (Week 11-14)
- [ ] Trend detection system
- [ ] Platform DNA analyzer
- [ ] A/B prediction
- [ ] Performance analytics

### Phase 4: Advanced Kata (Month 4+)
- [ ] Synthetic influencer generation
- [ ] UGC styling engine
- [ ] Advanced compositing (video inpainting)
- [ ] Multi-shot consistency

---

## Success Metrics

1. **Creation Quality**: Human can't tell AI-generated content
2. **Compositing Realism**: Products look naturally placed (>90% realism score)
3. **Platform Performance**: Content performs 2x organic benchmarks
4. **Time Savings**: Full campaign in hours, not weeks
5. **Customer Retention**: Agencies can't live without us
