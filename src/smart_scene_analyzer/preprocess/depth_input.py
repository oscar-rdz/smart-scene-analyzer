"""Build the depth model input tensor — boundary B4.

Responsibility: letterbox the SOURCE frame onto the depth canvas and emit the tensor in
the layout, dtype, and normalization the exported artifact declares.

The layout is ``[1, 3, H, W]`` **NCHW**, dtype **float32**, normalized per channel. Note
that this is a different layout *and* a different dtype from the detection input built
by the sibling module: NCHW float32 and NHWC uint8 are not interchangeable, and a silent
swap produces a plausible-looking depth map of nothing rather than an error.

The normalization constants and the canvas extent are Assumptions 2 and 3 in
`docs/architecture.md`. The authoritative values are whatever the export writes into the
artifact manifest; this module reads them from configuration rather than embedding them,
so that the reference and the device cannot disagree by a literal.

The canvas extent is also the single largest lever on the depth stage of the latency
budget. It is configuration for that reason.

Returns the tensor paired with its own ``LetterboxParams`` — a different scale and a
different padding from the detection tensor's.

Planned contents: ``build_depth_input(frame, config)``.
"""
