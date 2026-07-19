# Phase 23: Canonical Asset Index & Safe Rebuilds - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-04
**Phase:** 23-canonical-asset-index-safe-rebuilds
**Areas discussed:** Index envelope, atomic writes, incremental refresh, workspace paths, module extraction, JSON content scope

---

## Index Envelope & Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Keep formal-library.json + envelope | Same filename, wrap list in versioned envelope. Old format auto-migrated. | ✓ |
| Rename to library-assets.json + envelope | Better semantics but migration needed. | |
| No envelope, per-entry version only | Minimal change, no overall metadata. | |

**User's choice:** Keep `formal-library.json`, add versioned envelope with `schema_version`, `generated_at`, `paper_count`, `items`.

---

## Atomic Write & File Lock

| Option | Description | Selected |
|--------|-------------|----------|
| tempfile + os.replace + filelock | Full protection: atomic write + cross-process lock. Windows safe. | ✓ |
| tempfile + os.replace only | Atomic write without concurrent write protection. | |

**User's choice:** Full protection (tempfile + os.replace + filelock).

---

## Incremental Refresh

| Option | Description | Selected |
|--------|-------------|----------|
| Full rebuild + incremental refresh | Both modes. Incremental by key after sync/ocr/repair. Full rebuild via flag or on schema mismatch. | ✓ |
| Full rebuild only | Always rewrite everything. Simple but grows slower with library size. | |

**User's choice:** Both modes supported.

---

## Paper Workspace Paths

| Option | Description | Selected |
|--------|-------------|----------|
| paper_root + main_note_path + full + deep + ai | Detailed workspace paths matching Phase 22 structure. | ✓ |
| paper_root only | Only root dir, other paths derived. | |

**User's choice:** Detailed paths: paper_root, main_note_path, fulltext_path, deep_reading_path, ai_path. System paths also retained.

**Additional insight from discussion:** "尝试把一些东西放进json，人不用看到的内容，然后只需要一个索引json就行" — Machine-only fields belong in the JSON. The index JSON is the single canonical inventory.

---

## Module Extraction

| Option | Description | Selected |
|--------|-------------|----------|
| Extract to asset_index.py | Independent module, cleaner. Also: machine fields stay in JSON, path fields mirrored in frontmatter for Base. | ✓ |
| Keep in sync.py | Less files changed but longer sync.py. | |

**User's choice:** Extract `paperforge/worker/asset_index.py`. Path fields double-written to frontmatter for Base compatibility.

---

## DEPENDENCIES TO ADD

- `filelock` for cross-process index locking

---

## the agent's Discretion

- Exact envelope field naming
- filelock timeout value
- --rebuild-index flag route (sync flag vs separate command)
- Incremental refresh granularity

## Deferred Ideas

None
