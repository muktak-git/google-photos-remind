---
name: ReMind AI Memory Reconstruction
colors:
  surface: '#121316'
  surface-dim: '#121316'
  surface-bright: '#38393c'
  surface-container-lowest: '#0d0e11'
  surface-container-low: '#1a1b1e'
  surface-container: '#1e2022'
  surface-container-high: '#292a2d'
  surface-container-highest: '#343538'
  on-surface: '#e3e2e6'
  on-surface-variant: '#c3c6d1'
  inverse-surface: '#e3e2e6'
  inverse-on-surface: '#2f3033'
  outline: '#8d919b'
  outline-variant: '#424750'
  surface-tint: '#a8c8ff'
  primary: '#b5cfff'
  on-primary: '#003061'
  primary-container: '#8ab4f8'
  on-primary-container: '#0d4582'
  inverse-primary: '#315f9d'
  secondary: '#6ddd81'
  on-secondary: '#003914'
  secondary-container: '#30a550'
  on-secondary-container: '#003210'
  tertiary: '#ffc53c'
  on-tertiary: '#402d00'
  tertiary-container: '#e3a900'
  on-tertiary-container: '#594100'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d5e3ff'
  primary-fixed-dim: '#a8c8ff'
  on-primary-fixed: '#001b3c'
  on-primary-fixed-variant: '#114784'
  secondary-fixed: '#89fa9b'
  secondary-fixed-dim: '#6ddd81'
  on-secondary-fixed: '#002108'
  on-secondary-fixed-variant: '#005320'
  tertiary-fixed: '#ffdfa0'
  tertiary-fixed-dim: '#fbbc05'
  on-tertiary-fixed: '#261a00'
  on-tertiary-fixed-variant: '#5c4300'
  background: '#121316'
  on-background: '#e3e2e6'
  surface-variant: '#343538'
typography:
  display-lg:
    fontFamily: Roboto Flex
    fontSize: 40px
    fontWeight: '400'
    lineHeight: 48px
  headline-lg:
    fontFamily: Roboto Flex
    fontSize: 32px
    fontWeight: '400'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Roboto Flex
    fontSize: 26px
    fontWeight: '500'
    lineHeight: 32px
  headline-md:
    fontFamily: Roboto Flex
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 28px
  headline-sm:
    fontFamily: Roboto Flex
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
  body-lg:
    fontFamily: Roboto Flex
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Roboto Flex
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Roboto Flex
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Roboto Flex
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-md:
    fontFamily: Roboto Flex
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Roboto Flex
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 0.5rem
  gutter-desktop: 1rem
  margin: 1rem
  margin-desktop: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style
The design system powers an advanced AI reconstruction suite integrated seamlessly within a flagship personal media ecosystem. The experience addresses emotional, fragile, and nostalgic moments—recovering missing fragments, enhancing archival photography, and re-synthesizing partial memories. 

The brand aesthetic merges Material 3 expressive principles with utilitarian precision. It balances technological capability with delicate reverence for personal history:
- **Tone:** Intimate, reverent, intelligent, and effortless.
- **Visual Style:** Modern dark-mode Material Design with expressive tonal layering, organic rounded forms, fluid tactile feedback, and restrained use of four-color brand accents (Red, Yellow, Green, Blue) to signal AI confidence and verification states.
- **Audience:** Mobile-first users navigating deeply personal archives who require trustworthy, non-destructive, and transparent AI interactions.

## Colors
The palette leverages a dark-mode architecture optimized for OLED displays, preserving battery and focusing visual attention entirely on user imagery.

### Core Canvas & Surfaces
- **Canvas Base:** `#202124` (near-black foundation)
- **Surface Container:** `#303134` (standard cards, modular sheets, input containers)
- **Surface Elevated / Hover:** `#3C4043` (floating controls, modals, active surface states)
- **Dividers & Subtle Borders:** `#3C4043` (internal structural lines) and `#5F6368` (interactive borders, inactive chips)

### Typography & Iconography
- **Primary Text / High-Emphasis Icons:** `#E8EAED`
- **Secondary Text / Medium-Emphasis Glyphs:** `#9AA0A6`
- **On-Primary Container / Inverse Text:** `#202124` (used directly atop filled `#8AB4F8` elements)

### Accents & Semantic AI Identifiers
- **Primary Accent (Google Blue):** `#8AB4F8` for primary CTAs, active selection indicators, and major workflow progress.
- **Reconstruction Status (Photos Pinwheel Palette):**
  - **Pinwheel Red (`#EA4335`):** Low model confidence, missing data alerts, discard actions.
  - **Pinwheel Yellow (`#FBBC04`):** Memory synthesis in-progress, heuristic estimation, partial hallucination tags.
  - **Pinwheel Green (`#34A853`):** High-confidence facial match, verified chronological anchor, successful restoration.
  - **Pinwheel Blue (`#4285F4`):** AI synthesis complete, neutral system prompts, metadata anchors.

