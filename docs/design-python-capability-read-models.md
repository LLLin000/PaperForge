# Python Capability Services and Semantic Read-Model Contract

- Date: 2026-08-09
- Decision ticket: [#140](https://github.com/LLLin000/PaperForge/issues/140)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Inputs: [#136 authority audit](https://github.com/LLLin000/PaperForge/issues/136), [#147 control-center reconciliation](https://github.com/LLLin000/PaperForge/issues/147), [#151 control-plane research](https://github.com/LLLin000/PaperForge/issues/151)
- Scope: architecture and migration contract; no production implementation

## 1. Decision

Use capability-owned Python read functions behind two small public operations:

```python
probe(module: ModuleId, context: ReadContext) -> CapabilityEnvelope
probe_all(context: ReadContext) -> ProbeAll
```

The functions are the application seam. They return JSON-ready typed mappings; no service classes, query objects, generic rule interpreter, dynamic registry, HTTP API, daemon, or persistent Python cache.

Each capability owns its semantic decision tree. A fixed dispatcher owns name routing, unexpected-exception conversion, deterministic aggregation, and CLI exit mapping. `commands/probe.py` becomes a transport adapter only.

This is a three-part seam:

```text
Canonical authorities
    ↓ module-owned readers
Capability semantic functions
    ↓ fixed dispatcher / pure maintenance projection
Versioned read models
    ↓ serialization only
CLI / Obsidian / Agent / tests
```

Canonical modules never import the read-model package. Clients never import canonical readers or parse canonical files.

## 2. Capability classification

The six accepted control-center modules remain unchanged.

| Concern | Classification | Owner and consequence |
|---|---|---|
| `installation` | Required capability envelope | Python derives runtime/config/package compatibility. Bootstrap performs pre-Python discovery and handoff, but does not own this semantic verdict. |
| `library` | Required capability envelope | Python derives catalog/index freshness from the existing library authorities. |
| `ocr` | Optional capability envelope | Python derives aggregate OCR readiness and activity. Per-paper rows stay out of the envelope. |
| `memory` | Optional capability envelope | Python derives database, FTS, and vector readiness in one ordered decision tree. |
| `maintenance` | Required derived envelope | A pure projection of the other five envelopes; it never re-probes canonical sources. |
| `help` | Optional capability envelope | Python reports packaged help/skill availability. It is never maintenance-eligible by itself. |
| Configuration | Separate `config` contract family | `paperforge.json` is substrate, not a seventh capability. #142 owns read/validate/write semantics. Capability readers consume one resolved config result per invocation. |
| Vector | Detail axis of `memory`, not a seventh capability | SQLite `build_state`, vec0 state, dependency availability, and legacy Chroma presence remain memory-owned. Existing `embed status --json` is the detail surface unless implementation proves one missing field. |
| Diagnostics | Separate diagnostics family | `ocr doctor`, `runtime-health`, architecture audit, and issue drafts remain explicit, redacted commands. `probe all` never runs deep or network diagnostics. |
| Actions | Separate action family | Envelopes reference a stable `action_id`; #145 owns descriptor and execution semantics. No command string enters a read model. |

Vector remains explicit without duplicating authority: `memory` owns the user-facing verdict; vector detail explains that verdict.

## 3. Python application interface

### 3.1 Read context

One context is built per CLI invocation:

```python
@dataclass(frozen=True)
class ReadContext:
    vault: Path
    config: ResolvedConfig | ConfigProblem
    observed_at: datetime
```

Rules:

- `config` is loaded once through the canonical Python config contract.
- `observed_at` is fixed once so `probe all` has a coherent read timestamp and deterministic tests.
- The context contains no client state, cache, subprocess, credential value, service locator, or mutable resource.
- The old `last_operation_exit_code` probe hint is removed. An action result reports its own failure; the next probe derives current state from canonical facts.
- Plugin/package compatibility belongs to the bootstrap handshake, not a caller-supplied capability-state hint.

### 3.2 Capability readers

Internal functions are capability-specific:

```python
read_installation(context) -> CapabilityEnvelope
read_library(context) -> CapabilityEnvelope
read_ocr(context) -> CapabilityEnvelope
read_memory(context) -> CapabilityEnvelope
read_help(context) -> CapabilityEnvelope
derive_maintenance(envelopes) -> CapabilityEnvelope
```

The public dispatcher uses one fixed mapping and order:

```python
PROBE_ORDER = ("installation", "library", "ocr", "memory", "help")
```

The mapping is static code, not an extension registry. A seventh module requires an explicit contract change.

### 3.3 Aggregation

`probe_all`:

1. builds one `ReadContext`;
2. calls each base reader exactly once and sequentially in `PROBE_ORDER`;
3. converts an unexpected reader exception into that module's valid `detection_failed` envelope;
4. derives `maintenance` from those exact five envelopes;
5. returns every base envelope unchanged plus the derived maintenance envelope.

Standalone `probe maintenance` uses the same fan-out and projection. No reader calls another reader. Maintenance is the only cross-capability projection.

Sequential evaluation is deliberate. All current summary reads are local and bounded; parallelism would add ordering and exception complexity without measured latency benefit. A future genuinely blocking probe may own a local timeout, but does not justify aggregate timeout machinery now.

## 4. Contract families

Each family has an independent major version. Same-major changes are additive; unknown fields are ignored. Unsupported majors fail closed.

| Family | Initial major | Purpose |
|---|---:|---|
| `paperforge.capability` | 3 | One module summary envelope |
| `paperforge.probe_all` | 1 | Deterministic collection of unchanged capability envelopes |
| `paperforge.<module>.detail` | Per existing command | Module-specific rows or diagnostics-sized detail |
| `paperforge.config` | Owned by #142 | Validated config reads and mutations |
| `paperforge.action` | Owned by #145 | Safe action descriptors, execution, and follow-ups |
| `paperforge.progress` | Owned by #137/#139 | NDJSON long-operation events |
| `paperforge.credential` | Owned by #138 | Credential status/mutation without secret disclosure |
| diagnostics | Existing command-specific contracts | Explicit deep checks and redacted support output |

Package SemVer does not determine these majors.

## 5. Capability envelope v3

Version 3 is a deliberate clean cutover from the current schema v2. It retains the accepted semantic axes and removes superseded transport fields.

```json
{
  "schema_family": "paperforge.capability",
  "schema_version": 3,
  "module": "library",
  "capability_state": "needs_action",
  "activity_state": "idle",
  "activity_label": null,
  "activity_progress": null,
  "severity": "warning",
  "reason": {
    "code": "library.index_stale",
    "text": "Library index is stale"
  },
  "action": {
    "primary": {
      "action_id": "library.sync"
    }
  },
  "notices": [],
  "user_state": "action_required",
  "capability_kind": "required",
  "maintenance_eligible": true,
  "user_visible_failure": false,
  "user_impact": "Search and downstream indexes may omit recent papers",
  "observed_at": "2026-08-09T11:30:00Z",
  "source_revisions": {
    "catalog": "sha256:…",
    "exports": "sha256:…"
  },
  "pipeline_version": null
}
```

Required fields:

- `schema_family`, `schema_version`, `module`;
- capability, activity, severity, reason, and user-state axes;
- one primary action reference or `null`;
- notices and maintenance flags;
- `observed_at`;
- `source_revisions`, an object of logical source name to opaque revision, possibly empty;
- `pipeline_version`, nullable.

Rules:

- State ordinal remains `unknown < unavailable < missing_input < needs_action < limited < ready`.
- `ready` has no primary action. `unknown` offers only the module's safe re-probe action.
- Reason codes remain `<module>.<snake_case>` and are stable within a major.
- Activity never masks capability/severity.
- `source_revisions` exposes no filesystem path, credential, SQL, or raw canonical document. Revisions are hashes, schema versions, or durable owner revisions already computed by the canonical reader.
- Do not invent or rescan a source solely to populate a revision. Use an empty object until the authority exposes a cheap revision.
- Version 3 deletes `ttl_seconds`. Client freshness uses response receipt time and mutation invalidation under #144/#148.
- Version 3 deletes executable command strings. `action.primary` contains only the #145 action descriptor/reference.
- OCR per-paper pipeline rows and other unbounded rows are not envelope fields.

No generic `facts` bag is added. Every field a client needs must either be a stable envelope field or belong to a module-specific detail contract; this prevents an unversioned second schema inside the envelope.

## 6. `probe all` v1

```json
{
  "schema_family": "paperforge.probe_all",
  "schema_version": 1,
  "observed_at": "2026-08-09T11:30:00Z",
  "modules": [
    { "schema_family": "paperforge.capability", "schema_version": 3, "module": "installation" },
    { "schema_family": "paperforge.capability", "schema_version": 3, "module": "library" },
    { "schema_family": "paperforge.capability", "schema_version": 3, "module": "ocr" },
    { "schema_family": "paperforge.capability", "schema_version": 3, "module": "memory" },
    { "schema_family": "paperforge.capability", "schema_version": 3, "module": "help" }
  ],
  "maintenance": {
    "schema_family": "paperforge.capability",
    "schema_version": 3,
    "module": "maintenance"
  }
}
```

The abbreviated members above stand for complete v3 envelopes. Their bytes and fields are the same as individual `probe <module> --json` results produced from the same context.

There is no aggregate readiness boolean or second top-level verdict. Consumers render the module envelopes; Maintenance is the accepted derived projection. Adding a global verdict would recreate the all-or-nothing product state rejected by #65/#147.

`modules` is an array in fixed order, not an object whose ordering a consumer might reinterpret.

## 7. Failures and exit behavior

### Expected domain conditions

Missing config, stale indexes, missing optional dependencies, provider unavailability, corrupt module data, and incomplete OCR are semantic results. Their capability reader returns a normal envelope with the correct reason/action. They are not command errors.

### Unexpected per-module detection failure

The dispatcher converts an unexpected exception to a valid envelope:

```json
{
  "schema_family": "paperforge.capability",
  "schema_version": 3,
  "module": "ocr",
  "capability_state": "unknown",
  "severity": "unknown",
  "reason": {"code": "ocr.probe_failed", "text": "OCR state could not be determined"},
  "action": {"primary": {"action_id": "ocr.probe"}},
  "user_state": "detection_failed",
  "maintenance_eligible": false
}
```

The real envelope includes every required field. Exception class and safe diagnostic correlation may go to stderr; secrets, raw paths, and exception payloads do not enter the envelope.

A detection failure in one module does not suppress any sibling envelope and does not turn `probe all` into a transport failure.

### Command failure

Unknown module, unsupported schema major, unresolvable vault argument, or serialization failure is a command/transport error. JSON mode emits the existing command-error family on stdout where already contracted, diagnostic detail on stderr, and a nonzero exit.

A successfully produced single envelope or complete `probe all` document exits 0 regardless of readiness. Non-ready product state is data, not process failure. Release/CI gates inspect the envelopes rather than overloading the process exit code.

## 8. Summary versus detail

Probe answers only: "Can this capability serve the user now, why, and what is the primary next action?"

Detail commands answer rows, counts beyond the summary, provenance, diagnostics, or implementation-specific state.

Keep and reuse existing detail surfaces before adding commands:

- OCR rows and maintenance: existing OCR status/list/maintenance commands;
- Vector build state: existing `embed status --json`;
- Memory counts/schema: existing memory status/query surfaces;
- Library papers: existing paper/library commands;
- Deep provider/runtime checks: existing doctor/runtime-health commands.

One proven missing surface is the per-paper OCR pipeline-version list currently embedded in `probe_ocr`. Move it to an OCR detail command during the v3 cutover. Do not create generic `query`, `detail`, or per-capability `refresh/diagnose` methods.

Detail payloads are independently versioned and may fail as command errors. They are not cached by default and are never required to render the control-center summary.

## 9. CLI adapter

The stable commands are:

```text
paperforge probe installation --json
paperforge probe library --json
paperforge probe ocr --json
paperforge probe memory --json
paperforge probe maintenance --json
paperforge probe help --json
paperforge probe all --json
```

`commands/probe.py` may contain only:

- argument-to-`ReadContext` construction;
- fixed module dispatch;
- JSON/text rendering;
- exit/error mapping.

It may not read canonical files, query SQLite, compute capability state, derive maintenance, construct actions, or apply freshness policy.

CLI, Obsidian, Agent, and tests consume the same command contract. In-process callers may call `probe`/`probe_all`; they do not call CLI parser functions.

## 10. Migration

Use vertical clean cutovers. Each slice has one authority and rolls back by reverting the slice.

1. **Pure maintenance projection** — extract `derive_maintenance`; make standalone maintenance and future `probe all` use it. Preserve current wire.
2. **Capability ownership** — move the five semantic decision trees from `commands/probe.py` into capability-owned Python modules. Keep current signatures/wire temporarily; the command becomes a thin adapter.
3. **Canonical config input** — after #142 lands, build one `ReadContext` per invocation; delete private config parsing and the Memory reader's Obsidian `data.json` feature gate. Move the vector-enabled setting to Python config.
4. **Add `probe all`** — aggregate the unchanged current envelopes once; migrate the plugin overview to one call. No schema break yet.
5. **Detail extraction and v3 cutover** — move OCR per-paper pipeline rows to its detail command; switch Python and every consumer together to v3; remove `ttl_seconds` and command strings. Unsupported v2/v3 mismatches fail closed; no runtime fallback.
6. **Action handoff** — replace the temporary action reference with the final #145 descriptor without changing capability semantics.
7. **Snapshot/client cutover** — #148 migrates remaining plugin consumers to these read models, then deletes runtime snapshot contracts and duplicate semantic readers.
8. **Enforcement** — #149 collectors prove adapter-only CLI/plugin boundaries and forbid canonical imports in clients.

Do not create a compatibility service, duplicate v2/v3 semantic owner, or three-release dual-read path. Temporary compatibility inside a slice has an explicit removal commit.

## 11. Acceptance criteria

- Python runs every individual probe and `probe all` in a vault with Obsidian absent.
- `probe all` calls each base capability exactly once in fixed order and derives Maintenance without re-probing.
- One reader exception yields one valid `detection_failed` envelope; all sibling envelopes still appear; command exits 0.
- Individual and aggregate envelopes from one context are contract-equal.
- No capability reader imports plugin code or reads `.obsidian`.
- `commands/probe.py` contains no canonical file/SQLite/domain-state interpretation.
- Config is loaded once per invocation through #142.
- Vector remains visible through Memory summary plus existing vector detail; no duplicate readiness owner exists.
- No unbounded row list appears in a capability envelope.
- v3 contains no `ttl_seconds` and no command string.
- Unknown same-major fields are ignored; unsupported majors disable actions and fail closed.
- Reason/action/state semantics from #69/#147 remain covered by the existing probe contract tests.
- Headless CLI, plugin, and Agent fixtures validate the same serialized examples.
- Architecture collectors reject canonical imports, duplicate semantic classifiers, and adapter-side envelope construction.

## 12. Alternatives rejected

### Service classes plus registrar/coordinator

Rejected. Six stateless reader classes, a registration protocol, metadata descriptors, and a coordinator add indirection without runtime substitution or dynamic loading. They invite pass-through services and an accidental god registry.

### Serializable query objects and one generic `execute(query)`

Rejected. Existing CLI commands already provide the Agent/subprocess contract. A second generic query language duplicates routing, adds one class per detail request, and weakens discoverable command boundaries.

### Data-driven rule interpreter

Rejected. Capability decision trees are different and already explicit. Encoding them as rule rows creates a private DSL and hides the control flow maintainers need to audit.

### Typed dataclass graph plus separate renderer

Rejected for the first cutover. Current consumers already need JSON-ready mappings; constructing value objects and then copying them into dictionaries adds code and allocations without changing the contract. Use `TypedDict`/type aliases and one validated builder. Reconsider runtime models only if type-checking evidence shows the mappings are unsafe.

### One aggregate control-plane service

Rejected. It would own module semantics, diagnostics, actions, and detail queries in one shallow module. The accepted seam keeps policy in capability modules and aggregation mechanical.
