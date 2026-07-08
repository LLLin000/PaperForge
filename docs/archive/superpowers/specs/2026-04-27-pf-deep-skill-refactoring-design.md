# /pf-deep Skill Refactoring Design

> **Goal**: Refactor ld_deep.py + prompt_deep_subagent.md into atoms/molecules/compounds layers for more deterministic AI behavior, fixing skeleton errors, image placement issues, and figure ordering problems — without changing the deep reading methodology.

---

## Architecture

```
ld_deep.py (target: ~900 lines, split into atoms + molecules)
├── Atoms (pure functions, no agent calls)
│   ├── Fulltext parsing: extract_figures, extract_tables, build_figure_map
│   ├── Skeleton: render_skeleton (figure blocks with fixed structure)
│   └── Postprocessing: validate_order, validate_images_in_callouts, validate_no_placeholders
│
├── Molecules (explicit orchestration, calls atoms only)
│   ├── prepare: figure-map → chart-type → render_skeleton → validate_skeleton
│   └── postprocess-pass2: run all validators → structured error list
│
└── CLI (thin dispatch)
    └── prepare, figure-map, chart-type-scan (existing, unchanged), validate-note, postprocess-pass2 (new)

prompt_deep_subagent.md (target: ~150 lines)
└── Compound (orchestrates molecules + AI passes)
    ├── prepare
    ├── Pass 1 (AI fills skeleton's Pass 1 section)
    ├── Pass 2 (AI fills numbered figure callout blocks in order)
    ├── postprocess-pass2 → fix loop
    ├── Pass 3
    └── validate-note
```

---

## Detailed Design

### 1. Skeleton Generation (render_skeleton)

**Current**: Skeleton rendered by `ensure_study_section()` which inserts generic `> [!note]- Figure N` blocks with `![[image]]` embed but no internal structure.

**New**: Each figure callout gets a fixed internal structure with sub-section headings that AI fills in:

````markdown
> [!note]- Figure N: {caption}
> ![[{image_link}]]
>
> **图像定位与核心问题**
> （AI fills: 页码、这张图要回答什么）
>
> **方法与结果**
> （AI fills: 方法、主要结果）
>
> **图表质量审查**
> （AI fills: 轴标签、误差棒、chart-reading 审查结果）
>
> **作者解释**
> （AI fills: 文中描述）
>
> **我的理解**
> （AI fills: 自己的分析）
>
> **疑点 / 局限**
> （AI fills: 可酌情用 `> [!warning]`）
````

Tables follow the same pattern with a simpler structure.

Key rules:
- `![[image]]` is embedded in the skeleton — AI never moves it
- Each sub-heading is a fixed string — AI only fills content below
- Figure N is the actual number from the paper order — never `[?]`
- Skeleton is written in one shot by `prepare`, never modified by `ensure-scaffold` separately

### 2. Postprocess Pass 2 (postprocess-pass2)

New molecule `postprocess-pass2` runs after AI finishes Pass 2 writing. It is the sole entry point for all validation checks — individual checks (order, image bounds, empty blocks, missing sub-headings, duplicates, missing figures) are implemented as helper functions within this molecule, not as separate CLI commands.

| Check | What it detects | Error format |
|-------|----------------|--------------|
| Order | Figure callout order differs from skeleton | `Figure 3 appears before Figure 2 (line 42)` |
| Image bounds | `![[image]]` found outside any `> [!note]-` block | `Stray image at line 85: ![[ocr/KEY/images/fig_3.png]]` |
| Empty blocks | Callout with no content between sub-headings | `Figure 5 (line 120): all sub-sections are empty` |
| Missing sub-headings | Figure block missing one or more fixed sub-headings | `Figure 3 (line 45): sub-heading "我的理解" not found` |
| Duplicates | Same figure appears twice | `Figure 2 appears at lines 40 and 95` |
| Missing | Skeleton figure not found in written note | `Figure 4 is missing from the note` |

