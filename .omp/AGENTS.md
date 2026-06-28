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
