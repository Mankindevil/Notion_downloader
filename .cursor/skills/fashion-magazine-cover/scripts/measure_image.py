"""
measure_image — tiny helper for the cover-author workflow.

Prints the input image's dimensions and a suggested capped --cw/--ch pair
to paste into the .cover element's inline style. The cap (2400px on the
longest side by default) keeps Playwright viewports manageable while
giving export_covers.py less work to upscale to the 4K (3840px) default.

Usage:
    python measure_image.py path/to/subject.jpg
    python measure_image.py path/to/subject.jpg --max 1860

Output:
    1398 x 3839  (portrait, 0.364 ratio)
    Suggested:  --cw: 874; --ch: 2400;
"""
import argparse
import sys
from PIL import Image


def main() -> None:
    ap = argparse.ArgumentParser(description="Print image dims + suggested capped CSS vars.")
    ap.add_argument("path", help="Path to the input image")
    ap.add_argument("--max", type=int, default=2400,
                    help="Cap on longest side in CSS pixels (default: 2400). "
                         "export_covers.py auto-upscales these to 4K (3840px).")
    args = ap.parse_args()

    try:
        with Image.open(args.path) as img:
            w, h = img.size
    except Exception as e:
        sys.exit(f"error opening {args.path}: {e}")

    ratio = w / h
    if abs(ratio - 1) < 0.05:
        orient = "square"
    elif ratio > 1:
        orient = "landscape"
    else:
        orient = "portrait"

    # Cap longest side, keep aspect.
    if max(w, h) > args.max:
        scale = args.max / max(w, h)
        cw = int(w * scale)
        ch = int(h * scale)
    else:
        cw, ch = w, h

    print(f"{w} x {h}  ({orient}, {ratio:.3f} ratio)")
    print(f"Suggested:  --cw: {cw}; --ch: {ch};")


if __name__ == "__main__":
    main()
