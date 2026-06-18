# OCR-v2 Readiness Master Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the first four OCR-v2 readiness gates so the branch can be called "state healthy" on known layout classes, then leave unseen-paper blind audit as the next-stage gate with explicit entry criteria.

**Architecture:** Keep the anchor-first OCR-v2 backbone and sequence the remaining work as four readiness phases: completeness detection, figure ownership generalization, ordering/boundary authority cleanup, and layout-class coverage formalization. Reuse the existing completeness and figure-group designs where they are already strong, add only the missing execution detail for ordering authority and coverage formalization, and keep project truth files aligned after each phase so the branch has one active narrative.

**Tech Stack:** Python 3.14, existing `paperforge.worker` OCR pipeline, pytest, audit-backed real-paper regressions, repo-local docs under `project/current/`, audit artifacts under `audit/`.

---

## File Structure

- Modify: `paperforge/worker/ocr_blocks.py`
  - Owns structured-block build flow; Gate 1 belongs here.
- Modify: `paperforge/worker/ocr_pdf_spans.py`
  - Owns PDF-region lookup / backfill utilities; Gate 1 should reuse this rather than fork a second PDF-text path.
- Modify: `paperforge/worker/ocr_health.py`
  - Best home for rendered-text coverage summary output.
- Modify: `paperforge/worker/ocr_figures.py`
  - Owns Gate 2 figure ownership logic.
- Modify: `paperforge/worker/ocr_document.py`
  - Owns Gate 3 boundary authority and normalized structure truth.
- Modify: `paperforge/worker/ocr_orchestrator.py`
  - May need small cleanup if ordering authority still leaks downstream.
- Modify: `paperforge/worker/ocr_render.py`
  - Keep only minimal presentation ordering after Gate 3.
- Modify: `tests/test_ocr_document.py`
  - Gate 1 and Gate 3 unit/regression coverage.
- Modify: `tests/test_ocr_figures.py`
  - Gate 2 deterministic inventory coverage.
- Modify: `tests/test_ocr_real_paper_regressions.py`
  - Production-path replay checks for Gates 1-3.
- Modify: `tests/test_ocr_real_paper_audit_contracts.py`
  - Gate 4 contract tightening; move it off stale fixture-ledger assumptions.
- Create: `audit/coverage_ledger.json`
  - Readiness ledger for real audited papers and layout/risk coverage.
- Modify: `project/current/ocr-v2-closeout-priority.md`
  - Keep the short active queue aligned after each phase.
- Modify: `project/current/ocr-v2-generalization-boundary.md`
  - Keep the broader architectural note aligned.
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
  - Keep active residuals aligned to actual gates.
- Modify: `PROJECT-MANAGEMENT.md`
  - Record each completed phase and any newly parked hard cases.

---

### Task 1: Lock The Readiness-Gates Baseline And Replace The Stale Fixture-Ledger Assumption

**Files:**
- Create: `audit/coverage_ledger.json`
- Modify: `tests/test_ocr_real_paper_audit_contracts.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`
- Modify: `project/current/ocr-v2-closeout-priority.md`
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`

- [ ] **Step 1: Create an audit-side coverage ledger from the real audited paper set**

Create `audit/coverage_ledger.json` with a minimal but valid readiness ledger shape:

```json
{
  "audit_root": "audit",
  "papers": [
    {"paper_key": "2GN9LMCW", "layout_tags": ["single_column", "special_structure"], "risk_tags": ["special_structure"]},
    {"paper_key": "6FGDBFQN", "layout_tags": ["multi_column", "side_caption"], "risk_tags": ["figure_heavy"]},
    {"paper_key": "A8E7SRVS", "layout_tags": ["multi_column"], "risk_tags": ["table_heavy"]},
    {"paper_key": "CAQNW9Q2", "layout_tags": ["multi_column", "same_page_ref_body_split"], "risk_tags": ["reference_boundary_sensitive", "frontmatter_sensitive"]},
    {"paper_key": "DWQQK2YB", "layout_tags": ["multi_column", "preproof_frontmatter", "post_reference_biography"], "risk_tags": ["frontmatter_sensitive", "figure_heavy", "cross_page_caption"]},
    {"paper_key": "K7R8PEKW", "layout_tags": ["single_column"], "risk_tags": ["frontmatter_sensitive"]},
    {"paper_key": "SAN9AYVR", "layout_tags": ["multi_column"], "risk_tags": ["special_structure"]},
    {"paper_key": "TSCKAVIS", "layout_tags": ["single_column", "review_callout"], "risk_tags": ["special_structure", "table_heavy"]}
  ]
}
```

- [ ] **Step 2: Move the audit-contract test off `tests/fixtures` manifest lookup**

In `tests/test_ocr_real_paper_audit_contracts.py`, change the ledger root and replace the current coarse check with an explicit readiness-class check:

```python
LEDGER_PATH = Path(__file__).resolve().parents[1] / "audit" / "coverage_ledger.json"


