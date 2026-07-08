# Reference Zone And Ownership Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared layout-facts layer that improves reference-zone containment and figure/table ownership on untouched OCR papers without reopening OCR-v2 role classification.

**Architecture:** Keep the existing OCR-v2 pipeline and strengthen it in place. First compute lightweight layout facts after document normalization, then consume those facts in two downstream paths: a practical reference corridor that optimizes for clean containment, and a cluster-first ownership path that treats bridgeable empty gaps as display continuity rather than hard separators.

**Tech Stack:** Python 3.14, existing `paperforge.worker` OCR pipeline, pytest, real-paper regressions, existing audit helpers under `.opencode/skills/paperforge-development/`.

---

## File Structure

- Modify: `paperforge/worker/ocr_document.py`
  - Own the shared layout-facts layer, reference corridor scoring, and local entry reconstruction hooks.
- Create: `paperforge/worker/ocr_reference_signals.py`
  - Own coarse reference-family scoring, journal-abbreviation support, and block/entry-level style signals.
- Create: `paperforge/resources/nlm_journal_abbreviations.json`
  - Compact biomedical journal abbreviation lexicon used as strong positive evidence only.
- Modify: `paperforge/worker/ocr_figures.py`
  - Own display-cluster construction, bridge-aware grouping, and ownership validation for figures.
- Modify: `paperforge/worker/ocr_tables.py`
  - Reuse display-cluster facts for table ownership and prevent empty-gap fragmentation on irregular table pages.
- Modify: `paperforge/worker/ocr_structural_gate.py`
  - Ensure `HOLD` reference candidates stop contaminating accepted reference membership.
- Modify: `paperforge/worker/ocr_health.py`
  - Consume accepted outcomes only where health logic needs the hardened reference/ownership surfaces.
- Test: `tests/test_ocr_document.py`
  - Unit coverage for shared layout facts, reference corridor anti-intrusion, and local entry reconstruction.
- Test: `tests/test_ocr_layout_zones.py`
  - Zone-oriented regression coverage for mixed body/reference/tail pages.
- Test: `tests/test_ocr_figures.py`
  - Bridge-aware display-cluster and validation coverage for irregular figure layouts.
- Test: `tests/test_ocr_tables.py`
  - Bridge-aware table ownership coverage on sparse and empty-gap pages.
- Test: `tests/test_ocr_pdf_text_fallback.py`
  - Local PDF text fallback boundary coverage.
- Test: `tests/test_ocr_real_paper_regressions.py`
  - Untouched-paper protection for reference and ownership hardening.
- Update: `PROJECT-MANAGEMENT.md`
  - Record the hardening slice, measured impact, and any deliberately deferred edge cases.

Per repo policy, do not create git commits unless the user explicitly requests them.

---

