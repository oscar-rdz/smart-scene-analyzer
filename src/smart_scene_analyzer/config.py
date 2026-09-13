"""Single home for every tunable the pipeline reads.

Responsibility: hold the numbers that `docs/requirements.md` does not specify, in one
place, so that the Python reference and the TypeScript port can be shown to agree on
them rather than each inlining its own copy.

Everything here is listed in the Assumptions section of `docs/architecture.md`. A value
that appears in this module and nowhere else can be changed by one edit and one fixture
regeneration; a value inlined in two languages cannot.

Planned contents (stubs only at this stage):

- ``PreprocessConfig`` — detection input extent, depth input extent, letterbox pad
  value, normalization constants.
- ``PostprocessConfig`` — confidence threshold, NMS IoU threshold, max detections.
- ``FusionConfig`` — ``erosion_fraction`` and the reduction method named in
  `docs/architecture.md` section 4.
- ``PipelineConfig`` — the composition of the three, plus the source-frame long-edge cap.

These defaults are serialized into `tests/fixtures/fusion_cases.json` so the port is
compared against the same configuration, not merely the same algorithm.
"""
