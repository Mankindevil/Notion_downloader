"""
art-title-maker — PIL-based high-fidelity generator.

Use this when the chosen variant needs effects HTML can't deliver cleanly:
  - Hard offset shadows with exact alpha/layer control
  - Scattered decorations (hearts/stars/sparkles) with collision detection
  - Custom transforms (skew + rotate stacked)
  - 4K (3840×2160) print output at exact DPI metadata
  - Layered compositing with per-element opacity

This file is a TEMPLATE — copy it into the working directory, rename, and
customize the CONFIG block + the build_title() function for the specific
character. Don't try to make it config-file-driven; per-title customization
is the point.

Usage:
    python generate_title_pil.py
    python generate_title_pil.py --out chloe_hero.png --width 3840 --height 2160 --dpi 500

Dependencies: Pillow.
    pip install Pillow
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
from dataclasses import dataclass
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG — customize this block per character.
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    # Canvas
    width: int = 3840
    height: int = 2160
    dpi: int = 500

    # Output is transparent — never set a fill here.
    canvas_bg: tuple = (0, 0, 0, 0)

    # Accent palette (sample these from the artwork — see references/color_theory.md).
    text_color:   tuple = (255, 255, 255, 255)        # hero text fill
    accent_color: tuple = (196, 30, 110, 255)         # outline / hard shadow
    shadow_color: tuple = (74, 12, 32, 200)           # deep shadow / depth
    glow_color:   tuple = (255, 216, 107, 120)        # soft glow / metal
    deco_palette: tuple = (
        (255, 255, 255, 255),
        (255, 216, 107, 255),
        (255, 95, 168, 220),
    )

    # Fonts — point at local TTF files. Bundled assets/fonts/ is a good place.
    # The skill ships with no fonts; download what you need and reference here.
    hero_font_path:    str = "Chewy-Regular.ttf"      # change to fit the direction
    support_font_path: str = "Cormorant-Italic.ttf"
    cjk_font_path:     str = "C:/Windows/Fonts/msyh.ttc"  # fallback to a system CJK font

    # Sizes (at 4K — scale all dimensions in build_title proportionally).
    hero_font_size:    int = 720
    support_font_size: int = 320
    subtitle_font_size: int = 200

    # Transforms on the hero word.
    skew_x: float = -0.12   # CSS skewX(-7deg) ≈ -0.12 in PIL's affine matrix
    rotate_deg: float = -2  # whole-block rotation

    # Hard shadow offset (in px at config resolution).
    shadow_offset: tuple = (28, 36)
    # Secondary shadow (deeper) for double-stack effect.
    shadow2_offset: tuple = (52, 68)
    shadow2_alpha: int = 140

    # Decoration scatter parameters.
    scatter_count:  int = 28
    scatter_size:   tuple = (60, 130)
    scatter_radius_safe: int = 1600  # don't place decorations closer than this to the title center

    # Hero text content.
    text_hero:     str = "Hero"
    text_subtitle: str = "クロエ"
    text_romaji:   str = "CHARACTER NAME"

    # Random seed for reproducible scatter.
    seed: int = 42


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if not os.path.exists(path):
        print(f"warning: font not found: {path} — falling back to default", file=sys.stderr)
        return ImageFont.load_default()
    return ImageFont.truetype(path, size)


def transparent_canvas(width: int, height: int, bg: tuple) -> Image.Image:
    return Image.new("RGBA", (width, height), bg)


def text_image(text: str, font: ImageFont.FreeTypeFont, color: tuple, padding: int = 80) -> Image.Image:
    """Render `text` onto a tight transparent RGBA image."""
    dummy = Image.new("RGBA", (10, 10))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + padding * 2
    h = bbox[3] - bbox[1] + padding * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((padding - bbox[0], padding - bbox[1]), text, font=font, fill=color)
    return img


def shadow_from_alpha(rgba: Image.Image, color: tuple) -> Image.Image:
    """Build a shadow layer by reusing the alpha channel of `rgba` and filling with `color`."""
    alpha = rgba.split()[3]
    shadow = Image.new("RGBA", rgba.size, color)
    shadow.putalpha(alpha)
    return shadow


def skew_image(rgba: Image.Image, sx: float) -> Image.Image:
    """Apply horizontal skew. sx is the x-shift per y-unit (negative leans right at top)."""
    w, h = rgba.size
    # Affine matrix is (a, b, c, d, e, f) where x' = a*x + b*y + c, y' = d*x + e*y + f
    # To skew so the top of the image moves right relative to the bottom, we want x' = x - sx*y.
    # PIL's AFFINE goes the *inverse* direction, so we use (1, sx, ...) for visual skewX(-deg).
    matrix = (1, sx, 0, 0, 1, 0)
    return rgba.transform((w + abs(int(sx * h)), h), Image.AFFINE, matrix, resample=Image.BICUBIC)


def rotate_image(rgba: Image.Image, deg: float) -> Image.Image:
    return rgba.rotate(deg, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))


def paste_centered(canvas: Image.Image, layer: Image.Image, cx: int, cy: int,
                    dx: int = 0, dy: int = 0) -> None:
    """Paste `layer` so its center sits at (cx + dx, cy + dy)."""
    x = cx - layer.width // 2 + dx
    y = cy - layer.height // 2 + dy
    canvas.alpha_composite(layer, dest=(x, y))


# ═══════════════════════════════════════════════════════════════════════════
# Decoration scatter — collision-detected hearts/stars
# ═══════════════════════════════════════════════════════════════════════════


def draw_heart(size: int, color: tuple) -> Image.Image:
    """Draw a small heart sprite on a transparent canvas."""
    pad = int(size * 0.25)
    w = size + pad * 2
    img = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    ox, oy = pad, pad
    d.ellipse((ox,           oy,           ox + s * 0.55, oy + s * 0.55), fill=color)
    d.ellipse((ox + s * 0.45, oy,           ox + s,        oy + s * 0.55), fill=color)
    triangle = [
        (ox + s * 0.02, oy + s * 0.38),
        (ox + s * 0.98, oy + s * 0.38),
        (ox + s * 0.50, oy + s * 1.00),
    ]
    d.polygon(triangle, fill=color)
    return img


def draw_star(size: int, color: tuple, points: int = 5) -> Image.Image:
    """Draw a star sprite on a transparent canvas."""
    pad = int(size * 0.2)
    w = size + pad * 2
    img = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = w / 2
    outer_r = size / 2
    inner_r = outer_r * 0.45
    pts = []
    for i in range(points * 2):
        r = outer_r if i % 2 == 0 else inner_r
        theta = -math.pi / 2 + math.pi * i / points
        pts.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    d.polygon(pts, fill=color)
    return img


def scatter_decorations(canvas: Image.Image, cfg: Config,
                         center_x: int, center_y: int, exclude_radius: int) -> None:
    """Place decorations randomly, avoiding the title area and overlaps."""
    rng = random.Random(cfg.seed)
    placed: list[tuple[int, int, int]] = []  # (x, y, radius)
    attempts = 0
    placed_count = 0
    while placed_count < cfg.scatter_count and attempts < 2000:
        attempts += 1
        x = rng.randint(80, cfg.width - 80)
        y = rng.randint(80, cfg.height - 80)
        size = rng.randint(*cfg.scatter_size)
        r = int(size * 0.6)
        # Avoid the title area.
        if math.hypot(x - center_x, y - center_y) < exclude_radius:
            continue
        # Avoid overlaps.
        if any(math.hypot(x - px, y - py) < r + pr for px, py, pr in placed):
            continue
        kind = rng.choice(["heart", "star"])
        color = rng.choice(cfg.deco_palette)
        sprite = draw_heart(size, color) if kind == "heart" else draw_star(size, color)
        sprite = rotate_image(sprite, rng.uniform(-30, 30))
        canvas.alpha_composite(sprite, dest=(x - sprite.width // 2, y - sprite.height // 2))
        placed.append((x, y, r))
        placed_count += 1


# ═══════════════════════════════════════════════════════════════════════════
# Main build
# ═══════════════════════════════════════════════════════════════════════════


def build_title(cfg: Config) -> Image.Image:
    """Compose the full title. Customize this for each character."""
    canvas = transparent_canvas(cfg.width, cfg.height, cfg.canvas_bg)
    cx, cy = cfg.width // 2, cfg.height // 2

    # Load fonts.
    hero_font    = load_font(cfg.hero_font_path,    cfg.hero_font_size)
    support_font = load_font(cfg.support_font_path, cfg.support_font_size)
    cjk_font     = load_font(cfg.cjk_font_path,     cfg.subtitle_font_size)

    # 1) Hero text as transparent layer.
    hero_layer = text_image(cfg.text_hero, hero_font, cfg.text_color, padding=120)
    hero_layer = skew_image(hero_layer, cfg.skew_x)
    hero_layer = rotate_image(hero_layer, cfg.rotate_deg)

    # 2) Two-tier shadow stack (depth).
    shadow1 = shadow_from_alpha(hero_layer, cfg.accent_color)
    shadow2_color = cfg.shadow_color[:3] + (cfg.shadow2_alpha,)
    shadow2 = shadow_from_alpha(hero_layer, shadow2_color)

    # 3) Composite shadows + hero (hero centered, shadows offset).
    paste_centered(canvas, shadow2, cx, cy, *cfg.shadow2_offset)
    paste_centered(canvas, shadow1, cx, cy, *cfg.shadow_offset)
    paste_centered(canvas, hero_layer, cx, cy)

    # 4) Subtitle (CJK) below.
    sub_layer = text_image(cfg.text_subtitle, cjk_font, cfg.text_color, padding=40)
    sub_shadow = shadow_from_alpha(sub_layer, cfg.accent_color)
    sub_y = cy + hero_layer.height // 2 + 60
    paste_centered(canvas, sub_shadow, cx, sub_y, 8, 10)
    paste_centered(canvas, sub_layer,  cx, sub_y)

    # 5) Romaji line below subtitle.
    romaji_font = load_font(cfg.support_font_path, int(cfg.support_font_size * 0.5))
    romaji_layer = text_image(cfg.text_romaji, romaji_font, cfg.glow_color, padding=20)
    rom_y = sub_y + sub_layer.height // 2 + 40
    paste_centered(canvas, romaji_layer, cx, rom_y)

    # 6) Decoration scatter (skip if cfg.scatter_count == 0).
    if cfg.scatter_count > 0:
        scatter_decorations(canvas, cfg, cx, cy, cfg.scatter_radius_safe)

    return canvas


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PIL-based high-fidelity title generator (4K, transparent, DPI-stamped).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "This script is a template — copy it into the working directory and\n"
            "customize the Config dataclass + build_title() per character.\n"
        ),
    )
    ap.add_argument("--out", default="title_pil.png", help="Output PNG path")
    ap.add_argument("--width",  type=int, default=Config.width)
    ap.add_argument("--height", type=int, default=Config.height)
    ap.add_argument("--dpi",    type=int, default=Config.dpi)
    ap.add_argument("--seed",   type=int, default=Config.seed,
                    help="Random seed for the decoration scatter (default: 42)")
    args = ap.parse_args()

    cfg = Config(width=args.width, height=args.height, dpi=args.dpi, seed=args.seed)
    img = build_title(cfg)
    img.save(args.out, dpi=(cfg.dpi, cfg.dpi))
    print(f"saved {args.out} ({cfg.width}×{cfg.height} @ {cfg.dpi} DPI, transparent)")


if __name__ == "__main__":
    main()
