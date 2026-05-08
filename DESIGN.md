---
name: Datakura – Warehouse Management
colors:
  # Brand / Action
  primary: "#1976d2"
  primary-light: "#1976d27b"
  on-primary: "#ffffff"
  primary-container: "#e3f0fc"
  on-primary-container: "#0d47a1"
  # Accents
  secondary: "#192072"
  on-secondary: "#ffffff"
  accent: "#3f84e5"
  on-accent: "#ffffff"
  # Semantic
  positive: "#30ba78"
  on-positive: "#ffffff"
  warning: "#f59e0b"
  on-warning: "#1a1a1a"
  negative: "#d92b2b"
  on-negative: "#ffffff"
  light-negative: "#fee2e2"
  # Neutral / Surface (light)
  surface: "#ffffff"
  surface-container-low: "#f1f1f1"
  surface-container: "#fafafa"
  surface-container-high: "#efefef"
  on-surface: "#1a1a1a"
  on-surface-variant: "#6d6d6d"
  outline: "#e0e0e0"
  # Neutral / Surface (dark)
  surface-dark: "#000000"
  surface-dark-container: "#3a3a3a"
  surface-dark-container-high: "#424242"
  on-surface-dark: "#ffffff"
  on-surface-dark-variant: "#bdbdbd"
  outline-dark: "#424242"
  # Logo accent bars (decorative)
  logo-bar-red: "#ef4444"
  logo-bar-orange: "#f97316"
  logo-bar-blue: "#1976d2"
  # Link / interactive text
  link: "#1976d2"
typography:
  display:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: "600"
    lineHeight: 36px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: "500"
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: "500"
    lineHeight: 24px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: "500"
    lineHeight: 22px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: "400"
    lineHeight: 24px
    letterSpacing: 0.01em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: "400"
    lineHeight: 20px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: "600"
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: "500"
    lineHeight: 16px
    letterSpacing: 0.03em
  overline:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: "600"
    lineHeight: 24px
    letterSpacing: 0.1em
  caption:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: "400"
    lineHeight: 16px
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.3125rem
  md: 0.375rem
  lg: 0.75rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  gutter: 8px
  sidebar-width: 256px
  header-height: 56px
  container-padding: 16px
elevation:
  shadow-sm: "0 1px 2px 0 rgba(102,102,102,0.15)"
  shadow-md: "0 4px 6px -1px rgba(102,102,102,0.2), 0 2px 4px -1px rgba(102,102,102,0.1)"
  shadow-lg: "0 10px 15px -3px rgba(102,102,102,0.15), 0 4px 6px -2px rgba(102,102,102,0.1)"
  shadow-dark-sm: "0 1px 2px 0 rgba(68,68,68,0.3)"
  shadow-dark-md: "0 4px 6px -1px rgba(68,68,68,0.4)"
motion:
  duration-fast: 150ms
  duration-base: 200ms
  duration-slow: 400ms
  easing: ease-in-out
components:
  foreground-panel:
    backgroundColor: "{colors.surface}"
    darkBackgroundColor: "{colors.surface-dark-container}"
    borderColor: "{colors.outline}"
    darkBorderColor: "{colors.outline-dark}"
    rounded: "{rounded.DEFAULT}"
    padding: "{spacing.md}"
    shadow: "{elevation.shadow-md}"
  foreground-panel-active:
    borderColor: "rgba(25,118,210,0.29)"
    textColor: "{colors.primary}"
  sidebar:
    backgroundColor: "#1a1a2e"
    textColor: "#ffffff"
    itemRounded: "{rounded.md}"
    itemPaddingY: "{spacing.xs}"
    itemActiveBackground: "{colors.primary-light}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.DEFAULT}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.on-surface-variant}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.DEFAULT}"
  input-outlined:
    backgroundColor: "transparent"
    borderColor: "{colors.outline}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "{rounded.DEFAULT}"
    height: 36px
  badge-state:
    rounded: "{rounded.full}"
    typography: "{typography.label-sm}"
    padding: "2px 6px"
  badge-package:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
    typography: "{typography.label-sm}"
  list-item:
    padding: "8px 12px"
    gap: "{spacing.sm}"
    rounded: "{rounded.DEFAULT}"
    borderColor: "{colors.outline}"
  list-item-hover:
    backgroundColor: "{colors.surface-container-low}"
  timeline-step:
    activeColor: "{colors.primary}"
    completedColor: "{colors.positive}"
    pendingColor: "#9e9e9e"
    rounded: "{rounded.full}"
    stepSize: 24px
