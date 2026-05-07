# Phase 35: AI Discussion Recorder - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Python module (`paperforge/worker/discussion.py`) that records AI-paper discussion sessions into structured files in each paper's workspace `ai/` directory. Triggered by `/pf-paper` agent session at completion. Produces `discussion.json` (canonical) and `discussion.md` (human-readable) with atomic append-only writes. Zero new dependencies.

</domain>

<decisions>
## Implementation Decisions

### API Surface
- **D-01:** Dual-mode API: importable `record_session(vault_path, zotero_key, agent, model, qa_pairs)` + CLI subcommand.
- **D-02:** Function signature returns `{"status": "ok"/"error", "json_path": "...", "md_path": "..."}`.
- **D-03:** CLI subcommand: `python -m paperforge.worker.discussion record <zotero_key> --vault <path> --agent <name> --model <model>`.
- **D-04:** Module: `paperforge/worker/discussion.py`, stdlib only (`json`, `pathlib`, `datetime`, `tempfile`, `os`, `argparse`).

### Agent Integration
- **D-05:** Only `/pf-paper` records discussions. `/pf-deep` does NOT record (output already in formal note).
- **D-06:** Integration via updating `pf-paper.md` prompt: add "保存讨论记录" step at workflow end.
- **D-07:** Agent accumulates Q&A pairs during session, passes to `record_session()` at session end.

### File Sync Strategy
- **D-08:** Both files written independently from the same data object.
- **D-09:** Atomic write via `tempfile.NamedTemporaryFile` + `os.replace()` for both files.
- **D-10:** Append-only: read existing discussion.json, append new session to sessions[], write back.

### Q&A Data Model
- **D-11:** session metadata: `session_id` (UUID), `agent` ("pf-paper"), `model`, `started` (ISO 8601), `paper_key`, `paper_title`, `domain`, `qa_pairs[]`.
- **D-12:** qa_pair: `question`, `answer`, `source` ("user_question" | "agent_analysis"), `timestamp` (ISO 8601).
- **D-13:** discussion.md format: `##` session heading with date + model, `问题:` / `解答:` per pair, chronological.

### File Organization
- **D-14:** `ai/` directory auto-created if not exists (`parent.mkdir(parents=True, exist_ok=True)`).
- **D-15:** `ai_path` already computed by `asset_index.py`.

### Error Handling
- **D-16:** JSON serialization with `ensure_ascii=False, indent=2` for CJK support.
- **D-17:** File write failures produce graceful error via status-return pattern (never crash).

### the agent's Discretion
- UUID generation method, qa_pairs CLI argument format, Markdown template styling

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` § Phase 35
- `.planning/REQUIREMENTS.md` § AI-01, AI-02, AI-03
- `.planning/phases/33-deep-reading-dashboard-rendering/33-CONTEXT.md`
- `paperforge/worker/asset_index.py` — ai_path computation
- `paperforge/skills/literature-qa/scripts/ld_deep.py` — CLI subparser pattern
- `paperforge/skills/literature-qa/scripts/pf-paper.md` — Prompt to update
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `asset_index.py:307` — ai_path already computed
- `ld_deep.py` — argparse subparser + dual import/subprocess pattern
- `_utils.py` — read_json/write_json patterns

### Integration Points
- `pf-paper.md` needs new "保存讨论记录" step
- Phase 36 verifies full pipeline: agent records → dashboard reads discussion.json
</code_context>

<specifies>
- pf-deep 不需要记录
- Agent 在 session 中积累 Q&A，结束时调用 CLI
</specifies>

<deferred>
## Deferred Ideas

- Direct agent-paper discussion recording (非 pf-paper 场景) — future capability
</deferred>

---

*Phase: 35-ai-discussion-recorder*
*Context gathered: 2026-05-06*
