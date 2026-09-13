"""The reference Depth Anything V2 estimator. Adapts it to the ``DepthEstimator`` protocol.

Responsibility: load the model, run it, squeeze the output to a two-dimensional grid, and
build a ``DepthMap``. Thin, for the same reason the detector adapter is thin.

The output is **relative inverse depth**: larger is nearer, no unit, no scale, comparable
only within one image. It has no physical scale to recover, which is why requirement N4
measures rank correlation rather than an error statistic — the usual statistics
presuppose a scale this model does not have.

The squeeze is strict. A rank other than the two the model is known to produce raises,
rather than being reshaped hopefully into something that will run and be wrong.

``transformers`` and ``timm`` are imported inside this module, never at package level.

Tests carry the ``integration`` marker.
"""
