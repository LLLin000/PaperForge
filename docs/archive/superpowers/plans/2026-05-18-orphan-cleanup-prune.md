# Orphan Paper Cleanup (Prune) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `paperforge sync --prune` and `paperforge prune` commands to delete orphaned workspace/OCR/vector artifacts for papers removed from Zotero.

**Architecture:** New standalone `worker/prune.py` module — testable without SyncService. Consumed by both `SyncService.run()` (for `sync --prune`) and a standalone `commands/prune.py` (for `paperforge prune`). Three-tier safety: dry-run default, `--force` to execute, explicit key-match filtering.

**Tech Stack:** Python 3.11+, `shutil.rmtree`, ChromaDB `collection.delete(ids=...)` (single-key, safe). No new dependencies.

---

## Files Changed

| Type | Path | Responsibility |
|---|---|---|
| Create | `paperforge/worker/prune.py` | Core prune logic: collect orphan keys, delete workspace/OCR/vectors |
| Modify | `paperforge/services/sync_service.py` | Add `prune(vault, paths, fresh_index, dry_run)` method; hook into `run()` after index rebuild |
| Modify | `paperforge/commands/sync.py` | Add `--prune` / `--force` CLI args; pass to SyncService |
| Modify | `paperforge/cli.py` | Add `prune` subcommand parser |
| Create | `paperforge/commands/prune.py` | Standalone `paperforge prune [--force]` CLI module |
| Modify | `paperforge/commands/__init__.py` | Register `prune` in command registry |
| Create | `tests/unit/worker/test_prune.py` | Unit tests for core prune logic |

### Unchanged

| File | Why unchanged |
|---|---|
| `paperforge/embedding/_chroma.py` | `delete_paper_vectors()` already exists and is safe |
| `paperforge/commands/embed.py` | Not involved — prune calls `delete_paper_vectors` directly |
| `paperforge/worker/asset_index.py` | Not involved — prune reads fresh index after build |
| `paperforge/memory/builder.py` | Not involved — memory DB is rebuilt from fresh index before prune runs |

---

## Task Breakdown

### Task 1: Core prune module (`worker/prune.py`)

**Files:**
- Create: `paperforge/worker/prune.py`
- Test: `tests/unit/worker/test_prune.py`

Logic:

```
def prune_orphan_papers(vault: Path, *, fresh_index: dict, dry_run: bool = True) -> dict:
    1. Build key_set from fresh_index["items"][*]["zotero_key"]
    2. Scan literature/ subdirectories for {key} - {slug}/ pattern
    3. For each key on filesystem but not in key_set:
       a. collect: ocr_dir, workspace_dir
       b. if dry_run: accumulate in preview list
       c. if not dry_run: rmtree each, then delete_paper_vectors(key)
    4. Return {"deleted": [...], "counts": {...}}
```

- [ ] **Step 1: Write failing tests**

