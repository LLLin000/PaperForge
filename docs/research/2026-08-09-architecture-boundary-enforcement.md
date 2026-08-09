# Architecture Boundary Enforcement Research

- Date: 2026-08-09
- Wayfinder ticket: [#152](https://github.com/LLLin000/PaperForge/issues/152)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Scope: Primary-source research plus current-repository enforcement mapping; no production implementation.

## 0. Corrected seam model

The seam to enforce is the **versioned Python CLI / read-model / action protocol**: the TypeScript plugin is an adapter client — it gets state from read-model commands (status / paper-context / search) and causes change through action commands. **Canonical vault files are internal Python authorities, not a TS-visible seam.** Enforcement target: the plugin's only data/effect path is the protocol; nothing on either side re-implements authority semantics; migration artifacts retire on schedule; permanent adapter roles are first-class contract, temporary deviations are exceptions.

Read access has two distinct classes that must not be conflated: (a) **forbidden semantic canonical reads** — the plugin parsing canonical *state* files (meta.json, ocr state, figure inventory, fulltext.md-as-state) to derive meaning; (b) **permitted display/open** — the plugin opening or rendering artifacts the Python side returned to it (note .md paths, PDF/fulltext paths from the read-model, for the GUI). Rules are path-class based, not a blanket read ban.

## 1. The five migration invariants

**I1 — Plugin cannot semantically read/write canonical facts.**
- Write side: **provable today.** `canonical.no_ui_writer` + `publication.uses_protocol` flag any plugin canonical write not routed through the authorized publication protocol; TS Tier-1 fs-write sinks + wrapper registry already produce these facts.
- Read side (semantic): **the one justified collector gap.** `ts_collect.js` / `python_ast.py` collect writes and subprocess spawns; reads are invisible. Minimal fix: add read sinks (readFileSync/readFile/existsSync; read_text/read_bytes/open-r) to Tier-1, ~30–60 lines per collector. Contract rule then: plugin read facts may only target **allowlisted display/artifact path classes returned via the protocol**; read facts on canonical-state paths are violations. Dynamic/unresolvable read targets follow existing Tier-3 `unresolved` semantics.
- Semantic reading (deriving meaning from content) is not fully statically provable → E2E: plugin integration test asserting plugin data flow consumes only CLI read-model output.

**I2 — Duplicate classifiers/readiness logic are absent.**
- Provable in part: signal facts + wrapper registry assert **producer/consumer identity** (e.g. OCR_REBUILD_PROGRESS producer is backend; plugin registers only as consumer); an unregistered duplicate producer surfaces as an unexpected producer fact.
- **Authority half — prefer deterministic role facts**: extend the wrapper registry so registered wrappers emit `RoleAuthorityFact` (execution/lifecycle_state/stop/observer/adapter), closing today's `unresolved` role rules (`role_authority.ocr_execution/ocr_stop/embed_stop`) from collector-observable callsites. Declared-evidence review is only the fallback where collectors genuinely cannot observe (process-boundary authority).
- Not provable: semantic duplication of classification/readiness computation inside plugin code. → Review checklist item ("plugin must not re-derive state it receives from the read-model") + E2E state-shape parity (plugin-rendered state equals CLI-provided state on fixture vaults).

**I3 — Snapshot writers/readers retire after cutover.**
- **Primary: same no-read/no-write collector path rules as I1.** After cutover, contract rules forbid read AND write facts targeting snapshot paths. Removed code → zero facts → satisfied; a renamed or reimplemented snapshot writer/reader still touches the same paths → facts → violation. Path-based facts are structural; an import-absence test alone misses reimplementations and is only an optional complement (cheap pytest), never the mechanism.
- Contract records the cutover as `effective_after` (issue+commit).
- E2E: post-cutover migration run produces no snapshot artifacts.

**I4 — Generic action transport replaces client action semantics.**
- Provable with existing machinery: register the generic action transport as the **only authorized wrapper** for plugin-origin mutations; any plugin mutation fact not routed through it violates (WriteSpec fields writer_id / publication_authority / via_publication_protocol already express this — registry-only, no new rule kind).
- E2E: action-path test — plugin action → CLI executes semantics → canonical unit updated by the authority; plugin never writes directly.

**I5 — Bootstrap adapter and GUI allowances are first-class; exceptions are temporary.**
- **First-class contract roles/wrappers (permanent, not ExceptionDecls):** the Bootstrap Adapter (settings/workspace-state read/write during bootstrap) and GUI display/navigation allowances (opening/rendering Python-returned note/PDF/fulltext paths). `AuthorityRole` already includes ADAPTER and OBSERVER; model these as declared roles on the relevant operations plus wrapper specs carrying authorized read/write facts. These are legitimate, permanent parts of the contract — exceptions machinery is the wrong bucket for them.
- **ExceptionDecl is reserved for temporary migration deviations** with `review_condition` + expiry; reconciler applies `RuleStatus.EXCEPTION_APPLIED`, gate treats it as non-blocking. Current contract `exceptions: []` is consistent.
- E2E: bootstrap test asserts bootstrap-scoped access happens only in the bootstrap window.

## 2. Minimal collector / E2E matrix

| Invariant | Collector-provable (exists) | Collector-provable (small ext.) | E2E | Review |
|---|---|---|---|---|
| I1 write | canonical_writer / publication_marker + TS Tier-1 writes | — | plugin data flow via CLI only | — |
| I1 read semantic | — (reads uncollected) | fs-read sinks + path-class rule (~30–60 lines) | vault-state-free data flow | policy: which paths are canonical-state vs display |
| I2 duplicate producers | signal facts + registry (producer identity) | — | state-shape parity (render == CLI state) | duplicate-semantics checklist |
| I2 authority | role_authority rules (currently unresolved) | registry wrappers emitting RoleAuthorityFact | lifecycle E2E (stop via delegated executor) | declared-evidence only as fallback |
| I3 retirement | — (path rules after cutover) | same read/write path rules as I1 | no snapshot artifacts post-cutover | cutover issue/commit record |
| I4 transport | registry sole-authorization of transport wrapper | — | action path E2E | legacy-path exception list |
| I5 bootstrap/UI | ADAPTER/OBSERVER roles + authorized wrapper facts | — | bootstrap-window test | exception expiry (temporary only) |

## 3. Adopt / Defer / Reject

### ADOPT — wire existing machinery (zero new deps)
1. **Allowlist promotion as lifecycle review, not blanket.** Promote gate-eligible rules one at a time via `ArchitectureReview` (adjudication + issue link), each based on a **clean-repo audit run** — the live audit (docs/architecture-audit-2026-08-06/audit.json) is gate-ineligible (`repository_dirty`, transient) and must not drive promotion. Candidates with satisfied findings: query.side_effect_free, signal.has_consumer, publication.uses_protocol, canonical.no_ui_writer, restore.display_only, coverage.required_complete, collectors.deterministic.
2. **Wrapper registry as the protocol contract (I4 + I2 authority + I5 roles).** Extend the default registry with: CLI read-model/action-transport entries; wrappers that emit RoleAuthorityFact for ocr_run/ocr_rebuild/embed_build_resume (prefer deterministic role facts over declared evidence); Bootstrap-Adapter and GUI display/navigation wrapper facts. Registry stays versioned separately from contract policy (existing design).
3. **First-class I5 roles** via AuthorityRole.ADAPTER/OBSERVER + authorized wrapper facts; ExceptionDecl reserved for temporary deviations only.
4. **I3 retirement path rules** — once cutover lands, add no-read/no-write path rules over snapshot paths to the contract; optional import-absence pytest as complement.

### ADOPT — minimal, justified extension (the only new code)
5. **fs-read sink collection** in `ts_collect.js` (+ symmetric `python_ast.py`): ~30–60 lines, reuses existing evidence/fact plumbing; enables the I1 read path-class rule, the I3 retirement rule, and the I5 permitted-display classes from one mechanism.

### DEFER (trigger noted)
6. JSON Schema for contract/registry — only if a TS-side consumer of the contract emerges; dataclass validation + issue references suffice today.
7. Generated TS constants from Python enums — only after a real cross-language literal-drift bug is observed.
8. gate.py GitHub-annotations mode — cosmetic; the HTML report suffices.
9. ADR field on rules — existing `effective_after`/`known_gap` issue references satisfy traceability for now.

### REJECT
10. **terms.json + glossary-parity collector** — a literal-set diff does not prove the required invariant (I2 is about *absent duplicate semantics*, which is code behavior, not vocabulary sets); YAGNI until a concrete drift bug. If that happens, revisit via the JSON Schema Test Suite conformance pattern, not a custom collector.
11. **External tools** — import-linter (Python-only import edges, cannot see TS), dependency-cruiser (new dep + second rule language; typescript already wired into ts_collect.js), eslint no-restricted-imports / import/no-restricted-paths (plugin has no eslint; import edges aren't the seam's risk surface), ts-arch (TS-only test framework), Nx enforce-module-boundaries / Conformance (monorepo-oriented; Conformance enterprise-licensed), Semgrep as primary substrate (per-pattern rules drift from contract; community edition single-function/file-boundary), OPA/Rego + conftest (contract+reconciler already is a policy engine with epistemic statuses Rego lacks), ArchGuard (server+DB platform).
12. **ArchUnit-freeze / depcruise-baseline as the gate mechanism** — baselines permanently mask known violations; depcruise's own docs warn the known-violations format may shift without a major bump. Allowlist-of-reviewed-rules + planned-gap achieves the same onboarding without masking.

## 4. Open risks and questions
- **Role-authority facts**: registry wrappers must map real plugin/backend callsites to role facts without fabricating observation — if a role is assigned outside code (process boundary), declared evidence remains the honest fallback.
- **fs-read false positives**: plugin reads of non-canonical files (settings, workspace state) must be scoped via the I5 first-class roles, not by suppressing the collector.
- **Path-class stability**: the canonical-state vs display path classification lives in the contract; drift between the two lists silently weakens I1 — keep it one table in the contract, reviewed with the contract.
- **Retirement timing**: I3 path rules must land with (not before) the cutover, else pre-cutover legacy paths produce violations; use `effective_after` on the rule.
- **Promotion reviews on clean tree**: repository_dirty gate-ineligibility is transient and must not block or drive allowlist decisions.
- **Exception creep**: with I5 moved to first-class roles, ExceptionDecls should be rare; enforce review_condition expiry on the few that remain.

## 5. Bibliography (primary sources)
1. import-linter — https://import-linter.readthedocs.io/en/stable/
2. Kubernetes import-boss — https://github.com/kubernetes/kubernetes/blob/master/cmd/import-boss/README.md
3. dependency-cruiser — https://github.com/sverweij/dependency-cruiser ; doc/cli.md (baseline, --ignore-known, format caveat)
4. Nx Enforce Module Boundaries — https://nx.dev/features/enforce-module-boundaries
5. ArchUnit §8.6 Freezing Arch Rules — https://www.archunit.org/userguide/html/000_Index.html#_freezing_arch_rules
6. pytest-archon — https://github.com/jwbargsten/pytest-archon ; ts-arch — https://github.com/ts-arch/ts-arch
7. ESLint no-restricted-imports — https://eslint.org/docs/latest/rules/no-restricted-imports ; import/no-restricted-paths — https://github.com/import-js/eslint-plugin-import/blob/main/docs/rules/no-restricted-paths.md
8. Semgrep — https://github.com/semgrep/semgrep
9. Vitest Snapshot (CI behavior) — https://vitest.dev/guide/snapshot
10. JSON Schema Test Suite — https://github.com/json-schema-org/JSON-Schema-Test-Suite
11. pydantic JSON Schema — https://docs.pydantic.dev/latest/concepts/json_schema/ ; json-schema-to-typescript — https://github.com/bcherny/json-schema-to-typescript
12. Conftest — https://www.conftest.dev/ ; Django system checks — https://docs.djangoproject.com/en/5.0/ref/checks/
13. Jupyter messaging spec — https://jupyter-client.readthedocs.io/en/stable/messaging.html
14. Nygard ADR — https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions ; MADR — https://adr.github.io/
15. Ruff preview — https://docs.astral.sh/ruff/preview/ ; ThoughtWorks fitness function — https://www.thoughtworks.com/radar/techniques/architectural-fitness-function
16. PaperForge: paperforge/architecture_audit/report/gate.py ; paperforge/architecture_audit/layers.py ; paperforge/architecture_audit/collectors/ts_collect.js ; paperforge/architecture_audit/collectors/python_ast.py ; paperforge/architecture_audit/collectors/common.py ; docs/architecture-audit-2026-08-06/contract.json ; docs/architecture-audit-2026-08-06/audit.json ; .github/workflows/ci.yml ; tests/test_architecture_audit_collectors.py