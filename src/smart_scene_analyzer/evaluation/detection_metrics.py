"""Detection metrics — requirement N3.

Responsibility: compute mAP and the per-class breakdown on a held-out split, and report
the confusion structure that tells a weak class apart from a weak model.

**Per-class, always.** An aggregate mAP is the wrong instrument for almost every question
worth asking here: quantization destroying one class, a taxonomy with two classes nobody
can tell apart, a split with four examples of something. All three are invisible in the
aggregate and obvious in the breakdown.

The target itself is provisional until the taxonomy exists, and this module reports the
number rather than judging it.

Box comparisons happen in a single stated coordinate space — xyxy, absolute SOURCE
pixels — for predictions and ground truth alike. An IoU computed across two spaces
returns a plausible number and means nothing.

Pure given arrays of boxes; testable offline with hand-built cases.
"""