```python
"""Tests for worker/prune.py — orphan detection and cleanup."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.worker.prune import (
    _collect_orphan_candidates,
    prune_orphan_papers,
)


class TestCollectOrphanCandidates:
    """_collect_orphan_candidates(lit_dir, fresh_keys) -> list[dict]"""

    def test_returns_no_orphans_when_all_match(self, tmp_path: Path) -> None:
        """All workspace dirs have keys in the fresh index."""
        lit = tmp_path / "Literature" / "CS"
        (lit / "key1 - Paper One").mkdir(parents=True)
        (lit / "key2 - Paper Two").mkdir(parents=True)
        fresh_keys = {"key1", "key2"}
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert result == []

    def test_returns_orphan_for_missing_key(self, tmp_path: Path) -> None:
        """Workspace with key not in fresh index is orphan."""
        lit = tmp_path / "Literature" / "CS"
        ws = lit / "key1 - Orphan Paper"
        ws.mkdir(parents=True)
        fresh_keys = set()
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert len(result) == 1
        assert result[0]["key"] == "key1"
        assert result[0]["workspace_dir"] == ws

    def test_skips_non_workspace_dirs(self, tmp_path: Path) -> None:
        """Directories not matching {key} - {slug} pattern are skipped."""
        lit = tmp_path / "Literature" / "CS"
        (lit / "orphan_file.md").write_text("not a dir")
        (lit / "random_dir").mkdir()
        fresh_keys = set()
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert result == []

    def test_skips_dirs_without_dash_space_pattern(self, tmp_path: Path) -> None:
        """Directory name must contain ' - ' to be a workspace."""
        lit = tmp_path / "Literature" / "CS"
        (lit / "justakey").mkdir()
        (lit / "key-with-dashes-no-slug").mkdir()
        fresh_keys = set()
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert result == []

    def test_handles_multiple_domains(self, tmp_path: Path) -> None:
        """Scans all domain subdirectories under literature root."""
        lit = tmp_path / "Literature"
        (lit / "CS" / "key1 - Paper One").mkdir(parents=True)
        (lit / "Med" / "key2 - Paper Two").mkdir(parents=True)
        (lit / "Sport" / "key3 - Paper Three").mkdir(parents=True)
        fresh_keys = {"key1"}
        result = _collect_orphan_candidates(lit, fresh_keys)
        assert len(result) == 2
        returned_keys = {c["key"] for c in result}
        assert returned_keys == {"key2", "key3"}


class TestPruneOrphanPapers:
    """prune_orphan_pairs(vault, fresh_index, dry_run)"""

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        """With dry_run=True, nothing is actually deleted."""
        lit = tmp_path / "Literature" / "CS"
        ws = lit / "key1 - Orphan"
        ws.mkdir(parents=True)
        note = ws / "note.md"
        note.write_text("hello")
        fresh_index = {"schema_version": "3", "items": []}

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=True)

        assert len(result["preview"]) == 1
        assert note.exists()  # not deleted

    def test_force_deletes_workspace(self, tmp_path: Path) -> None:
        """With dry_run=False, workspace dir is deleted."""
        lit = tmp_path / "Literature" / "CS"
        ws = lit / "key1 - Orphan"
        ws.mkdir(parents=True)
        (ws / "note.md").write_text("hello")
        (ws / "ai" / "discussion.md").write_text("some discussion")
        fresh_index = {"schema_version": "3", "items": []}

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=False)

        assert result["deleted"] == ["key1"]
        assert not ws.exists()

    def test_force_deletes_ocr_dir(self, tmp_path: Path) -> None:
        """With dry_run=False, OCR dir is deleted."""
        ocr = tmp_path / "System" / "PaperForge" / "ocr" / "key1"
        ocr.mkdir(parents=True)
        (ocr / "fulltext.md").write_text("fulltext")
        lit = tmp_path / "Literature" / "CS"
        (lit / "key1 - Orphan").mkdir(parents=True)
        fresh_index = {"schema_version": "3", "items": []}

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=False)

        assert result["deleted"] == ["key1"]
        assert not ocr.exists()

    def test_vectors_not_deleted_in_dry_run(self, tmp_path: Path, monkeypatch) -> None:
        """Dry run must not call delete_paper_vectors."""
        calls = []

        def _mock_delete(vault, key):
            calls.append(key)
            return 0

        monkeypatch.setattr("paperforge.worker.prune.delete_paper_vectors", _mock_delete)

        lit = tmp_path / "Literature" / "CS"
        (lit / "key1 - Orphan").mkdir(parents=True)
        fresh_index = {"schema_version": "3", "items": []}

        prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=True)
        assert calls == []

    def test_orphan_not_in_fresh_index_is_skipped(self, tmp_path: Path) -> None:
        """A key present in fresh_index must NOT be deleted."""
        lit = tmp_path / "Literature" / "CS"
        ws = lit / "key1 - Active Paper"
        ws.mkdir(parents=True)
        fresh_index = {
            "schema_version": "3",
            "items": [{"zotero_key": "key1", "title": "Active Paper"}],
        }

        result = prune_orphan_papers(tmp_path, fresh_index=fresh_index, dry_run=False)
        assert result["deleted"] == []
        assert ws.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/worker/test_prune.py -v`
