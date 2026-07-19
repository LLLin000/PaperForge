# OCR Verified Structural Role Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make OCR-v2 final structural roles non-bypassable by installing a document-level verified role gate before rendering, indexing, health, and structured artifacts consume roles.

**Architecture:** OCR-v2 already uses the document pipeline: `build_structured_blocks(raw_blocks, source_metadata=None, structure_output_dir=None)` -> `normalize_document_structure(blocks) -> (DocumentStructure, normalized_blocks)` -> keyword-only `render_fulltext_markdown(...)` -> `build_ocr_health(...)`. Keep `assign_block_role()` as seed/proposal logic. Install the gate in `normalize_document_structure()` after anchors/families/zones/object evidence are known, then make render and health consume accepted artifacts and gate summaries.

**Tech Stack:** Python 3, dataclasses, existing OCR-v2 modules (`ocr_blocks.py`, `ocr_document.py`, `ocr_render.py`, `ocr_health.py`, `ocr_roles.py`, `ocr_figure_reader.py`), pytest.

---

## File Map

- Create: `paperforge/worker/ocr_structural_gate.py`
  - Verification dataclasses, document-level abstract/reference artifact builders, final role resolver, health counters.
- Modify: `paperforge/worker/ocr_roles.py`
  - Keep seed generation; remove seed passthrough responsibility from final role resolution over time.
- Modify: `paperforge/worker/ocr_blocks.py`
  - Preserve seed fields only; no final high-risk roles here.
- Modify: `paperforge/worker/ocr_document.py`
  - Build `abstract_span`, `reference_zone`, source-backed frontmatter anchors, run gate, prevent post-gate mutation.
- Modify: `paperforge/worker/ocr_render.py`
  - Keep existing keyword-only signature; render from `document_structure` artifacts and accepted reader statuses.
- Modify: `paperforge/worker/ocr_health.py`
  - Merge role-gate summary into primary health without treating successful corrections as errors.
- Add/modify tests: `tests/test_ocr_structural_gate.py`, `tests/test_ocr_blocks.py`, `tests/test_ocr_document.py`, `tests/test_ocr_rendering.py`, `tests/test_ocr_health.py`, `tests/test_ocr_v2_structural_regressions.py`.

## Non-Negotiable Invariants

```python
VERIFY_REQUIRED = {
    "paper_title",
    "authors",
    "abstract_heading",
    "abstract_body",
    "keywords",
    "section_heading",
    "subsection_heading",
    "reference_heading",
    "reference_item",
    "figure_caption",
    "table_caption",
    "table_html",
}
```

- If `seed_role in VERIFY_REQUIRED` and no verifier accepts it, the decision is `HOLD`, not `ACCEPT`.
- HOLD fallback is conservative: rejected structural seeds become `role="unknown_structural"`, keep `role_candidate=<original seed_role>`, keep `text`, set `render_default=False` unless a later non-structural/body verifier accepts the block. Do not silently drop text from artifacts; report held text in health/debug artifacts so it can be inspected.
- `paper_title`, `authors`, and `keywords` must have explicit verifiers; they must not fall through as `non_structural_seed`.
- Successful correction of a bad seed is tracked as warning/info, not an automatic OCR health failure.
- Production must not raise by default for unverified roles; collect offenders, downgrade/fallback, write health, and keep output readable. Test helpers may raise.
- The gate is the final authority for `VERIFY_REQUIRED`. Any later code that wants to assign a high-risk role must either run before the gate, write `role_candidate`, or call the gate again and store a fresh `ACCEPT` decision.
- `render_fulltext_markdown()` tests must call the real keyword-only signature or a new private helper. Do not force the public API into a single positional document argument.
- Reader figure/table rendering must use actual OCR-v2 reader statuses: `EXACT_MATCH`, `SEQUENCE_MATCH`, `GROUPED_APPROXIMATE`, `LEGEND_ONLY`, `ASSET_GROUP_ONLY`, `HOLD`.
- Caption verification must reuse strict/formal legend helpers when available; regex is fallback only.

## Completion Thresholds For Low-Context Executors

These thresholds are intentionally strict. Do not mark the plan complete unless all are true:

- `tests/test_ocr_entrypoints.py` proves the production route is `ocr_blocks -> ocr_document -> ocr_render -> ocr_health`.
- Zero final blocks have `role in VERIFY_REQUIRED` without `role_verification_status == "ACCEPT"`.
- Zero final blocks have `role_source == "non_structural_seed"` while `role in VERIFY_REQUIRED` or `seed_role in VERIFY_REQUIRED`.
- `render_fulltext_markdown()` has no global abstract collection based on `role in ("abstract_heading", "abstract_body")`.
- `render_fulltext_markdown()` does not unconditionally return `non_ref + refs` for tail ordering.
- `_emit_page_objects()` suppresses legacy figure/unresolved outputs when reader figures are present for that page.
- `ocr_health.py` includes `role_gate_summary`; corrected seeds are warning/info, passthrough/final-unverified are degraded.
- Synthetic Yoo/Caffard/adversarial tests go through document-pipeline functions, not `render_page_blocks()`.
- Regression tests import `build_structured_blocks`, `normalize_document_structure`, and keyword-only `render_fulltext_markdown`; they must not import or call `render_page_blocks`, `emit_page_markdown`, or `ocr_emit`.
- Boundary tests include structured abstracts with subheadings/support exclusions and multi-column/reference-tail split cases.
- Focused OCR-v2 suites pass, and any broader-suite failure is documented as pre-existing with exact test names.

## Pre-Execution Patch Notes

Before implementation, apply these execution constraints exactly:

1. Gate must not clobber pre-gate normalized non-`VERIFY_REQUIRED` roles. `resolve_verified_role()` must consider both current `role` and `seed_role`.
2. Gate context inputs must come from explicit adapter helpers. Adapters return empty sets when real evidence is absent and must not fabricate accepted ids from `seed_role` or current `role`.
3. `AbstractSpan` must stop at Introduction-like headings even when `body_start_block_id` is absent.
4. `ReferenceZone` adapter must support dict, dataclass, and namedtuple-like artifacts; missing `reference_end_before_block_id` means skip that filter, not invent a boundary.
5. Reader rendering tests must include at least one renderable block unless renderer is explicitly changed to emit reader figures for empty block lists.
6. Degraded role-gate health must force `report["overall"] = "red"`; it must not leave green unchanged.
7. Static source-code audits are regression tripwires only. Dynamic document-pipeline tests are the authoritative acceptance tests.
8. If current `role` is already a normalized non-`VERIFY_REQUIRED` role, the gate must preserve it even when `seed_role` is `VERIFY_REQUIRED`. Required-seed verification only triggers when current role is unassigned or is itself `VERIFY_REQUIRED`.
9. HOLD fallback must not cause silent content loss. Regression tests must verify that rejected abstract/reference seeds do not enter the wrong section and still appear in a safe body/support/debug path when appropriate.
10. Heading/caption/table accepted-id adapters must be backed by real artifacts. If the artifact does not exist yet, do not fabricate acceptance and do not hard-final/reject object roles in the document gate; keep them as candidates for later verification.
11. Before setting OCR health overall to `red`/`yellow`/`green`, confirm the current health severity vocabulary and use the existing schema.

---

### Task 0: Confirm OCR-v2 Entrypoints and Signatures

**Files:**
- Create: `tests/test_ocr_entrypoints.py`

- [ ] **Step 1: Write the hard entrypoint test**

```python
from __future__ import annotations

from pathlib import Path

import inspect


def test_ocr_v2_entrypoints_and_signatures_are_document_pipeline() -> None:
    from paperforge.worker import ocr_blocks, ocr_document, ocr_health, ocr_render

    assert hasattr(ocr_blocks, "build_structured_blocks")
    assert hasattr(ocr_document, "normalize_document_structure")
    assert hasattr(ocr_render, "render_fulltext_markdown")
    assert hasattr(ocr_health, "build_ocr_health")

    blocks_sig = inspect.signature(ocr_blocks.build_structured_blocks)
    render_sig = inspect.signature(ocr_render.render_fulltext_markdown)

    assert "raw_blocks" in blocks_sig.parameters
    assert render_sig.parameters["structured_blocks"].kind is inspect.Parameter.KEYWORD_ONLY
    assert render_sig.parameters["document_structure"].kind is inspect.Parameter.KEYWORD_ONLY
    assert render_sig.parameters["reader_payload"].kind is inspect.Parameter.KEYWORD_ONLY
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_ocr_entrypoints.py::test_ocr_v2_entrypoints_and_signatures_are_document_pipeline -v`

