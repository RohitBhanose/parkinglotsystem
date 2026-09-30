---
name: Smart Parking DBMS
colors:
  surface: '#111417'
  surface-dim: '#111417'
  surface-bright: '#37393d'
  surface-container-lowest: '#0b0e11'
  surface-container-low: '#191c1f'
  surface-container: '#1d2023'
  surface-container-high: '#272a2d'
  surface-container-highest: '#323538'
  on-surface: '#e1e2e6'
  on-surface-variant: '#d4c4b0'
  inverse-surface: '#e1e2e6'
  inverse-on-surface: '#2e3134'
  outline: '#9d8f7c'
  outline-variant: '#504535'
  surface-tint: '#fabc4d'
  primary: '#ffc665'
  on-primary: '#432c00'
  primary-container: '#e5a93c'
  on-primary-container: '#5e4000'
  inverse-primary: '#7e5700'
  secondary: '#b9c9d3'
  on-secondary: '#24323a'
  secondary-container: '#3a4951'
  on-secondary-container: '#a8b7c2'
  tertiary: '#afd2ff'
  on-tertiary: '#003258'
  tertiary-container: '#79b8fe'
  on-tertiary-container: '#00487b'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdead'
  primary-fixed-dim: '#fabc4d'
  on-primary-fixed: '#281900'
  on-primary-fixed-variant: '#604100'
  secondary-fixed: '#d5e5f0'
  secondary-fixed-dim: '#b9c9d3'
  on-secondary-fixed: '#0f1d25'
  on-secondary-fixed-variant: '#3a4951'
  tertiary-fixed: '#d1e4ff'
  tertiary-fixed-dim: '#9ecaff'
  on-tertiary-fixed: '#001d36'
  on-tertiary-fixed-variant: '#00497d'
  background: '#111417'
  on-background: '#e1e2e6'
  surface-variant: '#323538'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  title-sm:
    fontFamily: Space Grotesk
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-code:
    fontFamily: Space Grotesk
    fontSize: 13px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-bay:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 20px
    letterSpacing: 0.02em
  label-table-header:
    fontFamily: Space Grotesk
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1.5rem
  margin-sm: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system is tailored for an operational University Smart Parking Database Management System. The design merges high-utility technical precision with architectural minimalism. The emotional response is one of instant clarity, structured control, and calm efficiency—built for transit operators, campus security, and parking managers who need immediate insight into occupancy, sensor events, and vehicle relational records.

The aesthetic avoids bloated dashboard trends, extraneous analytics widgets, and neon sci-fi tropes. Instead, it relies on:
- A dark graphite/charcoal backdrop mimicking tarmac and architectural structural concrete.
- Crisp, deliberate contrasts using an amber/gold accent inspired by physical thermoplastic parking bays and road markings.
- Structural layout discipline influenced by technical database schematics and airport terminal signage.
- Utilitarian hierarchy prioritizing tabular legibility, physical slot states, camera streams, and unambiguous relational integrity.

## Colors

The palette employs a restrained, dark foundation to reduce visual fatigue in control room environments, complemented by focused functional accents.

- **Primary (`#e5a93c`)**: Warm amber/gold. Reserved strictly for active focal points, interactive highlights, occupied/reserved indicators, focused input states, and primary operational actions.
- **Secondary (`#8c9ba5`)**: Anodized slate. Used for metadata tags, column headers, secondary actions, and structural boundaries.
- **Neutral Base (`#14171a`)**: Deep graphite foundation. Surfaces scale subtly through `#1b1f24` (card/row surface), `#232830` (elevated panels/viewfinder chrome), and `#2e3540` (borders/dividers).
- **Functional Semantics**:
  - `Available / Open`: `#34d399` (Clear, muted emerald; never neon)
  - `Occupied / Active`: `#e5a93c` (Core amber)
  - `Violation / Overstay / Error`: `#f87171` (Clean crimson)
  - `Maintenance / Offline`: `#64748b` (Neutral cool grey)

## Typography

Typography establishes an unambiguous distinction between data points and operational content:

- **Space Grotesk** is deployed for slot identifiers (e.g., `BAY-B04`, `LEVEL-02`), primary numeric readouts, section titles, and table column definitions. It carries an engineered, technical character without descending into unreadable monospace gimmicks.
- **Inter** handles high-density tabular data, record values, logs, and relational foreign-key references where sustained reading comfort and optical neutrality are required.
- All table headers and slot codes enforce uppercase formatting with controlled positive letter-spacing (`0.04em` to `0.08em`) to guarantee legibility at a distance or across dense monitoring grids.

## Layout & Spacing

The layout is built on a 12-column fluid grid system optimized for information density and fast visual scanning.

