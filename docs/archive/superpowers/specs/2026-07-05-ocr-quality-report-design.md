# OCR Quality Report + Readiness Policy — Design Spec

> **Date:** 2026-07-05
> **Status:** Draft (Layer 2 design session), revised
> **Domain model:** `CONTEXT.md` (OCR Quality Report section)
> **Previous layer:** PR 1–4 (architecture hardening) — merged to `master`

---

## Architecture

```
build_ocr_health() [LEGACY — preserved]
    │
    ▼  ocr_health.json
    │
build_quality_indicators()     ← PR A (new)
    │
    ▼  quality_indicators (five normalized dimensions)
    │
evaluate_readiness(policy)     ← PR B (new)
    │
    ├─► user_readiness (green|yellow|red + score)
    └─► recommended_use (per-use-case gate)
    │
    ▼  ocr_quality_report.json

human feedback sidecar         ← PR C (new)
    ▼  ocr_quality_feedback.json
```

### Boundary rules

- `build_ocr_health()` is **preserved unchanged** — raw diagnostics, legacy compatibility surface.
- `ocr_quality.py` is a **new module**. It consumes `ocr_health.json` (or in-memory `health` dict) as one input, alongside `figure_inventory`, `table_inventory`, `structured_blocks`, `resolved_metadata`, `reader_payload`, and an optional `run_integrity` dict.
- `ocr_quality_report.json` is written **separately from** `ocr_health.json`. Never merge the two.
- Readiness policy is read from a **YAML file** (default in-repo, override in user config dir). Never hardcoded in Python.
- Human feedback is a **sidecar file**, never part of pipeline output.

---

## Field resolution precedence

This is critical for correct implementation. `build_quality_indicators()` accepts multiple optional inputs. When multiple sources provide the same signal, use this precedence:

1. **Direct inventory fields** (for figure/table signals):
   `figure_inventory["matched_figures"]` → `health.get("matched_figure_count_v2")`
   `figure_inventory["unmatched_assets"]` → `health.get("media_without_caption_count")`
   `figure_inventory["unmatched_legends"]` → `health.get("caption_without_media_count")`

2. **structured_blocks direct computation** (for structural signals):
   `sum(1 for b in structured_blocks if b["role"]=="reference_item")` → `health.get("reference_item_count")`

3. **resolved_metadata** (for metadata signals) — health does NOT have a metadata source, so there is no fallback chain.

4. **health dict** is the **compatibility source**, not the sole source of truth. When a higher-priority input is available (e.g., `figure_inventory` was passed), prefer it over health aggregates.

```python
# Example: figure_match_count resolution
figure_match_count = (
    len(figure_inventory.get("matched_figures", []))
    if figure_inventory is not None
    else health.get("matched_figure_count_v2", 0)
)
```

---

## PR A: Quality Indicators

### Module

`paperforge/worker/ocr_quality.py` — new file.

### Entrypoint

```python
def build_quality_indicators(
    *,
    health: dict,
    figure_inventory: dict | None = None,
    table_inventory: dict | None = None,
    structured_blocks: list[dict] | None = None,
    resolved_metadata: dict | None = None,
    reader_payload: dict | None = None,
    run_integrity: dict | None = None,
) -> dict:
```

Pure function. No file I/O. Deterministic given the same inputs.

`run_integrity` is an optional dict provided by the caller:
```python
run_integrity = {
    "result_hash": "...",
    "fulltext_hash": "...",
    "output_fulltext_chars": 12345,
    "artifact_presence": {"blocks_raw": True, "figure_inventory": True, ...},
}
```

If `run_integrity` is not provided, hard-red rules that depend on it are skipped (their `developer_diagnostics.run_integrity` fields will be `None`).

### Output structure

```python
{
    "schema_version": "ocr_quality_v1",

    "quality_indicators": {
        "rendered_text_integrity": Indicator,
        "body_reference_structure": Indicator,
        "figure_table_integrity": Indicator,
        "metadata_frontmatter_quality": Indicator,
        "confidence_and_fallbacks": Indicator,
    },

    "developer_diagnostics": {
        "run_integrity": run_integrity or {},
        "anchor_summary": health.get("anchor_summary", {}),
        "zone_summary": health.get("zone_summary", {}),
        "decision_summary": {...},
        "raw_health_keys": list(health.keys()),
    }
}
```

