# Project Engineering

When user asks about PaperForge codebase issues (branch, code review, feature,
dashboard, memory layer, user feedback, errors, installation, Git, Zotero,
BetterBibTeX, OCR, plugin):

1. Read `AGENTS.md` and `README.md` for architecture context
2. Use `git log --oneline` and `git diff` to understand recent changes
3. Search codebase with grep/glob as needed
4. Run diagnostics: `python -m paperforge doctor` (if applicable)
5. Present findings and recommend fixes

Do NOT modify code without user confirmation.

## Review Dimensions

When auditing branches, code, or user-reported issues, check:

1. **Source of truth clarity:** Is data stored in one canonical location?
2. **Derived index rebuildability:** Can SQLite be rebuilt from JSONL?
3. **Agent routing stability:** Will the skill router pick the right workflow?
4. **Obsidian file integrity:** Are .md files still readable with valid frontmatter?
5. **User flow length:** Has the number of manual steps decreased?
6. **Cross-platform safety:** Paths use `/`, Python detection works on Win/Mac/Linux, Git is accessible.
7. **Data loss risk:** Does any operation silently drop records?
8. **Deprecation hygiene:** Are old functions properly wrapped or removed?
