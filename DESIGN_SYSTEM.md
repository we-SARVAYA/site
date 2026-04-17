# SARVAYA — Design System Reference

Complete design specification for the SARVAYA brand. Use this file as the single source of truth when building any sub-site that needs to look and feel identical to [sarvaya.in](https://sarvaya.in/).

Source of tokens: `css/style.css` (`:root` block), `css/pages.css`, `index.html`.

---

## 1. Design Philosophy

| | |
|---|---|
| **Mood** | Dark, editorial, premium agency. Cinematic but restrained. |
| **Voice** | Confident, lowercase subheads, big display headlines. |
| **Contrast** | Deep near-black backgrounds vs. lime-green accent. White/muted grey text hierarchy. |
| **Motion** | Slow, springy easing (`cubic-bezier(0.16, 1, 0.3, 1)`). Nothing jitters. |
| **Texture** | Subtle film-grain overlay at 2.8% opacity. Soft radial glows behind hero sections. |
| **Cursor** | Custom lime dot + ring follower (hidden on touch devices). |

---

## 2. Color Tokens

Copy these verbatim. They are the single source of truth.

```css
:root {
  /* Backgrounds */
  --bg-primary:      #060606;   /* page background */
  --bg-secondary:    #0c0c0c;   /* alternating section bg */
  --bg-card:         #111111;   /* card / surface */
  --bg-card-hover:   #151515;   /* card hover */

  /* Text */
  --text-primary:    #f0f0f0;   /* headings, primary copy */
  --text-secondary:  #8a8a8a;   /* body copy, nav links */
  --text-muted:      #555555;   /* captions, dates, metadata */

  /* Accent — this is THE brand color */
  --accent:          #c8ff00;   /* lime — CTAs, highlights */
  --accent-hover:    #d4ff33;   /* CTA hover */

  /* Borders */
  --border:          #1a1a1a;   /* default 1px stroke */
  --border-light:    #242424;   /* hover stroke, dividers */
}
```

### Derived / semi-transparent accents (used everywhere — don't change)

| Usage | Color |
|---|---|
| Soft accent fill (pills, chips) | `rgba(200, 255, 0, 0.06)` → `rgba(200, 255, 0, 0.12)` on hover |
| Accent border | `rgba(200, 255, 0, 0.18)` → `rgba(200, 255, 0, 0.35)` on hover |
| Accent glow (radial bg) | `rgba(200, 255, 0, 0.04)` → `0.06` |
| Accent card halo (on hover) | `rgba(200, 255, 0, 0.25)` border + `rgba(200, 255, 0, 0.08)` outer ring |
| CTA drop shadow | `0 8px 30px rgba(200, 255, 0, 0.2)` |
| Card watermark number | `rgba(255, 255, 255, 0.03)` → `rgba(200, 255, 0, 0.07)` on hover |
| Avatar bg | `rgba(255, 255, 255, 0.05)` |
| Secondary badge (yellow — testimonials) | `#facc15` with `rgba(250, 204, 21, 0.06)` fill |
| WhatsApp float | `#25D366` with `0 4px 20px rgba(37, 211, 102, 0.4)` glow |

---

## 3. Typography

### Fonts (loaded from Google Fonts)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Syne:wght@400;500;600;700;800&display=swap" rel="stylesheet">
```

```css
--font-main:    'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-display: 'Syne', 'DM Sans', sans-serif;
```

- **DM Sans** → body, nav, forms, buttons, captions.
- **Syne** → all headings, logo, large numbers, card titles, badges.

### Type scale

| Role | Family | Size | Weight | Letter-spacing | Line-height | Notes |
|---|---|---|---|---|---|---|
| Hero title | Syne | `clamp(60px, 12vw, 140px)` | 900 | `-2px` | `1` | White→grey gradient text (see §7) |
| Page hero title | Syne | `clamp(40px, 8vw, 72px)` | 800 | `-2px` | `1.1` | Same gradient |
| Section title | Syne | `clamp(36px, 5vw, 56px)` | 700 | `-1.5px` | `1.1` | `margin-bottom: 56px` |
| Mid title (24hrs, CTA) | Syne | `clamp(28px, 4vw, 42px)` | 700 | `-0.5px` | — | |
| Intro title | Syne | `clamp(28px, 4vw, 44px)` | 700 | `-1px` | `1.2` | |
| Card title (work) | Syne | `22px` | 700 | — | — | Featured variant: `32px` |
| Card title (service/step) | Syne | `20px` | 600 | — | — | |
| Card title (blog/feature/about) | Syne | `18px` | 600 | — | `1.5` | |
| Legal H2 | Syne | `22px` | 700 | `-0.3px` | — | |
| Logo | Syne | `18px` | 700 | `0.5px` | — | |
| **Body (large)** | DM Sans | `20px` | 400 | — | `1.7` | About paragraph |
| Body (default) | DM Sans | `16–17px` | 400 | — | `1.7–1.8` | Section copy |
| Body (card) | DM Sans | `14–15px` | 400–500 | — | `1.7` | Card descriptions |
| Nav link | DM Sans | `14px` | 500 | — | — | `color: --text-secondary` |
| Section label | DM Sans | `11px` | 500 | `3px` | — | UPPERCASE, `opacity: 0.7`, `--text-muted` |
| Tag / pill text | DM Sans | `11–14px` | 500–600 | `0.3–1.2px` | — | Often UPPERCASE |
| Metric number | Syne | `clamp(48px, 6vw, 72px)` | 800 | — | `1` | Accent color |
| Card number watermark | Syne | `72px` (grid) / `120px` (featured) | 900 | — | `1` | Super low opacity |
| Loader text | Syne | `clamp(28px, 5vw, 48px)` | 800 | `8px` | — | |

### Gradient text recipe (hero titles)

```css
background: linear-gradient(135deg, #ffffff 0%, #888888 100%);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
background-clip: text;
```

Page-hero variant uses `#ffffff → #777777`.

### Body defaults

```css
body {
  font-family: var(--font-main);
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

---

## 4. Spacing & Layout

### Container

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;           /* 24px for .nav-container */
}
/* @media (max-width: 480px) → padding: 0 16px */
```

### Section vertical padding (the rhythm of the site)

| Section | Desktop padding | Mobile (<768) |
|---|---|---|
| Hero | `120px 24px 80px`, `min-height: 100vh` | `100px 20px 60px`, `min-height: 100dvh` |
| Page hero | `180px 0 80px` (tall: `180px 0 100px`) | `140px 0 60px` |
| About / Services / Work / Blog / 24hrs / FAQ / Contact CTA | `160px 0` | `100px 0` |
| Testimonials | `120px 0` | `100px 0` |
| Content (sub-pages) | `140px 0` | `100px 0` |
| Metrics | `100px 0` | `80px 0` |
| Footer | `80px 0 32px` | — |

### Grid gaps

- Cards grid: `20–24px`
- About grid (2-col): `60px`
- Contact grid (2-col `1.1fr 0.9fr`): `60px`
- Footer links: `80px` (desktop) / `32–48px` (tablet/mobile)

---

## 5. Radius Scale

```css
--radius-sm:   8px;    /* logo icon, small inputs */
--radius-md:  12px;    /* FAQ items, form inputs */
--radius-lg:  16px;    /* standard cards */
--radius-xl:  24px;    /* work cards, contact form wrap */
--radius-full: 9999px; /* all pills, badges, CTAs */
```

---

## 6. Shadows

The site is largely shadowless at rest — shadow is a **hover reward**, not a default. Use these exact values:

| Context | Shadow |
|---|---|
| CTA hover (lime) | `0 8px 30px rgba(200, 255, 0, 0.2)` |
| Work card hover | `0 24px 80px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(200, 255, 0, 0.08)` |
| WhatsApp float (rest) | `0 4px 20px rgba(37, 211, 102, 0.4)` |
| WhatsApp float (hover) | `0 8px 30px rgba(37, 211, 102, 0.5)` |
| Testimonials yellow badge hover | `0 4px 20px rgba(250, 204, 21, 0.1)` |

Cards at rest use `border: 1px solid var(--border)` — NOT a box-shadow — and transition border-color on hover.

---

## 7. Motion / Transitions

```css
--transition:      0.4s cubic-bezier(0.16, 1, 0.3, 1);
--transition-slow: 0.6s cubic-bezier(0.16, 1, 0.3, 1);
```

Every interactive element uses one of these two. Do not use `ease`, `ease-in-out`, or `linear` for UI transitions (except progress bar, carousels, and cursor dot which use `0.05s linear` / `0.1s ease` respectively).

### Scroll-reveal classes (set `opacity:0` until `.visible` is added via IntersectionObserver)

| Class | From | To |
|---|---|---|
| `.fade-up` | `translateY(40px)` + opacity 0 | `translateY(0)` + opacity 1 |
| `.slide-left` | `translateX(-60px)` | `translateX(0)` |
| `.slide-right` | `translateX(60px)` | `translateX(0)` |
| `.scale-in` | `scale(0.9)` + opacity 0 | `scale(1)` + opacity 1 |
| `.blur-in` | `blur(12px)` + `translateY(20px)` | `blur(0)` + `translateY(0)` |
| `.text-reveal` | child `translateY(105%)` under `overflow:hidden` | `translateY(0)` |
| `.draw-line` | `scaleX(0)` origin left | `scaleX(1)` |

Durations: `0.8–0.9s` with the standard `cubic-bezier(0.16, 1, 0.3, 1)`.

### Keyframe animations

- **`loaderFade`** — 1.2s ease forwards, letter-spacing 16px→8px + fade in.
- **`scroll-logos`** — 25s linear infinite (`translateX(0 → -50%)`). Track is `width: max-content`, paired with fade-mask edges.
- **`scroll-testimonials`** — 40s linear infinite, `animation-play-state: paused` on hover.
- **`whatsapp-pulse`** — 2.5s infinite, `scale(1 → 1.15)` + opacity `0.4 → 0`.
- **`particleFloat`** — linear infinite per-particle, from `translateY(100vh)` to `translateY(-10vh) translateX(40px)`.

### Carousel edge masks (required for all looping rows)

```css
mask-image: linear-gradient(90deg, transparent, black 10%, black 90%, transparent);
-webkit-mask-image: linear-gradient(90deg, transparent, black 10%, black 90%, transparent);
```

---

## 8. Signature Effects

### Film grain overlay (on every page)

```html
<div class="grain-overlay"></div>
```

```css
.grain-overlay {
  position: fixed; inset: 0; z-index: 9990;
  pointer-events: none; opacity: 0.028;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 180px;
}
```

### Custom cursor (hide on touch via `@media (pointer: coarse)`)

- `.cursor-dot` — 6×6px lime, z-index 9998, scales to 12×12 on hover.
- `.cursor-ring` — 36×36px border `1.5px solid rgba(200, 255, 0, 0.3)`, grows to 52×52 on hover.
- `body { cursor: none }` globally.

### Scroll progress bar

- Fixed top, `height: 2px`, `linear-gradient(90deg, var(--accent), rgba(200, 255, 0, 0.6))`, z-index 1100.

### Hero radial glow (behind titles)

```css
.hero::before {
  content: ''; position: absolute;
  top: -50%; left: 50%; transform: translateX(-50%);
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(200, 255, 0, 0.06) 0%, transparent 70%);
  pointer-events: none;
}
```

Page-hero variant: `top: -40%`, `700px × 700px`, `rgba(200,255,0,0.04) → transparent 65%`.

### Floating particles (hero only)

`.hero-particle` = 3×3 (or 2×2 for `:nth-child(odd)`) circles, `background: rgba(200, 255, 0, 0.15)` (or `0.08`), animated by `particleFloat`.

---

## 9. Component Recipes

### 9.1 Button — Primary (lime CTA)

```css
display: inline-flex; align-items: center; gap: 8px;
padding: 16px 40px;              /* compact: 14px 36px | nav: 10px 24px */
background: var(--accent); color: #000;
font-weight: 700; font-size: 16px;
border-radius: var(--radius-full);
transition: all var(--transition);
```
```css
:hover {
  background: var(--accent-hover);
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(200, 255, 0, 0.2);
}
```
Bonus: add a white sheen wipe on hover via `::after` (see `.hero-cta::after` in style.css — `translateX(-100% → 100%)` on a `rgba(255,255,255,0.15)` overlay).

### 9.2 Button — Ghost / Outline ("View all")

```css
padding: 14px 36px;
border: 1px solid var(--border);
border-radius: var(--radius-full);
font-weight: 600; font-size: 15px;
color: var(--text-primary);
/* hover */
border-color: var(--accent); color: var(--accent); transform: translateY(-2px);
```

### 9.3 Pill / Tag (accent variant)

```css
padding: 10px 22px;
background: rgba(200, 255, 0, 0.06);
border: 1px solid rgba(200, 255, 0, 0.18);
border-radius: var(--radius-full);
font-size: 14px; font-weight: 500;
color: var(--accent); letter-spacing: 0.3px;
```
Hover: fill → `0.12`, border → `0.35`, `translateY(-2px)`.

### 9.4 Pill (neutral)

```css
padding: 12px 24px;
background: var(--bg-card);
border: 1px solid var(--border);
border-radius: var(--radius-full);
font-size: 14px; font-weight: 500;
color: var(--text-secondary);
```

### 9.5 Card — Base

```css
padding: 32px;
background: var(--bg-card);
border: 1px solid var(--border);
border-radius: var(--radius-lg);  /* 16px */
transition: all var(--transition);
```
Hover: `border-color: var(--border-light); transform: translateY(-4px);`

Service-card variant adds a top accent bar (`::before` scaleX 0→1) and a lime hover glow at cursor (`--glow-x / --glow-y` set via JS + radial gradient).

### 9.6 Card — Work (portfolio)

- Outer: `border-radius: var(--radius-xl)` (24px), split into `.work-card__visual` (image area with radial bg + 40px padding) and `.work-card__content` (28px 32px).
- Image scales `1 → 1.06`, brightness `0.95 → 1.05` on hover.
- Corner watermark number: Syne 72/120px, opacity ~3–7%.
- Hover shadow: see §6.
- Featured variant: `grid-template-columns: 1.2fr 0.8fr`, visual height 380px, title 32px.

### 9.7 Form input

```css
width: 100%;
padding: 14px 18px;
background: var(--bg-primary);
border: 1px solid var(--border);
border-radius: var(--radius-md);
color: var(--text-primary);
font-family: var(--font-main); font-size: 15px;
outline: none;
transition: border-color var(--transition);
```
Focus: `border-color: rgba(200, 255, 0, 0.4);`
Label: `13px / 600 / var(--text-secondary) / letter-spacing: 0.5px`.
Form wrap: `padding: 48px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-xl);`.

### 9.8 FAQ accordion

- Item: `border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-card);`
- Active border: `rgba(200, 255, 0, 0.3)`, icon rotates `45deg` (`+` → `×`), color → accent.
- Question padding: `24px 28px`; answer: `padding: 0 28px 24px; font-size: 15px; line-height: 1.8;`
- `.faq-answer { max-height: 0 → 300px; transition: max-height 0.4s ease; }`.

### 9.9 Nav bar

- `position: fixed; top: 0; padding: 16px 0; z-index: 1000;`
- On scroll (`.scrolled`): `background: rgba(10, 10, 10, 0.85); backdrop-filter: blur(20px); border-bottom: 1px solid var(--border); padding: 12px 0;`
- Nav links: `14px / 500 / var(--text-secondary)` with animated underline (`::after` 0→100% width, 1.5px high, accent color).

### 9.10 Footer

- `padding: 80px 0 32px; border-top: 1px solid var(--border);`
- Social icon: `32×32` circle, `background: var(--bg-card); border: 1px solid var(--border);` → on hover `border-color: rgba(200,255,0,0.3); color: var(--accent); translateY(-2px);`

### 9.11 Section label ("kicker")

```css
font-size: 11px; font-weight: 500;
color: var(--text-muted);
letter-spacing: 3px;
text-transform: uppercase;
opacity: 0.7;
margin-bottom: 20px;
```

### 9.12 Badge (page hero)

```css
padding: 8px 24px;
background: rgba(200, 255, 0, 0.08);
border: 1px solid rgba(200, 255, 0, 0.2);
border-radius: var(--radius-full);
font-family: var(--font-display);
font-size: 13px; font-weight: 700;
color: var(--accent); letter-spacing: 3px;
```

---

## 10. Responsive Breakpoints

| Break | Target |
|---|---|
| `max-width: 1024px` | tablet landscape — collapse 4-col → 2-col, 2-col → 1-col, shrink gaps |
| `max-width: 768px` | tablet portrait / mobile — hide nav links + nav CTA, show `.hamburger`, section padding `100px 0`, testimonial cards `300px` wide |
| `max-width: 600px` | small phones — force 1-col grids |
| `max-width: 480px` | compact phones — container padding `16px`, smaller tags/FAQ |
| `@media (pointer: coarse)` | disable custom cursor, restore native |

---

## 11. Z-index Scale

| Layer | z-index |
|---|---|
| Cookie banner | 9994 |
| WhatsApp float | 9995 |
| Cursor ring | 9997 |
| Cursor dot | 9998 |
| Page loader | 9999 |
| Grain overlay | 9990 |
| Scroll progress bar | 1100 |
| Navbar | 1000 |
| Mobile menu | 999 |
| Nav logo / hamburger | 1001 |

---

## 12. Drop-in for the sub-site (Next.js)

Put this in `src/app/globals.css` (or equivalent) **before** any component imports:

```css
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Syne:wght@400;500;600;700;800&display=swap');

:root {
  --bg-primary: #060606;
  --bg-secondary: #0c0c0c;
  --bg-card: #111111;
  --bg-card-hover: #151515;
  --text-primary: #f0f0f0;
  --text-secondary: #8a8a8a;
  --text-muted: #555555;
  --accent: #c8ff00;
  --accent-hover: #d4ff33;
  --border: #1a1a1a;
  --border-light: #242424;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-full: 9999px;
  --font-main: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-display: 'Syne', 'DM Sans', sans-serif;
  --transition: 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  --transition-slow: 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

* , *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

html { scroll-behavior: smooth; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }

body {
  font-family: var(--font-main);
  background-color: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.7;
  overflow-x: hidden;
}

a { color: inherit; text-decoration: none; }
img { max-width: 100%; height: auto; display: block; }

.container { max-width: 1200px; margin: 0 auto; padding: 0 32px; }
@media (max-width: 480px) { .container { padding: 0 16px; } }
```

### Optional: Tailwind mapping (`tailwind.config.ts`)

```ts
export default {
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#060606',
          secondary: '#0c0c0c',
          card: '#111111',
          'card-hover': '#151515',
        },
        text: {
          primary: '#f0f0f0',
          secondary: '#8a8a8a',
          muted: '#555555',
        },
        accent: {
          DEFAULT: '#c8ff00',
          hover: '#d4ff33',
        },
        border: {
          DEFAULT: '#1a1a1a',
          light: '#242424',
        },
      },
      fontFamily: {
        sans: ['DM Sans', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        display: ['Syne', 'DM Sans', 'sans-serif'],
      },
      borderRadius: {
        sm: '8px', md: '12px', lg: '16px', xl: '24px', full: '9999px',
      },
      boxShadow: {
        cta: '0 8px 30px rgba(200, 255, 0, 0.2)',
        'card-hover': '0 24px 80px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(200, 255, 0, 0.08)',
      },
      transitionTimingFunction: {
        brand: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      maxWidth: { container: '1200px' },
    },
  },
};
```

---

## 13. Checklist — "does my sub-site match?"

- [ ] Background is `#060606`, not pure `#000`.
- [ ] Accent is `#c8ff00`. Never `#d4ff33` at rest (that's hover only).
- [ ] All headings use **Syne**; all body/UI uses **DM Sans**.
- [ ] Hero titles have the white → grey gradient clip.
- [ ] Every CTA is a lime full-radius pill with `translateY(-2px)` + lime glow shadow on hover.
- [ ] Cards sit on `#111` with a `1px #1a1a1a` border — no box-shadow at rest.
- [ ] Every interactive transition uses `0.4s cubic-bezier(0.16, 1, 0.3, 1)`.
- [ ] Alternating sections toggle between `--bg-primary` and `--bg-secondary` with hairline borders between them.
- [ ] Section vertical padding is `160px 0` desktop / `100px 0` mobile (unless listed otherwise).
- [ ] Film-grain overlay (`opacity: 0.028`) is present on every page.
- [ ] Custom cursor is active on desktop and disabled via `@media (pointer: coarse)`.
- [ ] Carousels have the 10%/90% fade mask on both edges.
- [ ] Accent-tinted radial glow sits behind hero section.
- [ ] Section labels are `11px / 3px tracking / UPPERCASE / muted / 0.7 opacity`.
