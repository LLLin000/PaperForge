# Discussion MD as Truth Source — Design Spec

> **Status:** Draft | **Date:** 2026-05-18
> **Motivation:** `discussion.json` forces rich markdown content (tables, code blocks, callouts, ASCII flowcharts) into JSON strings, destroying formatting and making output unreadable. Switch to `discussion.md` as the sole truth source.

## Goal

1. **Stop writing `discussion.json`** — QA content lives only in `.md`
2. **Keep `discussion.md` as the rich markdown output** — no `_escape_md()` on answer text
3. **Plugin card reads `.md` directly** — parse the last 3 Q&A pairs from markdown structure
4. **Existing `.json` files are ignored** — no migration needed

---

## Current Architecture (as-is)

```
Agent workflow (paper-qa.md)
  ↓  --qa-pairs '<JSON string>'
discussion.py record_session()
  ↓
  ├── ai/discussion.json  ← canonical (structured, sessions[], qa_pairs[])
  ├── ai/discussion.md    ← human-readable (escaped, no rich formatting)
  │
plugin main.js
  ├── _renderRecentDiscussionCard()  ← reads discussion.json
  └── "查看全部讨论" link            ← opens discussion.md
```

**Problem:** `_escape_md()` escapes `**bold**` → `\*\*bold\*\*`, tables, code blocks, callouts all get destroyed. The `.md` file is barely readable.

---

## Target Architecture (to-be)

```
Agent workflow (paper-qa.md)
  ↓  --qa-pairs '<JSON string>'  (same API, no change)
discussion.py record_session()
  ↓
  └── ai/discussion.md  ← truth source (RICH markdown, no escaping)
       │
plugin main.js
  ├── _renderRecentDiscussionCard()  ← reads discussion.md, parses last 3 Q&A
  └── "查看全部讨论" link            ← opens discussion.md (same)
```

---

## File Changes

### Part A: `paperforge/worker/discussion.py`

**Schema:**
- Remove `_escape_md()` — answer text goes directly into `.md` unescaped
- Remove `_atomic_write_json()` — no more `.json` writing
- `_build_md_session()` — no longer calls `_escape_md()` on answer text
- `record_session()` — remove JSON reading/writing, only lock + write `.md`
- Return value: remove `json_path`, keep `md_path`
- Lock file: change from `discussion.json.lock` to `discussion.md.lock`

**New `record_session()` flow:**
```
1. Validate inputs (same)
2. Find paper metadata (same)
3. Build paths: ai_dir + /discussion.md (no json_path)
4. Build session dict (same, but only used for md generation)
5. Acquire lock on discussion.md.lock
6. Read existing discussion.md (if exists)
7. Append new session markdown
8. Atomic write discussion.md
9. Release lock
10. Return {"status": "ok", "md_path": str(md_path)}
```

### Part B: `paperforge/plugin/main.js`

**`_renderRecentDiscussionCard()` — new logic:**

Instead of reading `discussion.json`, read `discussion.md` and render with `MarkdownRenderer.render()`:

1. Read `wsDir + '/ai/discussion.md'`
2. Split content by `## ` headings (session separator)
3. Take the last session section
4. Within that section, split by `**问题:**` to extract QA pairs
5. Take the last 3 QA pairs
6. For each QA pair:
   - Render question as `**提问:** ...` via `MarkdownRenderer.render()`
   - Render answer as formatted markdown via `MarkdownRenderer.render()`
   - No manual truncation — API renders native Obsidian markdown (tables, code blocks, callouts all work)
7. For long answers (>500 chars): wrap in `max-height: 200px` + `overflow: hidden` with "展开更多" toggle
8. "查看全部讨论" link unchanged

**QA pair parser (extract from .md):**

