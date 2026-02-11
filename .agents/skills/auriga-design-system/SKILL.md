---
name: auriga-design-system
description: Enforces the "Ivy League SaaS" design system for Auriga's UI. Use when building, reviewing, or styling React/Next.js components, pages, or layouts in auriga-web. Covers colors, typography, component styling, iconography, and layout patterns using Tailwind CSS.
---

# Auriga "Ivy League SaaS" Design System

Premium, academic, trustworthy UI — the "Digital Acceptance Letter" aesthetic.

## Core Aesthetic

**Vibe:** Premium, Academic, Trustworthy, High-Signal, "Clean Paper."

**Avoid:** Generic startup blues, dark mode by default (unless specified), playful/cartoonish elements, heavy gradients.

## Color Palette

| Role | Classes | Notes |
|------|---------|-------|
| Background | `bg-[#FBFBF9]` or `bg-orange-50/10` | Warm, off-white "Paper" — never sterile white |
| Primary Brand | `text-orange-600`, `bg-orange-500`, `border-orange-200` | Burnished Orange |
| Success / Financial | `text-emerald-700`, `bg-emerald-50` | **Strictly** for money, acceptance, and match scores |
| Headlines | `text-gray-900` | Deep Charcoal |
| Body Text | `text-gray-600` | Muted Slate |
| **Never** | `#000` / pure black | — |

## Typography

### Headlines — Serif ("The Voice")

Use **Merriweather** or **Playfair Display** for H1/H2/H3.

- Bold weight, centered on landing pages
- Tight tracking (`tracking-tight`)
- Example: `font-serif text-3xl font-bold tracking-tight text-gray-900`

### UI & Data — Sans-Serif ("The Brain")

Use **Inter** or **Geist** for body text, buttons, data tables.

- Clean, legible
- `font-medium` for labels
- Example: `font-sans text-sm font-medium text-gray-600`

## Component Styling

### Cards

```
bg-white rounded-xl border border-gray-100 shadow-sm
hover:shadow-md transition-all
```

Use `rounded-2xl` for hero/feature cards.

### Buttons

| Variant | Classes |
|---------|---------|
| Primary | `rounded-full bg-orange-600 text-white shadow-orange-500/20 shadow-sm` |
| Secondary | `rounded-full border border-gray-200 hover:bg-gray-50` |

### Inputs

```
bg-white border border-gray-200 rounded-lg focus:ring-orange-500
```

## Iconography

Use **Lucide React** with thin strokes (`strokeWidth={1.5}`).

Wrap icons in circular containers:

```tsx
<div className="w-10 h-10 rounded-full bg-orange-50 flex items-center justify-center">
  <Icon className="w-5 h-5 text-orange-600" strokeWidth={1.5} />
</div>
```

**No cartoons.** Use abstract geometric shapes, architectural lines, or frosted glass effects for imagery.

## Layout Patterns

| Pattern | When to Use |
|---------|------------|
| **Master-Detail** | Complex data — Sidebar (list) + Main View (detail) |
| **Bento Grid** | Feature showcases — distinct, bordered rectangular cells |
| **Sidebar Navigation** | App chrome — `bg-gray-50` sidebar to separate nav from content |

## Quick Reference

```tsx
// Card with the full "Ivy League" treatment
<div className="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-all p-6">
  <h2 className="font-serif text-2xl font-bold tracking-tight text-gray-900">
    Title
  </h2>
  <p className="mt-2 font-sans text-sm text-gray-600">
    Description text
  </p>
  <button className="mt-4 rounded-full bg-orange-600 px-6 py-2 text-sm font-medium text-white shadow-sm shadow-orange-500/20 hover:bg-orange-700 transition-colors">
    Action
  </button>
</div>
```

## Checklist

When building or reviewing Auriga UI, verify:

- [ ] Backgrounds use warm paper tones, not pure white
- [ ] No pure black (`#000`) anywhere
- [ ] Headlines use serif font
- [ ] Body/UI text uses sans-serif font
- [ ] Cards have `rounded-xl`+, subtle border, soft shadow
- [ ] Primary buttons are pill-shaped (`rounded-full`) with orange
- [ ] Emerald green used **only** for financial/acceptance/match data
- [ ] Icons are Lucide with `strokeWidth={1.5}`
- [ ] Icons wrapped in circular containers where appropriate
- [ ] Layout follows Master-Detail, Bento, or Sidebar patterns
- [ ] No cartoons, playful elements, or heavy gradients
- [ ] Responsive across all screen sizes
