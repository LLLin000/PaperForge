# OCR Truth Surface Realignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the OCR-v2 truth surface coherent by distinguishing completed readiness-gate status from the active post-readiness rebuild-hardening queue.

**Architecture:** Keep the change narrow. Do not rewrite historical analysis bodies. Change only headers, status lines, active-queue wording, cross-links, and contradictory phrases so one active queue governs execution while the rebuild audit becomes the evidence source and historical readiness files are explicitly frozen.

**Tech Stack:** Markdown docs in `project/current/` and repo root, pytest for doc-contract assertions, existing OCR project truth files.

**Execution Status:** completed on `ocr-v2` via subagent-driven execution

---

## File Structure

- Create: `tests/test_ocr_truth_surface_docs.py`
  - Doc-contract guard for active queue, historical residual labeling, and contradiction phrases.
- Modify or Create: `project/current/ocr-v2-active-queue.md`
  - Preferred clean active queue file if introducing a new name is acceptable.
- Modify: `project/current/ocr-v2-closeout-priority.md`
  - Either becomes a transitional pointer or is frozen as historical closeout context.
- Modify: `project/current/ocr-v2-generalization-boundary.md`
  - Remains the broader architecture note, not the active queue.
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
  - Freeze as readiness-cycle residuals.
- Modify: `project/current/ocr_rebuild_audit.md`
  - Mark explicitly as post-readiness rebuild-hardening evidence.
- Modify: `PROJECT-MANAGEMENT.md`
  - Record the narrative handoff and point to the active queue.

---

### Task 1: Install A Truth-Surface Doc Contract Test Before Editing Docs

**Files:**
- Create: `tests/test_ocr_truth_surface_docs.py`

- [ ] **Step 1: Write a failing doc-contract test file**

Create `tests/test_ocr_truth_surface_docs.py` with this content:

```python
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_QUEUE = ROOT / "project" / "current" / "ocr-v2-active-queue.md"
GENERALIZATION = ROOT / "project" / "current" / "ocr-v2-generalization-boundary.md"
REMAINING = ROOT / "project" / "current" / "ocr-v2-remaining-issues-2026-06-18.md"
REBUILD_AUDIT = ROOT / "project" / "current" / "ocr_rebuild_audit.md"
PM = ROOT / "PROJECT-MANAGEMENT.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_active_queue_file_exists_and_declares_post_readiness_role() -> None:
    text = _text(ACTIVE_QUEUE)
    assert "ACTIVE QUEUE" in text
    assert "post-readiness rebuild hardening" in text


def test_rebuild_audit_declares_it_is_an_evidence_surface() -> None:
    text = _text(REBUILD_AUDIT)
    assert "post-readiness audit surface" in text
    assert "evidence source" in text


def test_remaining_issues_file_is_frozen_as_readiness_cycle_residuals() -> None:
    text = _text(REMAINING)
    assert "readiness-cycle residuals" in text


def test_project_management_points_to_active_queue_not_itself() -> None:
    text = _text(PM)
    assert "active queue" in text
    assert "ocr-v2-active-queue.md" in text


def test_no_active_truth_file_claims_nothing_remains() -> None:
    for path in [ACTIVE_QUEUE, GENERALIZATION, REMAINING, REBUILD_AUDIT, PM]:
        text = _text(path).lower()
        assert "nothing remains" not in text
        assert "merge now" not in text
```

- [ ] **Step 2: Run the red doc-contract test**

Run: `python -m pytest tests/test_ocr_truth_surface_docs.py -v`

Expected: FAIL because `ocr-v2-active-queue.md` does not exist yet and the current files do not carry the new contract language.

- [ ] **Step 3: Commit the guardrail test**

```bash
git add tests/test_ocr_truth_surface_docs.py
git commit -m "test: add OCR truth surface doc contract guard"
```

---

### Task 2: Create The Active Queue File And Freeze The Old Queue Vocabulary

