# Roadmap — Smart Scene Analyzer

- **Status:** engineering plan, written after `docs/architecture.md` and constrained by
  `docs/decisions/0001-inference-target.md`.
- **Author:** Architecture role.
- **Designed against:** `docs/requirements.md` (F1–F9, N1–N21), `docs/architecture.md`
  (boundaries B1–B12), `docs/credit-budget.md`, `docs/artifact-budget.md`, and the role
  definitions in `.claude/agents/`.

> **This plan contains no dates, no durations, and no effort estimates, deliberately.**
> The "Week N" labels are the course's phase names and carry no schedule claim. What this
> document asserts is **order and dependency**: which artifacts must exist before which
> other artifacts can be produced. A phase is done when its exit artifacts exist and can
> be checked by someone who was not present — not when someone judges the work finished.
>
> Every deliverable below is named as a **file, a registry entry, or a filled row in a
> ledger**. "Trained the model" is not a deliverable. `docs/model-card-*.md` recording
> mAP@50 on the test split of a named dataset version is.

---

## 0. Where the project actually stands

Stated here because several phases' entry conditions are "the previous phase's output
exists", and the baseline needs to be honest.

| Area | On disk now |
|---|---|
| `src/smart_scene_analyzer/` | 33 modules. **Docstrings only — no function bodies.** The design exists; the reference implementation does not |
| `tests/` | Exactly one test file, `test_units_guard.py`, which tests a **hook**. Nothing in the pipeline is covered |
| `app/` | `app.json`, `metro.config.js`, `README.md`. **No `package.json`.** Nothing is buildable |
| `.github/workflows/ci.yml` | lint → format → typecheck → `pytest -m "not integration"`. No coverage gate, no parity job, no artifact-size check |
| `data/`, `docs/taxonomy.md`, `app/assets/models/`, MLflow runs | Do not exist |
| `docs/artifact-budget.md` | Every Target cell is **blank** |
| `docs/credit-budget.md` | 20.0 remaining, ledger empty |

Two documents already reference files that do not exist, and this is the plan's first
concrete dependency rather than an error to fix in passing:
`.claude/agents/dataset-engineer.md` requires every dataset version to enforce
`docs/taxonomy.md`, and `.claude/agents/data-pipeline.md` writes into `scripts/`.
Both land in Week 2.

---

## 1. Roles — what exists, and the gaps that are not missing files

Every role named in `CLAUDE.md`'s table resolves to a definition. **No role file needs to
be created.** One detail is worth stating because the table reads as though eleven files
exist and ten do:

| Role in `CLAUDE.md` | Definition | Note |
|---|---|---|
| Architecture | `.claude/agents/architecture.md` | |
| Documentation | `.claude/agents/documentation.md` | |
| DevOps | `.claude/agents/devops.md` | |
| Dataset Engineer | `.claude/agents/dataset-engineer.md` | |
| Data Pipeline | `.claude/agents/data-pipeline.md` | |
| ML Engineer | `.claude/agents/ml-engineer.md` | |
| Evaluation | `.claude/agents/evaluation.md` | No `Edit`, by design |
| **Export** | `.claude/agents/ml-engineer.md` | **Shares the ML Engineer's file.** Not a separate agent — the same definition owns training *and* export |
| QA | `.claude/agents/qa.md` | |
| Integration | `.claude/agents/integration.md` | |
| Mobile | `.claude/agents/mobile.md` | |

What *is* missing is not files but **ownership of three things**, each of which this plan
has to assign to proceed. All three are flagged again in §8:

1. **`geometry/`, `preprocess/`, `contracts/`, and `config.py` have no owner in any role
   file.** They are the pure spine of the reference implementation and every role touches
   their output. This plan assigns them to **Integration**, on the grounds that
   `.claude/agents/integration.md` already owns "reconcile resolutions explicitly" and the
   coordinate spaces are the thing most likely to be wrong. That assignment is a proposal,
   not a decision.
2. **The device-vs-reference report has no owner.** By design neither Mobile nor Export
   may settle a disagreement alone. This plan assigns the *report* to **Evaluation**
   (it measures and reports, and it holds `Write` for exactly this), with the device-side
   numbers produced by Mobile and the reference-side numbers by Export.
3. **The promotion gate has no owner.** Evaluation owns the thresholds and cannot `Edit`;
   DevOps can `Edit` and does not own metrics. This plan assigns the *code* to **DevOps**
   and the *numbers it compares against* to **Evaluation**, recorded in an ADR so the
   split is visible rather than improvised.

---

## 2. Week 2 — Dataset Engineering

**Owning roles:** Dataset Engineer (platform), Data Pipeline (local code), Documentation
(taxonomy and dataset card prose).

### Deliverables — artifacts

