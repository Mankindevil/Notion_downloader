#!/usr/bin/env python3
"""
Notion Gallery Downloader (CloakBrowser / Playwright edition)
- Clicks 中文畫廊 tab
- Detects year groups (2026 / 2025 / ...) and mirrors that structure
- Uses sub-page 投稿日 date as folder/file prefix (e.g. 2026-02-28_理解・美/)
- Saves README.md per entry (not JSON)
- Downloads cover thumbnails + all sub-page images
- Uses CloakBrowser for source-level stealth (defeats Cloudflare / FingerprintJS)

Usage:
    pip install cloakbrowser
    python notion_downloader.py
    python notion_downloader.py --no-headless     # watch the browser
    python notion_downloader.py --url "..." --out my_folder
"""

import argparse
import json
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
    m = re.match(r'^(\d{4}-\d{2}-\d{2})', raw)
    if m:
        result = m.group(1)
        log.debug(f"    → ISO match: {result}")
        return result

    m = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})', raw)
    if m:
        result = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        log.debug(f"    → slash match: {result}")
        return result

    m = re.search(r'(\d{4})[年/](\d{1,2})[月/](\d{1,2})日?', raw)
    if m:
        result = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        log.debug(f"    → Chinese/JP full match: {result}")
        return result

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

    _wd_map = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}
    m = re.search(r'(?:上星期|上週|先週)([一二三四五六日天])', raw)
    if m:
        target_wd = _wd_map[m.group(1)]
        last_week_monday = today - timedelta(days=today.weekday() + 7)
        result = (last_week_monday + timedelta(days=target_wd)).isoformat()
        log.debug(f"    → 上星期X match: {result}")
        return result

    # Bare weekday name → most recent occurrence (Notion collapses recent dates this way)
    _weekday_names = {
        # Chinese
        "星期一": 0, "星期二": 1, "星期三": 2, "星期四": 3, "星期五": 4, "星期六": 5, "星期日": 6, "星期天": 6,
        "週一": 0, "週二": 1, "週三": 2, "週四": 3, "週五": 4, "週六": 5, "週日": 6, "週天": 6,
        "周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6, "周天": 6,
        # Japanese (long form must come before short to match correctly in substring scan)
        "月曜日": 0, "火曜日": 1, "水曜日": 2, "木曜日": 3, "金曜日": 4, "土曜日": 5, "日曜日": 6,
        "月曜": 0, "火曜": 1, "水曜": 2, "木曜": 3, "金曜": 4, "土曜": 5, "日曜": 6,
        # Korean
        "월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3, "금요일": 4, "토요일": 5, "일요일": 6,
        # English
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    raw_stripped = raw.strip()
    matched_wd = _weekday_names.get(raw_stripped)
    if matched_wd is None:
        matched_wd = _weekday_names.get(raw_stripped.lower())
    if matched_wd is None:
        for key, wd in _weekday_names.items():
            if not key.isascii() and key in raw:
                matched_wd = wd
                break
    if matched_wd is not None:
        diff = (today.weekday() - matched_wd) % 7
        result = (today - timedelta(days=diff)).isoformat()
        log.debug(f"    → bare weekday {raw_stripped!r}: {result}")
        return result

    # ── Relative: N units ago ─────────────────────────────────────────────
    m = re.search(r'(\d+)\s*(?:天前|日前|days?\s*ago)', raw, re.I)
    if m:
        result = (today - timedelta(days=int(m.group(1)))).isoformat()
        log.debug(f"    → relative N days ago: {result}")
        return result

    m = re.search(r'(\d+)\s*(?:周前|週前|weeks?\s*ago)', raw, re.I)
    if m:
        result = (today - timedelta(weeks=int(m.group(1)))).isoformat()
        log.debug(f"    → relative N weeks ago: {result}")
        return result
    if "a week ago" in r or "1 week ago" in r:
        result = (today - timedelta(weeks=1)).isoformat()
        log.debug(f"    → relative 1 week ago: {result}")
        return result

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
    patterns = [
        r'"start"\s*:\s*"(20\d\d-\d{2}-\d{2})',
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
# CloakBrowser / Playwright helpers
# ──────────────────────────────────────────────────────────────────────────────

def make_context(headless: bool, profile_dir: Path):
    """Launch a persistent CloakBrowser context — stealth fingerprints baked into the binary."""
    from cloakbrowser import launch_persistent_context
    profile_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Launching CloakBrowser (persistent profile: {profile_dir})")
    return launch_persistent_context(
        str(profile_dir),
        headless=headless,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--lang=zh-TW"],
        viewport={"width": 1920, "height": 1080},
        locale="zh-TW",
        humanize=True,
    )


def wait_for_page(page, timeout=30):
    for sel in ["[data-block-id]", ".notion-page-content", ".notion-scroller", ".notion-collection", "main"]:
        try:
            page.wait_for_selector(sel, timeout=timeout * 1000)
            return sel
        except Exception:
            continue
    return None


def slow_scroll(page, step_px=400, delay=0.35):
    page.evaluate("window.scrollTo(0,0)")
    time.sleep(0.5)
    total = page.evaluate("document.body.scrollHeight")
    pos = 0
    while pos < total:
        pos += step_px
        page.evaluate(f"window.scrollTo(0,{pos})")
        time.sleep(delay)
        total = page.evaluate("document.body.scrollHeight")
    time.sleep(1)


def open_all_toggles(page):
    """Click all closed toggle blocks to expose hidden content."""
    toggle_selectors = [
        ".notion-toggle-block [role='button']",
        "[class*='toggle'][aria-expanded='false']",
        "summary",
    ]
    opened = 0
    for sel in toggle_selectors:
        try:
            for t in page.query_selector_all(sel):
                try:
                    expanded = t.get_attribute("aria-expanded")
                    if expanded == "false" or expanded is None:
                        t.evaluate("el => el.click()")
                        opened += 1
                        time.sleep(0.15)
                except Exception:
                    pass
        except Exception:
            pass
    if opened:
        log.debug(f"    opened {opened} toggle block(s)")
        time.sleep(0.5)


def get_bg_image_urls(page):
    urls = []
    for el in page.query_selector_all("[style*='background-image']"):
        style = el.get_attribute("style") or ""
        for m in re.finditer(r'url\(["\']?(https?://[^"\')\s]+)["\']?\)', style):
            u = m.group(1)
            if ".svg" not in u:
                urls.append(u)
    return urls


# Hosts that only ever serve non-content thumbnails / proxies / tracking pixels —
# never the artist's uploaded artwork. Filtered out of post images.
_JUNK_IMG_HOSTS = (
    "gstatic.com", "encrypted-tbn", "google.com/images",
    "googleusercontent.com/proxy", "notion.so/images/",
)


def get_all_img_urls(page):
    """Collect resolved (absolute) <img> URLs, skipping placeholders, icons and junk thumbnails.

    Notion lazy-loads content images: the `src` *attribute* is often a relative path
    ("/image/...") or still a data: placeholder, while the resolved `.src` / `.currentSrc`
    *property* is always the absolute URL. We read the property — reading the attribute and
    testing `startswith("http")` silently drops every relative-attribute content image.
    """
    raw = page.evaluate("""() => Array.from(document.querySelectorAll('img')).map(im => ({
        src: im.currentSrc || im.src || '',
        nw: im.naturalWidth || 0,
    }))""")
    urls = []
    for im in raw:
        src = im.get("src") or ""
        low = src.lower()
        if not src.startswith("http") or src.startswith("data:"):
            continue
        if ".svg" in low:
            continue
        if any(h in low for h in _JUNK_IMG_HOSTS):
            continue
        # naturalWidth is 0 for not-yet-loaded images (keep those); only drop true tiny icons.
        if 0 < im.get("nw", 0) < 30:
            continue
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
            if ".svg" in u.lower():
                continue
            if u not in seen:
                seen.add(u)
                result.append(u)
    return result


def click_tab(page, label: str) -> bool:
    try:
        els = page.query_selector_all(f"xpath=//*[contains(text(), '{label}')]")
        for el in els:
            target = el
            for _ in range(5):
                try:
                    target.evaluate("el => el.click()")
                    time.sleep(0.3)
                    return True
                except Exception:
                    pass
                try:
                    handle = target.evaluate_handle("el => el.parentElement")
                    parent = handle.as_element()
                    if not parent:
                        break
                    target = parent
                except Exception:
                    break
    except Exception:
        pass
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Sub-page scraper
# ──────────────────────────────────────────────────────────────────────────────

def scrape_subpage(page, page_url: str, fallback_year: str = "") -> dict:
    """Visit a card sub-page, extract title, properties (incl. date), images, text."""
    result = {"url": page_url, "title": "", "date": "", "properties": {}, "images": [], "text": [],
              "is_collection": False}

    try:
        log.info(f"  Loading sub-page: {page_url}")
        page.goto(page_url)
        sel = wait_for_page(page, timeout=30)
        if not sel:
            log.warning(f"  ⚠ Page load timeout: {page_url}")
            return result
        time.sleep(2.5)

        if page.query_selector(".notion-collection_view_page-block"):
            result["is_collection"] = True
            log.debug("  (page contains a collection-view block)")

        open_all_toggles(page)
        slow_scroll(page)
        open_all_toggles(page)  # open any toggles revealed after scroll

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
                el = page.query_selector(ts)
                if not el:
                    continue
                t = el.inner_text().strip()
                if t:
                    result["title"] = t
                    log.debug(f"  title found via {ts!r}: {t!r}")
                    break
            except Exception:
                continue
        if not result["title"]:
            result["title"] = page.title().replace("| Notion", "").replace("– Notion", "").strip()
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
                time_el.hover()
                time.sleep(0.6)
                for tip in page.query_selector_all(
                        "[class*='tooltip'], [role='tooltip'], [data-radix-popper-content-wrapper] *"):
                    try:
                        tip_text = (tip.inner_text() or "").strip()
                    except Exception:
                        continue
                    if tip_text and re.search(r'\d{4}|\d{1,2}[月/]\d{1,2}', tip_text):
                        d = parse_notion_date(tip_text, fallback_year)
                        if d:
                            log.debug(f"    → date from tooltip: {d}")
                            return d
            except Exception as e:
                log.debug(f"    hover failed: {e}")

            # 5. Visible text of the element
            try:
                visible_text = (time_el.inner_text() or "").strip()
            except Exception:
                visible_text = ""
            log.debug(f"    <time> visible text: {visible_text!r}")
            if visible_text:
                d = parse_notion_date(visible_text, fallback_year)
                if d:
                    log.debug(f"    → date from visible text: {d}")
                    return d

            return ""

        # ── Strategy A: scan ALL <time> elements ──────────────────────────────
        time_els = page.query_selector_all("time")
        log.debug(f"  Found {len(time_els)} <time> element(s)")
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
                js_prop_result = page.evaluate("""() => {
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
                }""")
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
        prop_selectors = [
            ".notion-page-property",
            "[class*='property-row']",
            "[class*='property'][data-property-id]",
            "[class*='propertyRow']",
            "[class*='notion-property']",
        ]
        for ps in prop_selectors:
            rows = page.query_selector_all(ps)
            if not rows:
                continue
            log.debug(f"  property selector {ps!r} → {len(rows)} rows")
            for row in rows:
                try:
                    txt = (row.inner_text() or "").strip()
                    if not txt:
                        continue
                    lines = [l.strip() for l in txt.splitlines() if l.strip()]
                    if len(lines) < 2:
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
                        te = row.query_selector("time")
                        if te:
                            d = extract_date_from_time_el(te)
                            if d:
                                result["date"] = d
                                log.info(f"  date from property <time>: {d}")
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
                    label_els = page.query_selector_all(
                        f"xpath=//*[normalize-space(text())='{prop_name}']"
                    )
                    for label_el in label_els:
                        try:
                            container = label_el
                            for _ in range(8):
                                handle = container.evaluate_handle("el => el.parentElement")
                                parent = handle.as_element()
                                if not parent:
                                    break
                                parent_text = (parent.inner_text() or "").strip()
                                if prop_name in parent_text and len(parent_text) > len(prop_name):
                                    container = parent
                                    break
                                container = parent
                            row_text = (container.inner_text() or "").strip()
                            v = row_text.replace(prop_name, "").strip()
                            v = _COPY_NOISE_RE.sub('', v).strip()
                            if v and prop_name not in result["properties"]:
                                result["properties"][prop_name] = v
                                log.debug(f"  XPath property: {prop_name!r} = {v!r}")

                            if prop_name in date_prop_keys and not result["date"]:
                                te = container.query_selector("time")
                                if te:
                                    d = extract_date_from_time_el(te)
                                    if d:
                                        result["date"] = d
                                        log.info(f"  date from XPath <time>: {d}")
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
                js_props = page.evaluate("""() => {
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
                }""")
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
        page_source = page.content()
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
            for b in page.query_selector_all(sel):
                try:
                    t = (b.inner_text() or "").strip()
                except Exception:
                    continue
                if t and t not in seen_texts:
                    seen_texts.add(t)
                    result["text"].append(t)

        if not result["text"]:
            log.debug("  No text blocks via specific selectors, trying broad fallback...")
            for tag in ["p", "h1", "h2", "h3"]:
                for el in page.query_selector_all(tag):
                    try:
                        t = (el.inner_text() or "").strip()
                    except Exception:
                        continue
                    if t and len(t) > 10 and t not in seen_texts:
                        seen_texts.add(t)
                        result["text"].append(t)

        log.debug(f"  extracted {len(result['text'])} text block(s)")

        # ── Images ────────────────────────────────────────────────────────────
        img_urls = []
        img_urls.extend(get_all_img_urls(page))
        img_urls.extend(get_bg_image_urls(page))
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

    if record.get("cover_file"):
        rel = f"../../covers/{record['cover_file']}"
        lines.append(f"## Cover\n\n![cover]({rel})\n")

    if record.get("text"):
        lines.append("## Content\n")
        for t in record["text"]:
            lines.append(t + "\n")
        lines.append("")

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

def get_cards_with_years(page) -> list:
    """
    Use JavaScript to walk the full DOM in order, finding:
    - Year group headers (elements whose trimmed text matches 20XX)
    - Card <a> elements (any internal Notion link with text)
    Returns list of {year, href, title, tags, cover_url}
    """
    js_cards = page.evaluate("""() => {
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
    }""")

    js_years = page.evaluate("""() => {
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
    }""")

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

    # ── Filter to actual gallery cards ───────────────────────────────────
    card_items = [c for c in js_cards if c['text'] and re.search(r'[0-9a-f]{20,}', c['href'])]
    log.info(f"  Filtered to {len(card_items)} gallery card links")

    if not card_items:
        card_items = [c for c in js_cards if '\n' in c['text'] and re.search(r'[0-9a-f]{10,}', c['href'])]
        log.info(f"  Fallback: {len(card_items)} candidates")

    # ── Sort by y-position, assign years ──────────────────────────────────
    card_items.sort(key=lambda x: x['y'])
    year_headers = sorted(js_years, key=lambda x: x['y'])

    def assign_year(card_y):
        assigned = str(date.today().year)
        for yh in year_headers:
            if yh['y'] <= card_y + 50:
                assigned = yh['year']
        return assigned

    # ── Dedupe and build result ──────────────────────────────────────────
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

        # Cover (best-effort: look for bg-image / <img> inside the card link)
        try:
            escaped = href.replace('"', '\\"')
            card_el = page.query_selector(f'a[href="{escaped}"]')
            if card_el:
                for div in card_el.query_selector_all("[style*='background-image']"):
                    style = div.get_attribute("style") or ""
                    m = re.search(r'url\(["\']?(https?://[^"\')\ \s]+)["\']?\)', style)
                    if m and ".svg" not in m.group(1):
                        info["cover_url"] = m.group(1)
                        break
                if not info["cover_url"]:
                    for img in card_el.query_selector_all("img"):
                        # Read the resolved property (absolute) — the attribute may be relative.
                        src = img.evaluate("el => el.currentSrc || el.src || ''") or ""
                        low = src.lower()
                        if not src.startswith("http") or ".svg" in low:
                            continue
                        if any(h in low for h in _JUNK_IMG_HOSTS):
                            continue
                        try:
                            w = img.evaluate("el => el.naturalWidth")
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

def scrape_gallery(url: str, out_dir: Path, headless: bool = True,
                   skip_downloaded: bool = False, skip_collections: bool = False,
                   profile_dir: Path = None):
    profile_dir = profile_dir or (out_dir / ".cloak-profile")
    ctx = make_context(headless, profile_dir)
    try:
        page = ctx.new_page()
        page.set_default_timeout(30000)

        log.info(f"\n{'='*60}")
        log.info(f"Loading: {url}")
        log.info(f"{'='*60}")
        page.goto(url)
        wait_for_page(page, timeout=30)
        time.sleep(3)

        # ── Click 中文畫廊 tab ─────────────────────────────────────────────
        for label in ["中文畫廊", "中文画廊"]:
            if click_tab(page, label):
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
                    btns = page.query_selector_all(
                        f"xpath=//*[normalize-space(text())='{label}' or contains(text(),'{label}')]"
                    )
                    for btn in btns:
                        try:
                            try:
                                btn.scroll_into_view_if_needed(timeout=2000)
                            except Exception:
                                pass
                            time.sleep(0.3)
                            btn.evaluate("el => el.click()")
                            log.info(f"  ↓ Clicked '{label}'")
                            clicked += 1
                            time.sleep(2)
                        except Exception:
                            pass
                except Exception:
                    pass
            return clicked

        prev_height = 0
        for _pass in range(20):
            page.evaluate("window.scrollTo(0,0)")
            time.sleep(0.5)
            total = page.evaluate("document.body.scrollHeight")
            pos = 0
            while pos < total:
                pos += 500
                page.evaluate(f"window.scrollTo(0,{pos})")
                time.sleep(0.3)
                total = page.evaluate("document.body.scrollHeight")
            click_all_load_more_visible()
            new_height = page.evaluate("document.body.scrollHeight")
            log.debug(f"  Pass {_pass + 1}: height={new_height} (prev={prev_height})")
            if new_height == prev_height:
                break
            prev_height = new_height
        log.info("  ✓ All content loaded")

        slow_scroll(page)
        time.sleep(3)  # allow any lazily-rendered cards to finish appearing

        # ── Collect all cards with year info ──────────────────────────────
        log.info("Collecting cards...")
        cards = get_cards_with_years(page)

        if not cards:
            log.warning("⚠ No cards found — saving debug_source.html")
            (out_dir / "debug_source.html").write_text(page.content(), encoding="utf-8")
            return

        from collections import Counter
        year_counts = Counter(c["year"] for c in cards)
        log.info(f"✓ {len(cards)} cards: {dict(sorted(year_counts.items(), reverse=True))}\n")

        covers_dir = out_dir / "covers"
        covers_dir.mkdir(parents=True, exist_ok=True)

        # ── Download manifest (href → folder/date/status) ─────────────────────
        # A JSON manifest replaces the old flat .downloaded_hrefs.txt. It records WHERE each
        # post went and whether every image succeeded, so --skip-downloaded only skips posts
        # that are actually complete (incomplete ones get retried), and a re-run reuses the
        # existing folder instead of creating a stale duplicate when the parsed date changes.
        manifest_file = out_dir / ".manifest.json"
        manifest: dict = {}
        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
            except Exception as e:
                log.warning(f"  ⚠ manifest unreadable ({e}); starting fresh")
        # One-time migration from the legacy flat cache: treat listed hrefs as complete.
        legacy = out_dir / ".downloaded_hrefs.txt"
        if legacy.exists():
            for h in legacy.read_text(encoding="utf-8").splitlines():
                manifest.setdefault(h.strip(), {"complete": True, "local_path": ""})
        if skip_downloaded:
            done = sum(1 for v in manifest.values() if v.get("complete"))
            log.info(f"  Skip-downloaded: {done} complete post(s) in manifest")

        def save_manifest():
            manifest_file.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        all_records = []

        for idx, info in enumerate(cards, 1):
            year = info["year"]
            title = info["title"] or f"untitled_{idx}"
            log.info(f"\n[{idx:03d}/{len(cards)}] [{year}] {title}")

            prev = manifest.get(info["href"])
            # Skip only posts recorded as fully complete whose folder still exists —
            # an incompletely-downloaded post is re-visited so its missing images recover.
            if (skip_downloaded and prev and prev.get("complete")
                    and prev.get("local_path") and (out_dir / prev["local_path"]).exists()):
                log.info("  → Already fully downloaded, skipping")
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
                sub = scrape_subpage(page, info["href"], fallback_year=info["year"])
            else:
                log.warning("  (no href for this card)")

            if skip_collections and sub.get("is_collection"):
                log.info("  → Skipped (collection-view page, use --no-skip-collections to include)")
                continue

            post_date = sub.get("date", "")
            if not post_date:
                log.warning(f"  ⚠ No date found for {title!r}, using year fallback")
                post_date = f"{year}-00-00"

            safe_title = slugify(sub.get("title") or title)
            folder_name = f"{post_date}_{safe_title}"
            local_path = f"{year}/{folder_name}"
            year_dir = out_dir / year
            year_dir.mkdir(parents=True, exist_ok=True)
            page_dir = year_dir / folder_name

            # If this post was previously saved under a different folder (e.g. the date went
            # from 2026-00-00 to 2026-05-19 once parsing improved), move the old folder rather
            # than leaving a stale duplicate behind.
            if prev and prev.get("local_path") and prev["local_path"] != local_path:
                old_dir = out_dir / prev["local_path"]
                if old_dir.exists() and not page_dir.exists():
                    old_dir.rename(page_dir)
                    log.info(f"  ↻ migrated {prev['local_path']} → {local_path}")

            page_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"  → folder: {folder_name}")

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

            # Record outcome in the manifest. "complete" only when every image saved OK,
            # so a partial download is retried on the next --skip-downloaded run.
            if info["href"]:
                n_ok = sum(1 for r in image_records if r["file"])
                manifest[info["href"]] = {
                    "local_path": local_path,
                    "title": record["title"],
                    "date": post_date,
                    "images": n_ok,
                    "complete": bool(image_records) and n_ok == len(image_records),
                }
                save_manifest()

        write_index_md(out_dir, all_records)
        build_html(out_dir, all_records, url)

        log.info(f"\n{'='*60}")
        log.info(f"✅ DONE — {len(all_records)} entries → {out_dir.resolve()}")
        log.info(f"{'='*60}\n")

    finally:
        try:
            ctx.close()
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
# Reverify: re-check already-downloaded posts and recover images the old bug dropped
# ──────────────────────────────────────────────────────────────────────────────

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_SRC_RE = re.compile(r'\|\s*Source\s*\|\s*\[[^\]]*\]\((https?://[^)\s]+)\)')
_TAGS_RE = re.compile(r'\|\s*Tags\s*\|\s*([^|]+?)\s*\|')
_COVER_RE = re.compile(r'!\[cover\]\([^)]*covers/([^)]+)\)')
# Junk thumbnails (e.g. gstatic 225×225) are ~10 KB; real artwork is far larger.
# Only stale image files under this size are deleted, so real images are never lost.
_JUNK_MAX_BYTES = 20 * 1024


def _read_post_meta(readme: Path):
    """Pull Source href, Tags and cover filename out of an existing README.md."""
    href, tags, cover = "", [], None
    try:
        txt = readme.read_text(encoding="utf-8")
    except Exception:
        return href, tags, cover
    m = _SRC_RE.search(txt)
    if m:
        href = m.group(1).strip()
    m = _TAGS_RE.search(txt)
    if m:
        tags = [t.strip() for t in m.group(1).split(",") if t.strip()]
    m = _COVER_RE.search(txt)
    if m:
        cover = m.group(1).strip()
    return href, tags, cover


def rebuild_index_from_disk(out_dir: Path, source_url: str = ""):
    """Regenerate the top-level README.md + index.html from whatever post folders exist on
    disk (used after reverify/dedup so the index reflects the cleaned state)."""
    records = []
    for readme in sorted(out_dir.glob("*/*/README.md")):
        folder = readme.parent
        year = folder.parent.name
        href, tags, cover = _read_post_meta(readme)
        txt = readme.read_text(encoding="utf-8")
        tm = re.search(r'^#\s+(.+)$', txt, re.M)
        title = tm.group(1).strip() if tm else folder.name
        dm = re.search(r'\|\s*投稿日\s*\|\s*([0-9-]+)\s*\|', txt)
        n_imgs = sum(1 for f in folder.iterdir() if f.suffix.lower() in _IMG_EXTS)
        records.append({
            "year": year, "local_path": f"{year}/{folder.name}",
            "title": title, "date": dm.group(1) if dm else "",
            "tags": tags, "cover_file": cover, "href": href,
            "images": [None] * n_imgs,
        })
    write_index_md(out_dir, records)
    build_html(out_dir, records, source_url)
    log.info(f"  rebuilt index from {len(records)} folder(s)")


def reverify_existing(out_dir: Path, headless: bool = True, profile_dir: Path = None,
                      force: bool = False, source_url: str = ""):
    """Re-visit every already-downloaded post, refetch its real images (recovering ones the
    old relative-`src` bug silently dropped) and delete junk thumbnails left on disk.

    Resumable: posts marked `reverified` in the manifest are skipped unless --force.
    Safe: a post that yields no images is left untouched; only sub-20 KB stale files are
    deleted, so real artwork is never removed even if a page under-fetches on one pass.
    """
    profile_dir = profile_dir or (out_dir / ".cloak-profile")

    manifest_file = out_dir / ".manifest.json"
    manifest: dict = {}
    if manifest_file.exists():
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    def save_manifest():
        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                 encoding="utf-8")

    # Worklist from existing folders — every README carries its Source href.
    posts, seen = [], set()
    for readme in sorted(out_dir.glob("*/*/README.md")):
        href, tags, cover = _read_post_meta(readme)
        if not href or href in seen:
            continue
        seen.add(href)
        posts.append({"href": href, "folder": readme.parent,
                      "year": readme.parent.parent.name, "tags": tags, "cover": cover})
    log.info(f"Reverify: {len(posts)} post(s) to check")

    stats = {"checked": 0, "added": 0, "junk_removed": 0, "skipped": 0, "no_images": 0}
    ctx = make_context(headless, profile_dir)
    try:
        page = ctx.new_page()
        page.set_default_timeout(30000)
        for idx, p in enumerate(posts, 1):
            href, folder = p["href"], p["folder"]
            if manifest.get(href, {}).get("reverified") and not force:
                stats["skipped"] += 1
                continue

            log.info(f"\n[{idx:03d}/{len(posts)}] reverify {p['year']}/{folder.name}")
            existing = {f.name for f in folder.iterdir() if f.suffix.lower() in _IMG_EXTS}

            sub = scrape_subpage(page, href, fallback_year=p["year"])
            imgs = sub.get("images", [])
            if not imgs:
                log.warning("  ⚠ no images extracted — leaving folder untouched")
                stats["no_images"] += 1
                continue

            new_files, records = [], []
            for i, u in enumerate(imgs, 1):
                fn = f"{i:03d}.{url_ext(u)}"
                ok = download(u, folder / fn)
                new_files.append(fn)
                records.append({"file": fn if ok else None, "url": u})
            new_set = set(new_files)

            added = [f for f in new_files if f not in existing]
            if added:
                stats["added"] += len(added)
                log.info(f"  + recovered {len(added)} image(s): {', '.join(added)}")

            # Remove stale junk thumbnails (small files not in the fresh set).
            for f in list(folder.iterdir()):
                if (f.suffix.lower() in _IMG_EXTS and f.name not in new_set
                        and f.stat().st_size < _JUNK_MAX_BYTES):
                    try:
                        f.unlink()
                        stats["junk_removed"] += 1
                        log.info(f"  ✗ removed junk thumbnail: {f.name}")
                    except Exception:
                        pass

            rec = {
                "title": sub.get("title") or folder.name,
                "date": sub.get("date") or "",
                "year": p["year"],
                "tags": p["tags"],
                "cover_file": p["cover"],
                "href": href,
                "properties": sub.get("properties", {}),
                "text": sub.get("text", []),
                "images": records,
            }
            write_markdown(folder, rec)

            n_ok = sum(1 for r in records if r["file"])
            manifest[href] = {
                "local_path": f"{p['year']}/{folder.name}",
                "title": rec["title"],
                "date": rec["date"],
                "images": n_ok,
                "complete": n_ok == len(records) and n_ok > 0,
                "reverified": True,
            }
            save_manifest()
            stats["checked"] += 1

        rebuild_index_from_disk(out_dir, source_url)
        log.info(f"\n{'='*60}")
        log.info(f"✅ Reverify done — checked {stats['checked']}, recovered {stats['added']} "
                 f"image(s), removed {stats['junk_removed']} junk, skipped {stats['skipped']} "
                 f"(already reverified), {stats['no_images']} yielded no images")
        log.info(f"{'='*60}")
    finally:
        try:
            ctx.close()
        except Exception:
            pass
    return stats


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Download Notion gallery with year structure (CloakBrowser edition).")
    ap.add_argument("--url", default="https://hightway420.notion.site/HOME-2d3110e3721d80918573e279b930c277")
    ap.add_argument("--out", default="notion_download")
    ap.add_argument("--no-headless", action="store_true", help="Show Chrome window")
    ap.add_argument("--log", default="notion_downloader.log", help="Log file path")
    ap.add_argument("--skip-downloaded", action="store_true",
                    help="Skip entries whose href is already in the download cache")
    ap.add_argument("--skip-collections", action="store_true",
                    help="Skip pages that contain a Notion collection-view block")
    ap.add_argument("--profile-dir", default=None,
                    help="CloakBrowser persistent profile directory (default: <out>/.cloak-profile)")
    ap.add_argument("--reverify", action="store_true",
                    help="Re-check already-downloaded posts: refetch real images and remove junk thumbnails")
    ap.add_argument("--force", action="store_true",
                    help="With --reverify, re-check even posts already marked reverified in the manifest")
    args = ap.parse_args()

    setup_logging(args.log)
    log.info(f"notion_downloader starting — log: {args.log}")

    try:
        import cloakbrowser  # noqa: F401
    except ImportError:
        log.error("cloakbrowser not installed. Run: pip install cloakbrowser")
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(args.profile_dir) if args.profile_dir else None

    if args.reverify:
        reverify_existing(out_dir, headless=not args.no_headless,
                          profile_dir=profile_dir, force=args.force, source_url=args.url)
    else:
        scrape_gallery(args.url, out_dir, headless=not args.no_headless,
                       skip_downloaded=args.skip_downloaded,
                       skip_collections=args.skip_collections,
                       profile_dir=profile_dir)


if __name__ == "__main__":
    main()
