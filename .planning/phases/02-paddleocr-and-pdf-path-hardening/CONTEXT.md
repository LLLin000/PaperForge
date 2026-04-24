# Phase 2: PaddleOCR And PDF Path Hardening — CONTEXT

**Phase:** 02-paddleocr-and-pdf-path-hardening
**Status:** discuss-phase complete, decisions locked
**Created:** 2026-04-23
**Requirements:** OCR-01, OCR-02, OCR-03, OCR-04, OCR-05, ZOT-01, ZOT-02

---

## 1. Executive Summary

Phase 2 hardens the OCR subsystem to make failures diagnosable and recoverable. Two major gaps exist:

1. **OCR failures are opaque** — `run_ocr()` in `literature_pipeline.py` submits PDFs without preflight validation and records only a generic "PaddleOCR request failed" message in `meta.json`.
2. **PDF path resolution is fragile** — `obsidian_wikilink_for_pdf()` assumes vault-relative paths; it does not handle Zotero junction links, storage-relative paths, or missing files. On failure, `pdf_path` is silently empty.

This phase delivers:
- `paperforge ocr doctor` — tiered diagnostics (token, URL, API structure, live PDF)
- PDF preflight in `run_ocr()` — file existence, junction resolution, `nopdf` status
- Failure taxonomy (`blocked` vs `error`) with actionable fix suggestions
- Zotero PDF path resolver supporting absolute, relative, junction, and storage-relative formats

---

## 2. Research Findings

### 2.1 OCR Code Scouting (`literature_pipeline.py`, lines 2294–2810)

**`run_ocr()` flow:**
```python
# Simplified current flow (lines ~2300-2400)
for _, row in queue.iterrows():
    pdf_path = row['pdf_path']          # used directly without preflight
    key = row['zotero_key']
    # ... upload to PaddleOCR API
    # On any exception: log.error(f"OCR failed for {key}: {e}")
    # meta.json gets: {"ocr_status": "failed", "error": "PaddleOCR request failed"}
```

**Problems identified:**
1. **No PDF preflight** — `pdf_path` used raw; no check for `None`, empty string, or non-existent file
2. **No path resolution** — junction paths, storage-relative paths passed verbatim to API
3. **Broad error classification** — all failures collapse to `"failed"` with identical message
4. **No retry signal** — `meta.json` does not distinguish fixable (blocked) vs unfixable (error) states
5. **No diagnostics command** — user must manually inspect logs to debug API issues

**`obsidian_wikilink_for_pdf()` (line ~2720):**
```python
def obsidian_wikilink_for_pdf(pdf_path, vault_root):
    if pdf_path and pdf_path.startswith(vault_root):
        rel = os.path.relpath(pdf_path, vault_root)
        return f"[[{rel}]]"
    return ""
```

- Only handles absolute paths within vault. Does not handle:
  - Relative paths (e.g., `Zotero/storage/XXXX/item.pdf`)
  - Junction links (Windows symlinks to external Zotero storage)
  - Zotero storage-relative URIs

### 2.2 API Error Patterns (from production observations)

| Symptom | Likely Cause | Current Output |
|---------|--------------|----------------|
| 401 Unauthorized | Missing/invalid PADDLEOCR_API_KEY | "PaddleOCR request failed" |
| Connection refused | Wrong PADDLEOCR_BASE_URL | "PaddleOCR request failed" |
| 404 Not Found | PDF path invalid or file missing | "PaddleOCR request failed" |
| Timeout | Large PDF or slow network | "PaddleOCR request failed" |
| Schema mismatch | PaddleOCR API version change | "PaddleOCR request failed" |

---

## 3. Locked Decisions

### 3.1 OCR Doctor (OCR-01) — DECIDED

**Command:** `paperforge ocr doctor`

Runs tiered diagnostics in order, stopping early on failure with actionable message:

| Level | Check | Action on Failure |
|-------|-------|-------------------|
| **L1** | Token presence | Check `PADDLEOCR_API_KEY` in env/.env |
| **L2** | URL reachability | `GET` base URL, check HTTP status |
| **L3** | API response structure | Submit minimal request, validate response schema |
| **L4** | Live PDF test (optional) | Upload a tiny fixture PDF, verify round-trip |

**Decision record:** Single command completes all diagnostics. No separate subcommands. L4 is optional (flag `--live`).

### 3.2 PDF Preflight (OCR-02) — DECIDED

**Flow in `run_ocr()` before submission:**

