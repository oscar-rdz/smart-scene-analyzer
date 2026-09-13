"""Fine-tune YOLO11 on the project dataset.

Responsibility: take a pinned dataset version and an explicit config, run the training,
and hand every parameter that shaped the result to the tracking module.

The class list comes from the dataset version. It is not declared here — the taxonomy is
open until Lesson 02, and a class list written into training code is one that can
disagree with the data it trained on.

The seed is explicit and recorded. A run whose seed was left to a library default is not
reproducible even when everything else about it was written down.

``ultralytics`` and ``torch`` are imported inside this module. Marked ``integration``.
"""
