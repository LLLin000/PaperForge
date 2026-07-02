# Layout Robustness Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace naive global header/footer banding with a robust global estimator, make usable-content gating role-aware, and separately fix two-column continuation reference ownership without conflating it with banding.

**Architecture:** Create a dedicated `ocr_banding.py` module for candidate collection, robust global band estimation, runtime band selection, and structured usable-content decisions. Keep `ocr_document.py` and `ocr_render.py` as consumers: first add audit-only robust diagnostics, then enable robust runtime band selection, then normalize role-aware gating, and only after that fix two-column continuation references with an explicit column-aware ownership helper.

**Tech Stack:** Python 3.x, existing PaperForge OCR worker modules, pytest, no new runtime dependencies.

## Global Constraints

- Preserve / enforce the validated local patch: `reference_item` and `reference_body` must bypass generic header/footer usable-content gating during tail reference routing.
- The primary model stays **global**, not page-local.
- A single outlier candidate must not define the paper-level header/footer band.
- Strong structural roles must not be demoted by generic band heuristics.
- Two-column continuation reference ownership is a separate upper-layer problem; do not hide it inside band estimation.
- No new third-party dependencies.
- Keep changes auditable: every exclusion/bypass decision must leave structured evidence.

## Prerequisite

This plan assumes the reference-zone ordering fix work is already present in the branch or will be landed first. Specifically, these behaviors are treated as external prerequisites for paper-level regression assertions in Task 6:

- table consumed-key page collision fix
- `skip_section_grouping` tail non-ref placement fix
- page-continuation-marker false-reference fix
- same-page refs-after-heading guard

If those are absent, remove the corresponding paper-level assertions from Task 6 or land that earlier plan first.

---

## File Map

- **Create:** `paperforge/worker/ocr_banding.py`
  - Focused module for `LayoutBandEstimate`, `UsableContentDecision`, candidate collection, exclusion logic, aggregation, runtime band selection, and the decision API.
- **Modify:** `paperforge/worker/ocr_document.py`
  - Replace direct noise-band estimation with the new module, expose audit-only robust diagnostics, then consume robust runtime band selection during body-promotion logic.
- **Modify:** `paperforge/worker/ocr_render.py`
  - Consume structured band decisions, preserve ref bypass, enforce ownership-before-band for `backmatter_body`, and add column-aware continuation helper for reference attachment.
- **Modify:** `tests/test_ocr_document.py`
  - Add estimator, runtime band selection, and decision API tests.
- **Modify:** `tests/test_ocr_render.py`
  - Add render routing and two-column continuation regression tests.

---

### Task 1: Build the robust banding core module

**Files:**
- Create: `paperforge/worker/ocr_banding.py`
- Modify: `tests/test_ocr_document.py`

**Interfaces:**
- Consumes: OCR block dicts with `bbox`, `block_bbox`, `page`, `page_width`, `page_height`, `role`, `raw_label`, `text`, `block_content`, `evidence`
- Produces:
  - `LayoutBandEstimate`
  - `UsableContentDecision`
  - `collect_layout_band_candidates(blocks: list[dict]) -> list[dict]`
  - `estimate_layout_bands(blocks: list[dict]) -> LayoutBandEstimate`
  - `choose_runtime_bands(robust_estimate: LayoutBandEstimate, legacy_header_band: float | None, legacy_footer_band: float | None, *, max_page_height: float) -> tuple[float | None, float | None, str]`
  - `decide_usable_content(block: dict, band_estimate: LayoutBandEstimate | None, *, context: str) -> UsableContentDecision`

- [ ] **Step 1: Write the failing estimator tests**

