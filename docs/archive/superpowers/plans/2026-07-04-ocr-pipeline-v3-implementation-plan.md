# OCR Pipeline V3 Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the current monolithic normalize path into `pre_match_normalize(...)` and `post_match_normalize(...)`, keep the public `block["role"]` contract intact, and gate the entire v3 path behind `OCR_PIPELINE_V3` so legacy callers stay untouched by default.

**Architecture:** Keep the legacy path as the default. Add a seed-only mode to `build_structured_blocks(...)`, then let the v3 path run pre-match normalization, figure/table matching, and post-match normalization in `ocr.py`. To keep blast radius low, the first v3 implementation uses shadow calls into `normalize_document_structure(...)` to compute candidate/final roles while preserving the new sequencing and matching contract.

**Tech Stack:** Python 3, existing PaperForge OCR workers, `DocumentStructure`, `ocr_tail_settlement.py`, pytest, environment toggle via `OCR_PIPELINE_V3`

## Global Constraints

- Workstream C only. Workstreams A and B are already landed on this branch and must stay green.
- `block["role"]` remains the final public role field.
- Under v3, matching code must not require final `role`; it must work from `seed_role`, `role_candidate`, `raw_label`, `bbox`, `zone`, and ownership evidence when present.
- The entire v3 path is behind `OCR_PIPELINE_V3`; legacy behavior is the default and must remain byte-for-byte compatible for existing callers.
- Do not rewrite figure/table pairing logic in this workstream. Change only the inputs those builders accept.
- Do not change object writeback sequencing from Workstream A. `apply_object_writebacks(...)` remains after figure/table inventory exists.
- Reuse the existing `settle_tail_and_backmatter(...)` module from Workstream B. Do not re-inline tail settlement.
- If v3 parity is not green, stop at the gate. Do not force-switch callers to v3.

---

## File Structure

- **Create:** `paperforge/worker/ocr_pre_match_normalize.py`
  - v3 candidate-only normalization. Preserves `role = seed_role`, writes `role_candidate` from a shadow normalize pass.
- **Create:** `paperforge/worker/ocr_post_match_normalize.py`
  - v3 final role commit after figure/table inventories exist. Reuses tail settlement from Workstream B.
- **Modify:** `paperforge/worker/ocr_blocks.py`
  - add `normalize_mode="seed_only" | "legacy"` to `build_structured_blocks(...)`
  - return rows/doc before legacy normalize when v3 wants seed-only rows
- **Modify:** `paperforge/worker/ocr.py`
  - add `_ocr_pipeline_v3_enabled()`
  - branch between legacy path and v3 pre-match → inventory build → post-match path
- **Modify:** `paperforge/worker/ocr_figures.py`
  - add a helper that resolves match-time role from `role_candidate` / `role` / `seed_role`
  - replace role checks used by figure matching with the helper
- **Modify:** `paperforge/worker/ocr_tables.py`
  - same candidate-role helper approach for table matching
- **Create:** `tests/test_ocr_pipeline_v3.py`
  - toggle tests, pre-match tests, post-match tests, and one figure/table contract test each

---

### Task 1: C0 — Add the v3 toggle and seed-only build path

**Files:**
- Create: `paperforge/worker/ocr_pre_match_normalize.py`
- Create: `paperforge/worker/ocr_post_match_normalize.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr.py`
- Create: `tests/test_ocr_pipeline_v3.py`

**Interfaces:**
- Consumes:
  - current seed-row construction in `build_structured_blocks(...)`
  - current top-level OCR flow in `ocr.py`
