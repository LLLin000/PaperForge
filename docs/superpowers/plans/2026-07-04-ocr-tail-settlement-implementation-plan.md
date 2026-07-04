# OCR Tail Settlement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the current tail/body/backmatter settlement logic into a dedicated module, preserve current behavior while removing cross-module leakage between `normalize_document_structure()` and `build_structured_blocks()`, then add a settlement report and a hard corpus-diff gate before any policy change.

**Architecture:** Keep the current OCR pipeline order unchanged. First move the existing tail settlement implementation into `paperforge/worker/ocr_tail_settlement.py` and route current call sites through it without changing behavior. Then introduce `TailSettlementReport` so normalize-phase promotion/exclusion and build-phase restore both write into one report attached to `DocumentStructure`. B2 is a verification gate, not a policy rewrite: if the diff is not green, stop.

**Tech Stack:** Python 3, existing PaperForge OCR workers, `DocumentStructure`, pytest, current tail/backmatter render regressions in `tests/test_ocr_rendering.py`

## Global Constraints

- Workstream B only: implement **B0 / B1 / B2**; do not touch Workstream C.
- Workstream A is already landed on this branch (`feat/ocr-tail-settlement`, `964e05b`); do not regress `ocr_object_writeback` behavior.
- B0/B1 are **behavior-preserving extraction only**. Do **not** change tail/backmatter/reference policy in those tasks.
- Do **not** reorder the main OCR pipeline.
- Do **not** change figure/table ownership behavior.
- Keep `block["role"]` as the current public final role contract.
- Because `DocumentStructure` is only materialized late in `normalize_document_structure()` (`ocr_document.py:5678` today), normalize-phase extraction must use module-local helpers first; the public `settle_tail_and_backmatter(...)` wrapper only owns the post-normalize pass until B1 attaches the shared report.
- B2 may only adjust policy after the corpus diff is green. If the diff is not green, stop after instrumentation/reporting and do **not** commit any policy change.

---

## File Structure

- **Create:** `paperforge/worker/ocr_tail_settlement.py`
  - Owns the extracted tail settlement helpers and the public `settle_tail_and_backmatter(...)` wrapper.
  - Hosts `promote_backmatter_heading_candidates(...)`, `exclude_tail_nonref_from_body_flow(...)`, `restore_numbered_body_from_tail_hold(...)`.
  - Hosts `TailSettlementReport` in B1.
- **Modify:** `paperforge/worker/ocr_document.py`
  - Replace the inline backmatter-candidate promotion loop and direct tail exclusion call with imports from `ocr_tail_settlement.py`.
  - Attach the shared `TailSettlementReport` to `DocumentStructure` in B1.
- **Modify:** `paperforge/worker/ocr_blocks.py`
  - Replace the direct `_exclude_tail_nonref_from_body_flow(...)` / `_restore_numbered_body_from_tail_hold(...)` imports and calls with `settle_tail_and_backmatter(...)`.
- **Create:** `tests/test_ocr_tail_settlement.py`
  - Unit tests for B0/B1 extraction behavior and report contents.
- **Reuse existing tests:** `tests/test_ocr_rendering.py`
  - Existing tail/backmatter regressions remain the acceptance suite for behavior-preserving extraction.

---

### Task 1: B0 — Extract the existing tail settlement seam into one deep module

**Files:**
- Create: `paperforge/worker/ocr_tail_settlement.py`
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Create: `tests/test_ocr_tail_settlement.py`

**Interfaces:**
- Consumes:
  - `structured_blocks: list[dict]`
  - optional `document_structure: object | None`
  - current block fields already produced by `normalize_document_structure()` (`role`, `seed_role`, `zone`, `style_family`, `marker_signature`, `text`, `bbox`)
- Produces:
  - `promote_backmatter_heading_candidates(blocks: list[dict]) -> None`
  - `exclude_tail_nonref_from_body_flow(blocks: list[dict]) -> None`
  - `restore_numbered_body_from_tail_hold(blocks: list[dict]) -> None`
  - `settle_tail_and_backmatter(*, structured_blocks: list[dict], document_structure: object | None = None) -> dict`
  - behavior-preserving delegation of the current helper order

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ocr_tail_settlement.py
from __future__ import annotations


