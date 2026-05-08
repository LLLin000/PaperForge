# Chaos Matrix — Destructive Test Scenarios

> Complete reference of all destructive/abnormal test scenarios for PaperForge.
> Every scenario must be run in isolated tmp_path vaults with mock backends. Never on real vaults.

---

## Corrupted Inputs (CHAOS-01)

| Scenario ID | Category | Trigger | Expected Behavior | Safety Contract | Test File |
|---|---|---|---|---|---|
| CI-01 | corrupted_input | Place malformed JSON in exports/ (missing closing brace, trailing comma) | `paperforge sync` prints "Error parsing JSON: {path}" with line number, exits with non-zero code, no crash | Only reads from tmp_path vault; assert "tmp" in str(vault) | test_corrupted_inputs.py |
| CI-02 | corrupted_input | Place an empty JSON file (`{}`) in exports/ | `paperforge sync` prints "No items found in {path}" or warning, exits successfully (0) — no formal notes created for empty export | Only reads from tmp_path vault | test_corrupted_inputs.py |
| CI-03 | corrupted_input | BBT JSON with items missing `citationKey` field | Sync gracefully skips the item, prints warning "Skipping item at index {N}: missing citationKey", continues processing valid items | Only reads from tmp_path vault | test_corrupted_inputs.py |
| CI-04 | corrupted_input | Corrupt PDF file (truncated, binary garbage) in Zotero storage | OCR submission fails or PDF processing prints "Error processing PDF: {path}" — no crash, non-zero exit but graceful | Only reads from tmp_path vault | test_corrupted_inputs.py |
| CI-05 | corrupted_input | Broken meta.json in OCR dir (invalid JSON, missing required fields) | `paperforge ocr` prints "Warning: meta.json corrupted for {key}" — ocr_status set to "failed" with error detail, no crash | Only reads from tmp_path vault | test_corrupted_inputs.py |
| CI-06 | corrupted_input | Formal note frontmatter missing `zotero_key` field | Status/doctor/repair handle gracefully — prints warning, skips the note in aggregate counts, no crash | Only reads from tmp_path vault | test_corrupted_inputs.py |

## Network Failures (CHAOS-02)

| Scenario ID | Category | Trigger | Expected Behavior | Safety Contract | Test File |
|---|---|---|---|---|---|
| NF-01 | network_failure | OCR API returns HTTP 401 on submit | `paperforge ocr` prints "OCR API authentication failed (401)" — ocr_status set to "failed" with error detail, no crash, suggests checking PADDLEOCR_API_TOKEN | Mock backend via responses; no real HTTP calls | test_network_failures.py |
| NF-02 | network_failure | OCR API returns HTTP 500 on submit | `paperforge ocr` prints "OCR API server error (500)" — retries with backoff (configured max retries), eventually sets ocr_status: "failed" | Mock backend via responses | test_network_failures.py |
| NF-03 | network_failure | OCR poll returns 'queued' indefinitely (timeout) | After max poll attempts, `paperforge ocr` prints "OCR job {id} did not complete after {N} polls" — ocr_status set to "failed" or "pending" with timeout note, no crash | mock_ocr_timeout() from fixtures | test_network_failures.py |
| NF-04 | network_failure | DNS unreachable / connection refused | `paperforge ocr` prints "Network error: unable to reach OCR API" — exits with error message, no traceback, no crash | Mock backend via responses or monkeypatch | test_network_failures.py |

## Filesystem Errors (CHAOS-03)

| Scenario ID | Category | Trigger | Expected Behavior | Safety Contract | Test File |
|---|---|---|---|---|---|
| FE-01 | filesystem_error | PDF attachments directory deleted after sync | `paperforge status` or `paperforge doctor` prints "PDF not found: {path}" — path_error field set, graceful degradation | assert "tmp" in str(vault); never touches real vault | test_filesystem_errors.py |
| FE-02 | filesystem_error | System/PaperForge/ocr directory deleted | `paperforge ocr` re-creates missing dirs or prints "OCR directory missing, creating: {path}" — non-fatal | assert "tmp" in str(vault) | test_filesystem_errors.py |
| FE-03 | filesystem_error | Formal note file deleted but entry still in canonical index | `paperforge repair` detects divergence, prints "Formal note missing for {key}" — suggests repair with `--fix` | assert "tmp" in str(vault) | test_filesystem_errors.py |
| FE-04 | filesystem_error | Path too long (deeply nested Zotero path with CJK chars) | Path resolution falls back gracefully — prints warning about long path, uses available alternative path, no crash | assert "tmp" in str(vault) | test_filesystem_errors.py |
| FE-05 | filesystem_error | Permission denied on exports/ directory | `paperforge sync` prints "Cannot read exports directory: {path}" — non-zero exit, actionable message, no crash | assert "tmp" in str(vault) | test_filesystem_errors.py |

---

## Safety Contracts (Mandatory)

1. **Isolation assertion**: EVERY chaos test MUST include `assert "tmp" in str(vault)` or `assert "pytest" in str(vault)` to prevent real vault access.
2. **CI isolation**: Chaos tests run ONLY in scheduled CI (`ci-chaos.yml`) — never in regular CI gate.
3. **Mock backends**: Chaos tests use mock backends (responses library) for network operations — no external HTTP calls.
4. **Marker**: All tests are marked `@pytest.mark.chaos`.
5. **Temp vaults**: All vaults are created via `tmp_path` (pytest built-in) or `tempfile.mkdtemp()` — never hardcoded paths.
6. **No state leakage**: Each test creates its own vault at the appropriate level; no test depends on another test's vault state.
