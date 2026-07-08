# OCR Quality Report + Readiness Policy — Implementation Plan

> **Date:** 2026-07-05
> **Spec:** `docs/superpowers/specs/2026-07-05-ocr-quality-report-design.md`
> **Strategy:** 3 sequential PRs, dependency-ordered. PR B branches after PR A is merged (extends `ocr_quality.py`). PR C depends on neither except optional integration shape.

---

## PR A: Quality Indicators

**Branch:** `feat/ocr-quality-indicators`
**Risk:** Low-medium
**Files:** `paperforge/worker/ocr_quality.py` (new), `tests/test_ocr_quality.py` (new)

### Execution contracts

- `build_quality_indicators()` is a **pure function** — no I/O, no file writing.
- It accepts `run_integrity: dict | None = None` and preserves it under `developer_diagnostics.run_integrity`.
- `ocr_quality_report.json` is **not written** in PR A. In-memory dict only.
- The existing `build_ocr_health()` is **untouched** — not renamed, not modified.

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

Where `run_integrity` is an optional dict provided by the caller:
```python
{
    "result_hash": "...",
    "fulltext_hash": "...",
    "output_fulltext_chars": 12345,
    "artifact_presence": {...},
}
```

### Steps

1. **Create `paperforge/worker/ocr_quality.py`**
   - `_make_indicator()` helper factory (canonical dict shape: `status`, `applicability`, `signals`, `evidence`)
   - `build_quality_indicators()` entrypoint with `run_integrity` parameter

2. **Implement `_normalize_rendered_text_integrity()`**
   - Reads from `health` dict
   - Thresholds: gap_count > 10 → red, gap_count 4-10 → yellow, body_spine "weak" → yellow, else green

3. **Implement `_normalize_body_reference_structure()`**
   - Reads from `health` + optional `structured_blocks` (for `reference_item_count`)
   - Uses `health.get("health_profile", "standard")` — not `_health_profile`
   - Short-form papers exempt from heading/reference requirements

4. **Implement `_normalize_figure_table_integrity()`**
   - Prefers direct `figure_inventory` / `table_inventory` fields over health aggregates
   - Computes `has_figure_evidence` from multiple signals: caption count, matched count, unmatched assets, unresolved clusters, unmatched legends
   - Red condition: `has_figure_evidence` AND `matched_count == 0` AND at least one of: `cap_no_media > 0`, `media_no_cap > 0`, `unresolved > 0`, `reader_ratio < 1.0`
   - Returns `applicability="not_applicable"` when no figure/table evidence
   - Does **not** use `health.figure_asset_count` as evidence signal

5. **Implement `_normalize_metadata_frontmatter_quality()`**
   - Reads from `resolved_metadata` (preferred) + `health.abstract_found`
   - Only DOI missing → still green; title or authors missing → yellow

6. **Implement `_normalize_confidence_fallbacks()`**
   - Reads from `health`
   - Only downgrades green→yellow, never triggers red alone

7. **Assemble `build_quality_indicators()`**
   - Calls all 5 normalizers
   - `developer_diagnostics.run_integrity = dict(run_integrity or {})`
   - Returns `{"schema_version": "ocr_quality_v1", "quality_indicators": {...}, "developer_diagnostics": {...}}`

8. **Write 10 unit tests** in `tests/test_ocr_quality.py`
   - A1: All 5 indicators returned with correct shape (status + applicability + signals + evidence)
   - A2: rendered_text_integrity red (gap_count > 10)
   - A3: rendered_text_integrity yellow (gap_count 4-10)
   - A4: figure_table_integrity green + not_applicable (no figure evidence)
   - A5: figure_table_integrity red (captions + no matches + unmatched evidence)
   - A6: metadata_frontmatter_quality yellow (title missing)
   - A7: body_reference_structure reads `health_profile` not `_health_profile`
   - A8: figure_table_integrity prefers inventory over health aggregates
   - A9: run_integrity None → developer_diagnostics.run_integrity is empty
   - A10: run_integrity dict preserved under developer_diagnostics.run_integrity

9. **Verify**
   - `python -m pytest tests/test_ocr_quality.py -v --tb=short` — all 10 pass
   - `python -m pytest tests/test_ocr_health.py -v --tb=short` — legacy tests still pass

### Acceptance

| # | Check | Method |
|---|-------|--------|
| A1 | All 5 indicators returned with status + applicability | `pytest` |
| A2 | Gap count > 10 → red | `pytest` |
| A3 | Gap count 4-10 → yellow | `pytest` |
| A4 | No figure evidence → green + not_applicable | `pytest` |
| A5 | Captions + 0 matched + unmatched evidence → red | `pytest` |
| A6 | Title missing → yellow | `pytest` |
| A7 | Uses `health_profile` not `_health_profile` | `pytest` |
| A8 | Prefers inventory over health aggregate | `pytest` |
| A9 | run_integrity=None → empty diagnostics | `pytest` |
| A10 | run_integrity preserved | `pytest` |
| A11 | Legacy `build_ocr_health()` still has `overall`, `needs_rebuild`, `structural_blockers`, `span_coverage_quality`, `degraded_mode_active`, `body_spine_quality`, `layout_audit_status`, `rendered_text_gap_count` | `pytest` regression |

