"""R (#161/#148) — read-model cutover acceptance.

- ZERO WRITERS: no Python code writes the three snapshot files.
- Wrong-snapshot authority: deliberately contradictory legacy snapshot files
  never influence read-model output — fresh Python responses fully determine
  UI-determining data.
- probe all aggregate + OCR pipeline-versions detail surface.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.conftest import canonical_test_config

SNAPSHOT_NAMES = (
    "memory-runtime-state.json",
    "vector-runtime-state.json",
    "runtime-health.json",
)


def test_zero_writers_no_snapshot_paths_in_python():
    """#148: the three snapshot contracts have no Python writer left.

    The sync cleanup sweep may name the files (best-effort unlink of inert
    garbage); only *write* operations on them are forbidden.
    """
    import re

    root = Path(__file__).resolve().parents[1]
    hits: list[str] = []
    write_re = re.compile(r"(write_text|write_bytes|open\()")
    for py in sorted((root / "paperforge").rglob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        for name in SNAPSHOT_NAMES:
            # a write to the snapshot name must appear on the same line
            for line in text.splitlines():
                if name in line and write_re.search(line):
                    hits.append(f"{py.relative_to(root)}: {name}")
                    break
    assert not hits, f"snapshot writers remain: {hits}"


def test_snapshot_module_deleted():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "paperforge" / "memory" / "state_snapshot.py").exists()


def test_wrong_snapshots_do_not_influence_read_models(tmp_path: Path):
    """#148 key acceptance: even with intentionally contradictory snapshot
    files present, fresh read-model responses fully determine state."""
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault, system_dir="System")
    (vault / "System" / "PaperForge" / "indexes").mkdir(parents=True, exist_ok=True)

    # Deliberately wrong snapshots: lie about the memory DB and vector state.
    lies = {
        "memory-runtime-state.json": {
            "paper_count_db": 999, "needs_rebuild": False, "fresh": True,
        },
        "vector-runtime-state.json": {
            "enabled": True, "healthy": True, "chunk_count": 999,
        },
        "runtime-health.json": {"summary": {"status": "ok"}},
    }
    for name, content in lies.items():
        (vault / "System" / "PaperForge" / "indexes" / name).write_text(
            json.dumps(content), encoding="utf-8")

    # The read model must report the TRUE state (no DB) — never the lies.
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault),
         "probe", "memory", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["module"] == "memory"
    assert envelope["capability_state"] in ("needs_action", "missing_input", "unknown")
    assert envelope["reason"]["code"] != "memory.ready"

def test_sync_cleanup_removes_legacy_snapshots_best_effort(tmp_path):
    """#148: sync's best-effort sweep removes the three retired snapshot
    files but never touches other indexes files; failure never fails sync."""
    from paperforge.commands.sync import _cleanup_legacy_snapshot_files

    indexes = tmp_path / "99_System" / "PaperForge" / "indexes"
    indexes.mkdir(parents=True)
    for name in ("memory-runtime-state.json", "vector-runtime-state.json", "runtime-health.json", "orphan-state.json"):
        (indexes / name).write_text("{}", encoding="utf-8")
    _cleanup_legacy_snapshot_files(tmp_path)
    left = sorted(p.name for p in indexes.iterdir())
    assert left == ["orphan-state.json"], left



def test_probe_all_aggregates_six_modules_with_derived_maintenance(tmp_path: Path):
    """#140: probe all = five base envelopes (read exactly once) + the
    maintenance projection derived from those exact envelopes. Six modules."""
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault),
         "probe", "all", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["module"] == "all"
    assert sorted(payload["modules"].keys()) == [
        "help", "installation", "library", "maintenance", "memory", "ocr",
    ]
    for env in payload["modules"].values():
        assert env["module"] in payload["modules"]
    # maintenance is a projection of the base envelopes
    maintenance = payload["modules"]["maintenance"]
    assert "items" in maintenance
    for item in maintenance["items"]:
        assert item["module"] in ("installation", "library", "ocr", "memory", "help")


def test_probe_all_derives_maintenance_with_zero_reprobe(monkeypatch, tmp_path: Path):
    """#140: the maintenance envelope is derived from the five base results;
    no reader is called a second time."""
    import paperforge.commands.probe as probe_mod

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)

    calls: dict[str, int] = {}
    for name in ("probe_installation", "probe_library", "probe_ocr", "probe_memory", "probe_help"):
        original = getattr(probe_mod, name)

        def make_wrapper(mod_name: str, fn):
            def wrapper(*args, **kwargs):
                calls[mod_name] = calls.get(mod_name, 0) + 1
                return fn(*args, **kwargs)
            return wrapper

        monkeypatch.setattr(probe_mod, name, make_wrapper(name, original))

    from io import StringIO
    import contextlib
    out = StringIO()
    with contextlib.redirect_stdout(out):
        assert probe_mod._run_probe_all(vault, json_output=False) == 0
    # each base reader exactly once; maintenance never re-probes
    assert calls == {"probe_installation": 1, "probe_library": 1, "probe_ocr": 1,
                     "probe_memory": 1, "probe_help": 1}, calls


def test_ocr_pipeline_versions_detail_surface(tmp_path: Path):
    """#140/#148: the per-paper OCR pipeline-version list is a detail command."""
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault),
         "ocr", "pipeline-versions", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "ocr pipeline-versions"
    assert payload["data"]["total"] == 0
    assert payload["data"]["versions"] == []


def test_probe_ocr_envelope_has_no_per_paper_detail(tmp_path: Path):
    """The envelope never carries the per-paper detail; the summary helpers
    stay available for the ready tail (#148)."""
    from paperforge.commands.probe import ocr_pipeline_version_summary, paper_pipeline_versions

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    result = subprocess.run(
        [sys.executable, "-m", "paperforge", "--vault", str(vault),
         "probe", "ocr", "--json"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    envelope = json.loads(result.stdout)
    assert "per_paper_pipeline_version" not in envelope
    # #148: the envelope keeps the summary on every rows-bearing path
    assert envelope.get("pipeline_version_summary") == {
        "total": 0, "on_current": 0, "stale": 0,
    }
    assert ocr_pipeline_version_summary(vault, []) == (0, 0)
    assert paper_pipeline_versions(vault, []) == []
