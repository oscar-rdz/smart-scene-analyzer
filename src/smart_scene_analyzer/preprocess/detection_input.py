"""Build the detection model input tensor — boundary B3.

Responsibility: letterbox the SOURCE frame onto the detection canvas and emit the tensor
in exactly the layout and dtype the exported artifact declares.

The layout is ``[1, H, W, 3]`` **NHWC**, dtype **uint8**, raw 0-255 intensities with
**no float normalization**. For an int8-quantized TFLite graph the quantization
parameters live inside the model; dividing by 255 here produces an almost-black input,
zero detections, and no error anywhere. This is Assumption 4 in
`docs/architecture.md` — it follows from "int8 TFLite" but is not stated in the
requirements, and getting it backwards fails silently.

The returned value is the tensor **paired with** its ``LetterboxParams``. The tensor
alone is not a complete value: without the scale and padding, nothing downstream can put
a box back into the source frame.

Planned contents: ``build_detection_input(frame, config)``.
"""