Expected: PASS on `ocr-v2`. If it fails, stop; do not patch `render_page_blocks()` as a substitute.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ocr_entrypoints.py
git commit -m "test: lock OCR v2 document pipeline entrypoints"
```

### Task 1: Add Gate Model With Safe Default Branch

**Files:**
- Create: `paperforge/worker/ocr_structural_gate.py`
- Test: `tests/test_ocr_structural_gate.py`

- [ ] **Step 1: Write failing tests for required seed HOLD behavior**

```python
from __future__ import annotations


def test_required_seed_without_verifier_holds_not_accepts() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {"block_id": "a1", "seed_role": "authors", "text": "Author One Author Two"}

    decision = resolve_verified_role(block, RoleGateContext())

    assert decision.role == "unknown_structural"
    assert decision.status == "HOLD"
    assert decision.seed_role == "authors"
    assert decision.source == "structural_gate"


def test_non_required_seed_can_accept_as_non_structural() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {"block_id": "b1", "seed_role": "body_paragraph", "text": "Regular body paragraph."}

    decision = resolve_verified_role(block, RoleGateContext())

    assert decision.role == "body_paragraph"
    assert decision.status == "ACCEPT"
    assert decision.source == "non_structural_seed"


def test_hold_preserves_candidate_and_hides_from_render_by_default() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {"block_id": "r1", "seed_role": "reference_item", "text": "[1] Not actually in references."}

    decision = resolve_verified_role(block, RoleGateContext())
    fields = decision.as_block_fields()

    assert fields["role"] == "unknown_structural"
    assert fields["role_candidate"] == "reference_item"
    assert fields["role_verification_status"] == "HOLD"
    assert fields["render_default"] is False


def test_gate_preserves_pre_normalized_non_structural_role() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {"block_id": "i1", "role": "structured_insert", "seed_role": "body_paragraph", "text": "Side note."}

    decision = resolve_verified_role(block, RoleGateContext())

    assert decision.role == "structured_insert"
    assert decision.seed_role == "body_paragraph"
    assert decision.source == "non_structural_normalized_role"


def test_gate_preserves_pre_normalized_safe_role_even_if_seed_is_required() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    block = {
        "block_id": "x",
        "role": "frontmatter_noise",
        "seed_role": "authors",
        "text": "Author-like sidebar",
    }

    decision = resolve_verified_role(block, RoleGateContext())

    assert decision.role == "frontmatter_noise"
    assert decision.source == "non_structural_normalized_role"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_structural_gate.py::test_required_seed_without_verifier_holds_not_accepts tests/test_ocr_structural_gate.py::test_non_required_seed_can_accept_as_non_structural tests/test_ocr_structural_gate.py::test_hold_preserves_candidate_and_hides_from_render_by_default tests/test_ocr_structural_gate.py::test_gate_preserves_pre_normalized_non_structural_role tests/test_ocr_structural_gate.py::test_gate_preserves_pre_normalized_safe_role_even_if_seed_is_required -v`

Expected: FAIL because `ocr_structural_gate.py` does not exist.

- [ ] **Step 3: Implement model and safe default resolver**

```python
from __future__ import annotations

from dataclasses import dataclass, field


VERIFY_REQUIRED = {
    "paper_title",
    "authors",
    "abstract_heading",
    "abstract_body",
    "keywords",
    "section_heading",
    "subsection_heading",
    "reference_heading",
    "reference_item",
    "figure_caption",
    "table_caption",
    "table_html",
}


@dataclass
class VerifiedRoleDecision:
    role: str
    status: str
    source: str
    evidence: list[str] = field(default_factory=list)
    seed_role: str = "unknown_structural"
    role_candidate: str | None = None
    render_default: bool | None = None

    def as_block_fields(self) -> dict:
        fields = {
            "role": self.role,
            "role_verification_status": self.status,
            "role_source": self.source,
            "role_evidence": list(self.evidence),
            "seed_role": self.seed_role,
        }
        if self.role_candidate is not None:
            fields["role_candidate"] = self.role_candidate
        if self.render_default is not None:
            fields["render_default"] = self.render_default
        return fields


@dataclass
class RoleGateContext:
    source_frontmatter_anchor_ids: dict[str, set[str | int]] = field(default_factory=dict)
    abstract_span: dict | None = None
    reference_zone: dict | None = None
    accepted_heading_block_ids: set[str | int] = field(default_factory=set)
    accepted_caption_block_ids: set[str | int] = field(default_factory=set)
    accepted_table_block_ids: set[str | int] = field(default_factory=set)


def _bid(block: dict) -> str | int | None:
    return block.get("block_id")


def accept_role(role: str, seed_role: str, source: str, evidence: list[str]) -> VerifiedRoleDecision:
    return VerifiedRoleDecision(role=role, status="ACCEPT", source=source, evidence=evidence, seed_role=seed_role)


def hold_role(seed_role: str, reason: str) -> VerifiedRoleDecision:
    return VerifiedRoleDecision(
        role="unknown_structural",
        status="HOLD",
        source="structural_gate",
        evidence=[reason],
        seed_role=seed_role,
        role_candidate=seed_role,
        render_default=False,
    )


def resolve_verified_role(block: dict, context: RoleGateContext) -> VerifiedRoleDecision:
    current_role = str(block.get("role") or "unassigned")
    seed_role = str(block.get("seed_role") or current_role or "unknown_structural")
    proposal = seed_role if current_role in {"", "unassigned"} else current_role
    block_id = _bid(block)

    if current_role not in {"", "unassigned"} and current_role not in VERIFY_REQUIRED:
        return accept_role(
            current_role,
            seed_role,
            "non_structural_normalized_role",
            ["pre-gate normalized non-structural role preserved"],
        )

    if proposal == "paper_title" or seed_role == "paper_title":
        if block_id in context.source_frontmatter_anchor_ids.get("title", set()):
            return accept_role("paper_title", seed_role, "source_frontmatter_title_anchor", ["matched source title anchor"])
        return hold_role(seed_role, "paper title seed lacks source-backed title anchor")
    if proposal == "authors" or seed_role == "authors":
        if block_id in context.source_frontmatter_anchor_ids.get("authors", set()):
            return accept_role("authors", seed_role, "source_frontmatter_authors_anchor", ["matched source authors anchor"])
        return hold_role(seed_role, "authors seed lacks source-backed authors anchor")
    if proposal == "keywords" or seed_role == "keywords":
        if block_id in set((context.abstract_span or {}).get("keyword_block_ids", [])):
            return accept_role("keywords", seed_role, "abstract_span_keyword_boundary", ["keywords follow accepted abstract span"])
        return hold_role(seed_role, "keywords seed lacks abstract-span keyword boundary")

    if proposal in VERIFY_REQUIRED or seed_role in VERIFY_REQUIRED:
        return hold_role(seed_role, f"{proposal} requires structural verifier")
    source = "non_structural_seed" if current_role in {"", "unassigned"} else "non_structural_normalized_role"
    return accept_role(proposal, seed_role, source, ["non-structural role accepted"])
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_ocr_structural_gate.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_structural_gate.py tests/test_ocr_structural_gate.py
git commit -m "feat: add OCR structural gate safe defaults"
```

### Task 2: Preserve Seed Roles Without Changing `build_structured_blocks()` API

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_blocks.py`
- Test: `tests/test_ocr_roles.py`

- [ ] **Step 1: Write seed-only tests against the real signature**

```python
from pathlib import Path


def test_build_structured_blocks_preserves_seed_without_final_role(tmp_path: Path) -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "P",
            "page": 1,
            "block_id": "b1",
            "raw_label": "abstract",
            "raw_order": 1,
            "bbox": [90, 100, 900, 150],
            "text": "This label is only a seed.",
            "page_width": 1200,
            "page_height": 1600,
        }
    ]

    rows, _doc = build_structured_blocks(raw_blocks, structure_output_dir=tmp_path)

    assert rows[0]["role"] == "unassigned"
    assert rows[0]["seed_role"]
    assert "seed_confidence" in rows[0]
    assert "seed_evidence" in rows[0]
```