- Produces:
  - `_ocr_pipeline_v3_enabled() -> bool`
  - `build_structured_blocks(..., normalize_mode: str = "legacy")`
  - `pre_match_normalize(rows: list[dict], *, source_frontmatter_anchors: dict | None = None, document_structure: DocumentStructure | None = None) -> tuple[list[dict], DocumentStructure]`
  - `post_match_normalize(rows: list[dict], figure_inventory: dict, table_inventory: dict, *, document_structure: DocumentStructure, source_frontmatter_anchors: dict | None = None) -> tuple[list[dict], DocumentStructure]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ocr_pipeline_v3.py
from __future__ import annotations


def test_ocr_pipeline_v3_enabled_defaults_false(monkeypatch) -> None:
    from paperforge.worker.ocr import _ocr_pipeline_v3_enabled

    monkeypatch.delenv("OCR_PIPELINE_V3", raising=False)

    assert _ocr_pipeline_v3_enabled() is False


def test_ocr_pipeline_v3_enabled_truthy(monkeypatch) -> None:
    from paperforge.worker.ocr import _ocr_pipeline_v3_enabled

    monkeypatch.setenv("OCR_PIPELINE_V3", "1")

    assert _ocr_pipeline_v3_enabled() is True


def test_build_structured_blocks_seed_only_skips_legacy_normalize(monkeypatch) -> None:
    import paperforge.worker.ocr_document as ocr_document
    from paperforge.worker.ocr_blocks import build_structured_blocks

    def boom(*args, **kwargs):
        raise AssertionError("legacy normalize should not run in seed_only mode")

    monkeypatch.setattr(ocr_document, "normalize_document_structure", boom)

    raw_blocks = [
        {
            "block_id": "r1",
            "page": 1,
            "raw_label": "text",
            "text": "Minimal body text.",
            "bbox": [100, 100, 420, 140],
        }
    ]

    rows, doc = build_structured_blocks(raw_blocks, normalize_mode="seed_only")

    assert len(rows) == 1
    assert rows[0]["role"] == rows[0]["seed_role"]
    assert doc is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
`python -m pytest tests/test_ocr_pipeline_v3.py::test_ocr_pipeline_v3_enabled_defaults_false tests/test_ocr_pipeline_v3.py::test_ocr_pipeline_v3_enabled_truthy tests/test_ocr_pipeline_v3.py::test_build_structured_blocks_seed_only_skips_legacy_normalize -v --tb=short`

Expected: FAIL because `_ocr_pipeline_v3_enabled`, `normalize_mode`, and the new modules do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# paperforge/worker/ocr.py
import os


def _ocr_pipeline_v3_enabled() -> bool:
    return os.environ.get("OCR_PIPELINE_V3", "").strip().lower() in {"1", "true", "yes", "on"}
```

```python
# paperforge/worker/ocr_blocks.py
def build_structured_blocks(
    raw_blocks: list[dict],
    source_metadata: dict | None = None,
    structure_output_dir: str | Path | None = None,
    normalize_mode: str = "legacy",
) -> tuple[list[dict], DocumentStructure]:
    ...
    body_family_anchor = discover_body_family_anchor(rows, page_count=total_pages)
    doc_structure = DocumentStructure(body_family_anchor=body_family_anchor)
    ...
    if normalize_mode == "seed_only":
        return rows, doc_structure
    ...
    doc_structure, rows = normalize_document_structure(rows, source_frontmatter_anchors=_sfm_anchors)
    ...
    settle_tail_and_backmatter(structured_blocks=rows, document_structure=doc_structure)
    return rows, doc_structure
```

```python
# paperforge/worker/ocr_pre_match_normalize.py
from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure


def pre_match_normalize(
    rows: list[dict],
    *,
    source_frontmatter_anchors: dict | None = None,
    document_structure: DocumentStructure | None = None,
) -> tuple[list[dict], DocumentStructure]:
    return rows, document_structure or DocumentStructure()
```

