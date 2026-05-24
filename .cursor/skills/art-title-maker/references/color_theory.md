# Color theory for title design

You're not picking pretty hexes. You're picking colors that **integrate the title into the artwork** and **make text legible against a specific ground**.

## 1. Palette extraction (do this first)

From the artwork, sample **3–5 hexes**:

| Slot | What to sample | Use |
|---|---|---|
| **Ground** | The dominant background color of the artwork | HTML body background; the surface text must read on |
| **Primary character** | Hair OR the largest character color | Text fill (often) |
| **Secondary character** | Eye color OR a striking clothing accent | Shadow / outline / glow |
| **Tertiary character** | A minor accent — armor, ribbon, flower, prop | Decorative element fill (badges, stars, hearts) |
| **Optional metal** | A glint, jewelry, gold/silver/chrome | Subtitle / divider / star fills |

Sample colors with a screen picker, an eyedropper, or by reading the image pixel-by-pixel. Don't invent hexes "in the spirit of" — sample real ones.

## 2. Contrast: the text color rule

The text's job is to be readable on the **artwork's ground**, not against the card (cards are transparent — see SKILL.md). Decide:

- **Saturated/dark ground** (deep blue, hot pink, crimson, black, navy) → **white text** is the safe baseline. Pure `#fff` reads cleanest at large sizes.
- **Light/pastel ground** (cream, light blue, pale pink, mint) → **dark text** in a deep saturated tone from the character palette (e.g. burgundy, deep teal, dark plum). Avoid pure black — it's flat and impersonal.
- **Mid-tone ground** (sage, mauve, dusty rose) → either works, but pick the one with the *bigger* WCAG contrast ratio. Often this means pushing the text further from the ground's value.
- **Busy/multi-color artwork** (background changes mid-image) → favor white with a heavy outline + shadow; outline color picks up the dominant ground.

WCAG contrast rule of thumb (not gospel for display type but useful as a sanity check): aim for ≥ 4.5:1 contrast between text fill and the ground behind it.

## 3. Accent hierarchy

Once text is set, the rest of the palette stacks like this — each tier should be 1 visual step quieter than the one above:

1. **Text fill** — highest contrast vs ground
2. **Outline / stroke** — accent color from character palette; saturated; reads as a halo
3. **Hard shadow** — deeper / darker variant of the outline color OR a complement (see next section)
4. **Glow / soft shadow** — desaturated, larger blur, ambient atmosphere
5. **Decorations** (hearts, stars, sparkles, badges) — metal accent (gold/silver) OR a tertiary character color

A clean stack is calmer than the "everything tier-1" approach. Don't compete with yourself.

## 4. The complementary-shadow trick

This is the secret that separates pro titles from amateur ones. The shadow color is *not* always a darker version of the text — sometimes it's a **complement** (the opposite hue on the color wheel). The two colors vibrate against each other and pop.

Examples that work:
- **Lime green text** (`#c6ff00`) → **deep blue shadow** (`#4264fa`)
- **Hot pink text** (`#ff5fa8`) → **teal shadow** (`#0fb39c`)
- **Yellow text** (`#ffd86b`) → **purple shadow** (`#6b3fa0`)
- **Crimson text** (`#c41e6e`) → **mint shadow** (`#7adfb5`) — but this only works for sticker variants
- **White text** → any saturated complementary or analogous accent works

Rule of use: only do this on **playful / sticker / pop / Y2K / arcade** directions. For elegant or dark variants, stay analogous (shadow is a deeper sibling of the text color).

## 5. Temperature consistency

Pick a **temperature lane** and stick to it:

- **Warm character art** (red/orange/yellow/peach skin tones, sunset backgrounds, gold accents) → warm accent stack: amber shadows, peach glows, gold decorations. A cold blue shadow on a warm illustration feels disconnected unless you're going for the complementary-shadow vibe (then commit to it as the whole point).
- **Cool character art** (blue/teal/purple hair, snow / night / underwater backgrounds, silver accents) → cool accent stack: deep navy shadows, lavender glows, silver decorations.
- **Neutral / pastel** → match the artwork's exact temperature; do not pull in saturated colors that aren't in the source.

## 6. Saturation and value

- **High-saturation art** (anime, magical-girl, vibrant scenes) → high-saturation accents. Muted accents disappear.
- **Low-saturation art** (watercolor, ink wash, monochrome) → keep accents muted too. A neon shadow on a watercolor reads as a mistake.
- **High-value art** (bright/light) → push text/accents darker so they don't blow out.
- **Low-value art** (dark/moody) → push text/accents lighter; metallic gold reads well on dark grounds.

## 7. Metal accents (gold, silver, chrome)

When a character has gold/silver/chrome details (jewelry, armor edges, eye color sparkle), borrow that hex for:
- Subtitle text
- Decorative stars / sparkles
- Thin dividers and rules
- Border accents on badges

Gold pairs especially well with: deep red, burgundy, navy, black, white.
Silver pairs especially well with: pastels, mint, sky blue, lavender.

## 8. CSS gradients as accent (when warranted)

The artwork ground in the HTML preview can be a **gradient mimicking the artwork** (e.g. `linear-gradient(160deg, #ff7eb9 0%, #f57aba 60%, #d42d78 100%)` for a pink background with depth). This makes the preview more accurate.

Don't use gradients on text fills unless the aesthetic direction calls for it (chrome/Y2K). Solid text fills read cleaner.

## 9. Common amateur mistakes

- **Black shadow as default** — flat and impersonal. Use a saturated dark from the palette instead.
- **Random "decorative" color** — every decoration's hex should come from the extracted palette. No new hexes appear past step 1.
- **Three competing accent colors** — keep the accent stack to 2 hues max (text vs shadow). Decorations can be a third only if they're small.
- **Low-contrast text on busy ground** — relying on a thin outline to fix a bad text color choice. Pick the right text color first.
- **Same-saturation everything** — flat. Vary saturation across tiers (text high, shadow medium, glow low).