Expected: `ModuleNotFoundError` or `FAILED` for all tests (no `worker/prune.py` yet)

- [ ] **Step 3: Implement `worker/prune.py`**

```python
"""paperforge.worker.prune — orphan paper cleanup.

Orphan detection: scan filesystem workspace dirs, find keys
not present in the fresh canonical index, and delete their
workspace/OCR/vector artifacts.

Safety: dry_run=True by default; --force required to execute.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from paperforge.config import paperforge_paths

logger = logging.getLogger(__name__)


def _collect_orphan_candidates(
    lit_dir: Path, fresh_keys: set[str]
) -> list[dict]:
    """Scan literature dir for workspace dirs whose key is not in fresh_keys.

    Returns list of dicts: {key, domain, workspace_dir, ocr_dir}
    Only matches dirs named ``{key} - {slug}``.
    """
    if not lit_dir.exists():
        return []

    candidates: list[dict] = []
    for domain_dir in sorted(lit_dir.iterdir()):
        if not domain_dir.is_dir():
            continue
        for sub in sorted(domain_dir.iterdir()):
            if not sub.is_dir():
                continue
            parts = sub.name.split(" - ", 1)
            if len(parts) < 2:
                continue
            key = parts[0]
            if not key:
                continue
            if key in fresh_keys:
                continue
            candidates.append({
                "key": key,
                "domain": domain_dir.name,
                "workspace_dir": sub,
                "ocr_dir": None,  # resolved later
            })

    return candidates


def _resolve_ocr_dir(vault: Path, key: str) -> Path:
    """Resolve OCR directory for a given key."""
    cfg = paperforge_paths(vault)
    ocr_root = cfg.get("ocr", vault / "System" / "PaperForge" / "ocr")
    return ocr_root / key


def prune_orphan_papers(
    vault: Path,
    *,
    fresh_index: dict,
    dry_run: bool = True,
) -> dict:
    """Delete orphan paper artifacts for keys not in the fresh index.

    Args:
        vault: Vault root path.
        fresh_index: The just-rebuilt canonical index dict.
        dry_run: If True, only preview; if False, actually delete.

    Returns:
        dict with keys:
          - preview: list of {key, domain, paths} (always populated)
          - deleted: list of keys actually deleted (only non-dry-run)
          - counts: {workspace, ocr, vectors, failed}
    """
    cfg = paperforge_paths(vault)
    lit_dir = cfg.get("literature")
    if not lit_dir:
        return {"preview": [], "deleted": [], "counts": {}}

    fresh_keys = {
        item["zotero_key"]
        for item in fresh_index.get("items", [])
        if item.get("zotero_key")
    }

    candidates = _collect_orphan_candidates(lit_dir, fresh_keys)
    if not candidates:
        return {"preview": [], "deleted": [], "counts": {}}

    # Resolve OCR dirs for all candidates
    for c in candidates:
        c["ocr_dir"] = _resolve_ocr_dir(vault, c["key"])

    preview = [
        {
            "key": c["key"],
            "domain": c["domain"],
            "workspace": str(c["workspace_dir"]),
            "ocr_dir": str(c["ocr_dir"]) if c["ocr_dir"].exists() else None,
        }
        for c in candidates
    ]

    if dry_run:
        return {"preview": preview, "deleted": [], "counts": {}}

    deleted: list[str] = []
    counts = {"workspace": 0, "ocr": 0, "vectors": 0, "failed": 0}

    for c in candidates:
        key = c["key"]
        try:
            # 1. Delete OCR dir first (safest — easily re-OCR'd)
            ocr = c["ocr_dir"]
            if ocr and ocr.exists():
                shutil.rmtree(ocr, ignore_errors=True)
                counts["ocr"] += 1

            # 2. Delete workspace dir (irreversible — discussion history)
            ws = c["workspace_dir"]
            if ws.exists():
                shutil.rmtree(ws, ignore_errors=True)
                counts["workspace"] += 1

            # 3. Delete vectors — single-key, non-corrupting
            try:
                from paperforge.embedding._chroma import delete_paper_vectors
                n = delete_paper_vectors(vault, key)
                if n > 0:
                    counts["vectors"] += n
            except Exception as vec_err:
                logger.warning("prune: failed to delete vectors for %s: %s", key, vec_err)
                counts["failed"] += 1

            deleted.append(key)

        except Exception as exc:
            logger.error("prune: failed to clean up %s: %s", key, exc)
            counts["failed"] += 1

    return {"preview": preview, "deleted": deleted, "counts": counts}
```

