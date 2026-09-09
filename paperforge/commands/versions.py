"""paperforge.commands.versions — display-fulltext version authority.

Ticket 07 step 6 item 6 (final semantic census): version discovery,
manifest interpretation, legacy backup-filename recognition, timestamp /
current-label semantics, key/label → canonical artifact path construction,
the restore copy, and restore-provenance mutation are all Python
authority.  The UI may only read a Python-returned artifact path for
presentation (Markdown render / text diff) — it never derives any of the
above itself.

Restore semantics stay DISPLAY-ONLY (#129): `restore` copies
``versions/<label>/fulltext.md`` → ``render/fulltext.md`` (or the legacy
``backups/fulltext.pre-rebuild.<ts>.md`` source) and persists
``meta.json.restore_provenance``.  Structure, indexes, memory units and
vectors are never touched.
"""

from __future__ import annotations

import argparse
import datetime
import shutil
from pathlib import Path
from typing import Any

BACKUP_PREFIX = "fulltext.pre-rebuild."


def _err(version: str, message: str):
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError, PFResult

    return PFResult(
        ok=False,
        command="versions",
        version=version,
        error=PFError(code=ErrorCode.VALIDATION_ERROR, message=message),
    )


def _ok(version: str, data: dict[str, Any]):
    from paperforge.core.result import PFResult

    return PFResult(ok=True, command="versions", version=version, data=data)


def _ocr_root(vault: Path) -> Path:
    from paperforge.config import load_vault_config, paperforge_paths

    return paperforge_paths(vault, load_vault_config(vault))["ocr"]


def _read_json(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    import json

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_manifest(paper_root: Path) -> dict[str, Any] | None:
    """Read versions/manifest.json — Python is the only interpreter."""
    manifest_path = paper_root / "versions" / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        parsed = _read_json(manifest_path)
    except Exception:
        return None
    if (
        isinstance(parsed, dict)
        and isinstance(parsed.get("versions"), list)
        and isinstance(parsed.get("current"), dict)
        and "label" in parsed["current"]
    ):
        return parsed
    return None


def _backup_label(ts: str) -> str:
    return f"backup-{ts}"


def _backup_timestamp_to_iso(ts: str) -> str:
    """``YYYYMMDDHHMMSS`` (legacy filename) → ISO-8601 UTC, best effort."""
    if len(ts) >= 14 and ts[:14].isdigit():
        return (
            f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}T{ts[8:10]}:{ts[10:12]}:{ts[12:14]}Z"
        )
    return ts


def list_backups(paper_root: Path) -> list[dict[str, Any]]:
    """Legacy ``backups/fulltext.pre-rebuild.<ts>.md`` recognition."""
    backups_dir = paper_root / "backups"
    if not backups_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for entry in sorted(backups_dir.iterdir()):
        if not entry.name.startswith(BACKUP_PREFIX) or not entry.name.endswith(".md"):
            continue
        ts = entry.name[len(BACKUP_PREFIX) : -len(".md")]
        try:
            size = entry.stat().st_size
        except OSError:
            size = 0
        out.append(
            {
                "label": _backup_label(ts),
                "created_at": _backup_timestamp_to_iso(ts),
                "source": "pre-rebuild",
                "fulltext_size": size,
                "path": str(entry.relative_to(paper_root.parent.parent)),
            }
        )
    return out


def _entry_paths(paper_root: Path, label: str) -> dict[str, Any]:
    """Canonical artifact paths for a label (formal version or legacy backup)."""
    if label.startswith("backup-"):
        ts = label[len("backup-") :]
        source = paper_root / "backups" / f"{BACKUP_PREFIX}{ts}.md"
        kind = "legacy_backup"
    else:
        source = paper_root / "versions" / label / "fulltext.md"
        kind = "version"
    return {
        "label": label,
        "kind": kind,
        "source_path": str(source),
        "current_path": str(paper_root / "render" / "fulltext.md"),
    }


def _paper_root(vault: Path, key: str) -> Path:
    return _ocr_root(vault) / key


def _with_paths(paper_root: Path, versions: list[Any]) -> list[dict[str, Any]]:
    """Attach the canonical artifact path to every version entry — the UI
    reads ONLY these Python-constructed paths."""
    out: list[dict[str, Any]] = []
    for entry in versions:
        if not isinstance(entry, dict):
            continue
        enriched = dict(entry)
        enriched["source_path"] = str(
            paper_root / "versions" / str(entry.get("label", "")) / "fulltext.md"
        )
        out.append(enriched)
    return out


def _paper_info(paper_root: Path) -> dict[str, Any] | None:
    manifest = read_manifest(paper_root)
    if not manifest:
        return None
    import contextlib

    versions = _with_paths(paper_root, manifest["versions"])
    total_size = 0
    for entry in versions:
        with contextlib.suppress(OSError):
            total_size += Path(str(entry["source_path"])).stat().st_size
    return {
        "key": paper_root.name,
        "title": paper_root.name.replace("_", " "),
        "versions": versions,
        "current_label": manifest["current"]["label"],
        "current_path": str(paper_root / "render" / "fulltext.md"),
        "total_size": total_size,
    }