```python
# paperforge/worker/ocr_post_match_normalize.py
from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure


def post_match_normalize(
    rows: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
    *,
    document_structure: DocumentStructure,
    source_frontmatter_anchors: dict | None = None,
) -> tuple[list[dict], DocumentStructure]:
    return rows, document_structure
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
`python -m pytest tests/test_ocr_pipeline_v3.py::test_ocr_pipeline_v3_enabled_defaults_false tests/test_ocr_pipeline_v3.py::test_ocr_pipeline_v3_enabled_truthy tests/test_ocr_pipeline_v3.py::test_build_structured_blocks_seed_only_skips_legacy_normalize -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr.py paperforge/worker/ocr_blocks.py paperforge/worker/ocr_pre_match_normalize.py paperforge/worker/ocr_post_match_normalize.py tests/test_ocr_pipeline_v3.py
git commit -m "feat: add OCR pipeline v3 toggle and seed-only path"
```

---

### Task 2: C1 — Implement pre-match normalize and the matching contract

**Files:**
- Modify: `paperforge/worker/ocr_pre_match_normalize.py`
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `tests/test_ocr_pipeline_v3.py`

**Interfaces:**
- Consumes:
  - seed-only rows from `build_structured_blocks(..., normalize_mode="seed_only")`
  - legacy `normalize_document_structure(...)` on a shadow copy
- Produces:
  - `role_candidate` filled from shadow normalize results
  - figure/table builders that accept `role_candidate` instead of requiring final `role`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ocr_pipeline_v3.py
from __future__ import annotations


def test_pre_match_normalize_preserves_public_role_and_sets_role_candidate(monkeypatch) -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    import paperforge.worker.ocr_pre_match_normalize as pre

    def fake_normalize(rows, source_frontmatter_anchors=None, pdf_path=None):
        shadow_rows = [dict(r) for r in rows]
        shadow_rows[0]["role"] = "figure_caption_candidate"
        return DocumentStructure(), shadow_rows

    monkeypatch.setattr(pre, "normalize_document_structure", fake_normalize)

    rows = [
        {
            "block_id": "c1",
            "page": 1,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": "Figure 1. Example caption text.",
            "bbox": [100, 100, 520, 160],
        }
    ]

    out_rows, doc = pre.pre_match_normalize(rows, source_frontmatter_anchors=None, document_structure=DocumentStructure())

    assert out_rows[0]["role"] == "body_paragraph"
    assert out_rows[0]["role_candidate"] == "figure_caption_candidate"
    assert doc is not None


def test_figure_inventory_accepts_role_candidate_caption_blocks() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory_vnext

    blocks = [
        {
            "block_id": "cap1",
            "page": 2,
            "role": "body_paragraph",
            "role_candidate": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number"},
            "text": "Figure 1. Example caption",
            "bbox": [100, 100, 420, 140],
        },
        {
            "block_id": "asset1",
            "page": 2,
            "role": "media_asset",
            "role_candidate": "media_asset",
            "seed_role": "media_asset",
            "raw_label": "image",
            "zone": "display_zone",
            "text": "",
            "bbox": [100, 160, 420, 380],
        },
    ]

    inv = build_figure_inventory_vnext(blocks)

    assert inv["matched_figures"] or inv["figure_legends"]


def test_table_inventory_accepts_role_candidate_caption_blocks() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    blocks = [
        {
            "block_id": "cap1",
            "page": 3,
            "role": "body_paragraph",
            "role_candidate": "table_caption_candidate",
            "seed_role": "table_caption",
            "raw_label": "figure_title",
            "zone": "display_zone",
            "style_family": "table_caption_like",
            "marker_signature": {"type": "table_number"},
            "text": "Table 1. Outcomes",
            "bbox": [100, 100, 420, 140],
        },
        {
            "block_id": "asset1",
            "page": 3,
            "role": "media_asset",
            "role_candidate": "media_asset",
            "seed_role": "media_asset",
            "raw_label": "table",
            "zone": "display_zone",
            "text": "",
            "bbox": [100, 160, 420, 380],
        },
    ]

    inv = build_table_inventory_vnext(blocks)

    assert inv["tables"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
`python -m pytest tests/test_ocr_pipeline_v3.py::test_pre_match_normalize_preserves_public_role_and_sets_role_candidate tests/test_ocr_pipeline_v3.py::test_figure_inventory_accepts_role_candidate_caption_blocks tests/test_ocr_pipeline_v3.py::test_table_inventory_accepts_role_candidate_caption_blocks -v --tb=short`

Expected: FAIL because `pre_match_normalize(...)` does not populate `role_candidate`, and figure/table builders still key too heavily off final `role`.

- [ ] **Step 3: Write minimal implementation**

```python
# paperforge/worker/ocr_pre_match_normalize.py
from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure, normalize_document_structure


