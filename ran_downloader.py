#!/usr/bin/env python3
"""
ran_downloader.py

Downloads all posts from ranagu.com (WordPress), including password-protected
ones. Passwords are loaded from local P:\\fanbox\\RAN★\\**\\links-*.txt files.

Usage:
    python ran_downloader.py
    python ran_downloader.py --pages 1 --delay 0.5    # smoke test first page
    python ran_downloader.py --out RAN_download --fanbox "P:\\fanbox\\RAN★"
    python ran_downloader.py --no-password             # skip protected posts
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

import requests

BASE_URL = "https://ranagu.com"
WP_POSTPASS_URL = f"{BASE_URL}/wp-login.php?action=postpass"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja-JP,ja;q=0.9",
    "Referer": BASE_URL + "/",
}

_active_password: str = ""  # password the current session cookie is set to

log = logging.getLogger("ran")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'[\\/*?:"<>|]', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip("._")
    return text[:80] or "untitled"


def url_ext(url: str) -> str:
    base = url.split("?")[0].rsplit(".", 1)
    ext = base[-1].lower() if len(base) > 1 else ""
    return ext if ext in ("jpg", "jpeg", "png", "gif", "webp") else "jpg"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _decode_response(resp: requests.Response) -> str:
    ct = resp.headers.get("Content-Type", "")
    m = re.search(r"charset=([^\s;]+)", ct, re.I)
    if m:
        try:
            return resp.content.decode(m.group(1), errors="replace")
        except LookupError:
            pass
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
            resp = session.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            resp.raise_for_status()
            return _decode_response(resp)
        except Exception as exc:
            log.warning("fetch %s attempt %d/%d: %s", url, attempt + 1, retries, exc)
            time.sleep(2 ** attempt)
    return ""


def download_image(session: requests.Session, url: str, dest: Path, retries: int = 3) -> bool:
    if dest.exists():
        log.debug("  already exists: %s", dest.name)
        return True
    hdrs = {**HEADERS, "Referer": BASE_URL + "/"}
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=hdrs, timeout=60, stream=True)
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
# Password management
# ---------------------------------------------------------------------------

_REFERENCE_PHRASES = ("同一", "共通", "最新", "プラン", "参照", "同じ")

def _extract_password(links_path: Path) -> str:
    """Read a links-*.txt file and return the actual 閲覧コード password.

    Skips reference strings like 「最新月の特濃プラン投稿と同一」 that point to
    another post's password rather than giving the password itself.
    """
    try:
        text = links_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    for line in reversed(text.splitlines()):
        if "閲覧コード" not in line:
            continue
        after = re.split(r"閲覧コード\s*", line, maxsplit=1)
        if len(after) < 2:
            continue
        pwd = after[1].strip()
        if not pwd:
            continue
        # Skip lines that start with a colon/bracket (reference, not a password)
        if pwd[0] in ("：", ":", "「", "『", "【", "（"):
            continue
        # Skip reference phrases that describe where the password is, not the password itself
        if any(phrase in pwd for phrase in _REFERENCE_PHRASES):
            continue
        # Real passwords are short ASCII strings — reject Japanese/fullwidth characters
        if re.search(r'[　-鿿＀-￯぀-ヿ]', pwd):
            continue
        if len(pwd) > 60 or len(pwd) < 2:
            continue
        return pwd
    return ""


def load_password_map(
    fanbox_dir: Path,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return (title_map, month_map) from P:\\fanbox\\RAN★\\.

    title_map: {post_title_without_date: password}
    month_map: {YYYY-MM: [unique passwords from that month]}
    """
    title_map: dict[str, str] = {}
    month_map: dict[str, list[str]] = {}

    if not fanbox_dir.exists():
        log.warning("Fanbox dir not found: %s", fanbox_dir)
        return title_map, month_map

    for folder in fanbox_dir.iterdir():
        if not folder.is_dir():
            continue
        m = re.match(r"^(\d{4}-\d{2})-\d{2}-(.+)$", folder.name)
        if not m:
            continue
        month, title = m.group(1), m.group(2).strip()

        links_files = list(folder.glob("links-*.txt"))
        if not links_files:
            continue

        pwd = _extract_password(links_files[0])
        if pwd:
            title_map[title] = pwd
            bucket = month_map.setdefault(month, [])
            if pwd not in bucket:
                bucket.append(pwd)

    log.info(
        "Loaded %d title passwords, %d months from %s",
        len(title_map), len(month_map), fanbox_dir,
    )
    return title_map, month_map


