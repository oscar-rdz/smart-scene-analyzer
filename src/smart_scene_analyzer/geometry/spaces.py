"""Named conversions between coordinate spaces. One function per direction.

Responsibility: be the only module in `src/` that moves a coordinate from one space to
another, so that the highest-risk arithmetic in the system has exactly one home.

Forward: ``x_model = x_source * scale + pad_x``.
Inverse: ``x_source = (x_model - pad_x) / scale``.

Planned contents (stubs only):

- ``source_to_model_input(box_source, params)`` — SOURCE pixels to letterboxed
  MODEL_INPUT pixels.
- ``model_input_to_source(box_model, params)`` — the inverse, with clipping to the
  source extent, so that a box overhanging into the pad region is truncated rather than
  handed downstream with a negative coordinate.
- ``source_box_to_grid_indices(box_source, depth_letterbox, grid_h, grid_w)`` — SOURCE
  pixels to integer indices in a depth grid that may be coarser than its own input
  canvas. Rounds **outward**, so a box narrower than one grid cell still covers a cell.

The detection and depth ``LetterboxParams`` are different values with different scales
and different pads. Passing one where the other is expected type-checks cleanly and is
silently wrong, which is why every signature here names the params it expects.

Tested by round-trip identity within float tolerance, not by fixture comparison.
"""