def test_gold_set_covers_readiness_layout_classes() -> None:
    manifest = _load_manifest()
    all_layouts = {tag for paper in manifest["papers"] for tag in paper.get("layout_tags", [])}
    assert "preproof_frontmatter" in all_layouts
    assert "same_page_ref_body_split" in all_layouts
    assert any(tag in all_layouts for tag in {"side_caption", "multi_panel"})
    assert "post_reference_biography" in all_layouts
    assert any(tag in all_layouts for tag in {"review_callout", "special_structure"})
```

- [ ] **Step 3: Add a Gate 2 red regression that no longer allows ambiguity as success for DW Figure 3**

In `tests/test_ocr_real_paper_regressions.py`, replace the current permissive assertion with a strict ownership target:

```python
def test_dwqqk2yb_figure3_is_fully_owned_not_merely_captured(tmp_path: Path) -> None:
    result = replay_production_pipeline("DWQQK2YB", tmp_path)
    reader_payload = result["reader_payload"]
    matched, ambiguous = _reader_figure_index(reader_payload)

    assert 3 in matched, "Fig 3 should be matched, not left ambiguous"
    assert 3 not in ambiguous, "Fig 3 ambiguity is no longer acceptable after Gate 2"
```

- [ ] **Step 4: Run the red baseline checks**

Run: `python -m pytest tests/test_ocr_real_paper_audit_contracts.py -v`

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_figure3_is_fully_owned" -v`

Expected: audit-ledger tests PASS once the ledger exists; the Gate 2 DW ownership test FAILS until Task 3 lands.

- [ ] **Step 5: Commit the baseline and ledger restoration**

```bash
git add audit/coverage_ledger.json tests/test_ocr_real_paper_audit_contracts.py tests/test_ocr_real_paper_regressions.py project/current/ocr-v2-closeout-priority.md project/current/ocr-v2-remaining-issues-2026-06-18.md
git commit -m "test: lock OCR readiness baseline and restore coverage ledger"
```

---

### Task 2: Implement Gate 1 Completeness Signals

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_pdf_spans.py`
- Modify: `paperforge/worker/ocr_health.py`
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add failing page-level and region-level completeness tests**

In `tests/test_ocr_document.py`, add two focused tests:

```python
def test_page_text_coverage_flags_low_ratio_when_pdf_text_dominates() -> None:
    from paperforge.worker.ocr_blocks import _summarize_page_text_coverage

    result = _summarize_page_text_coverage(
        ocr_text="short text",
        pdf_text="short text plus a much longer native PDF segment that should dominate coverage",
    )

    assert result["page_text_coverage_status"] == "low"
    assert result["page_text_coverage_ratio_chars"] < 0.5


def test_region_text_completeness_marks_empty_vs_pdf() -> None:
    from paperforge.worker.ocr_blocks import _classify_region_text_completeness

    result = _classify_region_text_completeness(
        ocr_text="",
        pdf_region_text="A complete sentence present in the PDF native text layer.",
    )

    assert result["text_completeness_status"] == "empty_vs_pdf"
```

- [ ] **Step 2: Add failing rendered-gap audit test**

Still in `tests/test_ocr_document.py`, add:

```python
def test_rendered_text_coverage_flags_missing_pdf_segment() -> None:
    from paperforge.worker.ocr_health import audit_rendered_text_coverage

    result = audit_rendered_text_coverage(
        rendered_markdown="Only the introduction survived.",
        pdf_segments=["Only the introduction survived.", "A long methods segment that is missing from render."],
    )

    assert result["rendered_text_gap_count"] == 1
