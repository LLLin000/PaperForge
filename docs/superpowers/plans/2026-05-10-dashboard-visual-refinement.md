# PaperForge Dashboard Visual Refinement Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or inline execution. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Apply Native Light Surface Design spec — strict typography, minimal containers, Obsidian-native colors, no decorative shadows, locale-unified UI text.

**Architecture:** CSS-first: establish --pf-* custom properties and .pf-* utility classes on `.paperforge-status-panel`, then rewrite Sections 39-43 with constrained typography (4 sizes, 3 weights), light borders, and contextual cards only for primary content modules. JS: restructure per-paper layout to merge header/status/files rows, collapse OCR/Analyze into technical details, compact "All Set" state.

**Tech Stack:** Obsidian DOM API (vanilla JS), CSS with Obsidian semantic variables only.

**Commit style:** `type(scope): description` (English, semantic, existing pattern).

---

## Files
- Modify: `paperforge/plugin/styles.css` (large rewrite of Sections 39-43)
- Modify: `paperforge/plugin/main.js` (per-paper layout + locale text)

---

### Task 1: Commit current CSS base changes

**Files:** styles.css (staged change on paperforge-status-panel + utility classes)

- [ ] Git commit the pending styles.css change

```bash
git add paperforge/plugin/styles.css
git commit -m "style(dashboard): establish CSS base --pf-* vars, typography tokens, utility classes"
```

---

### Task 2: Rewrite CSS Section 39 — Shared components

**Files:** styles.css (replace Section 39 "Shared Components")

Replace the existing Section 39 with:
- `.pf-card` — only for primary content modules (no box-shadow)
- `.pf-pill` + modifiers `.pf-pill--ok/warn/fail` — 999px radius, subtle
- `.pf-btn-secondary` / `.pf-btn-primary` — Obsidian interactive vars
- `.pf-complete-row` — compact green text, no card
- `.pf-disclosure-row` + `.pf-disclosure-body` — simple text+cursor
- `.pf-section-label` — 12px/600/uppercase/no accent border
- `.pf-stack-8` / `.pf-stack-12` — spacing utilities
- Remove old `.paperforge-section-label` left-border accent
- Remove old contextual button styles (replaced by pf-btn-*)
- Remove old card ::before elevation pseudo-elements

---

### Task 3: Rewrite CSS Section 40 — Per-paper view

**Files:** styles.css (replace Section 40)

Apply constrained typography to per-paper components:
- `.paperforge-paper-header`: title 16px/600, meta 13px/400, year 12px/400 (no bullet separator, use ` · `)
- `.paperforge-status-strip`: remove borders, keep flex + gap
- `.paperforge-status-pill`: inherit `.pf-pill` patterns (no colored backgrounds, text-only status colors)
- `.paperforge-paper-overview`: use `.pf-card` base (no shadow, no ::before)
- `.paperforge-discussion-card`: use `.pf-card` base (no shadow, no ::before)
- `.paperforge-discussion-q`: 14px/600
- `.paperforge-discussion-a`: 14px/400
- `.paperforge-discussion-expand`: text accent only
- `.paperforge-paper-files`: move inline with status strip
- `.paperforge-technical-details-toggle`: use `.pf-disclosure-row` style
- `.paperforge-technical-details-body`: use `.pf-disclosure-body` style
- `.paperforge-workflow-toggles`: NOT a card (remove background, border, shadow). Simple flex row.
- Dark theme overrides: remove shadow rules, keep only background/border tweaks

---

### Task 4: Rewrite CSS Section 41 — Collection/Base

**Files:** styles.css (replace Section 41)

- `.paperforge-workflow-overview`: `.pf-card` base, remove shadow
- `.paperforge-workflow-stage-value`: 18px/600, accent only for metric
- `.paperforge-collection-header`: title 16px/600
- `.paperforge-issue-summary`: light border-left accent (orange), no full red border
- `.paperforge-collection-actions`: simple flex row

---

### Task 5: Rewrite CSS Section 42 — Global/Home

**Files:** styles.css (replace Section 42)

- `.paperforge-library-snapshot`: `.pf-card` base, remove shadow
- `.paperforge-system-status`: `.pf-card` base, remove shadow
- `.paperforge-global-actions`: `.pf-card` base, remove shadow
- `.paperforge-snapshot-value`: 18px/600
- `.paperforge-status-row`: dot stays, label 14px

---

### Task 6: Rewrite JS per-paper layout (merge header + status strip + file row)

**Files:** main.js — `_renderPaperMode` and helpers

Layout per spec:
```
[PAPER badge] title
authors · year
[PDF ✓] [OCR ✓] [精读 ✓]    [打开 PDF] [打开全文]
┌ 文章概览 ─────────────┐
└──────────────────────┘
✓ 已完成，可直接使用
┌ 最近讨论 ─────────────┐
└──────────────────────┘
技术详情 ▸
```

Changes:
1. Status strip: place PDF pill + OCR pill + DeepRead pill left, Open PDF + Open Fulltext right (same flex row)
2. No separate `paperforge-paper-files` section below — file buttons ARE in the status row
3. Workflow toggles (OCR/Analyze checkbox): remove from standalone section, move into `_renderPaperTechnicalDetails` disclosure body
4. Next step card: when `nextStep === 'ready'`, render compact `.pf-complete-row` instead of card
5. Next step card: remove `'RECOMMENDED NEXT STEP'` all-caps label, use "下一步" (zh) / "Next Step" (en)
6. Locale: all UI text use Chinese when T===zh

---

### Task 7: Locale cleanup

**Files:** main.js — ensure all visible UI labels are locale-consistent

- "Open PDF" → `t('open_pdf')` or hardcoded 中文 `打开 PDF`
- "Open Fulltext" → `打开全文`
- "Copy /pf-deep Command" → `复制精读命令` or remove
- "Run in {0}" → remove or make Chinese
- Next-step labels: use Chinese when zh
- Section labels: "文章概览" stays, "最近讨论" stays, "技术详情" stays
- "Add to OCR Queue" → `加入 OCR`
- "Remove from OCR Queue" → `移出 OCR`
- "Analyze" label → `精读` / `标记精读`

Add missing i18n keys to LANG.zh and LANG.en.

---

### Task 8: Regression verification

- [ ] Verify syntax: `node --check main.js`
- [ ] Run tests: `npx vitest run` (all 40 pass)
- [ ] Copy to test vault
- [ ] Visual check: per-paper with 3EWBBTAS (deep-read done), 2Y9M3ILK (discussion), B29TFCL4 (no OCR)
- [ ] Check global view layout
- [ ] Check collection view layout
- [ ] Check dark theme (toggle Obsidian theme to dark)
- [ ] Check narrow sidebar width

---

## Non-goals
- Don't add new fonts
- Don't add decorative shadows to cards
- Don't add colored backgrounds to status pills
- Don't use more than 4 font sizes
- Don't use font-weight 700
- Don't rebuild existing working modules (only restructure layout, not logic)
