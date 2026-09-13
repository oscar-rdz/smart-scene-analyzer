"""Everything between a file on disk and a tensor a model will accept.

Responsibility: produce the SOURCE frame, and from it the two model input tensors, each
paired with the ``LetterboxParams`` that make it invertible.

The two models are letterboxed **independently from the same source frame**, not chained.
Letterboxing to the detection canvas and then resampling to the depth canvas resamples
twice and loses detail for nothing.

This package is pure and offline: images for its tests are generated in code with numpy
and pillow, and no weights, GPU, or network are involved at any point.
"""