```python
from __future__ import annotations


def test_tall_margin_band_noise_excluded_from_header_band() -> None:
    from paperforge.worker.ocr_banding import estimate_layout_bands

    blocks = [
        {
            "page": 1,
            "page_width": 1200,
            "page_height": 1600,
            "role": "noise",
            "raw_label": "header",
            "text": "Journal Name",
            "bbox": [100, 70, 420, 102],
            "evidence": [],
        },
        {
            "page": 3,
            "page_width": 1200,
            "page_height": 1600,
            "role": "noise",
            "raw_label": "header",
            "text": "Journal Name",
            "bbox": [100, 72, 420, 104],
            "evidence": [],
        },
        {
            "page": 2,
            "page_width": 1200,
            "page_height": 1600,
            "role": "noise",
            "raw_label": "header",
            "text": "Downloaded from https://publisher.example/...",
            "bbox": [18, 30, 140, 1480],
            "evidence": ["margin-band"],
        },
    ]

    estimate = estimate_layout_bands(blocks)

    assert estimate.status == "ACCEPT"
    assert estimate.header_band is not None
    assert estimate.header_band < 150
    assert estimate.support_pages == [1, 3]
    assert any("margin_band" in " ".join(c["reason"]) for c in estimate.excluded_candidates)


def test_empty_tall_noise_block_excluded_from_header_band() -> None:
    from paperforge.worker.ocr_banding import estimate_layout_bands

    blocks = [
        {
            "page": 1,
            "page_width": 1200,
            "page_height": 1500,
            "role": "noise",
            "raw_label": "header",
            "text": "Header",
            "bbox": [100, 75, 350, 100],
            "evidence": [],
        },
        {
            "page": 2,
            "page_width": 1200,
            "page_height": 1500,
            "role": "noise",
            "raw_label": "header",
            "text": "Header",
            "bbox": [100, 74, 350, 102],
            "evidence": [],
        },
        {
            "page": 3,
            "page_width": 1200,
            "page_height": 1500,
            "role": "noise",
            "raw_label": "header",
            "text": "",
            "bbox": [500, 90, 650, 213],
            "evidence": [],
        },
    ]

    estimate = estimate_layout_bands(blocks)

    assert estimate.status == "ACCEPT"
    assert estimate.header_band == 102
    assert any("empty_tall_noise" in c["reason"] for c in estimate.excluded_candidates)


def test_stable_running_headers_define_global_band() -> None:
    from paperforge.worker.ocr_banding import estimate_layout_bands

    blocks = []
    for page, y2 in [(1, 84), (2, 88), (3, 91), (4, 109), (5, 102)]:
        blocks.append(
            {
                "page": page,
                "page_width": 1200,
                "page_height": 1500,
                "role": "noise",
                "raw_label": "header",
                "text": f"Running header {page}",
                "bbox": [150, y2 - 24, 420, y2],
                "evidence": [],
            }
        )

    estimate = estimate_layout_bands(blocks)

    assert estimate.status == "ACCEPT"
    assert estimate.header_band == 109
    assert estimate.support_pages == [1, 2, 3, 4, 5]


def test_no_stable_noise_candidates_degrades_to_none() -> None:
    from paperforge.worker.ocr_banding import estimate_layout_bands

    blocks = [
        {
            "page": 1,
            "page_width": 1200,
            "page_height": 1500,
            "role": "noise",
            "raw_label": "header",
            "text": "Odd A",
            "bbox": [100, 70, 240, 95],
            "evidence": [],
        },
        {
            "page": 2,
            "page_width": 1200,
            "page_height": 1500,
            "role": "noise",
            "raw_label": "header",
            "text": "Odd B",
            "bbox": [100, 70, 240, 180],
            "evidence": [],
        },
    ]

    estimate = estimate_layout_bands(blocks)

    assert estimate.status == "HOLD_NO_STABLE_BAND"
    assert estimate.header_band is None
    assert estimate.support_pages == []
```

- [ ] **Step 2: Run the new estimator tests to confirm they fail**

Run:

```bash
pytest tests/test_ocr_document.py::test_tall_margin_band_noise_excluded_from_header_band \
       tests/test_ocr_document.py::test_empty_tall_noise_block_excluded_from_header_band \
       tests/test_ocr_document.py::test_stable_running_headers_define_global_band \
       tests/test_ocr_document.py::test_no_stable_noise_candidates_degrades_to_none -v
```

Expected: import failure for `paperforge.worker.ocr_banding` or missing symbols.

- [ ] **Step 3: Implement `ocr_banding.py` with the hard contracts**

