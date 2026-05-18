# Discussion MD as Truth Source — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `discussion.md` the sole truth source, remove `discussion.json`, render rich markdown in plugin card via `MarkdownRenderer.render()`.

**Architecture:** `discussion.py` stops writing JSON, drops `_escape_md()`, changes lock file. Plugin card reads `.md` directly and uses Obsidian's built-in `MarkdownRenderer.render()` for native rendering.

**Tech Stack:** Python stdlib, Obsidian `MarkdownRenderer` API

---

### Task 1: `discussion.py` — Remove JSON, remove escaping, change lock

**Files:**
- Modify: `paperforge/worker/discussion.py`

- [ ] **Step 1: Remove `_escape_md()` and related cruft**

  Delete lines 40-41 (`_MD_SPECIAL_CHARS` regex + comment):
  ```python
  _MD_SPECIAL_CHARS = re.compile(r"([*#\[\]_`])")
  """Regex for markdown special characters that must be escaped in QA text fields."""
  ```

  Delete lines 59-66 (`_escape_md()` function):
  ```python
  def _escape_md(text: str) -> str:
      ...
  ```

- [ ] **Step 2: Update `_build_md_session()` to not escape**

  In lines 186-187, change:
  ```python
  lines.append(f"**问题:** {_escape_md(qa['question'])}")
  lines.append(f"**解答:** {_escape_md(qa['answer'])}\n")
  ```
  to:
  ```python
  lines.append(f"**问题:** {qa['question']}")
  lines.append(f"**解答:** {qa['answer']}\n")
  ```

- [ ] **Step 3: Remove `_atomic_write_json()` function**

  Delete lines 145-171 (`_atomic_write_json()` function).

- [ ] **Step 4: Update `record_session()` — remove JSON, change lock**

  In `record_session()`:
  - Remove line 287: `json_path = ai_dir / "discussion.json"`
  - Change line 300: `.json.lock` → `.md.lock`
  - Remove JSON reading/writing block (lines 304-319): the `# Write discussion.json` block
  - Remove `json_path` from return value (line 343)

  The rewrite looks like:
  ```python
      md_path = ai_dir / "discussion.md"

      session = _build_session(agent, model, zotero_key, paper_title, domain, qa_pairs)

      lock_path = md_path.with_suffix(".md.lock")
      lock = filelock.FileLock(lock_path, timeout=LOCK_TIMEOUT)
      try:
          with lock:
              existing_md = ""
              if md_path.exists():
                  try:
                      existing_md = md_path.read_text(encoding="utf-8")
                  except (OSError, UnicodeDecodeError) as exc:
                      logger.warning("Could not read existing discussion.md: %s", exc)
                      existing_md = ""

              header = _build_md_header(paper_title)
              session_md = _build_md_session(session)
              content = _md_content(existing_md, header, session_md)
              _atomic_write_md(md_path, content)
      except filelock.Timeout:
          ...
          return {"status": "error", "message": "Concurrent access conflict. Please try again."}
      except Exception as exc:
          ...
          return {"status": "error", "message": f"Failed to write discussion file: {exc}"}

      return {"status": "ok", "md_path": str(md_path)}
  ```

- [ ] **Step 5: Update docstrings**

  In module docstring (lines 3-4), change `JSON (canonical)` → `Markdown (canonical)`:
  ```python
  """Discussion recorder — writes structured AI-paper Q&A into ai/ workspace directory.

  Atomic append-only writes for Markdown (canonical). stdlib only.
  """
  ```

  In `record_session()` docstring (lines 235-237), change:
  ```python
      """Record an AI-paper discussion session.

      Creates or appends to ai/discussion.md (canonical) with atomic writes.
  ```

- [ ] **Step 7: Remove unused `import re`**

  Remove `import re` (line 20) — no longer needed (no `_MD_SPECIAL_CHARS`). Keep `import json`.

- [ ] **Step 8: Run existing tests to see what breaks**
  Run: `python -m pytest tests/test_discussion.py -v --tb=short`
  Expected: several failures (JSON assertions, test_utc_timestamp, escape tests, etc.)

- [ ] **Step 9: Commit**
  ```bash
  git add -A && git commit -m "feat(discussion): remove JSON output and markdown escaping"
  ```

