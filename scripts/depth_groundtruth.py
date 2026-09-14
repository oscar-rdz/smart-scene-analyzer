#!/usr/bin/env python3
"""Build and verify the depth ground-truth set for a dataset version.

Implements `docs/decisions/0003-depth-ground-truth.md`. Roboflow does not store
depth maps, so this is the versioning path that replaces it: a set of decoded
frames in gitignored ``data/depth-v1/`` plus a manifest whose own ``sha256`` is
recorded in the ADR. A regenerated set either reproduces that digest or it does
not.

What it does per frame, and why each step is not optional:

* Reads ``depth_bfx``, **not** ``depth``. The raw frames carry up to 27.4%
  invalid (zero) pixels on kv2; a rank correlation over a map that is a quarter
  holes measures the masking strategy rather than the model. ``depth_bfx`` is
  hole-filled and therefore partly inpainted — a stated limitation in the ADR.
* Decodes the bit rotation with ``(v >> 3) | (v << 13)``. On kv1/kv2/realsense
  the low three bits are zero, so the rotation reduces to a monotonic divide by
  eight and skipping it changes no ranks. **On xtion 1.41% of pixels carry
  non-zero low bits** and their order does change — 34% of this dataset would be
  quietly wrong.
* Never names a unit and never converts to a physical scale. These values are
  consumed only as **ranks**, which is what makes N4/N4a measurable without
  asserting a scale the pipeline does not have.

Sign convention, stated because getting it wrong looks like total failure rather
than like a bug: the values written here are **direct** depth (larger is
farther). The pipeline produces relative **inverse** depth (larger is nearer).
One side must be negated before correlating, or rho lands near -1.

Output::

    data/depth-v1/frames/<stem>.png    decoded 16-bit PNG, one per dataset image
    data/depth-v1/manifest.json        {stem: {source, sha256}}, plus counts

Stems match the detection converter exactly, so depth joins to detections by
filename.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_converter():
    """Import the converter for its stem rule.

    Deliberate coupling: this script must produce *exactly* the stems the
    converter produced, so sharing that one rule is the point rather than a
    smell. Contrast `validate_dataset.py`, which must stay independent.
    """
    path = REPO_ROOT / "scripts" / "convert_sunrgbd_to_yolo.py"
    spec = importlib.util.spec_from_file_location("convert_sunrgbd_to_yolo", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def decode(raw: np.ndarray) -> np.ndarray:
    """Undo SUN RGB-D's bit rotation.

    Args:
        raw: uint16 array as stored in the PNG.

    Returns:
        uint16 array in the source's own encoding, ordering restored. No unit is
        implied and no scale is asserted — use ranks only.
    """
    raw = raw.astype(np.uint16)
    return ((raw >> 3) | (raw << 13)).astype(np.uint16)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--meta", type=Path, default=REPO_ROOT / "data" / "raw" / "SUNRGBDMeta2DBB_v2.mat"
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=REPO_ROOT / "data" / "interim" / "yolo-v1-split",
        help="the converted dataset whose stems define the set",
    )
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "depth-v1")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="recompute the manifest digest and compare, writing nothing",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    converter = _load_converter()

    wanted = {p.stem for p in args.dataset.rglob("labels/*.txt")}
    if not wanted:
        raise SystemExit(f"no label files under {args.dataset}")
    print(f"dataset stems : {len(wanted)}")

    records = converter.read_records(args.meta)
    by_stem = {r.stem: r for r in records if r.stem in wanted}
    print(f"matched in .mat: {len(by_stem)}")
    missing_record = wanted - set(by_stem)
    if missing_record:
        print(
            f"WARNING: {len(missing_record)} stem(s) have no metadata record, "
            f"e.g. {sorted(missing_record)[:3]}"
        )

    frames_dir = args.out / "frames"
    if not args.verify:
        frames_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, dict[str, str]] = {}
    missing_source: list[str] = []
    written = 0
    for i, (stem, record) in enumerate(sorted(by_stem.items())):
        if args.limit is not None and i >= args.limit:
            break
        source = args.root / record.sequence_name / "depth_bfx" / record.depth_name
        if not source.exists():
            missing_source.append(stem)
            continue
        target = frames_dir / f"{stem}.png"
        if not args.verify and not target.exists():
            Image.fromarray(decode(np.array(Image.open(source)))).save(target)
            written += 1
        if target.exists():
            manifest[stem] = {
                "source": str(source.relative_to(args.root)),
                "sha256": sha256_of(target),
            }

    if missing_source:
        print(
            f"WARNING: {len(missing_source)} frame(s) missing depth_bfx on disk, "
            f"e.g. {missing_source[:3]}"
        )

    payload = {
        "dataset_version": 1,
        "source": "SUN RGB-D depth_bfx, bit-rotation decoded",
        "decode": "(v >> 3) | (v << 13)",
        "sign": "direct depth, larger is farther; pipeline output is inverse, larger is nearer",
        "frames": len(manifest),
        "manifest": manifest,
    }
    blob = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()

    manifest_path = args.out / "manifest.json"
    if args.verify:
        if not manifest_path.exists():
            print(f"FAIL — {manifest_path} does not exist; nothing to verify against")
            return 1
        existing = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        print(f"\nframes hashed   : {len(manifest)}")
        print(f"recomputed      : {digest}")
        print(f"on disk         : {existing}")
        if existing == digest:
            print("\nPASSED — the depth set reproduces its manifest digest")
            return 0
        print("\nFAILED — the depth set does not match its manifest")
        return 1

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(blob)
    print(f"\nframes written  : {written}")
    print(f"frames in set   : {len(manifest)}")
    print(f"manifest        : {manifest_path}")
    print(f"MANIFEST SHA256 : {digest}")
    print("\nRecord that digest in docs/decisions/0003-depth-ground-truth.md.")
    print("It is the version marker — the thing Roboflow would have provided.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