### Indicator shape

```python
Indicator = {
    "status": "green" | "yellow" | "red" | "unknown",
    "applicability": "applicable" | "not_applicable" | "unknown",
    "signals": {...},        # raw signals that produced this status
    "evidence": [...],       # human-readable reasons
}
```

**`applicability`** is new — it distinguishes "this metric is good" from "this metric doesn't apply". For example, `figure_table_integrity` is `not_applicable` when a paper has no figures or tables. PR B's policy gates reference this field rather than guessing from evidence text.

**Status semantics:**
- `green` = signal is within expected range
- `yellow` = signal has minor issues (non-zero gaps, partial coverage)
- `red` = signal has severe issues (critical)
- `unknown` = signal could not be computed

Indicator status is **signal severity**, not user readiness. Policy evaluator decides whether a red indicator means the whole paper is red.

---

### `rendered_text_integrity`

**Purpose:** Is the rendered body text complete and readable?

**Raw signals consumed:**

| Source field | Type | Notes |
|-------------|------|-------|
| `health.rendered_text_gap_count` | int | Gaps between PDF text and rendered markdown |
| `health.rendered_text_gap_examples` | list[str] | First 3 examples |
| `health.text_completeness_summary` | dict | e.g. `{"all_complete": 10, "partial": 2}` |
| `health.page_text_coverage` | dict | Per-page coverage metrics |
| `health.body_spine_quality` | str | `consistent` / `partial` / `weak` |

**Normalization:**

```python
def _normalize_rendered_text_integrity(health: dict) -> Indicator:
    gap_count = health.get("rendered_text_gap_count", 0)
    body_spine = health.get("body_spine_quality", "weak")

    # Red: large number of text gaps (obvious failure)
    if gap_count > 10:
        return Indicator(
            status="red", applicability="applicable",
            signals={"rendered_text_gap_count": gap_count},
            evidence=["Large number of text gaps between OCR and PDF"],
        )

    # Yellow: moderate gaps or weak spine
    if gap_count > 3:
        return Indicator(
            status="yellow", applicability="applicable",
            signals={"rendered_text_gap_count": gap_count},
            evidence=[f"{gap_count} text gaps detected"],
        )
    if body_spine == "weak":
        return Indicator(
            status="yellow", applicability="applicable",
            signals={"body_spine_quality": body_spine},
            evidence=["Body spine quality is weak"],
        )

    # Green: clean
    return Indicator(
        status="green", applicability="applicable",
        signals={"rendered_text_gap_count": gap_count, "body_spine_quality": body_spine},
        evidence=[],
    )
```

---

### `body_reference_structure`

**Purpose:** Is the body/reference/tail flow structurally sound?

**Raw signals consumed:**

| Source field | Type | Notes |
|-------------|------|-------|
| `health.body_spine_quality` | str | |
| `health.layout_audit_status` | str | `pass` / `fail` / `unknown` |
| `health.layout_anomaly_count` | int | |
| `health.references_found` | bool | |
| `health.section_heading_count` | int | |
| `health.zone_summary` | dict | Per-zone status |
| `structured_blocks` (preferred) or `health` | int | `reference_item_count` — computed from blocks when available |
| `health.page_count` | int | Context for profile detection |

**`health_profile` correction:** The existing `build_ocr_health()` writes `health_profile` (not `_health_profile`), with values `"short_form"` or `"standard"` (not `"standard_paper"`).

