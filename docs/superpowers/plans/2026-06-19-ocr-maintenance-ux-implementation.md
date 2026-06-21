# OCR Maintenance UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the plugin Maintenance tab so ordinary users see actionability-first OCR guidance instead of raw maintenance table state.

**Architecture:** Keep `paperforge/worker/ocr_maintenance.py` as the backend truth source. Add a small UI-side categorization layer for `No Action Needed`, `Rebuild Recommended`, `OCR Failed`, and `Result Limited`, then rework `_renderMaintenanceTab()` to show a summary card, actionable sections, and a collapsed full table. Preserve existing maintenance commands and detailed data via progressive disclosure.

**Tech Stack:** TypeScript, Obsidian plugin DOM APIs, Vitest, esbuild, existing Python-backed OCR maintenance rows.

---

## File Structure

### Files to modify

- `paperforge/plugin/src/settings.ts`
  - Replace the current table-first Maintenance tab rendering with summary-first sections.
  - Wire category mapping, helper copy, disclosure details, and advanced full-table fallback.
- `paperforge/plugin/styles.css`
  - Add focused styles for the new summary card, category chips, action cards, limitation section, and advanced details.
- `paperforge/plugin/src/i18n.ts`
  - Add user-facing copy keys for the new Maintenance tab language so the tab does not hardcode raw engineering terminology.
- `paperforge/plugin/main.js`
  - Rebuild bundled plugin output after TypeScript changes.
- `PROJECT-MANAGEMENT.md`
  - Record the implemented UX redesign once the code is finished and verified.

### Files to create

- `paperforge/plugin/src/services/ocr-maintenance-ui.ts`
  - Pure functions for mapping backend rows into user-facing categories, summary counts, and explanation strings.
- `paperforge/plugin/tests/ocr-maintenance-ui.test.ts`
  - Unit coverage for the categorization and explanation rules.

### Existing files to reference while implementing

- `paperforge/worker/ocr_maintenance.py`
  - Backend truth for `recommended_action`, `status`, `degraded_reasons`, and `error_summary`.
- `docs/superpowers/specs/2026-06-19-ocr-maintenance-ux-design.md`
  - Approved design contract.

---

### Task 1: Add a Pure UI Categorization Layer

**Files:**
- Create: `paperforge/plugin/src/services/ocr-maintenance-ui.ts`
- Test: `paperforge/plugin/tests/ocr-maintenance-ui.test.ts`

- [ ] **Step 1: Write the failing test for category mapping**

```ts
import { describe, expect, it } from 'vitest';
import { categorizeMaintenanceRow, buildMaintenanceSummary } from '../src/services/ocr-maintenance-ui';

describe('categorizeMaintenanceRow', () => {
  it('maps rebuild recommendation to Rebuild Recommended', () => {
    const result = categorizeMaintenanceRow({
      key: 'A1',
      title: 'Paper A',
      status: 'done_degraded',
      health: 'yellow',
      recommended_action: 'rebuild',
      degraded_reasons: ['weak span coverage (62%)'],
      error_summary: '',
      error_stage: '',
      version: 'v2',
      finished_at: '06-19 10:00',
      model: 'PaddleOCR-VL-1.6',
    } as any);

    expect(result.category).toBe('rebuild');
    expect(result.label).toBe('Rebuild Recommended');
    expect(result.primaryAction).toBe('rebuild');
  });

  it('maps failed OCR to OCR Failed and only then promotes rerun', () => {
    const result = categorizeMaintenanceRow({
      key: 'B1',
      title: 'Paper B',
      status: 'failed',
      health: '-',
      recommended_action: 'redo',
      degraded_reasons: [],
      error_summary: 'timeout',
      error_stage: 'poll',
      version: 'v2',
      finished_at: '06-19 11:00',
      model: 'PaddleOCR-VL-1.6',
    } as any);

    expect(result.category).toBe('failed');
    expect(result.label).toBe('OCR Failed');
    expect(result.primaryAction).toBe('redo');
  });

  it('keeps non-actionable degraded papers in Result Limited', () => {
    const result = categorizeMaintenanceRow({
      key: 'C1',
      title: 'Paper C',
      status: 'done_degraded',
      health: 'yellow',
      recommended_action: '',
      degraded_reasons: ['weak body spine'],
      error_summary: '',
      error_stage: '',
      version: 'v2',
      finished_at: '06-19 12:00',
      model: 'PaddleOCR-VL-1.6',
    } as any);

    expect(result.category).toBe('limited');
    expect(result.label).toBe('Result Limited');
    expect(result.primaryAction).toBeNull();
  });

  it('keeps clean completed rows in No Action Needed', () => {
    const result = categorizeMaintenanceRow({
      key: 'D1',
      title: 'Paper D',
      status: 'done',
      health: 'green',
      recommended_action: '',
      degraded_reasons: [],
      error_summary: '',
      error_stage: '',
      version: 'v2',
      finished_at: '06-19 13:00',
      model: 'PaddleOCR-VL-1.6',
    } as any);

    expect(result.category).toBe('ok');
    expect(result.label).toBe('No Action Needed');
  });
});

describe('buildMaintenanceSummary', () => {
  it('counts categories and builds the top-level verdict', () => {
    const summary = buildMaintenanceSummary([
      { category: 'ok' },
      { category: 'rebuild' },
      { category: 'failed' },
      { category: 'limited' },
    ] as any);

    expect(summary.counts).toEqual({ ok: 1, rebuild: 1, failed: 1, limited: 1 });
    expect(summary.tone).toBe('warn');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- ocr-maintenance-ui.test.ts`
