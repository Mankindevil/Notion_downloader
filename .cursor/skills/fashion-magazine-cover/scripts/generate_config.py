"""
generate_config — emit cover_config.json from cover_options.html.

Walks each `.cover` in the HTML, collects every `[data-text-key]` element's
text content, and writes a JSON keyed by cover id → text-key → current value.
The user edits that JSON and re-runs export_covers.py to swap text without
touching HTML.

Idempotent: if cover_config.json already exists, the script MERGES — existing
user edits are preserved, only new/missing keys are filled with the HTML
defaults. Keys that disappeared from the HTML are dropped.

Usage (from the working directory containing cover_options.html):
    python generate_config.py
    python generate_config.py --html cover_options.html --out cover_config.json
    python generate_config.py --overwrite        # ignore existing config, full rewrite

The HTML is parsed with the stdlib html.parser — no external deps needed.
"""
import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path


class _CoverTextExtractor(HTMLParser):
    """Pull text content out of [data-text-key] elements grouped by enclosing
    .cover element's id.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        # Stack of (tag, attrs_dict, capture_buffer_or_None).
        self._stack: list[tuple[str, dict, list[str] | None]] = []
        # Stack of cover ids; top is the current cover scope.
        self._cover_stack: list[str] = []
        # Result: { cover_id: [(key, text), ...] }  — list preserves doc order.
        self.collected: dict[str, list[tuple[str, str]]] = {}

    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = {k: v for k, v in attrs_list}
        classes = (attrs.get("class") or "").split()
        is_cover = "cover" in classes and attrs.get("id")
        text_key = attrs.get("data-text-key")

        # Push cover scope BEFORE pushing the element, so the cover element
        # itself is inside its own scope (matches the DOM hierarchy).
        if is_cover:
            self._cover_stack.append(attrs["id"])
            self.collected.setdefault(attrs["id"], [])

        buf: list[str] | None = None
        if text_key and self._cover_stack:
            buf = []
        self._stack.append((tag, attrs, buf))

    def handle_endtag(self, tag: str) -> None:
        # Unwind the stack to the matching opening tag (handles unclosed inner tags).
        while self._stack and self._stack[-1][0] != tag:
            self._stack.pop()
        if not self._stack:
            return
        _, attrs, buf = self._stack.pop()

        if buf is not None and self._cover_stack:
            key = attrs["data-text-key"]
            text = "".join(buf).strip()
            cover_id = self._cover_stack[-1]
            self.collected[cover_id].append((key, text))

        # Pop cover scope AFTER closing the .cover element.
        classes = (attrs.get("class") or "").split()
        if "cover" in classes and attrs.get("id") and self._cover_stack \
                and self._cover_stack[-1] == attrs.get("id"):
            self._cover_stack.pop()

    def handle_data(self, data: str) -> None:
        # Append to every active text-key buffer (handles nesting where a
        # data-text-key element contains plain text mixed with child elements).
        for _, _, buf in self._stack:
            if buf is not None:
                buf.append(data)


def extract_from_html(html_path: Path) -> dict[str, dict[str, str]]:
    """Return { cover_id: { key: text, ... } } in document order."""
    html = html_path.read_text(encoding="utf-8")
    parser = _CoverTextExtractor()
    parser.feed(html)
    parser.close()
    out: dict[str, dict[str, str]] = {}
    for cover_id, pairs in parser.collected.items():
        # If the same key appears twice (rare), the last one wins. Preserve order.
        d: dict[str, str] = {}
        for k, v in pairs:
            d[k] = v
        out[cover_id] = d
    return out


def merge_configs(
    fresh: dict[str, dict[str, str]],
    existing: dict[str, dict[str, str]] | None,
) -> dict[str, dict[str, str]]:
    """Return fresh keys filled from existing where present, in fresh's order.

    Keys not in `fresh` (i.e. removed from HTML) are dropped.
    Covers in `fresh` not in `existing` get the fresh defaults.
    """
    if not existing:
        return fresh
    merged: dict[str, dict[str, str]] = {}
    for cover_id, fields in fresh.items():
        existing_cover = existing.get(cover_id, {}) if isinstance(existing, dict) else {}
        new_cover: dict[str, str] = {}
        for key, default_text in fields.items():
            if isinstance(existing_cover, dict) and key in existing_cover:
                new_cover[key] = existing_cover[key]
            else:
                new_cover[key] = default_text
        merged[cover_id] = new_cover
    return merged


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--html", default="cover_options.html",
                    help="Source HTML to scan (default: cover_options.html)")
    ap.add_argument("--out", default="cover_config.json",
                    help="Target JSON path (default: cover_config.json)")
    ap.add_argument("--overwrite", action="store_true",
                    help="Replace existing config wholesale instead of merging.")
    args = ap.parse_args()

    html_path = Path(args.html)
    if not html_path.exists():
        sys.exit(f"error: {html_path} not found")

    fresh = extract_from_html(html_path)
    if not fresh:
        sys.exit("error: no .cover elements with data-text-key attributes found "
                 f"in {html_path}")

    out_path = Path(args.out)
    existing: dict | None = None
    if out_path.exists() and not args.overwrite:
        try:
            with out_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception as e:
            print(f"warning: failed to read existing {out_path} ({e}); rewriting",
                  file=sys.stderr)
            existing = None

    merged = merge_configs(fresh, existing)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write("\n")

    total_keys = sum(len(v) for v in merged.values())
    action = "wrote" if existing is None else "merged"
    print(f"{action} {out_path}  ({len(merged)} covers, {total_keys} text fields)")


if __name__ == "__main__":
    main()