```python
def _normalize_body_reference_structure(
    health: dict,
    structured_blocks: list[dict] | None = None,
) -> Indicator:
    layout_status = health.get("layout_audit_status", "unknown")
    anomaly_count = health.get("layout_anomaly_count", 0)
    body_spine = health.get("body_spine_quality", "weak")
    ref_found = health.get("references_found", False)
    heading_count = health.get("section_heading_count", 0)
    # Use health_profile as written by build_ocr_health()
    profile = health.get("health_profile", "standard")

    # Prefer structured_blocks for reference_item_count when available
    reference_item_count = (
        sum(1 for b in (structured_blocks or []) if b.get("role") == "reference_item")
        if structured_blocks is not None
        else health.get("reference_item_count", 0)
    )

    evidence = []

    # Standard paper: missing references or no headings is structural
    if profile == "standard":
        if not ref_found and heading_count < 2:
            return Indicator(
                status="red", applicability="applicable",
                signals={"references_found": False, "section_heading_count": heading_count},
                evidence=["No references found and minimal section headings in standard paper"],
            )

    # Red: layout audit fails + body weak
    if layout_status == "fail" and body_spine == "weak":
        return Indicator(
            status="red", applicability="applicable",
            signals={"layout_audit_status": layout_status, "body_spine_quality": body_spine},
            evidence=["Layout audit failed and body spine is weak"],
        )

    # Yellow
    if anomaly_count > 0:
        evidence.append(f"{anomaly_count} layout anomalies")
    if body_spine == "partial":
        evidence.append("Body spine is partial")
    if evidence:
        return Indicator(
            status="yellow", applicability="applicable",
            signals={
                "layout_anomaly_count": anomaly_count,
                "body_spine_quality": body_spine,
                "reference_item_count": reference_item_count,
            },
            evidence=evidence,
        )

    return Indicator(
        status="green", applicability="applicable",
        signals={
            "layout_anomaly_count": anomaly_count,
            "body_spine_quality": body_spine,
            "references_found": ref_found,
            "reference_item_count": reference_item_count,
        },
        evidence=[],
    )
```

---

### `figure_table_integrity`

**Purpose:** Are figures and tables usable for reference and reasoning?

**Raw signals consumed:**

*Preferred:* direct `figure_inventory` / `table_inventory` fields.
*Fallback:* health aggregate fields.

| Source | Field | Notes |
|--------|-------|-------|
| `figure_inventory.matched_figures` | list | Prefer this over `health.figure_asset_count` |
| `figure_inventory.unmatched_assets` | list | |
| `figure_inventory.unmatched_legends` | list | |
| `figure_inventory.unresolved_clusters` | list | |
| `figure_inventory.held_figures` | list | |
| `figure_inventory.figure_legend_completeness` | dict | Contains `total`/`accounted_for`/`gap_count` |
| `health.figure_caption_count` | int | |
| `health.figure_reader_coverage_ratio` | float | 0.0–1.0 |
| `health.matched_figure_count_v2` | int | Fallback when no inventory |
| `health.media_without_caption_count` | int | Fallback |
| `health.caption_without_media_count` | int | Fallback |
| `table_inventory.tables` | list | |
| `table_inventory.unmatched_captions` | list | |

**Critical:** Do NOT use `health.figure_asset_count` as a figure-evidence signal. In the existing health output, `figure_asset_count` is actually `len(figure_inventory["matched_figures"])` — it's a match count, not an asset count. Use direct inventory fields instead.

