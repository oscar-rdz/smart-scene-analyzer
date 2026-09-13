"""The artifact contract, made machine-readable — boundary B10.

Responsibility: define the schema of ``models.manifest.json``, the file that ships
beside the ``.tflite`` and the ``.pte`` in ``app/assets/models/``.

This boundary crosses a **release**, not a function call. The export defines it; the app
consumes it; nothing validates it at runtime. An app built against last week's label
order runs, draws boxes, and names them wrong — so the things that can silently drift
are written down where both sides can read them: input shape, dtype and layout,
normalization constants, output layout and box encoding, letterbox pad value, class
label order, and the SHA-256 of each artifact.

The label order is **open** until the Lesson 02 taxonomy exists. This module defines the
field; it must never define its contents, and neither the Python reference nor the
TypeScript port may hardcode a class list anywhere.

The ``sha256`` fields are what let a test assert that the file the app bundles is the
file the export parity test blessed, rather than whatever the export script would
produce if somebody ran it now.

Planned contents: ``TensorSpec``, ``DetectionArtifactSpec``, ``DepthArtifactSpec``,
``ModelManifest``, and a loader that validates a manifest without loading a model.
"""