```
1. pdf_path = row['pdf_path']
2. If not pdf_path or pdf_path == "":
     a. Check row['has_pdf'] — if false → ocr_status = "nopdf"
     b. If has_pdf is true but file missing → ocr_status = "nopdf"
3. If pdf_path exists → proceed
4. If pdf_path is junction/symlink → resolve to actual path, check existence
5. If resolved path exists → proceed with resolved path
6. If still not found → ocr_status = "nopdf"
```

**Decision record:**
- `nopdf` is a terminal state (not `failed`). It means "no PDF available to OCR" — user should check Zotero attachment.
- Junction resolution: if `<system_dir>/Zotero/` is a junction/symlink, resolve through it to the actual Zotero storage path.
- If user placed Zotero storage directly in vault (no junction), paths are already vault-relative — no special handling needed.

### 3.3 Failure Classification (OCR-03, OCR-04) — DECIDED

**Taxonomy:**

| State | Meaning | User Action |
|-------|---------|-------------|
| `pending` | Queued for OCR | Wait or run `paperforge ocr` |
| `processing` | OCR job in flight | Wait |
| `done` | OCR complete | Ready for deep-reading |
| `blocked` | Fixable issue (config/path/token) | Fix issue, then re-run `paperforge ocr` |
| `error` | Runtime failure (API error, timeout, schema mismatch) | Check `meta.json` error field for fix suggestion |
| `nopdf` | No PDF attachment or file missing | Check Zotero PDF attachment |

**Decision record:**
- Distinguish `blocked` (configuration/path issues) from `error` (runtime/API issues).
- No `retry` command — retry is identical to re-running `paperforge ocr`.
- `meta.json` error field includes fix suggestion (e.g., "Set PADDLEOCR_API_KEY env var and re-run `paperforge ocr`").

### 3.4 PDF Path Resolver (ZOT-01) — DECIDED

**Supported path formats:**

| Format | Example | Resolution Strategy |
|--------|---------|---------------------|
| Absolute | `C:\Zotero\storage\ABC\item.pdf` | Use as-is |
| Vault-relative | `System/Zotero/storage/ABC/item.pdf` | Prepend vault root |
| Junction path | `<system_dir>/Zotero/` → actual `C:\Zotero\` | Resolve junction target |
| Zotero storage-relative | `storage:ABC/item.pdf` or `zotero://...` | Resolve via Zotero data directory |

**Decision record:**
- Must investigate Zotero storage path formats in full local pipeline at `D:\L\Med\Research\99_System\LiteraturePipeline`.
- Junction paths must be resolved on Windows (via `os.path.realpath` or `ctypes` for junctions).
- On resolution failure: return empty string + write error to log.

### 3.5 Selection Sync PDF Reporting (ZOT-02) — DECIDED

**Decision:** During `selection-sync`, if `has_pdf: false` or resolved `pdf_path` is empty, record `ocr_status: "nopdf"` in library-record frontmatter. This gives the user immediate visibility into which records lack PDFs before queueing OCR.

---

## 4. Architecture Changes

### 4.1 New Module: `paperforge/ocr_diagnostics.py`

Functions:
- `ocr_doctor(config, live=False) -> DoctorReport` — runs L1-L4 diagnostics
- `classify_error(exception, response) -> (state, suggestion)` — maps exception to `blocked`/`error` + fix suggestion

### 4.2 New Module: `paperforge/pdf_resolver.py`

Functions:
- `resolve_pdf_path(pdf_path, has_pdf, vault_root, zotero_dir) -> str` — returns resolved path or empty string
- `resolve_junction(path) -> str` — Windows junction resolution
- `is_valid_pdf(path) -> bool` — file exists and is readable

### 4.3 Modified: `literature_pipeline.py`

Changes in `run_ocr()`:
1. Call `resolve_pdf_path()` before submission
2. If empty → set `ocr_status = "nopdf"`, write `meta.json`, skip
3. Wrap API call in try/except with `classify_error()`
4. Write `meta.json` with `{ocr_status, error, suggestion}` on failure

### 4.4 Modified: `cli.py`

Add subcommand:
```python
parser_ocr = subparsers.add_parser('ocr')
ocr_sub = parser_ocr.add_subparsers()
doctor_parser = ocr_sub.add_parser('doctor')
doctor_parser.add_argument('--live', action='store_true')
```

---

## 5. Implementation Order

### Plan 02-01: PDF Path Resolver + Preflight
- Implement `pdf_resolver.py` with junction support
- Add tests for absolute, relative, junction, missing cases
- Wire into `run_ocr()` preflight

