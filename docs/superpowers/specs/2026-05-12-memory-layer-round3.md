# PaperForge v1.5.7 — Memory Layer Round 3

> **Branch:** `feature/memory` | **Date:** 2026-05-12

## Feature 1: Logging Skill — Strict Markdown Template

**Problem:** Agent-written reading-log.md may not parse reliably if format varies.

**Solution:** SKILL.md instructs agent to use strict template format.

### File: `paperforge/skills/logging/SKILL.md`

Update the reading-log route section to require this exact format:

```markdown
## ABCDEFGH — Author Last Name et al. Year
**Title:** Full Paper Title

### Section Name — Page NN or line NN-NN
**Info:** "verbatim excerpt from paper"
**Use:** how this supports current writing task
**Note:** optional cross-validation note

### Another Section — Page NN
**Info:** "..."
**Use:** ...
**Note:** (optional)
```

### Parsing Rules (for --validate and --import):

```
paper format:    ^## [A-Z0-9]{8} — .+$         (key is 8 uppercase alphanumeric)
title format:    ^\*\*Title:\*\* .+$
section format:  ^### .+$
info format:     ^\*\*Info:\*\* .+$
use format:      ^\*\*Use:\*\* .+$
note format:     ^\*\*Note:\*\* .+$             (optional)
```

Constraint: `info` and `use` are mandatory for every section entry. `note` is optional.

### CLI Changes

Update `reading-log` parser in `cli.py` to add `--validate` and `--import` subcommands under a shared parser.

## Feature 2: reading-log --validate

**File:** `paperforge/commands/reading_log.py`

```
paperforge reading-log --validate path/to/reading-log.md
```

Function: `validate_reading_log(filepath: Path) -> dict`

Returns:
```json
{
  "ok": true,
  "file": "Project/综述写作/reading-log.md",
  "errors": [],
  "papers_found": 3,
  "entries_found": 7
}
```

On failure:
```json
{
  "ok": false,
  "errors": [
    {"line": 15, "field": "info", "message": "missing **Info:** after section header"},
    {"line": 23, "field": "key", "message": "paper key must match ^[A-Z0-9]{8}$"}
  ]
}
```

Validation algorithm:
1. Parse into papers by `## KEY — Author` headers
2. For each paper: verify `**Title:**` follows
3. For each section `### ...`: verify `**Info:**` and `**Use:**` follow
4. Report all errors at once, not stop-at-first

## Feature 3: reading-log --import

**File:** `paperforge/commands/reading_log.py` + `paperforge/memory/events.py`

```
paperforge reading-log --import path/to/reading-log.md
```

Function: `import_reading_log(vault: Path, filepath: Path) -> dict`

Returns:
```json
{
  "ok": true,
  "papers_imported": 3,
  "entries_imported": 7,
  "skipped": 0
}
```

Algorithm:
1. Call `validate_reading_log(filepath)` — abort if errors
2. Parse valid file into paper-level entries
3. For each entry, call `write_reading_note(vault, paper_id, section, excerpt, usage, note)`
4. Each write INSERTs a new row — safe for accumulative use

### Add to `paperforge/memory/events.py`:

```python
def import_reading_log(vault: Path, filepath: Path) -> dict:
    """Parse a reading-log.md and bulk-write to paper_events."""
    # Parse, validate, write
    ...
```

## Feature 4: reading-log --lookup KEY

**File:** `paperforge/commands/reading_log.py`

```
paperforge reading-log --lookup KEY [--json]
```

Function: `lookup_paper_events(vault: Path, key: str) -> dict`

Returns all accumulated paper_events for a paper, ordered by created_at DESC:
```json
{
  "ok": true,
  "zotero_key": "ABCDEFGH",
  "title": "...",
  "entries": [
    {
      "created_at": "2026-05-12 14:30",
      "section": "Results P6",
      "excerpt": "...",
      "usage": "F 段参数数据",
      "note": "与 Lippiello 对比"
    }
  ],
  "count": 5,
  "projects": ["综述写作", "数据分析"]
}
```

