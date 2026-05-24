"""
fashion-magazine-cover — PIL-based generator for the pixel-perfect path.

Use this when the HTML→Playwright pipeline isn't enough — print-DPI output,
exact barcode rendering, layered text-on-image compositing with full alpha
control, paper-grain texture overlays. The HTML pipeline is faster for
typical web covers; reach for this when the chosen variant needs to go to
print or needs effects HTML can't deliver consistently.

Usage:
    python generate_cover_pil.py --config cover_b.json --out cover_b_print.png

The config JSON describes a single cover. See `example_config.json` in the
same directory for the full schema (or the `EXAMPLE_CONFIG` constant below).

Dependencies:
    pip install pillow                # required
    pip install rembg                 # optional, for --remove-bg

Fonts:
    Pass --fonts-dir <path> if the Google Fonts files aren't on PYTHONPATH.
    Defaults to scanning %USERPROFILE%\\AppData\\Local\\Microsoft\\Windows\\Fonts
    on Windows and ~/.fonts and /usr/share/fonts on Linux.
"""
import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# Default config — a starting point you can copy + edit. Mirrors the HTML
# template's variant B (high-fashion editorial).
#
# v2 token-driven workflow: the config below corresponds to ONE cover-variant
# instance with its tokens already chosen. See references/design_tokens.md for
# how to extract tokens from a subject.
#
# Size: set to [null, null] to auto-derive from the input image (capped to
# 1860px on the longest side). Or set explicit pixel dims if you need them.
EXAMPLE_CONFIG = {
    "size": [None, None],              # null,null = auto-derive from image
    "size_cap": 1860,                  # cap for longest side when auto-deriving
    "image": "subject.png",
    "bg_mode": "keep",                 # keep | replace | gradient
    "replace_color": [255, 100, 160],  # used when bg_mode == 'replace'
    "tokens": {
        # Design tokens — what makes this cover's identity. See design_tokens.md.
        "font_pair": "modern-fashion", # named pair from design_tokens.md
        "palette": {
            "ink":    [255, 255, 255],
            "accent": [216, 178, 90],
            "paper":  [255, 245, 232],
            "shade":  [0, 0, 0, 115]   # rgba
        },
        "decoration_vocab": "none",    # none | stars-hearts | botanical | acid-rule
        "mood_overlay": ["vignette"],  # subset of: vignette | rim-light | grade-warm | grade-cool | grade-cinematic | grade-acid
        "composition_bias": "center"   # center | left | right | top | off-axis
    },
    "overlay": {
        "top_alpha": 0.20,
        "bottom_alpha": 0.55,
        "tint": None                   # or [r,g,b] for a colored overlay
    },
    "masthead": {
        "text": "CHLOE",
        "font": "BodoniModa-Black",
        "size": 280,
        "color": [255, 255, 255],
        "top": 60,
        "letter_spacing": 0.01,
        "all_caps": True
    },
    "dateline": {
        "text": "MAY 2026 · NO. 17 · ¥980",
        "font": "MarcellusSC-Regular",
        "size": 22,
        "color": [255, 255, 255],
        "top": 360,
        "letter_spacing": 0.5,
        "center": True
    },
    "coverlines": [
        {
            "headline": "The Kuro Issue",
            "subline": "ON THE COVER · CHLOE VON EINZBERN",
            "font": "BodoniModa-Italic",
            "size": 90,
            "color": [255, 255, 255],
            "position": [80, 1220],
            "max_width": 600
        }
    ],
    "signature": {
        "text": "Chloe",
        "font": "Italianno-Regular",
        "size": 220,
        "color": [255, 255, 255],
        "position": [None, 1450],       # None x = centered
        "shadow": [0, 6, 24, [0, 0, 0, 130]]
    },
    "barcode": {
        "position": [80, 1580],
        "height": 50,
        "color": [255, 255, 255]
    },
    "grain": {
        "enabled": False,
        "intensity": 0.06
    },
    "dpi": 96
}


# ─── Font loading ────────────────────────────────────────────────────────────

