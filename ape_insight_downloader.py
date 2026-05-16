#!/usr/bin/env python3
"""
ape_insight_downloader.py

Downloads all product images from shop.ape-insight.jp, organized by product
with Japanese names auto-translated to Chinese.

Usage:
    pip install requests
    python ape_insight_downloader.py
    python ape_insight_downloader.py --pages 2     # first 2 listing pages only
    python ape_insight_downloader.py --out my_dir  # custom output folder
    python ape_insight_downloader.py --no-translate
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import requests

BASE_URL = "https://shop.ape-insight.jp/"
CDN_HOST_RE = re.compile(r"img\d+\.shop-pro\.jp")
IMG_EXT_RE = re.compile(r"\.(jpg|jpeg|png|gif|webp)(\?|$)", re.I)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja-JP,ja;q=0.9,zh-CN;q=0.8",
    "Referer": BASE_URL,
}

_translation_cache: dict[str, str] = {}

log = logging.getLogger("ape_insight")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'[\\/*?:"<>|]', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip("._")
    return text[:60] or "untitled"


def url_ext(url: str) -> str:
    base = url.split("?")[0].rsplit(".", 1)
    ext = base[-1].lower() if len(base) > 1 else ""
    return ext if ext in ("jpg", "jpeg", "png", "gif", "webp") else "jpg"


def _thumb_to_fullsize(url: str) -> str:
    """Remove _th suffix from Shop-Pro thumbnail URL to get full-size."""
    clean = url.split("?")[0]
    return re.sub(r"_th(\.\w+)$", r"\1", clean)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _decode_response(resp: requests.Response) -> str:
    """Decode response content, detecting EUC-JP and other Japanese encodings."""
    # Prefer charset from Content-Type header
    ct = resp.headers.get("Content-Type", "")
    m = re.search(r"charset=([^\s;]+)", ct, re.I)
    if m:
        try:
            return resp.content.decode(m.group(1), errors="replace")
        except LookupError:
            pass
    # Check meta charset in first 1 KB of raw bytes
    snippet = resp.content[:1024].decode("ascii", errors="ignore")
    m = re.search(r'charset=["\']?([^"\';\s>]+)', snippet, re.I)
    if m:
        try:
            return resp.content.decode(m.group(1), errors="replace")
        except LookupError:
            pass
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def fetch_html(session: requests.Session, url: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return _decode_response(resp)
        except Exception as exc:
            log.warning("fetch %s attempt %d/%d: %s", url, attempt + 1, retries, exc)
            time.sleep(2 ** attempt)
    return ""


def fetch_product_html(session: requests.Session, pid: str, retries: int = 3) -> str:
    """Fetch product page, bypassing the server-side age gate via POST."""
    url = BASE_URL + f"?pid={pid}"
    for attempt in range(retries):
        try:
            resp = session.post(
                url, data={"restricted_age_agree": "1"}, headers=HEADERS, timeout=30
            )
            resp.raise_for_status()
            return _decode_response(resp)
        except Exception as exc:
            log.warning("fetch product %s attempt %d/%d: %s", pid, attempt + 1, retries, exc)
            time.sleep(2 ** attempt)
    return ""


def download_image(session: requests.Session, url: str, dest: Path, retries: int = 3) -> bool:
    if dest.exists():
        log.debug("  already exists: %s", dest.name)
        return True
    hdrs = {**HEADERS, "Referer": BASE_URL}
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=hdrs, timeout=40, stream=True)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            log.info("  ✓ %s", dest.name)
            return True
        except Exception as exc:
            log.warning("  ✗ attempt %d/%d: %s", attempt + 1, retries, exc)
            time.sleep(2 ** attempt)
    log.error("  ✗ FAILED: %s", url)
    return False


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

def translate_ja_to_zh(text: str, session: requests.Session) -> str:
    text = text.strip()
    if not text:
        return text
    if text in _translation_cache:
        return _translation_cache[text]
    try:
        resp = session.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "ja", "tl": "zh-CN", "dt": "t", "q": text},
            headers={"User-Agent": HEADERS["User-Agent"]},
            timeout=15,
        )
        data = resp.json()
        translated = "".join(part[0] for part in data[0] if part[0])
        _translation_cache[text] = translated
        time.sleep(0.5)
        return translated
    except Exception as exc:
        log.warning("translation failed for %r: %s", text, exc)
        _translation_cache[text] = text
        return text


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

def parse_listing_page(html: str) -> list[dict]:
    """Extract products from a category listing page."""
    products: dict[str, dict] = {}

    # Thumbnails: href="?pid=NNN" immediately followed by <img src="...">
    for m in re.finditer(
        r'href=["\']?\?pid=(\d+)["\']?[^>]*>\s*<img\b[^>]*\bsrc=["\']([^"\']+)["\']',
        html, re.I | re.S,
    ):
        pid, src = m.group(1), m.group(2)
        if pid not in products:
            products[pid] = {"pid": pid, "name": "", "thumb_url": src.split("?")[0]}

    # Product names: text-only pid links (content has no inner tags)
    for m in re.finditer(
        r'<a\b[^>]*href=["\']?\?pid=(\d+)["\']?[^>]*>\s*([^<]{2,120}?)\s*</a>',
        html, re.I,
    ):
        pid, name = m.group(1), m.group(2).strip()
        if len(name) < 2:
            continue
        if pid in products:
            if not products[pid]["name"]:
                products[pid]["name"] = name
        else:
            products[pid] = {"pid": pid, "name": name, "thumb_url": ""}

    return [p for p in products.values() if p["pid"]]


def extract_cdn_images(html: str) -> list[str]:
    """Return all full-size product image URLs from the Shop-Pro CDN."""
    found: set[str] = set()

    for m in re.finditer(
        r'(?:src|href)=["\']([^"\']*img\d+\.shop-pro\.jp[^"\']+)["\']',
        html, re.I,
    ):
        url = m.group(1).split("?")[0]
        # Only product images (not logos, CSS, favicons)
        if "/product/" not in url:
            continue
        if IMG_EXT_RE.search(url):
            found.add(url)

    # Prefer full-size images; fall back to thumbnails converted to full-size
    fullsize = {u for u in found if "_th." not in u}
    if fullsize:
        return sorted(fullsize)

    return sorted({_thumb_to_fullsize(u) for u in found})


def fetch_product_images(session: requests.Session, pid: str, thumb_url: str) -> list[str]:
    """Fetch product page (POST to bypass age gate) and return image URL list."""
    html = fetch_product_html(session, pid)

    if html:
        images = extract_cdn_images(html)
        if images:
            return images

    # Fallback: construct full-size URL from thumbnail
    if thumb_url:
        return [_thumb_to_fullsize(thumb_url)]
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def setup_logging(log_path: Path) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    log.setLevel(logging.DEBUG)
    # Use UTF-8 for stdout to handle CJK characters on Windows
    sh = logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False))
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    log.addHandler(sh)
    log.addHandler(fh)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download product images from shop.ape-insight.jp"
    )
    parser.add_argument("--out", default="ape_insight", help="Output directory (default: ape_insight)")
    parser.add_argument("--pages", type=int, default=0, help="Pages to scrape, 0 = all (default: 0)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between product requests (default: 1.0)")
    parser.add_argument("--no-translate", action="store_true", help="Keep Japanese folder names")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(out_dir / "download.log")

    # Resume support
    done_file = out_dir / ".downloaded_pids.txt"
    done_pids: set[str] = set()
    if done_file.exists():
        done_pids = set(done_file.read_text(encoding="utf-8").split())
    log.info("Resuming: %d products already downloaded", len(done_pids))

    session = requests.Session()

    # -----------------------------------------------------------------------
    # Phase 1: Collect all product listings
    # -----------------------------------------------------------------------
    log.info("=== Phase 1: Collecting product list ===")
    all_products: dict[str, dict] = {}
    max_pages = args.pages if args.pages > 0 else 86

    for page_num in range(1, max_pages + 1):
        url = BASE_URL + f"?mode=cate&cbid=2241192&csid=5&sort=n&page={page_num}"
        log.info("Listing page %d/%d", page_num, max_pages)
        html = fetch_html(session, url)
        if not html:
            log.warning("Failed to fetch page %d, stopping", page_num)
            break

        products = parse_listing_page(html)
        if not products:
            log.info("No products on page %d — reached end of catalogue", page_num)
            break

        new_count = 0
        for p in products:
            if p["pid"] not in all_products:
                all_products[p["pid"]] = p
                new_count += 1

        log.info("  +%d new products (total: %d)", new_count, len(all_products))
        if new_count == 0:
            log.info("No new products found — stopping early")
            break

        time.sleep(0.5)

    log.info("Total unique products collected: %d", len(all_products))

    # -----------------------------------------------------------------------
    # Phase 2: Download images
    # -----------------------------------------------------------------------
    log.info("=== Phase 2: Downloading product images ===")
    index_rows: list[dict] = []
    total = len(all_products)

    for i, (pid, product) in enumerate(all_products.items(), 1):
        ja_name = (product.get("name") or f"商品_{pid}").strip()
        prefix = f"[{i}/{total}] pid={pid}"

        if pid in done_pids:
            log.info("%s — already done, skipping", prefix)
            continue

        log.info("%s: %s", prefix, ja_name)

        # Translate
        zh_name = ja_name if args.no_translate else translate_ja_to_zh(ja_name, session)
        if zh_name != ja_name:
            log.info("  → %s", zh_name)

        # Create product folder
        folder_name = slugify(zh_name) + "_" + pid
        folder = out_dir / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        # Get image URLs
        thumb_url = product.get("thumb_url", "")
        image_urls = fetch_product_images(session, pid, thumb_url)

        if not image_urls:
            log.warning("  No images found for pid=%s", pid)

        # Download images
        n_downloaded = 0
        for j, img_url in enumerate(image_urls, 1):
            if not img_url:
                continue
            ext = url_ext(img_url)
            dest = folder / f"{j:03d}.{ext}"
            if download_image(session, img_url, dest):
                n_downloaded += 1

        index_rows.append(
            {"zh_name": zh_name, "ja_name": ja_name, "pid": pid, "n_images": n_downloaded}
        )

        # Mark done immediately so a crash can resume
        with done_file.open("a", encoding="utf-8") as f:
            f.write(pid + "\n")

        time.sleep(args.delay)

    # -----------------------------------------------------------------------
    # Write index.md
    # -----------------------------------------------------------------------
    log.info("Writing index.md")
    lines = [
        "# Ape Insight 商品图片存档\n",
        f"共 {len(index_rows)} 件商品\n",
        "",
        "| 中文名 | 原日文名 | 商品ID | 图片数 |",
        "|--------|----------|--------|--------|",
    ]
    for row in index_rows:
        lines.append(
            f"| {row['zh_name']} | {row['ja_name']} | {row['pid']} | {row['n_images']} |"
        )
    (out_dir / "index.md").write_text("\n".join(lines), encoding="utf-8")

    log.info("Done! Output in: %s/", out_dir)


if __name__ == "__main__":
    main()
