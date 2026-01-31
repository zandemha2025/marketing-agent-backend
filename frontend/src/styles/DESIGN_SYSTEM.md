# Marketing Agent Platform - Design System

This document describes the comprehensive design system implemented for the Marketing Agent Platform frontend.

## Overview

The design system is built on CSS custom properties (variables) defined in `tokens.css` and base styles in `global.css`. It provides:

- **Consistent theming** with light and dark mode support
- **Typography scale** with responsive sizes
- **Spacing scale** based on 4px increments
- **Color palette** with semantic colors
- **Component tokens** for buttons, inputs, cards, etc.

## File Structure

```
frontend/src/styles/
├── tokens.css      # Design tokens (CSS variables)
├── global.css      # Base styles and utility classes
├── kata-lab.css    # Page-specific styles
└── DESIGN_SYSTEM.md # This documentation
```

## Usage

### Importing Styles

In your main entry point (`main.jsx`):

```jsx
import './styles/tokens.css';
import './styles/global.css';
```

### Theme Switching

The design system supports three theme modes:

1. **Light mode (default)**: No attribute needed
2. **Dark mode**: Add `data-theme="dark"` to the root element
3. **System preference**: Automatically follows `prefers-color-scheme`

```jsx
// Force dark mode
document.documentElement.setAttribute('data-theme', 'dark');

// Force light mode
document.documentElement.setAttribute('data-theme', 'light');

// Follow system preference (remove attribute)
document.documentElement.removeAttribute('data-theme');
```

## Design Tokens

### Colors

#### Primary Colors (Blue)
```css
--color-primary-50 through --color-primary-950
```

#### Secondary Colors (Cyan/Teal)
```css
--color-secondary-50 through --color-secondary-950
```

#### Accent Colors (Coral/Orange)
```css
--color-accent-50 through --color-accent-950
```

#### Semantic Colors
```css
/* Success (Green) */
--color-success-50 through --color-success-950
--color-success (alias for 500)

/* Warning (Amber) */
--color-warning-50 through --color-warning-950
--color-warning (alias for 500)

/* Error (Red) */
--color-error-50 through --color-error-950
--color-error (alias for 500)

/* Info (Blue) */
--color-info-50 through --color-info-950
--color-info (alias for 500)
```

#### Neutral Colors (Gray)
```css
--color-gray-0 (white) through --color-gray-950 (near black)
```

### Theme-Aware Colors

These colors automatically adjust based on the current theme:

```css
/* Backgrounds */
--color-bg-primary      /* Main background */
--color-bg-secondary    /* Secondary background */
--color-bg-tertiary     /* Tertiary background */
--color-bg-card         /* Card background */
--color-bg-card-hover   /* Card hover state */
--color-bg-elevated     /* Elevated surfaces */
--color-bg-overlay      /* Modal overlays */

/* Text */
--color-text-primary    /* Primary text */
--color-text-secondary  /* Secondary text */
--color-text-tertiary   /* Tertiary text */
--color-text-muted      /* Muted text */
--color-text-link       /* Link text */

/* Borders */
--color-border          /* Default border */
--color-border-hover    /* Hover state border */
--color-border-focus    /* Focus state border */
```

### Typography

#### Font Families
```css
--font-family-sans   /* Primary font (Inter) */
--font-family-mono   /* Monospace font (JetBrains Mono) */
--font-family-display /* Display font (Inter) */
```

#### Font Sizes
```css
--font-size-xs    /* 12px / 0.75rem */
--font-size-sm    /* 14px / 0.875rem */
--font-size-base  /* 16px / 1rem */
--font-size-lg    /* 18px / 1.125rem */
--font-size-xl    /* 20px / 1.25rem */
--font-size-2xl   /* 24px / 1.5rem */
--font-size-3xl   /* 30px / 1.875rem */
--font-size-4xl   /* 36px / 2.25rem */
--font-size-5xl   /* 48px / 3rem */
--font-size-6xl   /* 60px / 3.75rem */
```

#### Font Weights
```css
--font-weight-normal    /* 400 */
--font-weight-medium    /* 500 */
--font-weight-semibold  /* 600 */
--font-weight-bold      /* 700 */
```

#### Line Heights
```css
--line-height-none     /* 1 */
--line-height-tight    /* 1.25 */
--line-height-snug     /* 1.375 */
--line-height-normal   /* 1.5 */
--line-height-relaxed  /* 1.625 */
--line-height-loose    /* 2 */
```

### Spacing

Based on 4px increments:

```css
--spacing-0     /* 0 */
--spacing-px    /* 1px */
--spacing-0-5   /* 2px */
--spacing-1     /* 4px */
--spacing-1-5   /* 6px */
--spacing-2     /* 8px */
--spacing-2-5   /* 10px */
--spacing-3     /* 12px */
--spacing-4     /* 16px */
--spacing-5     /* 20px */
--spacing-6     /* 24px */
--spacing-8     /* 32px */
--spacing-10    /* 40px */
--spacing-12    /* 48px */
--spacing-16    /* 64px */
--spacing-20    /* 80px */
--spacing-24    /* 96px */
```

### Border Radius

```css
--radius-none   /* 0 */
--radius-sm     /* 4px */
--radius-md     /* 6px */
--radius-lg     /* 8px */
--radius-xl     /* 12px */
--radius-2xl    /* 16px */
--radius-3xl    /* 24px */
--radius-full   /* 9999px (pill shape) */
```

### Shadows

```css
--shadow-xs     /* Subtle shadow */
--shadow-sm     /* Small shadow */
--shadow-md     /* Medium shadow */
--shadow-lg     /* Large shadow */
--shadow-xl     /* Extra large shadow */
--shadow-2xl    /* Huge shadow */
--shadow-inner  /* Inset shadow */

/* Glow effects */
--shadow-glow-primary
--shadow-glow-secondary
--shadow-glow-accent
--shadow-glow-success
--shadow-glow-error
```

