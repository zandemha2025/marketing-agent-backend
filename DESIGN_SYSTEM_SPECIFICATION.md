# Marketing Agent Platform - Complete Design Specification

**Version:** 2.0
**Last Updated:** January 31, 2026
**Target Price Point:** $10,000 - $30,000/month Enterprise SaaS

---

## PART 1: INTRODUCTION & VISION

### What This Document Is

This is the definitive design specification for the Marketing Agent Platform. Any developer, designer, or AI agent should be able to build this interface pixel-perfect using only this document. Nothing is left to interpretation.

### Product Vision

An AI-powered marketing command center that feels like having an entire creative agency at your fingertips. The interface should feel:

- **Powerful but not overwhelming** - Like a professional recording studio, not a toy
- **Intelligent** - The AI should feel present but not intrusive
- **Premium** - Every pixel should justify the $10K-$30K/month price tag
- **Dark and focused** - Designed for long working sessions, easy on the eyes

### Design Inspiration

The primary inspiration is **Claude Code Desktop** - a professional AI tool that:
- Uses deep dark backgrounds with subtle gradients
- Features coral/orange accent colors for brand identity
- Employs sliding panels that emerge smoothly from edges
- Shows minimal chrome - content IS the interface
- Uses Lucide icons (NEVER emojis)
- Has a command palette (Cmd+K) for power users

---

## PART 2: DESIGN PRINCIPLES

### Principle 1: Breathing Room
Every element needs space to exist. Minimum gaps of 8px between related items, 16px between unrelated items. Padding inside interactive elements minimum 8px vertical, 12px horizontal.

**Wrong:** `padding: 2px 8px; gap: 4px;`
**Right:** `padding: 8px 16px; gap: 12px;`

### Principle 2: No Emojis, Ever
Emojis are for chat apps and social media. This is enterprise software. Use Lucide React icons exclusively.

**Wrong:** 💬 Chat, 📊 Analytics, 🚀 Launch
**Right:** `<MessageSquare />` Chat, `<BarChart3 />` Analytics, `<Rocket />` Launch

### Principle 3: Hierarchy Through Subtle Contrast
Don't use borders to separate things. Use background color shifts. Each level deeper gets slightly lighter (in dark mode) or darker (in light mode).

**Surface levels (dark mode):**
- Level 0 (background): `#0a0a0f`
- Level 1 (cards): `#12121a`
- Level 2 (elevated): `#1a1a24`
- Level 3 (floating): `#22222e`

### Principle 4: Motion With Purpose
Every animation must serve a purpose. Entrance animations guide attention. Exit animations provide closure. Loading animations indicate progress.

**Timing:**
- Instant feedback (hover): 100ms
- Quick transitions (buttons): 150ms
- Standard transitions (panels): 250ms
- Elaborate transitions (modals): 350ms

### Principle 5: Consistent Interactive States
Every clickable element has exactly 5 states:
1. Default
2. Hover
3. Active (pressed)
4. Focused (keyboard)
5. Disabled

---

## PART 3: DESIGN TOKENS

### 3.1 Colors

#### Brand Colors
```
Primary Orange (Brand):
  --brand-500: #f97316    /* Main brand color */
  --brand-400: #fb923c    /* Lighter variant */
  --brand-600: #ea580c    /* Darker variant */
  --brand-gradient: linear-gradient(135deg, #f97316 0%, #ea580c 100%)
```

#### Neutral Colors (Dark Mode - DEFAULT)
```
Backgrounds:
  --bg-base: #0a0a0f        /* Deepest background */
  --bg-surface-1: #12121a   /* Cards, panels */
  --bg-surface-2: #1a1a24   /* Elevated elements */
  --bg-surface-3: #22222e   /* Floating elements, dropdowns */
  --bg-hover: #2a2a36       /* Hover state backgrounds */
  --bg-active: #32323e      /* Active/pressed backgrounds */

Text:
  --text-primary: #ffffff     /* Main text - 100% white */
  --text-secondary: #a1a1aa   /* Secondary text - gray-400 */
  --text-tertiary: #71717a    /* Placeholder, disabled - gray-500 */
  --text-muted: #52525b       /* Very subtle text - gray-600 */

Borders:
  --border-subtle: #27272a    /* Barely visible borders */
  --border-default: #3f3f46   /* Standard borders */
  --border-strong: #52525b    /* Emphasized borders */
```

#### Semantic Colors
```
Success:
  --success-bg: rgba(34, 197, 94, 0.1)
  --success-border: rgba(34, 197, 94, 0.3)
  --success-text: #22c55e

Warning:
  --warning-bg: rgba(234, 179, 8, 0.1)
  --warning-border: rgba(234, 179, 8, 0.3)
  --warning-text: #eab308

Error:
  --error-bg: rgba(239, 68, 68, 0.1)
  --error-border: rgba(239, 68, 68, 0.3)
  --error-text: #ef4444

Info:
  --info-bg: rgba(59, 130, 246, 0.1)
  --info-border: rgba(59, 130, 246, 0.3)
  --info-text: #3b82f6
```

#### Platform Colors (Social Media)
```
  --twitter: #1da1f2
  --linkedin: #0a66c2
  --instagram: #e4405f
  --facebook: #1877f2
  --tiktok: #000000
  --youtube: #ff0000
```

### 3.2 Typography

#### Font Families
```
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
--font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace
```

#### Font Sizes
```
--text-xs: 11px      /* Labels, badges, timestamps */
--text-sm: 13px      /* Secondary text, captions */
--text-base: 15px    /* Body text, inputs */
--text-lg: 17px      /* Emphasized body */
--text-xl: 20px      /* Section headers */
--text-2xl: 24px     /* Page titles */
--text-3xl: 30px     /* Hero text */
--text-4xl: 36px     /* Display text */
```

#### Font Weights
```
--font-normal: 400   /* Body text */
--font-medium: 500   /* Labels, buttons */
--font-semibold: 600 /* Headers, emphasis */
--font-bold: 700     /* Strong emphasis only */
```

#### Line Heights
```
--leading-tight: 1.25    /* Headings */
--leading-normal: 1.5    /* Body text */
--leading-relaxed: 1.75  /* Long-form content */
```

### 3.3 Spacing Scale

All spacing uses a 4px base unit. Use these tokens, never arbitrary values.

```
--space-0: 0px
--space-1: 4px      /* Tight internal spacing */
--space-2: 8px      /* Default internal spacing */
--space-3: 12px     /* Comfortable internal spacing */
--space-4: 16px     /* Section internal padding */
--space-5: 20px     /* Card padding */
--space-6: 24px     /* Section gaps */
--space-8: 32px     /* Major section gaps */
--space-10: 40px    /* Page section gaps */
--space-12: 48px    /* Large gaps */
--space-16: 64px    /* Hero spacing */
--space-20: 80px    /* Page margins */
```

### 3.4 Border Radius

```
--radius-none: 0px
--radius-sm: 4px      /* Small badges, tags */
--radius-md: 6px      /* Buttons, inputs */
--radius-lg: 8px      /* Cards, panels */
--radius-xl: 12px     /* Modals, large cards */
--radius-2xl: 16px    /* Feature cards */
--radius-full: 9999px /* Pills, avatars */
```

### 3.5 Shadows

Shadows in dark mode are subtle glows, not drops.

```
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3)
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.4)
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.5)
--shadow-xl: 0 20px 25px rgba(0, 0, 0, 0.6)

/* Glow effects for emphasis */
--glow-brand: 0 0 20px rgba(249, 115, 22, 0.3)
--glow-success: 0 0 20px rgba(34, 197, 94, 0.3)
--glow-error: 0 0 20px rgba(239, 68, 68, 0.3)
```

### 3.6 Z-Index Scale

```
--z-base: 0
--z-dropdown: 100
--z-sticky: 200
--z-drawer: 300
--z-modal: 400
--z-toast: 500
--z-tooltip: 600
```

### 3.7 Transitions

```
/* Timing */
--duration-instant: 50ms
--duration-fast: 150ms
--duration-normal: 250ms
--duration-slow: 350ms

/* Easing */
--ease-default: cubic-bezier(0.4, 0, 0.2, 1)
--ease-in: cubic-bezier(0.4, 0, 1, 1)
--ease-out: cubic-bezier(0, 0, 0.2, 1)
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1)
```