**Files:**
- Create: `project/current/ocr-v2-active-queue.md`
- Modify: `project/current/ocr-v2-closeout-priority.md`

- [ ] **Step 1: Create the new active queue file**

Create `project/current/ocr-v2-active-queue.md` with this content:

```md
# OCR-v2 Active Queue

> Status: ACTIVE QUEUE — post-readiness rebuild hardening
> Last updated: 2026-06-19
> Scope: authoritative next-work queue for OCR after readiness-gate completion

## Queue Contract

OCR-v2 architecture readiness is complete.
Post-readiness rebuild hardening is now the active queue.
This file governs next execution when other OCR truth files disagree.

## Current Priorities

1. Rebuild-output pollution fixes
2. Ownership write-through fixes
3. Figure/table inventory contract hardening
4. Additive health-v2 semantics

## Cross-Links

- Evidence source: `project/current/ocr_rebuild_audit.md`
- Architecture boundary note: `project/current/ocr-v2-generalization-boundary.md`
- Historical readiness residuals: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- Narrative ledger: `PROJECT-MANAGEMENT.md`
```

- [ ] **Step 2: Freeze the old closeout file as non-authoritative**

Replace the header and next-work section at the top of `project/current/ocr-v2-closeout-priority.md` so it becomes a transitional historical pointer, for example:

```md
# OCR-v2 Close-Out Priority

> Status: historical closeout queue — superseded by `project/current/ocr-v2-active-queue.md`
> Last updated: 2026-06-19
> Former role: authoritative readiness / closeout queue

## Status

This file records the final closeout/readiness queue state that led into post-readiness rebuild hardening.
It no longer governs next execution.

## Current Authority

Use `project/current/ocr-v2-active-queue.md` for active OCR work.
```

- [ ] **Step 3: Run the doc-contract test again**

Run: `python -m pytest tests/test_ocr_truth_surface_docs.py -k "active_queue_file_exists" -v`

Expected: PASS for the active-queue existence contract.

- [ ] **Step 4: Commit**

```bash
git add project/current/ocr-v2-active-queue.md project/current/ocr-v2-closeout-priority.md
git commit -m "docs: add OCR active queue and freeze closeout queue"
```

---

### Task 3: Relabel The Remaining Truth Files Without Rewriting Their Analysis Bodies

**Files:**
- Modify: `project/current/ocr-v2-generalization-boundary.md`
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- Modify: `project/current/ocr_rebuild_audit.md`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Update the broader architecture note header and next-actions lines**

Edit only the control-plane surfaces in `project/current/ocr-v2-generalization-boundary.md`:

```md
> Status: broader architecture note
> Readiness status: complete
> Active execution queue: `project/current/ocr-v2-active-queue.md`
```

Replace the current `Next Actions` section with a short pointer section:

```md
## Queue Relationship

This file is the broader architecture note.
It does not govern day-to-day execution.
Use `project/current/ocr-v2-active-queue.md` for active work and `project/current/ocr_rebuild_audit.md` for rebuild-hardening evidence.
```

- [ ] **Step 2: Freeze the readiness residual file explicitly**

Edit only the header and top summary in `project/current/ocr-v2-remaining-issues-2026-06-18.md`:

```md
> Status: historical readiness-cycle residuals
> Readiness gates: complete
> Active queue: `project/current/ocr-v2-active-queue.md`
```

Add a short note below the header:

```md
This file records the residual state at the end of the readiness-gate cycle.
It is not the active rebuild-hardening queue.
```

- [ ] **Step 3: Mark the rebuild audit as evidence source, not architecture repudiation**

Edit only the top section of `project/current/ocr_rebuild_audit.md`:

```md
> Status: post-readiness audit surface
> Role: evidence source for rebuild hardening
> Does not change: the completed OCR-v2 readiness-gate conclusion
```

Add a short intro paragraph:

```md
This audit evaluates rebuild outputs across the broader corpus after readiness-gate completion.
It identifies post-readiness hardening work; it does not reopen the OCR-v2 backbone decision.
```