```

- [ ] **Step 3: Run red tests for Gate 1**

Run: `python -m pytest tests/test_ocr_document.py -k "coverage or completeness or rendered_text_coverage" -v`

Expected: FAIL.

- [ ] **Step 4: Add the minimal completeness helpers and wire them into structured-block build**

In `paperforge/worker/ocr_blocks.py`, add small helper seams and attach the emitted metadata before `normalize_document_structure()`:

```python
def _summarize_page_text_coverage(*, ocr_text: str, pdf_text: str) -> dict:
    ocr_chars = len((ocr_text or "").strip())
    pdf_chars = len((pdf_text or "").strip())
    if pdf_chars == 0:
        return {"page_text_coverage_status": "missing_pdf_text", "page_text_coverage_ratio_chars": 1.0}
    ratio = ocr_chars / max(pdf_chars, 1)
    return {
        "page_text_coverage_status": "low" if ratio < 0.6 else "ok",
        "page_text_coverage_ratio_chars": ratio,
    }


def _classify_region_text_completeness(*, ocr_text: str, pdf_region_text: str) -> dict:
    ocr = (ocr_text or "").strip()
    pdf = (pdf_region_text or "").strip()
    if not pdf:
        return {"text_completeness_status": "pdf_unavailable", "text_completeness_confidence": 0.0}
    if not ocr:
        return {"text_completeness_status": "empty_vs_pdf", "text_completeness_confidence": 0.95}
    if len(ocr) < len(pdf) * 0.45:
        return {"text_completeness_status": "short_vs_pdf", "text_completeness_confidence": 0.8}
    if pdf.startswith(ocr) and len(pdf) > len(ocr) + 24:
        return {"text_completeness_status": "likely_missing_tail", "text_completeness_confidence": 0.85}
    return {"text_completeness_status": "complete", "text_completeness_confidence": 0.7}
```

- [ ] **Step 5: Add rendered-gap audit in health layer**

In `paperforge/worker/ocr_health.py`, add:

```python
def audit_rendered_text_coverage(*, rendered_markdown: str, pdf_segments: list[str]) -> dict:
    missing = [segment for segment in pdf_segments if segment and segment not in rendered_markdown]
    return {
        "rendered_text_gap_count": len(missing),
        "rendered_text_gap_examples": missing[:3],
    }
```

- [ ] **Step 6: Run Gate 1 focused tests until green**

Run: `python -m pytest tests/test_ocr_document.py -k "coverage or completeness or rendered_text_coverage" -v`

Expected: PASS.

- [ ] **Step 7: Run the nearest production-path Gate 1 regression slice**

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "DWQQK2YB or CAQNW9Q2" -v`

Expected: PASS or only pre-existing skipped tests; no new failures.

- [ ] **Step 8: Commit Gate 1**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_pdf_spans.py paperforge/worker/ocr_health.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py PROJECT-MANAGEMENT.md
git commit -m "feat: add OCR completeness coverage signals"
```

---

### Task 3: Implement Gate 2 Group-First Figure Ownership Generalization

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_health.py`
- Modify: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add the failing deterministic group-first unit test if it is not already present**

In `tests/test_ocr_figures.py`, keep the unit explicit:

```python
def test_group_first_matching_prefers_same_row_pair_over_single_asset() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        {"block_id": 1, "role": "figure_caption", "text": "Fig. 2 A and B, MRI and gross anatomic correlation.", "page": 3, "bbox": [80, 120, 420, 210]},
        {"block_id": 2, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [450, 120, 780, 520]},
        {"block_id": 3, "role": "media_asset", "raw_label": "image", "page": 3, "bbox": [805, 120, 1130, 520]},
    ]

    inventory = build_figure_inventory(blocks, page_width=1200)
    matched = inventory["matched_figures"]

    assert len(matched) == 1
    assert [a["block_id"] for a in matched[0]["matched_assets"]] == [2, 3]
```

- [ ] **Step 2: Run the focused Gate 2 red tests**

Run: `python -m pytest tests/test_ocr_figures.py -k "group_first_matching_prefers_same_row_pair or partition_assets_by_caption_bands" -v`

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "dwqqk2yb_figure3_is_fully_owned" -v`

Expected: at least the DW ownership test FAILS until the refactor lands.

- [ ] **Step 3: Implement candidate-group-first matching in `ocr_figures.py`**

Add deterministic candidate group helpers and reserve asset sets rather than individual assets:

```python
def _candidate_group_entry(group_id: str, page: int, media_blocks: list[dict], group_type: str, evidence: list[str]) -> dict:
    return {
        "group_id": group_id,
        "page": page,
        "group_type": group_type,
        "asset_block_ids": [b.get("block_id") for b in media_blocks],
        "media_blocks": media_blocks,
        "group_evidence": evidence,
    }


