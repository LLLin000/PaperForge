# Subagent Prompt for /pf-deep

## Task

Execute Keshav 3-pass journal-club style deep reading on a paper and write the results into the `## 🔍 精读` section of its formal note.

## Input Variables

- `{{ZOTERO_KEY}}` — Zotero citation key (e.g. `Y5KQ4JQ7`)
- `{{VAULT}}` — Vault root path
- `{{SCRIPT}}` — Path to `ld_deep.py`

## Workflow (execute in strict order)

### Step 1: Prepare
Run:
```
python {{SCRIPT}} prepare {{ZOTERO_KEY}} --vault "{{VAULT}}" --format text
```
- Reads formal note path, figure count, table count from output.
- If output starts with `[ERROR]`: report error to user, stop.
- If output contains `[WARN] deep_reading_status already 'done'` and user did not request re-read: stop.
- Prepare inserts the `## 🔍 精读` skeleton with figure/table callout blocks and fixed sub-headings into the formal note. Read the note to inspect its structure.

### Step 2: Pass 1 (概览)
Fill `### Pass 1: 概览` only. Do not touch Pass 2/3.
- `**一句话总览**`: paper type + core finding in one sentence.
- `**5 Cs 快速评估**`: Category, Context, Correctness (intuition only), Contributions (1-3 items), Clarity.
- `**Figure 导读**`: list key figures with one-line guesses, note evidence turning points.
- Save immediately after writing.

### Step 3: Pass 2 (精读还原)
Fill `### Pass 2: 精读还原`. Process figures sequentially starting from Figure 1. Each figure callout block has fixed sub-headings. Fill content under each sub-heading. Do NOT modify sub-headings, reorder blocks, or move `![[image]]` embeds.

**Figure sub-headings:**
- `**图像定位与核心问题**`: what question this figure answers, page number.
- `**方法与结果**`: experimental design / data source / technical approach. Core data points, trends, comparisons.
- `**图表质量审查**`: check axis labels, units, error bars, statistical significance markers. Read `chart-type-map.json` for the figure, open recommended chart-reading guides, apply their checklists.
- `**作者解释**`: authors' description from the text.
- `**我的理解**`: your own analysis (distinct from author explanation).
- `**疑点/局限**`: use `> [!warning]` for concerns.

**Table sub-headings:** (same callout pattern, simpler)
- What question this table answers, key fields/groups, main results, my understanding, doubts/limitations.

After all figures and tables, fill:
- `**关键方法补课**`: briefly explain unfamiliar experimental techniques.
- `**主要发现与新意**`: list findings with evidence source (Figure X / Table Y).

Save after each figure block.

### Step 4: Postprocess
Run:
```
python {{SCRIPT}} postprocess-pass2 <formal_note_path> --figures <N> --format text
```
- If output is `OK`: proceed.
- If not `OK`: fix each error (errors include exact line numbers), re-run postprocess-pass2. Max 3 fix rounds. If still failing after 3 rounds, report remaining errors to user.

### Step 5: Pass 3 (深度理解)
Fill `### Pass 3: 深度理解` based on Pass 1/2 content already written. Sections:
- `**假设挑战与隐藏缺陷**`: implicit assumptions, what breaks if relaxed, missing references, technical issues.
- `**哪些结论扎实，哪些仍存疑**`: split into 较扎实 / 仍存疑.
- `**Discussion 与 Conclusion 怎么读**`: what authors actually accomplished vs. overclaim vs. speculation.
- `**对我的启发**`: research design, figure organization, method combination, future work ideas.
- `**遗留问题**`: open questions.
- Save.

### Step 6: Final Validation
Run:
```
python {{SCRIPT}} validate-note <formal_note_path> --fulltext <fulltext_path>
```
- Report result to user. If not `OK`, list missing items and fix.

## Callout Rules

- `> [!important]`: each main finding entry
- `> [!warning]`: doubts, limitations, evidence boundaries, items in 仍存疑
- `> [!question]`: open questions in 遗留问题
- Regular markdown lists for structural sections (research question, methods, inspiration)
- **Spacing**: adjacent callout blocks MUST have a blank line between them, otherwise Obsidian merges them.
- Correct: `> [!important] A\n\n> [!important] B`
- Incorrect: `> [!important] A\n> [!important] B` (missing blank line → merged)

## Error Handling

- prepare fails (`[ERROR]`) → report to user, stop.
- postprocess exceeds 3 fix rounds → report remaining errors to user, ask for guidance.
- validate-note fails → fix missing items, do not report success until it passes.

## Command Reference

```
# Prepare (insert skeleton + check preconditions)
python {{SCRIPT}} prepare {{ZOTERO_KEY}} --vault "{{VAULT}}" --format text

# Postprocess Pass 2 (fix spacing/section issues)
python {{SCRIPT}} postprocess-pass2 <note_path> --figures <N> --format text

# Validate final note structure
python {{SCRIPT}} validate-note <note_path> --fulltext <fulltext_path>
```
