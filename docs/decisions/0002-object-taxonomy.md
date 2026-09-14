# ADR 0002 — Object taxonomy: 11 indoor classes merged from SUN RGB-D

- **Status:** accepted
- **Date:** 2026-09-13
- **Deciders:** Oscar Rodríguez

## Context

`docs/requirements.md` deferred the class list deliberately — "the class list is a
property of the dataset, and committing to classes before the data exists risks a
taxonomy the data cannot support." The data now exists, so the decision is due.

The source is SUN RGB-D (`data/raw/`, 10,335 images, 80,220 annotated 2D boxes). Its
label vocabulary is **1,068 distinct strings**, and the distribution is extremely long
tailed: the top 45 labels carry 86% of all objects, and the remaining 1,023 labels share
the other 14%. `chair` alone is 31% of every annotated object in the dataset.

Three constraints make the selection non-obvious. None of them is "pick the most frequent
classes".

**1. The fusion layer cannot produce a trustworthy depth value for a thin object.**
`docs/architecture.md` §7 fuses per-object depth as a **median over an eroded box**, and
records the trade-off openly: "Fails on thin structures, stated openly"
(`docs/architecture.md:625`). A class whose boxes are mostly narrow — `lamp` with its
stem, `bottle`, `paper`, `keyboard` — yields an eroded core that is largely background.
Such a class would satisfy N3 (detection mAP) while systematically damaging N4 (per-object
depth ordering, Spearman ρ ≥ 0.85 after fusion). Median box short side is therefore a
**selection criterion**, not a statistic.

**2. No class may be empty in the test split.** `docs/roadmap.md` §2 exit criterion 2
requires per-class instance counts for train/valid/test "with no class at zero instances
in the test split". At a 10% test share this puts a hard floor under how rare a class may
be, and it is what rules out the 1,023-label tail outright.

**3. Some distinctions in SUN RGB-D are annotator noise, not signal.** `desk` vs `table`
vs `coffee_table` vs `endtable`, `sofa` vs `sofa_chair`, `shelf` vs `bookshelf` are
applied inconsistently across the dataset. Asking a detector to learn a distinction the
labels do not consistently encode manufactures a confusion matrix that no amount of
training data fixes — the failure the `error-triage` skill classifies as TAXONOMY rather
than DATA or MODEL.

Two merges were genuinely ambiguous and were resolved by measurement rather than
judgement:

- **`drawer` → `cabinet`** risked nested boxes (a drawer annotated inside an
  already-boxed dresser would produce two overlapping boxes of the same merged class).
  Measured: median containment of a `drawer` box inside a `dresser`/`cabinet` box in the
  same image is **0.00**, and only 3.4–3.8% are ≥90% contained. Drawers are annotated as
  standalone furniture. Merge is safe.
- **`computer` → `screen`** was ambiguous in the metadata: `computer` boxes never overlap
  `monitor` boxes (0.00 containment) yet share an identical median aspect ratio of 0.95,
  and co-occur with the separate `cpu` label in 24.9% of images. The metadata supports
  both readings. Resolved by cropping eight `computer` boxes from the extracted images and
  looking at them: **all eight are displays.** The disjointness means "two screens in one
  room, labelled inconsistently", not "two kinds of object".

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Adopt SUN RGB-D's 1,068 labels as-is** | No mapping decisions; nothing discarded | Violates exit criterion 2 on ~1,020 classes. Unlearnable at N3. Not a real option |
| **B. Top-N by frequency, no merges** | Simple, defensible, reproducible | Ignores constraint 1 — admits `pillow`, `lamp`, `box`, `paper` whose fused depth N4 cannot trust. Preserves the `desk`/`table` confusion as a permanent accuracy ceiling |
| **C. 11 merged classes, filtered by test-split survival, box short side, and annotator consistency** | Every class is populated in the test split, large enough for the eroded-box median, and free of known-inconsistent splits | Discards 30% of annotated objects. Worsens `chair` dominance to 44.5% |
| **D. 5–6 core furniture classes only** | Near-balanced; very robust | Too thin for a scene *understanding* demo; discards ~45% of objects for little gain |

## Decision

Adopt **11 classes**, merged from 26 SUN RGB-D source labels, in the frozen `class_id`
order below.

| `class_id` | class | merged from | inst | images | med. short side |
|---|---|---|---|---|---|
| 0 | `chair` | chair, stool | 25,000 | 5,595 | 92 px |
| 1 | `table` | table, desk, coffee_table, endtable, night_stand, dining_table | 12,248 | 6,436 | 139 |
| 2 | `sofa` | sofa, sofa_chair, ottoman, bench | 4,546 | 2,136 | 155 |
| 3 | `cabinet` | cabinet, dresser, drawer | 3,095 | 2,247 | 127 |
| 4 | `screen` | monitor, tv, computer, laptop | 2,785 | 1,639 | 78 |
| 5 | `shelf` | shelf, bookshelf | 2,011 | 1,414 | 119 |
| 6 | `bin` | garbage_bin, recycle_bin | 1,679 | 1,225 | 79 |
| 7 | `door` | door | 1,580 | 1,327 | 100 |
| 8 | `bed` | bed | 1,548 | 1,200 | 247 |
| 9 | `counter` | counter | 926 | 799 | 202 |
| 10 | `sink` | sink | 758 | 654 | 70 |

