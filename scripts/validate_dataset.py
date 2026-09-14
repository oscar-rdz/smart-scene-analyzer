#!/usr/bin/env python3
"""Validate a YOLO dataset directory on disk.

This script is deliberately **independent of the converter**. It imports nothing
from ``convert_sunrgbd_to_yolo.py`` and re-derives every fact from the files that
are actually on disk plus ``docs/taxonomy.md``. A validator that shares code with
the thing it validates agrees with it by construction, including when both are
wrong.

Accepts either layout:

    <root>/images/*.jpg           <root>/train/images/*.jpg
    <root>/labels/*.txt     OR    <root>/train/labels/*.txt
    <root>/classes.txt            <root>/valid/... <root>/test/...
                                  <root>/classes.txt

Label file format required — one line per object::

    <class_id> <cx> <cy> <w> <h>

with ``class_id`` an integer in ``[0, n_classes)`` and ``cx cy w h`` normalized to
``[0, 1]`` against the image frame, ``cx``/``cy`` being the box **centre**.

Exits non-zero if any check fails, so it is usable as a CI gate.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TAXONOMY = REPO_ROOT / "docs" / "taxonomy.md"
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")
SPLIT_NAMES = ("train", "valid", "val", "test")


@dataclass
class Findings:
    """Accumulated problems. Empty means the dataset passed."""

    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def taxonomy_names(path: Path) -> list[str]:
    """Read the ordered class names from the Classes table of ``docs/taxonomy.md``.

    Independent of the converter's parser on purpose: this reads the **Classes**
    table, while the converter reads the **Source label mapping** table. If the
    two tables ever disagree, that disagreement is itself a finding.
    """
    text = path.read_text(encoding="utf-8")
    try:
        section = text.split("## Classes", 1)[1].split("\n## ", 1)[0]
    except IndexError:
        raise SystemExit(f"{path}: no '## Classes' section found") from None
    rows = re.findall(r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|", section, re.MULTILINE)
    if not rows:
        raise SystemExit(f"{path}: Classes table parsed to zero rows")
    by_id = {int(i): name for i, name in rows}
    if sorted(by_id) != list(range(len(by_id))):
        raise SystemExit(f"{path}: class_ids not contiguous from 0: {sorted(by_id)}")
    return [by_id[i] for i in range(len(by_id))]


def find_splits(root: Path) -> dict[str, Path]:
    """Return ``{split_name: directory}``. A flat dataset reports one split, ``all``."""
    splits = {name: root / name for name in SPLIT_NAMES if (root / name / "labels").is_dir()}
    if splits:
        return splits
    if (root / "labels").is_dir():
        return {"all": root}
    raise SystemExit(f"{root}: found neither <root>/labels nor <root>/<split>/labels")


def check_classes_file(root: Path, expected: list[str], findings: Findings) -> None:
    """``classes.txt`` must match the taxonomy in names AND order, exactly.

    Order is the whole point: a dataset whose class list is correct but permuted
    trains a model that labels every box with a different class's name, and
    nothing raises.
    """
    path = root / "classes.txt"
    if not path.exists():
        findings.fail(f"{path} is missing")
        return
    found = path.read_text(encoding="utf-8").splitlines()
    found = [line.strip() for line in found if line.strip()]
    if found == expected:
        return
    if sorted(found) == sorted(expected):
        findings.fail(
            f"{path}: same class names as docs/taxonomy.md but DIFFERENT ORDER.\n"
            f"        on disk : {found}\n"
            f"        taxonomy: {expected}"
        )
    else:
        missing = [n for n in expected if n not in found]
        extra = [n for n in found if n not in expected]
        findings.fail(
            f"{path}: disagrees with docs/taxonomy.md. missing={missing} unexpected={extra}"
        )


def check_pairing(split: str, directory: Path, findings: Findings) -> tuple[list[Path], int]:
    """Every label needs an image and every image needs a label."""
    label_dir, image_dir = directory / "labels", directory / "images"
    if not image_dir.is_dir():
        findings.fail(f"[{split}] {image_dir} is missing")
        return [], 0

    labels = sorted(label_dir.glob("*.txt"))
    images = [p for p in sorted(image_dir.iterdir()) if p.suffix.lower() in IMAGE_SUFFIXES]
    label_stems = {p.stem for p in labels}
    image_stems = {p.stem for p in images}

    orphan_labels = sorted(label_stems - image_stems)
    orphan_images = sorted(image_stems - label_stems)
    if orphan_labels:
        findings.fail(
            f"[{split}] {len(orphan_labels)} label file(s) with no image, e.g. {orphan_labels[:3]}"
        )
    if orphan_images:
        findings.fail(
            f"[{split}] {len(orphan_images)} image(s) with no label file, e.g. {orphan_images[:3]}"
        )
    return labels, len(images)


def check_labels(
    split: str, labels: list[Path], n_classes: int, findings: Findings
) -> tuple[Counter[int], dict[int, set[str]]]:
    """Parse every label file and assert the coordinate contract.

    Returns ``(instances_per_class_id, images_per_class_id)``.
    """
    per_class: Counter[int] = Counter()
    images_per_class: dict[int, set[str]] = defaultdict(set)
    empty: list[str] = []
    malformed: list[str] = []
    bad_id: list[str] = []
    out_of_range: list[str] = []
    nonpositive: list[str] = []

    for path in labels:
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            empty.append(path.name)
            continue
        for number, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) != 5:
                malformed.append(f"{path.name}:{number} has {len(parts)} fields, expected 5")
                continue
            try:
                class_id = int(parts[0])
                cx, cy, w, h = (float(v) for v in parts[1:])
            except ValueError:
                malformed.append(f"{path.name}:{number} unparseable: {line!r}")
                continue
            if not (0 <= class_id < n_classes):
                bad_id.append(f"{path.name}:{number} class_id={class_id}")
                continue
            if not all(0.0 <= v <= 1.0 for v in (cx, cy, w, h)):
                out_of_range.append(f"{path.name}:{number} ({cx:.4f},{cy:.4f},{w:.4f},{h:.4f})")
                continue
            if w <= 0.0 or h <= 0.0:
                nonpositive.append(f"{path.name}:{number} w={w} h={h}")
                continue
            per_class[class_id] += 1
            images_per_class[class_id].add(path.stem)

    for label, items in (
        ("empty label file(s) where annotations were expected", empty),
        ("malformed label line(s)", malformed),
        ("class_id outside the taxonomy", bad_id),
        ("coordinate(s) outside [0, 1]", out_of_range),
        ("box(es) with non-positive width or height", nonpositive),
    ):
        if items:
            findings.fail(f"[{split}] {len(items)} {label}, e.g. {items[:3]}")

    return per_class, images_per_class


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dir", type=Path, default=REPO_ROOT / "data" / "interim" / "yolo-v1")
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument(
        "--require-all-classes",
        action="store_true",
        help="fail if any class has zero instances in any split "
        "(roadmap exit criterion 2 applies this to the test split)",
    )
    args = parser.parse_args()

    names = taxonomy_names(args.taxonomy)
    findings = Findings()
    print(f"taxonomy : {len(names)} classes from {args.taxonomy}")
    print(f"dataset  : {args.dir}\n")

    check_classes_file(args.dir, names, findings)
    splits = find_splits(args.dir)

    totals: Counter[int] = Counter()
    for split, directory in splits.items():
        labels, n_images = check_pairing(split, directory, findings)
        per_class, images_per_class = check_labels(split, labels, len(names), findings)
        totals.update(per_class)

        print(f"[{split}] images={n_images}  labels={len(labels)}  boxes={sum(per_class.values())}")
        for class_id, name in enumerate(names):
            count = per_class[class_id]
            marker = "  <-- ZERO" if count == 0 else ""
            n_img = len(images_per_class[class_id])
            print(f"    {class_id:2d} {name:9s} {count:7d} inst  {n_img:6d} img{marker}")
            if count == 0:
                message = f"[{split}] class {class_id} ({name}) has zero instances"
                findings.fail(message) if args.require_all_classes else findings.warn(message)
        print()

    print("=" * 62)
    print(f"total boxes: {sum(totals.values())}")
    for message in findings.warnings:
        print(f"WARN  {message}")
    for message in findings.failures:
        print(f"FAIL  {message}")

    if findings.failures:
        print(f"\nFAILED — {len(findings.failures)} check(s)")
        return 1
    suffix = f" with {len(findings.warnings)} warning(s)" if findings.warnings else ""
    print(f"\nPASSED{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
