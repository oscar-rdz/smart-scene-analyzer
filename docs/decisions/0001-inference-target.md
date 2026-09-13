# ADR 0001 — Inference target: on-device, not cloud

- **Status:** accepted
- **Date:** 2026-09-13
- **Deciders:** Oscar

## Context

The Smart Scene Analyzer runs two models on every image: YOLO11 for detection and
Depth Anything V2 for monocular depth. Where those models execute is the single
largest architectural fork in the project — it determines whether there is a serving
container at all, whether a model update is a deploy or an app-store release, and
whether the pipeline can assume a network.

**The constraint that forced it is privacy: an image captured by this app must never
leave the device.** That is a product commitment, not a performance preference, and it
eliminates every option that puts a frame on a wire — including a self-hosted container
we control, since "we would only send it to our own server" is still sending it.

Two further constraints point the same way and would each be sufficient on their own,
but neither is the reason:

- **Cost.** Hosted inference bills per request (`CLAUDE.md` records hosted serverless
  at 500 seconds of execution per credit, self-hosted at 3,000 images per credit and
  explicitly "metered, not free"). This project has a hard lifetime budget of 20
  credits, and `docs/credit-budget.md` allocates **0.0** to Lesson 05 on the grounds
  that "the models run on the handset." A camera client makes far more requests than a
  `curl` loop, so a per-request rate against a fixed lifetime cap is unbounded exposure.
- **Offline operation.** The app is expected to work in airplane mode (requirement F9).

The non-obvious part is that on-device is the *expensive* option in engineering terms.
It buys the privacy property with an export toolchain, int8 quantization, two native
runtimes shipped in one binary, a device memory floor, and a model update that moves at
an app store's timetable rather than a deploy's. That bill is accepted knowingly.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A — Cloud, self-hosted container serving both models** | One codebase, one Python implementation, no export step, no per-platform validation; model updates are a deploy; zero per-image platform cost since the weights are ours | **Fails the privacy constraint — the image is uploaded.** Network round-trip per frame; requires a GPU-sized host; needs availability, scaling, and cold-start engineering; the app stops working offline |
| **B — Cloud, hosted API (detection served by Roboflow)** | No weights in our image, no GPU to size, least infrastructure work | **Fails the privacy constraint.** Also **bills per request** against a 20-credit lifetime cap with 0.0 allocated to Lesson 05; ties detection to a vendor's model and label order; still offline-fragile |
| **C — On-device (TFLite + ExecuTorch)** | **Satisfies the privacy constraint absolutely** — there is no upload path to audit or misconfigure; works offline; no per-image cost; no serving infrastructure | Forces per-platform export, quantization, and numerical parity validation of two models; ships two native runtimes (tens of MB); sets a device floor; a model bug becomes an app-store release; two implementations of the fusion layer must be kept in agreement |

## Decision

Both models run entirely on the handset via `react-native-fast-tflite` (detection) and
`react-native-executorch` (depth); no network call appears anywhere on the inference
path, for weights, labels, or telemetry.

## Consequences

**Easier:** no serving infrastructure, no availability or scaling target, no cold-start
container engineering, no per-request cost, and no upload path that could leak an image
through misconfiguration. `docs/requirements.md` N5 and N11 become inapplicable rather
than unmet, and the app ships with no credentials at all.

**Harder:** every model change now passes through export and quantization; correctness
must be proven twice, once against the PyTorch reference and once on the device; and the
fusion algorithm exists in two languages that can silently disagree.

**Forecloses:** server-side batching, hot-swapping a model without a release, and any
feature that needs a model too large for a mid-range phone.

**Files and configuration that now depend on this choice** — a future reversal has to
account for all of them:

| Path | Dependency |
|---|---|
| `CLAUDE.md`, `AGENTS.md` | State the no-network-on-the-inference-path rule and the artifact contract as standing constraints |
| `docs/requirements.md` | F9, N1, N1a, N5–N11 are all written for on-device; N5 and N11 have no meaning under a served architecture |
| `docs/artifact-budget.md` | Exists **only** because we ship models and two native runtimes to a device |
| `docs/credit-budget.md` | Allocates 0.0 credits to Lesson 05 on the strength of this decision |
| `.claude/hooks/units_guard.py` | Guards `app/` as well as `src/`, because depth is now computed on the device |
| `.claude/hooks/artifact_drift.py` | Exists to warn that bundled artifacts have diverged from the export config |
| `.claude/agents/mobile.md`, `.claude/agents/qa.md`, `.claude/agents/architecture.md` | Role boundaries assume the device runs inference and the export/app split is load-bearing |
| `.claude/skills/offline-suite/SKILL.md` | The no-GPU, no-network, no-weights test default follows from this |
| `pyproject.toml` | Dependencies are array/image/validation libraries only — "nothing here serves HTTP" |
| `README.md` | Describes the product as running entirely on the handset |

## Revisit when

Never, while "no image leaves the phone" is a product commitment. A faster or cheaper
cloud option does not reopen this — it fails the constraint regardless of its numbers.

Reopening requires withdrawing the privacy commitment itself, which is a product
decision and would supersede this ADR rather than amend it.