- [ ] **Step 4: Run tests again**

Run: `pytest tests/unit/worker/test_prune.py -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/prune.py tests/unit/worker/test_prune.py
git commit -m "feat(prune): core orphan paper cleanup module"
```

---

### Task 2: Standalone `prune` CLI command

**Files:**
- Create: `paperforge/commands/prune.py`
- Modify: `paperforge/commands/__init__.py`
- Modify: `paperforge/cli.py`

- [ ] **Step 1: Create `commands/prune.py`**

```python
"""Prune command — standalone orphan paper cleanup."""
from __future__ import annotations

import argparse
import json
import logging

from paperforge import __version__
from paperforge.core.result import PFResult
from paperforge.worker.asset_index import read_index

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    dry_run = not getattr(args, "force", False)
    json_output = getattr(args, "json", False)

    # Read the current canonical index
    try:
        fresh_index = read_index(vault)
    except Exception as e:
        logger.error("prune: failed to read canonical index: %s", e)
        if json_output:
            result = PFResult(
                ok=False, command="prune", version=__version__,
                data={"error": f"cannot read index: {e}"},
            )
            print(result.to_json())
        else:
            print(f"[FAIL] Cannot read canonical index: {e}")
        return 1

    from paperforge.worker.prune import prune_orphan_papers

    result_data = prune_orphan_papers(vault, fresh_index=fresh_index, dry_run=dry_run)

    if json_output:
        result = PFResult(
            ok=True, command="prune", version=__version__, data=result_data,
        )
        print(result.to_json())
        return 0

    # Human-readable output
    preview = result_data.get("preview", [])
    if not preview:
        print("[OK] No orphan papers found.")
        return 0

    print(f"[PRUNE] Found {len(preview)} orphan paper(s):")
    for p in preview:
        extras = []
        if p.get("ocr_dir"):
            extras.append("OCR")
        print(f"  {p['key']} ({p['domain']}) — workspace + {' + '.join(extras)}")

    if dry_run:
        print(f"\n--- Dry run (pass --force to actually delete) ---")
    else:
        counts = result_data.get("counts", {})
        print(f"\n[PRUNE] Deleted {len(result_data.get('deleted', []))} paper(s)")
        print(f"  workspaces: {counts.get('workspace', 0)}")
        print(f"  OCR dirs:   {counts.get('ocr', 0)}")
        print(f"  vectors:    {counts.get('vectors', 0)}")
        if counts.get("failed", 0):
            print(f"  failed:     {counts['failed']}")

    return 0
```

- [ ] **Step 2: Register in command registry**

Edit `paperforge/commands/__init__.py`: add `"prune": "paperforge.commands.prune"` to `_COMMAND_REGISTRY`.

- [ ] **Step 3: Add CLI parser**

Edit `paperforge/cli.py`:

```python
# In build_parser(), after embed parser:
p_prune = subparsers.add_parser("prune", help="Delete orphan paper artifacts")
p_prune.add_argument("--force", action="store_true", help="Actually delete (default: dry-run)")
_shared_args(p_prune)

# In main(), after embed dispatch:
if args.command == "prune":
    from paperforge.commands.prune import run
    return run(args)
```

- [ ] **Step 4: Test the standalone command**

Run: `python -m paperforge prune --vault <test-vault-path>` (or use a fixture)
Expected: Shows "No orphan papers found." or dry-run list.

- [ ] **Step 5: Commit**

```bash
git add paperforge/commands/prune.py paperforge/commands/__init__.py paperforge/cli.py
git commit -m "feat(prune): standalone CLI command"
```