Expected: FAIL with `Cannot find module '../src/services/ocr-maintenance-ui'` or missing export errors.

- [ ] **Step 3: Write the minimal implementation**

```ts
export type MaintenanceCategory = 'ok' | 'rebuild' | 'failed' | 'limited';
export type MaintenanceAction = 'rebuild' | 'redo' | null;

export type MaintenanceRowLike = {
  key: string;
  title: string;
  status: string;
  health: string;
  recommended_action: string;
  degraded_reasons: string[];
  error_summary: string;
  error_stage: string;
  version: string;
  finished_at: string;
  model: string;
};

export function categorizeMaintenanceRow(row: MaintenanceRowLike) {
  if (row.recommended_action === 'rebuild') {
    return {
      category: 'rebuild' as const,
      label: 'Rebuild Recommended',
      primaryAction: 'rebuild' as const,
      reason: 'Derived OCR results can be regenerated from existing OCR data.',
    };
  }

  if (row.status === 'failed') {
    return {
      category: 'failed' as const,
      label: 'OCR Failed',
      primaryAction: 'redo' as const,
      reason: row.error_summary || 'OCR did not finish successfully.',
    };
  }

  if ((row.degraded_reasons || []).length > 0 || row.status === 'done_degraded') {
    return {
      category: 'limited' as const,
      label: 'Result Limited',
      primaryAction: null,
      reason: row.degraded_reasons?.[0] || 'This paper has weaker confidence signals, but no clear maintenance action is recommended.',
    };
  }

  return {
    category: 'ok' as const,
    label: 'No Action Needed',
    primaryAction: null,
    reason: 'OCR results look usable and no maintenance action is recommended.',
  };
}

export function buildMaintenanceSummary(items: Array<{ category: MaintenanceCategory }>) {
  const counts = { ok: 0, rebuild: 0, failed: 0, limited: 0 };
  for (const item of items) counts[item.category] += 1;
  const tone = counts.failed > 0 || counts.rebuild > 0 ? 'warn' : 'ok';
  return { counts, tone };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- ocr-maintenance-ui.test.ts`
Expected: PASS for the new categorization tests.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/src/services/ocr-maintenance-ui.ts paperforge/plugin/tests/ocr-maintenance-ui.test.ts
git commit -m "feat: add OCR maintenance UI categorization"
```

### Task 2: Replace Table-First Maintenance Rendering with Summary-First UX

**Files:**
- Modify: `paperforge/plugin/src/settings.ts`
- Modify: `paperforge/plugin/src/i18n.ts`
- Test: `paperforge/plugin/tests/ocr-maintenance-ui.test.ts`

- [ ] **Step 1: Extend tests to lock the user-facing explanation rules**

```ts
it('uses rebuild-first copy for actionable items', () => {
  const result = categorizeMaintenanceRow({
    key: 'R1',
    title: 'Paper R',
    status: 'done_degraded',
    health: 'yellow',
    recommended_action: 'rebuild',
    degraded_reasons: ['weak span coverage (51%)'],
    error_summary: '',
    error_stage: '',
    version: 'v2',
    finished_at: '06-19 14:00',
    model: 'PaddleOCR-VL-1.6',
  } as any);

  expect(result.reason).toContain('existing OCR data');
});