```python
# paperforge/worker/ocr_banding.py
from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import median


@dataclass
class LayoutBandEstimate:
    header_band: float | None
    footer_band: float | None
    status: str
    method: str
    accepted_candidates: list[dict]
    excluded_candidates: list[dict]
    support_pages: list[int]
    warnings: list[str]


@dataclass
class UsableContentDecision:
    usable: bool
    policy: str
    reason: list[str]
    header_band: float | None
    footer_band: float | None
    role: str


def _block_text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _block_bbox(block: dict) -> list[float] | None:
    bbox = block.get("bbox") or block.get("block_bbox")
    return bbox if bbox and len(bbox) >= 4 else None


def collect_layout_band_candidates(blocks: list[dict]) -> list[dict]:
    records: list[dict] = []
    for block in blocks:
        bbox = _block_bbox(block)
        if not bbox:
            continue
        page_width = float(block.get("page_width") or 0)
        page_height = float(block.get("page_height") or 0)
        if page_width <= 0 or page_height <= 0:
            continue
        role = str(block.get("role") or "")
        raw_label = str(block.get("raw_label") or "")
        if role not in {"noise", "header", "footer", "number"} and raw_label not in {"header", "footer", "number"}:
            continue

        x1, y1, x2, y2 = bbox
        width = max(0.0, x2 - x1)
        height = max(0.0, y2 - y1)
        touches_header_band = y1 < page_height * 0.15
        inside_header_band = y2 < page_height * 0.15
        touches_footer_band = y2 > page_height * 0.85
        inside_footer_band = y1 > page_height * 0.85
        if not (touches_header_band or touches_footer_band):
            continue

        records.append(
            {
                "page": int(block.get("page") or 0),
                "page_width": page_width,
                "page_height": page_height,
                "role": role,
                "raw_label": raw_label,
                "text": _block_text(block),
                "bbox": [x1, y1, x2, y2],
                "x1_ratio": x1 / page_width,
                "x2_ratio": x2 / page_width,
                "y1_ratio": y1 / page_height,
                "y2_ratio": y2 / page_height,
                "width_ratio": width / page_width,
                "height_ratio": height / page_height,
                "candidate_side": "header" if touches_header_band else "footer",
                "inside_header_band": inside_header_band,
                "inside_footer_band": inside_footer_band,
                "decision": "accepted",
                "reason": [],
                "evidence": list(block.get("evidence") or []),
            }
        )
    return records


def _is_margin_band_like(candidate: dict) -> bool:
    return candidate["height_ratio"] > 0.08 and candidate["width_ratio"] < 0.35


def _is_watermark_text(candidate: dict) -> bool:
    text = candidate["text"].lower()
    return any(s in text for s in ["downloaded from", "accepted manuscript", "publisher", "onlinelibrary", "copyright"])


def _exclude_candidates(candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    accepted: list[dict] = []
    excluded: list[dict] = []
    for c in candidates:
        reasons: list[str] = []
        if c["height_ratio"] > 0.12:
            reasons.append("abnormally_tall_noise")
        if c["height_ratio"] > 0.04 and not c["text"].strip():
            reasons.append("empty_tall_noise")
        if _is_margin_band_like(c):
            reasons.append("margin_band_geometry")
        if _is_margin_band_like(c) and (_is_watermark_text(c) or any("margin-band" in e or "margin_band" in e for e in c.get("evidence", []))):
            reasons.append("watermark_margin_band")

        if reasons:
            excluded.append({**c, "decision": "excluded", "reason": reasons})
        else:
            accepted.append(c)
    return accepted, excluded


def _cluster_tolerance(page_heights: list[float]) -> float:
    med = median(page_heights) if page_heights else 0.0
    return max(25.0, 0.015 * med)


def _cluster_values(values: list[tuple[int, float]], tolerance: float) -> list[list[tuple[int, float]]]:
    if not values:
        return []
    values = sorted(values, key=lambda x: x[1])
    clusters: list[list[tuple[int, float]]] = [[values[0]]]
    for item in values[1:]:
        if abs(item[1] - clusters[-1][-1][1]) <= tolerance:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def estimate_layout_bands(blocks: list[dict]) -> LayoutBandEstimate:
    candidates = collect_layout_band_candidates(blocks)
    accepted, excluded = _exclude_candidates(candidates)
    if not accepted:
        return LayoutBandEstimate(None, None, "EMPTY", "robust_cluster", [], excluded, [], ["no_accepted_candidates"])

    page_heights = [c["page_height"] for c in accepted]
    tolerance = _cluster_tolerance(page_heights)
    header_page_values: dict[int, float] = {}
    footer_page_values: dict[int, float] = {}
    for c in accepted:
        page = c["page"]
        if c["candidate_side"] == "header":
            header_page_values[page] = max(header_page_values.get(page, c["bbox"][3]), c["bbox"][3])
        else:
            footer_page_values[page] = min(footer_page_values.get(page, c["bbox"][1]), c["bbox"][1])

    def support_threshold(n: int) -> int:
        return max(2, math.ceil(0.2 * n))

    def choose(values: dict[int, float], side: str) -> tuple[float | None, list[int], str]:
        if not values:
            return None, [], "none"
        clusters = _cluster_values(list(values.items()), tolerance)
        clusters.sort(key=lambda cl: (-len(cl), min(v for _, v in cl)))
        best = clusters[0]
        if len(best) < support_threshold(len(values)):
            return None, [], "hold"
        only_vals = sorted(v for _, v in best)
        if side == "header":
            value = only_vals[math.ceil(0.9 * (len(only_vals) - 1))]
        else:
            value = only_vals[math.floor(0.1 * (len(only_vals) - 1))]
        return value, sorted(p for p, _ in best), "accept"

    header_band, header_pages, header_status = choose(header_page_values, "header")
    footer_band, footer_pages, footer_status = choose(footer_page_values, "footer")

    status = "ACCEPT" if (header_status == "accept" or footer_status == "accept") else "HOLD_NO_STABLE_BAND"
    if header_status == "none" and footer_status == "none":
        status = "EMPTY"

    support_pages = sorted({*header_pages, *footer_pages})
    warnings: list[str] = []
    if status == "HOLD_NO_STABLE_BAND":
        warnings.append("no_stable_cluster")

    return LayoutBandEstimate(header_band, footer_band, status, "robust_cluster", accepted, excluded, support_pages, warnings)


def choose_runtime_bands(
    robust_estimate: LayoutBandEstimate,
    legacy_header_band: float | None,
    legacy_footer_band: float | None,
    *,
    max_page_height: float,
) -> tuple[float | None, float | None, str]:
    if robust_estimate.status == "ACCEPT":
        return robust_estimate.header_band, robust_estimate.footer_band, "robust"

    legacy_header_safe = legacy_header_band is not None and legacy_header_band < 0.2 * max_page_height
    legacy_footer_safe = legacy_footer_band is not None and legacy_footer_band > 0.8 * max_page_height
    if legacy_header_safe or legacy_footer_safe:
        return legacy_header_band if legacy_header_safe else None, legacy_footer_band if legacy_footer_safe else None, "legacy_safe"

    return None, None, "none"


def decide_usable_content(block: dict, band_estimate: LayoutBandEstimate | None, *, context: str) -> UsableContentDecision:
    role = str(block.get("role") or "")
    strong_bypass = {
        "reference_heading",
        "reference_item",
        "reference_body",
        "backmatter_heading",
        "backmatter_boundary_heading",
    }
    if role in strong_bypass:
        return UsableContentDecision(True, "role_bypass", ["strong_role_bypass"], band_estimate.header_band if band_estimate else None, band_estimate.footer_band if band_estimate else None, role)

    bbox = _block_bbox(block)
    if not bbox or band_estimate is None:
        return UsableContentDecision(True, "no_band", ["missing_bbox_or_band"], band_estimate.header_band if band_estimate else None, band_estimate.footer_band if band_estimate else None, role)

    y1, y2 = bbox[1], bbox[3]
    if band_estimate.header_band is not None and y2 < band_estimate.header_band:
        return UsableContentDecision(False, context, ["above_header_band"], band_estimate.header_band, band_estimate.footer_band, role)
    if band_estimate.footer_band is not None and y1 > band_estimate.footer_band:
        return UsableContentDecision(False, context, ["below_footer_band"], band_estimate.header_band, band_estimate.footer_band, role)
    return UsableContentDecision(True, context, ["within_usable_band"], band_estimate.header_band, band_estimate.footer_band, role)
```