**Coverage: 56,176 of 80,220 objects (70.0%), across 9,891 of 10,335 images.**

Source labels are matched after normalization (lowercase, strip whitespace, strip
non-alphanumerics, strip trailing plural `s`), which folds in the observed variants
`chairs`, `drawers`, `end_table`, `nightstand`, `coffeetable`, and `garbage_bin `
(trailing space).

**`toilet` was considered and rejected.** It clears exit criterion 2 literally (340
instances, ~33 test images) but at that volume its per-class AP would swing substantially
between runs, making the model card's headline number less stable for a 0.4% coverage
gain.

**Explicitly excluded, with reasons** — these are close enough to a taxonomy class that a
future reader will wonder, so the rejections are recorded rather than left implicit:

| Source label | inst | Why excluded |
|---|---|---|
| `stack_of_chairs` | 67 | A group, not an instance. Would teach the detector to box several chairs as one |
| `dresser_mirror` | 172 | A mirror, not a dresser. There is no `mirror` class |
| `tv_stand` | 105 | Furniture, not a screen. Merging into `cabinet` would blur the `screen`/`cabinet` boundary at the exact location both appear |
| `desktop` | 58 | Ambiguous between a desk surface and a desktop computer |
| `stand` | 41 | Too vague to map without guessing |
| `pillow`, `lamp`, `box`, `paper`, `keyboard`, `bottle`, `picture`, `cpu` | 4,655–415 | Frequent enough to train, too thin or small for the eroded-box median. Constraint 1 |

## Consequences

**Harder / newly constrained.** The `class_id` order above is now load-bearing and must
not be renumbered. It becomes the `labels` array in `models.manifest.json`
(`docs/architecture.md:336`, currently the placeholder `"<OPEN — Lesson 02 taxonomy>"`),
and `Detection.class_id` indexes into it (`docs/architecture.md:232`). Reordering it
produces an app that draws correct boxes with wrong names and raises no error anywhere —
the failure `CLAUDE.md`'s artifact-contract section describes.

Files and components that now depend on this decision:

- `docs/taxonomy.md` — the normative class list; written from this ADR
- `docs/architecture.md` §8.2, §B5 (`num_classes` = 11), §B10 (`labels`) — resolves an
  item marked **OPEN**
- `docs/requirements.md` — the "Object taxonomy: pending" section, and N3's
  "provisional until the taxonomy exists" caveat
- `src/smart_scene_analyzer/contracts/artifacts.py`, `src/smart_scene_analyzer/export/manifest.py`
  — write and validate the `labels` array
- `scripts/convert_sunrgbd_to_yolo.py` (Lesson 02) — reads this mapping; per
  `.claude/skills/annotation-conversion/SKILL.md` it must **stop rather than guess** on an
  unmapped label
- `scripts/validate_dataset.py` — asserts class IDs fall inside the taxonomy
- The Roboflow project `smart-scene-analyzer-2026-09-13` — enforced per-version via
  **Modify Classes**, per `.claude/agents/dataset-engineer.md:38`
- `.claude/hooks/artifact_drift.py` — fires on `taxonomy.md` edits
  (`SOURCE_SUFFIXES`), warning that bundled artifacts predate the taxonomy

**Easier.** The design was already insulated: the label list is read from the manifest and
never hardcoded in Python or TypeScript, and `num_classes` is derived from tensor shape
(`docs/architecture.md:654`). Nothing in the architecture changes because the taxonomy
landed — only the exported artifacts do.

**Foreclosed.** 30% of SUN RGB-D's annotated objects become background. This is not
neutral: `pillow` sits on `bed` and `lamp` on the furniture in class 1, so the detector is
actively taught to suppress objects that co-occur with classes it must find. This must be
stated in `docs/dataset-card-v1.md` rather than discovered in Lesson 03.

`chair` is 44.5% of the taxonomy and the imbalance ratio is 32:1. A headline mAP@50 can
clear N3's 0.50 on `chair` alone, so the model card must report **per-class AP**, and N3
should be read per class rather than in aggregate.

## Revisit when

- The dataset card shows a class at or near zero instances in the test split after the
  real split is generated — the 10% estimate above is an estimate, not the split.
- Per-class AP in `docs/model-card-yolo11-detection.md` shows a merged class
  (`table`, `sofa`, `cabinet`, `screen`) performing far worse than its components'
  frequency predicts, indicating a merge joined genuinely distinct objects.
- A product requirement appears that needs a class not in this list.

**Renumbering is never a valid revision.** Adding a class appends at `class_id` 11;
removing one retires the ID rather than reusing it. Any change here requires re-export and
a new `models.manifest.json` — `artifact_drift.py` will say so.
