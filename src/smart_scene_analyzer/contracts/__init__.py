"""The data contracts for every boundary in `docs/architecture.md` section 3.

Responsibility: define the types that cross module boundaries, and make each one state
its units and its coordinate space in the type itself rather than in a comment beside
the call site.

Two rules this package exists to enforce:

- **A bare number pair is never a point.** Anything crossing a boundary names its
  coordinate space in its field name or its type name.
- **A resized tensor without its scale and padding is an incomplete value.** Tensors
  travel paired with the ``LetterboxParams`` that relate them back to the source frame.

Depth fields in this package carry relative inverse depth — larger is nearer, no unit,
no scale, comparable only within one image.
"""
