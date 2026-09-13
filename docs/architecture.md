# Architecture — Smart Scene Analyzer

- **Status:** Lesson 01 design. Supersedes nothing; constrained by `docs/decisions/0001-inference-target.md`.
- **Date:** 2026-09-13
- **Author:** Architecture role
- **Designed against:** `docs/requirements.md` (F1–F9, N1–N21), `docs/artifact-budget.md`

> Everything here is a **design**, not a measurement. No stage in the latency budget has
> been timed, because neither model has been exported and the app does not exist yet.
> Sections marked **OPEN** are decisions this document deliberately does not make.

---

## 1. Deployment units and the component diagram

There are exactly two deployment units, and they move on different clocks. That is the
most important fact on this page.

| Unit | What it is | How it ships | Who can change it at runtime |
|---|---|---|---|
| **A — the app** (`app/`) | Expo development build for iOS and Android. Contains both runtimes, both model artifacts, the fusion port, and the UI | An **app-store release**. Days to weeks, and only for users who update | Nobody. Not us |
| **B — the reference and export pipeline** (`src/`) | Python. Trains, exports, and remains the reference implementation the device is checked against | Never ships. It produces files | N/A — it is a dev-time tool |

The consequence is the whole reason ADR 0001 calls on-device "the expensive option":
**a model bug inside unit A cannot be fixed by editing the file next to it.** There is no
deploy. Unit B can be corrected in an afternoon and the corrected artifact still sits on
a developer's disk until a release carries it to a handset. Every design choice below that
looks over-careful — the versioned artifact manifest, the parity tests, the explicit
coordinate spaces — is paying for that one property.

