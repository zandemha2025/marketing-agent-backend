# Marketing Agent - Complete Architecture Status

## Executive Summary

**Current State:** Frontend UI shells exist, but most features are NOT connected to backend APIs.

**What "Working" Means:** Data flows from UI → API → Database → AI Services → Back to UI

---

## 🔴 CRITICAL: Connection Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Vercel)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  DashboardPage.jsx                                                           │
│  ├── Chat View ────────────────► api.sendMessage() ──► ✅ CONNECTED          │
│  ├── Campaigns View ───────────► api.listCampaigns() ► ✅ CONNECTED          │
│  ├── Brand View ───────────────► api.getKnowledgeBase() ✅ CONNECTED         │
│  ├── Assets View ──────────────► api.getAssets() ────► ⚠️  PARTIAL          │
│  ├── TrendMaster ──────────────► ❌ NO API ──────────► 🔴 MOCK DATA ONLY    │
│  ├── Kanban Board ─────────────► ❌ NO API ──────────► 🔴 LOCAL STATE ONLY  │
│  ├── Social Calendar ──────────► ❌ NO API ──────────► 🔴 LOCAL STATE ONLY  │
│  ├── Image Editor ─────────────► ❌ NO API ──────────► 🔴 CONSOLE.LOG ONLY  │
│  └── Deliverables Panel ───────► ❌ NO API ──────────► 🔴 LOCAL STATE ONLY  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (Railway)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  EXISTING ENDPOINTS:                                                         │
│  ├── POST /api/onboarding/analyze ────────► ✅ WORKS (fixed)                │
│  ├── GET  /api/onboarding/presentation ───► ✅ WORKS (fixed)                │
│  ├── POST /api/conversations ─────────────► ✅ EXISTS                       │
│  ├── POST /api/conversations/{id}/message ► ✅ EXISTS                       │
│  ├── GET  /api/campaigns ─────────────────► ✅ EXISTS                       │
│  ├── POST /api/campaigns ─────────────────► ✅ EXISTS                       │
│  ├── POST /api/campaigns/{id}/execute ────► ⚠️  PARTIAL (WebSocket issues) │
│  └── GET  /api/knowledge-base ────────────► ✅ EXISTS                       │
│                                                                              │
│  MISSING ENDPOINTS (needed for Phase 2 features):                           │
│  ├── GET  /api/trends ────────────────────► ❌ DOES NOT EXIST               │
│  ├── POST /api/trends/analyze ────────────► ❌ DOES NOT EXIST               │
│  ├── GET  /api/tasks ─────────────────────► ❌ DOES NOT EXIST               │
│  ├── POST /api/tasks ─────────────────────► ❌ DOES NOT EXIST               │
│  ├── PUT  /api/tasks/{id} ────────────────► ❌ DOES NOT EXIST               │
│  ├── GET  /api/scheduled-posts ───────────► ❌ DOES NOT EXIST               │
│  ├── POST /api/scheduled-posts ───────────► ❌ DOES NOT EXIST               │
│  ├── POST /api/images/edit ───────────────► ❌ DOES NOT EXIST               │
│  ├── GET  /api/deliverables ──────────────► ❌ DOES NOT EXIST               │
│  ├── POST /api/deliverables ──────────────► ❌ DOES NOT EXIST               │
│  └── POST /api/content/refine ────────────► ❌ DOES NOT EXIST               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE (PostgreSQL)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  EXISTING TABLES:                                                            │
│  ├── organizations ───────────────────────► ✅ EXISTS                       │
│  ├── brand_profiles ──────────────────────► ✅ EXISTS                       │
│  ├── campaigns ───────────────────────────► ✅ EXISTS                       │
│  ├── conversations ───────────────────────► ✅ EXISTS                       │
│  ├── messages ────────────────────────────► ✅ EXISTS                       │
│  └── assets ──────────────────────────────► ✅ EXISTS                       │
│                                                                              │
│  MISSING TABLES (needed for Phase 2 features):                              │
│  ├── trends ──────────────────────────────► ❌ DOES NOT EXIST               │
│  ├── tasks ───────────────────────────────► ❌ DOES NOT EXIST               │
│  ├── scheduled_posts ─────────────────────► ❌ DOES NOT EXIST               │
│  ├── deliverables ────────────────────────► ❌ DOES NOT EXIST               │
│  └── image_edits ─────────────────────────► ❌ DOES NOT EXIST               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL APIs                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  CONNECTED:                                                                  │
│  ├── OpenRouter (Claude) ─────────────────► ✅ CONNECTED                    │
│  ├── Perplexity ──────────────────────────► ✅ CONNECTED (market research)  │
│  └── Firecrawl ───────────────────────────► ✅ CONNECTED (website scraping) │
│                                                                              │
│  NOT CONNECTED (needed for full features):                                   │
│  ├── NewsAPI / Google Trends ─────────────► ❌ NOT CONNECTED (TrendMaster)  │
│  ├── Replicate / DALL-E ──────────────────► ❌ NOT CONNECTED (Image Editor) │
│  ├── Twitter API ─────────────────────────► ❌ NOT CONNECTED (Publishing)   │
│  ├── LinkedIn API ────────────────────────► ❌ NOT CONNECTED (Publishing)   │
│  └── Instagram API ───────────────────────► ❌ NOT CONNECTED (Publishing)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature-by-Feature Status

