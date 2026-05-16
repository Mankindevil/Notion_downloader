# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Always use `.venv\Scripts\python.exe` (never system `python`) — a `.venv` is present in the repo root.

```powershell
.\.venv\Scripts\python.exe script.py --flags
.\.venv\Scripts\pip.exe install package
```

No test suite exists. Testing is done by running the scripts against live URLs and checking output.

## Scrapers

### notion_downloader.py

Selenium-based scraper for a Notion gallery page. Single-file, 1,191 lines.

```powershell
# dependency
.\.venv\Scripts\pip.exe install selenium   # also requires Chrome/Chromium

.\.venv\Scripts\python.exe notion_downloader.py
.\.venv\Scripts\python.exe notion_downloader.py --url "https://your.notion.site/…" --out my_gallery
.\.venv\Scripts\python.exe notion_downloader.py --no-headless   # show browser for debugging
```

**Execution path:** `main()` → `scrape_gallery()` scrolls the page and collects all gallery cards → per-card `scrape_subpage()` extracts title/date/images → `write_entry_readme()` → global `README.md` + `index.html`.

**Key functions**

| Function | Notes |
|---|---|
| `scrape_gallery()` | Year-group detection by comparing card Y-positions to header Y-positions in DOM |
| `scrape_subpage()` | Five-strategy fallback chain for date: time elements → CSS rows → XPath → JS DOM → raw source |
| `parse_notion_date()` | 20+ format variations: ISO, English, Chinese, Japanese, Korean, relative ("3天前") |
| `download()` | `urllib` with 3-retry exponential backoff; reuse this pattern in new scripts |
| `slugify()` | Strips `\/*?:"<>|`, collapses whitespace, caps at 60 chars — safe on Windows |

Output: `notion_download/{year}/{date}_{slug}/README.md` + `covers/` + `index.html`.

---

### ape_insight_downloader.py

HTTP scraper (no browser) for a Shop-Pro e-commerce site. Single-file.

```powershell
# dependency
.\.venv\Scripts\pip.exe install requests

.\.venv\Scripts\python.exe ape_insight_downloader.py              # all 86 pages
.\.venv\Scripts\python.exe ape_insight_downloader.py --pages 1    # smoke test
.\.venv\Scripts\python.exe ape_insight_downloader.py --no-translate
```

**Execution path:** Phase 1 — iterate listing pages 1–86 collecting `{pid, name, thumb_url}` dicts → Phase 2 — for each product POST to bypass age gate, extract image URLs, translate name, download images, append pid to `.downloaded_pids.txt` (resume support).

**Key design decisions**

- **Age gate bypass**: product pages return a 7 KB gate page on GET; must POST `restricted_age_agree=1` to get the full 69 KB product page. Implemented in `fetch_product_html()`.
- **Encoding**: site is EUC-JP. `_decode_response()` detects charset from the `Content-Type` header and `<meta charset>` tag before falling back to chardet.
- **Image filter**: CDN URLs containing `/product/` and no `_th.` suffix are full-size product images. Logo/CSS/favicon URLs lack `/product/` and are excluded in `extract_cdn_images()`.
- **Translation**: Google Translate unofficial JSON endpoint (`translate.googleapis.com/translate_a/single?client=gtx`), result cached in `_translation_cache` dict, 0.5 s delay per call.
- **stdout on Windows**: stream log handler opened with `encoding="utf-8"` explicitly to avoid GBK encoding errors on CJK output.

Output: `ape_insight/{zh_name}_{pid}/001.jpg …` + `index.md`.
