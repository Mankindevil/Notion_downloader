# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

Always use `.venv\Scripts\python.exe` (never system `python`) — a `.venv` is present in the repo root.

```powershell
.\.venv\Scripts\python.exe script.py --flags
.\.venv\Scripts\pip.exe install package
```

No test suite exists. Testing is done by running the scripts against live URLs and checking output.

## Repository layout

| Path | What it is |
|---|---|
| `notion_downloader.py`, `ape_insight_downloader.py`, `ran_downloader.py` | The three scrapers — the maintained code in this repo |
| `layer_split/` | Illustration → depth-layer PSD pipeline for Live2D |
| `art_title_maker/`, `fashion_magazine_cover/` | **Skill workspaces** — generated artifacts of the custom design skills, not tools (see below) |
| `.cursor/skills/` | Source of the two custom design skills (art-title-maker, fashion-magazine-cover) |
| `.agents/skills/` | Installed lark-* skills, managed via `skills-lock.json` — don't hand-edit |
| `lark/` | One-off Feishu Base maintenance scripts (shell out to `lark-cli`) |
| `notion_download/`, `ape_insight/`, `RAN_download/`, `Takeout/`, `收集截图/`, `*.xlsx` | Output/data — gitignored |

## Scrapers

### notion_downloader.py

CloakBrowser/Playwright-based scraper for a Notion gallery page (clicks the 中文畫廊 tab). Single-file. CloakBrowser (a stealth Playwright drop-in) keeps Cloudflare / FingerprintJS / reCAPTCHA v3 from blocking the scrape; persistent profile under `<out>/.cloak-profile/` keeps cookies between runs. `cloakbrowser` is the only third-party dependency (auto-downloads the ~200 MB stealth Chromium on first run); the script hard-exits if it's missing.

```powershell
.\.venv\Scripts\python.exe notion_downloader.py
.\.venv\Scripts\python.exe notion_downloader.py --url "https://your.notion.site/…" --out my_gallery
.\.venv\Scripts\python.exe notion_downloader.py --skip-downloaded    # skip posts marked complete in .manifest.json
.\.venv\Scripts\python.exe notion_downloader.py --skip-collections  # skip sub-pages containing a collection-view block
.\.venv\Scripts\python.exe notion_downloader.py --reverify           # repair mode: re-scrape downloaded posts, refetch images, purge junk thumbnails, rebuild index
.\.venv\Scripts\python.exe notion_downloader.py --reverify --force   # re-check posts already marked reverified
.\.venv\Scripts\python.exe notion_downloader.py --no-headless        # show browser for debugging
.\.venv\Scripts\python.exe notion_downloader.py --profile-dir ./pf --log run.log
```

**Execution path:** `main()` → `scrape_gallery()` scrolls the page + clicks load-more buttons → `get_cards_with_years()` collects cards and assigns years by comparing card Y-positions to year-header Y-positions in the DOM → per-card `scrape_subpage()` extracts title/date/images → `write_markdown()` (per-entry README) → `write_index_md()` + `build_html()` (global `README.md` + `index.html`). With `--reverify`: `reverify_existing()` builds the worklist from on-disk per-entry `README.md` files instead, re-scrapes each post, then `rebuild_index_from_disk()`.

**Key mechanics**

