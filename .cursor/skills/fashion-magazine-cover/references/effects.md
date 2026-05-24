# After-Effects

Atmospheric treatments that elevate a cover from "text on photo" to "designed". Two pipelines: CSS-side (live in the skeleton HTML, baked into the background-layer screenshot) and PIL-side (post-pass on the exported background PNG via `apply_fx.py`).

> **Opt-in by default.** Always confirm with the user before applying any FX using `clarification_prompts.md` template 3. The "subtle defaults" are recommendations, not silent auto-apply.

## When to use which effect

| Effect | When it fits | Skeleton hint |
|---|---|---|
| Vignette | Almost any cover. Subtle darkening at edges focuses attention on the subject. | All |
| Rim light | Portrait close-ups, regal/dreamy subjects. | 1, 2, 5 |
| Grade warm | Sunny/golden subjects, daylight scenes, glossy mags. | 1, 3 |
| Grade cool | Night scenes, sci-fi, brooding portraits. | 2, 4 |
| Grade cinematic | Editorial portraits, model headshots. | 2, 4 |
| Grade acid | Cyber/punk subjects, i-D-style irreverent covers. | 4 |
| Sparkles | Magical-girl, glossy pop, character-mag. | 1, 3 |
| Lens flare | Sci-fi, dramatic action, hero-lit close-ups. | 1, 2, 5 |
| Paper grain | Editorial print feel, retro covers. | All — especially 2, 4 |

### Don't pile them on

A real designer picks 1–3 effects max. AI-overdone covers stack 5+ effects and read as filtered Instagram, not editorial. The default "subtle" combo is:
- `.fx-vignette` + `.fx-rim-light` for portrait
- `.fx-vignette` alone for landscape

That's it. Add a grade or sparkles only when the variant calls for it.

## CSS effects (live in skeleton HTML)

Applied as classes on the `.cover` element. Live in `[data-layer="background"]` so they bake into the background-layer screenshot (not the transparent effects layer).

### `.fx-vignette`
Radial darkening from center outward. Always subtle (final 35% radius). Multiply blend mode means it darkens without changing color cast.

### `.fx-rim-light`
Soft warm glow from top-left, like studio key light. Screen blend mode lifts highlights. Off-by-default for landscape (too directional in wide aspect).

### `.fx-shade-top` / `.fx-shade-bottom`
Linear gradient overlays at the top + bottom edges. Used by skeletons to ensure top-masthead text + bottom-signature text stay legible against busy subject images. Strength is tuned per skeleton; can be removed if the subject's own composition already creates dark bands at those edges.

### `.fx-grade-warm` / `.fx-grade-cool` / `.fx-grade-cinematic` / `.fx-grade-acid`
Applies a CSS `filter:` on `.bg-img` (NOT on the whole `.cover`, so text colors aren't shifted). Each grade uses saturate + contrast + hue-rotate or sepia tuned for the named mood. Off-by-default — opt in per skeleton via the `mood-overlay` token (see `design_tokens.md`).

### `.fx-sparkle` (effects layer)
Individual sparkle / star / heart glyphs placed in `data-layer="effects"`. Each instance is a `<div class="fx-sparkle">` with absolute positioning. Drop in 4–10 per cover. Use `mix-blend-mode: screen` so they brighten the subject they overlap.

```html
<div data-layer="effects">
  <div class="fx-sparkle" style="top: 32%; left: 38%; font-size: 36px; color: #e8b43a;">✦</div>
  <div class="fx-sparkle" style="top: 56%; right: 26%; font-size: 28px; color: #ff6fa8;">♡</div>
  <div class="fx-sparkle" style="bottom: 24%; left: 22%; font-size: 24px; color: #46c5b7;">★</div>
</div>
```

### `.fx-flare` (effects layer)
CSS radial gradient simulating a lens flare. Good for sci-fi or dramatic-light covers. PIL version (below) is sharper if you need photorealism.

## PIL effects (post-pass on background PNG)

Run `scripts/apply_fx.py` after the layered export to add print-quality effects to the background layer specifically. The script reads `cover_*_background.png`, applies the named effects, and writes the modified PNG back (or to a new path).

```powershell
# Add procedural lens flare at 75% along width, 30% down
.\.venv\Scripts\python.exe scripts/apply_fx.py `
    --input nahida_cover-a_background.png `
    --flare 0.75,0.30,warm `
    --grain 0.06
```

### Procedural lens flare

Generated entirely in PIL — no PNG assets needed. Composites:
- A bright central hotspot (gaussian-blurred white circle)
- An orange/cool ring of secondary refractions along the line through the flare and the image center
- 3–4 small ghost rings at decreasing intensity

Color presets: `warm` (orange-yellow), `cool` (blue-white), `magenta` (lens-leak style).

### Paper grain

Procedural noise tile — fine luminance variation overlaid via `Image.composite` at 5–10% intensity. Gives the cover a film-grain or print-grain texture without looking digitally clean.

## Verification

After applying effects, the layered export should produce:
- `cover_*_background.png` — with vignette, rim-light, grading, AND any PIL-applied flare/grain baked in.
- `cover_*_effects.png` — sparkles + free-floating decorations only (transparent everywhere else).
- `cover_*_artwork.png` — text + barcode (transparent everywhere else).
- `cover_*_final.jpg` — flattened composite of all three.

Drop the three PNGs into Photoshop in order (background → effects → artwork). The result should match `_final.jpg` within JPG-compression tolerance.

## Adding new effects

For new CSS effects:
1. Add the `.fx-*` class to the skeleton stylesheet.
2. Place it in `[data-layer="background"]` if it acts on the image (gradient, blend mode), in `[data-layer="effects"]` if it's a discrete decoration (sparkle, glyph).
3. Document the when-to-use in this file.
4. Mention in `design_tokens.md` under the `mood-overlay` mapping if it should be auto-applied per mood.

For new PIL effects: add a function to `apply_fx.py`, expose via CLI flag, document here. Avoid bundling new binary asset files — generate procedurally when possible.
