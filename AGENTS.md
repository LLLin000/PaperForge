# PaperForge — Agent Operating Guide

> Principles and execution rules for this project. Detailed how-tos live in `docs/` and project skills.

---

## Design Rules

### 1. The pipeline is a contract, not code

The OCR pipeline has a fixed ordering because each stage makes assumptions about what the previous stage has written. Breaking the order breaks those assumptions silently — no crash, just wrong output.

The order is:

raw blocks → build structured (seed roles) → pre_match_normalize → figure/table matching → post_match_normalize → apply_object_writebacks → write inventory → extract objects → render

Key invariants:
- **writeback before write_inventory** — `apply_object_writebacks` stamps `associated_text_block_ids` onto the in-memory figure inventory. If inventory is written before writeback runs, those claims are lost from disk. The in-memory `figure_inventory` dict is the one source of truth during a session; the JSON file is a checkpoint.
- **matching on candidate roles, not final roles** — V3 runs matching with `role_candidate` set but `role` still at `seed_role`. The matching code uses `_match_role()` which reads `role_candidate → role → seed_role` in priority order. This is intentional: it lets figure/table matching see caption candidates before normalize hard-commits their role.

### 2. V3 is on by default; trust the shadow

`OCR_PIPELINE_V3=0` reverts to legacy. V3 was enabled after a 555-paper full vault corpus diff: 547/555 no diff, 5/555 v3 improvements (3 more figures found, 2 block boundary corrections). All 5 diffs were v3 being more correct.

Trading rule: if V3 produces a different answer than legacy, believe V3. Legacy's normalize-then-match order prematurely hardens roles before matching can see caption candidates. V3 defers role commit until after matching. The diff evidence supports this.

### 3. Figure inner_text is figure content, not body text

Blocks identified as `figure_inner_text` (y-axis labels, panel markers, nomogram variable names) belong in the cropped figure image, not as separate text in the render. The chain:

`tag_figure_contained_text` or side-adjacent scoring → stamps `_object_owner_id` on the block → `extract_and_write_objects` expands crop bbox to include the block → `render_figure_object_markdown` outputs only image + Legend

Never add a text listing of inner_text below a figure image. The bbox expansion IS the merge. This applies equally to side-adjacent and contained-text blocks — role unifies them.

### 4. Ownership evidence is the test surface

The `apply_object_writebacks` seam is where figure/table ownership claims are stamped onto blocks. Test through this interface: if the claim is wrong, the problem is in the scoring or the inventory, not in the writeback. Tests should assert on `block["_object_owner_id"]` and `block["_object_association_reason"]` after writeback runs.

---

## Execution Rules

### 1. Two verification phases

Before committing: (a) run the focused suite (`105 tests — v3 + writeback + tail settlement + appendix numbering + rendering`), (b) if changing figure/table matching, also run the full figure test suite.

If focused suite fails, don't push. No exception.

### 2. Rebuild before debug

If a production paper has wrong output, rebuild it with `python scripts/dev/ocr_rebuild_paper.py <KEY>` before investigating. The rebuild runs the current code path; what's on disk may be stale.

### 3. Start from context, not grep

The project has many interlocking modules. Use `search_graph` (codebase memory MCP) to trace call chains before opening files. `trace_path("build_figure_inventory", direction="both")` gives callees and callers in one shot. `get_code_snippet("_score_side_adjacent_text_claim")` gives the exact function body without the 6295-line file dump.

### 4. Commit granularity

One logical change per commit. A logical change is: a bug fix, a feature, a refactor. Not "fix + new test + unrelated lint." Every commit message must state what changed and why — the rationale that a reviewer (human or agent) needs to decide whether it's correct.

### 5. Post-session

Update `PROJECT-MANAGEMENT.md` with a timeline entry, fix table row, and decision log entry. Archive stale `project/current/` files to `project/archive/`.


## Agent skills

### Issue tracker

GitHub Issues, with external PRs as a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Multi-context — CONTEXT-MAP.md at root pointing to per-context CONTEXT.md files. See `docs/agents/domain.md`.
---

## Reference

| Topic | Location |
|-------|----------|
| Architecture | `docs/ARCHITECTURE.md` |
| OCR spec index | `docs/archive/superpowers/specs/README-ocr.md` |
| Command docs | `docs/COMMANDS.md` |
| Project state | `project/current/ocr-v2-active-queue.md` |
| Full history | `PROJECT-MANAGEMENT.md` |