def pre_match_normalize(
    rows: list[dict],
    *,
    source_frontmatter_anchors: dict | None = None,
    document_structure: DocumentStructure | None = None,
) -> tuple[list[dict], DocumentStructure]:
    live_rows = [dict(row) for row in rows]
    shadow_doc, shadow_rows = normalize_document_structure(
        [dict(row) for row in rows],
        source_frontmatter_anchors=source_frontmatter_anchors,
    )
    for live, shadow in zip(live_rows, shadow_rows):
        live["role_candidate"] = shadow.get("role") or shadow.get("seed_role") or live.get("seed_role")
        live["zone"] = shadow.get("zone", live.get("zone"))
        live["style_family"] = shadow.get("style_family", live.get("style_family"))
        live["marker_signature"] = shadow.get("marker_signature", live.get("marker_signature"))
        live["render_default"] = live.get("render_default", True)
        live["role"] = live.get("seed_role") or live.get("role")
    return live_rows, document_structure or shadow_doc
```

```python
# paperforge/worker/ocr_figures.py

def _match_role(block: dict) -> str:
    return str(block.get("role_candidate") or block.get("role") or block.get("seed_role") or "")
```

```python
# paperforge/worker/ocr_figures.py
# replace match-time role reads like:
role = str(block.get("role") or "")
# with:
role = _match_role(block)
```

Replace that pattern anywhere figure matching decides whether a block is a caption candidate, figure asset, or excluded demoted body paragraph. Do not change post-writeback render-only checks.

```python
# paperforge/worker/ocr_tables.py

def _match_role(block: dict) -> str:
    return str(block.get("role_candidate") or block.get("role") or block.get("seed_role") or "")
```

```python
# paperforge/worker/ocr_tables.py
# replace match-time role reads like:
role = str(block.get("role", "") or "")
# with:
role = _match_role(block)
```

Replace only the role reads that affect caption/asset selection for matching. Leave write-back and render-only code alone.

- [ ] **Step 4: Run tests to verify they pass**

Run:
`python -m pytest tests/test_ocr_pipeline_v3.py::test_pre_match_normalize_preserves_public_role_and_sets_role_candidate tests/test_ocr_pipeline_v3.py::test_figure_inventory_accepts_role_candidate_caption_blocks tests/test_ocr_pipeline_v3.py::test_table_inventory_accepts_role_candidate_caption_blocks -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_pre_match_normalize.py paperforge/worker/ocr_figures.py paperforge/worker/ocr_tables.py tests/test_ocr_pipeline_v3.py
git commit -m "feat: add pre-match normalize and candidate-role matching"
```

---

### Task 3: C2 — Implement post-match normalize and top-level v3 orchestration

**Files:**
- Modify: `paperforge/worker/ocr_post_match_normalize.py`
- Modify: `paperforge/worker/ocr.py`
- Modify: `tests/test_ocr_pipeline_v3.py`

**Interfaces:**
- Consumes:
  - pre-match rows with `role_candidate`
  - `figure_inventory` and `table_inventory`
  - existing `DocumentStructure`
- Produces:
  - final public `role`
  - reuse of `settle_tail_and_backmatter(...)` after post-match commit
  - v3 sequencing in `ocr.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ocr_pipeline_v3.py
from __future__ import annotations


