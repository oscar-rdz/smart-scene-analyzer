"""Write ``models.manifest.json`` — the artifact contract, serialized.

Responsibility: emit, next to the two artifacts, the machine-readable description of
everything the app would otherwise have to assume: input shape, dtype and layout; output
layout and box encoding; normalization constants; letterbox pad value; class label order;
the SHA-256 of each file; and the provenance that requirement F7 surfaces in the result.

Provenance means the MLflow run id, the registry version, and the dataset version. With
no network on the inference path, a bundled manifest is the only honest way for the app
to know which model it is running — hardcoding those strings in TypeScript guarantees
they go stale without failing.

The SHA-256 fields are the load-bearing ones. They are what let a test assert that the
file the app bundles is the file the parity test blessed, rather than whatever the export
script would produce if somebody ran it now.

The label order is read from the trained model and the dataset version. It is **never**
defaulted here — the taxonomy is open until Lesson 02, and a placeholder class list that
silently survives into a release is exactly the failure the artifact contract exists to
prevent.
"""
