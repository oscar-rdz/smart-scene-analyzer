"""The only module in this package that touches MLflow.

Responsibility: start runs, log parameters, metrics, and artifacts, and return the run id
that the export manifest records as provenance.

The tracking URI is read from the environment (``MLFLOW_TRACKING_URI``), never
constructed here and never hardcoded. That is what keeps the open hosting question
(`docs/architecture.md` section 8.1) out of the rest of the codebase: both branches are
this same code with a different string.

It is also what keeps the credential dev-time only. There is no runtime service in this
project and the app ships with no credentials of any kind; nothing under ``app/`` may
ever import a tracking concept.

What a run must carry for requirement N19 to hold: the seed, the dataset version as an
explicit number, the full training config, and the resulting metrics.

Marked ``integration``.
"""
