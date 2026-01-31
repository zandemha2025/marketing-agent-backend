# V3 Product Map: UI/UX, Flows & Routes

## Navigation Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  SIDEBAR                           MAIN CONTENT                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🏠 Dashboard                      [Current Page Content]        │
│                                                                  │
│  📊 Campaigns                                                    │
│     └─ All Campaigns                                             │
│     └─ Create New                                                │
│                                                                  │
│  🎨 Content Studio                                               │
│     └─ Assets Library                                            │
│     └─ Quick Create                                              │
│     └─ Kata Lab (NEW)                                            │
│                                                                  │
│  📤 Publishing (NEW)                                             │
│     └─ Queue                                                     │
│     └─ Calendar                                                  │
│     └─ Connected Accounts                                        │
│                                                                  │
│  📈 Analytics (NEW)                                              │
│     └─ Overview                                                  │
│     └─ By Campaign                                               │
│     └─ By Platform                                               │
│                                                                  │
│  🔥 Trends (NEW)                                                 │
│     └─ Trending Now                                              │
│     └─ Alerts                                                    │
│                                                                  │
│  👤 Influencers (NEW)                                            │
│     └─ Synthetic Profiles                                        │
│     └─ Create New                                                │
│                                                                  │
│  ⚙️ Settings                                                     │
│     └─ Brand & Knowledge                                         │
│     └─ Team                                                      │
│     └─ Integrations                                              │
│     └─ Billing                                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Routes Map

```
/                           → Redirect to /dashboard
/onboarding                 → New user onboarding flow
/onboarding/domain          → Enter company domain
/onboarding/research        → Watch AI research (progress)
/onboarding/review          → Review & refine brand profile

/dashboard                  → Main dashboard (overview)

/campaigns                  → Campaign list
/campaigns/new              → Create campaign wizard
/campaigns/:id              → Campaign detail view
/campaigns/:id/brief        → View/edit brief
/campaigns/:id/concepts     → View/select concepts
/campaigns/:id/assets       → Asset gallery for campaign
/campaigns/:id/publish      → Publish campaign assets

/studio                     → Content studio home
/studio/assets              → All assets library
/studio/create              → Quick create (single asset)
/studio/kata                → Kata Lab (compositing)
/studio/kata/new            → New compositing job
/studio/kata/:id            → Compositing job detail

/publish                    → Publishing dashboard
/publish/queue              → Scheduled posts queue
/publish/calendar           → Calendar view
/publish/accounts           → Connected social accounts
/publish/newsroom           → Newsroom page builder (NEW)

/analytics                  → Analytics overview
/analytics/campaigns/:id    → Campaign performance
/analytics/platforms        → By platform breakdown

/trends                     → Trend dashboard
/trends/alerts              → Trend alert settings

/influencers                → Synthetic influencer profiles
/influencers/new            → Create new influencer
/influencers/:id            → Influencer profile
/influencers/:id/generate   → Generate content as influencer

/settings                   → Settings home
/settings/brand             → Brand & knowledge base
/settings/team              → Team management
/settings/integrations      → Connected apps
/settings/billing           → Subscription & billing
```

---

## Key User Flows

### Flow 1: New User Onboarding
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Landing   │───▶│   Enter     │───▶│   Watch     │───▶│   Review    │
│    Page     │    │   Domain    │    │   Research  │    │   Profile   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                            │                    │
                   "Enter your              │ Real-time          │ Edit/approve
                    company URL"            │ progress           │ brand details
                                            │ animation          │
                                            ▼                    ▼
                                      ┌─────────────┐    ┌─────────────┐
                                      │  AI crawls  │    │  Dashboard  │
                                      │  & analyzes │    │   (done!)   │
                                      └─────────────┘    └─────────────┘
