# R3 Visual Acceptance Sample (24 papers)

## Sample
- Candidate set: 787 READY keys (migration status == "READY"), excluding CHILQ4KJ, HOLD, M2_REVIEW_REQUIRED, and REQUIRES_APPROVAL. After the heading fix CHILQ4KJ is also READY (788 total), but this sample stays frozen at 787.
- Selected 24 keys, 4 per stratum: see `sample-manifest.json`.
- Strata: figure_heavy, table_heavy, multi_asset, single_asset, mixed_shape, control.

## Tools executed (isolated temp vault; real vault read-only)
- Rebuild: `paperforge.worker.ocr_rebuild._rebuild_one_paper` on isolated copies (combined temp vault; meta.source_pdf resolved to source vault PDFs; bootstrap_config).
- `scripts/dev/figure_quality_eval.py` -> `docs/evidence/r3/result.json`, per-key `baseline.json`, `labels.jsonl`, `page_*.jpg`, crop images.
- `scripts/dev/visual_detection_benchmark.py --overlays --dpi 120` -> `docs/evidence/r3/visual-benchmark/benchmark.json`, `pages/*.png`, `overlays/*.png`.
- `paperforge.render_audit.audit_papers` -> `docs/evidence/r3/render_audit.json`.

## Structural results
- figure_quality_eval: 19/24 passed; 5 failed (4 missing manifest assets: 24YKLTHQ, AUUNHWSN, NJWU2G4V, NLKKXD5Z; 1 tooling crash: 2ZBAK9VY page 8 not in document).
- render_audit: 19/24 CLEAN, 5 DEGRADED, 0 failed.
- visual_detection_benchmark: 253 pages; visual_missing=143; inventory_unsupported=17. (Automated IoU vs PDF vector graphics; not a fidelity verdict.)

## Evidence paths
- Manifest: `docs/evidence/r3/sample-manifest.json`
- Structural: `docs/evidence/r3/result.json`, `docs/evidence/r3/render_audit.json`
- Visual benchmark: `docs/evidence/r3/visual-benchmark/benchmark.json` (page images/overlays were generated locally but are not committed because they are ~200 MB).
- Per-paper: `docs/evidence/r3/<KEY>/` (`baseline.json`, `labels.jsonl`, `page_*.jpg`, `figure_*_asset*.jpg`)

## Tooling gap
- `2ZBAK9VY`: source PDF has 8 pages but inventory references page 9 (supplemental PDF mismatch). figure_quality_eval crashed; baseline/crops not generated for this key. Evidence gap noted; no production code changed.

## UNKNOWN (requires human visual review)
- All `caption_ok`, `panels_ok`, `crop_ok`, `delivery_ok` labels are unreviewed (reviewer empty); automated scores alone do not establish visual acceptance.
- Whether tight crops include all intended panel content and exclude adjacent body text (especially multi-asset figures) must be checked by human against `page_*.jpg` overlays and crops.
- Whether captions/legends are correctly associated and rendered in final markdown (delivery) must be checked by human.
- Papers flagged structurally/degraded need priority review.
- No claim of visual acceptance is made from automated metrics.

## R3 failure triage
- See `docs/evidence/r3/failure-triage.json` for per-key classification.
- 24YKLTHQ, AUUNHWSN, NJWU2G4V, NLKKXD5Z: real_delivery_defect - manifest asset genuinely absent because corresponding figure is a cross-page reservation with zero matched asset blocks; no crop or standard render markdown produced.
- 2ZBAK9VY: supplemental_pdf_mismatch - figure_quality_eval used an 8-page PDF while pipeline OCR'd the 15-page supplemental PDF; page 9 is valid in supplemental source, so inventory is not stale.