### Plan 02-02: OCR Failure Classification
- Implement `classify_error()` with exception-to-state mapping
- Update `meta.json` schema to include `suggestion`
- Update `ocr` worker to use classification

### Plan 02-03: OCR Doctor Command
- Implement `ocr_diagnostics.py` L1-L4 checks
- Add `paperforge ocr doctor` CLI dispatch
- Add tests with mocked `requests`

### Plan 02-04: Selection Sync PDF Reporting
- Update `selection-sync` to set `ocr_status: nopdf` when `has_pdf: false`
- Update library-record template frontmatter

---

## 6. Testing Strategy

### Unit Tests

| Test | File | Coverage |
|------|------|----------|
| Absolute path resolution | `tests/test_pdf_resolver.py` | ZOT-01 |
| Vault-relative path resolution | `tests/test_pdf_resolver.py` | ZOT-01 |
| Junction resolution (mock) | `tests/test_pdf_resolver.py` | ZOT-01 |
| Missing file → empty string | `tests/test_pdf_resolver.py` | ZOT-01 |
| `has_pdf: false` → nopdf | `tests/test_ocr_preflight.py` | OCR-02, ZOT-02 |
| API auth failure → blocked | `tests/test_ocr_classify.py` | OCR-03 |
| Network timeout → error | `tests/test_ocr_classify.py` | OCR-03 |
| Schema mismatch → error | `tests/test_ocr_classify.py` | OCR-03, OCR-05 |
| Doctor L1 (missing token) | `tests/test_ocr_doctor.py` | OCR-01 |
| Doctor L2 (bad URL) | `tests/test_ocr_doctor.py` | OCR-01 |
| Doctor L3 (bad response) | `tests/test_ocr_doctor.py` | OCR-01 |
| Doctor L4 (live test, mocked) | `tests/test_ocr_doctor.py` | OCR-01 |

### Integration Tests

| Test | Coverage |
|------|----------|
| `paperforge ocr doctor` CLI exit codes | OCR-01 |
| `paperforge ocr` with invalid PDF path | OCR-02 |
| `paperforge ocr` with junction path | ZOT-01 |
| `selection-sync` sets `ocr_status: nopdf` | ZOT-02 |

---

## 7. Backward Compatibility

- Existing `meta.json` with `"ocr_status": "failed"` remains valid — new states are additive.
- `paperforge ocr` without `doctor` subcommand continues to run OCR queue (unchanged behavior).
- Library records without `ocr_status` field are treated as `pending` (graceful default).

---

## 8. Files to Create / Modify

### New Files
- `paperforge/pdf_resolver.py`
- `paperforge/ocr_diagnostics.py`
- `tests/test_pdf_resolver.py`
- `tests/test_ocr_preflight.py`
- `tests/test_ocr_classify.py`
- `tests/test_ocr_doctor.py`

### Modified Files
- `paperforge/cli.py` — add `ocr doctor` subcommand
- `pipeline/worker/scripts/literature_pipeline.py` — preflight + classification in `run_ocr()`
- `command/lp-ocr.md` — document `ocr doctor` and failure states

---

## 9. Success Criteria

Per ROADMAP.md Phase 2:

1. [ ] `paperforge ocr doctor` distinguishes missing token, bad URL, unauthorized response, network timeout, schema mismatch, and unreadable PDF.
2. [ ] OCR worker resolves common Zotero PDF paths before submission and records the resolved path in diagnostics.
3. [ ] Blocked/error records can be reset or retried with a documented command (re-running `paperforge ocr`).
4. [ ] `meta.json` error messages are actionable and include a suggested next command.

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Junction resolution differs on Windows vs Unix | High | Medium | Test on Windows; use `os.path.realpath` fallback |
| PaddleOCR API schema changes unexpectedly | Medium | High | Defensive parsing in L3; log raw response snippets |
| Zotero storage path format unknown | Medium | High | Research full pipeline; support common formats |
| Live PDF test in doctor hits rate limits | Low | Low | Make L4 optional (`--live` flag) |

---

## 11. Reference Links

- Phase 1 CONTEXT: `.planning/phases/01-config-and-command-foundation/01-CONTEXT.md`
- Requirements: `.planning/REQUIREMENTS.md` (OCR-01 through OCR-05, ZOT-01, ZOT-02)
- OCR code: `pipeline/worker/scripts/literature_pipeline.py` lines 2294–2810
- Full pipeline (Zotero path research): `D:\L\Med\Research\99_System\LiteraturePipeline`
