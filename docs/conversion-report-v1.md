# Conversion report — SUN RGB-D → YOLO, v1

- **Date:** 2026-09-13
- **Converter:** `scripts/convert_sunrgbd_to_yolo.py`
- **Preview:** `scripts/preview_yolo_labels.py`
- **Taxonomy:** `docs/taxonomy.md` (11 classes), decided in `docs/decisions/0002-object-taxonomy.md`
- **Source:** `data/raw/SUNRGBDMeta2DBB_v2.mat` + `data/raw/SUNRGBD/` (read-only; never modified)
- **Output:** `data/interim/yolo-v1/` — 9,890 images, 9,890 label files, 429 MB

## Reconciliation

Input and output counts reconcile exactly. Nothing is dropped without a reason
attached to it.

| | count |
|---|---|
| records in metadata | 10,335 |
| images written | 9,890 |
| images skipped | 445 |
| **boxes read** | **80,220** |
| boxes written | 56,113 |
| boxes skipped | 24,107 |
| **check** | 56,113 + 24,107 = **80,220** ✅ |

### Images skipped, by reason

| Reason | count |
|---|---|
| `no_boxes_survived` — every box in the image was an unmapped label | 399 |
| `no_source_boxes` — the record carries no 2D annotation at all | 46 |

### Boxes skipped, by reason

| Reason | count |
|---|---|
| `label_not_in_taxonomy` — expected; the taxonomy deliberately covers ~70% | 24,044 |
| `below_min_side` — shorter side < 8 px after clipping | 52 |
| `outside_frame` — box lies entirely outside the image after clipping | 11 |

**4,991 boxes were clipped to the frame rather than skipped.** SUN RGB-D annotates
partly-visible objects with boxes that extend past the image edge (`x` as low as −12.4,
`x + w` as high as 908.5 against a 730 px frame). Dropping them would bias the dataset
toward centered objects, so they are clipped and kept.

## Per-class output

| `class_id` | class | boxes written | predicted in `taxonomy.md` | delta |
|---|---|---|---|---|
| 0 | `chair` | 24,968 | 25,000 | −32 |
| 1 | `table` | 12,241 | 12,248 | −7 |
| 2 | `sofa` | 4,543 | 4,546 | −3 |
| 3 | `cabinet` | 3,092 | 3,095 | −3 |
| 4 | `screen` | 2,777 | 2,785 | −8 |
| 5 | `shelf` | 2,010 | 2,011 | −1 |
| 6 | `bin` | 1,672 | 1,679 | −7 |
| 7 | `door` | 1,579 | 1,580 | −1 |
| 8 | `bed` | 1,548 | 1,548 | 0 |
| 9 | `counter` | 926 | 926 | 0 |
| 10 | `sink` | 757 | 758 | −1 |
| | **total** | **56,113** | **56,176** | **−63** |

The 63-box delta is fully accounted for: `below_min_side` (52) + `outside_frame` (11).
`taxonomy.md`'s counts are measured on raw metadata before geometric filtering; these are
post-filter. No box is unexplained.

## Conversion decisions

Each of these is a behaviour the source data forced, verified by inspection rather than
taken from the dataset's documentation.

| Source property | Handling |
|---|---|
| `gtBb2D` is `[x, y, w, h]` absolute px, top-left origin | Converted to normalized `cxcywh`; `cx`/`cy` are the box **centre** |
| Coordinates are **1-indexed** (MATLAB) | 1 subtracted from `x` and `y` before normalizing |
| Stored as float64 / uint16 / uint8 per record | Cast to float64 **before** any arithmetic — `x + w` on uint8 saturates silently |
| ~2,500 boxes extend outside the frame | Clipped to the frame, kept (4,991 clipped in total once both axes counted) |
| Boxes as small as 0.07 px exist | Dropped below an **8 px** shorter side, configurable via `--min-side`, recorded here |
| `rgbpath` is an absolute path on the authors' fileserver | Ignored; join key is `sequenceName` + `rgbname` |
| Label variants `chairs`, `end_table`, `nightstand`, `coffeetable`, `drawers`, `garbage_bin ` | Folded by the normalization rule in `docs/taxonomy.md` |

**Unmapped labels stop the run rather than being guessed at.** The 1,035 distinct unmapped
labels here are the deliberate exclusions from ADR 0002, reported in full by the converter
on every run so the exclusion stays visible rather than becoming invisible.

## Verification against pixels

The reconciliation above can be perfectly consistent while every box is wrong — a y-flip,
an origin off-by-one, or a uniform offset raises no exception and passes every assertion.

`scripts/preview_yolo_labels.py` draws the **written label files** back onto their images
(not a re-derivation from the source metadata) and writes a contact sheet. Ten images were
rendered and inspected visually.

Result: boxes sit tightly on the named objects across all ten, with no offset and no axis
flip. The taxonomy merges are visibly correct in the pixels — a stool renders as `chair`,
a nightstand as `table`, monitors as `screen` — and excluded objects (`lamp`, `pillow`)
are correctly unboxed.

To reproduce:

```bash
uv run python scripts/convert_sunrgbd_to_yolo.py --dry-run          # report, writes nothing
uv run python scripts/convert_sunrgbd_to_yolo.py                    # full run, idempotent
uv run python scripts/preview_yolo_labels.py --count 20             # then LOOK at the sheet
```

## Known limitations

- **`--limit N` is not representative.** The first N records are bedroom scenes; taxonomy
  coverage reads 46% there against 70% overall. Use `--sample N`, which spreads
  deterministically across capture sessions.
- **`sofa_bed` (11 instances) is unmapped.** It could defensibly merge into either `sofa`
  or `bed`. At 11 instances it is below the noise floor, and guessing is precisely what
  the converter is built not to do.
- **No train/valid/test split is applied here.** Splitting happens at Roboflow version
  generation; per-class counts per split go in `docs/dataset-card-v1.md`, and that is what
  the roadmap's exit criterion checks — not the totals above.
- **30% of annotated objects are now background.** `pillow` (4,655) and `lamp` (1,752) are
  the largest, and both co-occur with classes the detector must find. Consequence recorded
  in ADR 0002.