| What | Notes |
|---|---|
| Manifest | `<out>/.manifest.json` maps href → `{local_path, title, date, images, complete, reverified}`; saved after **every** post (crash-resumable); migrates the legacy `.downloaded_hrefs.txt` once. `complete` is true only when all images downloaded, so `--skip-downloaded` retries partial posts. If a post's recomputed folder name differs (date parsing improved), the old folder is renamed instead of duplicated. |
| Image collection | Reads the resolved `im.currentSrc \|\| im.src` JS property, **not** the `src` attribute — Notion serves relative `/image/...` attributes and an attribute-based `startswith('http')` test silently drops them (the historical bug `--reverify` repairs). Junk filter drops `_JUNK_IMG_HOSTS` (gstatic, notion.so/images, …) and true icons < 30 px. |
| Reverify safety | Only stale files < 20 KB (`_JUNK_MAX_BYTES`) absent from the fresh download set are deleted, so real artwork survives; pages yielding zero images are left untouched. |
| `scrape_subpage()` | Six-strategy date fallback chain: `<time>` elements → JS DOM walk over property rows → CSS rows → XPath → JS bulk extraction → raw-source regex |
| `parse_notion_date()` | 20+ format variations: ISO, English, Chinese, Japanese, Korean, relative ("3天前"), and bare weekday names ("星期一" → most recent Monday) |
| `download()` | `urllib` with Chrome UA + notion.so Referer, 3-retry exponential backoff, no-op if dest exists; reuse this pattern in new scripts |
| `slugify()` | Replaces `\/*?:"<>\|` and whitespace runs with `_`, caps at 60 chars — safe on Windows |

Output: `notion_download/{year}/{date}_{slug}/README.md` + `covers/` + `index.html` + `.manifest.json`.

---

### ape_insight_downloader.py

HTTP scraper (no browser) for a Shop-Pro e-commerce site. Single-file; `requests` is the only dependency.

```powershell
.\.venv\Scripts\python.exe ape_insight_downloader.py              # all pages (--pages 0 = all, capped at 86)
.\.venv\Scripts\python.exe ape_insight_downloader.py --pages 1    # smoke test
.\.venv\Scripts\python.exe ape_insight_downloader.py --no-translate --out my_dir --delay 2.0
```

**Execution path:** Phase 1 — iterate the hardcoded category listing URL (`?mode=cate&cbid=2241192&csid=5&sort=n&page={n}`) collecting `{pid, name, thumb_url}` dicts, early-stopping on an empty page or zero new pids → Phase 2 — per product: translate name → create folder → POST to bypass age gate and extract image URLs → download images → append pid to `.downloaded_pids.txt` (resume support).

**Key design decisions**

- **Age gate bypass**: product pages return a 7 KB gate page on GET; must POST `restricted_age_agree=1` to get the full 69 KB product page. Implemented in `fetch_product_html()`.
- **Encoding**: site is EUC-JP. `_decode_response()` detects charset from the `Content-Type` header and `<meta charset>` tag before falling back to requests' `apparent_encoding`.
- **Image filter**: CDN URLs containing `/product/` and no `_th.` suffix are full-size product images. Fallbacks: strip `_th` from thumbnail URLs when only thumbs exist; construct the full-size URL from the listing thumbnail as a last resort.
- **Translation**: Google Translate unofficial JSON endpoint (`translate.googleapis.com/translate_a/single?client=gtx`), cached in `_translation_cache`, 0.5 s delay per call; a failed translation caches the Japanese name.
- **stdout on Windows**: stream log handler opened with `encoding="utf-8"` explicitly to avoid GBK encoding errors on CJK output.
- **Caveat**: `index.md` is rewritten each run with only the products processed in that run — resume runs lose earlier rows.

Output: `ape_insight/{zh_name}_{pid}/001.jpg …` + `index.md` + `download.log` + `.downloaded_pids.txt`.

---

### ran_downloader.py

HTTP scraper (`requests`, no browser) for ranagu.com — a Japanese WordPress (Colibri theme) art site whose posts are individually password-protected ("保護中:" titles).

```powershell
.\.venv\Scripts\python.exe ran_downloader.py                        # listing pages 1–9 (default)
.\.venv\Scripts\python.exe ran_downloader.py --pages 1 --delay 0.5  # smoke test
.\.venv\Scripts\python.exe ran_downloader.py --fanbox "P:\fanbox\RAN★"  # password source dir
.\.venv\Scripts\python.exe ran_downloader.py --no-password          # skip protected posts entirely
```

**Execution path:** Phase 1 — `scrape_post_list()` iterates `?paged={N}`, splitting listing HTML at `data-href="?p=NNN"` blocks → Phase 2 — per post: `find_password()` → `unlock_post()` POSTs to `wp-login.php?action=postpass` (sets the `wp-postpass` session cookie) → `fetch_post_content()` → download images → `README.md` → append URL to `.downloaded_urls.txt` (resume support).

