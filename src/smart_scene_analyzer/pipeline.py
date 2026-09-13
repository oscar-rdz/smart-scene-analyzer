"""Composition root for the reference pipeline. Wires the stages; owns no logic.

Responsibility: run acquire, preprocess, both inferences, and fusion in order, and
assemble the result. Every interesting decision belongs to the module it delegates to;
this one exists so there is a single place that states the order.

The dependency rule that makes the offline suite possible: this module accepts a
``Detector`` and a ``DepthEstimator`` **as constructor arguments**, typed by the
protocols in ``inference.protocols``. It never constructs a concrete model, and it never
imports ``torch``, ``ultralytics``, ``transformers``, or ``mlflow``. A test passes two
fakes returning canned values and exercises the whole path with no GPU, no network, and
no weights on disk.

The two model stages have **no data dependency on each other** — detection does not need
depth and depth does not need detection, and they converge for the first time at the
fusion layer. This module runs them sequentially, because it is the reference and
determinism is worth more here than speed. The app runs the same two stages concurrently
on separate native threads; that concurrency is the app's, and the latency budget in
`docs/architecture.md` section 5 depends on it while this module does not.

Failure handling mirrors the app's branches so the reference and the device agree about
what a partial result looks like: a depth failure degrades to detection-only with a
stated status, a detection failure is surfaced rather than rendered as an empty scene,
and a rejected input names the stage that rejected it.

Stage timings are recorded into the result for development builds. They are never
transmitted — requirement N15 puts no telemetry on the inference path.

Planned contents: ``ScenePipeline`` with ``__init__(detector, depth_estimator, config)``
and ``analyze(image) -> SceneResult``.
"""