### Transitions

```css
--transition-fast    /* 150ms ease */
--transition-normal  /* 200ms ease */
--transition-slow    /* 300ms ease */
--transition-slower  /* 500ms ease */
--transition-bounce  /* Bouncy animation */
--transition-spring  /* Spring animation */
```

### Z-Index Scale

```css
--z-base            /* 0 */
--z-dropdown        /* 1000 */
--z-sticky          /* 1020 */
--z-fixed           /* 1030 */
--z-modal-backdrop  /* 1040 */
--z-modal           /* 1050 */
--z-popover         /* 1060 */
--z-tooltip         /* 1070 */
--z-toast           /* 1080 */
--z-max             /* 9999 */
```

## Component Classes

### Buttons

```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-danger">Danger</button>
<button class="btn btn-ghost">Ghost</button>

<!-- Sizes -->
<button class="btn btn-primary btn-sm">Small</button>
<button class="btn btn-primary btn-lg">Large</button>

<!-- Icon button -->
<button class="btn btn-icon btn-secondary">
  <svg>...</svg>
</button>
```

### Inputs

```html
<input type="text" class="input" placeholder="Enter text...">
<input type="text" class="input input-sm" placeholder="Small input">
<input type="text" class="input input-lg" placeholder="Large input">
<textarea class="input">Textarea content</textarea>
```

### Cards

```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Card Title</h3>
    <p class="card-description">Card description</p>
  </div>
  <div class="card-content">
    Content goes here
  </div>
  <div class="card-footer">
    Footer content
  </div>
</div>
```

### Badges

```html
<span class="badge badge-default">Default</span>
<span class="badge badge-primary">Primary</span>
<span class="badge badge-success">Success</span>
<span class="badge badge-warning">Warning</span>
<span class="badge badge-error">Error</span>
```

### Status Classes

```html
<div class="status-success">Success message</div>
<div class="status-warning">Warning message</div>
<div class="status-error">Error message</div>
<div class="status-info">Info message</div>
```

## Utility Classes

### Text

```css
.text-xs, .text-sm, .text-base, .text-lg, .text-xl, .text-2xl, .text-3xl, .text-4xl
.font-normal, .font-medium, .font-semibold, .font-bold
.text-primary, .text-secondary, .text-muted, .text-accent
.text-left, .text-center, .text-right
.truncate, .line-clamp-1, .line-clamp-2, .line-clamp-3
```

### Layout

```css
.flex, .inline-flex, .block, .inline-block, .hidden
.flex-col, .flex-row, .flex-wrap, .flex-nowrap
.items-start, .items-center, .items-end
.justify-start, .justify-center, .justify-end, .justify-between
.gap-1, .gap-2, .gap-3, .gap-4, .gap-5, .gap-6, .gap-8
```

### Spacing

```css
/* Margin */
.m-0, .m-1, .m-2, .m-3, .m-4, .m-auto
.mt-0, .mt-1, .mt-2, .mt-3, .mt-4, .mt-6, .mt-8
.mb-0, .mb-1, .mb-2, .mb-3, .mb-4, .mb-6, .mb-8
.ml-0, .ml-1, .ml-2, .ml-3, .ml-4, .ml-auto
.mr-0, .mr-1, .mr-2, .mr-3, .mr-4, .mr-auto

/* Padding */
.p-0, .p-1, .p-2, .p-3, .p-4, .p-6, .p-8
.px-0, .px-1, .px-2, .px-3, .px-4, .px-6
.py-0, .py-1, .py-2, .py-3, .py-4, .py-6
```

### Visual

```css
.rounded-none, .rounded-sm, .rounded, .rounded-md, .rounded-lg, .rounded-xl, .rounded-2xl, .rounded-full
.shadow-none, .shadow-sm, .shadow, .shadow-md, .shadow-lg, .shadow-xl
.opacity-0, .opacity-25, .opacity-50, .opacity-75, .opacity-100
```

### Animation

```css
.animate-fadeIn, .animate-fadeOut
.animate-slideInRight, .animate-slideInLeft
.animate-slideInUp, .animate-slideInDown
.animate-pulse, .animate-spin, .animate-bounce
.animate-shimmer
.transition, .transition-fast, .transition-slow, .transition-none
```

## Best Practices

1. **Always use design tokens** instead of hardcoded values
2. **Use semantic color variables** (e.g., `--color-text-primary`) instead of raw colors
3. **Use spacing scale** for consistent margins and padding
4. **Use component tokens** for buttons, inputs, cards, etc.
5. **Test in both light and dark modes** to ensure proper contrast
6. **Use utility classes** for common patterns to reduce custom CSS

## Migration Guide

When updating existing components to use the design system:

1. Replace hardcoded colors with CSS variables:
   ```css
   /* Before */
   color: #fff;
   background: #0a0a0a;
   
   /* After */
   color: var(--color-text-primary);
   background: var(--color-bg-primary);
   ```

2. Replace hardcoded spacing with spacing variables:
   ```css
   /* Before */
   padding: 16px;
   margin-bottom: 24px;
   
   /* After */
   padding: var(--spacing-4);
   margin-bottom: var(--spacing-6);
   ```

3. Replace hardcoded border-radius with radius variables:
   ```css
   /* Before */
   border-radius: 8px;
   
   /* After */
   border-radius: var(--radius-lg);
   ```

4. Replace hardcoded transitions with transition variables:
   ```css
   /* Before */
   transition: all 0.2s ease;
   
   /* After */
   transition: all var(--transition-fast);
   ```