| Artifact | Owner |
|---|---|
| `docs/taxonomy.md` — the class list with **explicit, numbered `class_id` order**. This order becomes `labels` in `models.manifest.json` (B10) and is the thing an app built against last week's export gets wrong | Dataset Engineer |
| `docs/decisions/0002-object-taxonomy.md` — the ADR recording which classes and **why those and not others** | Dataset Engineer |
| A Roboflow project and **dataset version 1**, with its integer version number written down | Dataset Engineer |
| `docs/dataset-card-v1.md` — per-class instance counts per split, image counts per split, and the preprocessing and augmentation steps with their parameters | Dataset Engineer |
| `scripts/convert_<source>_to_yolo.py` — converter with a docstring naming the exact input layout | Data Pipeline |
| `scripts/validate_dataset.py` — file counts per split, label/image pairing, coordinate ranges, class IDs inside the taxonomy | Data Pipeline |
| `docs/conversion-report-v1.md` — records in, out, skipped by reason, class distribution | Data Pipeline |
| A resolved storage and versioning path for **depth ground truth**, recorded as an ADR (see §8, open decision D-1) | Dataset Engineer + Architecture |
| Filled rows in `docs/credit-budget.md`, each with `Actual` completed | Dataset Engineer |

### Entry conditions

- `docs/decisions/0001-inference-target.md` is accepted (it is).
- `docs/credit-budget.md` parses: the `| **Remaining** | <number> |` row is numeric and
  above the 0.5 reserve floor. `credit_gate.py` reads this and refuses otherwise.
- `uv sync --extra dataset` resolves and imports `roboflow`, `h5py`, `scipy`.
- The object taxonomy decision (D-2) is **resolved before the first version generation**,
  not after.

### Exit criteria — checkable without having been present

1. `docs/taxonomy.md` exists and lists N classes in an explicit numbered order, and
   `docs/decisions/0002-object-taxonomy.md` exists with status `accepted`.
2. A Roboflow dataset version with a specific integer version number exists, and that
   number appears in `docs/dataset-card-v1.md`. The card states per-class instance counts
   for train / valid / test, with no class at zero instances in the test split.
3. Every class name in the dataset card appears in `docs/taxonomy.md`, and vice versa —
   comparable by reading two files.
4. `uv run python scripts/validate_dataset.py <export-path>` exits 0, and
   `docs/conversion-report-v1.md` reconciles: `records_in == records_out + records_skipped`,
   with every skip reason named.
5. `docs/credit-budget.md` has **zero rows with a numeric `Estimated` and a blank
   `Actual`**, `Remaining` is ≥ 16.0, and `Last reconciled` carries a date.
6. An ADR exists stating where depth ground truth lives and how it is versioned — **or**
   stating that no depth ground truth will be acquired, in which case it also records that
   N4 and N4a are unmeasurable and what replaces them.

### Dependencies

None on an earlier phase. This is the first phase that spends credits and the first that
produces anything downstream consumes.

### Risk most likely to derail this phase

**Depth ground truth has no storage path, and the repository currently contradicts itself
about whether it exists at all.** `docs/requirements.md` N4 and N4a specify Spearman ρ
targets *against ground truth*. `.claude/agents/evaluation.md` states flatly that "depth
has no ground truth in this project" and forbids manufacturing a depth metric.
`.claude/agents/dataset-engineer.md` states that Roboflow stores boxes, polygons,
keypoints and image labels — **not depth maps** — and says to escalate. Meanwhile
`pyproject.toml`'s `dataset` extra pulls `h5py` ("NYU Depth V2 ships as HDF5") and `scipy`
("SUN RGB-D ships MATLAB `.mat` metadata"), which are the dependencies of a depth ground
truth path nobody has written down. If this is not settled here, N4 and N4a are
unmeasurable in Week 3, unpromotable in Week 6, and the whole fusion design's known
weakness (thin structures, `docs/architecture.md` §4) becomes undetectable.

**Early warning sign:** the first version of `docs/dataset-card-v1.md` can state per-class
box counts and has **no row for depth**. More precisely: `uv sync --extra dataset` installs
`h5py` and `scipy`, and nothing in the plan names a directory those two libraries read from
that carries a version number the way `data/v1` does.

---

## 3. Week 3 — Model Development

**Owning roles:** ML Engineer (training, MLflow, the depth reference), Integration (the
pure spine — see §1 gap 1), Evaluation (model card and metrics).

### Deliverables — artifacts

| Artifact | Owner |
|---|---|
| Implemented `src/smart_scene_analyzer/geometry/letterbox.py`, `geometry/spaces.py`, `preprocess/*`, `contracts/*`, `config.py` — the pure modules every later phase indexes into | Integration |
| Implemented `training/detector.py`, `training/tracking.py` | ML Engineer |
| Implemented `inference/protocols.py`, `inference/detector.py`, `inference/depth.py`, `inference/postprocess.py` | ML Engineer |
| An **MLflow registered model version** for detection, with the run recording seed, dataset version number, base checkpoint, and every hyperparameter (N19) | ML Engineer |
| `docs/model-card-yolo11-detection.md` — per-class precision/recall/AP, mAP@50, mAP@50-95, instance counts, the split and dataset version named, the confidence threshold named, and a **known failure modes** section | Evaluation |
| `docs/decisions/000N-mlflow-hosting.md` — the ADR closing D-3 | DevOps + ML Engineer |
| `docs/model-card-depth-anything-v2.md` — stating that the output is relative inverse depth, larger is nearer, unitless, and what was and was not measured | Evaluation |
| An updated `docs/requirements.md` row for N3/N4/N4a converting "provisional" into a target justified by the dataset that now exists | Evaluation |

