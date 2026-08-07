# PaperForge — Project Record Management

Project state is split across three layers with distinct roles:

- **Narrative ledger** (`PROJECT-MANAGEMENT.md`) — full history, updated every session end
- **Active queue** (`project/current/ocr-v2-active-queue.md`) — next-work priorities, updated at milestones
- **Archive** (`project/archive/`) — superseded files from `current/`, moved not deleted

## Update Rules

### PROJECT-MANAGEMENT.md — Every Session End

Update before final commit. Touches:
- Executive summary (§0) — one-line current state + next action
- Current status (§2) — test counts, component state, fix table
- Remaining issues (§3) — resolved out, new ones in
- Active queue checkpoint (§4) — next steps
- Decision log (§6) — one line per decision with rationale
- Session timeline (§8) — compressed one-line record

### project/current/ — Milestones Only

`ocr-v2-active-queue.md` updates after major fix series or priority shifts. Never mid-session.
Other `ocr-v2-*.md` files: update only when architecture or evidence changes.

### project/archive/ — Move, Don't Delete

When a current file no longer reflects active truth: prepend archive header (date + reason + replacement), move to `project/archive/`, remove from `current/`.

## Format Conventions

- **Timeline entry** (§8): `| YYYY-MM-DD | Short title | Key results — what was done, what was found | §N.M |`
- **Decision log** (§6): `| YYYY-MM-DD | Decision title | Rationale — why, not what |`
- **Fix table** (§2.3): `| # | Paper + symptom | Root cause | Fix approach | Commit |`

## Lifecycle Truth Hierarchy (architecture audit review, 2026-08-07)

Each capability's state is expressed in exactly one authoritative place; the
rest are projections and must never override it:

| Fact | Single authority |
|------|------------------|
| Code existence / observed facts | the #133 deterministic collectors (Survey) — never prose |
| Architecture acceptance (planned → active) | `ArchitectureContract.lifecycle` — explicit promotion, commit-tracked |
| Task/workflow state | the GitHub issue |
| Release acceptance | CI / owner gate |
| `PROJECT-MANAGEMENT.md` | projection only — never the authority for system state |

Consequences:

- `PROJECT-MANAGEMENT.md` and the queue may say "implemented", but the
  report/contract decide "accepted". The Pages report keeps
  `collectors.deterministic` as `planned` until the owner accepts #133 and the
  Contract lifecycle is promoted in a tracked commit.
- A capability's report coverage must reflect the collector's observation, not
  the ledger's prose (the 2026-08-06 mismatch: ledger said #133 implemented,
  live report said `unavailable` — fixed by making the report collector-driven).
- Contract promotion (`planned` → `active`) is a code change with a commit; it
  is never implied by issue close or ledger prose alone.