### 1. ✅ Brand Onboarding (WORKING)
**What "working" means:** Enter domain → Get English brand analysis with industry, audience, offerings

| Component | Status | Notes |
|-----------|--------|-------|
| Frontend form | ✅ Works | OnboardingPage.jsx |
| API endpoint | ✅ Works | POST /api/onboarding/analyze |
| Firecrawl scraping | ✅ Works | Gets website content |
| Perplexity analysis | ✅ Works | Analyzes brand |
| Language detection | ✅ Fixed | Now forces English |
| Industry detection | ✅ Fixed | Added fallbacks |
| Audience extraction | ✅ Fixed | Added fallback segments |
| Database storage | ✅ Works | Saves to brand_profiles |

### 2. ✅ AI Chat (WORKING - with fixes)
**What "working" means:** Type message → Get AI response about marketing

| Component | Status | Notes |
|-----------|--------|-------|
| Chat UI | ✅ Works | DashboardPage.jsx |
| Send message API | ✅ Works | POST /conversations/{id}/message |
| Conversation creation | ✅ Fixed | Now auto-creates if none exists |
| OpenRouter integration | ✅ Works | Uses Claude via OpenRouter |
| Response display | ✅ Works | Shows AI responses |

### 3. ⚠️ Campaign Management (PARTIAL)
**What "working" means:** Create campaign → Execute → Get generated assets

| Component | Status | Notes |
|-----------|--------|-------|
| Campaign list UI | ✅ Works | Shows campaigns |
| Campaign create | ✅ Works | Creates in database |
| Campaign execute | ⚠️ Partial | WebSocket may have issues |
| Asset generation | ⚠️ Untested | Depends on execution |
| Asset display | ⚠️ Partial | Gallery exists but may not load |

### 4. 🔴 TrendMaster (NOT CONNECTED)
**What "working" means:** See real-time trends → Click to create campaign brief

| Component | Status | What's Needed |
|-----------|--------|---------------|
| TrendMaster.jsx UI | ✅ Built | Has mock data |
| Trends API endpoint | ❌ Missing | Need GET /api/trends |
| Trends database table | ❌ Missing | Need `trends` table |
| NewsAPI integration | ❌ Missing | Need API key + integration |
| Perplexity trend scan | ❌ Missing | Need to call for trend analysis |
| Create brief action | ❌ Not connected | Need to link to campaign creation |

**To make it work:**
```python
# Backend needs:
# 1. New file: /backend/app/api/trends.py
# 2. New table: trends (id, title, description, category, score, sources, created_at)
# 3. Scheduled job to fetch trends from NewsAPI/Perplexity
# 4. Frontend needs to call API instead of using MOCK_TRENDS
```

### 5. 🔴 Kanban Board (NOT CONNECTED)
**What "working" means:** Drag tasks between columns → Persists to database

| Component | Status | What's Needed |
|-----------|--------|---------------|
| KanbanBoard.jsx UI | ✅ Built | Drag-drop works locally |
| Tasks API endpoint | ❌ Missing | Need CRUD /api/tasks |
| Tasks database table | ❌ Missing | Need `tasks` table |
| Campaign linkage | ❌ Missing | Need to link tasks to campaigns |
| Real-time sync | ❌ Missing | Need WebSocket for live updates |

**To make it work:**
```python
# Backend needs:
# 1. New file: /backend/app/api/tasks.py
# 2. New table: tasks (id, campaign_id, title, description, status, priority, assignee, due_date)
# 3. CRUD endpoints
# 4. Frontend needs to fetch/save tasks via API
```

### 6. 🔴 Social Calendar (NOT CONNECTED)
**What "working" means:** Schedule posts → See on calendar → Publish to platforms

