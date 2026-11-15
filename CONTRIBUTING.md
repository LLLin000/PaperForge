# Contributing to PaperForge

## Local module diagnostics

Start with the [module responsibility and interface map](docs/research/module-status-and-interface-map-2026-10-24.md).
It lists existing authorities, focused local checks, shared-sandbox constraints, and unverified product boundaries.
Use a dedicated venv and record `sys.executable` / `paperforge.__file__` before diagnosing a failure; do not mix an editable install from another checkout with this checkout's tests.
Use `python scripts/ci_local.py --list --json` to inspect existing local job commands without triggering GitHub Actions.
Local development need not wait on hosted CI; merging and release acceptance remain separate gates.

## Before submitting a PR

**Sync your fork first.** This avoids conflicts from outdated forks:

```bash
git remote add upstream https://github.com/LLLin000/PaperForge.git
git fetch upstream
git checkout master
git merge upstream/master
git push origin master
```

Then create your feature branch from the updated master:

```bash
git checkout -b my-feature upstream/master
```

## Code style

- Plugin (JS): follow existing patterns in `paperforge/plugin/`
- Python: `ruff check` and `ruff format` before committing

## PR checklist

- [ ] Fork synced with upstream master
- [ ] `ruff check && ruff format` passes
- [ ] `pytest tests/ --ignore=tests/sandbox --ignore=tests/e2e --ignore=tests/journey --ignore=tests/chaos --ignore=tests/audit -x` passes
- [ ] Plugin changes: `npx vitest run` in `paperforge/plugin/` passes
