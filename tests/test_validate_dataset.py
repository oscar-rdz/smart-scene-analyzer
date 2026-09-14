"""Tests for ``scripts/validate_dataset.py``.

The point of these is narrow and specific: **prove the validator can fail.** A
validator that returns "PASSED" unconditionally is worse than no validator,
because it converts an unchecked dataset into one that looks checked. So every
test below deliberately corrupts one thing and asserts the corresponding check
fires.

Offline by construction — no network, no GPU, no weights, no dataset on disk.
Every fixture is a handful of text files in ``tmp_path``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "validate_dataset.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_dataset", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec: @dataclass resolves its own module out of
    # sys.modules, and fails with AttributeError if it is not there yet.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


vd = _load_module()

NAMES = ["chair", "table", "sofa"]

TAXONOMY_MD = """# Object taxonomy

## Classes

| `class_id` | name |
|---|---|
| 0 | `chair` |
| 1 | `table` |
| 2 | `sofa` |

## Source label mapping

| `class_id` | name | SUN RGB-D source labels |
|---|---|---|
| 0 | `chair` | `chair` |
| 1 | `table` | `table` |
| 2 | `sofa` | `sofa` |
"""


@pytest.fixture
def taxonomy(tmp_path: Path) -> Path:
    path = tmp_path / "taxonomy.md"
    path.write_text(TAXONOMY_MD, encoding="utf-8")
    return path


def make_dataset(
    root: Path,
    labels: dict[str, str],
    *,
    class_names: list[str] | None = None,
    images: list[str] | None = None,
) -> Path:
    """Build a minimal YOLO dataset. ``images`` defaults to one per label file."""
    (root / "images").mkdir(parents=True, exist_ok=True)
    (root / "labels").mkdir(parents=True, exist_ok=True)
    (root / "classes.txt").write_text(
        "\n".join(class_names if class_names is not None else NAMES) + "\n",
        encoding="utf-8",
    )
    for stem, content in labels.items():
        (root / "labels" / f"{stem}.txt").write_text(content, encoding="utf-8")
    for stem in images if images is not None else list(labels):
        (root / "images" / f"{stem}.jpg").write_bytes(b"\xff\xd8\xff\xe0stub")
    return root


def run_checks(root: Path, taxonomy_path: Path) -> vd.Findings:
    """Run every check the way ``main`` does, and return the findings."""
    names = vd.taxonomy_names(taxonomy_path)
    findings = vd.Findings()
    vd.check_classes_file(root, names, findings)
    for split, directory in vd.find_splits(root).items():
        label_files, _ = vd.check_pairing(split, directory, findings)
        vd.check_labels(split, label_files, len(names), findings)
    return findings


# ---------------------------------------------------------------- happy path


def test_clean_dataset_passes(tmp_path: Path, taxonomy: Path) -> None:
    root = make_dataset(
        tmp_path / "ds",
        {"a": "0 0.5 0.5 0.2 0.2\n", "b": "1 0.25 0.25 0.1 0.1\n2 0.7 0.7 0.2 0.2\n"},
    )
    findings = run_checks(root, taxonomy)
    assert findings.failures == []


def test_taxonomy_parses_names_in_order(taxonomy: Path) -> None:
    assert vd.taxonomy_names(taxonomy) == NAMES


# ------------------------------------------------------------- the failures
# Each of these must fail. If one starts passing, the validator has stopped
# validating and the dataset it blesses is unchecked.


def test_permuted_classes_txt_fails(tmp_path: Path, taxonomy: Path) -> None:
    """Right names, wrong order — the silent-mislabel case."""
    root = make_dataset(
        tmp_path / "ds",
        {"a": "0 0.5 0.5 0.2 0.2\n"},
        class_names=["table", "chair", "sofa"],
    )
    findings = run_checks(root, taxonomy)
    assert any("DIFFERENT ORDER" in f for f in findings.failures)


def test_missing_class_in_classes_txt_fails(tmp_path: Path, taxonomy: Path) -> None:
    root = make_dataset(
        tmp_path / "ds", {"a": "0 0.5 0.5 0.2 0.2\n"}, class_names=["chair", "table"]
    )
    findings = run_checks(root, taxonomy)
    assert any("disagrees with docs/taxonomy.md" in f for f in findings.failures)


def test_empty_label_file_fails(tmp_path: Path, taxonomy: Path) -> None:
    root = make_dataset(tmp_path / "ds", {"a": "0 0.5 0.5 0.2 0.2\n", "empty": ""})
    findings = run_checks(root, taxonomy)
    assert any("empty label file" in f for f in findings.failures)


def test_class_id_outside_taxonomy_fails(tmp_path: Path, taxonomy: Path) -> None:
    root = make_dataset(tmp_path / "ds", {"a": "99 0.5 0.5 0.2 0.2\n"})
    findings = run_checks(root, taxonomy)
    assert any("class_id outside the taxonomy" in f for f in findings.failures)


@pytest.mark.parametrize(
    "line",
    [
        "0 1.4 0.5 0.2 0.2\n",  # cx > 1
        "0 -0.1 0.5 0.2 0.2\n",  # cx < 0
        "0 0.5 0.5 1.7 0.2\n",  # w > 1
    ],
)
def test_coordinate_outside_unit_range_fails(tmp_path: Path, taxonomy: Path, line: str) -> None:
    root = make_dataset(tmp_path / "ds", {"a": line})
    findings = run_checks(root, taxonomy)
    assert any("outside [0, 1]" in f for f in findings.failures)


@pytest.mark.parametrize("line", ["0 0.5 0.5 0.0 0.2\n", "0 0.5 0.5 0.2 0.0\n"])
def test_nonpositive_box_fails(tmp_path: Path, taxonomy: Path, line: str) -> None:
    root = make_dataset(tmp_path / "ds", {"a": line})
    findings = run_checks(root, taxonomy)
    assert any("non-positive width or height" in f for f in findings.failures)


def test_malformed_line_fails(tmp_path: Path, taxonomy: Path) -> None:
    root = make_dataset(tmp_path / "ds", {"a": "0 0.5 0.5 0.2\n"})
    findings = run_checks(root, taxonomy)
    assert any("malformed label line" in f for f in findings.failures)


def test_label_without_image_fails(tmp_path: Path, taxonomy: Path) -> None:
    root = make_dataset(
        tmp_path / "ds",
        {"a": "0 0.5 0.5 0.2 0.2\n", "orphan": "0 0.5 0.5 0.2 0.2\n"},
        images=["a"],
    )
    findings = run_checks(root, taxonomy)
    assert any("with no image" in f for f in findings.failures)


def test_image_without_label_fails(tmp_path: Path, taxonomy: Path) -> None:
    root = make_dataset(tmp_path / "ds", {"a": "0 0.5 0.5 0.2 0.2\n"}, images=["a", "lonely"])
    findings = run_checks(root, taxonomy)
    assert any("with no label file" in f for f in findings.failures)


def test_missing_classes_txt_fails(tmp_path: Path, taxonomy: Path) -> None:
    root = make_dataset(tmp_path / "ds", {"a": "0 0.5 0.5 0.2 0.2\n"})
    (root / "classes.txt").unlink()
    findings = run_checks(root, taxonomy)
    assert any("is missing" in f for f in findings.failures)


# ------------------------------------------------------------------ layouts


def test_split_layout_is_discovered(tmp_path: Path, taxonomy: Path) -> None:
    root = tmp_path / "ds"
    for split in ("train", "valid", "test"):
        make_dataset(root / split, {f"{split}_a": "0 0.5 0.5 0.2 0.2\n"})
        (root / split / "classes.txt").unlink()
    (root / "classes.txt").write_text("\n".join(NAMES) + "\n", encoding="utf-8")
    assert set(vd.find_splits(root)) == {"train", "valid", "test"}
    assert run_checks(root, taxonomy).failures == []
