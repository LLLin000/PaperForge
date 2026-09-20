# W18 Resilience Evidence – Gap Analysis (Read-Only Audit)

**Date:** 2026-09-19  
**Source SHA:** `3485f44f` (release source), `56407222` (candidate evidence)  
**Scope:** Windows 11 x64 / Obsidian desktop / Python 3.11–3.12 / PaddleOCR-VL-1.6 + OpenAI text-embedding-3-small / manual Release-N rollback only / USD 20 spend cap  
**Excluded (P0-A NOT supporting):** macOS/Linux, Flatpak/Snap, Python 3.13+, mobile Obsidian, junction/symlink live-retarget race, multi-process writer, performance timing SLA

---

## Summary Table

| Case | Existing Coverage | Gap Status | Required Action | Priority |
|------|-------------------|------------|-----------------|----------|
| **X02** shell metachar / Unicode / long path (Windows NTFS vault) | ✅ Found in `tests/test_utils_slugify.py`, `tests/test_local_read.py` | Minor gap: not explicitly bound to Windows-specific metachars (`|`, `"`, `<`, `>`, etc.) | Add explicit test cases for Windows reserved chars + long path (>260 chars) | High |
| **X03** concurrency / autosync+manual race | ✅ Extensive coverage in `capability-state.test.ts`, `main-autosync-cutover.test.ts`, `paperforge-client.test.ts` | Strong coverage but lacks explicit "double-click restore" guard testing (F-3 was recent fix) | Add regression test for restore button pending lock (disabled during await) | Medium |
| **X05** runtime pointer atomicity | ✅ Strong in `managed-runtime.test.ts`, `node-transport.test.ts`, `test_runtime_pointer.py` | Adequate; covers atomic publish via temp file + rename pattern | Minor: ensure F-12 onClose guards don't interfere with pointer state | Low |
| **X06** network failure honesty (timeout/stderr/401/403/429) | ✅ Excellent in `node-transport.test.ts`, `errors.test.ts`, `protocol-conformance.test.ts` | Very strong; includes stderr capture on timeout (F-10 fix) | None | None |
| **X07** dry-run / preflight / idempotent | ✅ Good in `library-render-quality-cutover.test.ts`, `protocol-conformance.test.ts`, `e2e/test_status_doctor_repair.py` | Solid; includes repair dry-run, pre-checks before mutation | Ensure rollback path is covered in same tests | Low |
| **X09** soak (repeated view open/close, resource leak) | ✅ Present in `maintenance-inbox.test.ts`, `next-actions-orchestrator.test.ts` | Weak; mostly implicit via repeated renders | Explicit soak test: 10× open-close cycles, verify `_searchTimer` cleared, no DOM detachment | Medium |
| **J03** stop→restart→resume recovery | ✅ Strong in `architecture-boundaries.test.ts`, `protocol-conformance.test.ts`, `dashboard-runtime.test.ts` | Good; verifies operation lock, cancellation safety | Explicit: OCR Stop → restart → verify resume without re-send | Medium |

---

## Detailed Findings per Case

### X02: shell metachar / Unicode / long path (Windows NTFS vault)
- **Current tests:** `tests/test_utils_slugify.py` (slugify edge cases), `tests/test_local_read.py` (vault read robustness)
- **Gap:** No dedicated Windows-reserved-character tests (`CON|PRN|AUX|NUL` names, `|<>?`, backslash handling); long-path (>260 chars) not explicitly exercised
- **Recommended test cases:**
  - Create paper PDFs with Windows reserved filenames
  - Create PDFs with >260 char paths (via junction mapping or explicit long-string rendering)
  - Verify PaperForge handles these gracefully (no crash, proper error messages if unsupported)