---

## Brand & Style

Datakura is a warehouse management system (WMS) for small-to-medium businesses. The product is a web-based internal tool — Czech-language UI — used daily by operators to manage stock, inbound/outbound orders, invoices, and inventory snapshots.

The design language is **compact and functional**. It borrows from enterprise SaaS conventions (Material Design via Quasar) but softens them with an Inter-based typographic scale and a muted, low-saturation neutral palette. The primary blue (`#1976d2`) drives all interactive affordances. The interface avoids decoration; whitespace and subtle shadows do the heavy lifting.

The product ships a full **dark/light dual theme**. Light mode uses white surfaces with light gray containers. Dark mode flips to true black (`#000000`) backgrounds with charcoal containers (`#424242`). Active and hover states lean on the primary blue at reduced opacity rather than introducing new colors.

The logo is a three-bar column chart in red → orange → blue (ascending height), reinforcing the data-and-movement nature of the product.

## Colors

The palette is deliberately narrow. One primary action color (blue `#1976d2`), one deep secondary/brand navy (`#192072`), and a clean set of semantic colors for status communication.

- **Primary blue** drives all buttons, links, active nav items, and focus rings.
- **Positive green** (`#30ba78`) marks completed states in timelines, badges, and order progress.
- **Negative red** (`#d92b2b`) is used sparingly for error states and cancellation badges. A tinted soft variant (`#fee2e2`) is used for inline error backgrounds.
- **Warning amber** (`#f59e0b`) indicates in-progress or receiving states (e.g. "Příjem" order status).
- **Neutral grays** provide the surface stack. Both light and dark variants use only two or three steps — the system avoids deep multi-level neutral hierarchies in favor of simplicity.
- **No decorative gradients** in the main UI. The homepage hero panel is the sole exception: two blurred radial color blobs (primary at 10 % opacity and orange at 10 % opacity) provide depth without competing with data.

## Typography

The entire interface uses **Inter** as its sole typeface, loaded via Google Fonts. Sora and Outfit are imported as alternatives but are not applied at the system level.

- Hierarchy is communicated through **weight** (400 → 700) and **size** rather than font-family changes.
- Overline labels (`font-semibold uppercase tracking-wide`) in `text-xs` introduce sections and widget headers without resorting to h-tags.
- Body copy is kept at 14–16 px. Dense data tables, list items, and sidebar labels use 14 px (`body-md`).
- Letter-spacing stays tight on headings (negative tracking) and slightly wide on overline/label text — never more than `tracking-wide` (`0.025em`).
- The `font-600`/`font-500`/`font-400` three-weight system maps to UnoCSS utility classes throughout components.

## Layout & Spacing

The layout follows a **left-sidebar + content-area** shell. The sidebar is fixed-width (~256 px), always visible on desktop, and contains hierarchical navigation grouped by domain (Produkty / Nákup-Prodej / Sklad / Zákazník / Nastavení).

- Base spacing unit is **4 px**. All gaps, paddings, and margins are multiples of 4.
- The 8 px grid is used for component internal rhythm; 16 px and 24 px for section separations.
- Content area uses a full-flex layout. Widgets and panels use CSS Grid with responsive `xl:grid-cols-2` breakpoints.
- A top toolbar (`q-header`) is transparent with a prominent `SearchInput` field and user info. It blends into the page background rather than establishing a distinct chrome band.
- List views use `border-b` dividers rather than cards to keep data density high.