def test_promote_backmatter_heading_candidates_promotes_same_page_followers() -> None:
    from paperforge.worker.ocr_tail_settlement import promote_backmatter_heading_candidates

    blocks = [
        {
            "block_id": "h1",
            "page": 10,
            "role": "backmatter_heading_candidate",
            "seed_role": "backmatter_heading_candidate",
            "text": "Funding",
            "bbox": [100, 100, 260, 130],
        },
        {
            "block_id": "b1",
            "page": 10,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": "This work was supported by Grant A.",
            "bbox": [100, 150, 520, 220],
        },
        {
            "block_id": "b2",
            "page": 10,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": "The funders had no role in study design.",
            "bbox": [100, 230, 520, 300],
        },
    ]

    promote_backmatter_heading_candidates(blocks)

    assert blocks[0]["role"] == "backmatter_heading"
    assert blocks[1]["role"] == "backmatter_body"
    assert blocks[2]["role"] == "backmatter_body"


def test_settle_tail_and_backmatter_preserves_tail_hold_restore() -> None:
    from paperforge.worker.ocr_tail_settlement import settle_tail_and_backmatter

    blocks = [
        {
            "block_id": "h1",
            "page": 11,
            "role": "section_heading",
            "zone": "tail_nonref_hold_zone",
            "style_family": "heading_like",
            "marker_signature": {"type": "heading_numbered"},
            "text": "5. Conclusions",
        },
        {
            "block_id": "b1",
            "page": 11,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "zone": "tail_nonref_hold_zone",
            "text": "Funding: supported by Grant A.",
        },
        {
            "block_id": "b2",
            "page": 11,
            "role": "backmatter_body",
            "zone": "tail_nonref_hold_zone",
            "style_family": "body_like",
            "marker_signature": {"type": "none"},
            "text": "This section returns to the main conclusions.",
        },
    ]

    report = settle_tail_and_backmatter(structured_blocks=blocks, document_structure=None)

    assert blocks[1]["role"] == "backmatter_body"
    assert blocks[2]["role"] == "body_paragraph"
    assert report["applied_count"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
`python -m pytest tests/test_ocr_tail_settlement.py::test_promote_backmatter_heading_candidates_promotes_same_page_followers tests/test_ocr_tail_settlement.py::test_settle_tail_and_backmatter_preserves_tail_hold_restore -v --tb=short`

Expected: FAIL with `ModuleNotFoundError: No module named 'paperforge.worker.ocr_tail_settlement'`

- [ ] **Step 3: Write minimal implementation**

```python
# paperforge/worker/ocr_tail_settlement.py
from __future__ import annotations

import re

from paperforge.worker.ocr_decisions import record_decision

_BACKMATTER_TITLE_DENY_LIST: frozenset[str] = frozenset()
_BACKMATTER_BODY_SIGNALS = re.compile(
    r"\b(?:declare|conflict|interest|funding|support|grant|author|contribut|"
    r"acknowledge|thank|ethic|review|approv|consent|availab|data|material|"
    r"competing|financial|disclos|report|none|no conflict|nothing to declare)\b",
    re.IGNORECASE,
)


def _block_text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _next_nonempty_block_same_page(blocks: list[dict], idx: int) -> dict | None:
    page = blocks[idx].get("page")
    if page is None:
        return None
    for j in range(idx + 1, len(blocks)):
        if blocks[j].get("page") != page:
            break
        if _block_text(blocks[j]).strip():
            return blocks[j]
    return None


def _canonical_section_text(block: dict) -> str:
    text = _block_text(block).strip().lower()
    if re.match(r"^(?:\w\s)+\w$", text):
        text = re.sub(r"\s+", "", text)
    return text


def _looks_like_tail_body(block: dict) -> bool:
    text = _block_text(block).strip()
    if not text:
        return False
    words = text.split()
    if len(words) > 80:
        return False
    role = block.get("role", "")
    if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
        return False
    return bool(_BACKMATTER_BODY_SIGNALS.search(text))


def _looks_like_backmatter_body_text(text: str) -> bool:
    lower = text.lower()
    markers = (
        "conflict of interest",
        "declaration",
        "publisher",
        "author contributions",
        "funding",
        "acknowledg",
        "data availability",
        "supplement",
        "ethics",
        "copyright",
    )
    return any(marker in lower for marker in markers)


def promote_backmatter_heading_candidates(blocks: list[dict]) -> None:
    for idx, block in enumerate(blocks):
        is_candidate = (
            block.get("role") == "backmatter_heading_candidate"
            or block.get("seed_role") == "backmatter_heading_candidate"
        )
        if not is_candidate or block.get("role") == "backmatter_heading":
            continue
        next_body = _next_nonempty_block_same_page(blocks, idx)
        if next_body and next_body.get("role") in {"body_paragraph", "backmatter_body"} and _looks_like_tail_body(next_body):
            old_role = block.get("role")
            block["role"] = "backmatter_heading"
            block.setdefault("role_confidence", 0.6)
            if old_role != block["role"]:
                record_decision(
                    block,
                    stage="backmatter_candidate_promotion",
                    old_role=old_role,
                    new_role=block["role"],
                    reason="backmatter heading candidate promoted: followed by tail-like body on same page",
                )
            for j in range(idx + 1, len(blocks)):
                if blocks[j].get("page") != block.get("page"):
                    break
                if blocks[j].get("role") == "body_paragraph":
                    old_follower_role = blocks[j].get("role")
                    blocks[j]["role"] = "backmatter_body"
                    blocks[j].setdefault("role_confidence", 0.6)
                    if old_follower_role != blocks[j]["role"]:
                        record_decision(
                            blocks[j],
                            stage="backmatter_candidate_promotion",
                            old_role=old_follower_role,
                            new_role=blocks[j]["role"],
                            reason="follower body converted to backmatter_body under confirmed heading",
                        )
            break


def exclude_tail_nonref_from_body_flow(blocks: list[dict]) -> None:
    for block in blocks:
        effective_role = block.get("role")
        if effective_role == "unassigned":
            effective_role = block.get("seed_role")
        if effective_role != "body_paragraph":
            continue
        if block.get("zone") != "tail_nonref_hold_zone":
            continue
        text = _block_text(block)
        if not _looks_like_backmatter_body_text(text):
            continue
        old_role = block.get("role")
        block["role"] = "backmatter_body"
        if block.get("seed_role") == "body_paragraph":
            block["seed_role"] = "backmatter_body"
        if old_role != block["role"]:
            record_decision(
                block,
                stage="tail_nonref_exclusion",
                old_role=old_role,
                new_role=block["role"],
                reason="tail non-reference body block excluded from body flow",
            )
        block.setdefault("evidence", []).append("tail_nonref_hold_zone excluded from body flow")


def restore_numbered_body_from_tail_hold(blocks: list[dict]) -> None:
    active_numbered_body = False
    for block in blocks:
        role = block.get("role")
        text = _canonical_section_text(block)
        marker_type = str(((block.get("marker_signature") or {}).get("type")) or "none")

        if role in {"reference_heading", "backmatter_heading", "backmatter_boundary_heading"}:
            active_numbered_body = False
            continue

        if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
            active_numbered_body = (
                (
                    marker_type in {"heading_numbered", "heading_arabic", "heading_decimal", "heading_roman", "heading_alpha"}
                    or (block.get("zone") == "tail_nonref_hold_zone" and str(block.get("style_family") or "") == "heading_like")
                )
                and text not in _BACKMATTER_TITLE_DENY_LIST
            )
            continue

        if role == "backmatter_body" and active_numbered_body:
            block["role"] = "body_paragraph"


def settle_tail_and_backmatter(*, structured_blocks: list[dict], document_structure: object | None = None) -> dict:
    exclude_tail_nonref_from_body_flow(structured_blocks)
    restore_numbered_body_from_tail_hold(structured_blocks)
    return {
        "promoted_backmatter_heading_ids": [],
        "converted_to_backmatter_body_ids": [],
        "restored_body_paragraph_ids": [],
        "applied_count": 0,
    }
```

```python
# paperforge/worker/ocr_document.py
# add near the top-level imports
from paperforge.worker.ocr_tail_settlement import (
    promote_backmatter_heading_candidates,
    exclude_tail_nonref_from_body_flow,
)

# inside normalize_document_structure(...), replace the inline loop + direct helper call:
promote_backmatter_heading_candidates(blocks)
exclude_tail_nonref_from_body_flow(blocks)

# later, replace the second direct helper call too:
exclude_tail_nonref_from_body_flow(blocks)
```

```python
# paperforge/worker/ocr_blocks.py
# replace:
# from paperforge.worker.ocr_document import (
#     _exclude_tail_nonref_from_body_flow,
#     _restore_numbered_body_from_tail_hold,
# )
# _exclude_tail_nonref_from_body_flow(rows)
# _restore_numbered_body_from_tail_hold(rows)

from paperforge.worker.ocr_tail_settlement import settle_tail_and_backmatter

settle_tail_and_backmatter(structured_blocks=rows, document_structure=doc_structure)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
`python -m pytest tests/test_ocr_tail_settlement.py::test_promote_backmatter_heading_candidates_promotes_same_page_followers tests/test_ocr_tail_settlement.py::test_settle_tail_and_backmatter_preserves_tail_hold_restore -v --tb=short`

Expected: PASS

- [ ] **Step 5: Run the behavior-preserving tail regression subset**

Run:
`python -m pytest tests/test_ocr_rendering.py::test_tail_zone_noise_band_guard tests/test_ocr_rendering.py::test_tail_zone_supplementary_material_not_noise tests/test_ocr_rendering.py::test_tail_candidate_overreach_does_not_absorb_late_body tests/test_ocr_rendering.py::test_cross_page_funding_continuation_preserves_order tests/test_ocr_rendering.py::test_mixed_tail_page_keeps_late_body_out_of_funding_and_attaches_real_funding tests/test_ocr_rendering.py::test_backmatter_boundary_normalizes_child_sections_before_references -q --tb=line`

Expected: PASS, because B0 is extraction-only.

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_tail_settlement.py paperforge/worker/ocr_document.py paperforge/worker/ocr_blocks.py tests/test_ocr_tail_settlement.py
git commit -m "refactor: extract OCR tail settlement helpers"
```

---

### Task 2: B1 — Add `TailSettlementReport` and attach it to `DocumentStructure`

**Files:**
- Modify: `paperforge/worker/ocr_tail_settlement.py`
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `tests/test_ocr_tail_settlement.py`

**Interfaces:**
- Consumes:
  - extracted B0 helper functions from `ocr_tail_settlement.py`
  - `DocumentStructure` from `ocr_document.py`
- Produces:
  - `TailSettlementReport`
  - `DocumentStructure.tail_settlement_report`
  - report accumulation across normalize-phase promotion/exclusion and build-phase restore

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ocr_tail_settlement.py
from __future__ import annotations


def test_settle_tail_and_backmatter_reports_promotions_conversions_and_restores() -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    from paperforge.worker.ocr_tail_settlement import (
        TailSettlementReport,
        promote_backmatter_heading_candidates,
        exclude_tail_nonref_from_body_flow,
        settle_tail_and_backmatter,
    )

    blocks = [
        {
            "block_id": "h1",
            "page": 10,
            "role": "backmatter_heading_candidate",
            "seed_role": "backmatter_heading_candidate",
            "text": "Funding",
            "bbox": [100, 100, 260, 130],
        },
        {
            "block_id": "b1",
            "page": 10,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "zone": "tail_nonref_hold_zone",
            "text": "Funding: supported by Grant A.",
            "bbox": [100, 150, 520, 220],
        },
        {
            "block_id": "h2",
            "page": 11,
            "role": "section_heading",
            "zone": "tail_nonref_hold_zone",
            "style_family": "heading_like",
            "marker_signature": {"type": "heading_numbered"},
            "text": "5. Conclusions",
        },
        {
            "block_id": "b2",
            "page": 11,
            "role": "backmatter_body",
            "zone": "tail_nonref_hold_zone",
            "style_family": "body_like",
            "marker_signature": {"type": "none"},
            "text": "This section returns to the main conclusions.",
        },
    ]

    report = TailSettlementReport()
    promote_backmatter_heading_candidates(blocks, report=report)
    exclude_tail_nonref_from_body_flow(blocks, report=report)

    doc = DocumentStructure(tail_settlement_report=report)
    returned = settle_tail_and_backmatter(structured_blocks=blocks, document_structure=doc)

    assert returned is report
    assert report.promoted_backmatter_heading_ids == ["h1"]
    assert report.converted_to_backmatter_body_ids == ["b1"]
    assert report.restored_body_paragraph_ids == ["b2"]
    assert doc.tail_settlement_report is report
```

- [ ] **Step 2: Run test to verify it fails**

Run:
`python -m pytest tests/test_ocr_tail_settlement.py::test_settle_tail_and_backmatter_reports_promotions_conversions_and_restores -v --tb=short`

Expected: FAIL on missing `TailSettlementReport`, missing `report=` parameters, or missing `DocumentStructure.tail_settlement_report`

- [ ] **Step 3: Write minimal implementation**

```python
# paperforge/worker/ocr_tail_settlement.py
from dataclasses import dataclass, field


@dataclass
class TailSettlementReport:
    promoted_backmatter_heading_ids: list[str] = field(default_factory=list)
    converted_to_backmatter_body_ids: list[str] = field(default_factory=list)
    restored_body_paragraph_ids: list[str] = field(default_factory=list)

    @property
    def applied_count(self) -> int:
        return (
            len(self.promoted_backmatter_heading_ids)
            + len(self.converted_to_backmatter_body_ids)
            + len(self.restored_body_paragraph_ids)
        )
```

```python
# paperforge/worker/ocr_tail_settlement.py
# update helper signatures

def promote_backmatter_heading_candidates(blocks: list[dict], report: TailSettlementReport | None = None) -> None:
    ...
    if old_role != block["role"] and report is not None:
        report.promoted_backmatter_heading_ids.append(str(block.get("block_id")))
    ...
    if old_follower_role != blocks[j]["role"] and report is not None:
        report.converted_to_backmatter_body_ids.append(str(blocks[j].get("block_id")))


def exclude_tail_nonref_from_body_flow(blocks: list[dict], report: TailSettlementReport | None = None) -> None:
    ...
    if old_role != block["role"] and report is not None:
        report.converted_to_backmatter_body_ids.append(str(block.get("block_id")))


def restore_numbered_body_from_tail_hold(blocks: list[dict], report: TailSettlementReport | None = None) -> None:
    ...
    if role == "backmatter_body" and active_numbered_body:
        block["role"] = "body_paragraph"
        if report is not None:
            report.restored_body_paragraph_ids.append(str(block.get("block_id")))


def settle_tail_and_backmatter(
    *, structured_blocks: list[dict], document_structure: object | None = None
) -> TailSettlementReport:
    report = getattr(document_structure, "tail_settlement_report", None) if document_structure is not None else None
    if report is None:
        report = TailSettlementReport()
        if document_structure is not None:
            document_structure.tail_settlement_report = report
    exclude_tail_nonref_from_body_flow(structured_blocks, report=report)
    restore_numbered_body_from_tail_hold(structured_blocks, report=report)
    return report
```

```python
# paperforge/worker/ocr_document.py
from typing import TYPE_CHECKING
...
if TYPE_CHECKING:
    from paperforge.worker.ocr_tail_settlement import TailSettlementReport
...
@dataclass
class DocumentStructure:
    ...
    tail_settlement_report: "TailSettlementReport | None" = None
```

```python
# paperforge/worker/ocr_document.py
# inside normalize_document_structure(...)
from paperforge.worker.ocr_tail_settlement import TailSettlementReport

...
settlement_report = TailSettlementReport()
promote_backmatter_heading_candidates(blocks, report=settlement_report)
exclude_tail_nonref_from_body_flow(blocks, report=settlement_report)
...
exclude_tail_nonref_from_body_flow(blocks, report=settlement_report)
...
doc_structure = DocumentStructure(
    ...,
    tail_settlement_report=settlement_report,
)
```

```python
# paperforge/worker/ocr_blocks.py
settle_tail_and_backmatter(structured_blocks=rows, document_structure=doc_structure)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
`python -m pytest tests/test_ocr_tail_settlement.py::test_settle_tail_and_backmatter_reports_promotions_conversions_and_restores -v --tb=short`

Expected: PASS

- [ ] **Step 5: Run B0 + B1 focused suite**

Run:
`python -m pytest tests/test_ocr_tail_settlement.py tests/test_ocr_rendering.py::test_tail_zone_noise_band_guard tests/test_ocr_rendering.py::test_tail_zone_supplementary_material_not_noise tests/test_ocr_rendering.py::test_tail_candidate_overreach_does_not_absorb_late_body tests/test_ocr_rendering.py::test_cross_page_funding_continuation_preserves_order tests/test_ocr_rendering.py::test_mixed_tail_page_keeps_late_body_out_of_funding_and_attaches_real_funding tests/test_ocr_rendering.py::test_backmatter_boundary_normalizes_child_sections_before_references -q --tb=line`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_tail_settlement.py paperforge/worker/ocr_document.py paperforge/worker/ocr_blocks.py tests/test_ocr_tail_settlement.py
git commit -m "feat: add OCR tail settlement report"
```

---

### Task 3: B2 — Corpus-diff gate before any policy change

**Files:**
- No production-file changes by default.
- Reuse: `tests/test_ocr_tail_settlement.py`
- Reuse: `tests/test_ocr_rendering.py`
- Reuse: `tests/test_ocr_object_writeback.py`
- Reuse: `tests/test_appendix_figure_numbering.py`

**Interfaces:**
- Consumes:
  - B0/B1 extracted tail-settlement module and report
  - existing render regressions for tail/backmatter ordering
  - existing Workstream A tests to prove no cross-regression
- Produces:
  - go / no-go decision for any future tail policy edits
  - **no policy change commit unless diff is green**

- [ ] **Step 1: Run the full tail/backmatter acceptance suite**

Run:
`python -m pytest tests/test_ocr_tail_settlement.py tests/test_ocr_rendering.py::test_tail_zone_noise_band_guard tests/test_ocr_rendering.py::test_tail_zone_supplementary_material_not_noise tests/test_ocr_rendering.py::test_tail_candidate_overreach_does_not_absorb_late_body tests/test_ocr_rendering.py::test_cross_page_funding_continuation_preserves_order tests/test_ocr_rendering.py::test_mixed_tail_page_keeps_late_body_out_of_funding_and_attaches_real_funding tests/test_ocr_rendering.py::test_backmatter_boundary_normalizes_child_sections_before_references -q --tb=line`

Expected: PASS

- [ ] **Step 2: Run cross-workstream guard suite**

Run:
`python -m pytest tests/test_ocr_object_writeback.py tests/test_ocr_rendering.py::test_body_renderer_skips_consumed_object_owned_blocks tests/test_appendix_figure_numbering.py -q --tb=line`

Expected: PASS — Workstream B must not disturb Workstream A.

- [ ] **Step 3: Evaluate whether any policy change is even needed**

Decision rule:
- If **all** B0/B1 tests are green and the tail/backmatter render regressions remain green, **stop here**. Workstream B is complete as an extraction/reporting phase.
- If a future branch still needs a tail policy change, create a fresh micro-spec and micro-plan for that change; do **not** smuggle policy edits into this workstream after a green diff.

- [ ] **Step 4: Commit only if code changed in this task**

```bash
# Default case after a green diff gate: no code changed in B2, so no commit.
git status --short
#
# Expected: no output
#
# If you intentionally tightened the gate by editing only
# tests/test_ocr_tail_settlement.py in this task, use:
git add tests/test_ocr_tail_settlement.py
git commit -m "chore: lock OCR tail settlement diff gate"
```

---

## Self-Review

- **Spec coverage:** This plan covers Workstream B from `2026-07-04-ocr-pipeline-deepening-design.md`: B0 extraction, B1 report, B2 diff gate. It intentionally does **not** start Workstream C.
- **Grounding against current code:** The plan explicitly reflects the current split call order: normalize-phase promotion/exclusion still happens before `DocumentStructure` exists (`ocr_document.py:5474-5521` today), while build-phase exclusion/restore still happens in `ocr_blocks.py:350-356` today. That sequencing is preserved.
- **Placeholder scan:** No `TODO`/`TBD` placeholders remain. B2 is intentionally a stop gate, not an unfinished implementation.
- **Type consistency:** B0 starts with a dict return for the wrapper because the module is brand-new; B1 upgrades that wrapper to `TailSettlementReport` and attaches it to `DocumentStructure`. The helper names are consistent across all tasks.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-04-ocr-tail-settlement-implementation-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