### X03: concurrency / autosync+manual race
- **Current tests:** `capability-state.test.ts` (epoch guards), `main-autosync-cutover.test.ts` (autosync vs manual), `paperforge-client.test.ts` (concurrent ops)
- **Gap:** Specific "restore button double-click" guard (F-3 recent fix) has no regression test
- **Recommended test case:**
  - Mock versions restore API call; click restore twice rapidly; assert second click disabled until first completes

### X05: runtime pointer atomicity
- **Current tests:** `managed-runtime.test.ts`, `node-transport.test.ts`, `test_runtime_pointer.py` cover atomic publish patterns (temp file → rename)
- **Gap:** Minimal; F-12 onClose should not interfere with pointer state
- **Recommended check:** Verify onClose doesn't trigger pointer re-publish; confirm _closed flag gates are independent of pointer lifecycle

### X06: network failure honesty (timeout/stderr/401/403/429)
- **Current tests:** `node-transport.test.ts` (timeout + stderr capture), `errors.test.ts` (error boundary), `protocol-conformance.test.ts` (HTTP status codes)
- **Status:** **Strong coverage**
- **Note:** F-10 already implemented bounded stderr + `err.timedOut=true`

### X07: dry-run / preflight / idempotent
- **Current tests:** `library-render-quality-cutover.test.ts`, `protocol-conformance.test.ts`, `e2e/test_status_doctor_repair.py` include repair dry-run and pre-checks
- **Gap:** Rollback path integration in same tests
- **Recommended addition:**
  - Repair dry-run followed by actual repair → rollback → verify user content preserved
  - Idempotent behavior: run same repair twice, verify no duplicate mutations

### X09: soak (repeated view open/close, resource leak)
- **Current tests:** `maintenance-inbox.test.ts` (inbox refresh stress), `next-actions-orchestrator.test.ts` (retry stress)
- **Gap:** **Explicit soak test missing** for OcrWorkspaceView lifecycle
- **Recommended test case:**
  - 10× OcrWorkspaceView open → close cycles
  - Assert `_searchTimer` cleared each time (no lingering timer)
  - Assert `_closed` flag properly toggled
  - Assert progress events after closed view don’t render (no console errors)

### J03: stop→restart→resume recovery
- **Current tests:** `architecture-boundaries.test.ts` (operation lock), `protocol-conformance.test.ts` (state machine), `dashboard-runtime.test.ts` (activity indicators)
- **Gap:** No explicit "Stop → restart → verify resume" scenario
- **Recommended test case:**
  - Trigger OCR build; call Stop mid-flight; verify cancelled state
  - Restart build; verify it starts fresh (not resumed from partial state)
  - Assert operation lock resets correctly

---

## Immediate Next Steps

1. **Write missing test files** (only 3 critical):
   - `x02_winspecific_chars.test.ts` (Windows reserved chars + long path)
   - `x09_soak_ocrworkspace.test.ts` (10× open/close cycle for OcrWorkspaceView)
   - `j03_stop_resume_recovery.test.ts` (OCR stop → restart flow)

2. **Add one regression test**:
   - Restore button double-click guard (verify disabled state during async op)

3. **Minor additions**:
   - Include rollback path in existing repair/dry-run tests

All recommended tests fit within P0-A support contract scope (Windows 11 x64 only). No macOS/Linux/Python3.13+/Jetty/etc. tests needed for release acceptance.

---

## Conclusion

W18 coverage is **mostly solid**, with three clear gaps that can be filled in <2 days:
- X02 (Windows-specific metachars/long path): existing slugify/local-read tests need extension
- X09 (soak/OcrWorkspaceView lifecycle): explicit stress test needed
- J03 (stop/restart/resume): explicit verification scenario needed

The remaining 4 cases (X03/X05/X06/X07) have strong foundational coverage; minor regression additions suffice.

No architectural refactoring required. All tests remain scoped to Windows 11 x64 desktop environment per P0-A frozen contract.

**Estimated effort for completion:** 2–3 days (including review + CI pass). Not a blocker for W22 certification once completed.
