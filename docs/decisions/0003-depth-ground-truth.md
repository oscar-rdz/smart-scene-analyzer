# ADR 0003 — Depth ground truth: keep SUN RGB-D depth, versioned by manifest

- **Status:** accepted
- **Date:** 2026-09-13
- **Deciders:** Oscar Rodríguez

## Context

**The repository contradicts itself about whether depth ground truth exists.**
`docs/requirements.md` N4 and N4a specify Spearman ρ targets *against ground truth*
(ρ ≥ 0.85 per-object after fusion, ρ ≥ 0.90 pixel-wise before it).
`.claude/agents/evaluation.md` states flatly that depth has no ground truth in this
project and forbids manufacturing a depth metric. Both cannot hold. This is open decision
D-1 in `docs/roadmap.md` §8, and the roadmap requires it settled **before Lesson 02
exits**.

The forcing constraint is acquisition order, not storage. **Roboflow stores boxes,
polygons, keypoints and image labels — not depth maps** (`.claude/agents/dataset-engineer.md`).
So depth ground truth cannot ride along with dataset version 1, and the detection dataset
has already been uploaded. SUN RGB-D ships depth frames beside every RGB frame, and they
are on disk now in `data/raw/`. Deciding later means a second 6.4 GB acquisition and
conversion pass over a dataset we would have already discarded.

Without depth ground truth, N4 and N4a are unmeasurable in Lesson 03, unpromotable at the
Lesson 06 gate, and the fusion design's **openly stated** weakness — "median over an
eroded box… fails on thin structures" (`docs/architecture.md:625`) — becomes permanently
undetectable. The system would have a known failure mode that nothing can observe.

### What is actually on disk, verified by inspection

| | |
|---|---|
| Location | `data/raw/SUNRGBD/<sensor>/<subset>/<scene>/depth/` and `depth_bfx/` |
| Format | 16-bit single-channel PNG, same pixel dimensions as the registered RGB frame |
| Pairing | `SUNRGBDMeta2DBB_v2.mat` carries `depthpath`/`depthname` on every record, alongside `rgbpath`/`rgbname` |
| `depth` | raw sensor output. **Contains invalid (zero) pixels — 27.4% on a sampled kv2 frame**, 0.2% on kv1 |
| `depth_bfx` | hole-filled. Zero invalid pixels on every frame sampled |

Two properties of this data are traps, and both were confirmed by measurement rather than
taken from the dataset's documentation:

**1. The stored values are bit-rotated and must be decoded.** SUN RGB-D stores each
value rotated, recovered with `(v >> 3) | (v << 13)`. Decoding a sampled kv2 frame makes
the map **8× smoother** between horizontally adjacent pixels (mean neighbour difference
154.3 → 19.3), which is the signature of a correct decode: real depth maps are locally
smooth, a rotated array is not.

**2. Skipping the decode is *almost* harmless, which is what makes it dangerous.** On
kv1, kv2 and realsense the low three bits are zero, so the rotation reduces to a divide
by eight — monotonic, and therefore invisible to a rank correlation. **On xtion it is
not:** 1.41% of pixels carry non-zero low bits, so their relative order changes. xtion is
3,389 images, 34% of the dataset. An undecoded pipeline would pass every smoke test on
three sensors out of four and quietly return a slightly wrong ρ on the fourth.

### Why no unit conversion is required

