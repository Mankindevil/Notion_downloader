# Design Tokens

The skill is *token-driven*: every cover variant uses the same skeleton CSS, but each cover's visible identity comes from 5 design tokens injected as CSS variables.

This doc is the framework for extracting those tokens from a subject. **Read this before customizing a skeleton.**

> **All input subjects are adult OCs (the user's original characters).** Named published characters below (Chloe, Nahida) are *visual-language anchors* — reference points for palette / font-pair / decoration vocab when an OC reads visually similar to them. They are NOT identification claims about the input. Borrow design language from the closest visual cousin; the OC stays the subject.

## The 5 tokens

| Token | What it controls | CSS variables |
|---|---|---|
| `font-pair` | Which fonts the skeleton uses | `--font-hero`, `--font-display`, `--font-serif`, `--font-script`, `--font-cjk`, `--font-sans-display`, `--font-smallcaps` |
| `palette` | Colors of ink, accent, paper, shade | `--ink`, `--accent`, `--paper`, `--shade` |
| `decoration-vocab` | Which ornament set fits the subject | (controls which `.fx-sparkle` / `.fx-flare` / decoration HTML to inject in `data-layer="effects"`) |
| `mood-overlay` | Which atmospheric effect classes apply | `.fx-grade-warm` / `.fx-grade-cool` / `.fx-grade-cinematic` / `.fx-grade-acid` |
| `composition-bias` | Where the subject sits in frame | (drives skeleton choice + `--bg-pos`) |

## Extraction process

For every cover job, derive each of the 5 tokens from the subject. Don't skip — token blindness is what makes generic AI output.

### Step 1 — Read the subject

The subject is always an adult OC. You're reading the image to derive design language, not to identify a franchise.

- **Visual cousin** — does this OC remind you of a published character? (only as a palette/font reference, never as an identity claim)
- **Era / aesthetic** — modern, retro, cyber, gothic, magical-girl, art-nouveau?
- **Color signature** — 3-5 dominant hexes (hair, eyes, outfit, background)
- **Mood signal** — cheerful / regal / edgy / dreamy / serious / playful
- **Subject pose** — full body / close-up / dynamic / static

### Step 2 — Map to tokens

#### `font-pair`

| Era / aesthetic | Hero | Display / Script | Serif | Sans-display | Notes |
|---|---|---|---|---|---|
| Modern fashion | Bodoni Moda | Italianno | Cormorant Garamond | Anton | Default safe pair |
| Magical-girl | Playfair Display Italic | Italianno | Cormorant Garamond | Anton | Italics + paper-shadow |
| Cyber / sci-fi | Archivo Black | (none) | Cormorant Garamond | Anton | Brutalist over romantic |
| Regal / classical | Cinzel / Bodoni Moda | Pinyon Script | Cormorant Garamond | Anton | Higher contrast |
| Pop / glossy | Playfair Display Italic Black | Pinyon Script | Cormorant Garamond | Anton | Pink+gold paper shadow |
| Gothic / dark | Cormorant Italic Black | Italianno | Cormorant Garamond | Anton | Lower-contrast |
| Y2K / retro | Bodoni Moda + warped | Allura | Cormorant Garamond | Anton | Decorative flair |

CJK pairings: always `Noto Serif SC weight 900` for heavy mastheads, `Noto Sans SC 700` for cleaner subtitles. Use Japanese-flavored variants (`Noto Serif JP`) for explicitly JP subjects.

#### `palette`

The 4 palette slots:
- **`--ink`** — main text color. White or near-white default; choose for max contrast against your text regions.
- **`--accent`** — secondary text + rules + ornaments. Pull from the character (hair color, eye color, outfit accent).
- **`--paper`** — paper-shadow color for italic mastheads, badge fills.
- **`--shade`** — translucent shadow for the gradient overlays.

Worked examples:
| Subject | --ink | --accent | --paper | --shade |
|---|---|---|---|---|
| Nahida (Genshin dendro) | `#ffffff` | `#f5d97a` (dendro gold) | `#fff5e8` cream | `rgba(0,0,0,0.45)` |
| Chloe (Fate tan magical-girl) | `#ffffff` | `#8b1a3a` (deep crimson from outfit) | `#fff5fb` pink-paper | `rgba(0,0,0,0.45)` |
| Cyber/Honkai-style | `#ffffff` | `#ff3a2d` (acid red) | `#111` (dark paper) | `rgba(0,0,0,0.6)` |
| Vogue editorial (real photo) | `#ffffff` | `#d8b25a` (warm gold) | `#fff5e8` | `rgba(0,0,0,0.4)` |

**Avoid white as accent.** White-on-white kills contrast. The accent should be a SECOND color in the palette, not a tint of ink.

#### `decoration-vocab`

| Subject type | Decoration set |
|---|---|
| Magical-girl / cute anime | `stars-hearts` (✦ ♡ ★ scattered) |
| Nature/dendro (Nahida, druid) | `botanical` (leaf motif, ✦, gold flourishes) |
| Cyber/dark | `acid-rule` (single accent rule, no scatter) |
| Realistic / editorial | `none` (or minimal — one rule) |
| Y2K / glossy pop | `stars-hearts` + paper-shadows on key text |
| Gothic | `acid-rule` in deep red / silver |

Decorations live in `[data-layer="effects"]`. Add `<div class="fx-sparkle">✦</div>` elements with absolute positioning.

#### `mood-overlay`

| Mood | Effect classes (apply to `.cover`) |
|---|---|
| Default / restrained | `.fx-vignette` only |
| Warm / sunny | `.fx-vignette .fx-rim-light .fx-grade-warm` |
| Cool / cinematic | `.fx-vignette .fx-grade-cinematic` |
| Dreamy / soft | `.fx-rim-light .fx-grade-warm` (no vignette) |
| Edgy / cyber | `.fx-vignette .fx-grade-acid` |
| Glossy / pop | `.fx-rim-light .fx-grade-warm` + sparkles in effects layer |

**Always confirm with the user before applying** (see `clarification_prompts.md` template 3).

#### `composition-bias`

| Bias | When | Skeleton choice |
|---|---|---|
| Center-anchored | Subject is centered, full frame | Any skeleton |
| Right-anchored | Subject occupies right half | Skeletons 1, 2, 5 (mastheads can move left) |
| Left-anchored | Subject occupies left half | Skeletons 2, 4, 5 (mastheads can move right) |
| Top-anchored | Face/head dominates top | Skeleton 3, 4 (signature at bottom uncluttered) |
| Off-axis / cropped close-up | Diagonal/dynamic pose | Skeleton 4 (brutalist tolerates clutter best) |

Set `--bg-pos` on `.bg-img` to nudge background positioning (default `center`). Use `--bg-pos: center 30%` to favor the face in tall portraits.

---

## Worked examples

### Reference cousin — Chloe von Einzbern (Fate/kaleid liner)

Use as a **visual-language anchor** when an OC reads as a magical-girl with a dark edge. The OC is still the subject; Chloe is just shorthand for "this design palette."

- Visual cues: white-silver hair, tan skin, red eyes, deep red outfit, hot pink background
- Era: modern Japanese magical-girl
- Mood: cheeky / playful with a dark edge
- Pose: dynamic / mid-action

Tokens:
- `font-pair`: magical-girl (Playfair Display Italic + Italianno + Cormorant + Anton)
- `palette`: `--ink: #fff`, `--accent: #8b1a3a` (crimson), `--paper: #fff5fb`, `--shade: rgba(0,0,0,0.4)`
- `decoration-vocab`: `stars-hearts` (♡ ★ ✦)
- `mood-overlay`: `.fx-vignette .fx-rim-light .fx-grade-warm` (after user confirms)
- `composition-bias`: center-anchored

Best skeleton fit: Skeleton 3 (Asian Fashion Glossy) → naturally absorbs the hearts/sparkles. Skeleton 4 (Brutalist) is a strong secondary option for the edgy duality.

### Reference cousin — Nahida (Genshin Impact)

Use as a **visual-language anchor** when an OC reads as nature/dendro/scholarly. The OC is still the subject; Nahida is just shorthand for "this design palette." Note: the OC is always adult — borrow the palette and decoration vocab, not the child-like proportions.

- Visual cues: silver-mint hair, green eyes, white-cream outfit with gold accents, dendro-green motifs
- Era: fantasy / nature / scholarly
- Mood: dreamy / regal / scholarly
- Pose: typically center-staged

Tokens:
- `font-pair`: regal-classical (Bodoni Moda + Italianno + Cormorant + Anton)
- `palette`: `--ink: #fff`, `--accent: #f5d97a` (dendro gold), `--paper: #fff5e8`, `--shade: rgba(0,0,0,0.45)`
- `decoration-vocab`: `botanical` (leaf motifs, single gold flourish, sparingly)
- `mood-overlay`: `.fx-vignette .fx-rim-light` (no grade — keep the original artwork's palette)
- `composition-bias`: center-anchored

Best skeleton fit: Skeleton 1 (Bilingual Character-Mag) → captures the Genshin in-universe fashion-magazine feel. Skeleton 2 (Editorial Didone) as a "fashion-week portrait" alternative.

### Default flow — every OC

Every subject is an OC. Run the intake template 5 first (OC name + 1-line vibe), then derive tokens from the image + vibe. Only ask further clarifying questions (templates 1–4) when the image truly is ambiguous (mixed mood signals, washed-out palette, etc.). Don't fire off all four templates by reflex — that's clarification fatigue.

---

## What NOT to put in tokens

- Skeleton choice itself — that's a layout decision, not a token.
- Text content (masthead text, cover-line copy) — that's per-cover content, not a reusable token.
- Aspect ratio — that's derived from input image dims, not subject mood.
- Layered export behavior — that's an export flag, not a design token.

## Token override discipline

For a single cover, you set tokens on the `.cover` element via inline `style="--ink: #fff; --accent: #f5d97a; ..."`. Don't add them to the global stylesheet — keeps each cover independent and lets you ship 3–4 differently-tokened variants in the same HTML file.