```python
def test_assign_block_role_abstract_heading_seed_is_explicit() -> None:
    from paperforge.worker.ocr_roles import assign_block_role

    block = {"block_label": "paragraph_title", "block_content": "Abstract", "block_bbox": [90, 100, 220, 130]}

    role = assign_block_role(block, page_blocks=[block], page_width=1200, page_height=1600)

    assert role.role == "abstract_heading"
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_ocr_blocks.py::test_build_structured_blocks_preserves_seed_without_final_role tests/test_ocr_roles.py::test_assign_block_role_abstract_heading_seed_is_explicit -v`

Expected: first test likely PASS already; second fails if current seed is `frontmatter_heading`.

- [ ] **Step 3: Fix only seed naming if needed**

In `ocr_roles.py`, literal `Abstract` paragraph title should return:

```python
return RoleAssignment(
    role="abstract_heading",
    confidence=0.95,
    evidence=["abstract heading seed held for structural verification"],
)
```

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_ocr_blocks.py tests/test_ocr_roles.py -v`

Expected: PASS.

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_roles.py tests/test_ocr_blocks.py tests/test_ocr_roles.py
git commit -m "fix: keep OCR structured roles as seeds"
```

### Task 3: Build Document-Level AbstractSpan Including Structured Subheadings

**Files:**
- Modify: `paperforge/worker/ocr_structural_gate.py`
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_structural_gate.py`

- [ ] **Step 1: Write abstract-span test**

```python
def test_document_abstract_span_includes_structured_subheadings_and_excludes_support() -> None:
    from paperforge.worker.ocr_structural_gate import build_document_abstract_span

    blocks = [
        {"block_id": "h", "seed_role": "abstract_heading", "text": "Abstract"},
        {"block_id": "q", "seed_role": "section_heading", "text": "Questions/purposes"},
        {"block_id": "a1", "seed_role": "abstract_body", "text": "First abstract sentence."},
        {"block_id": "authors", "seed_role": "authors", "text": "Author One Author Two"},
        {"block_id": "m", "seed_role": "section_heading", "text": "Methods"},
        {"block_id": "a2", "seed_role": "body_paragraph", "text": "Second abstract sentence."},
        {"block_id": "intro", "seed_role": "section_heading", "text": "Introduction"},
        {"block_id": "bad", "seed_role": "abstract_body", "text": "Mislabeled body."},
    ]
    context = {
        "body_start_block_id": "intro",
        "frontmatter_main_zone_ids": {"h", "q", "a1", "m", "a2"},
        "frontmatter_support_zone_ids": {"authors"},
        "publisher_sidebar_zone_ids": set(),
        "correspondence_zone_ids": set(),
        "affiliation_zone_ids": set(),
    }

    span = build_document_abstract_span(blocks, context)

    assert span["status"] == "ACCEPT"
    assert span["heading_block_id"] == "h"
    assert span["body_block_ids"] == ["q", "a1", "m", "a2"]
    assert span["excluded_support_block_ids"] == ["authors"]
    assert span["stop_reason"] == "body_start"


def test_abstract_span_stops_before_intro_even_when_later_block_has_abstract_seed() -> None:
    from paperforge.worker.ocr_structural_gate import build_document_abstract_span

    blocks = [
        {"block_id": "h", "seed_role": "abstract_heading", "text": "Abstract"},
        {"block_id": "a", "seed_role": "abstract_body", "text": "Actual abstract."},
        {"block_id": "intro", "seed_role": "section_heading", "text": "Introduction"},
        {"block_id": "bad", "seed_role": "abstract_body", "text": "Mislabeled body result."},
    ]
    span = build_document_abstract_span(blocks, {"body_start_block_id": "intro"})

    assert span["body_block_ids"] == ["a"]
    assert span["stop_reason"] == "body_start"


def test_abstract_span_stops_at_intro_like_heading_without_body_start_id() -> None:
    from paperforge.worker.ocr_structural_gate import build_document_abstract_span

    blocks = [
        {"block_id": "h", "seed_role": "abstract_heading", "text": "Abstract"},
        {"block_id": "a", "seed_role": "abstract_body", "text": "Actual abstract."},
        {"block_id": "intro", "seed_role": "section_heading", "text": "1. Introduction"},
        {"block_id": "bad", "seed_role": "abstract_body", "text": "Mislabeled body result."},
    ]
    span = build_document_abstract_span(blocks, {})

    assert span["body_block_ids"] == ["a"]
    assert span["stop_reason"] == "intro_like_heading"
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_ocr_structural_gate.py::test_document_abstract_span_includes_structured_subheadings_and_excludes_support tests/test_ocr_structural_gate.py::test_abstract_span_stops_before_intro_even_when_later_block_has_abstract_seed tests/test_ocr_structural_gate.py::test_abstract_span_stops_at_intro_like_heading_without_body_start_id -v`

Expected: FAIL until builder exists.

- [ ] **Step 3: Implement builder as a pure helper**

Add a helper returning a plain dict so it can be stored on `DocumentStructure` or serialized without custom JSON code:

```python
def build_document_abstract_span(blocks: list[dict], context: dict) -> dict:
    support_ids = set(context.get("frontmatter_support_zone_ids", set()))
    support_ids |= set(context.get("publisher_sidebar_zone_ids", set()))
    support_ids |= set(context.get("correspondence_zone_ids", set()))
    support_ids |= set(context.get("affiliation_zone_ids", set()))
    main_ids = set(context.get("frontmatter_main_zone_ids", set()))
    body_start_id = context.get("body_start_block_id")
    heading_index = next(
        (idx for idx, block in enumerate(blocks) if block.get("seed_role") == "abstract_heading" or str(block.get("text", "")).strip().lower() == "abstract"),
        None,
    )
    if heading_index is None:
        return {"heading_block_id": None, "body_block_ids": [], "excluded_support_block_ids": [], "status": "MISSING", "stop_reason": "missing_heading", "confidence": 0.0}
    body_ids: list = []
    excluded: list = []
    stop_reason = "document_end"
    accepted_inside_abstract = {"abstract_body", "body_paragraph", "section_heading", "subsection_heading"}
    for block in blocks[heading_index + 1 :]:
        block_id = block.get("block_id")
        if block_id == body_start_id:
            stop_reason = "body_start"
            break
        text = str(block.get("text", "") or "").strip().lower()
        intro_text = text.lstrip("0123456789. ")
        if block.get("seed_role") in {"section_heading", "subsection_heading"} and intro_text.startswith("introduction"):
            stop_reason = "intro_like_heading"
            break
        if text.startswith(("keywords", "key words")):
            stop_reason = "keywords"
            break
        if block_id in support_ids:
            excluded.append(block_id)
            continue
        if main_ids and block_id not in main_ids:
            continue
        if block.get("seed_role") in accepted_inside_abstract:
            body_ids.append(block_id)
    return {
        "heading_block_id": blocks[heading_index].get("block_id"),
        "body_block_ids": body_ids,
        "excluded_support_block_ids": excluded,
        "status": "ACCEPT" if body_ids else "HOLD",
        "stop_reason": stop_reason,
        "confidence": 0.9 if body_ids else 0.2,
    }
```

- [ ] **Step 4: Integrate into `normalize_document_structure()`**

After zone/family labels and before gate resolution, call the helper with existing frontmatter/body-start artifacts. If exact artifact names differ, create a small adapter function in `ocr_document.py` that maps current names into the context keys above.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/test_ocr_structural_gate.py tests/test_ocr_document.py -v`

Expected: PASS.

```bash
git add paperforge/worker/ocr_structural_gate.py paperforge/worker/ocr_document.py tests/test_ocr_structural_gate.py tests/test_ocr_document.py
git commit -m "feat: build OCR document abstract spans"
```

### Task 4: Build Verified ReferenceZone Through Adapter

**Files:**
- Modify: `paperforge/worker/ocr_structural_gate.py`
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_structural_gate.py`

- [ ] **Step 1: Write adapter test**

```python
def test_reference_zone_adapter_excludes_tail_after_boundary() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"block_id": "body", "seed_role": "reference_item", "text": "[1] body parameter"},
        {"block_id": "refs", "seed_role": "reference_heading", "text": "References"},
        {"block_id": "r1", "seed_role": "reference_item", "text": "[1] Smith J. 2020."},
        {"block_id": "bio", "seed_role": "section_heading", "text": "Biography"},
        {"block_id": "bad", "seed_role": "reference_item", "text": "Biography text mislabeled."},
    ]
    artifacts = {
        "reference_family_anchor": {"heading_block_id": "refs", "item_block_ids": ["r1", "bad"]},
        "region_bus": {"reference_zone_ids": {"refs", "r1"}},
        "tail_spread": {"reference_end_before_block_id": "bio"},
        "reference_numbering_family": {"accepted_item_ids": {"r1"}},
    }

    zone = build_verified_reference_zone_from_artifacts(blocks, artifacts)

    assert zone["status"] == "ACCEPT"
    assert zone["heading_block_id"] == "refs"
    assert zone["item_block_ids"] == ["r1"]