### Entry conditions

- Week 2's exit criteria all hold. In particular `docs/taxonomy.md` is frozen: training
  against a class list that later changes invalidates the checkpoint and every downstream
  artifact.
- **`uv sync --extra ml` resolves on the actual development machine.** See the risk below —
  this is an entry condition and not a detail.
- `uv sync --extra depth` resolves and `transformers` + `timm` can load a Depth Anything V2
  checkpoint.
- D-3 (MLflow hosting) is resolved, or the first run is knowingly disposable.

### Exit criteria — checkable without having been present

1. An MLflow registered model named for detection exists at an explicit version number,
   and that version number is quoted in `docs/model-card-yolo11-detection.md`.
2. The model card states `mAP@50` **and** a per-class AP table, computed on the **held-out
   test split of dataset version `<N>`** at a stated confidence threshold, with the MLflow
   run ID printed. A reader can open that run and find the number.
3. That MLflow run's parameters include `seed`, `dataset_version`, and the base checkpoint.
   N19 is satisfied when a second person can read all three out of the run record without
   asking anyone.
4. `uv run mypy src` exits 0 under `strict` on every module implemented in this phase.
5. `uv run pytest -m "not integration"` exits 0 with `ultralytics`, `torch`, and
   `transformers` **absent from the environment** — proving the Protocol seam in
   `docs/architecture.md` §6 actually holds and that `pipeline.py` never imports a model
   library.
6. `docs/model-card-depth-anything-v2.md` contains no metric that presupposes a scale, and
   says in prose why (the model returns relative inverse depth).
7. `docs/decisions/000N-mlflow-hosting.md` exists with status `accepted`.

### Dependencies

- Week 2's taxonomy fixes `num_classes` at boundary B5 and `labels` at B10.
- Week 2's dataset version is the only thing a metric in the model card can be quoted
  against.

### Risk most likely to derail this phase

**RESOLVED before the phase began — recorded because the constraint still binds.**
`pyproject.toml` originally pinned `torch>=2.5`, and the dev machine is an Intel x86_64
Mac. PyTorch's last macOS x86_64 wheel is **2.2.2**, verified against PyPI, so that pin was
unsatisfiable here. `torch` is the reference implementation Week 4's parity test compares
the exported artifacts against, so no torch would have meant no reference, N20 unsatisfiable,
and Weeks 4-6 resting on an export nobody compared.

Fixed with platform markers rather than a global downgrade: `torch==2.2.2` plus `numpy<2`
on `darwin`/`x86_64`, `torch>=2.5` everywhere else, so CI and any Apple Silicon machine are
unaffected. Verified: `uv sync --extra ml` installs and `torch.randn(2,3) @ torch.randn(3,2)`
runs.

**The same ceiling caught a second, quieter failure.** `transformers` 5.x requires
`torch>=2.5` and, below it, **disables torch silently** — `is_torch_available()` returns
False and the library reports "PyTorch was not found" while torch is installed and working.
Depth Anything V2 would have been unloadable for a reason naming the wrong cause. The
`depth` extra is now capped `transformers<5` on the same platform; verified
`is_torch_available()` is True at transformers 4.57.6.

**What still binds:** this machine is pinned to a 2023 torch. Any future dependency
requiring `torch>=2.4` hits the same wall with no upgrade path, because there is no newer
macOS x86_64 wheel to move to. The escape is different hardware, not a different pin.

**Early warning sign:** the first `uv sync --extra ml` on the dev Mac prints a resolution
error mentioning `torch`, **or** — the more dangerous variant — succeeds by selecting a
source distribution and starts a long compile. Either output, on the first run, is the
signal. A second sign appears later and is worse: a `torch` version resolved by accident
rather than chosen, recorded nowhere, silently becoming the reference that Week 4's
tolerance is measured against.

---

## 4. Week 4 — Export, quantization, parity, and the fusion layer

**Owning roles:** Integration (fusion reference + shared fixtures), ML Engineer wearing the
Export hat (`.claude/agents/ml-engineer.md`), QA (the suite), DevOps (CI gates),
Evaluation (the quantization delta report).

### Deliverables — artifacts

