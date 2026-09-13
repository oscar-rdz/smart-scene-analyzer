"""Model adapters, and the protocols that keep the rest of the system independent of them.

Responsibility: wrap the expensive things — weights, a GPU, a heavyweight library — behind
two narrow interfaces, and keep those wrappers thin enough that nothing important lives
inside them.

This is the seam the offline test suite depends on. `pipeline.py` depends on the
protocols in ``protocols.py``; it never constructs a concrete model and never imports
``ultralytics``, ``torch``, or ``transformers``. Those imports live inside the concrete
adapters in this package, so that importing the pipeline does not drag in a gigabyte of
dependency and a bare checkout can still run the whole default suite.

The rule that makes the suite meaningful: **mock at the model boundary, never at the
logic boundary.** Mocking the fusion layer would delete the only thing worth testing.

``postprocess.py`` is deliberately *not* behind a protocol. Decode and non-maximum
suppression are pure logic, they are ported to TypeScript, and they are exactly what the
tests need to reach.
"""
