"""
Export each .card from title_transparent.html as a transparent PNG
using Playwright's omit_background=True (same approach as generate_4k_png.py).
"""
import asyncio, os
from playwright.async_api import async_playwright

HTML = "title_transparent.html"
SELECTORS_AND_NAMES = [
    ("#card-a", "title_A_bubbly_kawaii.png"),
    ("#card-b", "title_B_elegant_serif.png"),
    ("#card-c", "title_C_pop_outline.png"),
    ("#card-d", "title_D_soft_dreamy.png"),
]

async def main():
    html_path = os.path.abspath(HTML).replace(os.sep, "/")
    file_url = f"file:///{html_path}"

    async with async_playwright() as p:
        # device_scale_factor=2 → crisp 2× output
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 700, "height": 1200},
            device_scale_factor=2,
        )
        page = await context.new_page()
        await page.goto(file_url)
        # Let Google Fonts finish loading
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)

        for selector, out in SELECTORS_AND_NAMES:
            el = await page.query_selector(selector)
            await el.screenshot(path=out, omit_background=True)
            print(f"saved {out}")

        await browser.close()
        print("done")

if __name__ == "__main__":
    asyncio.run(main())