- [ ] **Step 4: Run the estimator tests to verify they pass**

Run:

```bash
pytest tests/test_ocr_document.py::test_tall_margin_band_noise_excluded_from_header_band \
       tests/test_ocr_document.py::test_empty_tall_noise_block_excluded_from_header_band \
       tests/test_ocr_document.py::test_stable_running_headers_define_global_band \
       tests/test_ocr_document.py::test_no_stable_noise_candidates_degrades_to_none -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_banding.py tests/test_ocr_document.py
git commit -m "feat: add robust layout band estimator core"
```

---

### Task 2: Integrate audit-only robust band diagnostics into document normalization

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `tests/test_ocr_document.py`

**Interfaces:**
- Consumes: `estimate_layout_bands(blocks) -> LayoutBandEstimate`
- Produces:
  - `DocumentStructure.layout_band_estimate: dict | None`
  - dry-run diagnostics with `mode="DRY_RUN"`
  - `robust_status` separated from dry-run mode

- [ ] **Step 1: Add failing test for dry-run shape**

```python
def test_normalize_document_structure_exposes_layout_band_estimate_dry_run() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure

    blocks = [
        {
            "page": 1,
            "page_width": 1200,
            "page_height": 1500,
            "role": "noise",
            "raw_label": "header",
            "text": "Header",
            "bbox": [100, 70, 300, 100],
            "block_id": "h1",
        },
        {
            "page": 1,
            "page_width": 1200,
            "page_height": 1500,
            "role": "body_paragraph",
            "text": "Body text.",
            "bbox": [100, 130, 550, 220],
            "block_id": "b1",
        },
    ]

    doc, normalized = normalize_document_structure(blocks)

    assert doc.layout_band_estimate is not None
    assert doc.layout_band_estimate["mode"] == "DRY_RUN"
    assert doc.layout_band_estimate["robust_status"] in {"ACCEPT", "EMPTY", "HOLD_NO_STABLE_BAND"}
    assert "legacy_header_band" in doc.layout_band_estimate
    assert "robust_header_band_candidate" in doc.layout_band_estimate
```

- [ ] **Step 2: Run the dry-run test to confirm it fails**

Run:

```bash
pytest tests/test_ocr_document.py::test_normalize_document_structure_exposes_layout_band_estimate_dry_run -v
```

Expected: `DocumentStructure` has no `layout_band_estimate` field or dry-run keys mismatch.

- [ ] **Step 3: Add the field and wire dry-run output**

```python
# in DocumentStructure dataclass
layout_band_estimate: dict | None = None
```

Then in `normalize_document_structure()` after role resolution but before tail/body promotion:

```python
from paperforge.worker.ocr_banding import estimate_layout_bands

legacy_header_band, legacy_footer_band = _estimate_noise_bands(blocks)
robust_estimate = estimate_layout_bands(blocks)

layout_band_estimate = {
    "mode": "DRY_RUN",
    "legacy_header_band": legacy_header_band,
    "legacy_footer_band": legacy_footer_band,
    "robust_header_band_candidate": robust_estimate.header_band,
    "robust_footer_band_candidate": robust_estimate.footer_band,
    "robust_status": robust_estimate.status,
    "accepted_candidates": robust_estimate.accepted_candidates,
    "excluded_candidates": robust_estimate.excluded_candidates,
    "support_pages": robust_estimate.support_pages,
    "method": robust_estimate.method,
    "warnings": robust_estimate.warnings,
}

doc_structure.layout_band_estimate = layout_band_estimate
```

Important: runtime behavior must still use the **legacy** bands in this task.

- [ ] **Step 4: Run the dry-run integration test**

Run:

```bash
pytest tests/test_ocr_document.py::test_normalize_document_structure_exposes_layout_band_estimate_dry_run -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py tests/test_ocr_document.py
git commit -m "feat: expose layout band diagnostics in dry-run mode"
```

---

