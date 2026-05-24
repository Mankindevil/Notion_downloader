# Image Prep — Background Modes & Pre-Processing

A magazine cover's first job is making the subject look intentional in frame. The raw image you receive is rarely that. This doc covers the three background modes the skill supports and the PIL recipes to prep the image before composing.

## Decision flow

```
Input image
├─ Already finished art with a coherent backdrop (Nahida illustration with stars/aura)
│   → bg-mode: keep
├─ Pre-cut transparent-PNG character (just the figure, alpha around it)
│   → bg-mode: replace  (compose onto a palette-derived solid / gradient)
└─ Messy crop, photo background, distracting elements
    → bg-mode: gradient  (apply a translucent overlay so text reads)
    OR  pre-process with bg removal → bg-mode: replace
```

## Mode A — `keep`

The image goes in as-is, fills the cover via `background-size: cover`. Use the lightweight `::before` gradient overlay in the template to ensure top/bottom text readability (built into cover-a/b/c/d already).

```css
.cover {
  background-image: url('subject.png');
  background-size: cover;
  background-position: center;     /* or 'center 30%' to favor the face */
}
.cover::before {
  background: linear-gradient(
    180deg,
    rgba(0,0,0,0.35) 0%,
    rgba(0,0,0,0) 22%,
    rgba(0,0,0,0) 70%,
    rgba(0,0,0,0.45) 100%
  );
}
```

Tune `background-position` if the subject's face would otherwise be cropped. `center 25%` favors faces in tall portraits; `center 60%` favors lower-body shots.

## Mode B — `replace`

Use when the input is a transparent-PNG character cutout. Compose onto a solid color or gradient sampled from the character's palette.

```python
# scripts/prep_replace.py — example helper
from PIL import Image

W, H = 1240, 1650
CHAR_PATH = 'chloe_cutout.png'        # transparent PNG
OUT = 'chloe_on_bg.png'

# Pick a backdrop color from the character's palette. Hot pink for Chloe; warm
# sand for Nahida; midnight blue for a Honkai character. Default to a complement
# of the dominant character color — never white.
BG = (255, 100, 160, 255)             # hot pink

canvas = Image.new('RGBA', (W, H), BG)
char = Image.open(CHAR_PATH).convert('RGBA')

# Scale character to ~80% of canvas height, centered.
ratio = (H * 0.8) / char.height
char_w = int(char.width * ratio)
char_h = int(char.height * ratio)
char = char.resize((char_w, char_h), Image.LANCZOS)

x = (W - char_w) // 2
y = int(H * 0.12)                      # leave room at top for masthead
canvas.alpha_composite(char, (x, y))
canvas.save(OUT)
```

For a gradient backdrop instead of a solid color:

```python
import numpy as np
from PIL import Image

W, H = 1240, 1650
TOP    = np.array([255, 100, 160])     # warm hot pink top
BOTTOM = np.array([100, 30,  80])      # deeper magenta bottom

gradient = np.zeros((H, W, 3), dtype=np.uint8)
for y in range(H):
    t = y / (H - 1)
    gradient[y] = (1 - t) * TOP + t * BOTTOM

Image.fromarray(gradient).save('backdrop.png')
```

## Mode C — `gradient` overlay

Use when the image's own background is busy/photographic and we need to suppress part of it so cover-line text reads. The overlay is part of the cover composition (always present in the template's `::before`) but for messy inputs you can intensify it.

```css
/* Heavier top + bottom for busy photo backgrounds */
.cover::before {
  background:
    linear-gradient(180deg,
      rgba(0,0,0,0.55) 0%,
      rgba(0,0,0,0) 28%,
      rgba(0,0,0,0) 60%,
      rgba(0,0,0,0.70) 100%
    );
}
```

If the WHOLE image is too busy (rare), tint with a translucent palette color instead of black:

```css
.cover::before {
  background:
    linear-gradient(180deg,
      rgba(139,26,58,0.6) 0%,            /* crimson tint top */
      rgba(139,26,58,0.2) 50%,
      rgba(139,26,58,0.6) 100%
    );
  mix-blend-mode: multiply;              /* deepens existing colors instead of greying */
}
```

## Recipes

### Background removal (PIL via rembg)

```bash
.\.venv\Scripts\pip.exe install rembg
```

```python
# scripts/prep_remove_bg.py
from rembg import remove
from PIL import Image

INPUT = 'chloe_messy.png'
OUTPUT = 'chloe_cutout.png'

img = Image.open(INPUT)
cutout = remove(img)                      # returns RGBA with bg removed
cutout.save(OUTPUT)
```

