# Phase 31: Bug Fixes — Summary

**Status:** Complete ✅

## One-Liner
Restored version number display from canonical index envelope; removed meaningless "AI Ready" lifecycle stage from plugin dashboard.

## Key Deliverables
- `_fetchStats()` reads `paperforge_version` from `formal-library.json` envelope (line 382, `index.paperforge_version`)
- "AI Ready" lifecycle stage removed from dashboard stepper and bar chart — lifecycle keys are now: `indexed`, `pdf_ready`, `fulltext_ready`, `deep_read_done`, `ai_context_ready`
- Collection mode lifecycle thresholds fixed to match actual Python compute values