### Task 1: Add Shared Layout Facts Before Specialized Consumers

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_layout_zones.py`

- [ ] **Step 1: Write the failing shared-layout-facts unit test**

Add to `tests/test_ocr_document.py`:

```python
def test_compute_layout_facts_marks_reading_band_region_boundary_and_bridge() -> None:
    from paperforge.worker.ocr_document import compute_layout_facts

    blocks = [
        {
            "block_id": "body_1",
            "page": 5,
            "role": "body_paragraph",
            "zone": "body_zone",
            "bbox": [80, 120, 520, 220],
            "text": "Body text.",
        },
        {
            "block_id": "ref_1",
            "page": 5,
            "role": "reference_item",
            "zone": "reference_zone",
            "bbox": [610, 120, 1120, 180],
            "text": "Smith J, Doe P. J Bone Miner Res. 2021;36(4):100-110.",
        },
        {
            "block_id": "gap_1",
            "page": 5,
            "role": "unknown_structural",
            "zone": "display_zone",
            "bbox": [640, 200, 1110, 360],
            "text": "",
        },
    ]

    facts = compute_layout_facts(blocks)
    by_id = {row["block_id"]: row for row in facts}

    assert by_id["body_1"]["layout_region"] == "body_flow"
    assert by_id["ref_1"]["layout_region"] == "reference_candidate"
    assert by_id["body_1"]["reading_band_id"] != by_id["ref_1"]["reading_band_id"]
    assert by_id["gap_1"]["bridge_eligible"] is True
    assert by_id["ref_1"]["boundary_before"] in {"weak", "hard"}
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python -m pytest tests/test_ocr_document.py -k "compute_layout_facts" -v --tb=short`

Expected: FAIL with import or missing function errors.

- [ ] **Step 3: Implement the minimal shared-layout-facts helper**

Add near layout/document helpers in `paperforge/worker/ocr_document.py`:

```python
def compute_layout_facts(blocks: list[dict]) -> list[dict]:
    facts: list[dict] = []
    band_seq = 0
    last_key: tuple[int, str, int] | None = None
    for block in sorted(blocks, key=lambda b: (int(b.get("page", 0) or 0), (b.get("bbox") or [0, 0, 0, 0])[0], (b.get("bbox") or [0, 0, 0, 0])[1])):
        page = int(block.get("page", 0) or 0)
        bbox = block.get("bbox") or [0, 0, 0, 0]
        role = str(block.get("role") or "")
        zone = str(block.get("zone") or "")
        text = str(block.get("text") or block.get("block_content") or "").strip()
        if zone == "reference_zone" or role in {"reference_heading", "reference_item"}:
            layout_region = "reference_candidate"
        elif zone == "display_zone" or role in {"figure_asset", "media_asset", "table_html", "figure_caption", "table_caption"}:
            layout_region = "display_zone"
        elif zone in {"tail_nonref_hold_zone", "post_reference_backmatter_zone"} or role.startswith("backmatter"):
            layout_region = "tail_candidate"
        elif zone in {"frontmatter_side_zone", "frontmatter_main_zone"} and role in {"structured_insert", "structured_insert_candidate", "non_body_insert"}:
            layout_region = "side_insert"
        else:
            layout_region = "body_flow"
        col_key = 0 if len(bbox) < 4 else (0 if bbox[0] < 600 else 1)
        key = (page, layout_region, col_key)
        if key != last_key:
            band_seq += 1
            last_key = key
        facts.append(
            {
                "block_id": str(block.get("block_id") or ""),
                "reading_band_id": f"band_{band_seq:03d}",
                "display_cluster_candidate_id": f"disp_{page}_{col_key}" if layout_region == "display_zone" else "",
                "layout_region": layout_region,
                "boundary_before": "hard" if layout_region in {"reference_candidate", "display_zone"} and role not in {"reference_item", "figure_asset", "media_asset", "table_html"} else "none",
                "boundary_after": "none",
                "bridge_eligible": role == "unknown_structural" and not text and layout_region == "display_zone",
            }
        )
    return facts
```

- [ ] **Step 4: Attach layout facts to the normalized block flow**

In the normalization flow in `paperforge/worker/ocr_document.py`, after blocks have stable `role` and `zone`, add:

```python
    layout_facts = compute_layout_facts(blocks)
    fact_by_id = {row["block_id"]: row for row in layout_facts if row.get("block_id")}
    for block in blocks:
        block_id = str(block.get("block_id") or "")
        fact = fact_by_id.get(block_id)
        if not fact:
            continue
        block["reading_band_id"] = fact["reading_band_id"]
        block["display_cluster_candidate_id"] = fact["display_cluster_candidate_id"]
        block["layout_region"] = fact["layout_region"]
        block["boundary_before"] = fact["boundary_before"]
        block["boundary_after"] = fact["boundary_after"]
        block["bridge_eligible"] = fact["bridge_eligible"]
```

- [ ] **Step 5: Add one zone regression for mixed same-page content**

Add to `tests/test_ocr_layout_zones.py`:

```python
def test_layout_facts_split_body_and_reference_candidates_on_same_page() -> None:
    from paperforge.worker.ocr_document import compute_layout_facts

    blocks = [
        {"block_id": "b1", "page": 12, "role": "body_paragraph", "zone": "body_zone", "bbox": [70, 100, 540, 160], "text": "Conclusion paragraph."},
        {"block_id": "r1", "page": 12, "role": "reference_item", "zone": "reference_zone", "bbox": [620, 100, 1110, 150], "text": "Brown T. Lancet. 2020;395:10-12."},
    ]

    facts = {row["block_id"]: row for row in compute_layout_facts(blocks)}
    assert facts["b1"]["layout_region"] == "body_flow"
    assert facts["r1"]["layout_region"] == "reference_candidate"
    assert facts["b1"]["reading_band_id"] != facts["r1"]["reading_band_id"]