**Key design decisions**

- **Passwords come from the local filesystem, not the site**: `load_password_map()` walks the `--fanbox` dir for `YYYY-MM-DD-<title>` folders and extracts 閲覧コード lines from `links-*.txt`, rejecting reference-pointer lines and anything containing CJK (real passwords are short ASCII). Candidates are tried best-first: exact title match → fuzzy title → same-month passwords → all known passwords newest-first.
- **`_active_password`** caches which password the session cookie currently holds, so `unlock_post()` no-ops on repeats.
- **Images**: prefers the largest `srcset` entry, keeps only `wp-content/uploads` URLs.
- `slugify()` caps at 80 chars here (60 in notion_downloader).
- Folder gets a `{YYYY-MM-DD}_` prefix only when a `<time datetime>` is found on the post — in practice it rarely fires, so output folders are bare slugs.

Output: `RAN_download/{slug}/README.md` + `img/001.ext …` + `download.log` + `.downloaded_urls.txt`.

---

## layer_split/

Splits one anime illustration (`フリーレン-135462873_p30.png`) into 5 mutually exclusive depth layers (sky/cloud/body/hair/face) and packs them into a PSD for Live2D Cubism import. All paths are cwd-relative — run from inside `layer_split\`.

```powershell
cd layer_split
..\.venv\Scripts\python.exe split_layers.py    # --src / --out layers_output / --model isnet-anime|u2net|isnet-general-use
..\.venv\Scripts\python.exe build_psd.py       # no flags; layers_output\ → frieren_live2d.psd
# layered_preview.html / live2d_preview.html — open directly in a browser for parallax / idle-animation preview
```

- Segmentation: `rembg` (isnet-anime ONNX model, auto-downloaded on first run) for the character alpha, then hand-tuned color thresholds for cloud/face/hair — the skin-seed constants are tuned to this specific artwork and need retuning for any other image.
- PSD writing uses **pytoshop** (not psd-tools); its `size` arg is actually `(width, height)` despite the docstring, and zip compression is used because pytoshop's RLE codec is broken on Windows.
- Layers are passed top-of-stack-first (face first) so Live2D's back-to-front draw order imports correctly.

## Skill workspaces (generated artifacts — do not refactor)

`art_title_maker/` and `fashion_magazine_cover/` are per-character **output workspaces** of the two custom design skills in `.cursor/skills/`. The `.py`/`.html` files inside them are frozen one-off session helpers, several with stale hardcoded paths that no longer run (e.g. `fashion_magazine_cover/chloe/cover_role_special/*.py` reference a since-moved `chloe_new/` dir; `art_title_maker/generate_4k_png.py` needs a deleted `style6_4k.html`). For a new title or cover job, invoke the skill — it creates a fresh per-character dir — instead of reusing or "fixing" workspace scripts.

Canonical entry points live with the skills:

- `.cursor/skills/art-title-maker/scripts/export_titles.py` — Playwright transparent-PNG export. Run with cwd = the dir containing `title_options.html`; flags `--html/--out-prefix/--scale/--width/--height/--dpi`.
- `.cursor/skills/fashion-magazine-cover/scripts/export_covers.py` — layered export per variant (`<prefix>_<id>_background.png` / `_effects.png` / `_artwork.png` / `_final.jpg`); auto-reads `cover_config.json` in cwd so covers can be re-texted without touching HTML.

`_verify_fmc/` in the repo root is an empty leftover verification dir — safe to ignore or delete.

## lark/

One-off Feishu Base maintenance scripts that shell out to `lark-cli` (per user preference — no OpenAPI wrappers). `migrate_date_field.py` is the reusable one: `argv = BASE_TOKEN TABLE_ID SRC_FIELD YM_FIELD DAY_FIELD`, splits Chinese dates like `2026年5月13日` into year-month + day fields via 500-record `+record-batch-update` chunks (requires 4-digit years; `26年5月13日` is skipped). `show_dates.py` and the `.json` files are dead debug artifacts.
