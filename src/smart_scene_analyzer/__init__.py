"""Smart Scene Analyzer — the reference implementation and export pipeline.

This package is **deployment unit B** in `docs/architecture.md`: it trains the models,
exports the artifacts the app bundles, and remains the reference the device is checked
against. It ships nowhere and serves nothing.

Nothing in this package opens a socket on an inference path — see
`docs/decisions/0001-inference-target.md`.

Depth throughout this package is **relative inverse depth**: larger is nearer, no unit,
no scale, comparable only within one image.

Import discipline, which the offline test suite depends on:

- Importing `smart_scene_analyzer` or `smart_scene_analyzer.pipeline` must not import
  `torch`, `ultralytics`, `transformers`, or `mlflow`. Those imports live inside the
  concrete adapters in `inference/`, `export/`, and `training/`.
- A bare checkout with no optional extras installed must still run the default suite.
"""

__version__ = "0.1.0"
