# Contributing to PaperForge

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
