from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


def _sample_bg_color(img: Image.Image) -> tuple[int, int, int]:
    # Sample from top-right area, which is mostly flat pink background.
    w, h = img.size
    region = img.crop((int(w * 0.78), int(h * 0.04), int(w * 0.96), int(h * 0.22)))
    avg = region.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    return (avg[0], avg[1], avg[2])


def sanitize_image(src: Path, dst: Path) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    bg = _sample_bg_color(img)

    draw = ImageDraw.Draw(img, "RGBA")

    # 1) Remove problematic top-left logo/text block.
    draw.rounded_rectangle(
        (
            int(w * 0.03),
            int(h * 0.04),
            int(w * 0.45),
            int(h * 0.35),
        ),
        radius=int(w * 0.03),
        fill=(*bg, 245),
    )

    # 2) Add a modest stylized dress shape to fully cover central explicit area.
    dress_top_y = int(h * 0.43)
    dress_bottom_y = int(h * 0.82)
    dress_points = [
        (int(w * 0.40), dress_top_y),
        (int(w * 0.60), dress_top_y),
        (int(w * 0.67), int(h * 0.58)),
        (int(w * 0.73), dress_bottom_y),
        (int(w * 0.27), dress_bottom_y),
        (int(w * 0.33), int(h * 0.58)),
    ]
    draw.polygon(dress_points, fill=(255, 235, 244, 255))

    # Inner shading for a softer painted look.
    draw.polygon(
        [
            (int(w * 0.43), int(h * 0.47)),
            (int(w * 0.57), int(h * 0.47)),
            (int(w * 0.62), int(h * 0.60)),
            (int(w * 0.66), int(h * 0.79)),
            (int(w * 0.34), int(h * 0.79)),
            (int(w * 0.38), int(h * 0.60)),
        ],
        fill=(255, 218, 236, 210),
    )

    # Add neckline ribbon.
    draw.ellipse(
        (
            int(w * 0.43),
            int(h * 0.40),
            int(w * 0.57),
            int(h * 0.48),
        ),
        fill=(255, 245, 250, 230),
        outline=(230, 180, 205, 255),
        width=max(2, int(w * 0.004)),
    )

    # 3) Add a top banner replacing removed text, keeping it neutral.
    banner_y1 = int(h * 0.065)
    banner_y2 = int(h * 0.13)
    draw.rounded_rectangle(
        (int(w * 0.06), banner_y1, int(w * 0.43), banner_y2),
        radius=int(w * 0.015),
        fill=(255, 255, 255, 230),
    )
    font = ImageFont.load_default()
    draw.text((int(w * 0.085), int(h * 0.085)), "SAFE EDITION", fill=(160, 80, 120), font=font)

    # 4) Gentle blur mask around edited zones to blend edges.
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse(
        (int(w * 0.18), int(h * 0.34), int(w * 0.82), int(h * 0.90)),
        fill=(255, 220, 235, 70),
    )
    od.rounded_rectangle(
        (int(w * 0.03), int(h * 0.04), int(w * 0.45), int(h * 0.35)),
        radius=int(w * 0.03),
        fill=(255, 220, 235, 60),
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(8, int(w * 0.02))))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, quality=95)


if __name__ == "__main__":
    source = Path("o:/Coding/Claude/fashion_magazine_cover/chloe_new/chloe_clean.png")
    output = Path("o:/Coding/Claude/fashion_magazine_cover/chloe_new/chloe_safe.png")
    sanitize_image(source, output)
    print(f"Saved sanitized image: {output}")