| Artifact | Owner |
|---|---|
| Implemented `src/smart_scene_analyzer/fusion.py` — pure, with `FusionConfig.erosion_fraction` defaulted in exactly one place | Integration |
| Implemented `src/smart_scene_analyzer/pipeline.py`, taking `Detector` and `DepthEstimator` as constructor arguments | Integration |
| `tests/fixtures/fusion_cases.json` — plain JSON, analytic-gradient depth grids, boxes in SOURCE pixels, `LetterboxParams`, and expected `relative_depth` per box **computed by hand** (B12) | Integration |
| Implemented `export/tflite.py`, `export/executorch.py`, `export/manifest.py`, `export/parity.py` | Export (ML Engineer) |
| `app/assets/models/yolo11*_int8.tflite` and `app/assets/models/depth_anything_v2*.pte` (gitignored binaries, present on disk) | Export |
| `app/assets/models/models.manifest.json` — **committed**, since it is the artifact contract made machine-readable and `.gitignore` excludes only the binaries | Export |
| `tests/` — one test file per implemented `src/` module, plus `tests/conftest.py` with image fixtures generated in code | QA |
| `tests/test_export_parity.py`, marked `integration`, with the accepted tolerance in its docstring and its justification | QA + Export |
| `docs/model-card-yolo11-detection.md` updated with the **per-class** int8-vs-fp32 confidence and AP delta, and the calibration set named | Evaluation |
| `docs/artifact-budget.md` with the detection model, depth model, and bundled-total rows carrying **both** a Target and a Measured figure | Export + DevOps |
| `.github/workflows/ci.yml` extended with a coverage gate (`--cov-fail-under=85`, N16) | DevOps |

### Entry conditions

- A registered detection model version exists (Week 3) and the taxonomy is frozen (Week 2).
- **`docs/artifact-budget.md`'s Target cells are filled in before the first export runs.**
  The file states its own rule: "a target chosen after seeing the number is not a budget,
  it is a description." Filling targets after the first `.tflite` exists forfeits the only
  thing the budget does.
- The export toolchain's dependencies are agreed and added to `pyproject.toml` as an
  explicit extra. Neither an ExecuTorch exporter nor a TFLite converter is declared
  anywhere in `pyproject.toml` today.
- D-4 (are two native runtimes affordable) has at least a **measured native library size**,
  even if the decision is not yet closed — see the risk.

### Exit criteria — checkable without having been present

1. `app/assets/models/models.manifest.json` exists, and its `detection.labels` array equals
   the class list in `docs/taxonomy.md` **element for element, in order**. A diff of the two
   is the check.
2. Each `sha256` in the manifest matches the file it names, verifiable with `shasum -a 256`
   against the two binaries on disk.
3. `uv run pytest -m integration -k parity` exits 0. The test's docstring states a numeric
   tolerance and says whether that tolerance was chosen before or after seeing the results.
4. The depth half of the parity test asserts on **rank correlation**, not on values —
   checkable by reading the assertion. An assertion comparing depth magnitudes across two
   runtimes is a reject, because the output has no scale.
5. The detection half of the parity report contains a **per-class** delta table, not only an
   aggregate.
6. `uv run pytest -m "not integration" --cov=src --cov-fail-under=85` exits 0, and the same
   invocation is a job in `.github/workflows/ci.yml`.
7. Every module under `src/smart_scene_analyzer/` has a matching file under `tests/` —
   checkable by listing both trees.
8. `tests/fixtures/fusion_cases.json` loads as plain JSON with no NumPy or pickle payload,
   and contains at least one case for each row of the failure table in
   `docs/architecture.md` §4, including the degenerate box that must yield `null` and not
   `0.0`.
9. `docs/artifact-budget.md` rows for detection model, depth model and bundled total each
   have a non-empty Target, a non-empty Measured, and a date.

### Dependencies

- Week 3's checkpoint is the thing being exported and the reference being compared against.
- Week 2's taxonomy fixes the `labels` order that the manifest freezes.
- The fixture set produced here is consumed unchanged by Week 5 (N21) — it is not a test
  detail, it is the mechanism.

### Risk most likely to derail this phase

**The export toolchain is undeclared, and adding it can silently move the reference.**
`pyproject.toml` declares `ml` (`ultralytics`, `torch`, `mlflow`) and `depth`
(`transformers`, `timm`) and nothing that can produce a `.tflite` or a `.pte`. Both
converters carry their own hard pins on `torch`. The failure mode is not an install error —
it is a resolver that satisfies everything by **moving `torch` under the `ml` extra**, so
the PyTorch model the parity test calls "the reference" is no longer the PyTorch model the
checkpoint was trained and validated with. The parity test then passes, comparing an
artifact against a reference that itself shifted, and reports agreement that means nothing.
`CLAUDE.md` requires asking before adding a dependency; that rule is doing real work here.

**Early warning sign:** the first `uv sync` after adding the export extra reports a
`torch` version different from the one recorded in the Week 3 MLflow run's environment —
or `uv.lock`'s diff for that sync touches the `torch` line at all. Either is the signal,
and it appears before a single export has been produced.

---

## 5. Week 5 — On-device inference and mobile delivery