```
┌─ DEPLOYMENT UNIT B — dev-time only. Ships nowhere. ────────────────────────────┐
│                                                                                │
│   src/smart_scene_analyzer/                                                    │
│                                                                                │
│    training/ ──▶ evaluation/ ──▶ export/ ──┬──▶ yolo11*_int8.tflite            │
│        │                                   └──▶ depth_anything_v2*.pte        │
│        │                                        + models.manifest.json         │
│    (MLflow: tracking URI OPEN — §8)                                            │
│                                                                                │
│   preprocess/ · geometry/ · inference/ · fusion.py  ← THE REFERENCE            │
│        ▲                                                                       │
│        └── tests/fixtures/fusion_cases.json  (shared, plain JSON)              │
└────────────────────────────────────────────────────────────────────────────────┘
              │                                              ▲
              │  B10: THE ARTIFACT CONTRACT                  │  B12: shared fixtures
              │  crosses a RELEASE boundary, not a           │  (the only thing keeping
              │  function call. Copied by hand/CI into       │   two implementations of
              │  app/assets/models/. Nothing checks it       │   one algorithm honest)
              ▼  at runtime.                                 │
┌─ DEPLOYMENT UNIT A — the Expo binary. Ships on a store's timetable. ═══════════╗
║                                                                                ║
║   ┌──────────────┐  B1  ┌───────────────┐                                      ║
║   │  Capture /   │─────▶│  Acquisition  │  decode · EXIF-orient · downscale    ║
║   │  Pick        │      │               │  to the SOURCE frame                 ║
║   └──────────────┘      └───────┬───────┘                                      ║
║                                 │ B2: SourceFrame (RGB uint8, SOURCE space)    ║
║                                 ▼                                              ║
║                    ┌────────────────────────┐                                  ║
║                    │  Preprocess / geometry │  letterbox · normalize           ║
║                    │  ONE source frame,     │  → two tensors, two              ║
║                    │  TWO model-input spaces│    LetterboxParams               ║
║                    └───┬────────────────┬───┘                                  ║
║             B3: det tensor    │         │    B4: depth tensor                  ║
║             MODEL_INPUT(det)  │         │    MODEL_INPUT(depth)                ║
║                    ▼          │         │          ▼                           ║
║   ┌─────────────────────────┐ │         │ ┌──────────────────────────────┐     ║
║   │ YOLO11 int8 .tflite     │ │         │ │ Depth Anything V2 .pte       │     ║
║   │ react-native-fast-tflite│ │         │ │ react-native-executorch      │     ║
║   │        (native thread)  │ │         │ │        (native thread)       │     ║
║   └───────────┬─────────────┘ │         │ └──────────────┬───────────────┘     ║
║        B5: raw output tensors │         │  B7: raw relative inverse depth      ║
║               ▼               │         │                ▼                     ║
║   ┌─────────────────────────┐ │         │ ┌──────────────────────────────┐     ║
║   │ Decode + NMS  (pure TS) │ │         │ │ DepthMap adapter (pure TS)   │     ║
║   │ un-letterboxes to SOURCE│ │         │ │ keeps depth-map index space  │     ║
║   └───────────┬─────────────┘ │         │ └──────────────┬───────────────┘     ║
║               │ B6: Detection[]          │  B8: DepthMap + its LetterboxParams ║
║               └───────────────┬─────────┴────────────────┘                     ║
║                               ▼                                                ║
║              ┌──────────────────────────────────┐                              ║
║              │  SCENE UNDERSTANDING LAYER       │  app/src/fusion/             ║
║              │  pure TS · no I/O · no runtime   │  PORT of fusion.py           ║
║              │  median over eroded box (§4)     │                              ║
║              └────────────────┬─────────────────┘                              ║
║                               │ B9: SceneResult (still SOURCE pixels)          ║
║                               ▼                                                ║
║              ┌──────────────────────────────────┐                              ║
║              │  Overlay / renderer              │  B11: SOURCE → SCREEN,       ║
║              │  the ONLY place SCREEN exists    │  one named function          ║
║              └──────────────────────────────────┘                              ║
║                                                                                ║
║        ── no network call anywhere inside this box, by ADR 0001 ──             ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

The double line is the deployment boundary. The single line at the top is not — unit B is
a toolchain, and it has no boundary to defend because nothing consumes it at runtime.

**Why the two inference branches are drawn side by side:** they have no data dependency on
each other. Detection does not need depth and depth does not need detection; they converge
for the first time at the fusion layer. This is what makes the parallel block in the
latency budget (§5) legitimate rather than wishful, and it is also why the failure modes
are independent (N12 — depth can fail while detection succeeds, and the UI must say so).

---

## 2. The three coordinate spaces

Named once, here, and referenced by name everywhere else. `CLAUDE.md` requires this; the
contracts in §3 are unreadable without it.

| Space | Definition | Extent | Origin / axes |
|---|---|---|---|
| **SOURCE** | Pixels of the image after acquisition-time orientation and downscale. This is the frame every externally visible box is quoted in (F3) | `W_src × H_src`, long edge ≤ 1280, aspect preserved | Top-left, x→right, y→down |
| **MODEL_INPUT(m)** | Letterboxed pixels of one specific model's input tensor. **There are two instances** — `MODEL_INPUT(det)` and `MODEL_INPUT(depth)` — and they are not interchangeable | det: 640×640 (N1a). depth: 518×518 (**assumed**, §9) | Top-left of the padded canvas |
| **SCREEN** | React Native density-independent points, relative to the top-left of the image view after its content-fit transform | The view's laid-out size | Top-left of the **view**, not of the screen |

Every conversion between spaces is mediated by a `LetterboxParams` record:

```
LetterboxParams {
  scale:      float   # SOURCE px → MODEL_INPUT px, uniform, aspect-preserving
  pad_x:      int     # MODEL_INPUT px of padding on the LEFT edge
  pad_y:      int     # MODEL_INPUT px of padding on the TOP edge
  src_w:      int     # SOURCE extent, carried so the inverse is total
  src_h:      int
  input_w:    int     # MODEL_INPUT extent
  input_h:    int
  pad_value:  int     # the fill colour, needed to EXCLUDE pad pixels (§4)
}
```

Forward: `x_model = x_source * scale + pad_x`.
Inverse: `x_source = (x_model - pad_x) / scale`.

Three rules that this project will otherwise lose an afternoon to:

1. **A bare number pair is never a point.** Anything crossing a boundary carries its space
   in its type name or its field name. `bbox_source`, not `bbox`.
2. **Conversions live in exactly one named function per direction, with both spaces in the
   signature** — `source_to_model_input(...)`, `model_input_to_source(...)`,
   `sourceToScreen(...)`. A box indexed into the wrong space returns a number, in range,
   and wrong.
3. **`MODEL_INPUT(det)` and `MODEL_INPUT(depth)` have different scales and different pads.**
   They are letterboxed independently from the same SOURCE frame. Passing a detection
   `LetterboxParams` to the depth un-letterbox compiles fine and is silently wrong.

---

## 3. Data contracts — every boundary

Each row states the **type**, the **units**, and the **coordinate space**. Boundaries where
resizing happens are marked ⚠.

### B1 — Capture/Picker → Acquisition

- **Type:** `CapturedImageRef { uri: string, width: int, height: int, mimeType: string }`
- **Units:** `width`/`height` in **native image pixels**, pre-orientation. Up to 12 MP (N7).
- **Space:** none yet — this is a file reference, not a frame.
- **Notes:** EXIF orientation is **not** applied at this point. A picker URI can be a HEIC
  with a rotation flag; treating its `width`/`height` as the display geometry is wrong for
  a quarter of iPhone photos.

### B2 ⚠ — Acquisition → Preprocess

- **Type:** `SourceFrame { pixels: uint8[H][W][3], width: int, height: int }`
- **Layout:** `[H, W, 3]` **HWC**, channel order **RGB** (not BGR), sRGB, non-premultiplied,
  alpha discarded.
- **Units:** pixel intensities `0–255`, integer.
- **Space:** defines **SOURCE**. Origin top-left. EXIF orientation is applied **here** and
  nowhere else downstream, so `width`/`height` are the upright extent.
- **⚠ Resize:** long edge downscaled to ≤ 1280 with aspect preserved (N7). A 4032×3024
  capture becomes 1280×960, **not** 1280×720. `SourceFrame` never assumes 16:9.
- **Invariant:** once constructed, a `SourceFrame` is immutable. Every box the user ever
  sees is expressible in this frame.

### B3 ⚠ — Preprocess → Detection runtime

- **Type:** `(tensor, LetterboxParams)`
- **Layout:** `[1, 640, 640, 3]` **NHWC**, dtype **uint8**.
- **Units:** raw `0–255` intensities, **no float normalization**. For an int8-quantized
  TFLite graph the quantization parameters live inside the model; dividing by 255 here
  produces a black image. The tensor's dtype is part of the artifact contract, fixed by
  export (§7).
- **Space:** `MODEL_INPUT(det)`. Letterbox pad value `114` on all four sides as needed,
  centred (pad split evenly, remainder to the right/bottom).
- **⚠ Resize:** this is the resize. `scale` and `pad_x`/`pad_y` returned alongside; the
  tensor alone is not a complete value.

### B4 ⚠ — Preprocess → Depth runtime

- **Type:** `(tensor, LetterboxParams)`
- **Layout:** `[1, 3, 518, 518]` **NCHW**, dtype **float32**. Note this is a *different
  layout* from B3 — NCHW not NHWC, float not uint8. A silent swap here produces a
  plausible-looking depth map of nothing.
- **Units:** ImageNet-normalized: `(x/255 - mean) / std`, `mean = [0.485, 0.456, 0.406]`,
  `std = [0.229, 0.224, 0.225]`, channel order RGB. **Assumed** — the authoritative values
  are whatever the export writes into `models.manifest.json` (§7, §9).
- **Space:** `MODEL_INPUT(depth)`, an independent letterbox with its own scale and pads.
- **⚠ Resize:** yes, and to a **different** target than B3.

### B5 — Detection runtime → Decode + NMS

- **Type:** raw output tensor(s) from `react-native-fast-tflite`.
- **Layout:** `[1, 4 + num_classes, num_anchors]` float32 after dequantization, the
  ultralytics YOLO11 export layout. `num_classes` is **OPEN** until the taxonomy exists
  (§8); nothing in this design depends on its value, only on it being read from the
  manifest rather than hardcoded.
- **Units:** box terms are `cxcywh` in **`MODEL_INPUT(det)` pixels** — already scaled to the
  640 canvas by the export, not normalized to 0–1. Class terms are sigmoid probabilities in
  `[0, 1]`.
- **Space:** `MODEL_INPUT(det)`. Still letterboxed. Still padded.

### B6 ⚠ — Decode + NMS → Scene understanding layer

**This is the contract the project will otherwise get wrong.**

- **Type:** `list[Detection]`, where

```
Detection {
  bbox:        [x1, y1, x2, y2]   float
  class_id:    int
  label:       string
  confidence:  float
}
```

- **Units:** `bbox` is **`xyxy` in absolute pixels of the SOURCE frame** — not `cxcywh`, not
  normalized 0–1, and **not** the 640×640 letterboxed model-input frame. `confidence` is a
  probability in `[0, 1]`. `class_id` indexes the label list in `models.manifest.json`.
- **Space:** **SOURCE.** The un-letterbox (`model_input_to_source`) happens **here**, at the
  exit of decode, and never again downstream. Every component after this point may assume
  SOURCE and nothing else.
- **⚠ Resize:** this is the inverse of B3's resize. Boxes are clipped to
  `[0, W_src] × [0, H_src]` **after** un-letterboxing, so a box that overhangs into the pad
  region is truncated rather than given a negative coordinate.
- **Empty is valid:** zero detections is `[]`. Not `None`, not an exception, not a sentinel
  (F8).
- **Ordering:** descending confidence. Stated because the UI draws in this order and the
  parity fixtures compare element-wise.

### B7 — Depth runtime → DepthMap adapter

- **Type:** raw output tensor from `react-native-executorch`.
- **Layout:** `[1, 1, h, w]` or `[1, h, w]` float32; the adapter squeezes to `[h, w]` and
  **raises on any other rank** rather than reshaping hopefully.
- **Units:** **relative inverse depth. Larger is nearer. No unit, no scale, comparable only
  within one image.** The raw range is model-dependent and is not assumed to be `[0, 1]`.
- **Space:** `MODEL_INPUT(depth)` index space, at the model's output resolution `h × w`,
  which may be smaller than 518×518.

### B8 — DepthMap adapter → Scene understanding layer

- **Type:**

```
DepthMap {
  values:    float32[h][w]      # relative inverse depth, larger is nearer
  height:    int                # h
  width:     int                # w
  letterbox: LetterboxParams    # relates this grid to SOURCE
  vmin:      float              # observed min over NON-PAD pixels
  vmax:      float              # observed max over NON-PAD pixels
}
```

- **Units:** unitless relative inverse depth. `vmin`/`vmax` exist so the UI can shade
  without recomputing, and are computed over **non-pad** pixels only — letterbox padding is
  grey canvas, the model happily assigns it a depth, and including it skews the range.
- **Space:** `MODEL_INPUT(depth)` grid indices. **The map is deliberately NOT upsampled to
  SOURCE resolution.** Fusion samples into this grid via `letterbox`. Rationale: a
  518×518 → 1280×960 bilinear upsample is ~1.2 M output pixels of work on the critical path
  to produce information the fusion layer then reduces to one number per box. The
  reduction is cheaper than the interpolation.
- **Invariant:** `values` is read-only. Both fusion implementations must not normalize it
  in place, or the second call on the same map gives a different answer.

### B9 — Scene understanding layer → Overlay

- **Type:**

```
SceneResult {
  status:         "ok" | "detection_failed" | "depth_unavailable" | "input_rejected"
  objects:        SceneObject[]
  depth:          DepthMap | null
  source_width:   int
  source_height:  int
  model_versions: { detection: string, depth: string, manifest_sha256: string }
  timings_ms:     { acquire, preprocess, detect, depth, fuse: float }   # dev builds only
}

