#!/usr/bin/env python3
"""Split a flat YOLO dataset into train/valid/test directories.

Roboflow can split on its own, but doing it here buys two things: the split is
**deterministic and reproducible from this repo** (same seed, same result, on any
machine), and it can be verified against the roadmap's exit criterion — no class
with zero instances in the test split — *before* any credits are spent, rather
than after.

Input (flat)::

    <src>/images/*.jpg
    <src>/labels/*.txt
    <src>/classes.txt

Output::

    <dst>/train/images/*.jpg   <dst>/train/labels/*.txt
    <dst>/valid/...            <dst>/test/...
    <dst>/classes.txt

Images are **hard-linked**, not copied, so a 429 MB dataset does not become 858 MB.
The source directory is never modified.

Assignment is a deterministic shuffle by a fixed seed, then a straight
proportional cut. Stratification is deliberately *not* applied: it would couple
the split to the taxonomy, and the verification step below is a stronger
guarantee than stratification is — it checks the property we actually care about
instead of approximating it.
"""

from __future__ import annotations

import argparse
import random
import shutil
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def class_ids_in(label_path: Path) -> set[int]:
    """The distinct class_ids annotated in one label file."""
    ids: set[int] = set()
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts:
            try:
                ids.add(int(parts[0]))
            except ValueError:
                continue
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--src", type=Path, default=REPO_ROOT / "data" / "interim" / "yolo-v1")
    parser.add_argument(
        "--dst", type=Path, default=REPO_ROOT / "data" / "interim" / "yolo-v1-split"
    )
    parser.add_argument("--train", type=float, default=0.70)
    parser.add_argument("--valid", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    names = (args.src / "classes.txt").read_text(encoding="utf-8").split()
    labels = sorted((args.src / "labels").glob("*.txt"))
    if not labels:
        raise SystemExit(f"no labels in {args.src / 'labels'}")

    ordered = list(labels)
    random.Random(args.seed).shuffle(ordered)
    n = len(ordered)
    n_train = int(n * args.train)
    n_valid = int(n * args.valid)
    assignment = {
        "train": ordered[:n_train],
        "valid": ordered[n_train : n_train + n_valid],
        "test": ordered[n_train + n_valid :],
    }

    # ---- verify BEFORE writing anything -------------------------------
    per_split: dict[str, Counter[int]] = {}
    images_per_split: dict[str, Counter[int]] = {}
    for split, paths in assignment.items():
        instances: Counter[int] = Counter()
        images: Counter[int] = Counter()
        for path in paths:
            seen = class_ids_in(path)
            for class_id in seen:
                images[class_id] += 1
            for line in path.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if parts:
                    instances[int(parts[0])] += 1
        per_split[split] = instances
        images_per_split[split] = images

    print(f"seed={args.seed}  images={n}\n")
    header = f"{'id':>2} {'class':9s}" + "".join(f"{s:>18s}" for s in assignment)
    print(header)
    print("-" * len(header))
    empty: list[str] = []
    for class_id, name in enumerate(names):
        row = f"{class_id:2d} {name:9s}"
        for split in assignment:
            inst = per_split[split][class_id]
            img = images_per_split[split][class_id]
            row += f"{inst:>10d}/{img:<7d}"
            if inst == 0:
                empty.append(f"{name} in {split}")
        print(row)
    print("-" * len(header))
    print("     " + " " * 9 + "".join(f"{len(assignment[s]):>10d} img      " for s in assignment))

    if empty:
        print(f"\nFAIL — class(es) with zero instances: {empty}")
        print("Exit criterion 2 requires no class empty in the test split.")
        return 1
    print("\nevery class populated in every split ✅")

    if args.dry_run:
        print("\nDRY RUN — nothing written")
        return 0

    for split, paths in assignment.items():
        (args.dst / split / "images").mkdir(parents=True, exist_ok=True)
        (args.dst / split / "labels").mkdir(parents=True, exist_ok=True)
        for label_path in paths:
            image_src = args.src / "images" / f"{label_path.stem}.jpg"
            image_dst = args.dst / split / "images" / image_src.name
            label_dst = args.dst / split / "labels" / label_path.name
            if not image_dst.exists():
                image_dst.hardlink_to(image_src)
            if not label_dst.exists():
                label_dst.hardlink_to(label_path)
    shutil.copyfile(args.src / "classes.txt", args.dst / "classes.txt")
    print(f"\nwritten to {args.dst} (images hard-linked, source untouched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
