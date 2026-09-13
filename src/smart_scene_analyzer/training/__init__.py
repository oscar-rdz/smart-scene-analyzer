"""Training and experiment tracking. Lesson 03 fills this in.

Responsibility: fine-tune the detection model, and record every run so that requirement
N19 — seed, dataset version, and config recorded — is satisfied by construction rather
than by memory.

Depth Anything V2 is used for inference only in this project; there is no depth training
module, and its absence is deliberate rather than pending.

Dataset versions are referenced by explicit version number, never as "the latest". A
version is an immutable snapshot in Roboflow, and a run pinned to "latest" is a run
nobody can reproduce.

Nothing here is on the default test path. Config construction is tested offline; the fit
loop is marked ``integration``.

**OPEN — MLflow hosting.** See `docs/architecture.md` section 8.1. The choice between a
local file store and a remote tracking server does not change any code in this package,
because ``tracking`` reads the URI from the environment. It does change what the run id
written into the artifact manifest *means*: under a local store it resolves only on the
laptop that produced it. This scaffold does not decide it.
"""