def _normalize(text: str) -> str:
    """Strip all punctuation/spaces, keep CJK + alphanumeric for fuzzy match."""
    return re.sub(r"[^\w　-鿿゠-ヿ぀-ゟ]", "", text)


def find_password(
    wp_title: str,
    wp_date: str,
    title_map: dict[str, str],
    month_map: dict[str, list[str]],
) -> list[str]:
    """Return candidate passwords best-first.

    Priority: title match → month match → all known passwords newest-first.
    The global fallback ensures the site-wide shared password is always tried
    even for months not represented in the local fanbox files.
    """
    candidates: list[str] = []
    title = re.sub(r"^保護中:\s*", "", wp_title).strip()

    # Exact title match
    if title in title_map:
        candidates.append(title_map[title])

    # Fuzzy title match
    if not candidates:
        norm = _normalize(title)
        for key, pwd in title_map.items():
            if _normalize(key) == norm:
                candidates.append(pwd)
                break

    # Month-specific passwords
    if wp_date and len(wp_date) >= 7:
        for pwd in month_map.get(wp_date[:7], []):
            if pwd not in candidates:
                candidates.append(pwd)

    # Global fallback: all passwords from newest month to oldest
    for month in sorted(month_map.keys(), reverse=True):
        for pwd in month_map[month]:
            if pwd not in candidates:
                candidates.append(pwd)

    return candidates


# ---------------------------------------------------------------------------
# WordPress password unlock
# ---------------------------------------------------------------------------

def unlock_post(session: requests.Session, post_url: str, password: str) -> None:
    """POST the password to set the wp-postpass cookie. Skips if already active."""
    global _active_password
    if password == _active_password:
        return
    try:
        session.post(
            WP_POSTPASS_URL,
            data={"post_password": password, "redirect_to": post_url},
            headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
            allow_redirects=True,
        )
        _active_password = password
        log.debug("  Password submitted; cookies: %s", list(session.cookies.keys()))
    except Exception as exc:
        log.warning("  unlock_post error: %s", exc)


def is_still_locked(html: str) -> bool:
    return bool(re.search(r'class="post-password-form"', html))


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&nbsp;", " ").replace("&#8203;", "").replace("&hellip;", "…"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _largest_from_srcset(srcset_str: str) -> str:
    """Parse srcset and return URL of the largest-width entry."""
    entries = []
    for m in re.finditer(r'(\S+)\s+(\d+)w', srcset_str):
        entries.append((int(m.group(2)), m.group(1).split("?")[0]))
    return max(entries, key=lambda x: x[0])[1] if entries else ""


