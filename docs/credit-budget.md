# Credit budget

**Hard cap: 20 Roboflow credits for the entire project, Lessons 01 through 06.**

There is no top-up. If you run out in Week 4, Week 6 does not happen. This file is the
ledger, and it is the reason the assistant can answer "can I afford this?" before it
spends anything.

It is also machine-read. `.claude/hooks/credit_gate.py` parses the **Remaining** row and
the Ledger table, and refuses billed Roboflow tool calls until a row exists with an
estimate and no actual. If you change this file's shape, change the hook with it —
a parser that silently finds nothing reports a balance of zero and blocks everything.

| | |
|---|---|
| Workspace | `oscar-rodriguez-enroutesystems-com` |
| Plan | Public (free) |
| Starting balance | 20.0 |
| **Remaining** | **18.51** |
| Last reconciled | `2026-09-13` against `app.roboflow.com/oscar-rodriguez-enroutesystems-com/settings/usage` |

---

## Planned allocation

Set once, at the start of Lesson 02. Revise it deliberately, not silently.

| Lesson | Budget | What it buys |
|---|---|---|
| 01 — Project Definition | 0.0 | No platform contact |
| 02 — Dataset Engineering | 4.0 | Uploads, storage, two version generations, the 100-image Auto Label audit |
| 03 — Model Development | 3.0 | One hosted training run (Roboflow Instant is free) |
| 04 — Backend Engineering | 2.0 | One hosted-API latency and cost comparison |
| 05 — On-Device Inference & Delivery | 0.0 | The models run on the handset. The app has no credentials, so no Roboflow call on the inference path is even possible |
| 06 — CI/CD/CT | 4.0 | One end-to-end continuous-training dry run |
| Buffer | 7.0 | Re-runs, mistakes, a regenerated version |
| **Total** | **20.0** | |

---

## Ledger

Append one row per billed operation. Free operations do not need a row, but recording
the significant ones (the 4-image Auto Label preview, a Roboflow Instant run) is worth
doing — it documents that you took the free path deliberately.

| Date | Lesson | Operation | Rate | Estimated | Actual | Running total | Remaining |
|---|---|---|---|---|---|---|---|
| | | *starting balance* | | | | 0.0 | 20.0 |
| 2026-09-13 | 02 | Upload 9,890 SUN RGB-D images to `smart-scene-analyzer-2026-09-13` | 1cr/10,000 images | 0.989 | 0.99 | 0.99 | 19.01 |
| | | *Note: estimate 0.989 vs actual 0.99 is Roboflow's 2-decimal display rounding, not a rate the table fails to model.* | | | | | |
| 2026-09-13 | 02 | Generate dataset version 1 (9,890 images, no augmentation) | 1cr/20,000 images | 0.495 | 0.50 | 1.49 | 18.51 |

---

## Rates

Verify against `roboflow:roboflow-plans-and-pricing` before relying on these. Upstream
rates change, and the skill is read fresh from disk every session; this table is not.

**What 1 credit buys**

| Operation | 1 credit |
|---|---|
| Uploads | 10,000 images |
| Storage | 5,000 images/month |
| Version generation | 20,000 images |
| Auto Label | 100 images |
| Model training (GPU) | 30 minutes |
| Hosted serverless inference (v2) | 500 seconds of execution |
| Self-hosted inference | 3,000 images |
| Dedicated deployment (GPU) | 1 hour of **uptime** |
| Batch processing (GPU) | 15 minutes |

**Free**

- Auto Label "Generate Test Results" on a 4-image subset — unlimited, and the whole
  reason prompt tuning is cheap
- Roboflow Instant training — few-shot, object detection only
- Universe search and browsing; RoboQL queries; tags; splits
- Workflow authoring, block listing, and spec validation — only *running* a workflow bills
- Cancelling a training run early ("refund if early in training")

---

## Reconciliation

At the end of every lesson:

1. Open `app.roboflow.com/<workspace>/settings/usage`.
2. Compare the platform's total against this ledger's running total.
3. Update **Remaining** and **Last reconciled** above.

**A gap between your estimate and the actual charge is a finding, not a mistake.** It
means an operation costs something you did not model. Write down what it was — that note
is worth more than the credit it cost you.

---

## Notes

Record anything that surprised you: an operation that billed unexpectedly, a rate that
turned out to be different from the table, a free-tier limit you hit.

| Date | Note |
|---|---|
| | |
