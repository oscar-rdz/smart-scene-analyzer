# Requirements — Smart Scene Analyzer

> Adapted from the Lesson 01 requirements worksheet. The worksheet is written for a
> **served** architecture; this project runs both models on the handset, so the rows that
> described a serving container have been replaced by their on-device equivalents rather
> than filled in with fiction. Each substitution is marked **[on-device]** and says what it
> replaced.

## Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| F1 | The app accepts a single RGB image, captured or picked, and returns detected objects | Must |
| F2 | Each detection carries a class label and a confidence score | Must |
| F3 | Each detection carries a bounding box in `xyxy`, absolute pixels of the **source image** frame | Must |
| F4 | Each detection carries a relative depth value (`relativeDepth`) | Must |
| F5 | A dense relative-depth map is produced for the whole image | Should — internal to the scene layer; not surfaced as a product feature |
| F6 | Batch of images in one request | Won't — single-shot capture; there is no request |
| F7 | The result reports the model versions used (detection and depth) | Must |
| F8 | Zero detections renders as a successful empty result, visually distinct from "loading" and from "model failed to load" | Must |
| F9 | The whole path works in airplane mode | Must |

### Object taxonomy

`pending — see Lesson 02 step 10`

Deferred deliberately: the class list is a property of the dataset, and committing to
classes before the data exists risks a taxonomy the data cannot support. F1–F4 do not
depend on which classes are chosen.

### Out of scope

- Instance segmentation — boxes only
- Video, temporal tracking, or frame-to-frame association
- **Metric-scale absolute depth.** The system produces relative inverse depth: larger is
  nearer, no unit, no scale, comparable only within one image. The UI may order and shade
  by it; it may never print a distance
- Any server component on the inference path, including for labels or telemetry
- Multi-image or panoramic reconstruction

---

## Non-functional requirements

### Performance

| ID | Requirement | Target | How it is measured |
|---|---|---|---|
| N1 | End-to-end p95 latency, single 1280×720 image | **400 ms** | **[on-device]** Steady state, in-app instrumentation, iOS Simulator on the Intel x86_64 dev Mac. Excludes one-time model load (see N6). Replaces the worksheet's client-observed-over-a-link measurement: there is no link |
| N1a | Model input tensor prepared on device | 640×640 letterboxed from the 1280×720 source | **[on-device]** Replaces "upload size" — nothing is uploaded |
| N2 | p50 latency | 250 ms | Same conditions as N1 |
| N3 | Detection accuracy | mAP@50 ≥ 0.50 | Held-out test split, dataset version stated. Provisional until the taxonomy exists (Lesson 02) |
| N4 | **Per-object** depth ordering, measured **after fusion** | Spearman ρ ≥ 0.85 between fused `relativeDepth` and ground-truth object ordering, per image | Held-out test split, over the objects the detector found. This is the number the product renders — see the note below |
| N4a | Dense depth-model quality, **before fusion** | Spearman ρ ≥ 0.90 pixel-wise against ground truth, per image | Held-out test split. A **diagnostic for the depth model alone**, not a product requirement |
| N5 | Throughput | n/a | **[on-device]** No server, no concurrency. Replaces "req/s at concurrency" |
| N6 | Time to first usable inference after cold app launch | ≤ 5 s | **[on-device]** Both runtimes initialized and both models loaded. Replaces the worksheet's container cold start |

> **⚠️ N1's measurement environment is a dev-loop proxy, not the product target.** The
> iOS Simulator on an Intel Mac has no NPU, runs x86_64, and cannot use the Core ML or
> NNAPI delegates a phone would. A number measured there does **not** predict handset
> behaviour and must not be quoted as a product claim. It is chosen because it is
> measurable today on the hardware that exists. **Lesson 05 re-baselines N1 and N6 on a
> real device, and those numbers supersede these.**
>
> The **product** device floor is unchanged and lives in `docs/artifact-budget.md`: a
> mid-range phone from three years ago. This requirement does not redefine it.
>
> Risk to verify in Lesson 05: `react-native-executorch` may not ship an x86_64 simulator
> slice. If it does not, N1 cannot be measured as written and the fallback is an Apple
> Silicon device or an Android emulator with an arm64 image.

