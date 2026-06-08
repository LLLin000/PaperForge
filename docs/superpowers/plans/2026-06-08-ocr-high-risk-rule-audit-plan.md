# OCR High Risk Rule Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a concrete audit of OCR hard-rule decisions that can become the baseline for later scorer gates and health summaries.

**Architecture:** This is a docs-and-test plan. It adds a deterministic audit report generator in tests/docs rather than changing OCR behavior, so later plans can target exact production seams.

**Tech Stack:** Python, pytest, Markdown docs, PaperForge OCR worker modules.

---

## File Structure

- Create: `docs/ocr/high-risk-rule-audit.md` — human-readable audit of hard rules, production paths, and remediation mapping.
- Create: `tests/test_ocr_high_risk_rule_audit.py` — locks the audit file contract and required sections.
- Modify: `docs/superpowers/plans/2026-06-08-ocr-v1-convergence-master-plan.md` — add a cross-reference to the audit after the report exists.

Do not change OCR behavior in this plan.

---

### Task 1: Lock Audit Report Contract

**Files:**
- Create: `tests/test_ocr_high_risk_rule_audit.py`
- Create: `docs/ocr/high-risk-rule-audit.md`

- [ ] **Step 1: Write the failing report contract test**

Create `tests/test_ocr_high_risk_rule_audit.py`:

```python
from __future__ import annotations

from pathlib import Path


def test_high_risk_rule_audit_has_required_sections() -> None:
    report = Path("docs/ocr/high-risk-rule-audit.md")
    assert report.exists()
    text = report.read_text(encoding="utf-8")

    required = [
        "## Production OCR Chain",
        "## Direct Role Mutations",
        "## Direct Object Matches",
        "## Direct Reorder Decisions",
        "## Renderer Inference",
        "## Remediation Map",
        "## Baseline Counts",
    ]
    for heading in required:
        assert heading in text

    for metric in [
        "direct_role_mutation_count",
        "direct_object_match_count",
        "direct_reorder_decision_count",
        "direct_renderer_inference_count",
    ]:
        assert metric in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/test_ocr_high_risk_rule_audit.py -v --tb=short
```

Expected: FAIL because `docs/ocr/high-risk-rule-audit.md` does not exist or lacks sections.

- [ ] **Step 3: Create the audit report skeleton with concrete production files**

Create `docs/ocr/high-risk-rule-audit.md` with this exact skeleton. Task 2 replaces the zero baseline counts with audited counts and adds rows for each inspected rule family:

```markdown
# OCR High Risk Rule Audit

## Production OCR Chain

`paperforge/worker/ocr.py` is the production orchestrator. The production artifact chain is:

`result.json -> blocks.raw.jsonl -> blocks.structured.jsonl -> document_structure.json -> figure_inventory.json/table_inventory.json -> objects -> render/fulltext.md -> health/ocr_health.json`

Production modules:

- `paperforge/worker/ocr_blocks.py`
- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_figures.py`
- `paperforge/worker/ocr_tables.py`
- `paperforge/worker/ocr_objects.py`
- `paperforge/worker/ocr_render.py`
- `paperforge/worker/ocr_health.py`

## Direct Role Mutations

| File | Symbol | Rule | Current Risk | Remediation |
| --- | --- | --- | --- | --- |

## Direct Object Matches

| File | Symbol | Rule | Current Risk | Remediation |
| --- | --- | --- | --- | --- |

## Direct Reorder Decisions

| File | Symbol | Rule | Current Risk | Remediation |
| --- | --- | --- | --- | --- |

## Renderer Inference

| File | Symbol | Rule | Current Risk | Remediation |
| --- | --- | --- | --- | --- |

## Remediation Map

| Rule Family | Plan | Action |
| --- | --- | --- |
| Figure asset matching | `2026-06-08-ocr-figure-score-matching-plan.md` | Convert nearest-asset choice into scored candidate selection. |
| Table asset matching | `2026-06-08-ocr-table-score-matching-plan.md` | Convert vertical-nearest choice into scored candidate selection. |
| Layout column inference | `2026-06-08-ocr-layout-confidence-plan.md` | Add confidence and low-confidence reorder guard. |
| Structured insert promotion | `2026-06-08-ocr-insert-score-plan.md` | Convert direct promotion into score/candidate behavior. |
| Health aggregation | `2026-06-08-ocr-health-hard-rule-summary-plan.md` | Report remaining hard-rule and uncertainty counts. |

