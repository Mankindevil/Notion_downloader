"""
art-title-maker — export each .card from title_options.html as a transparent PNG.

Contract: every exported PNG has a fully transparent background. The page's
artwork-color body background (used only for the HTML preview) is stripped via
Playwright's `omit_background=True`, and each card's background is explicitly
forced to transparent right before screenshotting so any accidental card-plate
fill in the HTML does not bake into the PNG.

Usage (from the directory containing title_options.html):
    python export_titles.py
    python export_titles.py --html my_titles.html --out-prefix seria
    python export_titles.py --width 3840 --height 2160 --dpi 500   # 4K print
"""
import argparse
import asyncio
import os
import re
import sys

from playwright.async_api import async_playwright


SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def safe(s: str) -> str:
    """File-system-safe slug for an element id."""
    return SAFE_NAME_RE.sub("_", s).strip("_") or "card"


def set_png_dpi(path: str, dpi: int) -> None:
    """Stamp DPI metadata onto the PNG so print software treats it correctly."""
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


async def export(
    html_file: str,
    out_prefix: str,
    scale: int,
    viewport_width: int,
    viewport_height: int,
    dpi: int,
) -> None:
    if not os.path.exists(html_file):
        sys.exit(f"error: {html_file} not found")

    html_path = os.path.abspath(html_file).replace(os.sep, "/")
    file_url = f"file:///{html_path}"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            device_scale_factor=scale,
        )
        page = await context.new_page()
        await page.goto(file_url)

        # Let Google Fonts (and any other network assets) settle.
        try:
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        # Strip the page-level artwork-color background. The HTML uses it for
        # an accurate preview, but the PNG must be transparent — so we wipe it
        # before any screenshot so cards with transparent regions don't pick
        # up the body color when their bounding box is rastered.
        await page.evaluate(
            "() => {"
            " document.documentElement.style.background = 'transparent';"
            " document.body.style.background = 'transparent';"
            "}"
        )

        cards = await page.query_selector_all(".card")
        if not cards:
            sys.exit("error: no .card elements found in HTML")

        for i, card in enumerate(cards):
            # Prefer the element's id (e.g. card-a) for the filename; fall back to index.
            card_id = await card.get_attribute("id") or f"card-{i}"
            out = f"{out_prefix}_{safe(card_id)}.png"
            # Defensive: force the card's own background to transparent so the PNG
            # is guaranteed transparent regardless of what's set in the HTML.
            await card.evaluate(
                "el => { el.style.background = 'transparent';"
                " el.style.backgroundColor = 'transparent';"
                " el.style.backgroundImage = 'none';"
                " el.style.boxShadow = 'none';"
                " el.style.border = 'none'; }"
            )
            await card.screenshot(path=out, omit_background=True)
            if dpi != 96:
                set_png_dpi(out, dpi)
            print(f"saved {out}")

        await browser.close()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Export .card elements from title_options.html as transparent PNGs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python export_titles.py\n"
            "  python export_titles.py --html my_titles.html --out-prefix seria\n"
            "  python export_titles.py --width 3840 --height 2160 --dpi 500\n"
        ),
    )
    ap.add_argument("--html", default="title_options.html",
                    help="Path to the HTML file (default: title_options.html)")
    ap.add_argument("--out-prefix", default="title",
                    help="Filename prefix for the exported PNGs (default: title)")
    ap.add_argument("--scale", type=int, default=2,
                    help="Device scale factor for crisp output (default: 2)")
    ap.add_argument("--width", type=int, default=800,
                    help="Viewport width in CSS px (default: 800; use 3840 for 4K)")
    ap.add_argument("--height", type=int, default=1200,
                    help="Viewport height in CSS px (default: 1200; use 2160 for 4K)")
    ap.add_argument("--dpi", type=int, default=96,
                    help="Stamp this DPI into the PNG metadata (default: 96; use 500 for print)")
    args = ap.parse_args()

    asyncio.run(export(
        args.html,
        args.out_prefix,
        args.scale,
        args.width,
        args.height,
        args.dpi,
    ))


if __name__ == "__main__":
    main()
