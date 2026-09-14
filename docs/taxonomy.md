# Object taxonomy

- **Status:** normative. This file is the single source of the class list.
- **Decision:** `docs/decisions/0002-object-taxonomy.md`
- **Source dataset:** SUN RGB-D, 2D bounding boxes from `SUNRGBDMeta2DBB_v2.mat`
- **Classes:** 11

> **The `class_id` order below is frozen.** It becomes the `labels` array in
> `models.manifest.json`, and `Detection.class_id` indexes into it. Renumbering produces
> an app that draws correct boxes with the wrong names and raises no error anywhere.
> Adding a class appends at 11; removing one retires its ID rather than reusing it.

## Classes

| `class_id` | name |
|---|---|
| 0 | `chair` |
| 1 | `table` |
| 2 | `sofa` |
| 3 | `cabinet` |
| 4 | `screen` |
| 5 | `shelf` |
| 6 | `bin` |
| 7 | `door` |
| 8 | `bed` |
| 9 | `counter` |
| 10 | `sink` |

## Source label mapping

A converter reads this table. **If a source label is not listed here, do not guess** —
collect it, print it with its count, and stop. See
`.claude/skills/annotation-conversion/SKILL.md`.

Matching is performed on a **normalized** form of the source label:

```
normalize(s) = strip non-alphanumeric characters
               from s.strip().lower()
               then strip one trailing "s"
```

so `chairs`, `garbage_bin ` (trailing space), `end_table`, `nightstand`, `coffeetable`
and `drawers` all fold onto their base label without needing separate rows.

| `class_id` | name | SUN RGB-D source labels |
|---|---|---|
| 0 | `chair` | `chair`, `stool` |
| 1 | `table` | `table`, `desk`, `coffee_table`, `endtable`, `night_stand`, `dining_table` |
| 2 | `sofa` | `sofa`, `sofa_chair`, `ottoman`, `bench` |
| 3 | `cabinet` | `cabinet`, `dresser`, `drawer` |
| 4 | `screen` | `monitor`, `tv`, `computer`, `laptop` |
| 5 | `shelf` | `shelf`, `bookshelf` |
| 6 | `bin` | `garbage_bin`, `recycle_bin` |
| 7 | `door` | `door` |
| 8 | `bed` | `bed` |
| 9 | `counter` | `counter` |
| 10 | `sink` | `sink` |

## Expected counts

Measured on the full SUN RGB-D metadata before any train/valid/test split. The dataset
card records the post-split per-class counts, and those are the ones the exit criteria
check.

| `class_id` | name | instances | images | median box short side |
|---|---|---|---|---|
| 0 | `chair` | 25,000 | 5,595 | 92 px |
| 1 | `table` | 12,248 | 6,436 | 139 px |
| 2 | `sofa` | 4,546 | 2,136 | 155 px |
| 3 | `cabinet` | 3,095 | 2,247 | 127 px |
| 4 | `screen` | 2,785 | 1,639 | 78 px |
| 5 | `shelf` | 2,011 | 1,414 | 119 px |
| 6 | `bin` | 1,679 | 1,225 | 79 px |
| 7 | `door` | 1,580 | 1,327 | 100 px |
| 8 | `bed` | 1,548 | 1,200 | 247 px |
| 9 | `counter` | 926 | 799 | 202 px |
| 10 | `sink` | 758 | 654 | 70 px |

**Total: 56,176 objects across 9,891 images — 70.0% of SUN RGB-D's 80,220 annotated
boxes.** `chair` is 44.5% of the taxonomy; the imbalance ratio is 32:1. Report per-class
AP, not only aggregate mAP.

## Deliberately excluded

Recorded so that a future reader does not have to re-derive the reasoning. Full rationale
in ADR 0002.

| Source label | instances | Reason |
|---|---|---|
| `toilet` | 340 | Clears the no-empty-test-class floor only barely; per-class AP would be unstable |
| `stack_of_chairs` | 67 | A group, not an instance |
| `dresser_mirror` | 172 | A mirror, not a dresser; no `mirror` class exists |
| `tv_stand` | 105 | Furniture, not a screen; would blur the `screen`/`cabinet` boundary |
| `desktop` | 58 | Ambiguous between a desk surface and a desktop computer |
| `stand` | 41 | Too vague to map without guessing |
| `pillow` | 4,655 | Median short side 71 px — too thin for the eroded-box depth median |
| `lamp` | 1,752 | Thin stem; eroded box is largely background |
| `box` | 1,451 | 80 px, and semantically unbounded |
| `paper` | 501 | 66 px, effectively planar |
| `keyboard` | 438 | 72 px, thin |
| `picture` | 391 | 72 px, planar |
| `cpu` | 415 | Retained as a separate concept from `screen`; too small at 93 px |
| ~1,020 others | 11,199 total | Long tail; cannot satisfy the no-empty-test-class criterion |

The exclusions above are not neutral. Objects present in the images but outside the
taxonomy become background, which teaches the detector to suppress them — `pillow`
co-occurs with `bed`, `lamp` with `table`. This is recorded in `docs/dataset-card-v1.md`.