```python
def _normalize_figure_table_integrity(
    health: dict,
    figure_inventory: dict | None = None,
    table_inventory: dict | None = None,
) -> Indicator:
    # Prefer direct inventory fields
    if figure_inventory is not None:
        matched_count = len(figure_inventory.get("matched_figures", []))
        unmatched_asset_count = len(figure_inventory.get("unmatched_assets", []))
        unresolved_cluster_count = len(figure_inventory.get("unresolved_clusters", []))
        unmatched_legend_count = len(figure_inventory.get("unmatched_legends", []))
        held_count = len(figure_inventory.get("held_figures", []))
        completeness = figure_inventory.get("figure_legend_completeness", {})
        completeness_ratio = (
            completeness.get("accounted_for", 0) / max(completeness.get("total", 1), 1)
            if completeness.get("total", 0) > 0
            else 1.0
        )
        media_no_cap = unmatched_asset_count
        cap_no_media = unmatched_legend_count
    else:
        # Fallback: health aggregate fields
        matched_count = health.get("matched_figure_count_v2", 0)
        unmatched_asset_count = health.get("media_without_caption_count", 0)
        unresolved_cluster_count = health.get("unresolved_cluster_count", 0)
        unmatched_legend_count = health.get("caption_without_media_count", 0)
        held_count = health.get("held_figure_count", 0)
        completeness_ratio = health.get("figure_legend_completeness_ratio", 1.0)
        media_no_cap = unmatched_asset_count
        cap_no_media = unmatched_legend_count

    figure_caption_count = health.get("figure_caption_count", 0)
    reader_ratio = health.get("figure_reader_coverage_ratio", 1.0)

    # Table signals
    if table_inventory is not None:
        tables = table_inventory.get("tables", [])
        table_asset_count = sum(1 for t in tables if t.get("has_asset"))
        table_unmatched = len(table_inventory.get("unmatched_captions", []))
    else:
        table_asset_count = health.get("table_asset_count", 0)
        table_unmatched = 0

    # Determine if there is ANY figure/table evidence
    has_figure_evidence = (
        figure_caption_count > 0
        or matched_count > 0
        or unmatched_asset_count > 0
        or unresolved_cluster_count > 0
        or unmatched_legend_count > 0
    )
    has_table_evidence = table_asset_count > 0 or table_unmatched > 0

    if not has_figure_evidence and not has_table_evidence:
        return Indicator(
            status="green", applicability="not_applicable",
            signals={"has_figure_table_evidence": False},
            evidence=["No figure/table evidence detected"],
        )

    evidence = []

    # Red: evidence exists but no matches
    if has_figure_evidence and matched_count == 0 and figure_caption_count > 0:
        return Indicator(
            status="red", applicability="applicable",
            signals={"figure_caption_count": figure_caption_count, "matched_count": 0},
            evidence=[f"{figure_caption_count} captions but 0 matched figures"],
        )

    # Yellow: partial coverage
    if unresolved_cluster_count > 0:
        evidence.append(f"{unresolved_cluster_count} unresolved clusters")
    if completeness_ratio < 0.8:
        evidence.append(f"Legend completeness {completeness_ratio:.0%}")
    if reader_ratio < 0.8:
        evidence.append(f"Reader coverage {reader_ratio:.0%}")
    if media_no_cap > 0:
        evidence.append(f"{media_no_cap} assets without caption")
    if evidence:
        return Indicator(
            status="yellow", applicability="applicable",
            signals={
                "matched_count": matched_count,
                "unresolved_cluster_count": unresolved_cluster_count,
                "completeness_ratio": completeness_ratio,
                "reader_ratio": reader_ratio,
                "has_figure_table_evidence": True,
            },
            evidence=evidence,
        )

    return Indicator(
        status="green", applicability="applicable",
        signals={
            "matched_count": matched_count,
            "completeness_ratio": completeness_ratio,
            "reader_ratio": reader_ratio,
            "has_figure_table_evidence": True,
        },
        evidence=[],
    )
```

---

### `metadata_frontmatter_quality`

**Purpose:** Is title/authors/DOI/abstract metadata available?

**Raw signals consumed:**

| Source field | Type | Notes |
|-------------|------|-------|
| `resolved_metadata.title.value` | str | Empty = missing |
| `resolved_metadata.authors_display` | str | Empty = missing |
| `resolved_metadata.doi.value` | str | Empty = missing |
| `health.abstract_found` | bool | |

**Normalization:**

```python
def _normalize_metadata_frontmatter_quality(
    health: dict,
    resolved_metadata: dict | None = None,
) -> Indicator:
    meta = resolved_metadata or {}
    has_title = bool(meta.get("title", {}).get("value", ""))
    has_author = bool(meta.get("authors_display", ""))
    has_doi = bool(meta.get("doi", {}).get("value", ""))
    has_abstract = health.get("abstract_found", False)

    missing = []
    if not has_title:
        missing.append("title")
    if not has_author:
        missing.append("authors")
    if not has_doi:
        missing.append("DOI")
    if not has_abstract:
        missing.append("abstract")

    # Still green if only DOI missing (common in many papers)
    if len(missing) <= 1 and has_title:
        return Indicator(
            status="green", applicability="applicable",
            signals={"missing_fields": missing},
            evidence=[],
        )

    # Yellow: missing title or authors
    if not has_title or not has_author:
        return Indicator(
            status="yellow", applicability="applicable",
            signals={"missing_fields": missing},
            evidence=[f"Missing: {', '.join(missing)}"],
        )

    return Indicator(
        status="green", applicability="applicable",
        signals={"missing_fields": missing},
        evidence=[],
    )
```

---

### `confidence_and_fallbacks`

**Purpose:** Was degraded mode, heavy fallback, or low-confidence matching used?

**Raw signals consumed:**