rembg uses a U-Net to mask out backgrounds. Works well for anime characters on clean grounds; sometimes struggles with thin hair edges (add `alpha_matting=True` for fixes).

### Dominant color extraction

```python
# scripts/prep_palette.py
from PIL import Image
from collections import Counter

img = Image.open('chloe.png').convert('RGB').resize((200, 200))
# Bin colors to nearest 16 (reduce noise from JPG artifacts).
pixels = [tuple(c // 16 * 16 for c in px) for px in img.getdata()]
top = Counter(pixels).most_common(5)
for color, count in top:
    print(f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}  ({count} px)")
```

Pick the dominant non-skin / non-hair color as the canvas color for `replace` mode. Pick a contrasting color as `--accent`.

### Soft vignette (focuses attention on subject)

```python
from PIL import Image, ImageDraw, ImageFilter

W, H = 1240, 1650
vignette = Image.new('L', (W, H), 0)
draw = ImageDraw.Draw(vignette)
draw.ellipse((W*-0.1, H*-0.1, W*1.1, H*1.1), fill=255)   # bright ellipse
vignette = vignette.filter(ImageFilter.GaussianBlur(180))

# Multiply onto image's RGB
img = Image.open('subject.png').convert('RGB')
darkened = Image.eval(img, lambda v: int(v * 0.75))      # 75% brightness
composite = Image.composite(img, darkened, vignette)
composite.save('subject_vignetted.png')
```

### Outpaint for portrait-aspect crop (when input is landscape)

If the source image is landscape (4:3 or 16:9) and you need a 3:4 portrait cover, you have two choices:

1. **Crop to fit (loses sides)** — what `background-size: cover` does by default. Acceptable when the subject is centered.
2. **Extend the background** — sample the edge color and pad. Works when the original has a flat-color background:

```python
from PIL import Image

src = Image.open('chloe_landscape.png').convert('RGB')
sw, sh = src.size
target_w, target_h = 1240, 1650
scale = target_h / sh
new_w = int(sw * scale)

# Resize image to fit target height; the result is wider OR narrower than target.
resized = src.resize((new_w, target_h), Image.LANCZOS)

if new_w >= target_w:
    # Crop to target width (lose sides) — same as bg-size: cover.
    left = (new_w - target_w) // 2
    out = resized.crop((left, 0, left + target_w, target_h))
else:
    # Pad with the edge color — sample left edge of the resized image.
    edge = resized.getpixel((0, target_h // 2))
    out = Image.new('RGB', (target_w, target_h), edge)
    out.paste(resized, ((target_w - new_w) // 2, 0))

out.save('chloe_3x4.png')
```

For better results when the edge color isn't flat, use `cv2.inpaint` or an actual outpainting model — out of scope for this skill, but worth knowing.

## When to use each mode in production

| Input type | Best mode | Why |
|---|---|---|
| Finished pixiv/twitter illustration with own backdrop | `keep` | Artist already designed the negative space. Don't fight them. |
| Transparent-PNG character cutout | `replace` | Lets you pick a backdrop that contrasts cover-line text. |
| Game splash screen (often busy) | `gradient` | Suppress backdrop noise without losing the action. |
| Photo of a real person on a studio backdrop | `keep` | Studio backdrops are already designed-for-text. |
| Photo with cluttered real-world background | `replace` (after rembg) | Real-world clutter steals attention. |

## Going to print: CMYK + 300 DPI

The skill outputs sRGB JPG/PNG by default. Actual print houses want CMYK at 300 DPI with a real color profile. The skill doesn't ship a CMYK pipeline (out of v2 scope) — for print, convert in Photoshop:

1. Open the `_final.jpg` (or `_final.png` for higher quality) in Photoshop.
2. `Image → Mode → CMYK Color`. Photoshop will ask which profile — use your printer's recommended profile (US Web Coated SWOP v2 is a safe default for offset).
3. `Image → Image Size`, set DPI to 300 and confirm dimensions match the print spec (e.g. 8.5×11 inches at 300 DPI = 2550×3300 px). Export the original cover at `--scale 3` first to have enough resolution.
4. `File → Save As → Photoshop PDF` with the press profile of your choice.

If you want CMYK metadata stamped on the export from this skill (without the conversion), pass `--dpi 300` to `export_covers.py` — that gets you the DPI metadata at native sRGB. The color conversion still needs Photoshop or another DTP tool.
