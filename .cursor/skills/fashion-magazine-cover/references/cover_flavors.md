# Cover Flavors — Skeleton Archetypes

Five **starting skeletons** that feed the token system. Pick one per variant. Each skeleton is a layout structure — the *visible identity* comes from the design tokens you inject (see `design_tokens.md`).

For each flavor: the publications it's modeled on, the masthead style, the palette range it tolerates, the cover-line voice, and the failure modes. **The fonts and colors listed below are defaults — token overrides are how you make a Chloe-cover and a Nahida-cover look different even when they share a skeleton.**

> In v2 the skeletons are coded in `assets/cover_skeletons.html`. Each `.cover` has classes `skeleton-bilingual-cjk` / `skeleton-didone` / `skeleton-asian-glossy` / `skeleton-brutalist` / `skeleton-vertical`. CSS variables drive the visual identity — no hard-coded fonts/colors in the skeleton CSS.

---

## A — Bilingual Character-Mag

**Models:** Nahida-reference cover, Newtype, Megami Magazine, character-album bilingual mags from CN/JP fandom.

**Identity:** A fictional fashion magazine for an anime/game world. CJK masthead anchors the magazine's identity in the source-material culture; English italic-script masthead carries the romantic editorial flair. Cover lines treat in-universe lore as fashion news.

**Masthead:** CJK 时尚 + franchise name (原神 for Genshin, 崩坏 for Honkai, etc.) in Noto Serif SC weight 900. Paired with a giant italic-script English title (Italianno) — usually the franchise's English name or a tone-rhyming variant.

**Palette:** White ink + a warm gold (`#f5d97a`, `#e8b43a`) or character-derived accent. The subject's full illustration is the background, often with a subtle top + bottom gradient for legibility.

**Cover-line voice:** Mock in-universe fashion news.
- *"Monde idol in the new era"* (mock Mondstadt fashion week)
- *"High end customization in Liyue"* (mock Liyue couture)
- *"latest fashion · Art · Make up"* — single-word stack
- *"Inazuma is the country you absolutely don't want to miss"*

Italic serif (Cormorant Italic 700) for headlines, regular Cormorant for subtitles.

**Signature:** Character's name in huge italic script (Italianno) at the bottom, with a small Marcellus SC tagline ("Special guest from Sumeru"). The signature should be the second-loudest element after the masthead.

**Decoration:** A small badge top-left (round, gold-outlined, with an "x" + a tagline like "Super virtual auto blend crystal clothing"). A vertical Cormorant Italic line on the left margin ("Special issue of God").

**Avoid:** Too many cover lines (3 is plenty), making the CJK masthead too small (it needs to anchor the top), losing the character signature in clutter.

---

## B — High-Fashion Editorial

**Models:** Vogue, Harper's Bazaar, Numero, W Magazine.

**Identity:** Authoritative, restrained, confident. The masthead is the loudest thing on the cover by a wide margin. Cover lines are sparse — one hero, maybe 1–2 supporting — because the brand can afford negative space.

**Masthead:** Single huge Didone serif word (Bodoni Moda 900, 240–320px), all-caps, centered. Real models: VOGUE, BAZAAR, NUMERO, ELLE. For fictional or character mags use the franchise name in the same treatment, e.g., GENSHIN as a Vogue-style masthead.

**Palette:** White ink default. Optional warm gold (`#d8b25a`) or muted color for one accent line. The image dominates — text exists in service of the photograph.

**Cover-line voice:** Confident, minimal, slightly cryptic.
- *"Power Dressing"* (no subtitle needed)
- *"The September Issue"*
- *"The New Volume"*
- *"Inside: a portrait of [name]"*

Italic Bodoni for hero headlines, Marcellus SC small-caps for datelines.

**Signature:** Often omitted — the masthead + image carry the cover. If used, it's a small Marcellus SC line like "ELENA · INSIDE" rather than a script display.

**Decoration:** One thin horizontal rule under the masthead, with the dateline letter-spaced wide across it. Sometimes a single accent line in gold. Nothing else.

**Avoid:** Too many cover lines (kills the high-fashion air), script fonts (too sweet for this voice), gradient bars, hearts/stars.

---

## C — Asian Fashion Glossy

**Models:** Vivi (JP), Cawaii, JJ, Mina, Ray, ViVi-style trend mags.

**Identity:** Playful, pastel, dense. Multiple cover lines in different colors crowd the cover. The masthead is decorative — italic serif with a paper-shadow, often paired with a kanji sub-masthead. Hearts/stars/sparkles. The cover feels generous and busy.

**Masthead:** Italic Playfair Display Black 900 in hot pink (`#ff6fa8`) with a paper-shadow offset and gold echo-shadow. Kanji sub-masthead in Noto Serif SC 700 below.

**Palette:** Hot pink (`#ff6fa8`) + teal (`#46c5b7`) + gold (`#e8b43a`) + cream paper (`#fff5fb`). Subject is photographed against a pastel ground (or the cover lines are dark ink on a pastel image overlay).

