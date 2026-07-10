# Retrieval Recovery — Phase 1: Unified Contract

> **For agentic workers:** Use TDD. Write failing test, watch it fail, implement minimal fix, verify green.

**Goal:** Restore retrieval correctness by unifying the Python result envelope and fixing the plugin parser/spawn contracts.

**Architecture:** Approach A — Python CLI is sole retrieval owner. Plugin spawns CLI per query, parses one unified PFResult envelope. sql.js deleted.

**Tech Stack:** Python 3.14 (D:/L/OB/Literature-hub/.venv/Scripts/python.exe), TypeScript/esbuild Obsidian plugin, sqlite-vec 0.1.9, FTS5.

## Global Constraints

- Source Corpus (papers, OCR, blocks, metadata, annotations) MUST NOT be modified.
- Retrieval Artifacts (FTS indexes, vec0 tables, companion meta) are disposable.
- Python executable: `D:/L/OB/Literature-hub/.venv/Scripts/python.exe`
- Vault: `D:/L/OB/Literature-hub`
- Repository worktree: `D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/retrieval-recovery`
- Test vault for disposable tests: `tests/fixtures/vault`
- All CLI calls use `--vault` flag pointing to the test vault, never the live vault in tests.
- Contract tests must parse real CLI JSON output, not mock it.
- Existing 89 tests must keep passing.
- Commit after every task with Conventional Commits style (repo convention: `feat:`, `fix:`, `chore:`).

---