---

## PR B: Readiness Policy Evaluator

**Branch:** `feat/ocr-readiness-policy` (after PR A is merged to master)
**Risk:** Low-medium
**Files:** extends `paperforge/worker/ocr_quality.py`, adds `paperforge/policies/ocr_readiness_v1.yaml` (new), extends `tests/test_ocr_quality.py`, modifies `pyproject.toml`

### Execution contracts

- `evaluate_readiness()` accepts the **full output** of `build_quality_indicators()` (not just the `quality_indicators` sub-dict). The parameter name is `quality_report_base`.
- Policy weights and thresholds live in YAML. **Not hardcoded in Python.**
- `load_readiness_policy()` uses **`importlib.resources.files()`** — not `pkg_resources`.
- `ocr_quality_report.json` is **not written** in PR B. In-memory dict only.

### Steps

1. **Create `paperforge/policies/ocr_readiness_v1.yaml`**
   - Schema version, weights, hard-red rules, use-case gates as defined in spec
   - Field paths reference `quality_indicators.*` and `developer_diagnostics.*`

2. **Implement `load_readiness_policy()`**
   ```python
   def load_readiness_policy(
       policy: dict | None = None,
       *,
       policy_path: str | Path | None = None,
   ) -> dict:
       """Load and merge readiness policy.

       Args:
           policy: in-memory policy dict (mutually exclusive with policy_path)
           policy_path: path to explicit YAML file (mutually exclusive with policy)

       Returns:
           merged policy dict

       Resolution order:
           1. Default: paperforge/policies/ocr_readiness_v1.yaml (via importlib.resources)
           2. If policy_path is provided: deep-merge that file over default.
              Skip user override.
           3. Else if ~/.paperforge/policies/ocr_readiness_v1.yaml exists:
              deep-merge user override over default.
           4. If in-memory policy is provided: deep-merge over whatever was loaded.
              Skip user override and explicit file loading.

       Merge rules:
           - dicts: recursive deep-merge
           - lists: replace (not append)
           - scalars: override
       """
       from importlib.resources import files as pkg_files
       ...
   ```
   - policy and policy_path are mutually exclusive → raise `ValueError` if both provided
   - Default policy loaded via `importlib.resources.files("paperforge") / "policies/ocr_readiness_v1.yaml"`

3. **Implement `_resolve_field(data: dict, path: str)` helper**
   - Resolves dotted field path against a nested dict
   - Example: `"quality_indicators.rendered_text_integrity.signals.rendered_text_gap_count"`
   - Returns the value at that path, or `None`

4. **Implement `_check_hard_red(policy, indicators, diagnostics)`**
   - Iterates `policy["hard_red"]`
   - Single-field rules: resolves field path, applies op (`gt`/`lt`/`eq`), collects triggered rules
   - Multi-field `condition` rules: evaluates both sides and logical AND

5. **Implement `_evaluate_gate()`**
   - Status rank order: `red=0`, `unknown=1`, `yellow=2`, `green=3`
   - Gate passes if `rank(status) >= rank(min_status)`
   - **`unknown` fails required gates** (rank=1 is below yellow=2)
   - Soft gates are advisory only (do not fail the use case)

6. **Implement `_compute_use_case()`**
   - Applies required gates + soft gates
   - Respects `if_no_figure_table_evidence: "not_applicable"` by checking `quality_indicators.figure_table_integrity.applicability`

7. **Implement `evaluate_readiness()`**
   ```python
   def evaluate_readiness(
       quality_report_base: dict,
       policy: dict | None = None,
       *,
       policy_path: str | Path | None = None,
   ) -> dict:
   ```
   - Loads policy via `load_readiness_policy()`
   - Checks hard-red (early return with red status if any triggered)
   - Computes weighted score:
     ```
     score = sum(weight_i * status_score_i for i in 5 indicators)
     status_score: green=1.0, yellow=0.6, red=0.2, unknown=0.5
     not_applicable → excluded from sum, weights renormalized
     ```
   - Determines status: `≥0.75` green, `≥0.40` yellow, else red
   - Evaluates all 4 use cases
   - Returns `{"user_readiness": {...}, "recommended_use": {...}}`

8. **Modify `pyproject.toml`**
   ```toml
   [tool.setuptools.package-data]
   paperforge = [
       ...
       "policies/*.yaml",
   ]
   ```

9. **Write 7 tests**
   - B1: evaluate_readiness with default policy returns status + score
   - B2: Hard-red rule overrides green/yellow
   - B3: Reading gate yellow when rendered_text_integrity yellow
   - B4: figure_table_reasoning not_applicable via applicability field
   - B5: Policy loaded from temp YAML
   - B6: Default policy file exists in package
   - B7: User override merges correctly (deep-merge + list replace)

10. **Verify**
    - `python -m pytest tests/test_ocr_quality.py -v --tb=short` — all 17 tests (A10 + B7) pass

