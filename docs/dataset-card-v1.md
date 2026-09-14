# Dataset card — smart-scene-analyzer, version 1

- **Roboflow project:** `oscar-rodriguez-enroutesystems-com/smart-scene-analyzer-2026-09-13`
- **Dataset version:** **1** — an immutable snapshot. Reference it by this integer in code
  and docs, never as "the latest".
- **Generated:** 2026-09-13 (Roboflow's display name for the version is
  `2026-09-14 4:45am`, which is UTC — the integer `1` is the identifier that matters)
- **Taxonomy:** `docs/taxonomy.md`, 11 classes, decided in `docs/decisions/0002-object-taxonomy.md`
- **Source:** SUN RGB-D, 2D bounding boxes from `SUNRGBDMeta2DBB_v2.mat`
- **License:** Public Domain — this project is public on Roboflow Universe

## Contents

| | images | boxes |
|---|---|---|
| train | 6,923 | 39,409 |
| valid | 1,978 | 11,168 |
| test | 989 | 5,536 |
| **total** | **9,890** | **56,113** |

Split is 70 / 20 / 10, assigned **locally and deterministically** by
`scripts/split_dataset.py` at `--seed 0`, not by Roboflow. That choice was made so the
split is reproducible from this repository on any machine, and so the "no empty class in
test" criterion could be verified *before* credits were spent rather than after.

## Per-class counts per split

Format is `instances / images`.

| `class_id` | class | train | valid | test |
|---|---|---|---|---|
| 0 | `chair` | 17,477 / 3,892 | 4,940 / 1,140 | 2,551 / 563 |
| 1 | `table` | 8,605 / 4,503 | 2,458 / 1,292 | 1,178 / 640 |
| 2 | `sofa` | 3,268 / 1,513 | 852 / 412 | 423 / 209 |
| 3 | `cabinet` | 2,209 / 1,577 | 589 / 443 | 294 / 225 |
| 4 | `screen` | 1,924 / 1,147 | 599 / 348 | 254 / 141 |
| 5 | `shelf` | 1,362 / 966 | 454 / 320 | 194 / 128 |
| 6 | `bin` | 1,179 / 852 | 321 / 240 | 172 / 128 |
| 7 | `door` | 1,091 / 924 | 319 / 258 | 169 / 145 |
| 8 | `bed` | 1,091 / 841 | 305 / 241 | 152 / 118 |
| 9 | `counter` | 665 / 578 | 184 / 156 | 77 / 65 |
| 10 | `sink` | 538 / 466 | 147 / 127 | 72 / 60 |

**No class has zero instances in any split.** The thinnest is `sink` at 72 instances
across 60 test images.

## Preprocessing and augmentation

Recorded by the platform, read back after generation to confirm it was applied as sent:

```json
"preprocessing": {
  "auto-orient": true,
  "resize": { "width": 640, "height": 640, "format": "Fit (black edges) in" }
},
"augmentation": {}
```

- **Auto-orient** strips EXIF rotation so stored pixels match displayed pixels.
- **Resize 640×640, "Fit (black edges) in"** is a **letterbox, not a stretch**. This
  matches requirement N1a, which fixes the model input at 640×640 letterboxed from a
  1280×720 source. A stretched dataset would train the detector on distorted aspect
  ratios while the app feeds it letterboxed frames at inference — a train/serve mismatch
  that produces no error, only quietly worse on-device accuracy. The recorded value was
  verified against what was sent, because an unrecognized `format` string falls back to
  stretching silently.
- **No augmentation**, deliberately. Two reasons: it gives an honest un-augmented baseline
  for any later augmented version to be measured against, and augmentation multiplies the
  train split, which inflates both version-generation cost and the recurring storage
  charge (~1.98 credits/month at this image count) — the largest ongoing line in
  `docs/credit-budget.md`.

## Provenance

| Stage | Artifact |
|---|---|
| Source inspection | Round 1 of `.claude/skills/annotation-conversion` |
| Conversion | `scripts/convert_sunrgbd_to_yolo.py` |
| Conversion report | `docs/conversion-report-v1.md` — 80,220 boxes in, 56,113 out, every skip itemized |
| Validation | `scripts/validate_dataset.py` — independent of the converter; `tests/test_validate_dataset.py` proves it can fail |
| Split | `scripts/split_dataset.py --seed 0` |
| Visual check | `scripts/preview_yolo_labels.py` — Round 3, boxes drawn back onto pixels and inspected |

Counts reconcile end to end: the converter wrote 56,113 boxes, the independent validator
counted 56,113 on disk, and Roboflow reports 56,113 across the 11 classes.

## Known limitations

**`chair` is 44.5% of all boxes, and the imbalance ratio is 32:1** (`chair` 24,968 vs
`sink` 757). A headline mAP@50 can clear requirement N3's 0.50 threshold on `chair` alone.
**Report per-class AP**; read N3 per class, not in aggregate.

**30% of SUN RGB-D's annotated objects are now background.** 24,044 boxes across ~1,035
source labels were dropped by the taxonomy, the largest being `pillow` (4,655) and `lamp`
(1,752). This is not neutral: those objects are still in the images, so the detector is
actively trained to suppress things that co-occur with classes it must find — `pillow`
with `bed`, `lamp` with `table`. Expect it to show up as reduced recall on cluttered
surfaces rather than as an obvious failure.

**4,991 boxes were clipped to the image frame.** SUN RGB-D annotates partly-visible
objects with boxes extending past the edge. They were clipped rather than dropped, because
dropping ~2,500 of them would bias the dataset toward centered objects.

**63 boxes were dropped on geometry** — 52 below an 8 px shorter side (the source contains
boxes as small as 0.07 px), 11 entirely outside the frame after clipping. The threshold is
a recorded decision, configurable via `--min-side`, not a silent default.

**Sensor mix is not balanced and was not balanced deliberately:** kv2 3,784 · xtion 3,389
· kv1 2,003 · realsense 1,159 images in the source. The split spreads across capture
sessions but does not stratify by sensor, so per-sensor performance is unmeasured.

**Depth ground truth is not in Roboflow — it is versioned separately.** Roboflow stores
boxes, not depth maps, so D-1 was resolved by `docs/decisions/0003-depth-ground-truth.md`:
SUN RGB-D's `depth_bfx` frames are decoded and kept in gitignored `data/depth-v1/`, pinned
to this dataset version by a manifest digest.

| | |
|---|---|
| Frames | 9,890 — one per image here, joined by the same stem |
| **Manifest `sha256`** | `1d0bb2856e28080eb425df03d7f502be3b8a8e5787bd58f18e978bfe258b6284` |
| Verify | `uv run python scripts/depth_groundtruth.py --verify` |

Requirements N4 and N4a are therefore **measurable** against this version. Two caveats
carried from the ADR: the frames are `depth_bfx`, which is hole-filled and so partly
inpainted rather than measured; and the values are consumed **only as ranks**, never
converted to a scale — Spearman ρ is invariant under monotonic transforms, which is what
makes this compatible with the project's relative-depth vocabulary rule.