```

- [ ] **Step 6: Re-run the focused tests until green**

Run: `python -m pytest tests/test_ocr_document.py -k "compute_layout_facts" -v --tb=short`

Run: `python -m pytest tests/test_ocr_layout_zones.py -k "layout_facts_split_body_and_reference_candidates" -v --tb=short`

Expected: PASS.

---

### Task 2: Add Reference Family Signals And Journal-Abbreviation Support

**Files:**
- Create: `paperforge/worker/ocr_reference_signals.py`
- Create: `paperforge/resources/nlm_journal_abbreviations.json`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Write failing tests for coarse reference-family scoring**

Append to `tests/test_ocr_document.py`:

```python
def test_reference_signal_detector_scores_unnumbered_vancouver_entry() -> None:
    from paperforge.worker.ocr_reference_signals import score_reference_entry

    result = score_reference_entry(
        "Smith J, Doe P. Bone regeneration with scaffold support. J Bone Miner Res. 2021;36(4):100-110. doi:10.1000/test"
    )

    assert result["family"] == "vancouver_structured_unnumbered"
    assert result["confidence"] > 0.6
    assert result["signals"]["journal_lexicon_match"] is True


def test_reference_signal_detector_distinguishes_report_like_entry() -> None:
    from paperforge.worker.ocr_reference_signals import score_reference_entry

    result = score_reference_entry(
        "World Health Organization. Clinical management guideline [Internet]. 2023 [cited 2024 Jan 10]. Available from: https://example.org"
    )

    assert result["family"] == "book_or_report"
    assert result["signals"]["online_marker_signature"] is True
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python -m pytest tests/test_ocr_document.py -k "reference_signal_detector" -v --tb=short`

Expected: FAIL with module import errors.

- [ ] **Step 3: Add a compact biomedical journal abbreviation lexicon**

Create `paperforge/resources/nlm_journal_abbreviations.json` with a small seed set that is enough for unit tests and the first untouched-paper pass:

```json
[
  {"canonical_title": "The New England Journal of Medicine", "med_abbr": "N Engl J Med", "iso_abbr": "N. Engl. J. Med."},
  {"canonical_title": "The Lancet", "med_abbr": "Lancet", "iso_abbr": "Lancet"},
  {"canonical_title": "Journal of Bone and Mineral Research", "med_abbr": "J Bone Miner Res", "iso_abbr": "J. Bone Miner. Res."},
  {"canonical_title": "British Medical Journal", "med_abbr": "BMJ", "iso_abbr": "BMJ"},
  {"canonical_title": "Nature Reviews Rheumatology", "med_abbr": "Nat Rev Rheumatol", "iso_abbr": "Nat. Rev. Rheumatol."}
]
```

- [ ] **Step 4: Implement the minimal reference signal module**

Create `paperforge/worker/ocr_reference_signals.py`:

```python
from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]+", " ", text)).strip().lower()


@lru_cache(maxsize=1)
def _journal_rows() -> list[dict]:
    raw = resources.files("paperforge.resources").joinpath("nlm_journal_abbreviations.json").read_text(encoding="utf-8")
    return json.loads(raw)


def _has_journal_match(text: str) -> bool:
    norm = _norm(text)
    for row in _journal_rows():
        for field in ("med_abbr", "iso_abbr", "canonical_title"):
            value = _norm(str(row.get(field) or ""))
            if value and value in norm:
                return True
    return False