it('does not promote redo for non-failed rows', () => {
  const result = categorizeMaintenanceRow({
    key: 'R2',
    title: 'Paper R2',
    status: 'done_degraded',
    health: 'yellow',
    recommended_action: 'redo',
    degraded_reasons: ['weak body spine'],
    error_summary: '',
    error_stage: '',
    version: 'v2',
    finished_at: '06-19 14:10',
    model: 'PaddleOCR-VL-1.6',
  } as any);

  expect(result.category).toBe('limited');
  expect(result.primaryAction).toBeNull();
});
```

- [ ] **Step 2: Run tests to verify the new cases fail if the mapper is still too naive**

Run: `npm test -- ocr-maintenance-ui.test.ts`
Expected: FAIL if `recommended_action === 'redo'` is still being promoted outside real failure states.

- [ ] **Step 3: Update the mapper and build the new Maintenance tab sections**

```ts
// settings.ts
import {
  buildMaintenanceSummary,
  categorizeMaintenanceRow,
} from './services/ocr-maintenance-ui';

// inside _renderMaintenanceTab callback, after rows load
const items = rows.map((row: any) => ({ row, ui: categorizeMaintenanceRow(row) }));
const summary = buildMaintenanceSummary(items.map(item => item.ui));
const actionable = items.filter(item => item.ui.category === 'rebuild' || item.ui.category === 'failed');
const limited = items.filter(item => item.ui.category === 'limited');
const okItems = items.filter(item => item.ui.category === 'ok');

const hero = containerEl.createDiv({ cls: 'pf-maint-hero pf-card' });
hero.createEl('h3', { text: summary.tone === 'warn'
  ? `OCR needs attention: ${summary.counts.rebuild} rebuild, ${summary.counts.failed} failed.`
  : 'OCR looks usable overall.' });
hero.createEl('p', {
  text: 'This page only promotes issues where maintenance is likely to help. Some papers may have limitations that maintenance will not improve.',
  cls: 'setting-item-description',
});

const counts = hero.createDiv({ cls: 'pf-maint-counts' });
for (const [label, value] of [
  ['No Action Needed', summary.counts.ok],
  ['Rebuild Recommended', summary.counts.rebuild],
  ['OCR Failed', summary.counts.failed],
]) {
  const stat = counts.createDiv({ cls: 'pf-maint-stat' });
  stat.createEl('strong', { text: String(value) });
  stat.createEl('span', { text: label });
}

renderMaintenanceSection(containerEl, 'Needs Attention', actionable, { showPrimaryAction: true });
renderMaintenanceSection(containerEl, 'Result Limitations', limited, { showPrimaryAction: false, intro: 'These papers look less certain, but PaperForge does not currently have a high-confidence maintenance action to recommend.' });

const advanced = containerEl.createEl('details', { cls: 'pf-maint-advanced' });
advanced.createEl('summary', { text: `All Papers (${rows.length})` });
renderMaintenanceTable(advanced, rows);
```

```ts
// i18n.ts
ocr_maint_title: 'Maintenance',
ocr_maint_hero_note: 'This page only promotes issues where maintenance is likely to help.',
ocr_maint_no_action: 'No Action Needed',
ocr_maint_rebuild: 'Rebuild Recommended',
ocr_maint_failed: 'OCR Failed',
ocr_maint_limited: 'Result Limited',
ocr_maint_rebuild_help: 'Rebuild regenerates OCR-derived results from existing OCR data. It does not call the OCR service again.',
ocr_maint_redo_help: 'Rerun OCR is only recommended when OCR clearly failed.',
```

- [ ] **Step 4: Run focused tests after the rendering refactor**

Run: `npm test -- ocr-maintenance-ui.test.ts runtime.test.ts`
Expected: PASS with no regressions in the new helper behavior.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/src/settings.ts paperforge/plugin/src/i18n.ts paperforge/plugin/src/services/ocr-maintenance-ui.ts paperforge/plugin/tests/ocr-maintenance-ui.test.ts
git commit -m "feat: redesign OCR maintenance tab for actionability"
```

### Task 3: Style the New Sections and Preserve Advanced Table Access

**Files:**
- Modify: `paperforge/plugin/styles.css`
- Modify: `paperforge/plugin/src/settings.ts`
- Test: `paperforge/plugin/tests/ocr-maintenance-ui.test.ts`

- [ ] **Step 1: Add a minimal style smoke test target by keeping stable class names**

```ts
// settings.ts class names used by CSS and future DOM assertions
'pf-maint-hero'
'pf-maint-counts'
'pf-maint-stat'
'pf-maint-section'
'pf-maint-card'
'pf-maint-chip'
'pf-maint-actions'
'pf-maint-details'
'pf-maint-advanced'
```

