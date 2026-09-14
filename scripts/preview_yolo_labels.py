#!/usr/bin/env python3
"""Draw converted YOLO labels back onto their images, so a human can look.

Round 3 of ``.claude/skills/annotation-conversion``. Every assertion in the
converter passes on a dataset whose boxes are uniformly shifted, flipped in y,
or off by one — those errors do not raise, they just train a worse model. The
only check that catches them is looking at the pixels.

Reads the converter's output directly (``images/``, ``labels/``,
``classes.txt``) rather than re-deriving boxes from the source metadata, so what
is drawn is what was actually written to disk.

Label format consumed: ``<class_id> <cx> <cy> <w> <h>``, all normalized to
``[0, 1]`` against the image frame, ``cx``/``cy`` being the box centre.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent

# Distinct hues, readable on the dim indoor frames this dataset is made of.
PALETTE = [
    (255, 89, 94),
    (255, 202, 58),
    (138, 201, 38),
    (25, 130, 196),
    (106, 76, 147),
    (255, 146, 76),
    (0, 187, 249),
    (241, 91, 181),
    (0, 245, 212),
    (155, 93, 229),
    (247, 37, 133),
]


def draw_one(
    image_path: Path, label_path: Path, names: list[str], cell: tuple[int, int]
) -> Image.Image:
    """Render one image with its boxes drawn, scaled to ``cell``."""
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    draw = ImageDraw.Draw(image)

    for line in label_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        class_id = int(parts[0])
        cx, cy, nw, nh = (float(v) for v in parts[1:5])
        # normalized cxcywh -> absolute xyxy in SOURCE IMAGE pixels
        x0 = (cx - nw / 2.0) * width
        y0 = (cy - nh / 2.0) * height
        x1 = (cx + nw / 2.0) * width
        y1 = (cy + nh / 2.0) * height
        colour = PALETTE[class_id % len(PALETTE)]
        draw.rectangle([x0, y0, x1, y1], outline=colour, width=3)
        name = names[class_id] if class_id < len(names) else f"?{class_id}"
        tw = 6 * len(name) + 6
        draw.rectangle([x0, max(0, y0 - 14), x0 + tw, max(14, y0)], fill=colour)
        draw.text((x0 + 3, max(0, y0 - 13)), name, fill=(0, 0, 0))

    return image.resize(cell)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=REPO_ROOT / "data" / "interim" / "yolo-v1")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--cols", type=int, default=5)
    parser.add_argument("--cell", type=int, nargs=2, default=(384, 288))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=Path("/tmp/yolo_preview"))
    args = parser.parse_args()

    names = (args.dir / "classes.txt").read_text(encoding="utf-8").split()
    labels = sorted((args.dir / "labels").glob("*.txt"))
    if not labels:
        raise SystemExit(f"no labels in {args.dir / 'labels'}")

    random.Random(args.seed).shuffle(labels)
    picked = labels[: args.count]

    args.out.mkdir(parents=True, exist_ok=True)
    cell = tuple(args.cell)
    tiles = []
    for label_path in picked:
        image_path = args.dir / "images" / f"{label_path.stem}.jpg"
        if not image_path.exists():
            continue
        tile = draw_one(image_path, label_path, names, cell)
        tile.save(args.out / f"{label_path.stem}.jpg", quality=88)
        tiles.append(tile)

    cols = args.cols
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell[0], rows * cell[1]), "white")
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * cell[0], (i // cols) * cell[1]))
    sheet_path = args.out / "contact_sheet.jpg"
    sheet.save(sheet_path, quality=88)

    print(f"classes      : {names}")
    print(f"previewed    : {len(tiles)} images")
    print(f"per-image    : {args.out}")
    print(f"contact sheet: {sheet_path}")
    print("\nNow LOOK at the contact sheet. Boxes must sit tightly on the named")
    print("objects. A uniform offset, a y-flip, or an off-by-one will be visible")
    print("here and nowhere else.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