---

## PART 4: ICON SYSTEM

### Icon Library: Lucide React

Every icon in the application MUST come from Lucide React. No exceptions. No emojis.

### Icon Sizes
```
--icon-xs: 14px    /* Inside small badges */
--icon-sm: 16px    /* Inline with text, buttons */
--icon-md: 20px    /* Navigation, standard use */
--icon-lg: 24px    /* Feature icons, headers */
--icon-xl: 32px    /* Empty states, heroes */
--icon-2xl: 48px   /* Onboarding, major features */
```

### Navigation Icons Mapping

| Feature | Icon Name | Lucide Component |
|---------|-----------|------------------|
| Chat | MessageSquare | `<MessageSquare />` |
| Campaigns | Megaphone | `<Megaphone />` |
| Analytics | BarChart3 | `<BarChart3 />` |
| Workflow | GitBranch | `<GitBranch />` |
| Calendar | Calendar | `<Calendar />` |
| Trends | TrendingUp | `<TrendingUp />` |
| Assets | FolderOpen | `<FolderOpen />` |
| Image Editor | ImagePlus | `<ImagePlus />` |
| Brand | Building2 | `<Building2 />` |
| Kanban | LayoutGrid | `<LayoutGrid />` |
| Writer | PenTool | `<PenTool />` |
| Settings | Settings | `<Settings />` |
| User Profile | User | `<User />` |
| Logout | LogOut | `<LogOut />` |
| Search | Search | `<Search />` |
| Add/Create | Plus | `<Plus />` |
| Close | X | `<X />` |
| Menu | Menu | `<Menu />` |
| More Options | MoreVertical | `<MoreVertical />` |
| Edit | Pencil | `<Pencil />` |
| Delete | Trash2 | `<Trash2 />` |
| Copy | Copy | `<Copy />` |
| Download | Download | `<Download />` |
| Upload | Upload | `<Upload />` |
| Refresh | RefreshCw | `<RefreshCw />` |
| Check/Success | Check | `<Check />` |
| Warning | AlertTriangle | `<AlertTriangle />` |
| Error | AlertCircle | `<AlertCircle />` |
| Info | Info | `<Info />` |
| Expand | ChevronDown | `<ChevronDown />` |
| Collapse | ChevronUp | `<ChevronUp />` |
| Next | ChevronRight | `<ChevronRight />` |
| Previous | ChevronLeft | `<ChevronLeft />` |
| External Link | ExternalLink | `<ExternalLink />` |
| Send | Send | `<Send />` |
| Attach | Paperclip | `<Paperclip />` |
| Play | Play | `<Play />` |
| Pause | Pause | `<Pause />` |
| Video | Video | `<Video />` |
| Image | Image | `<Image />` |
| File | FileText | `<FileText />` |
| Link | Link | `<Link />` |
| Lock | Lock | `<Lock />` |
| Unlock | Unlock | `<Unlock />` |
| Eye (View) | Eye | `<Eye />` |
| Eye Off (Hide) | EyeOff | `<EyeOff />` |
| Star | Star | `<Star />` |
| Heart | Heart | `<Heart />` |
| Share | Share2 | `<Share2 />` |
| Filter | Filter | `<Filter />` |
| Sort | ArrowUpDown | `<ArrowUpDown />` |
| Drag Handle | GripVertical | `<GripVertical />` |
| Clock/Time | Clock | `<Clock />` |
| Mail | Mail | `<Mail />` |
| Phone | Phone | `<Phone />` |
| Globe | Globe | `<Globe />` |
| Home | Home | `<Home />` |
| Bookmark | Bookmark | `<Bookmark />` |
| Tag | Tag | `<Tag />` |
| Command | Command | `<Command />` |
| Keyboard | Keyboard | `<Keyboard />` |
| Sparkles (AI) | Sparkles | `<Sparkles />` |
| Wand (Magic) | Wand2 | `<Wand2 />` |
| Zap (Quick Action) | Zap | `<Zap />` |
| Rocket (Launch) | Rocket | `<Rocket />` |
| Target | Target | `<Target />` |
| Layers | Layers | `<Layers />` |
| Grid | Grid3x3 | `<Grid3x3 />` |
| List | List | `<List />` |

---

## PART 5: COMPONENT SPECIFICATIONS

### 5.1 Button Component

#### Variants