---

### Task 3: `sync --prune` integration

**Files:**
- Modify: `paperforge/services/sync_service.py`
- Modify: `paperforge/commands/sync.py`

- [ ] **Step 1: Add `prune()` method to SyncService**

```python
# In sync_service.py, add method:
def prune(self, paths: dict, fresh_index: dict | None = None, *, dry_run: bool = True) -> dict:
    """Run orphan paper cleanup. Default dry_run=True."""
    if fresh_index is None:
        from paperforge.worker.asset_index import read_index
        fresh_index = read_index(self.vault)
    from paperforge.worker.prune import prune_orphan_papers
    return prune_orphan_papers(self.vault, fresh_index=fresh_index, dry_run=dry_run)
```

- [ ] **Step 2: Hook into `run()` method**

In `SyncService.run()`, after Phase 3 (index + memory rebuild), add:

```python
# In run() method, after line 298 (memory rebuild):
prune_result = None
if getattr(args, 'prune', False) or getattr(args, 'prune_force', False):
    dry_run = not getattr(args, 'prune_force', False)
    prune_result = self.prune(paths, fresh_index=None, dry_run=dry_run)
```

Update the method signature to accept `prune: bool = False, prune_force: bool = False`:
```python
def run(self, verbose=False, json_output=False, selection_only=False,
        index_only=False, prune=False, prune_force=False) -> PFResult:
```

Also add `prune` to the `_print_summary` section if present, or print after the index summary.

Update the `result.data` dict to include `prune` data.

- [ ] **Step 3: Update `commands/sync.py` to pass `--prune` args**

```python
# Add after lines 59-62:
svc = SyncService(vault)
prune_flag = getattr(args, "prune", False)
prune_force = getattr(args, "prune_force", False)
result = svc.run(
    verbose=verbose, json_output=json_output,
    selection_only=selection_only, index_only=index_only,
    prune=prune_flag, prune_force=prune_force,
)
```

- [ ] **Step 4: Add CLI args for sync prune**

Edit `paperforge/cli.py` sync parser:

```python
p_sync = subparsers.add_parser("sync", help="Sync Zotero selection + rebuild index")
p_sync.add_argument("--prune", action="store_true", help="Dry-run orphan cleanup")
p_sync.add_argument("--prune-force", action="store_true", help="Execute orphan cleanup")
# ... existing args
```

- [ ] **Step 5: Test sync integration**

Run: `python -m paperforge sync --prune --vault <test-vault-path>`
Expected: Sync runs normally, then prints orphan preview (or "no orphans").

- [ ] **Step 6: Commit**

```bash
git add paperforge/services/sync_service.py paperforge/commands/sync.py paperforge/cli.py
git commit -m "feat(prune): integrate prune into sync --prune"
```

---

### Task 4: Tests for SyncService prune integration

**Files:**
- Create: `tests/unit/services/test_sync_service_prune.py` (or add to existing `test_sync_service.py` if it exists)

- [ ] **Step 1: Write tests**