---

### Task 2: Plugin card — Read `.md`, render with `MarkdownRenderer`

**Files:**
- Modify: `paperforge/plugin/main.js`

- [ ] **Step 1: Rewrite `_renderRecentDiscussionCard()`**

  Replace the current implementation (lines 1959-2031) with:

  ```js
  /* ── Recent Discussion Card: read ai/discussion.md ── */
  _renderRecentDiscussionCard(container, entry) {
      const card = container.createEl('div', { cls: 'paperforge-discussion-card' });
      card.style.display = 'none';

      if (!entry.note_path) return;
      const lastSlash = entry.note_path.lastIndexOf('/');
      const wsDir = lastSlash !== -1 ? entry.note_path.substring(0, lastSlash) : '.';
      const mdPath = wsDir + '/ai/discussion.md';

      this.app.vault.adapter.exists(mdPath).then((exists) => {
          if (!exists) return;
          return this.app.vault.adapter.read(mdPath);
      }).then((raw) => {
          if (!raw) return;

          const pairs = this._parseDiscussionMD(raw);
          if (!pairs || pairs.length === 0) return;

          card.style.display = 'block';
          const header = card.createEl('div', { cls: 'paperforge-discussion-header' });
          header.createEl('span', { cls: 'paperforge-discussion-title', text: '\u6700\u8fd1\u8ba8\u8bba' });

          for (const qa of pairs) {
              const item = card.createEl('div', { cls: 'paperforge-discussion-item' });
              const qEl = item.createEl('div', { cls: 'paperforge-discussion-q' });
              await MarkdownRenderer.render(this.app, '**\u63d0\u95ee\uff1a**' + qa.question, qEl, mdPath, this);

              const aEl = item.createEl('div', { cls: 'paperforge-discussion-a' });
              if (qa.answer && qa.answer.length > 500) {
                  aEl.style.maxHeight = '200px';
                  aEl.style.overflow = 'hidden';
                  const toggle = item.createEl('button', { cls: 'paperforge-expand-btn', text: '\u5c55\u5f00\u66f4\u591a \u25bd' });
                  let expanded = false;
                  toggle.addEventListener('click', () => {
                      expanded = !expanded;
                      aEl.style.maxHeight = expanded ? '' : '200px';
                      toggle.setText(expanded ? '\u6536\u8d77 \u25b3' : '\u5c55\u5f00\u66f4\u591a \u25bd');
                  });
              }
              await MarkdownRenderer.render(this.app, qa.answer || '', aEl, mdPath, this);
          }

          // "查看全部" link
          const viewAll = card.createEl('a', { cls: 'paperforge-discussion-viewall', text: '\u67e5\u770b\u5168\u90e8\u8ba8\u8bba \u2192' });
          viewAll.addEventListener('click', (e) => {
              e.preventDefault();
              const discFile = this.app.vault.getAbstractFileByPath(mdPath);
              if (discFile) {
                  this.app.workspace.openLinkText(mdPath, '');
              } else {
                  new Notice('\u8ba8\u8bba\u6587\u4ef6\u5c1a\u672a\u751f\u6210');
              }
          });
      }).catch((e) => {
          console.error('PaperForge: discussion.md read error', mdPath, e.message);
      });
  }

  _parseDiscussionMD(content) {
      const sessions = content.split(/\n## /).slice(1);
      if (sessions.length === 0) return null;
      const lastSession = sessions[sessions.length - 1];
      const pairs = [];
      const qaBlocks = lastSession.split(/\*\*\u95ee\u9898:\*\*/).slice(1);
      for (const block of qaBlocks) {
          const answerMatch = block.match(/\*\*\u89e3\u7b54:\*\*/);
          if (!answerMatch) continue;
          const question = block.substring(0, answerMatch.index).trim();
          const answer = block.substring(answerMatch.index + '**解答:**'.length).trim();
          pairs.push({ question, answer });
      }
      return pairs.slice(-3);
  }
  ```

  **Note about `MarkdownRenderer`:** main.js line 1 already uses `const { Plugin, /* etc */ } = require('obsidian');`. Just add `MarkdownRenderer` to that destructuring:
  ```js
  const { Plugin, MarkdownRenderer, /* ... */ } = require('obsidian');
  ```