### Task 3: Enable robust runtime band selection with a real fallback helper

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `tests/test_ocr_document.py`

**Interfaces:**
- Consumes:
  - `choose_runtime_bands(...)`
  - `LayoutBandEstimate`
- Produces:
  - explicit runtime band source: `robust`, `legacy_safe`, or `none`

- [ ] **Step 1: Add failing tests for real fallback selection**

```python
def test_runtime_bands_use_robust_when_accept() -> None:
    from paperforge.worker.ocr_banding import LayoutBandEstimate, choose_runtime_bands

    estimate = LayoutBandEstimate(109, None, "ACCEPT", "robust_cluster", [], [], [1, 2], [])
    hb, fb, source = choose_runtime_bands(estimate, legacy_header_band=150, legacy_footer_band=None, max_page_height=1600)

    assert (hb, fb, source) == (109, None, "robust")


def test_runtime_bands_fallback_to_safe_legacy_when_robust_holds() -> None:
    from paperforge.worker.ocr_banding import LayoutBandEstimate, choose_runtime_bands

    estimate = LayoutBandEstimate(None, None, "HOLD_NO_STABLE_BAND", "robust_cluster", [], [], [], ["no_stable_cluster"])
    hb, fb, source = choose_runtime_bands(estimate, legacy_header_band=110, legacy_footer_band=None, max_page_height=1600)

    assert (hb, fb, source) == (110, None, "legacy_safe")


def test_runtime_bands_drop_unsafe_legacy_when_robust_holds() -> None:
    from paperforge.worker.ocr_banding import LayoutBandEstimate, choose_runtime_bands

    estimate = LayoutBandEstimate(None, None, "HOLD_NO_STABLE_BAND", "robust_cluster", [], [], [], ["no_stable_cluster"])
    hb, fb, source = choose_runtime_bands(estimate, legacy_header_band=1300, legacy_footer_band=None, max_page_height=1600)

    assert (hb, fb, source) == (None, None, "none")
```

- [ ] **Step 2: Run the runtime-selection tests to confirm the integration is still incomplete**

Run:

```bash
pytest tests/test_ocr_document.py::test_runtime_bands_use_robust_when_accept \
       tests/test_ocr_document.py::test_runtime_bands_fallback_to_safe_legacy_when_robust_holds \
       tests/test_ocr_document.py::test_runtime_bands_drop_unsafe_legacy_when_robust_holds -v
```

Expected:
- helper-only tests may already pass after Task 1
- runtime selection is still incomplete until the selected bands are wired into `ocr_document.py` and `ocr_render.py`

- [ ] **Step 3: Wire runtime selection in normalization and `_order_tail_blocks()` explicitly**

Inside `normalize_document_structure()` after dry-run diagnostics:

```python
max_page_height = max((float(b.get("page_height") or 0) for b in blocks), default=0.0)
header_band, footer_band, runtime_band_source = choose_runtime_bands(
    robust_estimate,
    legacy_header_band,
    legacy_footer_band,
    max_page_height=max_page_height,
)
doc_structure.layout_band_estimate["runtime_band_source"] = runtime_band_source
```

Use these selected `header_band/footer_band` values where `normalize_document_structure()` currently consumes the legacy tuple.

Then update `ocr_render.py` inside `_order_tail_blocks()` itself — not just `render_fulltext_markdown()` — because `_order_tail_blocks()` currently owns `_estimate_noise_bands(blocks)` and passes the result to `_reorder_tail_run()`:

```python
legacy_header_band, legacy_footer_band = _estimate_noise_bands(blocks)
robust_estimate = estimate_layout_bands(blocks)
max_page_height = max((float(b.get("page_height") or 0) for b in blocks), default=0.0)

header_band, footer_band, runtime_band_source = choose_runtime_bands(
    robust_estimate,
    legacy_header_band,
    legacy_footer_band,
    max_page_height=max_page_height,
)

runtime_band_estimate = LayoutBandEstimate(
    header_band=header_band,
    footer_band=footer_band,
    status="ACCEPT" if (header_band is not None or footer_band is not None) else "EMPTY",
    method=f"runtime_{runtime_band_source}",
    accepted_candidates=robust_estimate.accepted_candidates,
    excluded_candidates=robust_estimate.excluded_candidates,
    support_pages=robust_estimate.support_pages,
    warnings=robust_estimate.warnings,
)
```

Pass `runtime_band_estimate` into `_reorder_tail_run()` using the Task 4 signature bridge below.
- [ ] **Step 4: Run the runtime selection tests**

Run:

```bash
pytest tests/test_ocr_document.py::test_runtime_bands_use_robust_when_accept \
       tests/test_ocr_document.py::test_runtime_bands_fallback_to_safe_legacy_when_robust_holds \
       tests/test_ocr_document.py::test_runtime_bands_drop_unsafe_legacy_when_robust_holds -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_banding.py paperforge/worker/ocr_document.py paperforge/worker/ocr_render.py tests/test_ocr_document.py
git commit -m "feat: enable robust runtime band selection"
```

---