N4 and N4a are **Spearman rank correlations**, which are invariant under any monotonic
transform. The pipeline's own output is relative inverse depth — unitless, unscaled,
comparable only within one image (`docs/taxonomy.md`'s sibling contract in `CLAUDE.md`).
Comparing ranks against the source's decoded values therefore never requires converting
either side to a physical scale, and no unit is ever named. This is what makes measuring
N4/N4a compatible with the project's depth vocabulary rule and the `units_guard` hook.

The one sign convention that must be stated: the pipeline's value is **inverse** depth
(larger is nearer) while the source's is direct (larger is farther). One side must be
negated before correlating, or ρ comes out near −1 and looks like total failure.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Keep depth in `data/`, versioned by a committed manifest** | N4/N4a stay measurable; data already on disk; no second acquisition; thin-structure weakness stays observable | A versioning path outside Roboflow, enforced by our own script rather than by a platform |
| **B. Drop it; record N4/N4a as unmeasurable** | Free, zero maintenance, resolves the contradiction immediately | The fusion layer's known weakness becomes permanently undetectable; the Lesson 06 promotion gate loses its depth criterion |
| **C. Store depth maps in Roboflow alongside the images** | One versioning system | **Not possible.** Roboflow does not store depth maps |
| **D. Keep the raw download and decide later** | Defers the work | This *is* the decision being deferred, and the roadmap requires it closed before the phase exits. "Later" is where the second acquisition pass comes from |

## Decision

**Keep the SUN RGB-D depth ground truth**, in gitignored `data/`, pinned to dataset
version 1 by a **committed manifest digest**.

Specifically:

1. **`depth_bfx` is the ground truth**, not `depth`. The raw frames carry up to 27.4%
   invalid pixels, and a pixel-wise ρ over a map that is a quarter holes measures the
   masking strategy more than the depth model. The cost is that `depth_bfx` values are
   partly inpainted rather than measured — recorded here as a known limitation, not
   hidden.
2. **Values are decoded with `(v >> 3) | (v << 13)` before any use.** Not optional; see
   xtion above.
3. **Ground truth is only ever consumed as ranks.** No unit is named, no scale is
   asserted, and no code converts these values to a physical quantity.
4. **`data/depth-v1/` holds one decoded frame per image in dataset version 1**, named by
   the same stem the converter assigned, so depth joins to detections by filename.
   Gitignored, like all of `data/`.
5. **The version marker is a manifest** — stem, source path, and `sha256` per frame —
   whose own `sha256` is recorded here. That single committed hash pins the entire set: a
   regenerated `data/depth-v1/` either reproduces the digest or it does not, which is the
   property Roboflow would otherwise have provided.

### The version marker

Built by `scripts/depth_groundtruth.py`, 2026-09-13, against dataset version 1.

| | |
|---|---|
| Frames | **9,890** — one per image in dataset version 1, no gaps |
| Location | `data/depth-v1/frames/<stem>.png`, gitignored |
| Size | 895 MB |
| Manifest | `data/depth-v1/manifest.json`, gitignored |
| **Manifest `sha256`** | **`1d0bb2856e28080eb425df03d7f502be3b8a8e5787bd58f18e978bfe258b6284`** |

Verify with `uv run python scripts/depth_groundtruth.py --verify`, which recomputes every
frame's hash and the manifest digest. It returns exit 1 on any mismatch — confirmed
against a deliberately corrupted frame, where a single flipped byte in 20 frames was
detected.

## Consequences

**Newly possible.** N4 and N4a become measurable, which makes the Lesson 06 promotion
gate's depth criterion real rather than aspirational, and makes the thin-structure failure
mode in `docs/architecture.md` §4 detectable instead of merely documented.

**Newly required.** A versioning path that no platform enforces. If `data/depth-v1/` is
rebuilt from a differently-extracted `data/raw/`, only the manifest digest will catch it —
so the verification step must actually run, not merely exist.

Depends on this decision:

- `docs/requirements.md` N4, N4a — no longer unmeasurable; the "provisional" caveat can be
  lifted once a measurement exists
- `.claude/agents/evaluation.md` — its "depth has no ground truth" statement is now
  **superseded for SUN RGB-D images**. It remains true for any image the app captures in
  the field, which is the case it was written about
- `docs/dataset-card-v1.md` — its "No depth ground truth is included" limitation must be
  amended to reference this ADR and the manifest digest
- `scripts/depth_groundtruth.py` (to be written) — builds and verifies the manifest
- `src/smart_scene_analyzer/` evaluation code in Lesson 03 — consumes ranks only
- `data/raw/` — **must not be deleted.** It is the only source for regenerating this

**Foreclosed.** Depth ground truth exists for SUN RGB-D frames only. The app's own
captures have none, so N4 can never be measured on real device input — only on the held-out
test split. Any claim about depth quality on user photographs remains unsupported, and
`.claude/agents/evaluation.md`'s prohibition on manufacturing a depth metric stands
undiminished there.

## Revisit when

- A depth model is adopted whose output is not monotonically related to inverse depth, at
  which point rank correlation stops being the right comparison and this ADR's
  no-unit-conversion argument no longer holds.
- The measured ρ on `depth_bfx` diverges materially from ρ on masked raw `depth`,
  indicating the inpainting is doing the work rather than the model — in which case the
  ground truth choice in decision 1 is wrong.
- Storage pressure forces a subset. The manifest makes a subset expressible; the digest
  would change and this ADR would need a successor.