def test_reference_zone_adapter_keeps_multicolumn_reference_items_inside_region() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"block_id": "refs", "seed_role": "reference_heading", "text": "References", "column": 1},
        {"block_id": "r1", "seed_role": "reference_item", "text": "[1] Left column reference.", "column": 1},
        {"block_id": "r2", "seed_role": "reference_item", "text": "[2] Right column reference.", "column": 2},
        {"block_id": "appendix", "seed_role": "section_heading", "text": "Appendix", "column": 1},
    ]
    artifacts = {
        "reference_family_anchor": {"heading_block_id": "refs", "item_block_ids": ["r1", "r2"]},
        "region_bus": {"reference_zone_ids": {"refs", "r1", "r2"}},
        "tail_spread": {"reference_end_before_block_id": "appendix"},
        "reference_numbering_family": {"accepted_item_ids": {"r1", "r2"}},
    }

    zone = build_verified_reference_zone_from_artifacts(blocks, artifacts)

    assert zone["status"] == "ACCEPT"
    assert zone["item_block_ids"] == ["r1", "r2"]


def test_reference_zone_adapter_accepts_without_tail_end_boundary_when_region_is_present() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"block_id": "refs", "seed_role": "reference_heading", "text": "References"},
        {"block_id": "r1", "seed_role": "reference_item", "text": "[1] Smith J. 2020."},
    ]
    artifacts = {
        "reference_family_anchor": {"heading_block_id": "refs", "item_block_ids": ["r1"]},
        "region_bus": {"reference_zone_ids": {"refs", "r1"}},
        "tail_spread": {},
    }

    zone = build_verified_reference_zone_from_artifacts(blocks, artifacts)

    assert zone["status"] == "ACCEPT"
    assert zone["item_block_ids"] == ["r1"]