### Task 4: Normalize role-aware gating and enforce ownership-before-band for backmatter

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_render.py`

**Interfaces:**
- Consumes: `decide_usable_content(...)`
- Produces: explicit role-matrix behavior at every gate site

- [ ] **Step 1: Add failing role-aware tests**

```python
def test_reference_item_bypasses_usable_content_gate_even_above_header_band() -> None:
    from paperforge.worker.ocr_banding import LayoutBandEstimate, decide_usable_content

    estimate = LayoutBandEstimate(213, None, "ACCEPT", "robust_cluster", [], [], [16], [])
    block = {
        "role": "reference_item",
        "text": "2. Example reference",
        "bbox": [611, 142, 1069, 180],
    }

    decision = decide_usable_content(block, estimate, context="tail_render")
    assert decision.usable is True
    assert decision.policy == "role_bypass"


def test_backmatter_body_with_heading_owner_not_dropped_by_band() -> None:
    from paperforge.worker.ocr_render import _reorder_tail_run

    heading = {"role": "backmatter_heading", "text": "Acknowledgments", "bbox": [100, 1000, 300, 1030]}
    body = {"role": "backmatter_body", "text": "We thank the lab.", "bbox": [100, 1035, 500, 1080]}

    ordered, _, _ = _reorder_tail_run([heading, body], None, None, header_band=1100, footer_band=None, page_width=1200)
    texts = [b.get("text") for b in ordered]
    assert texts == ["Acknowledgments", "We thank the lab."]
```

- [ ] **Step 2: Run the tests to confirm the current call-site order is wrong/incomplete**

Run:

```bash
pytest tests/test_ocr_document.py::test_reference_item_bypasses_usable_content_gate_even_above_header_band \
       tests/test_ocr_render.py::test_backmatter_body_with_heading_owner_not_dropped_by_band -v
```

Expected: one or both fail before call-site conversion.

- [ ] **Step 3: Convert call sites with the correct ordering and add the `_reorder_tail_run()` bridge**

First extend `_reorder_tail_run()` to accept a structured estimate while remaining backward compatible:

```python
from paperforge.worker.ocr_banding import LayoutBandEstimate, decide_usable_content

def _reorder_tail_run(
    tail_blocks: list[dict],
    carried_ref: dict | None = None,
    carried_backmatter: dict | None = None,
    *,
    header_band: float | None = None,
    footer_band: float | None = None,
    band_estimate: LayoutBandEstimate | None = None,
    page_width: float = 1200,
    skip_section_grouping: bool = False,
) -> tuple[list[dict], dict | None, dict | None]:
    if band_estimate is None:
        band_estimate = LayoutBandEstimate(
            header_band=header_band,
            footer_band=footer_band,
            status="ACCEPT" if (header_band is not None or footer_band is not None) else "EMPTY",
            method="runtime_selected",
            accepted_candidates=[],
            excluded_candidates=[],
            support_pages=[],
            warnings=[],
        )
```

Then in `ocr_render.py` Phase 1 classification inside `_reorder_tail_run()`:

```python
elif role == "reference_item":
    ref_items.append(block)
elif role == "reference_body":
    ref_items.append(block)
elif role == "backmatter_body":
    body_pool.append(block)
```

Do **not** gate `backmatter_body` at Phase 1.

Then in Phase 4b, after `_find_owning_heading()`:

```python
if idx is not None:
    backmatter_sections[idx]["bodies"].append(body)
    continue

decision = decide_usable_content(body, band_estimate, context="tail_render_backmatter")
if not decision.usable:
    non_tail_pass.append(body)
    continue
```

This enforces:

- heading ownership first
- band gate second

In `ocr_document.py`, `_promote_tail_body_candidates()` should call `decide_usable_content(..., context="tail_candidate_promotion")` instead of the raw bool helper.

Finally, when `_order_tail_blocks()` calls `_reorder_tail_run()`, pass the new structured estimate:

```python
ordered, carried_ref, carried_backmatter = _reorder_tail_run(
    sorted_blocks,
    carried_ref,
    carried_backmatter,
    header_band=header_band,
    footer_band=footer_band,
    band_estimate=runtime_band_estimate,
    page_width=pw,
    skip_section_grouping=_page_has_ref_items and not _page_has_ref_heading,
)
```

- [ ] **Step 4: Run the role-aware tests plus the focused OCR suite**

Run:

```bash
pytest tests/test_ocr_document.py::test_reference_item_bypasses_usable_content_gate_even_above_header_band \
       tests/test_ocr_render.py::test_backmatter_body_with_heading_owner_not_dropped_by_band \
       tests/test_ocr_document.py tests/test_ocr_render.py tests/test_ocr_families.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_banding.py paperforge/worker/ocr_document.py paperforge/worker/ocr_render.py tests/test_ocr_document.py tests/test_ocr_render.py
