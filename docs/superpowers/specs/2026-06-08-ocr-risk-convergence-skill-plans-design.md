# OCR Risk Convergence Skill Plans Design

> **Status:** Proposed  
> **Date:** 2026-06-08  
> **Target branch:** `feat/ocr-structured-pipeline`  
> **Audience:** maintainers, reviewers, agentic implementers

## 1. Goal

Turn the OCR structured pipeline risk report into six focused Superpowers implementation plans. The plans must converge the riskiest OCR layout judgments from hard-rule output toward score/evidence-driven decisions with conservative fallbacks.

The goal is not perfect human-visual reconstruction. The v1 target is safer behavior:

- confident output only when evidence is strong;
- candidate, ambiguous, unresolved, orphan, or degraded states when evidence is weak;
- health and decision logs that explain uncertainty;
- raw OCR truth preserved for rebuilds;
- renderer behavior that does not hide low-confidence upstream structure.

## 2. Current Context

The OCR worktree is:

`D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline`

The branch already contains recent scorer and health work, including:

- `paperforge/worker/ocr_scores.py` with figure caption, table match, and tail boundary scoring helpers;
- figure/table inventories that carry some score evidence;
- OCR health confidence distributions;
- decision log and error taxonomy work;
- a v1 convergence master plan at `docs/superpowers/plans/2026-06-08-ocr-v1-convergence-master-plan.md`.

This design should not duplicate that work. It should define the next stricter P1/P2 risk-convergence plans that make scores control decisions instead of acting only as after-the-fact health signals.

## 3. Non-Goals

- Do not add visual-model, document-AI, or ML dependencies for OCR v1.
- Do not pursue perfect rendering of every PDF layout.
- Do not use `fulltext.md` as a fact source.
- Do not overwrite or weaken raw artifacts such as `result.json`, `blocks.raw.jsonl`, page image cache, or PDF span metadata.
- Do not broaden OCR heuristics while the hard-rule audit is still incomplete.
- Do not mix these plans into unrelated root-worktree changes.

## 4. Shared Principles

Every high-risk OCR decision should move toward this shape:

```json
{
  "decision": "matched | candidate | ambiguous | rejected | unresolved",
  "score": 0.0,
  "evidence": [],
  "fallback": "conservative behavior when score is low"
}
```

Rules that previously produced direct conclusions should become evidence inputs, including:

- figure or table prefix;
- nearest media asset;
- vertical distance;
- visual container membership;
- x-center gap;
- dense reference item count;
- same-page or adjacent-page proximity;
- page-1 frontmatter zone;
- Zotero/OCR metadata alignment.

Low confidence must prefer preservation over mutation. If the system is uncertain, it should keep raw order, keep unmatched captions/assets visible, mark candidates, and report health warnings instead of pretending the result is final.

## 5. Plan Set

Create six implementation plans under `docs/superpowers/plans/`.

### 5.1 `2026-06-08-ocr-high-risk-rule-audit-plan.md`

Goal: inventory direct role mutations and direct object matches before deeper changes.

Expected outputs:

- `docs/ocr/high-risk-rule-audit.md`;
- categorized counts for direct role mutation, direct match, direct reorder, and direct renderer inference;
- mapping from each high-risk rule to one of: keep as evidence, guard with score, defer to P2, or remove;
- explicit list of production files and non-production/legacy files.

Scope:

- inspect `ocr_document.py`, `ocr_figures.py`, `ocr_tables.py`, `ocr_render.py`, `ocr_health.py`, and adjacent OCR modules;
- do not change behavior except tests/docs required to expose the audit contract;
- do not search vault content directly.

Acceptance criteria:

- audit identifies every direct promotion to `structured_insert`, `non_body_insert`, figure/table match, and tail/layout reorder decision;
- audit distinguishes production path from legacy or experimental modules;
- audit becomes the baseline for `hard_rule_decision_count` in health.

### 5.2 `2026-06-08-ocr-figure-score-matching-plan.md`

Goal: make figure scoring control matching decisions, not merely annotate inventory after matching.

Minimum behavior:

- score all same-page candidate asset clusters for each legend;
- reject confident matching when `caption_score.score < 0.4`;
- produce unmatched legend when best match score is below threshold;
- mark ambiguous when top candidate scores are close;
- allow a legend to match multiple nearby assets when evidence supports a multi-panel cluster;
- preserve orphan assets and unresolved clusters without hiding them in render.

Expected inventory states:

- `matched_figures` for high-confidence matches;
- `ambiguous_figures` or equivalent ambiguous match records;
- `unmatched_legends`;
- `unmatched_assets`;
- `unresolved_clusters` with stable IDs.

Acceptance criteria:

- every matched figure has score and evidence that participated in selection;
- low-score figure captions cannot create confident figure matches;
- nearest-asset tie cases become ambiguous instead of silently choosing top1;
- renderer shows unresolved/orphan figure information instead of dropping it.

### 5.3 `2026-06-08-ocr-table-score-matching-plan.md`

Goal: make `score_table_match()` choose table assets across a conservative page window.

Minimum behavior:

- candidate pages include previous, current, and next page;
- all candidate assets receive match scores;
- choose only when top score passes threshold and separation from top2 is sufficient;
- expose `match_status` such as `matched`, `matched_low_confidence`, `ambiguous`, `unmatched_caption`, `unmatched_asset`, or `continuation`;
- keep `truth_source = image` for table objects.

Acceptance criteria:

