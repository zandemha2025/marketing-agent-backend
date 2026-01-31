# Marketing Agent Platform - Complete Fix Handoff Document

**Version:** 1.0.0  
**Date:** January 31, 2026  
**Purpose:** Comprehensive handoff document for another agent to continue platform fixes

---

## Executive Summary

The Marketing Agent Platform is an autonomous AI-powered creative agency that replicates the end-to-end workflow of world-class agencies like Ogilvy and R/GA. This document provides everything needed to continue fixing the platform to achieve 100% functionality.

### Current Status
- **Brand Onboarding:** ✅ 90% Complete (Workstream 1 DONE)
- **Campaign Execution:** 🔴 17% (Workstream 2 - NEEDS FIX)
- **AI Chat:** 🔴 0% (Workstream 3 - NEEDS FIX)
- **Kata Lab:** 🟡 Partial (Workstream 4 - NEEDS FIX)
- **Asset Generation:** 🔴 0% (Workstream 5 - NEEDS FIX)
- **Landing Pages:** 🔴 0% (Workstream 6 - NOT STARTED)
- **Email Marketing:** 🔴 0% (Workstream 7 - NOT STARTED)

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Workstream Details](#2-workstream-details)
3. [Technical Architecture](#3-technical-architecture)
4. [Environment Setup](#4-environment-setup)
5. [Testing Instructions](#5-testing-instructions)
6. [File Reference](#6-file-reference)
7. [API Reference](#7-api-reference)
8. [Acceptance Criteria](#8-acceptance-criteria)

---

## 1. Platform Overview

### What This Platform Does
The Marketing Agent Platform is a **full marketing agency** powered by AI. It should:

1. **Onboard brands** - Crawl websites, research markets, build knowledge base
2. **Execute campaigns** - AI agents create copy, images, strategy documents
3. **Generate assets** - Images, videos, landing pages, emails
4. **Provide AI chat** - Brand-aware conversational interface
5. **Manage content** - Calendar, scheduling, publishing

### Multi-Agent Architecture
The platform uses 8 specialized AI agents:

| Agent | Role | Capabilities |
|-------|------|--------------|
| Orchestrator | Account Director | Intent classification, workflow routing |
| Strategist | Research & Insights | Market research, competitive analysis |
| Creative Director | Concept Development | Big ideas, creative concepts (3 directions) |
| Copywriter | Text Content | Headlines, body copy, scripts, social posts |
| Art Director | Visual Direction | Layout specs, color palettes, typography |
| Producer | Production Mgmt | Asset creation, quality assurance |
| Media Planner | Distribution | Channel recommendations, scheduling |
| Analyst | Measurement | Metrics analysis, optimization |

### Technology Stack
- **Frontend:** React 18, Vite 5, TipTap Editor
- **Backend:** FastAPI 2.0, SQLAlchemy 2.0 (async), Celery + Redis
- **Database:** PostgreSQL (prod) / SQLite (dev)
- **AI Services:** OpenRouter (Claude/GPT-4), Perplexity, Firecrawl, Segmind, ElevenLabs

---

## 2. Workstream Details

### Phase 1: Foundation (Can Run in Parallel)

#### Workstream 1: Brand Onboarding Pipeline ✅ COMPLETED

**Status:** 90% Complete - DONE

**What Was Fixed:**
- Implemented full `FirecrawlService` with website scraping
- Implemented full `PerplexityService` with market research
- Created complete `OnboardingPipeline` orchestration
- Fixed schema to accept `website_url` as alternative to `domain`
- Added proper error handling and retry logic

**Files Modified:**
- `backend/app/services/onboarding/pipeline.py` - Full implementation
- `backend/app/services/onboarding/firecrawl.py` - Website scraping
- `backend/app/services/onboarding/perplexity.py` - Market research
- `backend/app/schemas/onboarding.py` - Added website_url field
- `backend/app/api/onboarding.py` - Fixed domain extraction

**Test Command:**
```bash
cd backend && python test_onboarding_manual.py
```

---

#### Workstream 5: Asset Generation 🔴 NEEDS FIX

**Status:** 0% - 405 Error on generate endpoint

**Current Issue:**
- `POST /api/assets/generate` returns 405 Method Not Allowed
- Image generation service not properly implemented
- Segmind API integration incomplete

**What Needs to Be Fixed:**

1. **Fix the 405 error** in `backend/app/api/assets.py`
   - Add POST endpoint for `/generate`
   - Route should accept: prompt, style, dimensions

2. **Implement image generation** in `backend/app/services/assets/segmind.py`
   - Call Segmind API with prompt
   - Return generated image URL
   - Store in S3/local storage

3. **Connect to storage service** in `backend/app/services/storage.py`
   - Upload generated images
   - Return public URLs

**Files to Modify:**
- `backend/app/api/assets.py` - Add generate endpoint
- `backend/app/services/assets/segmind.py` - Implement API calls
- `backend/app/services/assets/asset_generator.py` - Orchestrate generation
- `backend/app/services/storage.py` - File upload

**Environment Variables Needed:**
```
SEGMIND_API_KEY=your_key_here
AWS_ACCESS_KEY_ID=your_key (or use local storage)
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET_NAME=your_bucket
```

**Acceptance Criteria:**
- `POST /api/assets/generate` returns 200 with image URL
- Generated images are stored and accessible
- Multiple styles supported (realistic, artistic, etc.)

---

### Phase 2: Core Features (Depends on Phase 1)

#### Workstream 2: Campaign Orchestrator 🔴 NEEDS FIX

**Status:** 17% - Campaigns stay "queued" forever

**Current Issue:**
- Campaigns can be created via API ✅
- Campaign status changes to "queued" when executed ✅
- Campaigns NEVER progress past "queued" status ❌
- No deliverables are ever generated ❌
- Celery worker is not processing jobs ❌

**What Needs to Be Fixed:**

1. **Verify Celery Configuration**
   - Check `backend/app/core/celery_app.py`
   - Ensure Redis broker URL is correct
   - Ensure Celery worker can connect

2. **Fix Campaign Execution Endpoint** (`backend/app/api/campaigns.py`)
   - `POST /api/campaigns/{id}/execute` should enqueue Celery task
   - Currently just changes status but doesn't enqueue

3. **Implement Campaign Processing Task** (`backend/app/services/campaigns/orchestrator.py`)
   - Create Celery task that processes campaigns
   - Task should:
     a. Load campaign from database
     b. Call AI agents (copywriter, designer, strategist)
     c. Generate deliverables (copy, images, strategy docs)
     d. Save deliverables to database
     e. Update campaign status to "completed"

4. **Implement AI Agent Calls**
   - Copywriter: Generate ad copy, social posts, headlines
   - Designer: Generate image prompts, creative concepts
   - Strategist: Generate campaign strategy, audience targeting
   - Use OpenRouter API (already configured)

5. **Create Deliverable Records**
   - Save to `deliverables` table
   - Link to campaigns
   - Types: COPY, IMAGE, STRATEGY, SOCIAL_POST, etc.

**Files to Modify:**
- `backend/app/core/celery_app.py` - Celery configuration
- `backend/app/api/campaigns.py` - Execute endpoint
- `backend/app/services/campaigns/orchestrator.py` - Main processing
- `backend/app/services/campaigns/creative_director.py` - Concept generation
- `backend/app/services/campaigns/brief_generator.py` - Brief creation
- `backend/app/models/deliverable.py` - Deliverable model

**Environment Variables Needed:**
```
REDIS_URL=redis://localhost:6379/0
OPENROUTER_API_KEY=your_key_here
```

**How to Start Celery Worker:**
```bash
cd backend && celery -A app.core.celery_app worker --loglevel=info
```

**Acceptance Criteria:**
- Campaign execution triggers Celery task
- Campaign status progresses: queued → in_progress → completed
- Deliverables are generated (at least 5 per campaign):
  - 1 Research Report
  - 3 Creative Concepts
  - 10+ Headlines
  - 5+ Social Posts
  - 1 Strategy Document

---

#### Workstream 4: Kata Lab 🟡 PARTIAL

**Status:** Jobs created but not processed

**Current Issue:**
- Synthetic influencer creation creates job ✅
- Video compositing creates job ✅
- Script builder creates job ✅
- Avatar generation needs SEGMIND_API_KEY ❌
- Video generation not implemented ❌

**What Needs to Be Fixed:**

1. **Synthetic Influencer Generation**
   - File: `backend/app/services/kata/synthetic_influencer.py`
   - Needs: Segmind API for face generation
   - Needs: ElevenLabs for voice cloning

2. **Video Compositing**
   - File: `backend/app/services/kata/video_compositor.py`
   - Needs: FFmpeg integration for video merging
   - Needs: Scene analysis with Grok Vision

3. **Video Generation from Scripts**
   - File: `backend/app/services/kata/video_generator.py`
   - Needs: Text-to-video API (Runway, Pika, etc.)
   - Or: Image sequence + audio composition

**Files to Modify:**
- `backend/app/services/kata/synthetic_influencer.py`
- `backend/app/services/kata/video_compositor.py`
- `backend/app/services/kata/video_generator.py`
- `backend/app/services/kata/grok_scene_analyzer.py`
- `backend/app/api/kata.py`

**Environment Variables Needed:**
```
SEGMIND_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
XAI_API_KEY=your_key (for Grok vision)
REPLICATE_API_TOKEN=your_token (alternative for video)
```

**Acceptance Criteria:**
- Synthetic influencer generates face + voice
- Video compositor merges videos with product placement
- Script builder generates video from script

---

### Phase 3: Advanced Features (Full Marketing Agency)

#### Workstream 6: Landing Page/Website Generation 🔴 NOT STARTED

**Status:** 0% - Not implemented

**What Needs to Be Built:**

1. **Landing Page Generator Service**
   - Generate HTML/CSS from campaign brief
   - Use AI to create copy and layout
   - Support multiple templates (product launch, lead gen, etc.)

2. **Static Site Builder**
   - Generate complete static sites
   - Include: Hero, Features, Testimonials, CTA sections
   - Mobile responsive

3. **Deployment Pipeline**
   - Upload to S3/CDN
   - Generate public URLs
   - Support custom domains (future)

**Files to Create:**
- `backend/app/services/content/landing_page_generator.py`
- `backend/app/services/content/static_site_builder.py`
- `backend/app/api/content.py` - Add landing page endpoints

**API Endpoints to Create:**
```
POST /api/content/landing-page/generate
  - Input: campaign_id, template, sections
  - Output: { url: "https://...", html: "..." }

POST /api/content/website/generate
  - Input: organization_id, pages, style
  - Output: { url: "https://...", pages: [...] }
```

**Acceptance Criteria:**
- Landing page generated from campaign brief
- HTML/CSS is valid and responsive
- Page is deployed and accessible via URL

---

#### Workstream 7: Email Marketing System 🔴 NOT STARTED

**Status:** 0% - Not implemented

**What Needs to Be Built:**

1. **Newsletter Design Generator**
   - Generate HTML email templates
   - Support brand colors and fonts
   - Include: Header, body, CTA, footer

2. **Sequential Email Campaigns**
   - Create email sequences (welcome, nurture, etc.)
   - Schedule sends over time
   - Track opens/clicks (future)

3. **Email Template Engine**
   - Merge templates with dynamic data
   - Support personalization tokens
   - Generate plain text versions

**Files to Create:**
- `backend/app/services/content/email_generator.py`
- `backend/app/services/content/email_sequence.py`
- `backend/app/models/email_campaign.py`
- `backend/app/api/content.py` - Add email endpoints

**API Endpoints to Create:**
```
POST /api/content/email/generate
  - Input: campaign_id, type (newsletter/promotional/transactional)
  - Output: { html: "...", plain_text: "...", subject_lines: [...] }

POST /api/content/email/sequence
  - Input: campaign_id, sequence_type, num_emails
  - Output: { emails: [...], schedule: [...] }
```

**Acceptance Criteria:**
- Email HTML is valid and renders in major clients
- Subject line variations generated
- Sequential campaigns have proper timing

---

### Phase 4: Integration

#### Workstream 3: AI Chat Context 🔴 NEEDS FIX

**Status:** 0% - No brand context in chat

**Current Issue:**
- AI chat works but has no brand context
- Knowledge base not loaded into prompts
- RAG (Retrieval Augmented Generation) not implemented

**What Needs to Be Fixed:**

1. **Load Brand Data into Chat**
   - File: `backend/app/api/chat.py`
   - Query knowledge base for organization
   - Include brand data in system prompt

2. **Implement RAG**
   - Create embeddings for knowledge base content
   - Search relevant context for each query
   - Include in prompt

3. **Context-Aware Responses**
   - Chat should know brand voice
   - Chat should know products/services
   - Chat should know target audiences

**Files to Modify:**
- `backend/app/api/chat.py` - Add knowledge base loading
- `backend/app/services/ai/openrouter.py` - Add context to prompts
- `backend/app/repositories/knowledge_base.py` - Query methods

**Acceptance Criteria:**
- Chat responses reference brand information
- Chat knows company name, products, voice
- Chat can answer questions about the brand

---

### Phase 5: Validation

#### Final Testing

**Run Deep Functional Test:**
```bash
cd backend && python ../deep_functional_test.py
```

**Expected Results After All Fixes:**
- Brand Onboarding: 100%
- Campaign Execution: 100%
- AI Chat: 100%
- Kata Lab: 100%
- Asset Generation: 100%
- Landing Pages: 100%
- Email Marketing: 100%

---

## 3. Technical Architecture

### Directory Structure
```
workflow/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── core/             # Config, database, celery
│   │   ├── models/           # SQLAlchemy models
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   │   ├── ai/           # OpenRouter, LLM services
│   │   │   ├── assets/       # Segmind, ElevenLabs
│   │   │   ├── campaigns/    # Orchestrator, agents
│   │   │   ├── content/      # Landing pages, emails
│   │   │   ├── kata/         # Video, influencers
│   │   │   └── onboarding/   # Firecrawl, Perplexity
│   │   └── intelligence/     # Agent prompts/instructions
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   └── services/         # API client
│   └── package.json
└── plans/                    # Documentation
```

### Database Models (Key Ones)
```
Organization → User (1:many)
Organization → Campaign (1:many)
Organization → KnowledgeBase (1:1)
Campaign → Deliverable (1:many)
Campaign → Asset (1:many)
Conversation → Message (1:many)
```

### API Flow
```
Frontend → FastAPI → Service → Repository → Database
                  ↓
              AI Services (OpenRouter, Segmind, etc.)
                  ↓
              Celery Tasks (background processing)
```

---

## 4. Environment Setup

### Required Environment Variables

Create `backend/.env`:
```bash
# Database
DATABASE_URL=sqlite:///./data.db

# Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256

# AI Services
OPENROUTER_API_KEY=your-openrouter-key
PERPLEXITY_API_KEY=your-perplexity-key
FIRECRAWL_API_KEY=your-firecrawl-key

# Asset Generation
SEGMIND_API_KEY=your-segmind-key
ELEVENLABS_API_KEY=your-elevenlabs-key

# Video/Vision
XAI_API_KEY=your-xai-key
REPLICATE_API_TOKEN=your-replicate-token

# Task Queue
REDIS_URL=redis://localhost:6379/0

# Storage (optional - uses local if not set)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
S3_BUCKET_NAME=your-bucket
```

### Starting the Backend
```bash
# Terminal 1: Start FastAPI
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Celery Worker (for background tasks)
cd backend && celery -A app.core.celery_app worker --loglevel=info

# Terminal 3: Start Redis (if not running)
redis-server
```

### Starting the Frontend
```bash
cd frontend && npm install && npm run dev
```

---

## 5. Testing Instructions

### Manual API Testing

**Test Brand Onboarding:**
```bash
curl -X POST http://localhost:8000/api/onboarding/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"organization_id": "your-org-id", "website_url": "https://nike.com"}'
```

**Test Campaign Creation:**
```bash
curl -X POST http://localhost:8000/api/campaigns \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"name": "Test Campaign", "goal": "Brand Awareness", "organization_id": "your-org-id"}'
```

**Test Campaign Execution:**
```bash
curl -X POST http://localhost:8000/api/campaigns/{campaign_id}/execute \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Automated Testing

**Run Deep Functional Test:**
```bash
python deep_functional_test.py
```

This tests:
1. Brand onboarding quality
2. Campaign execution flow
3. AI chat context
4. Kata Lab features
5. Asset generation

---

## 6. File Reference

### Key Files to Modify

| Workstream | File | Purpose |
|------------|------|---------|
| WS2 | `backend/app/api/campaigns.py` | Campaign execute endpoint |
| WS2 | `backend/app/services/campaigns/orchestrator.py` | Campaign processing |
| WS2 | `backend/app/core/celery_app.py` | Celery configuration |
| WS3 | `backend/app/api/chat.py` | Chat with brand context |
| WS4 | `backend/app/services/kata/synthetic_influencer.py` | AI influencer |
| WS4 | `backend/app/services/kata/video_compositor.py` | Video merging |
| WS5 | `backend/app/api/assets.py` | Asset generation endpoint |
| WS5 | `backend/app/services/assets/segmind.py` | Image generation |
| WS6 | `backend/app/services/content/landing_page_generator.py` | Landing pages |
| WS7 | `backend/app/services/content/email_generator.py` | Email marketing |

### Agent Prompts/Instructions
Located in `backend/app/intelligence/`:
- `departments/copywriter.md` - Copywriter agent instructions
- `departments/designer.md` - Designer agent instructions
- `departments/strategist.md` - Strategist agent instructions
- `departments/creative_director.md` - Creative director instructions

---

## 7. API Reference

### Campaign Endpoints
```
GET    /api/campaigns                    - List campaigns
POST   /api/campaigns                    - Create campaign
GET    /api/campaigns/{id}               - Get campaign
PUT    /api/campaigns/{id}               - Update campaign
DELETE /api/campaigns/{id}               - Delete campaign
POST   /api/campaigns/{id}/execute       - Execute campaign
WS     /api/campaigns/{id}/ws/{session}  - Real-time updates
```

### Asset Endpoints
```
GET    /api/assets                       - List assets
POST   /api/assets                       - Create asset
POST   /api/assets/generate              - Generate image (NEEDS FIX)
GET    /api/assets/{id}                  - Get asset
DELETE /api/assets/{id}                  - Delete asset
```

### Chat Endpoints
```
GET    /api/chat/conversations           - List conversations
POST   /api/chat/conversations           - Create conversation
POST   /api/chat/conversations/{id}/messages - Send message
GET    /api/chat/conversations/{id}/messages?stream=true - SSE stream
```

### Kata Lab Endpoints
```
POST   /api/kata/synthetic-influencer    - Create AI influencer
POST   /api/kata/composite-product       - Composite product into video
POST   /api/kata/merge-videos            - Merge video sources
POST   /api/kata/generate-voice          - Generate voice
POST   /api/kata/generate-script         - Generate video script
```

### Content Endpoints
```
POST   /api/content/landing-page/generate - Generate landing page
POST   /api/content/email/generate        - Generate email
POST   /api/content/press-release         - Generate press release
```

---

## 8. Acceptance Criteria

### Overall Platform Success Criteria

The platform is considered 100% functional when:

1. **Brand Onboarding** (Workstream 1) ✅
   - Website crawling extracts brand information
   - Market research provides competitive insights
   - Knowledge base is populated with structured data
   - Quality score: 90%+

2. **Campaign Execution** (Workstream 2)
   - Campaigns progress through all phases
   - AI agents generate deliverables
   - At least 5 deliverables per campaign
   - Status updates in real-time via WebSocket

3. **AI Chat** (Workstream 3)
   - Chat responses include brand context
   - Chat knows company name, products, voice
   - Responses are relevant and helpful

4. **Kata Lab** (Workstream 4)
   - Synthetic influencer generates face + voice
   - Video compositor merges videos
   - Script builder creates video scripts

5. **Asset Generation** (Workstream 5)
   - Image generation returns valid images
   - Multiple styles supported
   - Images stored and accessible

6. **Landing Pages** (Workstream 6)
   - Landing pages generated from briefs
   - HTML/CSS is valid and responsive
   - Pages deployed and accessible

7. **Email Marketing** (Workstream 7)
   - Email HTML renders correctly
   - Subject line variations generated
   - Sequential campaigns supported

### Quality Metrics

Run `deep_functional_test.py` and verify:
- All workstreams score 80%+ quality
- No 4xx or 5xx errors
- Response times under 30 seconds
- Deliverables contain meaningful content

---

## Appendix: Quick Start for New Agent

### Step 1: Understand the Codebase
1. Read `MARKETING_AGENT_E2E_WORKFLOW.docx` for full platform spec
2. Review this handoff document
3. Check `deep_test_results.json` for current test results

### Step 2: Set Up Environment
1. Copy `.env.example` to `.env` and fill in API keys
2. Start backend: `cd backend && uvicorn app.main:app --reload`
3. Start Celery: `cd backend && celery -A app.core.celery_app worker`

### Step 3: Pick a Workstream
1. Start with Workstream 2 (Campaign Orchestrator) - highest impact
2. Or Workstream 5 (Asset Generation) - simpler fix
3. Follow the detailed instructions in Section 2

### Step 4: Test Your Changes
1. Run manual API tests (Section 5)
2. Run `deep_functional_test.py`
3. Verify quality scores improved

### Step 5: Move to Next Workstream
1. Update this document with progress
2. Pick next workstream based on dependencies
3. Repeat until all workstreams complete

---

**Document End**

*Last Updated: January 31, 2026*
*Author: AI Agent (Orchestrator Mode)*