- [ ] **Step 4: Add a narrative handoff section to `PROJECT-MANAGEMENT.md`**

Insert a new section near the top of `PROJECT-MANAGEMENT.md`:

```md
### 0.3 Truth-Surface Handoff

OCR-v2 readiness-gate work is complete.
Post-readiness rebuild hardening is now the active queue.

Execution authority:
- Active queue: `project/current/ocr-v2-active-queue.md`
- Evidence source: `project/current/ocr_rebuild_audit.md`
- Broader architecture note: `project/current/ocr-v2-generalization-boundary.md`
- Historical readiness residuals: `project/current/ocr-v2-remaining-issues-2026-06-18.md`

`PROJECT-MANAGEMENT.md` records the handoff but does not override the active queue.
```

- [ ] **Step 5: Run the full doc-contract test**

Run: `python -m pytest tests/test_ocr_truth_surface_docs.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add project/current/ocr-v2-generalization-boundary.md project/current/ocr-v2-remaining-issues-2026-06-18.md project/current/ocr_rebuild_audit.md PROJECT-MANAGEMENT.md
git commit -m "docs: realign OCR truth surface roles"
```

---

### Task 4: Run The Contradiction Pass And Normalize Cross-Links

**Files:**
- Modify: `project/current/ocr-v2-active-queue.md`
- Modify: `project/current/ocr-v2-closeout-priority.md`
- Modify: `project/current/ocr-v2-generalization-boundary.md`
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- Modify: `project/current/ocr_rebuild_audit.md`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Search for contradiction phrases in the active truth surface**

Run: `rg -n "merge now|nothing remains|all done|final remaining|active remaining issues|readiness incomplete|reopen architecture" PROJECT-MANAGEMENT.md project/current/ocr-v2-active-queue.md project/current/ocr-v2-closeout-priority.md project/current/ocr-v2-generalization-boundary.md project/current/ocr-v2-remaining-issues-2026-06-18.md project/current/ocr_rebuild_audit.md`

Expected: one or more hits that require reclassification or removal.

- [ ] **Step 2: For each hit, classify and rewrite only the contradictory control-plane wording**

Apply this rubric while editing:

```text
If the phrase is a historical readiness statement, preserve the analysis body and relabel it as historical.
If the phrase pretends to be current execution authority, replace it with a pointer to ocr-v2-active-queue.md.
If the phrase implies the architecture is incomplete because rebuild hardening exists, rewrite it to distinguish the two evaluation surfaces.
```

- [ ] **Step 3: Add consistent cross-links at the top of each active file**

Ensure each file’s top section includes a compact link set such as:

```md
- Active queue: `project/current/ocr-v2-active-queue.md`
- Evidence source: `project/current/ocr_rebuild_audit.md`
- Architecture boundary: `project/current/ocr-v2-generalization-boundary.md`
```

- [ ] **Step 4: Re-run the contradiction grep**

Run the same `rg` command from Step 1.

Expected: only acceptable historical-context hits remain, or no hits remain.

- [ ] **Step 5: Re-run the doc-contract test**

Run: `python -m pytest tests/test_ocr_truth_surface_docs.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add PROJECT-MANAGEMENT.md project/current/ocr-v2-active-queue.md project/current/ocr-v2-closeout-priority.md project/current/ocr-v2-generalization-boundary.md project/current/ocr-v2-remaining-issues-2026-06-18.md project/current/ocr_rebuild_audit.md
git commit -m "docs: remove OCR truth surface contradictions"
```

---

## Self-Review Notes

- Spec coverage: this plan establishes one active queue, distinguishes evidence source vs queue vs architecture note vs historical residuals, constrains edits to control-plane surfaces, and adds an explicit contradiction pass.
- Narrow-scope guarantee: no task rewrites historical analysis bodies; all edits are limited to headers, status sections, next-work sections, and cross-links.
- Plan split: this is intentionally separate from rebuild/output code remediation and should be executed before large remediation batches so future workers read the right queue.
