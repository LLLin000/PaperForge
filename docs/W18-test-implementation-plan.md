# W18 Test Implementation Plan (Corrected for Accuracy)

**Correction:** Previous gap analysis overestimated coverage in the audit worktree context (`242e16ad`). Key finding: **F-10 timeout stderr fix is NOT in this tree** — it's in `chore/integrate-stale-root` and merged via `fix-view-lifecycle`. This means X06 coverage assessment was premature.

**New approach:** Implement missing tests directly, then re-validate against corrected baseline.

---

## Priority Order

### Immediate (Day 1–2)

#### 1. X09 Soak Test (OcrWorkspaceView lifecycle leak prevention)
**Why critical:** User explicitly flagged timer leak risk; earlier audit found no `onClose()`. F-12 added `onClose()` + `_closed` flag, but no regression test verifying the fix works under repeated stress.

**Test file:** `tests/sandbox/W18-soak-ocrworkspace.py` or `paperforge/plugin/tests/W18-soak-ocrworkspace.test.ts`  
**Scope:** 
- 10× OcrWorkspaceView open → close cycles
- Verify `_searchTimer` cleared each time (no console errors)
- Verify `_closed` flag toggles correctly
- Verify late progress events don't render after closed state
- Resource leak: check JS heap snapshot before/after (optional)

**Expected result:** No memory growth, no detached-DOM renders, no lingering timers.

#### 2. X03 Restore Button Double-Click Guard
**Why critical:** F-3 added `disabled=true` during await; needs regression test confirming double-click doesn't trigger two parallel restores.

**Test file:** `paperforge/plugin/tests/W18-restoredoubleclick.test.ts`  
**Scope:**
- Mock versions restore API (slow response ~5s)
- Click restore button twice rapidly
- Assert second click does nothing (button remains disabled)
- Assert first restore completes successfully
- Assert only one API call made (not two)

**Expected result:** Idempotent behavior; no race condition.

#### 3. X02 Windows Reserved Char Handling
**Why needed:** Existing `test_utils_slugify.py` covers generic slugification but not Windows-specific edge cases.

**Test file:** `tests/test_winspecific_paths.py`  
**Scope:**
- Create PDFs with Windows reserved filenames (CON, PRN, AUX, NUL, COM1–COM9, LPT1–LPT9)
- Create PDFs with >260 char paths (via explicit long strings)
- Verify PaperForge handles these gracefully (error message if unsupported OR successful processing)
- Verify no crash, no undefined behavior

**Expected result:** Either graceful rejection or full support; never crash.

---

### Secondary (Day 3–4)

#### 4. J03 Stop→Restart Recovery
**Why needed:** F-12 added stop/cancellation guards; need verify resume behavior.

**Test file:** `paperforge/plugin/tests/W18-stopresumerecovery.test.ts`  
**Scope:**
- Start OCR build
- Trigger Stop mid-flight
- Verify cancelled state reaches UI
- Restart build from same point
- Verify new build starts fresh (not resumed from partial state)
- Verify operation lock resets correctly

**Expected result:** Clean state transitions; no stale locks.

#### 5. X07 Repair Rollback Integration
**Why needed:** Dry-run/preflight tests exist but rollback path integration missing.

**Test file:** `paperforge/plugin/tests/W18-repairrollbackintegration.test.ts`  
**Scope:**
- Execute repair dry-run
- Execute actual repair
- Execute rollback to pre-repair state
- Verify user vault content preserved (notes/PDFs not corrupted)
- Verify derived indexes rebuilt cleanly

**Expected result:** Data integrity across rollback.

---

### Tertiary (Minor Refinements)

#### 6. X05 Pointer Atomicity Edge Case
**Why minor:** Existing coverage strong; only need ensure F-12 onClose doesn't interfere.

**Change:** Add assertion in existing pointer tests that onClose clears search timer independently of pointer lifecycle.

**Priority:** Low (can be done as part of X09 soak test).

---

## Implementation Notes

1. **All tests scoped to Windows 11 x64** per P0-A frozen contract. No macOS/Linux/Python 3.13+ edge cases needed for release acceptance.
2. **No architectural changes required** — tests sit on top of existing guards (F-10/F-12/F-3).
3. **Run locally on Windows machine** or CI runner with Windows environment.
4. **Estimated timeline:** 
   - Day 1: Write X09 + X03 tests + CI setup
   - Day 2: Run & iterate tests; start X02 test
   - Day 3: Complete X02 + X03 + J03 tests
   - Day 4: X07 + refinements + final validation

---

## Validation Criteria

Once all tests pass:
- ✅ 10× soak cycles complete without leaks
- ✅ Double-click restore fails safely (disabled state enforced)
- ✅ Windows reserved chars handled gracefully
- ✅ Stop→restart recovers cleanly
- ✅ Repair rollback preserves data integrity

This satisfies W18 resilience requirements for P0-A scope. Proceed to W19 (supported environments/installers) after completion.

---

## Next Step

Start writing **X09 soak test** now. It's the most urgent (timer leak + resource leak risk), has clear pass/fail criteria, and ties directly into F-12 correction we already landed.

Shall I generate the X09 test file immediately? Or prefer other priority first?
