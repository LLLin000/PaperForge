# Annotation Phase 3: Annotation CLI JSON Contracts - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Annotation Phase 3 exposes the annotation backend through stable CLI commands:

`paperforge annotation import/list/status/export --json`

In plain terms: Phase 2 builds the safe Zotero-to-PaperForge import machinery. Phase 3 gives that machinery a command-line surface that a user, Obsidian plugin, or future automation can call without guessing internal Python APIs.

This phase defines command names, flags, JSON response shape, dry-run/apply behavior, and failure output. It does not build the Obsidian PDF overlay, local PDF annotation editor, Zotero write-back, or concept-card evidence integration.

</domain>

<decisions>
## Implementation Decisions

### Command Shape
- **D-01:** Annotation commands must live under a single namespace: `paperforge annotation ...`.
- **D-02:** Phase 3 should add four subcommands: `import`, `list`, `status`, and `export`.
- **D-03:** Do not scatter annotation behavior into existing `sync`, `status`, `doctor`, or `memory` commands. Existing commands may later call annotation status internally, but the user-facing annotation API starts here.

### Import Behavior
- **D-04:** `paperforge annotation import` defaults to preview mode, meaning it should show what would happen without writing changes to `annotations.db`.
- **D-05:** Real writes require an explicit `--apply` flag. This keeps annotation imports safe because they can mark stale rows in PaperForge's annotation database.
- **D-06:** The JSON output must clearly distinguish preview from applied import using a stable field such as `dry_run: true/false` or `applied: true/false`.
- **D-07:** Import output must include stable counts for inserted, updated, unchanged, stale/soft-deleted, skipped, and invalid rows when those counts are available from the backend.

### Paper Filtering
- **D-08:** The main paper selector should be `--paper KEY`.
- **D-09:** `--paper KEY` should be allowed to resolve through the existing PaperForge paper identity layer where possible, rather than forcing users to know internal IDs.
- **D-10:** Advanced disambiguation may use `--attachment-key` because a Zotero item can have multiple attachments. This should stay optional and only needed when one paper has more than one relevant PDF attachment.
- **D-11:** Avoid making `--zotero-key` the only public entry point. Zotero is the first source, but `annotations.db` is source-agnostic and future sources should not make the CLI name obsolete.

### JSON Contract
- **D-12:** All annotation `--json` commands should use the existing PFResult-style envelope: `ok`, `command`, `version`, `data`, and `error`.
- **D-13:** Command-specific payload belongs under `data`, not at the top level. For example, import counts go in `data.counts`, and listed annotations go in `data.annotations`.
- **D-14:** The `command` value should be stable and specific, such as `annotation.import`, `annotation.list`, `annotation.status`, and `annotation.export`.
- **D-15:** JSON keys should be machine-friendly English identifiers. User-facing text fields may include Chinese-friendly explanations where useful.

### Error Output
- **D-16:** With `--json`, failures must return valid JSON rather than traceback text.
- **D-17:** JSON failures must include a stable error code, a clear message, optional details, and optional suggestions.
- **D-18:** Error messages should be actionable in plain language. For example, say that the Zotero database was not found and tell the user to check `--zotero-db` or `paperforge.json`, instead of only showing `sqlite3.OperationalError`. Chinese-friendly messages are preferred for user-facing text.
- **D-19:** Representative error cases for this phase are: missing Zotero DB, unreadable or locked Zotero DB, missing PaperForge config, unknown Zotero annotation schema, invalid annotation payload, invalid paper filter, missing `annotations.db`, and schema version mismatch.

### List vs Export
- **D-20:** `paperforge annotation list --json` is the lightweight view for quickly showing ordered annotations for one paper.
- **D-21:** `list --json` should include fields needed for scanning: id, type, page, selected text, comment, color, source, read-only state, and source provenance.
- **D-22:** `paperforge annotation export --json` is the full structured payload for plugins, downstream tools, and future evidence workflows.
- **D-23:** `export --json` should be paper-scoped and include complete annotation content, source identity, timestamps, JSON position/selector fields, tags, and soft-delete state where relevant.
- **D-24:** Both `list` and `export` should work without Obsidian plugin runtime.