def _build_candidate_figure_groups_from_assets(assets: list[dict]) -> list[dict]:
    groups: list[dict] = []
    for asset in assets:
        groups.append(_candidate_group_entry(f"single_{asset['block_id']}", asset.get("page", 0), [asset], "single_asset", ["single_asset"]))
    return groups
```

Then update `build_figure_inventory()` so legend scoring consumes candidate groups first, and fallback only sees truly unclaimed assets.

- [ ] **Step 4: Expose grouped-vs-single counters in health output**

In `paperforge/worker/ocr_health.py`, add grouped counters to the figure summary:

```python
figure_summary["grouped_match_count"] = sum(1 for item in matched_figures if len(item.get("matched_assets", [])) > 1)
figure_summary["single_match_count"] = sum(1 for item in matched_figures if len(item.get("matched_assets", [])) == 1)
```

- [ ] **Step 5: Run Gate 2 tests until green**

Run: `python -m pytest tests/test_ocr_figures.py -k "group_first_matching_prefers_same_row_pair or partition_assets_by_caption_bands" -v`

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "DWQQK2YB" -v`

Expected: PASS, with no ambiguity-acceptable DW Figure 3 path remaining.

- [ ] **Step 6: Commit Gate 2**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_health.py tests/test_ocr_figures.py tests/test_ocr_real_paper_regressions.py PROJECT-MANAGEMENT.md
git commit -m "feat: generalize OCR figure ownership with group-first matching"
```

---

### Task 4: Implement Gate 3 Ordering And Boundary Authority Cleanup

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_orchestrator.py`
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add a failing same-page mixed-layout authority test**

In `tests/test_ocr_document.py`, add:

```python
def test_same_page_reference_boundary_is_resolved_upstream_not_in_renderer() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"block_id": "body_1", "page": 7, "seed_role": "body_paragraph", "text": "Conclusion text above refs.", "bbox": [80, 420, 980, 510]},
        {"block_id": "refs_h", "page": 7, "seed_role": "reference_heading", "text": "References", "bbox": [80, 900, 320, 960]},
        {"block_id": "ref_1", "page": 7, "seed_role": "reference_item", "text": "[1] First ref", "bbox": [80, 980, 980, 1060]},
    ]

    _doc, normalized = normalize_document_structure(blocks)
    by_id = {b["block_id"]: b for b in normalized}
    assert by_id["body_1"]["role"] == "body_paragraph"
    assert by_id["ref_1"]["role"] == "reference_item"
```

- [ ] **Step 2: Run the red Gate 3 authority tests**

Run: `python -m pytest tests/test_ocr_document.py -k "reference_boundary_is_resolved_upstream" -v`

Expected: FAIL if renderer/orchestrator still carries meaningful authority for this case.

- [ ] **Step 3: Move authority to explicit structure artifacts**

In `paperforge/worker/ocr_document.py`, add a small artifact-first helper:

```python
def _same_page_reference_boundary_y(page_blocks: list[dict]) -> float | None:
    headings = [b for b in page_blocks if b.get("seed_role") == "reference_heading"]
    if not headings:
        return None
    return min((b.get("bbox") or [0, 0, 0, 0])[1] for b in headings)
```

Then classify blocks above that Y boundary as body-capable and blocks below it as reference-capable before renderer ordering runs.

- [ ] **Step 4: Shrink renderer-side reorder logic**

In `paperforge/worker/ocr_render.py`, replace any correctness-bearing mixed-page reorder branch with a no-op or assertion that structure ordering already exists:

```python
# ponytail: renderer should consume normalized order, not invent it.
ordered_blocks = structured_blocks
```

If a minimal presentational sort is still required, keep it local to already-normalized sibling groups only.

- [ ] **Step 5: Run Gate 3 focused tests until green**

Run: `python -m pytest tests/test_ocr_document.py -k "reference_boundary_is_resolved_upstream or same_page" -v`

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "CAQNW9Q2 or DWQQK2YB" -v`

Expected: PASS.

- [ ] **Step 6: Commit Gate 3**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_orchestrator.py paperforge/worker/ocr_render.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py PROJECT-MANAGEMENT.md project/current/ocr-v2-generalization-boundary.md
git commit -m "refactor: move OCR ordering authority upstream"
```

