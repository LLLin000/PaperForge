"""Regression tests for .paperforge path authority, sync F821 cleanup, and durable R/P staging."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from paperforge.commands.dashboard import _dashboard_from_db
from paperforge.commands.ocr import _collect_batch_unsettled
from paperforge.config import bootstrap_config, paperforge_paths, set_config
from paperforge.figure_reconciliation import (
    reconcile_staging_search_bases,
    reconcile_staging_write_base,
)
from paperforge.memory.db import get_memory_db_path
from paperforge.memory.runtime_health import get_runtime_health
from paperforge.memory.schema import ensure_schema
from paperforge.query_planning import enrich_query_plan_with_runtime
from paperforge.services.sync_service import SyncService
from paperforge.setup_wizard import EnvChecker

pytestmark = pytest.mark.unit


def _init_dot_paperforge_vault(vault: Path) -> dict[str, Path]:
    vault.mkdir(parents=True, exist_ok=True)
    bootstrap_config(vault)
    set_config(vault, "system_dir", ".paperforge")
    paths = paperforge_paths(vault)
    for key in ("paperforge", "exports", "ocr", "resources", "literature", "bases"):
        paths[key].mkdir(parents=True, exist_ok=True)
    (paths["paperforge"] / "indexes").mkdir(parents=True, exist_ok=True)
    (paths["paperforge"] / "logs").mkdir(parents=True, exist_ok=True)
    (paths["index"]).write_text(json.dumps({"schema_version": "2", "items": []}), encoding="utf-8")
    return paths


def test_dot_paperforge_layout_honored_across_health_dashboard_ocr_and_query_plan(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    paths = _init_dot_paperforge_vault(vault)

    # Create Memory DB at .paperforge/indexes/paperforge.db
    db_path = get_memory_db_path(vault)
    conn = sqlite3.connect(str(db_path))
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO papers (zotero_key, title, domain, has_pdf, ocr_status) VALUES (?, ?, ?, ?, ?)",
        ("K1", "Sample Paper", "General", 1, "done"),
    )
    conn.commit()
    conn.close()

    # 1. runtime_health bootstrap & read layers must pass on .paperforge without System/PaperForge
    health = get_runtime_health(vault)
    assert health["layers"]["bootstrap"]["status"] == "ok", health["layers"]["bootstrap"]
    assert health["layers"]["read"]["status"] == "ok", health["layers"]["read"]

    # 2. _dashboard_from_db fast path must resolve .paperforge/indexes/paperforge.db
    stats = _dashboard_from_db(vault)
    assert stats is not None
    assert stats["stats"]["papers"] == 1
    assert stats["stats"]["ocr_health"]["done"] == 1

    # 3. _collect_batch_unsettled & enrich_query_plan_with_runtime must see .paperforge/ocr/
    ocr_paper = paths["ocr"] / "K1"
    (ocr_paper / "index").mkdir(parents=True, exist_ok=True)
    (ocr_paper / "index" / "role-index.json").write_text("{}", encoding="utf-8")
    (ocr_paper / "meta.json").write_text(
        json.dumps({"zotero_key": "K1", "provider_batch_id": "pf-batch-1", "ocr_status": "failed"}),
        encoding="utf-8",
    )
    assert _collect_batch_unsettled(vault, "pf-batch-1") == ["K1"]

    plan = enrich_query_plan_with_runtime({"intent": "locate", "identifier": {"value": "K1"}}, vault)
    assert plan["runtime"]["ocr_evidence_available"] is True

    # 4. SyncService.load_exports & EnvChecker.get_exports_dir must point to .paperforge/exports
    (paths["exports"] / "library.json").write_text(
        json.dumps([{"key": "K1", "title": "Sample Paper"}]),
        encoding="utf-8",
    )
    assert len(SyncService(vault).load_exports()) == 1
    checker = EnvChecker(vault)
    checker.system_dir = ".paperforge"
    assert checker.get_exports_dir() == paths["exports"]


def test_static_guard_no_raw_system_paperforge_shortcuts() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    package_root = repo_root / "paperforge"
    allowlist = {
        "paperforge/cli.py",
        "paperforge/config.py",
        "paperforge/commands/auth.py",
        "paperforge/services/state_signal.py",
        "paperforge/services/storage_migration.py",
        "paperforge/plugin/test/fixtures/build_e2e_vault.py",
    }
    offenders: list[str] = []
    for py_path in sorted(package_root.rglob("*.py")):
        rel = py_path.relative_to(repo_root).as_posix()
        if rel in allowlist:
            continue
        text = py_path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if '/ "System" / "PaperForge"' in line or 'cfg["system_dir"] / "PaperForge"' in line:
                offenders.append(f"{rel}:{lineno}: {stripped}")
    assert not offenders, "Hardcoded System/PaperForge path bypasses found:\n  " + "\n  ".join(offenders)


def test_reconcile_staging_prefers_durable_dir_and_honors_temp_monkeypatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    explicit = tmp_path / "durable-staging"
    monkeypatch.setenv("PAPERFORGE_STAGING_DIR", str(explicit))
    assert reconcile_staging_write_base() == explicit
    assert reconcile_staging_search_bases() == [explicit]

    monkeypatch.delenv("PAPERFORGE_STAGING_DIR", raising=False)
    custom_tmp = tmp_path / "mock-tmp"
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(custom_tmp))
    assert reconcile_staging_write_base() == custom_tmp / "paperforge-staging"
    assert reconcile_staging_search_bases() == [custom_tmp / "paperforge-staging"]