**Owning roles:** Mobile (everything under `app/`), DevOps (the native build, bundling,
size accounting), Evaluation (the device-vs-reference report — see §1 gap 2).

### Deliverables — artifacts

| Artifact | Owner |
|---|---|
| `app/package.json` with **exact pinned versions** for the Expo SDK, `react-native-fast-tflite`, and `react-native-executorch` | DevOps |
| `app/App.tsx` — capture or pick, run, render | Mobile |
| `app/src/inference/detector.ts`, `app/src/inference/depth.ts` | Mobile |
| `app/src/fusion/index.ts` — the **port**, reading the same fixtures | Mobile |
| `app/src/geometry/toScreen.ts` — the single SOURCE → SCREEN function (B11) | Mobile |
| `app/src/components/DetectionOverlay.tsx` — four distinguishable `status` renderings plus the loading state (F8, N12) | Mobile |
| A jest configuration whose fixture path resolves to `tests/fixtures/fusion_cases.json` — **the same file**, not a copy | Mobile |
| `docs/device-parity-report.md` — device or simulator named, OS version named, the input image named, per-object rank agreement between app and reference, tolerance stated | Evaluation |
| `docs/artifact-budget.md` with Android install size, iOS install size, peak RSS with both models loaded, and cold model load filled — each with the method that produced it | DevOps |
| Re-baselined N1 / N2 / N6 figures in `docs/requirements.md`, each labelled **dev-loop proxy** or **product claim**, never ambiguous | Mobile |
| `docs/decisions/000N-bundle-identifier.md` — closing D-6 | DevOps |
| An ADR sanctioning the parity input image, closing D-5 | Architecture + QA |

### Entry conditions

- Both artifacts exist in `app/assets/models/` and were produced by the export step, not
  copied by hand (`.claude/agents/devops.md` is explicit; `artifact_drift.py` depends on
  the copy being a deliberate event).
- `models.manifest.json` is committed and its `sha256` values match those binaries.
- `tests/fixtures/fusion_cases.json` exists and the Python suite passes on it — the port
  has nothing to be checked against otherwise.
- D-5 resolved: there is a sanctioned, deterministic image both the device and the
  reference can run.
- D-6 resolved before the first `expo prebuild` anyone intends to keep.

### Exit criteria — checkable without having been present

1. `cd app && npx tsc --noEmit` exits 0.
2. `cd app && npm test` exits 0, and the jest config's fixture path points **outside**
   `app/`, at `tests/fixtures/fusion_cases.json`. A copied fixture file inside `app/` is a
   reject: it defeats N21 entirely, because two implementations of one algorithm reading
   two files are not being compared.
3. `cd app && npx expo run:ios` and `npx expo run:android` each produce an installed
   development build, and `app/package.json` pins exact versions (no `^`, no `~`) for the
   Expo SDK and both native runtimes.
4. A test file asserts that the four `SceneResult.status` values and the absent-result
   loading state produce five distinguishable renders (F8, N12).
5. `docs/artifact-budget.md`'s Android install size, iOS install size and peak-RSS rows
   each hold a number, a date, and the method that produced it. A figure whose method is
   not stated is a reject, per the file's own rule.
6. `docs/device-parity-report.md` records, for the sanctioned image: the app's per-object
   `relativeDepth` **ordering** and the reference's, the agreement between them, and the
   tolerance. Where they disagree, the report says which side is wrong or says that it is
   not yet known — it does not resolve the disagreement by changing either side.
7. N1, N2 and N6 appear in `docs/requirements.md` with measured numbers, the device named,
   and the dev-loop-proxy-or-product-claim label attached to each.

### Dependencies

- Week 4's manifest is the contract this phase consumes and may not modify.
- Week 4's fixture set is the only thing making the fusion port checkable.
- Week 3's reference implementation is the other side of the device-vs-reference report.

### Risk most likely to derail this phase

**`react-native-executorch` may ship no x86_64 simulator slice, and the only development
machine is an Intel Mac.** `docs/requirements.md` already flags this against N1, but the
consequence is larger than a missing measurement: if the depth runtime will not link into
an x86_64 simulator build, **the app cannot be run at all on the machine that exists**, and
every Week 5 exit criterion that depends on a running build becomes unreachable. The
fallbacks — an Apple Silicon machine, an arm64 Android emulator, or a physical handset —
are all hardware acquisitions, not code changes, and none of them is currently assumed.
Sitting behind this is D-4: `app.json` already sets `deploymentTarget: 17.0` and
`minSdkVersion: 26`, while `docs/artifact-budget.md` notes the ExecuTorch runtime's own
floor is iOS 17+ / Android 13+ — so the declared Android floor and the runtime's floor do
not currently agree.

**Early warning sign:** the first `npx expo run:ios` fails at the link step with an
"undefined symbols for architecture x86_64" error, or `pod install` output lists only
`arm64` slices for the ExecuTorch pod. Both appear at the **first native build**, before
any inference code is written — which is why the first deliverable of this phase should be
a build that does nothing but load both runtimes and print their versions.