---

### Task 5: Implement Gate 4 Layout-Coverage Formalization

**Files:**
- Modify: `audit/coverage_ledger.json`
- Modify: `tests/test_ocr_real_paper_audit_contracts.py`
- Modify: `project/current/ocr-v2-generalization-boundary.md`
- Modify: `project/current/ocr-v2-closeout-priority.md`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Expand the audit ledger taxonomy beyond broad layout labels**

In `audit/coverage_ledger.json`, keep the new readiness-class tags and normalize naming to the approved set:

```json
"layout_tags": ["multi_column", "same_page_ref_body_split", "preproof_frontmatter"]
```

Use only these readiness-class names in this phase:

```text
multi_panel
side_caption
same_page_ref_body_split
post_reference_biography
preproof_frontmatter
review_callout
special_structure
```

- [ ] **Step 2: Tighten the contract tests for page/object coverage by class**

In `tests/test_ocr_real_paper_audit_contracts.py`, add a per-class minimum:

```python
def test_layout_class_manifest_has_named_representatives() -> None:
    manifest = _load_manifest()
    by_tag = {}
    for paper in manifest["papers"]:
        for tag in paper.get("layout_tags", []):
            by_tag.setdefault(tag, set()).add(paper["paper_key"])

    assert by_tag["preproof_frontmatter"]
    assert by_tag["same_page_ref_body_split"]
    assert by_tag["post_reference_biography"]
    assert by_tag["review_callout"] or by_tag["special_structure"]
```

- [ ] **Step 3: Run Gate 4 tests**

Run: `python -m pytest tests/test_ocr_real_paper_audit_contracts.py -v`

Expected: PASS.

- [ ] **Step 4: Update project truth files to say layout coverage is now a tracked capability surface**

Use these exact narrative shifts:

```text
old: examples of useful gold papers
new: explicit readiness classes with named representatives and contract coverage
```

Write the updated summary into:

- `project/current/ocr-v2-generalization-boundary.md`
- `project/current/ocr-v2-closeout-priority.md`
- `PROJECT-MANAGEMENT.md`

- [ ] **Step 5: Commit Gate 4**

```bash
git add audit/coverage_ledger.json tests/test_ocr_real_paper_audit_contracts.py project/current/ocr-v2-generalization-boundary.md project/current/ocr-v2-closeout-priority.md PROJECT-MANAGEMENT.md
git commit -m "test: formalize OCR layout coverage readiness classes"
```

---

### Task 6: Record Gate 5 Blind-Audit Entry Criteria Without Executing It

**Files:**
- Modify: `project/current/ocr-v2-closeout-priority.md`
- Modify: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Add explicit blind-audit trigger wording to the short queue**

Insert this kind of entry in `project/current/ocr-v2-closeout-priority.md` once Gates 1-4 are complete:

```text
Next stage after readiness: run bounded unseen-paper blind audit with no code changes during the audit window.
```

- [ ] **Step 2: Record the gate-entry checklist in `PROJECT-MANAGEMENT.md`**

Add a short checklist block:

```text
- Gates 1-4 complete
- no active P0 trust risk in known fixtures
- project truth files aligned
- blind audit sample selected before execution
```

- [ ] **Step 3: Commit the Gate 5 handoff wording**

```bash
git add project/current/ocr-v2-closeout-priority.md project/current/ocr-v2-remaining-issues-2026-06-18.md PROJECT-MANAGEMENT.md
git commit -m "docs: record OCR blind-audit entry gate"
```

---

## Verification Checklist Before Claiming "State Healthy"

- [ ] `python -m pytest tests/test_ocr_document.py -v`
- [ ] `python -m pytest tests/test_ocr_figures.py -v`
- [ ] `python -m pytest tests/test_ocr_real_paper_regressions.py -v`
- [ ] `python -m pytest tests/test_ocr_real_paper_audit_contracts.py -v`
- [ ] `python -m pytest tests/cli/ tests/unit/ -v --tb=short`
- [ ] `ruff check paperforge/ tests/`

Only after those pass, and only after project truth files point at Gate 5 as the next step, may OCR-v2 be called "state healthy" on known layout classes.