SceneObject {
  bbox:            [x1, y1, x2, y2]   float
  class_id:        int
  label:           string
  confidence:      float
  relative_depth:  float | null
  depth_rank:      int | null
  depth_status:    "ok" | "degenerate_box" | "no_depth_map"
}
```

- **Units:** `bbox` **xyxy, absolute SOURCE pixels** — unchanged from B6, deliberately.
  `relative_depth` is relative inverse depth, larger is nearer, unitless, **comparable only
  against other objects in this same `SceneResult`**. `depth_rank` is `0` for the nearest
  object, ascending; it exists so the UI can shade by rank without ever being tempted to
  treat the raw value as a quantity. `timings_ms` are milliseconds, wall clock.
- **Space:** SOURCE. Still. The fusion layer performs **no** coordinate transform on boxes.
- **`status` is a discriminated union, not a boolean** — F8 and N12 require that "zero
  detections", "depth failed", "detection failed", and "still loading" are four visually
  distinct states. "Still loading" is the absence of a `SceneResult`, which is why it is not
  a member of the enum.
- **`model_versions` satisfies F7** and is read from the bundled manifest, never from a
  network call and never hardcoded in TypeScript.

### B10 — **The artifact contract** (`src/export/` → `app/assets/models/`)

Crosses a **release boundary**, not a function call. Nothing validates it at runtime; an
app built against last week's label order runs, draws boxes, and names them wrong.

- **Type:** two binary artifacts plus one `models.manifest.json`, co-located and versioned
  together in `app/assets/models/`.
- **The manifest is the contract made machine-readable:**

```
{
  "detection": {
    "file": "yolo11n_int8.tflite", "sha256": "...",
    "input":  { "shape": [1,640,640,3], "dtype": "uint8",  "layout": "NHWC" },
    "output": { "shape": [1,84,8400],   "dtype": "float32", "boxes": "cxcywh",
                "box_space": "MODEL_INPUT(det)" },
    "letterbox_pad_value": 114,
    "labels": ["<OPEN — Lesson 02 taxonomy>"],
    "mlflow_run_id": "...", "registry_version": "...", "dataset_version": "..."
  },
  "depth": {
    "file": "depth_anything_v2s.pte", "sha256": "...",
    "input":  { "shape": [1,3,518,518], "dtype": "float32", "layout": "NCHW",
                "normalization": { "mean": [...], "std": [...] } },
    "output": { "semantics": "relative inverse depth, larger is nearer, unitless" }
  },
  "exported_at": "...", "exporter_version": "..."
}
```

- **Direction:** strictly one-way. **The export defines it; the app consumes it.** The app
  never regenerates it, and Mobile never edits it — that is the role boundary in `CLAUDE.md`
  made concrete.
- **Enforcement:** `artifact_drift.py` warns on divergence; the export-parity test (N20) is
  the actual gate. The manifest `sha256` lets a test assert that the file the app bundles is
  the file the parity test blessed.

### B11 ⚠ — Overlay: SOURCE → SCREEN

- **Type:** `sourceToScreen(bbox_source, { srcW, srcH, viewW, viewH, fit }) → bbox_screen`
- **Units:** input absolute SOURCE pixels; output React Native **points** (density-
  independent), relative to the top-left of the image view.
- **Space:** the only place SCREEN exists. **⚠ Resize:** yes — and it is a *third*
  independent scale, unrelated to either model letterbox. It changes on rotation and on
  every different device, which is why it may not be cached alongside the `SceneResult`.
- **`fit`:** `"contain"` assumed (§9). Under `contain` the view has its own letterbox pads,
  and they are not the model's pads. Three letterboxes exist in this system and none of
  them is the same as another.

### B12 — Shared fixtures (`tests/fixtures/fusion_cases.json`)

- **Type:** plain JSON. No pickle, no `.npy`, no binary.
- **Contents:** per case — a `DepthMap` grid with a **known analytic gradient**, a list of
  input boxes in SOURCE pixels, the `LetterboxParams`, and the expected `relative_depth` per
  box computed by hand.
- **Direction:** neither implementation owns it. `src/smart_scene_analyzer/fusion.py` and
  `app/src/fusion/index.ts` both read it (N21). When they disagree, the disagreement is the
  finding — the fixture is never edited to make them agree.

---

## 4. The scene understanding layer — fusion strategy

**Input:** `list[Detection]` in SOURCE pixels (B6) + a `DepthMap` in its own grid (B8).
**Output:** one `relative_depth` per object (B9).
**Properties:** pure. No I/O, no model handle, no clock, no randomness. Same inputs, same
outputs, in both languages. That is what makes N21 testable at all.

### The method: **median of relative inverse depth over a centre-eroded, pad-excluded box**

Five steps, in this order:

1. **Project the box into the depth grid.** `bbox_source → bbox_depth` via
   `DepthMap.letterbox` (SOURCE → MODEL_INPUT(depth)), then scale by the model's
   output-to-input ratio if `h × w` is smaller than the input canvas. One named function.
   Round outward (`floor` on x1/y1, `ceil` on x2/y2) so a box narrower than one depth cell
   still covers a cell.
2. **Erode toward the centre by `erosion_fraction = 0.25` per side**, keeping the central
   50% of the width and 50% of the height (25% of the area). Rationale below.
3. **Clip** to the valid, **non-pad** region of the depth grid. Letterbox padding is grey
   canvas; the model assigns it a depth and that depth means nothing.
4. **Reduce by median** over the surviving cells.
5. **Rank** all objects by `relative_depth` descending (larger is nearer) to fill
   `depth_rank`.

### Why median, and not mean

Mean is wrong for a reason that will occur in almost every real image. An axis-aligned box
around a chair contains the wall visible between its legs. That wall's relative inverse
depth is far from the chair's, and a mean is dragged toward it in proportion to how much of
the box it occupies. A median only moves once the contaminating surface holds **more than
half** the sampled cells — it degrades at a threshold rather than continuously.

Median also survives quantization artefacts and depth-edge ringing, which appear as a thin
band of extreme values along every object boundary and are exactly the thing a mean is most
sensitive to.

### Why eroded, and by how much

The erosion attacks the same problem earlier. Background contamination in a bounding box is
concentrated at the **corners and edges**, because the box is the tight axis-aligned hull of
a shape that is not a rectangle. Keeping the central 50%×50% removes the corners entirely
and keeps the region most likely to be on the object.

`0.25` per side is a **choice, not a requirement** — `docs/requirements.md` is silent. It
is exposed as `FusionConfig.erosion_fraction`, defaulted in one place, serialized into the
fixture cases, and identical in both implementations. It is not a magic number inlined
twice in two languages.

### What it does when the box contains a background gap

This is the honest part, and it is a **stated failure mode rather than a solved problem**:

| Case | Behaviour | Correct? |
|---|---|---|
| Object fills > 50% of the eroded region (the common case: a sofa, a person, a table) | Median lands on the object surface | Yes |
| Object fills < 50% — thin or skeletal structures seen through their own gaps: a floor lamp, a chair from the side, a plant | **The median returns the BACKGROUND**, and the object reads as farther than it is | **No — and the design says so rather than hiding it** |
| Box overhangs the frame | Clipped at step 3; the median is over what remains | Yes |
| Eroded box empties (box smaller than ~2 depth cells) | **Fall back** to the un-eroded clipped box | Yes |
| Un-eroded clipped box is also empty (zero-area box, or entirely in the pad region) | `relative_depth = null`, `depth_status = "degenerate_box"`. **Never `0.0`** — a sentinel zero is a valid relative inverse depth and would render as the farthest object in the scene | Yes |
| No depth map at all (depth model failed to load, N12) | Every object gets `relative_depth = null`, `depth_status = "no_depth_map"`, `SceneResult.status = "depth_unavailable"`. Detection results still render | Yes |

The thin-structure case is the design's known weakness. Two mitigations exist and **neither
is adopted now**, because adopting an unmeasured heuristic is worse than a documented
failure: (a) a bimodality test on the sampled cells, falling back to the nearer mode's
median; (b) a fixed high percentile (e.g. p75) instead of p50, on the reasoning that the
object is usually the nearer surface. Both trade a new failure mode for this one — (b) in
particular makes every object slightly too near, including the ones that were correct.
Revisit with the Evaluation role once N4 can be measured against real ground truth. **N4 is the test that would catch it**: it measures per-object ordering *after* this median, so adopting either mitigation is a change N4 can score rather than a matter of taste. N4a isolates whether a regression came from the depth model or from here.

**The test that keeps this honest** is in `.claude/skills/offline-suite`: fuse the same
detections against an inverted depth map and assert the outputs change. Every other
assertion here passes on a `fuse()` that returns a constant.

---

## 5. Latency budget — N1 (p95 = 400 ms)

### What this budget is measured against, and what it is not

> **N1's reference device is the iOS Simulator on an Intel x86_64 Mac, and
> `docs/requirements.md` records it as a provisional dev-loop proxy, NOT a product claim.**
> That machine has no NPU, runs x86_64, and cannot use the Core ML or NNAPI delegate a phone
> would. **None of the numbers below are handset numbers**, and none may be quoted as one.
> `docs/requirements.md` schedules a re-baseline on real hardware in Lesson 05, and those
> numbers supersede these. The product device floor remains "a mid-range phone from three
> years ago" in `docs/artifact-budget.md` and is not redefined here.
>
> The reference-device decision is **still provisional** and this document does not close
> it. §8 states the branches.

**Network transit: 0 ms — none, by ADR 0001.** The worksheet this requirement descends from
assumes a client-observed latency over a link, and would require a transit line here. There
is no link. No stage in this pipeline opens a socket, for a model, a label set, or
telemetry. The term is zero structurally, not zero by optimization, and it is written down
rather than omitted so that a future reader cannot mistake its absence for an oversight.

### The critical path

Detection and depth have no data dependency (§1), so the middle of the pipeline is a
parallel block and the budget is a **critical path**, not a sum of every stage. Both
runtimes are native modules that execute off the JavaScript thread; the JS thread is free
during a native invoke. **This is an assumption (§9.6) and the single biggest risk to the
budget** — if the two runtimes serialize, the arithmetic below does not hold and N1 is
unachievable as written.

| # | Stage | Executes on | p95 allocation | Running total |
|---|---|---|---|---|
| 1 | Acquire: decode, EXIF-orient, downscale to SOURCE (B1→B2) | JS / native image lib | **40 ms** | 40 |
| 2 | Preprocess: two letterboxes, two normalizations, two tensor packs (B3, B4) | JS thread | **40 ms** | 80 |
| 3 | **Parallel inference block** (see below) | two native threads | **250 ms** | 330 |
| 4 | Fusion: scene understanding layer (B6+B8 → B9) | JS thread | **25 ms** | 355 |
| 5 | Overlay: SOURCE→SCREEN transform + first paint (B11) | JS + UI thread | **45 ms** | 400 |
| — | **Network transit** | — | **0 ms — none, by ADR 0001** | 400 |
| | **Total** | | **400 ms** | **= N1** ✔ |

Arithmetic: `40 + 40 + 250 + 25 + 45 + 0 = 400 ms`.

### Inside the parallel block

The block's cost is the **slower branch**, not the sum:

| Branch | Sub-stage | Allocation |
|---|---|---|
| Detection | TFLite invoke (int8, 640×640) | 95 ms |
| Detection | Decode + NMS in TS (B5→B6), incl. un-letterbox | 30 ms |
| | **detection branch total** | **125 ms** |
| Depth | ExecuTorch invoke (518×518) | 245 ms |
| Depth | DepthMap adapt: squeeze, non-pad vmin/vmax (B7→B8) | 5 ms |
| | **depth branch total** | **250 ms** |

`block = max(125, 250) = 250 ms`.

The detection branch finishes with **125 ms of slack**, which is where its TS-side decode
and NMS are paid for — they run on the JS thread while ExecuTorch is still working on its
own. The slack is real but it is not free capacity: it exists only as long as depth remains
the slower branch.

### p50 (N2 = 250 ms)

Same shape, scaled:

`25 (acquire) + 25 (preprocess) + 150 (block = max(75 det, 150 depth)) + 15 (fuse) + 35 (overlay) = 250 ms` ✔

### N6 — cold start ≤ 5 s

Budgeted separately, per `docs/requirements.md`, and **not** folded into N1:

`1.0 s (JS bundle + runtime init) + 1.5 s (TFLite model load + delegate warm) + 2.0 s (ExecuTorch .pte load) + 0.5 s (one warmup inference per model) = 5.0 s` ✔

The warmup inference is in the budget on purpose. Without it the first user-facing
inference pays lazy graph allocation and lands outside the N1 p95 — which would make N1's
"steady state" qualifier do work it should not have to.

### What I am flagging about this budget

1. **It has zero contingency.** The allocations sum to exactly 400 ms because the task
   requires them to. A real budget holds 10–15% back. Treat the first measurement that
   exceeds any line as a budget failure, not as noise.
2. **The depth line is the whole risk.** 245 ms for a ViT-based model at 518×518 on
   **x86_64 with no accelerator delegate** is optimistic, and I would not be surprised by
   2–4× that. If it misses, the levers in order of preference are: reduce the depth input
   to 392×392 or 252×252 (§9.2 — this is the single largest lever and requirements are
   silent on it); use a smaller Depth Anything V2 variant; re-baseline N1 on hardware that
   can actually use a delegate, which Lesson 05 already schedules.
3. **If the runtimes serialize, N1 as written is unachievable** on this reference device.
   Serial worst case: `40 + 40 + (125 + 250) + 25 + 45 = 525 ms`, which is 131% of target.
   That is the number to report if the parallelism assumption fails — not a quietly
   re-derived 400.
4. **`timings_ms` in `SceneResult` (B9) is how this gets checked**, per stage, in dev
   builds only. N15 forbids telemetry on the inference path, so these numbers are logged
   locally and never transmitted.

---

## 6. Module boundaries, designed to be mockable

**Requirement:** the default suite runs with **no GPU, no network, and no weights on disk**
(`.claude/skills/offline-suite`, N16). That is a constraint on the architecture, not on the
tests — a suite can only be offline if the seams let it be.

### The seam: models are behind Protocols, and the pipeline depends on the Protocol

```
inference/protocols.py

  class Detector(Protocol):
      def detect(self, tensor, letterbox) -> list[Detection]: ...

  class DepthEstimator(Protocol):
      def estimate(self, tensor, letterbox) -> DepthMap: ...
