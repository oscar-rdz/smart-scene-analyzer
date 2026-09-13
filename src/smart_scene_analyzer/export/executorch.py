"""Export Depth Anything V2 to an ExecuTorch ``.pte``.

Responsibility: produce the depth artifact and record the input contract it commits to —
the ``[1, 3, H, W]`` NCHW float32 layout, the per-channel normalization constants, and
the canvas extent.

The canvas extent is not only a correctness fact. It is the single largest lever on the
depth stage of the latency budget in `docs/architecture.md` section 5, and it is the
first thing to change if that stage misses its allocation. Changing it changes the
artifact, which means it changes a release.

The output carries relative inverse depth: larger is nearer, no unit, no scale. The
export does not rescale or normalize it, because there is no scale to normalize into and
inventing one here would make every consumer downstream believe a false thing.

A vision transformer is the harder of the two models to shrink, which
`docs/artifact-budget.md` already flags. Record the size before bundling.

Marked ``integration``.
"""