def _run_list(vault: Path, version: str) -> int:
    root = _ocr_root(vault)
    papers: list[dict[str, Any]] = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if child.is_dir():
                info = _paper_info(child)
                if info:
                    papers.append(info)
    papers.sort(key=lambda p: p["title"].lower())
    print(_ok(version, {"intent": "versions-list", "papers": papers}).to_json())
    return 0


def _run_show(vault: Path, key: str, version: str) -> int:
    root = _paper_root(vault, key)
    if not root.is_dir():
        print(_err(version, f"unknown paper key: {key}").to_json())
        return 1
    manifest = read_manifest(root)
    if not manifest:
        # No manifest is a legitimate state (paper never rebuilt), not an
        # authority failure: ok with an empty list.
        print(
            _ok(
                version,
                {
                    "intent": "versions-show",
                    "key": key,
                    "versions": [],
                    "current_label": "",
                    "current_path": str(root / "render" / "fulltext.md"),
                },
            ).to_json()
        )
        return 0
    print(
        _ok(
            version,
            {
                "intent": "versions-show",
                "key": key,
                "versions": _with_paths(root, manifest["versions"]),
                "current_label": manifest["current"]["label"],
                "current_path": str(root / "render" / "fulltext.md"),
            },
        ).to_json()
    )
    return 0


def _run_backups(vault: Path, key: str, version: str) -> int:
    root = _paper_root(vault, key)
    if not root.is_dir():
        print(_err(version, f"unknown paper key: {key}").to_json())
        return 1
    print(
        _ok(
            version,
            {
                "intent": "versions-backups",
                "key": key,
                "backups": list_backups(root),
            },
        ).to_json()
    )
    return 0


def _run_paths(vault: Path, key: str, label: str, version: str) -> int:
    root = _paper_root(vault, key)
    if not root.is_dir():
        print(_err(version, f"unknown paper key: {key}").to_json())
        return 1
    if not label:
        manifest = read_manifest(root)
        if not manifest:
            print(_err(version, f"no version manifest for {key}").to_json())
            return 1
        label = str(manifest["current"]["label"])
    paths = _entry_paths(root, label)
    if not Path(paths["source_path"]).exists():
        print(_err(version, f"version artifact not found for {key}/{label}").to_json())
        return 1
    print(_ok(version, {"intent": "versions-paths", "key": key, **paths}).to_json())
    return 0


def _run_restore(vault: Path, key: str, label: str, version: str) -> int:
    """Display-only restore: copy source fulltext → render/fulltext.md and
    persist restore provenance. Python owns both the copy and the mutation."""
    root = _paper_root(vault, key)
    if not root.is_dir():
        print(_err(version, f"unknown paper key: {key}").to_json())
        return 1
    if not label:
        print(_err(version, "restore requires --label").to_json())
        return 1
    paths = _entry_paths(root, label)
    source = Path(paths["source_path"])
    if not source.exists():
        print(_err(version, f"version artifact not found for {key}/{label}").to_json())
        return 1
    target = Path(paths["current_path"])
    version_created_at = ""
    manifest = read_manifest(root)
    if manifest and paths["kind"] == "version":
        for entry in manifest["versions"]:
            if str(entry.get("label")) == label:
                version_created_at = str(entry.get("created_at", ""))
                break
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    except OSError as exc:
        print(_err(version, f"restore failed: {exc}").to_json())
        return 1
    provenance = {
        "label": label,
        "restored_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version_created_at": version_created_at,
    }
    meta_path = root / "meta.json"
    try:
        meta = _read_json(meta_path) if meta_path.exists() else {}
        if not isinstance(meta, dict):
            meta = {}
        meta["restore_provenance"] = provenance
        _write_json(meta_path, meta)
    except Exception:
        # Provenance is best-effort metadata; the restore itself succeeded.
        pass
    print(
        _ok(
            version,
            {
                "intent": "versions-restore",
                "key": key,
                "label": label,
                "target_path": str(target),
                "provenance": provenance,
            },
        ).to_json()
    )
    return 0


def run(args: argparse.Namespace) -> int:
    from paperforge import __version__
    from paperforge.config import resolve_vault

    try:
        vault = resolve_vault(cli_vault=getattr(args, "vault", None))
    except FileNotFoundError as exc:
        print(_err(__version__, str(exc)).to_json())
        return 1
    command = getattr(args, "versions_command", None)
    try:
        if command == "list":
            return _run_list(vault, __version__)
        if command == "show":
            return _run_show(vault, args.key, __version__)
        if command == "backups":
            return _run_backups(vault, args.key, __version__)
        if command == "paths":
            return _run_paths(vault, args.key, getattr(args, "label", "") or "", __version__)
        if command == "restore":
            return _run_restore(vault, args.key, getattr(args, "label", "") or "", __version__)
        print(_err(__version__, f"unknown versions subcommand: {command}").to_json())
        return 1
    except Exception as exc:
        from paperforge.core.errors import ErrorCode
        from paperforge.core.result import PFError, PFResult

        print(
            PFResult(
                ok=False,
                command="versions",
                version=__version__,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
            ).to_json()
        )
        return 1