**Cover-line voice:** Conversational, advisory, sometimes single-word.
- *"今月のモテ服!"* (this month's flattering outfits)
- *"summer makeup tutorial"*
- *"new color LIP — 5 shades"*
- *"30-day skin reset"*
- *"特集 · The Dendro Trend"* (bilingual ok)

Italic serif (Playfair Italic 700) for headlines in **different colors per line** — pink, teal, gold. Subtitles in Cormorant Regular 18px in dark ink.

**Signature:** Pinyon Script (more delicate than Italianno), in the dominant accent (hot pink) with a paper-shadow. Smaller than the A signature.

**Decoration:** Scattered hearts/stars/sparkles. A round gold "¥980" price badge tilted -8°.

**Avoid:** White-only palette (kills the glossy energy), generic sans cover lines, missing the kanji sub-masthead (that's part of the language).

---

## D — Avant-Garde Brutalist

**Models:** i-D, Dazed, Numero Homme, 032c, AnOther Magazine.

**Identity:** Punk-editorial, design-school, deliberately ugly-confident. One huge heavy-sans word (often lowercase, often a single letter). One color block. Cover lines are minimal, lowercase, deadpan. The cover feels like it was made by an art student who knows exactly what they're doing.

**Masthead:** Anton (or Druk if available) at 180–220px, lowercase, sometimes set inside a colored block (red `#ff3a2d` is the i-D move). Or a single letter (`i-D`'s lowercase `i-D` ligature, Dazed's tight `DAZED`).

**Palette:** White + one saturated accent (red `#ff3a2d`, electric blue, neon green). High contrast, no pastels. The subject is often cropped aggressively or has a color overlay across part of the image.

**Cover-line voice:** Deadpan, lowercase, single-thought.
- *"the youth issue"*
- *"on the new wave"*
- *"chloe, ungoverned"*
- *"a portrait of dendro"*

Italic Cormorant Garamond for the cover lines (italic + lowercase together = the avant-garde tic), small Anton labels under each as kicker tags ("interview · pg 24", "fashion · pg 60").

**Signature:** Character name in heavy Anton at the bottom, all caps, with a small italic serif "x" tag in red ("NAHIDA × the spring issue"). Or skipped entirely.

**Decoration:** One horizontal rule in the accent color, often labelled in tiny Anton caps. No hearts, no stars, no scripts.

**Avoid:** Hearts/stars (wrong voice), centered cover lines (this flavor prefers off-axis), script fonts, gold (too precious — i-D doesn't do gold).

---

## E — Vertical Masthead (landscape-first)

**Models:** Editorial spreads, fashion-week side-rail layouts, art-book covers, magazine *back* covers, modern landscape billboards.

**Identity:** A landscape-first composition that puts the masthead vertical on the left edge so the subject can dominate the right 70% of the canvas. Especially useful when the input image is landscape (e.g. a screenshot, a wide hero illustration, a fashion-week panoramic).

**Masthead:** Heavy display sans (Anton) set with `writing-mode: vertical-rl` on the left edge. Paired with a smaller italic serif sub-masthead beside it. Both run top-to-bottom along the page edge.

**Palette:** White + character accent. Works with subdued color grading (cinematic or cool grade) more than warm.

**Cover-line voice:** Italic Cormorant headlines stacked down the right edge, each with a Marcellus SC small-caps sub. Tone: editorial, semi-formal — closer to Numéro than to Vivi.

**Signature:** Italianno script at the bottom-right corner, signature-style.

**Decoration:** Sparse. Maybe a single vignette and rim-light; no hearts/sparkles. Portrait fallback: masthead rotates to horizontal-top — the layout still works but loses the vertical-rail energy.

**Avoid:** Using this skeleton for a portrait-aspect input — the masthead has nowhere to "live" along the edge. For portrait subjects, Skeleton 1/2/3/4 will all look stronger.

---

## How to pick

For an **anime/game character** subject (portrait input):
- Ship A + (B or C) + D. A is the natural fit; pick B if the subject looks confident/regal, C if the subject is cute/playful, and D as the wildcard.

For a **real person / non-character subject** (portrait input):
- Ship B + C + D + variant of B (e.g. Numero-style + Bazaar-style + Dazed-style + Vogue-style). Skip A.

For an **editorial reference photo** (fashion-week shot, model headshot — portrait):
- B + D (high-fashion + avant-garde) is the natural duo.

For a **landscape input** (screenshot, wide hero illustration):
- E is the natural fit. Pair with A (in landscape orientation with the auto-applied `.landscape` class) and B for variety. D works well in landscape too.

Don't ship four versions of the same flavor (four Vogue variants) — that's the AI-slop default. The user came to this skill for *variety of editorial voice*, not "Vogue in four colors".

## Skeleton + token = bespoke

Within one skeleton, swapping design tokens produces visually distinct covers:
- Skeleton C (Asian glossy) for **Chloe** uses hot-pink-on-pink palette + hearts/sparkles → magical-girl ViVi
- Skeleton C for **Nahida** uses dendro-gold-on-cream palette + botanical sparkles → nature-themed glossy

The skeleton is the layout structure; the tokens determine what kind of magazine that structure becomes. See `design_tokens.md` for the full extraction framework.