| Source field | Type | Notes |
|-------------|------|-------|
| `health.degraded_mode_active` | bool | |
| `health.degraded_reasons` | list | |
| `health.warning_reasons` | list | |
| `health.hard_degraded_reasons` | list | |
| `health.low_confidence_matches` | int | |
| `health.ambiguous_match_count` | int | |
| `health.held_figure_count` | int | |
| `health.held_table_count` | int | |
| `health.span_coverage_quality` | str | |

**Normalization:**

```python
def _normalize_confidence_fallbacks(health: dict) -> Indicator:
    degraded = health.get("degraded_mode_active", False)
    span_quality = health.get("span_coverage_quality", "good")

    evidence = []
    if degraded:
        evidence.append("Degraded mode active")
    if span_quality not in ("good", "acceptable"):
        evidence.append(f"Span coverage: {span_quality}")

    # This dimension should not trigger red alone — it only downgrades green to yellow
    if degraded and span_quality in ("poor", "none"):
        return Indicator(
            status="yellow", applicability="applicable",
            signals={"degraded_mode_active": degraded, "span_coverage_quality": span_quality},
            evidence=evidence + ["Degraded mode + poor span coverage"],
        )

    if evidence:
        return Indicator(
            status="yellow", applicability="applicable",
            signals={"degraded_mode_active": degraded, "span_coverage_quality": span_quality},
            evidence=evidence,
        )

    return Indicator(
        status="green", applicability="applicable",
        signals={"degraded_mode_active": degraded, "span_coverage_quality": span_quality},
        evidence=[],
    )
```

---

## PR B: Readiness Policy Evaluator

### Design principle

Pipeline produces `quality_indicators` with no opinion (except basic signal severity). The policy evaluator applies a configurable YAML policy to produce `user_readiness` and `recommended_use`. This separation means:

- Policy thresholds can be tuned **without re-running OCR**.
- Multiple policies can be tested on the same `quality_indicators`.
- The policy file is the **single source of truth** for readiness decisions.

### Entrypoint

```python
def evaluate_readiness(
    quality_report_base: dict,
    policy: dict | None = None,
    *,
    policy_path: str | Path | None = None,
) -> dict:
    """Apply readiness policy to quality report.
    
    Args:
        quality_report_base: output of build_quality_indicators() (the full dict,
                            containing both quality_indicators and developer_diagnostics)
        policy: in-memory policy dict (mutually exclusive with policy_path)
        policy_path: path to YAML policy file (mutually exclusive with policy)
    
    Returns:
        dict with user_readiness + recommended_use
    """
    indicators = quality_report_base.get("quality_indicators", {})
    diagnostics = quality_report_base.get("developer_diagnostics", {})
    ...
```

### Policy loading and merge

1. Default policy is loaded from `paperforge/policies/ocr_readiness_v1.yaml`.
2. If `~/.paperforge/policies/ocr_readiness_v1.yaml` exists, its values **override** the defaults (shallow merge at top level — weights, hard_red, use_cases replaced per-key).
3. If `policy` dict is passed in-memory, it takes precedence over both file paths.

### Package-data requirement

Add to `pyproject.toml`:
```toml
[tool.setuptools.package-data]
paperforge = [
    ...,
    "policies/*.yaml",
]
```

### Policy YAML format

```yaml
schema_version: ocr_readiness_policy_v1

# --- Composite score weights (only for user_readiness.score) ---
weights:
  rendered_text_integrity: 0.35
  body_reference_structure: 0.25
  figure_table_integrity: 0.20
  metadata_frontmatter_quality: 0.10
  confidence_and_fallbacks: 0.10

# --- Hard-red rules: any match overrides composite score ---
hard_red:
  - rule: "rendered_text_gap_excessive"
    field: "quality_indicators.rendered_text_integrity.signals.rendered_text_gap_count"
    op: "gt"
    value: 10

  - rule: "body_weak_and_no_refs"
    condition:
      field_a: "quality_indicators.body_reference_structure.signals.body_spine_quality"
      op_a: "eq"
      value_a: "weak"
      field_b: "quality_indicators.body_reference_structure.signals.references_found"
      op_b: "eq"
      value_b: false

  - rule: "fulltext_too_short"
    field: "developer_diagnostics.run_integrity.output_fulltext_chars"
    op: "lt"
    value: 2000

# --- Use-case gates ---
use_cases:
  reading:
    gates:
      required:
        - indicator: "rendered_text_integrity"
          min_status: "yellow"
        - indicator: "body_reference_structure"
          min_status: "yellow"

  qa:
    gates:
      required:
        - indicator: "rendered_text_integrity"
          min_status: "yellow"
        - indicator: "body_reference_structure"
          min_status: "yellow"
      soft:
        - indicator: "metadata_frontmatter_quality"
          min_status: "yellow"  # advisory only

  figure_table_reasoning:
    if_no_figure_table_evidence: "not_applicable"
    gates:
      required:
        - indicator: "figure_table_integrity"
          min_status: "yellow"

  section_chunking:
    gates:
      required:
        - indicator: "body_reference_structure"
          min_status: "green"
        - indicator: "rendered_text_integrity"
          min_status: "yellow"
```

