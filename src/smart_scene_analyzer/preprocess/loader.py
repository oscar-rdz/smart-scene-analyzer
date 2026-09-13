"""Decode, orient, and downscale an image into the SOURCE frame — boundary B1 to B2.

Responsibility: turn an arbitrary input image into the one immutable frame that every
box in the system is afterwards quoted against.

Three things happen here and nowhere else:

- **EXIF orientation is applied.** A picker URI can hand back a HEIC with a rotation
  flag, and treating its stored width and height as the display geometry is wrong for a
  large fraction of phone photos. Downstream code may assume the frame is upright.
- **The long edge is downscaled to the configured cap**, aspect preserved. A 4:3 capture
  therefore becomes 1280x960, not 1280x720 — see Assumption 7 in
  `docs/architecture.md`, where requirement N7 is read as a long-edge rule rather than a
  fixed 16:9 target.
- **Alpha is discarded and channel order is fixed to RGB**, not BGR. Both are silent
  failures if left to whichever decoder happens to be installed.

Grayscale and single-pixel inputs are handled, not rejected. An unreadable or oversized
input raises a typed error naming the stage that rejected it, which is what requirement
N13 surfaces on screen.

Planned contents: ``load_source_frame(path_or_bytes, config)`` and the typed rejection
errors.
"""
