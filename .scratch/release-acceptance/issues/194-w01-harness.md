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

- [ ] **Data-diff Sync assertion — BLOCKED on #219.** Replacing the trace-based assertion requires the bystander paper to be byte-identical after an unrelated Sync; today it is not (measured A/B). Needs the #219 fix or an explicit owner narrowing of the criterion.
- [ ] Same-sandbox restart persistence demo (restart the current temp vault, not a fresh copy).
- [ ] Bind the backend artifact (path/hash), not just its version — the sandbox backend may resolve to a managed slot rather than the worktree source.
- [ ] Network / user-state isolation (HOME/APPDATA, runtime pointer, provider endpoints, credential backend) — in the package criteria, not yet covered.
- [ ] Fixture `meta.json` → producer-shaped (currently a 4-field hand-written stub missing `fulltext_md_path`/`markdown_path`/`json_path`; patching it does not change behaviour, so this is hygiene).

## Slice 2 (2026-09-10) — measurements and one blocker

Repair pass `51e369eb` (self-review, Standards + Spec): freshness teeth for "build before WDIO" (proved to fail on a stale build), guarded plugin-dir resolution, appended evidence records (first failure is preserved), `worktree_dirty` recorded; plus two defects introduced by the repair itself and caught by the suite.

Measured baseline behaviour (disposable copies):

| Step | Delta |
|---|---|
| fixture → sync #1 | 2 changed (`Bases/*.base`), 2 transient sqlite sidecars |
| sync #1 → sync #2 | 0 added, 0 removed, only the two `.base` files (whitespace-only churn) |

`.base` view files are therefore an explicit **volatile allowlist** for any diff assertion, never a preservation target.

Blocker filed as **#219**: adding an unrelated paper flips `TSTONE001` from `ocr_status="done"` to `"done_incomplete"` and clears `fulltext_md_path`, while both fulltexts exist and the index keeps a valid `fulltext_path`.

### #219 root cause (bisected, 2026-09-10)

The trigger is the **first `sync` on a vault whose OCR artifacts predate the derived layout** — i.e. exactly the upgrade path:

| Step | canonical `ocr/<key>/fulltext.md` | markers | note |
|---|---|---|---|
| seeded from the OCR fixture | 1574 B | 3 | — |
| after one `sync` | **247 B** | **0** | `done` |

Within that single sync the validator passes against the original artifact (so the note is written `done`), and later the legacy backfill renders from raw and writes the **rendered** markdown over the canonical fulltext (`worker/ocr_rebuild.py:561` → `user_fulltext=artifacts.compat_fulltext`, where `ocr_artifacts.py:28` defines `compat_fulltext = paper_root/"fulltext.md"`). `meta.page_count` stays 3, so the pipeline's own validator (`worker/ocr.py:357-363`) then rejects the artifact it just produced.

Confirmed one-shot: re-seeding the canonical fulltext and dropping the stale `machine_fulltext_hash` leaves two consecutive syncs with no further change (`derived_rebuild_count=0`).

**Consequence for the plan:** this is an upgrade-path defect (A08/J08 territory), not just a harness artefact — every existing vault with legacy OCR layout hits it on its first sync.

**Fix direction:** P-a (backfill writes rendered markdown only to `render/fulltext.md`; canonical keeps page-marked text) — the culprit files are frozen, so it needs owner approval. P-b containment and P-c validator alignment are the alternatives. Plus: use the existing drift helper to force revalidation so a stale `done` cannot persist.

**W01 unblock (independent of the product fix):** make the fixture a validator-passing sync fixed point — end the build with a canonical, hash-consistent OCR state and assert `sync` twice produces only `.base` churn. Proven achievable.

## Acceptance (package)

Per plan §8 W01: build before WDIO with hash verification; safe root, network/user-state isolation; same-sandbox restart demonstrated; no trace-based false success.