```

- [ ] **Step 2: Run test**

Run: `python -m pytest tests/test_ocr_structural_gate.py::test_reference_zone_adapter_excludes_tail_after_boundary tests/test_ocr_structural_gate.py::test_reference_zone_adapter_keeps_multicolumn_reference_items_inside_region tests/test_ocr_structural_gate.py::test_reference_zone_adapter_accepts_without_tail_end_boundary_when_region_is_present -v`

Expected: FAIL until adapter exists.

- [ ] **Step 3: Implement adapter helper**

```python
def build_verified_reference_zone_from_artifacts(blocks: list[dict], artifacts: dict) -> dict:
    def _obj_get(obj, key, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    anchor = artifacts.get("reference_family_anchor") or {}
    region_bus = artifacts.get("region_bus") or {}
    tail_spread = artifacts.get("tail_spread") or {}
    numbering = artifacts.get("reference_numbering_family") or {}
    region_ids = set(_obj_get(region_bus, "reference_zone_ids", set()))
    accepted_numbering_ids = set(_obj_get(numbering, "accepted_item_ids", set()))
    end_before = _obj_get(tail_spread, "reference_end_before_block_id")
    before_tail = set()
    if end_before:
        for block in blocks:
            block_id = block.get("block_id")
            if block_id == end_before:
                break
            before_tail.add(block_id)
    item_ids = []
    for item_id in _obj_get(anchor, "item_block_ids", []):
        if region_ids and item_id not in region_ids:
            continue
        if before_tail and item_id not in before_tail:
            continue
        if accepted_numbering_ids and item_id not in accepted_numbering_ids:
            continue
        item_ids.append(item_id)
    heading_id = _obj_get(anchor, "heading_block_id")
    return {
        "heading_block_id": heading_id,
        "item_block_ids": item_ids,
        "status": "ACCEPT" if heading_id and item_ids else "HOLD",
        "evidence": ["reference zone from anchor, region bus, tail boundary, and numbering continuity"],
    }
```

- [ ] **Step 4: Use the adapter in `normalize_document_structure()`**

Build the artifacts dict from actual local variables already present: `reference_family_anchor`, `region_bus`, `tail_spread`, and the current reference numbering/family signal if present. If no numbering artifact exists yet, omit `reference_numbering_family` rather than inventing fake data.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/test_ocr_structural_gate.py tests/test_ocr_document.py -v`

Expected: PASS.

```bash
git add paperforge/worker/ocr_structural_gate.py paperforge/worker/ocr_document.py tests/test_ocr_structural_gate.py tests/test_ocr_document.py
git commit -m "feat: verify OCR reference zone from document artifacts"
```

### Task 5A: Build Gate Context Adapters

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Add adapter tests that forbid seed-derived acceptance**

```python
def test_gate_context_adapters_do_not_accept_from_seed_roles_only() -> None:
    from paperforge.worker.ocr_document import (
        _build_accepted_caption_block_ids,
        _build_accepted_heading_block_ids,
        _build_accepted_table_block_ids,
        _build_source_frontmatter_anchor_ids,
    )

    blocks = [
        {"block_id": "t", "seed_role": "paper_title", "role": "paper_title"},
        {"block_id": "h", "seed_role": "section_heading", "role": "section_heading"},
        {"block_id": "c", "seed_role": "figure_caption", "role": "figure_caption"},
        {"block_id": "tbl", "seed_role": "table_html", "role": "table_html"},
    ]

    assert _build_source_frontmatter_anchor_ids(None, blocks) == {"title": set(), "authors": set()}
    assert _build_accepted_heading_block_ids(blocks, None) == set()
    assert _build_accepted_caption_block_ids({}, {"reader_figures": []}, blocks) == set()
    assert _build_accepted_table_block_ids({}, blocks) == set()
```

- [ ] **Step 2: Implement adapter helpers**

Add these helpers to `ocr_document.py`. The exact artifact keys may need to be expanded to match current local objects, but the default behavior must remain empty-set, never seed-derived acceptance:

```python
def _doc_get(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _build_source_frontmatter_anchor_ids(doc_structure, blocks: list[dict]) -> dict[str, set]:
    anchors = _doc_get(doc_structure, "source_frontmatter_anchor_ids", {}) or {}
    return {
        "title": set(_doc_get(anchors, "title", set()) or set()),
        "authors": set(_doc_get(anchors, "authors", set()) or set()),
    }


def _build_accepted_heading_block_ids(blocks: list[dict], doc_structure) -> set:
    heading_artifact = _doc_get(doc_structure, "accepted_heading_block_ids", set()) or set()
    return set(heading_artifact)


def _build_accepted_caption_block_ids(figure_inventory: dict | None, reader_payload: dict | None, blocks: list[dict]) -> set:
    accepted = set()
    for figure in (reader_payload or {}).get("reader_figures", []):
        for item in figure.get("consumed_caption_block_ids", []):
            if isinstance(item, dict):
                accepted.add(item.get("block_id"))
            else:
                accepted.add(item)
    accepted.discard(None)
    return accepted


def _build_accepted_table_block_ids(table_inventory: dict | None, blocks: list[dict]) -> set:
    accepted = set()
    for table in (table_inventory or {}).get("matched_tables", []):
        for key in ("block_id", "table_block_id", "html_block_id"):
            if table.get(key) is not None:
                accepted.add(table[key])
    return accepted
```

Document-gate vs object-gate split:

```text
document gate owns: paper_title, authors, abstract_heading, abstract_body, keywords, reference_heading, reference_item, section_heading, subsection_heading
object gate owns: figure_caption, table_caption, table_html
```

If caption/table artifacts are not available yet, do not fabricate acceptance and do not convert object roles into final verified roles or hard HOLD in the document gate. Keep them as `figure_caption_candidate`, `table_caption_candidate`, or `table_html_candidate` for later object-specific verification.

- [ ] **Step 3: Add formal fields to `DocumentStructure`**

Modify the existing `DocumentStructure` dataclass instead of using dynamic attributes:

```python
abstract_span: dict | None = None
reference_zone: dict | None = None
role_gate_summary: dict | None = None
```

This ensures `dataclasses.asdict()`, artifact writing, and health merge can see these fields.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/test_ocr_document.py::test_gate_context_adapters_do_not_accept_from_seed_roles_only -v`

Expected: PASS.

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py
git commit -m "feat: add OCR role gate context adapters"
```

### Task 5: Install Gate in `normalize_document_structure()`

**Files:**
- Modify: `paperforge/worker/ocr_structural_gate.py`
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Write source-backed verifier test**

```python
def test_gate_accepts_frontmatter_only_from_source_anchors() -> None:
    from paperforge.worker.ocr_structural_gate import RoleGateContext, resolve_verified_role

    context = RoleGateContext(source_frontmatter_anchor_ids={"title": {"t"}, "authors": {"a"}})

    title = resolve_verified_role({"block_id": "t", "seed_role": "paper_title", "text": "Canonical Title"}, context)
    authors = resolve_verified_role({"block_id": "a", "seed_role": "authors", "text": "Author One"}, context)
    bad = resolve_verified_role({"block_id": "x", "seed_role": "authors", "text": "Author-like sidebar"}, context)

    assert title.status == "ACCEPT"
    assert title.source == "source_frontmatter_title_anchor"
    assert authors.status == "ACCEPT"
    assert authors.source == "source_frontmatter_authors_anchor"
    assert bad.status == "HOLD"
```

- [ ] **Step 2: Write final-block invariant test**

```python
def test_normalized_required_roles_have_accept_verification() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure
    from paperforge.worker.ocr_structural_gate import VERIFY_REQUIRED

    blocks = [
        {"block_id": "h", "role": "unassigned", "seed_role": "abstract_heading", "text": "Abstract"},
        {"block_id": "a", "role": "unassigned", "seed_role": "abstract_body", "text": "Real abstract."},
        {"block_id": "intro", "role": "unassigned", "seed_role": "section_heading", "text": "Introduction"},
        {"block_id": "bad", "role": "unassigned", "seed_role": "authors", "text": "Author-like sidebar"},
    ]
    _doc, normalized = normalize_document_structure(blocks)

    offenders = [
        block for block in normalized
        if block.get("role") in VERIFY_REQUIRED and block.get("role_verification_status") != "ACCEPT"
    ]
    assert offenders == []
    assert next(block for block in normalized if block["block_id"] == "bad")["role"] != "authors"


def test_rejected_required_seed_can_fallback_to_safe_body_role_without_content_loss() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"block_id": "intro", "role": "section_heading", "seed_role": "section_heading", "text": "Introduction", "page": 1, "render_default": True},
        {"block_id": "bad", "role": "body_paragraph", "seed_role": "abstract_body", "text": "Body mislabeled as abstract.", "page": 1, "render_default": True},
    ]

    _doc, normalized = normalize_document_structure(blocks)
    repaired = next(block for block in normalized if block["block_id"] == "bad")

    assert repaired["role"] == "body_paragraph"
    assert repaired["role_source"] == "structural_gate_fallback"
    assert repaired["render_default"] is True
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_ocr_structural_gate.py::test_gate_accepts_frontmatter_only_from_source_anchors tests/test_ocr_document.py::test_normalized_required_roles_have_accept_verification tests/test_ocr_document.py::test_rejected_required_seed_can_fallback_to_safe_body_role_without_content_loss -v`

Expected: FAIL until the gate is wired and frontmatter verifier exists.

- [ ] **Step 4: Implement missing role verifiers**

Extend `resolve_verified_role()` with explicit branches for:

```python
paper_title -> source_frontmatter_anchor_ids["title"]
authors -> source_frontmatter_anchor_ids["authors"]
keywords -> abstract_span["keyword_block_ids"]
abstract_heading/body -> abstract_span heading/body ids
reference_heading/item -> reference_zone heading/item ids
section/subsection -> accepted_heading_block_ids
figure/table caption + table_html -> accepted_caption_block_ids / accepted_table_block_ids
```

Heading verification must be backed by a real heading-family / numbering / body-adjacency artifact. If `accepted_heading_block_ids` is empty because no such artifact exists yet, add the heading artifact first instead of fabricating acceptance from seed roles.

Object-role execution rule:

```text
If accepted_caption_block_ids / accepted_table_block_ids are empty at document-gate time,
do not final ACCEPT and do not hard HOLD figure/table roles there.
Convert them to *_candidate roles and defer final verification to object-specific inventory/reader stages.
```

Required fallback behavior when a structural verifier rejects a seed:

```text
abstract_body rejected but block is already body-like/body-zone/current_role=body_paragraph -> body_paragraph, status=HOLD, source=structural_gate_fallback
reference_item rejected but block is body-like/body-zone -> body_paragraph, status=HOLD, source=structural_gate_fallback
authors/paper_title rejected -> frontmatter_noise or frontmatter_support, status=HOLD, source=structural_gate_fallback
```

This fallback must preserve readable content. Do not replace a safe normalized role with `unknown_structural` when an existing body/support role can preserve the text without polluting Abstract/References.

End the function with this exact safe default:

```python
if proposal in VERIFY_REQUIRED or seed_role in VERIFY_REQUIRED:
    return hold_role(seed_role, f"{proposal} requires structural verifier")
source = "non_structural_seed" if current_role in {"", "unassigned"} else "non_structural_normalized_role"
return accept_role(proposal, seed_role, source, ["non-structural role accepted"])
```

- [ ] **Step 5: Wire in `normalize_document_structure()`**

In `ocr_document.py`, after `abstract_span` and `reference_zone` exist and before return:

```python
from paperforge.worker.ocr_structural_gate import RoleGateContext, compute_role_gate_health, resolve_verified_role

gate_figure_inventory = locals().get("figure_inventory", {})
gate_reader_payload = locals().get("reader_payload", {})
gate_table_inventory = locals().get("table_inventory", {})
gate_context = RoleGateContext(
    source_frontmatter_anchor_ids=_build_source_frontmatter_anchor_ids(doc_structure, blocks),
    abstract_span=abstract_span,
    reference_zone=reference_zone,
    accepted_heading_block_ids=_build_accepted_heading_block_ids(blocks, doc_structure),
    accepted_caption_block_ids=_build_accepted_caption_block_ids(gate_figure_inventory, gate_reader_payload, blocks),
    accepted_table_block_ids=_build_accepted_table_block_ids(gate_table_inventory, blocks),
)
decisions = []
for block in blocks:
    decision = resolve_verified_role(block, gate_context)
    decisions.append(decision)
    block.update(decision.as_block_fields())
doc_structure.role_gate_summary = compute_role_gate_health(decisions)
```

Before this loop, if object-verification artifacts are not available yet, convert unresolved object seeds to candidates instead of forcing document-gate acceptance/rejection:

```python
if not gate_context.accepted_caption_block_ids:
    for block in blocks:
        if block.get("seed_role") == "figure_caption":
            block["role"] = "figure_caption_candidate"
if not gate_context.accepted_table_block_ids:
    for block in blocks:
        if block.get("seed_role") == "table_caption":
            block["role"] = "table_caption_candidate"
        if block.get("seed_role") == "table_html":
            block["role"] = "table_html_candidate"
```

Use the Task 5A adapter functions. If current local variable names differ, pass the real artifact object into the adapter; do not fabricate accepted ids from seed roles or current roles. If a rejected structural seed can safely fall back to an already normalized body/support role, preserve that role with `source="structural_gate_fallback"` instead of downgrading to `unknown_structural`.

- [ ] **Step 6: Run tests and commit**

Run: `python -m pytest tests/test_ocr_structural_gate.py tests/test_ocr_document.py -v`

Expected: PASS.

```bash
git add paperforge/worker/ocr_structural_gate.py paperforge/worker/ocr_document.py tests/test_ocr_structural_gate.py tests/test_ocr_document.py
git commit -m "feat: install OCR verified role gate"
```

### Task 6: Prevent Post-Gate Mutation Without Production Failure

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Add collector/assert tests**

```python
def test_collect_unverified_required_roles_reports_offenders_without_raising() -> None:
    from paperforge.worker.ocr_document import _collect_unverified_required_roles

    blocks = [{"block_id": "x", "role": "reference_item", "role_verification_status": "HOLD"}]

    assert _collect_unverified_required_roles(blocks) == ["x"]
```

- [ ] **Step 2: Implement collector plus test-only assert helper**

```python
def _collect_unverified_required_roles(blocks: list[dict]) -> list:
    from paperforge.worker.ocr_structural_gate import VERIFY_REQUIRED

    return [
        block.get("block_id")
        for block in blocks
        if block.get("role") in VERIFY_REQUIRED and block.get("role_verification_status") != "ACCEPT"
    ]


def _assert_verified_required_roles(blocks: list[dict]) -> None:
    offenders = _collect_unverified_required_roles(blocks)
    if offenders:
        raise ValueError(f"Unverified structural roles after OCR gate: {offenders[:10]}")
```

- [ ] **Step 3: Production path must degrade, not raise**

Immediately before returning from `normalize_document_structure()`, collect offenders. For each offender, apply the HOLD fallback contract without causing silent content loss. Prefer a safe preserved role when one already exists; only downgrade to `unknown_structural` when there is no safe body/support/debug path:

```python
offenders = set(_collect_unverified_required_roles(blocks))
for block in blocks:
    if block.get("block_id") in offenders:
        block["role_candidate"] = block.get("role") or block.get("seed_role")
        if block.get("role") == "body_paragraph":
            block["role_source"] = "structural_gate_fallback"
            block["render_default"] = True
            continue
        if block.get("role") in {"frontmatter_noise", "frontmatter_support", "structured_insert", "non_body_insert"}:
            block["role_source"] = "structural_gate_fallback"
            continue
        block["role"] = "unknown_structural"
        block["render_default"] = False
doc_structure.role_gate_summary["rendered_unverified_structural_role_count"] = 0
doc_structure.role_gate_summary["downgraded_unverified_structural_role_count"] = len(offenders)
```

- [ ] **Step 4: Move/constrain late role mutators**

Inspect calls after the gate that assign `block["role"]`. Move them before the gate, change them to `role_candidate`, or re-run `resolve_verified_role()` for changed blocks. Do not leave any post-gate direct assignment of `VERIFY_REQUIRED` roles.

- [ ] **Step 4B: Add static audit for post-gate high-risk role mutation**

Append this test to `tests/test_ocr_document.py`:

```python
def test_no_high_risk_role_assignment_after_gate_collector() -> None:
    from pathlib import Path

    source = Path("paperforge/worker/ocr_document.py").read_text(encoding="utf-8")
    marker = "_collect_unverified_required_roles"
    assert marker in source
    tail = source[source.rfind(marker):]
    forbidden = [
        'block["role"] = "abstract_heading"',
        'block["role"] = "abstract_body"',
        'block["role"] = "reference_heading"',
        'block["role"] = "reference_item"',
        'block["role"] = "authors"',
        'block["role"] = "paper_title"',
        'block["role"] = "figure_caption"',
        'block["role"] = "table_caption"',
        'block["role"] = "table_html"',
    ]
    for snippet in forbidden:
        assert snippet not in tail
```

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/test_ocr_document.py::test_collect_unverified_required_roles_reports_offenders_without_raising tests/test_ocr_document.py::test_no_high_risk_role_assignment_after_gate_collector -v`

Run: `python -m pytest tests/test_ocr_document.py -v`

Expected: PASS.

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py
git commit -m "fix: prevent post-gate OCR role mutation"
```

### Task 7: Refactor `render_fulltext_markdown()` With Existing Signature

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Add tests using the real keyword-only signature**

```python
def test_render_fulltext_uses_accepted_abstract_span_only() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {"block_id": "h", "page": 1, "role": "abstract_heading", "role_verification_status": "ACCEPT", "text": "Abstract", "render_default": True},
        {"block_id": "a", "page": 1, "role": "abstract_body", "role_verification_status": "ACCEPT", "text": "Real abstract.", "render_default": True},
        {"block_id": "bad", "page": 1, "role": "abstract_body", "role_verification_status": "HOLD", "text": "Mislabeled body.", "render_default": True},
        {"block_id": "intro", "page": 1, "role": "section_heading", "role_verification_status": "ACCEPT", "text": "Introduction", "render_default": True},
    ]
    document_structure = {"abstract_span": {"heading_block_id": "h", "body_block_ids": ["a"], "status": "ACCEPT"}}

    markdown = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        document_structure=document_structure,
        reader_payload={"reader_figures": []},
    )

    assert "Real abstract." in markdown
    assert markdown.index("Real abstract.") < markdown.index("Introduction")
    assert "Mislabeled body." not in markdown.split("Introduction")[0]
```

- [ ] **Step 2: Add accepted reader status test**

```python
def test_render_fulltext_renders_all_reader_visible_statuses() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    statuses = ["EXACT_MATCH", "SEQUENCE_MATCH", "GROUPED_APPROXIMATE", "LEGEND_ONLY", "ASSET_GROUP_ONLY", "HOLD"]
    reader_figures = [
        {"reader_figure_id": f"rf{i}", "reader_status": status, "figure_number": i, "caption_text": f"Caption {i}", "consumed_caption_block_ids": [{"page": 1, "block_id": f"c{i}"}]}
        for i, status in enumerate(statuses, start=1)
    ]
    structured_blocks = [
        {"block_id": "body", "page": 1, "role": "body_paragraph", "text": "Body.", "render_default": True}
    ]

    markdown = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        document_structure={},
        reader_payload={"reader_figures": reader_figures},
    )

    for status in statuses:
        assert status in markdown
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest tests/test_ocr_rendering.py::test_render_fulltext_uses_accepted_abstract_span_only tests/test_ocr_rendering.py::test_render_fulltext_renders_all_reader_visible_statuses -v`

Expected: FAIL if renderer still globally scans `abstract_body` or filters statuses incorrectly.

- [ ] **Step 4: Implement artifact-based rendering**

In `ocr_render.py`, replace `abstract_blocks = [b for b in structured_blocks if b.get("role") in ...]` with lookup from `document_structure.abstract_span`. Use `_doc_attr` or a small local adapter so both dict and dataclass structures work.

For reader figures, use:

```python
_RENDERABLE_READER_STATUSES = {
    "EXACT_MATCH",
    "SEQUENCE_MATCH",
    "GROUPED_APPROXIMATE",
    "LEGEND_ONLY",
    "ASSET_GROUP_ONLY",
    "HOLD",
}
```

Render reader cards when `reader_status in _RENDERABLE_READER_STATUSES`; do not use lowercase `matched/held/ambiguous`.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/test_ocr_rendering.py -v`

Expected: PASS.

```bash
git add paperforge/worker/ocr_render.py tests/test_ocr_rendering.py
git commit -m "fix: render OCR fulltext from verified artifacts"
```

### Task 8: Merge Role-Gate Health Without Penalizing Corrections

**Files:**
- Modify: `paperforge/worker/ocr_structural_gate.py`
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_health.py`

- [ ] **Step 1: Write health semantics tests**

```python
def test_role_gate_health_corrections_are_not_errors() -> None:
    from paperforge.worker.ocr_structural_gate import VerifiedRoleDecision, compute_role_gate_health

    decisions = [VerifiedRoleDecision(role="unknown_structural", status="HOLD", source="structural_gate", seed_role="abstract_body")]

    summary = compute_role_gate_health(decisions)

    assert summary["status"] == "healthy"
    assert summary["corrected_structural_seed_count"] == 1
    assert summary["final_unverified_structural_role_count"] == 0
    assert summary["seed_role_passthrough_count"] == 0


def test_role_gate_health_degrades_on_passthrough() -> None:
    from paperforge.worker.ocr_structural_gate import VerifiedRoleDecision, compute_role_gate_health

    decisions = [VerifiedRoleDecision(role="authors", status="ACCEPT", source="non_structural_seed", seed_role="authors")]

    summary = compute_role_gate_health(decisions)

    assert summary["status"] == "degraded"
    assert summary["seed_role_passthrough_count"] == 1


def test_ocr_health_role_gate_degraded_forces_overall_red() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=1,
        raw_blocks_count=1,
        structured_blocks=[],
        figure_inventory={},
        table_inventory={},
        doc_structure={"role_gate_summary": {"status": "degraded"}},
        reader_payload={"reader_figures": []},
    )

    assert report["role_gate_summary"]["status"] == "degraded"
    assert report["overall"] == "red"
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_ocr_structural_gate.py::test_role_gate_health_corrections_are_not_errors tests/test_ocr_structural_gate.py::test_role_gate_health_degrades_on_passthrough tests/test_ocr_health.py::test_ocr_health_role_gate_degraded_forces_overall_red -v`

Expected: FAIL until health summary exists.

- [ ] **Step 3: Implement health counters**

```python
def compute_role_gate_health(decisions: list[VerifiedRoleDecision]) -> dict:
    corrected = sum(1 for d in decisions if d.seed_role in VERIFY_REQUIRED and d.status != "ACCEPT")
    final_unverified = sum(1 for d in decisions if d.role in VERIFY_REQUIRED and d.status != "ACCEPT")
    passthrough = sum(1 for d in decisions if d.role in VERIFY_REQUIRED and d.source == "non_structural_seed")
    abstract_outside = sum(1 for d in decisions if d.seed_role == "abstract_body" and d.role != "abstract_body")
    reference_outside = sum(1 for d in decisions if d.seed_role == "reference_item" and d.role != "reference_item")
    status = "degraded" if final_unverified > 0 or passthrough > 0 else "healthy"
    return {
        "status": status,
        "corrected_structural_seed_count": corrected,
        "held_structural_seed_count": corrected,
        "final_unverified_structural_role_count": final_unverified,
        "seed_role_passthrough_count": passthrough,
        "abstract_body_outside_span_count": abstract_outside,
        "reference_item_outside_reference_zone_count": reference_outside,
    }
```

- [ ] **Step 4: Merge into `build_ocr_health()`**

In `ocr_health.py`, read `role_gate_summary` from `doc_structure` using `_doc_attr()`. Add it to `report`. First confirm the existing `overall` severity vocabulary already used by `build_ocr_health()`. If it is the current `red/yellow/green` schema, force degraded gate health to red; if the function already uses a different enum/helper, map into that existing schema instead of inventing a new one. Increase issue severity only when status is `degraded`, not when corrections are merely present:

```python
role_gate_summary = _doc_attr(doc_structure, "role_gate_summary", {}) or {}
report["role_gate_summary"] = role_gate_summary
if role_gate_summary.get("status") == "degraded":
    report["overall"] = "red"
```

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/test_ocr_structural_gate.py tests/test_ocr_health.py -v`

Expected: PASS.

```bash
git add paperforge/worker/ocr_structural_gate.py paperforge/worker/ocr_health.py tests/test_ocr_structural_gate.py tests/test_ocr_health.py
git commit -m "feat: add OCR structural gate health"
```

### Task 9: Main-Pipeline Regression Tests

**Files:**
- Create: `tests/test_ocr_v2_structural_regressions.py`

- [ ] **Step 1: Add adversarial and real-pattern tests**

```python
from __future__ import annotations

from pathlib import Path


def test_body_abstract_seed_does_not_render_as_abstract(tmp_path: Path) -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_document import normalize_document_structure
    from paperforge.worker.ocr_render import render_fulltext_markdown

    raw_blocks = [
        {"paper_id": "P", "page": 1, "block_id": "h", "raw_label": "paragraph_title", "raw_order": 1, "bbox": [90, 100, 220, 130], "text": "Abstract", "page_width": 1200, "page_height": 1600},
        {"paper_id": "P", "page": 1, "block_id": "a", "raw_label": "abstract", "raw_order": 2, "bbox": [90, 140, 900, 190], "text": "Real abstract.", "page_width": 1200, "page_height": 1600},
        {"paper_id": "P", "page": 1, "block_id": "intro", "raw_label": "paragraph_title", "raw_order": 3, "bbox": [90, 260, 300, 290], "text": "Introduction", "page_width": 1200, "page_height": 1600},
        {"paper_id": "P", "page": 1, "block_id": "bad", "raw_label": "abstract", "raw_order": 4, "bbox": [90, 320, 900, 380], "text": "Body mislabeled as abstract.", "page_width": 1200, "page_height": 1600},
    ]
    rows, _ = build_structured_blocks(raw_blocks, structure_output_dir=tmp_path)
    doc, normalized = normalize_document_structure(rows)
    markdown = render_fulltext_markdown(
        structured_blocks=normalized,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=1,
        document_structure=doc,
        reader_payload={"reader_figures": []},
    )

    before_intro, after_intro = markdown.split("Introduction", 1)

    assert markdown.index("Real abstract.") < markdown.index("Introduction")
    assert "Body mislabeled as abstract." not in before_intro
    assert "Body mislabeled as abstract." in after_intro
```

- [ ] **Step 2: Run regression test**

Run: `python -m pytest tests/test_ocr_v2_structural_regressions.py::test_body_abstract_seed_does_not_render_as_abstract -v`

Expected: FAIL until Tasks 3, 5, and 7 are integrated.

- [ ] **Step 3: Add Yoo/Caffard synthetic tests through real functions**

Append these tests to `tests/test_ocr_v2_structural_regressions.py`:

```python
def test_yoo_like_tail_order_through_render_fulltext_markdown() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {"block_id": "refs", "page": 26, "role": "reference_heading", "role_verification_status": "ACCEPT", "text": "References", "render_default": True},
        {"block_id": "r1", "page": 26, "role": "reference_item", "role_verification_status": "ACCEPT", "text": "[1] Yoo H. Real reference.", "render_default": True},
        {"block_id": "bio", "page": 34, "role": "body_paragraph", "text": "Biography", "render_default": True},
        {"block_id": "caps", "page": 35, "role": "section_heading", "role_verification_status": "ACCEPT", "text": "Table and Figure Captions", "render_default": True},
    ]
    document_structure = {
        "abstract_span": {"heading_block_id": None, "body_block_ids": [], "status": "MISSING"},
        "reference_zone": {"heading_block_id": "refs", "item_block_ids": ["r1"], "status": "ACCEPT"},
    }

    markdown = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
        page_count=35,
        document_structure=document_structure,
        reader_payload={"reader_figures": []},
    )

    assert markdown.index("References") < markdown.index("Table and Figure Captions")