- [ ] **Step 2: Run existing tests**
  Run: `python -m pytest tests/ -v --tb=short`
  Expected: all Python tests pass (JS change is untestable via pytest)

- [ ] **Step 3: Commit**
  ```bash
  git add -A && git commit -m "feat(plugin): render discussion card from .md with MarkdownRenderer"
  ```

---

### Task 3: Update `paper-qa.md` description

**Files:**
- Modify: `paperforge/skills/paperforge/workflows/paper-qa.md`

- [ ] **Step 1: Update line 8 text**

  Change:
  ```markdown
  每次问答记录到 `discussion.json`（Dashboard 可见）。
  ```
  to:
  ```markdown
  每次问答记录到 `discussion.md`（Dashboard 可见）。
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add -A && git commit -m "docs(paper-qa): update discussion.json -> discussion.md"
  ```

---

### Task 4: Update tests

**Files:**
- Modify: `tests/test_discussion.py`

- [ ] **Step 1: Rewrite tests to match new behavior**

  - Rename `test_create_both_files` → `test_create_md_file`: remove JSON assertions, verify .md content is rich (no escaping)
  - `test_append_second_session`: change to use `.md` lock
  - `test_markdown_escaping`: **reverse** — verify `**bold**` is preserved unescaped
  - `test_markdown_escaping_cjk`: same
  - `test_file_lock`: change `.json.lock` → `.md.lock`
  - `test_lock_timeout_returns_error`: same
  - `test_cli_invocation`: no longer checks `json_path`
  - `test_cjk_encoding`: replace `result["json_path"]` with `result["md_path"]`
  - `test_atomic_write_no_partial`: replace `result["json_path"]` with `result["md_path"]`, remove JSON assertions
  - Remove `test_utc_timestamp` entirely
  - Remove `import json` if no longer needed in test

  Key test changes:
  ```python
  def test_create_md_file(self, tmp_path: Path) -> None:
      """Test: Creates ai/discussion.md with rich unescaped markdown."""
      vault = _create_minimal_vault(tmp_path)
      result = record_session(...)
      assert result["status"] == "ok"
      assert "json_path" not in result
      md_path = Path(result["md_path"])
      assert md_path.exists()
      md_content = md_path.read_text(encoding="utf-8")
      assert "# AI Discussion Record:" in md_content
      assert "**问题:**" in md_content
      assert "**解答:**" in md_content

  def test_markdown_preserved_unescaped(self, tmp_path: Path) -> None:
      """Test: **bold** is NOT escaped to \*\*bold\*\*."""
      vault = _create_minimal_vault(tmp_path)
      qa = [{"question": "What does **bold** mean?",
             "answer": "Use **bold** and `code`",
             "source": "user_question",
             "timestamp": "2026-05-06T12:00:00+00:00"}]
      result = record_session(...)
      md = Path(result["md_path"]).read_text(encoding="utf-8")
      assert "**bold**" in md  # NOT \*\*bold\*\*
      assert "\\*" not in md  # no escaping

  def test_file_lock_uses_md_lock(self, tmp_path: Path) -> None:
      """Lock file is .md.lock not .json.lock."""
      vault = _create_minimal_vault(tmp_path)
      result = record_session(...)
      md_path = Path(result["md_path"])
      lock_path = md_path.with_suffix(".md.lock")
      assert not lock_path.exists()
  ```

- [ ] **Step 2: Run tests**
  Run: `python -m pytest tests/test_discussion.py -v --tb=short`
  Expected: all PASS

- [ ] **Step 3: Commit**
  ```bash
  git add -A && git commit -m "test(discussion): update tests for MD-only truth source"
  ```

---

### Task 5: Full suite + lint

- [ ] **Step 1: Run all tests**
  Run: `python -m pytest tests/ -v --tb=short`
  Expected: all PASS

- [ ] **Step 2: Run lint**
  Run: `ruff check --fix paperforge/ && ruff format paperforge/`
  Expected: clean

- [ ] **Step 3: Final commit if lint fixes applied**
  ```bash
  git add -A && git commit -m "style: lint after discussion MD-truth-source changes"
  ```
