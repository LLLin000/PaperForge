# Annotation Phase 4 Research: Annotation Verification Gate

## Research Summary

Annotation Phase 4 should not add another annotation feature. It should turn the already-implemented annotation backend and CLI into a release-quality verification gate.

Current evidence from prior phases:

- Phase 2 verifies the backend path: 71 annotation unit tests pass, 1 expected skip, no Zotero write-back path.
- Phase 3 verifies the CLI path: 52 annotation CLI tests pass, all JSON commands use the PFResult envelope.
- Known unrelated baseline failures are already documented: Windows `tmp_path` PermissionError, `ld_deep_script` versus `pf_deep_script`, and missing `filelock`.

The useful planning question is therefore: what extra proof is needed before calling annotation v0.1 ready?

## Existing Test Assets

Useful existing files:

- `tests/unit/annotation/test_zotero_probe.py`
- `tests/unit/annotation/test_zotero_normalize.py`
- `tests/unit/annotation/test_importer.py`
- `tests/unit/annotation/test_zotero_import_flow.py`
- `tests/cli/test_annotation_import_json.py`
- `tests/cli/test_annotation_read_json.py`
- `tests/cli/test_annotation_json_contracts.py`
- `tests/cli/test_annotation_error_contracts.py`

These files already contain generated SQLite fixture builders, preview/apply tests, scoped import regression coverage, and PFResult contract checks.

## Gaps to Close

Phase 4 should close three remaining release-gate gaps:

1. The generated Zotero fixture pattern should be consolidated enough that the final gate clearly satisfies TEST-01. Right now fixture builders exist in multiple test files.
2. The final verification matrix should explicitly prove TEST-01 through TEST-04, including service-level list/export behavior and the paper-scoped stale-deletion regression.
3. The release report should explicitly separate blocking annotation failures from unrelated baseline failures and record the safety audit.

## Planning Recommendation

Use three plans:

1. Fixture and service verification foundation.
2. Final annotation CLI/regression gate.
3. Verification report, safety audit, and roadmap/state closeout.

This keeps test-support cleanup, test coverage, and release documentation separate.

## Research Complete