def test_caffard_like_abstract_flow_through_normalize_document_structure() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {"block_id": "h", "role": "unassigned", "seed_role": "abstract_heading", "text": "Abstract", "render_default": True},
        {"block_id": "q", "role": "unassigned", "seed_role": "section_heading", "text": "Questions/purposes", "render_default": True},
        {"block_id": "a1", "role": "unassigned", "seed_role": "abstract_body", "text": "First abstract sentence.", "render_default": True},
        {"block_id": "authors", "role": "unassigned", "seed_role": "authors", "text": "Author One Author Two", "render_default": True},
        {"block_id": "m", "role": "unassigned", "seed_role": "section_heading", "text": "Methods", "render_default": True},
        {"block_id": "a2", "role": "unassigned", "seed_role": "abstract_body", "text": "Second abstract sentence.", "render_default": True},
        {"block_id": "intro", "role": "unassigned", "seed_role": "section_heading", "text": "Introduction", "render_default": True},
    ]

    doc, _normalized = normalize_document_structure(blocks)
    span = doc.get("abstract_span") if isinstance(doc, dict) else getattr(doc, "abstract_span", {})

    assert span["body_block_ids"] == ["q", "a1", "m", "a2"]
    assert "authors" in span["excluded_support_block_ids"]


def test_regression_file_does_not_use_legacy_page_renderers() -> None:
    source = Path(__file__).read_text(encoding="utf-8")

    assert "render_page_blocks" not in source
    assert "emit_page_markdown" not in source
    assert "ocr_emit" not in source
