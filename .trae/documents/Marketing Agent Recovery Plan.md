# Marketing Agent Recovery & Completion Plan

Based on the analysis of `MARKETING_AGENT_MASTER_PLAN.md`, `MARKETING_AGENT_FIX_PLAN.md`, `Marketing_Agent_Evaluation_Report.md`, and `ARCHITECTURE_STATUS.md`, here is the comprehensive plan to fix the broken system and implement the missing backend infrastructure.

## Phase 1: Emergency Stabilization (Critical - Days 1-2)

**Goal: Fix the "HTTP 503" errors and get the core system online.**

### 1.1 Backend Infrastructure Fix
- **Check Railway deployment logs** to identify the root cause of 503 errors.
- **Verify Environment Variables:** Ensure `OPENROUTER_API_KEY`, `FIRECRAWL_API_KEY`, `PERPLEXITY_API_KEY`, `DATABASE_URL`, and `CORS_ORIGINS` are correctly set.
- **Fix Database Connection:** Update `backend/app/core/database.py` to handle SSL connections correctly for Railway.
- **Add Health Check:** Implement a detailed `/health` endpoint in `backend/app/main.py` to diagnose database and API key status.

### 1.2 Brand Analysis Engine Repair
- **Fix Language Detection:** Modify `backend/app/services/onboarding/firecrawl.py` to force English content (add `Accept-Language` headers).
- **Improve Industry Detection:** Update `backend/app/services/onboarding/perplexity.py` prompts to prevent "Unknown" results.
- **Fix Audience & Offerings:** Update extraction logic to ensure at least 2-3 audiences and products are returned.
- **Validation:** Add validation in `pipeline.py` to ensure empty data is not saved.

### 1.3 AI Chat Functionality Restoration
- **Connection Test:** Add `test_connection()` to `backend/app/services/ai/openrouter.py`.
- **Error Handling:** Update `backend/app/api/chat.py` to handle exceptions gracefully and return user-friendly errors.
- **Fix Streaming:** Ensure SSE headers (`X-Accel-Buffering: no`) are set correctly for streaming responses.

### 1.4 Frontend Error Handling
- **Global Error Boundary:** Create `frontend/src/components/ErrorBoundary.jsx`.
- **Toast Notifications:** Implement `frontend/src/components/Toast.jsx` for API errors.
- **Loading States:** Add loading indicators to Dashboard, Chat, and Campaign creation flows.
- **Fix Brand View:** Ensure `DashboardPage.jsx` correctly renders the brand knowledge base data.

## Phase 2: Core Feature Backend Implementation (Days 3-5)

**Goal: Connect the "UI-Only" features to real backend APIs.**

### 2.1 Kanban Board Backend (`tasks`)
- **Database:** Create `tasks` table (id, campaign_id, title, status, etc.).
- **API:** Create `backend/app/api/tasks.py` with CRUD endpoints.
- **Frontend:** Update `KanbanBoard.jsx` to use `api.listTasks`, `api.createTask`, etc.

### 2.2 Deliverables Panel Backend (`deliverables`)
- **Database:** Create `deliverables` table (id, campaign_id, type, content, etc.).
- **API:** Create `backend/app/api/deliverables.py` with CRUD endpoints.
- **AI Refinement:** Implement `POST /api/content/refine` using OpenRouter for the Document Editor.
- **Frontend:** Update `SlidingDeliverablesPanel.jsx` to fetch real data.

### 2.3 TrendMaster Backend (`trends`)
- **Database:** Create `trends` table.
- **API:** Create `backend/app/api/trends.py`.
- **Service:** Implement `backend/app/services/trends/trend_scanner.py` using Perplexity (since we have the key) to fetch trends if NewsAPI is not available.
- **Frontend:** Connect `TrendMaster.jsx` to the new API.

### 2.4 Social Calendar Backend (`scheduled_posts`)
- **Database:** Create `scheduled_posts` table.
- **API:** Create `backend/app/api/scheduled_posts.py`.
- **Frontend:** Connect `SocialCalendar.jsx` to the API for saving/retrieving posts.
- **Note:** Actual publishing to platforms (Twitter/LinkedIn) will be mocked or logged until API keys are available.

### 2.5 Image Editor Backend (`images`)
- **Database:** Create `image_edits` table.
- **API:** Create `backend/app/api/images.py`.
- **Service:** Stub out `backend/app/services/images/image_editor.py`. If Replicate key is missing, mock the response or use a placeholder generation.

## Phase 3: Integration & Polish (Week 2)

**Goal: Ensure all parts work together and the system is stable.**

### 3.1 Campaign Execution Fixes
- **WebSocket:** Debug and fix `POST /api/campaigns/{id}/execute` to ensure real-time updates work.
- **Asset Generation:** Verify that campaign execution actually creates entries in the `assets` table.

### 3.2 End-to-End Testing
- **Onboarding:** Test full flow from URL to Knowledge Base.
- **Campaigns:** Test creation, execution, and asset generation.
- **Chat:** Test multi-turn conversations.
- **New Features:** Test Kanban, Trends, and Calendar persistence.

### 3.3 UI Polish
- **Design System:** Apply the "Enterprise Cloud Desktop" aesthetic (remove purple gradients).
- **Feedback:** Ensure all actions have success/error feedback (toasts).

## Success Criteria
- [ ] `/health` returns 200 OK.
- [ ] Brand analysis correctly identifies Stripe as Fintech.
- [ ] Chat responds to user messages.
- [ ] Campaign creation works and generates assets.
- [ ] Kanban board persists tasks to the database.
- [ ] TrendMaster shows trends from the API.
- [ ] No "silent failures" in the UI.

## Immediate Next Step
Start with **Phase 1.1: Backend Infrastructure Fix** to get the server healthy.
