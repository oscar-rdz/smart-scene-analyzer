"""The result contract — boundary B9 of `docs/architecture.md`.

Responsibility: define what the scene understanding layer hands to the renderer, and
the status vocabulary that keeps the app's failure states distinguishable.

Boxes here are still ``xyxy`` in absolute **SOURCE** pixels, unchanged from the
detection contract. The fusion layer performs no coordinate transform; the conversion to
screen points happens in the overlay and nowhere else.

``relative_depth`` is relative inverse depth — larger is nearer, no unit, no scale,
comparable only against the other objects in the same result. It is optional, and the
absent case is ``None`` rather than ``0.0``: zero is a perfectly legal relative inverse
depth, and a sentinel zero would render as the farthest object in the scene and look
entirely plausible.

``depth_rank`` is an ordinal, ``0`` for the nearest object and ascending. It exists so
the overlay has something orderable that it can never be tempted to print as a quantity.

``status`` is a discriminated union, not a boolean. Requirements F8 and N12 need four
states to be distinguishable: a successful empty result, a depth model that failed while
detection succeeded, a detection failure, and a rejected input. "Still loading" is the
absence of a result, which is why it is not a member of this enum.

Planned contents: ``SceneStatus``, ``DepthStatus``, ``SceneObject``, ``ModelVersions``,
``StageTimings`` (development builds only — no telemetry on the inference path), and
``SceneResult``.
"""