```

`pipeline.py` accepts a `Detector` and a `DepthEstimator` **as constructor arguments**. It
never imports `ultralytics`, `torch`, or `transformers`, and never constructs a concrete
model. The real implementations (`inference/detector.py`, `inference/depth.py`) import those
libraries **inside** their own modules, so that importing the pipeline does not drag a
1 GB dependency — and so that a bare checkout, which by design raises
`ModuleNotFoundError: ultralytics`, can still run the whole offline suite.

### What is pure and therefore trivially testable

These modules import **nothing heavier than numpy**, have no I/O, no clock, and no global
state. They are the majority of the logic, and they are 100% of the logic that is ported to
TypeScript:

| Module | Pure? | Tested with |
|---|---|---|
| `geometry/letterbox.py`, `geometry/spaces.py` | yes | Analytic round-trip: `source → model_input → source` is identity within float tolerance |
| `preprocess/*` | yes | Images generated in code by numpy/pillow |
| `inference/postprocess.py` (decode + NMS) | yes | Hand-built raw tensors with known boxes |
| **`fusion.py`** | yes | The known-gradient depth map — expected medians computed by hand |
| `contracts/*` | yes | Schema walked **programmatically**; assert no field name implies a metric unit |
| `pipeline.py` | yes, given fakes | Fake `Detector`/`DepthEstimator` returning canned values |

### What is not pure, and is therefore small on purpose

| Module | Impurity | Test strategy |
|---|---|---|
| `inference/detector.py` | loads weights, may use a GPU | `integration` marker. Thin — it adapts a library call to the Protocol and does nothing else |
| `inference/depth.py` | loads weights | `integration` marker. Same shape |
| `export/*` | writes artifacts | `integration` marker |
| `export/parity.py` | needs **both** the reference and the artifact — the one test that cannot be offline | `integration`. This is the exception the offline rule exists to make possible (N20) |
| `training/*` | GPU, MLflow, dataset | `integration`. Config construction is tested offline; the fit loop is not |

**The rule that makes this work: mock at the model boundary, never at the logic boundary.**
Mocking the fusion layer would delete the only thing worth testing.

### The app side

The same seam, one language over. `app/src/inference/detector.ts` and `depth.ts` export the
same two interfaces; `app/src/fusion/index.ts` is pure and takes plain data. A Jest run of
the fusion suite loads no native module, which is what lets it run in CI on a machine with
neither a simulator nor a `.tflite` file — and lets it read the **same**
`tests/fixtures/fusion_cases.json` the Python suite reads (B12, N21).

---

## 7. Rationale for the major choices

| Choice | Why | What it costs |
|---|---|---|
| Two deployment units with the artifact contract between them | ADR 0001 makes the model artifact the only shared surface. Naming it as a release boundary, with a manifest, makes a break visible at export time instead of at "why is the chair labelled a lamp" time | A manifest to keep current, and a parity test that must actually run |
| Boxes leave decode in **SOURCE** space, once, and never move again | Un-letterboxing is the highest-risk transform in the system. Doing it in exactly one place means there is exactly one place to get it wrong, and everything downstream has a single stated space | Decode is slightly fatter; it must carry `LetterboxParams` |
| `LetterboxParams` is a value carried with every tensor | A resized tensor without its scale and pad is an incomplete value. Making it a *pair* means the type system refuses to let you forget | Slightly noisier signatures |
| Depth map stays in its own grid, not upsampled to SOURCE | Interpolating 1.2 M pixels on the critical path to compute one median per box is work spent to throw away. §5 line 3 cannot afford it | Fusion must do a space conversion. This is why §4 step 1 exists |
| **Median over an eroded box** for fusion | Robust at a threshold rather than continuously; erosion removes the corners where background contamination lives. §4 | Fails on thin structures, stated openly |
| `relative_depth` is `float \| null`, never a sentinel | `0.0` is a legal relative inverse depth. A sentinel zero renders as "farthest object in the scene" and looks entirely plausible | Callers must handle null. Good |
| `depth_rank` alongside `relative_depth` | Gives the UI something orderable that it can never be tempted to print as a quantity. The raw value is unitless; the rank is honestly an ordinal | One more field |
| `SceneResult.status` is a 4-way union | F8 and N12 demand four distinguishable states. A boolean `ok` cannot express "depth failed but detection worked" | The UI must render four states |
| Models behind `Protocol`, injected into `pipeline.py` | The offline suite is a hard requirement, and it is an architectural property, not a testing technique | Dependency injection everywhere |
| Two independent letterboxes, not one shared canvas | Letterboxing to 640 and then resampling to 518 resamples twice and loses detail for no gain. Each model gets a direct SOURCE→input path | Two `LetterboxParams` in flight; they must not be confused (§2 rule 3) |
| `models.manifest.json` shipped beside the artifacts | F7 needs model versions, and the app has no network to fetch them from. Hardcoding them in TypeScript guarantees they go stale | Export must write it; drift is possible but `sha256` makes it detectable |

---

## 8. OPEN — decisions this document deliberately does not make

Per the Architecture role's constraints: a design that resolves an open question by picking
quietly is worse than one that stops and states the branches.

### 8.1 MLflow hosting — **OPEN** (blocks N19)

| Branch | Architectural consequence |
|---|---|
| **Local file store** (`mlflow.set_tracking_uri("file://./mlruns")`) | Zero infrastructure. `mlruns/` is gitignored, so **run history is per-developer and dies with the laptop**; the `mlflow_run_id` in the artifact manifest (B10) then references something nobody else can resolve, and N19's "reproducible run" is reproducible only by its author |
| **Remote tracking server** (self-hosted or managed) | Run IDs and registry versions become globally meaningful, and the manifest's `registry_version` is checkable by CI. Costs a service, a credential (`MLFLOW_TRACKING_URI`, already in `.env.example`), and an availability question this project otherwise does not have |

**Why it does not block this design:** `training/tracking.py` reads the URI from the
environment and is the only module that touches MLflow. Both branches are the same code
with a different string. It **does** block the meaning of `manifest.mlflow_run_id`, so the
answer is needed before the first export ships an ID anybody relies on — Lesson 03.

### 8.2 Object taxonomy — **OPEN**, deferred to Lesson 02 step 10

Affects `num_classes` in B5, the `labels` array in B10, and `Detection.class_id`/`label`.
The design is insulated: the label list is **read from the manifest**, never hardcoded in
Python or TypeScript, and `num_classes` is derived from the tensor shape. Nothing above
changes when the taxonomy lands. What does change is every exported artifact, which is why
`artifact_drift.py` fires on taxonomy edits.

### 8.3 N1's reference device — **provisional**

| Branch | Consequence |
|---|---|
| **Intel Mac iOS Simulator** (current) | Measurable today. x86_64, no NPU, no Core ML delegate. `docs/requirements.md` already flags the risk that `react-native-executorch` may ship no x86_64 simulator slice, in which case N1 **cannot be measured as written** |
| **Apple Silicon device or arm64 Android emulator** | Delegate-capable; numbers begin to resemble a handset. Requires hardware not currently assumed |
| **A real mid-range handset** | The only branch that produces a product claim. This is what Lesson 05 schedules |

§5 is written against the first branch and says so. **I have not chosen among these**; the
budget is explicitly labelled a dev-loop proxy.

### 8.4 Whether two native runtimes are affordable at all

`docs/artifact-budget.md` flags this as unresolved and it is not mine to close. If the
combined native library size or peak RSS proves unacceptable, the fix is consolidation onto
one runtime, which **changes B3/B4/B5/B7 and the entire artifact contract**. The design is
arranged so the damage is contained to `inference/` and `preprocess/` — `fusion.py`,
`geometry/`, and every contract from B6 onward are runtime-agnostic by construction.

---

## 9. Assumptions

Every one of these is a place `docs/requirements.md` is silent and the design forced a
choice. None is a decision I am entitled to make permanently; each is written here so it can
be contradicted cheaply.

1. **Model variants: YOLO11n and Depth Anything V2-Small.** Requirements name the model
   families, not the sizes. `app/README.md` sketches `yolo11n_int8.tflite` and
   `depth_anything_v2s.pte`, which I have taken as indicative. The artifact budget will
   decide this for real.
2. **Depth model input is 518×518.** N1a specifies 640×640 for detection and says nothing
   about depth. 518 is the natural size for a ViT-S/14 backbone (37 patches × 14). **This is
   the single largest lever on the §5 depth line** and the first thing to change if that
   line misses.
3. **Depth normalization is ImageNet mean/std, RGB order.** Standard for this model family,
   but the authoritative value is whatever export writes into the manifest.
4. **Detection input is uint8 with in-graph quantization**, not float32 normalized. This
   follows from "int8 TFLite" but is not stated anywhere, and getting it backwards produces
   a black input and zero detections with no error.
5. **Letterbox pad value is 114 grey, pads centred.** The ultralytics convention. Requires
   the export and the app to agree; it is in the manifest for that reason.
6. **Both native runtimes execute off the JS thread and can overlap.** §5's parallel block
   depends entirely on this. It is the riskiest assumption in this document, it is unverified,
   and §5.3 states the serial fallback number (525 ms).
7. **The SOURCE frame is long-edge ≤ 1280 with aspect preserved**, not literally 1280×720.
   N7 says both; I read "1280×720" as the reference measurement image and "long-edge" as the
   rule. A 4:3 capture yields 1280×960. If the intent was a hard 1280×720 with a centre crop,
   that changes B2 and the crop would silently discard detections.
8. **The image view uses `contain` fit.** Requirements say nothing about presentation. Under
   `cover` the view crops, and boxes outside the visible area need a policy that does not
   exist yet.
9. **SCREEN is React Native density-independent points, not physical pixels.** Choosing
   pixels would make every box wrong by the device scale factor on exactly the devices
   nobody tests on.
10. **`erosion_fraction = 0.25` per side** (§4). No requirement informs this. Configurable,
    serialized into the fixtures, defaulted in one place.
11. **Confidence threshold 0.25, NMS IoU 0.45, class-agnostic NMS off, max 100 detections.**
    Requirements are silent on all four. Config, not constants; they belong to whoever tunes
    against N3 once the taxonomy exists.
12. **`models.manifest.json` is the F7 mechanism.** Requirements say the result reports the
    model versions; they do not say how the app learns them. With no network, a bundled
    manifest is the only honest source.
13. **Timings are collected in dev builds only** and never leave the device (N15).
14. **Depth inference runs on every image, unconditionally** — not skipped when zero objects
    are detected. F5 asks for a dense map for the whole image, and skipping it would make
    latency depend on scene content, which would make the p95 in §5 meaningless.
15. **Model artifacts are copied into `app/assets/models/` by a deliberate step**, not
    symlinked or built on demand. "What is in `assets/models/` is what runs" requires that
    the copy be an event somebody performs, which is the only thing `artifact_drift.py` can
    detect.

---

## 10. Traceability

| Requirement | Where this design satisfies it |
|---|---|
| F1, F2, F3 | B6 — `Detection` with label, confidence, `xyxy` SOURCE pixels |
| F4 | B9 — `SceneObject.relative_depth`; §4 |
| F5 | B8 — `DepthMap`, internal, not surfaced |
| F7 | B9 `model_versions`, from B10's manifest |
| F8 | B6 empty list is valid; B9 `status` union |
| F9, N11 | §1 — no socket anywhere inside deployment unit A |
| N1, N2, N6 | §5 |
| N1a | B3 |
| N7 | B2 |
| N12 | B9 `status` + `depth_status`; §4 failure table |
| N13 | B9 `status = "input_rejected"`; the rejecting stage is named in the payload |
| N14, N15 | §1; `timings_ms` dev-only |
| N16, N17 | §6 |
| N20 | `export/parity.py`, `integration`-marked |
| N21 | B12 — shared `fusion_cases.json` |
| N3 | `evaluation/detection_metrics.py` — provisional target, deferred with the taxonomy |
| **N4** | **§4 — measured on the OUTPUT of `fusion.py`, not on `DepthMap`.** Per-object ordering after the eroded-box median, so the thin-structure failure in §4's table is inside what N4 measures rather than invisible to it. `evaluation/depth_metrics.py` |
| N4a | `evaluation/depth_metrics.py` — dense, pixel-wise, on B8's `DepthMap` **before** fusion. Diagnostic only: separates a depth-model regression from a fusion regression |
