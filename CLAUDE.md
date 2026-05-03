# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Selenium-based scraper that downloads Notion gallery pages — extracting metadata, cover images, sub-page content, and generating a static markdown + HTML gallery organized by year.

## Running the Scraper

```bash
# Install the only external dependency
pip install selenium

# Run with defaults (targets hightway420.notion.site)
python notion_downloader.py

# Common flags
python notion_downloader.py --url "https://your.notion.site/..." --out my_gallery
python notion_downloader.py --no-headless   # show Chrome window for debugging
python notion_downloader.py --log custom.log
```

Requires Chrome/Chromium installed on the system. No test suite exists; testing is done manually by running against a live Notion URL.

## Architecture

Everything lives in `notion_downloader.py` (1,191 lines). The main execution path:

1. `main()` → `scrape_gallery()` — loads the Notion page, clicks the "中文畫廊" tab, scrolls and triggers all "Load More" buttons, then collects all gallery cards
2. For each card, `scrape_subpage()` extracts title, date, properties, text blocks, and images
3. `write_entry_readme()` generates per-entry `README.md` with metadata table + image gallery
4. `main()` then writes a global `notion_download/README.md` index and `index.html` gallery

### Key functions

| Function | Purpose |
|---|---|
| `scrape_gallery()` | JS-based card extraction with year-group detection from visual Y-position |
| `scrape_subpage()` | Five-strategy fallback chain for date extraction (time elements → CSS rows → XPath → JS DOM → raw page source) |
| `parse_notion_date()` | Parses 20+ date format variations (ISO, English, Chinese, Japanese, Korean, relative) |
| `download()` | HTTP downloader with 3-attempt retry + exponential backoff |
| `slugify()` | Sanitizes strings into safe filesystem names |

### Output structure

```
notion_download/
├── 2026/entry-slug/README.md    # per-entry metadata + images
├── 2025/...
├── covers/                      # card cover images
├── README.md                    # auto-generated global index by year
└── index.html                   # dark-themed HTML gallery grid
```

### Notion-specific details

- Gallery year groups are detected by comparing card Y-positions to year-header Y-positions in the DOM
- Cover images are extracted from both `<img>` tags and CSS `background-image` properties
- Property names are matched against a hardcoded list in English, Chinese, and Japanese
- "Load More" button text is matched in 5 languages
- Anti-detection Chrome options are applied to avoid bot blocking