git commit -m "fix: make layout band gating role-aware"
```

---

### Task 5: Implement column-aware two-column continuation attachment without body-pool fallback

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `tests/test_ocr_render.py`

**Interfaces:**
- Consumes:
  - page width / bbox geometry
  - `reference_heading`, `reference_item`, `reference_body`
- Produces:
  - `_block_column(block: dict, page_width: float) -> int | None`
  - `_should_attach_reference_item_to_ref_section(...) -> bool`
  - `rejected_ref_items: list[dict]` path that does **not** silently fall back to generic `body_pool`

- [ ] **Step 1: Add helper-level failing tests**

```python
def test_different_column_reference_above_heading_attaches() -> None:
    from paperforge.worker.ocr_render import _should_attach_reference_item_to_ref_section

    heading = {"role": "reference_heading", "bbox": [100, 1345, 204, 1367]}
    ref2 = {"role": "reference_item", "bbox": [611, 142, 1069, 180]}

    assert _should_attach_reference_item_to_ref_section(ref2, heading, page_width=1200, ref_bottom=1367) is True


def test_same_column_reference_above_heading_does_not_attach() -> None:
    from paperforge.worker.ocr_render import _should_attach_reference_item_to_ref_section

    heading = {"role": "reference_heading", "bbox": [100, 700, 204, 730]}
    bad_ref = {"role": "reference_item", "bbox": [110, 650, 566, 690]}

    assert _should_attach_reference_item_to_ref_section(bad_ref, heading, page_width=1200, ref_bottom=730) is False
```

- [ ] **Step 2: Add the integration failing test for the 95FDVE4W pattern**

```python
def test_two_column_right_column_refs_attach_after_left_column_heading() -> None:
    from paperforge.worker.ocr_render import _reorder_tail_run

    open_access = {
        "role": "body_paragraph",
        "text": "This is an open access article distributed...",
        "bbox": [98, 1071, 568, 1193],
        "page_width": 1200,
        "page": 16,
    }
    ack = {
        "role": "body_paragraph",
        "text": "Acknowledgments We thank the Core Facilities...",
        "bbox": [99, 1225, 568, 1327],
        "page_width": 1200,
        "page": 16,
    }
    ref_heading = {
        "role": "reference_heading",
        "text": "References",
        "bbox": [100, 1345, 204, 1367],
        "page_width": 1200,
        "page": 16,
    }
    ref1 = {
        "role": "reference_item",
        "text": "1. Bedi A, Bishop J...",
        "bbox": [110, 1377, 566, 1416],
        "page_width": 1200,
        "page": 16,
        "block_number": "1",
    }
    ref2 = {
        "role": "reference_item",
        "text": "2. Bedi A, Dines J...",
        "bbox": [611, 142, 1069, 180],
        "page_width": 1200,
        "page": 16,
        "block_number": "2",
    }

    ordered, _, _ = _reorder_tail_run(
        [open_access, ack, ref_heading, ref1, ref2],
        carried_ref=None,
        carried_backmatter=None,
        page_width=1200,
    )

    texts = [b.get("text", "") for b in ordered]
    assert texts.index("References") < texts.index("1. Bedi A, Bishop J...")
    assert texts.index("1. Bedi A, Bishop J...") < texts.index("2. Bedi A, Dines J...")
```

- [ ] **Step 3: Run the helper and integration tests to confirm they fail**

Run:

```bash
pytest tests/test_ocr_render.py::test_different_column_reference_above_heading_attaches \
       tests/test_ocr_render.py::test_same_column_reference_above_heading_does_not_attach \
       tests/test_ocr_render.py::test_two_column_right_column_refs_attach_after_left_column_heading -v
```

Expected: current code fails at least the integration test.

- [ ] **Step 4: Implement the helper and stop using generic body_pool for rejected refs**

Add to `ocr_render.py`:

```python
def _block_column(block: dict, page_width: float) -> int | None:
    bbox = block.get("bbox") or block.get("block_bbox")
    if not bbox or len(bbox) < 4:
        return None
    x_center = (bbox[0] + bbox[2]) / 2
    return 0 if x_center < (page_width / 2.0) else 1


def _should_attach_reference_item_to_ref_section(
    block: dict,
    ref_heading: dict | None,
    *,
    page_width: float,
    ref_bottom: float,
) -> bool:
    bbox = block.get("bbox") or block.get("block_bbox")
    if not bbox or len(bbox) < 4:
        return True
    if ref_heading is None:
        return True

    heading_bbox = ref_heading.get("bbox") or ref_heading.get("block_bbox")
    if not heading_bbox or len(heading_bbox) < 4:
        return True

    block_col = _block_column(block, page_width)
    heading_col = _block_column(ref_heading, page_width)
    if block_col == heading_col:
        return bbox[1] >= ref_bottom
    return True
```

Then replace the old Phase 3 ref assignment with:

```python
rejected_ref_items: list[dict] = []
for block in ref_items:
    if ref_heading:
        if _should_attach_reference_item_to_ref_section(
            block,
            ref_heading,
            page_width=page_width,
            ref_bottom=ref_bottom,
        ):
            ref_section["bodies"].append(block)
        else:
            rejected_ref_items.append(block)
    elif _needs_synthetic_ref:
        ref_section["bodies"].append(block)
    else:
        rejected_ref_items.append(block)
