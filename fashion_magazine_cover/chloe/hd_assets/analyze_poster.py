"""Extract element bounding boxes from reference poster PNG and print base-coordinate positions."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

REF = Path(r"o:\Coding\Claude\微信图片_20260524152203_2639_210.png")
NEW = Path(__file__).parent / "poster_overlay_4k.png"
BASE_W, BASE_H = 1024, 761


def load(path):
    return np.array(Image.open(path).convert("RGBA"))


def to_base(x, y, w, h, img_w, img_h):
    sx, sy = BASE_W / img_w, BASE_H / img_h
    return x * sx, y * sy, w * sx, h * sy


def blobs(a, mask, min_px=400):
    lbl, n = ndimage.label(mask)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        if len(xs) < min_px:
            continue
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
        out.append((len(xs), x0, y0, x1, y1))
    out.sort(reverse=True)
    return out


def analyze(path, label):
    a = load(path)
    h, w = a.shape[:2]
    al = a[:, :, 3]
    rgb = a[:, :, :3]
    opaque = al > 128

    orange = opaque & (rgb[:, :, 0] > 200) & (rgb[:, :, 1] > 100) & (rgb[:, :, 1] < 180) & (rgb[:, :, 2] < 80)
    white = opaque & (rgb[:, :, 0] > 200) & (rgb[:, :, 1] > 200) & (rgb[:, :, 2] > 200)
    black = opaque & (rgb.sum(axis=2) < 80)

    print(f"\n=== {label} ({w}x{h}) ===")
    for name, mask in [("orange", orange), ("white", white), ("black", black)]:
        items = blobs(a, mask)
        print(f"  {name} top blobs:")
        for cnt, x0, y0, x1, y1 in items[:15]:
            bx, by, bw, bh = to_base(x0, y0, x1 - x0, y1 - y0, w, h)
            print(f"    ({bx:.0f},{by:.0f})-({bx+bw:.0f},{by+bh:.0f})  {bw:.0f}x{bh:.0f}  px={cnt}")


if __name__ == "__main__":
    analyze(REF, "ref")
    if NEW.exists():
        analyze(NEW, "new")
