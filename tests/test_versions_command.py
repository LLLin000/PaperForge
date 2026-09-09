"""``paperforge versions`` — display-fulltext version authority (step 6 item 6).

Discovery, manifest interpretation, legacy backup recognition, timestamp
semantics, canonical path construction, the restore copy, and the
restore-provenance mutation are Python authority.  These regressions pin the
authority-result == durable-state contract for every subcommand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paperforge.commands.versions import run
from paperforge.config import load_vault_config, paperforge_paths
from tests.conftest import canonical_test_config

KEY = "ABCD1234"


def _seed(vault: Path) -> Path:
    canonical_test_config(vault)
    ocr = paperforge_paths(vault, load_vault_config(vault))["ocr"]
    root = ocr / KEY
    (root / "versions" / "v1").mkdir(parents=True)
    (root / "versions" / "v2").mkdir(parents=True)
    (root / "render").mkdir(parents=True)
    (root / "backups").mkdir(parents=True)
    (root / "versions" / "v1" / "fulltext.md").write_text("v1 text\n", encoding="utf-8")
    (root / "versions" / "v2" / "fulltext.md").write_text("v2 text\n", encoding="utf-8")
    (root / "render" / "fulltext.md").write_text("current text\n", encoding="utf-8")
    (root / "backups" / "fulltext.pre-rebuild.20260909T123456Z.md").write_text(
        "legacy text\n", encoding="utf-8"
    )
    (root / "backups" / "fulltext.pre-rebuild.20260909T123456Z.001.md").write_text(
        "legacy seq text\n", encoding="utf-8"
    )
    # non-canonical name must be ignored (not a producer artifact)
    (root / "backups" / "fulltext.pre-rebuild.20250102030405.md").write_text(
        "not canonical\n", encoding="utf-8"
    )
    (root / "meta.json").write_text(json.dumps({"ocr_finished_at": "2025-01-03T00:00:00Z"}), encoding="utf-8")
    (root / "versions" / "manifest.json").write_text(
        json.dumps(
            {
                "versions": [
                    {
                        "label": "v1",
                        "created_at": "2025-01-01T00:00:00Z",
                        "source": "pre-rebuild",
                        "fulltext_size": 8,
                    },
                    {
                        "label": "v2",
                        "created_at": "2025-01-02T00:00:00Z",
                        "source": "pre-rebuild",
                        "fulltext_size": 8,
                    },
                ],
                "current": {"label": "v2"},
            }
        ),
        encoding="utf-8",
    )
    return root


def _run(vault: Path, command: str, **kw) -> tuple[int, dict | None, str]:
    args = argparse.Namespace(
        vault=str(vault),
        vault_path=vault,
        versions_command=command,
        key=kw.get("key"),
        label=kw.get("label", ""),
        json=True,
    )
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run(args)
    out = buf.getvalue()
    try:
        return rc, json.loads(out), out
    except json.JSONDecodeError:
        return rc, None, out


def test_list_reports_manifest_versions_and_total_size(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    _seed(vault)
    root = paperforge_paths(vault, load_vault_config(vault))["ocr"] / KEY
    rc, payload, raw = _run(vault, "list")
    assert rc == 0, raw
    papers = payload["data"]["papers"]
    assert len(papers) == 1
    paper = papers[0]
    assert paper["key"] == KEY
    assert paper["current_label"] == "v2"
    assert [v["label"] for v in paper["versions"]] == ["v1", "v2"]
    assert paper["versions"][0]["source_path"] == str(
        root / "versions" / "v1" / "fulltext.md"
    )
    assert paper["current_path"] == str(root / "render" / "fulltext.md")
    expected = sum(
        (root / "versions" / label / "fulltext.md").stat().st_size
        for label in ("v1", "v2")
    )
    assert paper["total_size"] == expected  # stat'd in Python


def test_show_returns_manifest_or_fails_closed(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    _seed(vault)
    rc, payload, raw = _run(vault, "show", key=KEY)
    assert rc == 0, raw
    assert payload["data"]["current_label"] == "v2"
    # no-manifest paper is a legitimate empty state, not a failure
    (paperforge_paths(vault, load_vault_config(vault))["ocr"] / "NOMANIFEST").mkdir()
    rc3, payload3, _ = _run(vault, "show", key="NOMANIFEST")
    assert rc3 == 0
    assert payload3["data"]["versions"] == []
    assert payload3["data"]["current_label"] == ""
    # unknown key still fails closed
    rc2, payload2, _ = _run(vault, "show", key="ZZZZ9999")
    assert rc2 == 1
    assert payload2["ok"] is False


def test_backups_uses_the_real_producer_format_and_keeps_seq_identity(
    tmp_path: Path,
) -> None:
    """The SSOT producer format is fulltext.pre-rebuild.<stamp>[.<seq>].md
    with stamp = YYYYMMDDTHHMMSSZ — the earlier fixture (a compact
    YYYYMMDDHHMMSS stamp) was NOT producible and masked this."""
    vault = tmp_path / "v"
    vault.mkdir()
    root = _seed(vault)
    rc, payload, raw = _run(vault, "backups", key=KEY)
    assert rc == 0, raw
    backups = payload["data"]["backups"]
    # producer ordering is filename-sorted (seq sorts before the bare stamp)
    by_label = {b["label"]: b for b in backups}
    assert set(by_label) == {
        "backup-20260909T123456Z",
        "backup-20260909T123456Z.001",
    }
    first = by_label["backup-20260909T123456Z"]
    seq = by_label["backup-20260909T123456Z.001"]
    assert first["created_at"] == "2026-09-09T12:34:56Z"
    assert seq["created_at"] == "2026-09-09T12:34:56Z"
    assert seq["fulltext_size"] == (
        root / "backups" / "fulltext.pre-rebuild.20260909T123456Z.001.md"
    ).stat().st_size
    assert seq["source_path"].replace("\\", "/").endswith(
        "fulltext.pre-rebuild.20260909T123456Z.001.md"
    )


def test_restore_by_seq_label_hits_the_exact_backup(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    root = _seed(vault)
    rc, _, raw = _run(vault, "restore", key=KEY, label="backup-20260909T123456Z.001")
    assert rc == 0, raw
    assert (root / "render" / "fulltext.md").read_text(encoding="utf-8") == (
        "legacy seq text\n"
    )


def test_cross_paper_label_traversal_is_refused(tmp_path: Path) -> None:
    """A label is NOT a free path segment: it must exactly match an
    authority label, so a dot-segment label can never reach another paper."""
    vault = tmp_path / "v"
    vault.mkdir()
    root = _seed(vault)
    ocr = root.parent
    (ocr / "OTHERPAPER" / "render").mkdir(parents=True)
    (ocr / "OTHERPAPER" / "render" / "fulltext.md").write_text(
        "other paper bytes\n", encoding="utf-8"
    )
    before = (root / "render" / "fulltext.md").read_text(encoding="utf-8")
    for label in (
        "../../OTHERPAPER/render",
        "../../OTHERPAPER/render/fulltext.md",
        "../OTHERPAPER",
        "..",
    ):
        rc, payload, _ = _run(vault, "restore", key=KEY, label=label)
        assert rc == 1, label
        assert payload["ok"] is False
        assert (root / "render" / "fulltext.md").read_text(encoding="utf-8") == before
        rc2, payload2, _ = _run(vault, "paths", key=KEY, label=label)
        assert rc2 == 1 and payload2["ok"] is False


def test_key_traversal_is_refused_without_writing(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    root = _seed(vault)
    ocr = root.parent
    (ocr / "OTHERPAPER" / "versions" / "v1").mkdir(parents=True)
    (ocr / "OTHERPAPER" / "versions" / "v1" / "fulltext.md").write_text(
        "other\n", encoding="utf-8"
    )
    for key in ("../OTHERPAPER", "OTHERPAPER/../..", "..", "OTHERPAPER/v1"):
        rc, payload, _ = _run(vault, "restore", key=key, label="v1")
        assert rc == 1, key
        assert payload["ok"] is False
        rc2, payload2, _ = _run(vault, "show", key=key)
        assert rc2 == 1 and payload2["ok"] is False
    # no other-paper mutation happened
    assert not (ocr / "OTHERPAPER" / "render" / "fulltext.md").exists()


def test_paths_constructs_canonical_artifact_paths(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    root = _seed(vault)
    rc, payload, raw = _run(vault, "paths", key=KEY, label="v1")
    assert rc == 0, raw
    assert payload["data"]["source_path"] == str(root / "versions" / "v1" / "fulltext.md")
    assert payload["data"]["current_path"] == str(root / "render" / "fulltext.md")
    # current-label default
    rc2, payload2, raw2 = _run(vault, "paths", key=KEY)
    assert rc2 == 0, raw2
    assert payload2["data"]["label"] == "v2"
    # legacy label resolves into backups/
    rc3, payload3, raw3 = _run(vault, "paths", key=KEY, label="backup-20260909T123456Z")
    assert rc3 == 0, raw3
    assert payload3["data"]["source_path"] == str(
        root / "backups" / "fulltext.pre-rebuild.20260909T123456Z.md"
    )
    # missing artifact fails closed
    rc4, payload4, _ = _run(vault, "paths", key=KEY, label="v9")
    assert rc4 == 1 and payload4["ok"] is False


def test_restore_copies_and_persists_provenance(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    root = _seed(vault)
    rc, payload, raw = _run(vault, "restore", key=KEY, label="v1")
    assert rc == 0, raw
    # durable state: render/fulltext.md now holds the v1 bytes
    assert (root / "render" / "fulltext.md").read_text(encoding="utf-8") == "v1 text\n"
    # provenance mutation is Python-owned and durable
    meta = json.loads((root / "meta.json").read_text(encoding="utf-8"))
    prov = meta["restore_provenance"]
    assert prov["label"] == "v1"
    assert prov["version_created_at"] == "2025-01-01T00:00:00Z"
    assert prov["restored_at"]
    assert payload["data"]["target_path"] == str(root / "render" / "fulltext.md")
    assert payload["data"]["provenance_persisted"] is True
    # ocr_finished_at survives (merge, not replace)
    assert meta["ocr_finished_at"] == "2025-01-03T00:00:00Z"


def test_restore_missing_label_fails_closed_without_writing(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    root = _seed(vault)
    before = (root / "render" / "fulltext.md").read_text(encoding="utf-8")
    rc, payload, _ = _run(vault, "restore", key=KEY, label="v9")
    assert rc == 1 and payload["ok"] is False
    assert (root / "render" / "fulltext.md").read_text(encoding="utf-8") == before
    assert "restore_provenance" not in json.loads(
        (root / "meta.json").read_text(encoding="utf-8")
    )
