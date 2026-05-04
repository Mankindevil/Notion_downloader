#!/usr/bin/env python3
"""
Notion Gallery Downloader
- Clicks 中文畫廊 tab
- Detects year groups (2026 / 2025 / ...) and mirrors that structure
- Uses sub-page 投稿日 date as folder/file prefix (e.g. 2026-02-28_理解・美/)
- Saves README.md per entry (not JSON)
- Downloads cover thumbnails + all sub-page images

Usage:
    pip install selenium
    python notion_downloader.py
    python notion_downloader.py --no-headless     # watch the browser
    python notion_downloader.py --url "..." --out my_folder
"""

import argparse
import logging
import re
import sys
import time
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import date, timedelta


# ──────────────────────────────────────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────────────────────────────────────

def setup_logging(log_file: str = "notion_downloader.log") -> logging.Logger:
    logger = logging.getLogger("notion")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)-8s] %(message)s", datefmt="%H:%M:%S")

    fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = logging.getLogger("notion")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_COPY_NOISE_RE = re.compile(
    r'\s*(?:拷貝到剪貼板|拷贝到剪切板|コピー|복사|Copy to clipboard|Copied).*$', re.I
)


def slugify(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'[\\/*?:"<>|]', "_", text)
    text = re.sub(r'\s+', "_", text)
    text = text.strip("._")
    return text[:60] or "untitled"


def url_ext(url: str) -> str:
    base = url.split("?")[0].rsplit(".", 1)
    ext = base[-1].lower() if len(base) > 1 else ""
    return ext if ext in ("jpg", "jpeg", "png", "gif", "webp") else "jpg"


def download(url: str, dest: Path, retries: int = 3) -> bool:
    if dest.exists():
        log.debug(f"  already exists: {dest.name}")
        return True
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://notion.so/",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=40) as r:
                dest.write_bytes(r.read())
            log.info(f"  ✓ downloaded: {dest.name}")
            return True
        except Exception as e:
            log.warning(f"  ✗ attempt {attempt + 1}/{retries} failed: {e}")
            time.sleep(2 ** attempt)
    log.error(f"  ✗ FAILED after {retries} attempts: {dest.name}")
    return False


def parse_notion_date(raw: str, fallback_year: str = "") -> str:
    """
    Convert any Notion date string to YYYY-MM-DD.

    Handles:
      ISO:            2026-02-28  /  2026-02-28T12:34:56.000Z
      Slash:          2026/02/28
      Chinese abs:    2026年2月28日
      Chinese m/d:    2月28日  (uses fallback_year or current year)
      Japanese rel:   今日/昨日/一昨日/X日前/X週間前/Xヶ月前
      Chinese rel:    今天/昨天/前天/X天前/X周前/X个月前/X個月前
      Korean rel:     오늘/어제/그제
      English rel:    today/yesterday/X days ago/X weeks ago/X months ago
                      just now / a moment ago / an hour ago (→ today)
      Notion tooltip: "February 28, 2026"  /  "2026年2月28日"
    Returns '' if unparseable.
    """
    if not raw:
        return ""
    raw = raw.strip()
    today = date.today()

    log.debug(f"    parse_notion_date({raw!r}, fallback_year={fallback_year!r})")

    # ── Absolute formats ─────────────────────────────────────────────────
    # ISO / datetime attr: 2026-02-28 or 2026-02-28T...
    m = re.match(r'^(\d{4}-\d{2}-\d{2})', raw)
    if m:
        result = m.group(1)
        log.debug(f"    → ISO match: {result}")
        return result

    # Slash: 2026/02/28
    m = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})', raw)
    if m:
        result = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        log.debug(f"    → slash match: {result}")
        return result

    # Chinese/Japanese full: 2026年2月28日
    m = re.search(r'(\d{4})[年/](\d{1,2})[月/](\d{1,2})日?', raw)
    if m:
        result = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        log.debug(f"    → Chinese/JP full match: {result}")
        return result

    # English full: "February 28, 2026" or "Feb 28, 2026" or "28 February 2026"
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8,
        'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }
    m = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', raw)
    if m and m.group(1).lower() in months:
        result = f"{int(m.group(3)):04d}-{months[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
        log.debug(f"    → English full match: {result}")
        return result
    m = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', raw)
    if m and m.group(2).lower() in months:
        result = f"{int(m.group(3)):04d}-{months[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
        log.debug(f"    → English DMY match: {result}")
        return result

    # Month+day only: "2月28日" — use fallback_year or current year
    m = re.search(r'(\d{1,2})月(\d{1,2})日', raw)
    if m:
        yr = int(fallback_year) if fallback_year and fallback_year.isdigit() else today.year
        result = f"{yr:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
        log.debug(f"    → M月D日 match: {result}")
        return result

    # ── Relative: exact words ─────────────────────────────────────────────
    r = raw.lower()
    if any(w in raw for w in ["今天", "今日", "오늘"]) or "today" in r or "just now" in r or "a moment" in r:
        log.debug(f"    → relative 'today': {today.isoformat()}")
        return today.isoformat()
    if any(w in raw for w in ["昨天", "昨日", "어제"]) or "yesterday" in r:
        result = (today - timedelta(days=1)).isoformat()
        log.debug(f"    → relative 'yesterday': {result}")
        return result
    if any(w in raw for w in ["前天", "一昨日", "그제", "그저께"]):
        result = (today - timedelta(days=2)).isoformat()
        log.debug(f"    → relative '2 days ago': {result}")
        return result

    # Chinese/Traditional relative weekday: 上星期X / 上週X / 先週X (last week's X-day)
    _wd_map = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}
    m = re.search(r'(?:上星期|上週|先週)([一二三四五六日天])', raw)
    if m:
        target_wd = _wd_map[m.group(1)]
        last_week_monday = today - timedelta(days=today.weekday() + 7)
        result = (last_week_monday + timedelta(days=target_wd)).isoformat()
        log.debug(f"    → 上星期X match: {result}")
        return result

    # ── Relative: N units ago ─────────────────────────────────────────────
    # N days/天/日
    m = re.search(r'(\d+)\s*(?:天前|日前|days?\s*ago)', raw, re.I)
    if m:
        result = (today - timedelta(days=int(m.group(1)))).isoformat()
        log.debug(f"    → relative N days ago: {result}")
        return result

    # N weeks/周/週
    m = re.search(r'(\d+)\s*(?:周前|週前|weeks?\s*ago)', raw, re.I)
    if m:
        result = (today - timedelta(weeks=int(m.group(1)))).isoformat()
        log.debug(f"    → relative N weeks ago: {result}")
        return result
    if "a week ago" in r or "1 week ago" in r:
        result = (today - timedelta(weeks=1)).isoformat()
        log.debug(f"    → relative 1 week ago: {result}")
        return result

    # N months/个月/個月/ヶ月
    m = re.search(r'(\d+)\s*(?:个月前|個月前|ヶ月前|months?\s*ago)', raw, re.I)
    if m:
        n = int(m.group(1))
        mo = today.month - n
        yr = today.year + mo // 12
        mo = mo % 12 or 12
        try:
            result = date(yr, mo, today.day).isoformat()
        except ValueError:
            result = date(yr, mo, 1).isoformat()
        log.debug(f"    → relative N months ago: {result}")
        return result
    if "a month ago" in r:
        mo = today.month - 1 or 12
        yr = today.year if today.month > 1 else today.year - 1
        result = date(yr, mo, today.day).isoformat()
        log.debug(f"    → relative 1 month ago: {result}")
        return result

    log.debug(f"    → unparseable date: {raw!r}")
    return ""