```

Emit order must keep rejected refs explicit and separate from generic body routing:

```python
result.extend(non_tail_pass)
result.extend(rejected_ref_items)
result.extend(carried_bodies)
```

Do **not** send rejected refs into generic `body_pool`, or Phase 4b will reabsorb them and make the helper meaningless.

- [ ] **Step 5: Run the helper tests plus paper regressions**

Run:

```bash
pytest tests/test_ocr_render.py::test_different_column_reference_above_heading_attaches \
       tests/test_ocr_render.py::test_same_column_reference_above_heading_does_not_attach \
       tests/test_ocr_render.py::test_two_column_right_column_refs_attach_after_left_column_heading -v
python scripts/dev/ocr_rebuild_paper.py 95FDVE4W WV2FF4NV 58UFL9UN
```

Expected:
- helper tests pass
- integration test passes
- `95FDVE4W/fulltext.md` has `## References` before both ref 1 and ref 2
- `WV2FF4NV` and `58UFL9UN` still rebuild cleanly

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_render.py tests/test_ocr_render.py
git commit -m "fix: attach two-column continuation refs to reference sections"
```

---

### Task 6: Final regression and paper verification

**Files:**
- Modify: none (verification only)

**Interfaces:**
- Consumes: all previous tasks
- Produces: verified plan completion evidence

- [ ] **Step 1: Run the focused OCR test suite**

Run:

```bash
pytest tests/test_ocr_document.py tests/test_ocr_render.py tests/test_ocr_families.py -q
```

Expected: all tests pass.

- [ ] **Step 2: Rebuild the known regression papers plus catastrophic watermark papers**

Run:

```bash
python scripts/dev/ocr_rebuild_paper.py 37LK5T97 B43QSAJP 62LTMCI8 4KCHGV2Z 58UFL9UN JQMRCEXY TXMVULD7 95FDVE4W WV2FF4NV KH3GMDCH BKKR4KIV ES23M9IS 97M7HFCD 3CEUN7T3
```

Expected: all papers rebuild with `[OK]` fulltext output.

- [ ] **Step 3: Spot-check only the assertions owned by this plan**

Run:

```bash
python -c "
import json
from pathlib import Path

root = Path('D:/L/OB/Literature-hub/System/PaperForge/ocr')

checks = {
    '95FDVE4W': ['## References', '1. Bedi A, Bishop J', '2. Bedi A, Dines J'],
}

for key, needles in checks.items():
    with open(root / key / 'fulltext.md', encoding='utf-8') as f:
        text = f.read()
    print('===', key, '===')
    for n in needles:
        print(n, '->', n in text)

for key in ['KH3GMDCH', 'BKKR4KIV', 'ES23M9IS', '97M7HFCD', '3CEUN7T3']:
    with open(root / key / 'structure' / 'document_structure.json', encoding='utf-8') as f:
        ds = json.load(f)
    lbe = ds.get('layout_band_estimate') or {}
    print('===', key, 'layout_band_estimate ===')
    print('mode ->', lbe.get('mode'))
    print('robust_status ->', lbe.get('robust_status'))
    print('legacy_header_band ->', lbe.get('legacy_header_band'))
    print('robust_header_band_candidate ->', lbe.get('robust_header_band_candidate'))
    print('excluded_margin_band ->', any(
        'margin_band' in ' '.join(c.get('reason', []))
        for c in lbe.get('excluded_candidates', [])
    ))
"
```

Expected:
- `95FDVE4W`: heading before refs in output order
- catastrophic watermark papers expose serialized diagnostics
- `KH3GMDCH` / `BKKR4KIV` / `ES23M9IS` / `97M7HFCD`: `legacy_header_band` is very high, `robust_header_band_candidate` is back in a sane range, and `excluded_candidates` includes `margin_band_geometry` / `watermark_margin_band`
- `3CEUN7T3`: stable baseline remains normal

Note: do **not** use this task to validate unrelated reference-zone fixes unless those prerequisite fixes are already landed.

- [ ] **Step 4: Review worktree state**

Run:

```bash
git status --short
git log -6 --oneline
```

Expected: only the planned files changed; commit sequence is intelligible.

- [ ] **Step 5: Commit final verification-related touchups only if needed**

```bash
# Only if a final tiny test/doc adjustment was required.
git add tests/test_ocr_document.py tests/test_ocr_render.py tests/test_ocr_families.py paperforge/worker/ocr_document.py paperforge/worker/ocr_render.py paperforge/worker/ocr_banding.py
git commit -m "test: lock layout robustness regressions"
```

If no final touchup was needed, skip the commit.

---

## Self-Review

### Spec coverage

- Candidate record contract / exclusion / aggregation → Task 1
- Dry-run diagnostics shape → Task 2
- Runtime band selection contract → Task 3
- Role matrix and ownership-before-band → Task 4
- Two-column continuation refs → Task 5
- Focused regressions and prerequisite-aware verification → Task 6

### Placeholder scan

- No `TBD` / `TODO`
- All code-changing steps include code blocks
- All verification steps include exact commands

### Type consistency

Defined interfaces are consistent:

- `LayoutBandEstimate`
- `UsableContentDecision`
- `collect_layout_band_candidates()`
- `estimate_layout_bands()`
- `choose_runtime_bands()`
- `decide_usable_content()`
- `_should_attach_reference_item_to_ref_section()`

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-02-layout-robustness-layer-implementation.md`.

Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints
