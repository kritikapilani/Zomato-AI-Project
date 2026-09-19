---
name: Crimson Consumer
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1b1b1b'
  on-surface-variant: '#5b403f'
  inverse-surface: '#313030'
  inverse-on-surface: '#f3f0ef'
  outline: '#8f6f6e'
  outline-variant: '#e4bebc'
  surface-tint: '#bb162c'
  primary: '#b7122a'
  on-primary: '#ffffff'
  primary-container: '#db313f'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb3b1'
  secondary: '#006e26'
  on-secondary: '#ffffff'
  secondary-container: '#8af793'
  on-secondary-container: '#007328'
  tertiary: '#805200'
  on-tertiary: '#ffffff'
  tertiary-container: '#a16900'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#8dfa96'
  secondary-fixed-dim: '#71dd7c'
  on-secondary-fixed: '#002106'
  on-secondary-fixed-variant: '#00531b'
  tertiary-fixed: '#ffddb4'
  tertiary-fixed-dim: '#ffb955'
  on-tertiary-fixed: '#291800'
  on-tertiary-fixed-variant: '#633f00'
  background: '#fcf9f8'
  on-background: '#1b1b1b'
  surface-variant: '#e5e2e1'
typography:
  display:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  display-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.005em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 2rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

The design system establishes a high-frequency, consumer-facing utility aesthetic tailored for instant discovery, effortless ordering, and appetite appeal. It merges functional utility with vibrant warmth, creating a dependable, immediate, and delightful user experience.

### Visual Style
- **Corporate & Modern Utility**: Crisp, structured, and content-first. Layouts emphasize food photography, promotional banners, restaurant cards, and action-oriented metadata.
- **Tone**: Energetic, transparent, efficient, and accessible.
- **Visual Contrast**: Pristine white canvas foundations with selective, punchy crimson accents and warm gray surface framing.

## Colors

The palette leverages an unmistakable crimson primary balanced by neutral surfaces and functional semantic cues.

- **Primary (`#E23744`)**: The primary brand accent, reserved for core call-to-action buttons, active navigation markers, interactive highlights, and price discounts.
- **Primary Hover / Pressed (`#C72835`)**: Deep crimson for pressed and hovered interactive states.
- **Secondary / Success (`#24963F`)**: Food safety ratings, positive badges (e.g., veg indicators, successful order statuses), and ratings cards.
- **Tertiary / Warning (`#F5A623`)**: Delivery delays, low stock warnings, and moderate ratings badges.
- **Neutral Primary (`#1C1C1C`)**: Ultra-dark charcoal for primary typography, titles, and iconography to maintain crisp WCAG AAA/AA legibility.
- **Neutral Secondary (`#696969`)**: Medium neutral for metadata, delivery durations, subtitle cues, and inactive icons.
- **Surface Background (`#FFFFFF`)**: Base canvas color providing clean separation for photography and cards.
- **Surface Container (`#F8F8F8`)**: Subtle warm neutral for card backgrounds, input containers, and chips.
- **Surface Border (`#E8E8E8`)**: Soft perimeter line to structure cards, dividers, and floating headers.
- **Gamification & Ranking Tiers**:
  - Gold: `#D4AF37`
  - Silver: `#9E9E9E`
  - Bronze: `#CD7F32`

## Typography

Inter is chosen across headlines, body copy, and interface labels for its legibility at scale, robust tabular figures, and tall x-height.

- **Headlines & Titles**: Utilize bold and semi-bold weights with slight negative letter-spacing to build authoritative visual hierarchy without compromising speed of scan.
- **Numbers & Pricing**: Currency symbols and price indicators must always use tabular figures (`font-feature-settings: 'tnum'`) with medium or semi-bold weights.
- **Labels & Microcopy**: Compact, capitalized or title-cased labels guide quick choices across food tags, delivery estimates, and nutritional flags.

## Layout & Spacing

The layout is built on a responsive 4-column (mobile), 8-column (tablet), and 12-column (desktop) fluid grid structure with an 8pt base grid rhythm.

- **Mobile Viewports (<640px)**: 4 columns, 16px page margins, 12px to 16px gutters. Edge-to-edge listing layouts with padded inner content.
- **Tablet Viewports (640px–1024px)**: 8 columns, 32px margins, 16px gutters. Double-column feed cards.
- **Desktop Viewports (>1024px)**: 12 columns, max container width of 1200px, 24px gutters, centered page alignment.
- **Spacing Rhythm**: Internal card padding standardizes on `space-md` (12px) and `space-lg` (16px). Section spacing uses `space-xl` (24px) to balance density with breathing room.

