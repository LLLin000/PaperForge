# 194 — W01: Harness — real bundle, isolation, independent oracle

**GitHub:** #194 | **Parent:** #192 (PRD) | **Plan:** `project/current/plugin-major-release-acceptance-plan.md` §8 W01

**What to build:** make the real-Obsidian harness prove *which artifact* it ran and that the sandbox cannot leak into the fixture; then rework the inherited 7 cases so a green run means a real user-visible change, not a trace string.

**Blocked by:** #193 (W00)

**Status:** in progress — slice 1 VERIFIED, 3 items remain

## Slice 1 (2026-09-10) — VERIFIED, branch `feat/issue-194-e2e-harness` @ `d9a65e5d`

- [x] `pretest:e2e` builds (tsc + production esbuild) before WDIO — no stale-bundle pass.
- [x] Case **X11 / bundle-binding+isolation** (H): loaded `main.js` hash == built hash; plugin and backend versions == candidate version; sandbox is a temp copy; sentinel write does not reach the fixture.
- [x] Evidence record per plan §4.3 → `paperforge/plugin/test/evidence/` (gitignored).
- [x] Finding fixed: tracked `main.js` was a dev build (1.79 MB inline sourcemap) → production bundle 340 KB; deterministic across 3 builds.
- Gates: e2e 8/8 (Obsidian 1.13.7, 35.8 s); vitest 452/452; tsc clean.

## Remaining

- [ ] Replace the trace-based Sync assertion with a data-diff assertion (mutate export → click Sync → exact key-set change; bystander paper byte-identical). The current assertion is satisfiable by the startup autosync.
- [ ] Same-sandbox restart persistence demo (restart the current temp vault, not a fresh copy).
- [ ] Bind the backend artifact (path/hash), not just its version — the sandbox backend may resolve to a managed slot rather than the worktree source.

## Acceptance (package)

Per plan §8 W01: build before WDIO with hash verification; safe root, network/user-state isolation; same-sandbox restart demonstrated; no trace-based false success.
