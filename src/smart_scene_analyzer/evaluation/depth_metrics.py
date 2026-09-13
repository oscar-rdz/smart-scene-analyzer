"""Depth metrics — requirement N4. Ordering, not error.

Responsibility: measure whether the predicted relative inverse depth **orders** a scene
the way the ground truth does, per image, by rank correlation.

Why ordering. The model returns relative inverse depth with no scale, so the customary
depth statistics are not directly computable — they presuppose a scale this model does
not have. Rank correlation measures the property the product actually uses: whether the
chair is correctly nearer than the wall. That is also exactly what the overlay renders,
so the metric and the feature are measuring the same thing.

If a figure comparable to published benchmarks is wanted later, it is computed **after**
a least-squares scale-and-shift alignment against the ground truth, and the report says
plainly that this is what was done. An aligned number presented as an unaligned one is a
misreport, not a shortcut.

Larger predicted values mean nearer. Ground truth conventions from public datasets
frequently run the other way, and a sign error here produces a strongly *negative*
correlation that is easy to misread as a broken model rather than a flipped axis. The
loader states the convention it read.

Pure; testable offline against a known analytic gradient.
"""
