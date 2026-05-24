import os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=700,1000")
options.add_argument("--hide-scrollbars")
options.add_argument("--force-device-scale-factor=2")  # 2x for crisp output

driver = webdriver.Chrome(options=options)

html_path = os.path.abspath("title_options.html").replace("\\", "/")
driver.get(f"file:///{html_path}")
time.sleep(4)  # let Google Fonts finish loading

cards = driver.find_elements(By.CSS_SELECTOR, ".card")
names = [
    "title_A_bubbly_kawaii",
    "title_B_elegant_serif",
    "title_C_pop_outline",
    "title_D_soft_dreamy",
]

for card, name in zip(cards, names):
    out = f"{name}.png"
    card.screenshot(out)
    print(f"saved {out}")

driver.quit()
print("done")