| Component | Status | What's Needed |
|-----------|--------|---------------|
| SocialCalendar.jsx UI | ✅ Built | Calendar renders |
| Scheduled posts API | ❌ Missing | Need CRUD /api/scheduled-posts |
| Scheduled posts table | ❌ Missing | Need `scheduled_posts` table |
| Platform publishing | ❌ Missing | Need Twitter/LinkedIn/Instagram APIs |
| Scheduler job | ❌ Missing | Need background job to publish at scheduled time |

**To make it work:**
```python
# Backend needs:
# 1. New file: /backend/app/api/scheduled_posts.py
# 2. New table: scheduled_posts (id, campaign_id, platform, content, scheduled_at, status)
# 3. Background worker (Celery/APScheduler) to publish at scheduled times
# 4. Platform API integrations
```

### 7. 🔴 Image Editor (NOT CONNECTED)
**What "working" means:** Upload image → Type command → See AI-edited result

| Component | Status | What's Needed |
|-----------|--------|---------------|
| ConversationalImageEditor.jsx | ✅ Built | Upload works, chat UI works |
| Image edit API | ❌ Missing | Need POST /api/images/edit |
| AI image service | ❌ Missing | Need Replicate/DALL-E integration |
| Image storage | ❌ Missing | Need S3/Cloudinary for images |
| History/versioning | ❌ Missing | Need to store edit history |

**To make it work:**
```python
# Backend needs:
# 1. New file: /backend/app/api/images.py
# 2. Replicate API integration (for img2img, remove-bg, etc.)
# 3. S3/Cloudinary setup for image storage
# 4. Frontend needs to call API and display results
```

### 8. 🔴 Deliverables Panel (NOT CONNECTED)
**What "working" means:** See campaign deliverables → Edit with AI → Save changes

| Component | Status | What's Needed |
|-----------|--------|---------------|
| SlidingDeliverablesPanel.jsx | ✅ Built | Panel slides, editor works |
| DocumentEditor.jsx | ✅ Built | Formatting, AI menu works |
| Deliverables API | ❌ Missing | Need CRUD /api/deliverables |
| Deliverables table | ❌ Missing | Need `deliverables` table |
| AI refinement | ❌ Missing | Need POST /api/content/refine |
| Asset linkage | ❌ Missing | Should link to campaign assets |

**To make it work:**
```python
# Backend needs:
# 1. New file: /backend/app/api/deliverables.py
# 2. New table: deliverables (id, campaign_id, type, title, content, status)
# 3. AI refinement endpoint that calls OpenRouter
# 4. Frontend needs to fetch/save deliverables via API
```

---

## Priority Order to Make Things Work

### Week 1: Stabilize Existing Features
1. **Verify backend is responding** - Check Railway logs
2. **Test campaign execution end-to-end** - Fix WebSocket if broken
3. **Test asset display** - Ensure generated assets show up
4. **Add error handling everywhere** - User-friendly messages

### Week 2: Connect Phase 2 Features
1. **Create database migrations** for new tables (tasks, trends, scheduled_posts, deliverables)
2. **Build Tasks API** - Connect Kanban board
3. **Build Deliverables API** - Connect deliverables panel
4. **Add AI refinement endpoint** - Enable document editor AI

### Week 3: Add External Integrations
1. **TrendMaster** - Connect NewsAPI or use Perplexity for trends
2. **Calendar Publishing** - At minimum, add "copy to clipboard" for manual posting
3. **Image Editor** - Connect to Replicate for basic edits (resize, filter)

### Week 4: Polish & Testing
1. **End-to-end testing** of all flows
2. **Error handling and edge cases**
3. **Performance optimization**
4. **User feedback incorporation**

---

## Files That Need To Be Created

### Backend (Python/FastAPI)

```
/backend/app/api/
├── trends.py          # TrendMaster backend
├── tasks.py           # Kanban tasks CRUD
├── scheduled_posts.py # Social calendar backend
├── deliverables.py    # Deliverables CRUD + AI refinement
└── images.py          # Image editing with AI

/backend/app/models/
├── trend.py
├── task.py
├── scheduled_post.py
└── deliverable.py

/backend/app/services/
├── trend_service.py   # NewsAPI/Perplexity integration
├── image_service.py   # Replicate integration
└── publish_service.py # Social media publishing
```

### Frontend (React)

```
/frontend/src/services/
└── api.js             # Add methods for new endpoints

The UI components are ALREADY BUILT, just need API connections
```

---

## Environment Variables Needed

