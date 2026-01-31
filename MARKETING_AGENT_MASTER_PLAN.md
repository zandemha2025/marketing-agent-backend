# Marketing Agent - Complete Master Plan

## Vision Statement

Create an **autonomous AI marketing platform** that does the work FOR you, not WITH you. The AI handles everything - trend monitoring, campaign creation, content generation, scheduling, optimization - and humans only interject when needed.

**Core Philosophy: AUTONOMOUS BY DEFAULT**

| Traditional Tools | Marketing Agent |
|-------------------|-----------------|
| User fills out forms | AI asks "what do you want?" then does it ALL |
| User triggers each step | AI runs the entire workflow automatically |
| User manually schedules | AI schedules optimally and adjusts |
| User reviews everything | AI presents finished work for approval |
| Human does heavy lifting | AI does heavy lifting, human approves |

**Example Workflows:**

1. **"Launch a campaign for our new feature"**
   - AI analyzes the feature from your knowledge base
   - AI identifies target audiences automatically
   - AI generates full brief, creative concepts, all assets
   - AI schedules across all channels at optimal times
   - Human reviews and approves (or AI auto-publishes if trusted)

2. **"We need more LinkedIn presence"**
   - AI audits current LinkedIn performance
   - AI identifies content gaps and opportunities
   - AI generates 30 days of posts automatically
   - AI schedules them at best engagement times
   - Human reviews weekly batch, approves/tweaks

3. **"Create a blog post about [trending topic]"**
   - AI already spotted the trend (TrendMaster running 24/7)
   - AI generates outline, draft, images, social snippets
   - AI optimizes for SEO automatically
   - Human reviews, makes any tweaks, publishes

