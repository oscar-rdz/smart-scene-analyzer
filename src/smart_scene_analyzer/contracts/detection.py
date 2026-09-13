"""The detection contract — boundary B6 of `docs/architecture.md`.

Responsibility: define the single type in which detections leave the detector and enter
the scene understanding layer.

``Detection.bbox`` is ``[x1, y1, x2, y2]`` — **xyxy, absolute pixels of the SOURCE
frame**. Not ``cxcywh``. Not normalized to 0-1. Not the letterboxed model-input canvas.
The un-letterbox happens once, at the exit of decode, and every component downstream of
this type may assume SOURCE and nothing else.

``confidence`` is a probability in ``[0.0, 1.0]``. ``class_id`` indexes the label list
in the bundled artifact manifest; the taxonomy itself is open until Lesson 02 and this
module must never hardcode it.

Two invariants the tests assert:

- Zero detections is an empty list. Not ``None``, not an exception, not a sentinel.
- The list is ordered by descending confidence, because the overlay draws in that order
  and the parity fixtures compare element-wise.

Planned contents: ``Detection`` and any narrow alias for the list form.
"""
