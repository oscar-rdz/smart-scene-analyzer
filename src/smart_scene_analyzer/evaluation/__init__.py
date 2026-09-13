"""Metrics. Reports on models; does not tune them.

Responsibility: compute the numbers requirements N3 and N4 are stated in, on a named
held-out split of a pinned dataset version, and produce the reports and model cards that
go with them.

The role boundary is load-bearing and is recorded in `CLAUDE.md`: an agent that can
adjust the model when it dislikes the number is not measuring anything. This package
computes and reports. It does not reach into training or export.

Both accuracy targets are **provisional** and stay that way until the taxonomy and a
dataset version exist. Nothing here should be read as settled.

Metrics assert on the contract — shapes, label order, ordering — never on a specific
confidence or coordinate that a retrain would move.
"""
