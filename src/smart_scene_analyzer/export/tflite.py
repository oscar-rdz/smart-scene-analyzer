"""Export YOLO11 to int8 TFLite.

Responsibility: produce the detection artifact and record what it committed to.

Quantization is the whole point and also the whole risk: int8 buys the size the artifact
budget needs, and it can destroy one class while leaving the aggregate metric almost
unmoved. The representative dataset used for calibration is part of the export's
identity and is recorded alongside the artifact, not chosen ad hoc at run time.

What this module fixes, and the app then assumes: the ``[1, H, W, 3]`` NHWC uint8 input,
the output tensor layout and its cxcywh box encoding in model-input pixels, the class
label order, and the letterbox pad value. All of it is written into the manifest.

The fp32 size is recorded as well as the int8 size. The delta is what quantization
bought, and `docs/artifact-budget.md` asks for both.

Marked ``integration``.
"""
