# Phase 22: Configuration Truth & Compatibility - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 22-configuration-truth-compatibility
**Areas discussed:** Paper workspace file composition, paperforge.json schema, legacy config migration, plugin config truth

---

## Paper Workspace File Composition

| Option | Description | Selected |
|--------|-------------|----------|
| `<Key> - <Short Title>.md` | ABCDEF - Paper Title.md. Unique, Quick Switcher-friendly. | ✓ |
| `<Short Title> - <Key>.md` | Paper Title - ABCDEF.md. Visually natural but harder to search by key. | |
| `fulltext.md` in workspace root | User-facing entry copy. System retains authoritative OCR copy. Index tracks both. | ✓ |
| `fulltext.md` via index only | Not in workspace. Accessed through canonical index link. | |
| Root + ai/ subdirectory | Main files in root, ai/ subdirectory for AI atoms. | ✓ |
| + reading/ subdirectory | Extra reading/ folder for canvas etc. Deeper hierarchy. | |

**User's choice:** `<Key> - <Short Title>.md` naming, `fulltext.md` in workspace, root + `ai/` layout.

---

## paperforge.json Schema

| Option | Description | Selected |
|--------|-------------|----------|
| vault_config canonical, legacy compat | New installs write vault_config. Old users auto-migrated. Compat read for top-level. | ✓ |
| All in vault_config, no compat | Rewrite on upgrade. No top-level compat after migration. | |
| Both indefinitely | Keep both supported. | |

**User's choice:** Consolidate to vault_config block with backward compatibility.

---

## Legacy Config Migration

| Option | Description | Selected |
|--------|-------------|----------|
| Auto during sync | paperforge sync detects and migrates. Backup as .bak. | ✓ |
| doctor warns + repair | doctor reports, user explicitly runs repair. | |
| Only during setup | Only new installs write new format. Legacy forever compatible. | |

**User's choice:** Auto-migration during `paperforge sync`.

---

## Plugin Config Truth

| Option | Description | Selected |
|--------|-------------|----------|
| Plugin reads paperforge.json | No independent DEFAULT_SETTINGS. Startup reads vault file. | ✓ |
| Plugin caches paperforge.json | Cache from vault file, writes back to vault file. | |
| Keep status quo, doctor detects | No change to plugin, just detection in doctor. | |

**User's choice:** Plugin reads `paperforge.json` directly.

---

## the agent's Discretion

- Exact schema_version format
- Backup filename convention
- Plugin UI layout for editing paperforge.json

## Deferred Ideas

None — discussion stayed within phase scope