**Policy field path reference:**
- `quality_indicators.<dimension>.status` — indicator severity
- `quality_indicators.<dimension>.signals.<field>` — raw signal value
- `quality_indicators.<dimension>.applicability` — `applicable` | `not_applicable`
- `developer_diagnostics.run_integrity.<field>` — run-level metadata

### Scoring logic

```
score = sum(weight_i * status_score_i for i in 5 dimensions)

status_score:
  green  → 1.0
  yellow → 0.6
  red    → 0.2
  unknown → 0.5
  (not_applicable → excluded from weighted sum; weights renormalized)

If any hard_red rule matches:
  user_readiness.status = "red"
  score = min(score, 0.3)  # still compute score for granularity, but status overrides

If no hard_red and score >= 0.75:
  user_readiness.status = "green"
If no hard_red and score >= 0.40:
  user_readiness.status = "yellow"
Else:
  user_readiness.status = "red"
```

### Output structure

```python
{
    "user_readiness": {
        "status": "green" | "yellow" | "red",
        "score": 0.83,
        "policy_version": "ocr_readiness_policy_v1",
        "policy_path": "/path/to/policy.yaml",
        "basis": "policy_estimate",
        "primary_reasons": [...],
        "warnings": [...],
        "hard_red_triggers": [...],  # empty if none
    },

    "recommended_use": {
        "reading": UseCaseResult,
        "qa": UseCaseResult,
        "figure_table_reasoning": UseCaseResult,
        "section_chunking": UseCaseResult,
    }
}

UseCaseResult = {
    "status": "ok" | "caution" | "not_recommended" | "not_applicable",
    "gates": [...],    # gates that were evaluated
    "reasons": [...],  # why this status was assigned
}
```

---

## PR C: Human Feedback Sidecar

### Design principle

Human validation must be separate from pipeline output. It lives in a sidecar file that can be read/written by the dashboard (or CLI) without touching `ocr_health.json` or `ocr_quality_report.json`.

### Scope

PR C does the **sidecar API only** — no dashboard UI. The schema, read/write/append functions, and hash validation. Dashboard buttons belong to Layer 3 (Plugin UI polish).

### File location

Per-paper: `<paper_dir>/ocr_quality_feedback.json`
(same level as `ocr_health.json`, `ocr_quality_report.json`)

### Schema

```json
{
    "schema_version": "ocr_quality_feedback_v1",
    "paper_id": "key",
    "result_hash": "abc123",
    "fulltext_hash": "def456",
    "marks": [
        {
            "marked_by": "user|developer",
            "marked_at": "2026-07-05T12:00:00Z",
            "overall": "correct|usable_with_minor_issues|bad",
            "use_cases": {
                "reading": "ok|caution|bad",
                "qa": "ok|caution|bad",
                "figure_table_reasoning": "ok|caution|bad|not_applicable"
            },
            "issue_tags": [
                "missing_body_text",
                "wrong_reference_boundary",
                "figure_caption_mismatch",
                "table_missing",
                "metadata_missing",
                "heading_wrong_level"
            ],
            "notes": ""
        }
    ]
}
```

### Key rules

- `result_hash` and `fulltext_hash` are **required** — a mark is bound to a specific pipeline run.
- Multiple marks are allowed (same paper, different evaluators). Latest mark is authoritative for display; all marks are kept for calibration.
- Marks are **append-only** — never delete old marks.

