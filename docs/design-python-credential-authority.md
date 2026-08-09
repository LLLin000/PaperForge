# Python Credential Authority and Secret Migration Contract

- Date: 2026-08-09
- Decision ticket: [#138](https://github.com/LLLin000/PaperForge/issues/138)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Research: [#141](https://github.com/LLLin000/PaperForge/issues/141)
- Scope: architecture and migration contract; no production implementation

## 1. Decision

Python owns all PaperForge credential resolution and durable storage.

- Durable authority: Python `keyring >= 25`, service name `paperforge`.
- Desktop backends: Windows Credential Manager, macOS Keychain, Linux Secret Service through `keyring`.
- Ephemeral noninteractive authority: explicitly supplied process environment variables.
- No custom OS backend, `keyrings.alt`, plaintext fallback, vault secret, config secret, plugin-owned runtime secret, daemon, or HTTP broker.
- Obsidian SecretStorage, `.env`, legacy environment names, Windows HKCU, and plaintext plugin settings are migration inputs only. Production resolution never consults them after cutover.

The public Python seam is a small functional module. No provider registry framework, URI references, opaque handles, backend selection per profile, sidecar binding file, or secret-returning CLI command is introduced.

## 2. Credential identity

A credential is identified by two non-secret fields:

```python
@dataclass(frozen=True)
class CredentialKey:
    kind: Literal["ocr", "embedding"]
    profile: str = "default"
```

Profile IDs use:

```text
[a-z][a-z0-9_]{0,63}
```

They are stable IDs declared by Python-owned configuration under #142. They describe which configured OCR or embedding profile needs a credential; they never identify an OS backend.

Keyring naming is deterministic:

```text
service  = paperforge
username = <kind>:<profile>
```

Examples:

```text
paperforge / ocr:default
paperforge / ocr:institution
paperforge / embedding:default
paperforge / embedding:local_openai
```

No keyring enumeration is required. `auth status` checks the explicit key requested or the profiles declared in the resolved vault configuration.

Existing Obsidian embedding secrets keyed by endpoint/model hash are mapped during migration to the selected Python config profile. The hash is migration metadata, not the new credential identity.

## 3. Resolution precedence

For a requested `CredentialKey`, Python resolves exactly:

1. the canonical explicit environment variable for that key;
2. the OS keyring entry;
3. missing.

Environment names are deterministic:

```text
PAPERFORGE_CREDENTIAL_<KIND>__<PROFILE>
```

Examples:

```text
PAPERFORGE_CREDENTIAL_OCR__DEFAULT
PAPERFORGE_CREDENTIAL_OCR__INSTITUTION
PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT
```

Because profile IDs permit only lowercase letters, digits, and underscore, uppercasing is reversible and collision-free.

Rules:

- Presence of a canonical environment variable is explicit CI/noninteractive opt-in and overrides keyring for that process.
- The plugin strips `PAPERFORGE_CREDENTIAL_`, `PADDLEOCR_`, `VECTOR_DB_`, `OPENAI_`, and `OCR_TOKEN` from its inherited environment. It never injects a credential after migration.
- If the canonical environment variable is absent, Python asks keyring.
- Legacy variables such as `PADDLEOCR_API_TOKEN`, `PADDLEOCR_API_KEY`, `VECTOR_DB_API_KEY`, `OPENAI_API_KEY`, and `OCR_TOKEN` are not runtime fallbacks. They are accepted only by explicit migration commands.
- `.env` files are never loaded for credential resolution after cutover.
- Python does not initialize keyring when a canonical environment credential already satisfies the request. This keeps CI independent of desktop keyring services.

`PAPERFORGE_KEYRING_BACKEND`, if explicitly set, is copied to `PYTHON_KEYRING_BACKEND` before importing `keyring`. It is a test/deployment control, not a credential value and not stored in vault config.

## 4. Python module contract

```python
SERVICE = "paperforge"

@dataclass(frozen=True)
class CredentialStatus:
    key: CredentialKey
    state: Literal[
        "available",
        "missing",
        "backend_unavailable",
        "backend_locked",
        "permission_denied",
        "backend_error",
    ]
    source: Literal["environment", "keyring"] | None
    backend: str | None
    remediation_code: str | None


def resolve(key: CredentialKey, *, env: Mapping[str, str] | None = None) -> str:
    """Return the secret from explicit environment or keyring; otherwise raise a typed credential error."""


def store(key: CredentialKey, secret: str, *, replace: bool = False) -> None:
    """Write to keyring, read back, and restore/delete on verification failure."""


def delete(key: CredentialKey) -> bool:
    """Delete the keyring entry. Return False when absent."""


def status(key: CredentialKey, *, env: Mapping[str, str] | None = None) -> CredentialStatus:
    """Report availability and source without returning, masking, hashing, or fingerprinting the value."""
```

Implementation rules:

- Functions are lazy: import and access `keyring` only when needed.
- Callers receive the secret only from `resolve`; no process-global secret cache exists.
- `status` may retrieve a value into local memory because `keyring` has no portable presence-only operation, but returns only state/source/backend.
- A value is never copied into an exception, structured result, log field, traceback annotation, progress event, config object, or client cache.
- `store` refuses to replace an existing different value unless `replace=True`.
- For replacement, retain the previous value in local memory, write, read-back verify, and restore the previous value if verification fails. For a new entry, delete a partially written value on failure.
- `delete` is idempotent at the Python API; the CLI still requires explicit confirmation.

The credential module wraps `keyring` exceptions into PaperForge errors with stable codes:

| Code | Meaning | User action |
|---|---|---|
| `credential.missing` | No canonical env value and no keyring entry | Set the profile or supply the canonical env variable |
| `credential.backend_unavailable` | No secure keyring backend, common in minimal/headless Linux | Start Secret Service for durable storage or use an explicit process env in CI |
| `credential.backend_locked` | Keychain/keyring is locked or unlock was declined | Unlock and retry |
| `credential.permission_denied` | OS session/interpreter cannot access the store | Use an interactive user session or supported signed Python |
| `credential.backend_error` | Other keyring operation failure | Retry; run status for backend/remediation detail |
| `credential.input_required` | Noninteractive set received no stdin | Pipe the secret on stdin |
| `credential.conflict` | A different durable value already exists | Retry only after explicit replace confirmation |
| `credential.invalid_profile` | Kind/profile does not satisfy the contract | Correct non-secret profile configuration |

Python commands return the normal `PFResult` JSON envelope. Stable error codes carry the distinction; process exit is 0 for success, 1 for an operation failure, and 2 for CLI usage. No new numeric exit-code taxonomy is added.

## 5. CLI contract

Use one command family:

```text
paperforge auth status [KIND] [--profile ID] [--vault PATH] --json
paperforge auth set KIND [--profile ID] [--stdin] [--replace] --json
paperforge auth delete KIND [--profile ID] --yes --json
paperforge auth migrate --from dotenv|environment|windows-registry [--vault PATH] [--dry-run] [--replace] --json
```

There is no `auth get`, `--raw`, export, backup, list-all-keyring-entries, or secret-bearing JSON command.

### `auth status`

- With `KIND`, checks one explicit key.
- Without `KIND`, loads the resolved vault config and checks only credential profiles used by that vault.
- Reports profile, state, source, backend class, and remediation code.
- Never returns masked values, lengths, hashes, fingerprints, legacy values, or environment contents.
- Environment-sourced success reports `source: environment`; keyring is not touched.

Example:

```json
{
  "ok": true,
  "command": "auth.status",
  "version": "1.0.0",
  "data": {
    "schema_version": 1,
    "credentials": [
      {
        "kind": "ocr",
        "profile": "default",
        "state": "available",
        "source": "keyring",
        "backend": "keyring.backends.Windows.WinVaultKeyring",
        "remediation_code": null
      },
      {
        "kind": "embedding",
        "profile": "default",
        "state": "missing",
        "source": null,
        "backend": "keyring.backends.Windows.WinVaultKeyring",
        "remediation_code": "credential.set_required"
      }
    ]
  },
  "error": null,
  "warnings": [],
  "next_actions": []
}
```

### `auth set`

- TTY input uses `getpass` and never echoes.
- Non-TTY requires `--stdin`; one secret is read until EOF, with one trailing newline removed.
- A secret is never accepted as an argv option.
- Empty input is rejected.
- Existing different value produces `credential.conflict` unless `--replace` is present.
- Success returns only kind/profile/state/source; no masked or fingerprinted value.

### `auth delete`

- Deletes only the keyring entry; it cannot delete or change an environment variable.
- Requires `--yes` in noninteractive mode. Interactive mode requires typing the exact `kind:profile`.
- If the canonical environment override remains present, success includes a warning that resolution is still environment-backed.
- Missing keyring entry is an idempotent success with `deleted: false`.

### `auth migrate`

Migration sources are explicit and never become runtime fallbacks.

- `dotenv`: known legacy credential keys in the vault and system `.env` files.
- `environment`: known legacy process environment names.
- `windows-registry`: known legacy HKCU values, only on Windows.

For every discovered source entry:

1. derive the target `CredentialKey` from resolved configuration or an explicit kind/profile;
2. compare with any existing keyring value in memory;
3. refuse a different value unless `--replace` is present;
4. store and read-back verify;
5. scrub the source only after verification when PaperForge can safely mutate it;
6. report source cleanup separately from keyring success.

`.env` cleanup uses the canonical same-directory atomic writer and removes only recognized secret assignments. It does not create a plaintext backup containing the secret. If write-back fails, the verified keyring value remains and the source remains; the command returns `cleanup_pending` and can be rerun safely.

Process environment and HKCU are never silently deleted. The command returns exact variable/value-name identifiers to remove manually after verified migration.

`--dry-run` returns discovered source names and target keys, never values.

## 6. Obsidian SecretStorage migration

SecretStorage is a temporary migration source, not a runtime provider after cutover.

The plugin owns this one user-mediated bridge because only Obsidian can access its SecretStorage:

1. The UI shows old source, target `kind:profile`, security note, and replace consequence.
2. The user explicitly confirms.
3. The plugin reads the old value into memory and spawns `paperforge auth set <kind> --profile <profile> --stdin --json`.
4. The plugin writes the value once to child stdin, closes stdin, and clears its local reference.
5. Python stores and read-back verifies it.
6. The plugin calls `auth status` and switches all future runtime resolution to Python.
7. The old SecretStorage value is deleted only through a supported Obsidian API. If no documented delete exists, the UI gives exact manual deletion steps and keeps a non-secret `legacy_copy_present` warning until the user clears it.

The value never appears in argv, environment, files, JSON, logs, notices, diagnostics, or issue drafts. Stdin is a migration transport, not a storage authority.

After successful cutover:

- `resolveCredentialEnv`, credential command allowlists, and per-command secret injection are deleted;
- SecretStorage reads are deleted except the expiring migration helper;
- plugin API-key fields become transient password inputs that call `auth set --stdin`; they never persist to `data.json` or SecretStorage;
- `_paddleocr_configured`, `_vector_db_configured`, and similar flags are display-only old cache during migration, then removed;
- presence/readiness comes from Python capability/auth read models.

## 7. Legacy source cutover

The clean cutover removes every old runtime resolution path in the same implementation family:

- OCR environment alias chain;
- OCR HKCU read;
- OCR `.env` read;
- embedding `VECTOR_DB_API_KEY`/`OPENAI_API_KEY` aliases;
- embedding plugin `data.json` plaintext read;
- embedding `.env` read;
- plugin SecretStorage injection;
- plugin and setup-wizard credential writes to `.env`;
- setup/dashboard/doctor presence checks that inspect env or plugin settings directly.

Legacy sources remain readable only by explicit migration code with an expiry/removal condition. They are not dual authorities and never serve production OCR or embedding after cutover.

Non-secret provider configuration remains in `paperforge.json`: API base URL, model, provider type, job URL, and profile ID. Credential values never enter #142's config contract.

## 8. Platform and headless behavior

### Windows

Interactive user sessions use Credential Manager. Network-logon/service contexts that cannot access a user vault return `credential.permission_denied`; no retry loop or fallback file appears.

### macOS

Keychain may reject unsigned or nonstandard Python interpreters. Return `credential.permission_denied` with the supported-Python remediation. Do not auto-change keychain ACLs or install a custom helper.

### Linux

Secret Service is the supported durable backend. Missing D-Bus/daemon or locked collections return unavailable/locked respectively. Minimal servers and containers use explicit canonical process environment variables; PaperForge does not install a keyring daemon.

### CI

CI supplies canonical environment variables. Because resolution checks them first, no keyring backend is required. Tests may inject an in-memory fake through the credential module seam; `keyrings.alt` and plaintext test backends never ship in production dependencies.

### Backup and restore

Vault backup does not include credentials. A new machine or user account requires re-entry or explicit environment input. PaperForge never exports, syncs, or reconstructs secret values.

## 9. Acceptance criteria

- With Obsidian absent, a key set by `paperforge auth set ... --stdin` supports complete OCR/embedding execution without prompts.
- Canonical environment credentials support the same headless paths without initializing keyring.
- Missing, locked, unavailable, denied, and backend-error states produce distinct stable error codes and remediation without hanging.
- Every Python credential consumer calls the one credential module; no caller reads legacy env names, `.env`, HKCU, plugin data, or SecretStorage.
- Plugin-spawned processes receive no secret in argv or environment after migration.
- `paperforge.json`, plugin `data.json`, snapshots, logs, stderr, NDJSON, diagnostics, and issue drafts contain no credential value, masked value, fingerprint, or hash.
- `auth set` verifies its write and restores/deletes on failure.
- `auth delete` cannot silently override an active environment credential.
- `.env` migration scrubs only after verification and leaves the source intact on failure; no plaintext backup is created.
- SecretStorage migration is explicit, uses stdin once, verifies before source deletion, and never creates a runtime fallback.
- All desktop OS backends have one real-store integration check; CI uses a fake plus canonical environment-path checks.
- The plugin and Python share golden tests for kind/profile/env-name derivation and redaction.
- Architecture collectors forbid legacy credential reads/writes and secret-bearing subprocess env construction.

## 10. Alternatives rejected

### Plugin SecretStorage plus environment injection

Rejected as the target. It keeps Obsidian as credential authority and makes headless Python incomplete. It exists only as the migration source.

### Config URI references such as `keyring://...` or `env://...`

Rejected. Storage selection is execution environment policy, not vault domain configuration. URI references add a permanent grammar and permit a synced config to demand an insecure/unavailable backend.

### Credential registry or descriptor framework

Rejected. PaperForge has two credential kinds and deterministic profile IDs. A class hierarchy, source protocol, dynamic registry, or entry-point discovery adds indirection and invites unsupported file/cloud providers.

### Opaque handles or machine-local binding file

Rejected. They create a second durable registry and a config-to-handle-to-provider lookup chain without a multi-user revocation requirement.

### Runtime legacy fallback window

Rejected. `.env`, HKCU, legacy env names, plugin settings, and SecretStorage are explicit migration inputs only. A fallback window would keep multiple live authorities and contradict the clean-cutover rule.

### Secret-returning CLI

Rejected. PaperForge has no product need to print or export a credential. Removing `get --raw`, fingerprints, and masked values eliminates a leak path and simplifies redaction tests.
