"""Coordinate spaces and the conversions between them.

Responsibility: hold every transform between the coordinate spaces named in
`docs/architecture.md` section 2, so that there is exactly one place to get each one
wrong.

The project's three spaces are SOURCE pixels, letterboxed MODEL_INPUT pixels (two
independent instances, one per model, each with its own scale and padding), and SCREEN
points. SCREEN belongs to the app and does not appear in this package; the Python
reference stops at SOURCE.

The rule: **every conversion is a named function with both spaces in its signature.** A
box indexed into the wrong space returns a number, in range, and wrong — there is no
exception to catch and no assertion that fires.

This package is pure. It imports nothing heavier than numpy, touches no I/O, and is
tested by analytic round-trip rather than by fixture comparison.
"""