---

## 6. Week 6 — CI / CD / CT

**Owning roles:** DevOps (workflows, promotion code), Evaluation (the numbers the promotion
gate compares against), ML Engineer (the training entry point CT invokes), QA (tests for
the gate itself).

### Deliverables — artifacts

| Artifact | Owner |
|---|---|
| `.github/workflows/ci.yml` extended: lint → format → typecheck → tests with coverage gate → export parity → artifact-size regression | DevOps |
| `.github/workflows/ct.yml` — continuous training, triggered on a new dataset version, producing an MLflow run | DevOps |
| `scripts/promote.py` — compares a candidate run against the incumbent on the **same dataset version, split and threshold**, and exits nonzero when it does not pass | DevOps |
| `docs/decisions/000N-promotion-policy.md` — the thresholds, where each came from, and the depth criterion (or an explicit record that none can be computed and why) | Evaluation + DevOps |
| `tests/test_promotion.py` — offline, driven by recorded metric fixtures, no network and no weights | QA |
| An artifact-size regression check that fails a PR when a bundled model exceeds its `docs/artifact-budget.md` target | DevOps |
| `docs/release-checklist.md` — what a human does to ship, given that `.claude/agents/devops.md` forbids the agent from pushing or submitting | DevOps + Documentation |
| A reconciled `docs/credit-budget.md`: `Remaining` matching the platform usage page, `Last reconciled` dated, zero pending rows | DevOps |

### Entry conditions

- Week 4's parity test passes and is runnable in CI. **This depends on D-3**: if MLflow is
  a local file store, a CI runner cannot fetch the checkpoint, and the parity job either
  cannot run or must rebuild the artifact in-job.
- N3 / N4 / N4a have been converted from provisional to actual targets (Week 3 exit), or
  the promotion policy ADR records which of them the gate cannot use.
- Credit balance is above the 0.5 reserve floor with enough headroom for the planned CT
  dry run.

### Exit criteria — checkable without having been present

1. A pull request shows the job list `lint → format → typecheck → test (coverage ≥ 85) →
   export parity → artifact size`, each as its own check, gated with `needs` so an
   expensive job never runs behind a cheap failure.
2. A branch that deliberately inflates a bundled model past its `docs/artifact-budget.md`
   target produces a **red** artifact-size check. The branch name and the run URL are
   recorded in the promotion-policy ADR. An untested gate is not a gate.
3. `ct.yml` has completed at least one run, and it produced an MLflow run whose parameters
   include the dataset version that triggered it.
4. `uv run pytest tests/test_promotion.py` exits 0 with no network and no weights on disk,
   and it includes a case where a candidate **improves aggregate mAP while regressing one
   class** and is correctly rejected.
5. `docs/decisions/000N-promotion-policy.md` exists with status `accepted` and names either
   a depth criterion or the reason there is none.
6. `docs/credit-budget.md` has zero rows with a numeric `Estimated` and blank `Actual`,
   `Remaining` is above 0.5, and `Last reconciled` carries a date.

### Dependencies

- Every earlier phase. Week 6 automates what Weeks 2–5 established by hand; a gate for a
  check that has never been run manually encodes a guess.
- The promotion gate's thresholds are Week 3's metrics and Week 2's taxonomy. Its depth
  criterion, if any, descends directly from Week 2's depth-ground-truth decision.

### Risk most likely to derail this phase

