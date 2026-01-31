# Frontend Agent Briefing Document

## Your Mission

You are rebuilding the frontend UI for a premium B2B marketing platform priced at **$10,000 - $30,000/month**. The current UI looks rushed and unprofessional. Your job is to make it look like it was designed by a world-class design team.

---

## Working Directory

**Work from:** `frontend/`

All your work happens here:
```
frontend/
├── src/
│   ├── components/    ← React components to update
│   ├── pages/         ← Page-level components
│   └── styles/        ← Global styles (if present)
├── package.json
└── vite.config.js
```

**DO NOT touch:** `backend/` - Another agent is handling that.

---

## Your Bible: The Design Specification

Read this file completely before writing ANY code:

**`DESIGN_SYSTEM_SPECIFICATION.md`** (in project root)

This 1,500+ line document contains:
- Every color, spacing, typography value
- Every component spec with exact dimensions
- Every screen layout pixel-by-pixel
- Every animation timing
- Every icon mapping

**Follow it exactly. No improvisation.**

---

## The Core Problems You're Fixing

### Problem 1: Emojis Everywhere (Makes it Look Amateur)

The app uses emojis instead of professional icons:
- Navigation: 💬📋📈📊📅🔥📦🎨🏢🎯✍️
- Quick actions: 🚀✍️🎭📱
- Cards and badges: 📝🎬📧🖼️

**Fix:** Replace ALL emojis with Lucide React icons. The design spec has the complete mapping.

```jsx
// WRONG (current)
{ icon: '💬', label: 'Chat' }

// RIGHT (what you'll do)
import { MessageSquare } from 'lucide-react';
{ icon: <MessageSquare size={20} />, label: 'Chat' }
```

### Problem 2: Cramped Spacing (No Breathing Room)

Everything is squished together:
- Gaps of 4px where there should be 8-12px
- Padding of 2px where there should be 8-16px
- Items stacked too close

**Fix:** Update all spacing to match the design spec tokens.

```css
/* WRONG (current) */
.element { padding: 2px 8px; gap: 4px; }

/* RIGHT (what you'll do) */
.element { padding: 8px 16px; gap: 12px; }
```

### Problem 3: Hard-coded Colors (Broken Dark Mode)

Some components use hard-coded colors like `#222`, `#888` instead of design tokens.

**Fix:** Replace with CSS variables from the design spec.

```css
/* WRONG */
color: #888;
background: #222;

/* RIGHT */
color: var(--text-secondary);
background: var(--bg-surface-1);
```

### Problem 4: Login/Signup Looks Basic

Current auth pages are just forms on a gradient. For $10K-$30K/month, they need:
- Proper branding
- Social proof elements
- Premium feel
- Polished animations

---

## Files That Need the Most Work

### Priority 1: Critical (Do These First)

| File | Issues |
|------|--------|
| `src/pages/DashboardPage.jsx` | Emojis in nav (lines 24-34), quick actions (396-409) |
| `src/pages/DashboardPage.css` | Cramped nav spacing (line 39: `gap: spacing-xs`) |
| `src/components/deliverables/cards/DeliverableCards.css` | 8 spacing issues, hard-coded colors |
| `src/components/chat/ChatPanel.css` | Cramped padding throughout |

### Priority 2: High Impact

| File | Issues |
|------|--------|
| `src/pages/LoginPage.jsx` & `.css` | Complete redesign needed |
| `src/components/kanban/KanbanBoard.css` | Cramped task cards |
| `src/components/shared/AssetCard.jsx` | Emojis in type mapping |

### Priority 3: Polish

| File | Issues |
|------|--------|
| `src/pages/TrendMaster.jsx` & `.css` | Emojis, undefined CSS variables |
| `src/pages/CalendarPage.css` | Small gaps (4px) |
| `src/components/image-editor/ConversationalImageEditor.jsx` | Emojis |

---

## Icon Mapping Reference (Quick Reference)

Install Lucide if not present:
```bash
npm install lucide-react
```

