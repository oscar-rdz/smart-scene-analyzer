#!/usr/bin/env python3
"""Convert SUN RGB-D 2D bounding-box metadata to YOLO format.

Input layout — exactly what is on disk, verified by inspection, not from the
dataset's documentation:

    data/raw/SUNRGBDMeta2DBB_v2.mat
        MATLAB 5.0 MAT-file (NOT v7.3 / HDF5), so ``scipy.io.loadmat``.
        One variable, ``SUNRGBDMeta2DBB``, shape ``(1, 10335)`` struct array.
        Fields: sequenceName, groundtruth2DBB, depthpath, rgbpath, depthname,
                rgbname, sensorType
        ``groundtruth2DBB`` is a ``(1, n_objects)`` struct array with fields
        objid, gtBb2D, classname, has3dbox.

    data/raw/SUNRGBD/<sensor>/<subset>/<scene>/image/<rgbname>

Coordinate convention of the source — every item here is a trap that produces
plausible-looking wrong boxes rather than an exception:

  * ``gtBb2D`` is ``[x, y, w, h]`` in **absolute pixels of the source image**,
    top-left origin. It is NOT ``xyxy`` and NOT normalized.
  * Coordinates are **1-indexed** (MATLAB). 10,949 boxes sit at ``x == 1`` or
    ``y == 1``, which is the image edge, not one pixel in from it.
  * ``gtBb2D`` is stored as **float64, uint16, or uint8** depending on the record.
    Arithmetic must happen in float: ``x + w`` on two uint8 values saturates
    silently in numpy and yields a wrong right edge with no error.
  * ~2,500 boxes extend outside the image (``x`` as low as -12.4, ``x+w`` as high
    as 908.5 against a 730 px frame). These are real annotations of partly
    visible objects, so they are **clipped, not skipped** — dropping them would
    bias the dataset toward centered objects.
  * ``rgbpath`` is an absolute path on the dataset authors' fileserver
    (``/n/fs/sun3d/data/...``) and is useless here. The join key is
    ``sequenceName`` + ``rgbname``.

Output layout (YOLO):

    <out>/images/<stem>.jpg
    <out>/labels/<stem>.txt   one line per object:
                              "<class_id> <cx> <cy> <w> <h>"
                              all four coordinates normalized to [0, 1],
                              cx/cy are the box CENTER
    <out>/classes.txt         one name per line; line index is the class_id

The class mapping is read from ``docs/taxonomy.md``. An unmapped source label is
never guessed at: it is collected, reported with its count, and the run stops.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import scipy.io
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_META = REPO_ROOT / "data" / "raw" / "SUNRGBDMeta2DBB_v2.mat"
DEFAULT_ROOT = REPO_ROOT / "data" / "raw"
DEFAULT_TAXONOMY = REPO_ROOT / "docs" / "taxonomy.md"


# --------------------------------------------------------------------------
# taxonomy
# --------------------------------------------------------------------------


def normalize_label(source_label: str) -> str:
    """Normalize a SUN RGB-D source label for mapping lookup.

    Lowercase, strip whitespace and non-alphanumerics, then strip one trailing
    "s". This is the rule stated in ``docs/taxonomy.md`` and it is what folds
    ``chairs``, ``end_table``, ``nightstand``, ``coffeetable``, ``drawers`` and
    ``"garbage_bin "`` (trailing space) onto their base labels.
    """
    return re.sub(r"[^a-z0-9]", "", source_label.strip().lower()).rstrip("s")


@dataclass(frozen=True)
class Taxonomy:
    """The class list and source-label mapping from ``docs/taxonomy.md``.

    ``names`` is ordered by ``class_id``; index == id.
    ``lookup`` maps a normalized source label to a ``class_id``.
    """

    names: tuple[str, ...]
    lookup: dict[str, int]

    def class_id_for(self, source_label: str) -> int | None:
        return self.lookup.get(normalize_label(source_label))


def load_taxonomy(path: Path) -> Taxonomy:
    """Parse the 'Source label mapping' table out of ``docs/taxonomy.md``.

    Rows look like::

        | 0 | `chair` | `chair`, `stool` |

    Only the table under the "## Source label mapping" heading is read, so the
    "Expected counts" table below it cannot be picked up by accident.
    """
    text = path.read_text(encoding="utf-8")
    try:
        section = text.split("## Source label mapping", 1)[1].split("\n## ", 1)[0]
    except IndexError as exc:  # pragma: no cover - malformed taxonomy
        raise SystemExit(f"{path}: no '## Source label mapping' section found") from exc

    row = re.compile(r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*$", re.MULTILINE)
    names: dict[int, str] = {}
    lookup: dict[str, int] = {}
    for match in row.finditer(section):
        class_id, name, sources = int(match.group(1)), match.group(2), match.group(3)
        names[class_id] = name
        for source in re.findall(r"`([^`]+)`", sources):
            key = normalize_label(source)
            if key in lookup and lookup[key] != class_id:
                raise SystemExit(
                    f"{path}: source label {source!r} maps to both "
                    f"{names[lookup[key]]!r} and {name!r}"
                )
            lookup[key] = class_id

    if not names:
        raise SystemExit(f"{path}: mapping table parsed to zero classes")
    expected = list(range(len(names)))
    if sorted(names) != expected:
        raise SystemExit(f"{path}: class_ids are not contiguous from 0: {sorted(names)}")
    return Taxonomy(tuple(names[i] for i in expected), lookup)


# --------------------------------------------------------------------------
# source records
# --------------------------------------------------------------------------


@dataclass
class SourceBox:
    """One annotated object, in source-image pixels, 1-indexed, ``xywh``."""

    source_label: str
    xywh: tuple[float, float, float, float]


@dataclass
class SourceRecord:
    """One SUN RGB-D image and its 2D boxes."""

    index: int
    sequence_name: str
    rgb_name: str
    sensor_type: str
    boxes: list[SourceBox]
    # Carried but unused by this script: the depth ground-truth path consumed by
    # scripts/depth_groundtruth.py, per ADR 0003. Kept here so both sides read the
    # same record and cannot disagree about which depth frame pairs with an image.
    depth_name: str = ""

    @property
    def stem(self) -> str:
        """A stable, unique, traceable output filename stem.

        The sequence name is the dataset's own identifier, so it is kept
        (sanitized and truncated) for traceability, with a short digest of the
        full name appended to guarantee uniqueness after truncation.
        """
        relative = self.sequence_name.removeprefix("SUNRGBD/")
        safe = re.sub(r"[^A-Za-z0-9]+", "_", relative).strip("_")[:80]
        digest = hashlib.sha1(self.sequence_name.encode("utf-8")).hexdigest()[:8]
        return f"{safe}_{digest}"

    def image_path(self, root: Path) -> Path:
        return root / self.sequence_name / "image" / self.rgb_name


def _first(value: np.ndarray) -> str:
    flat = np.asarray(value).ravel()
    return str(flat[0]) if flat.size else ""


def read_records(meta_path: Path) -> list[SourceRecord]:
    """Load every record from the ``.mat``. Does not touch the image files."""
    raw = scipy.io.loadmat(meta_path)["SUNRGBDMeta2DBB"]
    records: list[SourceRecord] = []
    for i in range(raw.shape[1]):
        entry = raw[0, i]
        boxes: list[SourceBox] = []
        bbs = entry["groundtruth2DBB"]
        if bbs.size:
            for j in range(bbs.shape[1]):
                obj = bbs[0, j]
                label = _first(obj["classname"])
                if not label:
                    continue
                # Cast to float BEFORE any arithmetic: the source stores boxes as
                # float64, uint16 or uint8, and uint arithmetic saturates silently.
                values = np.asarray(obj["gtBb2D"]).ravel().astype(np.float64)
                if values.size != 4:
                    continue
                boxes.append(
                    SourceBox(
                        label,
                        (float(values[0]), float(values[1]), float(values[2]), float(values[3])),
                    )
                )
        records.append(
            SourceRecord(
                index=i,
                sequence_name=_first(entry["sequenceName"]),
                rgb_name=_first(entry["rgbname"]),
                sensor_type=_first(entry["sensorType"]),
                depth_name=_first(entry["depthname"]),
                boxes=boxes,
            )
        )
    return records


# --------------------------------------------------------------------------
# conversion
# --------------------------------------------------------------------------


@dataclass
class Tally:
    """Itemized counts. A converter that drops records silently is the failure."""

    records_read: int = 0
    images_written: int = 0
    images_skipped: Counter[str] = field(default_factory=Counter)
    boxes_read: int = 0
    boxes_written: int = 0
    boxes_skipped: Counter[str] = field(default_factory=Counter)
    boxes_clipped: int = 0
    unmapped: Counter[str] = field(default_factory=Counter)
    per_class: Counter[str] = field(default_factory=Counter)


def convert_box(
    xywh: tuple[float, float, float, float],
    image_width: int,
    image_height: int,
    min_side_px: float,
) -> tuple[tuple[float, float, float, float] | None, str | None, bool]:
    """Convert one source box to normalized YOLO ``cxcywh``.

    Args:
        xywh: ``[x, y, w, h]`` in source-image pixels, **1-indexed** (MATLAB).
        image_width: source image width in pixels.
        image_height: source image height in pixels.
        min_side_px: reject a box whose shorter side is below this, measured in
            source pixels **after** clipping.

    Returns:
        ``(cxcywh_normalized_or_None, skip_reason_or_None, was_clipped)`` where
        the box is normalized to ``[0, 1]`` against the source frame and
        ``cx``/``cy`` are the box centre.
    """
    x, y, w, h = xywh
    if w <= 0 or h <= 0:
        return None, "nonpositive_source_wh", False

    # 1-indexed -> 0-indexed.
    x0, y0 = x - 1.0, y - 1.0
    x1, y1 = x0 + w, y0 + h

    clipped_x0, clipped_y0 = max(0.0, x0), max(0.0, y0)
    clipped_x1 = min(float(image_width), x1)
    clipped_y1 = min(float(image_height), y1)
    was_clipped = (clipped_x0, clipped_y0, clipped_x1, clipped_y1) != (x0, y0, x1, y1)

    cw, ch = clipped_x1 - clipped_x0, clipped_y1 - clipped_y0
    if cw <= 0 or ch <= 0:
        return None, "outside_frame", was_clipped
    if min(cw, ch) < min_side_px:
        return None, "below_min_side", was_clipped

    cx = (clipped_x0 + clipped_x1) / 2.0 / image_width
    cy = (clipped_y0 + clipped_y1) / 2.0 / image_height
    nw, nh = cw / image_width, ch / image_height

    # Assert rather than trust. A silently out-of-range coordinate trains a
    # worse model and raises nothing downstream.
    for name, value in (("cx", cx), ("cy", cy), ("w", nw), ("h", nh)):
        if not (0.0 <= value <= 1.0):
            return None, f"normalized_{name}_out_of_range", was_clipped
    if nw <= 0.0 or nh <= 0.0:
        return None, "nonpositive_normalized_wh", was_clipped

    return (cx, cy, nw, nh), None, was_clipped


def select(
    records: list[SourceRecord], limit: int | None, sample: int | None, seed: int
) -> list[SourceRecord]:
    """Pick the records to convert.

    ``--limit`` takes the first N (fast iteration, not representative).
    ``--sample`` takes N spread deterministically across capture sessions, so a
    sample is not all one sensor or one building.
    """
    if limit is not None:
        return records[:limit]
    if sample is None:
        return records

    groups: dict[str, list[SourceRecord]] = defaultdict(list)
    for record in records:
        # Group by sensor + subset directory, which is the capture-session axis.
        parts = record.sequence_name.split("/")
        groups["/".join(parts[1:3]) if len(parts) > 2 else record.sensor_type].append(record)

    rng = np.random.default_rng(seed)
    for bucket in groups.values():
        rng.shuffle(bucket)

    picked: list[SourceRecord] = []
    keys = sorted(groups)
    position = 0
    while len(picked) < sample and any(groups[k] for k in keys):
        key = keys[position % len(keys)]
        if groups[key]:
            picked.append(groups[key].pop())
        position += 1
    return picked


def iter_conversion(
    records: list[SourceRecord],
    taxonomy: Taxonomy,
    root: Path,
    out_dir: Path,
    min_side_px: float,
    tally: Tally,
    resume: bool,
) -> Iterator[tuple[SourceRecord, Path, list[str]]]:
    """Yield ``(record, image_path, yolo_lines)`` for every convertible record."""
    for record in records:
        tally.records_read += 1
        tally.boxes_read += len(record.boxes)

        if not record.boxes:
            tally.images_skipped["no_source_boxes"] += 1
            continue

        label_path = out_dir / "labels" / f"{record.stem}.txt"
        image_out = out_dir / "images" / f"{record.stem}.jpg"
        if resume and label_path.exists() and image_out.exists():
            tally.images_skipped["already_converted"] += 1
            continue

        image_path = record.image_path(root)
        if not image_path.exists():
            tally.images_skipped["image_missing_on_disk"] += 1
            continue

        try:
            with Image.open(image_path) as handle:
                width, height = handle.size
        except OSError:
            tally.images_skipped["image_unreadable"] += 1
            continue

        lines: list[str] = []
        for box in record.boxes:
            class_id = taxonomy.class_id_for(box.source_label)
            if class_id is None:
                tally.unmapped[box.source_label] += 1
                tally.boxes_skipped["label_not_in_taxonomy"] += 1
                continue
            converted, reason, was_clipped = convert_box(box.xywh, width, height, min_side_px)
            if was_clipped:
                tally.boxes_clipped += 1
            if converted is None:
                tally.boxes_skipped[reason or "unknown"] += 1
                continue
            cx, cy, nw, nh = converted
            lines.append(f"{class_id} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            tally.boxes_written += 1
            tally.per_class[taxonomy.names[class_id]] += 1

        if not lines:
            tally.images_skipped["no_boxes_survived"] += 1
            continue

        yield record, image_path, lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--meta", type=Path, default=DEFAULT_META)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="directory containing the extracted SUNRGBD/ tree",
    )
    parser.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "interim" / "yolo-v1")
    parser.add_argument(
        "--min-side",
        type=float,
        default=8.0,
        help="drop a box whose shorter side is below this many source "
        "pixels after clipping (default: 8). Recorded in the "
        "conversion report; the source contains boxes as small as "
        "0.07 px",
    )
    parser.add_argument("--limit", type=int, default=None, help="first N records")
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="N records spread across capture sessions, deterministic",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument(
        "--no-resume", action="store_true", help="reconvert records whose output already exists"
    )
    parser.add_argument("--report", type=Path, default=None, help="write the tally as JSON")
    args = parser.parse_args()

    taxonomy = load_taxonomy(args.taxonomy)
    print(f"taxonomy: {len(taxonomy.names)} classes from {args.taxonomy}")
    print(f"          {taxonomy.names}\n")

    records = read_records(args.meta)
    selected = select(records, args.limit, args.sample, args.seed)
    print(f"records in metadata : {len(records)}")
    print(f"records selected    : {len(selected)}")
    print(f"mode                : {'DRY RUN (writing nothing)' if args.dry_run else 'writing'}")
    print(f"output              : {args.out}")
    print(f"min box short side  : {args.min_side} px\n")

    if not args.dry_run:
        (args.out / "images").mkdir(parents=True, exist_ok=True)
        (args.out / "labels").mkdir(parents=True, exist_ok=True)

    tally = Tally()
    for record, image_path, lines in iter_conversion(
        selected,
        taxonomy,
        args.root,
        args.out,
        args.min_side,
        tally,
        resume=not args.no_resume,
    ):
        if not args.dry_run:
            shutil.copyfile(image_path, args.out / "images" / f"{record.stem}.jpg")
            (args.out / "labels" / f"{record.stem}.txt").write_text(
                "\n".join(lines) + "\n", encoding="utf-8"
            )
        tally.images_written += 1

    if not args.dry_run:
        (args.out / "classes.txt").write_text("\n".join(taxonomy.names) + "\n", encoding="utf-8")

    # ---- reconciliation ---------------------------------------------------
    print("=" * 62)
    print(f"records read        : {tally.records_read}")
    print(f"images written      : {tally.images_written}")
    print(f"images skipped      : {sum(tally.images_skipped.values())}")
    for reason, count in tally.images_skipped.most_common():
        print(f"    {reason:26s} {count}")
    print(f"\nboxes read          : {tally.boxes_read}")
    print(f"boxes written       : {tally.boxes_written}")
    print(f"boxes clipped to frame: {tally.boxes_clipped}")
    print(f"boxes skipped       : {sum(tally.boxes_skipped.values())}")
    for reason, count in tally.boxes_skipped.most_common():
        print(f"    {reason:26s} {count}")

    reconciled = tally.boxes_written + sum(tally.boxes_skipped.values())
    status = "OK" if reconciled == tally.boxes_read else "MISMATCH"
    print(
        f"\nreconcile boxes     : {tally.boxes_written} + "
        f"{sum(tally.boxes_skipped.values())} = {reconciled} vs {tally.boxes_read} read  [{status}]"
    )

    print("\nper class:")
    for name in taxonomy.names:
        print(f"    {name:10s} {tally.per_class[name]}")

    if tally.unmapped:
        print(f"\n{'=' * 62}")
        print(
            f"UNMAPPED SOURCE LABELS: {len(tally.unmapped)} distinct, "
            f"{sum(tally.unmapped.values())} boxes"
        )
        print("These are expected — docs/taxonomy.md deliberately covers ~70% of")
        print("SUN RGB-D's objects. Listed so the exclusion stays visible:")
        for label, count in tally.unmapped.most_common(15):
            print(f"    {label:24s} {count}")

    if args.report:
        args.report.write_text(
            json.dumps(
                {
                    "records_read": tally.records_read,
                    "images_written": tally.images_written,
                    "images_skipped": dict(tally.images_skipped),
                    "boxes_read": tally.boxes_read,
                    "boxes_written": tally.boxes_written,
                    "boxes_clipped": tally.boxes_clipped,
                    "boxes_skipped": dict(tally.boxes_skipped),
                    "per_class": dict(tally.per_class),
                    "unmapped": dict(tally.unmapped),
                    "min_side_px": args.min_side,
                    "reconciled": status == "OK",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nreport written: {args.report}")

    return 0 if status == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