- vertical nearest is no longer the sole selector;
- low-confidence table captions/assets remain visible;
- previous-page, next-page, and continuation cases have tests;
- table health reports low-confidence and ambiguous table counts.

### 5.4 `2026-06-08-ocr-layout-confidence-plan.md`

Goal: make page layout profiles carry confidence and prevent low-confidence layout from driving strong reorder behavior.

Minimum behavior:

- build column profiles from eligible body-like blocks only;
- exclude media, table, frontmatter, structured insert, noise, and other non-body blocks from column inference;
- add `confidence` and `evidence` to `PageLayoutProfile`;
- serialize layout confidence into `document_structure.json`;
- prevent strong tail/column reorder when layout confidence is low.

Acceptance criteria:

- wide headings, figures, tables, and sidebars do not dominate column detection;
- low-confidence pages preserve raw order or use conservative local ordering;
- health reports layout confidence distribution;
- renderer consumes layout confidence instead of inventing new layout semantics.

### 5.5 `2026-06-08-ocr-insert-score-plan.md`

Goal: replace direct structured insert promotion with score/candidate/fallback behavior.

Minimum behavior:

- add a structured insert scorer using evidence such as visual container, keyword anchor, width mismatch, font mismatch, cluster coherence, page context, and body-spine mismatch;
- treat `_in_visual_container` as evidence, not a conclusion;
- keep medium-confidence blocks as `structured_insert_candidate`;
- avoid promoting low-confidence candidates to `structured_insert`;
- record cluster expansion inputs and added block IDs;
- warn when cluster expansion covers too much probable body text.

Acceptance criteria:

- every structured insert promotion has score and evidence in decision log or block metadata;
- low-score candidates do not swallow body paragraphs;
- visual container alone cannot force a final structured insert role;
- health reports low-confidence insert count and candidate-forced count.

### 5.6 `2026-06-08-ocr-health-hard-rule-summary-plan.md`

Goal: make OCR health summarize uncertainty and remaining hard-rule decisions across the whole pipeline.

Minimum metrics:

- `hard_rule_decision_count`;
- `low_score_but_matched_count`;
- `ambiguous_match_count`;
- `unresolved_cluster_count`;
- `candidate_forced_count`;
- low-confidence figure/table/layout/insert/tail distributions;
- direct renderer inference count, if any remains.

Acceptance criteria:

- health tells users which outputs are certain, uncertain, degraded, or unresolved;
- health counts agree with figure/table inventories, document structure, and decision log;
- release gate can fail or warn based on severe uncertainty counts;
- no high-risk scorer silently writes confident output without health visibility.

## 6. Execution Order

Run the plans in this order:

1. `ocr-high-risk-rule-audit`
2. `ocr-figure-score-matching`
3. `ocr-table-score-matching`
4. `ocr-layout-confidence`
5. `ocr-insert-score`
6. `ocr-health-hard-rule-summary`

Figure and table plans come before layout and insert because object misbinding is the highest-risk user-visible error. Health summary comes last because it should report final semantics after decision behavior changes.

## 7. Cross-Plan Interfaces

The plans should use these shared contracts:

- score objects contain `score`, `decision`, and `evidence`;
- decision log records role mutations and forced/candidate decisions;
- inventories preserve unmatched, ambiguous, and orphan states;
- `document_structure.json` carries layout and tail confidence;
- renderer consumes confidence and inventory states but does not perform new semantic classification;
- health is the aggregation layer, not the only place where uncertainty exists.

## 8. Testing Strategy

Each plan should begin with focused failing tests before implementation. Tests should prefer synthetic fixtures unless real PDF behavior is required.

Required coverage themes:

- figure nearest-asset ambiguity;
- low-caption-score figure refusal;
- multi-panel figure cluster preservation;
- table previous/current/next page matching;
- table ambiguous top1/top2 scores;
- layout confidence with wide headings and sidebars;
- low-confidence layout preserving raw order;
- structured insert candidate not swallowing body text;
- visual container alone not forcing structured insert;
- health summary consistency with inventories and decision log.

Recommended verification after each plan:

```bash
python -m pytest tests/test_ocr_scores.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_document.py tests/test_ocr_health.py tests/test_ocr_rendering.py -q --tb=short
```

Run broader OCR regression before branch merge:

```bash
python -m pytest tests/test_ocr_roles.py tests/test_ocr_document.py tests/test_ocr_profiles.py tests/test_ocr_metadata.py tests/test_ocr_health.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_rebuild.py tests/test_ocr_blocks.py tests/test_ocr_pdf_spans.py tests/test_ocr_tables.py tests/test_ocr_artifacts.py -q --tb=short
```

## 9. Merge Gate

OCR v1 risk convergence is complete when:

- all figure/table matches have score and evidence used in selection;
- low-score figure/table evidence cannot produce confident matches;
- layout confidence low blocks strong reorder behavior;
- structured insert low scores remain candidates or body, not forced callouts;
- tail/layout confidence controls render behavior;
- health exposes hard rules, low-confidence matches, ambiguous matches, unresolved clusters, and forced candidates;
- decision log can trace high-risk role mutations;
- raw artifacts remain untouched and rebuildable;
- `fulltext.md` remains a structured reading artifact, not a claimed PDF truth source.

## 10. Open Decisions

- Exact thresholds should start conservative and be documented in each implementation plan.
- Existing score helper names may be extended rather than replaced if tests preserve current behavior.
- Ambiguous inventory schema can be explicit lists or status fields, but renderer and health must consume it consistently.
- Commit strategy is intentionally unspecified here; agents should not commit unless explicitly instructed.