```js
function _parseDiscussionMD(content) {
    const sessions = content.split(/\n## /).slice(1);
    if (sessions.length === 0) return null;
    const lastSession = sessions[sessions.length - 1];
    const pairs = [];
    const qaBlocks = lastSession.split(/\*\*问题:\*\*/).slice(1);
    for (const block of qaBlocks) {
        const answerMatch = block.match(/\*\*解答:\*\*/);
        if (!answerMatch) continue;
        const question = block.substring(0, answerMatch.index).trim();
        const answer = block.substring(answerMatch.index + '**解答:**'.length).trim();
        pairs.push({ question, answer });
    }
    return pairs.slice(-3);
}
```

**Render each QA pair with MarkdownRenderer:**

```js
async function _renderQAPair(container, qa, sourcePath) {
    // Question
    const qEl = container.createEl('div', { cls: 'paperforge-discussion-q' });
    await MarkdownRenderer.render(
        this.app,
        '**提问：**' + qa.question,
        qEl, sourcePath, this
    );

    // Answer
    const aEl = container.createEl('div', { cls: 'paperforge-discussion-a' });
    if (qa.answer.length > 500) {
        aEl.style.maxHeight = '200px';
        aEl.style.overflow = 'hidden';
        // Add "展开更多" toggle
        const toggle = container.createEl('button', { text: '展开更多 ▽' });
        toggle.addEventListener('click', () => {
            aEl.style.maxHeight = aEl.style.maxHeight ? '' : '200px';
            toggle.setText(aEl.style.maxHeight ? '展开更多 ▽' : '收起 △');
        });
    }
    await MarkdownRenderer.render(
        this.app,
        qa.answer,
        aEl, sourcePath, this
    );
}
```

**Lifecycle management:**
- The `this` context in `_renderRecentDiscussionCard()` is the plugin instance (extends `Plugin` which extends `Component`)
- Pass `this` as the `component` parameter — ensures proper cleanup when card content changes
- No need to create a separate `Component` instance

### Part C: `paperforge/skills/paperforge/workflows/paper-qa.md`

- Update line 8: `discussion.json` → `discussion.md`
- No other changes — the CLI command `python -m paperforge.worker.discussion record` keeps same interface

### Part D: Tests

`tests/test_discussion.py`:
- `test_create_both_files` → `test_create_md_file` (remove JSON assertions, verify .md has rich content)
- `test_append_second_session` → verify .md appends correctly
- `test_markdown_escaping` → **REVERSE** this test: verify that `**bold**` is preserved (not escaped)
- `test_markdown_escaping_cjk` → same: verify CJK + unescaped markdown coexists
- `test_file_lock` → use `.md.lock` instead of `.json.lock`
- `test_cli_invocation` → no longer checks json_path
- Remove `test_utc_timestamp` (no JSON to check)

### Part E: Backward Compatibility

- Old `discussion.json` files are **left in place**, not deleted
- Old `discussion.md` files (with escaped content) will be parsed by the new card — the Q&A text will have `\*` characters, but this is acceptable
- Over time, as new sessions are appended, the card shows the latest (unescaped) content
- No migration needed

---

## Data Flow

### Write path (unchanged except no JSON)

```
Agent:  --qa-pairs '[
           {"question": "What is X?",
            "answer": "X is **significant** (p<0.05)\n\n| Group | Mean |\n|------|------|\n| A | 10 |"} ]'

discussion.py record_session():
  → Build md session with raw markdown (no escaping)
  → Atomic append to discussion.md
  → Return {md_path: "..."}
```

### Read path (new)

```
plugin main.js:
  → this.app.vault.adapter.read('ai/discussion.md')
  → split by "## " → take last session
  → split by "**问题:**" → take last 3 QA pairs
  → MarkdownRenderer.render(app, qa.answer, el, sourcePath, this)
  → Native Obsidian rendering: tables, code blocks, callouts, bold all visible
  → max-height: 200px for long answers (>500 chars) with "展开更多"
```

---

## Out of Scope

- Deleting old `discussion.json` files
- Migrating existing escaped content to unescaped
- Adding a "copy as JSON" button or API
