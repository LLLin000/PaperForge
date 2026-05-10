## Summary
<!-- Briefly describe what this PR does -->

## Checklist
- [ ] Fork synced with upstream master (`git merge upstream/master`)
- [ ] `ruff check && ruff format` passes
- [ ] `pytest tests/ --ignore=tests/sandbox -x` passes
- [ ] Plugin changes: `npx vitest run` in `paperforge/plugin/` passes
- [ ] No secrets, API keys, or `.env` files committed