**Design Philosophy:** Clean, minimal, enterprise cloud desktop aesthetic. No purple gradients. Professional, dark mode interface with sliding panels, contextual workspaces, and real-time AI generation.

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Phase 1: Critical Fixes](#phase-1-critical-fixes)
3. [Phase 2: Core Feature Completion](#phase-2-core-feature-completion)
4. [Phase 3: PressMaster Features](#phase-3-pressmaster-features)
5. [Phase 4: Jasper-Style Editor](#phase-4-jasper-style-editor)
6. [Phase 5: Content Management](#phase-5-content-management)
7. [Phase 6: Design System Overhaul](#phase-6-design-system-overhaul)
8. [Phase 7: Advanced Features](#phase-7-advanced-features)
9. [Implementation Timeline](#implementation-timeline)

---

## Current State Assessment

### What Exists (But Is Broken)

| Feature | Status | Issues |
|---------|--------|--------|
| Onboarding/Brand Analysis | ❌ Broken | Dutch content, Unknown industry, No audiences/offerings |
| AI Chat | ❌ Broken | No responses, 503 errors, silent failures |
| Campaigns | ❌ Broken | HTTP 503, can't create campaigns |
| Assets Page | ⚠️ Empty | Only shows "select campaign first" |
| Brand Knowledge Base | ❌ Broken | Page empty despite "data loaded" |
| Kata Lab | ⚠️ UI Only | Untested, wrong design language (purple gradient) |

### What's Completely Missing

| Feature | Priority | Notes |
|---------|----------|-------|
| Sliding Deliverables Panel | HIGH | Right-side panel for generated content |
| Inline Document Editor | HIGH | Jasper-style AI writing canvas |
| TrendMaster (Trend Spotter) | HIGH | PressMaster's flagship feature |
| Social Calendar | HIGH | Visual content scheduling |
| Kanban Board | HIGH | Project/content management |
| Image Editor | MEDIUM | Conversational image editing |
| Press Release Generator | MEDIUM | PressMaster feature |
| Content Distribution | MEDIUM | Multi-platform publishing |
| Analytics Dashboard | MEDIUM | KPIs and performance tracking |
| External Interviews | LOW | AI-guided interview → content |
| White Label / Workspaces | LOW | Agency features |

---

## Phase 1: Critical Fixes

**Goal:** Get the existing features working before adding new ones.

**Estimated Time:** 8-12 hours

### 1.1 Backend Stability

**Files to modify:**
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/database.py`

**Tasks:**

| Task | File | Change |
|------|------|--------|
| 1.1.1 | Railway Dashboard | Check deployment logs for 503 cause |
| 1.1.2 | Railway Dashboard | Verify all env vars: OPENROUTER_API_KEY, FIRECRAWL_API_KEY, PERPLEXITY_API_KEY, DATABASE_URL, CORS_ORIGINS |
| 1.1.3 | `database.py` | Add SSL support for PostgreSQL: `connect_args={"ssl": "require"}` |
| 1.1.4 | `main.py` | Add diagnostic health endpoint showing DB connection, API key status |

**Acceptance Criteria:**
- [ ] `/health` endpoint returns 200 with all checks passing
- [ ] No 503 errors on any endpoint

---

### 1.2 Brand Analysis Quality

**Files to modify:**
- `backend/app/services/onboarding/firecrawl.py`
- `backend/app/services/onboarding/perplexity.py`
- `backend/app/services/onboarding/pipeline.py`

**Tasks:**

| Task | File | Change |
|------|------|--------|
| 1.2.1 | `firecrawl.py` | Add `Accept-Language: en-US` header to all requests |
| 1.2.2 | `firecrawl.py` | Strip country subdomains (nl.stripe.com → stripe.com) |
| 1.2.3 | `firecrawl.py` | Improve product/service extraction from page content |
| 1.2.4 | `perplexity.py` | Rewrite industry detection prompt - NEVER return "Unknown" |
| 1.2.5 | `perplexity.py` | Rewrite audience detection prompt - MUST return 2-3 segments |
| 1.2.6 | `perplexity.py` | Rewrite offerings detection prompt - extract from all pages |
| 1.2.7 | `pipeline.py` | Add validation layer before saving - fallback to AI inference if empty |

**Acceptance Criteria:**
- [ ] stripe.com analysis returns English content
- [ ] Industry shows "Financial Technology" or "Fintech"
- [ ] At least 2 audience segments with details
- [ ] At least 3 products/services detected

---

### 1.3 AI Chat Functionality

**Files to modify:**
- `backend/app/services/ai/openrouter.py`
- `backend/app/api/chat.py`

**Tasks:**

| Task | File | Change |
|------|------|--------|
| 1.3.1 | `openrouter.py` | Add `test_connection()` method |
| 1.3.2 | `openrouter.py` | Add proper timeout handling (60s default) |
| 1.3.3 | `chat.py` | Add try/catch with user-friendly error messages |
| 1.3.4 | `chat.py` | Fix SSE streaming format with proper headers |
| 1.3.5 | `chat.py` | Add `X-Accel-Buffering: no` for nginx/proxy compatibility |

**Acceptance Criteria:**
- [ ] Chat responds within 30 seconds
- [ ] Errors show user-friendly messages (not silent)
- [ ] Streaming works with real-time text chunks

---

### 1.4 Campaign Functionality

**Files to modify:**
- `backend/app/api/campaigns.py`
- `frontend/src/pages/DashboardPage.jsx`

**Tasks:**

| Task | File | Change |
|------|------|--------|
| 1.4.1 | `campaigns.py` | Add validation for organization_id |
| 1.4.2 | `campaigns.py` | Add proper error handling with HTTPException |
| 1.4.3 | `DashboardPage.jsx` | Add loading state to campaign creation |
| 1.4.4 | `DashboardPage.jsx` | Add error display with retry button |

**Acceptance Criteria:**
- [ ] Can create a campaign successfully
- [ ] Errors show in UI with retry option

---

### 1.5 Frontend Error Handling

**Files to create/modify:**
- NEW: `frontend/src/components/ErrorBoundary.jsx`
- NEW: `frontend/src/components/Toast.jsx`
- `frontend/src/main.jsx`
- `frontend/src/services/api.js`
- `frontend/src/pages/DashboardPage.jsx`

**Tasks:**

| Task | File | Change |
|------|------|--------|
| 1.5.1 | `ErrorBoundary.jsx` | Create global error boundary component |
| 1.5.2 | `Toast.jsx` | Create toast notification system |
| 1.5.3 | `main.jsx` | Wrap app with ErrorBoundary and ToastProvider |
| 1.5.4 | `api.js` | Add error handler callback, user-friendly messages |
| 1.5.5 | `api.js` | Map HTTP status codes to friendly messages |
| 1.5.6 | `DashboardPage.jsx` | Fix Brand Knowledge Base rendering |
| 1.5.7 | `DashboardPage.jsx` | Add loading states to all data fetching |
| 1.5.8 | `DashboardPage.jsx` | Add chat loading indicator (typing dots) |

**Acceptance Criteria:**
- [ ] No silent failures anywhere
- [ ] All errors show toast notifications
- [ ] Brand page displays all data correctly
- [ ] Loading indicators during all async operations

---

## Phase 2: Core Feature Completion

**Goal:** Complete the foundational features that exist but are incomplete.

**Estimated Time:** 15-20 hours

### 2.1 Sliding Deliverables Panel

**Files to create:**
- `frontend/src/components/panels/DeliverablesSlidePanel.jsx`
- `frontend/src/components/panels/DeliverableCard.jsx`
- `frontend/src/hooks/useDeliverables.js`

**Specifications:**

```
┌─────────────────────────────────────┬──────────────────┐
│                                     │   DELIVERABLES   │ ← Slides in/out
│         MAIN CONTENT AREA           │                  │
│         (Chat, Editor, etc)         │  [Image 1]       │
│                                     │  [Video 1]       │
│                                     │  [Copy Block]    │
│                                     │  [Social Post]   │
│                                     │                  │
│                                     │  ← Toggle button │
└─────────────────────────────────────┴──────────────────┘
```

**Behavior:**
- Slides in automatically when AI is generating content
- Can be manually toggled open/closed
- Shows deliverables for current project/campaign
- Each card shows: thumbnail, type icon, title, status, actions
- Click card to expand/edit
- Drag to reorder

**Tasks:**

| Task | Description |
|------|-------------|
| 2.1.1 | Create `DeliverablesSlidePanel` component with slide animation |
| 2.1.2 | Create `DeliverableCard` for each content type (image, video, copy, social) |
| 2.1.3 | Create `useDeliverables` hook to manage panel state and content |
| 2.1.4 | Add WebSocket listener for real-time deliverable updates |
| 2.1.5 | Integrate into main layout with toggle button |
| 2.1.6 | Add generation progress indicator on cards |

---

### 2.2 Assets Management (Complete)

**Files to modify:**
- `frontend/src/pages/DashboardPage.jsx` (assets view)
- `backend/app/api/assets.py`

**Tasks:**

| Task | Description |
|------|-------------|
| 2.2.1 | Create asset grid view with filters (type, status, date) |
| 2.2.2 | Add asset preview modal with full content |
| 2.2.3 | Add asset actions: edit, duplicate, delete, download |
| 2.2.4 | Add asset version history |
| 2.2.5 | Add bulk selection and actions |
| 2.2.6 | Add search/filter functionality |

---

### 2.3 Kata Lab Polish

**Files to modify:**
- `frontend/src/pages/KataLabPage.jsx`
- `frontend/src/components/kata/*`

**Tasks:**

| Task | Description |
|------|-------------|
| 2.3.1 | Remove purple gradient styling |
| 2.3.2 | Apply enterprise cloud desktop design |
| 2.3.3 | Test Synthetic Influencer generation |
| 2.3.4 | Test Video Compositor functionality |
| 2.3.5 | Test Script Builder functionality |
| 2.3.6 | Add proper error handling |
| 2.3.7 | Add loading states during generation |

---

## Phase 3: PressMaster Features

**Goal:** Integrate all PressMaster AI features to be better than PressMaster.

**Estimated Time:** 30-40 hours

### 3.1 TrendMaster (Trend Spotter)

**Reference:** PressMaster scans 500,000+ sources daily, identifies trends 3-4 weeks early.

**Files to create:**
- `backend/app/services/trends/trend_scanner.py`
- `backend/app/services/trends/trend_analyzer.py`
- `backend/app/api/trends.py`
- `frontend/src/pages/TrendMasterPage.jsx`
- `frontend/src/components/trends/*`

**Backend Implementation:**

```python
# trend_scanner.py
class TrendScanner:
    """Scans multiple sources for emerging trends."""

    SOURCES = [
        "news_api",      # NewsAPI for headlines
        "reddit",        # Reddit trending topics
        "twitter",       # Twitter/X trends
        "google_trends", # Google Trends API
        "hacker_news",   # Tech trends
        "product_hunt",  # Product trends
    ]

    async def scan_all_sources(self, industry: str, keywords: list) -> list[Trend]:
        """Scan all sources and return emerging trends."""
        pass

    async def analyze_trend(self, trend: Trend) -> TrendAnalysis:
        """Deep analysis of a specific trend."""
        pass

    async def predict_trajectory(self, trend: Trend) -> TrendPrediction:
        """Predict if trend will grow, peak, or decline."""
        pass
```

**Frontend Features:**
- Dashboard showing trending topics in user's industry
- Trend cards with: title, source count, growth rate, sentiment, predicted peak
- Click to see full analysis
- "Create Content" button to generate content about trend
- Historical trend tracking
- Custom keyword alerts

**Tasks:**

| Task | Description |
|------|-------------|
| 3.1.1 | Create `TrendScanner` service with multi-source scanning |
| 3.1.2 | Integrate NewsAPI for news trends |
| 3.1.3 | Integrate Google Trends API |
| 3.1.4 | Create AI-powered trend analysis using OpenRouter |
| 3.1.5 | Create trend prediction model |
| 3.1.6 | Create `/api/trends` endpoints |
| 3.1.7 | Create `TrendMasterPage` with dashboard layout |
| 3.1.8 | Create trend cards with visualization |
| 3.1.9 | Add "Create Content from Trend" workflow |
| 3.1.10 | Add trend alerts/notifications |

---

### 3.2 Press Release Generator

**Files to create:**
- `backend/app/services/content/press_release.py`
- `frontend/src/components/content/PressReleaseBuilder.jsx`

**Features:**
- Guided press release creation
- AI-generated drafts from bullet points
- Standard press release format (headline, dateline, lead, body, boilerplate)
- Quote generation
- Distribution channel selection
- Preview in standard PR format

**Tasks:**

| Task | Description |
|------|-------------|
| 3.2.1 | Create press release template system |
| 3.2.2 | Create AI generation with brand voice |
| 3.2.3 | Create quote generator for executives |
| 3.2.4 | Create formatting engine for standard PR format |
| 3.2.5 | Create frontend builder with step-by-step flow |
| 3.2.6 | Add preview mode |

---

### 3.3 Article Writer (Interview-to-Content)

**Reference:** PressMaster turns 5-minute interviews into weeks of content.

**Files to create:**
- `backend/app/services/content/interview_processor.py`
- `backend/app/services/content/article_generator.py`
- `frontend/src/pages/ArticleWriterPage.jsx`

**Features:**
- Voice/text interview input
- AI transcription and analysis
- Generate multiple content pieces from one interview:
  - Blog articles
  - LinkedIn posts
  - Twitter threads
  - Press releases
  - Email newsletters
- Content calendar integration

**Tasks:**

| Task | Description |
|------|-------------|
| 3.3.1 | Create interview transcription service (Whisper API) |
| 3.3.2 | Create content extraction and structuring |
| 3.3.3 | Create multi-format content generator |
| 3.3.4 | Create frontend interview interface |
| 3.3.5 | Add content preview and editing |

---

### 3.4 Content Distribution

**Reference:** PressMaster offers 400+ syndications, WordPress/Medium/Webflow integration.

**Files to create:**
- `backend/app/services/distribution/publisher.py`
- `backend/app/services/distribution/integrations/*`
- `frontend/src/components/distribution/PublishPanel.jsx`

**Integrations:**
- WordPress (REST API)
- Medium (API)
- Webflow (CMS API)
- LinkedIn (API)
- Twitter/X (API)
- Email (SendGrid/Mailchimp)

**Tasks:**

| Task | Description |
|------|-------------|
| 3.4.1 | Create publisher service architecture |
| 3.4.2 | WordPress integration |
| 3.4.3 | Medium integration |
| 3.4.4 | LinkedIn integration |
| 3.4.5 | Twitter integration |
| 3.4.6 | Create one-click publish UI |
| 3.4.7 | Add scheduling capability |

---

### 3.5 Analytics Dashboard

**Reference:** PressMaster offers 45+ KPIs.

**Files to create:**
- `backend/app/services/analytics/tracker.py`
- `backend/app/api/analytics.py`
- `frontend/src/pages/AnalyticsPage.jsx`

**Metrics to Track:**
- Content performance (views, engagement, shares)
- Campaign ROI
- Trend prediction accuracy
- Content velocity
- Brand mention tracking
- Competitor comparison

**Tasks:**

| Task | Description |
|------|-------------|
| 3.5.1 | Create analytics data model |
| 3.5.2 | Create tracking pixel/integration |
| 3.5.3 | Create dashboard with charts (Recharts) |
| 3.5.4 | Add date range filtering |
| 3.5.5 | Add export functionality |

---

### 3.6 Quality Control System

**Reference:** PressMaster's triple-check: accuracy, plagiarism, AI detection.

**Files to create:**
- `backend/app/services/quality/fact_checker.py`
- `backend/app/services/quality/plagiarism_checker.py`
- `backend/app/services/quality/ai_detector.py`

**Tasks:**

| Task | Description |
|------|-------------|
| 3.6.1 | Integrate fact-checking (claim verification) |
| 3.6.2 | Integrate plagiarism detection (Copyscape API or similar) |
| 3.6.3 | Add AI content detection scoring |
| 3.6.4 | Create quality score badge on all content |
| 3.6.5 | Add humanization suggestions |

---

## Phase 4: Jasper-Style Editor

**Goal:** Create a powerful inline document editor for marketing content.

**Estimated Time:** 25-30 hours

### 4.1 Rich Text Editor Foundation

**Files to create:**
- `frontend/src/components/editor/MarketingEditor.jsx`
- `frontend/src/components/editor/EditorToolbar.jsx`
- `frontend/src/components/editor/AICommands.jsx`

**Tech Stack:**
- TipTap (ProseMirror-based) or Slate.js
- Custom AI command extensions

**Features:**
- Google Docs-like editing experience
- Formatting: bold, italic, headers, lists, links, images
- Real-time collaboration ready
- Comment threads
- Version history

**Tasks:**

| Task | Description |
|------|-------------|
| 4.1.1 | Set up TipTap/Slate editor foundation |
| 4.1.2 | Create custom toolbar with formatting options |
| 4.1.3 | Add image upload and embedding |
| 4.1.4 | Add link management |
| 4.1.5 | Add undo/redo with history |

---

### 4.2 AI Writing Assistant

**Inline AI commands (like Jasper):**

| Command | Action |
|---------|--------|
| `/write` | Generate content from prompt |
| `/expand` | Expand selected text |
| `/shorten` | Condense selected text |
| `/rewrite` | Rewrite in different tone |
| `/headline` | Generate headlines |
| `/cta` | Generate call-to-action |
| `/outline` | Generate content outline |

**Implementation:**

```jsx
// Slash command menu
const AICommands = [
  { command: '/write', label: 'Write', icon: PenIcon, action: generateContent },
  { command: '/expand', label: 'Expand', icon: ExpandIcon, action: expandText },
  { command: '/shorten', label: 'Shorten', icon: CompressIcon, action: shortenText },
  { command: '/rewrite', label: 'Rewrite', icon: RefreshIcon, action: rewriteText },
  // ... more commands
];
```

**Tasks:**

| Task | Description |
|------|-------------|
| 4.2.1 | Create slash command detection and menu |
| 4.2.2 | Implement `/write` - generate from prompt |
| 4.2.3 | Implement `/expand` - expand selection |
| 4.2.4 | Implement `/shorten` - condense selection |
| 4.2.5 | Implement `/rewrite` - tone/style change |
| 4.2.6 | Implement `/headline` - generate headlines |
| 4.2.7 | Implement `/cta` - generate CTAs |
| 4.2.8 | Add inline AI suggestions (ghost text) |
| 4.2.9 | Add tone selector (professional, casual, bold, etc.) |

---

### 4.3 Brand Voice Integration

**Files to modify:**
- `backend/app/services/ai/brand_voice.py`
- `frontend/src/components/editor/BrandVoiceSelector.jsx`

**Features:**
- Editor automatically uses brand voice from knowledge base
- Toggle brand voice on/off
- Voice strength slider (subtle → strong)
- Custom voice profiles

**Tasks:**

| Task | Description |
|------|-------------|
| 4.3.1 | Create brand voice prompt injection |
| 4.3.2 | Create voice strength parameter |
| 4.3.3 | Create UI for voice selection |
| 4.3.4 | Add voice preview/comparison |

---

### 4.4 Content Templates

**50+ templates like Jasper:**

**Categories:**
- Blog Posts (listicle, how-to, comparison, thought leadership)
- Social Media (LinkedIn post, Twitter thread, Instagram caption)
- Email (newsletter, cold outreach, follow-up, announcement)
- Ads (Google, Facebook, LinkedIn)
- Website (landing page, product description, about page)
- PR (press release, media pitch, executive quote)

**Tasks:**

| Task | Description |
|------|-------------|
| 4.4.1 | Create template data structure |
| 4.4.2 | Create 50+ templates across categories |
| 4.4.3 | Create template browser UI |
| 4.4.4 | Add template customization |
| 4.4.5 | Add user custom templates |

---

## Phase 5: Content Management

**Goal:** Organize and schedule content effectively.

**Estimated Time:** 20-25 hours

### 5.1 Kanban Board

**Files to create:**
- `frontend/src/pages/KanbanPage.jsx`
- `frontend/src/components/kanban/*`

**Columns:**
- Ideas / Backlog
- In Progress
- Review
- Approved
- Scheduled
- Published

**Features:**
- Drag-and-drop cards
- Card details: title, content preview, assignee, due date, labels
- Quick actions: edit, schedule, publish, delete
- Filtering by type, status, date, assignee
- Bulk operations

**Tasks:**

| Task | Description |
|------|-------------|
| 5.1.1 | Create Kanban board layout with react-beautiful-dnd |
| 5.1.2 | Create content cards with previews |
| 5.1.3 | Implement drag-and-drop between columns |
| 5.1.4 | Add card detail modal |
| 5.1.5 | Add filtering and search |
| 5.1.6 | Add bulk selection and actions |
| 5.1.7 | Connect to backend for persistence |

---

### 5.2 Social Calendar

**Files to create:**
- `frontend/src/pages/CalendarPage.jsx`
- `frontend/src/components/calendar/*`
- `backend/app/services/scheduling/scheduler.py`

**Views:**
- Month view
- Week view
- Day view
- List view

**Features:**
- Visual content scheduling
- Drag to reschedule
- Platform icons on each post
- Preview on hover
- Time zone support
- Best time suggestions (AI-powered)
- Bulk scheduling

**Tasks:**

| Task | Description |
|------|-------------|
| 5.2.1 | Create calendar component (react-big-calendar or custom) |
| 5.2.2 | Create event cards with platform badges |
| 5.2.3 | Implement drag-to-reschedule |
| 5.2.4 | Create scheduling backend with queue |
| 5.2.5 | Add "best time to post" AI suggestions |
| 5.2.6 | Add recurring post support |
| 5.2.7 | Add bulk scheduling UI |

---

### 5.3 Image Editor (Conversational)

**Files to create:**
- `frontend/src/components/editor/ImageEditor.jsx`
- `backend/app/services/images/editor.py`

**Features:**
- Upload or AI-generate base image
- Conversational editing:
  - "Make the background blue"
  - "Add our logo in the corner"
  - "Remove the person on the right"
  - "Add text: 'Summer Sale'"
  - "Resize for Instagram stories"
- Edit history with undo
- Export in multiple formats/sizes

**Tasks:**

| Task | Description |
|------|-------------|
| 5.3.1 | Create image canvas component |
| 5.3.2 | Integrate image generation (Segmind/DALL-E) |
| 5.3.3 | Create conversational edit interface |
| 5.3.4 | Implement edit operations via AI |
| 5.3.5 | Add text overlay capability |
| 5.3.6 | Add resize/crop for social formats |
| 5.3.7 | Add export functionality |

---

## Phase 6: Design System Overhaul

**Goal:** Create a cohesive, enterprise cloud desktop aesthetic.

**Estimated Time:** 15-20 hours

### 6.1 Design Tokens

**Create:** `frontend/src/styles/tokens.css`

```css
:root {
  /* Colors - Dark Enterprise Theme */
  --color-bg-primary: #0f0f0f;
  --color-bg-secondary: #1a1a1a;
  --color-bg-elevated: #242424;
  --color-bg-hover: #2a2a2a;

  --color-border: #333333;
  --color-border-subtle: #262626;

  --color-text-primary: #ffffff;
  --color-text-secondary: #a0a0a0;
  --color-text-muted: #666666;

  --color-accent: #3b82f6;  /* Blue */
  --color-accent-hover: #2563eb;
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;

  /* Typography */
  --font-family: 'Inter', -apple-system, sans-serif;
  --font-size-xs: 11px;
  --font-size-sm: 13px;
  --font-size-base: 14px;
  --font-size-lg: 16px;
  --font-size-xl: 20px;
  --font-size-2xl: 24px;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;

  /* Borders */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 12px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.5);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;
}
```

---

### 6.2 Component Library

**Create consistent components:**

| Component | File | Notes |
|-----------|------|-------|
| Button | `Button.jsx` | Primary, secondary, ghost, danger variants |
| Input | `Input.jsx` | Text, textarea, with labels and errors |
| Select | `Select.jsx` | Dropdown with search |
| Modal | `Modal.jsx` | Slide-in panels and centered modals |
| Card | `Card.jsx` | Content cards with hover states |
| Badge | `Badge.jsx` | Status indicators |
| Avatar | `Avatar.jsx` | User/brand avatars |
| Tooltip | `Tooltip.jsx` | Contextual hints |
| Tabs | `Tabs.jsx` | Tab navigation |
| Table | `Table.jsx` | Data tables with sorting |

**Tasks:**

| Task | Description |
|------|-------------|
| 6.2.1 | Create design tokens file |
| 6.2.2 | Create Button component with variants |
| 6.2.3 | Create Input components |
| 6.2.4 | Create Modal/Panel components |
| 6.2.5 | Create Card components |
| 6.2.6 | Create all other base components |
| 6.2.7 | Replace all existing inline styles |

---

### 6.3 Layout System

**Cloud Desktop Layout:**

```
┌────────────────────────────────────────────────────────────────┐
│  HEADER: Logo | Navigation Tabs | Search | User Menu           │
├────────┬───────────────────────────────────────────┬───────────┤
│        │                                           │           │
│  SIDE  │           MAIN CONTENT AREA              │  CONTEXT  │
│  NAV   │                                           │  PANEL    │
│        │  (Editor / Dashboard / Calendar / etc)    │           │
│  Chat  │                                           │  Slides   │
│  Camp  │                                           │  In/Out   │
│  Assets│                                           │           │
│  Brand │                                           │  Shows:   │
│  Trends│                                           │  - AI Gen │
│        │                                           │  - Details│
│  ───── │                                           │  - Help   │
│  Kata  │                                           │           │
│        │                                           │           │
└────────┴───────────────────────────────────────────┴───────────┘
```

**Tasks:**

| Task | Description |
|------|-------------|
| 6.3.1 | Create main layout wrapper component |
| 6.3.2 | Create collapsible sidebar |
| 6.3.3 | Create sliding context panel |
| 6.3.4 | Create responsive breakpoints |
| 6.3.5 | Add keyboard shortcuts for panel toggle |

---

### 6.4 Kata Lab Redesign

**Remove purple gradient, apply enterprise design:**

**Tasks:**

| Task | Description |
|------|-------------|
| 6.4.1 | Replace gradient backgrounds with solid colors |
| 6.4.2 | Apply design tokens to all components |
| 6.4.3 | Redesign cards and buttons |
| 6.4.4 | Improve form layouts |
| 6.4.5 | Add consistent iconography |

---

## Phase 7: Advanced Features

**Goal:** Enterprise and power-user features.

**Estimated Time:** 20-25 hours

### 7.1 Multi-Workspace Support

**For agencies managing multiple clients:**

- Separate workspaces per client
- Workspace switching in header
- Per-workspace settings
- Per-workspace brand voice
- Access controls per workspace

### 7.2 Team Collaboration

- User roles (admin, editor, viewer)
- Content assignments
- Approval workflows
- Comment threads on content
- Activity feed
- @mentions

### 7.3 White Label

- Custom branding per workspace
- Custom domain support
- Remove "Marketing Agent" branding
- Custom colors

### 7.4 API Access

- Public API for integrations
- Webhooks for events
- Zapier integration
- API key management

### 7.5 AI Model Selection

- Choose between Claude, GPT-4, etc.
- Model comparison for outputs
- Cost tracking per model

---

## Implementation Timeline

### Sprint 1 (Week 1-2): Critical Fixes
- Phase 1: All critical fixes
- Backend stable, chat working, brand analysis accurate
- **Deliverable:** Working MVP

### Sprint 2 (Week 3-4): Core Completion
- Phase 2: Sliding panel, assets, Kata Lab polish
- **Deliverable:** Complete existing features

### Sprint 3 (Week 5-7): PressMaster Features
- Phase 3: TrendMaster, Press Release, Article Writer
- **Deliverable:** PressMaster parity

### Sprint 4 (Week 8-10): Editor & Content Management
- Phase 4: Jasper-style editor
- Phase 5: Kanban, Calendar, Image Editor
- **Deliverable:** Full content creation suite

### Sprint 5 (Week 11-12): Design Polish
- Phase 6: Design system overhaul
- Full UI consistency
- **Deliverable:** Enterprise-ready UI

### Sprint 6 (Week 13-14): Advanced Features
- Phase 7: Teams, workspaces, integrations
- **Deliverable:** Enterprise features

---

## File Inventory

### Backend Files to Create
- `backend/app/services/trends/trend_scanner.py`
- `backend/app/services/trends/trend_analyzer.py`
- `backend/app/services/content/press_release.py`
- `backend/app/services/content/interview_processor.py`
- `backend/app/services/content/article_generator.py`
- `backend/app/services/distribution/publisher.py`
- `backend/app/services/analytics/tracker.py`
- `backend/app/services/quality/fact_checker.py`
- `backend/app/services/quality/plagiarism_checker.py`
- `backend/app/services/scheduling/scheduler.py`
- `backend/app/services/images/editor.py`
- `backend/app/api/trends.py`
- `backend/app/api/analytics.py`

### Frontend Files to Create
- `frontend/src/components/panels/DeliverablesSlidePanel.jsx`
- `frontend/src/components/editor/MarketingEditor.jsx`
- `frontend/src/components/editor/AICommands.jsx`
- `frontend/src/components/editor/ImageEditor.jsx`
- `frontend/src/pages/TrendMasterPage.jsx`
- `frontend/src/pages/KanbanPage.jsx`
- `frontend/src/pages/CalendarPage.jsx`
- `frontend/src/pages/AnalyticsPage.jsx`
- `frontend/src/components/ErrorBoundary.jsx`
- `frontend/src/components/Toast.jsx`
- `frontend/src/styles/tokens.css`
- All design system components

### Backend Files to Modify
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/database.py`
- `backend/app/api/chat.py`
- `backend/app/api/campaigns.py`
- `backend/app/services/onboarding/firecrawl.py`
- `backend/app/services/onboarding/perplexity.py`
- `backend/app/services/onboarding/pipeline.py`
- `backend/app/services/ai/openrouter.py`

### Frontend Files to Modify
- `frontend/src/main.jsx`
- `frontend/src/App.jsx`
- `frontend/src/services/api.js`
- `frontend/src/pages/DashboardPage.jsx`
- `frontend/src/pages/KataLabPage.jsx`
- All existing component files (for design system)

---

## Testing Checklist

### Phase 1 Acceptance
- [ ] `/health` returns 200 with all checks passing
- [ ] Brand analysis returns English content
- [ ] Industry correctly identified
- [ ] 2+ audiences detected
- [ ] 3+ products detected
- [ ] Chat responds within 30s
- [ ] All errors show user-friendly messages
- [ ] Campaigns can be created

### Phase 2 Acceptance
- [ ] Deliverables panel slides in on generation
- [ ] Panel can be manually toggled
- [ ] Assets page shows all content
- [ ] Kata Lab works without errors
- [ ] Kata Lab matches enterprise design

### Phase 3 Acceptance
- [ ] TrendMaster shows relevant trends
- [ ] Press releases generate correctly
- [ ] Article writer creates multiple formats
- [ ] Distribution publishes to platforms
- [ ] Analytics shows meaningful data

### Phase 4 Acceptance
- [ ] Editor loads without errors
- [ ] All slash commands work
- [ ] Brand voice affects output
- [ ] Templates load and customize

### Phase 5 Acceptance
- [ ] Kanban drag-and-drop works
- [ ] Calendar scheduling works
- [ ] Image editor responds to commands

### Phase 6 Acceptance
- [ ] No purple gradients anywhere
- [ ] Consistent design tokens used
- [ ] All components match design system
- [ ] Responsive on tablet/desktop

---

## Prompt for Claude Code

```
I need you to implement the Marketing Agent Master Plan.

PLAN FILE: Read /sessions/charming-upbeat-galileo/mnt/workflow/MARKETING_AGENT_MASTER_PLAN.md

Start with Phase 1 (Critical Fixes) and complete each task in order.

For each phase:
1. Read the relevant files before modifying
2. Make minimal, targeted changes
3. Test after each major change
4. Report progress and any issues

Key priorities:
- Phase 1 is CRITICAL - get basic features working first
- Don't skip to later phases until Phase 1 is complete
- Follow the design tokens for all UI work
- Use the exact file structure specified

Current status: Nothing works. Backend returns 503. Start there.
```

---

*This plan provides a complete roadmap from broken prototype to enterprise-ready marketing platform.*