- **Desktop (1280px+)**: 12-column layout with `1.5rem` gutters and margins. The screen is segmented into clear structural panels: primary slot matrix/visualizer (8 columns) alongside active telemetry, camera viewfinder, and selected entity records (4 columns). Full-width tabular views occupy the lower quadrant.
- **Tablet (768px - 1023px)**: 8-column layout. Camera viewfinder and detail inspection panels transition below the bay grid or collapse into tabbed side sheets.
- **Mobile (< 768px)**: Single column with persistent status bar and simplified list/card bay views. Margins compress to `1rem`.

Spacing principles:
- Internal panel padding strictly adheres to `space-md` (`0.75rem`) for compact records and `space-lg` (`1.25rem`) for major container borders.
- Zero extraneous white space: layouts prioritize compact data proximity so operators do not need to scroll to correlate camera feeds with row data.

## Elevation & Depth

This system avoids floating drop shadows and blur-heavy glassmorphism in favor of **structural tonal layering** and **crisp low-contrast outlines**:

- **Ground Level (`#14171a`)**: Canvas root and main workspace background.
- **Surface Level 1 (`#1b1f24`)**: Table bodies, data grids, and bay grid housings. Delineated by a solid 1px border (`#2a3038`).
- **Surface Level 2 (`#232830`)**: Elevated cards, camera viewfinder bezels, filter toolbars, and modal sheets. Bordered with a subtle `#353d48`.
- **Active State Elevation**: Interactive rows or focused parking bays use a 1px solid inner/outer rule in `#e5a93c` with no blur, maintaining a hard, architectural outline.
- **Shadows**: Only applied to floating contextual menus (`0 4px 16px rgba(0, 0, 0, 0.4)`), keeping the general viewport flat, grounded, and legible.

## Shapes

The interface embraces a strict, architectural geometry:
- Base border radius is set to **Soft (`roundedness: 1`)**, delivering `4px` corner radii on standard inputs, slot cards, and table badges, with `8px` on main operational containers.
- Viewfinder reticles, parking slot frames, and table records retain squared or minimally rounded silhouettes to evoke physical terminal screens and precision sensor monitors.
- Status dots and camera recording indicators remain true circles (`50%`).

## Components

### Parking Slot Grid & Bay Indicators
- **Bay Cell**: Rectangular card with 4px radius, framed by a 1px border (`#2e3540`).
- **Header**: Contains bold slot ID (`Space Grotesk`, `label-bay`, e.g., `A-12`) alongside a small hardware sensor indicator dot.
- **Status State**:
  - `Vacant`: Border in `#2e3540`, text `#8c9ba5`, with an emerald dot.
  - `Occupied`: 1px solid `#e5a93c` border, subtle `#e5a93c` 8% background wash, displaying vehicle plate snippet and duration.
  - `Reserved/Staff`: 1px dashed `#8c9ba5` border.
- **Hover/Select**: Border hard-shifts to solid white or vibrant amber with zero animation delay.

### Camera Viewfinder Panel
- **Frame**: Deep `#0f1215` fill enclosed in `#2e3540` border.
- **Overlays**: Subtle thin corner-reticle markings (white, 40% opacity). Top-left displays camera ID (`CAM-04 ENTRY LANE`) in `label-code`; top-right shows real-time timestamp and live status indicator.
- **License Plate Recognition (ANPR) Box**: A bounding box in `#e5a93c` pinpointing detected plates with an attached pill chip displaying OCR text (e.g., `[ 7XYZ890 - 98.4% ]`).

### Data Tables (Relational Database Views)
- **Container**: Bordered table block with `#1b1f24` background.
- **Header**: `#14171a` background, 32px height. Text rendered in uppercase `label-table-header` with `#8c9ba5` fill.
- **Rows**: Fixed 40px height for dense scanning. Separated by hairline dividers (`#232830`). Alternating hover state shifts row background to `#232830`.
- **Keys & References**: Foreign keys (e.g., `slot_id`, `driver_id`) are displayed in `Space Grotesk` with an amber tint on hover to signal navigation to related records.

### Buttons & Inputs
- **Primary Button**: Solid `#e5a93c` background with `#14171a` bold text (`Space Grotesk`). Flat, tactile hover to `#d89b30`.
- **Secondary / Ghost Button**: Transparent background, 1px `#353d48` border, `#8c9ba5` text. Hover yields white text and `#2e3540` background.
- **Search & Filter Inputs**: 36px height, dark graphite fill (`#14171a`), 1px `#2e3540` border. Focus transitions border cleanly to `#e5a93c`.

### Status Badges & Chips
- Compact, flat pills (4px radius) with `11px` uppercase type.
- Backgrounds use a 12% tint of their respective status color (`#e5a93c` for active, `#34d399` for clear, `#f87171` for violation), paired with a solid text label in that same hue.