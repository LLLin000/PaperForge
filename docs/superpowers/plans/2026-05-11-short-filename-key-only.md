# Short Filename: `{key}.md` Instead of `{key} - {title}.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change the formal note filename inside workspace directories from `{key} - {title}.md` to `{key}.md`, and inject the full title into frontmatter `aliases`. This prevents Windows MAX_PATH (260 char) overflow when vault paths are long. Workspace directory names stay as `{key} - {title}/` (unchanged).

**Architecture:** Two-layer change: (1) filename construction sites switch from `f"{key} - {slug}.md"` to `f"{key}.md"`, (2) a self-healing migration in `_build_entry` renames old-format `{key} - *.md` files to `{key}.md` and injects `aliases` on first encounter. All broad `rglob("*.md")` frontmatter scanners are unaffected (they match any .md file and parse frontmatter). Only key-specific globs need updating. Test fixtures updated first.

**Tech Stack:** Python 3, `pathlib`, `re`, `json`, `yaml`

---

## Review Fixes (Post-Review)

| ID   | Issue                                        | Fix Applied                                                                     |
| ---- | -------------------------------------------- | ------------------------------------------------------------------------------- |
| C-1  | Tests not updated                            | Added Task 0 updating conftest.py + 3 test files                                |
| C-2  | migrate_to_workspace parse breaks flat notes | Task 2 Step 3: keep `" - "` split for old flat notes, add key-only fallback      |
| H-1  | Alias injection doesn't quote title          | Task 1 Step 5: use `yaml_quote()` from `_utils.py`                                |
| H-2  | Old workspace files silently skipped         | Task 2 Step 2: add self-healing rename inside migrate_to_workspace              |
| L-3  | ocr.py fallback loses max() tiebreaker       | Task 4 Step 1: add `max(note_glob, key=lambda p: len(p.parents))` after fallback |

---

## Affected Code Map

### Filename Construction (need to change)

| File                | Line | Current                                    | Change To       |
| ------------------- | ---- | ------------------------------------------ | --------------- |
| `asset_index.py`      | 265  | `f"{key} - {title_slug}.md"` (note_path)     | `f"{key}.md"`     |
| `asset_index.py`      | 282  | `f"{key} - {title_slug}.md"` (main_note_path) | `f"{key}.md"`     |
| `sync.py`             | 249  | `f"{item['key']} - {slugify_filename(item['title'])}.md"` | `f"{item['key']}.md"` |
| `sync.py`             | 1138 | `f"{key} - {title_slug}.md"` (main_note_path) | `f"{key}.md"`     |

### Key-Specific Glob/Search (need to change)

| File                | Line | Current Pattern                            | Change To                          |
| ------------------- | ---- | ------------------------------------------ | ---------------------------------- |
| `asset_index.py`      | 277  | `glob(f"{key} - *.md")` stale cleanup        | `glob(f"{key}*.md")` + guard for new |
| `ocr.py`              | 1697 | `rglob(f"{key} - *.md")` auto_analyze         | `rglob(f"{key}.md")` or fallback     |
| `ld_deep.py`          | 1399 | `.startswith(f"{key} ")` or `"{key} -"`        | `== f"{key}.md"` or `.startswith(f"{key}.")` |

### NOT Changing

| File                | Line | Reason                                      |
| ------------------- | ---- | ------------------------------------------- |
| `asset_index.py`      | 268  | Workspace dir name — stays `{key} - {title}` |
| `asset_index.py`      | 270  | Workspace dir glob — stays `{key} - *`       |
| `sync.py`             | 1137 | Workspace dir — stays                        |
| `discussion.py`       | 120  | AI dir — stays inside `{key} - {title}/`     |
| `status.py`           | 780  | Health check — checks dir, not filename     |
| `frontmatter_note`    | 1013 | Add `aliases` field — constructive change    |
| All `rglob("*.md")`    | —    | Broad scanners — work regardless of filename |

---

## Task Breakdown

### Task 0: Update Test Fixtures for New Filename Format

**Files:**
- Modify: `tests/conftest.py:121` (fixture note creation)
- Modify: `tests/test_e2e_pipeline.py:37,165` (workspace search + assertion)
- Modify: `tests/test_e2e_cli.py:54,141` (rglob patterns)
- Modify: `tests/test_prepare_rollback.py:64,98,132` (filename references)

- [ ] **Step 1: Update conftest.py fixture (line ~121)**

Change fixture filename from `"TSTONE001 - Biomechanical..."` to `"TSTONE001.md"`.

- [ ] **Step 2: Update test_e2e_pipeline.py**

Line 37 `_find_workspace_note()`: change `glob(f"{key} - *.md")` to `glob("*.md")` (search inside workspace dir for any .md).
Line 165: change `note_path.name.startswith("TSTONE001 - ")` to `note_path.stem == "TSTONE001"`.

- [ ] **Step 3: Update test_e2e_cli.py**

Lines 54, 141: change `rglob("TSTONE001 - *.md")` to `rglob("TSTONE001.md")`.