def score_reference_entry(text: str) -> dict:
    text = str(text or "").strip()
    lower = text.lower()
    has_author_signature = bool(re.search(r"\b[A-Z][a-zA-Z'\-]+\s+[A-Z]{1,3}(?:,|\b)", text))
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", text))
    has_vol_pages = bool(re.search(r"\b\d+\s*\(\d+\)\s*:\s*[A-Za-z0-9\-]+", text) or re.search(r"\b\d+\s*:\s*[A-Za-z0-9\-]+", text))
    has_online = any(token in lower for token in ("[internet]", "available from", "doi:", "pmid:", "pmcid:", "published online", "cited "))
    has_report_markers = any(token in lower for token in ("guideline", "organization", "committee", "available from")) or "[internet]" in lower
    has_number_lead = bool(re.match(r"^\s*(\[\d+\]|\d+[\.)]?)(\s+|$)", text))
    journal_match = _has_journal_match(text)

    family = "unknown"
    confidence = 0.0
    if has_author_signature and has_year and (has_vol_pages or journal_match):
        family = "vancouver_structured_numbered" if has_number_lead else "vancouver_structured_unnumbered"
        confidence = 0.8 if journal_match else 0.65
    elif has_report_markers and has_year:
        family = "book_or_report"
        confidence = 0.7
    elif re.search(r"\b[A-Z][a-zA-Z'\-]+\s+[A-Z].*\((19|20)\d{2}\)", text):
        family = "author_year"
        confidence = 0.6
    return {
        "family": family,
        "confidence": confidence,
        "signals": {
            "author_signature": has_author_signature,
            "year_signature": has_year,
            "volume_issue_pages_signature": has_vol_pages,
            "online_marker_signature": has_online,
            "journal_lexicon_match": journal_match,
        },
    }
```

- [ ] **Step 5: Re-run the reference-signal tests until green**

Run: `python -m pytest tests/test_ocr_document.py -k "reference_signal_detector" -v --tb=short`

Expected: PASS.

---

### Task 3: Harden Reference Corridor Containment Without Over-Parsing Citations

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_structural_gate.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_layout_zones.py`

- [ ] **Step 1: Write the failing anti-intrusion regression tests**

Append to `tests/test_ocr_document.py`:

```python
def test_reference_corridor_keeps_reference_like_blocks_but_rejects_acknowledgements() -> None:
    from paperforge.worker.ocr_document import score_reference_corridor_membership

    ref_block = {
        "block_id": "r1",
        "page": 20,
        "role": "reference_item",
        "zone": "reference_zone",
        "layout_region": "reference_candidate",
        "text": "Brown T, Green S. N Engl J Med. 2020;382(4):100-110.",
    }
    ack_block = {
        "block_id": "a1",
        "page": 20,
        "role": "backmatter_body",
        "zone": "tail_nonref_hold_zone",
        "layout_region": "tail_candidate",
        "text": "Acknowledgements We thank the patients and families.",
    }

    ref_score = score_reference_corridor_membership(ref_block)
    ack_score = score_reference_corridor_membership(ack_block)

    assert ref_score["accept_reference_membership"] is True
    assert ack_score["accept_reference_membership"] is False
    assert ack_score["non_ref_intrusion_score"] > ref_score["non_ref_intrusion_score"]


def test_reference_hold_does_not_promote_final_reference_membership() -> None:
    from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts

    blocks = [
        {"block_id": "x1", "role": "backmatter_body", "zone": "tail_nonref_hold_zone", "text": "Data availability statement."},
    ]
    zone = build_verified_reference_zone_from_artifacts(blocks, {"region_bus": {"reference_zone_ids": set()}})
    assert zone.get("status") != "ACCEPT"
```

- [ ] **Step 2: Run the corridor tests to verify they fail**

Run: `python -m pytest tests/test_ocr_document.py -k "reference_corridor_keeps_reference_like_blocks or reference_hold_does_not_promote" -v --tb=short`

Expected: FAIL with missing function or stale behavior.

- [ ] **Step 3: Implement practical corridor scoring in `ocr_document.py`**

Add near reference-zone helpers in `paperforge/worker/ocr_document.py`:

```python
def score_reference_corridor_membership(block: dict) -> dict:
    from paperforge.worker.ocr_reference_signals import score_reference_entry

    text = str(block.get("text") or block.get("block_content") or "").strip()
    role = str(block.get("role") or "")
    layout_region = str(block.get("layout_region") or "")
    style = score_reference_entry(text)
    ref_membership_score = 0.0
    if role in {"reference_heading", "reference_item"}:
        ref_membership_score += 0.6
    if layout_region == "reference_candidate":
        ref_membership_score += 0.2
    ref_membership_score += float(style.get("confidence") or 0.0) * 0.3

    intrusion = 0.0
    lower = text.lower()
    if role.startswith("backmatter"):
        intrusion += 0.4
    if any(token in lower for token in ("acknowledgements", "funding", "conflict of interest", "data availability")):
        intrusion += 0.8
    if str(block.get("layout_region") or "") in {"body_flow", "display_zone", "side_insert"} and role not in {"reference_heading", "reference_item"}:
        intrusion += 0.3
    return {
        "ref_membership_score": ref_membership_score,
        "non_ref_intrusion_score": intrusion,
        "reference_style_family": style["family"],
        "reference_style_confidence": style["confidence"],
        "accept_reference_membership": ref_membership_score >= 0.55 and intrusion < 0.5,
    }
```

- [ ] **Step 4: Clamp HOLD so it cannot become accepted reference membership**

In `paperforge/worker/ocr_structural_gate.py`, after verified-zone construction, ensure candidate-only states stay non-accepted:

```python
    if zone.get("status") == "HOLD":
        zone["accepted_block_ids"] = []
        zone["reference_item_count"] = 0
```

If those exact fields do not exist in the current structure, apply the same rule to the nearest accepted-membership fields already present.

- [ ] **Step 5: Re-run the targeted tests until green**

Run: `python -m pytest tests/test_ocr_document.py -k "reference_corridor_keeps_reference_like_blocks or reference_hold_does_not_promote" -v --tb=short`

Expected: PASS.

---

### Task 4: Add Bridge-Aware Display Clusters For Figures

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write the failing figure bridge test**

Append to `tests/test_ocr_figures.py`:

```python
def test_display_cluster_keeps_empty_bridge_between_asset_and_caption() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"page": 9, "block_id": "asset_1", "role": "figure_asset", "bbox": [100, 100, 520, 360], "text": "", "layout_region": "display_zone"},
        {"page": 9, "block_id": "gap_1", "role": "unknown_structural", "bbox": [530, 110, 900, 360], "text": "", "layout_region": "display_zone", "bridge_eligible": True},
        {"page": 9, "block_id": "cap_1", "role": "figure_caption", "bbox": [120, 380, 880, 430], "text": "Figure 2. Multi-panel reconstruction.", "layout_region": "display_zone"},
    ]

    inventory = build_figure_inventory(structured_blocks)
    matched = inventory["matched_figures"][0]
    assert matched["asset_block_ids"] == ["asset_1"]
    assert matched.get("bridge_block_ids") == ["gap_1"]
```

- [ ] **Step 2: Run the targeted figure test to verify it fails**

Run: `python -m pytest tests/test_ocr_figures.py -k "empty_bridge_between_asset_and_caption" -v --tb=short`

Expected: FAIL because bridge block ids are not carried yet.

- [ ] **Step 3: Implement bridge-aware candidate collection**

In `paperforge/worker/ocr_figures.py`, when gathering display candidates, add a helper:

```python
def _collect_bridge_blocks(structured_blocks: list[dict], page: int) -> list[dict]:
    bridges: list[dict] = []
    for block in structured_blocks:
        if int(block.get("page", 0) or 0) != page:
            continue
        if not block.get("bridge_eligible"):
            continue
        if str(block.get("layout_region") or "") != "display_zone":
            continue
        bridges.append(block)
    return bridges
```

Then when a matched figure is emitted, carry any locally relevant bridge ids into the record:

```python
        local_bridges = _collect_bridge_blocks(structured_blocks, caption_page)
        bridge_ids = [str(b.get("block_id") or "") for b in local_bridges if b.get("block_id")]
        match_record["bridge_block_ids"] = bridge_ids
```