```

**Screens needed:**
- `/onboarding` - Welcome + domain input
- `/onboarding/research` - Progress visualization (crawling, analyzing, etc.)
- `/onboarding/review` - Brand profile review/edit form

---

### Flow 2: Campaign Creation
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Campaign   │───▶│   Define    │───▶│   Watch     │───▶│   Review    │
│    List     │    │  Objective  │    │   Brief     │    │   Brief     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                                       │
      │ Click            │ "What's the goal?"                   │ Approve or
      │ "New Campaign"   │ "Who's the audience?"                │ request changes
      │                  │ "Which platforms?"                    │
      ▼                  ▼                                       ▼
                   ┌─────────────┐                        ┌─────────────┐
                   │  Quick form │                        │   Select    │
                   │  or chat    │                        │   Concept   │
                   └─────────────┘                        └─────────────┘
                                                                 │
                                                                 │ Pick from
                                                                 │ 3 concepts
                                                                 ▼
                                                         ┌─────────────┐
                                                         │   Asset     │
                                                         │ Generation  │
                                                         └─────────────┘
                                                                 │
                                                                 ▼
                                                         ┌─────────────┐
                                                         │   Review    │
                                                         │   Assets    │
                                                         └─────────────┘
                                                                 │
                                                                 ▼
                                                         ┌─────────────┐
                                                         │   Publish   │
                                                         └─────────────┘
```

**Screens needed:**
- `/campaigns` - List view with filters, search
- `/campaigns/new` - Multi-step wizard OR chat-based creation
- `/campaigns/:id` - Overview with tabs (Brief, Concepts, Assets)
- `/campaigns/:id/brief` - Full brief view with edit capability
- `/campaigns/:id/concepts` - Concept cards with selection
- `/campaigns/:id/assets` - Asset gallery with regenerate options
- `/campaigns/:id/publish` - Select assets → schedule → publish

---

### Flow 3: Kata Lab (Product Compositing)
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Kata Lab   │───▶│   Upload    │───▶│   Select    │───▶│   Preview   │
│    Home     │    │   Video     │    │   Product   │    │   Zones     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                                                          │
      │ "New Compositing                                         │ AI shows
      │  Job"                                                    │ placement
      │                                                          │ options
      ▼                                                          ▼
┌─────────────┐                                          ┌─────────────┐
│  OR: Choose │                                          │   Adjust    │
│  from       │                                          │   Settings  │
│  generated  │                                          │  (position, │
│  video      │                                          │   shadow)   │
└─────────────┘                                          └─────────────┘
                                                                 │
                                                                 ▼
                                                         ┌─────────────┐
                                                         │  Generate   │
                                                         │  Composite  │
                                                         └─────────────┘
                                                                 │
                                                                 ▼
                                                         ┌─────────────┐
                                                         │   Review    │
                                                         │  & Export   │
                                                         └─────────────┘
```

**Screens needed:**
- `/studio/kata` - Kata Lab home (recent jobs, templates)
- `/studio/kata/new` - New job wizard
  - Step 1: Source selection (upload video / use generated / stock)
  - Step 2: Product selection (upload product image / from brand assets)
  - Step 3: Zone preview (AI shows where it can place)
  - Step 4: Settings (lighting match, shadow intensity, etc.)
- `/studio/kata/:id` - Job detail (progress, result, regenerate)

---

### Flow 4: Synthetic Influencer Creation
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Influencer  │───▶│   Define    │───▶│   Generate  │───▶│   Review    │
│    List     │    │   Persona   │    │   Avatar    │    │   Profile   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                                       │
      │ "Create          │ Name, age, style,                    │ Approve or
      │  Influencer"     │ personality, niche                   │ regenerate
      │                  │ voice selection                       │
      ▼                  ▼                                       ▼
                   ┌─────────────┐                        ┌─────────────┐
                   │   Persona   │                        │  Generate   │
                   │    Form     │                        │   Content   │
                   └─────────────┘                        └─────────────┘
                                                                 │
                                                                 │ Create posts
                                                                 │ as this
                                                                 │ influencer
                                                                 ▼
                                                         ┌─────────────┐
                                                         │   Content   │
                                                         │   Gallery   │
                                                         └─────────────┘
```

**Screens needed:**
- `/influencers` - List of synthetic influencer profiles
- `/influencers/new` - Create influencer wizard
  - Persona definition (demographics, style, voice)
  - Avatar generation (AI-generated face/look)
  - Voice selection (ElevenLabs voice match)
- `/influencers/:id` - Profile detail
- `/influencers/:id/generate` - Generate content as this influencer

---

