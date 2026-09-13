"""Decode raw detector output and suppress duplicates — boundary B5 to B6.

Responsibility: turn the detector's raw output tensor into ``list[Detection]`` with
boxes in **xyxy, absolute SOURCE pixels**. Pure: numpy only, no model handle, no I/O.

Three transforms happen here, in this order, and the order matters:

1. **cxcywh to xyxy.** The raw box terms are centre-and-extent, in MODEL_INPUT pixels.
2. **Non-maximum suppression**, per class, at the configured IoU threshold. Done while
   still in model-input space, because that is where the boxes are square-pixel uniform.
3. **Un-letterbox to SOURCE**, then clip to the source extent. This is the inverse of the
   preprocessing resize, and it happens **exactly once, here**. Everything downstream of
   this module may assume SOURCE and nothing else. Clipping after the inverse, rather
   than before, is what stops a box that overhangs into the padding from arriving with a
   negative coordinate.

``num_classes`` is derived from the output tensor shape and the label text comes from the
artifact manifest. Neither is hardcoded — the taxonomy is open until Lesson 02, and a
class list inlined here is one that goes stale without failing.

Zero surviving boxes returns an empty list.

Tested offline against hand-built raw tensors with known boxes, including the degenerate
cases: zero-area boxes, boxes entirely inside the padding, and an empty input.
"""
