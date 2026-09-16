# Web Scrapers

Two standalone Python scrapers for archiving web content locally.

---

## notion_downloader.py

Downloads a Notion gallery page — metadata, cover images, sub-page images — and generates a static markdown + HTML archive organized by year.

**Dependencies**
```
pip install selenium
```
Requires Chrome/Chromium installed on the system.

**Usage**
```bash
python notion_downloader.py                                      # defaults to hightway420.notion.site
python notion_downloader.py --url "https://your.notion.site/…"
python notion_downloader.py --out my_gallery
python notion_downloader.py --no-headless    # show browser window
python notion_downloader.py --log custom.log
```

**Output**
```
notion_download/
├── 2026/entry-slug/README.md   # per-entry metadata + images
├── covers/                     # card cover thumbnails
├── README.md                   # global index by year
└── index.html                  # dark-themed HTML gallery grid
```

---

## ape_insight_downloader.py

Downloads all product images from [shop.ape-insight.jp](https://shop.ape-insight.jp/?mode=cate&cbid=2241192&csid=5&sort=n) (~1026 products across 86 pages), organized into per-product folders with Japanese names auto-translated to Chinese.

**Dependencies**
```
pip install requests
```

**Usage**
```bash
python ape_insight_downloader.py                  # full run, all 86 pages
python ape_insight_downloader.py --pages 2        # first 2 listing pages only
python ape_insight_downloader.py --out my_dir     # custom output folder
python ape_insight_downloader.py --no-translate   # keep Japanese folder names
python ape_insight_downloader.py --delay 2.0      # slower request pacing
```

Supports resume: already-downloaded products are tracked in `.downloaded_pids.txt` and skipped on re-run.

**Output**
```
ape_insight/
├── 日刊女孩时间停止列车_读野堇_1_6_比例涂装完成品_191824854/
│   ├── 001.jpg
│   ├── 002.jpg
│   └── …
├── index.md                    # table of all products with zh/ja names
├── download.log
└── .downloaded_pids.txt        # resume checkpoint
```

# Fanbox MEGA update sync

`fanbox_mega_sync.py` scans all text exports below `FANBOX_SOURCE_DIR`. For
duplicate exports such as `links-123.txt`, `links-123 (1).txt`, and
`links-123 (2).txt`, it first selects the newest document snapshot, then picks
the highest `UpdateN` MEGA file link inside that snapshot. It recursively checks
`MEGA_TARGET_DIR`; matching files are
verified using the content MAC embedded in the public MEGA link, and only
missing files are downloaded. Incomplete downloads use a resumable `.part`
file and are renamed into place only after integrity verification.

Configure local paths in `.env`, then run with the repository virtual
environment:

```powershell
.\.venv\Scripts\python.exe fanbox_mega_sync.py --dry-run
.\.venv\Scripts\python.exe fanbox_mega_sync.py
```

Every post is checked by default. `--recent-days 30` is available only when a
temporary date filter is wanted. If a same-name file has the wrong size or
MEGA content MAC, the script fails closed and does not overwrite it.
