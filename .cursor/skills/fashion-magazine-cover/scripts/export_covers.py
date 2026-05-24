"""
fashion-magazine-cover v3 — export each .cover from cover_options.html.

NEW in v3:
  • 4K-by-default — auto-computes device_scale_factor so the longest side of
    every screenshot lands at --target-size (default 3840). Override with
    --scale to force a specific multiplier.
  • Text-config patching — reads cover_config.json (auto-detected) and patches
    every [data-text-key] element in the matching .cover before screenshot.
    Lets the user edit cover text via JSON without touching the HTML.

Carried over from v2:
  • Dynamic per-cover viewport sizing — reads --cw/--ch CSS variables on each
    .cover and screenshots at that aspect.
  • Layered export (DEFAULT ON) — for each .cover, screenshots three layer
    groups (background / effects / artwork) as separate transparent PNGs plus
    one composited final JPG, so they can be edited in Photoshop.
  • --font-dir — load local .ttf/.otf font files in addition to Google Fonts.

Usage (from the working directory containing cover_options.html):
    python export_covers.py                              # 4K + layered + JPG default
    python export_covers.py --no-layered                 # single composited JPG only
    python export_covers.py --target-size 1920           # quick preview, ~1920px longest
    python export_covers.py --target-size 5120           # 5K for print
    python export_covers.py --scale 3                    # force exact 3x, ignore target
    python export_covers.py --text-config my_text.json   # custom text-config path
    python export_covers.py --no-text-config             # ignore any cover_config.json
    python export_covers.py --font-dir ./fonts           # custom local fonts
    python export_covers.py --out-prefix nahida          # cover_X → nahida_X
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright


SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]+")
DEFAULT_TEXT_CONFIG = "cover_config.json"


def safe(s: str) -> str:
    return SAFE_NAME_RE.sub("_", s).strip("_") or "cover"


def build_font_face_css(font_dir: Path) -> str:
    """Scan a directory for font files and emit @font-face declarations.

    The font's filename stem (e.g. 'MyDisplayFont' from 'MyDisplayFont.ttf')
    becomes its font-family name. The user can then reference it via
    `font-family: 'MyDisplayFont'` in their HTML.
    """
    if not font_dir.exists():
        print(f"warning: --font-dir {font_dir} does not exist; skipping local fonts",
              file=sys.stderr)
        return ""
    decls = []
    for path in sorted(font_dir.glob("**/*")):
        if path.suffix.lower() not in (".ttf", ".otf", ".woff", ".woff2"):
            continue
        family = path.stem
        url = path.resolve().as_uri()
        fmt = {
            ".ttf":   "truetype",
            ".otf":   "opentype",
            ".woff":  "woff",
            ".woff2": "woff2",
        }[path.suffix.lower()]
        decls.append(
            f"@font-face {{ font-family: '{family}'; "
            f"src: url('{url}') format('{fmt}'); "
            f"font-display: block; }}"
        )
    if not decls:
        print(f"warning: no font files found in {font_dir}", file=sys.stderr)
        return ""
    print(f"loaded {len(decls)} custom fonts from {font_dir}")
    return "\n".join(decls)


def stamp_dpi(path: str, dpi: int) -> None:
    """Write DPI metadata into the PNG/JPG so print software treats it right."""
    try:
        from PIL import Image
    except ImportError:
        print(f"warning: Pillow not installed — skipping DPI metadata for {path}")
        return
    try:
        img = Image.open(path)
        img.save(path, dpi=(dpi, dpi))
    except Exception as e:
        print(f"warning: failed to set DPI on {path}: {e}")


def load_text_config(path: Path | None, fallback_default: bool) -> dict | None:
    """Return parsed text-config JSON, or None if no config should be applied.

    Honors explicit --text-config first; otherwise looks for cover_config.json
    in cwd if fallback_default is True.
    """
    if path is not None:
        if not path.exists():
            print(f"warning: --text-config {path} not found; skipping text patch",
                  file=sys.stderr)
            return None
        target = path
    elif fallback_default and Path(DEFAULT_TEXT_CONFIG).exists():
        target = Path(DEFAULT_TEXT_CONFIG)
    else:
        return None
    try:
        with target.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"warning: failed to parse {target}: {e}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"warning: {target} is not a JSON object; skipping", file=sys.stderr)
        return None
    print(f"loaded text config from {target} ({len(data)} cover entr"
          f"{'y' if len(data) == 1 else 'ies'})")
    return data


async def apply_text_config(page, config: dict) -> None:
    """Patch every [data-text-key] inside each .cover with the JSON values.

    Only sets textContent (no HTML injection) — safe against accidental tags.
    """
    await page.evaluate(
        """(cfg) => {
            Object.entries(cfg).forEach(([coverId, fields]) => {
              const root = document.getElementById(coverId);
              if (!root) {
                console.warn('text-config: no cover with id=' + coverId);
                return;
              }
              Object.entries(fields).forEach(([key, value]) => {
                const els = root.querySelectorAll('[data-text-key="' + key + '"]');
                if (!els.length) {
                  console.warn('text-config: no [data-text-key=' + key +
                               '] under ' + coverId);
                  return;
                }
                els.forEach(el => { el.textContent = String(value); });
              });
            });
        }""",
        config,
    )


async def get_cover_size(cover_handle) -> tuple[int, int]:
    """Read computed --cw/--ch from the .cover element, fall back to offset size."""
    dims = await cover_handle.evaluate(
        "el => { const s = getComputedStyle(el);"
        " return {"
        "  cw: parseFloat(s.getPropertyValue('--cw')) || el.offsetWidth,"
        "  ch: parseFloat(s.getPropertyValue('--ch')) || el.offsetHeight"
        " }; }"
    )
    return int(dims["cw"]), int(dims["ch"])


async def probe_cover_dims(p, file_url: str) -> list[tuple[str, int, int]]:
    """Quick first pass: open the page, read every .cover's id + --cw/--ch.

    Used to compute the device_scale_factor needed to hit --target-size.
    """
    ctx = await p.chromium.launch()
    context = await ctx.new_context(viewport={"width": 1024, "height": 1024})
    page = await context.new_page()
    await page.goto(file_url)
    try:
        await page.wait_for_load_state("networkidle", timeout=5_000)
    except Exception:
        pass
    handles = await page.query_selector_all(".cover")
    out: list[tuple[str, int, int]] = []
    for h in handles:
        cid = await h.get_attribute("id") or "cover"
        cw, ch = await get_cover_size(h)
        out.append((cid, cw, ch))
    await ctx.close()
    return out


async def hide_layers_for(cover_handle, keep_layer: str) -> None:
    """Hide all layer groups except the named one. Used for layered export."""
    await cover_handle.evaluate(
        """(el, keep) => {
            el.querySelectorAll('[data-layer]').forEach(l => {
              l.style.visibility = (l.dataset.layer === keep) ? 'visible' : 'hidden';
            });
            // For non-background layers, suppress the .cover's own bg + box-shadow.
            if (keep !== 'background') {
              el.dataset._prevBg = el.style.background || '';
              el.style.background = 'transparent';
              el.style.boxShadow = 'none';
            } else {
              if (el.dataset._prevBg !== undefined) {
                el.style.background = el.dataset._prevBg;
                delete el.dataset._prevBg;
              }
            }
            // Hide the cover-id helper label.
            const lbl = el.querySelector('.cover-id');
            if (lbl) lbl.style.display = 'none';
        }""",
        keep_layer,
    )


async def restore_all_layers(cover_handle) -> None:
    """Re-show all layer groups (after a layered-mode pass) for the final composite."""
    await cover_handle.evaluate(
        """el => {
            el.querySelectorAll('[data-layer]').forEach(l => {
              l.style.visibility = '';
            });
            if (el.dataset._prevBg !== undefined) {
              el.style.background = el.dataset._prevBg;
              delete el.dataset._prevBg;
            }
            const lbl = el.querySelector('.cover-id');
            if (lbl) lbl.style.display = 'none';   // stay hidden in the final
        }"""
    )


def resolve_scale(cover_dims: list[tuple[str, int, int]],
                  explicit_scale: float | None,
                  target_size: int) -> float:
    """Pick the device_scale_factor for the whole batch.

    If the user passed --scale, honor it.
    Else: compute the scale needed to push the largest cover's longest side
    to >= target_size, so every cover meets the 4K floor.
    """
    if explicit_scale is not None:
        return float(explicit_scale)
    if not cover_dims:
        return 1.0
    longest = max(max(cw, ch) for _, cw, ch in cover_dims)
    if longest <= 0:
        return 1.0
    return max(1.0, target_size / longest)


async def export(
    html_file: str,
    out_prefix: str,
    explicit_scale: float | None,
    target_size: int,
    fmt: str,
    quality: int,
    dpi: int,
    layered: bool,
    font_dir: Path | None,
    text_config_path: Path | None,
    use_default_text_config: bool,
) -> None:
    if not os.path.exists(html_file):
        sys.exit(f"error: {html_file} not found")

    html_path = os.path.abspath(html_file).replace(os.sep, "/")
    file_url = f"file:///{html_path}"

    text_config = load_text_config(text_config_path, use_default_text_config)

    async with async_playwright() as p:
        # First pass — probe dims so we can pick the right device scale factor.
        cover_dims = await probe_cover_dims(p, file_url)
        if not cover_dims:
            sys.exit("error: no .cover elements found in HTML")
        scale = resolve_scale(cover_dims, explicit_scale, target_size)
        longest_css = max(max(cw, ch) for _, cw, ch in cover_dims)
        print(f"target-size: {target_size}px  |  longest .cover css-px: {longest_css}"
              f"  |  device_scale_factor: {scale:.3f}")

        browser = await p.chromium.launch()
        # Viewport must accommodate the largest cover at the chosen scale; Playwright
        # screenshots elements at viewport/dpr-multiplied resolution.
        max_w_css = max(cw for _, cw, _ in cover_dims)
        max_h_css = max(ch for _, _, ch in cover_dims)
        vp_w = max(1024, int(max_w_css) + 64)
        vp_h = max(1024, int(max_h_css) + 64)
        context = await browser.new_context(
            viewport={"width": vp_w, "height": vp_h},
            device_scale_factor=scale,
        )
        page = await context.new_page()
        await page.goto(file_url)

        # Inject local-font @font-face block BEFORE network-idle wait, so
        # the new fonts load with the rest.
        if font_dir is not None:
            css = build_font_face_css(font_dir)
            if css:
                await page.add_style_tag(content=css)

        # Wait for Google Fonts + background-image decode to settle.
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        await page.wait_for_timeout(1800)

        # Patch text from config (before screenshots).
        if text_config:
            await apply_text_config(page, text_config)

        # Wipe the page-level background so layered exports don't pick up #2a2a2a.
        await page.evaluate(
            "() => { document.documentElement.style.background = 'transparent';"
            " document.body.style.background = 'transparent'; }"
        )

        covers = await page.query_selector_all(".cover")

        ext_final = "jpg" if fmt in ("jpg", "jpeg") else "png"

        for i, cover in enumerate(covers):
            cover_id = await cover.get_attribute("id") or f"cover-{i}"
            slug = safe(cover_id)
            cw, ch = await get_cover_size(cover)
            out_w = round(cw * scale)
            out_h = round(ch * scale)
            print(f"\n→ {slug}  css {cw}×{ch}  → output {out_w}×{out_h}px")

            if layered:
                # 1) background layer (opaque): show only data-layer=background
                await hide_layers_for(cover, "background")
                bg_path = f"{out_prefix}_{slug}_background.png"
                await cover.screenshot(path=bg_path, type="png")
                if dpi != 96: stamp_dpi(bg_path, dpi)
                print(f"   saved {bg_path}")

                # 2) effects layer (transparent)
                await hide_layers_for(cover, "effects")
                fx_path = f"{out_prefix}_{slug}_effects.png"
                await cover.screenshot(path=fx_path, type="png", omit_background=True)
                if dpi != 96: stamp_dpi(fx_path, dpi)
                print(f"   saved {fx_path}")

                # 3) artwork layer (transparent)
                await hide_layers_for(cover, "artwork")
                art_path = f"{out_prefix}_{slug}_artwork.png"
                await cover.screenshot(path=art_path, type="png", omit_background=True)
                if dpi != 96: stamp_dpi(art_path, dpi)
                print(f"   saved {art_path}")

                # Restore everything for the final composite.
                await restore_all_layers(cover)

            # 4) final composite (always emitted)
            final_path = f"{out_prefix}_{slug}_final.{ext_final}"
            shot_kwargs = {"path": final_path}
            if ext_final == "jpg":
                shot_kwargs["type"] = "jpeg"
                shot_kwargs["quality"] = quality
            else:
                shot_kwargs["type"] = "png"
            await cover.screenshot(**shot_kwargs)
            if dpi != 96: stamp_dpi(final_path, dpi)
            print(f"   saved {final_path}")

        await browser.close()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Export .cover elements from cover_options.html.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python export_covers.py                            # 4K + layered + JPG\n"
            "  python export_covers.py --no-layered               # final JPG only\n"
            "  python export_covers.py --target-size 1920         # quick preview\n"
            "  python export_covers.py --target-size 5120         # print 5K\n"
            "  python export_covers.py --scale 3                  # force exact 3x\n"
            "  python export_covers.py --text-config text.json    # custom config path\n"
            "  python export_covers.py --no-text-config           # ignore cover_config.json\n"
            "  python export_covers.py --font-dir ./fonts         # use local fonts\n"
            "  python export_covers.py --out-prefix nahida        # custom file prefix\n"
            "\n"
            "Layered mode produces 4 files per .cover:\n"
            "  <prefix>_<id>_background.png  — opaque image + grading + light effects\n"
            "  <prefix>_<id>_effects.png     — transparent: sparkles/decorations\n"
            "  <prefix>_<id>_artwork.png     — transparent: text + barcode\n"
            "  <prefix>_<id>_final.jpg       — flattened composite\n"
            "\n"
            "Default resolution: 4K (3840px on longest side). Override with\n"
            "--target-size N for a different floor, or --scale N to force an exact\n"
            "device scale factor and ignore the target.\n"
            "\n"
            "Text config: if a cover_config.json sits next to cover_options.html,\n"
            "every cover's [data-text-key] elements get patched from it before\n"
            "screenshotting. Generate one with scripts/generate_config.py.\n"
        ),
    )
    ap.add_argument("--html", default="cover_options.html",
                    help="Path to the HTML file (default: cover_options.html)")
    ap.add_argument("--out-prefix", default="cover",
                    help="Filename prefix for exported covers (default: cover)")
    ap.add_argument("--scale", type=float, default=None,
                    help="Force a specific device scale factor. If omitted, the "
                         "scale is auto-computed from --target-size so the longest "
                         "side hits the target.")
    ap.add_argument("--target-size", type=int, default=3840,
                    help="Target px on the longest side of every output (default: 3840 = 4K). "
                         "Ignored if --scale is set.")
    ap.add_argument("--format", default="jpg", choices=["jpg", "jpeg", "png"],
                    help="Final composite format. (default: jpg)")
    ap.add_argument("--quality", type=int, default=92,
                    help="JPG quality 0-100, ignored for PNG. (default: 92)")
    ap.add_argument("--dpi", type=int, default=96,
                    help="DPI metadata stamp. Use 300 or 500 for print. (default: 96)")
    ap.add_argument("--no-layered", dest="layered", action="store_false",
                    help="Skip layer-group export; emit only the final composite.")
    ap.set_defaults(layered=True)
    ap.add_argument("--font-dir", type=Path, default=None,
                    help="Directory of local font files (.ttf/.otf/.woff/.woff2) to load "
                         "alongside Google Fonts.")
    ap.add_argument("--text-config", type=Path, default=None,
                    help="Path to a text-override JSON. If omitted, cover_config.json "
                         "in the cwd is auto-used (if present).")
    ap.add_argument("--no-text-config", dest="use_default_text_config",
                    action="store_false",
                    help="Ignore any auto-detected cover_config.json.")
    ap.set_defaults(use_default_text_config=True)
    args = ap.parse_args()

    asyncio.run(export(
        args.html,
        args.out_prefix,
        args.scale,
        args.target_size,
        args.format,
        args.quality,
        args.dpi,
        args.layered,
        args.font_dir,
        args.text_config,
        args.use_default_text_config,
    ))


if __name__ == "__main__":
    main()