- [ ] **Step 4: Re-run the targeted figure test until green**

Run: `python -m pytest tests/test_ocr_figures.py -k "empty_bridge_between_asset_and_caption" -v --tb=short`

Expected: PASS.

---

### Task 5: Reuse Bridge-Aware Display Facts For Tables

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Test: `tests/test_ocr_tables.py`

- [ ] **Step 1: Write the failing sparse-table bridge test**

Append to `tests/test_ocr_tables.py`:

```python
def test_table_inventory_keeps_bridge_gap_inside_sparse_display_cluster() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 10, "block_id": "table_asset", "role": "table_asset", "raw_label": "table", "bbox": [100, 120, 620, 420], "text": "", "layout_region": "display_zone"},
        {"page": 10, "block_id": "gap_block", "role": "unknown_structural", "bbox": [640, 130, 930, 420], "text": "", "layout_region": "display_zone", "bridge_eligible": True},
        {"page": 10, "block_id": "table_caption", "role": "table_caption", "bbox": [120, 450, 900, 490], "text": "Table 1. Sparse reconstruction.", "layout_region": "display_zone"},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]
    assert table["asset_block_id"] == "table_asset"
    assert table.get("bridge_block_ids") == ["gap_block"]
```

- [ ] **Step 2: Run the targeted table test to verify it fails**

Run: `python -m pytest tests/test_ocr_tables.py -k "sparse_display_cluster" -v --tb=short`

Expected: FAIL because bridge block ids are not emitted.

- [ ] **Step 3: Emit bridge block ids from table inventory**

In `paperforge/worker/ocr_tables.py`, when a table asset is matched, add:

```python
        bridge_block_ids = [
            str(block.get("block_id") or "")
            for block in structured_blocks
            if int(block.get("page", 0) or 0) == int(caption_page or 0)
            and block.get("bridge_eligible")
            and str(block.get("layout_region") or "") == "display_zone"
            and block.get("block_id")
        ]
```

Then include:

```python
                "bridge_block_ids": bridge_block_ids,
```

- [ ] **Step 4: Re-run the targeted table test until green**

Run: `python -m pytest tests/test_ocr_tables.py -k "sparse_display_cluster" -v --tb=short`

Expected: PASS.

---

### Task 6: Add Local PDF Text Fallback For Hard Reference Entry Repair

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_pdf_text_fallback.py`

- [ ] **Step 1: Write the failing local-fallback boundary test**

Append to `tests/test_ocr_pdf_text_fallback.py`:

```python
def test_local_reference_pdf_fallback_repairs_only_local_candidate_text() -> None:
    from paperforge.worker.ocr_document import repair_reference_entry_from_pdf_text

    block_run = [
        {"block_id": "r1", "page": 14, "bbox": [620, 900, 1100, 950], "text": "Brown T, Green S."},
        {"block_id": "r2", "page": 14, "bbox": [620, 952, 1100, 1000], "text": "N Engl J M"},
    ]
    page_text = "Body text ... Brown T, Green S. N Engl J Med. 2020;382(4):100-110. More body text"

    repaired = repair_reference_entry_from_pdf_text(block_run, page_text)
    assert "N Engl J Med" in repaired
    assert repaired.startswith("Brown T, Green S.")
```

- [ ] **Step 2: Run the fallback test to verify it fails**

Run: `python -m pytest tests/test_ocr_pdf_text_fallback.py -k "local_reference_pdf_fallback" -v --tb=short`

Expected: FAIL with missing function.

- [ ] **Step 3: Implement a strict local text-repair helper**

Add to `paperforge/worker/ocr_document.py`:

```python
def repair_reference_entry_from_pdf_text(block_run: list[dict], page_text: str) -> str:
    seed = " ".join(str(block.get("text") or "").strip() for block in block_run if str(block.get("text") or "").strip())
    seed = re.sub(r"\s+", " ", seed).strip()
    if not seed:
        return ""
    if seed in page_text:
        return seed
    parts = [part for part in seed.split() if len(part) > 2]
    if not parts:
        return seed
    first = parts[0]
    idx = page_text.find(first)
    if idx < 0:
        return seed
    window = page_text[idx: idx + 300]
    return window.strip()
