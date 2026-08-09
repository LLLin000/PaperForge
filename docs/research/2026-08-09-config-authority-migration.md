# Canonical Configuration Authority and Migration Research

- Date: 2026-08-09
- Wayfinder ticket: [#153](https://github.com/LLLin000/PaperForge/issues/153)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Scope: Primary-source configuration research plus current PaperForge gap mapping; no production implementation.

Scope: **one Python authority over `paperforge.json`** (human-editable JSON, CLI + Obsidian plugin + Agent consumers; no daemon/HTTP API). Research grounded in CPython os/tempfile docs, pip, npm/@npmcli/config, uv, VS Code, filelock, watchdog, dynaconf, jsonschema, atomicwrites, and PaperForge's own source. Every material fact has a direct URL in `sources`.

**Boundary set by the parent:** Python exclusively reads/validates/writes `paperforge.json`; the plugin must not parse it for semantic/config resolution. Credential authority is owned by issue #138 (confirmed: defines provider priority, keyring/env behavior, SecretStorage migration, redaction) — this report only mandates that secrets be **excluded from config**, and defers provider choice. Which plugin settings are genuinely UI-only (e.g. `python_path`, feature flags) is left to the local audit; nothing is assumed here.

---

## Adopt (smallest robust contract for the config authority)

### A1. One authority, one file, one precedence chain
- Python owns read/validate/write of `paperforge.json`. Keep the existing 5-level precedence: overrides > `PAPERFORGE_*` env > nested `vault_config` > legacy top-level (read-only fallback + warning) > built-in defaults, with the existing per-key `source_trace` (`load_vault_config(..., trace_sources=True)`). This mirrors pip's global<user<site<env<CLI chain, npm's `find(key)` provenance, and uv's system<user<project merge with env>file and CLI>env.
- **Plugin constraint (new):** the Obsidian plugin must not parse `paperforge.json` for semantic/config resolution. Today `main.ts` calls `readPaperforgeJson()` and copies `system_dir`/`resources_dir`/`literature_dir`/`base_dir` into `this.settings` (Obsidian `data.json`) — a second, precedence-free source of truth. Replace with a single consumption path through the Python authority: `paperforge config list --json` / `paperforge paths --json` (no daemon needed — per-invocation CLI call).

### A2. One shared atomic, durable writer
- Promote the in-repo canonical pattern (`worker/asset_index.atomic_write_index`: same-directory `tempfile.NamedTemporaryFile(delete=False)` → `json.dump` → `flush()` → `os.fsync()` → `os.replace()`) into a single `write_paperforge_json(path, data)` and route `ConfigWriter.write`, `migrate_paperforge_json`, and `core.io.write_json_atomic` through it.
- Rationale (source-grounded): `os.replace` is atomic when it succeeds (POSIX requirement; fails cross-filesystem ⇒ temp must be same-directory); `os.fsync` is POSIX `fsync()`/Windows `_commit()` and requires `f.flush()` first; on Windows replace is best-effort (MoveFileEx can silently fall back to a non-atomic copy) — hence flush+fsync+replace + temp cleanup + a retry on transient `PermissionError` (AV/OneDrive) is the correct contract.
- Fix two real gaps: `migrate_paperforge_json` currently writes with plain `path.write_text` (non-atomic — crash mid-migration can truncate the file) and `core.io.write_json_atomic` skips fsync and temp cleanup.

### A3. Concurrency: lock + re-read; no CAS
- Wrap read-modify-write (`set`, `unset`, migration) in `filelock.FileLock` on `paperforge.json.lock` — already the in-repo pattern (`worker/asset_index.py` 10 s timeout, `worker/discussion.py`). `filelock` = Windows `LockFileEx` (kernel-enforced), Unix `fcntl.flock`, cooperative `SoftFileLock` fallback; stdlib alternatives are `msvcrt.locking`/`fcntl.flock`.
- Canonical tools (pip, npm, uv) do **not** implement version-field CAS for config files; they serialize writers or accept last-write-wins on human-edited files. Lock + re-read + last-write-wins, with the `.bak` covering the crash window, is the contract.

### A4. Unknown-field preservation (explicit policy)
- Already implemented (`ConfigWriter` and `migrate_paperforge_json` round-trip non-path top-level keys) — keep and make it explicit: **never delete unknown keys; validate only known keys; warn on wrong-typed known values.** Canonical precedent: @npmcli/config collects unknown keys with provenance (env/publishConfig warn, file/CLI unknowns error after subcommand validation — npm 12 hardening), and VS Code edits settings.json by JSON-path tree so every other key/comment/format survives.

### A5. Schema versioning: forward-only, idempotent, fail-closed on the future
- Keep `schema_version` + the existing forward-only v1→v2 migration (fills `vault_config` gaps from legacy keys, preserves non-path keys, single `.bak` backup first time, idempotent).
- Normalize `schema_version` to a real **integer** (today it is written as the string `"2"` in three places but read via `int()`; accept both on read for one release).
- Add the fail-closed rule: `schema_version > current` ⇒ **refuse writes** with a clear "config was written by a newer PaperForge" error (reads tolerated). No auto-downgrade, no multi-version rollback chain.

### A6. Validation + error contract (smallest form)
- Validate the ~10 known flat keys by hand on read (paths are non-empty `str`, `auto_analyze_after_ocr` is `bool`, `schema_version` is `int`). At this schema size **omit jsonschema/pydantic** (revisit only if the schema grows past ~20 keys or becomes nested).
- Error contract: corrupt/missing file → existing structured reason codes in `probe.py` (`installation.config_missing/corrupt`, `library.config_corrupt`, …) — keep. `config get` on unknown/missing key → non-zero exit + message. `set`/`unset` on corrupt JSON → **fail closed** ("run `paperforge setup`"), never silently merge from `{}` (current `ConfigWriter` behavior on `JSONDecodeError` is a data-loss hazard for human edits). `unset` of an absent key → success (idempotent, npm-delete semantics).

### A7. `paperforge config` CLI surface (the one real missing piece)
- Add `paperforge config get KEY | set KEY VALUE | unset KEY | list [--json]` on flat keys, modeled on `pip config get/set/unset/list/debug` and `npm config set/get/delete/list [--json]`. `get`/`list --json` return the **resolved** view with per-key source, reusing `trace_sources`.

### A8. No file watcher in Python
- CLI tools are canonical in re-reading config per invocation (pip, npm, uv: no watchers). PaperForge has no daemon by design. **Omit watchers and the `watchdog` dependency in Python.** If a future GUI freshness need is proven by the audit, use Obsidian's native vault file event — and note the atomic-replace caveat: the file's inode changes on every Python write, so any watcher must watch the *directory*, not the path (VS Code watches dirname + resource; watchdog misses rename-swapped files).

---

## Defer (owned elsewhere or gated on audit)

- **D1 — Credentials (issue #138).** This report only mandates: the config schema contains **no secret fields**; `paperforge config list --json` and `config get` must never emit secret env values (explicit allowlist of known non-secret keys); secrets are never written into `paperforge.json` and never read into logs or canonical config. Provider priority, OS keyring vs env vs SecretStorage, auth set/status/delete, profiles, migration, and redaction are #138's decision.
- **D2 — Plugin settings inventory (local audit).** Which plugin settings are genuinely UI-only (candidate: `python_path`, feature flags, `last_seen_version`, capability envelopes, `_*_configured` booleans) must be determined by the local audit before anything is kept in `data.json`. The only hard rule adopted now: **no plugin setting may mirror a Python config key or re-implement precedence.**
- **D3 — GUI freshness mechanism.** Only if the audit proves the plugin needs live config updates; adopt Obsidian's native vault event then, never a Python watcher.
- **D4 — jsonschema/pydantic.** Escalation path only: adopt jsonschema (Draft 2020-12 `validate`) if the schema grows past ~20 keys or becomes nested; pydantic-settings only if typed config objects become necessary. Note jsonschema `format` checks are off by default (extra required).

---

## Reject (explicit complexity to omit)

- **R1 — CAS/version-field concurrency** and multi-writer merge: no canonical JSON-config CLI does this; lock + last-write-wins suffices for a human-edited file.
- **R2 — Config frameworks (dynaconf)** as the engine: mature (layered envs, `.secrets.*`, validation) but a heavy dependency and its own priority model for a ~10-key flat schema. (Its separate-secrets-file idea is already satisfied by env + #138's provider.)
- **R3 — Format change to TOML/INI** (uv/pip precedent): PaperForge's consumers already read JSON; format churn with zero benefit.
- **R4 — VS Code-style resident config service** (watchers, debounced change events, `onDidChangeConfiguration`): requires a process; PaperForge has no daemon. Borrow the *concepts* (single registry, resolved view, JSON-tree editing), not the machinery.
- **R5 — Multi-file layering** (global/user/site config files, pip-style `[command]` sections): PaperForge already collapses legacy top-level fallback into one `vault_config` block — keep collapsing, don't expand.
- **R6 — Multi-version rollback chain / migration history file:** canonical practice is one pre-migration snapshot (`paperforge.json.bak`, already shipped) + idempotent forward migration; VS Code leans on user git. Single `.bak` only.
- **R7 — Secrets in `paperforge.json` / encrypted-at-rest config:** secrets stay out of the config file by construction.
- **R8 — Plugin-side schema or precedence re-implementation:** the plugin reads resolved values from the Python authority; it never recomputes merges.

---

## Minimal PaperForge contract (delta from today)
1. `paperforge config get|set|unset|list [--json]`; `set`/`unset` = lock → read → validate-known → merge → shared atomic writer; `get`/`list --json` = resolved view with source trace.
2. Shared `write_paperforge_json()` (mkstemp same-dir → flush → fsync → os.replace + cleanup + one retry on Windows `PermissionError`); migrate + ConfigWriter + core.io all route through it.
3. `schema_version` integer; future-version ⇒ writes fail closed; migration stays forward-only/idempotent/`.bak`-once.
4. Hand-rolled known-key/type validation on read; corrupt ⇒ existing probe reason codes; `config set` refuses on corrupt JSON.
5. Plugin: remove `readPaperforgeJson()` semantic copy; no path keys in plugin settings; consume Python authority output. UI-only inventory per audit.
6. Secrets: schema has no secret fields; config surface allowlists output keys (never emits env secrets); provider per #138.
7. No Python watcher; no CAS; no config framework; no TOML; single `.bak`.

## Rejected alternatives & why (summary)
- dynaconf / pydantic / jsonschema now → dependency weight vs 10-key flat schema (D4 is the escalation path).
- TOML → consumer breakage, no benefit.
- Obsidian settings as single source → CLI/Agent consumers need file config independent of Obsidian.
- keyring-only secrets → headless/CI degeneracy documented; and provider authority belongs to #138.
- VS Code-style service/watchers → requires a resident process that does not exist.

## Primary-source bibliography (direct links)
- CPython `os`: https://docs.python.org/3/library/os.html · CPython `tempfile`: https://docs.python.org/3/library/tempfile.html
- pip Configuration: https://pip.pypa.io/en/stable/topics/configuration/ · pip config: https://pip.pypa.io/en/stable/cli/pip_config/
- npm config: https://docs.npmjs.com/cli/v10/using-npm/config · npm-config command: https://docs.npmjs.com/cli/v10/commands/npm-config · @npmcli/config source: https://github.com/npm/cli/blob/latest/workspaces/config/lib/index.js
- uv Configuration files: https://docs.astral.sh/uv/concepts/configuration-files/ · uv 0.8.0 changelog (disallowed uv.toml fields now error): https://github.com/astral-sh/uv/blob/main/changelogs/0.8.x.md
- VS Code configuration.ts: https://github.com/microsoft/vscode/blob/main/src/vs/workbench/services/configuration/browser/configuration.ts · configurationModels.ts: https://github.com/microsoft/vscode/blob/main/src/vs/platform/configuration/common/configurationModels.ts · jsonEditing.ts: https://github.com/microsoft/vscode/blob/main/src/vs/workbench/services/configuration/common/jsonEditing.ts
- atomicwrites: https://pypi.org/project/atomicwrites/ · filelock: https://py-filelock.readthedocs.io/en/latest/index.html · keyring: https://github.com/jaraco/keyring · watchdog: https://github.com/gorakhargosh/watchdog · dynaconf secrets: https://www.dynaconf.com/secrets/ · jsonschema: https://python-jsonschema.readthedocs.io/en/stable/
- PaperForge (local checkout, main): `paperforge/config.py`, `paperforge/setup/config_writer.py`, `paperforge/core/io.py`, `paperforge/worker/asset_index.py`, `paperforge/worker/discussion.py`, `paperforge/cli.py`, `paperforge/commands/probe.py`, `paperforge/plugin/src/main.ts`, `paperforge/plugin/src/constants.ts`, `paperforge/plugin/src/services/secret-storage.ts`
- Credential scope boundary: https://github.com/LLLin000/PaperForge/issues/138

## Open risks & questions
1. **Windows transient replace failures** (AV/OneDrive): adopt one retry-with-backoff in the shared writer; confirm acceptable worst-case latency.
2. **`config set` fail-closed vs `setup` re-runs:** `ConfigWriter` currently tolerates corrupt JSON (merge from `{}`) so `setup` can repair half-written files; flip to refuse-with-error for `set` only, keep repair semantics in `setup` — confirm this split.
3. **`schema_version` string→int normalization:** accept both forms on read for one release; confirm the tolerance window.
4. **Plugin consumption path without a daemon:** per-invocation `paperforge config list --json` adds ~100 ms CLI startup per settings-panel render — verify acceptable for the settings UI; cache with manual refresh if not (do not add a watcher).
5. **Unknown-field warn vs error:** npm 12 hardened file/CLI unknowns to error; for a human-edited file, warn-not-error is recommended — make the choice explicit in the contract.
6. **Multi-vault:** `paperforge.json` is per-vault and the plugin is per-vault; confirm no cross-vault shared config is wanted (machine-level runtime config already lives separately under `~/.paperforge/runtime/` with its own atomic-pointer pattern — out of scope).

[INFERENCE markers: gaps (no `config` subcommand; non-atomic migration write; plugin path-key duplication; ConfigWriter corrupt-merge hazard) are inferred from direct comparison of PaperForge source with the cited canonical implementations; all other claims are directly sourced.]