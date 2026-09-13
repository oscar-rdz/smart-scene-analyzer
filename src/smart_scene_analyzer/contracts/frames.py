"""Image frames, model input tensors, and the letterbox record that relates them.

Responsibility: own boundaries B2, B3, and B4 of `docs/architecture.md` — the source
frame and the two model input tensors — and the ``LetterboxParams`` value that makes a
resized tensor an invertible one.

Coordinate spaces defined here (section 2 of `docs/architecture.md`):

- ``SOURCE`` — pixels of the upright, downscaled capture. Origin top-left, x right,
  y down. Long edge capped, aspect preserved. Every externally visible box is quoted
  in this space.
- ``MODEL_INPUT(det)`` — letterboxed pixels of the detection input canvas.
- ``MODEL_INPUT(depth)`` — letterboxed pixels of the depth input canvas. A **different**
  scale and a different padding from the detection canvas. They are not interchangeable
  and passing one where the other is expected type-checks and is silently wrong.

Planned contents:

- ``CoordinateSpace`` — an enum, so a space can be asserted rather than assumed.
- ``LetterboxParams`` — ``scale``, ``pad_x``, ``pad_y``, source extent, input extent,
  and ``pad_value``. The pad value is carried because padding must be *excluded* from
  depth reductions, not merely produced.
- ``SourceFrame`` — ``[H, W, 3]`` HWC uint8 RGB, intensities 0-255, sRGB, immutable.
  EXIF orientation is already applied; ``width`` and ``height`` are the upright extent.
- ``ModelInputTensor`` — an array paired with its ``LetterboxParams`` and an explicit
  declared layout, since ``[1, 640, 640, 3]`` uint8 NHWC and ``[1, 3, 518, 518]``
  float32 NCHW both appear in this pipeline and a silent swap produces plausible
  garbage rather than an error.
"""
