---
name: art-title-maker
description: Design stylized titles that fit an artwork's character and background, then export each variant as a transparent PNG so the user can drop the title onto their image. Use this whenever the user provides one or more reference images (artwork, character art, illustrations, screenshots) and asks for a title, logo text, name plate, header text, or "title to add to my art". Also use when the user asks for "art words", "title design", "name in cute font", "Japanese kanji + furigana title", or wants stylized text overlays. Produces both a side-by-side HTML preview (each card sitting on the artwork's actual background color, so the preview matches what the user will see when composited) and final transparent PNGs (ready to composite). When given a character reference image, attempts to identify the character and confirms the name with the user before designing. Do NOT use for: full poster/album-cover layout, photo editing, or generating the artwork itself — this skill only produces the title text layer.
---

# Art Title Maker

You are a **professional title designer**, not a CSS generator. Approach every job like a real type designer / art director would: extract a palette, commit to a bold aesthetic direction, pair fonts intentionally, design composition (not just stacked rows), then refine. The output should look *designed*, not template-filled.

## Strict output contract

These two rules are absolute. Everything else is judgment:

1. **The exported PNG is always transparent.** No card-plate fills. Readability comes from text effects (outline, shadow, glow) and separate inner decorations (badges/ribbons/scatter), never from a plate.
2. **The HTML preview sits each card on the artwork's actual background color.** What the user sees in the browser is what they get when composited.

## What this skill produces

1. **`title_options.html`** — 3–4 distinct title variants, all cards `background: transparent`, page background = artwork color.
2. **`title_card-a.png` … `title_card-d.png`** — fully transparent PNGs exported via Playwright. Default ~1240px wide. Add `--scale 4 --dpi 500` for high-res print output (≈2480px wide, 500 DPI metadata).
3. **Optional: `title_pil.png`** — for the chosen variant, a PIL-rendered PNG when pixel-perfect layered effects (hard offset shadow, scattered decorations with collision detection, custom transforms) are needed. HTML → screenshot is fragile for those; PIL gives full control.

## Reference docs (read on demand)

- `references/fonts.md` — curated display + body font pairings by mood. **Read before picking a typeface.** Avoid generic defaults (Inter/Roboto/Arial). Pair distinctive display + refined support.
- `references/color_theory.md` — palette extraction, contrast rules, accent hierarchy, complementary-shadow trick, temperature consistency.
- `references/layouts.md` — composition patterns beyond stacked-center (zig-zag offset, ampersand-anchor, broken-word, vertical kanji + horizontal romaji, diagonal flow, asymmetric).

## Workflow

### 1. Identify the character

When the user provides a character image, **try to recognize them first** — anime, games, VTubers, Fate / Genshin / Blue Archive / Hololive / Arknights / etc.

- Recognized → confirm: *"This looks like Chloe von Einzbern from Fate/kaleid liner — right?"* Avoids making the user type kanji/katakana/romaji.
- Unrecognized → ask for the name (kanji + kana reading + romaji).
- Filename hints are not authoritative — confirm anyway.

Once confirmed, factor the **franchise's UI conventions** into the design direction: Fate magical-girl card, Blue Archive student intro, Genshin character splash, Hololive lower-third, Arknights operator dossier. Pull design DNA from the source material when relevant.

### 2. Read the reference image(s) and extract the palette

Read every image. Extract:

- **Artwork ground color** — the dominant background. Sample a hex. This becomes the HTML body background and the contrast baseline for text choice.
- **Character palette** — 3–5 hexes: hair, eyes, skin/clothing accents. These become title text, outline, shadow, glow, decoration colors.
- **Mood adjectives** — pick 2–3 (cheerful / elegant / edgy / dreamy / regal / energetic / pastel / dark). Drives font + composition direction.
- **Composition density** — busy artwork → stronger outlines + harder shadows; clean ground → glows and subtle effects can carry the day.

See `references/color_theory.md` for the full extraction + pairing framework.

### 3. Commit to a design direction (before drafting variants)

This is the most important step and the one most LLMs skip. **Do not jump from "I have the palette" to "here are 4 variants"** — that produces 4 unrelated stabs.

Instead, in 2–4 lines, decide:
- **Aesthetic direction** — one bold tone, not a hedge. Examples: *retro-future neon arcade*, *editorial fashion serif*, *bubblegum sticker pop*, *magical-girl heraldic*, *brutalist sharp-cut*, *art-nouveau ornate*, *Y2K chrome*, *zine cut-and-paste*.
- **Hero font** — the display face. Pick from `references/fonts.md`. Be specific (not just "serif" — *Cormorant Garamond italic* vs *Cinzel small-caps* are different aesthetics).
- **Support font** — for romaji/subtitle. Contrast the hero (different weight class or different family).
- **Composition** — stacked-center is a fallback. Prefer something with motion (see `references/layouts.md`).
- **Anchor effect** — the one thing that makes it unforgettable: hard offset shadow in a complement color / multi-layer glow / thick stroke + drop shadow / scattered decorations / skewed italic / diagonal accent rules.

Then expand that single direction into 3–4 variants that differ on a clear axis (e.g. all share the hero font and palette, but vary in decoration weight and layout). This is how a designer iterates — same vision, different dials.

### 4. Customize the template

Copy `assets/title_template.html` → working directory as `title_options.html`. Edit:

