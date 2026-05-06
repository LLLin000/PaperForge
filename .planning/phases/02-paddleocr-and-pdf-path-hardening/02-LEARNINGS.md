---
phase: 02
phase_name: "PaddleOCR and PDF Path Hardening"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 12
  lessons: 4
  patterns: 5
  surprises: 4
missing_artifacts:
  - "UAT.md"
  - "VERIFICATION.md"
---

# Phase 02 Learnings: PaddleOCR and PDF Path Hardening

## Decisions

### D1: `nopdf` as a Distinct Terminal State
Missing or unreadable PDFs result in `ocr_status: nopdf` — distinct from `blocked` (fixable config/path issues) and `error` (runtime/API issues). This gives users immediate visibility into which records lack PDFs before queueing OCR.

**Rationale:** `nopdf` means "no PDF available to OCR" — user should check Zotero attachment. It prevents wasted OCR runs on attachments that don't exist.

**Source:** 02-01-PLAN.md, 02-01-SUMMARY.md, 02-CONTEXT.md

---

### D2: Junction Resolution Strategy
Windows junctions are resolved via `os.path.realpath` first, with a fallback to `GetFinalPathNameByHandleW` via ctypes when `realpath` does not follow the junction.

**Rationale:** `os.path.realpath` handles most symlinks but may not resolve all Windows directory junctions. The ctypes fallback provides comprehensive coverage.

**Source:** 02-01-PLAN.md, 02-01-SUMMARY.md

---

### D3: `resolve_pdf_path` Resolution Order
Path resolution tries strategies in strict sequence: absolute path → vault-relative path → junction resolution → Zotero storage-relative path. Returns empty string if all fail.

**Rationale:** Supports all known Zotero attachment path formats while providing predictable fallback behavior. Early exit on first successful resolution.

**Source:** 02-01-PLAN.md, 02-01-SUMMARY.md

---

### D4: Failure Taxonomy — `blocked` vs `error`
All OCR failures are classified into two categories: `blocked` (fixable issues like config, path, or token problems) and `error` (runtime issues like API timeout, schema mismatch, provider error).

**Rationale:** Enables actionable user messaging — blocked items tell the user exactly what to fix; error items signal a transient or provider-side issue.

**Source:** 02-02-PLAN.md, 02-02-SUMMARY.md, 02-CONTEXT.md

---

### D5: `suggestion` Field in `meta.json`
Every failure path writes a `suggestion` field to `meta.json` containing an actionable fix instruction for the user.

**Rationale:** Eliminates the opaque "PaddleOCR request failed" debugging experience. Users see exactly what to do next.

**Source:** 02-02-PLAN.md, 02-02-SUMMARY.md

---

### D6: Tiered L1-L4 Diagnostics with Early-Stop
OCR Doctor runs diagnostics in tiered order: L1 (token presence) → L2 (URL reachability) → L3 (API response structure) → L4 (live PDF test, optional). Stops at the first failure with actionable output.

**Rationale:** Each level depends on the previous. No point testing API schema if the URL is unreachable. Early-stop minimizes unnecessary API calls.

**Source:** 02-03-PLAN.md, 02-03-SUMMARY.md

---

### D7: L4 Live PDF Test Is Optional (`--live`)
The full round-trip PDF upload test (L4) requires the `--live` flag explicitly. Without it, doctor stops at L3.

**Rationale:** L4 consumes API resources and may hit rate limits. Making it opt-in prevents accidental resource waste while still providing the option for thorough diagnosis.

**Source:** 02-03-PLAN.md, 02-03-SUMMARY.md

---

### D8: CLI Sub-Subcommands for OCR (`ocr run`, `ocr doctor`)
The CLI changed from a flat `ocr` command to sub-subcommands: `paperforge ocr run` and `paperforge ocr doctor`. `ocr` without a subcommand defaults to `run`.

**Rationale:** Multiple OCR-related operations needed distinct entry points. Sub-subcommands provide clear separation while preserving backward compatibility through the default.

**Source:** 02-03-PLAN.md, 02-03-SUMMARY.md

---

### D9: Inline Import of `classify_error` in `run_ocr()`
`classify_error` is imported inline (inside the except block) rather than at the top of the file.

**Rationale:** Avoids circular import issues in the test environment where `run_ocr()` may be imported before `ocr_diagnostics.py` is fully available.

**Source:** 02-02-PLAN.md, 02-02-SUMMARY.md

---

### D10: `raw_response` Truncated to 1000 Characters
On polling schema mismatch, the raw API response is stored in `meta.json` truncated to 1000 characters for safety.

**Rationale:** Raw responses may contain large payloads. Truncation prevents meta.json bloat while preserving enough content for debugging schema changes.

**Source:** 02-02-PLAN.md, 02-02-SUMMARY.md

---

### D11: `record_ocr_status` Variable in Selection-Sync
`run_selection_sync()` introduces a local `record_ocr_status` variable (distinct from the existing `ocr_status` variable used for meta.json state) to hold the frontmatter-only status value.

**Rationale:** Avoids confusing the library-record frontmatter OCR status with the meta.json OCR state. The frontmatter value is derived from preflight checks and may differ from the persistent meta.json state.

**Source:** 02-04-PLAN.md, 02-04-SUMMARY.md

---

### D12: Explicit Boolean Conversion in `yaml_quote`
The `yaml_quote()` function was fixed to handle Python `True`/`False` booleans by converting them to YAML `true`/`false` instead of treating them as falsy empty strings.

**Rationale:** Python `bool(True)` was falling through to the falsy branch, causing frontmatter corruption for `has_pdf`, `do_ocr`, and `analyze` fields.