def extract_date_from_page_source(html: str, fallback_year: str = "") -> str:
    """
    Last-resort: scan embedded JSON / meta tags in the raw page source for an ISO date.
    Notion stores block data as JSON in <script> tags; we look for date-property values.
    """
    # ISO dates near date-field keywords
    patterns = [
        # Notion date property JSON: "start":"YYYY-MM-DD" (most reliable structure)
        r'"start"\s*:\s*"(20\d\d-\d{2}-\d{2})',
        # Keyword-anchored with strict post-date keys only (no generic "date" which matches last_edited_time etc.)
        r'(?:投稿日|post_date|created_time)"[^"]{0,60}"(20\d\d-\d{2}-\d{2})',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            candidate = m.group(1)
            log.debug(f"    page-source date candidate: {candidate!r}")
            result = parse_notion_date(candidate, fallback_year)
            if result and not result.endswith("-00-00"):
                return result
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# Selenium helpers
# ──────────────────────────────────────────────────────────────────────────────

def _chrome_major_version() -> int | None:
    """Return the installed Chrome major version, or None if undetectable."""
    import subprocess
    try:
        import winreg
        for hive, path in [
            (winreg.HKEY_CURRENT_USER,  r"Software\Google\Chrome\BLBeacon"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon"),
        ]:
            try:
                key = winreg.OpenKey(hive, path)
                ver, _ = winreg.QueryValueEx(key, "version")
                m = re.match(r"(\d+)", ver)
                if m:
                    return int(m.group(1))
            except OSError:
                continue
    except ImportError:
        pass
    for exe in ("google-chrome", "google-chrome-stable", "chromium-browser", "chrome"):
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)
            m = re.search(r"(\d+)\.\d+\.\d+", r.stdout)
            if m:
                return int(m.group(1))
        except Exception:
            continue
    return None


def make_driver(headless: bool, bypass_cloudflare: bool = False):
    if bypass_cloudflare:
        try:
            import undetected_chromedriver as uc
            opts = uc.ChromeOptions()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--lang=zh-TW")
            version = _chrome_major_version()
            log.info(f"Using undetected-chromedriver (Cloudflare bypass), Chrome major={version}")
            return uc.Chrome(options=opts, headless=headless, use_subprocess=True,
                             version_main=version)
        except ImportError:
            log.warning("undetected-chromedriver not found — run: pip install undetected-chromedriver")
            log.warning("Falling back to plain selenium (may be blocked by Cloudflare)")

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=zh-TW")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    return webdriver.Chrome(options=opts)


def wait_for_page(driver, timeout=30):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    for sel in ["[data-block-id]", ".notion-page-content", ".notion-scroller", ".notion-collection", "main"]:
        try:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            return sel
        except Exception:
            continue
    return None


def slow_scroll(driver, step_px=400, delay=0.35):
    driver.execute_script("window.scrollTo(0,0);")
    time.sleep(0.5)
    total = driver.execute_script("return document.body.scrollHeight")
    pos = 0
    while pos < total:
        pos += step_px
        driver.execute_script(f"window.scrollTo(0,{pos});")
        time.sleep(delay)
        total = driver.execute_script("return document.body.scrollHeight")
    time.sleep(1)


def open_all_toggles(driver):
    """Click all closed toggle blocks to expose hidden content."""
    from selenium.webdriver.common.by import By
    toggle_selectors = [
        ".notion-toggle-block [role='button']",
        "[class*='toggle'][aria-expanded='false']",
        "summary",
    ]
    opened = 0
    for sel in toggle_selectors:
        try:
            toggles = driver.find_elements(By.CSS_SELECTOR, sel)
            for t in toggles:
                try:
                    expanded = t.get_attribute("aria-expanded")
                    if expanded == "false" or expanded is None:
                        driver.execute_script("arguments[0].click();", t)
                        opened += 1
                        time.sleep(0.15)
                except Exception:
                    pass
        except Exception:
            pass
    if opened:
        log.debug(f"    opened {opened} toggle block(s)")
        time.sleep(0.5)


def get_bg_image_urls(driver):
    from selenium.webdriver.common.by import By
    urls = []
    for el in driver.find_elements(By.CSS_SELECTOR, "[style*='background-image']"):
        style = el.get_attribute("style") or ""
        for m in re.finditer(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', style):
            u = m.group(1)
            if ".svg" not in u:
                urls.append(u)
    return urls


def get_all_img_urls(driver):
    from selenium.webdriver.common.by import By
    urls = []
    for img in driver.find_elements(By.TAG_NAME, "img"):
        src = img.get_attribute("src") or ""
        if src.startswith("http") and ".svg" not in src and not src.startswith("data:"):
            try:
                w = driver.execute_script("return arguments[0].naturalWidth;", img)
                if w and w < 30:
                    continue
            except Exception:
                pass
            urls.append(src)
    return urls


def extract_images_from_source(html: str) -> list:
    patterns = [
        r'(https://prod-files-secure[^"\')\s<>]+)',
        r'(https://[^"\')\s<>]*notion-static[^"\')\s<>]+)',
        r'(https://[^"\')\s<>]*amazonaws\.com/[^"\')\s<>]+)',
    ]
    seen, result = set(), []
    for p in patterns:
        for u in re.findall(p, html):
            u = re.split(r'["\'\s<>]', u)[0]
            if u not in seen:
                seen.add(u)
                result.append(u)
    return result


def click_tab(driver, label: str) -> bool:
    from selenium.webdriver.common.by import By
    try:
        els = driver.find_elements(By.XPATH, f"//*[contains(text(), '{label}')]")
        for el in els:
            target = el
            for _ in range(5):
                try:
                    driver.execute_script("arguments[0].click();", target)
                    time.sleep(0.3)
                    return True
                except Exception:
                    pass
                try:
                    target = target.find_element(By.XPATH, "..")
                except Exception:
                    break
    except Exception:
        pass
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Sub-page scraper
# ──────────────────────────────────────────────────────────────────────────────

def scrape_subpage(driver, page_url: str, fallback_year: str = "") -> dict:
    """Visit a card sub-page, extract title, properties (incl. date), images, text."""
    result = {"url": page_url, "title": "", "date": "", "properties": {}, "images": [], "text": [],
              "is_collection": False}
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.action_chains import ActionChains

    try:
        log.info(f"  Loading sub-page: {page_url}")
        driver.get(page_url)
        sel = wait_for_page(driver, timeout=30)
        if not sel:
            log.warning(f"  ⚠ Page load timeout: {page_url}")
            return result
        time.sleep(2.5)

        if driver.find_elements(By.CSS_SELECTOR, ".notion-collection_view_page-block"):
            result["is_collection"] = True
            log.debug("  (page contains a collection-view block)")

        open_all_toggles(driver)
        slow_scroll(driver)
        open_all_toggles(driver)  # open any toggles revealed after scroll

        # ── Title ────────────────────────────────────────────────────────────
        title_selectors = [
            ".notion-page-block .notranslate",
            "h1.notion-title",
            "[class*='notion-page-block'] [data-content-editable-leaf]",
            "[placeholder='Untitled']",
            "h1",
        ]
        for ts in title_selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, ts)
                t = el.text.strip()
                if t:
                    result["title"] = t
                    log.debug(f"  title found via {ts!r}: {t!r}")
                    break
            except Exception:
                continue
        if not result["title"]:
            result["title"] = driver.title.replace("| Notion", "").replace("– Notion", "").strip()
            log.debug(f"  title from document.title: {result['title']!r}")

        # ── Date/property extraction helper ───────────────────────────────────
        date_prop_keys = {"投稿日", "Posted", "Date", "日付", "투고일", "投稿日付", "創建時間", "創建日期"}

        def extract_date_from_time_el(time_el) -> str:
            # 1. datetime attribute (most reliable; Notion always sets this to ISO even for relative display)
            dt_attr = (time_el.get_attribute("datetime") or "").strip()
            log.debug(f"    <time datetime={dt_attr!r}>")
            if dt_attr:
                d = parse_notion_date(dt_attr, fallback_year)
                if d:
                    log.debug(f"    → date from datetime attr: {d}")
                    return d

            # 2. title attribute
            title_attr = (time_el.get_attribute("title") or "").strip()
            if title_attr:
                d = parse_notion_date(title_attr, fallback_year)
                if d:
                    log.debug(f"    → date from title attr: {d}")
                    return d

            # 3. aria-label attribute
            aria = (time_el.get_attribute("aria-label") or "").strip()
            if aria:
                d = parse_notion_date(aria, fallback_year)
                if d:
                    log.debug(f"    → date from aria-label: {d}")
                    return d

            # 4. Hover for tooltip
            try:
                ActionChains(driver).move_to_element(time_el).perform()
                time.sleep(0.6)
                for tip in driver.find_elements(By.CSS_SELECTOR,
                        "[class*='tooltip'], [role='tooltip'], [data-radix-popper-content-wrapper] *"):
                    tip_text = tip.text.strip()
                    if tip_text and re.search(r'\d{4}|\d{1,2}[月/]\d{1,2}', tip_text):
                        d = parse_notion_date(tip_text, fallback_year)
                        if d:
                            log.debug(f"    → date from tooltip: {d}")
                            return d
            except Exception as e:
                log.debug(f"    hover failed: {e}")

            # 5. Visible text of the element
            visible_text = (time_el.text or "").strip()
            log.debug(f"    <time> visible text: {visible_text!r}")
            if visible_text:
                d = parse_notion_date(visible_text, fallback_year)
                if d:
                    log.debug(f"    → date from visible text: {d}")
                    return d

            return ""

        # ── Strategy A: scan ALL <time> elements ──────────────────────────────
        time_els = driver.find_elements(By.TAG_NAME, "time")
        log.debug(f"  Found {len(time_els)} <time> element(s)")
        # We want 投稿日 specifically; collect all and pick the earliest relevant one
        candidate_dates = []
        for time_el in time_els:
            d = extract_date_from_time_el(time_el)
            if d:
                candidate_dates.append(d)
                log.debug(f"  <time> candidate date: {d}")
        if candidate_dates:
            # Prefer the earliest date (投稿日 < 更新日)
            result["date"] = sorted(candidate_dates)[0]
            log.info(f"  date from <time> elements: {result['date']}")

        # ── Strategy A2: JS DOM walk for property key→value ───────────────────
        # Notion's current rendering uses obfuscated CSS classes and no <time> elements.
        # We find leaf nodes matching known property keys and walk up to the container
        # that holds both the key text and the value text (typically ~6–8 levels up).
        if not result["date"]:
            try:
                js_prop_result = driver.execute_script("""
                    var dateKeys = ['投稿日','Posted','Date','日付','투고일','投稿日付','創建時間','創建日期'];
                    var all = document.querySelectorAll('*');
                    for (var i = 0; i < all.length; i++) {
                        var el = all[i];
                        if (el.children.length > 0) continue;
                        var text = (el.innerText || el.textContent || '').trim();
                        if (dateKeys.indexOf(text) < 0) continue;
                        var node = el;
                        for (var d = 0; d < 10; d++) {
                            node = node.parentElement;
                            if (!node) break;
                            var full = (node.innerText || '').trim();
                            if (full.length > text.length + 2 && full.indexOf(text) >= 0) {
                                var lines = full.split(/\\n/).map(function(s){return s.trim();}).filter(Boolean);
                                var ki = lines.indexOf(text);
                                if (ki >= 0 && ki + 1 < lines.length) {
                                    return {key: text, value: lines[ki + 1]};
                                }
                            }
                        }
                    }
                    return null;
                """)
                if js_prop_result:
                    k, v = js_prop_result["key"], js_prop_result["value"]
                    log.debug(f"  JS DOM walk property: {k!r} = {v!r}")
                    d = parse_notion_date(v, fallback_year)
                    if d:
                        result["date"] = d
                        log.info(f"  date from JS DOM walk: {d}")
            except Exception as e:
                log.debug(f"  JS DOM walk failed: {e}")

        # ── Strategy B: Property rows via CSS ────────────────────────────────
        # Notion uses various class names depending on version; try all known patterns.
        prop_selectors = [
            ".notion-page-property",
            "[class*='property-row']",
            "[class*='property'][data-property-id]",
            "[class*='propertyRow']",
            "[class*='notion-property']",
        ]
        for ps in prop_selectors:
            rows = driver.find_elements(By.CSS_SELECTOR, ps)
            if not rows:
                continue
            log.debug(f"  property selector {ps!r} → {len(rows)} rows")
            for row in rows:
                try:
                    txt = row.text.strip()
                    if not txt:
                        continue
                    lines = [l.strip() for l in txt.splitlines() if l.strip()]
                    if len(lines) < 2:
                        # Single-line row: key and value may be separated by whitespace only.
                        # Try splitting by multiple spaces or tabs.
                        parts = re.split(r'\s{2,}|\t', txt, maxsplit=1)
                        if len(parts) < 2:
                            log.debug(f"  skip single-line row: {txt!r}")
                            continue
                        lines = parts
                    k, v = lines[0].strip(), " ".join(lines[1:]).strip()
                    if not k or not v:
                        continue
                    v = _COPY_NOISE_RE.sub('', v).strip()
                    result["properties"][k] = v
                    log.debug(f"  property: {k!r} = {v!r}")

                    if k in date_prop_keys and not result["date"]:
                        try:
                            te = row.find_element(By.TAG_NAME, "time")
                            d = extract_date_from_time_el(te)
                            if d:
                                result["date"] = d
                                log.info(f"  date from property <time>: {d}")
                        except Exception:
                            pass
                        if not result["date"]:
                            d = parse_notion_date(v, fallback_year)
                            if d:
                                result["date"] = d
                                log.info(f"  date from property text: {d}")
                except Exception as ex:
                    log.debug(f"  row parse error: {ex}")
                    continue
            if result["properties"]:
                break

        # ── Strategy C: XPath property rows (fallback if CSS missed) ─────────
        if not result["date"]:
            log.debug("  Trying XPath property extraction...")
            known_props = ["投稿日", "語言", "分類", "更新日", "別語言版", "Posted", "Date", "Language", "Category"]
            for prop_name in known_props:
                try:
                    label_els = driver.find_elements(
                        By.XPATH, f"//*[normalize-space(text())='{prop_name}']"
                    )
                    for label_el in label_els:
                        try:
                            # Walk up to find the row container (needs up to 6-8 levels in current Notion DOM)
                            container = label_el
                            for _ in range(8):
                                parent = container.find_element(By.XPATH, "..")
                                parent_text = parent.text.strip()
                                if prop_name in parent_text and len(parent_text) > len(prop_name):
                                    container = parent
                                    break
                                container = parent
                            row_text = container.text.strip()
                            v = row_text.replace(prop_name, "").strip()
                            v = _COPY_NOISE_RE.sub('', v).strip()
                            if v and prop_name not in result["properties"]:
                                result["properties"][prop_name] = v
                                log.debug(f"  XPath property: {prop_name!r} = {v!r}")

                            if prop_name in date_prop_keys and not result["date"]:
                                try:
                                    te = container.find_element(By.TAG_NAME, "time")
                                    d = extract_date_from_time_el(te)
                                    if d:
                                        result["date"] = d
                                        log.info(f"  date from XPath <time>: {d}")
                                except Exception:
                                    pass
                                if not result["date"] and v:
                                    d = parse_notion_date(v, fallback_year)
                                    if d:
                                        result["date"] = d
                                        log.info(f"  date from XPath text: {d}")
                        except Exception:
                            continue
                except Exception:
                    continue

        # ── Strategy D: JavaScript execution to get all property data ─────────
        if not result["date"]:
            log.debug("  Trying JS property extraction...")
            try:
                js_props = driver.execute_script("""
                    var results = {};
                    var timeEls = document.querySelectorAll('time');
                    var times = [];
                    timeEls.forEach(function(el) {
                        times.push({
                            datetime: el.getAttribute('datetime') || '',
                            text: el.innerText || el.textContent || '',
                            title: el.getAttribute('title') || '',
                            aria: el.getAttribute('aria-label') || ''
                        });
                    });
                    results.times = times;
                    // Try to get page-level property containers
                    var propEls = document.querySelectorAll(
                        '[class*="property"], [class*="Property"]'
                    );
                    var props = [];
                    propEls.forEach(function(el) {
                        var t = (el.innerText || '').trim();
                        if (t && t.length < 200) props.push(t);
                    });
                    results.props = props;
                    return results;
                """)
                log.debug(f"  JS extraction: {len(js_props.get('times', []))} time(s), "
                          f"{len(js_props.get('props', []))} prop(s)")
                for t in js_props.get("times", []):
                    for val in [t.get("datetime"), t.get("title"), t.get("aria"), t.get("text")]:
                        if val:
                            d = parse_notion_date(val.strip(), fallback_year)
                            if d:
                                result["date"] = d
                                log.info(f"  date from JS time extraction: {d}")
                                break
                    if result["date"]:
                        break
                # Try raw property text
                if not result["date"]:
                    for p in js_props.get("props", []):
                        if any(k in p for k in date_prop_keys):
                            d = parse_notion_date(p, fallback_year)
                            if d:
                                result["date"] = d
                                log.info(f"  date from JS prop text: {d}")
                                break
            except Exception as e:
                log.debug(f"  JS extraction failed: {e}")

        # ── Strategy E: Page source scan ──────────────────────────────────────
        page_source = driver.page_source
        if not result["date"]:
            log.debug("  Trying page-source date extraction...")
            d = extract_date_from_page_source(page_source, fallback_year)
            if d:
                result["date"] = d
                log.info(f"  date from page source: {d}")

        # ── Text blocks ───────────────────────────────────────────────────────
        text_selectors = [
            ".notion-text-block",
            ".notion-bulleted_list-block",
            ".notion-numbered_list-block",
            ".notion-quote-block",
            ".notion-callout-block",
            ".notion-header-block",
            ".notion-sub_header-block",
            ".notion-sub_sub_header-block",
            "[class*='notion-text']",
            "[class*='notion-paragraph']",
        ]
        seen_texts: set = set()
        for sel in text_selectors:
            for b in driver.find_elements(By.CSS_SELECTOR, sel):
                t = b.text.strip()
                if t and t not in seen_texts:
                    seen_texts.add(t)
                    result["text"].append(t)

        # Fallback: grab all paragraph-like elements if nothing found
        if not result["text"]:
            log.debug("  No text blocks via specific selectors, trying broad fallback...")
            for tag in ["p", "h1", "h2", "h3"]:
                for el in driver.find_elements(By.TAG_NAME, tag):
                    t = el.text.strip()
                    if t and len(t) > 10 and t not in seen_texts:
                        seen_texts.add(t)
                        result["text"].append(t)

        log.debug(f"  extracted {len(result['text'])} text block(s)")

        # ── Images ────────────────────────────────────────────────────────────
        img_urls = []
        img_urls.extend(get_all_img_urls(driver))
        img_urls.extend(get_bg_image_urls(driver))
        img_urls.extend(extract_images_from_source(page_source))
        seen: set = set()
        result["images"] = [u for u in img_urls if not (u in seen or seen.add(u))]

        log.info(f"  → title={result['title']!r}  date={result['date']!r}  "
                 f"images={len(result['images'])}  text_blocks={len(result['text'])}")

    except Exception as e:
        log.error(f"  ✗ scrape_subpage error: {e}", exc_info=True)

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Markdown writer
# ──────────────────────────────────────────────────────────────────────────────

def write_markdown(page_dir: Path, record: dict):
    """Write README.md for one entry."""
    lines = []
    title = record.get("title") or record.get("gallery_title") or "Untitled"
    lines.append(f"# {title}\n")

    # Metadata table
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    if record.get("date"):
        lines.append(f"| 投稿日 | {record['date']} |")
    if record.get("year"):
        lines.append(f"| Year | {record['year']} |")
    if record.get("tags"):
        lines.append(f"| Tags | {', '.join(record['tags'])} |")
    for k, v in (record.get("properties") or {}).items():
        lines.append(f"| {k} | {v} |")
    if record.get("href"):
        lines.append(f"| Source | [{record['href']}]({record['href']}) |")
    lines.append("")

    # Cover image
    if record.get("cover_file"):
        rel = f"../../covers/{record['cover_file']}"
        lines.append(f"## Cover\n\n![cover]({rel})\n")

    # Text content
    if record.get("text"):
        lines.append("## Content\n")
        for t in record["text"]:
            lines.append(t + "\n")
        lines.append("")

    # Image gallery
    images = record.get("images") or []
    if images:
        lines.append(f"## Images ({len(images)})\n")
        for img in images:
            f = img.get("file")
            if f:
                lines.append(f"![{f}]({f})\n")
        lines.append("")

    md_path = page_dir / "README.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    log.debug(f"  wrote {md_path}")


# ──────────────────────────────────────────────────────────────────────────────
# Gallery year-group detection
# ──────────────────────────────────────────────────────────────────────────────

def get_cards_with_years(driver) -> list:
    """
    Use JavaScript to walk the full DOM in order, finding:
    - Year group headers (elements whose trimmed text matches 20XX)
    - Card <a> elements (any internal Notion link with text)
    Returns list of {year, href, title, tags, cover_url}
    """
    from selenium.webdriver.common.by import By

    # ── Step 1: Use JS to extract all <a> hrefs + text + y-position ──────
    js_cards = driver.execute_script("""
        var results = [];
        var anchors = document.querySelectorAll('a[href]');
        anchors.forEach(function(a) {
            var href = a.href || '';
            var text = (a.innerText || a.textContent || '').trim();
            if (!href || !text) return;
            if (href.indexOf('notion.') === -1 && href.indexOf('/') !== 0) return;
            var rect = a.getBoundingClientRect();
            var y = rect.top + window.scrollY;
            results.push({href: href, text: text, y: y});
        });
        return results;
    """)

    # ── Step 2: Find year headers via JS ─────────────────────────────────
    js_years = driver.execute_script("""
        var results = [];
        var all = document.querySelectorAll('*');
        for (var i = 0; i < all.length; i++) {
            var el = all[i];
            if (el.children.length > 3) continue;
            var text = (el.innerText || '').trim();
            if (/^20[0-9]{2}$/.test(text)) {
                var rect = el.getBoundingClientRect();
                results.push({year: text, y: rect.top + window.scrollY});
            }
        }
        return results;
    """)

    # Deduplicate year headers: same year elements rendered as nested spans give many duplicates.
    # Keep at most one entry per (year, 100px y-bucket).
    seen_buckets: set = set()
    deduped_years = []
    for yh in js_years:
        bucket = (yh['year'], round(yh['y'] / 100))
        if bucket not in seen_buckets:
            seen_buckets.add(bucket)
            deduped_years.append(yh)
    js_years = deduped_years

    log.info(f"  JS found {len(js_cards)} anchor elements, {len(js_years)} year headers")
    for yh in js_years:
        log.info(f"    Year header: {yh['year']} @ y={yh['y']:.0f}")

    # ── Step 3: Filter to actual gallery cards ───────────────────────────
    card_items = [c for c in js_cards if c['text'] and re.search(r'[0-9a-f]{20,}', c['href'])]
    log.info(f"  Filtered to {len(card_items)} gallery card links")

    if not card_items:
        card_items = [c for c in js_cards if '\n' in c['text'] and re.search(r'[0-9a-f]{10,}', c['href'])]
        log.info(f"  Fallback: {len(card_items)} candidates")

    # ── Step 4: Sort by y-position, assign years ──────────────────────────
    card_items.sort(key=lambda x: x['y'])
    year_headers = sorted(js_years, key=lambda x: x['y'])

    def assign_year(card_y):
        assigned = str(date.today().year)
        for yh in year_headers:
            if yh['y'] <= card_y + 50:
                assigned = yh['year']
        return assigned

    # ── Step 5: Dedupe and build result ──────────────────────────────────
    seen_hrefs = set()
    cards = []
    for item in card_items:
        href = item['href']
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        lines = [l.strip() for l in item['text'].splitlines() if l.strip()]
        title = lines[0] if lines else ""
        tags = [l for l in lines[1:] if l and len(l) <= 30]
        year = assign_year(item['y'])

        log.debug(f"  card: {title!r} year={year} href={href[:60]}...")

        info = {
            "year": year,
            "href": href,
            "title": title,
            "tags": tags,
            "cover_url": None,
        }

        # Get cover
        try:
            card_el = driver.find_element(By.CSS_SELECTOR, 'a[href="%s"]' % href.replace('"', '\\"'))
            for div in card_el.find_elements(By.CSS_SELECTOR, "[style*='background-image']"):
                style = div.get_attribute("style") or ""
                m = re.search(r'url\(["\']?(https?://[^"\')\ \s]+)["\']?\)', style)
                if m and ".svg" not in m.group(1):
                    info["cover_url"] = m.group(1)
                    break
            if not info["cover_url"]:
                for img in card_el.find_elements(By.TAG_NAME, "img"):
                    src = img.get_attribute("src") or ""
                    if src.startswith("http") and ".svg" not in src:
                        try:
                            w = driver.execute_script("return arguments[0].naturalWidth;", img)
                            if not w or w > 30:
                                info["cover_url"] = src
                                break
                        except Exception:
                            info["cover_url"] = src
                            break
        except Exception:
            pass

        cards.append(info)

    return cards


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def scrape_gallery(url: str, out_dir: Path, headless: bool = True, skip_downloaded: bool = False,
                   bypass_cloudflare: bool = False, skip_collections: bool = False):
    from selenium.webdriver.common.by import By

    driver = make_driver(headless, bypass_cloudflare=bypass_cloudflare)
    try:
        log.info(f"\n{'='*60}")
        log.info(f"Loading: {url}")
        log.info(f"{'='*60}")
        driver.get(url)
        wait_for_page(driver, timeout=30)
        time.sleep(3)

        # ── Click 中文畫廊 tab ─────────────────────────────────────────────
        for label in ["中文畫廊", "中文画廊"]:
            if click_tab(driver, label):
                log.info(f"✓ Clicked '{label}' tab")
                break
        else:
            log.warning("⚠ Tab not found, using current view")
        time.sleep(3)

        # ── Scroll + click ALL "加载更多" interleaved ─────────────────────
        log.info("Scrolling and clicking 'Load More' buttons...")
        load_more_labels = ["加载更多", "Load more", "さらに読み込む", "더 보기", "加載更多", "載入更多"]

        def click_all_load_more_visible():
            clicked = 0
            for label in load_more_labels:
                try:
                    btns = driver.find_elements(
                        By.XPATH,
                        f"//*[normalize-space(text())='{label}' or contains(text(),'{label}')]"
                    )
                    for btn in btns:
                        try:
                            driver.execute_script(
                                "arguments[0].scrollIntoView({block:'center'});", btn)
                            time.sleep(0.3)
                            driver.execute_script("arguments[0].click();", btn)
                            log.info(f"  ↓ Clicked '{label}'")
                            clicked += 1
                            time.sleep(2)
                        except Exception:
                            pass
                except Exception:
                    pass
            return clicked

        prev_height = 0
        for _pass in range(20):  # more passes to ensure all content is loaded
            driver.execute_script("window.scrollTo(0,0);")
            time.sleep(0.5)
            total = driver.execute_script("return document.body.scrollHeight")
            pos = 0
            while pos < total:
                pos += 500
                driver.execute_script(f"window.scrollTo(0,{pos});")
                time.sleep(0.3)
                total = driver.execute_script("return document.body.scrollHeight")
            click_all_load_more_visible()
            new_height = driver.execute_script("return document.body.scrollHeight")
            log.debug(f"  Pass {_pass + 1}: height={new_height} (prev={prev_height})")
            if new_height == prev_height:
                break
            prev_height = new_height
        log.info("  ✓ All content loaded")

        slow_scroll(driver)
        time.sleep(3)  # allow any lazily-rendered cards to finish appearing

        # ── Collect all cards with year info ──────────────────────────────
        log.info("Collecting cards...")
        cards = get_cards_with_years(driver)

        if not cards:
            log.warning("⚠ No cards found — saving debug_source.html")
            (out_dir / "debug_source.html").write_text(driver.page_source, encoding="utf-8")
            return

        # Show year distribution
        from collections import Counter
        year_counts = Counter(c["year"] for c in cards)
        log.info(f"✓ {len(cards)} cards: {dict(sorted(year_counts.items(), reverse=True))}\n")

        covers_dir = out_dir / "covers"
        covers_dir.mkdir(parents=True, exist_ok=True)

        # ── Download cache for --skip-downloaded ──────────────────────────────
        cache_file = out_dir / ".downloaded_hrefs.txt"
        downloaded_hrefs: set = set()
        if skip_downloaded and cache_file.exists():
            downloaded_hrefs = set(cache_file.read_text(encoding="utf-8").splitlines())
            log.info(f"  Skip-downloaded: {len(downloaded_hrefs)} hrefs already in cache")

        all_records = []

        for idx, info in enumerate(cards, 1):
            year = info["year"]
            title = info["title"] or f"untitled_{idx}"
            log.info(f"\n[{idx:03d}/{len(cards)}] [{year}] {title}")

            # ── Skip already-downloaded entries ────────────────────────────────
            if skip_downloaded and info["href"] in downloaded_hrefs:
                log.info("  → Already downloaded, skipping")
                continue

            # ── Download cover ─────────────────────────────────────────────
            cover_file = None
            if info["cover_url"]:
                ext = url_ext(info["cover_url"])
                safe = slugify(title)
                cover_name = f"{safe}.{ext}"
                ok = download(info["cover_url"], covers_dir / cover_name)
                cover_file = cover_name if ok else None
                log.debug(f"  cover: {cover_name} ok={ok}")

            # ── Visit sub-page ─────────────────────────────────────────────
            sub = {}
            if info["href"]:
                sub = scrape_subpage(driver, info["href"], fallback_year=info["year"])
            else:
                log.warning("  (no href for this card)")

            # ── Skip collection-view pages if requested ────────────────────
            if skip_collections and sub.get("is_collection"):
                log.info("  → Skipped (collection-view page, use --no-skip-collections to include)")
                continue

            # ── Determine date prefix ──────────────────────────────────────
            post_date = sub.get("date", "")
            if not post_date:
                log.warning(f"  ⚠ No date found for {title!r}, using year fallback")
                post_date = f"{year}-00-00"

            safe_title = slugify(sub.get("title") or title)
            folder_name = f"{post_date}_{safe_title}"
            year_dir = out_dir / year
            page_dir = year_dir / folder_name
            page_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"  → folder: {folder_name}")

            # ── Download sub-page images ───────────────────────────────────
            image_records = []
            for i, img_url in enumerate(sub.get("images", []), 1):
                ext = url_ext(img_url)
                fname = f"{i:03d}.{ext}"
                dest = page_dir / fname
                ok = download(img_url, dest)
                image_records.append({
                    "file": fname if ok else None,
                    "url": img_url,
                })

            record = {
                "index": idx,
                "year": year,
                "date": post_date,
                "title": sub.get("title") or title,
                "gallery_title": title,
                "tags": info["tags"],
                "cover_file": cover_file,
                "cover_url": info["cover_url"],
                "href": info["href"],
                "properties": sub.get("properties", {}),
                "text": sub.get("text", []),
                "images": image_records,
                "local_path": f"{year}/{folder_name}",
            }
            all_records.append(record)

            write_markdown(page_dir, record)
            log.info(f"  ✓ saved: {year}/{folder_name}/README.md  "
                     f"({len(image_records)} images, {len(record['text'])} text blocks)")

            # ── Update download cache ──────────────────────────────────────
            if skip_downloaded and info["href"]:
                with cache_file.open("a", encoding="utf-8") as cf:
                    cf.write(info["href"] + "\n")
                downloaded_hrefs.add(info["href"])

        # ── Global index.md ───────────────────────────────────────────────
        write_index_md(out_dir, all_records)
        build_html(out_dir, all_records, url)

        log.info(f"\n{'='*60}")
        log.info(f"✅ DONE — {len(all_records)} entries → {out_dir.resolve()}")
        log.info(f"{'='*60}\n")

    finally:
        try:
            driver.quit()
        except Exception:
            pass