def test_post_match_normalize_commits_shadow_role_back_to_public_role(monkeypatch) -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    import paperforge.worker.ocr_post_match_normalize as post

    def fake_normalize(rows, source_frontmatter_anchors=None, pdf_path=None):
        shadow_rows = [dict(r) for r in rows]
        shadow_rows[0]["role"] = "figure_caption"
        shadow_rows[0]["role_source"] = "shadow_post_match"
        return DocumentStructure(), shadow_rows

    monkeypatch.setattr(post, "normalize_document_structure", fake_normalize)

    rows = [
        {
            "block_id": "c1",
            "page": 1,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "role_candidate": "figure_caption_candidate",
            "text": "Figure 1. Example caption text.",
            "bbox": [100, 100, 520, 160],
        }
    ]

    out_rows, doc = post.post_match_normalize(
        rows,
        {"matched_figures": []},
        {"tables": []},
        document_structure=DocumentStructure(),
        source_frontmatter_anchors=None,
    )

    assert out_rows[0]["role"] == "figure_caption"
    assert out_rows[0]["role_candidate"] == "figure_caption_candidate"
    assert out_rows[0]["role_source"] == "shadow_post_match"
    assert doc is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run:
`python -m pytest tests/test_ocr_pipeline_v3.py::test_post_match_normalize_commits_shadow_role_back_to_public_role -v --tb=short`

Expected: FAIL because `post_match_normalize(...)` is still a no-op.

- [ ] **Step 3: Write minimal implementation**

```python
# paperforge/worker/ocr_post_match_normalize.py
from __future__ import annotations

from paperforge.worker.ocr_document import DocumentStructure, normalize_document_structure
from paperforge.worker.ocr_tail_settlement import settle_tail_and_backmatter


def post_match_normalize(
    rows: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
    *,
    document_structure: DocumentStructure,
    source_frontmatter_anchors: dict | None = None,
) -> tuple[list[dict], DocumentStructure]:
    live_rows = [dict(row) for row in rows]
    shadow_doc, shadow_rows = normalize_document_structure(
        [dict(row) for row in rows],
        source_frontmatter_anchors=source_frontmatter_anchors,
    )
    for live, shadow in zip(live_rows, shadow_rows):
        live["role"] = shadow.get("role", live.get("role"))
        live["role_source"] = shadow.get("role_source", live.get("role_source"))
        live["role_confidence"] = shadow.get("role_confidence", live.get("role_confidence"))
        live["role_candidate"] = live.get("role_candidate") or shadow.get("role")
        live["render_default"] = shadow.get("render_default", live.get("render_default"))
        live["index_default"] = shadow.get("index_default", live.get("index_default"))
    settle_tail_and_backmatter(structured_blocks=live_rows, document_structure=shadow_doc)
    return live_rows, shadow_doc
```

```python
# paperforge/worker/ocr.py
from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize
from paperforge.worker.ocr_post_match_normalize import post_match_normalize

...
normalize_mode = "seed_only" if _ocr_pipeline_v3_enabled() else "legacy"
structured, doc_structure = build_structured_blocks(
    all_raw_blocks,
    source_metadata=source_meta,
    structure_output_dir=artifacts.blocks_structured.parent,
    normalize_mode=normalize_mode,
)
if _ocr_pipeline_v3_enabled():
    structured, doc_structure = pre_match_normalize(
        structured,
        source_frontmatter_anchors=getattr(doc_structure, "source_frontmatter_anchors", None),
        document_structure=doc_structure,
    )
write_structured_blocks_jsonl(artifacts.blocks_structured, structured)
...
figure_inventory = build_figure_inventory(structured)
...
table_inventory = build_table_inventory(structured)
if _ocr_pipeline_v3_enabled():
    structured, doc_structure = post_match_normalize(
        structured,
        figure_inventory,
        table_inventory,
        document_structure=doc_structure,
        source_frontmatter_anchors=getattr(doc_structure, "source_frontmatter_anchors", None),
    )
# object writeback stays here
apply_object_writebacks(
    structured_blocks=structured,
    figure_inventory=figure_inventory,
    table_inventory=table_inventory,
)
```

The top-level order under v3 is now:
1. seed-only block build
2. pre-match normalize
3. figure/table inventory build
4. post-match normalize
5. object writeback

The legacy path stays unchanged.

- [ ] **Step 4: Run tests to verify they pass**

