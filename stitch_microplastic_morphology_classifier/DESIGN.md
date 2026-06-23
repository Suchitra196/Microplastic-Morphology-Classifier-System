---
name: Luminous Analytics
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#bacac5'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#859490'
  outline-variant: '#3c4a46'
  surface-tint: '#3cddc7'
  primary: '#57f1db'
  on-primary: '#003731'
  primary-container: '#2dd4bf'
  on-primary-container: '#00574d'
  inverse-primary: '#006b5f'
  secondary: '#9ad1cb'
  on-secondary: '#003734'
  secondary-container: '#144f4b'
  on-secondary-container: '#89bfba'
  tertiary: '#ffd1aa'
  on-tertiary: '#4b2800'
  tertiary-container: '#ffac5a'
  on-tertiary-container: '#744000'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#62fae3'
  primary-fixed-dim: '#3cddc7'
  on-primary-fixed: '#00201c'
  on-primary-fixed-variant: '#005047'
  secondary-fixed: '#b5ede7'
  secondary-fixed-dim: '#9ad1cb'
  on-secondary-fixed: '#00201e'
  on-secondary-fixed-variant: '#144f4b'
  tertiary-fixed: '#ffdcc0'
  tertiary-fixed-dim: '#ffb875'
  on-tertiary-fixed: '#2d1600'
  on-tertiary-fixed-variant: '#6b3b00'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding: 32px
  gutter: 24px
  margin-mobile: 16px
---

## Brand & Style

The visual identity for this design system is rooted in a "Deep Space" aesthetic—a fusion of technical precision and immersive depth designed for the Microplastic Morphology Classifier. It targets researchers and environmental scientists who require high-performance analytical tools.

The style is defined by **Glassmorphism** and **Futuristic Minimalism**. It utilizes a pitch-black canvas to allow data and microscopy imagery to emerge with high visual priority. The emotional response is one of "Sophisticated Insight": the UI feels like a high-end laboratory instrument or a next-generation orbital HUD. Key characteristics include:
- **Immersive Depth:** Large, soft background blurs in muted teals and greens suggest biological or oceanic environments.
- **Translucency:** UI elements utilize frosted glass effects to maintain context while layering complex information.
- **Technical Precision:** Thin strokes and high-contrast typography evoke the feeling of a microscopic lens.

## Colors

The palette is optimized for a dark-room laboratory environment, reducing eye strain while highlighting critical data points.

- **Background:** A pure charcoal-black (#0A0A0A) serves as the foundation.
- **Primary:** A vibrant Teal (#2DD4BF) is used sparingly for active states, data highlights, and glowing accents.
- **Secondary:** A deep Forest Green (#134E4A) is used for subtle gradients and secondary buttons.
- **Glass/Surface:** Containers use a semi-transparent black with a white-tinted border (12% opacity) to create a "glass" effect.
- **Typography:** High-contrast White (#FFFFFF) for headers and an off-white/gray (#A1A1AA) for body text to ensure legibility against the dark backdrop.

## Typography

Typography centers on clarity and technicality. 
- **Headlines:** Uses **Hanken Grotesk** for a sharp, contemporary look. Larger display sizes should use tighter letter spacing to create a more "engineered" feel.
- **Body:** **Inter** is utilized for its exceptional legibility in data-dense interfaces.
- **Metadata/Technical Labels:** **JetBrains Mono** is introduced for monospaced data, coordinates, and classification IDs to reinforce the scientific nature of the product.

All text should default to high-contrast white or light gray. Captions and labels should be treated with a slightly lower opacity (70-80%) to maintain hierarchy.

## Layout & Spacing

The layout follows a **Fluid Grid** model with generous inner-container padding to support the "Glassmorphism" effect. 

- **Grid:** A 12-column layout for desktop with 24px gutters. Elements should span columns to create distinct functional zones (e.g., classification sidebar, central image viewer, data visualization panel).
- **Rhythm:** An 8px base unit drives all spacing.
- **Safe Zones:** Background "glow" gradients should be positioned behind primary content areas to lead the eye toward the most important classification data.
- **Adaptive Strategy:** On mobile, the grid collapses to a single column, but the glass effect is preserved to maintain the brand identity. Padding reduces to 16px to maximize the viewing area of microscopic imagery.

## Elevation & Depth

Depth is achieved through **Backdrop Blurs and Tonal Stacking** rather than traditional shadows.

1.  **Level 0 (Base):** Deep black (#0A0A0A).
2.  **Level 1 (Substrate):** Soft, large-radius blurs (teal/green) that sit behind the UI.
3.  **Level 2 (Panels):** Semi-transparent surfaces with a `backdrop-filter: blur(20px)`. These panels feature a 1px solid border using a low-opacity white stroke to define the edges.
4.  **Level 3 (Interactive):** Hover states increase the border opacity and add a subtle inner glow (box-shadow: inset) to make the element appear "energized."

## Shapes

The design system uses **Rounded** (Level 2) geometry to balance the technical "coldness" of the dark theme with an approachable, modern feel.

- **Primary Containers:** 1rem (16px) corner radius.
- **Buttons & Small Elements:** 0.5rem (8px) corner radius.
- **Data Points:** Small circular markers for microplastic particle identification.

The interaction between the soft corners and the sharp 1px borders creates a high-end "machined" appearance.

## Components

### Buttons
Primary buttons should be high-contrast: white backgrounds with black text for maximum "pop." Secondary buttons use the translucent glass style with white borders.

### Cards
Cards are the primary structural element. They must utilize the backdrop blur and thin border. Headers within cards should be separated by a 1px horizontal line of the same border color.

### Input Fields
Fields are dark with a 1px border. Upon focus, the border transitions to the Primary Teal color with a subtle outer glow (neon effect).

### Chips & Badges
Classification badges (e.g., "Fragment," "Fiber," "Pellet") use high-saturation backgrounds with low opacity, paired with high-contrast text to ensure they are readable against the dark background.

### Data Visualization
Charts should use the Primary Teal and Secondary Green. Grid lines should be faint (5-10% white) to keep the focus on the data trends. Use the monospaced font for all axis labels.