```bash
# Currently have:
OPENROUTER_API_KEY=xxx
PERPLEXITY_API_KEY=xxx
FIRECRAWL_API_KEY=xxx
DATABASE_URL=postgresql://...

# Need to add:
NEWSAPI_KEY=xxx              # For TrendMaster
REPLICATE_API_KEY=xxx        # For Image Editor
TWITTER_API_KEY=xxx          # For Calendar publishing
TWITTER_API_SECRET=xxx
LINKEDIN_CLIENT_ID=xxx       # For Calendar publishing
LINKEDIN_CLIENT_SECRET=xxx
AWS_ACCESS_KEY=xxx           # For image storage (if using S3)
AWS_SECRET_KEY=xxx
```

---

## Summary

| Feature | UI Built | API Exists | DB Table | Connected | Status |
|---------|----------|------------|----------|-----------|--------|
| Onboarding | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| AI Chat | ✅ | ✅ | ✅ | ✅ | **WORKING** |
| Campaigns | ✅ | ✅ | ✅ | ⚠️ | **PARTIAL** |
| Assets | ✅ | ⚠️ | ✅ | ⚠️ | **PARTIAL** |
| TrendMaster | ✅ | ❌ | ❌ | ❌ | **UI ONLY** |
| Kanban | ✅ | ❌ | ❌ | ❌ | **UI ONLY** |
| Calendar | ✅ | ❌ | ❌ | ❌ | **UI ONLY** |
| Image Editor | ✅ | ❌ | ❌ | ❌ | **UI ONLY** |
| Deliverables | ✅ | ❌ | ❌ | ❌ | **UI ONLY** |

**Bottom Line:** The Phase 2 features I built are beautiful UI shells with no backend. To make them "work", each needs:
1. Database table
2. API endpoints (CRUD + any special actions)
3. Frontend API calls to replace local state/mock data
4. (Some features) External API integrations

---

## Frontend API Service - Current Methods

```javascript
// File: /frontend/src/services/api.js

// ✅ EXISTING METHODS (backend endpoints exist):
api.startOnboarding(domain, companyName)        // POST /onboarding/start
api.getOnboardingStatus(orgId)                  // GET /onboarding/status/{id}
api.getOnboardingResult(orgId)                  // GET /onboarding/result/{id}
api.getOrganization(orgId)                      // GET /organizations/{id}
api.getKnowledgeBase(orgId)                     // GET /organizations/{id}/knowledge-base
api.listCampaigns(orgId)                        // GET /campaigns
api.getCampaign(campaignId)                     // GET /campaigns/{id}
api.createCampaign(data)                        // POST /campaigns
api.executeCampaign(campaignId)                 // POST /campaigns/{id}/execute
api.listAssets(campaignId)                      // GET /assets
api.getAsset(assetId)                           // GET /assets/{id}
api.listConversations(orgId)                    // GET /chat/conversations
api.getConversation(convId)                     // GET /chat/conversations/{id}
api.createConversation(orgId, title, type)      // POST /chat/conversations
api.sendMessage(convId, content)                // POST /chat/conversations/{id}/messages

// ❌ NEEDED METHODS (must add to api.js AND create backend endpoints):

// TrendMaster
api.listTrends(orgId, filters)                  // GET /trends
api.getTrend(trendId)                           // GET /trends/{id}
api.refreshTrends(orgId)                        // POST /trends/refresh
api.createBriefFromTrend(trendId, data)         // POST /trends/{id}/create-brief

// Kanban Tasks
api.listTasks(campaignId)                       // GET /tasks
api.createTask(data)                            // POST /tasks
api.updateTask(taskId, data)                    // PUT /tasks/{id}
api.deleteTask(taskId)                          // DELETE /tasks/{id}
api.moveTask(taskId, newStatus)                 // PATCH /tasks/{id}/status

// Social Calendar
api.listScheduledPosts(orgId, dateRange)        // GET /scheduled-posts
api.createScheduledPost(data)                   // POST /scheduled-posts
api.updateScheduledPost(postId, data)           // PUT /scheduled-posts/{id}
api.deleteScheduledPost(postId)                 // DELETE /scheduled-posts/{id}
api.publishPost(postId)                         // POST /scheduled-posts/{id}/publish

// Deliverables
api.listDeliverables(campaignId)                // GET /deliverables
api.getDeliverable(deliverableId)               // GET /deliverables/{id}
api.createDeliverable(data)                     // POST /deliverables
api.updateDeliverable(deliverableId, data)      // PUT /deliverables/{id}
api.deleteDeliverable(deliverableId)            // DELETE /deliverables/{id}
api.refineContent(text, action, type)           // POST /content/refine

// Image Editor
api.uploadImage(file)                           // POST /images/upload
api.editImage(imageId, prompt)                  // POST /images/{id}/edit
api.getImageHistory(imageId)                    // GET /images/{id}/history
api.exportImage(imageId, format)                // GET /images/{id}/export
```

