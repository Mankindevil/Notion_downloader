"""Build a layered PSD from the 5 layer PNGs for Live2D Cubism Editor import.

Layer naming follows Cubism conventions: leaf parts named explicitly, grouped
under folders so the model tree is tidy after import.
"""
from __future__ import annotations
from pathlib import Path

import numpy as np
from PIL import Image
from pytoshop import enums
from pytoshop.user import nested_layers


def png_to_layer(path: Path, name: str) -> nested_layers.Image:
    """Build a pytoshop Image layer from an RGBA PNG, including its alpha."""
    im = Image.open(path).convert("RGBA")
    a = np.array(im)
    # pytoshop expects per-channel 2D uint8 arrays
    return nested_layers.Image(
        name=name,
        visible=True,
        opacity=255,
        color_mode=enums.ColorMode.rgb,
        channels={
            0: a[:, :, 0],         # R
            1: a[:, :, 1],         # G
            2: a[:, :, 2],         # B
            -1: a[:, :, 3],        # alpha
        },
    )


def build(src_dir: Path, out_psd: Path) -> None:
    # Inspect canvas size from any layer
    sample = Image.open(src_dir / "1_sky.png")
    W, H = sample.size

    # Order matters: pytoshop expects layers top-of-stack first.
    # In Live2D, drawing order is back-to-front, so the topmost layer in
    # Photoshop should be the FRONT-most layer (face). We pass them in that order.
    spec = [
        ("face",  "5_face.png"),
        ("hair",  "4_hair.png"),
        ("body",  "3_body.png"),
        ("cloud", "2_cloud.png"),
        ("sky",   "1_sky.png"),
    ]

    parts = [png_to_layer(src_dir / fn, name) for name, fn in spec]
    character = nested_layers.Group(
        name="character", visible=True, opacity=255,
        layers=[p for p in parts if p.name in ("face", "hair", "body")],
        closed=False,
    )
    backdrop = nested_layers.Group(
        name="backdrop", visible=True, opacity=255,
        layers=[p for p in parts if p.name in ("cloud", "sky")],
        closed=False,
    )

    psd = nested_layers.nested_layers_to_psd(
        [character, backdrop],
        color_mode=enums.ColorMode.rgb,
        version=enums.Version.psd,  # standard PSD (not PSB)
        size=(W, H),  # despite the docstring saying (height, width), code does (width, height)
        compression=enums.Compression.zip,  # pytoshop's RLE codec is broken on win
    )

    with open(out_psd, "wb") as f:
        psd.write(f)
    print(f"[psd] wrote {out_psd}  ({out_psd.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build(Path("layers_output"), Path("frieren_live2d.psd"))