- [ ] **Step 2: Add the CSS for the summary-first layout**

```css
.pf-maint-hero {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.pf-maint-counts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 10px;
}

.pf-maint-stat {
    background: var(--background-primary);
    border: 1px solid var(--pf-border);
    border-radius: var(--pf-radius);
    padding: 10px;
}

.pf-maint-section {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.pf-maint-card {
    background: var(--pf-surface);
    border: 1px solid var(--pf-border);
    border-radius: var(--pf-radius);
    padding: 12px;
}

.pf-maint-chip {
    display: inline-flex;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}

.pf-maint-chip--rebuild { background: color-mix(in srgb, var(--interactive-accent) 12%, transparent); }
.pf-maint-chip--failed { background: color-mix(in srgb, var(--text-error) 14%, transparent); }
.pf-maint-chip--limited { background: color-mix(in srgb, var(--text-warning) 14%, transparent); }
.pf-maint-chip--ok { background: color-mix(in srgb, var(--text-success) 14%, transparent); }

.pf-maint-advanced summary {
    cursor: pointer;
    color: var(--text-muted);
}
```

- [ ] **Step 3: Keep the old full table renderer behind the advanced disclosure instead of deleting it**

```ts
const advanced = containerEl.createEl('details', { cls: 'pf-maint-advanced' });
advanced.createEl('summary', { text: `All Papers (${rows.length})` });
const tableHost = advanced.createDiv();
renderMaintenanceTable(tableHost, rows);
```

- [ ] **Step 4: Run the plugin test suite and rebuild the bundle**

Run: `npm test && npm run build`
Expected: PASS for all Vitest files, then a successful `main.js` rebuild from esbuild.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/styles.css paperforge/plugin/src/settings.ts paperforge/plugin/main.js
git commit -m "feat: style OCR maintenance summary layout"
```

### Task 4: Verify End-to-End Behavior and Record the Change

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`
- Modify: `paperforge/plugin/main.js`

- [ ] **Step 1: Manually verify the core UX paths in the plugin**

```text
Check these states in the Maintenance tab:
1. No rows -> empty state still reads clearly.
2. Rebuild row -> appears under Needs Attention with rebuild-focused copy.
3. Failed row -> appears under Needs Attention with rerun OCR copy.
4. Degraded but non-actionable row -> appears under Result Limitations, not Needs Attention.
5. Full table -> still available inside All Papers disclosure.
```

- [ ] **Step 2: Run final verification commands**

Run: `npm test && npm run build`
Expected: all plugin tests pass, TypeScript emits no errors, esbuild regenerates `main.js`.

- [ ] **Step 3: Update the project log**

```md
### 12.x OCR maintenance UX redesign (2026-06-19)

- Problem: the plugin maintenance tab exposed raw OCR states and pushed ordinary users toward interpreting any warning as a repair task.
- Root cause: the UI was organized around backend table rows instead of actionability.
- Fix: added a UI-side categorization layer, promoted rebuild-only actionable items, limited redo promotion to true failures, and moved the full table into an advanced disclosure.
- Result: ordinary users now see a summary-first maintenance view that distinguishes actionable issues from non-actionable result limitations.
- Test status: `npm test && npm run build` in `paperforge/plugin`.
```

- [ ] **Step 4: Commit the verification and log update**

```bash
git add PROJECT-MANAGEMENT.md paperforge/plugin/main.js
git commit -m "docs: record OCR maintenance UX redesign"
```

## Self-Review

### Spec coverage

- Summary-first judgment: covered by Task 2 hero + counts.
- Actionability-first categories: covered by Task 1 mapper.
- Rebuild promoted over redo: covered by Task 1 and Task 2 tests.
- Redo only for true failure: covered by Task 1 and Task 2 tests.
- Result Limited explanation without false repair pressure: covered by Task 2 section and copy.
- Full technical detail preserved behind disclosure: covered by Task 2 and Task 3 advanced table retention.

### Placeholder scan

- No `TBD`, `TODO`, or “similar to above” placeholders remain.
- Commands, files, and target code shapes are explicit.

### Type consistency

- Category vocabulary is consistent across tasks: `ok`, `rebuild`, `failed`, `limited`.
- Primary actions remain `rebuild | redo | null`.
- UI labels remain `No Action Needed`, `Rebuild Recommended`, `OCR Failed`, `Result Limited`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-ocr-maintenance-ux-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