---

## Backend Files - Current vs Needed

### Current Backend Structure:
```
/backend/app/
├── api/
│   ├── assets.py         # ✅ Asset CRUD
│   ├── campaigns.py      # ✅ Campaign CRUD + execute
│   ├── chat.py           # ✅ Conversations + messages
│   ├── kata.py           # ✅ Kata Lab endpoints
│   ├── onboarding.py     # ✅ Brand analysis
│   ├── orchestrator.py   # ✅ Campaign orchestration
│   └── organizations.py  # ✅ Org management
│
├── models/
│   ├── asset.py          # ✅ Asset model
│   ├── campaign.py       # ✅ Campaign model
│   ├── conversation.py   # ✅ Conversation + Message models
│   ├── knowledge_base.py # ✅ BrandProfile model
│   └── user.py           # ✅ User model
│
├── services/
│   ├── ai/
│   │   └── openrouter.py # ✅ OpenRouter integration
│   └── kata/             # ✅ Kata Lab services
│
└── main.py               # ✅ FastAPI app
```

### Needed Backend Files:
```
/backend/app/
├── api/
│   ├── trends.py         # ❌ NEED TO CREATE - TrendMaster endpoints
│   ├── tasks.py          # ❌ NEED TO CREATE - Kanban endpoints
│   ├── scheduled_posts.py# ❌ NEED TO CREATE - Calendar endpoints
│   ├── deliverables.py   # ❌ NEED TO CREATE - Deliverables endpoints
│   └── images.py         # ❌ NEED TO CREATE - Image editor endpoints
│
├── models/
│   ├── trend.py          # ❌ NEED TO CREATE
│   ├── task.py           # ❌ NEED TO CREATE
│   ├── scheduled_post.py # ❌ NEED TO CREATE
│   ├── deliverable.py    # ❌ NEED TO CREATE
│   └── image_edit.py     # ❌ NEED TO CREATE
│
├── services/
│   ├── trends/
│   │   └── trend_scanner.py  # ❌ NEED TO CREATE - NewsAPI/Perplexity integration
│   ├── images/
│   │   └── image_editor.py   # ❌ NEED TO CREATE - Replicate integration
│   └── publishing/
│       └── social_publisher.py # ❌ NEED TO CREATE - Twitter/LinkedIn APIs
```

---

## Quick Reference: What to Tell KimiK2

### What I (Claude) Built - Phase 2 UI Components:
| Component | File Location | What It Does |
|-----------|--------------|--------------|
| TrendMaster | `/frontend/src/components/trends/TrendMaster.jsx` | Trend display, filtering, create brief button |
| KanbanBoard | `/frontend/src/components/kanban/KanbanBoard.jsx` | Drag-drop columns, task cards |
| SocialCalendar | `/frontend/src/components/calendar/SocialCalendar.jsx` | Month/week/day views, post scheduling |
| ConversationalImageEditor | `/frontend/src/components/image-editor/ConversationalImageEditor.jsx` | Upload, chat interface, quick actions |
| SlidingDeliverablesPanel | `/frontend/src/components/deliverables/SlidingDeliverablesPanel.jsx` | Slide-in panel with deliverable list |
| DocumentEditor | `/frontend/src/components/editor/DocumentEditor.jsx` | Rich text editor with AI menu |

### What KimiK2 Needs to Build - Backend APIs:
| Feature | Backend File Needed | Database Table |
|---------|---------------------|----------------|
| TrendMaster | `/backend/app/api/trends.py` | `trends` |
| Kanban | `/backend/app/api/tasks.py` | `tasks` |
| Calendar | `/backend/app/api/scheduled_posts.py` | `scheduled_posts` |
| Image Editor | `/backend/app/api/images.py` | `image_edits` |
| Deliverables | `/backend/app/api/deliverables.py` | `deliverables` |

### Priority Order:
1. **First:** Verify backend stability (Railway logs, 503 errors)
2. **Second:** Create `tasks.py` + `deliverables.py` (simplest, no external APIs)
3. **Third:** Create `trends.py` (can use existing Perplexity integration)
4. **Fourth:** Create `scheduled_posts.py` + `images.py` (need external APIs)
