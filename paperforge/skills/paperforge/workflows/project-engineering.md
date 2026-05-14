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