### Acceptance

| # | Check | Method |
|---|-------|--------|
| B1 | evaluate_readiness with default policy produces status + score | `pytest` |
| B2 | Hard-red overrides green/yellow | `pytest` |
| B3 | Reading gate responds to indicator status | `pytest` |
| B4 | figure_table_reasoning uses applicability field | `pytest` |
| B5 | YAML loading works | `pytest` |
| B6 | Default policy ships with repo | File check |
| B7 | User policy override merges correctly | `pytest` |

---

## PR C: Human Feedback Sidecar

**Branch:** `feat/ocr-quality-feedback`
**Risk:** Low
**Files:** `paperforge/worker/ocr_quality_feedback.py` (new), `tests/test_ocr_quality_feedback.py` (new)

**Scope boundary:** PR C does **sidecar API only** — no dashboard UI. Dashboard buttons belong to Layer 3.

### Execution contracts

- Hashes are stored **per mark**, not just at root. Each mark carries its own `result_hash` and `fulltext_hash`.
- `append_mark()` injects hashes automatically — caller does not manually set them.
- Stale detection compares `latest_mark.result_hash` with `current_result_hash`.
- No `ocr_quality_report.json` is written. Integration deferred to Layer 3.

### Steps

1. **Create `paperforge/worker/ocr_quality_feedback.py`**

2. **Implement `read_feedback(path)`**
   - Reads `ocr_quality_feedback.json`
   - Returns `None` if file doesn't exist (not an error)

3. **Implement `write_feedback(path, feedback)`**
   - Atomically writes via temp file + rename
   - Validates `marks` list is not empty

4. **Implement `append_mark()`**
   ```python
   def append_mark(
       path: Path,
       mark: dict,
       *,
       current_result_hash: str,
       current_fulltext_hash: str,
   ) -> dict:
       """Append a human validation mark to the feedback file.

       Hashes are injected automatically from current_result_hash/current_fulltext_hash.
       Old marks with different hashes are preserved for audit.
       """
   ```
   - Loads existing feedback (or creates new skeleton)
   - Injects hashes into the mark: `mark["result_hash"] = current_result_hash`, same for fulltext
   - Appends to `marks` list
   - Writes back

5. **Implement `resolve_human_validation(feedback, current_result_hash)`**
   - Returns `human_validation` dict:
     - `status`: `"unreviewed"` (no marks) / `"confirmed"` (latest overall is correct/usable) / `"disputed"` (latest is bad) / `"stale"` (`latest_mark.result_hash != current_result_hash`)
     - `mark_count`, `latest_mark`, `feedback_path`

6. **Write 5 tests**
   - C1: write + read roundtrip
   - C2: missing hash raises validation error (append without hashes)
   - C3: append_mark adds, does not replace (marks list grows)
   - C4: stale hash → status = "stale" (current hash differs from latest mark)
   - C5: resolve_human_validation returns correct status without UI

7. **Verify**
   - `python -m pytest tests/test_ocr_quality_feedback.py -v --tb=short` — all 5 pass
   - `python -m pytest tests/test_ocr_*.py -v --tb=short` — no regressions

### Acceptance

| # | Check | Method |
|---|-------|--------|
| C1 | Write + read roundtrip | `pytest` |
| C2 | Hashes injected by append_mark | `pytest` |
| C3 | append_mark adds, does not overwrite | `pytest` |
| C4 | Stale hash → status stale | `pytest` |
| C5 | resolve_human_validation works without UI | `pytest` |

---

## Branch Strategy

```bash
# PR A — creates ocr_quality.py
git checkout master -b feat/ocr-quality-indicators
# ... implement, test, commit, push, PR → merge

# PR B — extends ocr_quality.py; wait for PR A merged to master
git checkout master
git pull origin master
git checkout -b feat/ocr-readiness-policy
# ... implement, test, commit, push, PR → merge

# PR C — independent; can start from master after PR A/B or in parallel with B
git checkout master
git pull origin master
git checkout -b feat/ocr-quality-feedback
# ... implement, test, commit, push, PR → merge
```

PR B is **not** file-independent — it extends `ocr_quality.py` created by PR A. Must branch after PR A is merged.

PR C is independent of PR A/B except for the integration shape (the `human_validation` sub-dict inside `user_readiness`). Can be done in parallel with PR B if desired, or after both A/B merged.

## File Writing — Deferred

`ocr_quality_report.json` is **not written** in this layer. The in-memory `build_quality_indicators()` / `evaluate_readiness()` outputs are the PR A/B deliverable. File writing and pipeline integration belong to a future step (Layer 3 integration or dedicated write module).

## Verification

After all 3 PRs merged:

```bash
# PR A + B tests
python -m pytest tests/test_ocr_quality.py -v --tb=short

# PR C tests
python -m pytest tests/test_ocr_quality_feedback.py -v --tb=short

# Legacy health compatibility
python -m pytest tests/test_ocr_health.py -v --tb=short

# Full OCR suite (no regressions)
python -m pytest tests/test_ocr_*.py -v --tb=short
```