**The promotion gate will gate on the only metric it can compute, and that metric is not
the one the product renders.** Detection mAP is computable from the moment Week 3 ends.
N4 — per-object depth ordering measured *after fusion* — requires depth ground truth that
may not exist (Week 2's risk), and it is precisely the number that catches the fusion
layer's documented failure: thin and skeletal structures whose eroded-box median lands on
the background, so the object reads as farther than it is (`docs/architecture.md` §4).
A gate that checks mAP alone will happily promote a model whose object ordering has
regressed, because nothing it measures moved. This is how the project's known weakness
becomes permanent and invisible.

**Early warning sign:** the first draft of `scripts/promote.py` references `mAP@50` and no
depth criterion at all, and the promotion-policy ADR's depth row reads "TBD" rather than a
threshold or an explicit "cannot be computed, here is why". The moment "TBD" is acceptable
in that row, the gate's scope has been decided by omission.

---

## 7. Risks that cross every phase

Two constraints do not belong to any single phase and will not announce themselves.

### Credit exhaustion — the budget is a scheduling constraint, not a footnote

20 credits for the project lifetime, no top-up. `docs/credit-budget.md` allocates Week 2 =
4.0, Week 3 = 3.0, Week 4 = 2.0, Week 5 = 0.0, Week 6 = 4.0, buffer = 7.0. `credit_gate.py`
refuses any billed call unless a pending ledger row exists **and** the balance is above 0.5.
The structural danger is order: Week 6's continuous-training dry run is allocated 4.0 and is
spent **last**, so every overrun in Weeks 2–4 eats the phase that has no alternative. Running
out in Week 4 does not shrink Week 6 — it deletes it.

**Early warning sign:** the buffer being touched for the first time. The moment a phase's
`Actual` column exceeds its allocation in the Planned allocation table and the difference is
absorbed silently by the 7.0 buffer instead of being written down as a revision, the budget
has stopped being a plan. A second, sharper sign: `credit_gate.py` blocking a call — by then
the arithmetic was already wrong before the tool fired.

The most likely single overrun is GPU training at 1 credit per 30 minutes. Week 3's 3.0
allocation buys 90 minutes of hosted training in total. `.claude/agents/ml-engineer.md`
already directs training locally first for exactly this reason; hosted training is a
budgeted comparison, not the default path.

### The artifact budget is entirely blank

Every Target cell in `docs/artifact-budget.md` is empty, and the file states its own rule:
fill the targets in before the first build, because "a target chosen after seeing the number
is not a budget, it is a description." No hook can enforce this — there is no tool call to
intercept, and the failure surfaces as a build error or a crash on somebody else's device.

**Early warning sign:** the first `.tflite` or `.pte` existing on disk while the Target
column is still blank. At that instant the budget can no longer be set honestly, and the
two-native-runtimes question (D-4) loses the only measurement that could have answered it
before the design depended on the answer.

---

## 8. Blocked on decisions

Ordered by the phase they block. "Latest point" is the last moment at which the decision
can be made without discarding work that has already been done.

| ID | Open decision | Blocks | Branches, and what each costs | **Latest point it can be resolved** |
|---|---|---|---|---|
| **D-2** | **Object taxonomy** — deferred to Lesson 02 step 10, `docs/requirements.md` "Object taxonomy: pending" | The whole F-list; `num_classes` at B5; `labels` at B10; `Detection.class_id`; `docs/taxonomy.md`, which `.claude/agents/dataset-engineer.md` already requires and which does not exist | More classes: richer product, thinner per-class instance counts, more classes that can fall below a usable AP. Fewer: each better supported, less to show. Either way the **order** is frozen into the manifest | **Before Roboflow dataset version 1 is generated (Week 2).** A version is an immutable snapshot; changing the taxonomy afterwards costs another version generation, another credit charge, and invalidates any checkpoint trained on it |
| **D-1** | **Where depth ground truth lives, and how it is versioned** — *discovered by this plan.* Roboflow stores no depth maps; `.claude/agents/evaluation.md` says depth has no ground truth; `docs/requirements.md` N4/N4a specify ρ targets against ground truth. The repository contradicts itself | N4, N4a; the Week 3 depth model card; the Week 6 promotion gate's depth criterion; the detectability of the §4 thin-structure failure | (a) Acquire NYU Depth V2 / SUN RGB-D depth maps into gitignored `data/` with a hand-maintained version marker — a versioning path outside Roboflow that nothing enforces. (b) Drop N4/N4a and record that depth is qualitatively checked only — cheap, and the fusion layer's known weakness becomes permanently unmeasurable | **Before Week 2 exits.** It determines whether depth ground truth is acquired alongside the detection dataset; acquiring it later means a second data pass |
| **D-3** | **MLflow hosting** — `docs/architecture.md` §8.1, `docs/requirements.md` open table. The `TODO(Lesson 01)` marker is still live in `CLAUDE.md` and `AGENTS.md` | N19; the meaning of `manifest.mlflow_run_id` (B10); **and the Week 6 CI parity job**, which cannot fetch a checkpoint from a local file store | Local file store: zero infrastructure, `mlruns/` gitignored, run history dies with the laptop, and the run ID in the manifest references something nobody else can resolve. Remote server: run IDs and registry versions become globally meaningful and CI can check them; costs a service and a credential | **Before the first `models.manifest.json` is written in Week 4** — that is the moment an unresolvable run ID gets frozen into the artifact contract. Practically, before the first Week 3 run anything downstream consumes |
| **D-4** | **Whether two native runtimes are affordable at all** — `docs/artifact-budget.md` OPEN section | B3, B4, B5, B7 and the entire artifact contract. Also the device floor: `app.json` declares `minSdkVersion: 26` while the ExecuTorch runtime's own floor is Android 13+ | Keep both: the design as written. Consolidate onto one runtime (YOLO11 to `.pte`, or Depth Anything V2 to TFLite): both unverified, both a real workstream, and both change which format Week 4 exports to. `docs/architecture.md` contains the damage to `inference/` and `preprocess/` — `fusion.py`, `geometry/` and every contract from B6 onward survive either way | **Before Week 4 exports the artifacts in their final form.** The awkward part: the measurement that answers it (install size, peak RSS) only exists in Week 5. Mitigation — measure the two runtimes' native library sizes from a throwaway prebuild during Week 4's entry, before choosing export targets |
| **D-7** | **N3 / N4 / N4a accuracy targets** — provisional in `docs/requirements.md` until a taxonomy and a dataset version exist | The Week 3 model card's pass/fail claim; the Week 6 promotion gate's thresholds | A target set too low promotes anything; too high blocks every candidate and gets quietly lowered, which is worse | **Before `scripts/promote.py` is written (Week 6 entry).** Ideally at Week 3 exit, so the first model card states pass or fail rather than a number without a verdict |
| **D-8** | **N1's reference device** — provisional: the Intel Mac iOS Simulator, recorded in `docs/requirements.md` and `docs/architecture.md` §8.3 as a **dev-loop proxy and explicitly not a product claim** | N1, N2, N6 and the meaning of every latency figure | Intel Mac Simulator: measurable today, x86_64, no NPU, no Core ML delegate — **and may not be measurable at all if `react-native-executorch` ships no x86_64 slice** (§5's risk). Apple Silicon or arm64 emulator: delegate-capable, requires hardware not currently assumed. A real mid-range handset: the only branch that yields a product claim | **Before any latency number is written into a report or a README (Week 5).** A number published without its device attached cannot be un-published |
| **D-5** | **The device-vs-reference parity input image has no sanctioned home** — *discovered by this plan.* `CLAUDE.md` says do not commit images. `app/README.md` says inference runs on a bundled or picked still image, and that determinism is what makes the Lesson 05 parity check possible. Both cannot hold | The Week 5 device-vs-reference exit criterion | (a) Commit one small image as a deliberate, ADR-recorded exception to the no-images rule. (b) Generate it procedurally in both languages — hard to keep byte-identical through an encoder, and a decode difference would be indistinguishable from a fusion difference. (c) Drop the check, and lose the only evidence that the port and the reference agree on real data | **Before the first device-vs-reference run (Week 5).** It needs an ADR either way, because it is an exception to a standing rule in `CLAUDE.md` |
| **D-6** | **Bundle identifier and Android package name** — `app/app.json` carries the placeholder `com.smartsceneanalyzer.app` on both platforms | The Week 5 native build and anything downstream of signing | Keeping the placeholder is a choice, not a default. Changing it after a build invalidates installed builds and any signing setup | **Before the first `expo prebuild` you intend to keep (Week 5 entry)** |
| **D-9** | **Lesson 04's 2.0-credit allocation** — *discovered by this plan.* `docs/credit-budget.md` allocates 2.0 to "one hosted-API latency and cost comparison", an operation ADR 0001 forecloses from the product path | Week 4's budget, and 2.0 credits that Week 6 may need | (a) Spend it as a dev-time comparison that is explicitly not a product path — legitimate, but it is 2.0 credits of the 20 for a number that cannot change a decision ADR 0001 says never to reopen. (b) Return it to the buffer and record the reallocation | **Before Week 4 spends it.** Revising the allocation table deliberately is allowed; absorbing the difference silently is what the ledger exists to prevent |
| **D-10** | **Ownership of `geometry/`, `preprocess/`, `contracts/`, `config.py`** — *discovered by this plan.* No role file claims them | Week 3 implementation, which cannot start without an owner | This plan proposes Integration (§1). Alternatives: ML Engineer, or split by module — a split is the worst option, because the coordinate spaces are one design | **Before Week 3 implementation begins** |
| **D-11** | **Who owns the promotion gate's code, given Evaluation has no `Edit`** — *discovered by this plan* | Week 6 | This plan proposes DevOps writes the gate, Evaluation supplies the thresholds via the ADR. Giving Evaluation `Edit` would collapse the boundary `CLAUDE.md` calls load-bearing | **Before `scripts/promote.py` is written (Week 6 entry)** |

### Decisions that are closed — recorded here so they are not re-litigated

The Lesson 01 worksheet's "Blocked on decisions" template expects the **inference target**
to appear in this section. **For this repository it does not belong here, because it is
decided**, and listing a decided question as open would invite exactly the reopening the
ADR forbids. It is recorded as resolved instead:

| Decision | Resolution | Where |
|---|---|---|
| **Inference target: cloud vs. on-device** | **Decided — on-device.** Forced by privacy: an image captured by this app must never leave the device. Cost and offline operation point the same way but are not the reason. The ADR's "Revisit when" is *never*, while the privacy commitment stands; a faster or cheaper cloud option does not reopen it, because it fails the constraint regardless of its numbers | `docs/decisions/0001-inference-target.md`, status accepted |
| N1: which side of the network, on what link | **Moot.** There is no network on the inference path. N1 is measured in-app and is device-stated | `docs/requirements.md` |
| Mobile app: real client or stub | **Decided — a real Expo development build for iOS and Android**, not Expo Go, because both ML runtimes are native modules | `CLAUDE.md`, `app/README.md` |

Anything in the first table that resolves should become a numbered ADR in
`docs/decisions/` via `/adr <title>` **before** the work that depends on it starts, and this
table should then move that row down into the closed one.