Output: JSON array of error objects:
```json
[
  {"type": "order", "severity": "error", "figure": "3", "line": 42, "message": "Figure 3 appears before Figure 2"},
  {"type": "image_bounds", "severity": "error", "line": 85, "message": "Stray image at line 85: ..."}
]
```

Each error has enough context for the AI to locate and fix it without re-reading the entire note.

### 3. Prompt Restructuring

**Current**: ~300 lines with detailed figure-by-figure writing instructions, chart-reading integration rules, and callout formatting rules embedded in prose. AI has freedom to interpret structure.

**New**: ~150 lines, structured as:

```
1. prepare (run molecule)
   → read the generated formal note (skeleton is ready)

2. Pass 1: write overview (call molecule: ...)
   → 5Cs, figure overview
   → save

3. Pass 2: fill figure blocks (repeat for each figure in order)
   → read note, locate Figure N callout block
   → fill each sub-heading under it
   → do NOT reorder blocks, do NOT move images
   → save after each figure

4. postprocess-pass2 (run molecule)
   → if errors found, fix each error by line number, goto 4
   → if clean, continue

5. Pass 3: write synthesis
   → save

6. validate-note (run molecule)
   → report result
```

The key change: instead of telling the AI *how* to analyze a figure (the chart-reading rules stay in the chart-reading .md files), the prompt tells the AI *what to do*: "fill the sub-heading 'Methods & Results' under Figure N".

The fix loop has a max of 3 attempts. If postprocess still reports errors after 3 rounds, the AI reports the remaining errors to the user and asks for manual intervention.

### 4. Files to Modify

| File | Change |
|------|--------|
| `paperforge/skills/literature-qa/scripts/ld_deep.py` | Refactor: split monolithic functions into atoms/molecules, add postprocess commands, fix skeleton rendering to include sub-headings |
| `paperforge/skills/literature-qa/prompt_deep_subagent.md` | Rewrite: shorter, more directive, postprocess loop |

### 5. What Stays the Same

- Keshav 3-pass reading method
- Pass 1 (5 Cs)
- Pass 2 figure analysis structure (methods/results/quality review/author interpretation/my understanding/limitations)
- Pass 3 (critical evaluation + research transfer)
- Chart-reading guides (19 .md files) — not touched
- Callout types (`> [!important]`, `> [!warning]`, `> [!question]`, `> [!note]-`)
- `validate-note` command (already exists and works)

### 6. What Changes

- Skeleton includes figure sub-headings (AI fills, doesn't create structure)
- Post-process validates Pass 2 output against skeleton
- Prompt emphasizes "fill the blanks" over "write the section"
- Fix loop: postprocess → AI fixes → recheck

---

## Edge Cases

1. **AI ignores sub-headings and writes free-form**: Postprocess detects missing sub-headings per figure block; reports as error per figure
2. **Figure has no meaningful content to fill**: Allow empty sub-headings (postprocess only warns, doesn't fail)
3. **AI inserts extra callout block**: Detected by "figures in note != figures in skeleton" check
4. **AI writes content outside any callout block**: Detected by image_bounds check, also checks for stray markdown text
5. **User re-runs prepare on already-prepared note**: Skeleton is fully regenerated. Existing Pass 1/2/3 content between `## 🔍 精读` and end of file preserved. If figure count changed between runs, new figures appear as empty callouts (postprocess will flag), and orphaned Pass 2 content from removed figures remains (user notified).
6. **Zero-figure papers**: Skeleton contains only the section headings (Pass 1/2/3) with no figure callout blocks. Pass 2 rendered as text-only analysis. Postprocess skips figure-specific checks.
7. **Fix loop exceeds 3 attempts**: AI reports remaining postprocess errors to user as a warning and asks for manual intervention for the specific issues.

---

## Verification

- `pytest tests/` — full suite must pass
- `python ld_deep.py prepare <key> --vault <vault>` — generates correct skeleton with sub-headings
- `python ld_deep.py postprocess-pass2 <note> --skeleton <skeleton>` — detects known-bad notes
- Manual: run `/pf-deep` on a test paper, verify skeleton correctness and postprocess catches intentional errors
