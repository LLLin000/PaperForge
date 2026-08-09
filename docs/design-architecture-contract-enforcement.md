# ArchitectureContract Enforcement and Authority Collectors

> Date: 2026-08-09
> Status: **ACCEPTED — ARCHITECTURE FROZEN** (decision [#149](https://github.com/LLLin000/PaperForge/issues/149))
> Research: [#152](https://github.com/LLLin000/PaperForge/issues/152), Client boundaries: [#144](https://github.com/LLLin000/PaperForge/issues/144), Bootstrap: [#143](https://github.com/LLLin000/PaperForge/issues/143), Action contract: [#145](https://github.com/LLLin000/PaperForge/issues/145), Read-model cutover: [#148](https://github.com/LLLin000/PaperForge/issues/148)

## 0. Principle

**Complete the existing ArchitectureContract + deterministic collectors + E2E surface; do not build a second lint/policy stack.** The audit stays a *deterministic structural fact* auditor, not a *static semantic understanding* engine.

```text
Collector output → ArchitectureSurvey → ArchitectureContract → DeterministicAudit → Report → Ledger projection
```

- tracked contract commit = authority; collector evidence = observation; report = projection; ledger = project-tracking projection.
- deterministic reconciliation never auto-changes lifecycle and never modifies inputs.
- Review never modifies deterministic facts.

## 1. Minimal additions (the whole delta)

### 1.1 `RuleKind.CANONICAL_READ` (new — the only new kind)

```text
RuleKind.CANONICAL_READ
```

Rules split per canonical unit for locatable findings:

```text
client_read.formal_library
client_read.paperforge_config
client_read.ocr_state
client_read.memory_db
client_read.runtime_snapshots
```

Prohibited pattern: plugin/TS-side reads of canonical vault state (formal-library.json, paperforge.json, OCR meta/hash/blocks/role-index, memory DB, snapshots). Structural facts only — the collector reports *where canonical units are read*, it never judges semantic equivalence.

### 1.2 `FilesystemReadFact` (new — the only new fact)

```python
@dataclass(frozen=True)
class FilesystemReadFact:
    operation_id: str
    unit_id: str | None
    wrapper_id: str | None
    path_expression: str
    evidence: Evidence
```

Answers one question: **where does TS read which canonical unit?**

TS collector extraction:

- `readFile` / `readFileSync`, `open` where applicable, SQLite open/read wrappers, Obsidian `Vault.read` / `cachedRead`.
- Statically resolvable path to a canonical unit → exact `FilesystemReadFact` (or VIOLATED when the callsite is outside a legitimate adapter).
- Dynamic/unclassifiable path → `UnresolvedFact` (existing semantics).

No `SpawnFact` is added: the existing TS collector already identifies spawns and reports unregistered spawns as `UnresolvedFact` with `possible_effects = remote_operation, business_mutation`.

### 1.3 Wrapper registry (collector knowledge, not contract policy)

Permanent allowances are expressed as **first-class contract roles/operations + a wrapper registry**; they are not `Rule.allowed_wrappers` fields and not `ExceptionDecl`.

```text
ArchitectureContract declares the semantic role/operation:

bootstrap.pointer.read   adapter = plugin.bootstrap
client_cache.read        adapter = plugin.cache
navigation.open          adapter = plugin.navigation
workspace.context        adapter = plugin.workspace

Wrapper registry (extractor knowledge, Tier 2) maps concrete helpers:

readRuntimePointer()  → bootstrap.pointer.read
loadLastKnown()       → client_cache.read
openReturnedPath()    → navigation.open
getActiveFile()       → workspace.context
```

`ExceptionDecl` keeps exactly one job: **temporary migration deviations** with explicit rationale + `review_condition` + eventual removal.

## 2. Reuse map — everything else stays on existing mechanisms

| Concern | Mechanism (no new kind) |
|---|---|
| Semantic duplication (e.g., two materialization-repair recommenders, W3) | review + E2E (facts → reconcile → exactly one recommendation source) + implementation deletion/grep assertions |
| Action policy ownership (TS argv tables, `isAutomaticLocal`/`requiresConfirmation`) | `ROLE_AUTHORITY` (action.dispatch: Python authority, plugin = ADAPTER) + #145 parity tests; old symbols deleted deterministically in T8 |
| Runtime install/lifecycle ownership | `ROLE_AUTHORITY` (setup/update/repair/pointer-write: Python; bootstrap = one-time install + pointer READ) + wrapper registry |
| Snapshot retirement | existing `CANONICAL_WRITER` rules over snapshot units; lifecycle → deprecated + deletion with #148 cutover |
| Wire command strings | #145 contract/parity tests (no-command-wire), not an audit rule |
| Exceptions | existing `ExceptionDecl` (review_condition, temporary) |
| Promotion | existing lifecycle + enforcement axes (below) |
| Report | existing renderer (below) |

## 3. Lifecycle and enforcement promote separately

Two axes stay independent (they already exist in the model):

```text
Lifecycle:     planned → active → deprecated
Enforcement:   observe → advisory → blocking
```

Promotion ladder for new rules:

```text
planned + observe/advisory
      ├ synthetic fixtures
      ├ golden fixture
      ├ real-repo evidence
      └ unresolved/FP review
      ↓
active + advisory
      ├ CI soak
      └ no systemic false positives
      ↓
active + blocking
```

`CANONICAL_READ` involves dynamic paths, Obsidian API, and wrapper classification — it starts planned/observe and earns blocking. The gate `--allowlist` (reviewed low-FP rules only) is unchanged.

## 4. Report presentation

Unchanged: existing report with rule coverage, findings, severity, lifecycle, evidence. New rules appear as planned-gap/advisory until promoted. No new HTML pages, badges, or dashboards.

## 5. ADR and glossary (documentation only, no machinery)

- One consolidated ADR: `docs/adr/python-core-authority.md` — Context / Decision / Consequences, with sections: § Read Model, § Action, § Reconciliation, § Progress, § Bootstrap, § Thin Client, § Trigger, § Enforcement.
- Glossary: one section in the existing architecture/glossary document adding six terms: Canonical Fact, Semantic Read Model, Action Contract, Bootstrap Adapter, Client Cache, Convergence Tick.
- Explicitly rejected: `terms.json`, ADR IDs injected into the contract schema, collectors checking ADRs, glossary codegen. The ADR explains *why*; the Contract is the machine authority.

## 6. Evidence authority (process, no new rule kind)

```text
collector output → survey → contract → deterministic audit → report → ledger projection
```

- Contract promotion is a tracked commit (ArchitectureContract.lifecycle), never implied by issue close or ledger prose (repo truth hierarchy).
- Report is collector-driven; ledger (`PROJECT-MANAGEMENT.md`) is a projection and never overrides it.
- Exceptions carry `review_condition`.

## 7. UNRESOLVED semantics — never a pass

- `UNRESOLVED` only when the collector genuinely cannot determine the fact (e.g., dynamically computed path).
- A **statically provable violation** is `VIOLATED` even when the wrapper is unrecognized — unknown wrapper must not downgrade a known violation.
- `blocking + unresolved` → audit **incomplete** → gate **not green** (fail-incomplete), never treated as no-violation.