### Flow 5: Publishing
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Asset     │───▶│   Select    │───▶│   Preview   │───▶│  Schedule   │
│  (anywhere) │    │  Platforms  │    │   Per       │    │    or       │
│             │    │             │    │  Platform   │    │  Publish    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                    │
      │ "Publish"        │ LinkedIn ✓       │ Auto-adapted       │ Pick time
      │  button          │ Twitter ✓        │ for each           │ or "Now"
      │                  │ Instagram ✓      │ platform           │
      ▼                  ▼                  ▼                    ▼
                                                         ┌─────────────┐
                                                         │   Queue     │
                                                         │   View      │
                                                         └─────────────┘
```

**Screens needed:**
- Publish modal (triggered from any asset)
- `/publish/queue` - Scheduled posts with edit/cancel
- `/publish/calendar` - Calendar view of scheduled content
- `/publish/accounts` - Connect/manage social accounts (OAuth flows)

---

## Page Layouts

### Dashboard (`/dashboard`)
```
┌────────────────────────────────────────────────────────────────────┐
│  Good morning, Nazeem                                    [+ New]   │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  Active         │  │  Scheduled      │  │  This Week      │    │
│  │  Campaigns: 3   │  │  Posts: 12      │  │  Published: 28  │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                     │
│  Recent Campaigns                                    [View All →]   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Campaign Card │ Campaign Card │ Campaign Card │             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Trending Now 🔥                                      [View All →]   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ #trend1  │ #trend2  │ Sound: xyz │ Format: carousel         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Quick Actions                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ New      │ │ Quick    │ │ Kata     │ │ View     │             │
│  │ Campaign │ │ Post     │ │ Lab      │ │ Calendar │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Campaign Detail (`/campaigns/:id`)
```
┌────────────────────────────────────────────────────────────────────┐
│  ← Back    Summer Product Launch                      [Publish ▼]  │
├────────────────────────────────────────────────────────────────────┤
│  [Overview] [Brief] [Concepts] [Assets] [Analytics]                │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Status: Assets Ready                    Created: Jan 15, 2026     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Selected Concept: "Summer Vibes"                           │   │
│  │  ─────────────────────────────────────────                  │   │
│  │  Tagline: "Refresh Your Day"                                │   │
│  │  Platforms: Instagram, TikTok, LinkedIn                     │   │
│  │                                                              │   │
│  │  [View Brief] [Change Concept] [Regenerate Assets]          │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Assets (12)                                           [+ Add]     │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │
│  │  IMG   │ │  IMG   │ │  VID   │ │  VID   │ │  COPY  │          │
│  │  IG    │ │  LI    │ │  Reel  │ │  TikTok│ │  Post  │          │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘          │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Kata Lab (`/studio/kata`)
```
┌────────────────────────────────────────────────────────────────────┐
│  🧪 Kata Lab                                    [+ New Composite]  │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  What is Kata Lab?                                                 │
│  AI-powered product placement. Insert your products into any       │
│  video content naturally - matching lighting, depth, and shadows.  │
│                                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                 │
│  │                     │  │                     │                 │
│  │  📹 Composite       │  │  👤 Synthetic       │                 │
│  │     Video           │  │     Influencer      │                 │
│  │                     │  │                     │                 │
│  │  Insert product     │  │  Generate UGC-style │                 │
│  │  into existing      │  │  content with your  │                 │
│  │  video              │  │  product placed     │                 │
│  │                     │  │                     │                 │
│  └─────────────────────┘  └─────────────────────┘                 │
│                                                                     │
│  Recent Jobs                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Job 1 - Complete │ Job 2 - Processing │ Job 3 - Complete   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Publishing Calendar (`/publish/calendar`)
```
┌────────────────────────────────────────────────────────────────────┐
│  📅 Publishing Calendar               [← Jan 2026 →]    [+ New]   │
├────────────────────────────────────────────────────────────────────┤
│  [Month] [Week] [Day]                    Filter: [All Platforms ▼] │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  MON     TUE     WED     THU     FRI     SAT     SUN              │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │
│  │     │ │ 🔵  │ │ 🔵  │ │     │ │ 🔵  │ │     │ │     │         │
│  │ 27  │ │ 28  │ │ 29  │ │ 30  │ │ 31  │ │ 1   │ │ 2   │         │
│  │     │ │ 🟣  │ │     │ │ 🟢  │ │     │ │     │ │     │         │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘         │
│                                                                     │
│  🔵 LinkedIn  🟣 Instagram  🟢 Twitter  🔴 TikTok                  │
│                                                                     │
│  Upcoming                                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 9:00 AM  │ LinkedIn │ Summer campaign post 1    │ [Edit]   │   │
│  │ 12:00 PM │ Twitter  │ Product announcement      │ [Edit]   │   │
│  │ 3:00 PM  │ Instagram│ Behind the scenes reel    │ [Edit]   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Library Needed

### Core Components
- `Sidebar` - Main navigation
- `Header` - Page header with actions
- `Card` - Content container
- `Button` - Primary, secondary, ghost variants
- `Modal` - Dialogs and wizards
- `Tabs` - Tab navigation
- `Form` - Input, select, textarea, etc.

### Domain Components
- `CampaignCard` - Campaign preview card
- `AssetCard` - Asset preview (image, video, copy)
- `BriefView` - Formatted brief display
- `ConceptCard` - Creative concept card with selection
- `TrendBadge` - Trending topic indicator
- `PlatformIcon` - Social platform icons
- `ProgressRing` - Circular progress indicator
- `PublishModal` - Multi-platform publish flow
- `CalendarView` - Publishing calendar
- `InfluencerCard` - Synthetic influencer profile

### Kata-Specific Components
- `VideoPlayer` - Video preview with zone overlay
- `ZoneSelector` - Select/adjust placement zones
- `CompositePreview` - Before/after comparison
- `SettingsPanel` - Compositing settings (shadow, lighting)

---

## Tech Stack (Frontend)

**Current v2:**
- React + Vite
- Convex (real-time)

**Recommended additions:**
- Tailwind CSS (utility-first styling)
- Framer Motion (animations)
- React Query (data fetching)
- Zustand or Jotai (state management)
- React Hook Form (forms)
- date-fns (date handling)
- react-big-calendar (calendar view)

---

## API Requirements by Screen

| Screen | API Endpoints Needed |
|--------|---------------------|
| Dashboard | `GET /campaigns`, `GET /trends`, `GET /publish/upcoming` |
| Campaign List | `GET /campaigns`, `POST /campaigns` |
| Campaign Detail | `GET /campaigns/:id`, `PUT /campaigns/:id` |
| Campaign Brief | `GET /campaigns/:id/brief`, `PUT /campaigns/:id/brief` |
| Campaign Concepts | `GET /campaigns/:id/concepts`, `POST /campaigns/:id/select-concept` |
| Campaign Assets | `GET /campaigns/:id/assets`, `POST /campaigns/:id/regenerate-asset` |
| Kata Lab | `GET /kata/jobs`, `POST /kata/analyze`, `POST /kata/composite` |
| Publishing Queue | `GET /publish/queue`, `DELETE /publish/:id` |
| Calendar | `GET /publish/calendar?month=` |
| Accounts | `GET /accounts`, `POST /accounts/connect`, `DELETE /accounts/:id` |
| Trends | `GET /trends`, `GET /trends/:platform` |
| Influencers | `GET /influencers`, `POST /influencers`, `POST /influencers/:id/generate` |

---

## Priority Order for Building

### Phase 1: Core Flow (Weeks 1-2)
1. ✅ Dashboard (basic)
2. ✅ Campaign list + detail
3. 🔲 Asset gallery with publish button
4. 🔲 Publish modal (platform selection → schedule)
5. 🔲 Publishing queue

### Phase 2: Kata Lab (Weeks 3-4)
1. 🔲 Kata Lab home
2. 🔲 New composite wizard
3. 🔲 Zone preview/selection
4. 🔲 Composite generation + review

### Phase 3: Distribution (Weeks 5-6)
1. 🔲 Calendar view
2. 🔲 Account connection (OAuth)
3. 🔲 Newsroom builder (basic)

### Phase 4: Intelligence (Weeks 7-8)
1. 🔲 Trends dashboard
2. 🔲 Analytics overview
3. 🔲 Synthetic influencers

