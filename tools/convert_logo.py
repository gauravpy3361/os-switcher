#!/usr/bin/env python3
"""Convert SVG logo to PNG and ICO format using Pillow and cairosvg."""

from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def make_fallback_image(width: int, height: int) -> Image.Image:
    # A beautiful, high-quality PIL drawn representation of the logo if Cairo is missing
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background roundrect
    # Dark purple to gray-blue premium gradient (represented as base colors in flat design)
    draw.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=int(width * 0.25),
        fill="#1f1c2c",
        outline=None,
    )

    # 2. Outer Ring abstract arrows
    # Blue / Cyan arrow (Top-Right)
    draw.arc(
        [width * 0.15, height * 0.15, width * 0.85, height * 0.85],
        start=270,
        end=90,
        fill="#00c6ff",
        width=int(width * 0.1),
    )
    # Orange / Pink arrow (Bottom-Left)
    draw.arc(
        [width * 0.15, height * 0.15, width * 0.85, height * 0.85],
        start=90,
        end=270,
        fill="#f857a6",
        width=int(width * 0.1),
    )

    # Draw arrow heads
    # Blue head
    draw.polygon(
        [
            (width * 0.5, height * 0.05),
            (width * 0.5, height * 0.25),
            (width * 0.35, height * 0.15),
        ],
        fill="#00c6ff",
    )
    # Pink head
    draw.polygon(
        [
            (width * 0.5, height * 0.95),
            (width * 0.5, height * 0.75),
            (width * 0.65, height * 0.85),
        ],
        fill="#f857a6",
    )

    # 3. Inner crosshair
    draw.ellipse(
        [width * 0.375, height * 0.375, width * 0.625, height * 0.625],
        fill=None,
        outline="#ffffff",
        width=2,
    )
    draw.line(
        [(width * 0.44, height * 0.5), (width * 0.56, height * 0.5)],
        fill="#ffffff",
        width=3,
    )
    draw.line(
        [(width * 0.5, height * 0.44), (width * 0.5, height * 0.56)],
        fill="#ffffff",
        width=3,
    )

    return img


def main() -> int:
    svg_path = ROOT / "gui" / "os-switcher-logo.svg"
    png_path = ROOT / "gui" / "os-switcher-logo.png"
    ico_path = ROOT / "gui" / "os-switcher-logo.ico"

    print("Checking for cairosvg dependencies...")
    try:
        import cairosvg

        print("cairosvg imported successfully. Converting SVG to PNG...")
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            output_width=256,
            output_height=256,
        )
        print("OK   SVG to PNG conversion successful.")
    except Exception as exc:
        print(f"Warning: cairosvg conversion failed or Cairo C-library is missing ({exc}).")
        print("Falling back to pure PIL high-quality vector rendering...")
        img_fallback = make_fallback_image(256, 256)
        img_fallback.save(png_path, "PNG")
        print("OK   Pure PIL fallback PNG generation successful.")

    # Convert PNG to ICO
    try:
        img = Image.open(png_path)
        img.save(
            ico_path,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)],
        )
        print(f"OK   ICO file generated successfully at {ico_path}.")
        return 0
    except Exception as exc:
        print(f"Error generating ICO file: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
