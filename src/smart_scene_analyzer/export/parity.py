"""Numerical parity between an exported artifact and the reference it came from.

Responsibility: answer the only question that makes an export trustworthy — does the
artifact agree with the model it was exported from, on the same inputs, within a stated
tolerance?

This is the one part of the system that cannot be tested offline, and it is the exception
that the offline rule exists to make possible. It is marked ``integration`` so the
default suite still passes on a machine with no weights; a parity test that breaks the
fast suite gets deleted within a month.

Four disciplines, from `.claude/skills/offline-suite`:

- **Compare against the ORIGINAL**, never against the exported artifact loaded by a
  second runtime. Comparing an artifact to itself confirms that two libraries can read
  one file and nothing more.
- **State the tolerance and justify it.** Exports do not match bit for bit and are not
  meant to. A tolerance chosen after seeing the results is a description, not a
  threshold — and if that is what happened, say so.
- **Report per-class deltas** for detection. An aggregate is exactly the wrong instrument
  for finding a single class that quantization destroyed.
- **For depth, compare ORDERING, not values.** The output has no scale, so comparing
  magnitudes across two runtimes is meaningless even when the assertion passes. Rank
  correlation measures the property the product actually uses.

The signature question to hold this module to: **would this test fail if the export were
broken?** One that checks only that the artifact loads and returns the right shape passes
on a model quantized into uselessness.
"""