## Elevation & Depth

Visual hierarchy uses ambient diffusion and low-contrast borders instead of heavy drop shadows to keep the UI light, fast, and modern.

- **Level 0 (Flat)**: Pure `#FFFFFF` or `#F8F8F8` surfaces with an optional `1px solid #E8E8E8` border. Applied to baseline cards, embedded input boxes, and list dividers.
- **Level 1 (Subtle Cards)**: `box-shadow: 0 2px 8px rgba(28, 28, 28, 0.06); border: 1px solid #E8E8E8;`. Applied to restaurant grid cards, filter buttons, and search bars.
- **Level 2 (Interactive & Hover)**: `box-shadow: 0 6px 16px rgba(28, 28, 28, 0.10); border: 1px solid #E0E0E0; transform: translateY(-2px);`. Applied during card hover and interactive preview states.
- **Level 3 (Overlays & Sticky Bars)**: `box-shadow: 0 8px 24px rgba(28, 28, 28, 0.12);`. Applied to sticky bottom carts, floating filters, modal sheets, and quick-view popovers.

## Shapes

The design system incorporates soft, friendly geometric shapes that evoke modern consumer lifestyle applications:

- **Base Radius (`0.5rem` / 8px)**: Standard for small UI elements like checkboxes, tooltips, nested tags, and segmented tabs.
- **Large Radius (`1rem` / 16px)**: Standard for restaurant menu cards, promotional hero carousels, and dialog boxes.
- **Extra Large Radius (`1.5rem` / 24px)**: Applied to large bottom-sheet modal drawers, search trigger bars, and category circular badges.
- **Pill Formats (`9999px`)**: Reserved for primary CTAs, tag filters, floating pill buttons, counter badges, and rating chips.

## Components

### Buttons
- **Primary Button**: Solid `#E23744` background with `#FFFFFF` text. Fully rounded pill (`9999px`) or `0.5rem` corners based on context. Height 48px (large) or 40px (medium). Hover: `#C72835`.
- **Secondary Button**: Outlined with `1px solid #E8E8E8`, `#FFFFFF` background, and `#1C1C1C` text. Hover: `#F8F8F8` background.
- **Ghost / Text Button**: Transparent background with `#E23744` text. Used for "View all", "Add more items", and inline actions.

### Chips & Filters
- **Filter Chips**: Height 36px, `0.5rem` or pill radius. Default: `#FFFFFF` surface with `1px solid #E8E8E8` border and `#1C1C1C` text. Selected: `#F8F8F8` surface with `1px solid #E23744` border and `#E23744` text with an active cross icon.

### Input Fields & Search
- **Universal Search Bar**: Height 48px, `#FFFFFF` background with subtle ambient shadow (`Level 1`), `0.75rem` radius, placeholder text in `#696969`, and a crimson search icon accent.
- **Form Inputs**: Height 44px, `#F8F8F8` background with `1px solid #E8E8E8` border, transitioning to `#FFFFFF` with `1px solid #E23744` on focus.

### Restaurant & Food Cards
- **Restaurant Card**: `#FFFFFF` background, `1rem` radius, `Level 1` elevation. Features a 16:9 ratio food image with a rounded top, delivery badge positioned top-left, bookmark icon top-right, followed by a 12px content padding containing name, rating chip, cuisine tags, and pricing.
- **Rating Chip**: Compact pill badge with green (`#24963F`) background, `#FFFFFF` text, bold `label-sm`, and an inline star icon.

### Selection Controls
- **Checkboxes & Radios**: 20px size, rounded-sm (checkbox) or circular (radio), `#E8E8E8` default border. Active state: filled `#E23744` with `#FFFFFF` check/dot mark.
- **Veg / Non-Veg Indicator**: Square outline with rounded corners (`4px`). Veg: Green `#24963F` outline with an internal green circle. Non-veg: Brown `#8B4513` outline with an internal brown triangle.

### Quantity Stepper (Add-to-Cart)
- Outlined `#E23744` button (`32px` height) with white fill when unselected. On add: transitions to a filled or border-retained pill housing decrement (`-`), numerical count, and increment (`+`) triggers in bold crimson.