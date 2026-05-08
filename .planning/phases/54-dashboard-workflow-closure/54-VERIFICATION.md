# Phase 54 Verification: Dashboard Workflow Closure & Onboarding Surface

**Date:** 2026-05-08
**Branch:** milestone/v1.12-install-runtime-closure

---

## Verification Checklist

### [PASS] 1. OCR Queue Add/Remove Buttons on Per-Paper Card

- **Location:** `_renderPaperMode()` in main.js
- **Implementation:** OCR queue control row with toggle button added after maturity gauge, before next-step card
- **Mechanism:** Uses `this.app.fileManager.processFrontMatter()` to set `do_ocr` true/false on the note file
- **i18n:** Button text uses `t('ocr_queue_add')` / `t('ocr_queue_remove')`, notices use `t('ocr_queue_added')` / `t('ocr_queue_removed')`
- **Hint:** Shows "OCR pending" or "OCR already done" via `.paperforge-ocr-queue-hint` when `do_ocr` is true
- **Verification:** `main.js` contains `processFrontMatter` and `do_ocr` references

### [PASS] 2. /pf-deep Copy Button Copies Full Command

- **Location:** `_renderNextStepCard()` in main.js
- **Before:** Copied only the zotero key
- **After:** Copies full command `'/pf-deep ' + key` to clipboard
- **Button label:** Uses `t('copy_pf_deep_cmd')` = "Copy /pf-deep Command"
- **Notice:** Shows full command, e.g. "/pf-deep ABCDEFG copied"

### [PASS] 3. Agent Platform Label

- **Location:** Below the /pf-deep copy button in `_renderNextStepCard()`
- **Implementation:** Reads `this.plugin.settings?.agent_platform` (defaults to `'opencode'`)
- **CSS class:** `.paperforge-agent-platform-label`
- **i18n:** Uses `t('run_in_agent').replace('{0}', platform)` = "Run in opencode"

### [PASS] 4. Privacy Modal Shows Once Per Session Before OCR

- **Location:** `_runAction()` in main.js
- **Implementation:** Privacy check intercepts `a.id === 'paperforge-ocr'` when `this._ocrPrivacyShown` is false
- **Modal class:** `PaperForgeOcrPrivacyModal` extends `Modal`
- **Flag:** `this._ocrPrivacyShown` initialized `false` in constructor, set `true` on "I Understand" click
- **CSS:** `.paperforge-ocr-privacy-modal`, `.paperforge-ocr-privacy-warning`, `.paperforge-ocr-privacy-actions`
- **i18n keys:** `ocr_privacy_title`, `ocr_privacy_warning`, `ocr_understand`

### [PASS] 5. "Run All Pending OCR" Quick Action

- **Location:** `_renderOcr()` calls `this._renderPendingOcrAction(pending)` appended after OCR counts
- **Method:** `_renderPendingOcrAction(pending)` added after `_renderActions()`
- **Behavior:** Creates a styled action card `.paperforge-pending-ocr-action` in the actions grid when `pending > 0`
- **Click handler:** Finds the `paperforge-ocr` action and calls `this._runAction()`
- **Stale cleanup:** Removes existing `.paperforge-pending-ocr-action` before re-render

### [PASS] 6. docs/INSTALLATION.md and docs/setup-guide.md Deleted

- `docs/INSTALLATION.md`: DELETED
- `docs/setup-guide.md`: DELETED
- Verified via `Test-Path`: both return `False`

### [PASS] 7. README.md References Consistent

- Removed rows for `docs/setup-guide.md` and `docs/INSTALLATION.md` from the Documents table
- Remaining refs: AGENTS.md, CHANGELOG.md, CONTRIBUTING.md
- No stale references to deleted docs files

### [PASS] 8. AGENTS.md Updated

- First line changed from referencing `docs/setup-guide.md` and `docs/INSTALLATION.md`
- Now reads: "如果还没有安装 PaperForge，请通过 Obsidian 插件市场安装，或查看 [README.md](README.md) 中的安装说明。"

---

## File Changes Summary

| File | Action | Plan |
|------|--------|------|
| `paperforge/plugin/main.js` | Modified | 54-001, 54-003 |
| `paperforge/plugin/styles.css` | Modified | 54-001, 54-003 |
| `README.md` | Modified | 54-002 |
| `AGENTS.md` | Modified | 54-002 |
| `docs/INSTALLATION.md` | Deleted | 54-002 |
| `docs/setup-guide.md` | Deleted | 54-002 |

---

## Commits

- `{hash}`: feat(54-001): add i18n keys for OCR queue, /pf-deep handoff, and privacy labels
- `{hash}`: feat(54-001): add OCR queue buttons, /pf-deep full command copy, pending OCR action, CSS
- `{hash}`: docs(54-002): delete pip-first docs files, update README.md and AGENTS.md references
- `{hash}`: feat(54-003): add once-per-session OCR privacy warning modal and session flag
- `{hash}`: docs(54): add verification document and state updates

---

## Verification Result

**STATUS: ALL CHECKS PASSED**

All 8 verification criteria confirmed. Plans 54-001, 54-002, and 54-003 implemented completely.