**Primary Button**
- Background: `--brand-500` (#f97316)
- Text: white
- Hover: `--brand-600` (#ea580c)
- Active: `--brand-600` with `transform: scale(0.98)`
- Focus: 2px ring of `rgba(249, 115, 22, 0.5)` offset 2px

**Secondary Button**
- Background: `--bg-surface-2` (#1a1a24)
- Border: 1px solid `--border-default` (#3f3f46)
- Text: `--text-primary` (white)
- Hover: `--bg-hover` (#2a2a36)
- Active: `--bg-active` (#32323e)
- Focus: 2px ring of `rgba(255, 255, 255, 0.2)` offset 2px

**Ghost Button**
- Background: transparent
- Text: `--text-secondary` (#a1a1aa)
- Hover: `--bg-hover` (#2a2a36), text becomes white
- Active: `--bg-active` (#32323e)
- Focus: 2px ring of `rgba(255, 255, 255, 0.2)` offset 2px

**Danger Button**
- Background: `--error-text` (#ef4444)
- Text: white
- Hover: darken 10% (#dc2626)
- Active: darken 15% with `transform: scale(0.98)`
- Focus: 2px ring of `rgba(239, 68, 68, 0.5)` offset 2px

**Link Button**
- Background: none
- Text: `--brand-500` (#f97316)
- Hover: underline, text `--brand-400` (#fb923c)
- Active: `--brand-600`
- Focus: 2px ring around text

#### Sizes

| Size | Height | Padding | Font Size | Icon Size | Border Radius |
|------|--------|---------|-----------|-----------|---------------|
| xs | 28px | 6px 10px | 12px | 14px | 4px |
| sm | 32px | 8px 12px | 13px | 16px | 6px |
| md | 40px | 10px 16px | 14px | 18px | 6px |
| lg | 48px | 12px 20px | 16px | 20px | 8px |
| xl | 56px | 14px 24px | 18px | 24px | 8px |

#### States

**Disabled State (all variants)**
- Opacity: 0.5
- Cursor: not-allowed
- No hover/active effects
- Background stays at default

**Loading State**
- Show spinner icon (Loader2 from Lucide, animated spin)
- Text changes to "Loading..." or custom loading text
- Button is non-interactive but not visually disabled
- Spinner: 16px, animating with `animation: spin 1s linear infinite`

#### Icon Placement

- Icon-only button: square dimensions (width = height)
- Icon + text: icon on left, 8px gap to text
- Text + icon: icon on right, 8px gap from text

#### Button Groups

When buttons are grouped:
- First button: `border-radius: 6px 0 0 6px`
- Middle buttons: `border-radius: 0`
- Last button: `border-radius: 0 6px 6px 0`
- Remove borders between buttons, use 1px gap

---

### 5.2 Input Component

#### Base Input

**Dimensions**
- Height: 40px (md), 32px (sm), 48px (lg)
- Padding: 10px 12px
- Font size: 15px
- Border radius: 6px

**Default State**
- Background: `--bg-surface-1` (#12121a)
- Border: 1px solid `--border-default` (#3f3f46)
- Text: `--text-primary` (white)
- Placeholder: `--text-tertiary` (#71717a)

**Hover State**
- Border: 1px solid `--border-strong` (#52525b)

**Focus State**
- Border: 1px solid `--brand-500` (#f97316)
- Box shadow: `0 0 0 3px rgba(249, 115, 22, 0.2)`
- Outline: none

**Error State**
- Border: 1px solid `--error-text` (#ef4444)
- Box shadow: `0 0 0 3px rgba(239, 68, 68, 0.2)` on focus

**Success State**
- Border: 1px solid `--success-text` (#22c55e)
- Show check icon on right side

**Disabled State**
- Background: `--bg-base` (#0a0a0f)
- Opacity: 0.6
- Cursor: not-allowed

#### Input with Icon

- Icon container: 40px width, centered
- Icon color: `--text-tertiary` (#71717a)
- When focused, icon color: `--text-secondary` (#a1a1aa)
- Input padding-left when icon present: 44px

#### Input with Addon

- Addon background: `--bg-surface-2` (#1a1a24)
- Addon border: same as input
- Addon text: `--text-secondary`
- No border between addon and input

#### Textarea

- Min height: 80px
- Resize: vertical only
- Same styling as input
- Line height: 1.5

#### Input Label

- Font size: 13px
- Font weight: 500
- Color: `--text-secondary` (#a1a1aa)
- Margin bottom: 6px
- Required indicator: red asterisk after label

#### Helper Text

- Font size: 12px
- Color: `--text-tertiary` (#71717a)
- Margin top: 6px
- Error helper text: `--error-text` (#ef4444)

---

### 5.3 Select/Dropdown Component

#### Trigger Button

Same styling as Input, plus:
- Chevron icon on right side (ChevronDown)
- Chevron rotates 180° when open
- Transition: 150ms

#### Dropdown Panel

- Background: `--bg-surface-3` (#22222e)
- Border: 1px solid `--border-default` (#3f3f46)
- Border radius: 8px
- Box shadow: `--shadow-lg`
- Max height: 300px
- Overflow-y: auto
- Z-index: `--z-dropdown` (100)
- Animation: fade in + slide down 8px, 150ms

#### Dropdown Item

- Padding: 10px 12px
- Font size: 14px
- Color: `--text-primary`
- Hover: background `--bg-hover` (#2a2a36)
- Selected: background `rgba(249, 115, 22, 0.1)`, text `--brand-500`
- Selected shows check icon on right

#### Dropdown with Search

- Search input pinned at top
- Input has no border radius on bottom
- Divider line below search

#### Dropdown Group

- Group label: 11px, uppercase, `--text-tertiary`, padding 8px 12px
- Divider between groups: 1px `--border-subtle`

---

### 5.4 Modal Component

#### Overlay

- Background: `rgba(0, 0, 0, 0.7)`
- Backdrop filter: `blur(4px)`
- Z-index: `--z-modal` (400)
- Animation: fade in 200ms
- Click outside closes modal (configurable)

#### Modal Container

- Background: `--bg-surface-2` (#1a1a24)
- Border: 1px solid `--border-default` (#3f3f46)
- Border radius: 12px
- Box shadow: `--shadow-xl`
- Max width: 480px (sm), 640px (md), 800px (lg), 90vw (max)
- Max height: 85vh
- Animation: fade in + scale from 95% to 100%, 250ms, ease-out

#### Modal Header

- Padding: 20px 24px
- Border bottom: 1px solid `--border-subtle`
- Title: 18px, font-weight 600
- Close button: top right, ghost style, 32px square

#### Modal Body

- Padding: 24px
- Overflow-y: auto if content exceeds

#### Modal Footer

- Padding: 16px 24px
- Border top: 1px solid `--border-subtle`
- Buttons aligned right
- Gap between buttons: 12px

#### Focus Trap

- Focus trapped inside modal when open
- First focusable element receives focus on open
- Escape key closes modal

---

### 5.5 Sliding Drawer Component

#### Overlay

- Same as Modal overlay
- Z-index: `--z-drawer` (300)

#### Drawer Panel

- Background: `--bg-surface-1` (#12121a)
- Border-left: 1px solid `--border-default` (right drawer)
- Width: 400px (sm), 560px (md), 720px (lg)
- Height: 100vh
- Position: fixed, right: 0, top: 0
- Animation: slide in from right, 300ms, ease-out
- On close: slide out to right, 250ms, ease-in

#### Drawer Header

- Height: 64px
- Padding: 0 24px
- Display: flex, align-items: center, justify-content: space-between
- Border bottom: 1px solid `--border-subtle`
- Title: 16px, font-weight 600
- Close button: ghost, 36px square

#### Drawer Body

- Padding: 24px
- Height: calc(100vh - 64px - 80px) if footer present
- Overflow-y: auto

#### Drawer Footer

- Height: 80px
- Padding: 16px 24px
- Border top: 1px solid `--border-subtle`
- Position: sticky, bottom: 0
- Background: `--bg-surface-1`

---

### 5.6 Toast/Notification Component

#### Container

- Position: fixed
- Bottom: 24px, right: 24px
- Z-index: `--z-toast` (500)
- Display: flex, flex-direction: column-reverse
- Gap: 12px

#### Toast Item

- Background: `--bg-surface-3` (#22222e)
- Border: 1px solid `--border-default`
- Border-left: 4px solid (color based on type)
- Border radius: 8px
- Padding: 16px
- Min width: 320px
- Max width: 480px
- Box shadow: `--shadow-lg`

#### Toast Types

| Type | Left Border Color | Icon |
|------|-------------------|------|
| Success | #22c55e | CheckCircle |
| Error | #ef4444 | XCircle |
| Warning | #eab308 | AlertTriangle |
| Info | #3b82f6 | Info |

#### Toast Content

- Icon: 20px, matching border color
- Title: 14px, font-weight 600, white
- Description: 13px, `--text-secondary`
- Close button: top right, 24px, ghost

#### Animation

- Enter: slide in from right + fade, 300ms
- Exit: slide out to right + fade, 200ms
- Auto dismiss after 5 seconds (configurable)

---

### 5.7 Card Component

#### Base Card

- Background: `--bg-surface-1` (#12121a)
- Border: 1px solid `--border-subtle` (#27272a)
- Border radius: 8px
- Padding: 20px

#### Interactive Card (Clickable)

- Cursor: pointer
- Hover: border-color `--border-default`, background `--bg-surface-2`
- Active: `transform: scale(0.99)`
- Transition: all 150ms

#### Selected Card

- Border: 2px solid `--brand-500`
- Background: `rgba(249, 115, 22, 0.05)`

#### Card Header

- Display: flex, justify-content: space-between, align-items: center
- Margin bottom: 16px
- Title: 16px, font-weight 600

#### Card Body

- Standard content area
- Typography uses base styles

#### Card Footer

- Margin top: 16px
- Padding top: 16px
- Border top: 1px solid `--border-subtle`
- Display: flex, justify-content: space-between

---

### 5.8 Badge Component

#### Sizes

| Size | Height | Padding | Font Size |
|------|--------|---------|-----------|
| sm | 20px | 4px 8px | 11px |
| md | 24px | 5px 10px | 12px |
| lg | 28px | 6px 12px | 13px |

#### Variants

**Solid Badges**
```
Default: bg #3f3f46, text white
Primary: bg #f97316, text white
Success: bg #22c55e, text white
Warning: bg #eab308, text black
Error: bg #ef4444, text white
Info: bg #3b82f6, text white
```

**Subtle Badges** (preferred for status indicators)
```
Default: bg rgba(63, 63, 70, 0.3), text #a1a1aa
Primary: bg rgba(249, 115, 22, 0.15), text #fb923c
Success: bg rgba(34, 197, 94, 0.15), text #4ade80
Warning: bg rgba(234, 179, 8, 0.15), text #facc15
Error: bg rgba(239, 68, 68, 0.15), text #f87171
Info: bg rgba(59, 130, 246, 0.15), text #60a5fa
```

#### Badge with Icon

- Icon size: same as font size
- Gap between icon and text: 4px

#### Badge with Remove Button

- X icon on right
- Hover: icon becomes white
- Gap: 6px

---

### 5.9 Avatar Component

#### Sizes

| Size | Dimensions | Font Size | Icon Size |
|------|------------|-----------|-----------|
| xs | 24px | 10px | 12px |
| sm | 32px | 12px | 14px |
| md | 40px | 14px | 18px |
| lg | 48px | 16px | 20px |
| xl | 64px | 20px | 28px |
| 2xl | 96px | 28px | 40px |

#### Image Avatar

- Border radius: 50% (always circular)
- Object-fit: cover
- Border: 2px solid `--bg-surface-2`

#### Initials Avatar

- Background: gradient from `--brand-500` to `--brand-600`
- Text: white, font-weight 600
- Max 2 characters

#### Icon Avatar

- Background: `--bg-surface-2`
- Icon: `--text-secondary`

#### Status Indicator

- Small circle at bottom-right
- Size: 25% of avatar size
- Border: 2px solid `--bg-surface-1`
- Colors: green (online), yellow (away), gray (offline), red (busy)

---

### 5.10 Skeleton Loader Component

#### Base Skeleton

- Background: `--bg-surface-2` (#1a1a24)
- Animation: shimmer effect moving left to right
- Shimmer gradient: `linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%)`
- Animation duration: 1.5s, infinite
- Border radius: 4px

#### Skeleton Variants

**Text Skeleton**
- Height: matches line height (20px for body text)
- Width: varies (100%, 80%, 60%)
- Border radius: 4px

**Avatar Skeleton**
- Circular
- Matches avatar sizes

**Button Skeleton**
- Height: matches button heights
- Border radius: 6px

**Card Skeleton**
- Combines multiple text lines + optional image area
- Maintains card padding

---

### 5.11 Progress Indicator Component

#### Linear Progress

- Height: 4px (sm), 8px (md), 12px (lg)
- Background: `--bg-surface-2`
- Border radius: full
- Fill: `--brand-500` or gradient
- Animation: width transition 300ms

#### Circular Progress (Spinner)

- Uses Loader2 icon from Lucide
- Animation: `spin 1s linear infinite`
- Sizes: 16px, 20px, 24px, 32px, 48px
- Color: `--brand-500` or `--text-secondary`

#### Step Progress

- Horizontal line connecting circles
- Circle sizes: 32px
- Completed: solid `--brand-500`, white check icon
- Current: border `--brand-500`, pulsing glow animation
- Upcoming: border `--border-default`, no fill
- Line: 2px height, `--border-default`, fills with `--brand-500` as steps complete

---

### 5.12 Tabs Component

#### Tab List

- Display: flex
- Gap: 0 (tabs touch)
- Border-bottom: 1px solid `--border-subtle`

#### Tab Button

- Padding: 12px 20px
- Font size: 14px
- Font weight: 500
- Color: `--text-secondary`
- Background: transparent
- Border: none
- Border-bottom: 2px solid transparent
- Cursor: pointer

**Hover State**
- Color: `--text-primary`
- Background: `--bg-hover`

**Active/Selected State**
- Color: `--brand-500`
- Border-bottom: 2px solid `--brand-500`

**Focus State**
- Outline: 2px solid `rgba(249, 115, 22, 0.5)`
- Outline-offset: -2px

#### Tab Panel

- Padding: 24px 0
- Hidden when not active (display: none, not visibility)

---

## PART 6: LAYOUT SPECIFICATIONS

### 6.1 App Shell

#### Structure
```
┌─────────────────────────────────────────────────────────────────┐
│  Header Bar (optional, 48px)                                     │
├────────────┬──────────────────────────────────┬─────────────────┤
│            │                                  │                 │
│  Sidebar   │        Main Content              │   Right Panel   │
│  (260px)   │        (flexible)                │   (360px)       │
│            │                                  │                 │
│            │                                  │                 │
│            │                                  │                 │
│            │                                  │                 │
│            │                                  │                 │
└────────────┴──────────────────────────────────┴─────────────────┘
```

#### Dimensions

- Total viewport: 100vw × 100vh
- Sidebar: 260px fixed width
- Right panel: 360px fixed width (collapsible)
- Main content: calc(100vw - 260px - 360px)
- Minimum main content width: 600px

#### Responsive Breakpoints

| Breakpoint | Sidebar | Main | Right Panel |
|------------|---------|------|-------------|
| ≥1440px | 260px visible | Flexible | 360px visible |
| 1024-1439px | 260px visible | Flexible | Collapsed (toggle button) |
| 768-1023px | 72px collapsed | Flexible | Hidden (drawer) |
| <768px | Hidden (drawer) | 100% | Hidden (drawer) |

---

### 6.2 Sidebar Navigation

#### Container

- Width: 260px
- Height: 100vh
- Position: fixed, left: 0, top: 0
- Background: `--bg-surface-1` (#12121a)
- Border-right: 1px solid `--border-subtle`
- Display: flex, flex-direction: column
- Z-index: `--z-sticky` (200)

#### Logo Section

- Height: 64px
- Padding: 0 20px
- Display: flex, align-items: center
- Border-bottom: 1px solid `--border-subtle`
- Logo: 28px height
- App name: 18px, font-weight 600, margin-left 12px

#### Navigation List

- Flex: 1
- Padding: 16px 12px
- Overflow-y: auto

#### Navigation Item

- Height: 44px
- Padding: 0 16px
- Border radius: 8px
- Display: flex, align-items: center
- Gap: 12px
- Margin-bottom: 4px
- Font size: 14px
- Font weight: 500
- Color: `--text-secondary`
- Cursor: pointer

**Hover State**
- Background: `--bg-hover`
- Color: `--text-primary`

**Active State**
- Background: `rgba(249, 115, 22, 0.1)`
- Color: `--brand-500`
- Border-left: 3px solid `--brand-500` (inside the padding)

**Icon**
- Size: 20px
- Color: inherits from parent

#### Section Divider

- Height: 1px
- Background: `--border-subtle`
- Margin: 16px 12px

#### Section Label

- Padding: 8px 16px
- Font size: 11px
- Font weight: 600
- Color: `--text-tertiary`
- Text-transform: uppercase
- Letter-spacing: 0.5px

#### User Section (Bottom)

- Margin-top: auto
- Padding: 16px 12px
- Border-top: 1px solid `--border-subtle`

#### User Card

- Display: flex, align-items: center
- Padding: 12px
- Border-radius: 8px
- Gap: 12px
- Hover: background `--bg-hover`
- Cursor: pointer

- Avatar: 36px
- Name: 14px, font-weight 500
- Email/Role: 12px, `--text-tertiary`

---

### 6.3 Main Content Area

#### Container

- Margin-left: 260px (sidebar width)
- Margin-right: 360px (right panel width, when visible)
- Min-height: 100vh
- Background: `--bg-base` (#0a0a0f)

#### Page Header

- Height: 72px
- Padding: 0 32px
- Display: flex, align-items: center, justify-content: space-between
- Border-bottom: 1px solid `--border-subtle`
- Background: `--bg-base`
- Position: sticky, top: 0
- Z-index: `--z-sticky`

**Page Title**
- Font size: 24px
- Font weight: 600
- Color: `--text-primary`

**Page Actions**
- Display: flex, gap: 12px

#### Page Content

- Padding: 32px
- Max-width: 1400px (optional, for very wide screens)

---

### 6.4 Right Panel (Context Panel)

#### Container

- Width: 360px
- Height: 100vh
- Position: fixed, right: 0, top: 0
- Background: `--bg-surface-1`
- Border-left: 1px solid `--border-subtle`
- Z-index: `--z-sticky`
- Display: flex, flex-direction: column

#### Panel Header

- Height: 56px
- Padding: 0 20px
- Display: flex, align-items: center, justify-content: space-between
- Border-bottom: 1px solid `--border-subtle`
- Title: 15px, font-weight 600

#### Panel Content

- Flex: 1
- Overflow-y: auto
- Padding: 20px

#### Collapse Button (When Collapsible)

- Position: absolute
- Left: -16px
- Top: 50%
- Transform: translateY(-50%)
- Width: 32px
- Height: 64px
- Background: `--bg-surface-2`
- Border: 1px solid `--border-subtle`
- Border-radius: 8px 0 0 8px
- Display: flex, align-items: center, justify-content: center
- Icon: ChevronRight (when collapsed), ChevronLeft (when expanded)

---

## PART 7: SCREEN SPECIFICATIONS

### 7.1 Login Page

#### Layout

- Full viewport background with subtle animated gradient
- Centered card container
- No sidebar, no navigation

#### Background

```css
background: linear-gradient(135deg, #0a0a0f 0%, #12121a 50%, #0a0a0f 100%);
```

Optional: Subtle animated particles or grid pattern

#### Login Card

- Width: 420px
- Background: `--bg-surface-1`
- Border: 1px solid `--border-subtle`
- Border-radius: 16px
- Padding: 48px 40px
- Box-shadow: `--shadow-xl`

#### Card Content (Top to Bottom)

1. **Logo**
   - Centered
   - Height: 40px
   - Margin-bottom: 8px

2. **Title**
   - Text: "Welcome back"
   - Font-size: 24px
   - Font-weight: 600
   - Text-align: center
   - Margin-bottom: 8px

3. **Subtitle**
   - Text: "Sign in to your account to continue"
   - Font-size: 14px
   - Color: `--text-secondary`
   - Text-align: center
   - Margin-bottom: 32px

4. **SSO Buttons** (if enabled)
   - Full-width secondary buttons
   - "Continue with Google" - Google icon
   - "Continue with Microsoft" - Microsoft icon
   - Gap: 12px
   - Margin-bottom: 24px

5. **Divider**
   - Horizontal line with "or" text centered
   - Line: `--border-subtle`
   - Text: 12px, `--text-tertiary`
   - Margin-bottom: 24px

6. **Email Input**
   - Label: "Email address"
   - Placeholder: "you@company.com"
   - Type: email
   - Margin-bottom: 16px

7. **Password Input**
   - Label: "Password"
   - Placeholder: "••••••••"
   - Type: password (with toggle visibility button)
   - Margin-bottom: 8px

8. **Forgot Password Link**
   - Text: "Forgot password?"
   - Alignment: right
   - Font-size: 13px
   - Color: `--brand-500`
   - Margin-bottom: 24px

9. **Sign In Button**
   - Full width
   - Primary variant
   - Size: lg
   - Text: "Sign in"

10. **Sign Up Link**
    - Text: "Don't have an account? Sign up"
    - Text-align: center
    - Font-size: 14px
    - Margin-top: 24px
    - Link color: `--brand-500`

#### States

**Loading State**
- Sign in button shows spinner + "Signing in..."
- Form inputs disabled

**Error State**
- Show error toast OR inline error below form
- Shake animation on card (subtle, 300ms)
- Error text: "Invalid email or password"

**Success State**
- Button shows check icon briefly
- Redirect to dashboard

---

### 7.2 Sign Up Page

#### Layout

Same as Login page

#### Card Content (Top to Bottom)

1. **Logo** (same as login)

2. **Title**
   - Text: "Create your account"

3. **Subtitle**
   - Text: "Start your 14-day free trial"
   - Or: "Join 500+ marketing teams"

4. **SSO Buttons** (same as login)

5. **Divider** (same as login)

6. **Full Name Input**
   - Label: "Full name"
   - Placeholder: "John Doe"
   - Margin-bottom: 16px

7. **Email Input**
   - Label: "Work email"
   - Placeholder: "you@company.com"
   - Margin-bottom: 16px

8. **Password Input**
   - Label: "Password"
   - Placeholder: "Create a strong password"
   - Show password strength indicator below
   - Margin-bottom: 16px

9. **Organization Name Input** (Optional)
   - Label: "Organization name (optional)"
   - Placeholder: "Acme Inc."
   - Margin-bottom: 24px

10. **Terms Checkbox**
    - Text: "I agree to the Terms of Service and Privacy Policy"
    - Links: underlined, `--brand-500`
    - Margin-bottom: 24px

11. **Create Account Button**
    - Full width, primary, lg
    - Text: "Create account"

12. **Sign In Link**
    - Text: "Already have an account? Sign in"

#### Password Strength Indicator

- 4 bars below password input
- Gap: 4px
- Height: 4px each
- Border-radius: 2px
- Colors based on strength:
  - Weak (1 bar): `--error-text`
  - Fair (2 bars): `--warning-text`
  - Good (3 bars): `--info-text`
  - Strong (4 bars): `--success-text`
- Text below: "Password strength: [Weak/Fair/Good/Strong]"

---

### 7.3 Dashboard Home

#### Page Header

- Title: "Dashboard"
- Actions: "New Campaign" button (primary)

#### Content Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Welcome Banner (collapsible for returning users)           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Metric Card │  │ Metric Card │  │ Metric Card │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
├──────────────────────────────┬──────────────────────────────┤
│  Recent Campaigns            │  Quick Actions               │
│  (List view)                 │  (Grid of action cards)      │
│                              │                              │
│                              │                              │
└──────────────────────────────┴──────────────────────────────┘
```

#### Welcome Banner (New Users)

- Background: gradient `--brand-gradient`
- Padding: 32px
- Border-radius: 12px
- Title: "Welcome to Marketing Agent, [Name]!"
- Subtitle: "Let's get your brand set up and launch your first campaign."
- CTA Button: "Complete Setup" (white button)
- Dismiss: X button top-right
- Margin-bottom: 32px

#### Metric Cards Row

- Display: grid, 3 columns
- Gap: 24px
- Margin-bottom: 32px

**Single Metric Card**
- Background: `--bg-surface-1`
- Border: 1px solid `--border-subtle`
- Border-radius: 12px
- Padding: 24px

- Icon: 40px circle with subtle background, icon inside
- Label: 13px, `--text-secondary`, margin-top: 16px
- Value: 32px, font-weight: 700, margin-top: 4px
- Trend: 13px, green/red with arrow icon, margin-top: 8px

#### Recent Campaigns Section

- Width: 60% of content area
- Title: "Recent Campaigns", 18px, font-weight: 600
- "View All" link on right

**Campaign List Item**
- Height: 72px
- Padding: 16px 20px
- Border-bottom: 1px solid `--border-subtle`
- Display: flex, align-items: center, gap: 16px

- Status dot: 10px circle (green=active, yellow=draft, gray=completed)
- Campaign name: 15px, font-weight: 500
- Date: 13px, `--text-tertiary`
- Channels: Platform icons, 16px each, gap: 4px
- Arrow: ChevronRight, right side

**Hover State**
- Background: `--bg-hover`
- Cursor: pointer

#### Quick Actions Section

- Width: 40% of content area
- Title: "Quick Actions"

**Action Card**
- Display: grid, 2 columns
- Gap: 16px

- Background: `--bg-surface-1`
- Border: 1px solid `--border-subtle`
- Border-radius: 8px
- Padding: 20px
- Cursor: pointer

- Icon: 32px, `--brand-500`
- Title: 14px, font-weight: 600, margin-top: 12px
- Description: 12px, `--text-secondary`

**Hover State**
- Border-color: `--brand-500`
- Background: `rgba(249, 115, 22, 0.05)`

**Quick Action Items**
1. Icon: Rocket, Title: "Launch Campaign", Desc: "Create a new marketing campaign"
2. Icon: PenTool, Title: "Create Content", Desc: "Write posts, emails, or blogs"
3. Icon: Sparkles, Title: "AI Assistant", Desc: "Chat with your marketing AI"
4. Icon: Calendar, Title: "Schedule Posts", Desc: "Plan your content calendar"

---

### 7.4 Chat Interface (Right Panel)

The chat panel lives in the right panel area and is always accessible.

#### Chat Header

- Height: 56px
- Title: "AI Assistant"
- Icon: Sparkles, 20px
- Clear history button: Trash2 icon, ghost button

#### Messages Area

- Flex: 1
- Overflow-y: auto
- Padding: 16px
- Display: flex, flex-direction: column
- Gap: 16px

#### Message Bubble

**User Message**
- Align: flex-end (right side)
- Max-width: 85%
- Background: `--brand-500`
- Color: white
- Border-radius: 16px 16px 4px 16px
- Padding: 12px 16px
- Font-size: 14px

**AI Message**
- Align: flex-start (left side)
- Max-width: 85%
- Background: `--bg-surface-2`
- Color: `--text-primary`
- Border-radius: 16px 16px 16px 4px
- Padding: 12px 16px
- Font-size: 14px

**AI Message with Actions**
- Below message text, show action buttons
- Margin-top: 12px
- Buttons: secondary, sm size
- Examples: "Create Campaign", "Edit", "View Details"

#### Typing Indicator

- Show when AI is generating response
- Three dots with bounce animation
- Background: `--bg-surface-2`
- Border-radius: 16px
- Padding: 12px 16px
- Dot size: 8px
- Dot color: `--text-tertiary`
- Animation: sequential bounce, 1.4s infinite

#### Chat Input Area

- Position: sticky bottom
- Background: `--bg-surface-1`
- Padding: 16px
- Border-top: 1px solid `--border-subtle`

**Input Container**
- Display: flex
- Background: `--bg-surface-2`
- Border: 1px solid `--border-default`
- Border-radius: 24px
- Padding: 8px 16px
- Gap: 8px

**Textarea**
- Flex: 1
- Background: transparent
- Border: none
- Resize: none
- Min-height: 24px
- Max-height: 120px (auto-expand)
- Font-size: 14px
- Placeholder: "Ask anything..."

**Send Button**
- 36px circle
- Background: `--brand-500`
- Icon: Send, 18px, white
- Hover: `--brand-600`
- Disabled when input empty

**Attachment Button** (Optional)
- 36px circle
- Background: transparent
- Icon: Paperclip, 18px, `--text-secondary`
- Hover: background `--bg-hover`

---

### 7.5 Campaign List Page

#### Page Header

- Title: "Campaigns"
- Actions:
  - Search input (240px width)
  - Filter dropdown
  - "New Campaign" button (primary)

#### Filters Bar

- Below header
- Background: `--bg-surface-1`
- Padding: 12px 24px
- Border-bottom: 1px solid `--border-subtle`
- Display: flex, gap: 12px

**Filter Pills**
- Status: All, Active, Draft, Completed, Paused
- Channel: All, Social, Email, Blog, Ads
- Pill style: ghost buttons, active shows `--brand-500` with subtle bg

#### Campaign Grid

- Display: grid
- Columns: repeat(auto-fill, minmax(340px, 1fr))
- Gap: 24px
- Padding: 24px

#### Campaign Card

- Background: `--bg-surface-1`
- Border: 1px solid `--border-subtle`
- Border-radius: 12px
- Overflow: hidden
- Cursor: pointer

**Card Header**
- Height: 140px
- Background: gradient based on campaign type or brand colors
- Position: relative

**Status Badge** (on card header)
- Position: absolute top-right
- Margin: 12px
- Badge style (subtle variant)

**Card Body**
- Padding: 20px

**Campaign Name**
- Font-size: 16px
- Font-weight: 600
- Margin-bottom: 8px

**Campaign Description**
- Font-size: 13px
- Color: `--text-secondary`
- Line-clamp: 2
- Margin-bottom: 16px

**Metrics Row**
- Display: flex, justify-content: space-between

**Metric Item**
- Label: 11px, `--text-tertiary`
- Value: 16px, font-weight: 600

**Card Footer**
- Padding: 12px 20px
- Border-top: 1px solid `--border-subtle`
- Display: flex, justify-content: space-between, align-items: center

**Channel Icons**
- Display: flex, gap: 8px
- Icon size: 18px
- Colored by platform

**Date**
- Font-size: 12px
- Color: `--text-tertiary`

#### Empty State

- Centered in content area
- Illustration: 200px (abstract marketing illustration or icon)
- Title: "No campaigns yet"
- Description: "Create your first campaign to get started"
- CTA: "Create Campaign" button (primary)

---

### 7.6 Brand Onboarding Flow

This is a full-screen takeover experience for new users.

#### Step 1: Website Entry

**Layout**
- Full screen, centered content
- Background: `--bg-base` with subtle radial gradient

**Content**
- Logo at top center, 40px height
- Title: "Let's set up your brand"
- Subtitle: "Enter your website and we'll analyze your brand automatically"
- Margin-bottom: 48px

**URL Input**
- Width: 480px
- Size: lg (48px height)
- Placeholder: "https://yourcompany.com"
- Icon left: Globe
- Clear button on right when has value

**Example URLs** (Below input)
- Text: "Try with:"
- Clickable links: "apple.com", "nike.com", "stripe.com"
- Style: ghost buttons, sm size

**Continue Button**
- Below input, margin-top: 24px
- Primary, lg size
- Width: 480px
- Text: "Analyze My Brand"
- Disabled until valid URL

**Skip Link**
- Below button
- Text: "Skip for now"
- Color: `--text-tertiary`
- Font-size: 13px

#### Step 2: Analysis Progress

**Layout**
- Full screen takeover
- Dark background with subtle animated particles

**Central Animation**
- Circular progress ring (120px diameter)
- Brand colors gradient
- Percentage in center: 48px, font-weight: 700
- Or: Pulsing brand icon

**Stage Indicators**
- Below animation
- Horizontal steps with connecting lines
- Steps: Crawling → Analyzing → Researching → Synthesizing
- Current step: `--brand-500` with pulse
- Completed: `--success-text` with check
- Upcoming: `--text-tertiary`

**Status Text**
- Below steps
- Font-size: 14px
- Color: `--text-secondary`
- Examples: "Scanning website pages...", "Analyzing brand voice...", "Researching competitors..."

**Activity Log** (Optional, collapsible)
- Below status
- Scrolling list of activities
- Font: monospace, 12px
- Max-height: 200px
- Background: `--bg-surface-1`
- Border-radius: 8px
- Padding: 16px

**Cancel Button**
- Fixed bottom center
- Ghost style
- Text: "Cancel"

#### Step 3: Brand Review

**Layout**
- Return to normal dashboard layout
- But main content is full-width (no right panel)

**Header**
- Title: "Your Brand DNA"
- Subtitle: "Review and edit your brand profile"
- Save button: primary, "Save & Continue"

**Brand Cards Grid**
- Display: grid, 2 columns
- Gap: 24px

**Brand Card**
- Background: `--bg-surface-1`
- Border: 1px solid `--border-subtle`
- Border-radius: 12px
- Padding: 24px

**Card Header**
- Icon + Title
- Edit button (ghost, Pencil icon)

**Card Content**
- Varies by card type

**Card Types**:

1. **Brand Voice**
   - Tone tags (Professional, Friendly, etc.)
   - Sample text

2. **Target Audience**
   - Demographics
   - Psychographics bullets

3. **Brand Colors**
   - Color swatches
   - Hex values

4. **Key Messages**
   - Numbered list of messages

5. **Competitors**
   - Logo + name for each
   - "Add more" button

6. **Products/Services**
   - List with descriptions

---

### 7.7 Kanban Board

#### Page Header

- Title: "Task Board"
- Actions:
  - View toggle: Kanban / List
  - Filter dropdown
  - "Add Task" button (primary)

#### Board Layout

- Display: flex
- Gap: 20px
- Overflow-x: auto
- Padding: 24px

#### Column

- Width: 300px
- Min-width: 300px
- Background: `--bg-surface-1`
- Border-radius: 12px
- Display: flex, flex-direction: column
- Max-height: calc(100vh - 180px)

**Column Header**
- Padding: 16px 20px
- Display: flex, justify-content: space-between, align-items: center
- Border-bottom: 1px solid `--border-subtle`

- Title: 14px, font-weight: 600
- Count badge: subtle variant
- More button: MoreVertical icon, ghost

**Column Colors** (Left border or header accent)
- To Do: `--text-tertiary` (gray)
- In Progress: `--brand-500` (orange)
- Review: `--info-text` (blue)
- Done: `--success-text` (green)

**Column Body**
- Flex: 1
- Overflow-y: auto
- Padding: 12px

**Task Cards Container**
- Display: flex, flex-direction: column
- Gap: 12px

#### Task Card

- Background: `--bg-surface-2`
- Border: 1px solid `--border-subtle`
- Border-radius: 8px
- Padding: 16px
- Cursor: grab

**Hover State**
- Border-color: `--border-default`
- Box-shadow: `--shadow-md`

**Dragging State**
- Opacity: 0.8
- Transform: rotate(3deg)
- Box-shadow: `--shadow-xl`
- Cursor: grabbing

**Card Content**
- Title: 14px, font-weight: 500, margin-bottom: 8px
- Description: 12px, `--text-secondary`, line-clamp: 2
- Tags: display flex, gap: 6px, margin-top: 12px
- Tag: Badge component, sm, subtle

**Card Footer**
- Margin-top: 12px
- Padding-top: 12px
- Border-top: 1px solid `--border-subtle`
- Display: flex, justify-content: space-between, align-items: center

- Assignee: Avatar, xs size
- Due date: 11px, `--text-tertiary`, Clock icon
- Priority: Colored dot (red=high, yellow=medium, green=low)

#### Add Task Button (In Column)

- At bottom of column body
- Full width
- Ghost style
- Icon: Plus
- Text: "Add task"
- Border: 1px dashed `--border-default`
- Border-radius: 8px
- Padding: 12px

**Hover State**
- Background: `--bg-hover`
- Border: 1px dashed `--border-strong`

---

### 7.8 Calendar Page

#### Page Header

- Title: "Content Calendar"
- Actions:
  - Today button
  - Navigation: < Month Year >
  - View toggle: Month / Week / Day
  - "Schedule Post" button (primary)

#### Calendar Grid (Month View)

**Header Row**
- Day names: Sun, Mon, Tue, Wed, Thu, Fri, Sat
- Font-size: 12px
- Color: `--text-tertiary`
- Text-align: center
- Padding: 12px

**Day Cells**
- Border: 1px solid `--border-subtle`
- Min-height: 120px
- Padding: 8px

**Day Number**
- Font-size: 13px
- Font-weight: 500
- Color: `--text-primary`
- Other month days: `--text-tertiary`

**Today**
- Day number has circle background: `--brand-500`
- Color: white

**Scheduled Post Item**
- Background: platform color with 0.2 opacity
- Border-left: 3px solid platform color
- Border-radius: 4px
- Padding: 4px 8px
- Font-size: 11px
- Margin-bottom: 4px
- Cursor: pointer
- Truncate text with ellipsis

**Hover**
- Show full text in tooltip
- Background opacity increases

**More Indicator**
- When more than 3 items
- Text: "+2 more"
- Font-size: 11px
- Color: `--text-secondary`

#### Week/Day Views

Similar structure but expanded height per day/hour
Time labels on left side: 12px, `--text-tertiary`

---

### 7.9 Asset Gallery Page

#### Page Header

- Title: "Assets"
- Actions:
  - Search input
  - Filter by type dropdown
  - Sort dropdown
  - View toggle: Grid / List
  - "Upload" button (primary)

#### Asset Grid

- Display: grid
- Columns: repeat(auto-fill, minmax(240px, 1fr))
- Gap: 20px
- Padding: 24px

#### Asset Card

- Background: `--bg-surface-1`
- Border: 1px solid `--border-subtle`
- Border-radius: 8px
- Overflow: hidden
- Cursor: pointer

**Preview Area**
- Height: 160px
- Background: `--bg-surface-2`
- Display: flex, align-items: center, justify-content: center

- Image: object-fit: cover, 100% fill
- Video: thumbnail with play button overlay
- Document: File icon, 48px, colored by type
- Audio: waveform visualization or audio icon

**Info Area**
- Padding: 16px

**File Name**
- Font-size: 14px
- Font-weight: 500
- Truncate with ellipsis

**Meta Row**
- Display: flex, justify-content: space-between
- Margin-top: 8px
- Font-size: 12px
- Color: `--text-tertiary`

- Type: "Image", "Video", "PDF", etc.
- Size: "2.4 MB"
- Date: "Jan 15, 2026"

**Hover Overlay**
- Position: absolute, full coverage
- Background: rgba(0, 0, 0, 0.6)
- Display: flex, gap: 8px, centered
- Action buttons: Download, Edit, Delete
- Button style: ghost, white icons

---

## PART 8: USER FLOWS

### 8.1 First-Time User Flow

```
1. Sign Up Page
   ↓
2. Email Verification (if required)
   ↓
3. Welcome Modal (brief product tour)
   ↓
4. Brand Onboarding - Step 1 (URL entry)
   ↓
5. Brand Onboarding - Step 2 (Analysis)
   ↓
6. Brand Onboarding - Step 3 (Review)
   ↓
7. Dashboard with Welcome Banner
   ↓
8. Prompt to create first campaign
```

### 8.2 Campaign Creation Flow

```
1. Click "New Campaign" from anywhere
   ↓
2. Modal: Choose campaign type
   - Quick Campaign (AI does everything)
   - Guided Campaign (step-by-step)
   - From Template
   ↓
3. Step 1: Objective
   - What's the goal?
   - AI suggestions based on brand
   ↓
4. Step 2: Audience
   - Who are we targeting?
   - Use existing segments or create new
   ↓
5. Step 3: Channels
   - Select platforms
   - See content requirements
   ↓
6. Step 4: Timeline
   - Start/end dates
   - Posting frequency
   ↓
7. Step 5: Review
   - Preview all selections
   - Edit any section
   ↓
8. Generate Content
   - AI creates all deliverables
   - Progress screen
   ↓
9. Campaign Workspace
   - Edit/approve content
   - Schedule/publish
```

### 8.3 Content Editing Flow

```
1. Click on any content card
   ↓
2. Sliding drawer opens from right
   - Full content preview
   - Edit form
   ↓
3. Make changes
   - Direct editing
   - Or: AI suggestions panel
   ↓
4. Preview changes
   - Live preview for social posts
   - Mobile/desktop toggle
   ↓
5. Save or Publish
   - Save as draft
   - Schedule for later
   - Publish now
```

### 8.4 AI Chat Interaction Flow

```
1. Chat is always visible in right panel
   ↓
2. Type question or command
   ↓
3. AI responds with text
   - May include action buttons
   - May include content previews
   ↓
4. Click action button (optional)
   - Opens relevant modal/drawer
   - Pre-filled with AI suggestions
   ↓
5. Complete action
   - Returns to chat
   - AI confirms action taken
```

---

## PART 9: ANIMATIONS & TRANSITIONS

### 9.1 Page Transitions

**Navigate to new page:**
- Current content fades out: 150ms, ease-out
- New content fades in + slides up 20px: 250ms, ease-out
- Total: feels like 300ms

### 9.2 Modal Animations

**Open:**
- Overlay: fade in 200ms
- Modal: fade in + scale from 95% to 100%, 250ms, ease-out

**Close:**
- Modal: fade out + scale to 95%, 150ms, ease-in
- Overlay: fade out 200ms

### 9.3 Drawer Animations

**Open (from right):**
- Overlay: fade in 200ms
- Drawer: slide in from translateX(100%) to translateX(0), 300ms, ease-out

**Close:**
- Drawer: slide out to translateX(100%), 250ms, ease-in
- Overlay: fade out 200ms

### 9.4 Toast Animations

**Enter:**
- Slide in from right + fade: 300ms, ease-out
- Slight bounce at end: ease-bounce

**Exit:**
- Slide out right + fade: 200ms, ease-in

### 9.5 Button Interactions

**Hover:**
- Background color: 150ms
- Transform: none

**Active/Click:**
- Transform: scale(0.98), 100ms
- Returns to scale(1): 100ms

### 9.6 Card Interactions

**Hover:**
- Border color change: 150ms
- Optional: slight lift (translateY(-2px)) + shadow increase

**Click/Active:**
- Scale: 0.99, 100ms

### 9.7 Loading States

**Skeleton Shimmer:**
```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
animation: shimmer 1.5s infinite;
background: linear-gradient(90deg,
  var(--bg-surface-2) 25%,
  var(--bg-surface-3) 50%,
  var(--bg-surface-2) 75%
);
background-size: 200% 100%;
```

**Spinner:**
```css
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
animation: spin 1s linear infinite;
```

**Pulse (for active indicators):**
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
animation: pulse 2s ease-in-out infinite;
```

**Typing Dots:**
```css
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}
.dot:nth-child(1) { animation: bounce 1.4s infinite 0s; }
.dot:nth-child(2) { animation: bounce 1.4s infinite 0.2s; }
.dot:nth-child(3) { animation: bounce 1.4s infinite 0.4s; }
```

---

## PART 10: KEYBOARD SHORTCUTS

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + K` | Open command palette |
| `Cmd/Ctrl + /` | Open AI chat |
| `Cmd/Ctrl + N` | New campaign |
| `Cmd/Ctrl + S` | Save current item |
| `Escape` | Close modal/drawer/dropdown |
| `?` | Show keyboard shortcuts |

### Navigation Shortcuts

| Shortcut | Action |
|----------|--------|
| `G then D` | Go to Dashboard |
| `G then C` | Go to Campaigns |
| `G then A` | Go to Analytics |
| `G then K` | Go to Kanban |
| `G then S` | Go to Settings |

### Editor Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + B` | Bold text |
| `Cmd/Ctrl + I` | Italic text |
| `Cmd/Ctrl + U` | Underline text |
| `Cmd/Ctrl + Enter` | Submit/Publish |
| `Tab` | Next field |
| `Shift + Tab` | Previous field |

---

## PART 11: RESPONSIVE BEHAVIOR

### Breakpoint Definitions

```css
--bp-mobile: 640px
--bp-tablet: 768px
--bp-laptop: 1024px
--bp-desktop: 1280px
--bp-wide: 1440px
```

### Mobile (<768px)

- Sidebar: hidden, hamburger menu in header
- Right panel: hidden, accessible via button
- Navigation: bottom tab bar for main items
- Cards: single column
- Tables: horizontal scroll or card view
- Modals: full-screen
- Drawers: full-screen

### Tablet (768px - 1023px)

- Sidebar: collapsed (72px), icons only, expand on hover
- Right panel: hidden by default, slide-over when opened
- Cards: 2 columns
- Modals: centered, max-width 90%

### Laptop (1024px - 1279px)

- Sidebar: full width (260px)
- Right panel: collapsible (toggle button)
- Cards: 2-3 columns

### Desktop (≥1280px)

- Full layout as designed
- Sidebar: 260px
- Right panel: 360px
- Cards: 3-4 columns

---

## PART 12: ACCESSIBILITY REQUIREMENTS

### Focus Management

- All interactive elements must be focusable
- Focus visible: 2px ring, offset 2px
- Focus trap in modals/drawers
- Return focus to trigger when closed

### ARIA Labels

- All icon-only buttons: `aria-label`
- Form inputs: associated labels or `aria-label`
- Live regions for dynamic content: `aria-live`
- Modal: `role="dialog"`, `aria-modal="true"`
- Navigation: `role="navigation"`

### Color Contrast

- Text on backgrounds: minimum 4.5:1
- Large text (18px+): minimum 3:1
- UI components: minimum 3:1

### Motion

- Respect `prefers-reduced-motion`
- Provide alternative static states
- No autoplay videos without user control

### Screen Reader Support

- Semantic HTML elements
- Heading hierarchy (h1 → h2 → h3)
- Skip links to main content
- Alt text for images

---

## PART 13: ERROR, EMPTY, AND LOADING STATES

### Error States

**Form Field Error**
- Red border
- Error message below: 12px, `--error-text`
- Error icon optional

**Page Error (API failure)**
- Centered card
- Icon: AlertCircle, 48px, `--error-text`
- Title: "Something went wrong"
- Description: "We couldn't load this page. Please try again."
- Actions: "Retry" (primary), "Go Home" (ghost)

**Toast Error**
- Red left border
- X icon
- Auto-dismiss in 8 seconds (longer than success)

### Empty States

**No Data**
- Centered in content area
- Illustration or icon: 160px
- Title: 20px, font-weight: 600
- Description: 14px, `--text-secondary`
- CTA button: primary

**Search No Results**
- Icon: Search
- Title: "No results found"
- Description: "Try adjusting your search or filters"
- CTA: "Clear filters"

### Loading States

**Initial Page Load**
- Skeleton of page layout
- Match exact structure of loaded state

**Content Loading**
- Skeleton cards in grid
- Match card dimensions

**Action in Progress**
- Button: spinner + "Loading..."
- Full page: centered spinner

**Streaming Content (AI)**
- Text appears character by character
- Cursor blinks at end

---

## PART 14: COMMAND PALETTE

The command palette (Cmd+K) is a power-user feature for quick navigation and actions.

### Overlay

- Background: `rgba(0, 0, 0, 0.7)`
- Backdrop filter: blur(4px)

### Container

- Width: 560px
- Max-height: 400px
- Background: `--bg-surface-2`
- Border: 1px solid `--border-default`
- Border-radius: 12px
- Box-shadow: `--shadow-xl`
- Overflow: hidden
- Position: centered, 20% from top

### Search Input

- Full width
- Height: 56px
- Background: transparent
- Border: none
- Border-bottom: 1px solid `--border-subtle`
- Padding: 0 20px
- Font-size: 16px
- Placeholder: "Search or type a command..."
- Icon: Search, left side

### Results Area

- Overflow-y: auto
- Max-height: calc(400px - 56px)

### Result Group

- Padding-top: 8px
- Group label: 11px, `--text-tertiary`, uppercase, padding: 8px 20px

### Result Item

- Padding: 12px 20px
- Display: flex, align-items: center, gap: 12px
- Cursor: pointer

**Hover/Active State**
- Background: `--bg-hover`

**Icon**
- 20px
- Color: `--text-secondary`

**Title**
- 14px
- Color: `--text-primary`

**Shortcut Badge** (right side, optional)
- Font: monospace
- Font-size: 11px
- Background: `--bg-surface-3`
- Padding: 2px 6px
- Border-radius: 4px

### Keyboard Navigation

- Arrow up/down: move selection
- Enter: execute selected
- Escape: close
- Type to search

### Categories

1. **Navigation**
   - Go to Dashboard
   - Go to Campaigns
   - Go to Analytics
   - etc.

2. **Actions**
   - Create Campaign
   - Upload Asset
   - New Task
   - etc.

3. **Recent**
   - Recently visited pages
   - Recent campaigns

---

## APPENDIX A: FILE LOCATIONS TO UPDATE

### Emojis to Remove

| File | Location | Change |
|------|----------|--------|
| DashboardPage.jsx | Lines 24-34 | Replace emoji with Lucide icon |
| DashboardPage.jsx | Lines 396-409 | Replace emoji in quick actions |
| DashboardPage.jsx | Lines 418, 426 | Replace chat avatars |
| AssetCard.jsx | Lines 5-12 | Replace type emojis |
| SlidingDeliverablesPanel.jsx | Lines 19-25 | Replace type emojis |
| TrendMaster.jsx | Lines 16-19, 78, 98, 170 | Replace all emojis |
| ConversationalImageEditor.jsx | Lines 18-21, 341, 481, 511 | Replace emojis |
| ConceptPitch.jsx | Lines 51, 105, 121, 144 | Replace emojis |

### Spacing to Fix

| File | Line | Current | Required |
|------|------|---------|----------|
| DeliverableCards.css | 66 | 2px 8px | 6px 12px |
| DeliverableCards.css | 114 | 2px 6px | 4px 10px |
| DeliverableCards.css | 140 | gap: 4px | gap: 8px |
| DeliverableCards.css | 171 | gap: 4px | gap: 8px |
| DeliverableCards.css | 176 | 4px 12px | 8px 16px |
| ChatPanel.css | 203 | spacing-2 | spacing-3 |
| ChatPanel.css | 265 | spacing-1 spacing-2 | spacing-2 spacing-3 |
| KanbanBoard.css | 154 | 12px | 16px |
| DashboardPage.css | 39 | spacing-xs | spacing-sm |

---

## APPENDIX B: COMPONENT CHECKLIST

Before any component is considered complete, verify:

- [ ] All 5 interactive states work (default, hover, active, focus, disabled)
- [ ] Uses design tokens exclusively (no hard-coded colors/sizes)
- [ ] Works in dark mode
- [ ] Works in light mode (if applicable)
- [ ] Responsive at all breakpoints
- [ ] Keyboard accessible
- [ ] Has proper ARIA attributes
- [ ] Loading state implemented
- [ ] Error state implemented
- [ ] Empty state implemented (if applicable)
- [ ] Animations use correct timing/easing
- [ ] No emojis used

---

**END OF DESIGN SPECIFICATION**

This document is the single source of truth for the Marketing Agent Platform design. Any deviation requires explicit approval and documentation update.