- [ ] **Step 4: Update test_prepare_rollback.py**

Lines 64, 98, 132: update old-format filename strings to `"TSTONE001.md"`.

- [ ] **Step 5: Run tests BEFORE source changes to confirm they fail as expected**

Run: `pytest tests/unit/test_e2e_pipeline.py tests/unit/test_e2e_cli.py -q --tb=short`
Expected: target tests FAIL (old filename not found).

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_e2e_pipeline.py tests/test_e2e_cli.py tests/test_prepare_rollback.py
git commit -m "test: update fixtures to {key}.md filename format (red phase)"
```

---

### Task 1: Change Filename Construction in `asset_index.py`

**Files:**
- Modify: `paperforge/worker/asset_index.py:265`
- Modify: `paperforge/worker/asset_index.py:282`
- Modify: `paperforge/worker/asset_index.py:277` (stale cleanup)
- Test: run existing test suite

- [ ] **Step 1: Read current code around lines 265, 277, 282**

- [ ] **Step 2: Change `note_path` construction (line 265)**

```python
# Before:
note_path = paths["literature"] / domain / f"{key} - {title_slug}.md"

# After:
note_path = paths["literature"] / domain / f"{key}.md"
```

- [ ] **Step 3: Change stale-note cleanup (lines 276-279)**

```python
# Before:
if note_path.parent.exists():
    for stale_note in note_path.parent.glob(f"{key} - *.md"):
        if stale_note != note_path:
            stale_note.unlink()

# After: cleanup old-format {key} - *.md files that aren't the canonical {key}.md
if note_path.parent.exists():
    for stale_note in note_path.parent.glob(f"{key}*.md"):
        if stale_note != note_path:
            stale_note.unlink()
```

- [ ] **Step 4: Change `main_note_path` construction (line 282)**

```python
# Before:
main_note_path = workspace_dir / f"{key} - {title_slug}.md"

# After:
main_note_path = workspace_dir / f"{key}.md"
```

- [ ] **Step 5: Add self-healing migration logic (after line 282)**

Insert after `main_note_path = workspace_dir / f"{key}.md"`:

```python
# Self-healing migration: rename old-format {key} - {title}.md → {key}.md
if not main_note_path.exists():
    for old_candidate in workspace_dir.glob(f"{key} - *.md"):
        old_candidate.rename(main_note_path)
        # Inject alias into frontmatter
        try:
            text = main_note_path.read_text(encoding="utf-8")
        except Exception:
            text = frontmatter_note(entry, "")
        # Add aliases line after title line in frontmatter, using yaml_quote for safety
        if "aliases:" not in text[: text.find("\n---", 4)]:
            from paperforge.worker._utils import yaml_quote
            alias_line = f"aliases: [{yaml_quote(entry.get('title', ''))}]\n"
            text = re.sub(
                r'(^title:.*\n)',
                r'\1' + alias_line,
                text,
                count=1,
                flags=re.MULTILINE,
            )
            main_note_path.write_text(text, encoding="utf-8")
        break  # only one old file per key
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/ -q --tb=short`
Expected: 207 passed

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/asset_index.py
git commit -m "feat: change formal note filename to {key}.md, add self-healing migration"
```

---

### Task 2: Change Filename Construction in `sync.py`

**Files:**
- Modify: `paperforge/worker/sync.py:249`
- Modify: `paperforge/worker/sync.py:1138`
- Modify: `paperforge/worker/sync.py:1108-1112` (filename parse logic in migration)

- [ ] **Step 1: Change flat note construction (line 249)**

```python
# Before:
note_path = paths["literature"] / domain / f"{item['key']} - {slugify_filename(item['title'])}.md"

# After:
note_path = paths["literature"] / domain / f"{item['key']}.md"
```

- [ ] **Step 2: Change workspace main_note_path + add self-healing (line 1138)**

```python
# Before:
main_note_path = workspace_dir / f"{key} - {title_slug}.md"

# After:
main_note_path = workspace_dir / f"{key}.md"

# Self-healing: old workspaces have {key} - {title}.md inside, rename to {key}.md
if not main_note_path.exists():
    for old_candidate in workspace_dir.glob(f"{key} - *.md"):
        old_candidate.rename(main_note_path)
        break
```

This ensures `main_note_path.exists()` at line 1142 (legacy flag bridging) finds the file.

- [ ] **Step 3: Update filename parsing in migrate_to_workspace (lines 1108-1112)**

The current code parses the key from the filename `{key} - {title}.md` when frontmatter key is missing. Old flat notes still use this format. Keep the old-format parsing but add key-only fallback:

```python
# Before:
stem = note_path.stem
if " - " not in stem:
    continue
zotero_key = stem.split(" - ", 1)[0].strip()

# After:
stem = note_path.stem
if " - " in stem:
    zotero_key = stem.split(" - ", 1)[0].strip()
else:
    zotero_key = stem  # new format: stem IS the key

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/ -q --tb=short`
Expected: 207 passed

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/sync.py
git commit -m "feat: change sync to construct {key}.md filenames, simplify migration parse"
```

---

### Task 3: Add `aliases` Field to `frontmatter_note()`

**Files:**
- Modify: `paperforge/worker/sync.py:1013-1063` (frontmatter_note function)

- [ ] **Step 1: Add `aliases` line**

Insert after the `title:` line (around line 1021-1022):

```python
# After:
lines = [
    "---",
    f"title: {yaml_quote(entry.get('title', ''))}",
    f"aliases: [{entry.get('title', '')}]",   # NEW
    f"year: {entry.get('year', '')}",
    ...
]
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/unit/ -q --tb=short`
Expected: 207 passed

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/sync.py
git commit -m "feat: add aliases field to formal note frontmatter"
```

---

### Task 4: Update Key-Specific Globs in `ocr.py`

**Files:**
- Modify: `paperforge/worker/ocr.py:1697`

- [ ] **Step 1: Change rglob pattern**

```python
# After:
note_glob = list(paths["literature"].rglob(f"{key}.md"))
if not note_glob:
    note_glob = list(paths["literature"].rglob(f"{key} - *.md"))
if note_glob:
    note_path = max(note_glob, key=lambda p: len(p.parents))  # prefer workspace over flat

# After: try {key}.md first, fallback to old format
note_glob = list(paths["literature"].rglob(f"{key}.md"))
if not note_glob:
    note_glob = list(paths["literature"].rglob(f"{key} - *.md"))
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/unit/ -q --tb=short`
Expected: 207 passed

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/ocr.py
git commit -m "fix: update ocr auto_analyze glob for {key}.md filenames with fallback"
```

---

### Task 5: Update Key-Specific Search in `ld_deep.py`

**Files:**
- Modify: `paperforge/skills/literature-qa/scripts/ld_deep.py:1399`

- [ ] **Step 1: Change startswith check**

```python
# Before:
if candidate.name.startswith(f"{zotero_key} ") or candidate.name.startswith(f"{zotero_key} -"):

# After:
if candidate.name == f"{zotero_key}.md" or candidate.name.startswith(f"{zotero_key} -"):
```

The `== f"{zotero_key}.md"` matches the new format. The `startswith(f"{zotero_key} -")` keeps backward compat with any remaining old-format flat notes.

- [ ] **Step 2: Verify existing fallback path**

The fallback at line 1403-1410 uses frontmatter regex which works regardless of filename. This is already correct.

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/ -q --tb=short`
Expected: 207 passed

- [ ] **Step 4: Commit**

```bash
git add paperforge/skills/literature-qa/scripts/ld_deep.py
git commit -m "fix: ld_deep search updated for {key}.md filename format with compat"
```

---

### Task 6: Update `sync_service.py` Flat-Note Cleanup

**Files:**
- Modify: `paperforge/services/sync_service.py:169`

- [ ] **Step 1: Update workspace existence check**

The `clean_flat_notes` function checks if a workspace directory exists before deleting flat notes. The workspace directory construction references `slugify_filename(title)`, but since we're not changing directory names, this should already be correct. Just verify.

- [ ] **Step 2: Verify the `leak_check.py` inline reference**

Not needed for now.

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/ -q --tb=short`
Expected: 207 passed

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: verify sync_service flat-note cleanup works with {key}.md format"
```

---

### Task 7: Integration Test — End-to-End

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/unit/ -q --tb=short
```

Expected: 207 passed

- [ ] **Step 2: Run ruff**

```bash
ruff check paperforge/ --select F,E,W
```

Ensure no new errors introduced.

- [ ] **Step 3: Manual verification — check a sync run**

```bash
python -m paperforge sync --dry-run --verbose
```

Ensure no crash. Path output should show `{key}.md` names.

---

## Risk Assessment (Post-Review)

| Risk                                     | Likelihood | Mitigation                                                    |
| ---------------------------------------- | ---------- | ------------------------------------------------------------- |
| Old files not found                      | Low        | Self-healing rename in `_build_entry` + `migrate_to_workspace`  |
| Broad `rglob` breaks                       | None       | Category 4 scanners match any .md file, filename agnostic     |
| Alias YAML quoting                       | **FIXED**  | Now uses `yaml_quote()` from `_utils.py`                        |
| Stale cleanup deletes new file           | Low        | Guard: `stale_note != note_path` still works                    |
| Workspace dir naming unchanged           | None       | Only .md filename changes, directory stays `{key} - {title}`     |
| migrate_to_workspace misses old-format   | **FIXED**  | Self-healing rename before exist check + key-only stem fallback |
| ocr auto_analyze loses workspace pick    | **FIXED**  | `max()` tiebreaker preserved after fallback                     |
| Tests fail                               | **FIXED**  | Task 0 updates all fixtures first                             |

## Rollback Plan

1. Revert filename construction to `f"{key} - {title_slug}.md"` in 4 lines
2. Revert glob patterns to `f"{key} - *.md"` in 3 lines
3. Old renamed files will still work (same content, different name)
4. Alias field is harmless if left in frontmatter
