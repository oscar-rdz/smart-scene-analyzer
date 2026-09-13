"""The two interfaces the pipeline depends on. The mock seam, stated as types.

Responsibility: describe what a detector and a depth estimator must do, in terms of the
contracts alone, so that a test double is a few lines and a real model is an
implementation detail.

Nothing in this module imports a model library, and nothing in it may.

Both methods take a tensor already paired with its ``LetterboxParams``, and both return
a contract type in a stated coordinate space — so an implementation cannot quietly hand
back coordinates in the letterboxed canvas and leave the caller to guess.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Detector(Protocol):
    """Produces detections in the SOURCE frame from a prepared detection tensor."""

    def detect(self, tensor: object, letterbox: object) -> list[object]:
        """Return detections with boxes in xyxy, absolute SOURCE pixels.

        Zero detections is an empty list — never ``None``, never an exception.
        Results are ordered by descending confidence.
        """
        ...


@runtime_checkable
class DepthEstimator(Protocol):
    """Produces a dense relative inverse depth grid from a prepared depth tensor."""

    def estimate(self, tensor: object, letterbox: object) -> object:
        """Return a ``DepthMap`` in the depth model's own grid index space.

        Values are relative inverse depth: larger is nearer, no unit, no scale,
        comparable only within one image. The grid is not resampled to the source
        frame; the returned ``LetterboxParams`` are what relate it back.
        """
        ...
