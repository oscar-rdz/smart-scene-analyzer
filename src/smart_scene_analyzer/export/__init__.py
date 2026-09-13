"""Export and quantization. The producing side of the artifact contract.

Responsibility: turn the reference models into the two files the app bundles, and emit
the manifest that describes them.

**The export defines the artifact contract; the app consumes it.** Input shape and dtype,
output tensor count and order, class label order, normalization constants, and the
letterbox pad value are all fixed here and assumed there. Nothing checks them at runtime,
and this package is where a change becomes a release rather than an edit.

The boundary this crosses is a **release boundary**. Correcting a bug here does not
correct it on any handset until a store ships the result, which is the bill
`docs/decisions/0001-inference-target.md` knowingly accepts.

An export nobody compared against the reference is not known to be correct — it is only
known to run. ``parity.py`` is that comparison, and requirement N20 makes it a test.

Everything in this package needs weights on disk and is marked ``integration``.
"""