```

- [ ] **Step 4: Run and commit**

Run: `python -m pytest tests/test_ocr_v2_structural_regressions.py -v`

Expected: PASS.

```bash
git add tests/test_ocr_v2_structural_regressions.py
git commit -m "test: add OCR v2 structural regressions"
```

### Task 10: Add Hard Contract Audits

Static audits in this task are regression tripwires, not semantic proof. Dynamic document-pipeline tests from Task 9 and the dynamic audit in Step 2 are authoritative. If a static audit conflicts with a passing dynamic test because of a safe refactor, rewrite the static audit as an AST check or a helper-level behavioral test instead of weakening the dynamic test.

**Files:**
- Create: `tests/test_ocr_v2_contract_audit.py`
- Modify only if audits fail: `paperforge/worker/ocr_document.py`
- Modify only if audits fail: `paperforge/worker/ocr_render.py`
- Modify only if audits fail: `paperforge/worker/ocr_health.py`

- [ ] **Step 1: Add static audit tests for forbidden renderer patterns**

Create `tests/test_ocr_v2_contract_audit.py`:

```python
from __future__ import annotations

import inspect


def test_render_fulltext_does_not_globally_scan_abstract_roles() -> None:
    from paperforge.worker import ocr_render

    source = inspect.getsource(ocr_render.render_fulltext_markdown)

    assert 'role") in ("abstract_heading", "abstract_body")' not in source
    assert "role') in ('abstract_heading', 'abstract_body')" not in source
    assert "abstract_span" in source


