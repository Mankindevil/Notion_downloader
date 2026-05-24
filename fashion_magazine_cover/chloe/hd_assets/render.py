"""Render poster_overlay.html to poster_overlay_4k.png using Playwright."""
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
ROOT = Path(__file__).parent.parent.parent.parent  # O:\Coding\Claude

SCALE = 3.75
BASE_W, BASE_H = 1024, 761


def render():
    html_file = HERE / "poster_overlay.html"
    out_file = HERE / "poster_overlay_4k.png"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": BASE_W, "height": BASE_H},
            device_scale_factor=SCALE,
        )
        page = ctx.new_page()
        page.goto(f"file:///{html_file.as_posix()}", wait_until="networkidle")
        # Extra wait for Google Fonts to load
        page.wait_for_timeout(3000)
        page.screenshot(path=str(out_file), full_page=False, type="png", omit_background=True)
        browser.close()
        print(f"Rendered: {out_file}  ({BASE_W * SCALE:.0f}x{BASE_H * SCALE:.0f})")


if __name__ == "__main__":
    render()