## Typography
Typographic hierarchy is built upon clean, mechanical clarity, ensuring immediate legibility against varied photographic content. Letter tracking remains slightly open for all micro-labels to prevent optical blending on emissive screens.

- Use **headline-md** for modal sheet headers, step titles, and active reconstruction queries.
- Use **body-md** as the default narrative description for memory prompts and system context.
- Use **label-lg** strictly for interactive pill buttons and selection targets.
- Use **label-sm** for confidence score indicators and timestamp badges.

## Layout & Spacing
The layout system follows a mobile-first philosophy centered around standard 390px-wide viewport frames with a fluid single-column structure, scaling up to adaptive multi-column arrangements on wide tablets and foldable devices.

- **Photo Grids:** Use tight spacing (`space-xs` to `space-sm`, 4px–8px) between photographic assets to produce a continuous collage effect that mirrors a personal timeline.
- **Component Padding:** Standard interactive cards utilize `space-md` (16px) internal padding. Screen edges maintain a consistent `margin` of 16px on mobile viewports.
- **Vertical Flow:** AI generation steps, control toolbars, and preview comparison viewports are separated by `space-lg` (24px) to ensure thumb-reach accessibility and clear visual chunking.

## Elevation & Depth
Depth is created via tonal surface transitions rather than heavy directional drop shadows, keeping rendering crisp and maintaining OLED power efficiency:

- **Level 0 (Canvas):** `#202124` for background canvas and underlying full-bleed media viewports.
- **Level 1 (Card & Content Blocks):** `#303134` with an optional 1px subtle stroke of `#3C4043` for unselected list items, resting toolbars, and prompt cards.
- **Level 2 (Floating Surfaces & Bottom Sheets):** `#3C4043` with an ultra-diffused, ambient shadow: `box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.45)`.
- **Level 3 (Modal Dialogs & AI Floating Action Controls):** Layered atop Level 2 using a 40% backdrop blur (`backdrop-filter: blur(16px)`) with `#202124CC` background fills to retain contextual spatial awareness of the underlying photo.

## Shapes
Shapes follow a dual-tier Material 3 curve syntax:

- **Cards & Image Containers:** Standard containers use 16px corner radii (`rounded-lg`), creating an approachable, soft-cornered frame for reconstructed media.
- **Photo Thumbnails:** Secondary grid elements scale down to 12px radii.
- **Interactive Controls:** All buttons, selection chips, input bars, and confidence chips adopt full pill geometry (`border-radius: 9999px`, minimum 24px–28px curve).

## Components

### Buttons
- **Filled Primary Button:** Full pill shape (height: 48px). Background: `#8AB4F8`. Typography: `label-lg`, `#202124` with bold weight. No border. On press: `#8AB4F8` with a 10% black overlay.
- **Tonal / Secondary Button:** Full pill shape (height: 48px). Background: `#3C4043`. Typography: `label-lg`, `#E8EAED`. Border: none.
- **Outlined / Discard Button:** Full pill shape. Background: transparent. Border: 1px solid `#5F6368`. Typography: `label-lg`, `#E8EAED`.

### Filter & Option Chips
- **Resting / Inactive:** Height 36px, full pill shape. Background: transparent. Border: 1px solid `#5F6368`. Text: `label-md`, `#9AA0A6`.
- **Active / Selected:** Background: `#8AB4F8`. Text: `label-md`, `#202124`. Optional leading checkmark or pinwheel colored dot (4px).

### Step Indicators (1 through 5)
- Horizontal progress strip placed immediately below the top app bar.
- Five pill segments (height: 4px; radius: 2px) separated by 6px gaps.
- Active & Completed Steps: Filled with `#8AB4F8`.
- Incomplete Steps: Filled with `#3C4043`.
- Active Step Label: Micro text (`label-sm`) beneath the bar indicating progress (e.g., "Step 2 of 5: Identity Synthesis").

### Top App Bar
- Fixed 56px height. Background: `#202124` with a subtle bottom divider of `#3C4043`.
- Left slot: Circular icon button (40px) with navigation back arrow (`#E8EAED`).
- Center: Feature title (`headline-sm`, `#E8EAED`) paired with an AI sparkle glyph.
- Right slot: Secondary action or "Cancel" link button.

### Photo Grids & Comparison Containers
- Two-column or dynamic masonry layout with 6px gutters.
- Each thumbnail wrapped in a 12px rounded container with `overflow: hidden`.
- Before/After split viewports feature a 32px floating pill handle (`#8AB4F8`) centered over a 2px vertical rule dividing original and reconstructed memory states.

### AI Confidence Indicators
- Micro badges (`label-sm`, height 24px) pill-shaped with 8px horizontal padding.
- Consists of a 6px status circle tinted in Pinwheel Red (`#EA4335`), Yellow (`#FBBC04`), Green (`#34A853`), or Blue (`#4285F4`) accompanied by white/high-contrast confidence text (e.g., "94% Confident", "Historical Approximation").