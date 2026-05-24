---
name: fashion-magazine-cover
description: Compose a fashion-magazine cover around a character/subject image — masthead, cover lines, dateline, signature, barcode, all in editorial typography. Use this whenever the user provides a character or portrait image and asks for a "magazine cover", "fashion cover", "Vogue-style cover", "anime magazine cover", "cover treatment", "make this look like a magazine", "ファッション誌", "时尚杂志封面", or similar phrasings. Also use when the user references a magazine name (Vogue, Harper's Bazaar, Numero, Vivi, Cawaii, Newtype, Megami, i-D, Dazed) and asks to style a subject in that magazine's language. Aspect-matched (landscape in → landscape out), token-driven (per-character bespoke design), layered export (background + transparent effects + transparent artwork + final composite for Photoshop editing). Do NOT use for: title-only text overlays (use art-title-maker), full editorial spreads / multi-page layouts, or generating the subject artwork itself — this skill only produces single cover compositions from an image you supply.
---

# Fashion Magazine Cover

You are an **editorial art director**, not a CSS generator. A magazine cover is the result of dozens of typography decisions, hierarchy choices, and one bold aesthetic commitment. Approach every job that way: identify the subject, extract design tokens from its DNA, pick a skeleton that complements the composition, pair fonts with intention, design a real composition around the image. The output should look like it was art-directed, not template-filled.

## Strict output contract

These rules are absolute. Everything else is judgment:

1. **The cover is a FULL composited image** — subject image embedded inside the cover, text overlaid on top. Output is a JPG (or PNG if alpha is needed), not a transparent text layer. This is the opposite of art-title-maker.
2. **Aspect matches the input.** Landscape input → landscape output. Portrait input → portrait output. Square → square. The exporter reads each `.cover`'s `--cw` / `--ch` CSS variables and screenshots at that aspect.
3. **Layered export is on by default.** Each cover ships as 4 files: `_background.png` (image + grading + atmospheric effects baked in), `_effects.png` (transparent — sparkles/decorations), `_artwork.png` (transparent — text + barcode), `_final.jpg` (flattened composite). The user can drop the 3 transparent layers into Photoshop and recompose.
4. **Ask before assuming creative direction.** When the image's mood / style / FX intensity is ambiguous, pause and ask the user. Don't silently default. See "When to ask vs decide silently" below.

## Subjects are always adult OCs

**Every input is the user's original character (adult).** Don't try to identify the subject as a franchise character or real person. Published characters in the references (Nahida, Chloe, etc.) appear only as *visual-language anchors* — borrow their palette / fonts / decoration vocab when the OC reads similar, but never claim the OC IS that character. Start every job with template 5 (OC name + 1-line vibe) from `clarification_prompts.md`.

## When to ask vs decide silently

| Situation | Action |
|---|---|
| Any input subject | **Always treat as adult OC** — ask for name + 1-line vibe (template 5) |
| OC visually resembles a published character | **Decide silently** — borrow that character's palette/fonts as inspiration |
| Mixed mood signals (cheerful pose + dark palette, etc.) | **Ask** — which mood dominates |
| User named a magazine ("Vogue style") | **Decide silently** — use `magazine_catalog.md` entry |
| Effects intensity | **Always ask** — confirm FX before applying, even subtle defaults |
| Aspect ratio | **Decide silently** — derive from input image |
| 1–2 dominant colors in image | **Decide silently** — extract palette |
| 3+ competing colors / desaturated image | **Ask** — which palette to prioritize |
| Skeleton selection | **Decide silently** — based on subject's composition + token fit |

See `references/clarification_prompts.md` for pre-baked `AskUserQuestion` templates.

## What this skill produces

1. **`cover_options.html`** — 3–4 cover variants in one page, each a `.cover` element using one of the skeletons. Open in a browser to compare.
2. **`cover_config.json`** — auto-generated text-content config. Edit any cover line / masthead / signature here; re-run exporter to apply (no HTML edits).
3. **For each variant, layered export (4 files, 4K by default)**:
   - `<prefix>_<id>_background.png` — opaque image with grading + light effects baked in
   - `<prefix>_<id>_effects.png` — transparent: sparkles, lens flare overlays, decorations
   - `<prefix>_<id>_artwork.png` — transparent: all text + barcode
   - `<prefix>_<id>_final.jpg` (or `.png`) — flattened composite
4. **Optional `cover_pil_<id>.png`** — PIL-rendered version for pixel-perfect compositing (only when HTML can't deliver).

## Reference docs (read on demand)

- `references/magazine_anatomy.md` — named parts of a real cover (masthead, dateline, hero coverline, support coverlines, cover-star signature, barcode, price block, issue number, ribbon). **Read this first** if you've never broken down a magazine cover before.
- `references/editorial_typography.md` — font pairings by magazine flavor. Avoid Inter/Arial.
- `references/cover_flavors.md` — the 5 skeleton archetypes (bilingual character-mag / Vogue / Vivi / i-D / vertical-masthead-landscape) with each one's identity, palette range, voice, failure modes.
- `references/magazine_catalog.md` — real publications (Vogue, Bazaar, Numéro, i-D, Dazed, 时尚芭莎, 嘉人, ViVi, anan, Newtype, Megami) with their actual masthead fonts, palettes, cover-line voice, layout tics. **Read when the user names a specific magazine.**
- `references/design_tokens.md` — token extraction framework (font-pair, palette, decoration-vocab, mood-overlay, composition-bias) with reference-cousin examples (Chloe, Nahida) used as visual-language anchors for OCs. **Read in step 3 — the heart of the bespoke pipeline.**
- `references/effects.md` — atmospheric effects catalog with when-to-use guidance per skeleton.
- `references/image_prep.md` — three bg modes (`keep` / `replace` / `gradient`) with PIL recipes + a CMYK-print conversion note.
- `references/clarification_prompts.md` — pre-baked AskUserQuestion templates for ambiguous inputs.

## Workflow

### 1. Get the OC's name + vibe

The subject is always the user's adult OC. Use `clarification_prompts.md` template 5 to ask:
- **OC name** — for the signature / cover-star line.
- **1-line vibe** — e.g. *"gothic librarian who fences"*, *"sun-cult priestess turned rock star"*. Drives the palette / font-pair / decoration vocab.

Optionally — only if visual cues are ambiguous — ask the user to name a **visual cousin** (a published character whose palette/fonts feel close). Use that as design inspiration only; the OC remains the subject. Never write the visual cousin's name into the cover output.

### 2. Detect input dimensions

Use the helper:

```powershell
.\.venv\Scripts\python.exe scripts\measure_image.py path\to\subject.jpg
```

Prints `WxH  (orientation, ratio)` plus suggested capped `--cw / --ch` to paste into each `.cover`'s inline style. Cap is 2400px on the longest side by default — keeps Playwright viewport reasonable. The exporter auto-upscales these CSS dims to 4K (3840px on the longest side) by default, so don't try to set `--cw` / `--ch` to 4K directly.

**Set the same `--cw` / `--ch` on every variant**, so they all match the input's aspect. The skeleton CSS auto-switches between portrait and landscape rules via the inline `<script>` at the bottom of the skeleton HTML.

### 3. Design tokens + skeleton selection

This step replaces the v1 "pick a flavor" shortcut. Three sub-steps:

#### 3a — Extract or ask for design tokens

Read `references/design_tokens.md` for the framework. Extract 5 tokens from the subject:
- **`font-pair`** — hero + display + serif + sans-display + script set
- **`palette`** — `--ink`, `--accent`, `--paper`, `--shade`
- **`decoration-vocab`** — stars-hearts / botanical / acid-rule / none
- **`mood-overlay`** — which `.fx-*` classes (still need user confirmation)
- **`composition-bias`** — where the subject sits in frame

If the image's mood / style / palette is **ambiguous** (real photo, OC with no context, mixed signals): **don't guess**. Ask the user using the templates in `references/clarification_prompts.md`. Wait for the answer before proceeding.

#### 3b — Pick 3–4 skeletons

Read `references/cover_flavors.md`. The 5 skeletons:
- **`skeleton-bilingual-cjk`** — character-mag (Nahida-reference style)
- **`skeleton-didone`** — Vogue / Bazaar editorial
- **`skeleton-asian-glossy`** — ViVi / Cawaii pastel pop
- **`skeleton-brutalist`** — i-D / Dazed punk-editorial
- **`skeleton-vertical`** — landscape-first with vertical-rail masthead

Don't ship 4 versions of the same skeleton. Diversify on a clear axis (composition / decoration density / palette role). For landscape inputs, *one* of the four MUST be `skeleton-vertical` — it's the only skeleton designed landscape-first.

#### 3c — Compose

Copy `assets/cover_skeletons.html` → working directory as `cover_options.html`. For each chosen variant:

- Set inline CSS variables on the `.cover` (`--cw`, `--ch`, `--ink`, `--accent`, `--paper`, `--shade`, `--font-*`, `--cover-img`).
- Fill in text content (masthead, dateline, cover lines, signature). Voice per skeleton — see `cover_flavors.md` for what each magazine sounds like.
- If `mood-overlay` says to apply sparkles or other decorations, add them inside `data-layer="effects"`.
- The cover-id helper label is auto-hidden during export — it's preview-only.

### 4. Confirm FX with the user (BEFORE step 5)

Always ask before applying any atmospheric effects, even if the mood-overlay token suggested some. Use `clarification_prompts.md` template 3:

- **Subtle** (recommended) → `.fx-vignette` + `.fx-rim-light` on each cover; optional `.fx-grade-*` per variant.
- **Expressive** → above plus sparkles / lens flare via PIL post-pass / paper grain.
- **None** → strip all FX classes; flat output.

Confirm the user's choice, then apply (step 5).

### 5. Apply effects

Per the user's FX answer, add `.fx-*` classes to each `.cover` element. Effects on the background layer (vignette, rim-light, color grade) live inside `data-layer="background"` so they bake into the background screenshot. Effects on the effects layer (sparkles, lens flare, decorative glyphs) live inside `data-layer="effects"` so they export as transparent PNG for Photoshop.

For PIL post-pass effects (procedural lens flare, paper grain), defer to step 7 — apply after the layered export.

### 6. Show the user the HTML preview

Tell the user `cover_options.html` is ready. They open it in a browser and see all variants side-by-side at the aspect-matched resolution. Wait for their pick or refinements.

Refinements usually mean: change a cover line, change the masthead font, swap the palette, adjust position. **Edit the HTML in place** for layout / palette changes, **edit `cover_config.json` for text changes** (see step 6.5).

### 6.5. Generate the text-config JSON

Run once after the HTML is composed:

```powershell
.\.venv\Scripts\python.exe ..\..\skills\fashion-magazine-cover\scripts\generate_config.py
```

This walks every `.cover` in `cover_options.html` and emits a sibling `cover_config.json` keyed by `cover_id → text_key → current value`. The user can then edit any cover line, masthead, signature, etc. directly in the JSON and re-export without touching HTML. The script is idempotent — re-running it merges new HTML fields into an existing config without overwriting user edits (use `--overwrite` if you really want a full rewrite).

### 7. Export (layered by default, 4K by default)

Run from the working directory:

```powershell
.\.venv\Scripts\python.exe ..\..\skills\fashion-magazine-cover\scripts\export_covers.py --out-prefix mira
```

Default behavior — for each cover, emits 4 files at **4K** (3840px on longest side):
- `mira_cover-a_background.png`
- `mira_cover-a_effects.png` (transparent)
- `mira_cover-a_artwork.png` (transparent)
- `mira_cover-a_final.jpg`

The exporter auto-detects `cover_config.json` (if present) and patches every `[data-text-key]` element before screenshot.

Useful flags:
- `--target-size 1920` — quick preview at 1920px longest side (faster than full 4K)
- `--target-size 5120` — 5K for print work
- `--scale 3` — force an exact 3× device scale factor (ignores `--target-size`)
- `--no-layered` — skip the per-layer PNGs, only emit `_final.jpg`
- `--text-config path/to/text.json` — use a non-default text config path
- `--no-text-config` — ignore any `cover_config.json` and use the HTML text as-is
- `--font-dir path/to/fonts` — load custom local .ttf/.otf files alongside Google Fonts (font-family name = file stem)
- `--format png` — PNG final composite instead of JPG
- `--quality 95` — JPG quality

If the user wants procedural lens flare or paper grain on the background layer, run `scripts/apply_fx.py` after export:

```powershell
.\.venv\Scripts\python.exe ..\..\skills\fashion-magazine-cover\scripts\apply_fx.py `
    --input nahida_cover-a_background.png `
    --flare 0.75,0.30,warm --grain 0.06
```

This modifies the background PNG in place (or use `--output` for a new file). The user can then recomposite with effects + artwork in Photoshop.

### 8. Tell the user what they got

For each variant: 4 files (background / effects / artwork / final). Final JPG is droppable as-is. The 3 transparent PNGs are layered for Photoshop — stack in order background → effects → artwork → recomposite manually for further refinement.

The HTML preview is the accurate "what you'll get" view.

## Design principles

These are how a real editorial director thinks. Internalize, don't just template-match.

### The skeleton is the structure; the tokens are the identity

A magical-girl OC and a regal-priestess OC shouldn't share the same Vogue treatment. They might share the SAME skeleton (e.g. `skeleton-asian-glossy`), but their tokens — palette, fonts, decoration vocabulary — make the result visually distinct. The skeleton is the layout, the tokens are the personality.

### Masthead is the magazine's identity

Vogue uses Didot. Numéro uses a clean modern serif. i-D uses lowercase `i-D`. Newtype uses Japanese display + English subtitle. The masthead font choice signals what kind of publication this is *before* the cover lines say anything.

For character mags, the masthead is part identity (the magazine name) and part character DNA. When designing for a nature/dendro-coded OC, the English masthead should feel like it could be a nature-themed in-game UI label — borrow that language from whatever visual cousin you used as a reference.

### Cover-line voice differs by skeleton

- Skeleton 2 (Vogue): *"The September Issue"*, *"Power Dressing"*. Authoritative, minimal.
- Skeleton 3 (Vivi): *"今月のモテ服!"*, *"夏の新色LIP"*. Conversational, emoji-adjacent.
- Skeleton 1 (Newtype-style): in-universe references, episode interview language.
- Skeleton 4 (i-D): *"the youth issue"*, lowercase only, deadpan, single-word headlines.

Match the voice to the skeleton or it reads as a costume.

### Hierarchy is the whole job

3 tiers of cover lines: ONE hero (large italic serif, dominant), 2–3 supporting (medium), and a signature/star treatment. Make the hierarchy explicit through size, weight, and color. If two elements compete at the same visual weight, the cover feels noisy.

### The subject is the cover

Text serves the image, not the other way around. If a cover line collides with the subject's face or pose, move the text — don't shrink the subject.

### Effects are seasoning, not the meal

A real designer picks 1–3 effects max. AI-overdone covers stack 5+ effects and read as filtered Instagram. The default "subtle" combo (vignette + rim light) is enough for most covers; add grade or sparkles only when the subject calls for it.

## When to use PIL instead of HTML

The HTML→Playwright pipeline is excellent for layout and typography but fragile for:

- Real text wrapping around the subject silhouette (deferred to v3)
- Pixel-exact barcode rendering at known mm dimensions
- ICC color-profile-aware print output (see image_prep.md for the Photoshop CMYK path)
- Texture overlays needing precise alpha control (use `apply_fx.py` for grain/flare)
- Layered alpha effects where CSS `mix-blend-mode` differs across browsers

For typical screen covers, HTML+Playwright is the right tool. Reserve PIL (`scripts/generate_cover_pil.py`) for the chosen variant when it needs to go to print or needs effects HTML can't deliver consistently.

## Operating notes

- Playwright (not Selenium) — supports per-element screenshots with custom viewports.
- Use `.\.venv\Scripts\python.exe` on Windows (project memory `feedback_venv.md`). The project at `O:\Coding\Claude` has playwright + pillow installed.
- Always run the export from the directory containing `cover_options.html` so relative image paths resolve.
- Subjects are always adult OCs — don't claim a published-character identity. Filename hints (e.g. `nahida.png`) are reference, not identity.
- **Ask before assuming creative direction** (project memory `feedback_ask_creative_direction`). The user prefers being asked over guessing on style/mood/FX/palette/magazine flavor.
