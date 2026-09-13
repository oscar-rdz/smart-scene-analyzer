"""The dense depth contract — boundary B8 of `docs/architecture.md`.

Responsibility: define the grid the depth model produces and the record that lets the
scene understanding layer sample it from a source-frame box.

The values are **relative inverse depth**: larger is nearer, no unit, no scale,
comparable only within one image. The raw output range is model-dependent and is not
assumed to lie in ``[0, 1]``. Nothing in this project converts these numbers into a
physical quantity, and no field, docstring, or piece of UI text may imply that it could.

The grid stays in its own index space. It is deliberately **not** resampled up to the
source frame: interpolating roughly a million output pixels on the critical path, only
for the fusion layer to reduce each box to one number, is work spent to throw away. The
``letterbox`` field is what makes sampling from a source-frame box possible instead.

Planned contents:

- ``DepthMap`` — ``values`` as an ``[h, w]`` float32 array, the grid extent, the
  ``LetterboxParams`` relating that grid to SOURCE, and ``vmin``/``vmax`` observed over
  **non-padding** cells only. Letterbox padding is grey canvas; the model assigns it a
  value and including it skews the range the overlay shades against.
- The array is treated as read-only. Normalizing it in place would make a second call
  on the same map return a different answer.
"""
