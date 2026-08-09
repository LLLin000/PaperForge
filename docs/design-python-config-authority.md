# Canonical Python Configuration Authority

- Date: 2026-08-09
- Decision ticket: [#142](https://github.com/LLLin000/PaperForge/issues/142)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Research: [#153](https://github.com/LLLin000/PaperForge/issues/153)
- Scope: architecture and migration contract; no production implementation

## 1. Decision

`paperforge.json` remains the one human-editable PaperForge configuration file. Python exclusively reads, validates, resolves, and writes it.

All consumers use a small functional module or its `paperforge config` CLI adapter:

```text
paperforge.json + process env + invocation overrides
                         |
                         v
                 paperforge.config
                  /      |       \
          resolved values paths  mutation
                  |      |       |
                  +------+------+ 
                         |
             CLI / Obsidian / Agent
```

Obsidian never parses or writes `paperforge.json`. Plugin `data.json` contains only presentation preferences and display-only caches. It contains no product paths, provider configuration, domain feature state, credentials, readiness facts, or bootstrap lifecycle authority in the completed #135 architecture.

The accepted shape combines:

- the functional seam from the minimal alternative;
- a small static `FieldSpec` table because current defaults/key lists already drift across Python and TypeScript;
- typed immutable read results;
- one locked atomic writer.

It rejects a mutable `ConfigDocument` object, JSON Schema, a generic rule language, generated form framework, file watcher, daemon, CAS protocol, revision preconditions, multi-version rollback, and config-framework dependency.

## 2. Canonical file shape

Keep JSON and schema version 2. Do not introduce TOML/YAML, a new sidecar, or a schema-v3 restructure.

```json
{
  "schema_version": 2,
  "vault_config": {
    "system_dir": "System",
    "resources_dir": "Resources",
    "literature_dir": "Literature",
    "control_dir": "LiteratureControl",
    "base_dir": "Bases",
    "skill_dir": ".opencode/skills",
    "command_dir": ".opencode/command"
  },
  "zotero_data_dir": "C:/Users/name/Zotero",
  "agent_platform": "opencode",
  "auto_analyze_after_ocr": false,
  "ocr_profile": "default",
  "paddleocr_job_url": "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
  "paddleocr_model": "PaddleOCR-VL-1.6",
  "embedding_profile": "default",
  "vector_db_provider_type": "openai_sdk",
  "vector_db_api_base": "",
  "vector_db_api_model": "text-embedding-3-small"
}
```

Rules:

- `schema_version` is an integer in canonical writes. Existing string `"2"` is accepted and normalized on the next successful mutation.
- Seven vault-relative directory values remain under `vault_config`; this preserves the current v2 format.
- Existing top-level non-secret product settings stay top-level; this avoids a gratuitous format rewrite.
- `ocr_profile` and `embedding_profile` select the non-secret profile IDs used by #138's credential authority.
- Credential values never appear in this file. `paddleocr_api_key`, `paddleocr_api_token`, `vector_db_api_key`, `openai_api_key`, `token`, `password`, and `secret` fields are forbidden.
- Derived paths such as `paperforge_path` and `zotero_link` are not configuration. Python returns them from path resolution.
- `version` is package/runtime metadata, not a user setting. It may be preserved while migrating old files but is not writable through `config set`.

## 3. Field vocabulary

Python owns one static table. It is data used by the loader, validator, CLI response, and plugin presentation adapter; it is not an extension registry.

```python
@dataclass(frozen=True)
class FieldSpec:
    key: str
    storage_path: tuple[str, ...]
    value_type: Literal["string", "boolean", "enum", "path"]
    default: str | bool
    env: str | None = None
    choices: tuple[str, ...] = ()
    writable: bool = True
    allow_empty: bool = False
    vault_relative: bool = False
```

Canonical user fields:

| Public key | Storage | Type/default | Environment override | Validation |
|---|---|---|---|---|
| `system_dir` | `vault_config.system_dir` | path / `System` | `PAPERFORGE_SYSTEM_DIR` | non-empty vault-relative |
| `resources_dir` | `vault_config.resources_dir` | path / `Resources` | `PAPERFORGE_RESOURCES_DIR` | non-empty vault-relative |
| `literature_dir` | `vault_config.literature_dir` | path / `Literature` | `PAPERFORGE_LITERATURE_DIR` | non-empty vault-relative |
| `control_dir` | `vault_config.control_dir` | path / `LiteratureControl` | `PAPERFORGE_CONTROL_DIR` | non-empty vault-relative |
| `base_dir` | `vault_config.base_dir` | path / `Bases` | `PAPERFORGE_BASE_DIR` | non-empty vault-relative |
| `skill_dir` | `vault_config.skill_dir` | path / `.opencode/skills` | `PAPERFORGE_SKILL_DIR` | non-empty vault-relative |
| `command_dir` | `vault_config.command_dir` | path / `.opencode/command` | `PAPERFORGE_COMMAND_DIR` | non-empty vault-relative |
| `zotero_data_dir` | top-level | path / empty | `ZOTERO_DATA_DIR` | absolute or vault-relative; empty allowed |
| `agent_platform` | top-level | enum / `opencode` | `PAPERFORGE_AGENT_PLATFORM` | supported deployment adapter |
| `auto_analyze_after_ocr` | top-level | boolean / `false` | none | boolean |
| `ocr_profile` | top-level | string / `default` | `PAPERFORGE_OCR_PROFILE` | credential profile grammar from #138 |
| `paddleocr_job_url` | top-level | string / current Paddle endpoint | `PADDLEOCR_JOB_URL` | HTTP(S), no embedded credentials |
| `paddleocr_model` | top-level | string / `PaddleOCR-VL-1.6` | `PADDLEOCR_MODEL` | non-empty |
| `embedding_profile` | top-level | string / `default` | `PAPERFORGE_EMBEDDING_PROFILE` | credential profile grammar from #138 |
| `vector_db_provider_type` | top-level | enum / `openai_sdk` | `VECTOR_DB_PROVIDER_TYPE` | `openai_sdk` or `requests` |
| `vector_db_api_base` | top-level | string / empty | `VECTOR_DB_API_BASE` | empty or HTTP(S), no embedded credentials |
| `vector_db_api_model` | top-level | string / `text-embedding-3-small` | `VECTOR_DB_API_MODEL` | non-empty |

`agent_platform` choices initially mirror the installed deployment adapters: `opencode`, `claude`, `codex`, `cursor`, `windsurf`, `github_copilot`, and `gemini`. Python owns this list; the plugin obtains it from `config list` rather than maintaining an independent enum.

New product fields require a Python release and one `FieldSpec`. Unknown keys remain preserved but cannot become hidden product semantics.

## 4. Python seam

```python
@dataclass(frozen=True)
class ConfigValue:
    key: str
    value: str | bool
    stored_value: str | bool | None
    source: Literal["default", "file", "environment", "override"]
    is_set: bool
    spec: FieldSpec

@dataclass(frozen=True)
class ConfigSnapshot:
    schema_version: int
    revision: str
    values: Mapping[str, ConfigValue]
    unknown_keys: tuple[str, ...]
    warnings: tuple[str, ...]

@dataclass(frozen=True)
class ConfigValidation:
    state: Literal["valid", "missing", "migration_required", "invalid", "future_schema"]
    revision: str | None
    errors: tuple[dict[str, object], ...]
    warnings: tuple[dict[str, object], ...]
    migration: dict[str, object] | None

@dataclass(frozen=True)
class MutationResult:
    changed: bool
    snapshot: ConfigSnapshot

class ConfigError(Exception):
    code: str
    details: Mapping[str, object]


def load_config(vault: Path, *, env: Mapping[str, str] | None = None,
                overrides: Mapping[str, object] | None = None) -> ConfigSnapshot:
    """Strictly load current schema and resolve defaults < file < env < overrides."""


def validate_config(vault: Path) -> ConfigValidation:
    """Classify missing/corrupt/legacy/future/current without interpreting invalid state."""


def set_config(vault: Path, key: str, value: object) -> MutationResult:
    """Validate and atomically set one canonical user field."""


def unset_config(vault: Path, key: str) -> MutationResult:
    """Atomically remove the stored field; effective value falls through to env/default."""


def resolve_paths(vault: Path, snapshot: ConfigSnapshot | None = None) -> Mapping[str, Path]:
    """Return the complete existing D-Path inventory from resolved configuration."""


def bootstrap_config(vault: Path) -> MutationResult:
    """Create canonical schema-2 config with explicit defaults when absent; idempotent."""


def migrate_config(vault: Path, *, dry_run: bool = False) -> MutationResult:
    """Explicitly normalize legacy structure through the same writer."""
```

Implementation notes:

- `ConfigSnapshot` does not expose the raw document. The store holds a private deep copy only long enough to preserve unknown fields on mutation.
- `revision` is SHA-256 over the exact file bytes read, or over the canonical serialized default document after bootstrap. It is a cache key and evidence stamp only; mutation has no `if_revision` precondition.
- Existing `load_vault_config`, `paperforge_paths`, and `paths_as_strings` may remain during the internal Python callsite migration as thin wrappers over this seam. They must not parse files or define separate defaults. Remove them after every in-repo caller migrates.
- Consolidate `paperforge/setup/config_writer.py`, `read_paperforge_json`, `get_paperforge_schema_version`, and `migrate_paperforge_json` into this seam. There is one writer and one validator.

## 5. Load and resolution semantics

Resolution order is fixed:

```text
built-in default < canonical paperforge.json < process environment < explicit invocation override
```

Per-field source is returned with the value.

- Environment values are parsed through the same field validator as file and CLI values.
- An invalid canonical value makes the document invalid; it does not silently fall back to a default.
- An invalid environment override produces `config.invalid_environment` naming the variable; it does not silently use the file value.
- Invocation overrides are in-process command inputs only. They are never persisted or exposed as generic CLI `--set` flags.
- `PAPERFORGE_VAULT` participates only in vault discovery, not the file-field table.
- Missing configuration is not treated as a valid product configuration. `validate_config` returns `missing`; `config init`, setup, and installation probes remain available. Domain commands return `config.not_found` plus the setup/init action instead of silently operating on guessed paths.
- Corrupt JSON, non-object roots, future schema, and structurally invalid known fields are never interpreted by domain commands.
- Read operations are lock-free. Atomic replacement guarantees a reader sees the previous or next complete file.

## 6. Validation rules

`validate_config` reports every detectable issue in one response.

- File must be UTF-8 JSON with an object root.
- `schema_version` missing or `1`, legacy top-level path keys, `agent_key`, or duplicate legacy/canonical fields produce `migration_required`, not implicit precedence.
- Schema version greater than 2 is `future_schema`; reads and writes fail closed until PaperForge is upgraded.
- Schema version less than 2 is read only by `migrate_config`.
- Vault-relative paths reject absolute paths, drive prefixes, NUL, and any `..` segment. They permit nested relative paths and platform separators after normalization.
- URLs allow only `http` or `https`, require a host, and reject username/password components.
- Profile IDs follow `[a-z][a-z0-9_]{0,63}`.
- Booleans in JSON must be booleans. CLI/environment parsing accepts only explicit `true|false|1|0`.
- Unknown keys are preserved and reported by name as warnings. Their values are not returned to clients.
- Unknown keys matching secret patterns are `config.secret_field` errors. Mutation is refused until #138 migration removes them.
- A `FieldSpec` may be read-only metadata; `config set/unset` refuses it.

Stable errors:

| Code | Meaning |
|---|---|
| `config.not_found` | canonical file absent |
| `config.corrupt` | unreadable/invalid JSON or non-object root |
| `config.migration_required` | legacy structure must be explicitly migrated |
| `config.future_schema` | file version newer than this PaperForge |
| `config.invalid` | one or more known file fields invalid |
| `config.invalid_environment` | environment value failed the field rule |
| `config.unknown_key` | client requested an undeclared field |
| `config.read_only_key` | client tried to mutate metadata |
| `config.secret_field` | secret-like field is present or mutation was attempted |
| `config.locked` | another PaperForge mutation held the lock beyond the bounded wait |
| `config.write_failed` | durable atomic replacement failed |

CLI uses normal `PFResult`: exit 0 success, 1 operation failure, 2 usage. Error codes, not bespoke numeric exits, drive clients.

## 7. Mutation transaction

Every Python writer calls one internal primitive:

```text
acquire filelock
  -> re-read exact current bytes
  -> strict validate / refuse corrupt or future schema
  -> apply one field mutation to the fresh document
  -> validate complete candidate
  -> serialize canonical known structure while preserving unknown values
  -> same-directory temp file
  -> flush + fsync temp
  -> copy current file mode when present
  -> os.replace(temp, paperforge.json)
  -> best-effort fsync parent directory on POSIX
  -> read-back + return revision/snapshot
release filelock
```

Use the already-installed `filelock` dependency on `paperforge.json.lock` with a bounded five-second wait. Do not add `msvcrt`/`fcntl` branches or stale-PID lock recovery. All PaperForge writers honor this lock; external editors do not, so the writer re-reads immediately after acquiring it and changes only the requested key.

Concurrency contract:

- Two PaperForge processes setting different keys both survive because the second re-reads after locking.
- Same-key concurrent writes are last completed write wins. No CAS protocol is added for a local single-user config.
- Unknown and untouched fields from the fresh read survive.
- Invalid/corrupt/future documents are never overwritten.
- Same-value set and absent unset are successful `changed: false` operations.
- Unset removes the stored value. The response reports the effective environment/default source that now wins.

Rollback means validate-before-write plus atomic replace. A failed temp write or replace leaves the prior file intact; read-back failure restores the in-memory prior bytes through the same atomic primitive. Normal set/unset writes do not create backups.

Schema migration supports `--dry-run`, validates the candidate before replacement, and automatically restores the original bytes if commit/read-back fails. Successful migrations are forward-only; PaperForge does not maintain `.bak` chains or an undo history. The existing stale `paperforge.json.bak` mechanism is retired.

## 8. Bootstrap

`paperforge config init` creates a complete explicit schema-2 file from current defaults. Explicit defaults avoid a future package upgrade silently moving an established vault.

- Parent vault must exist and be writable.
- Existing valid file: idempotent success, `created: false`.
- Existing legacy file: `config.migration_required`; init never overwrites it.
- Existing corrupt/future file: fail closed.
- Directory/artifact creation remains `paperforge setup`; `config init` only creates configuration.
- Setup calls `bootstrap_config`/`set_config` rather than owning another writer.

Before Python is available, the Obsidian plugin may show only bootstrap discovery UI. It must not guess PaperForge defaults or write a provisional config. #143 owns the bootstrap executable lifecycle.

## 9. Legacy migration

Migration is explicit; normal reads do not keep a legacy precedence layer.

`paperforge config migrate --dry-run --json` identifies:

- top-level path keys currently shadowing or filling `vault_config`;
- string schema version normalization;
- top-level `agent_key` alias;
- derived `paperforge_path` and `zotero_link` fields;
- domain fields copied from legacy plugin settings during the plugin-assisted pass;
- forbidden secret fields delegated to #138.

Rules:

1. Existing `vault_config` value wins over the legacy top-level path value; a mismatch is reported before mutation.
2. A missing canonical value is filled from the legacy source.
3. Migrated top-level path aliases are deleted.
4. `agent_key` fills `agent_platform` only when the latter is absent, then is deleted.
5. Derived path fields are removed after Python confirms the same resolved value.
6. Unknown non-secret fields are preserved.
7. Forbidden secret fields stop migration and return #138's credential-migration action; they are never copied.
8. Candidate validation and atomic replacement happen once.
9. Migration is idempotent.

No `top_level` or `file_legacy` source exists in the final `ConfigSnapshot`. The old fallback in `load_vault_config` is deleted in the same vertical slice that migrates all consumers.

## 10. CLI and wire contract

```text
paperforge config list --json
paperforge config get KEY --json
paperforge config set KEY VALUE --json
paperforge config unset KEY --json
paperforge config validate --json
paperforge config paths --json
paperforge config init --json
paperforge config migrate [--dry-run] --json
```

`paperforge paths --json` remains a convenience adapter over the same `resolve_paths` function because its D-Path contract is already public. It is not a second implementation.

`config list` is the sole settings-form read contract. It returns values and minimal constraints; it does not return raw JSON or unknown values.

```json
{
  "ok": true,
  "command": "config.list",
  "version": "1.0.0",
  "data": {
    "schema_version": 2,
    "revision": "sha256:...",
    "fields": [
      {
        "key": "system_dir",
        "value": "99_System",
        "stored_value": "99_System",
        "source": "file",
        "is_set": true,
        "type": "path",
        "default": "System",
        "environment": "PAPERFORGE_SYSTEM_DIR",
        "choices": [],
        "writable": true,
        "allow_empty": false,
        "vault_relative": true
      }
    ],
    "unknown_keys": ["repository"]
  },
  "error": null,
  "warnings": [],
  "next_actions": []
}
```

`config get` returns the same single field. `config set` parses `VALUE` by the field spec, mutates once, and returns `changed`, `revision`, and the new field. `config unset` returns the field after fallback. `config validate` returns the `ConfigValidation` shape even when state is not valid; command success means the inspection completed, not that the file is valid. `config paths` returns the exact current path inventory plus config revision.

The wire never returns:

- the complete raw file;
- unknown field values;
- secrets or secret status (owned by #138);
- plugin UI preferences;
- TypeScript-authored defaults or validation decisions.

## 11. Obsidian boundary

Delete the plugin's direct semantic config code:

- `main.ts.readPaperforgeJson`;
- `main.ts.savePaperforgeJson`;
- `memory-state.ts.readPathConfig` and TypeScript path precedence/defaults;
- mirrored path and provider fields in `PaperForgeSettings`;
- settings code that writes `paperforge.json` with `fs.writeFileSync`;
- Python readers of plugin `data.json` such as `embedding/_config.py`.

The plugin obtains values from `config list`, absolute paths from `config paths`, and mutation results from `config set/unset`. It may keep an in-memory/display-only last-known response under #144's freshness rules. A cached response can render stale/unknown state; it can never enable an action after validation fails.

The plugin's presentation registry may map Python field keys to localized labels, descriptions, sections, and Obsidian controls. It must not copy defaults, choices, types, requiredness, path rules, environment precedence, or validation. A parity test requires every Python-writable field to be either rendered or explicitly marked hidden by the plugin presentation registry.

Final `data.json` may contain only:

- language/theme/display preferences;
- active tab, collapsed panels, pagination, search input, navigation memory;
- release-note dismissal/version;
- setup journey presentation progress or dismissal, never setup readiness;
- display-only cached Python envelopes with revision/freshness metadata.

Final `data.json` may not contain:

- `system_dir`, `resources_dir`, `literature_dir`, `control_dir`, `base_dir`, `skill_dir`, `command_dir`, or `zotero_data_dir`;
- `agent_platform`;
- OCR/embedding profile, endpoint, model, or provider type;
- `features.memory_layer` or `features.vector_db` as product enablement. If retained, rename them to an explicit UI preference such as `show_vector_tools`;
- any API key or `_configured` authority flag;
- `python_path`, `vault_path`, `frozen_skills`, `_python_path_stale`, or managed-runtime lifecycle state after #143 cutover;
- `capabilityState` without #144's cache-only revision and freshness contract;
- `_setup_complete` as a readiness fact.

## 12. Plugin settings migration

The plugin-assisted migration is a one-time client of Python commands, not a second writer.

Domain values move to `paperforge.json` through `config set`:

- path mirrors and `zotero_data_dir`;
- `agent_platform`;
- `vector_db_api_base`, `vector_db_api_model`, and any existing provider type;
- any currently meaningful non-UI workflow flag.

Precedence for conflicts:

1. an already stored canonical Python value wins;
2. an old plugin value fills only an unset/default canonical field after explicit summary;
3. mismatches are shown to the user and require choosing which value to keep;
4. the plugin field is deleted only after `config get` verifies the chosen value;
5. the migration is rerunnable after interruption.

Credentials use #138's stdin/keyring migration and never pass through config. Bootstrap fields use #143. Snapshot/capability cache fields use #144. Migration bookkeeping is removed when all old fields are absent; it is not permanent product state.

## 13. Client behavior

### CLI

Calls module functions directly and serializes `PFResult`. Human mode may format tables/prompts; JSON semantics stay identical.

### Obsidian

Calls the versioned CLI through the thin client from #144. It renders Python values and errors, sends user edits as `config set/unset`, then invalidates its cached config/probe responses and re-reads.

### Agent integrations

Use `paperforge config list|get|paths --json`. Skills and scripts do not parse `paperforge.json`, even though they run in Python. Mutations use `config set/unset`; no agent constructs JSON patches.

### Python domain code

Imports `load_config` or `resolve_paths`; it never reopens `paperforge.json`. Raw extension consumers must be declared as fields or moved to another canonical store before #142 implementation closes.

## 14. Acceptance criteria

- Exactly one Python parser, validator, resolver, and writer exists for `paperforge.json`.
- Every Python domain caller uses the seam; no command, worker, skill, setup writer, or probe parses the file independently.
- No TypeScript source parses or writes `paperforge.json` or reconstructs canonical paths/defaults/precedence.
- `config list/get/set/unset/validate/paths/init/migrate --json` obey the documented PFResult contracts.
- Current `paperforge paths --json` output remains byte-shape compatible except for additive revision metadata only if its existing contract permits it.
- Resolution is defaults < canonical file < environment < invocation override with exact per-field source traces.
- Missing/corrupt/invalid/future configuration never silently yields guessed product paths.
- Top-level legacy path precedence is gone after explicit idempotent migration.
- Unknown non-secret fields survive every mutation value-identically; their values never cross the client wire.
- Secret-like fields are refused and routed to #138.
- Two concurrent different-key mutations preserve both values.
- Atomic-write failure leaves prior bytes intact and removes temporary files.
- Mutation refuses corrupt/future files and never turns them into defaults.
- Config migration dry-run changes no bytes; failed migration restores prior bytes; successful migration creates no stale backup chain.
- Setup and config commands share the same writer.
- Provider/profile settings formerly in plugin `data.json` resolve identically in headless CLI and Obsidian.
- Final plugin `data.json` passes an allowlist test containing UI preferences and display caches only.
- Plugin presentation parity tests detect new writable fields without copied validation rules.
- Architecture collectors flag direct `paperforge.json` parsing/writes, Python reads of plugin `data.json`, duplicate default/key tables, and secret-bearing config fields.

## 15. Rejected alternatives

### Mutable `ConfigDocument` service object

Rejected. Configuration is a short read/mutate transaction, not a long-lived aggregate. A mutable document encourages stale state and adds method/lifecycle surface without hiding more complexity than the functional seam.

### Plain dicts with seven path keys only

Rejected. PaperForge already has product settings in plugin `data.json` and ad hoc environment lookups. Leaving provider, profile, agent, Zotero, and workflow settings undeclared would preserve the authority split #142 exists to remove.

### Full JSON Schema and schema-generated forms

Rejected. Current validation is scalar/path/URL/enum/profile checks. A static `FieldSpec` table and Python validation are enough. Obsidian still owns localization and layout.

### Direct plugin fallback while Python is unavailable

Rejected. Before bootstrap, the plugin may guide installation only. Reimplementing defaults/file parsing for convenience recreates a second authority.

### Auto-migration during ordinary reads

Rejected. Read commands must not mutate a human-edited file. Migration is explicit, previewable, validated, and reported.

### Client revision/CAS preconditions

Rejected. One local writer lock plus per-key re-read/merge prevents different-key loss. Same-key last-write-wins is acceptable; a CAS protocol would complicate every client for no demonstrated multi-user requirement.

### Permanent backup or config history

Rejected. Atomic replace and failed-write restoration protect integrity. User history belongs to normal vault backup/version control, not another PaperForge state machine.