```python
"""Tests for SyncService.prune() integration."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch, MagicMock
from paperforge.services.sync_service import SyncService


class TestSyncServicePrune:

    def test_prune_calls_worker_module(self, tmp_path: Path) -> None:
        svc = SyncService(tmp_path)
        svc.paths = {"literature": tmp_path / "Literature"}
        fresh_index = {"schema_version": "3", "items": []}

        with patch("paperforge.services.sync_service.prune_orphan_papers") as mock_fn:
            mock_fn.return_value = {"preview": [], "deleted": [], "counts": {}}
            result = svc.prune(svc.paths, fresh_index=fresh_index, dry_run=True)

        mock_fn.assert_called_once()
        assert result["deleted"] == []

    def test_sync_run_passes_prune_true(self, tmp_path: Path) -> None:
        """SyncService.run() with prune=True must call self.prune()."""
        vault = tmp_path
        cfg = vault / "System" / "PaperForge"
        cfg.mkdir(parents=True)
        cfg_exports = cfg / "exports"
        cfg_exports.mkdir(parents=True)
        cfg_indexes = cfg / "indexes"
        cfg_indexes.mkdir(parents=True)

        # minimal paperforge.json
        (vault / "paperforge.json").write_text('{"system_dir": "System", "resources_dir": "Resources", "literature_dir": "Resources/Literature"}')

        svc = SyncService(vault)
        svc.paths = {
            "literature": vault / "Resources" / "Literature",
            "exports": cfg_exports,
            "index": cfg_indexes,
            "system_dir": vault / "System",
        }
        (svc.paths["literature"]).mkdir(parents=True, exist_ok=True)

        with patch.object(svc, "prune") as mock_prune:
            mock_prune.return_value = {"preview": [], "deleted": [], "counts": {}}
            # run() will call build_index etc, need broader patching
            with patch("paperforge.worker.asset_index.build_index") as mock_build:
                mock_build.return_value = 0
                with patch("paperforge.worker.asset_index.read_index") as mock_read:
                    mock_read.return_value = {"schema_version": "3", "items": []}
                    with patch.object(svc, "resolve_paths", return_value=svc.paths):
                        with patch("paperforge.services.sync_service.load_export_rows", return_value=[]):
                            with patch("paperforge.services.sync_service.load_domain_config"):
                                with patch("paperforge.services.sync_service.ensure_base_views"):
                                    with patch("paperforge.services.sync_service.load_vault_config"):
                                        with patch("paperforge.services.sync_service.migrate_to_workspace"):
                                            svc.run(prune=True, prune_force=True)

        mock_prune.assert_called_once()
```

(Note: the `run()` integration test is complex due to many dependencies — the plan implementer may need to adjust the patching surface. The core `prune()` method test on SyncService is the essential one.)

- [ ] **Step 2: Run tests**

Run: `pytest tests/unit/services/test_sync_service_prune.py -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add tests/unit/services/test_sync_service_prune.py
git commit -m "test(prune): add SyncService prune integration tests"
```

---

### Task 5: Full suite + lint

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: All existing + new tests pass.

- [ ] **Step 2: Run lint**

```bash
ruff check --fix paperforge/ && ruff format paperforge/
```
Expected: Clean.

- [ ] **Step 3: Run type check (optional)**

```bash
python -m mypy paperforge/worker/prune.py --ignore-missing-imports
```
Expected: No type errors.

- [ ] **Step 4: Version bump**

Update version in `paperforge/__init__.py`, `manifest.json`, `plugin/manifest.json` to `1.5.6rc4` or next appropriate version.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: bump version to 1.5.6rc4"
```

---

## Vector DB Safety (重中之重)

| Concern | Mitigation |
|---|---|
| `delete_paper_vectors()` crashes | Wrapped in try/except — logs warning, continues cleanup. Corrupt HNSW index already handled by `get_collection()` (catches on access, recreates collection silently). |
| Partial delete (vector gone, file still there) | Not possible: delete order is 1-OCR 2-workspace 3-vectors. If step 3 fails, steps 1-2 already done; key not in index, no future operation touches it. |
| Resume mode confused by pruned vectors | Resume reads index keys then checks ChromaDB — a key in index that still has vectors = skip. A key in index whose vectors were pruned (impossible: prune only deletes keys NOT in index). Perfectly orthogonal. |
| Concurrent sync + embed build | Not a realistic threat vector. If somehow both run: embed build writes to ChromaDB, prune reads from index (already static). No lock contention. |
| Dry-run safety | `--prune` without `--force` (or bare `paperforge prune`) never touches disk. Only reports. User must explicitly pass `--force` or `--prune-force`. |

## Rollback Strategy

If prune accidentally deletes artifacts for an active paper:
1. Resync: `paperforge sync` restores `formal-library.json` entry
2. Re-OCR: `paperforge ocr run` restores OCR directory
3. Re-embed: `paperforge embed build --resume` restores vectors
4. Discussion history: **lost** (workspace + ai/ deletion is irreversible). This is the one irreversible cost, and matches the user's stated intent ("不然容易留下很多垃圾").