def find_font(name: str, fonts_dir: Optional[Path] = None) -> Optional[Path]:
    """Search common locations for the font file. Returns the path or None."""
    candidates = [
        f"{name}.ttf", f"{name}.otf",
        f"{name.replace('-', '')}.ttf", f"{name.replace('-', '')}.otf",
    ]
    search_dirs = []
    if fonts_dir:
        search_dirs.append(Path(fonts_dir))
    # Project-local cache (drop fonts in ./fonts/ alongside the working dir)
    search_dirs.append(Path.cwd() / "fonts")
    # OS-level font directories
    if sys.platform == "win32":
        search_dirs.append(Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts")
        search_dirs.append(Path(os.environ["USERPROFILE"]) / "AppData/Local/Microsoft/Windows/Fonts")
    elif sys.platform == "darwin":
        search_dirs += [Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path.home() / "Library/Fonts"]
    else:
        search_dirs += [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts"]

    for d in search_dirs:
        if not d.exists():
            continue
        for cand in candidates:
            # Direct match
            p = d / cand
            if p.exists():
                return p
            # Recursive search (one level — Google Fonts often nests by family)
            for sub in d.glob(f"**/{cand}"):
                return sub
    return None


def load_font(name: str, size: int, fonts_dir: Optional[Path] = None) -> ImageFont.ImageFont:
    """Load a font by name. Falls back to PIL default with a warning."""
    path = find_font(name, fonts_dir)
    if path:
        return ImageFont.truetype(str(path), size)
    print(f"warning: font '{name}' not found — using PIL default. "
          f"Download from Google Fonts and place in ./fonts/ to fix.",
          file=sys.stderr)
    return ImageFont.load_default()


# ─── Background composition ─────────────────────────────────────────────────

def resolve_size(cfg: dict) -> tuple[int, int]:
    """Derive (w, h) from config — explicit pixels, or auto-derive from input image."""
    size = cfg.get("size", [None, None])
    if size[0] and size[1]:
        return size[0], size[1]
    # Auto-derive from input image, capped to size_cap on the longest side.
    cap = cfg.get("size_cap", 1860)
    with Image.open(cfg["image"]) as src:
        sw, sh = src.size
    if max(sw, sh) > cap:
        scale = cap / max(sw, sh)
        return int(sw * scale), int(sh * scale)
    return sw, sh


def make_background(cfg: dict, fonts_dir: Optional[Path]) -> Image.Image:
    """Build the background canvas at config size with the subject image."""
    w, h = resolve_size(cfg)
    # Cache so downstream draw functions see the resolved size.
    cfg["_resolved_size"] = (w, h)
    mode = cfg.get("bg_mode", "keep")

    if mode == "replace":
        # Solid color canvas, then composite character on top.
        bg = Image.new("RGB", (w, h), tuple(cfg.get("replace_color", [240, 240, 240])))
        char = Image.open(cfg["image"]).convert("RGBA")
        ratio = (h * 0.85) / char.height
        cw, ch = int(char.width * ratio), int(char.height * ratio)
        char = char.resize((cw, ch), Image.LANCZOS)
        bg.paste(char, ((w - cw) // 2, int(h * 0.10)), char)
        return bg

    # 'keep' or 'gradient' — image fills the canvas via cover-style crop.
    src = Image.open(cfg["image"]).convert("RGB")
    sw, sh = src.size
    # Scale so the smaller dimension fills (cover semantics).
    scale = max(w / sw, h / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    src = src.resize((nw, nh), Image.LANCZOS)
    # Center crop to target.
    left, top = (nw - w) // 2, (nh - h) // 2
    return src.crop((left, top, left + w, top + h))


def apply_overlay(canvas: Image.Image, cfg: dict) -> Image.Image:
    """Top + bottom darkening gradient for text legibility."""
    w, h = canvas.size
    ov = cfg.get("overlay") or {}
    top_a = ov.get("top_alpha", 0.0)
    bot_a = ov.get("bottom_alpha", 0.0)
    tint = ov.get("tint") or [0, 0, 0]

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pixels = overlay.load()
    for y in range(h):
        t = y / (h - 1)
        # Two-zone gradient: bright top → clear middle → bright bottom.
        if t < 0.3:
            a = int(top_a * 255 * (1 - t / 0.3))
        elif t > 0.7:
            a = int(bot_a * 255 * (t - 0.7) / 0.3)
        else:
            a = 0
        if a > 0:
            for x in range(w):
                pixels[x, y] = (tint[0], tint[1], tint[2], a)

    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")
    canvas.alpha_composite(overlay)
    return canvas.convert("RGB")


# ─── Text rendering ──────────────────────────────────────────────────────────

def draw_text(
    img: Image.Image,
    text: str,
    font: ImageFont.ImageFont,
    pos: tuple[int, int],
    color: tuple[int, int, int],
    letter_spacing: float = 0.0,
    shadow: Optional[list] = None,
) -> None:
    """Draw text with optional drop-shadow + letter-spacing."""
    draw = ImageDraw.Draw(img, "RGBA")

    if shadow:
        ox, oy, blur, scolor = shadow
        # Render shadow text on a separate layer, blur it, composite.
        sh_img = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh_draw = ImageDraw.Draw(sh_img)
        sh_draw.text((pos[0] + ox, pos[1] + oy), text, font=font, fill=tuple(scolor))
        if blur:
            sh_img = sh_img.filter(ImageFilter.GaussianBlur(blur))
        img.alpha_composite(sh_img) if img.mode == "RGBA" else img.paste(sh_img, (0, 0), sh_img)

    if letter_spacing and letter_spacing != 0:
        # Manual letter-spacing — draw glyph-by-glyph.
        x, y = pos
        for ch in text:
            draw.text((x, y), ch, font=font, fill=color)
            bbox = draw.textbbox((x, y), ch, font=font)
            x = bbox[2] + int(font.size * letter_spacing)
    else:
        draw.text(pos, text, font=font, fill=color)


def draw_masthead(canvas: Image.Image, cfg: dict, fonts_dir: Optional[Path]) -> None:
    m = cfg["masthead"]
    font = load_font(m["font"], m["size"], fonts_dir)
    text = m["text"].upper() if m.get("all_caps") else m["text"]
    w = canvas.width

    # Compute width of text for centering.
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (w - tw) // 2

    draw_text(canvas, text, font, (x, m["top"]),
              tuple(m["color"]), letter_spacing=m.get("letter_spacing", 0))


def draw_dateline(canvas: Image.Image, cfg: dict, fonts_dir: Optional[Path]) -> None:
    d = cfg.get("dateline")
    if not d:
        return
    font = load_font(d["font"], d["size"], fonts_dir)
    text = d["text"]
    if d.get("center"):
        draw = ImageDraw.Draw(canvas)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = (canvas.width - tw) // 2
    else:
        x = d.get("position", [80, 0])[0]
    draw_text(canvas, text, font, (x, d["top"]),
              tuple(d["color"]), letter_spacing=d.get("letter_spacing", 0))


def draw_coverlines(canvas: Image.Image, cfg: dict, fonts_dir: Optional[Path]) -> None:
    for cl in cfg.get("coverlines", []):
        font = load_font(cl["font"], cl["size"], fonts_dir)
        pos = tuple(cl["position"])
        draw_text(canvas, cl["headline"], font, pos, tuple(cl["color"]))
        if cl.get("subline"):
            sub_font = load_font("MarcellusSC-Regular", int(cl["size"] * 0.22), fonts_dir)
            draw_text(canvas, cl["subline"], sub_font,
                      (pos[0], pos[1] + int(cl["size"] * 1.05)),
                      tuple(cl["color"]), letter_spacing=0.32)


def draw_signature(canvas: Image.Image, cfg: dict, fonts_dir: Optional[Path]) -> None:
    s = cfg.get("signature")
    if not s:
        return
    font = load_font(s["font"], s["size"], fonts_dir)
    text = s["text"]
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]

    pos = list(s["position"])
    if pos[0] is None:
        pos[0] = (canvas.width - tw) // 2

    canvas_rgba = canvas.convert("RGBA") if canvas.mode != "RGBA" else canvas
    draw_text(canvas_rgba, text, font, tuple(pos), tuple(s["color"]),
              shadow=s.get("shadow"))
    if canvas_rgba is not canvas:
        canvas.paste(canvas_rgba.convert("RGB"))


def draw_barcode(canvas: Image.Image, cfg: dict) -> None:
    """Render a visually-correct (not scannable) barcode."""
    b = cfg.get("barcode")
    if not b:
        return
    x, y = b["position"]
    h = b.get("height", 50)
    color = tuple(b["color"])
    # Pseudo-random but deterministic bar widths.
    widths = [2.5, 1, 1.5, 2, 1, 3, 1.5, 1, 2, 1, 2.5, 1.5, 1, 2, 1, 3, 1, 2]
    draw = ImageDraw.Draw(canvas)
    cx = x
    for w in widths:
        bw = max(1, int(w))
        draw.rectangle([cx, y, cx + bw, y + h], fill=color)
        cx += bw + 2


def apply_grain(canvas: Image.Image, cfg: dict) -> Image.Image:
    """Optional paper-grain texture overlay."""
    g = cfg.get("grain") or {}
    if not g.get("enabled"):
        return canvas
    import random
    intensity = g.get("intensity", 0.05)
    w, h = canvas.size
    noise = Image.new("L", (w, h))
    px = noise.load()
    random.seed(42)
    for y in range(h):
        for x in range(w):
            px[x, y] = random.randint(0, int(255 * intensity))
    noise_rgba = Image.merge("RGBA", (noise, noise, noise, Image.new("L", (w, h), 80)))
    canvas_rgba = canvas.convert("RGBA")
    canvas_rgba.alpha_composite(noise_rgba)
    return canvas_rgba.convert("RGB")


# ─── Main ─────────────────────────────────────────────────────────────────────

def build(cfg: dict, out_path: str, fonts_dir: Optional[Path]) -> None:
    canvas = make_background(cfg, fonts_dir)
    canvas = apply_overlay(canvas, cfg)
    canvas = canvas.convert("RGB")

    draw_masthead(canvas, cfg, fonts_dir)
    draw_dateline(canvas, cfg, fonts_dir)
    draw_coverlines(canvas, cfg, fonts_dir)
    draw_signature(canvas, cfg, fonts_dir)
    draw_barcode(canvas, cfg)
    canvas = apply_grain(canvas, cfg)

    dpi = cfg.get("dpi", 96)
    save_kwargs = {"dpi": (dpi, dpi)}
    if out_path.lower().endswith((".jpg", ".jpeg")):
        save_kwargs["quality"] = 92
        save_kwargs["optimize"] = True
    canvas.save(out_path, **save_kwargs)
    print(f"saved {out_path}  ({canvas.size[0]}×{canvas.size[1]}, {dpi} DPI)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="PIL-based fashion-magazine-cover generator (print-quality path).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python generate_cover_pil.py --emit-example > my_cover.json\n"
            "  python generate_cover_pil.py --config my_cover.json --out cover.png\n"
            "  python generate_cover_pil.py --config my_cover.json --out cover.png --dpi 500\n"
        ),
    )
    ap.add_argument("--config", help="JSON config describing the cover")
    ap.add_argument("--out", help="Output file path (.png or .jpg)")
    ap.add_argument("--fonts-dir", help="Directory containing font files (.ttf/.otf)")
    ap.add_argument("--dpi", type=int, help="Override DPI in the config")
    ap.add_argument("--emit-example", action="store_true",
                    help="Print the example config JSON to stdout and exit")
    args = ap.parse_args()

    if args.emit_example:
        print(json.dumps(EXAMPLE_CONFIG, indent=2))
        return

    if not args.config or not args.out:
        ap.error("--config and --out are required (unless --emit-example)")

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if args.dpi:
        cfg["dpi"] = args.dpi

    fonts_dir = Path(args.fonts_dir) if args.fonts_dir else None
    build(cfg, args.out, fonts_dir)


if __name__ == "__main__":
    main()