## Baseline Counts

- `direct_role_mutation_count`: 0
- `direct_object_match_count`: 0
- `direct_reorder_decision_count`: 0
- `direct_renderer_inference_count`: 0
```

- [ ] **Step 4: Run the contract test**

Run:

```bash
python -m pytest tests/test_ocr_high_risk_rule_audit.py -q --tb=short
```

Expected: PASS after the report exists with required headings and metrics.

---

### Task 2: Fill Concrete Hard-Rule Findings

**Files:**
- Modify: `docs/ocr/high-risk-rule-audit.md`

- [ ] **Step 1: Inspect direct mutation and match seams**

Use these source locations as the starting checklist:

```text
paperforge/worker/ocr_document.py:_build_region_prepass
paperforge/worker/ocr_document.py:_detect_structured_insert_clusters
paperforge/worker/ocr_document.py:_expand_structured_insert_cluster_with_mixed_sidebar_blocks
paperforge/worker/ocr_document.py:build_document_structure
paperforge/worker/ocr_figures.py:build_figure_inventory
paperforge/worker/ocr_tables.py:_pick_best_asset
paperforge/worker/ocr_tables.py:build_table_inventory
paperforge/worker/ocr_render.py
paperforge/worker/ocr_health.py
```

- [ ] **Step 2: Add known direct role mutation rows**

In `docs/ocr/high-risk-rule-audit.md`, add rows like:

```markdown
| `ocr_document.py` | `_build_region_prepass` | `_in_visual_container` can classify a block as `structured_insert` with confidence `0.85`. | Visual container is treated as a conclusion instead of evidence. | Move to `ocr-insert-score`; visual container becomes one evidence term. |
| `ocr_document.py` | `_build_region_prepass` | `page <= 3` plus key-points/highlights or box anchor can classify `structured_insert`. | Publisher-template sensitive; can swallow body text. | Move to `ocr-insert-score`; keep medium confidence as candidate. |
| `ocr_document.py` | `_build_region_prepass` | `last_insert_on_page` can continue short blocks into `structured_insert`. | Sequential propagation from one early mistake. | Move to `ocr-insert-score`; require cluster coherence and expansion audit. |
```

- [ ] **Step 3: Add known direct object match rows**

Add rows like:

```markdown
| `ocr_figures.py` | `build_figure_inventory` | Same-page nearest asset is assigned to a legend before `caption_score` is computed. | Nearest media can be wrong when multiple figures/assets exist. | Move to `ocr-figure-score-matching`; score all candidates first. |
| `ocr_tables.py` | `_pick_best_asset` | Candidate table asset is selected by vertical distance. | Previous-page, continuation, and rotated tables can misbind. | Move to `ocr-table-score-matching`; select by `score_table_match`. |
```

- [ ] **Step 4: Add baseline counts matching the rows**

Update the `## Baseline Counts` section. Count only the rows that are documented in this audit. Example format:

```markdown
- `direct_role_mutation_count`: 3
- `direct_object_match_count`: 2
- `direct_reorder_decision_count`: 1
- `direct_renderer_inference_count`: 0
```

- [ ] **Step 5: Run the audit contract test**

Run:

```bash
python -m pytest tests/test_ocr_high_risk_rule_audit.py -q --tb=short
```

Expected: PASS.

---

### Task 3: Cross-Reference the Audit From the Master Plan

**Files:**
- Modify: `docs/superpowers/plans/2026-06-08-ocr-v1-convergence-master-plan.md`

- [ ] **Step 1: Add the audit report to the final merge gate**

Add this bullet near the existing route-audit and health gates:

```markdown
- [ ] `docs/ocr/high-risk-rule-audit.md` documents remaining direct hard-rule decisions and maps each one to scorer, guard, removal, or P2 deferral.
```

- [ ] **Step 2: Run a focused markdown contract check**

Run:

```bash
python -m pytest tests/test_ocr_high_risk_rule_audit.py -q --tb=short
```

Expected: PASS.

---

## Verification

Run after all tasks:

```bash
python -m pytest tests/test_ocr_high_risk_rule_audit.py -q --tb=short
```

Expected: PASS.

Do not commit unless the user explicitly requests a commit.