def fetch_post_content(session: requests.Session, url: str) -> dict | None:
    """
    Returns {title, date, text, image_urls} or None if locked / failed.
    """
    html = fetch_html(session, url)
    if not html or is_still_locked(html):
        return None

    # Title (WordPress <h1>)
    title = ""
    for pat in [r'<h1[^>]*class="[^"]*(?:entry|post)-title[^"]*"[^>]*>(.*?)</h1>',
                r'<h1[^>]*>(.*?)</h1>']:
        m = re.search(pat, html, re.I | re.S)
        if m:
            title = _strip_tags(m.group(1))
            break
    title = re.sub(r"^保護中:\s*", "", title).strip()

    # Date
    date = ""
    dm = re.search(r'<time[^>]*datetime="(\d{4}-\d{2}-\d{2})', html, re.I)
    if dm:
        date = dm.group(1)

    # Content — Brite/Colibri theme uses class="colibri-post-content"
    content_html = ""
    cm = re.search(
        r'<div[^>]*class="[^"]*colibri-post-content[^"]*"[^>]*>(.*?)'
        r'(?:</div>\s*</div>|<div[^>]*class="[^"]*(?:comments|related|footer)[^"]*")',
        html, re.I | re.S,
    )
    if cm:
        content_html = cm.group(1)
    else:
        # Broader fallback: everything from the div opening to end
        cm2 = re.search(r'<div[^>]*class="[^"]*colibri-post-content[^"]*"[^>]*>(.*)', html, re.I | re.S)
        if cm2:
            content_html = cm2.group(1)

    # Text from <p> blocks
    paragraphs = [
        _strip_tags(p.group(1)).strip()
        for p in re.finditer(r"<p[^>]*>(.*?)</p>", content_html, re.I | re.S)
    ]
    paragraphs = [p for p in paragraphs if p]

    # Images — prefer largest from srcset, fall back to src
    seen: set[str] = set()
    image_urls: list[str] = []
    for img_m in re.finditer(r'<img\b[^>]+>', content_html, re.I):
        tag = img_m.group(0)
        best = ""
        ss_m = re.search(r'\bsrcset=["\']([^"\']+)["\']', tag, re.I)
        if ss_m:
            best = _largest_from_srcset(ss_m.group(1))
        if not best:
            src_m = re.search(r'\bsrc=["\']([^"\']+)["\']', tag, re.I)
            if src_m:
                best = src_m.group(1).split("?")[0]
        if best and "wp-content/uploads" in best and best not in seen:
            seen.add(best)
            image_urls.append(best)

    return {
        "title": title,
        "date": date,
        "text": "\n\n".join(paragraphs),
        "image_urls": image_urls,
    }


# ---------------------------------------------------------------------------
# Post listing
# ---------------------------------------------------------------------------

def _extract_from_block(block: str) -> tuple[str, str]:
    """Return (title, YYYY-MM) from a single post's HTML block."""
    title = ""
    tm = re.search(
        r'<h4[^>]*class="[^"]*colibri-word-wrap[^"]*"[^>]*>\s*([^<]+?)\s*</h4>',
        block, re.I,
    )
    if tm:
        title = _strip_tags(tm.group(1)).strip()

    # Date from thumbnail upload path: /wp-content/uploads/YYYY/MM/
    month = ""
    dm = re.search(r'/wp-content/uploads/(\d{4})/(\d{2})/', block)
    if dm:
        month = f"{dm.group(1)}-{dm.group(2)}"

    return title, month


