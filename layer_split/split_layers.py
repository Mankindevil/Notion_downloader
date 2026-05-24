"""
Split the Frieren artwork into 5 depth layers for a paper-craft / parallax effect.

Layers (back -> front):
  1_sky    : pure blue sky (no clouds)
  2_cloud  : all clouds in the sky
  3_body   : character body / clothes / cape
  4_hair   : flowing light-blue hair (around and behind the face)
  5_face   : face area (skin + eyes + mouth + ears)

Strategy:
  - rembg (isnet-anime) gives a clean character alpha.
  - Background is split by lightness: bright pixels = clouds, the rest = sky.
  - Within the character mask, skin color is detected to find the face;
    morphological closing fills the eye/mouth holes so the whole face
    region travels on the top layer.
  - Remaining character pixels are split into hair (cool/light) and body.

Every original pixel ends up in exactly one layer, so stacking the
five PNGs reproduces the original image.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove
from scipy.ndimage import binary_fill_holes, label


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    """Binary dilation using PIL MaxFilter (odd kernel)."""
    k = max(3, radius * 2 + 1)
    img = Image.fromarray((mask.astype(np.uint8)) * 255)
    img = img.filter(ImageFilter.MaxFilter(k))
    return np.array(img) > 128


def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    k = max(3, radius * 2 + 1)
    img = Image.fromarray((mask.astype(np.uint8)) * 255)
    img = img.filter(ImageFilter.MinFilter(k))
    return np.array(img) > 128


def _close(mask: np.ndarray, radius: int) -> np.ndarray:
    return _erode(_dilate(mask, radius), radius)


def split(src: Path, out_dir: Path, model: str = "isnet-anime") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGBA")
    W, H = img.size
    print(f"[load] {src.name}  {W}x{H}")

    # --- rembg: character alpha ---
    print(f"[rembg] using model: {model}")
    session = new_session(model)
    cut = remove(img, session=session, post_process_mask=True)
    char_alpha = np.array(cut)[:, :, 3]

    # Slight blur on the rembg edge to avoid jaggies
    char_alpha = np.array(
        Image.fromarray(char_alpha).filter(ImageFilter.GaussianBlur(0.6))
    )
    is_char = char_alpha > 96
    is_bg = ~is_char

    rgb = np.array(img.convert("RGB"))
    R = rgb[:, :, 0].astype(int)
    G = rgb[:, :, 1].astype(int)
    B = rgb[:, :, 2].astype(int)
    V = np.maximum(np.maximum(R, G), B)
    Mn = np.minimum(np.minimum(R, G), B)
    chroma = V - Mn

    # --- background: sky vs cloud ---
    # cloud = bright AND low chroma (whitish). Pure blue sky has high chroma (~180)
    # even when bright (V>240), so chroma is the discriminator.
    is_cloud = is_bg & (V >= 200) & (chroma <= 55)
    # close + open: fill cloud holes and remove tiny isolated white specks
    is_cloud = _close(is_cloud, 2)
    is_cloud = _dilate(is_cloud, 1)  # slight grow so edges go to cloud not sky
    is_cloud &= is_bg
    is_sky = is_bg & ~is_cloud

    # --- character: face / hair / body ---
    # This illustration's skin is desaturated grey-lavender (NOT warm pink):
    #   typical face pixel ~ (170, 168, 195) — R≈G, B slightly higher, mid chroma.
    # Tight skin-seed condition, then connected-components to find the face blob.
    skin_seed = (
        is_char
        & (R >= 140) & (R <= 220)
        & (G >= 140) & (G <= 225)
        & (B >= 155) & (B <= 250)
        & (np.abs(R - G) <= 15)
        & ((B - R) >= -5) & ((B - R) <= 40)   # B slightly above R, not way above
        & (chroma <= 75)
        & (V >= 160)
    )
    # Clean tiny noise specks before CC labeling
    skin_seed = _erode(skin_seed, 2)

    labels, n = label(skin_seed)
    if n > 0:
        # Pick the largest connected component as the face
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0  # background
        face_label = sizes.argmax()
        face_core = labels == face_label
    else:
        face_core = np.zeros_like(is_char, dtype=bool)

    # Dilate the face core so eyes/eyebrows/nose/mouth inside the face join it,
    # then close any internal holes. Kernel scaled to image.
    grow_r = max(10, min(W, H) // 60)
    face_region = _dilate(face_core, grow_r)
    face_region = _close(face_region, grow_r // 2)
    is_face = face_region & is_char

    # Hair candidate: light pixels in char (V>=195) outside face.
    # The cape has bright highlights with the same brightness, so we additionally
    # require connectedness to the face region — real hair is attached to the head.
    hair_candidate = is_char & ~is_face & (V >= 195)
    # Close internal dark hair outlines so a single strand becomes one blob
    hair_candidate = _close(hair_candidate, max(3, min(W, H) // 250))

    # Keep only components touching the face region (dilated). Isolated bright
    # patches in the cape go to body.
    face_neighborhood = _dilate(is_face, max(8, min(W, H) // 100))
    h_labels, h_n = label(hair_candidate)
    keep = np.zeros(h_n + 1, dtype=bool)
    if h_n > 0:
        # For each label, mark keep if it intersects face neighborhood
        # Use bincount on labels masked by face_neighborhood
        touching = np.bincount(
            h_labels[face_neighborhood].ravel(),
            minlength=h_n + 1,
        )
        keep = touching > 0
        keep[0] = False
    is_hair = keep[h_labels]
    # Fill internal holes (dark line-art inside a hair strand) so the strand
    # travels as one piece; restrict to character.
    is_hair = binary_fill_holes(is_hair) & is_char & ~is_face

    # Body: everything else inside the character (darker clothes, cape, etc.)
    is_body = is_char & ~is_face & ~is_hair

    # Sanity: every char pixel goes to exactly one of face/hair/body
    # (no overlap by construction)

    # --- write layers ---
    layers = [
        ("1_sky", is_sky),
        ("2_cloud", is_cloud),
        ("3_body", is_body),
        ("4_hair", is_hair),
        ("5_face", is_face),
    ]

    for name, mask in layers:
        rgba = np.zeros((H, W, 4), dtype=np.uint8)
        rgba[..., :3] = rgb
        rgba[..., 3] = (mask.astype(np.uint8)) * 255
        # Feather alpha edge slightly for smooth stacking
        alpha_pil = Image.fromarray(rgba[..., 3]).filter(
            ImageFilter.GaussianBlur(0.7)
        )
        rgba[..., 3] = np.array(alpha_pil)
        Image.fromarray(rgba, "RGBA").save(out_dir / f"{name}.png", optimize=True)
        pct = 100.0 * mask.sum() / (W * H)
        print(f"[save] {name}.png  {mask.sum():>10,} px  ({pct:5.1f}%)")

    # Coverage report
    total = is_sky | is_cloud | is_body | is_hair | is_face
    missed = ~total
    if missed.any():
        print(f"[warn] {missed.sum()} pixels unassigned")
    else:
        print("[ok] all pixels assigned to exactly one layer")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="フリーレン-135462873_p30.png")
    ap.add_argument("--out", default="layers_output")
    ap.add_argument("--model", default="isnet-anime",
                    help="rembg model (isnet-anime|u2net|isnet-general-use)")
    args = ap.parse_args()
    split(Path(args.src), Path(args.out), args.model)


if __name__ == "__main__":
    main()
