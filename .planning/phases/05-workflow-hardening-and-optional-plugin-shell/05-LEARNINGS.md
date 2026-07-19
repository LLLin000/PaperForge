---
phase: 05
phase_name: "Workflow Hardening and Optional Plugin Shell"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 7
  lessons: 3
  patterns: 4
  surprises: 3
missing_artifacts:
  - "UAT.md"
  - "VERIFICATION.md"
---

# Phase 05 Learnings: Workflow Hardening and Optional Plugin Shell

## Decisions

### D1: OCR State Machine Tests Cover 7 States
The state machine tests cover: pending, queued, running, done, error, blocked, and nopdf — all 7 OCR job states.

**Rationale:** Comprehensive coverage of all possible OCR job lifecycle states ensures that state transitions are handled correctly and no edge case crashes the worker.

**Source:** 05-01-PLAN.md, 05-01-SUMMARY.md

---

### D2: Blocked State Triggered via HTTPError 401 — Not Env Manipulation
Instead of patching environment variables to simulate a missing token (which doesn't work due to always-present registry tokens), the blocked state is triggered by making `requests.post` raise `HTTPError(401)` with `response.status_code=401`.

**Rationale:** The registry token is always present in the test environment, making `patch.dict(os.environ, {}, clear=True)` ineffective. HTTP 401 directly triggers the `classify_error` path that produces the `'blocked'` state.

**Source:** 05-01-SUMMARY.md

---

### D3: `ensure_ocr_meta` Patched with `side_effect` Factory (Not `return_value`)
The `ensure_ocr_meta` function is patched with `side_effect=make_meta` where `make_meta` is a factory function returning a fresh dict on each call, rather than `return_value={}` which would reuse the same dict.

**Rationale:** When called multiple times in a loop, the caller mutates the returned dict. A shared dict causes all subsequent iterations to see accumulated mutations.

**Source:** 05-01-SUMMARY.md

---

### D4: 13 End-to-End Smoke Tests Cover Full Pipeline
The smoke test suite (`test_smoke.py`) contains 13 tests across 6 categories: setup validation, selection sync, index refresh, OCR doctor (L1-L3 mocked), deep-reading queue, and CLI main entry.

**Rationale:** Ensures the entire pipeline — from `paperforge doctor` setup validation through `deep-reading` queue — can execute without crashing, using mocked external dependencies.

**Source:** 05-02-PLAN.md, 05-02-SUMMARY.md

---

### D5: Smoke Tests Use `tmp_path` Fixture Vault — Never Real Vault
Every smoke test creates a complete vault structure under `tmp_path` using the `fixture_vault` factory fixture. No test accesses the real user vault.

**Rationale:** Test isolation and safety — a bug in a test should never affect the user's real data. The fixture vault includes paperforge.json, directory structure, mock library records, and BBT export JSON.

**Source:** 05-02-PLAN.md, 05-02-SUMMARY.md

---

### D6: All Network Calls Mocked — No Live API in Tests
OCR diagnostics tests mock `requests.get` and `requests.post` via `unittest.mock.patch` to verify the full diagnostic flow without hitting the real PaddleOCR API.

**Rationale:** Tests must be hermetic and fast. Live API calls would introduce network dependency, rate limits, and timing issues into the test suite.

**Source:** 05-02-PLAN.md, 05-02-SUMMARY.md

---

### D7: Fixture Library Records Use `TESTKEY001/002/003`
Mock library records use predictable zotero_keys (`TESTKEY001`, `TESTKEY002`, `TESTKEY003`) that are easy to debug in test output.

**Rationale:** Predictable test data makes test failures easier to diagnose. The sequential key pattern also verifies that the system handles multiple records correctly in batch operations.

**Source:** 05-02-PLAN.md, 05-02-SUMMARY.md

---

## Lessons

### L1: Registry Token Makes Env-Based Test Patterns Unreliable
The PaddleOCR registry token is always present in the test environment. Patching `os.environ` to remove it has no effect on the actual token resolution path (which reads from Windows registry).

**Context:** This required 7 attempts to fix `test_missing_token_blocks_job` before finding the working approach: inject HTTPError 401 as a side_effect on the mocked `requests.post` to trigger the `classify_error` → `'blocked'` mapping.

**Source:** 05-01-SUMMARY.md

---

### L2: `ensure_ocr_meta` Dict Mutation Requires Factory Pattern
When `ensure_ocr_meta` is patched with `return_value={}`, all callers in the loop receive the same dict object. Mutations by one iteration affect all subsequent iterations.

**Context:** The run_ocr function iterates over queue items, each time calling `ensure_ocr_meta()` and then mutating the returned dict. Using `side_effect` with a factory creates independent dicts per call.

**Source:** 05-01-SUMMARY.md

---

### L3: `cleanup_blocked_ocr_dirs` Has Selective Cleanup Behavior
The cleanup function does NOT blindly remove all blocked directories — it preserves directories that contain a `fulltext.md` payload (indicating partial previous OCR results) and only removes empty blocked directories.

**Context:** This selective behavior prevents data loss where a blocked job may have produced partial results. The test suite includes tests for both cases (preserve vs remove) to lock this behavior.

**Source:** 05-01-SUMMARY.md

---

## Patterns

### P1: Fixture Factory Pattern for Test Vault Creation
A pytest fixture function that builds a complete vault directory tree under `tmp_path` with paperforge.json, directory structure, library records, and BBT export files. Every test gets an isolated, reproducible vault.

**When to use:** When multiple tests need a realistic project structure but must never touch the real user data. The fixture factory guarantees isolation and reproducibility.

**Source:** 05-02-PLAN.md, 05-02-SUMMARY.md

---

### P2: Mocked HTTP via `unittest.mock.patch`
Use `unittest.mock.patch` to replace `requests.get` and `requests.post` with MagicMock objects that return controlled responses. Side effects raise exceptions for error-path testing.

**When to use:** Testing code paths that make HTTP calls where you need to control response content, status codes, and error conditions without a real network.

**Source:** 05-02-PLAN.md, 05-02-SUMMARY.md

---

### P3: Side-Effect Factory Pattern for Mutable Return Values
When a mocked function returns a mutable object (like a dict) that the caller mutates, use `side_effect` with a factory function (not `return_value` with a single object) to produce a fresh object on each call.

**When to use:** When a mocked function is called multiple times and the caller mutates the return value. A single shared object would accumulate state across calls.

**Source:** 05-01-SUMMARY.md

---

### P4: Real Minimal PDF Creation for File I/O Tests
Create a real (minimal) PDF file on disk using `b"%PDF-1.4\n..."` bytes for tests that need actual PDF file I/O, as opposed to mocking the file existence check.

**When to use:** When testing file operations where you need actual file I/O behavior (open, read, stat) rather than just existence checks. A bytes-based stub file avoids external fixture dependencies.

**Source:** 05-02-SUMMARY.md

---

## Surprises

### S1: 7 Attempts to Fix `test_missing_token_blocks_job`
The blocked state test for missing tokens required 7 implementation attempts because the standard `patch.dict(os.environ, {}, clear=True)` approach was ineffective — the registry token is always present in the test environment.

**Impact:** Delayed completion of Plan 05-01 Task 1 by approximately 15 minutes. Ultimately fixed by using HTTPError 401 as a side_effect to trigger the `classify_error` path directly. This is now a documented testing pattern (see L1 above).

**Source:** 05-01-SUMMARY.md

---

### S2: Zero Deviations in Plan 05-02
The smoke test plan (05-02) was executed exactly as written with no deviations, no issues encountered, and no auto-fixes needed.

**Impact:** All 13 smoke tests passed on first implementation attempt. The fixture factory pattern and tmp_path isolation worked exactly as designed.

**Source:** 05-02-SUMMARY.md

---

### S3: Existing Base View Tests Already Covered Custom Paths
During Plan 05-01 Task 2 (base rendering with custom paths), it was discovered that the existing `test_base_views.py` (12 tests) and `test_base_preservation.py` (9 tests) already adequately covered custom path rendering via `substitute_config_placeholders` tests and force/non-force merge behavior.

**Impact:** No new tests were needed for Task 2 — the existing 21 tests provided sufficient coverage. Saved approximately 20 minutes of test authoring.

**Source:** 05-01-SUMMARY.md