**Source:** 02-04-SUMMARY.md

---

## Lessons

### L1: Windows Junction Mock Test Is Unpatchable
The test for Windows directory junction resolution is skipped because `from ctypes import wintypes` inside `resolve_junction()` bypasses module-level `ctypes` patches due to Python import semantics when `wintypes` is imported inside a function body.

**Context:** The symlink test and `os.path.realpath` path provide adequate coverage, but the direct ctypes junction code path cannot be unit-tested on non-Windows platforms.

**Source:** 02-01-SUMMARY.md

---

### L2: Exact String Matching in Test Assertions
One test assertion initially failed because it matched "format changed" vs "schema" — the expected suggestion string differed slightly from the implementation.

**Context:** The `classify_error` function for `JSONDecodeError` contained "PaddleOCR API response format changed." in the plan but "PaddleOCR API response schema changed." in the implementation (from earlier code). Ensures test assertions must match implementation exactly.

**Source:** 02-02-SUMMARY.md

---

### L3: Registry Token Blocks Env-Based Test Patters
The PaddleOCR registry token is always present in the test environment, making `patch.dict(os.environ, {}, clear=True)` ineffective for simulating a missing token scenario.

**Context:** Tests that need to verify behavior when `PADDLEOCR_API_TOKEN` is missing must use alternative approaches like HTTP 401 error injection rather than env var manipulation.

**Source:** 05-01-SUMMARY.md

---

### L4: Shared Dict Mutation with `return_value` in Mocks
Patching `ensure_ocr_meta` with `return_value={}` caused shared dict mutation because the same dict object was reused across multiple items in the loop.

**Context:** Must use `side_effect` with a factory function returning a fresh dict on each call instead of `return_value` when the mocked function is called multiple times and the caller mutates the result.

**Source:** 05-01-SUMMARY.md

---

## Patterns

### P1: Path Resolution Fallback Chain
Multiple resolution strategies tried in a fixed sequence, returning the first successful result. Each strategy handles a distinct path format. Empty string signals total failure.

**When to use:** When a value can be expressed in multiple formats and you need to normalize to a canonical form, with clear fallback semantics.

**Source:** 02-01-PLAN.md, 02-01-SUMMARY.md

---

### P2: Inline Import for Testability
Import a module inline (inside a function body, not at file top-level) to break circular import chains that manifest only during test invocation.

**When to use:** When two modules cyclically depend on each other at import time, or when a standalone script imports a module that itself imports back into the script's package.

**Source:** 02-02-PLAN.md, 02-02-SUMMARY.md

---

### P3: Classify-and-Suggest Error Handling
Map exceptions to (state, suggestion) pairs via a centralized classification function. The state drives downstream behavior; the suggestion drives user-facing messaging.

**When to use:** When different error types require different recovery strategies and different user-facing messages, but all errors flow through a single handler.

**Source:** 02-02-PLAN.md, 02-02-SUMMARY.md

---

### P4: Tiered Diagnostics with Early-Stop
Run checks in dependency order, stopping at the first failure. Each level validates a prerequisite for the next. Output is always actionable and specific to the failing level.

**When to use:** Diagnostic tools where higher-level checks are meaningless without lower-level prerequisites. Avoids users seeing "API schema mismatch" when the real issue is a missing API key.

**Source:** 02-03-PLAN.md, 02-03-SUMMARY.md

---

### P5: Worker Preflight Pattern
Before performing an operation, validate all prerequisites (file existence, path resolution, state validity). On preflight failure, record a specific terminal state and skip the operation.

**When to use:** Worker functions that operate on external resources (files, APIs, network services) where failure after partial work would leave inconsistent state.

**Source:** 02-01-PLAN.md, 02-04-PLAN.md

---

## Surprises

### S1: ctypes Import Inside Function Body Bypasses Module-Level Patches
`from ctypes import wintypes` inside `resolve_junction()` creates a new reference to the ctypes module that cannot be intercepted by patching `paperforge.pdf_resolver.ctypes` at module level.

**Impact:** The Windows junction mock test had to be disabled (skipped) on non-Windows platforms. The symlink test and `os.path.realpath` path provide equivalent coverage but the ctypes path remains untested on non-Windows.

**Source:** 02-01-SUMMARY.md

---

### S2: `yaml_quote()` Didn't Handle Python Boolean `True`/`False`
Python's `bool(True)` was treated as a falsy value by the YAML quoting function, producing empty strings for `has_pdf`, `do_ocr`, and `analyze` fields in frontmatter.

**Impact:** Introduced a subtle frontmatter corruption bug that silently dropped boolean fields. Fixed by adding explicit `isinstance(v, bool)` check before the truthiness test. This also fixed boolean handling in other frontmatter update paths.

**Source:** 02-04-SUMMARY.md

---

### S3: Obsidian Base UI Renders Absolute Paths for `pdf_path`
Obsidian's Base view displays `pdf_path` as an absolute path in the UI even though the data is stored as a relative wikilink in the actual file.

**Impact:** Cosmetic issue only — does not affect functionality. Users may be confused by the display but the underlying data is correct. Not worth fixing.

**Source:** AGENTS.md (FAQ section)

---

### S4: Chinese Domain Names Pass Through `slugify` Unchanged
`slugify_filename()` does not transliterate CJK characters, so Chinese domain names like `骨科` produce `骨科.base` directly rather than being transliterated to `guke.base`.

**Impact:** Correct behavior for this project — users want Chinese filenames to remain Chinese. But surprising if the developer assumed slugify would produce ASCII-only filenames.

**Source:** 03-01-SUMMARY.md
