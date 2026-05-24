# Editorial Typography

A cover's voice is its fonts. The masthead choice signals what kind of magazine this is *before* a single word is read. Pair fonts the way real magazines do — and avoid the Inter/Roboto/Arial trap.

## Mastheads by flavor

### Didone (Vogue / Harper's Bazaar / Numero)
High-contrast modern serif — thin horizontals, thick verticals. Defines the high-fashion editorial look.
- **Bodoni Moda** (Google Fonts) — closest to Vogue/Bazaar's actual mastheads. Use weight 700–900, optical size 96.
- **Playfair Display Black** — a softer Didone, good fallback.
- **Libre Caslon Text** — when you want Didone-adjacent but slightly warmer.

Usage: all-caps, centered, very large (200–300px on a 1240px cover). Letter-spacing 0.01em.

### Italic Script (character-mags, romantic flair)
Calligraphy/script display for in-universe magazine names or character-name signatures.
- **Italianno** — flowy connected italic, classic magazine-cover-bottom signature look.
- **Pinyon Script** — finer, more delicate, good for Asian-glossy mastheads.
- **Allura** — Pinyon-adjacent, slightly more confident.
- **Great Vibes** — pop-glossy; tends to look "cheap" if oversized — keep big or small, not medium.

Usage: 180–260px for masthead, 60–120px for cover-star signature at bottom. Always paired with a serif support font, never another script.

### Italic Serif (cover lines, hero headlines)
The workhorse for the hero coverline. Italic gives motion, serif gives editorial weight.
- **Cormorant Garamond Italic** (700 or 900) — the most versatile. Editorial, slightly literary.
- **Playfair Display Italic** (700) — bolder, more dramatic.
- **Bodoni Moda Italic** (700) — when the masthead is also Bodoni; keeps the family.

Usage: 36–90px for hero headlines, italic, line-height ~0.95 (tight). Subtitles drop to Cormorant Regular 16–22px.

### Roman Small Caps (datelines, taglines, signature subtitles)
The "official magazine" text — datelines, "September 2026 · Issue 12", "Special guest from Sumeru".
- **Marcellus SC** — classic small-caps serif, widely spaced.
- Cormorant Garamond all-caps with manual letter-spacing 0.4em as an alternative.

Usage: 14–22px, letter-spacing 0.3–0.5em, color = ink or accent.

### Geometric Sans (avant-garde, brutalist)
Tight, heavy, condensed sans-serif for i-D/Dazed/Numero Homme.
- **Anton** — closest free analog to Druk. Heavy condensed, all-caps.
- **Oswald 700** — slightly more refined.
- **Inter Black 900** — when you want clean modern instead of brutalist.

Usage: huge (160–220px), often lowercase (i-D-style) for shock, or all-caps for brutalist. Letter-spacing -0.02em to -0.04em (negative = tighter).

### CJK Serif / Sans (bilingual mastheads, sub-mastheads)
- **Noto Serif SC** weight 900 — for 时尚 / 原神 / etc. heavy CJK display.
- **Noto Serif JP** weight 700 — for Japanese.
- **Noto Sans SC** weight 900 — for cleaner modern CJK.

Usage: weight 900 for mastheads, weight 700 for sub-mastheads, 24–88px depending on placement.

## Pairing rules

### Two fonts max for cover lines
A masthead font + a cover-line font. Datelines, small text, and signatures can reuse one of those two. Three families is the upper bound — four reads as a font menu.

### Pair by contrast, not similarity
The hero font + support font should differ on at least one axis: weight class (Black + Regular), family (Serif + Sans), or stress (Italic + Roman). If they're too similar, the hierarchy collapses.

Good pairs:
- Bodoni Moda Black + Cormorant Garamond Italic (Didone + literary italic — classic Vogue)
- Italianno + Marcellus SC (script + small-caps — bilingual character-mag)
- Anton + Cormorant Italic (brutalist sans + romantic italic — avant-garde contrast)
- Playfair Display Italic Black + Noto Serif SC Heavy (Western italic serif + heavy CJK — glossy Asian)

Bad pairs (avoid):
- Two scripts (Italianno + Allura)
- Two Didones (Bodoni Moda + Playfair Display Black — they fight)
- Anything + Inter/Roboto/Arial as a "neutral" — they read as un-chosen

## Sizes that work on 1240×1650

| Element | Size range | Tightness |
|---|---|---|
| Didone masthead (single word) | 200–320px | 0.01em |
| Script masthead | 180–260px | -0.01em |
| CJK masthead | 60–90px | 0.08em |
| Hero coverline | 48–96px | -0.01em |
| Supporting coverline | 28–48px | 0 |
| Coverline subtitle | 16–22px | 0.01em |
| Cover-star signature script | 140–260px | -0.01em |
| Dateline / small caps | 14–22px | 0.3–0.5em |
| Issue number / tagline | 12–18px | 0.4em |

## Color rules for text on photo backgrounds

- **White ink** is the safest default — works on most subject photos.
- **Accent color text** (gold / red / character-derived) should only be used on 1–2 elements per cover. The rest stay white or near-white. Too much color competing with the image flattens the cover.
- **Shadow vs no shadow** — use a subtle soft shadow (`0 4px 18px rgba(0,0,0,0.35)`) only when the text crosses a busy region. Don't shadow everything — it's a crutch.
- **Outline strokes** are usually wrong on a magazine cover (they're a kids'-sticker move). Exception: glossy Asian fashion D with one paper-shadow on the masthead, see template C.