| Feature | Emoji to Remove | Lucide Icon |
|---------|-----------------|-------------|
| Chat | 💬 | `MessageSquare` |
| Campaigns | 📋 | `Megaphone` |
| Analytics | 📈 | `BarChart3` |
| Workflow | 📊 | `GitBranch` |
| Calendar | 📅 | `Calendar` |
| Trends | 🔥 | `TrendingUp` |
| Assets | 📦 | `FolderOpen` |
| Image Editor | 🎨 | `ImagePlus` |
| Brand | 🏢 | `Building2` |
| Kanban | 🎯 | `LayoutGrid` |
| Writer | ✍️ | `PenTool` |
| Launch/Rocket | 🚀 | `Rocket` |
| AI/Magic | ✨ | `Sparkles` |
| User | 👤 | `User` |
| Video | 🎬 | `Video` |
| Email | 📧 | `Mail` |
| Blog/Post | 📝 | `FileText` |
| Image | 🖼️ | `Image` |
| Social | 📱 | `Share2` |
| Ad | 📢 | `Megaphone` |
| Globe/Web | 🌐 | `Globe` |

Full mapping is in the design spec.

---

## Spacing Quick Reference

| Token | Value | Use For |
|-------|-------|---------|
| `--space-1` | 4px | Tight internal only |
| `--space-2` | 8px | Default gaps |
| `--space-3` | 12px | Comfortable gaps |
| `--space-4` | 16px | Section padding |
| `--space-5` | 20px | Card padding |
| `--space-6` | 24px | Section gaps |

**Rule of thumb:** If current value is 4px, change to 8px. If 2px, change to 6-8px.

---

## Color Quick Reference (Dark Mode)

| Variable | Hex | Use For |
|----------|-----|---------|
| `--bg-base` | #0a0a0f | Page background |
| `--bg-surface-1` | #12121a | Cards, panels |
| `--bg-surface-2` | #1a1a24 | Elevated elements |
| `--bg-hover` | #2a2a36 | Hover states |
| `--text-primary` | #ffffff | Main text |
| `--text-secondary` | #a1a1aa | Secondary text |
| `--text-tertiary` | #71717a | Placeholders |
| `--brand-500` | #f97316 | Primary orange |
| `--border-subtle` | #27272a | Light borders |
| `--border-default` | #3f3f46 | Standard borders |

---

## What Success Looks Like

When you're done:

1. **Zero emojis** in the entire frontend
2. **No cramped spacing** - everything breathes
3. **Login/Signup** looks like a premium SaaS product
4. **Consistent design tokens** - no hard-coded colors
5. **Dark mode works** everywhere
6. **Navigation feels professional** - proper icons, proper spacing

---

## How to Verify Your Work

After making changes:

1. Run the dev server: `npm run dev`
2. Check every screen visually
3. Test dark mode
4. Verify hover states work
5. Check mobile responsiveness (resize browser)

---

## Do NOT Do These Things

- ❌ Don't touch `backend/` folder
- ❌ Don't change API calls or endpoints
- ❌ Don't modify data structures
- ❌ Don't add new features
- ❌ Don't improvise on the design spec
- ❌ Don't use any emojis (even if "just one would be nice")

---

## Getting Started Checklist

1. [ ] Read `DESIGN_SYSTEM_SPECIFICATION.md` completely
2. [ ] Install Lucide: `npm install lucide-react`
3. [ ] Start with `DashboardPage.jsx` - replace nav emojis
4. [ ] Fix `DashboardPage.css` - increase nav spacing
5. [ ] Work through Priority 1 files
6. [ ] Then Priority 2, then Priority 3
7. [ ] Test everything visually

---

## Questions?

If something in the design spec is unclear, make the choice that looks most premium and professional. When in doubt:
- More spacing, not less
- Subtle, not flashy
- Consistent, not creative

This is enterprise software for serious marketing teams, not a consumer app.

---

**Good luck. Make it beautiful.**
