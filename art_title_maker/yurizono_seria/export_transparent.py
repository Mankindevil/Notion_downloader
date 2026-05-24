"""
Chroma-key approach:
  1. Render cards on a vivid green background (never appears in the title text)
  2. element.screenshot() works reliably
  3. PIL removes the green pixels → transparent PNG
"""
import os, time
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PIL import Image
import io

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=700,1200")
options.add_argument("--hide-scrollbars")
options.add_argument("--force-device-scale-factor=2")

driver = webdriver.Chrome(options=options)

html_path = os.path.abspath("title_options.html").replace("\\", "/")
driver.get(f"file:///{html_path}")

CHROMA = "#00FF00"  # vivid green — not used in any title colours

driver.execute_script(f"""
    document.body.style.background = '{CHROMA}';
    document.querySelectorAll('.label').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.card').forEach(el => {{
        el.style.background = '{CHROMA}';
        el.style.boxShadow = 'none';
        el.style.borderRadius = '0';
        el.style.marginBottom = '0';
    }});
    // card-b and card-d have inline gradient — override
    document.querySelectorAll('.card-b, .card-d').forEach(el => {{
        el.style.backgroundImage = 'none';
        el.style.background = '{CHROMA}';
    }});
    document.querySelectorAll('.c-badge').forEach(el => {{
        el.style.background = 'transparent';
        el.style.boxShadow = 'none';
        el.style.border = '2.5px solid #d42d78';
        el.style.color = '#d42d78';
    }});
""")

time.sleep(4)  # let Google Fonts render

# Chroma key: remove pixels close to our vivid green
def remove_chroma(png_bytes, chroma_rgb=(0, 255, 0), tolerance=40):
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    data = np.array(img, dtype=np.int16)
    r, g, b, a = data[...,0], data[...,1], data[...,2], data[...,3]
    cr, cg, cb = chroma_rgb
    mask = (
        (np.abs(r - cr) < tolerance) &
        (np.abs(g - cg) < tolerance) &
        (np.abs(b - cb) < tolerance)
    )
    data[mask, 3] = 0          # make chroma pixels fully transparent
    return Image.fromarray(data.astype(np.uint8), "RGBA")

cards = driver.find_elements(By.CSS_SELECTOR, ".card")
names = [
    "transparent_A_bubbly_kawaii",
    "transparent_B_elegant_serif",
    "transparent_C_pop_outline",
    "transparent_D_soft_dreamy",
]

for card, name in zip(cards, names):
    raw = card.screenshot_as_png
    img = remove_chroma(raw)
    out = f"{name}.png"
    img.save(out)
    print(f"saved {out}  {img.size[0]}x{img.size[1]}px")

driver.quit()
print("done")