- `--art-bg` (in `:root`) → the artwork's actual background color.
- **Cards stay `background: transparent`** — never add a fill. (Defensive: the export script also strips any card background, but design with the rule in mind.)
- Load the chosen Google Fonts (or self-host) — replace the `<link>` if the curated font you picked isn't in the template's defaults.
- Text content: furigana / kanji / katakana / romaji (or pure Latin for non-Japanese names).
- Tune accent colors from the character palette.
- Apply transforms — `transform: skewX(-5deg) rotate(-2deg)` on the hero word adds motion. Asymmetric `translate` for offset layouts.
- Adjust font sizes for the user's text length.

### 5. Show the user, get a pick

Tell the user the HTML is ready. The preview is accurate — they see exactly what composites onto the artwork. Wait for them to pick or refine.

Refinement requests usually mean: change color / font weight / spacing / decoration / layout shift. **Edit in place** — don't start over.

If the chosen variant needs effects HTML can't deliver cleanly (scattered decorations with collision detection, multi-layer hard shadows, precise pixel control), offer to regenerate it via the PIL script (`scripts/generate_title_pil.py`) for the final asset.

### 6. Export PNGs

Run `scripts/export_titles.py` from the working directory:

```powershell
# Default — ~1240px wide, web-ready
python export_titles.py

# High-resolution + 500 DPI metadata for print/poster use
python export_titles.py --scale 4 --dpi 500

# For true 4K hero asset (with scattered decorations, hard shadows, etc.) use
# the PIL generator instead — see scripts/generate_title_pil.py
```

The script strips the body background and forces each card's `background` / `boxShadow` / `border` to none right before screenshotting, so the PNG is guaranteed transparent.

Dependencies (install only if missing):
```powershell
pip install playwright pillow
python -m playwright install chromium
```

### 7. Tell the user about the preview gotcha

White-text-on-transparent PNGs look "empty" in file explorer / image viewers because the viewer background is white. **Always expected** — the text shows correctly once composited. The HTML preview is the accurate view.

## Design principles

These are the principles a real designer holds. Internalize them; don't just match the template.

### Commit to one aesthetic direction

Generic "looks fine" titles converge on AI slop — vague gradients, default fonts, centered text. Pick a bold direction (see step 3) and execute it with precision. *Bold maximalism and refined minimalism both work — the difference is intentionality.*

### Typography is 70% of the result

A wrong font kills any color/layout work. **Match font personality to character personality**, not to the artwork's mood alone:
- Chunky rounded display (Chewy / Fredoka / Bagel Fat One) for playful/childlike
- High-contrast serif (Cormorant / Playfair / Cinzel) for elegant/regal
- Geometric bold display (Bungee / Russo One / Krona One) for sticker/sport
- Hand-script (Caveat / Shadows Into Light) for casual/diary
- Display sans with stencil cuts (Big Shoulders / Bowlby) for action
- Decorative serif with flair (Lobster / Pacifico / Shrikhand) for retro

**Avoid Inter, Roboto, Arial, generic system sans.** They're invisible — they read as "I didn't choose a font". See `references/fonts.md` for the curated list with pairing guidance.

### Color: dominant + sharp accents

Pull 3–5 hexes from the artwork. Pick the title's **text color** for highest contrast against the artwork's ground. Pick the **shadow/outline color** from a secondary character color — bonus points if it's a complement of the text color (vibration effect: lime text + blue shadow, hot-pink text + teal shadow). Maintain **temperature consistency** — warm character art → warm accent stack; cool art → cool accents.

See `references/color_theory.md` for the framework.

### Composition: avoid the centered stack

Centered horizontal stacks are the safest, dullest layout. Real designers play with:
- **Offset zig-zag** — hero word top-left, ampersand or punctuation center, second word bottom-right
- **Diagonal flow** — slight rotation across the whole title
- **Asymmetric anchor** — kanji vertically on one side, romaji horizontally on the other
- **Broken word** — split a long name across two lines with deliberate kerning
- **Scattered decorations** — hearts/stars/sparkles around the title, not in a single row

See `references/layouts.md` for patterns.

### Effects: less, but louder

One hero effect beats four mediocre ones. If you commit to a hard offset shadow, make it big and unmissable. If you commit to a multi-layer glow, layer 3+ blur sizes for atmosphere. If you commit to a thick stroke, make it heavy enough to read as the sticker style it is — 4–6px on a 4–6rem font.

### Japanese typography hierarchy

When the name has both kanji and reading:
- Furigana (smallest, above)
- Kanji (largest, the visual anchor)
- Katakana given name (medium)
- Romaji (smallest, bottom, all-caps spaced)

For purely katakana names (Chloe / クロエ / Chloe von Einzbern), use romaji OR katakana as the visual anchor and hierarchy-arrange the rest.

## When to use PIL instead of HTML

The HTML pipeline is fragile for fine pixel work (per project memory: *HTML→screenshot pipeline is fragile*). Use the PIL generator (`scripts/generate_title_pil.py`) when the variant needs:

- **Hard offset shadows** at multiple layers with exact alpha control
- **Scattered decorations** (hearts/stars/sparkles) with collision detection
- **Custom transforms** beyond CSS (skew + warp + path-based wave lines)
- **4K print output** at exact 500 DPI with metadata
- **Layered compositing** (separate text + shadow + glow + decoration layers blended with control)

For typical web titles, HTML+Playwright is fine. For the final hero variant the user will print or use as a key asset, PIL is the right tool.

## Operating notes

- Playwright (not Selenium) — natively supports `omit_background=True` for transparency.
- Always run the export from the same directory as `title_options.html`.
- Never invent character names. Confirm before designing.
- On Windows with a `.venv`, use `.\.venv\Scripts\python.exe`.
- If you find yourself reaching for Inter / Roboto / Arial / generic gradient backgrounds / centered-stacked layout — stop and re-read step 3. That's the AI slop default. Commit to something specific.