### Stale detection

When the current pipeline run produces a different `result_hash` than the one stored in the feedback file, the feedback is **stale**. The human validation status is `"stale"` — the old mark is not discarded, but it no longer applies to the current output.

`human_validation.status` values: `"unreviewed" | "confirmed" | "disputed" | "stale"`

### Integration with quality_report

```python
{
    "user_readiness": {
        "status": "green",
        "score": 0.83,
        "basis": "policy_estimate",
        "human_validation": {
            "status": "unreviewed" | "confirmed" | "disputed" | "stale",
            "mark_count": 0,
            "latest_mark": null | {...},
            "feedback_path": ".../ocr_quality_feedback.json"
        }
    }
}
```

When `human_validation.status` is `confirmed` and `latest_mark.overall != user_readiness.status`, the dashboard should indicate a discrepancy.

---

## Acceptance Criteria

### PR A

| # | Check | Method |
|---|-------|--------|
| A1 | `build_quality_indicators()` returns all 5 indicators with status + signals + applicability | Unit test with minimal `health` dict |
| A2 | `rendered_text_integrity` red when gap_count > 10 | Unit test |
| A3 | `rendered_text_integrity` yellow when gap_count 4-10 | Unit test |
| A4 | `figure_table_integrity` green + `not_applicable` when no figure evidence | Unit test |
| A5 | `figure_table_integrity` red when captions exist but 0 matched | Unit test |
| A6 | `metadata_frontmatter_quality` yellow when title missing | Unit test |
| A7 | `build_ocr_health()` legacy output schema is untouched — assert `overall`, `needs_rebuild`, `structural_blockers`, `span_coverage_quality`, `degraded_mode_active`, `body_spine_quality`, `layout_audit_status`, `rendered_text_gap_count` still present | Legacy schema regression test |
| A8 | `body_reference_structure` reads `health_profile` not `_health_profile` | Unit test |
| A9 | All OCR tests still pass | `python -m pytest tests/test_ocr_*.py -v --tb=short` |

### PR B

| # | Check | Method |
|---|-------|--------|
| B1 | `evaluate_readiness()` with default policy produces status + score | Unit test |
| B2 | Hard-red rule overrides yellow/green | Unit test with crafted `quality_report_base` |
| B3 | Reading gate: yellow when `rendered_text_integrity` yellow | Unit test |
| B4 | `figure_table_reasoning`: `not_applicable` via `figure_table_integrity.applicability == "not_applicable"` | Unit test |
| B5 | Policy can be loaded from YAML | Unit test with temp YAML |
| B6 | Default policy ships with repo | File exists: `paperforge/policies/ocr_readiness_v1.yaml` |
| B7 | User policy override (merges with defaults) | Unit test with mock user config |

### PR C

| # | Check | Method |
|---|-------|--------|
| C1 | Read/write feedback file works | Unit test with temp dir |
| C2 | Schema validates `result_hash` required | Validation test |
| C3 | Multiple marks append, not overwrite | Unit test |
| C4 | Stale `result_hash` detected — status = `"stale"` | Unit test (current hash differs from feedback hash) |
| C5 | Feedback summary can be resolved for display without UI dependency | Unit test: `resolve_human_validation(feedback, current_result_hash)` returns correct status |

---

## Non-goals

- Do NOT rename `build_ocr_health()` or any existing health fields.
- Do NOT delete `overall` / `needs_rebuild` / `frontmatter_quality` from health output.
- Do NOT change `figure_inventory` internal field names.
- Do NOT merge `ocr_quality_report.json` into `ocr_health.json`.
- Do NOT hardcode weights in Python — policy file only.
- Do NOT mix human feedback into pipeline output.
- Do NOT implement dashboard UI changes in this layer (that's Layer 3).

## File changes summary

```
ADD paperforge/worker/ocr_quality.py          — PR A + B
ADD paperforge/policies/ocr_readiness_v1.yaml  — PR B
ADD tests/test_ocr_quality.py                 — PR A + B
ADD tests/test_ocr_quality_feedback.py         — PR C
MOD pyproject.toml                             — add policies/*.yaml to package-data
NEW <paper_dir>/ocr_quality_report.json        — PR A output
NEW <paper_dir>/ocr_quality_feedback.json      — PR C sidecar
```