def test_render_fulltext_does_not_force_references_after_all_non_refs() -> None:
    from paperforge.worker import ocr_render

    source = inspect.getsource(ocr_render.render_fulltext_markdown)

    helper_source = inspect.getsource(ocr_render)

    assert "return non_ref + refs" not in source
    assert "return non_ref + refs" not in helper_source


def test_emit_page_objects_uses_reader_as_primary_gate() -> None:
    from paperforge.worker import ocr_render

    source = inspect.getsource(ocr_render._emit_page_objects)

    assert "has_reader" in source
    assert "if not has_reader" in source or "if has_reader" in source
```

- [ ] **Step 2: Add dynamic audit for role-gate final blocks**

Append to `tests/test_ocr_v2_contract_audit.py`:

```python
def test_required_roles_cannot_finish_without_accept_verification() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure
    from paperforge.worker.ocr_structural_gate import VERIFY_REQUIRED

    blocks = [
        {"block_id": "h", "role": "unassigned", "seed_role": "abstract_heading", "text": "Abstract", "render_default": True},
        {"block_id": "a", "role": "unassigned", "seed_role": "abstract_body", "text": "Real abstract.", "render_default": True},
        {"block_id": "intro", "role": "unassigned", "seed_role": "section_heading", "text": "Introduction", "render_default": True},
        {"block_id": "bad_ref", "role": "unassigned", "seed_role": "reference_item", "text": "[1] body-zone parameter", "render_default": True},
    ]

    _doc, normalized = normalize_document_structure(blocks)

    offenders = [
        block for block in normalized
        if block.get("role") in VERIFY_REQUIRED and block.get("role_verification_status") != "ACCEPT"
    ]
    passthrough = [
        block for block in normalized
        if block.get("role") in VERIFY_REQUIRED and block.get("role_source") == "non_structural_seed"
    ]
    assert offenders == []
    assert passthrough == []
```

- [ ] **Step 3: Run audits to verify they fail before cleanup**

Run: `python -m pytest tests/test_ocr_v2_contract_audit.py -v`

Expected before Tasks 5-8 are fully complete: FAIL on current renderer/global role scan and possibly tail ordering. Expected after fixes: PASS.

- [ ] **Step 4: Fix only production contract violations**

If these tests fail, make the minimal production fix:

```text
abstract scan failure -> consume document_structure.abstract_span
reference reorder failure -> preserve observed semantic tail order or use verified profile artifact
reader primary failure -> skip legacy matched/unresolved figure output when reader_figures exist on page
final role failure -> move mutator before gate, write role_candidate, or re-run gate
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_ocr_v2_contract_audit.py paperforge/worker/ocr_document.py paperforge/worker/ocr_render.py paperforge/worker/ocr_health.py
git commit -m "test: add OCR v2 structural contract audits"
```

### Task 11: Documentation and Final Verification

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/troubleshooting.md` if OCR health output is documented there

- [ ] **Step 1: Document the contract**

Add this section to `docs/ARCHITECTURE.md`:

```markdown
### OCR-v2 Structural Role Gate

OCR-v2 treats OCR labels and `assign_block_role()` output as observations, not semantic truth. `build_structured_blocks()` stores `seed_role`, `seed_confidence`, and `seed_evidence` while leaving final roles unassigned. `normalize_document_structure()` builds document-level anchors, zones, families, `abstract_span`, `reference_zone`, and figure/table reader evidence before assigning final high-risk roles.

Any final role in `VERIFY_REQUIRED` must have `role_verification_status: ACCEPT`, `role_source`, and `role_evidence`. If a high-risk seed is not accepted by a verifier, production downgrades it to a safe non-final role or candidate and reports the correction in `role_gate_summary`; it does not silently pass the seed through. After the gate runs, role mutators may only write candidate fields, move before the gate, or re-run the gate.

`render_fulltext_markdown()` consumes accepted artifacts: Abstract from `abstract_span`, References from `reference_zone`, figures from `reader_figures`, and tables from table reader/table inventory artifacts. It must not rebuild semantic sections by globally scanning bare role labels. OCR health includes `role_gate_summary`; corrected seeds are warning/info, while final unverified roles and seed passthrough degrade health.
```

If `docs/troubleshooting.md` documents OCR health fields, add this entry:

```markdown
#### OCR structural role gate degraded

`role_gate_summary.status: degraded` means at least one high-risk structural role reached output without accepted verification or seed passthrough was detected. Re-run OCR after fixing the role-gate finding. Corrected seeds such as body text mislabeled as abstract are reported as correction counts and do not by themselves mean OCR failed.
```

- [ ] **Step 2: Run focused tests**

Run: `python -m pytest tests/test_ocr_entrypoints.py tests/test_ocr_structural_gate.py tests/test_ocr_blocks.py tests/test_ocr_document.py tests/test_ocr_rendering.py tests/test_ocr_health.py tests/test_ocr_v2_structural_regressions.py tests/test_ocr_v2_contract_audit.py -v`

Expected: PASS.

- [ ] **Step 3: Run broader OCR tests**

Run: `python -m pytest tests/test_ocr.py tests/test_ocr_roles.py tests/test_ocr_attachments.py tests/test_ocr_emission_regressions.py tests/test_ocr_body_spine.py tests/test_ocr_layout_zones.py tests/test_ocr_real_paper_reader_audit.py -v`

Expected: PASS or only pre-existing unrelated failures with exact failing test names recorded.

- [ ] **Step 4: Lint and format touched files**

Run: `ruff check --fix paperforge/worker/ocr_structural_gate.py paperforge/worker/ocr_roles.py paperforge/worker/ocr_blocks.py paperforge/worker/ocr_document.py paperforge/worker/ocr_render.py paperforge/worker/ocr_health.py tests/test_ocr_entrypoints.py tests/test_ocr_structural_gate.py tests/test_ocr_blocks.py tests/test_ocr_document.py tests/test_ocr_rendering.py tests/test_ocr_health.py tests/test_ocr_v2_structural_regressions.py tests/test_ocr_v2_contract_audit.py`

Run: `ruff format paperforge/worker/ocr_structural_gate.py paperforge/worker/ocr_roles.py paperforge/worker/ocr_blocks.py paperforge/worker/ocr_document.py paperforge/worker/ocr_render.py paperforge/worker/ocr_health.py tests/test_ocr_entrypoints.py tests/test_ocr_structural_gate.py tests/test_ocr_blocks.py tests/test_ocr_document.py tests/test_ocr_rendering.py tests/test_ocr_health.py tests/test_ocr_v2_structural_regressions.py tests/test_ocr_v2_contract_audit.py`

Expected: PASS/formatted.

- [ ] **Step 5: Commit**

```bash
git add docs/ARCHITECTURE.md docs/troubleshooting.md
git commit -m "docs: document OCR structural role gate"
```

---

## Acceptance Criteria

- `seed_role in VERIFY_REQUIRED` cannot fall through as `non_structural_seed`.
- `paper_title`, `authors`, and `keywords` have explicit verifiers or remain HOLD/candidate.
- `normalize_document_structure()` writes verification fields for every final high-risk role.
- Post-gate mutators cannot create unverified high-risk roles; production downgrades and reports instead of throwing by default.
- `render_fulltext_markdown()` keeps its keyword-only API and consumes accepted artifacts.
- Reader figure/table rendering uses OCR-v2 uppercase reader statuses.
- Primary OCR health distinguishes corrected structural seeds from true errors.
- Yoo/Caffard/adversarial tests exercise the document pipeline, not legacy page rendering.

## Self-Review

- Spec coverage: Covers source-backed frontmatter roles, safe default branch, health semantics, real renderer signature, reader statuses, production non-raise fallback, structured abstract subheadings, and reference-zone adapter.
- Red-flag scan: No deferred implementation markers or unexpanded test instructions remain.
- Type consistency: Uses `VerifiedRoleDecision`, `RoleGateContext`, `build_document_abstract_span()`, `build_verified_reference_zone_from_artifacts()`, `resolve_verified_role()`, and `compute_role_gate_health()` consistently.
