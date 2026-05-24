# Layout patterns

Centered-stack is the default. It's also the most boring choice. Real designers play with composition. Pick a pattern that matches the **energy** of the design direction.

## 1. Centered stack (the safe default)

```
       FURIGANA
       ━━━━━━━
        HERO
        WORD
       ───────
        SUBTITLE
       ━━━━━━━
       Romaji Caps
```

When it works: elegant / refined / formal directions. When it fails: anything playful or kinetic — feels static.

CSS: `flex-direction: column; align-items: center`.

---

## 2. Zig-zag / offset diagonal (high energy)

```
   HERO
       ←  &
              SECOND
```

The hero word offsets up-left, the connector (& · — or a small mark) anchors center, the second word offsets down-right. Creates diagonal energy. Great for "X & Y" titles, duo names, or two-part themes.

CSS: each line uses `margin-left` / `margin-right` differently, or `transform: translate(-80px, 0)` and `translate(80px, 0)`. Pair with a slight whole-block `rotate(-2deg)` for extra motion.

When it works: playful / pop / sticker / duo names.

---

## 3. Ampersand-as-anchor

```
                NOZOMI
                  &
        HIKARI
```

Same energy as zig-zag but the **&** is sized large and visually owns the center. Other words orbit it. Works as a one-shot visual signature.

CSS: ampersand gets a larger `font-size` (e.g. 60% of hero), often italicized or in a script font for contrast.

---

## 4. Broken word (multi-line typography)

```
   CHLO
       E
   VON EINZ
        BERN
```

Break a long name across awkward line breaks deliberately. Creates editorial / fashion-magazine feel. Each fragment gets its own size/weight. Works best with thin elegant serifs.

CSS: hard newlines + per-fragment classes with different sizes.

When it works: editorial / fashion / magazine. Fails on cute or sticker directions.

---

## 5. Vertical kanji + horizontal romaji (Japanese-rooted)

```
百            ARIYA YURIZONO
合           ━━━━━━━━━━━━
園
セ
イ
ア
```

Kanji runs top-to-bottom (`writing-mode: vertical-rl`); romaji sits horizontally beside or below it. Authentic Japanese poster typography. Works for franchise titles, character intros, formal/traditional vibes.

CSS:
```css
.kanji-vert { writing-mode: vertical-rl; text-orientation: upright; }
```

---

## 6. Diagonal flow (whole-title rotation)

```
    NOZOMI
        & HIKARI
            ✦
```

Rotate the entire title block by 2–6° to add kinetic energy. Pair with skew on the hero word for double motion. Works for playful, action, sport directions.

CSS: outer container `transform: rotate(-3deg)`. Be careful — too much rotation looks broken.

---

## 7. Stacked with offsets per line (rhythmic)

```
        FURIGANA  
   HERO WORD
        SUBTITLE
   ROMAJI
```

Each line indents differently — alternating left/right offsets create a rhythm down the title. More dynamic than centered stack, less chaotic than full zig-zag.

CSS: per-line `margin-left` overrides on flex column.

---

## 8. Side-by-side asymmetric (split layout)

```
              | ◆ ◆ ◆
   CHLOE     | Furigana
              | クロエ
              | Chloe von Einzbern
```

Hero word large on the left, supporting text in a column on the right. Magazine column feel. Works for editorial, fashion, character-card directions.

CSS: outer `display: flex; flex-direction: row; gap: 36px`. Hero column has the big word; right column has stacked supporting text.

---

## 9. Sticker / badge composition

```
   ╭───────╮
   │ BADGE │
   ╰───────╯
       CHLOE
        クロエ
       ★ ☆ ★
```

Top badge (small filled chip) → hero word with thick stroke → katakana below → decorative row. The badge is a separate element, not a card-plate. Reads as a sticker design.

CSS: `.badge` is `display: inline-block; background: #fff; border-radius: 100px; padding: 4px 22px;` then the rest of the card is transparent.

---

## 10. Scattered decoration field

```
   ♡        ♡   ✦
       CHLOE
   ✦          ♡
        クロエ           ♡
              ✦   ♡
```

The title sits in a field of small decorations (hearts / stars / sparkles / petals / bubbles) placed pseudo-randomly. Each decoration is a separate element with absolute positioning. Use collision detection (in PIL) or hand-place with care (in HTML).

CSS: parent `position: relative;` + many child `.deco { position: absolute; top: X%; left: Y%; }`. For real scatter with collision detection, use the PIL generator.

---

## Transforms cheat sheet

These are the small moves that make a static block feel designed:

- **Italic via skew** — `transform: skewX(-8deg)` on the hero word. More personality than a font's built-in italic. Combine with a slight `rotate(-2deg)` for forward lean.
- **Slight rotation** — `rotate(-2deg)` to `rotate(-4deg)` on a word or the whole block. More than 6° usually looks broken.
- **Letter-spacing** — wide spacing (0.3–0.6em) feels formal/airy; tight (-0.02em) feels punchy; default feels neutral and forgettable.
- **Mixed sizes within a word** — `<span class="big">C</span>hloe` to drop-cap the first letter. Editorial trick.
- **Mixed weights within a word** — `<span>CHLO</span><span class="thin">E</span>` for tension.

---

## Layout × direction matrix

| Direction | Best layouts | Worst layouts |
|---|---|---|
| Bubbly kawaii | Zig-zag, scattered decoration, ampersand-anchor | Centered stack, broken-word |
| Elegant serif | Centered stack, side-by-side, vertical kanji | Zig-zag, scattered decoration |
| Sticker pop | Sticker badge, zig-zag, diagonal flow | Vertical kanji, broken-word |
| Editorial | Broken-word, side-by-side, stacked-with-offsets | Scattered decoration, sticker badge |
| Magical-girl heraldic | Centered stack (with ornament), vertical kanji | Zig-zag, broken-word |
| Cyber / arcade | Diagonal flow, mixed sizes, side-by-side | Vertical kanji |

---

## Spacing rhythm

After picking a layout, set spacing intentionally:

- **Tight composition** (everything close) → reads as a unit, monolithic. Good for sticker / sport / arcade.
- **Loose composition** (generous margins between lines) → reads as refined, breathable. Good for editorial / elegant.
- **Asymmetric spacing** (one big gap, one tight gap) → reads as dynamic / designed. Good for editorial / fashion.

Spacing is your most underused tool. A title with great fonts + bad spacing looks worse than mediocre fonts + great spacing.
