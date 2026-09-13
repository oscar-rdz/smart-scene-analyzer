# Contributing

This project is an early-stage scaffold — see the "Current status" section of
[`README.md`](README.md) before you start. Most of `src/smart_scene_analyzer/` is
docstrings and type signatures with no function bodies yet, and `app/` does not exist
until Lesson 05. That does not relax any of the gates below; it means most contributions
right now are filling in a stub, not extending working code.

## Development environment

```bash
git clone <this repository's URL> smart-scene-analyzer
cd smart-scene-analyzer
uv python install 3.11
uv sync
cp .env.example .env
```

Fill in `.env`:

```
ROBOFLOW_API_KEY=<your Roboflow API key, from app.roboflow.com/settings/api>
ROBOFLOW_WORKSPACE=<your Roboflow workspace slug>
```

`.env` is gitignored. `MLFLOW_TRACKING_URI` already defaults to a local server in
`.env.example`. None of these three variables is a runtime secret — they are dev-time
credentials for Roboflow and MLflow, and the shipped app carries none of them.

`uv sync` installs the base dependencies plus the `dev` group (`pytest`, `ruff`,
`mypy`) — not the model libraries. Add the extra your change actually needs, when it
needs it:

```bash
uv sync --extra dataset  # roboflow, h5py, scipy        (Lesson 02 work)
uv sync --extra ml       # ultralytics, torch, mlflow   (Lesson 03 work)
uv sync --extra depth    # transformers, timm           (Lesson 03 work)
```

Never `pip install` into the system interpreter, and never `uv add` a package to work
around a `ModuleNotFoundError` for a library that belongs in one of the extras above —
that error is often the environment behaving correctly.

For `app/` (Lesson 05 onward): `npm` installs the app's dependencies; `uv` never touches
`app/`, and `npm`/`node_modules` never touch `src/`.

## Branch naming

`<role-or-area>/<short-kebab-case-description>`, using the role names from the table
below where the work maps to one, or a short area name otherwise:

```
dataset-engineer/roboflow-project-setup
ml-engineer/yolo11-baseline-run
mobile/detection-overlay
docs/architecture-lesson-01
fix/letterbox-pad-value
```

`<short-kebab-case-description>` is a few words, lowercase, hyphen-separated, naming the
change — not the ticket number, if there is one (put that in the commit body instead).

## Commit messages

- Imperative mood, present tense: "Add letterbox round-trip test," not "Added" or
  "Adds."
- Summary line ≤ 72 characters. If the change needs more explanation, leave a blank
  line and write the body as prose.
- The body says **why**, not a restatement of the diff. If the change was forced by a
  requirement or an ADR, name it: "Per N21, run the same fixture set from both the
  Python and TypeScript fusion implementations."
- Reference the relevant module or requirement ID (`F4`, `N20`, `ADR 0001`) when the
  commit exists because of one.
- One logical change per commit. A stub gaining a docstring and a pipeline stage
  gaining a real implementation are two commits, even in the same PR.

## Gates a change must pass before review

Run all of these locally before opening a PR. There is no CI workflow configured in
this repository yet (`.github/` does not exist) — `docs/requirements.md` N18 sets
"every PR passes CI before merge" as a target for when the DevOps role adds one. Until
it exists, these commands **are** the gate, and running them is the contributor's
responsibility rather than a machine's.

```bash
uv run ruff format .                 # format
uv run ruff check .                  # lint
uv run mypy src                      # type check `src/`, strict mode (N17)
uv run pytest -m "not integration"   # the offline suite: no GPU, no network, no weights
uv run pytest                        # the full suite, if your change touches anything integration-marked
```

For a change to `app/` (once it exists):

```bash
cd app && npx tsc --noEmit           # type check the app
```

Additional gates that apply depending on what the change touches:

- **Every module in `src/` has a matching test file** (`CLAUDE.md` → Conventions →
  Testing). A new module without one is not done.
- **A change to `src/smart_scene_analyzer/fusion.py` requires the same fixture set
  (`tests/fixtures/fusion_cases.json`) to still pass on both sides** — the Python
  implementation and, once it exists, the TypeScript port in `app/src/fusion/` (N21).
  If they disagree, fix the port or record why the reference is wrong. Never edit the
  fixtures to make them agree.
- **A change to an export config** (`src/smart_scene_analyzer/export/`) needs its
  parity test (N20) run and passing before the artifact it produces is treated as
  correct — an export nobody compared against the reference is only known to run, not
  known to be right.
- **A change that touches depth values** must not introduce a metric unit —
  `.claude/hooks/units_guard.py` blocks the bare word `meters`/`metres` in `.py`,
  `.ts`, and `.tsx` under `src/` and `app/`, in code, comments, docstrings, and UI
  strings alike. If it blocks you, rename the thing; do not edit the hook.