def _group_by_year(records: list) -> dict:
    from collections import defaultdict
    by_year: dict = defaultdict(list)
    for r in records:
        by_year[r["year"]].append(r)
    return by_year


def write_index_md(out_dir: Path, records: list):
    by_year = _group_by_year(records)

    lines = ["# Notion Gallery Archive\n"]
    for year in sorted(by_year, reverse=True):
        lines.append(f"## {year}\n")
        for r in by_year[year]:
            title = r.get("title") or "Untitled"
            path = r.get("local_path", "")
            date_str = r.get("date", "")
            tags = ", ".join(r.get("tags") or [])
            tag_str = f" `{tags}`" if tags else ""
            lines.append(f"- [{title}]({path}/README.md) — {date_str}{tag_str}")
        lines.append("")

    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
    log.info("✅ Saved README.md")


def build_html(out_dir: Path, records: list, source_url: str):
    by_year = _group_by_year(records)

    year_sections = ""
    for year in sorted(by_year, reverse=True):
        cards_html = ""
        for rec in by_year[year]:
            cover_src = f"covers/{rec['cover_file']}" if rec.get("cover_file") else ""
            cover_html = (f'<div class="cover"><img src="{cover_src}" loading="lazy"></div>'
                          if cover_src else '<div class="cover no-cover">No Cover</div>')
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in (rec.get("tags") or []))
            href = rec.get("href", "")
            title = rec.get("title", "")
            title_h = f'<a href="{href}" target="_blank">{title}</a>' if href else title
            date_str = rec.get("date", "")
            n_imgs = len(rec.get("images") or [])
            cards_html += f"""
<div class="card">
  {cover_html}
  <div class="card-body">
    <h3>{title_h}</h3>
    <div class="date">{date_str}</div>
    <div class="tags">{tags_html}</div>
    <div class="img-count">{n_imgs} image(s)</div>
  </div>
</div>"""
        year_sections += f'<h2 class="year-heading">{year}</h2><div class="grid">{cards_html}</div>\n'

    html = f"""<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Notion Archive</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#111;color:#e0e0e0;padding:24px}}
h1{{font-size:1.5rem;color:#fff;margin-bottom:6px}}
.src{{color:#888;font-size:.82rem;margin-bottom:28px}}
.year-heading{{font-size:1.2rem;color:#aaa;margin:28px 0 12px;border-bottom:1px solid #2a2a2a;padding-bottom:6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-bottom:8px}}
.card{{background:#1e1e1e;border-radius:10px;overflow:hidden;border:1px solid #252525;transition:border-color .15s}}
.card:hover{{border-color:#444}}
.cover{{height:160px;overflow:hidden;background:#0a0a0a;display:flex;align-items:center;justify-content:center}}
.cover img{{width:100%;height:100%;object-fit:cover}}
.no-cover{{color:#444;font-size:.75rem}}
.card-body{{padding:10px 12px}}
h3{{font-size:.88rem;font-weight:600;margin-bottom:6px;line-height:1.4}}
h3 a{{color:#7eb8f7;text-decoration:none}}
h3 a:hover{{text-decoration:underline}}
.date{{font-size:.75rem;color:#666;margin-bottom:5px}}
.tags{{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:5px}}
.tag{{background:#1a2a3a;color:#7eb8f7;padding:1px 7px;border-radius:10px;font-size:.68rem}}
.img-count{{font-size:.68rem;color:#555}}
</style></head><body>
<h1>🗂 Notion Gallery Archive</h1>
<p class="src">Source: <a href="{source_url}" target="_blank" style="color:#7eb8f7">{source_url}</a>
 &nbsp;·&nbsp; {len(records)} entries</p>
{year_sections}
</body></html>"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    log.info("✅ Saved index.html")


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Download Notion gallery with year structure.")
    ap.add_argument("--url", default="https://hightway420.notion.site/HOME-2d3110e3721d80918573e279b930c277")
    ap.add_argument("--out", default="notion_download")
    ap.add_argument("--no-headless", action="store_true", help="Show Chrome window")
    ap.add_argument("--log", default="notion_downloader.log", help="Log file path")
    ap.add_argument("--skip-downloaded", action="store_true",
                    help="Skip entries whose href is already in the download cache")
    ap.add_argument("--bypass-cloudflare", action="store_true",
                    help="Use undetected-chromedriver to bypass Cloudflare bot detection")
    ap.add_argument("--skip-collections", action="store_true",
                    help="Skip pages that contain a Notion collection-view block")
    args = ap.parse_args()

    setup_logging(args.log)
    log.info(f"notion_downloader starting — log: {args.log}")

    try:
        import selenium  # noqa: F401
    except ImportError:
        log.error("selenium not installed. Run: pip install selenium")
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    scrape_gallery(args.url, out_dir, headless=not args.no_headless,
                   skip_downloaded=args.skip_downloaded,
                   bypass_cloudflare=args.bypass_cloudflare,
                   skip_collections=args.skip_collections)


if __name__ == "__main__":
    main()