### the agent's Discretion
- The planner may choose exact internal module names, as long as they follow the existing `paperforge.commands.*` pattern.
- The planner may choose exact count field grouping, as long as the output remains stable and includes preview/apply state.
- The planner may decide whether annotation status lives in `paperforge.commands.annotation` or a small annotation command package, as long as `paperforge.cli.build_parser()` keeps the user-facing namespace stable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/ROADMAP.md` - Annotation Phase 3 goal, dependencies, and success criteria.
- `.planning/REQUIREMENTS.md` - CLI-01 through CLI-05 and SAFE-03 requirements.
- `.planning/STATE.md` - Current milestone state and dependency status.

### Prior Annotation Decisions
- `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-CONTEXT.md` - Phase 2 safety decisions that Phase 3 must preserve.
- `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-01-PLAN.md` - Planned Zotero probe and structured error foundation.
- `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-02-PLAN.md` - Planned normalization contract.
- `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-03-PLAN.md` - Planned import result counts and scoped reconciliation behavior.
- `.planning/phases/annotation-02-zotero-probe-safe-import/annotation-02-04-PLAN.md` - Planned end-to-end verification expectations.

### Existing CLI Patterns
- `paperforge/cli.py` - Main argparse parser and command dispatch.
- `paperforge/commands/status.py` - Existing command module pattern and PFResult JSON style.
- `paperforge/commands/sync.py` - Existing command with `--dry-run`, `--json`, and worker dispatch.
- `tests/cli/test_json_contracts.py` - Existing CLI JSON contract tests.
- `tests/cli/test_error_codes.py` - Existing CLI error output tests.
- `tests/cli/test_contract_helpers.py` - JSON assertion and snapshot normalization helpers.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/cli.py`: central place to add `annotation` parser and dispatch.
- `paperforge/commands/`: established home for command modules that implement `run(args)`.
- `tests/cli/conftest.py`: existing CLI invocation fixture should be reused for annotation CLI tests.
- `tests/cli/test_contract_helpers.py`: existing helpers can validate JSON shape and normalize snapshots.

### Established Patterns
- Commands are registered in `build_parser()` and then dispatched in `main()`.
- JSON-capable commands usually accept `--json` and print a single JSON object to stdout.
- Existing newer commands use a PFResult-style shape with `ok`, `command`, `version`, `data`, and `error`.
- Existing tests distinguish machine-readable JSON contracts from human-readable text contracts.

### Integration Points
- Phase 3 depends on Phase 2 modules for Zotero probe/import behavior. If Phase 2 is not executed yet, Phase 3 planning should describe dependencies rather than invent duplicate backend logic.
- Annotation CLI should call PaperForge-owned annotation services and `annotations.db`; it must not write to Zotero SQLite.
- `paperforge_paths(vault)` already exposes `annotations_db`; status/export commands should use configured paths.

</code_context>

<specifics>
## Specific Ideas

- Prefer safe-by-default import: preview first, explicit `--apply` to write.
- Keep command names short and predictable: `import`, `list`, `status`, `export`.
- Keep `--paper KEY` as the human-facing selector, with optional `--attachment-key` for multi-PDF cases.
- Use Chinese-friendly explanations in error messages where they help the user understand what to fix, while keeping JSON keys stable in English.

</specifics>

<deferred>
## Deferred Ideas

- Obsidian PDF overlay remains deferred to a later annotation milestone.
- Local annotation editing remains deferred.
- Zotero write-back remains deferred and must not be implemented through direct SQLite mutation.
- Concept-card/deep-reading evidence integration remains deferred until backend and CLI contracts stabilize.

</deferred>

---

*Phase: annotation-03-cli-json-contracts*
*Context gathered: 2026-06-18*