- **A billed Roboflow operation requires a ledger row in `docs/credit-budget.md`
  first** — see `.claude/skills/credit-ledger`. `.claude/hooks/credit_gate.py`
  enforces this on tool calls made through Claude Code; it does not run for a human
  using the Roboflow UI or SDK directly, so the same discipline applies by hand there.

None of these gates are currently measurable as *numbers* on this codebase — there is
no coverage report and no trained model to hold `N16`'s 85% or `N3`/`N4`'s accuracy
targets against yet. Don't write a PR description that implies otherwise.

## Working with the `.claude/agents/` roles

Work is scoped to specialized subagents, each owning one slice of the system. Route a
change to the matching role, or read that role's file before doing the equivalent work
by hand:

| Role | Owns | Definition |
|---|---|---|
| Architecture | System design, folder structure, engineering plan | `.claude/agents/architecture.md` |
| Documentation | README, architecture docs, contribution guide, model cards | `.claude/agents/documentation.md` |
| DevOps | Dev environment, mobile builds, GitHub Actions, releases | `.claude/agents/devops.md` |
| Dataset Engineer | Roboflow projects, annotation review, versioning, quality analysis | `.claude/agents/dataset-engineer.md` |
| Data Pipeline | Preprocessing, augmentation, conversion, validation scripts | `.claude/agents/data-pipeline.md` |
| ML Engineer | Training, fine-tuning, hyperparameters, MLflow, run diagnosis | `.claude/agents/ml-engineer.md` |
| Evaluation | Metrics, confusion matrices, run comparison, model cards | `.claude/agents/evaluation.md` |
| Export | Export, quantization, numerical parity against the reference | `.claude/agents/ml-engineer.md` |
| QA | Unit, integration, and regression tests | `.claude/agents/qa.md` |
| Integration | Fusing detections with depth into one scene result | `.claude/agents/integration.md` |
| Mobile | The Expo app: on-device inference, fusion, overlays, capture, latency | `.claude/agents/mobile.md` |

Two boundaries are load-bearing, not stylistic, and a review should reject a PR that
crosses either:

- **Evaluation reports on models; it does not tune the code that produces them.** A
  PR that fixes a metrics script and adjusts the model it measured in the same change
  is not "measuring" anything.
- **Mobile does not change the exported artifacts, and Export does not change the
  app.** When the device disagrees with the Python reference, the disagreement is the
  finding. A PR that "fixes" both sides at once erases which one was wrong.

Roles arrive with the lesson that first needs them (Dataset Engineer in Lesson 02, ML
Engineer and Evaluation in Lesson 03, Export/QA/Integration in Lesson 04, Mobile in
Lesson 05) — a PR that invokes a role's territory before that point is likely doing
work out of order.

## Review expectations

- A reviewer checks the gates above were actually run, not just claimed — paste the
  command output for `pytest`, `ruff`, and `mypy` in the PR description.
- A PR that adds a stub (a module with signatures and docstrings, no body) should say
  so plainly in its description, the same way this repository's stubs say so in their
  own docstrings. Do not describe a stub as "implemented."
- A PR that touches a coordinate space (`SOURCE`, `MODEL_INPUT(det)`,
  `MODEL_INPUT(depth)`, `SCREEN`) should name which one, in the function signature and
  in the PR description. `docs/architecture.md` §2 is the reference.
- A PR that changes behaviour the requirements or architecture document already
  describes should update that document in the same PR, not in a follow-up.

## What must never be committed

- **Secrets of any kind.** `ROBOFLOW_API_KEY`, `ROBOFLOW_WORKSPACE`, and
  `MLFLOW_TRACKING_URI` are read from the environment, never hardcoded. `.env` is
  gitignored; `.env.example` documents the variable names, never real values. If a
  diff contains something that looks like a live key, stop and rotate it — do not
  just remove it from the next commit.
- **Dataset exports or raw images.** `data/` is gitignored. Datasets are versioned in
  Roboflow; reference a version number in code and docs, never "the latest."
- **Model weights or exported artifacts**, including `.pt`, `.tflite`, and `.pte`
  files. `app/assets/models/` holds the bundled artifacts that ship, and they are
  gitignored — tracked by their entry in `docs/artifact-budget.md` and their SHA-256 in
  the artifact manifest, not by git.
- **Anything under `app/` prefixed `EXPO_PUBLIC_`** that isn't a build flag. That
  prefix embeds its value in the app bundle, readable by anyone who installs the app,
  and this app has nothing to authenticate to at runtime.

## Enforcement, not just convention

Some of the rules above are backed by a hook in `.claude/hooks/`, configured in
`.claude/settings.json`, that runs whether or not a human reads this file:
`units_guard.py` blocks metric depth vocabulary in guarded files, and `credit_gate.py`
blocks a billed Roboflow call without a matching ledger row. If one blocks you, the fix
is to satisfy it — rename the field, write the ledger row — not to edit the hook or
route around it. If a hook is genuinely wrong, say so and open an ADR (`/adr <title>`)
rather than patching past it.
