"""The reference YOLO11 detector. Adapts ultralytics to the ``Detector`` protocol.

Responsibility: load the PyTorch checkpoint, run it, and hand the raw output to
``postprocess``. Nothing else. This module is thin on purpose — every line of logic that
lives here is a line the offline suite cannot reach and the TypeScript port cannot be
compared against.

``ultralytics`` and ``torch`` are imported **inside this module**, never at the package
level, so that a checkout without the ``ml`` extra can still import the pipeline and run
the default suite. A ``ModuleNotFoundError`` raised from here is correct behaviour, not a
broken environment.

This is the reference half of the export parity test: the artifact the app bundles is
compared against *this*, never against itself loaded by a second runtime.

Tests for this module carry the ``integration`` marker — it needs weights on disk.
"""