## Elevation & Depth

Elevation is minimal and functional. The system uses two levels:

1. **Flat page background** — the `bg-color` CSS variable (white or black depending on theme).
2. **Foreground panels** — `ForegroundPanel` components carry `shadow-md` and a 1 px border (`border light:border-gray-200 dark:border-dark-3`) to float above the background.

Shadows use `#666` (light) and `#444` (dark) as shadow colors rather than pure black, avoiding a muddy appearance. No backdrop-filter blur effects are used anywhere in the current design.

The sidebar uses a near-black (`bg-dark-8`) to create a permanent dark panel that contrasts with both light and dark content areas.

## Shapes

The shape language is conservative. Minimal corner radius is the default; more pronounced rounding appears only on badge-like elements.

- **Generic containers / inputs**: `border-radius: 5px` (Quasar `$generic-border-radius`).
- **Buttons**: `border-radius: 6px`.
- **Menu items**: `rounded-md` (6 px via UnoCSS).
- **Badges and status chips**: `rounded-full` (9999 px) — pill shape.
- **Timeline step circles**: `rounded-full` for step indicator dots.
- **ForegroundPanel tabs in active state**: `rounded-xl` (`border-radius: 0.75rem`) for the `SimpleTimeline` step containers.

Icons are Material Symbols Outlined (`sym_o_*`) — consistent line weight with rounded terminals, harmonising with the corner radius system.

## Components

### ForegroundPanel

The primary surface component. Acts as an elevated card: white (light) or dark-6 (dark) background, 1 px border, `shadow-md`. Has variants: `flat` (no border/shadow/background — used as transparent section wrapper), `active` (adds a primary-tinted border), `clickable` (adds a primary hover tint at 8 % opacity). Transition: `all 0.2s ease-in-out`.

### Sidebar Navigation

Dark background (`bg-dark-8`, roughly `#1a1a1a`). Items are `q-item` with `rounded-md`, `dense`, full-width, and show a white text + ripple. Active state: `bg-primary-light` (primary at ~48 % opacity) in light mode, solid `bg-primary` in dark mode. Section headers use `text-gray-4` for a subdued category label.

### Badges & Status Chips

`GenericStateBadge` maps order/document states to Quasar badge colors:

- `draft` → grey-7
- `submitted` → primary (blue)
- `receiving` → orange-8
- `putaway` → cyan-8
- `completed` → positive (green)
- `cancelled` → negative (red)
- `confirmed` → positive (green)

Each badge includes a Material Symbol icon before the label text.

### Buttons

Primary actions: `q-btn color="primary" unelevated` — solid blue, no elevation, white label. Secondary/ghost actions: `q-btn color="grey-8" flat` — transparent background, grey label. Both share the same 6 px border-radius. Interactive states rely on Quasar's default ripple and hover layer.

### SearchInput

A `q-input` with `outlined` and `dense` modifiers, prefixed with a search icon. Clearable. Used in the main toolbar at a fixed width of 512 px. Serves as the primary global search affordance.

### SimpleTimeline (Order Progress)

A horizontal step indicator for multi-state workflows (e.g. order lifecycle). Each step is a pill-shaped container with a circular dot (grey → primary → positive as progress advances). On mobile, only the active step label is shown. Double-chevron icons separate steps on larger screens.

### Lists

Row-based list items use `border-b` dividers, `py-2 px-3 rounded` padding, and `hover:bg-light-3` / `hover:bg-dark-9` hover states. The `simple_list_item` shortcut (defined in UnoCSS config) encodes this pattern as a reusable utility class.

### Dark Mode

Dark mode is triggered by Quasar's `.body--dark` class. UnoCSS is configured to respect both `.body--light` and `.body--dark` selectors as dark-mode variants, allowing `light:` and `dark:` utility prefixes throughout the template markup. CSS custom properties (`--bg-color`, `--header-text-color`) bridge Quasar's theming with UnoCSS styles.
