# Smart Scene Analyzer

A mobile perception app for iOS and Android. Point it at a scene — capture a photo or
pick one from the library — and it draws a box around every object it recognizes, with a
class label, a confidence score, and a sense of which objects are nearer and which are
farther. Detection and depth estimation both run **on the handset**: no image, and no
network call of any kind, is on the inference path. It works in airplane mode because
there is nothing on the other end of a connection to reach.

What it deliberately does not do: it does not report a distance in metres or any other
unit. Depth here is *relative* — "this chair is nearer than that wall" — never a metric
measurement. See `docs/requirements.md` (out-of-scope) and `docs/architecture.md` §4 for
why.

- **Detection / classification:** YOLO11, exported to int8 TFLite
- **Monocular depth:** Depth Anything V2, exported to ExecuTorch (`.pte`)
- **On-device runtimes:** `react-native-fast-tflite` (detection), `react-native-executorch` (depth)
- **App:** Expo / React Native (TypeScript), iOS and Android from one codebase
- **Training / export / reference implementation:** Python, in `src/`
- **Experiment tracking / registry:** MLflow
- **Dataset versioning:** Roboflow

Full design: [`docs/architecture.md`](docs/architecture.md). The decision that shaped
all of it — why inference runs on the device instead of a server — is
[`docs/decisions/0001-inference-target.md`](docs/decisions/0001-inference-target.md).
Contributing to the project: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Current status

**This is an early-stage scaffold. Read this section before the rest of the file, or a
command below will surprise you.**

- **Nothing has been trained, exported, or benchmarked.** `docs/architecture.md` is a
  design document — it says so at the top of it. Every latency figure and every accuracy
  target in `docs/architecture.md` and `docs/requirements.md` (the 400 ms latency budget,
  mAP@50, Spearman ρ) is a **target the design was built against, not a measurement**.
  There is no MLflow run and no eval report yet that could make them measurements.
- **`src/smart_scene_analyzer/` is 33 Python modules of docstrings and type signatures,
  with no function bodies.** They exist to fix the interfaces (`Detection`, `DepthMap`,
  `SceneResult`, the `Detector`/`DepthEstimator` protocols, and so on) before anything is
  implemented behind them. `uv run mypy src` passes today — that checks the shapes are
  internally consistent, not that any of it runs.
