# M3 Isolated Migration Report

- Source vault: D:\L\OB\Literature-hub
- Workdir: C:\rtools44\tmp\m3
- Selected READY keys: 10
- Refused: 3

## Gate refusals
- 28JLIHLS: M2_REVIEW_REQUIRED (status_refused)
- 2UIPV93M: HOLD (status_refused)
- 28ALPCY7: REQUIRES_APPROVAL (status_refused)

## Clean run
- ok=10/10
  - 3QYCST4E: ok
  - 2BYRLKQS: ok
  - 2332GHPT: ok
  - 23T2B8ZX: ok
  - 24A2QUAH: ok
  - 24EZZ7CS: ok
  - 24YKLTHQ: ok
  - 25K5KZAQ: ok
  - 26WC6NT7: ok
  - 27MFWJWJ: ok

## Invariants
- dangling/fulltext targets: validated 0
- text decrease: validated 0
- leftovers: validated 0
- idempotent tree equal: True
- source vault untouched: True

## Faults
- kill: {"interrupted": true, "pending_before": true, "leftovers_before": [], "proc_rc": 1, "rebuild": {"key": "3QYCST4E", "status": "ok"}, "validation": {"ok": true, "errors": []}, "matches_clean": true}
- write_error: {"first": {"status": "exception", "error": "object materialization failed: ENOSPC"}, "rerun": {"key": "3QYCST4E", "status": "ok"}, "validation": {"ok": true, "errors": []}, "old_byte_identical": true, "leftovers": []}
- interrupted_commit: {"restored_old": true, "rebuild": {"key": "3QYCST4E", "status": "ok"}, "validation": {"ok": true, "errors": []}}
- concurrent: {"returncodes": [0, 0], "stdout": ["{'key': '3QYCST4E', 'status': 'ok'}\n", "{'key': '3QYCST4E', 'status': 'ok'}\n"], "stderr": ["D:\\programs\\Python\\Lib\\site-packages\\requests\\__init__.py:113: RequestsDependencyWarning: urllib3 (2.7.0) or chardet (7.4.3)/charset_normalizer (3.4.7) doesn't match a supported version!\n  warnings.wa", "D:\\programs\\Python\\Lib\\site-packages\\requests\\__init_
- corrupt: {"detected_before": true, "errors_before": ["json_parse:figure_inventory.json:Expecting property name enclosed in double quotes: line 1 column 2 (char 1)", "figure_inventory_parse:Expecting property name enclosed in double quotes: line 1 column 2 (char 1)", "dangling_fulltext_target:render/figures/figure_001.md"], "rebuild": {"key": "3QYCST4E", "status": "ok"}, "valid_after": true, "matches_clean"

## Selected keys
- 3QYCST4E (both)
- 2BYRLKQS (both)
- 2332GHPT (both)
- 23T2B8ZX (figures)
- 24A2QUAH (both)
- 24EZZ7CS (both)
- 24YKLTHQ (both)
- 25K5KZAQ (figures)
- 26WC6NT7 (both)
- 27MFWJWJ (figures)

## Refused keys
- 28JLIHLS: M2_REVIEW_REQUIRED
- 2UIPV93M: HOLD
- 28ALPCY7: REQUIRES_APPROVAL