```

- [ ] **Step 4: Re-run the fallback test until green**

Run: `python -m pytest tests/test_ocr_pdf_text_fallback.py -k "local_reference_pdf_fallback" -v --tb=short`

Expected: PASS.

---

### Task 7: Protect Untouched-Paper Behavior And Record The Slice

**Files:**
- Modify: `tests/test_ocr_real_paper_regressions.py`
- Update: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Add real-paper regressions for the two untouched audit keys**

Append to `tests/test_ocr_real_paper_regressions.py`:

```python
def test_kix7skxq_reference_zone_does_not_absorb_acknowledgements(tmp_path: Path) -> None:
    result = replay_production_pipeline("KIX7SKXQ", tmp_path)
    blocks = result["structured_blocks"]
    bad = [
        b for b in blocks
        if b.get("zone") == "reference_zone"
        and "acknowledgements" in str(b.get("text") or "").lower()
    ]
    assert bad == []


def test_gtrpmm56_reference_hold_does_not_create_accepted_reference_zone(tmp_path: Path) -> None:
    result = replay_production_pipeline("GTRPMM56", tmp_path)
    doc = result.get("document_structure") or {}
    ref_zone = doc.get("reference_zone") or {}
    if ref_zone.get("status") == "HOLD":
        assert ref_zone.get("reference_item_count", 0) == 0
```

- [ ] **Step 2: Run the focused untouched-paper regressions**

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "kix7skxq_reference_zone_does_not_absorb_acknowledgements or gtrpmm56_reference_hold_does_not_create_accepted_reference_zone" -v --tb=short`

Expected: PASS.

- [ ] **Step 3: Update `PROJECT-MANAGEMENT.md` with the hardening slice**

Add a new entry in the usual format. Include:

```md
### 0.X Reference Zone And Ownership Hardening (2026-06-20)

Problem:
- untouched truth-audit papers still showed reference intrusion and ownership fragmentation on irregular layouts.

Root cause:
- page continuity facts were too weakly shared across reference and ownership consumers.

Fix:
- added shared layout facts,
- hardened practical reference corridor containment,
- introduced journal-abbreviation-backed reference-style support,
- added bridge-aware display continuity for figure/table ownership,
- limited PDF text fallback to local reference-entry repair.

Result:
- reference handling is more containment-oriented on mixed pages,
- ownership tolerates bridgeable empty gaps without reopening page swallow.

Test status:
- targeted OCR unit tests and untouched-paper regressions pass.
```

- [ ] **Step 4: Run the focused verification bundle**

Run: `python -m pytest tests/test_ocr_document.py tests/test_ocr_layout_zones.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_pdf_text_fallback.py tests/test_ocr_real_paper_regressions.py -q`

Expected: PASS with no new failures in the touched areas.

---

## Self-Review

### Spec coverage

- Shared layout-facts layer: covered by Task 1.
- Practical reference corridor containment: covered by Tasks 2-3.
- Journal-abbreviation support: covered by Task 2.
- Local entry reconstruction hook: partially covered by Task 3 and local repair in Task 6.
- Local PDF fallback boundaries: covered by Task 6.
- Cluster-first ownership with bridge-aware continuity: covered by Tasks 4-5.
- Validation on untouched papers: covered by Task 7.

### Placeholder scan

- No `TBD`, `TODO`, or deferred implementation placeholders remain in the task steps.
- The only adaptive wording is in Task 3 Step 4 where the exact accepted-membership field name may differ in the current gate structure; the step explicitly constrains the behavior to the nearest existing accepted-membership fields.

### Type consistency

- Shared layout field names are consistent across tasks: `reading_band_id`, `display_cluster_candidate_id`, `layout_region`, `boundary_before`, `boundary_after`, `bridge_eligible`.
- Reference scoring contract names are consistent across tasks: `ref_membership_score`, `non_ref_intrusion_score`, `reference_style_family`, `reference_style_confidence`.
- Ownership bridge contract name is consistent across tasks: `bridge_block_ids`.
