# Phase 31: Bug Fixes — Context

## Domain Research

### Bug 1: Version Number Not Displayed (NAV-02)

**Root cause (confirmed by code audit):**
- `asset_index.py:build_envelope()` outputs `{schema_version, generated_at, paper_count, items}` — no `paperforge_version` field.
- Plugin `main.js:358` reads version from `_cachedStats.version`, which defaults to `\u2014` (em dash) on first load.
- Plugin `main.js:281` sets initial badge text to `'v\u2014'`.
- `main.js:459` updates badge via `d.version ? 'v' + d.version : 'v\u2014'`.
- `status.py:634` already has `"version": __import__("paperforge").__version__` but as a standalone field in `paperforge status --json` — NOT in the canonical index envelope.
- Since the canonical index is the primary data source the plugin reads, version never propagates.

**Fix:**
1. Add `"paperforge_version": __import__("paperforge").__version__` to `build_envelope()` output in `asset_index.py:88-93`.
2. Plugin reads it from `_cachedStats.version` automatically (already wired, just data missing).

### Bug 2: "ai" Row / Element in Dashboard (NAV-03)

**Preliminary finding:**
- No direct match for "ai" as a dashboard row in plugin JS/CSS.
- The lifecycle stepper has `{ key: 'ai_ready', label: 'AI Ready' }` stage (line 569).
- The bar chart has `{ key: 'ai_ready', label: 'AI Ready', cls: 'stage-ai-ready' }` stage (line 678).
- The health matrix has 4 dimensions: PDF, OCR, Note, Asset — no "ai" dimension.
- The metric cards show: Papers, Formal Notes, Exports — no "ai" metric.

**Most likely candidates for "ai row":**
- "AI Ready" stage in lifecycle stepper appearing when no data supports it.
- A rendering artifact or stale element from v1.7 development.
- A specific element in the plugin settings or setup wizard.

**Fix approach:** Audit during execution. Search for any dashboard-rendered "ai" string that appears as a standalone row/section. Remove the rendering code for that element.

## Constraints

- **Zero new dependencies** — plugin stays pure Obsidian JS/CSS, Python uses stdlib only.
- **Backward compatible** — adding `paperforge_version` to envelope must not break existing index consumers (it's additive, readers that ignore unknown fields continue working).
- **Thin-shell** — no business logic migration to JS. Version comes from Python `__init__.py`, flows through envelope.