- **`tests/` contains one test file: `test_units_guard.py`.** It tests the depth-units
  enforcement hook (`.claude/hooks/units_guard.py`), not the pipeline — the pipeline has
  no behaviour yet to test. Running the suite gives 13 passed, 2 known `xfail`s (documented
  gaps in the hook's regex, not failures).
- **`app/` contains only a README.** There is no `app/package.json`, no `app/app.json`,
  no `app/src/`. The Expo app is built in Lesson 05. `cd app && npm install` will fail
  right now — there is nothing to install. See `app/README.md` for why it stays empty
  until then.
- **`data/` does not exist**, by design — datasets are versioned in Roboflow, not
  committed. `docs/roadmap.md` does not exist yet either.
- **One ADR is recorded:** `docs/decisions/0001-inference-target.md` (on-device, not
  cloud, forced by the privacy commitment that no image leaves the phone).

In short: today, this repository is a specification and a set of enforced conventions,
not a working perception system. The sections below tell you what you actually can run.

## Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Python | 3.11+ | Everything under `src/` and `tests/` |
| [`uv`](https://docs.astral.sh/uv/) | recent | Python dependency management — never `pip install` into the system interpreter |
| Git | any recent | Cloning, branching |
| Node.js | LTS | The Expo app (`app/`) — **not needed until Lesson 05** |
| Xcode (macOS) | recent, with an iOS Simulator | Building/running the app on iOS — **Lesson 05** |
| Android Studio | recent, with an emulator image | Building/running the app on Android — **Lesson 05** |

The model libraries (`ultralytics`, `torch`, `transformers`, `timm`, `mlflow`,
`roboflow`) are **not** prerequisites of a base setup — they are optional `uv` extras
described below, added by the lesson that needs them.

## Setup

From a fresh clone:

```bash
uv python install 3.11
uv sync
cp .env.example .env
```

Then open `.env` and fill in the two Roboflow variables:

```
ROBOFLOW_API_KEY=<your Roboflow API key, from app.roboflow.com/settings/api>
ROBOFLOW_WORKSPACE=<your Roboflow workspace slug>
```

`MLFLOW_TRACKING_URI` is already defaulted to `http://localhost:5000` in
`.env.example`; change it once MLflow hosting is decided (currently open — see
`docs/requirements.md`). None of these three variables is a runtime secret: they
authenticate you at dev time only, and the app itself ships with no credentials at all,
because there is no server for it to call.

`uv sync` installs the base dependencies and the `dev` group (pytest, ruff, mypy) — **not**
the model libraries. A bare checkout that tries to `import ultralytics` and raises
`ModuleNotFoundError` is expected behaviour, not a broken environment. Sync the extra
the lesson you're on actually needs, rather than adding a dependency to work around a
missing one:

```bash
uv sync --extra dataset  # roboflow, h5py, scipy        (Lesson 02)
uv sync --extra ml       # ultralytics, torch, mlflow   (Lesson 03)
uv sync --extra depth    # transformers, timm           (Lesson 03)
```

## Running the app

**There is no app to run yet.** `app/` holds only a README explaining why it is
deliberately left empty until Lesson 05 — a half-built Expo app with two native ML
runtimes goes stale faster than almost anything else in a course repository. When
Lesson 05 lands, `app/README.md` and this section will both describe:

```bash
cd app && npm install
npx expo run:ios        # builds and installs to the iOS Simulator
npx expo run:android    # builds and installs to a running Android Emulator
```

as a **development build**, not Expo Go — both ML runtimes are native modules the Expo
Go sandbox cannot load.

## Running tests, lint, and type checks

```bash
uv run pytest -m "not integration"   # the offline suite: no GPU, no network, no weights on disk
uv run pytest                        # everything, including tests that need weights/exported artifacts on disk
uv run ruff check .                  # lint
uv run ruff format .                 # format
uv run mypy src                      # type check `src/` (strict mode)
```

Selecting one file or one test:

```bash
uv run pytest tests/test_units_guard.py
uv run pytest -k units_guard
```

Right now, `uv run pytest` and `uv run pytest -m "not integration"` produce the same
result — there is exactly one test file and it carries no `integration` marker. That
will stop being true as soon as `tests/` grows a case that needs an exported artifact.

## Project layout

The table below is the layout of the **finished** system, per `CLAUDE.md`. On disk
today, most of the Python side exists as stubs, `app/` holds only its README, and
`data/` and `docs/roadmap.md` do not exist — see **Current status** above for exactly
what that means.

| Path | Contents |
|---|---|
| `src/smart_scene_analyzer/` | Python: training, export, and the reference implementation |
| `app/` | The Expo app. TypeScript. This is the product (Lesson 05) |
| `app/assets/models/` | The bundled `.tflite` and `.pte` artifacts. What is here is what runs |
| `app/src/fusion/` | The TypeScript port of `src/`'s fusion layer. Must agree with it |
| `tests/` | Unit, integration, and regression tests — including export parity |
| `docs/` | Architecture, requirements, decisions, budgets |
| `docs/architecture.md` | The system design: data contracts, coordinate spaces, latency budget |
| `docs/requirements.md` | Functional and non-functional requirements |
| `docs/decisions/` | ADRs — one file per architectural decision |
| `docs/credit-budget.md` | The Roboflow credit ledger. Read before any billed call |
| `docs/artifact-budget.md` | Model and app size — the budget that fails at install time |
| `data/` | Dataset exports. Gitignored. Versioned in Roboflow |
| `notebooks/` | Exploration only. Nothing in a notebook is production code |
| `.claude/agents/` | Subagent definitions — the engineering roles |
| `.claude/skills/` | This project's own procedures |
| `.claude/hooks/` | Enforcement that runs on tool calls, whether or not anyone reads it |

## Further reading

- [`docs/architecture.md`](docs/architecture.md) — the design: deployment units, data
  contracts between every stage, coordinate spaces, the fusion algorithm, the latency
  budget (labelled as a target, not a measurement), and the open decisions the design
  does not close.
- [`docs/requirements.md`](docs/requirements.md) — the functional and non-functional
  requirements this design is built against.
- [`docs/decisions/`](docs/decisions/) — ADRs, starting with
  [`0001-inference-target.md`](docs/decisions/0001-inference-target.md).
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to set up a dev environment, the gates a
  change must pass, and which engineering role owns which part of the system.
- [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) — the project-wide rules loaded
  into every Claude Code / Codex session in this repo.