Run:
`python -m pytest tests/test_ocr_pipeline_v3.py::test_post_match_normalize_commits_shadow_role_back_to_public_role -v --tb=short`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr.py paperforge/worker/ocr_post_match_normalize.py tests/test_ocr_pipeline_v3.py
git commit -m "feat: wire OCR pipeline v3 pre-match and post-match flow"
```

---

### Task 4: C3 — Parity gate for v3

**Files:**
- Modify: `tests/test_ocr_pipeline_v3.py`
- Reuse: `tests/test_ocr_tail_settlement.py`
- Reuse: `tests/test_ocr_object_writeback.py`
- Reuse: `tests/test_ocr_rendering.py`
- Reuse: `tests/test_appendix_figure_numbering.py`

**Interfaces:**
- Consumes:
  - C0/C1/C2 v3 path
  - A/B regressions
- Produces:
  - go / no-go for turning on v3 in any real caller

- [ ] **Step 1: Add one v3 integration smoke test**

```python
# tests/test_ocr_pipeline_v3.py
from __future__ import annotations


def test_build_structured_blocks_legacy_default_still_matches_seed_contract() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "block_id": "r1",
            "page": 1,
            "raw_label": "text",
            "text": "Minimal body text.",
            "bbox": [100, 100, 420, 140],
        }
    ]

    rows, _ = build_structured_blocks(raw_blocks)

    assert rows[0]["role"]
    assert rows[0]["seed_role"]
```

- [ ] **Step 2: Run the v3-focused suite**

Run:
`python -m pytest tests/test_ocr_pipeline_v3.py tests/test_ocr_tail_settlement.py -q --tb=line`

Expected: PASS

- [ ] **Step 3: Run cross-workstream guard suite**

Run:
`python -m pytest tests/test_ocr_object_writeback.py tests/test_ocr_rendering.py::test_body_renderer_skips_consumed_object_owned_blocks tests/test_appendix_figure_numbering.py -q --tb=line`

Expected: PASS

- [ ] **Step 4: Run tail/backmatter parity suite**

Run:
`python -m pytest tests/test_ocr_rendering.py::test_tail_zone_noise_band_guard tests/test_ocr_rendering.py::test_tail_zone_supplementary_material_not_noise tests/test_ocr_rendering.py::test_tail_candidate_overreach_does_not_absorb_late_body tests/test_ocr_rendering.py::test_cross_page_funding_continuation_preserves_order tests/test_ocr_rendering.py::test_mixed_tail_page_keeps_late_body_out_of_funding_and_attaches_real_funding tests/test_ocr_rendering.py::test_backmatter_boundary_normalizes_child_sections_before_references -q --tb=line`

Expected: PASS

- [ ] **Step 5: Stop rule**

Decision rule:
- If all C tests and all A/B regressions are green, Workstream C is complete but still optional behind `OCR_PIPELINE_V3`.
- Do **not** flip the default to v3 in this workstream.
- Any future default-on change requires a separate micro-plan after corpus-diff review.

- [ ] **Step 6: Commit**

```bash
git add tests/test_ocr_pipeline_v3.py
git commit -m "test: add OCR pipeline v3 parity gate"
```

---

## Self-Review

- **Spec coverage:** This plan covers Workstream C from `2026-07-04-ocr-pipeline-deepening-design.md`: pre-match module, post-match module, role-field contract, matching contract, and behind-toggle migration rule.
- **Grounding against current code:** The plan matches the current placement of figure/table inventory building in `ocr.py` and the current seed-row construction in `ocr_blocks.py`. That is why the v3 split is staged across both files rather than only inside `normalize_document_structure(...)`.
- **Placeholder scan:** No `TBD` / `TODO` implementation placeholders remain.
- **Scope control:** The plan keeps v3 behind `OCR_PIPELINE_V3` and explicitly does not flip the default.
- **Type consistency:** `role` stays final public role; `role_candidate` is candidate-only; `seed_role` remains the early guess.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-04-ocr-pipeline-v3-implementation-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