def scrape_post_list(session: requests.Session, max_pages: int) -> list[dict]:
    all_posts: dict[str, dict] = {}

    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/?paged={page}"
        log.info("Listing page %d/%d", page, max_pages)
        html = fetch_html(session, url)
        if not html:
            log.warning("  Failed — stopping")
            break

        found = 0

        # Split HTML into per-post blocks by data-href="...?p=NNN" boundaries
        dh_all = list(re.finditer(
            r'data-href=["\'](?:https?://ranagu\.com)?/?\?p=(\d+)["\']', html, re.I
        ))

        for idx, dh_m in enumerate(dh_all):
            pid = dh_m.group(1)
            post_url = f"{BASE_URL}/?p={pid}"
            if post_url in all_posts:
                continue

            block_start = dh_m.start()
            block_end = dh_all[idx + 1].start() if idx + 1 < len(dh_all) else len(html)
            block = html[block_start:block_end]

            title, month = _extract_from_block(block)

            all_posts[post_url] = {
                "url": post_url,
                "title": title,
                "date": month,
                "is_protected": "保護中" in title,
            }
            found += 1

        # Fallback: plain href="?p=NNN" links for posts missed above
        for m in re.finditer(
            r'href=["\'](?:https://ranagu\.com)?/?\?p=(\d+)["\'][^>]*>\s*([^<]{3,200}?)\s*</a>',
            html, re.I,
        ):
            pid, raw_title = m.group(1), m.group(2).strip()
            post_url = f"{BASE_URL}/?p={pid}"
            if post_url in all_posts:
                continue
            if raw_title.lower() in ("もっと読む", "続きを読む", "read more", "edit"):
                continue
            snippet = html[max(0, m.start() - 500):min(len(html), m.start() + 4000)]
            _, month = _extract_from_block(snippet)

            all_posts[post_url] = {
                "url": post_url,
                "title": raw_title,
                "date": month,
                "is_protected": raw_title.startswith("保護中:"),
            }
            found += 1

        log.info("  +%d new posts (total: %d)", found, len(all_posts))
        if found == 0:
            log.info("  No new posts — done with listing")
            break

        time.sleep(0.5)

    return list(all_posts.values())


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def write_markdown(
    folder: Path, title: str, date: str, text: str, img_filenames: list[str]
) -> None:
    lines: list[str] = [f"# {title}\n"]
    if date:
        lines.append(f"**{date}**\n")
    if text:
        lines.append(text + "\n")
    if img_filenames:
        lines.append("## 图片\n")
        for fname in img_filenames:
            lines.append(f"![{fname}](img/{fname})")
    (folder / "README.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_path: Path) -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(
        open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
    )
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    log.addHandler(sh)
    log.addHandler(fh)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Download all posts from ranagu.com")
    parser.add_argument("--out", default="RAN_download")
    parser.add_argument("--pages", type=int, default=9, help="Listing pages to scrape (default: 9)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between posts in seconds")
    parser.add_argument("--fanbox", default=r"P:\fanbox\RAN★", help="Path to fanbox password dir")
    parser.add_argument("--no-password", action="store_true", help="Skip password-protected posts")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(out_dir / "download.log")

    # Resume
    done_file = out_dir / ".downloaded_urls.txt"
    done_urls: set[str] = set()
    if done_file.exists():
        done_urls = set(done_file.read_text(encoding="utf-8").split())
    log.info("Resume: %d posts already done", len(done_urls))

    # Passwords
    title_map, month_map = load_password_map(Path(args.fanbox))

    session = requests.Session()

    # Phase 1: collect posts
    log.info("=== Phase 1: Collecting posts ===")
    posts = scrape_post_list(session, args.pages)
    log.info("Total posts: %d", len(posts))

    # Phase 2: download
    log.info("=== Phase 2: Downloading ===")
    total = len(posts)

    for i, post in enumerate(posts, 1):
        url = post["url"]
        title = post["title"]
        is_protected = post["is_protected"]
        prefix = f"[{i}/{total}]"

        if url in done_urls:
            log.info("%s skip (done): %s", prefix, title)
            continue

        post_date = post.get("date", "")
        log.info("%s %s  [%s]", prefix, title, post_date or "no date")

        # Unlock if needed
        content = None
        if is_protected:
            if args.no_password:
                log.info("  --no-password: skipping")
                continue
            passwords = find_password(title, post_date, title_map, month_map)
            if not passwords:
                log.warning("  No password candidates found — will try anyway")
                content = fetch_post_content(session, url)
            elif len(passwords) == 1:
                unlock_post(session, url, passwords[0])
                content = fetch_post_content(session, url)
            else:
                log.debug("  %d password candidates for this post", len(passwords))
                for pwd in passwords:
                    unlock_post(session, url, pwd)
                    html_check = fetch_html(session, url)
                    if html_check and not is_still_locked(html_check):
                        log.debug("  Unlocked with candidate password")
                        break
                content = fetch_post_content(session, url)
        else:
            content = fetch_post_content(session, url)

        if content is None:
            log.warning("  Could not fetch content (locked or error) — skipping")
            continue

        clean_title = content["title"] or re.sub(r"^保護中:\s*", "", title).strip()
        date = content["date"]

        # Create folder: YYYY-MM-DD_slug
        folder_name = (f"{date}_" if date else "") + slugify(clean_title)
        folder = out_dir / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        img_dir = folder / "img"
        img_dir.mkdir(exist_ok=True)

        # Download images
        img_filenames: list[str] = []
        for j, img_url in enumerate(content["image_urls"], 1):
            ext = url_ext(img_url)
            fname = f"{j:03d}.{ext}"
            if download_image(session, img_url, img_dir / fname):
                img_filenames.append(fname)

        # Write markdown
        write_markdown(folder, clean_title, date, content["text"], img_filenames)
        log.info("  → %s  (%d images)", folder_name, len(img_filenames))

        with done_file.open("a", encoding="utf-8") as f:
            f.write(url + "\n")

        time.sleep(args.delay)

    log.info("Done. Output: %s/", out_dir)


if __name__ == "__main__":
    main()
