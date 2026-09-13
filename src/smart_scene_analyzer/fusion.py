"""The scene understanding layer. **The reference implementation.**

Responsibility: given detections in the SOURCE frame and a dense relative inverse depth
grid, derive one relative depth value per object and rank the objects by it.

This module is the one `app/src/fusion/index.ts` is a **port of**, and the two are held
together by `tests/fixtures/fusion_cases.json` — the same plain-JSON cases run against
both. When they disagree, the disagreement is the finding. The fixtures are never edited
to make them agree.

Purity is a requirement here, not a preference: no I/O, no model handle, no clock, no
randomness, no global state. Same inputs, same outputs, in both languages. That property
is the only thing that makes a cross-language parity test mean anything.

Depth vocabulary: ``relative_depth`` is **relative inverse depth**. Larger is nearer. No
unit, no scale. Comparable only against the other objects in the same result, never
across images, and never printed as a quantity.

The method — median of relative inverse depth over a centre-eroded, padding-excluded box.
Five steps, documented in full in `docs/architecture.md` section 4:

1. Project the SOURCE box into the depth grid's index space, rounding outward so a box
   narrower than one grid cell still covers a cell.
2. Erode toward the centre by the configured fraction per side, keeping the central
   portion. Background contamination in an axis-aligned box is concentrated at the
   corners, because the box is the tight hull of a shape that is not a rectangle.
3. Clip to the valid, **non-padding** region of the grid. Padding is grey canvas; the
   model assigns it a value and that value means nothing.
4. Reduce by **median**, not mean. A mean is dragged continuously by whatever background
   is visible through the object; a median only moves once the contaminating surface
   holds more than half the sampled cells. It also survives the band of extreme values
   that quantization and depth-edge ringing leave along every object boundary.
5. Rank all objects descending, nearest first, to fill the ordinal used by the overlay.

What it does when the box contains a background gap — the honest part, and a stated
failure mode rather than a solved problem:

- Object fills more than half the eroded region: the median lands on the object. Correct,
  and this is the common case.
- Object fills less than half — thin or skeletal structures seen through their own gaps,
  a floor lamp, a chair from the side, a plant — **the median returns the background**
  and the object reads as farther than it is. This is wrong, it is known, and it is
  written down instead of being papered over with an unmeasured heuristic. Two candidate
  mitigations are recorded in the architecture document and neither is adopted yet.
- Eroded box empties because the box is very small: fall back to the un-eroded clipped
  box.
- That is also empty — zero-area box, or a box entirely inside the padding: the object
  gets ``None`` and a status explaining why. **Never ``0.0``**: zero is a legal relative
  inverse depth and a sentinel zero renders as the farthest object in the scene, which
  looks entirely plausible and is entirely false.
- No depth grid at all, because the depth model failed to load: every object gets
  ``None``, the result reports depth as unavailable, and detections still render. That
  branch is requirement N12 and it must be visually distinct from a successful empty
  result.

Planned contents: ``fuse(detections, depth_map, config) -> SceneResult`` and the private
reduction helper the port mirrors step for step.

The test that keeps this module honest, from `.claude/skills/offline-suite`: fuse the
same detections against an inverted depth grid and assert the outputs change. Every
other assertion in the file passes on an implementation that returns a constant.
"""