## Feature 5: /methodology Skill

**File:** `paperforge/skills/methodology/SKILL.md`

Pure-prompt skill, no Python code. Same universal pattern as grill-me.

```yaml
---
name: methodology
description: >
  Project methodology extraction. Triggered by:
  methodology, /methodology, 提取方法论, 存档写作规律,
  总结本项目方法, 提取可复用规则.
source: paperforge
---
```

### Agent workflow:

1. Ask user which project to extract from (or detect from context)
2. Read `Project/<project>/working-log.md`
3. Identify extractable patterns:
   - Sections marked as "方法论" or "复用"
   - Wrong turns + corrections (弯路 + 修正)
   - Final logic flows (最终逻辑: XX 段)
   - Review feedback patterns (审阅修正)
   - Cross-study audit methodology
4. Classify into categories:
   - `review-writing.md` — 综述写作相关
   - `data-analysis.md` — 数据分析相关
   - `general-methods.md` — 通用方法
5. Present draft to user for confirmation
6. Write to `<system_dir>/PaperForge/methodologies/<category>.md`

### Methodology file format:

```markdown
---
project: 综述写作
extracted: 2026-05-12
category: review-writing
---

# [Method Name]

## Source
From working-log.md Section [X.Y]

## Pattern
[Extracted reusable methodology]

## Example
[Concrete example from the project]
```

## Feature 6: Dashboard → SQLite Migration

**File:** `paperforge/commands/dashboard.py`

Current `_gather_dashboard_data()` does file scanning with regex. Migrate to:

```python
def _gather_dashboard_data(vault: Path) -> dict:
    # Try DB first
    data = _dashboard_from_db(vault)
    if data is not None:
        data["permissions"] = _check_permissions(vault)
        return data
    # Fallback to file scanning
    return _dashboard_from_files(vault)
```

`_dashboard_from_db()` should read from paperforge.db:
- Paper count: `SELECT COUNT(*) FROM papers`
- Domain counts: `SELECT domain, COUNT(*) FROM papers GROUP BY domain`
- PDF/OCR health: from papers table `ocr_status`, `has_pdf` columns
- Remove the `_source` key (was added in earlier iteration but caused contract issues)

**Keep the permissions check** (`_check_permissions`) separate and lightweight.

## Feature 7: Bootstrap Update

**File:** `paperforge/skills/literature-qa/scripts/pf_bootstrap.py`

If present in repo (not already done), ensure `memory_layer` field is in bootstrap output. Already implemented in earlier harness work — verify status.

## Refactoring: Memory Layer No Longer Optional

**File:** `paperforge/plugin/main.js` ✓ DONE

Removed the Easy Memory Layer toggle. Status display always shown. Memory layer is always on — SQLite is lightweight enough to not need a toggle.

## Implementation Order

1. Logging SKILL.md format update
2. reading-log --validate CLI
3. reading-log --import CLI + events.py
4. reading-log --lookup CLI
5. /methodology SKILL.md
6. Dashboard SQLite migration
7. Integration test + deploy

## Cross-File Impact

| File | Action | Features |
|------|--------|----------|
| `paperforge/skills/logging/SKILL.md` | Modify | Feature 1 |
| `paperforge/commands/reading_log.py` | Modify | Features 2, 3, 4 |
| `paperforge/memory/events.py` | Modify | Feature 3 |
| `paperforge/cli.py` | Modify | Features 2, 3, 4 |
| `paperforge/skills/methodology/SKILL.md` | Create | Feature 5 |
| `paperforge/skills/methodology/scripts/pf_bootstrap.py` | Copy | Feature 5 (same bootstrap) |
| `paperforge/commands/dashboard.py` | Modify | Feature 6 |
| `paperforge/plugin/main.js` | ✓ DONE | Refactoring |
