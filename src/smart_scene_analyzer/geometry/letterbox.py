"""Aspect-preserving letterbox onto a fixed canvas, and its parameters.

Responsibility: resize a source frame onto a model's input canvas without distorting it,
and return the scale and padding that make the operation invertible.

The padding is centred — the remainder, when the pad is odd, goes to the right and
bottom edge, and the export and the app must agree on that or every box drifts by half
a pixel in one direction. The pad value is a constant of the artifact contract, not a
local choice.

Planned contents (stubs only):

- ``compute_letterbox_params(src_w, src_h, input_w, input_h, pad_value)`` — the geometry
  alone, with no pixels touched. Separated from the resize so it can be computed for a
  frame that has not been decoded and so the tests can assert it analytically.
- ``apply_letterbox(frame, params)`` — the pixel operation.
- ``non_pad_region(params)`` — the rectangle of the canvas that holds real image data.
  The depth reduction needs this: padding is grey canvas, the depth model assigns it a
  value, and that value means nothing.
"""
