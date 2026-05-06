# Plan 34-01: Jump to Deep Reading Button — Summary

## What Was Built

Added a "Jump to Deep Reading" button to the per-paper dashboard's next-step recommendation card.

### Changes to `paperforge/plugin/main.js`

**Task 1 — i18n keys:**
- Added `jump_to_deep_reading` to LANG.en ("Open Deep Reading") and LANG.zh ("跳转到精读")
- Added `deep_reading_not_found` to LANG.en ("Deep reading file not found") and LANG.zh ("精读文件未找到")

**Task 2 — Conditional button rendering in `_renderNextStepCard()`:**
- When `nextStep === 'ready'` AND `entry.deep_reading_path` exists AND `entry.deep_reading_status === 'done'`: shows jump-to-deep-reading button with magnifying glass icon
- Click handler follows `getAbstractFileByPath()` → `openLinkText()` pattern with `Notice()` on missing file
- Falls back to existing "Copy Context" button when deep reading conditions are not met

### Decisions Implemented (all 5 of 5 from CONTEXT.md)
| Decision | Status |
|----------|--------|
| D-01: Jump button in next-step card (ready state) | ✓ |
| D-03: Button hidden when conditions not met | ✓ |
| D-04: getAbstractFileByPath + openLinkText | ✓ |
| D-05: Notice on missing file | ✓ |
| D-08: Magnifying glass icon | ✓ |

### Files Modified
- `paperforge/plugin/main.js` — i18n keys + conditional render logic

## Self-Check
- JS syntax: OK
- i18n keys: 2 keys × 2 languages = 4 entries confirmed
- Conditional condition: `deep_reading_status === 'done'` present in render logic
- `openLinkText`: 2 matches (new button + existing _openFulltext)
- Copy Context preserved as fallback in else branch
