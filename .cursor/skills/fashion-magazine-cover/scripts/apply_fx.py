"""
apply_fx — PIL post-pass for atmospheric effects on a background layer.

After the layered export produces `cover_*_background.png`, this script can
overlay PIL-quality effects that the HTML pipeline can't deliver sharply:
procedural lens flare and procedural paper grain.

Usage:
    python apply_fx.py --input cover_a_background.png \\
                       --flare 0.75,0.30,warm \\
                       --grain 0.06

    # Multiple flares
    python apply_fx.py --input bg.png --flare 0.20,0.15,cool --flare 0.85,0.40,magenta

    # Output to a different file (default: overwrite input)
    python apply_fx.py --input bg.png --grain 0.08 --output bg_grained.png

Dependencies:
    pip install pillow
"""
import argparse
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


# ─── Lens flare ──────────────────────────────────────────────────────────────

FLARE_PRESETS = {
    "warm":    {"core": (255, 240, 210), "ring": (255, 180, 90)},
    "cool":    {"core": (240, 245, 255), "ring": (140, 180, 255)},
    "magenta": {"core": (255, 220, 240), "ring": (220, 100, 200)},
}


def make_flare(
    canvas_size: tuple[int, int],
    x_pct: float,
    y_pct: float,
    preset: str = "warm",
    intensity: float = 1.0,
) -> Image.Image:
    """Procedural lens flare layer (RGBA). x_pct/y_pct are 0–1 of canvas size.

    Composites a bright central hotspot + a few ghost rings along the line
    through (x, y) and the image center.
    """
    if preset not in FLARE_PRESETS:
        print(f"warning: unknown flare preset '{preset}', falling back to warm",
              file=sys.stderr)
        preset = "warm"
    colors = FLARE_PRESETS[preset]
    w, h = canvas_size
    cx, cy = int(w * x_pct), int(h * y_pct)
    img_cx, img_cy = w // 2, h // 2

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Central hotspot — a big soft circle.
    core_r = int(min(w, h) * 0.06 * intensity)
    for r, a in [(core_r * 3, 30), (core_r * 2, 60), (core_r, 180), (core_r // 2, 255)]:
        c = colors["core"] + (int(a * intensity),)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)

    # Blur the core hotspot.
    layer = layer.filter(ImageFilter.GaussianBlur(core_r * 0.5))

    # Ghost rings along the line through (cx, cy) and the image center.
    dx, dy = img_cx - cx, img_cy - cy
    ghost_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ghost_draw = ImageDraw.Draw(ghost_layer)
    for i, (t, r_scale, alpha) in enumerate([
        (0.4, 0.7, 40),
        (0.8, 1.2, 30),
        (1.2, 0.5, 50),
        (1.6, 0.9, 25),
    ]):
        gx = int(cx + dx * t)
        gy = int(cy + dy * t)
        r = int(core_r * r_scale)
        ring_color = colors["ring"] + (int(alpha * intensity),)
        # Hollow ring
        ghost_draw.ellipse((gx - r, gy - r, gx + r, gy + r),
                           outline=ring_color, width=max(2, r // 8))
        # Soft inner glow
        ghost_draw.ellipse((gx - r // 2, gy - r // 2, gx + r // 2, gy + r // 2),
                           fill=colors["ring"] + (int(alpha * 0.6 * intensity),))

    ghost_layer = ghost_layer.filter(ImageFilter.GaussianBlur(core_r * 0.25))

    # Combine.
    layer.alpha_composite(ghost_layer)
    return layer


# ─── Paper grain ────────────────────────────────────────────────────────────

def make_grain(canvas_size: tuple[int, int], intensity: float = 0.06,
               seed: int = 42) -> Image.Image:
    """Procedural paper-grain noise layer (RGBA).

    Intensity is the luminance variance (0 = none, 0.1 = pretty noisy).
    Deterministic for a given seed so repeated runs produce identical grain.
    """
    w, h = canvas_size
    random.seed(seed)
    # Generate a smaller noise tile, then scale up — gives a chunkier grain.
    tile_size = max(2, int(min(w, h) / 400))
    tw, th = w // tile_size + 1, h // tile_size + 1

    noise = Image.new("L", (tw, th))
    pixels = noise.load()
    for y in range(th):
        for x in range(tw):
            pixels[x, y] = random.randint(0, int(255 * intensity * 2))

    # Scale up to canvas size with bilinear interp.
    noise = noise.resize((w, h), Image.BILINEAR)
    # Wrap into RGBA with the noise as alpha and a neutral gray fill.
    # Using gray means the multiply/overlay blend just darkens by the noise alpha.
    rgba = Image.new("RGBA", (w, h), (128, 128, 128, 0))
    rgba.putalpha(noise)
    return rgba


# ─── Composition ─────────────────────────────────────────────────────────────

def apply_effects(
    input_path: Path,
    output_path: Path,
    flares: list[tuple[float, float, str]],
    grain_intensity: float,
) -> None:
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size

    for x, y, preset in flares:
        flare = make_flare((w, h), x, y, preset)
        img.alpha_composite(flare)

    if grain_intensity > 0:
        grain = make_grain((w, h), grain_intensity)
        # Blend the grain via overlay — desaturates pure colors slightly,
        # adds visible noise.
        img = Image.alpha_composite(img, grain)

    # Save as PNG (preserves alpha) or JPG (flattens).
    if output_path.suffix.lower() in (".jpg", ".jpeg"):
        rgb = Image.new("RGB", img.size, (255, 255, 255))
        rgb.paste(img, mask=img.split()[3])
        rgb.save(output_path, quality=92, optimize=True)
    else:
        img.save(output_path)

    print(f"saved {output_path}  ({len(flares)} flare(s), grain={grain_intensity})")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_flare(s: str) -> tuple[float, float, str]:
    """Parse 'x,y,preset' from CLI. e.g. '0.75,0.30,warm'."""
    parts = s.split(",")
    if len(parts) < 2 or len(parts) > 3:
        raise argparse.ArgumentTypeError(
            f"--flare must be 'x,y[,preset]', got '{s}'"
        )
    try:
        x, y = float(parts[0]), float(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(f"--flare x,y must be floats in '{s}'")
    if not (0 <= x <= 1) or not (0 <= y <= 1):
        raise argparse.ArgumentTypeError(f"--flare x,y must be 0–1 in '{s}'")
    preset = parts[2] if len(parts) == 3 else "warm"
    return (x, y, preset)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Apply PIL atmospheric effects to a background-layer PNG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python apply_fx.py --input bg.png --flare 0.75,0.30,warm\n"
            "  python apply_fx.py --input bg.png --grain 0.06\n"
            "  python apply_fx.py --input bg.png --flare 0.2,0.15,cool --flare 0.85,0.4,magenta\n"
            "  python apply_fx.py --input bg.png --grain 0.08 --output bg_fx.png\n"
            "\n"
            "Flare presets: warm | cool | magenta\n"
            "Coordinates are 0–1 fractions of image width/height.\n"
        ),
    )
    ap.add_argument("--input", "-i", type=Path, required=True,
                    help="Input PNG (typically a background-layer export)")
    ap.add_argument("--output", "-o", type=Path, default=None,
                    help="Output path (default: overwrite input)")
    ap.add_argument("--flare", action="append", default=[], type=parse_flare,
                    help="Add a lens flare: 'x,y[,preset]'. Pass multiple times for multiple flares.")
    ap.add_argument("--grain", type=float, default=0.0,
                    help="Paper-grain intensity, 0–0.15 (default: 0 = off)")
    args = ap.parse_args()

    if not args.input.exists():
        sys.exit(f"error: {args.input} not found")

    output = args.output or args.input
    apply_effects(args.input, output, args.flare, args.grain)


if __name__ == "__main__":
    main()
