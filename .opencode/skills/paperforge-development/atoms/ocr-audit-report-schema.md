# OCR Audit Report Schema

Truth-first invariant:

- Do not start by authoring expectations.
- Determine truth from page visuals and artifacts first.
- Use reports to record truth and mismatches, not to normalize incorrect output.

External vault invariant:

- The OCR source root is outside the repo.
- The audit helper must not assume a repo-local literature vault.
- The caller must provide `--source-root` or set `PAPERFORGE_OCR_ROOT`.

## Required Output Files

Write outputs under `audit/<paper_key>/`.

Concrete example:

 - `audit/CAQNW9Q2/audit_report.md`
 - `audit/CAQNW9Q2/audit_report.json`
 - `audit/CAQNW9Q2/audit_scope.json`
 - `audit/CAQNW9Q2/block_review.jsonl`
 - `audit/CAQNW9Q2/coverage_check.json`
 - `audit/CAQNW9Q2/block_coverage_summary.json`
 - `audit/CAQNW9Q2/page_risk_summary.json`
 - `audit/CAQNW9Q2/reference_intrusion_candidates.json`
 - `audit/CAQNW9Q2/figure_table_ownership_summary.json`
 - `audit/CAQNW9Q2/fulltext_block_mapping_summary.json`
 - `audit/CAQNW9Q2/reference_span_audit.json`
 - `audit/CAQNW9Q2/annotated_pages/page_*_overview.png` — all-block overview with short numeric labels
 - `audit/CAQNW9Q2/annotated_pages/page_*_index.json` — per-page block-to-metadata mapping

## Primary Categories

- `frontmatter_error`
- `body_flow_error`
- `reference_span_error`
- `same_page_boundary_error`
- `backmatter_error`
- `object_ownership_error`
- `reading_order_error`
- `render_mapping_error`

## Meta Category

- `audit_truth_gap`

Use `audit_truth_gap` when the audit process fails to surface real block-level truth or when prior expectations drift away from visual truth.

## Severities

- `critical`
- `major`
- `minor`
- `cosmetic`

Severity tracks trust and downstream damage, not implementation effort.

## audit_report.json Example

```json
{
  "paper_key": "CAQNW9Q2",
  "mode": "high-risk",
  "artifact_fingerprint": {
    "result_json_hash": "...",
    "structured_blocks_hash": "...",
    "fulltext_hash": "...",
    "document_structure_hash": "..."
  },
  "reviewed_pages": [1, 7, 8],
  "reviewed_blocks": ["p1:b3", "p7:b12"],
  "findings": [
    {
      "category": "reference_span_error",
      "severity": "critical",
      "block_ids": ["p7:b12"],
      "truth": "block belongs outside reference span",
      "pipeline_behavior": "rendered inside accepted references",
      "root_cause_hypothesis": "same-page boundary inference overreach",
      "evidence": {
        "annotated_page": "annotated_pages/page_007.png",
        "artifact": "structure/document_structure.json"
      }
    }
  ]
}
```

## reference_span_audit.json Example

```json
{
  "reference_span": {
    "status": "ACCEPT",
    "span_id": "refspan_001",
    "start": {
      "page": 7,
      "column": 1,
      "y": 1032,
      "block_id": "p7:b12"
    },
    "end": {
      "page": 10,
      "column": 2,
      "y": 1398,
      "block_id": "p10:b48"
    },
    "ordered_block_ids": ["p7:b12", "p7:b13"],
    "inside_block_ids": ["p7:b12", "p7:b13"],
    "explicitly_outside_nearby_block_ids": ["p7:b10", "p7:b11"],
    "intrusion_candidates": []
  }
}
```

## Minimum Reporting Expectations

- `audit_report.md` summarizes reviewed scope, freshness status, findings, and repair vs residual recommendations.
- `audit_report.json` is the machine-readable source of findings.
- `audit_scope.json` defines which pages and blocks must be reviewed for the chosen mode.
- `block_review.jsonl` is the agent-written visual truth review log.
- `coverage_check.json` is written by `verify_review_coverage.py` and must fail when mandatory reviews are missing.
- `block_coverage_summary.json` tracks which blocks were reviewed and their review state.
- `page_risk_summary.json` records page scores and reasons.
- `reference_intrusion_candidates.json` records candidate reference contamination.
- `figure_table_ownership_summary.json` records caption/asset/object mismatches.
- `fulltext_block_mapping_summary.json` records source-to-render placement checks.
- `reference_span_audit.json` records accepted reference span boundaries and intrusion checks.