> **Why N4 is split, and why it is measured after fusion.** The product never renders a
> dense depth map — F5 is internal. It renders **one `relativeDepth` per object**, derived
> by the fusion layer from a box and the dense map. Those two quantities fail
> independently: a depth map with excellent pixel-wise rank correlation can still yield the
> wrong *object* ordering, because the error is introduced downstream by the eroded-box
> median. `docs/architecture.md` §4 documents exactly this case — thin or skeletal
> structures (a floor lamp, a chair seen from the side) whose median lands on the
> background, so the object reads as farther than it is.
>
> A single dense metric cannot detect that. **N4 therefore measures per-object ordering
> after fusion**, which is what the user sees and what the known failure mode corrupts;
> **N4a keeps the dense metric as a separate diagnostic** so that a regression can be
> attributed — depth model, or our fusion of it. One number asked to answer both questions
> answers neither.
>
> **Why ordering at all.** Depth Anything V2 returns relative inverse depth with no
> scale, so the usual metric-depth statistics (δ<1.25, AbsRel) are not directly computable
> — they presuppose a scale this model does not have. Rank correlation measures the thing
> the product actually uses: whether the chair is correctly nearer than the wall. If a
> number comparable to published benchmarks is wanted later, compute δ<1.25 **after**
> least-squares scale-and-shift alignment and say that is what was done.

> **Why the model load is budgeted separately.** Folding a multi-second one-time load into
> a per-image p95 would let one startup cost dominate a number meant to describe steady-state
> responsiveness, and the two are fixed by different things — N1 by model size and whether
> the two inferences overlap, N6 by runtime initialization and file I/O. They are also felt
> differently: N6 is a spinner the user sees once, N1 is the interaction.

### Resource constraints

| ID | Requirement | Target |
|---|---|---|
| N7 | Max input image accepted | 12 MP from the picker; downscaled to 1280×720 long-edge before the pipeline |
| N8 | Peak app RSS with both models loaded | **[on-device]** Budget set in `docs/artifact-budget.md` before the first build. Replaces "serving container memory ceiling" |
| N9 | Delivered install size, per platform | **[on-device]** Budget set in `docs/artifact-budget.md`. Replaces "serving image size ceiling" |
| N10 | GPU required? | **[on-device]** No discrete GPU. Device accelerator delegate per platform, with a CPU fallback path that must still produce correct output. Replaces "GPU required for serving" |

> N8 and N9 are intentionally not given numbers here. `docs/artifact-budget.md` is the
> ledger that owns them, and duplicating a budget into two files is how the two disagree.

### Reliability and operations

| ID | Requirement | Target |
|---|---|---|
| N11 | Availability | **[on-device]** No service to be available. The functional equivalent is F9: the app works with no network at all. Replaces the availability percentage |
| N12 | A model fails to load | Fail **visibly and per branch**. If depth fails, degrade to detection-only and say so on screen; if detection fails, surface the failure rather than rendering an empty scene. Never silently indistinguishable from zero detections |
| N13 | Malformed, oversized, or unreadable image | **[on-device]** In-app error state naming which stage rejected it. Replaces the HTTP code and response shape |
| N14 | Are images retained? | **No.** No image leaves the device, and none is persisted beyond the session unless the user explicitly saves a result |
| N15 | Structured logging | Yes in development builds. **No telemetry on the inference path**, and nothing that blocks a result |

### Development quality gates

| ID | Requirement | Target |
|---|---|---|
| N16 | Test coverage on `src/` | ≥ 85% |
| N17 | Type checking | `mypy --strict` passes on `src/` |
| N18 | Every PR passes CI before merge | Yes |
| N19 | Reproducible training runs | Seed, dataset version, and config recorded in MLflow |
| N20 | Export parity | The exported artifact and the PyTorch reference agree on shared fixtures within a stated tolerance, as a test |
| N21 | Fusion port parity | `app/src/fusion/` reproduces `src/smart_scene_analyzer/fusion.py` on the **same** fixtures |

---

## Open decisions blocking this document

| Decision | Blocks | Status | ADR |
|---|---|---|---|
| Inference target: cloud vs. on-device | N1, N7–N11, the whole architecture | decided — on-device | `docs/decisions/0001-inference-target.md` |
| N1: which side of the network, on what link | N1, N2, the latency budget | decided — moot; there is no network. N1 is in-app and device-stated | — |
| N1 reference device | N1, N2, N6 | **provisional** — Intel Mac iOS Simulator as dev-loop proxy; re-baselined in Lesson 05 | — |
| MLflow hosting | N19 | **open** | — |
| Object taxonomy | F-list, all of Lesson 02 | **open** — deferred to Lesson 02 step 10 | — |
| N3 / N4 / N4a accuracy targets | N3, N4, N4a | **provisional** — revisit once the taxonomy and dataset version exist | — |

> Mobile app: real client or stub is **decided** — a real Expo client for iOS and Android,
> built in Lesson 05. On-device inference then removes the link-characteristics question
> the worksheet raises for N1, and replaces it with a device question instead.
